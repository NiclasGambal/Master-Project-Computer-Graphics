import bpy
import math
import mathutils
import random
from mathutils import Vector
import os
import numpy as np

"""
Script Name: voxelgrid.py
Description: Constructs a voxel grid by sampling the scene from the camera's perspective.
             Classifies voxels based on object intersections and saves the grid along with metadata.
Usage: Run this script in Blender to generate the voxel grid for subsequent processing.
"""

# --------------------------------------------------
# User Adjustable Parameters
# --------------------------------------------------
DEPTH_SLICES = 150           # Number of slices along the depth axis
SUB_STEPS = 2                # Sub-samples per voxel slice (for anti-aliasing)
PIXEL_JITTER_STRENGTH = 0.2  # Jitter strength to reduce aliasing
MAX_EMPTY = 200              # Threshold for consecutive empty slices (early exit)
EPSILON = 1e-5               # Small offset to avoid self-intersections

# --------------------------------------------------
# Helper Functions
# --------------------------------------------------
def point_in_mesh_local(obj, point_world):
    """
    Determine if the world-space point is inside the object.
    Transforms the point to local space and uses an odd/even ray test along +X.
    """
    m_inv = obj.matrix_world.inverted()
    point_local = m_inv @ point_world
    direction_local = Vector((1, 0, 0))
    max_dist = 1e8
    hits = 0
    origin = point_local + direction_local * 1e-4
    while True:
        end = origin + direction_local * max_dist
        hit, loc, _, _ = obj.ray_cast(origin, end)
        if not hit:
            break
        hits += 1
        offset = 1e-4
        origin = loc + direction_local * offset
        max_dist -= (loc - point_local).length
        if max_dist <= 0:
            break
    return (hits % 2) == 1

# --------------------------------------------------
# Main Execution
# --------------------------------------------------
scene = bpy.context.scene
depsgraph = bpy.context.evaluated_depsgraph_get()
cam_obj = scene.camera
if not cam_obj:
    raise RuntimeError("No active camera found!")
cam_data = cam_obj.data
cam_world_matrix = cam_obj.matrix_world
cam_location = cam_world_matrix.translation

width = int(scene.render.resolution_x * scene.render.resolution_percentage / 100)
height = int(scene.render.resolution_y * scene.render.resolution_percentage / 100)
clip_start, clip_end = cam_data.clip_start, cam_data.clip_end

def compute_fov(camera_data):
    sensor_size = camera_data.sensor_height if camera_data.sensor_fit == 'VERTICAL' else camera_data.sensor_width
    return 2.0 * math.atan((sensor_size * 0.5) / camera_data.lens)

fov_y = compute_fov(cam_data)
aspect = width / float(height)
shift_x, shift_y = cam_data.shift_x, cam_data.shift_y

# --------------------------------------------------
# Object Classification
# --------------------------------------------------
objects_by_type = {
    "skeleton": [],
    "muscle": [],
    "body": []
}
for obj in scene.objects:
    if obj.type == 'MESH':
        lower_name = obj.name.lower()
        if "skeleton" in lower_name:
            objects_by_type["skeleton"].append(obj)
        elif "muscle" in lower_name:
            objects_by_type["muscle"].append(obj)
        elif "body" in lower_name:
            objects_by_type["body"].append(obj)

# --------------------------------------------------
# Determine Depth Range in Front of the Camera
# --------------------------------------------------
cam_inv = cam_world_matrix.inverted()
min_dist = float('inf')
max_dist = float('-inf')
for obj_list in objects_by_type.values():
    for obj in obj_list:
        if not hasattr(obj.data, "vertices"):
            continue
        for v in obj.data.vertices:
            world_co = obj.matrix_world @ v.co
            cam_co = cam_inv @ world_co
            if cam_co.z < 0:
                dist = -cam_co.z
                min_dist = min(min_dist, dist)
                max_dist = max(max_dist, dist)
if min_dist == float('inf') or max_dist == float('-inf'):
    min_dist = clip_start
    max_dist = clip_end
min_dist = max(min_dist, clip_start)
max_dist = min(max_dist, clip_end)
depth_range = max_dist - min_dist
if depth_range <= 0:
    min_dist = clip_start
    max_dist = clip_end
    depth_range = max_dist - min_dist
print(f"Sampling depth range: {min_dist:.4f} -> {max_dist:.4f}")

# --------------------------------------------------
# Build the Voxel Grid
# --------------------------------------------------
step = depth_range / DEPTH_SLICES
voxel_grid = [
    [
        ["none" for _ in range(DEPTH_SLICES)]
        for _ in range(width)
    ]
    for _ in range(height)
]
depth_values = [min_dist + k * step for k in range(DEPTH_SLICES)]

# --------------------------------------------------
# Fill the Voxel Grid
# --------------------------------------------------
print("Filling voxel grid...")
def get_tag(pt):
    """Return a voxel tag based on the objects the point is inside."""
    if any(point_in_mesh_local(o, pt) for o in objects_by_type["skeleton"]):
        return "skeleton"
    elif any(point_in_mesh_local(o, pt) for o in objects_by_type["muscle"]):
        return "muscle"
    elif any(point_in_mesh_local(o, pt) for o in objects_by_type["body"]):
        return "body"
    return "none"

for j in range(height):
    v = (j + 0.5) / height
    for i in range(width):
        u = (i + 0.5) / width
        # Apply pixel jitter for anti-aliasing.
        jx = (random.random() - 0.5) * PIXEL_JITTER_STRENGTH / width
        jy = (random.random() - 0.5) * PIXEL_JITTER_STRENGTH / height
        u_j = u + jx
        v_j = v + jy
        screen_x = (u_j - 0.5) * 2.0 - shift_x * 2.0
        screen_y = (v_j - 0.5) * 2.0 - shift_y * 2.0
        px = screen_x * aspect * math.tan(fov_y * 0.5)
        py = screen_y * math.tan(fov_y * 0.5)
        pz = -1.0
        local_point = Vector((px, py, pz))
        world_point = cam_world_matrix @ local_point
        ray_dir_world = (world_point - cam_location).normalized()

        found_geometry = False
        exited_geometry = False
        empty_count = 0

        for k, base_dist in enumerate(depth_values):
            if exited_geometry:
                break
            tags = []
            for s in range(SUB_STEPS):
                frac = random.random()
                dist_sub = base_dist + frac * step
                pt_sample = cam_location + ray_dir_world * dist_sub + ray_dir_world * EPSILON
                tags.append(get_tag(pt_sample))
            if "skeleton" in tags:
                voxel_tag = "skeleton"
            elif "muscle" in tags:
                voxel_tag = "muscle"
            elif "body" in tags:
                voxel_tag = "body"
            else:
                voxel_tag = "none"
            voxel_grid[j][i][k] = voxel_tag
            if voxel_tag != "none":
                found_geometry = True
                empty_count = 0
            else:
                if found_geometry:
                    empty_count += 1
                    if empty_count > MAX_EMPTY:
                        exited_geometry = True
    if j % 50 == 0:
        print(f"Processed row {j+1}/{height}")

print("Voxel grid construction complete.")

# --------------------------------------------------
# Save Voxel Grid and Metadata
# --------------------------------------------------
save_dir = bpy.path.abspath("//")
if not os.path.exists(save_dir):
    os.makedirs(save_dir)
np.save(os.path.join(save_dir, "voxel_grid.npy"), voxel_grid)
metadata_path = os.path.join(save_dir, "voxel_metadata.txt")
with open(metadata_path, "w") as f:
    f.write(f"{width} {height}\n")
    f.write(f"{step}\n")
    f.write(f"{DEPTH_SLICES}\n")
print("Voxel grid and metadata saved.")
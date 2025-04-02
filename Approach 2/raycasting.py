import bpy
import math
from math import tan, exp
import mathutils
from mathutils import Vector
import os

"""
Script Name: raycasting.py
Description: Simulates radiography using a ray-casting method in Blender.
             Computes transmission based on object density and generates an radiography projection image.
Usage: Run this script in Blender with an active camera and scene.
"""

# --------------------------------------------------
# User Adjustable Parameters
# --------------------------------------------------
DENSITY_VALUES = {
    "Bone": 0.5,
    "Muscle": 0.08,
    "Skin": 0.05
}
EPS_DIST = 1e-4       # Minimum step distance
DOT_THRESHOLD = 1e-6  # Dot product threshold

# --------------------------------------------------
# Helper Functions
# --------------------------------------------------
def compute_fov(camera_data):
    sensor = camera_data.sensor_height if camera_data.sensor_fit == 'VERTICAL' else camera_data.sensor_width
    return 2.0 * math.atan((sensor * 0.5) / camera_data.lens)

def classify_object(obj):
    name = obj.name.lower()
    if "skeleton" in name:
        return "Bone"
    elif "muscles" in name:
        return "Muscle"
    elif "body" in name:
        return "Skin"
    return None

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

width, height = scene.render.resolution_x, scene.render.resolution_y
clip_start, clip_end = cam_data.clip_start, cam_data.clip_end
fov_y = compute_fov(cam_data)
aspect = width / float(height)
shift_x, shift_y = cam_data.shift_x, cam_data.shift_y

object_to_density = {}
for obj in scene.objects:
    if obj.type == 'MESH':
        cls = classify_object(obj)
        if cls:
            object_to_density[obj] = DENSITY_VALUES[cls]

projection = [[0.0 for _ in range(width)] for _ in range(height)]
print("Starting ray-casting simulation...")

for j in range(height):
    v = (j + 0.5) / height
    for i in range(width):
        u = (i + 0.5) / width
        screen_x = (u - 0.5) * 2.0 - shift_x * 2.0
        screen_y = (v - 0.5) * 2.0 - shift_y * 2.0
        px = screen_x * aspect * tan(fov_y * 0.5)
        py = screen_y * tan(fov_y * 0.5)
        pz = -1.0
        local_point = Vector((px, py, pz))
        world_point = cam_world_matrix @ local_point
        ray_dir = (world_point - cam_location).normalized()

        inside_stack = []
        total_density = 0.0
        current_dist = clip_start

        while current_dist < clip_end:
            seg_origin = cam_location + ray_dir * current_dist
            hit, hit_loc, hit_norm, _, hit_obj, _ = scene.ray_cast(depsgraph, seg_origin, ray_dir, distance=(clip_end - current_dist))
            if not hit:
                total_density += sum(object_to_density.get(o, 0.0) for o in inside_stack) * (clip_end - current_dist)
                break
            dist_to_hit = (hit_loc - seg_origin).length
            if dist_to_hit < EPS_DIST:
                current_dist += EPS_DIST
                continue
            abs_hit = current_dist + dist_to_hit
            total_density += sum(object_to_density.get(o, 0.0) for o in inside_stack) * dist_to_hit
            dot_val = ray_dir.dot(hit_norm)
            if abs(dot_val) < DOT_THRESHOLD:
                current_dist = abs_hit + EPS_DIST
                continue
            if dot_val < 0:
                inside_stack.append(hit_obj)
            elif hit_obj in inside_stack:
                inside_stack.remove(hit_obj)
            current_dist = abs_hit + max(EPS_DIST, 1e-5)

        projection[j][i] = 1.0 - exp(-total_density)
    if j % 50 == 0:
        print(f"Processed row {j+1}/{height}")

print("Ray-casting simulation complete.")

if "XrayProjection" in bpy.data.images:
    bpy.data.images.remove(bpy.data.images["XrayProjection"])
img = bpy.data.images.new("XrayProjection", width=width, height=height)
pixels = []
for row in projection:
    for val in row:
        pixels.extend([val, val, val, 1.0])

# Save final result as approach 2.
output_dir = bpy.path.abspath("//")
final_path = os.path.join(output_dir, "approach_2_final_result.png")
img.pixels = pixels
img.filepath_raw = final_path
img.file_format = 'PNG'
img.save()
print("Final radiography result of the second approach created at:", final_path)
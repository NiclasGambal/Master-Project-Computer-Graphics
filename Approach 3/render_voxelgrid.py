import bpy
import numpy as np
import math
import os

"""
Script Name: render_voxelgrid.py
Description: Integrates a precomputed voxel grid to generate an X-ray projection image.
             Loads metadata and voxel grid data, performs integration, and saves the result.
Usage: Run this script in Blender after generating the voxel grid.
"""

# --------------------------------------------------
# User Adjustable Parameters
# --------------------------------------------------
DENSITY_MAPPING = {
    "skeleton": 0.5,
    "muscle":   0.05,
    "body":     0.02,
    "marrow":   0.1,
    "none":     0.0
}

# --------------------------------------------------
# Main Execution
# --------------------------------------------------
save_dir = bpy.path.abspath("//")
metadata_path = os.path.join(save_dir, "voxel_metadata.txt")
with open(metadata_path, "r") as f:
    lines = f.readlines()
    width, height = int(lines[0].split()[0]), int(lines[0].split()[1])
    step = float(lines[1].strip())
    depth_slices = int(lines[2].strip())

voxel_grid_path = os.path.join(save_dir, "voxel_grid.npy")
voxel_grid = np.load(voxel_grid_path, allow_pickle=True)
print("Loaded voxel grid with shape:", voxel_grid.shape)

projection = [[0.0 for _ in range(width)] for _ in range(height)]
for j in range(height):
    for i in range(width):
        raw_sum = sum(DENSITY_MAPPING[voxel_grid[j][i][k]] for k in range(depth_slices))
        total_density = raw_sum * step
        intensity = 1.0 - math.exp(-total_density)
        projection[j][i] = intensity
    if j % 50 == 0:
        print(f"Processed row {j+1}/{height}")

if "XrayOutput" in bpy.data.images:
    bpy.data.images.remove(bpy.data.images["XrayOutput"])
img = bpy.data.images.new("XrayOutput", width=width, height=height)
pixels = []
for row in projection:
    for val in row:
        gray = max(0.0, min(val, 1.0))
        pixels.extend([gray, gray, gray, 1.0])
img.pixels = pixels
img.file_format = 'PNG'
# Save final result as approach 3.
output_path = os.path.join(save_dir, "approach_3_final_result.png")
img.filepath_raw = output_path
img.save()
print("Saved X-ray image to", output_path)

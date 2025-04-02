import bpy
import numpy as np

"""
Script Name: simulate_marrow.py
Description: Processes a voxel grid by converting interior 'skeleton' voxels to 'marrow' 
             to simulate bone marrow. The parameter SHELL_THICKNESS controls how many 
             voxel layers from the boundary remain as skeleton.
Usage: Run this script in Blender after the voxel grid has been generated.
"""

# --------------------------------------------------
# User Adjustable Parameters
# --------------------------------------------------
# Number of layers that remain as the outer shell (i.e. not converted to marrow).
SHELL_THICKNESS = 1  # Increase for a thicker outer shell (e.g., 2 or 3)

# --------------------------------------------------
# Helper Functions
# --------------------------------------------------
def erode_mask(mask, iterations=1):
    """
    Perform binary erosion on a 3D boolean mask without wrap-around.
    Each iteration peels off one voxel layer.
    """
    eroded = mask.copy()
    for _ in range(iterations):
        new_mask = np.zeros_like(eroded, dtype=bool)
        # Only process the inner region to avoid wrap-around effects.
        new_mask[1:-1, 1:-1, 1:-1] = (
            eroded[0:-2, 1:-1, 1:-1] &  # neighbor in -X
            eroded[2:  , 1:-1, 1:-1] &  # neighbor in +X
            eroded[1:-1, 0:-2, 1:-1] &  # neighbor in -Y
            eroded[1:-1, 2:  , 1:-1] &  # neighbor in +Y
            eroded[1:-1, 1:-1, 0:-2] &  # neighbor in -Z
            eroded[1:-1, 1:-1, 2:  ]    # neighbor in +Z
        )
        eroded = new_mask
    return eroded

# --------------------------------------------------
# Main Execution
# --------------------------------------------------
input_path = bpy.path.abspath("//voxel_grid.npy")
voxel_grid = np.load(input_path, allow_pickle=True)

# Create a mask for 'skeleton' voxels.
skeleton_mask = (voxel_grid == 'skeleton')

# Perform erosion to determine the interior where marrow will be created.
# Voxels that remain after eroding by SHELL_THICKNESS are considered fully interior.
interior_mask = erode_mask(skeleton_mask, iterations=SHELL_THICKNESS)

# Create a copy of the original voxel grid.
output_grid = voxel_grid.copy()
# Convert the interior skeleton voxels to 'marrow'; outer shell remains 'skeleton'.
output_grid[interior_mask] = 'marrow'

output_path = bpy.path.abspath("//voxel_grid_marrow.npy")
np.save(output_path, output_grid)

print(f"Bone marrow simulation complete with shell thickness: {SHELL_THICKNESS}.")
print(f"Output saved to {output_path}")

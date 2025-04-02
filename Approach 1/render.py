import bpy, os

"""
Script Name: render.py
Description: Renders individual mesh objects from the Blender scene as separate radiography layers.
             Excludes certain objects and saves each render as a PNG file.
Usage: Run this script in Blender with the desired scene loaded.
"""

# --------------------------------------------------
# User Adjustable Parameters
# --------------------------------------------------

# Set the fixed output directory.
OUTPUT_DIR = "C:/approach_1_results/"
EXCLUDE_OBJECTS = {
    "Emitter",
    "objarterialsystem_arm_left_001",
    "objlymphaticnodes_arm_left_001",
    "objlymphaticsystem_arm_left_001",
    "objnervoussystem_arm_left_001",
    "objvenoussystem_arm_left_001",
    "objtissue_arm_left_001"
}
RENDER_SAMPLES = 128         # Number of samples for Cycles rendering
RESOLUTION_PERCENTAGE = 100  # Render resolution percentage

# --------------------------------------------------
# Main Execution
# --------------------------------------------------
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

scene = bpy.context.scene
meshes = [obj for obj in scene.objects if obj.type == 'MESH' and obj.name not in EXCLUDE_OBJECTS]

scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'BW'
scene.render.engine = 'CYCLES'
scene.render.resolution_percentage = RESOLUTION_PERCENTAGE
scene.render.film_transparent = True
scene.cycles.samples = RENDER_SAMPLES

for obj in meshes:
    # Hide all meshes.
    for mesh in meshes:
        mesh.hide_render = True
    # Show only the current mesh.
    obj.hide_render = False
    scene.render.filepath = os.path.join(OUTPUT_DIR, f"{obj.name}.png")
    bpy.ops.render.render(write_still=True)

print("Individual radiography results created at, ", OUTPUT_DIR)

import bpy
import bmesh
from mathutils import Vector

"""
Script Name: setup.py
Description: Sets up the Blender scene for radiography simulation by creating an emitter plane,
             assigning shaders to mesh objects, optionally closing holes in meshes,
             and creating a simple compositing node setup with a color ramp.
Usage: Run this script in Blender to prepare the scene.
"""

# --------------------------------------------------
# User Adjustable Parameters
# --------------------------------------------------

GROUP_NAME = "arm_realistic_male_anatomy_grp"  # Parent object name for mesh group
ADD_NOISE = False                               # Toggle to add volume scatter noise in materials
CLOSE_HOLES = True                              # Toggle to run hole-closing routine on mesh objects
CREATE_PLANE = True                             # Toggle for creating the emitter plane

OFFSET = 2.0                                    # Extra distance for plane placement along camera view direction
SCALE_MULTIPLIER = 1.5                          # Scale multiplier for plane relative to mesh extents

densities = {
    "objarterialsystem": 0,
    "objvenoussystem": 0,
    "objlymphatic": 0,
    "objmuscles": 0.03,
    "objnervoussystem": 0.15,
    "objskeleton": 0.15,
    "objtissue": 0,
    "objbody": 0.01,
}

EMISSION_INTENSITY = 1.0           # Emission shader intensity for the emitter plane

# New parameter for compositing node setup
INVERTED = True                    # If True, the color ramp inverts the image (white->black). Otherwise normal black->white.

# --------------------------------------------------
# Helper Functions
# --------------------------------------------------

def create_plane(name, location, rotation, scale):
    """Create a plane with the given parameters."""
    bpy.ops.mesh.primitive_plane_add(location=location, rotation=rotation)
    plane = bpy.context.object
    plane.name = name
    plane.scale = scale
    return plane

def get_mesh_group_bbox(parent_name):
    """
    Compute the overall bounding box (min_corner, max_corner) for all MESH children
    of the specified parent object.
    """
    parent_obj = bpy.data.objects.get(parent_name)
    if not parent_obj:
        print(f"Mesh group parent '{parent_name}' not found!")
        return None, None
    mesh_children = [child for child in parent_obj.children if child.type == 'MESH']
    if not mesh_children:
        print(f"No mesh children found for '{parent_name}'.")
        return None, None

    min_corner = Vector((float('inf'), float('inf'), float('inf')))
    max_corner = Vector((-float('inf'), -float('inf'), -float('inf')))

    for obj in mesh_children:
        for corner in obj.bound_box:
            world_corner = obj.matrix_world @ Vector(corner)
            min_corner.x = min(min_corner.x, world_corner.x)
            min_corner.y = min(min_corner.y, world_corner.y)
            min_corner.z = min(min_corner.z, world_corner.z)
            max_corner.x = max(max_corner.x, world_corner.x)
            max_corner.y = max(max_corner.y, world_corner.y)
            max_corner.z = max(max_corner.z, world_corner.z)

    return min_corner, max_corner

def close_holes_in_mesh(mesh_obj):
    """Close boundary edges in the mesh to prevent volume shader issues."""
    if mesh_obj.type != 'MESH':
        return
    bpy.context.view_layer.objects.active = mesh_obj
    bpy.ops.object.mode_set(mode='EDIT')
    bm = bmesh.from_edit_mesh(mesh_obj.data)
    edges_to_fill = [edge for edge in bm.edges if edge.is_boundary]
    if edges_to_fill:
        bmesh.ops.contextual_create(bm, geom=edges_to_fill)
    bmesh.update_edit_mesh(mesh_obj.data)
    bpy.ops.object.mode_set(mode='OBJECT')

# --------------------------------------------------
# Main Execution
# --------------------------------------------------

# 1) Optionally create the emitter plane
if CREATE_PLANE:
    min_corner, max_corner = get_mesh_group_bbox(GROUP_NAME)
    if not min_corner or not max_corner:
        # Fallback: create a small plane at origin if bounding box not found
        plane = create_plane("Emitter", location=(0, 0, 0), rotation=(0, 0, 0), scale=(1, 1, 1))
        print("Fallback: Created plane at origin.")
    else:
        group_center = (min_corner + max_corner) * 0.5
        size_y = max_corner.y - min_corner.y
        size_z = max_corner.z - min_corner.z
        max_extent = max(size_y, size_z)
        plane_scale_value = max_extent * SCALE_MULTIPLIER
        plane_scale = (plane_scale_value, plane_scale_value, 1)

        camera = bpy.context.scene.camera or bpy.data.objects.get("Camera")
        if camera:
            cam_location = camera.location.copy()
            cam_dir = (group_center - cam_location).normalized()
            corners = [
                Vector((min_corner.x, min_corner.y, min_corner.z)),
                Vector((min_corner.x, min_corner.y, max_corner.z)),
                Vector((min_corner.x, max_corner.y, min_corner.z)),
                Vector((min_corner.x, max_corner.y, max_corner.z)),
                Vector((max_corner.x, min_corner.y, min_corner.z)),
                Vector((max_corner.x, min_corner.y, max_corner.z)),
                Vector((max_corner.x, max_corner.y, min_corner.z)),
                Vector((max_corner.x, max_corner.y, max_corner.z))
            ]
            dists = [(corner - cam_location).dot(cam_dir) for corner in corners]
            farthest = max(dists)
            plane_distance = farthest + OFFSET
            plane_location = cam_location + cam_dir * plane_distance
            normal_dir = (cam_location - plane_location).normalized()
            plane_rotation = normal_dir.to_track_quat('Z', 'Y').to_euler()
        else:
            print("No active camera found; defaulting to group center.")
            plane_location = group_center
            plane_rotation = (0, 0, 0)
        plane = create_plane("Emitter", location=plane_location, rotation=plane_rotation, scale=plane_scale)
        print("Plane created at", plane_location)

    # Assign an emission material to the Emitter plane
    emitter_obj = bpy.data.objects.get("Emitter")
    if emitter_obj:
        mat = bpy.data.materials.new(name="EmitterMaterial")
        mat.use_nodes = True
        nt = mat.node_tree
        for node in nt.nodes:
            nt.nodes.remove(node)
        emission_node = nt.nodes.new(type="ShaderNodeEmission")
        emission_node.inputs["Strength"].default_value = EMISSION_INTENSITY
        output_node = nt.nodes.new(type="ShaderNodeOutputMaterial")
        nt.links.new(emission_node.outputs["Emission"], output_node.inputs["Surface"])
        emitter_obj.data.materials.clear()
        emitter_obj.data.materials.append(mat)
        print("Emitter material assigned.")
    else:
        print("Emitter plane not found.")

# 2) Shader assignment for objects whose names start with "obj"
for obj in bpy.data.objects:
    if obj.type == 'MESH' and obj.name.startswith("obj"):
        for mat in obj.data.materials:
            if not mat or not mat.node_tree:
                continue
            nt = mat.node_tree
            # Find or create the Material Output node
            output_node = None
            for node in nt.nodes:
                if node.type == 'OUTPUT_MATERIAL':
                    output_node = node
                    break
            if output_node is None:
                output_node = nt.nodes.new(type="ShaderNodeOutputMaterial")
            # Remove all other nodes
            for node in list(nt.nodes):
                if node != output_node:
                    nt.nodes.remove(node)
            # Create a Transparent BSDF for the Surface
            transparent_node = nt.nodes.new(type="ShaderNodeBsdfTransparent")
            transparent_node.location = (-300, 100)
            nt.links.new(transparent_node.outputs["BSDF"], output_node.inputs["Surface"])
            # Create a Volume Absorption node
            absorption_node = nt.nodes.new(type="ShaderNodeVolumeAbsorption")
            absorption_node.location = (-300, -100)
            density_value = 0
            for prefix, density in densities.items():
                if obj.name.startswith(prefix):
                    density_value = density
                    break
            absorption_node.inputs["Density"].default_value = density_value
            # Optionally add volume scatter (ADD_NOISE)
            if ADD_NOISE:
                scatter_node = nt.nodes.new(type="ShaderNodeVolumeScatter")
                scatter_node.location = (-300, -300)
                scatter_node.inputs["Density"].default_value = density_value
                add_shader_node = nt.nodes.new(type="ShaderNodeAddShader")
                add_shader_node.location = (0, -200)
                nt.links.new(absorption_node.outputs["Volume"], add_shader_node.inputs[0])
                nt.links.new(scatter_node.outputs["Volume"], add_shader_node.inputs[1])
                nt.links.new(add_shader_node.outputs["Shader"], output_node.inputs["Volume"])
            else:
                nt.links.new(absorption_node.outputs["Volume"], output_node.inputs["Volume"])

print("Setup complete: Scene and materials updated.")

# 3) Optionally close holes in all meshes
if CLOSE_HOLES:
    print("Closing holes in meshes...")
    for obj in bpy.context.scene.objects:
        if obj.type == 'MESH':
            close_holes_in_mesh(obj)
    print("Mesh hole closing complete.")

# 4) Create a simple compositing node setup with a Color Ramp, if desired
#    We'll do it unconditionally here, but you can wrap it in another toggle if needed.
scene = bpy.context.scene
scene.use_nodes = True
node_tree = scene.node_tree

# Remove existing compositor nodes (optional - so we start fresh)
for node in node_tree.nodes:
    node_tree.nodes.remove(node)

# Create the necessary nodes
render_layers_node = node_tree.nodes.new(type="CompositorNodeRLayers")
render_layers_node.location = (-400, 0)

color_ramp_node = node_tree.nodes.new(type="CompositorNodeValToRGB")
color_ramp_node.label = "Color Ramp (Invert)" if INVERTED else "Color Ramp"
color_ramp_node.location = (-150, 0)

composite_node = node_tree.nodes.new(type="CompositorNodeComposite")
composite_node.location = (100, 0)

# Configure the Color Ramp stops depending on INVERTED
if INVERTED:
    # White at position 0, black at position 1
    color_ramp_node.color_ramp.elements[0].position = 0.0
    color_ramp_node.color_ramp.elements[0].color = (1, 1, 1, 1)
    color_ramp_node.color_ramp.elements[1].position = 1.0
    color_ramp_node.color_ramp.elements[1].color = (0, 0, 0, 1)
else:
    # Black at position 0, white at position 1
    color_ramp_node.color_ramp.elements[0].position = 0.0
    color_ramp_node.color_ramp.elements[0].color = (0, 0, 0, 1)
    color_ramp_node.color_ramp.elements[1].position = 1.0
    color_ramp_node.color_ramp.elements[1].color = (1, 1, 1, 1)

# Link the nodes: Render Layers -> Color Ramp -> Composite
node_tree.links.new(render_layers_node.outputs["Image"], color_ramp_node.inputs["Fac"])
node_tree.links.new(color_ramp_node.outputs["Image"], composite_node.inputs["Image"])

print("Compositing node setup complete.")

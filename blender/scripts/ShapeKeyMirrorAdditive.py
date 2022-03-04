bl_info = {
    "name": "Shape Key Mirror Additive Extras",
    "blender": (2, 80, 0),
    "category": "Object",
}

"""
Adds two extra buttons to the Shape Key Specials Menu (shape key context menu) that are like "Mirror Shape Key" and "Mirror Shape Key (Topology)",
 but add the mirrored movement to the current shape. This makes it easy to take a shape key for one side of a model and then additively mirror it
 onto itself so that the shape key now affects both sides.

This is equivalent to making a copy of the active shape key, mirroring the active shape key, blending the pre-mirror copy into the active shape key
 and then deleting the pre-mirror copy.
 """

import bpy
import numpy as np

# Mirror a shape key, but add the mirrored shape together with the current shape
def mirror_shape_key_additive(context, use_topology=False):
    object = context.object
    data = object.data
    active_key = object.active_shape_key
    relative_key = active_key.relative_key
    # Get the blend shape positions prior to mirroring
    num_verts = len(active_key.data)
    num_co = num_verts * 3
    orig_shape_positions = np.empty(num_co, dtype=np.single)
    active_key.data.foreach_get('co', orig_shape_positions)
    # Mirror the original shape key with the op
    mirror_result = bpy.ops.object.shape_key_mirror(use_topology=use_topology)
    if 'FINISHED' in mirror_result:
        # Add the shape key we copied earlier, we figure out how much to move by subtracting the position in the relative key
        # Get the relative key positions
        relative_key_positions = np.empty(num_co, dtype=np.single)
        relative_key.data.foreach_get('co', relative_key_positions)
        # Get the mirrored key positions
        mirrored_key_positions = np.empty(num_co, dtype=np.single)
        active_key.data.foreach_get('co', mirrored_key_positions)
        # Subtract the relative key to get the movement of the key
        relative_orig_movement = np.subtract(orig_shape_positions, relative_key_positions, out=orig_shape_positions)
        # Add the original relative movement to the mirrored positions
        mirrored_key_positions += relative_orig_movement
        # Set the updated positions with the mirrored possitions with the original movement added in
        active_key.data.foreach_set('co', mirrored_key_positions)
        # The visuals don't update immediately, so we'll set the value of the shape key to cause the visuals to update
        active_key.value = active_key.value
    # The mirror result already contains 'FINISHED' or an error so just return it as is
    return mirror_result

class MYSTERYEM_shape_key_mirror_additive(bpy.types.Operator):
    #tooltip
    """Add the mirror of the current shape key along the local x axis"""
    
    bl_idname = "mysteryem.shape_key_mirror_additive"
    bl_label = "Mirror shape key (Additive)"
    bl_context = "objectmode"
    bl_options = {'REGISTER', 'UNDO'}
    use_topology: bpy.props.BoolProperty(name="Use Topology", default=False)
    
    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT' and context.object and context.object.type == 'MESH' and context.object.active_shape_key
    
    def execute(self, context):
        return mirror_shape_key_additive(context, use_topology=self.use_topology)

def draw_menu(self, context):
    self.layout.operator(MYSTERYEM_shape_key_mirror_additive.bl_idname, icon='ARROW_LEFTRIGHT').use_topology = False
    self.layout.operator(MYSTERYEM_shape_key_mirror_additive.bl_idname, text="Mirror shape key (Additive) (Topology)").use_topology = True

def register():
    bpy.utils.register_class(MYSTERYEM_shape_key_mirror_additive)
    bpy.types.MESH_MT_shape_key_context_menu.append(draw_menu)

def unregister():
    bpy.types.MESH_MT_shape_key_context_menu.remove(draw_menu)
    bpy.utils.unregister_class(MYSTERYEM_shape_key_mirror_additive)

# Test from text editor
if __name__ == "__main__":
    register()
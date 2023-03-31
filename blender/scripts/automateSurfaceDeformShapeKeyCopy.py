bl_info = {
    "name": "Transfer Shape Keys (Surface Deform)",
    "description": "Transfer shape key movement by automating a surface deform modifier",
    "author": "Mysteryem",
    "version": (1, 0, 2),
    "blender": (3, 0, 0),
    "location": "View3D > Object > Link/Transfer Data",
    "tracker_url": "https://github.com/Mysteryem/Miscellaneous/issues",
    "category": "Mesh",
}

"""
Automates adding a Surface Transform modifier and applying it as a shape key for the effect of every shape key of the target mesh
"""

import bpy
import numpy as np

class MYSTERYEM_transfer_shape_key_movement(bpy.types.Operator):
    """Transfer Shape Key movement from Selected to Active using a Surface Deform modifier"""
    bl_idname = "mysteryem.copy_shape_key_movement"
    bl_label = "Transfer Shape Keys (Surface Deform)"
    bl_options = {"REGISTER", "UNDO"}
    
    # Properties for the Surface Deform modifier.
    falloff: bpy.props.FloatProperty(name="Falloff",
                                     description="Controls how much nearby polygons influence deformation",
                                     default=4.0)
    strength: bpy.props.FloatProperty(name="Strength",
                                      description="Strength of modifier deformations",
                                      default=1.0)
    
    vertex_group: bpy.props.StringProperty(name="Vertex Group", description="Vertex group name for selecting/weighting the affected areas", default="")
    invert_vertex_group: bpy.props.BoolProperty(name="Invert Vertex Group", description="Invert vertex group influence", default=False)
    use_sparse_bind: bpy.props.BoolProperty(name="Sparse Bind", description="Only record binding data for vertices matching the vertex group", default=False)
        
    @classmethod
    def poll(cls, context):
        if context.mode != 'OBJECT':
            cls.poll_message_set("Must be in Object mode")
            return False
        transfer_to = context.object
        if not transfer_to:
            cls.poll_message_set("No active Object to transfer to")
            return False
        if transfer_to.type != 'MESH':
            cls.poll_message_set("Active Object must be a Mesh")
            return False
        if transfer_to.data.users > 1:
            cls.poll_message_set("Active Object must not have multi-user data")
            return False
        if len(context.selected_objects) != 2 or transfer_to not in context.selected_objects:
            cls.poll_message_set("The active Object and only one other Object to transfer from must be selected")
            return False
        transfer_from = next(o for o in context.selected_objects if o != transfer_to)
        if transfer_from.type != 'MESH' or not transfer_from.data.shape_keys or len(transfer_from.data.shape_keys.key_blocks) < 2:
            cls.poll_message_set("The Object to transfer from must be a Mesh with Shape Keys")
            return False
        return True
    
    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.label(text="Surface Deform Modifier settings")
        layout.prop(self, "falloff")
        layout.prop(self, "strength")
        layout.prop_search(self, "vertex_group", context.object, "vertex_groups")
        layout.prop(self, "invert_vertex_group")
        layout.prop(self, "use_sparse_bind")
    
    def execute(self, context):
        transfer_to = context.object
        transfer_from = next(o for o in context.selected_objects if o != transfer_to)
        
        key_blocks = transfer_from.data.shape_keys.key_blocks
        
        for shape in key_blocks[1:]:
            if not shape.slider_min <= 0 < shape.slider_max or not shape.slider_min < 1 <= shape.slider_max:
                self.report({"ERROR"}, "All shape keys must be possible to set to 0 and 1")
                return {'CANCELLED'}
        
        surface_deform_mod = transfer_to.modifiers.new("transfer_shapes", 'SURFACE_DEFORM')
        
        # To restore once done
        old_shape_values = []
        
        try:
            surface_deform_mod.target = transfer_from
            surface_deform_mod.falloff = self.falloff
            surface_deform_mod.strength = self.strength
            surface_deform_mod.vertex_group = self.vertex_group
            surface_deform_mod.invert_vertex_group = self.invert_vertex_group
            surface_deform_mod.use_sparse_bind = self.use_sparse_bind
            # Move modifier to top
            bpy.ops.object.modifier_move_to_index(modifier=surface_deform_mod.name, index=0)
            # Bind to whatever the current shape of the target is
            bpy.ops.object.surfacedeform_bind(modifier=surface_deform_mod.name)
                    
            transfer_to_basis = False
            for shape in key_blocks[1:]:
                value = shape.value
                old_shape_values.append(value)
                if value != 0:
                    # transfer_to must not have more than a basis shape key
                    transfer_to_basis = True
                shape.value = 0

            if transfer_to_basis:
                to_shape_keys = transfer_to.data.shape_keys
                if to_shape_keys and len(to_shape_keys.key_blocks) > 1:
                    self.report({"ERROR"}, "Either all shape keys to transfer must have their values set to zero or the mesh to transfer"
                                           " to must not have shape keys")
                    return {'CANCELLED'}
            
                bpy.ops.object.modifier_apply_as_shapekey(keep_modifier=True, modifier=surface_deform_mod.name)
                to_shape_keys = transfer_to.data.shape_keys
                # Remove automatically created or pre-existing 'Basis'
                transfer_to.shape_key_remove(to_shape_keys.reference_key)

                # !!!Blender doesn't automatically update mesh vertices to match basis shape key, we have to do it ourselves!
                if bpy.app.version >= (3, 5):
                    verts = transfer_to.data.attributes["position"].data
                    verts_attribute = "vector"
                else:
                    verts = transfer_to.data.vertices
                    verts_attribute = "co"
                vcos = np.empty(len(transfer_to.data.vertices) * 3, dtype=np.single)
                to_shape_keys.reference_key.data.foreach_get("co", vcos)
                verts.foreach_set(verts_attribute, vcos)
                
                transfer_to.data.update()

                # New basis will be our added shape key, re-name it to the same as the 'Basis' of `transfer_from`
                to_shape_keys.reference_key.name = key_blocks[0].name
            
            for shape in key_blocks[1:]:
                shape.value = 1
                bpy.ops.object.modifier_apply_as_shapekey(keep_modifier=True, modifier=surface_deform_mod.name)
                transfer_to.data.shape_keys.key_blocks[-1].name = shape.name
                shape.value = 0
        finally:
            # Now tidy up
            for shape, old_value in zip(key_blocks[1:], old_shape_values):
                shape.value = old_value
            
            transfer_to.modifiers.remove(surface_deform_mod)
        
        return {'FINISHED'}

def draw_menu(self, context):
    layout = self.layout
    layout.separator()
    layout.operator(MYSTERYEM_transfer_shape_key_movement.bl_idname)
            
def register(test=False):
    bpy.utils.register_class(MYSTERYEM_transfer_shape_key_movement)
    if not test:
        bpy.types.VIEW3D_MT_make_links.append(draw_menu)

def unregister():
    bpy.utils.unregister_class(MYSTERYEM_transfer_shape_key_movement)
    bpy.types.VIEW3D_MT_make_links.remove(draw_menu)

if __name__ == "__main__":
    register(test=True)

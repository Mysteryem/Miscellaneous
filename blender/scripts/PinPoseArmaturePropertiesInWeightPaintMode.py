bl_info = {
    "name": "Pin Pose Armature Properties In Weight Paint Mode",
    "author": "Mysteryem",
    "version": (1, 0, 0),
    "blender": (2, 93, 7),  # Older versions have not been tested
    "location": "Properties Editor > Object Properties or Object Data Properties",
    "tracker_url": "https://github.com/Mysteryem/Miscellaneous/issues",
    "category": "Interface",
}

"""
When in Weight Paint mode with a pose_object (armature), adds a button at the top of the Object Data Properties tab of the Properties
 editor that pins the pose object.
The main purpose of this is to let the user toggle Pose/Rest position and Armature Layer Visibility while remaining in Weight Paint Mode.
I initially thought about simply duplicating the various armature-specific panels used in the Properties editor, modifying them to
 use the current pose_object instead of active object, but that wouldn't include any panels added by addons.
"""

import bpy


# We're creating duplicate panels, but with each one parented to a different panel
# We can use a class as a mixin that our actual Panel classes will extend
class DATA_PT_mysteryem_pin_armature_mixin:
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'data'
    bl_label = ""
    bl_options = {'HIDE_HEADER'}
    
    @classmethod
    def poll(cls, context):
        # context must have a pose_object
        # current mode must be Weight Paint
        # pose_object must be an Armature
        return context.pose_object and context.mode == 'PAINT_WEIGHT' and context.pose_object.type == 'ARMATURE'
    
    def draw(self, context):
        layout = self.layout
        
        already_pinned = context.space_data.pin_id == context.pose_object
        
        icon = 'PINNED' if already_pinned else 'UNPINNED'
        text = "Unpin Armature" if already_pinned else "Pin Armature"
        
        col = layout.column()
        col.operator(MYSTERYEM_pin_armature_to_properties.bl_idname, text=text, icon=icon)

# By parenting to the top panel, we can guarantee the position of the panels
# The downside is that if an object data other than a mesh or armature is pinned, the button won't be visible,
# but the user can simply click on the Toggle Pin ID button that is part of Blender's default UI to unpin.
class DATA_PT_mysteryem_pin_armature_mesh(DATA_PT_mysteryem_pin_armature_mixin, bpy.types.Panel):
    bl_parent_id = 'DATA_PT_context_mesh'

class DATA_PT_mysteryem_pin_armature_armature(DATA_PT_mysteryem_pin_armature_mixin, bpy.types.Panel):
    bl_parent_id = 'DATA_PT_context_arm'
    
class DATA_PT_mysteryem_pin_armature_object(DATA_PT_mysteryem_pin_armature_mixin, bpy.types.Panel):
    bl_parent_id = 'OBJECT_PT_context_object'
    

class MYSTERYEM_pin_armature_to_properties(bpy.types.Operator):
    """Toggle armature pin"""
    bl_idname = 'mysteryem.properties_toggle_armature_pin'
    bl_options = {'INTERNAL'}
    bl_label = "Pin Armature"
    
    @classmethod
    def poll(cls, context):
        space_data = context.space_data
        return context.pose_object and space_data.type == 'PROPERTIES' and (space_data.context == 'DATA' or space_data.context == 'OBJECT')
    
    def execute(self, context):
        space_data = context.space_data
        pin_id = space_data.pin_id
        # Never None
        pose_object = context.pose_object
        if pin_id:
            if pin_id == pose_object or pin_id == pose_object.data:
                space_data.pin_id = None
                space_data.use_pin_id = False
            elif isinstance(pin_id, bpy.types.Object):
                space_data.pin_id = pose_object
                space_data.use_pin_id = True
            else:
                # If the current pin is set to Object data, Blender won't let you set it directly to Object
                space_data.pin_id = None
                space_data.pin_id = pose_object
                space_data.use_pin_id = True
        else:
            space_data.pin_id = pose_object
            space_data.use_pin_id = True
        return {'FINISHED'}     

def register():
    bpy.utils.register_class(MYSTERYEM_pin_armature_to_properties)
    bpy.utils.register_class(DATA_PT_mysteryem_pin_armature_mesh)
    bpy.utils.register_class(DATA_PT_mysteryem_pin_armature_armature)
    bpy.utils.register_class(DATA_PT_mysteryem_pin_armature_object)


def unregister():
    bpy.utils.unregister_class(DATA_PT_mysteryem_pin_armature_object)
    bpy.utils.unregister_class(DATA_PT_mysteryem_pin_armature_armature)
    bpy.utils.unregister_class(DATA_PT_mysteryem_pin_armature_mesh)
    bpy.utils.unregister_class(MYSTERYEM_pin_armature_to_properties)

# Test from the text editor without adding to the menu each time
if __name__ == '__main__':
    register()
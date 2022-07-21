# Operator to select sibling bone of active bone with similar behaviour to bpy.ops.armature/pose.select_hierarchy
#
# I personally add key-bindings for mysteryem.armature_select_cycle_hierarchy to 3D View -> Armature -> Armature (Global) and 3D View -> Pose -> Pose (Global)
# with Direction: Forwards bound to '=' and Direction: Backwards bound to '-' with holding down Shift enabling Extend.
bl_info = {
    "name": "Bone Cycle Hierarchy",
    "blender": (2, 93, 7),
    "category": "Rigging",
}

import bpy

from itertools import chain

# TODO: Implement cycling cousin/etc. bones instead of only direct siblings:
#       Maybe loop through parents until a parent with more than one child is found, cycle to its next child, then loop through children the same number of times
#       parents were looped through, but only if each bone has only one child. The idea is that given multiple chains of bones from the same source, the next
#       chain over can be cycled to
class MYSTERYEM_bone_cycle_hierarchy(bpy.types.Operator):
    """Cycle hierarchy selection"""
    
    bl_idname = "mysteryem.armature_select_cycle_hierarchy"
    bl_label = "Cycle hierarchy selection"
    bl_options = {'REGISTER', 'UNDO'}
    direction: bpy.props.EnumProperty(items=[('FORWARDS', "Forwards", "Cycle Forwards"), ('BACKWARDS', "Backwards", "Cycle Backwards")], name="Direction", default='FORWARDS')
    # When True, deselect the old active bone, mirroring the behaviour of bpy.ops.armature/pose.select_hierarchy
    extend: bpy.props.BoolProperty(name="Extend", default=False, description="Extend the selection")
    # Default ordering uses the order that Blender returns bones in
    order: bpy.props.EnumProperty(items=[('DEFAULT', "Default", "Default Ordering"), ('ALPHABETICAL', "Alphabetical", "Alphabetical Ordering")], name="Order", default='DEFAULT')
    
    @classmethod
    def poll(cls, context):
        return ((context.mode == 'EDIT_ARMATURE' and context.active_bone and context.active_bone.parent)
                or (context.mode == 'POSE' and context.active_pose_bone and context.active_pose_bone.parent))
    
    @staticmethod
    def set_active_edit_bone(edit_bone):
        edit_bone.id_data.edit_bones.active = edit_bone
    
    @staticmethod
    def set_active_bone(bone):
        bone.id_data.bones.active = bone
    
    def execute(self, context):
        if context.mode == 'EDIT_ARMATURE':
            active_bone = context.active_bone
            parent = active_bone.parent
            # .children is a list
            siblings = parent.children
            
            set_active = MYSTERYEM_bone_cycle_hierarchy.set_active_edit_bone
        else:
            active_bone = context.active_pose_bone.bone
            parent = active_bone.parent
            # .children is a bpy_prop_collection
            siblings = list(parent.children)
            
            set_active = MYSTERYEM_bone_cycle_hierarchy.set_active_bone
        
        reverse_order = self.direction == 'BACKWARDS'
        
        if self.order == 'ALPHABETICAL':
            siblings = sorted(siblings, key=lambda b: b.name, reverse=reverse_order)
        elif reverse_order:
            siblings.reverse()
        
        active_index = siblings.index(active_bone)
        # All siblings, in order from active_bone, excluding active_bone
        siblings_chain = chain(siblings[active_index+1:], siblings[:active_index])
        # select_hierarchy won't select bones if the child/parent is hidden or is 'selection hidden'
        # mimic the same behaviour, skipping over any bones that are hidden or 'selection hidden'
        siblings_chain = (b for b in siblings_chain if not b.hide and not b.hide_select)
        
        next_bone = next(siblings_chain, None)
        if next_bone:
            if not self.extend:
                active_bone.select = False
                active_bone.select_head = False
                active_bone.select_tail = False
            next_bone.select = True
            next_bone.select_head = True
            next_bone.select_tail = True
            
            set_active(next_bone)
            
            return {'FINISHED'}
        else:
            return {'CANCELLED'}

class MYSTERYEM_VIEW3D_MT_select_armature_cycle(bpy.types.Menu):
    bl_label = "Cycle Sibling"

    def draw(self, _context):
        layout = self.layout

        props = layout.operator("mysteryem.armature_select_cycle_hierarchy", text="Forwards")
        props.extend = False
        props.direction = 'FORWARDS'

        props = layout.operator("mysteryem.armature_select_cycle_hierarchy", text="Backwards")
        props.extend = False
        props.direction = 'BACKWARDS'

        layout.separator()

        props = layout.operator("mysteryem.armature_select_cycle_hierarchy", text="Extend Forwards")
        props.extend = True
        props.direction = 'FORWARDS'

        props = layout.operator("mysteryem.armature_select_cycle_hierarchy", text="Extend Backwards")
        props.extend = True
        props.direction = 'BACKWARDS'

def draw_menu(self, context):
    self.layout.separator()
    self.layout.menu('MYSTERYEM_VIEW3D_MT_select_armature_cycle')

def register(test=False):
    # VIEW3D_MT_select_edit_armature is the Armature Edit mode Select menu
    # VIEW3D_MT_select_pose_more_less is the Armature Pose mode Select menu's Select More/Less menu
    bpy.utils.register_class(MYSTERYEM_bone_cycle_hierarchy)
    bpy.utils.register_class(MYSTERYEM_VIEW3D_MT_select_armature_cycle)
    if not test:
        bpy.types.VIEW3D_MT_select_edit_armature.append(draw_menu)
        bpy.types.VIEW3D_MT_select_pose_more_less.append(draw_menu)

def unregister(test=False):
    if not test:
        bpy.types.VIEW3D_MT_select_pose_more_less.remove(draw_menu)
        bpy.types.VIEW3D_MT_select_edit_armature.remove(draw_menu)
    bpy.utils.unregister_class(MYSTERYEM_VIEW3D_MT_select_armature_cycle)
    bpy.utils.unregister_class(MYSTERYEM_bone_cycle_hierarchy)

if __name__ == '__main__':
    register(test=True)

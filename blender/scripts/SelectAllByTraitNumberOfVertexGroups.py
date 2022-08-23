bl_info = {
    "name": "Select All By Trait: Number Of Vertex Groups",
    "author": "Mysteryem",
    "version": (1, 0, 1),
    "blender": (2, 93, 7),  # Older versions have not been tested
    "location": "Select > Select All By Trait > Number of Vertex Groups",
    "tracker_url": "https://github.com/Mysteryem/Miscellaneous/issues",
    "category": "Mesh",
}

"""
Addon intended to assist with limiting the number of vertex groups to 4 for Unity/VRChat usage by
enabling the user to select all vertices that might be affected by bpy.ops.object.vertex_group_limit_total.

One of Unity's Quality Settings limits the number of bones per vertex that are taken into account during skinning.
For VRChat, this limit is 4.

Additionally, Unity's default Model Import Settings only import up to 4 skin weights per vertex.

When there are more than the maximum number of skin weights, the lowest weighted bones are discarded.
"""

import bpy
import bmesh

# type constants
_not_equal_id = 'NOT_EQUAL'
_greater_than_id = 'GREATER_THAN'
_equal_to_id = 'EQUAL_TO'
_less_than_id = 'LESS_THAN'
# group subset constants
_subset_all = 'ALL'
_subset_deform = 'BONE_DEFORM'
_subset_other = 'OTHER_DEFORM'


def get_deform_indices(obj):
    vg_names_to_indices = {vg.name: i for i, vg in enumerate(obj.vertex_groups)}
    valid_mod_bones_gen = (mod.object.pose.bones for mod in obj.modifiers if mod.type == 'ARMATURE' and mod.object and mod.show_viewport)
    all_bones_gen = (pose_bone.bone for pose_bones in valid_mod_bones_gen for pose_bone in pose_bones)
    deform_bones_only = filter(lambda bone: bone.use_deform and bone.name in vg_names_to_indices, all_bones_gen)
    deform_indices = {vg_names_to_indices[bone.name] for bone in deform_bones_only}
    return deform_indices


# pre-3.0 support
class OperatorMixin:
    # poll_message_set was added in 3.0
    if not hasattr(bpy.types.Operator, 'poll_message_set'):
        @classmethod
        def poll_message_set(cls, message, *args):
            pass


class MYSTERYEM_select_all_my_trait_number_vertex_groups(OperatorMixin, bpy.types.Operator):
    """Select vertices by the number of vertex groups"""
    bl_idname = 'mysteryem.mesh_select_by_number_vertex_groups'
    bl_label = "Number of Vertex Groups"
    bl_options = {'REGISTER', 'UNDO'}
    
    number: bpy.props.IntProperty(
        name="Number of Groups",
        min=0,
        default=4,  # Default intended for VRChat usage where there is a max of 4 deform groups per vertex
        description="Number of Vertex Groups",
    )
    
    type: bpy.props.EnumProperty(
        name="Type",
        items=(
            (_not_equal_id, "Not Equal To", ""),
            (_greater_than_id, "Greater Than", ""),
            (_equal_to_id, "Equal To", ""),
            (_less_than_id, "Less Than", ""),
        ),
        default=_greater_than_id,  # Default intended for VRChat usage where there is a max of 4 deform groups per vertex
        description="Type of comparison to make",
    )
    
    subset: bpy.props.EnumProperty(
        name="Subset",
        items=(
            (_subset_all, "All Groups", "All Vertex Groups"),
            (_subset_deform, "Deform Pose Bones", "All Vertex Groups assigned to Deform Pose Bones"),
            (_subset_other, "Other", "All Vertex Groups not assigned to Deform Pose Bones"),
        ),
        default=_subset_deform,  # Default intended for VRChat usage where there is a max of 4 deform groups per vertex
        description="Define which subset of groups shall be used",
    )
    
    ignore_zero: bpy.props.BoolProperty(
        default=True,  # Default intended for VRChat usage where there is a max of 4 deform groups per vertex
        name="Ignore zero weight groups",
        description="Don't count a vertex group the vertex is in if its weight in that vertex group is zero",
    )
    
    extend: bpy.props.BoolProperty(
        name="Extend",
        description="Extend the selection",
    )
    
    @classmethod
    def poll(cls, context):
        # Using objects_in_mode_unique_data to support multi-object editing
        objects = context.objects_in_mode_unique_data
        if context.mode == 'EDIT_MESH' and objects:
            if context.tool_settings.mesh_select_mode[0]:
                if any(obj.vertex_groups for obj in objects):
                    # At least one object needs to have vertex groups
                    return True
                else:
                    cls.poll_message_set("No weights/vertex groups on " + ("objects" if len(objects) > 1 else "object"))
            else:
                cls.poll_message_set("Must be in vertex selection mode")
        else:
            cls.poll_message_set("Must be in mesh edit mode")
        return False
    
    def execute(self, context):
        number = self.number
        extend = self.extend
        type = self.type
        ignore_zero = self.ignore_zero
        subset = self.subset
        
        for obj in context.objects_in_mode_unique_data:
            # Skip objects without vertex groups, mirroring the behaviour of bpy.ops.mesh.select_ungrouped
            if obj.vertex_groups:
                me = obj.data
                bm = bmesh.from_edit_mesh(me)
                
                if extend and me.total_vert_sel == len(bm.verts):
                    # With extend enabled, if all the vertices are already selected, there's nothing to do
                    # Note that we do need to get the bmesh, because the number of vertices could have changed
                    # while in edit mode meaning len(me.vertices) is inaccurate.
                    #
                    # obj.update_from_editmode() might make len(me.vertices) accurate, but as we're likely to
                    # be getting the bmesh edit mesh anyway, it would be wasteful to usually do both
                    continue
                
                subset_indices = None
                if subset == _subset_deform:
                    subset_indices = get_deform_indices(obj)
                elif subset == _subset_other:
                    subset_indices = {i for i in range(len(obj.vertex_groups))} - get_deform_indices(obj)
            
                deform_layer = bm.verts.layers.deform.active
                if deform_layer and (subset_indices is None or subset_indices):
                    if extend:
                        # When extending the selection, we can skip vertices that are already selected
                        bmverts = (bv for bv in bm.verts if not bv.select)
                    else:
                        bmverts = bm.verts
                        
                    for bmvert in bmverts:
                        # Hidden vertices can be skipped
                        if not bmvert.hide:
                            # The code within this loop is as optimised as I could make it
                            bmdeformvert = bmvert[deform_layer]
                            if subset_indices is None:
                                # We want to count all vertex groups
                                if ignore_zero:
                                    group_count = 0
                                    for weight in bmdeformvert.values():
                                        # True for any non-zero
                                        if weight:
                                            group_count += 1
                                else:
                                    group_count = len(bmdeformvert)
                            else:
                                # We only want to count a subset of the vertex groups
                                if ignore_zero:
                                    group_count = 0
                                    for group_idx, weight in bmdeformvert.items():
                                        # Checking weight first because generally most groups on a vertex will be deform groups if
                                        # there are any deform groups and because there aren't many uses for the non-deform subset.
                                        #
                                        # Additionally, applying a data transfer modifier, of vertex groups from one mesh to another,
                                        # will add every group to every vertex, resulting in many groups on every vertex with a
                                        # weight of zero
                                        if weight and group_idx in subset_indices:
                                            group_count += 1
                                else:
                                    # Looping like when ignore_zero is True, but without the weight check and iterating
                                    # deform_vert.values() seems to be the same speed as this one-liner
                                    group_count = len(subset_indices.intersection(bmdeformvert.keys()))

                            # From my testing, an if-else chain with 4 conditional checks is roughly the same performance on average
                            # as pre-defining a function based on the type. This chain only has 3 conditional checks, so is on
                            # average faster to leave as an if-else chain.
                            #
                            # match statement might be faster, but it requires Python 3.10+
                            #
                            # Using .select rather than .select_set(select) shouldn't have different behaviour because .select_set
                            # only flushes down (Faces -> Edges -> Vertices) and we're changing the selection of vertices
                            if type == _greater_than_id:
                                bmvert.select = group_count > number
                            elif type == _not_equal_id:
                                bmvert.select = group_count != number
                            elif type == _equal_to_id:
                                bmvert.select = group_count == number
                            else:  # elif type == _less_than_id
                                bmvert.select = group_count < number
                else:
                    # deform_layer may not exist if vertex groups have only just been added and are empty
                    # or, alternatively, if subset_indices is not None, but is empty, then 
                    group_count = 0
                    if type == _greater_than_id:
                        select = group_count > number
                    elif type == _not_equal_id:
                        select = group_count != number
                    elif type == _equal_to_id:
                        select = group_count == number
                    else:  # elif type == _less_than_id
                        select = group_count < number
                    # No need to do anything if extend is True, but we are deselecting
                    if extend and not select:
                        continue
                    
                    # I would have used the operator for selecting/deselecting all, but it ignores context overrides
                    # meaning there's no way to stop it from acting on all the meshes opened in multi-editing when we
                    # only want it to act on the current mesh being iterated
                    for bmvert in bm.verts:
                        bmvert.select = select

                # Update edge/face selection according to current selection mode
                bm.select_flush_mode()
                # Update the edit_mesh for the selection changes
                bmesh.update_edit_mesh(me, loop_triangles=False, destructive=False)
        return {'FINISHED'}

def draw_menu(self, context):
    layout = self.layout
    layout.separator()
    layout.operator(MYSTERYEM_select_all_my_trait_number_vertex_groups.bl_idname)

def register(add_to_menu=True):
    bpy.utils.register_class(MYSTERYEM_select_all_my_trait_number_vertex_groups)
    if add_to_menu:
        bpy.types.VIEW3D_MT_edit_mesh_select_by_trait.append(draw_menu)

def unregister():
    bpy.types.VIEW3D_MT_edit_mesh_select_by_trait.remove(draw_menu)
    bpy.utils.unregister_class(MYSTERYEM_select_all_my_trait_number_vertex_groups)

if __name__ == '__main__':
    register(add_to_menu=False)

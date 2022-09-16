bl_info = {
    "name": "Extra mesh shape key operations",
    "author": "Mysteryem",
    "version": (1, 0, 0),
    "blender": (2, 93, 7),  # Older versions have not been tested
    "location": "Editmode > Vertex",
    "tracker_url": "https://github.com/Mysteryem/Miscellaneous/issues",
    "category": "Mesh",
}

"""Extra shape key operations
Clear Pending Shape Changes
    Clear pending changes of selected vertices made to the active shape key
    This can be finicky as undoing and other operations can cause pending shape changes to be saved

Transfer Pending Shape Changes
    Transfer pending changes of selected vertices made to the active shape key, to a different shape key
    Intended for when you have just made some changes, but had the wrong shape key active
    This can be finicky as undoing and other operations can cause pending shape changes to be saved

Average Shape Key Movement
    Average the shape key movement of the selected vertices

Blend from Shape (Active Vertex)
    Blend from Shape, but applying the movement of the active vertex to the selected vertices

"""

import bpy
import bmesh
from typing import Generator
from bpy.types import Operator, Mesh, Object, Context, PropertyGroup
from bpy.props import FloatProperty, BoolProperty, StringProperty, CollectionProperty, EnumProperty
from bmesh.types import BMVert
from mathutils import Vector


class OperatorBase(Operator):
    # Pre-3.0 support because poll_message_set was added in 3.0
    if not hasattr(Operator, 'poll_message_set'):
        @classmethod
        def poll_message_set(cls, message, *args):
            pass

    @classmethod
    def poll_fail(cls, message, *args):
        cls.poll_message_set(message, *args)
        return False

    @classmethod
    def poll_mode(cls, context: Context) -> bool:
        if context.mode != 'EDIT_MESH':
            return cls.poll_fail("Must be in edit mode")
        return True


class ClearPendingChanges(OperatorBase):
    """Clear pending changes to all selected vertices.
Normals may look incorrect, but it is a purely visual bug.
Note that many actions will save all pending changes, such as undoing"""
    bl_idname = "mesh.mysteryem_clear_pending_shape_key_changes"
    bl_label = "Clear Pending Shape Changes"
    # No 'REGISTER' because operator redo (where you can adjust the mix property) does not work due to the shape key
    # getting updated when performing an undo
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        if not cls.poll_mode(context):
            return False
        # This trick only works with shape keys
        # Check that all meshes in edit mode meet this condition
        if not all(obj.data.shape_keys for obj in context.objects_in_mode_unique_data):
            return cls.poll_fail("All meshes in edit mode must have shape keys")
        return True

    def execute(self, context: Context) -> set[str]:
        objects: list[Object] = context.objects_in_mode_unique_data
        meshes_to_update = []
        for obj in objects:
            me: Mesh = obj.data
            if me.total_vert_sel == 0:
                continue

            meshes_to_update.append(me)
            bm = bmesh.from_edit_mesh(me)
            active_shape_layer = bm.verts.layers.shape[obj.active_shape_key_index]
            bmverts = (bv for bv in bm.verts if bv.select and not bv.hide)

            bv: BMVert
            for bv in bmverts:
                bv.co = bv[active_shape_layer]

            bmesh.update_edit_mesh(me, loop_triangles=False, destructive=False)

        return {'FINISHED'}


class TransferPendingChanges(OperatorBase):
    """Transfer pending changes of selected vertices of the active shape key to another shape key
Note:
 Normals visual bug
 Does not update shape keys relative to the key transferred to
 Many actions save all pending changes, such as undoing"""
    bl_idname = "mesh.mysteryem_transfer_pending_shape_key_changes"
    bl_label = "Transfer Pending Shape Changes"
    # No 'REGISTER' because operator redo (where you can adjust the mix property) does not work due to the shape key
    # getting updated when performing an undo
    bl_options = {'UNDO'}

    mode: EnumProperty(
        name="Mode",
        items=(
            ('ADD', "Add", "Add to the existing shape key vertex positions"),
            ('REPLACE', "Replace", "Replace all existing shape key vertex positions"),
            ('REPLACE_CHANGED', "Replace Changed", "Replace the existing shape key vertex positions, but only where"
                                                   " there were pending changes"),
        ),
        description="How the pending changes should be transferred",
    )

    # Ensure that shape_key_name is always set to a shape key that exists, this prevents clearing the shape key via the
    # UI (which would normally set it to '')
    def shape_key_name_ensure_exists(self, context):
        obj = context.object
        if obj:
            me = obj.data
            if isinstance(me, Mesh):
                shape_keys = me.shape_keys
                if shape_keys:
                    key_blocks = shape_keys.key_blocks
                    if self.shape_key_name not in key_blocks:
                        active_shape_name = obj.active_shape_key.name
                        for key_block in key_blocks:
                            key_block_name = key_block.name
                            if key_block_name != active_shape_name:
                                # Note that setting shape_key_name here causes recursion
                                self.shape_key_name = key_block_name
                                break

    shape_key_name: StringProperty(
        name="Transfer to",
        description="Name of the shape key to transfer to",
        options={'SKIP_SAVE'},
        default='',
        update=shape_key_name_ensure_exists,
    )

    other_shape_key_names: CollectionProperty(
        type=PropertyGroup,
        description="Internal property for gathering available shape key names",
        options={'HIDDEN'},
    )

    swap_after_execute: BoolProperty(
        name="Swap to shape key",
        description="Set the shape key transferred to as the active shape key after transferring",
        default=True,
    )

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.prop_search(self, 'shape_key_name', self, 'other_shape_key_names', icon='SHAPEKEY_DATA')
        col.prop(self, 'mode')
        col.prop(self, 'swap_after_execute', text=f"Set {self.shape_key_name} as active")

    @classmethod
    def poll(cls, context: Context) -> bool:
        if not cls.poll_mode(context):
            return False
        # This trick only works with shape keys, additionally, there must be at least 2 so that there is a shape to
        # transfer to. Technically, a new shape key can be created while in edit mode using bmesh, but the UI doesn't
        # immediately update to show the new shape key and there may be other reasons that Blender doesn't normally
        # allow creating new shape keys while in edit mode.
        obj = context.object
        shape_keys = obj.data.shape_keys
        if not shape_keys or len(shape_keys.key_blocks) < 2:
            return cls.poll_fail("Active mesh must have at least two shape keys")
        return True

    def execute(self, context) -> set[str]:
        obj = context.object
        me = obj.data

        if self.shape_key_name not in me.shape_keys.key_blocks:
            # This shouldn't happen through normal execution that calls invoke
            self.report({'ERROR_INVALID_INPUT'}, f"Shape key '{self.shape_key_name}' not found")
            return {'FINISHED'}

        if self.shape_key_name == obj.active_shape_key.name:
            # This shouldn't happen through normal execution that calls invoke
            self.report({'ERROR_INVALID_INPUT'}, "The shape key to transfer to must not be the active shape key")
            return {'FINISHED'}

        if me.total_vert_sel == 0:
            return {'FINISHED'}

        bm = bmesh.from_edit_mesh(me)
        active_shape_layer = bm.verts.layers.shape[obj.active_shape_key_index]
        other_shape_layer = bm.verts.layers.shape[self.shape_key_name]
        bmverts = (bv for bv in bm.verts if bv.select and not bv.hide)

        bv: BMVert
        if self.mode == 'ADD':
            for bv in bmverts:
                pending_change = bv.co - bv[active_shape_layer]
                #
                if any(pending_change):
                    bv[other_shape_layer] += pending_change
                    bv.co = bv[active_shape_layer]
        elif self.mode == 'REPLACE':
            for bv in bmverts:
                bv[other_shape_layer] = bv.co
                bv.co = bv[active_shape_layer]
        elif self.mode == 'REPLACE_CHANGED':
            for bv in bmverts:
                pre_change_active_co = bv[active_shape_layer]
                if bv.co != pre_change_active_co:
                    bv[other_shape_layer] = bv.co
                    bv.co = pre_change_active_co
        else:
            self.report({'ERROR'}, f"Unexpected mode '{self.mode}'")
            return {'FINISHED'}

        if self.swap_after_execute:
            # Don't need to update the edit mesh if we change the active shape key, since it will refresh the 3D view
            # when it loads the other shape key
            obj.active_shape_key_index = me.shape_keys.key_blocks.find(self.shape_key_name)
        else:
            # Update the 3D view to show the changes
            bmesh.update_edit_mesh(me, loop_triangles=False, destructive=False)

        return {'FINISHED'}

    def invoke(self, context: Context, event) -> set[str]:
        self.other_shape_key_names.clear()
        obj: Object = context.object
        active_name = obj.active_shape_key.name
        # Set up the collection property to contain the names of all shape keys that aren't the active shape key
        for shape_key in context.object.data.shape_keys.key_blocks:
            key_name = shape_key.name
            if key_name != active_name:
                new_element = self.other_shape_key_names.add()
                new_element.name = key_name
        # Set the default shape key name to the first shape key found
        self.shape_key_name = self.other_shape_key_names[0].name
        # Draw the UI to let the user pick which shape key and to change the add/replace mode
        wm = context.window_manager
        return wm.invoke_props_dialog(self)


class AverageShapeKeyMovement(OperatorBase):
    """Average the shape key movement of the selected vertices.
If a mesh has no shape keys, its active shape key is the reference key or its active shape key is relative to
itself, it will be skipped"""
    bl_idname = "mesh.mysteryem_average_shape_key_movement"
    bl_label = "Average Shape Key Movement"
    bl_options = {'REGISTER', 'UNDO'}

    mix: FloatProperty(
        name="Mix",
        description="Mix between fully averaging (1.0) and no changes (0.0).",
        default=1.0,
        soft_min=-2.0,
        soft_max=2.0,
    )

    @staticmethod
    def object_has_relative_shape_keys_and_active_shape_is_not_basis_like(mesh_obj: Object):
        me: Mesh = mesh_obj.data
        shape_keys = me.shape_keys
        active_shape = mesh_obj.active_shape_key
        return (
                active_shape  # Also indicates that shape_keys is not None
                and shape_keys.use_relative  # Only supporting relative shape keys for now
                and active_shape.relative_key != active_shape  # Relative to itself results in no movement
                and active_shape != shape_keys.reference_key  # Reference key is always considered relative to itself
        )

    @classmethod
    def poll(cls, context: Context) -> bool:
        if cls.poll_mode(context):
            if any(map(
                    AverageShapeKeyMovement.object_has_relative_shape_keys_and_active_shape_is_not_basis_like,
                    context.objects_in_mode_unique_data
            )):
                return True
            else:
                return cls.poll_fail("At least one mesh must have an active relative shape key that isn't the reference"
                                     " key and isn't relative to itself")
        return False

    def execute(self, context: Context) -> set[str]:
        mix = self.mix
        if mix == 0.0:
            return {'FINISHED'}

        objects: list[Object] = context.objects_in_mode_unique_data

        all_selected_bmverts: list[tuple[BMVert, Vector, Vector]] = []
        sum_movement = Vector()
        meshes_to_update = []
        for obj in objects:
            active_shape = obj.active_shape_key
            if not active_shape or active_shape.relative_key == active_shape:
                continue

            me: Mesh = obj.data
            if not me.shape_keys.use_relative or me.shape_keys.reference_key == active_shape:
                continue

            if me.total_vert_sel == 0:
                continue

            bm = bmesh.from_edit_mesh(me)
            relative_shape_layer = bm.verts.layers.shape[active_shape.relative_key.name]
            bmverts = (bv for bv in bm.verts if bv.select and not bv.hide)
            bv: BMVert
            for bv in bmverts:
                relative_co = bv[relative_shape_layer]
                movement = bv.co - relative_co
                all_selected_bmverts.append((bv, relative_co, movement))
                sum_movement += movement
            meshes_to_update.append(me)

        if all_selected_bmverts:
            average_movement = sum_movement / len(all_selected_bmverts)
            if mix == 1.0:
                for bv, relative_co, _ in all_selected_bmverts:
                    bv.co = relative_co + average_movement
            else:
                for bv, relative_co, movement in all_selected_bmverts:
                    bv.co = relative_co + movement.lerp(average_movement, mix)

        for me in meshes_to_update:
            bmesh.update_edit_mesh(me, loop_triangles=False, destructive=False)

        return {'FINISHED'}


class ActiveVertexMovementToSelected(OperatorBase):
    """Blend the movement of the active vertex into selected vertices."""
    bl_idname = "mesh.mysteryem_active_vertex_movement_to_selected"
    bl_label = "Blend from Shape (Active Vertex)"
    bl_options = {'REGISTER', 'UNDO'}

    def shape_key_name_ensure_exists(self, context):
        obj = context.object
        if obj:
            me = obj.data
            if isinstance(me, Mesh):
                shape_keys = me.shape_keys
                if shape_keys:
                    key_blocks = shape_keys.key_blocks
                    if self.shape not in key_blocks:
                        # Note that setting shape_key_name here causes recursion
                        self.shape = obj.active_shape_key.name

    shape: StringProperty(
        name="Shape",
        description="Shape key to use for blending",
        update=shape_key_name_ensure_exists
    )

    mix: FloatProperty(
        name="Mix",
        description="Mix between fully blending (1.0) and no changes (0.0).",
        default=1.0,
        soft_min=-2.0,
        soft_max=2.0,
    )

    add: BoolProperty(
        name="Add",
        description="Add the movement of the active vertex to the other selected vertices.",
        default=True,
    )

    include_active_vertex: BoolProperty(
        name="Include active vertex",
        description="Blend the active vertex with itself (has no effect if Add is disabled)",
        default=True,
    )

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        col = layout.column()
        # For some reason, clearing the prop_search closes the Operator Redo popup...
        col.prop_search(self, 'shape', context.object.data.shape_keys, 'key_blocks')
        col.prop(self, 'mix')
        col.prop(self, 'add')
        if not self.add:
            col = layout.column()
            col.enabled = False
        col.prop(self, 'include_active_vertex')

    @classmethod
    def poll(cls, context: Context) -> bool:
        # Ideally we would also check if there is an active vertex, but there's no way of doing so other than getting
        # the bmesh of the current edit mesh which I'm not sure is good to do in a poll function
        if not cls.poll_mode(context):
            return False
        if not context.tool_settings.mesh_select_mode[0]:
            return cls.poll_fail("Vertex selection mode must be enabled")
        obj = context.object
        if not obj:
            # I don't think this is possible to happen
            return cls.poll_fail("Must have an object in edit mode")
        data: Mesh = obj.data
        shape_keys = data.shape_keys
        if not shape_keys:
            return cls.poll_fail("Active mesh must have shape keys")
        if not shape_keys.use_relative:
            return cls.poll_fail("Active mesh's shape keys must be relative")
        active_shape = obj.active_shape_key
        if active_shape.relative_key == active_shape:
            return cls.poll_fail("Active shape key must not be relative to itself")
        if active_shape == shape_keys.reference_key:
            return cls.poll_fail("Active shape key must not be the reference key")
        return True

    def execute(self, context: Context) -> set[str]:
        active_object: Object = context.object
        active_mesh: Mesh = active_object.data
        active_bm = bmesh.from_edit_mesh(active_mesh)
        active_vert = active_bm.select_history.active
        if not isinstance(active_vert, BMVert):
            # Even if we change the properties, nothing will happen if there's no active vertex
            return {'CANCELLED'}

        active_key_blocks = active_mesh.shape_keys.key_blocks

        if self.shape not in active_key_blocks:
            self.report({'ERROR_INVALID_INPUT'}, f"Shape key '{self.shape}' not found")
            return {'FINISHED'}

        shape_key = active_key_blocks[self.shape]
        relative_shape_key = shape_key.relative_key
        is_add = self.add

        if is_add and relative_shape_key == shape_key:
            # Nothing to do when they're the same key as there will be no movement
            return {'FINISHED'}

        shape_layers = active_bm.verts.layers.shape
        relative_shape_layer = shape_layers[relative_shape_key.name]
        if active_object.active_shape_key == shape_key:
            active_vert_movement = active_vert.co - active_vert[relative_shape_layer]
        else:
            shape_key_layer = shape_layers[shape_key.name]
            active_vert_movement = active_vert[shape_key_layer] - active_vert[relative_shape_layer]

        if not any(active_vert_movement) and is_add:
            # The movement of the active vertex is zero, adding it will do nothing
            return {'FINISHED'}

        mix = self.mix
        if mix == 0.0:
            return {'FINISHED'}
        add_movement = active_vert_movement * mix

        objects: list[Object] = context.objects_in_mode_unique_data

        for obj in objects:
            active_shape = obj.active_shape_key
            me: Mesh = obj.data
            shape_keys = me.shape_keys
            bm = bmesh.from_edit_mesh(me)
            bmverts = (bv for bv in bm.verts if bv.select and not bv.hide)
            bv: BMVert
            if is_add:
                if obj == active_object and not self.include_active_vertex:
                    # Need to skip the active vertex when adding since the operator blends into other selected vertices
                    for bv in bmverts:
                        if bv != active_vert:
                            bv.co += add_movement
                else:
                    for bv in bmverts:
                        bv.co += add_movement
            elif (
                    (not active_shape or not shape_keys)
                    or (shape_keys.use_relative and active_shape.relative_key == active_shape)
                    or active_shape == shape_keys.reference_key
            ):
                for bv in bmverts:
                    bv.co += add_movement
            else:
                if shape_keys.use_relative:
                    relative_shape_layer = bm.verts.layers.shape[active_shape.relative_key.name]
                else:
                    # Not sure if this is actually useful for non-relative shape keys
                    relative_shape_layer = bm.verts.layers.shape[obj.active_shape_key_index-1]

                for bv in bmverts:
                    bv.co = bv.co.lerp(bv[relative_shape_layer] + active_vert_movement, mix)
            bmesh.update_edit_mesh(me, loop_triangles=False, destructive=False)
        return {'FINISHED'}

    def invoke(self, context, event) -> set[str]:
        obj = context.object
        key_blocks = obj.data.shape_keys.key_blocks
        if self.shape not in key_blocks:
            self.shape = obj.active_shape_key.name
        return {'FINISHED'}


_register_classes, _unregister_classes = bpy.utils.register_classes_factory((
    ClearPendingChanges,
    TransferPendingChanges,
    AverageShapeKeyMovement,
    ActiveVertexMovementToSelected,
))


def draw_to_menu(self: bpy.types.Menu, context):
    layout = self.layout
    layout.separator()
    layout.operator(ClearPendingChanges.bl_idname)
    layout.operator(TransferPendingChanges.bl_idname)
    layout.operator(AverageShapeKeyMovement.bl_idname)
    layout.operator(ActiveVertexMovementToSelected.bl_idname)


def register():
    _register_classes()
    bpy.types.VIEW3D_MT_edit_mesh_vertices.append(draw_to_menu)


def unregister():
    bpy.types.VIEW3D_MT_edit_mesh_vertices.remove(draw_to_menu)
    _unregister_classes()


# Test from editor
if __name__ == "__main__":
    register()

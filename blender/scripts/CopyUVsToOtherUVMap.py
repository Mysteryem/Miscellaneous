bl_info = {
    "name": "Copy UVs To Other UVMap",
    "author": "Mysteryem",
    "version": (1, 0, 0),
    "blender": (2, 93, 7),  # Older versions have not been tested
    "location": "UV Editor > UV > Copy To...",
    "tracker_url": "https://github.com/Mysteryem/Miscellaneous/issues",
    "category": "UV",
}

"""
Adds a "Copy To..." menu to the UV menu of the UV Editor, which can be used to copy UVs or only specific attributes of UVs to another UVMap.
Only operates on the UVs that are visible in the UV Editor (with UV Sync Selection disabled, only the selected faces have their UVs visible).
Optionally filters which UVs are copied, defaulting to those which are selected.
Supports multi-object editing.
"""

import bpy
import bmesh

# Hardcoded Blender limit
max_uv_layers = 8


# Filter constants and functions
def filter_selected(source_bm_loop_uv):
    return source_bm_loop_uv.select


def filter_pinned(source_bm_loop_uv):
    return source_bm_loop_uv.pin_uv


selected_filter_id = 'SELECTED'
pin_filter_id = 'PINNED'

filter_dict = {
    selected_filter_id: filter_selected,
    pin_filter_id: filter_pinned,
}


# Attribute copy constants and functions
def copy_uv(source_bm_loop_uv, target_bm_loop_uv):
    target_bm_loop_uv.uv = source_bm_loop_uv.uv


def copy_uv_x(source_bm_loop_uv, target_bm_loop_uv):
    target_bm_loop_uv.uv.x = source_bm_loop_uv.uv.x


def copy_uv_y(source_bm_loop_uv, target_bm_loop_uv):
    target_bm_loop_uv.uv.y = source_bm_loop_uv.uv.y


def copy_pin(source_bm_loop_uv, target_bm_loop_uv):
    target_bm_loop_uv.pin_uv = source_bm_loop_uv.pin_uv


def copy_select(source_bm_loop_uv, target_bm_loop_uv):
    target_bm_loop_uv.select = source_bm_loop_uv.select


copy_x_id = 'X'
copy_y_id = 'Y'
copy_uv_id = 'UV'
copy_pin_id = 'PIN'
copy_select_id = 'SELECT'
copy_x_and_y_set = {copy_x_id, copy_y_id}

attributes_dict = {
    copy_x_id: copy_uv_x,
    copy_y_id: copy_uv_y,
    copy_uv_id: copy_uv,
    copy_pin_id: copy_pin,
    copy_select_id: copy_select,
}

# UV Map not found action constants
not_found_action_create = 'CREATE'
not_found_action_create_init = 'CREATE_INIT'
not_found_action_skip = 'SKIP'
not_found_action_create_set = {not_found_action_create, not_found_action_create_init}

success_message = "UV Copy To...: UVs copied"
no_changes_message = "UV Copy To...: No changes made"


class MYSTERYEM_copy_uvs_to_other_uvmap(bpy.types.Operator):
    """Copy UVs from the active UVMap to the specified UVMap"""
    bl_idname = 'mysteryem.uv_copy_to_other_uvmap'
    bl_label = "Copy to other UVMap"
    bl_options = {'REGISTER', 'UNDO'}

    filter: bpy.props.EnumProperty(
        name="Filter",
        description="Limit the copied UVs to only those that pass the selected filters",
        items=[
            (selected_filter_id, "Selected", "Only copy UVs that are selected"),
            (pin_filter_id, "Pinned", "Only copy UVs that are pinned"),
        ],
        options={'ENUM_FLAG'},
        default={selected_filter_id},
    )

    target: bpy.props.StringProperty(
        name="Target UV Map",
        description="Name of the UV Map to copy to",
    )

    attributes: bpy.props.EnumProperty(
        name="Attributes",
        description="Which attributes should be copied",
        items=[
            (copy_x_id, "X", "X location"),
            (copy_y_id, "Y", "Y location"),
            # copy_uv_id is used internally when both x and y are selecteds
            (copy_pin_id, "Pin", ""),
            (copy_select_id, "Select", ""),
        ],
        options={'ENUM_FLAG'},
        default={copy_x_id, copy_y_id},
    )

    # This is only really useful when multiple meshes are in edit mode at the same time or when calling the operator manually
    # or changing the target manually through the Redo Toolbar Panel
    not_found_action: bpy.props.EnumProperty(
        name="UV Map not found",
        description="What to do if the target UVMap does not exist",
        items=[
            (not_found_action_skip, "Skip", ""),
            (not_found_action_create, "Create Empty", "Create a new UV Map without any initialisation"),
            (not_found_action_create_init, "Copy", "Create a copy of the active UVMap"),
        ],
        default='SKIP',
    )

    @classmethod
    def poll(cls, context):
        return context.mode == 'EDIT_MESH'

    def execute(self, context):
        target = self.target
        create_target_when_missing = self.not_found_action in not_found_action_create_set
        init_during_create = self.not_found_action == not_found_action_create_init

        meshes = [mesh_obj.data for mesh_obj in context.objects_in_mode_unique_data if mesh_obj.type == 'MESH']

        if not meshes:
            # This shouldn't happen unless it is somehow possible to get into EDIT_MESH mode without a mesh
            self.report({'INFO'}, no_changes_message)
            return {'FINISHED'}

        # Find all meshes that need the target uv_layer to be created
        # We can't add the uv_layers immediately, because some meshes might already have the maximum number
        # of UV maps, in which case we cancel without doing anything and report an error
        need_target_creation_meshes = []
        if create_target_when_missing:
            # Find all the don't have the UVMap
            for mesh in meshes:
                uv_layers = mesh.uv_layers
                if target not in uv_layers:
                    # target needs to be added
                    if len(uv_layers) >= max_uv_layers:
                        self.report({'ERROR_INVALID_INPUT'}, f"The UV Map '{target}' can't be added to the mesh '{mesh.name}' because it already"
                                                             f" has the maximum number of UV Maps ({max_uv_layers}). Execution has been cancelled.")
                        # Nothing has been done
                        # When returning 'CANCELLED', the Redo Toolbar Panel will not undo the previous execution so we return 'FINISHED' even if
                        # nothing happened.
                        return {'FINISHED'}
                    else:
                        need_target_creation_meshes.append(mesh)

        # Add the target UV Map to each mesh that needs it
        init_created_mesh_names = set()
        for mesh in need_target_creation_meshes:
            mesh.uv_layers.new(name=target, do_init=init_during_create)
            # A new layer created with do_init=True is a copy of the active layer, meaning there is no need to
            # copy any attributes because all of them have already been copied in the initialisation
            if init_during_create:
                init_created_mesh_names.add(mesh.name)

        # If no attributes are to be copied, there is no more work to be done
        if not self.attributes:
            if need_target_creation_meshes:
                # Some uv layers were created, so an Undo needs to be pushed
                self.report({'INFO'}, success_message)
                return {'FINISHED'}
            else:
                # No uv layers were created and there are no attributes to be copied, nothing has been done
                self.report({'INFO'}, no_changes_message)
                return {'FINISHED'}
        else:
            filter_funcs = [filter_dict[filter_id] for filter_id in self.filter]

            attributes = self.attributes
            if attributes.issuperset(copy_x_and_y_set):
                # Not sure if it's important to not modify self.attributes, we'll make a copy to be safe
                attributes = attributes.copy()
                attributes -= copy_x_and_y_set
                attributes.add(copy_uv_id)

            attribute_copy_funcs = [attributes_dict[attribute_id] for attribute_id in attributes]

            # UV Sync Selection affects what loops are visible in the UV Editor
            uv_select_sync = context.scene.tool_settings.use_uv_select_sync

            attributes_modified = False
            for me in meshes:
                # If the active uv layer is the same as the target uv layer, nothing needs to be done
                # If the target uv layer doesn't exist on this mesh, then it will be skipped
                # If the target uv layer was created and initiliased because it didn't exist, it will be a copy of the active uv layer,
                # so nothing needs to be done
                if me.uv_layers.active.name != target and me.loops and target in me.uv_layers and me.name not in init_created_mesh_names:
                    bm = bmesh.from_edit_mesh(me)
                    bm_loops = bm.loops
                    active_uv = bm_loops.layers.uv.active
                    target_uv = bm_loops.layers.uv[target]
                    # Only operate on the loops that are actually visible in the UV Editor
                    # With UV Sync Selection enabled, all loops are visible, otherwise only loops belonging to selected faces are visible
                    visible_bm_faces = bm.faces if uv_select_sync else (bm_face for bm_face in bm.faces if bm_face.select)
                    for bm_face in visible_bm_faces:
                        for bm_loop in bm_face.loops:
                            active_loop = bm_loop[active_uv]
                            if all(filter_func(active_loop) for filter_func in filter_funcs):
                                target_loop = bm_loop[target_uv]
                                for attribute_copy_func in attribute_copy_funcs:
                                    attribute_copy_func(active_loop, target_loop)
                                    attributes_modified = True
            if not attributes_modified and not need_target_creation_meshes:
                # No attributes were modifier and no uv layers were created, so nothing has been done
                self.report({'INFO'}, no_changes_message)
                return {'FINISHED'}
        self.report({'INFO'}, success_message)
        return {'FINISHED'}


# This could be used to create a dynamic EnumProperty, but then it wouldn't be possible to specifically copy UVs to a new UV Layer
def get_uv_layer_names_gen(context):
    found_uv_map_names = set()
    active_uv_map_names = [obj.data.uv_layers.active.name for obj in context.objects_in_mode_unique_data if obj.type == 'MESH']
    # If all meshes in edit mode have the same active uv layer, we can exclude it from the menu
    if len(active_uv_map_names) == 1:
        found_uv_map_names.add(active_uv_map_names[0])
    for mesh_obj in context.objects_in_mode_unique_data:
        if mesh_obj.type == 'MESH':
            mesh = mesh_obj.data
            for uv_layer in mesh.uv_layers:
                layer_name = uv_layer.name
                if layer_name not in found_uv_map_names:
                    found_uv_map_names.add(layer_name)
                    yield layer_name


class MYSTERYEM_copy_uvs_menu(bpy.types.Menu):
    bl_idname = 'mysteryem_menu_uv_copy_to'
    bl_label = "Copy to..."

    def draw(self, context):
        layout = self.layout
        for layer_name in get_uv_layer_names_gen(context):
            layout.operator('mysteryem.uv_copy_to_other_uvmap', text=layer_name).target = layer_name


def uv_draw_menu(self, context):
    self.layout.separator()
    self.layout.menu('mysteryem_menu_uv_copy_to')


def register(test=False):
    bpy.utils.register_class(MYSTERYEM_copy_uvs_to_other_uvmap)
    bpy.utils.register_class(MYSTERYEM_copy_uvs_menu)
    if not test:
        bpy.types.IMAGE_MT_uvs.append(uv_draw_menu)


def unregister():
    bpy.types.IMAGE_MT_uvs.remove(uv_draw_menu)
    bpy.utils.unregister_class(MYSTERYEM_copy_uvs_menu)
    bpy.utils.unregister_class(MYSTERYEM_copy_uvs_to_other_uvmap)


# Test from the text editor without adding to the menu each time
if __name__ == '__main__':
    register(test=True)

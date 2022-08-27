# The functions here let you select all vertices of the active (currently selected) shape key that move a vertex by more than the specified distance argument
# With the default argument of 0, this selects all vertices that the active shape key moves
#
# I tried and failed to replicate the way selection by vertex group works, whereby if you're in FACE select mode only, vertices still get selected, but do not show as selected
# so have presented two options
#
#
# This version forces vertex selection on and doesn't use bmesh
def select_shape_key_verts(min_distance = 0):
    obj = bpy.context.object
    active_shape_key = obj.active_shape_key
    # If not in edit mode or there's no active shape key, don't do anything
    if obj.mode == 'EDIT' and active_shape_key != None :
        # Add vertex selection mode to the currently active selection modes
        bpy.ops.mesh.select_mode(use_extend = True, type = 'VERT', action = 'ENABLE')
        # Set to object mode so that data can be manipulated
        bpy.ops.object.mode_set(mode = 'OBJECT')
        # Working with squared distances is a minor optimisation since it avoid square roots
        min_distance_squared = min_distance * min_distance
        verts = obj.data.vertices
        # Get the data of the active (selected) shape key
        shape_key_data = active_shape_key.data
        # Get the data of the shape key the active shape key is relative to
        relative_key_name = active_shape_key.relative_key.name
        relative_shape_key_data = obj.data.shape_keys.key_blocks[relative_key_name].data
        # Go through every vertex comparing the difference between that vertex in both shape keys, selecting those that are further apart than the min_distance argument
        for i in range(len(verts)):
            difference = shape_key_data[i].co - relative_shape_key_data[i].co
            if difference.length_squared > min_distance_squared:
                verts[i].select = True
        # Go back to EDIT mode so it doesn't look like the mode was changed
        bpy.ops.object.mode_set(mode = 'EDIT')

# This version uses bmesh and you will need to import bmesh if using it directly from the console if it's not already imported.
#
# When in Face selection mode only, this behaves slightly weird in that it'll show edges in the selection, but at the same time, won't show lone vertices in the selection
# (despite the fact that they're still selected). Not showing the vertices as selected is the same behaviour as selecting by vertex group, but the edges showing as selected is
# different behaviour
#
#import bmesh
def select_shape_key_verts_alt(min_distance = 0):
    obj = bpy.context.object
    active_shape_key = obj.active_shape_key
    # If not in edit mode or there's no active shape key, don't do anything
    if obj.mode == 'EDIT' and active_shape_key != None :
        # Using squared distances is a minor optimisation since it avoids square roots
        min_distance_squared = min_distance * min_distance
        # Create the bmesh
        bm = bmesh.from_edit_mesh(obj.data)
        # Vertex selection mode since that's what we'll be selecting
        bm.select_mode = {'VERT'}
        # Get the layer for the shape key that the active shape key is relative to
        relative_shape_layer = bm.verts.layers.shape[active_shape_key.relative_key.name]
        # Go through every vertex comparing the difference between that vertex in both shape keys, selecting those that are further apart than the min_distance argument
        for v in bm.verts:
            # In a from_edit_mesh bmesh, the BMVert.co corresponds to the active shape key position, accessing via the active shape's layer will not give up-to-date values
            difference = v.co - v[relative_shape_layer]
            if difference.length_squared > min_distance_squared:
                v.select = True
        # Flush the selection changes
        bm.select_flush_mode()

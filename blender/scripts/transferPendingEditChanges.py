import bpy
import bmesh

"""
Transfer pending non-destructive changes to the current shape key to a different shape key and
undo the pending changes to the current shape key.

Intended for use when you start making changes to a shape key, but accidentally had the wrong
shape key active. The script lets you transfer those pending changes to a different shape key.
"""

# TODO: Could create a new shape key instead of requiring another one to exist already, though
#  a shape key created in edit mode (bm.verts.layers.shape.new()) won't immediately appear in
# the UI. Also note that shape keys created this way are initialised to (0,0,0) for every vertex

# Name of the shape key you intended to be working on, but weren't, changes will be transfered
# there
# Change this to the shape key you intended to be working on
key_name = "Key 1"

me = bpy.context.object.data
bm = bmesh.from_edit_mesh(me)

# In edit mode, the active shape key isn't updated until you change shape key, leave edit mode
# or perform certain operators, meaning it can contain the pre-modification positions of vertices
# still.
active_shape_layer = bm.verts.layers.shape.active
transfer_to_shape_layer = bm.verts.layers.shape[key_name]

# Add the pending changes to key_name and undo the pending changes
for bv in bm.verts:
    active_co = bv[active_shape_layer]
    pending_co = bv.co
    if pending_co != active_co:
        difference = pending_co - active_co
        bv[transfer_to_shape_layer] = bv[transfer_to_shape_layer] + difference
        bv.co = active_co

# Alternative to replace the co in key_name instead of adding
#for bv in bm.verts:
#    active_co = bv[active_shape_layer]
#    if bv.co != active_co:
#        bv[transfer_to_shape_layer] = bv.co
#        bv.co = active_co

# Alternative to replace all co instead only changed co
#for bv in bm.verts:
#    bv[transfer_to_shape_layer] = bv.co
#    bv.co = bv[active_shape_layer]

# Update viewport display
bmesh.update_edit_mesh(me, loop_triangles=False, destructive=False)

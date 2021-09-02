# Astonishingly, Blender has no way to reorder UV layers, something which is very important for working with exported models outside of Blender.
# The suggested workaround of duplicating and deleting layers until they're in the order you want is painful
# This script allows for reordering UV layers by swapping the data and names of two layers since I couldn't figure out a way to reorder them normally
# Since I don't know the extent of what's possible with Blender addons and scripts, it might be a good idea to add some sanity checks to ensure that
# len(layer1.data) == len(layer2.data) and that both layers have the same properties for each datum (uv, pin_uv, select and the read-only rna_type),
# possibly going further, to find all the non-read-only properties and swap them all, instead of doing a hardcoded swap of only the known properties.
#
# Internal function for swapping data
def swap_uv_layers(uv_layers, index1, index2, old_mode = 'OBJECT'):
    # Trying to swap the data in edit mode only swaps the names of the layers, I'm guessing because it's already open for editing by Blender itself
    bpy.ops.object.mode_set(mode = 'OBJECT')
    layer1 = uv_layers[index1]
    layer2 = uv_layers[index2]
    layer1_name = layer1.name
    layer2_name = layer2.name
    # Can't have two uvmaps with the same name. Blender will add .001 on the end of the changed name if it already exists, so we change to a temporary name first
    # It doesn't matter if there is already a layer called 'temp' since layer1 will become 'temp.001' and then we change it immediately afterwards
    layer1.name = 'temp'
    layer2.name = layer1_name
    layer1.name = layer2_name
    for i in range(len(layer1.data)):
        # The uvs in layer2 don't change without the copy(), not sure why this would only affect uv, and not pin_uv or select
        layer1_uv = layer1.data[i].uv.copy()
        layer1_pin_uv = layer1.data[i].pin_uv
        layer1_select = layer1.data[i].select
        layer1.data[i].uv = layer2.data[i].uv
        layer1.data[i].pin_uv = layer2.data[i].pin_uv
        layer1.data[i].select = layer2.data[i].select
        layer2.data[i].uv = layer1_uv
        layer2.data[i].pin_uv = layer1_pin_uv
        layer2.data[i].select = layer1_select
    # Swap back to whatever mode we were in before swapping to object mode
    bpy.ops.object.mode_set(mode = old_mode)

def move_active_uv_layer_up():
    active_object = bpy.context.object
    uv_layers = active_object.data.uv_layers
    index = uv_layers.active_index
    # If the active layer is not already at the top
    if index > 0:
        swap_uv_layers(uv_layers, index-1, index, active_object.mode)
        uv_layers.active_index = index-1

def move_active_uv_layer_down():
    active_object = bpy.context.object
    uv_layers = active_object.data.uv_layers
    index = uv_layers.active_index
    # If the active layer is not already at the bottom
    if index < len(uv_layers) - 1:
        swap_uv_layers(uv_layers, index, index+1, active_object.mode)
        uv_layers.active_index = index+1

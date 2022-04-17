# 'Unatlas' the selected uvs.
# To use, enter edit mode and select all uvs belonging to a specific texture in the atlas, then run the script from Blender's Text editor.
# The script will determine the texture's size in the atlas from the bounding box of the selection. The bounding box of the selection must
#  have non-zero width and height.
# This script will only work with texture atlases that are divided into powers of 2 with no margins between textures
#  (such texture atlases shouldn't be used in Unity otherwise the textures in the atlas will blend together much sooner in the atlas' mipmaps).
# There are most likely areas to improve since this was written quickly while drinking. Eventually it'd be nice to turn this into a mini-addon
#  that adds some buttons to the UI somewhere.
import bpy
import bmesh
import math
from mathutils import Vector

obj = bpy.context.object

me = obj.data
bm = bmesh.from_edit_mesh(me)
uv_layer = bm.loops.layers.uv.active

# Set to true if you want to 'unatlas' uvs of a non-square textures.
allow_non_square = False

if uv_layer:
    selected_uvs = []
    selected_u = []
    selected_v = []
    min_u = min_v = math.inf
    max_u = max_v = -math.inf

    for bmf in bm.faces:
        for bml in bmf.loops:
            bmuv = bml[uv_layer]
            if bmuv.select:
                selected_uvs.append(bmuv)
                selected_u.append(bmuv.uv.x)
                selected_v.append(bmuv.uv.y)
    
    print(f'num selected uvs: {len(selected_uvs)}')
    
    if selected_uvs:
        max_u = max(selected_u)
        min_u = min(selected_u)
        max_v = max(selected_v)
        min_v = min(selected_v)
        x_bb_length = max_u - min_u
        y_bb_length = max_v - min_v
        
        print(f'bb bottom left: ({min_u}, {min_v})')
        print(f'bb top right: ({max_u}, {max_v})')
        
        print(f'x bb length: {x_bb_length}')
        print(f'y bb length: {y_bb_length}')
        
        # todo: There's probably a purely maths based way to do this, though this shouldn't take too many
        #  iterations even with very small bb lengths since exponentiation grows very quickly
        def get_division_size(normalized_length):
            if normalized_length <= 0:
                raise RuntimeError('normalized_length must be positive. Make sure the selected uvs form a bounding box with non-zero width and non-zero height')
            n = 0
            while(True):
                if normalized_length > 1/(2**n):
                    return n - 1
                n += 1
        
        x_division_size = get_division_size(x_bb_length)
        y_division_size = get_division_size(y_bb_length)
        
        if not allow_non_square:
            x_division_size = y_division_size = min(x_division_size, y_division_size)
        
        x_divisions = 2**x_division_size
        y_divisions = 2**y_division_size
        
        print(f'x divisions: {x_divisions}')
        print(f'y divisions: {y_divisions}')
        
        def find_closest_division(divisions, normalized_value):
            return int(normalized_value * divisions)
        
        min_texture_u = find_closest_division(x_divisions, min_u)/x_divisions
        min_texture_v = find_closest_division(y_divisions, min_v)/y_divisions
        
        print(f'texture bottom left: ({min_texture_u}, {min_texture_v})')
        
        vec_to_subtract = Vector((min_texture_u, min_texture_v))
        
        print(f'to subtract: {vec_to_subtract}')
        
        vec_to_scale = Vector((x_divisions, y_divisions))
        
        print(f'to scale: {vec_to_scale}')
        
        for uv in selected_uvs:
            uv.uv = (uv.uv - vec_to_subtract) * vec_to_scale
        # Update the edit mode view so the user can see the updated uvs
        bmesh.update_edit_mesh(me, loop_triangles=False, destructive=False)

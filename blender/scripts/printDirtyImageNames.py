# If there is an easy way to see which images in blender have changes that haven't been saved, I have no idea where it is.
def print_dirty_images():
    for image in bpy.data.images:
        if image.is_dirty:
            print(image.name_full)

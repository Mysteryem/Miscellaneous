import bpy

bl_info = {
    "name": "Modified images menu",
    "author": "Mysteryem",
    "version": (1, 0, 0),
    "blender": (2, 93, 7),
    "location": "Image/UV Editor -> Image -> Modified Images",
    "tracker_url": "https://github.com/Mysteryem/Miscellaneous/issues",
    "category": "Interface",
}

"""
Adds a "Modified Images" menu to the Image menu. This new menu shows the names of all modified images, clicking on one 
will load that image into the editor
"""

class IMAGE_MT_mysteryem_modified_images(bpy.types.Menu):
    bl_idname = "IMAGE_MT_mysteryem_modified_images_list"
    bl_label = "Modified Images"

    def draw(self, context):
        layout = self.layout
        image: bpy.types.Image
        dirty_image_names = [image.name for image in bpy.data.images if image.is_dirty]
        if dirty_image_names:
            # Blender seems to sort images by lowercase when picking which image to show in the editor
            for image_name in sorted(dirty_image_names, key=str.lower):
                options = layout.operator('wm.context_set_id', text=image_name)
                options.data_path = 'space_data.image'
                options.value = image_name
        else:
            layout.label(text="No modified images")


def draw_modified_image_menu(self, context):
    layout: bpy.types.UILayout
    layout = self.layout
    layout.separator()
    col = layout.column()
    col.enabled = any(i.is_dirty for i in bpy.data.images)
    col.menu(menu=IMAGE_MT_mysteryem_modified_images.bl_idname)


def register():
    bpy.utils.register_class(IMAGE_MT_mysteryem_modified_images)
    bpy.types.IMAGE_MT_image.append(draw_modified_image_menu)


def unregister():
    bpy.types.IMAGE_MT_image.remove(draw_modified_image_menu)
    bpy.utils.unregister_class(IMAGE_MT_mysteryem_modified_images)

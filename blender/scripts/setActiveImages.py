# Sometimes I accidentally change the active image texture node in a material and sometimes I swear I don't, but I keep
# baking textures to the wrong image somehow.
# This script is meant to help with that by setting the active images in all materials of all selected objects to the current to the
# active image of the active material of the active object.
#
# create: True to create a new image texture node if the material processed does not contain an image texture node with the active image set,
#         otherwise won't modify materials that don't already contain a node with the correct image
def set_active_images(create = False):
    # Get the active node of the active material of the active object
    active_material = bpy.context.active_object.active_material
    active_node = active_material.node_tree.nodes.active
    # If the node is an image texture node, get its image
    if active_node.type == 'TEX_IMAGE':
        active_image = active_node.image
        if active_image is not None:
            # Keep a set of materials that we've processed so we don't do more work than we need to
            # The active material can be added initially, since we don't need to do anything to it
            found_materials = {active_material}
            processed_materials = {active_material}
            # Iterate the selected objects
            for obj in bpy.context.selected_objects:
                for material_slot in obj.material_slots:
                    material = material_slot.material
                    # Skip materials that have already been processed
                    if material not in found_materials:
                        # Add the material to the set of processed materials
                        found_materials.add(material)
                        nodes = material.node_tree.nodes
                        # Store if we find a suitable image texture node
                        found_node = False
                        # Iterate through the nodes looking for an image texture node with the correct image
                        for n in nodes:
                            if n.type == 'TEX_IMAGE' and n.image == active_image:
                                # Select the node
                                n.select = True
                                # Set it as the active node
                                nodes.active = n
                                found_node = True
                                # This material won't need to be processed again so add it to the set
                                processed_materials.add(material)
                                break
                        # With create set to True, if no suitable node is found, create one
                        if create and not found_node:
                            new_node = nodes.new("ShaderNodeTexImage")
                            new_node.select = True
                            new_node.image = active_image
                            nodes.active = new_node
                            # With the new node created, this material won't need to be processed again
                            processed_materials.add(material)
            # Print the names of the processed materials after sorting them
            processed_material_names = [material.name for material in processed_materials]
            # Ignore-case sorting
            processed_material_names.sort(key = str.lower)
            print('Set: ' + active_image.name + ' as the active image for ' + str(processed_material_names))

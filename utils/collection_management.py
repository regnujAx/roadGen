import bpy


def delete(collections: list):
    for collection_name in collections:
        objects = objects_from_collection(collection_name)

        while objects:
            bpy.data.objects.remove(objects.pop())

        remove_collection(collection_name)


def hide_collection(collection_name: str):
    bpy.context.view_layer.layer_collection.children[collection_name].hide_viewport = True


def link_to_collection(mesh: bpy.types.Object, collection_name: str):
    collection = bpy.data.collections.get(collection_name)

    if collection is None:
        collection = bpy.data.collections.new(collection_name)
        bpy.context.scene.collection.children.link(collection)

    collection.objects.link(mesh)


def objects_from_collection(collection_name: str):
    collection = bpy.data.collections.get(collection_name)

    if collection:
        # Find all objects in the collection
        objects = [obj for obj in collection.objects]
        return objects

    return []


def remove_collection(collection_name: str):
    collection = bpy.data.collections.get(collection_name)

    if collection:
        bpy.data.collections.remove(collection)

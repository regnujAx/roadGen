import bpy


def crossing_points():
    markers = objects_from_collection("Crossing Points")
    return [marker for marker in markers if marker.visible_get()]


def delete_collections_with_objects(collection_names: list):
    for collection_name in collection_names:
        objects = objects_from_collection(collection_name)

        while objects:
            bpy.data.objects.remove(objects.pop())

        remove_collection(collection_name)


def first_and_last_objects_from_collections(collection_names: list, number_of_objects: int):
    objects = []
    for collection_name in collection_names:
        collection = bpy.data.collections[collection_name]
        objects.extend(collection.objects[:number_of_objects])
        objects.extend(collection.objects[-number_of_objects:])

    return objects


def switch_collection_visibility(collection_name: str):
    collection = bpy.data.collections.get(collection_name)

    if collection:
        coll = bpy.context.view_layer.layer_collection.children[collection_name]
        coll.hide_viewport = not coll.hide_viewport


def switch_collections_visibility(collection_names: list):
    for collection_name in collection_names:
        switch_collection_visibility(collection_name)


def link_to_collection(mesh: bpy.types.Object, collection_name: str, child_collection_name: str = None):
    collection = bpy.data.collections.get(collection_name)

    if collection is None:
        collection = bpy.data.collections.new(collection_name)
        bpy.context.scene.collection.children.link(collection)

    if child_collection_name:
        child_collection = bpy.data.collections.get(child_collection_name)

        if child_collection is None:
            child_collection = bpy.data.collections.new(child_collection_name)
            # Add the new child collection to its parent collection
            collection.children.link(child_collection)

        collection = child_collection

    collection.objects.link(mesh)


def objects_from_collection(collection_name: str, subcollections: bool = False):
    collection = bpy.data.collections.get(collection_name)

    if collection:
        # Find all objects in the collection
        if subcollections:
            objects = [obj for obj in collection.children]
        else:
            objects = [obj for obj in collection.objects if obj.parent is None]
        return objects

    return []


def remove_collection(collection_name: str):
    collection = bpy.data.collections.get(collection_name)

    if collection:
        bpy.data.collections.remove(collection)

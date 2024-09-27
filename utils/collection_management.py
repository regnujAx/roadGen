import bpy


def count_empty_objects_in_collection(collection):
    counter = 0

    for obj in collection.objects:
        if obj.type == 'EMPTY':
            counter += 1

    for subcollection in collection.children:
        counter += count_empty_objects_in_collection(subcollection)

    return counter


def count_objects_in_collection(collection: bpy.types.Collection, with_subcollections: bool):
    counter = len(collection.objects)

    for subcollection in collection.children:
        counter += count_objects_in_collection(subcollection, with_subcollections) if with_subcollections else 1

    return counter


def count_objects_in_collections(collection_names: list, with_subcollections: bool = True, emptys: bool = False):
    counter = 0

    for collection_name in collection_names:
        collection = bpy.data.collections.get(collection_name)

        if collection:
            if emptys:
                counter += count_empty_objects_in_collection(collection)
            else:
                counter += count_objects_in_collection(collection, with_subcollections)

    return counter


def get_crossing_curves(crossroad_point: bpy.types.Object, with_crossroad_curves: bool = False):
    curves = []
    curves_number = crossroad_point.get("Number of Curves")

    if curves_number:
        curves_number = int(curves_number)

        if curves_number > 1:
            for i in range(curves_number):
                if with_crossroad_curves:
                    curve_name_1 = crossroad_point.get(f"Curve {i+1}")

                    if i < curves_number - 1:
                        curve_name_2 = crossroad_point.get(f"Curve {i+2}")
                    else:
                        curve_name_2 = crossroad_point.get("Curve 1")

                    curve_name = f"Crossroad_Curve_{curve_name_1}_{curve_name_2}"
                else:
                    curve_name = crossroad_point.get(f"Curve {i+1}")

                curve = bpy.data.objects.get(curve_name)

                if curve:
                    curves.append(curve)

    return curves


def get_crossing_points():
    markers = get_objects_from_collection("Crossing Points")
    return [marker for marker in markers if marker.visible_get()]


def delete_collection_and_subcollections(collection):
    for subcollection in collection.children:
        delete_collection_and_subcollections(subcollection)

    for obj in collection.objects:
        bpy.data.objects.remove(obj, do_unlink=True)

    bpy.data.collections.remove(collection)


def delete_collections_with_objects(collection_names: list):
    for collection_name in collection_names:
        collection = bpy.data.collections.get(collection_name)

        if collection:
            delete_collection_and_subcollections(collection)


def get_first_and_last_objects_from_collections(collection_names: list, number_of_objects: int):
    objects = []
    for collection_name in collection_names:
        collection = bpy.data.collections[collection_name]
        objects.extend(collection.objects[:number_of_objects])
        objects.extend(collection.objects[-number_of_objects:])

    return objects


def get_objects_from_subcollections_in_collection_by_name(collection_name: str, filter_name: str):
    objects = []
    collection = bpy.data.collections.get(collection_name)

    if collection:
        for subcollection in collection.children:
            if filter_name in subcollection.name:
                objects.extend([obj for obj in subcollection.objects if filter_name in obj.name])

    return objects


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


def get_objects_from_collection(collection_name: str, subcollections: bool = False):
    collection = bpy.data.collections.get(collection_name)

    if collection:
        # Find all objects in the collection
        if subcollections:
            objects = [obj for obj in collection.children]
        else:
            objects = [obj for obj in collection.objects if obj.parent is None]
        return objects

    return []


def switch_collection_visibility(collection_name: str):
    collection = bpy.data.collections.get(collection_name)

    if collection:
        coll = bpy.context.view_layer.layer_collection.children[collection_name]
        coll.hide_viewport = not coll.hide_viewport


def switch_collections_visibility(collection_names: list):
    for collection_name in collection_names:
        switch_collection_visibility(collection_name)

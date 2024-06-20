import bpy
import mathutils
import numpy as np


# ------------------------------------------------------------------------
#    Helper Methods
# ------------------------------------------------------------------------


def apply_rotation_and_scale(object: bpy.types.Object, properties: bool = True):
    object.select_set(True)
    bpy.ops.object.transform_apply(location=False, properties=properties)
    object.select_set(False)


def create_kdtree(list: list, size: int):
    # Create a KD-Tree to perform a spatial search
    kd = mathutils.kdtree.KDTree(size)
    for i, v in enumerate(list):
        kd.insert(v, i)

    # Balance (build) the KD-Tree
    kd.balance()

    return kd


def delete(collections: list):
    for collection_name in collections:
        objects = get_objects_from_collection(collection_name)

        while objects:
            bpy.data.objects.remove(objects.pop())

        remove_collection(collection_name)


def find_closest_points(list: list, reference_point: mathutils.Vector):
    num_vertices = len(list)
    kd = create_kdtree(list, num_vertices)
    # Sort the points by distance to the reference point and return them
    return kd.find_n(reference_point, num_vertices)


def get_closest_point(point_1: mathutils.Vector, point_2: mathutils.Vector, reference_point: mathutils.Vector):
    distance_1 = np.sqrt(np.sum([
        (point_1.x - reference_point.x)**2,
        (point_1.y - reference_point.y)**2,
        (point_1.z - reference_point.z)**2]))
    distance_2 = np.sqrt(np.sum([
        (point_2.x - reference_point.x)**2,
        (point_2.y - reference_point.y)**2,
        (point_2.z - reference_point.z)**2]))
    return point_1 if distance_1 < distance_2 else point_2


def get_coplanar_faces(
        object: bpy.types.Object, normal: mathutils.Vector, road_height: float = 0.1, threshold: float = 0.00001):
    return [f for f in object.data.polygons if f.normal.angle(normal) < threshold and f.center.z < road_height]


def get_line_meshes(curve_name: str):
    left_line = bpy.data.objects.get(f"Line_Mesh_Kerb_Left_{curve_name}")
    right_line = bpy.data.objects.get(f"Line_Mesh_Kerb_Right_{curve_name}")
    return left_line, right_line


def get_objects_from_collection(collection_name: str):
    collection = bpy.data.collections.get(collection_name)

    if collection:
        # Find all objects in the collection
        objects = [obj for obj in collection.objects]
        return objects

    return []


def get_visible_curves():
    # Get all visible (not hidden) curves
    objects = bpy.context.scene.objects
    return [obj for obj in objects if obj.type == "CURVE" and obj.visible_get()]


def link_to_collection(mesh: bpy.types.Object, collection_name: str):
    collection = bpy.data.collections.get(collection_name)

    if collection is None:
        collection = bpy.data.collections.new(collection_name)
        bpy.context.scene.collection.children.link(collection)

    collection.objects.link(mesh)


def remove_collection(collection_name: str):
    collection = bpy.data.collections.get(collection_name)

    if collection:
        bpy.data.collections.remove(collection)


def set_origin(object: bpy.types.Object):
    object.select_set(True)
    bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center='BOUNDS')
    object.select_set(False)


def show_message_box(title: str = "Message Box", message: str = "", icon: str = "INFO"):
    def draw(self, context):
        self.layout.label(text=message)

    bpy.context.window_manager.popup_menu(draw, title=title, icon=icon)

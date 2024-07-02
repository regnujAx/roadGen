import bmesh
import bpy
import math
import mathutils


# ------------------------------------------------------------------------
#    Helper Methods
# ------------------------------------------------------------------------


def add_mesh_to_curve(mesh_template: bpy.types.Object, curve: bpy.types.Object, name: str, lane_width: float, index: int):
    mesh = mesh_template.copy()
    mesh.data = mesh_template.data.copy()
    mesh.name = name + "_" + curve.name
    mesh.location = curve.location

    x, y, z = 0.0, 0.0, 0.0
    # Translate the created mesh according to the lane width and the number of lanes per road side (i.e. index)
    if "Lane" in name:
        y = lane_width * index - lane_width / 2
        mesh.dimensions[1] = lane_width
    elif "Kerb" in name:
        # Calculate an offset for the y-coordinate depending on the lane width, index and side of the kerb (right:neg, left:pos)
        sign = -1 if index < 0 else 1
        y = lane_width * index + (sign * mesh.dimensions[1]/2)
        # Keep its original z-location for the kerb
        z = mesh.location[2]
    mesh.location += mathutils.Vector((x, y, z))

    # Calculate and update the x-dimension of the mesh so it fits better to its curve
    threshold = 0.001
    x_dim = curve.data.splines[0].calc_length()
    while x_dim > 3.0:
        x_dim /= 2.0
    mesh.dimensions[0] = x_dim + threshold

    # Apply the correct curve for the mesh modifiers
    mesh.modifiers['Array'].curve = curve
    mesh.modifiers['Curve'].object = curve

    # Add the created mesh to the correct collection and apply its rotation and scale
    collection_name = "Road Lanes" if "Road_Lane" in name else "Kerbs"
    link_to_collection(mesh, collection_name)
    apply_transform(mesh, location=False, properties=False)

    # Set the mesh as active object and apply its modifiers
    bpy.context.view_layer.objects.active = mesh
    for modifier in mesh.modifiers:
        bpy.ops.object.modifier_apply(modifier=modifier.name)


def apply_transform(
        object: bpy.types.Object, location: bool = True, rotation: bool = True, scale: bool = True, properties: bool = True):
    object.select_set(True)
    bpy.ops.object.transform_apply(location=location, rotation=rotation, scale=scale, properties=properties)
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


def find_closest_points(list: list, reference_point: mathutils.Vector, find_all: bool = True):
    num_vertices = len(list)
    kd = create_kdtree(list, num_vertices)
    n = num_vertices if find_all else 1
    # Sort the points by distance to the reference point and return the nearest point or all
    return kd.find_n(reference_point, n)


def get_closest_point(points: list, reference_point: mathutils.Vector):
    closest_point = points[0]

    for i in range(len(points) - 1):
        point = points[i+1]
        vector_1 = closest_point - reference_point
        distance_1 = math.sqrt(sum(i**2 for i in vector_1))
        vector_2 = point - reference_point
        distance_2 = math.sqrt(sum(i**2 for i in vector_2))

        if distance_2 < distance_1:
            closest_point = point

    return closest_point


def get_coplanar_faces(
        object: bpy.types.Object, normal: mathutils.Vector, index: int, road_height: float = 0.1, threshold: float = 0.001):
    data = object.data
    bm = bmesh.new()
    bm.from_mesh(data)
    bm.faces.ensure_lookup_table()
    face = bm.faces[index]
    coplanar_faces_ids = []
    coplanar_faces_ids.append(face.index)

    # Iterate over all faces and check for each if it is coplanar to the current face
    for i in range(len(bm.faces)):
        for e in face.edges:
            for link_face in e.link_faces:
                if (link_face.normal.angle(normal) < threshold and
                        link_face.index not in coplanar_faces_ids and
                        link_face.calc_center_median().z < road_height):
                    coplanar_faces_ids.append(link_face.index)
                    face = link_face
                    break

    return [data.polygons[idx] for idx in coplanar_faces_ids]


def get_line_meshes(curve_name: str):
    left_line_mesh = bpy.data.objects.get(f"Line_Mesh_Kerb_Left_{curve_name}")
    right_line_mesh = bpy.data.objects.get(f"Line_Mesh_Kerb_Right_{curve_name}")
    return left_line_mesh, right_line_mesh


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


def hide_collection(collection_name: str):
    bpy.context.view_layer.layer_collection.children[collection_name].hide_viewport = True


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


# def get_geometry_center(object: bpy.types.Object):
#     sum_world_coord = [0, 0, 0]
#     num_vertices = len(object.data.vertices)
#     wm = object.matrix_world

#     for vert in object.data.vertices:
#         world_coord = wm @ vert.co
#         sum_world_coord += world_coord

#     sum_world_coord /= num_vertices

#     return sum_world_coord


# def set_origin(object: bpy.types.Object, crossing_point_loc: mathutils.Vector = None):
#     old_loc = object.location
#     if crossing_point_loc:
#         new_loc = crossing_point_loc
#     else:
#         new_loc = get_geometry_center(object)

#     for vert in object.data.vertices:
#         vert.co -= new_loc - old_loc

#     object.location = new_loc


def set_origin(object: bpy.types.Object):
    object.select_set(True)
    bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center='BOUNDS')
    object.select_set(False)


def show_message_box(title: str = "Message Box", message: str = "", icon: str = "INFO"):
    def draw(self, context):
        self.layout.label(text=message)

    bpy.context.window_manager.popup_menu(draw, title=title, icon=icon)

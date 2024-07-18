import bmesh
import bpy
import math
import mathutils

from .collection_management import link_to_collection


def add_line_following_mesh(mesh_name: str):
    mesh = bpy.data.objects.get(mesh_name)
    bm = bmesh.new()
    bm.from_mesh(mesh.data)

    top_faces_center = []
    # Calculate centers for all faces and save only the "top" (highest z-coordinate) faces
    for face in bm.faces:
        center = face.calc_center_median()

        if center[2] >= 0.24999:
            top_faces_center.append(center)

    bm.free()

    line_mesh_name = "Line_Mesh_" + mesh_name
    # Add a new mesh
    new_mesh = bpy.data.meshes.new("new_mesh")
    # Add a new object (line mesh) using the new mesh
    line_mesh = bpy.data.objects.new(line_mesh_name, new_mesh)

    # Deselect all selected objects to ensure that no object is selected
    deselect_all()

    # Link the line mesh to the correct colletion
    collection_name = "Line Meshes"
    link_to_collection(line_mesh, collection_name)

    line_mesh.select_set(True)

    points = find_closest_points(top_faces_center, top_faces_center[0])

    bm = bmesh.new()
    # Add the top faces centers as vertices to the new mesh
    for (co, index, dist) in points:
        bm.verts.new(co)

    # Ensure internal data needed for int subscription is initialized with vertices, e.g. bm.verts[index]
    bm.verts.ensure_lookup_table()

    for i in range(len(bm.verts) - 1):
        # Add a new edge with the current vertex and the closest next vertex
        bm.edges.new((bm.verts[i], bm.verts[i+1]))

    # Fill line mesh's data with the BMesh
    bm.to_mesh(line_mesh.data)
    bm.free()

    # Deselect the line mesh and update its location
    line_mesh.select_set(False)
    line_mesh.location = mesh.location


def add_mesh_to_curve(
        mesh_template: bpy.types.Object, curve: bpy.types.Object, name: str, lane_width: float, index: int,
        offset: float = None):
    collection_name = "Road Lanes"
    child_collection_name = None
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
        collection_name = "Kerbs"
        # Calculate an offset for the y-coordinate depending on the lane width, index and side of the kerb (right:neg, left:pos)
        sign = -1 if index < 0 else 1
        y = lane_width * index + sign * mesh.dimensions[1] / 2
        # Keep its original z-location for the kerb
        z = mesh.location[2]
    elif "Sidewalk" in name:
        collection_name = "Sidewalks"
        # Add for every sidewalk a new collection for separated meshes
        child_collection_name = mesh.name
        sign = -1 if index < 0 else 1
        y = lane_width * index + sign * (mesh.dimensions[1] / 2 + offset)
    mesh.location += mathutils.Vector((x, y, z))

    # Calculate and update the x-dimension of the mesh so it fits better to its curve
    threshold = 0.001
    x_dim = curve.data.splines[0].calc_length()
    while x_dim > 3.0:
        x_dim /= 2.0
    mesh.dimensions[0] = x_dim + threshold

    # Apply the correct curve for the mesh modifiers
    mesh.modifiers["Array"].curve = curve
    mesh.modifiers["Curve"].object = curve

    # Add the created mesh to the correct collection and apply its rotation and scale
    link_to_collection(mesh, collection_name, child_collection_name)
    apply_transform(mesh, location=False, properties=False)

    # Set the mesh as active object and apply its modifiers
    bpy.context.view_layer.objects.active = mesh
    for modifier in mesh.modifiers:
        bpy.ops.object.modifier_apply(modifier=modifier.name)

    return mesh


def edit_mesh_at_positions(mesh_name: str, positions: list):
    # Get the corresponding line mesh
    line_mesh_name = "Line_Mesh_" + mesh_name
    line_mesh = bpy.data.objects.get(line_mesh_name)

    # Create a BMesh from the line mesh for edge length calculation
    mesh_eval_data = line_mesh.data
    bm_line = bmesh.new()
    bm_line.from_mesh(mesh_eval_data)

    object_position = None
    for pos in positions:
        p = pos
        total_length = 0

        # Iterate over all line mesh edges to find its position, which corresponds to the given position
        for edge in bm_line.edges:
            edge_length = edge.calc_length()
            total_length += edge_length

            # Calculate the position on the line mesh when a position is reached
            if total_length > pos:
                v0 = edge.verts[0]
                v1 = edge.verts[1]
                vec = mathutils.Vector(v1.co) - mathutils.Vector(v0.co)
                unit_vec = vec / edge_length
                object_position = v0.co + unit_vec * p
                break

            p -= edge_length

        # Edit the mesh at the reached position
        if object_position:
            mesh = bpy.data.objects.get(mesh_name)
            vertices = [vertex.co for vertex in mesh.data.vertices]

            kd = create_kdtree(vertices, len(vertices))

            # Decrease the "height" (z-coordinate) of all vertices in a certain radius that are higher than 0
            radius = 2
            for (co, index, dist) in kd.find_range(object_position, radius):
                vertex = vertices[index]

                if vertex.z > 0.2:
                    vertex.z -= 0.135

    bm_line.free()


def apply_transform(
        object: bpy.types.Object, location: bool = True, rotation: bool = True, scale: bool = True, properties: bool = True):
    object.select_set(True)
    bpy.ops.object.transform_apply(location=location, rotation=rotation, scale=scale, properties=properties)
    object.select_set(False)


def closest_point(points: list, reference_point: mathutils.Vector):
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


def create_kdtree(vertices: list, size: int):
    # Create a KD-Tree to perform a spatial search
    kd = mathutils.kdtree.KDTree(size)
    for i, v in enumerate(vertices):
        kd.insert(v, i)

    # Balance (build) the KD-Tree
    kd.balance()

    return kd


def coplanar_faces(
        mesh: bpy.types.Object, normal: mathutils.Vector, index: int, road_height: float = 0.1, threshold: float = 0.001):
    data = mesh.data
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


def deselect_all():
    for object in bpy.context.selected_objects:
        object.select_set(False)


def find_closest_points(list: list, reference_point: mathutils.Vector, find_all: bool = True):
    num_vertices = len(list)
    kd = create_kdtree(list, num_vertices)
    n = num_vertices if find_all else 1
    # Sort the points by distance to the reference point and return the nearest point or all
    return kd.find_n(reference_point, n)


def line_meshes(curve_name: str):
    left_line_mesh = bpy.data.objects.get(f"Line_Mesh_Kerb_Left_{curve_name}")
    right_line_mesh = bpy.data.objects.get(f"Line_Mesh_Kerb_Right_{curve_name}")
    return left_line_mesh, right_line_mesh


def set_origin(object: bpy.types.Object):
    object.select_set(True)
    bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="BOUNDS")
    object.select_set(False)


def separate_array_meshes(mesh: bpy.types.Object):
    bpy.context.view_layer.objects.active = mesh
    bpy.ops.object.mode_set(mode="EDIT")

    # Separate the submeshes into independent meshes
    bpy.ops.mesh.separate(type="LOOSE")
    bpy.ops.object.mode_set(mode="OBJECT")

    # Ensure that no object is selected
    deselect_all()

import bmesh
import bpy
import math

from mathutils import bvhtree, kdtree, Vector

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
    link_to_collection(line_mesh, "Line Meshes")

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
    mesh.location += Vector((x, y, z))

    # Calculate and update the x-dimension of the mesh so it fits better to its curve
    curve_length = curve.data.splines[0].calc_length()
    minimum_width = 2.0
    threshold = 0.001
    x_dim = reduce_to_minimum(curve_length, minimum_width)
    mesh.dimensions[0] = x_dim + threshold

    # Apply the correct curve for the mesh modifiers
    mesh.modifiers["Array"].curve = curve
    mesh.modifiers["Curve"].object = curve

    # Add the created mesh to the correct collection and apply its rotation and scale
    link_to_collection(mesh, collection_name, child_collection_name)
    apply_transform(mesh, location=False, properties=False)

    # Set the mesh as active object and apply its modifiers
    apply_modifiers(mesh)

    return mesh


def add_object_at_position(object_template: bpy.types.Object, position: Vector):
    # Create a copy of the template and link it to its collection
    object_copy = object_template.copy()
    collection_name = object_template.name + "s"
    link_to_collection(object_copy, collection_name)

    # Hide the copy if it is an empty object
    if object_copy.type == 'EMPTY':
        object_copy.hide_set(True)

    # Copy also the children of the object template
    for child in object_template.children:
        child_copy = child.copy()
        child_copy.parent = object_copy
        child_copy.matrix_parent_inverse = child.matrix_parent_inverse
        link_to_collection(child_copy, collection_name)

    # Update the location of the object copy
    object_copy.location = position

    # The scene need to be updated so the locations are correct
    bpy.context.view_layer.update()

    return object_copy


def add_objects(curve: bpy.types.Object, side: str, object_template: bpy.types.Object, minimum_distance: float, offset: float):
    line_mesh = bpy.data.objects.get("Line_Mesh_Kerb_" + side + "_" + curve.name)
    m = line_mesh.matrix_world

    # Create a BMesh from the line mesh for edge length calculation
    mesh_eval_data = line_mesh.data
    bm_line = bmesh.new()
    bm_line.from_mesh(mesh_eval_data)

    total_length = line_mesh_length(bm_line)
    distance = reduce_to_minimum(total_length, minimum_distance)

    correction_difference = 0
    counter = 0
    length = 0
    position = None

    # Iterate over all line mesh edges to find the positions to add the objects
    for edge in bm_line.edges:
        edge_length = edge.calc_length()
        length += edge_length

        corrected_length = length - correction_difference
        current_distance = distance * counter

        # Calculate the position on the line mesh when the distance is big enough
        if corrected_length <= total_length and corrected_length >= current_distance:
            v0 = edge.verts[0].co
            v1 = edge.verts[1].co
            vec = v1 - v0
            unit_vec = vec / edge_length

            if counter == 0:
                # Use no difference for the first position, because we only use the first vertex for this
                # and not the second vertex
                difference = 0
                vertex = v0
            else:
                difference = corrected_length - current_distance
                vertex = v1

                # Add the difference to the current length for more precise finding of further positions
                length += difference

                # Note the difference for correction of further positions
                correction_difference += difference

            # Calculate the accurate point between the two line mesh vertices
            position = vertex - unit_vec * difference
            position = m @ position

            # Define a not parallel vector to get a correct orthogonal vector
            if vec[0] != 0 or vec[2] != 0:
                a = Vector((0, 0, 1))
            else:
                a = Vector((1, 0, 0))

            # Calculate the cross product and its length to find an orthogonal vector
            cross = a.cross(vec)
            cross_length = math.sqrt(sum(i**2 for i in cross))
            orthogonal_vec = cross / cross_length

            # Shift this vector by an offset and the found position
            shifted_position = position + orthogonal_vec * offset

            # Add an object at the shifted position and rotate it
            object = add_object_at_position(object_template, shifted_position)
            rotate_object(object, position)

            counter += 1


def apply_modifiers(mesh: bpy.types.Object):
    bpy.context.view_layer.objects.active = mesh

    for modifier in mesh.modifiers:
        bpy.ops.object.modifier_apply(modifier=modifier.name)


def apply_transform(
        object: bpy.types.Object, location: bool = True, rotation: bool = True, scale: bool = True, properties: bool = True):
    object.select_set(True)
    bpy.ops.object.transform_apply(location=location, rotation=rotation, scale=scale, properties=properties)
    object.select_set(False)


def closest_curve_point(curve: bpy.types.Object, reference_point: Vector):
    # Get the curve end points in world space
    m = curve.matrix_world
    first_curve_point = curve.data.splines[0].bezier_points[0]
    last_curve_point = curve.data.splines[0].bezier_points[-1]
    first_curve_point_co = m @ first_curve_point.co
    last_curve_point_co = m @ last_curve_point.co

    point = closest_point([first_curve_point_co, last_curve_point_co], reference_point)

    return first_curve_point if point == first_curve_point_co else last_curve_point


def closest_point(points: list, reference_point: Vector):
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


def coplanar_faces(mesh: bpy.types.Object, normal: Vector, index: int, road_height: float = 0.1, threshold: float = 0.001):
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


def create_kdtree(vertices: list, size: int):
    # Create a KD-Tree to perform a spatial search
    kd = kdtree.KDTree(size)
    for i, v in enumerate(vertices):
        kd.insert(v, i)

    # Balance (build) the KD-Tree
    kd.balance()

    return kd


def curve_to_mesh(curve: bpy.types.Object):
    # Create a line mesh from the curve and link it to its collection
    mesh = curve.to_mesh()
    line_mesh = bpy.data.objects.new("Line_Mesh_" + curve.name, mesh.copy())
    line_mesh.matrix_world = curve.matrix_world
    link_to_collection(line_mesh, "Line Meshes")


def deselect_all():
    for object in bpy.context.selected_objects:
        object.select_set(False)


def edit_mesh_at_positions(mesh_name: str, positions: list):
    # Get the corresponding line mesh
    line_mesh = bpy.data.objects.get("Line_Mesh_" + mesh_name)

    # Create a BMesh from the line mesh for edge length calculation
    mesh_eval_data = line_mesh.data
    bm_line = bmesh.new()
    bm_line.from_mesh(mesh_eval_data)

    object_position = None
    for pos in positions:
        p = pos
        length = 0

        # Iterate over all line mesh edges to find its position, which corresponds to the given position
        for edge in bm_line.edges:
            edge_length = edge.calc_length()
            length += edge_length

            # Calculate the position on the line mesh when a position is reached
            if length > pos:
                v0 = edge.verts[0].co
                v1 = edge.verts[1].co
                vec = v1 - v0
                unit_vec = vec / edge_length
                object_position = v0 + unit_vec * p
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


def find_closest_points(list: list, reference_point: Vector, find_all: bool = True):
    num_vertices = len(list)
    kd = create_kdtree(list, num_vertices)
    n = num_vertices if find_all else 1
    # Sort the points by distance to the reference point and return the nearest point or all
    return kd.find_n(reference_point, n)


def intersecting_meshes(meshes: list):
    intersecting_meshes = {}

    # For each mesh, check whether it intersects with every other mesh
    for mesh in meshes:
        # Create a BMesh object from the mesh and transform it into the correct space
        bm1 = bmesh.new()
        bm1.from_mesh(mesh.data)
        bm1.transform(mesh.matrix_world)

        # Create a BVH tree for the BMesh
        mesh_BVHtree = bvhtree.BVHTree.FromBMesh(bm1)

        for other_mesh in meshes:
            # Skip each other mesh if it belongs to a crossroad and is the same mesh as the current mesh
            # or if it does not belongs to a crossroad and is in the same collection like the current mesh
            if "Crossroad" in mesh.users_collection[0].name:
                if mesh == other_mesh:
                    continue
            else:
                if mesh.users_collection == other_mesh.users_collection:
                    continue

            # Create a BMesh and a BVH tree for the other mesh
            bm2 = bmesh.new()
            bm2.from_mesh(other_mesh.data)
            bm2.transform(other_mesh.matrix_world)
            other_mesh_BVHtree = bvhtree.BVHTree.FromBMesh(bm2)

            # Get the intersecting parts (indices) between the BVH trees
            inter = mesh_BVHtree.overlap(other_mesh_BVHtree)

            # Only add the first intersected mesh only if it is not in the list
            if inter:
                if mesh not in intersecting_meshes:
                    intersecting_meshes[mesh] = []
                if other_mesh not in intersecting_meshes[mesh]:
                    intersecting_meshes[mesh].append(other_mesh)

    return intersecting_meshes


def line_mesh_length(line_mesh: bmesh):
    total_length = 0

    for edge in line_mesh.edges:
        edge_length = edge.calc_length()
        total_length += edge_length

    return total_length


def line_meshes(curve_name: str):
    left_line_mesh = bpy.data.objects.get(f"Line_Mesh_Kerb_Left_{curve_name}")
    right_line_mesh = bpy.data.objects.get(f"Line_Mesh_Kerb_Right_{curve_name}")

    return left_line_mesh, right_line_mesh


def reduce_to_minimum(length: float, minimum: float):
    # Multiply the minimum by 2 to get the next largest number
    while length > minimum * 2:
        length /= 2.0

    return length


def rotate_object(object: bpy.types.Object, reference_point: Vector):
    # Get the vector between the object and one of its children
    child = object.children[1]
    vec = child.matrix_world.to_translation() - object.location
    vec.z = 0.0

    # Get the reference vector between the object and the reference point
    reference_vec = reference_point - object.location

    # Calculate the dot product of the two vectors and their lengths
    dot_product = vec.dot(reference_vec)
    length_vec = math.sqrt(sum(a ** 2 for a in vec))
    length_reference_vector = math.sqrt(sum(a ** 2 for a in reference_vec))

    # Calculate the angle between the two vectors
    cos_theta = dot_product / (length_vec * length_reference_vector)
    angle_radian = math.acos(cos_theta)

    # Calculate the cross product of the two vectors to check whether the reference vector is clockwise to the other vector,
    # i.e. whether the angle between them is greater than 180°
    cross = vec.cross(reference_vec)

    if cross[2] < 0:
        angle_radian = 2 * math.pi - angle_radian

    # Rotate the object along the z-axis by the calculated angle
    object.rotation_euler[2] = angle_radian


def set_origin(object: bpy.types.Object, center: str = 'MEDIAN'):
    object.select_set(True)
    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center=center)
    object.select_set(False)


def separate_array_meshes(mesh: bpy.types.Object):
    bpy.context.view_layer.objects.active = mesh
    bpy.ops.object.mode_set(mode='EDIT')

    # Separate the submeshes into independent meshes
    bpy.ops.mesh.separate(type='LOOSE')
    bpy.ops.object.mode_set(mode='OBJECT')

    # Ensure that no object is selected
    deselect_all()

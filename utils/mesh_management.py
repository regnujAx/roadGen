import bmesh
import bpy
import math
import random

from mathutils import bvhtree, kdtree, Vector

from roadGen.utils.collection_management import link_to_collection, objects_from_subcollections_in_collection_by_name


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
        sign = 1 if index < 0 else -1
        y = lane_width * index - sign * mesh.dimensions[1] / 2
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
    x_dim = calculate_optimal_distance(curve_length, minimum_width)
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
    child_collection_name = None
    collection_name = object_template.name

    if "Traffic Light" in collection_name:
        # Add an 's' to the collection name to make it different to the template
        child_collection_name = collection_name + "s"
        collection_name = "Traffic Lights"
    elif "Traffic Sign" in collection_name:
        child_collection_name = collection_name + "s"
        collection_name = "Traffic Signs"
    else:
        collection_name = collection_name + "s"

    link_to_collection(object_copy, collection_name, child_collection_name)

    # Hide the copy if it is an empty object
    if object_copy.type == 'EMPTY':
        object_copy.hide_set(True)

    # Copy also the children of the object template
    for child in object_template.children:
        child_copy = child.copy()
        child_copy.parent = object_copy
        child_copy.matrix_parent_inverse = child.matrix_parent_inverse

        if "Traffic Light" in collection_name or "Traffic Sign" in collection_name:
            link_to_collection(child_copy, child_collection_name)
        else:
            link_to_collection(child_copy, collection_name)

    # Update the location of the object copy
    object_copy.location = position

    # The scene need to be updated so the locations are correct
    bpy.context.view_layer.update()

    return object_copy


def add_objects_to_curve(object_name: str, curve: bpy.types.Object, side: str, minimum_distance: float, offset: float):
    line_mesh = bpy.data.objects.get("Line_Mesh_Kerb_" + side + "_" + curve.name)
    m = line_mesh.matrix_world

    # Create a BMesh from the line mesh for edge length calculation
    mesh_eval_data = line_mesh.data
    bm_line = bmesh.new()
    bm_line.from_mesh(mesh_eval_data)

    counter = 0
    position = None
    reference_direction = None

    if "Traffic Light" in object_name:
        bm_line.edges.ensure_lookup_table()
        edge = bm_line.edges[-1] if side == "Left" else bm_line.edges[0]
        v0 = edge.verts[0].co
        v1 = edge.verts[1].co
        vec = v1 - v0

        # Calculate the accurate point between the two line mesh vertices
        vert = v1 if side == "Left" else v0
        position = m @ vert

        # Find an orthogonal vector to determine the direction for shifting/moving the object
        orthogonal_vec = orthogonal_vector(vec)

        # Adjust the position offset for traffic lights
        offset /= 4

        # Shift this orthogonal vector by an offset and the found position
        shifted_position = position + orthogonal_vec * offset
        lanes_number = curve[f"{side} Lanes"]

        object_template_name = object_name + f" {lanes_number}"
        object_template = bpy.data.objects.get(object_template_name)
        if object_template:
            # Add an object at the shifted position and rotate it
            object = add_object_at_position(object_template, shifted_position)

            if lanes_number == 1:
                reference_direction = -vec if side == "Left" else vec

            rotate_object(object, position, reference_direction)

            counter += 1
        else:
            print(f"The object with the name {object_name} cannot be found. "
                  "Check whether the object you want to add exists.")
    else:
        total_length = line_mesh_length(bm_line)
        distance = calculate_optimal_distance(total_length, minimum_distance)
        sections = round(total_length / distance)

        if "Traffic Sign" in object_name:
            traffic_signs_templates = objects_from_subcollections_in_collection_by_name("Templates", "Traffic Sign")

            # Adjust the position offset for traffic signs
            offset /= 3

            # Get a random number of traffic signs
            number = random.randint(0, int(total_length / distance))

            # Find random positions for the number of traffic signs
            if number == 0:
                positions = [random.uniform(2, total_length - 2)]
            else:
                positions = [random.uniform(2, total_length - 2) for _ in range(number)]
                positions.sort()
        else:
            # Get the template for other objects
            object_template = bpy.data.objects.get(object_name)

            # Calculate the (uniform) positions for the other objects
            positions = [distance * i for i in range(sections + 1)]

        if not positions:
            return

        correction_difference = 0
        length = 0
        reference_direction = None

        current_distance = positions.pop(0)

        # Iterate over all line mesh edges to find the positions to add the objects
        for edge in bm_line.edges:
            edge_length = edge.calc_length()
            length += edge_length

            corrected_length = length - correction_difference

            # Calculate the position on the line mesh when the distance is big enough or when the last object is reached
            # (round corrected_length and current_distance to avoid floating point issues)
            if ((corrected_length <= total_length and corrected_length >= current_distance)
                    or (counter == sections and round(corrected_length, 10) == round(current_distance, 10))):
                v0 = edge.verts[0].co
                v1 = edge.verts[1].co
                vec = v1 - v0
                vec.normalize()

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
                position = vertex - vec * difference
                position = m @ position

                # Find an orthogonal vector to determine the direction for shifting/moving the object
                orthogonal_vec = orthogonal_vector(vec)

                # Shift this orthogonal vector by an offset and the found position
                shifted_position = position + orthogonal_vec * offset

                # Select a random traffic sign template
                if "Traffic Sign" in object_name:
                    index = random.randint(0, len(traffic_signs_templates) - 1)
                    object_template = traffic_signs_templates[index]
                    reference_direction = -vec if side == "Left" else vec

                # Add an object at the shifted position and rotate it
                object = add_object_at_position(object_template, shifted_position)
                rotate_object(object, position, reference_direction)

                counter += 1

                if positions:
                    current_distance = positions.pop(0)
                else:
                    break

    name = object_name + "s" if counter > 1 else object_name
    print(f"\t{counter} {name} added")


def apply_modifiers(mesh: bpy.types.Object):
    bpy.context.view_layer.objects.active = mesh

    for modifier in mesh.modifiers:
        bpy.ops.object.modifier_apply(modifier=modifier.name)


def apply_transform(
        object: bpy.types.Object, location: bool = True, rotation: bool = True, scale: bool = True, properties: bool = True):
    object.select_set(True)
    bpy.ops.object.transform_apply(location=location, rotation=rotation, scale=scale, properties=properties)
    object.select_set(False)


def calculate_optimal_distance(length: float, minimum: float):
    number = length // minimum

    return length if number == 0 else length / number


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
        vector_2 = point - reference_point

        if vector_2.length < vector_1.length:
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


def orthogonal_vector(vector: Vector):
    # Define a not parallel vector to get a correct orthogonal vector
    if vector[0] != 0 or vector[2] != 0:
        not_parallel_vec = Vector((0, 0, 1))
    else:
        not_parallel_vec = Vector((1, 0, 0))

    # Calculate the cross product to find an orthogonal vector and normalize it
    cross = not_parallel_vec.cross(vector)
    cross.normalize()

    return cross


def rotate_object(object: bpy.types.Object, reference_point: Vector, reference_direction: Vector = None):
    furthest_child_location = None
    max_distance = 0.0
    object_location = object.matrix_world.translation

    # Rotate a the object in a different way if a reference direction is passed
    if reference_direction:
        reference_direction.normalize()

        # Find the furthest child object from the original location of the object
        for child in object.children:
            child_global_location = child.matrix_world.translation
            distance = (child_global_location - object_location).length

            if distance > max_distance:
                max_distance = distance
                furthest_child_location = child_global_location

        # Get the direction from the object to its child, shifted to the reference point (for the later angle calculation),
        # as the object has a different position than the reference point, but for the angle calculation between two vectors,
        # both must have the same starting point
        shift = reference_point - object_location
        shifted_location = furthest_child_location + shift
        direction = shifted_location - reference_point
        direction.z = 0.0
        direction.normalize()
    else:
        # Find the furthest vertex of all children and remember the corresponding child location
        for child in object.children:
            if child.type == 'MESH':
                vertices = child.data.vertices

                for vertex in vertices:
                    global_vertex_pos = child.matrix_world @ vertex.co
                    global_vertex_pos.z = 0.0

                    distance = (global_vertex_pos - object_location).length
                    if distance > max_distance:
                        max_distance = distance
                        furthest_child_location = child.matrix_world.translation

        # Get the direction from the object to this furthest child
        direction = furthest_child_location - object_location
        direction.z = 0.0
        direction.normalize()

        # Get the reference vector between the object and the reference point
        reference_direction = reference_point - object_location
        reference_direction.normalize()

    # Calculate the dot product of the two vectors and their lengths
    dot_product = direction.dot(reference_direction)

    # Calculate the angle between the two vectors
    angle_radian = math.acos(dot_product)

    # Calculate the cross product of the two vectors to check whether the angle between them (in radians)
    # is positive (counter-clockwise) or negative (clockwise)
    cross = direction.cross(reference_direction)

    # If the z-coordinate of the cross is negative, we need switch the rotation direction to get the correct angle
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

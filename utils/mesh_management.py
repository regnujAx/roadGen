import bmesh
import bpy
import math
import random

from mathutils import bvhtree, kdtree, Vector

from roadGen.road import RG_Road
from roadGen.utils.collection_management import get_objects_from_subcollections_in_collection_by_name, link_to_collection
from roadGen.utils.curve_management import get_closest_curve_point, get_closest_point


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


def add_mesh_to_curve(mesh_template: bpy.types.Object, curve: bpy.types.Object, name: str, index: int, offset: float = 0.0):
    collection_name = "Kerbs"
    child_collection_name = None
    mesh = mesh_template.copy()
    mesh.data = mesh_template.data.copy()
    mesh.name = name
    mesh.location = curve.location

    x, y, z = 0.0, 0.0, 0.0

    if "Kerb" in name:
        # Keep its original z-location for the kerb
        z = mesh.location[2]
    elif "Sidewalk" in name:
        collection_name = "Sidewalks"

        # Add for every sidewalk a new collection for separated meshes
        child_collection_name = mesh.name

    # Translate the created mesh according to its y-dimension and an offset
    y += index * (mesh.dimensions[1] / 2 + offset)
    mesh.location += Vector((x, y, z))

    # Calculate and update the x-dimension of the mesh so it fits better to its curve
    # (add a threshold to also take the last part into account)
    curve_length = curve.data.splines[0].calc_length()
    minimum_width = 2.0
    threshold = 0.001
    mesh.dimensions[0] = calculate_optimal_distance(curve_length, minimum_width) + threshold

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

    # It is necessary to check the individual collections,
    # as some object templates have an index as a suffix to distinguish between the different versions
    if "Traffic Light" in collection_name:
        # Add an 's' to the collection name to make it different to the template
        child_collection_name = collection_name + "s"
        collection_name = "Traffic Lights"
    elif "Traffic Sign" in collection_name:
        child_collection_name = collection_name + "s"
        collection_name = "Traffic Signs"
    elif "Street Name Sign" in collection_name:
        child_collection_name = collection_name + "s"
        collection_name = "Street Name Signs"
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

        if "Traffic Light" in collection_name or "Traffic Sign" in collection_name or "Street Name Sign" in collection_name:
            link_to_collection(child_copy, child_collection_name)
        else:
            link_to_collection(child_copy, collection_name)

    # Update the location of the object copy
    object_copy.location = position

    # The scene need to be updated so the locations are correct
    bpy.context.view_layer.update()

    return object_copy


def add_objects_to_road(object_name: str, road: RG_Road, side: str, offset: float, height: float):
    curve_name = road.curve.name
    line_mesh = bpy.data.objects.get(f"Line_Mesh_{curve_name}_{side}")

    # Create a BMesh from the line mesh for edge length calculation
    mesh_eval_data = line_mesh.data
    bm_line = bmesh.new()
    bm_line.from_mesh(mesh_eval_data)
    total_length = line_mesh_length(bm_line)

    counter = 0
    direction = None
    position = None
    reference_direction = None
    use_reference_direction = False

    distance = calculate_optimal_distance(total_length, road.lamp_distance)
    sections = round(total_length / distance)

    if "Traffic Sign" in object_name:
        traffic_sign_templates = get_objects_from_subcollections_in_collection_by_name("Templates", "Traffic Sign")

        use_reference_direction = True

        # Get a random number of traffic signs
        number = random.randint(0, int(total_length / distance))

        # Find random positions for the number of traffic signs
        if number == 0:
            positions = [random.uniform(2, total_length - 2)]
        else:
            positions = [random.uniform(2, total_length - 2) for _ in range(number)]
            positions.sort()

        # Adjust the position offset for the traffic sign
        offset /= 3
    elif "Traffic Light" in object_name:
        # Check for turning lane and add an additional road lane if there is one
        lanes_number = road.curve.get(f"{side} Lanes")
        turning_lane_distance = road.left_turning_lane_distance if side == "Left" else road.right_turning_lane_distance
        has_turning_lane = road.has_left_turning_lane if side == "Left" else road.has_right_turning_lane

        if turning_lane_distance and has_turning_lane:
            lanes_number += 1

        object_template = bpy.data.objects.get(f"{object_name} {lanes_number}")

        # If there is only one lane per side use a reference vector to rotate the corresponding mesh correctly
        if lanes_number == 1:
            use_reference_direction = True

        positions = [1.0]

        # Adjust the position offset for the traffic light
        offset /= 4
    elif "Street Name Sign" in object_name:
        if road.right_neighbour_curve and side == "Right":
            # Set the direction to the negative y-axis, as we know that the street name sign template has this direction
            # (the calculation with its children locations leads to incorrect results)
            direction = Vector((0.0, -1.0, 0.0))

            # Get the correct template and crossroad curve
            roads_number = 2 if road.right_neighbour_curve else 1
            object_template = bpy.data.objects.get(f"{object_name} {roads_number}")
            crossroad_curve = bpy.data.objects.get(f"Crossroad_Curve_{curve_name}_{road.right_neighbour_curve.name}")

            # Get the correct right curve (left and right could be swapped because it depends on the point of view)
            curve = road.get_right_curve()
            curve_point = get_closest_curve_point(curve, crossroad_curve.matrix_world.translation)

            # Calculate the reference direction (the direction in which the sign should be rotated)
            m = curve.matrix_world
            reference_direction = m @ curve_point.co - m @ curve_point.handle_left

            # Get the corresponding line mesh
            line_mesh = bpy.data.objects.get(f"Line_Mesh_{crossroad_curve.name}")

            # Create a BMesh from the line mesh for edge length calculation
            mesh_eval_data = line_mesh.data
            bm_line = bmesh.new()
            bm_line.from_mesh(mesh_eval_data)
            total_length = line_mesh_length(bm_line)

            # Set the mid of the line mesh as the position for the sign
            positions = [total_length / 2]

            # Adjust the position offset for the street name sign
            offset *= -1
        else:
            return
    else:
        # Get the template for other objects
        object_template = bpy.data.objects.get(object_name)

        # Calculate the (uniform) positions for the other objects
        positions = [distance * i for i in range(sections + 1)]

    if not positions:
        return

    correction_difference = 0
    length = 0

    current_distance = positions.pop(0)
    m = line_mesh.matrix_world

    # Iterate over all line mesh edges to find the mesh positions to add the objects
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
            position = m @ (vertex - vec * difference)

            # Find an orthogonal vector to determine the direction for shifting/moving the object
            orthogonal_vector = Vector((-vec.y, vec.x, 0))

            # Shift this orthogonal vector by an offset and the found position
            shifted_position = position + orthogonal_vector * offset

            # Select a random traffic sign template
            if "Traffic Sign" in object_name:
                index = random.randint(0, len(traffic_sign_templates) - 1)
                object_template = traffic_sign_templates[index]

            if use_reference_direction:
                reference_direction = vec

            # Add an object at the shifted position and rotate it
            object = add_object_at_position(object_template, shifted_position)
            rotate_object(object, position, direction, reference_direction)

            # Set the height correctly
            if object.location.z == 0.0:
                object.location.z = height

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


def create_kdtree(vertices: list, size: int):
    # Create a KD-Tree to perform a spatial search
    kd = kdtree.KDTree(size)
    for i, v in enumerate(vertices):
        kd.insert(v, i)

    # Balance (build) the KD-Tree
    kd.balance()

    return kd


def create_mesh_from_vertices(vertices: list, category_name: str, suffix: str, height: float):
    # Create the face (only one) based on the vertices for the mesh
    face = []
    faces = []
    for index in range(len(vertices)):
        face.append(index)
    faces.append(face)

    # Create the 2D mesh and link it to its corresponding collection
    mesh = bpy.data.meshes.new(f"{category_name} Mesh")
    mesh.from_pydata(vertices, [], faces)
    new_category_name = category_name.replace(" ", "_")
    obj = bpy.data.objects.new(f"{new_category_name}_{suffix}", mesh)
    link_to_collection(obj, f"{category_name}s")

    # Extrude the 2D mesh so it is a 3D mesh
    extrude_mesh(obj, height)

    # Set the origin to the center of the mesh (Hint: This overwrites the location.)
    set_origin(obj, 'BOUNDS')

    return obj


def curve_to_mesh(curve: bpy.types.Object):
    # Create a line mesh from the curve and link it to its collection
    mesh = curve.to_mesh()
    line_mesh = bpy.data.objects.new(f"Line_Mesh_{curve.name}", mesh.copy())
    line_mesh.matrix_world = curve.matrix_world
    link_to_collection(line_mesh, "Line Meshes")

    return line_mesh


def deselect_all():
    for object in bpy.context.selected_objects:
        object.select_set(False)


def edit_mesh_at_positions(mesh_name: str, positions: list, reference_mesh_name: str):
    # Get the corresponding line mesh
    line_mesh = bpy.data.objects.get(f"Line_Mesh_{reference_mesh_name}")

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


def extrude_mesh(mesh: bpy.types.Object, height: float):
    # Edit the mesh
    bpy.context.view_layer.objects.active = mesh
    bpy.ops.object.mode_set(mode='EDIT')

    # Extrude the mesh
    bpy.ops.mesh.extrude_region_move(TRANSFORM_OT_translate={"value": (0.0, 0.0, height)})
    bpy.ops.object.mode_set(mode='OBJECT')


def find_closest_points(list: list, reference_point: Vector, find_all: bool = True):
    num_vertices = len(list)
    kd = create_kdtree(list, num_vertices)
    n = num_vertices if find_all else 1

    # Sort the points by distance to the reference point and return the nearest point or all
    return kd.find_n(reference_point, n)


def get_furthest_child_location(object: bpy.types.Object, by_vertex: bool):
    furthest_child_location = None
    max_distance = 0.0
    object_location = object.matrix_world.translation

    # Find the furthest child from the original location of the object
    for child in object.children:
        if child.type == 'MESH':
            child_global_location = child.matrix_world.translation

            # If necessary, iterate over all vertices of the child
            if by_vertex:
                vertices = child.data.vertices
                list = []

                for vertex in vertices:
                    global_vertex_pos = child.matrix_world @ vertex.co
                    global_vertex_pos.z = 0.0
                    list.append(global_vertex_pos)
            else:
                list = [child_global_location]

            for element in list:
                distance = (element - object_location).length

                if distance > max_distance:
                    max_distance = distance
                    furthest_child_location = child_global_location

    return furthest_child_location


def get_intersecting_meshes(meshes: list):
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


def rotate_object(
        object: bpy.types.Object, reference_point: Vector, direction: Vector = None, reference_direction: Vector = None):
    furthest_child_location = None
    object_location = object.matrix_world.translation
    by_vertex = False if reference_direction else True

    if not direction:
        # If no direction is passed, calculate it with the furthest child of the object
        furthest_child_location = get_furthest_child_location(object, by_vertex)
        direction = furthest_child_location - object_location

    direction.z = 0.0
    direction.normalize()

    if not reference_direction:
        # If no reference direction is passed, get the reference vector between the object and the reference point
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

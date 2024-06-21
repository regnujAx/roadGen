import bpy
import mathutils

from ..util import (
    find_closest_points,
    get_coplanar_faces,
    get_closest_point,
    get_objects_from_collection,
    link_to_collection,
    set_origin)


class CG_CrossroadGenerator:
    def __init__(self):
        self.crossing_points = get_crossing_points()

    def add_crossroads(self):
        for crossing_point in self.crossing_points:
            curves_number = int(crossing_point["Number of Curves"])

            curves = get_curves(crossing_point, curves_number)
            add_crossroad(curves, crossing_point)


def get_curves(crossing_point: bpy.types.Object, curves_number: int):
    curves = []
    for i in range(curves_number):
        curve_name = crossing_point[f"Curve {i+1}"]
        if curve_name:
            curve = bpy.data.objects[curve_name]
            curves.append(curve)

    return curves


def add_crossroad(curves: list, crossing_point: bpy.types.Object, height: float = 0.1):
    vertices = []
    vertices_to_remove = []
    for curve in curves:
        # Cast a ray from the crossing point to find the correct face and vertices of the curve
        bottom_vertices = get_outer_bottom_vertices(curve, crossing_point)
        # Add the outer bottom vertices to a list for every curve
        vertices_to_remove.extend(bottom_vertices)

    number_of_vertices = len(vertices_to_remove)
    # Mark one point as reference for distance calculation
    reference_point = crossing_point.location
    # Iterate over all vertices and collect the vertices in the correct order for the crossroad plane
    for i in range(number_of_vertices):
        if i < number_of_vertices - 1:
            vertex_0 = vertices_to_remove[0]
            vertex_1 = vertices_to_remove[1]
            # Get the closest vertex with respect to the reference point
            vertex = get_closest_point(vertex_0, vertex_1, reference_point)
            # Remove the closest vertex from the list
            vertex_to_remove = vertex_0 if vertex == vertex_0 else vertex_1
            # Set the current point as reference_point for the next iteration (to find the closest point)
            reference_point = vertex
        else:
            # Use the remaining vertex and then remove it
            vertex = vertices_to_remove[0]
            vertex_to_remove = vertex

        vertices_to_remove.remove(vertex_to_remove)
        vertex_vec = mathutils.Vector((vertex.x, vertex.y, 0.0))
        vertices.append(vertex_vec)

    # Create the face (only one) based on the vertices for the crossroad plane
    # (Assumption: All vertices are in the correct order.)
    faces = []
    face = []
    for index in range(len(vertices)):
        face.append(index)
    faces.append(face)

    # Create the crossroad plane and link it to its corresponding collection
    mesh = bpy.data.meshes.new("Crossroad Mesh")
    mesh.from_pydata(vertices, [], faces)
    crossroad_name = "Crossroad_" + crossing_point.name
    crossroad = bpy.data.objects.new(crossroad_name, mesh)
    link_to_collection(crossroad, "Crossroads")

    # Edit the crossroad plane
    bpy.context.view_layer.objects.active = crossroad
    bpy.ops.object.mode_set(mode='EDIT')

    # Extrude the crossroad plane so it is a 3D mesh
    bpy.ops.mesh.extrude_region_move(TRANSFORM_OT_translate={"value": (0.0, 0.0, height)})
    bpy.ops.object.mode_set(mode='OBJECT')

    # Set the origin to the center of the mesh (Hint: This overwrites the location.)
    set_origin(crossroad)


def calculate_ray_cast(curve_road_lane: bpy.types.Object, ray_begin: mathutils.Vector, ray_end: mathutils.Vector):
    # Translate the begin and the end of the ray into local space of the road lane
    location = curve_road_lane.location
    origin = ray_begin - location
    destination = ray_end - location

    # Calculate the direction for the ray cast and set its z-coordinate to 0.0 to make it easier to find the correct face
    direction = destination - origin
    direction.z = 0.0

    # Return the result of the ray cast
    return curve_road_lane.ray_cast(origin, direction)


def get_closest_curve_point(curve: bpy.types.Object, reference_point: mathutils.Vector):
    # Get the curve end points in world space
    m = curve.matrix_world
    first_curve_point = m @ curve.data.splines[0].bezier_points[0].co
    end_curve_point = m @ curve.data.splines[0].bezier_points[-1].co
    return get_closest_point(first_curve_point, end_curve_point, reference_point)


def get_crossing_points():
    return get_objects_from_collection("Nodes")


def get_outer_bottom_vertices(curve: bpy.types.Object, crossing_point: bpy.types.Object):
    # Take the crossing point as the begin for the ray cast
    ray_begin = crossing_point.location

    # Figure out the correct curve point and use it as the begin of the ray
    ray_end = get_closest_curve_point(curve, ray_begin)

    # Determine the road lane meshes corresponding to the curve
    road_lanes = get_objects_from_collection("Road Lanes")
    # ToDo: `endswith()` and `in` are not optimal for multiple road lanes per side and are linked to specific name conventions
    # `in` presupposes that the name of the first curve is indexed (i.e. BezierCurve.000 instead of BezierCurve)
    curve_road_lanes = [road_lane for road_lane in road_lanes if curve.name in road_lane.name]
    # curve_road_lanes = [road_lane for road_lane in road_lanes if road_lane.name.endswith(curve.name)]

    outer_bottom_vertices = []
    hit_objects = []
    locations = []
    normals = []
    indices = []

    # Iterate over all road lanes of the curve
    for curve_road_lane in curve_road_lanes:
        hit, location, normal, index = calculate_ray_cast(curve_road_lane, ray_begin, ray_end)
        if hit:
            # The ray cast can hit multiple road lanes so all should be saved
            hit_objects.append(curve_road_lane)
            locations.append(location + curve_road_lane.location)
            normals.append(normal)
            indices.append(index)

    # Remove all "wrong" hit locations and normals (i.e. keep only the nearest to the crossing point/begin of the ray)
    i = 0
    while len(locations) > 1:
        location_0 = locations[i]
        location_1 = locations[i+1]
        nearest_location = get_closest_point(location_0, location_1, ray_begin)
        index_to_remove = 0 if nearest_location == location_1 else 1

        # Delete unnecessary information
        del hit_objects[index_to_remove]
        del locations[index_to_remove]
        del normals[index_to_remove]
        del indices[index_to_remove]

    z_threshold = 0.001
    # Use the remaining hit object and normal to find the coplanar faces of the face with the remaining index
    hit_object = hit_objects[0]
    normal = normals[0]

    for curve_road_lane in curve_road_lanes:
        # Use the remaining index as reference for finding the coplanar faces
        index = indices[0]
        vertices = []

        # Overwrite the index if the current road lane does not match the hit object
        if curve_road_lane != hit_object:
            faces_centers = [face.center for face in curve_road_lane.data.polygons]
            closest_face = find_closest_points(faces_centers, ray_end - curve_road_lane.location, False)[0]
            index = faces_centers.index(closest_face[0])

        faces = get_coplanar_faces(curve_road_lane, normal, index)

        for face in faces:
            # Iterate over all edges of each coplanar face but consider only vertical edges and collect their bottom vertices
            for (index_0, index_1) in face.edge_keys:
                vertex_0 = curve_road_lane.data.vertices[index_0].co
                vertex_1 = curve_road_lane.data.vertices[index_1].co
                delta_z = abs(vertex_0.z - vertex_1.z)

                if delta_z <= z_threshold:
                    if vertex_0 not in vertices and vertex_0.z <= z_threshold:
                        vertices.append(vertex_0)
                    if vertex_1 not in vertices and vertex_1.z <= z_threshold:
                        vertices.append(vertex_1)

        location = curve_road_lane.location
        # Keep only the closest vertices to the end of the ray of the bottom vertices
        closest_vertices = find_closest_points(vertices, ray_end - location)

        # Append only the furthest vertex (in global space) to the return list
        outer_bottom_vertices.append(closest_vertices[-1][0] + location)

    return outer_bottom_vertices

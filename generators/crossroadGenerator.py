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


def calculate_ray_cast(origin: mathutils.Vector, closest_curve_point: mathutils.Vector):
    # Calculate the direction for the ray cast and set its z-coordinat to 0.0 to make it easier to find the correct face
    direction = closest_curve_point - origin
    direction.z = 0.0

    depsgraph = bpy.context.view_layer.depsgraph
    # Return only the normal of the hit face (i.e. the third element of the tuple)
    return bpy.context.scene.ray_cast(depsgraph, origin, direction)[2]


def get_closest_curve_point(curve: bpy.types.Object, reference_point: mathutils.Vector):
    first_curve_point = curve.data.splines[0].bezier_points[0].co
    end_curve_point = curve.data.splines[0].bezier_points[-1].co
    return get_closest_point(first_curve_point, end_curve_point, reference_point)


def get_crossing_points():
    return get_objects_from_collection("Nodes")


def get_outer_bottom_vertices(curve: bpy.types.Object, crossing_point):
    # Take the crossing point as the origin for the ray cast
    origin = crossing_point.location.xyz

    # Figure out the correct curve point
    closest_curve_point = get_closest_curve_point(curve, origin)

    # Determine the normal of the hit face when casting a ray from the origin to the correct curve point
    normal = calculate_ray_cast(origin, closest_curve_point)

    # Determine the road lane meshes corresponding to the curve
    road_lanes = get_objects_from_collection("Road Lanes")
    # ToDo: endswith() is not optimal for multiple road lanes per side
    curve_road_lanes = [road_lane for road_lane in road_lanes if road_lane.name.endswith(curve.name)]

    z_threshold = 0.0001
    bottom_vertices = []

    # Iterate over all road lanes of the curve
    for curve_road_lane in curve_road_lanes:
        vertices = []
        faces = get_coplanar_faces(curve_road_lane, normal)

        for face in faces:
            # Iterate over all edges of each coplanar face and collect the bottom vertices
            for (index_0, index_1) in face.edge_keys:
                vertex_0 = curve_road_lane.data.vertices[index_0].co
                vertex_1 = curve_road_lane.data.vertices[index_1].co
                delta_z = abs(vertex_0.z - vertex_1.z)

                if delta_z <= z_threshold:
                    if vertex_0 not in vertices and vertex_0.z <= 0.001:
                        vertices.append(vertex_0)
                    if vertex_1 not in vertices and vertex_1.z <= 0.001:
                        vertices.append(vertex_1)

        vertices = find_closest_points(vertices, closest_curve_point)

        # Append only the furthest vertex
        bottom_vertices.append(vertices[-1][0])

    return bottom_vertices

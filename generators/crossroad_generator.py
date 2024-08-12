import bpy
import math
import mathutils

from .geometry_generator import RG_GeometryGenerator
from .kerb_generator import RG_KerbGenerator
from .sidewalk_generator import RG_SidewalkGenerator
from ..utils.collection_management import objects_from_collection
from ..utils.mesh_management import (
    closest_point,
    coplanar_faces,
    find_closest_points,
    link_to_collection,
    set_origin)


class RG_CrossroadGenerator(RG_GeometryGenerator):
    def __init__(self, kerb_generator: RG_KerbGenerator, sidewalk_generator: RG_SidewalkGenerator):
        self.sidewalk_generator = sidewalk_generator
        self.kerb_generator = kerb_generator
        self.crossroads = []

    def add_geometry(self, crossing_point: bpy.types.Object):
        curves_number = int(crossing_point["Number of Curves"])

        if curves_number > 1:
            curves = crossing_curves(crossing_point, curves_number)
            crossroad = add_crossroad(curves, crossing_point, self.kerb_generator, self.sidewalk_generator)
            self.crossroads.append(crossroad)


# ------------------------------------------------------------------------
#    Helper Methods
# ------------------------------------------------------------------------


def add_crossroad(
        curves: list, crossing_point: bpy.types.Object,
        kerb_generator: RG_KerbGenerator, sidewalk_generator: RG_SidewalkGenerator, height: float = 0.1):
    road_vertices = {}
    vertices_to_remove = []

    # Mark one point as a reference for sorting the vertices
    reference_point = crossing_point.location

    for curve in curves:
        # Get the outer bottom vertices of the road lanes of a curve by casting a ray from the crossing point towards the curve
        bottom_vertices = outer_bottom_vertices(curve, crossing_point)

        # Sort the vertices (clockwise) with respect to the reference point
        vertex = closest_point([bottom_vertices[0], bottom_vertices[1]], reference_point)
        other_vertex = bottom_vertices[0] if vertex == bottom_vertices[1] else bottom_vertices[1]
        verts = [vertex, other_vertex]

        # Add the ordered vertices and its curve to the dictionary
        road_vertices[curve.name] = verts

        # Add the ordered vertices to a list to work through them one after the other
        vertices_to_remove.extend(verts)

        # Update the reference point
        reference_point = other_vertex

    # Check whether the first two vertices are in the correct order; if not, swap them
    vertex = closest_point([vertices_to_remove[0], vertices_to_remove[1]], vertices_to_remove[2])
    if vertex != vertices_to_remove[1]:
        v = vertices_to_remove[1]
        vertices_to_remove[1] = vertices_to_remove[0]
        vertices_to_remove[0] = v
        # Also update the dictionary
        road_vertices[0] = [vertices_to_remove[0], vertices_to_remove[1]]

    vertices = []
    first_vertex = None
    number_of_vertices = len(vertices_to_remove)

    # Convert the dictionary keys and values into lists
    curves_list = list(road_vertices.keys())
    vertices_list = [v for value in road_vertices.values() for v in value]

    # Iterate over all vertices and collect the vertices for the crossroad plane
    # Assumption: All vertices are in the correct order
    for i in range(number_of_vertices):
        vertex_0 = vertices_to_remove[0]

        # Remember the first vertex in order to connect the remaining (last) vertex to it
        if i == 0:
            first_vertex = vertex_0

        if i < number_of_vertices - 1:
            vertex_1 = vertices_to_remove[1]
        else:
            vertex_1 = first_vertex

        # Get the correct curves depending on the current vertices
        position_0 = int(vertices_list.index(vertex_0) / 2)
        position_1 = int(vertices_list.index(vertex_1) / 2)
        curve_0 = curves_list[position_0]
        curve_1 = curves_list[position_1]

        if curve_0 != curve_1:
            # Add a kerb between two different curves
            add_crossroad_kerb([curve_0, curve_1], [vertex_0, vertex_1], crossing_point.location, kerb_generator)

            # Add a sidewalk between two different curves
            crossroad_curve = bpy.data.objects.get(f"Crossroad_Curve_{curve_0}_{curve_1}")
            if crossroad_curve:
                sidewalk_generator.add_geometry(curve=crossroad_curve)

            # Add all vertices of the created line mesh to the crossroad vertices
            line_mesh = bpy.data.objects.get(f"Line_Mesh_Crossroad_Curve_{curve_0}_{curve_1}")
            for vertex in line_mesh.data.vertices:
                vertex_vec = mathutils.Vector((vertex.co.x, vertex.co.y, 0.0))
                vertices.append(vertex_vec)
        else:
            vertex_vec = mathutils.Vector((vertex_0.x, vertex_0.y, 0.0))
            vertices.append(vertex_vec)

        # Remove the closest vertex from the list
        vertex_to_remove = vertex_0
        vertices_to_remove.remove(vertex_to_remove)

    # Create the face (only one) based on the vertices for the crossroad plane
    face = []
    faces = []
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
    set_origin(crossroad, 'BOUNDS')
    # set_origin(crossroad, crossing_point.location)

    return crossroad


def add_crossroad_kerb(curve_names: list, points: list, crossing_point: mathutils.Vector, kerb_generator: RG_KerbGenerator):
    direction_unit_vectors = []
    for curve_name in curve_names:
        road_curve = bpy.data.objects.get(curve_name)
        curve_point = closest_curve_point(road_curve, crossing_point)

        # Find the closest handle of the curve point with respect to the crossing point
        left_handle = curve_point.handle_left + road_curve.location
        right_handle = curve_point.handle_right + road_curve.location
        closest_handle = closest_point([left_handle, right_handle], crossing_point)

        # Calculate the direction of the curve point and its handle as unit vector
        # for later calculation of the start/end point of the crossroad curve
        direction = closest_handle - (curve_point.co + road_curve.location)
        length = math.sqrt(sum(i**2 for i in direction))
        unit_vec = direction / length

        # Append the unit vector to the list
        direction_unit_vectors.append(unit_vec)

    # Create a new curve and change its curve type to 3D and increase its resolution
    crv = bpy.data.curves.new("curve", 'CURVE')
    crv.dimensions = "3D"
    crv.resolution_u = 32

    # Create a new spline for the new created curve
    spline = crv.splines.new(type='BEZIER')

    # Add one spline bezier point for each point (there is already one point by default so one additional is sufficient)
    spline.bezier_points.add(1)

    # Set the coordinates of the spline bezier points to the passed points
    for bezier_point, point in zip(spline.bezier_points, points):
        bezier_point.co = point

    # Calculate the distance between the kerb points
    vector = points[1] - points[0]
    distance = math.sqrt(sum(i**2 for i in vector))

    for i in range(len(spline.bezier_points)):
        # Use the calculated distance to obtain an offset dependent on the kerbs in direction of its road curve
        # and add it to the point
        new_co = points[i] + distance / 2 * direction_unit_vectors[i]
        # Set both bezier point handles to the new coordinate
        crv.splines[0].bezier_points[i].handle_left = new_co
        crv.splines[0].bezier_points[i].handle_right = new_co

    # Create a new object based on the curve and link it to its collection
    curve = bpy.data.objects.new(f"Crossroad_Curve_{curve_names[0]}_{curve_names[1]}", crv)
    link_to_collection(curve, "Crossroad Curves")

    # Create a line mesh from the curve (needed for crossroad plane) and link it to its collection
    mesh = curve.to_mesh()
    line_mesh = bpy.data.objects.new("Line_Mesh_" + curve.name, mesh.copy())
    line_mesh.matrix_world = curve.matrix_world
    link_to_collection(line_mesh, "Line Meshes")

    # Add a kerb to the curve
    kerb_generator.add_geometry(curve=curve)


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


def closest_curve_point(curve: bpy.types.Object, reference_point: mathutils.Vector):
    # Get the curve end points in world space
    m = curve.matrix_world
    first_curve_point = curve.data.splines[0].bezier_points[0]
    last_curve_point = curve.data.splines[0].bezier_points[-1]
    first_curve_point_co = m @ first_curve_point.co
    last_curve_point_co = m @ last_curve_point.co

    point = closest_point([first_curve_point_co, last_curve_point_co], reference_point)

    return first_curve_point if point == first_curve_point_co else last_curve_point


def crossing_curves(crossing_point: bpy.types.Object, curves_number: int):
    curves = []
    for i in range(curves_number):
        curve_name = crossing_point[f"Curve {i+1}"]

        if curve_name:
            curve = bpy.data.objects.get(curve_name)
            curves.append(curve)

    return curves


def outer_bottom_vertices(curve: bpy.types.Object, crossing_point: bpy.types.Object):
    # Take the crossing point as the begin for the ray cast
    ray_begin = crossing_point.location
    # Set the height a little bit higher to guarantee a hit
    ray_begin.z = 0.05

    # Figure out the correct curve point and use it as the begin of the ray
    curve_point = closest_curve_point(curve, ray_begin)
    ray_end = curve.matrix_world @ curve_point.co

    # Determine the road lane meshes corresponding to the curve
    road_lanes = objects_from_collection("Road Lanes")
    # `in` presupposes that the name of the first curve is indexed (i.e. BezierCurve.000 instead of BezierCurve)
    curve_road_lanes = [road_lane for road_lane in road_lanes if curve.name in road_lane.name]

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
        nearest_location = closest_point([location_0, location_1], ray_begin)
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

    # Handle each road side separately (if there are multiple road lanes on each side)
    for side in ["Left", "Right"]:
        side_road_lanes = [road_lane for road_lane in curve_road_lanes if side in road_lane.name]
        vertices = []

        for side_road_lane in side_road_lanes:
            # Use the remaining index as reference for finding the coplanar faces
            index = indices[0]

            # Overwrite the index if the current road lane does not match the hit object
            if side_road_lane != hit_object:
                faces_centers = [face.center for face in side_road_lane.data.polygons]
                closest_face = find_closest_points(faces_centers, ray_end - side_road_lane.location, False)[0]
                index = faces_centers.index(closest_face[0])

            faces = coplanar_faces(side_road_lane, normal, index)

            for face in faces:
                # Iterate over all edges of each coplanar face but consider only vertical edges
                # and collect their bottom vertices
                for (index_0, index_1) in face.edge_keys:
                    vertex_0 = side_road_lane.data.vertices[index_0].co
                    vertex_1 = side_road_lane.data.vertices[index_1].co
                    delta_z = abs(vertex_0.z - vertex_1.z)

                    if delta_z <= z_threshold:
                        if vertex_0 not in vertices and vertex_0.z <= z_threshold:
                            vertices.append(vertex_0)
                        if vertex_1 not in vertices and vertex_1.z <= z_threshold:
                            vertices.append(vertex_1)

        location = side_road_lane.location
        # Keep only the closest vertices to the end of the ray of the bottom vertices
        closest_vertices = find_closest_points(vertices, ray_end - location)

        # Append only the furthest vertex (in global space) to the return list
        outer_bottom_vertices.append(closest_vertices[-1][0] + location)

    return outer_bottom_vertices

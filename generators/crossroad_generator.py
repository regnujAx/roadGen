import bpy

from mathutils import Vector

from roadGen.generators.geometry_generator import RG_GeometryGenerator
from roadGen.utils.collection_management import objects_from_collection
from roadGen.utils.mesh_management import (
    closest_curve_point,
    closest_point,
    curve_to_mesh,
    extrude_mesh,
    link_to_collection,
    set_origin)


class RG_CrossroadGenerator(RG_GeometryGenerator):
    def __init__(self):
        self.crossroads = []

    def add_geometry(self, curves: list, crossroad_point: bpy.types.Object):
        crossroad = add_crossroad(curves, crossroad_point)
        self.crossroads.append(crossroad)


# ------------------------------------------------------------------------
#    Helper Methods
# ------------------------------------------------------------------------


def add_crossroad(curves: list, crossroad_point: bpy.types.Object, height: float = 0.1):
    road_vertices = {}
    vertices_to_remove = []

    # Mark one point as a reference for sorting the vertices
    reference_point = crossroad_point.location

    for curve in curves:
        # Get the outer vertices of the side curves of a curve
        curve_left = bpy.data.objects.get(f"{curve.name}_Left")
        curve_right = bpy.data.objects.get(f"{curve.name}_Right")
        point_left_co = closest_curve_point(curve_left, reference_point, True)
        point_right_co = closest_curve_point(curve_right, reference_point, True)
        outer_vertices = [point_left_co, point_right_co]

        # Sort the vertices (clockwise) with respect to the reference point
        vertex = closest_point([outer_vertices[0], outer_vertices[1]], reference_point)
        other_vertex = outer_vertices[0] if vertex == outer_vertices[1] else outer_vertices[1]
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
            # Add a curve between two different curves
            add_crossroad_curve([curve_0, curve_1], [vertex_0, vertex_1], crossroad_point.location)

            # Add all vertices of the created line mesh to the crossroad vertices
            line_mesh = bpy.data.objects.get(f"Line_Mesh_Crossroad_Curve_{curve_0}_{curve_1}")
            for vertex in line_mesh.data.vertices:
                vertex_vec = Vector((vertex.co.x, vertex.co.y, 0.0))
                vertices.append(vertex_vec)
        else:
            vertex_vec = Vector((vertex_0.x, vertex_0.y, 0.0))
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
    crossroad = bpy.data.objects.new(f"Crossroad_{crossroad_point.name}", mesh)
    link_to_collection(crossroad, "Crossroads")

    # Extrude the crossroad plane so it is a 3D mesh
    extrude_mesh(crossroad, height)

    # Set the origin to the center of the mesh (Hint: This overwrites the location.)
    set_origin(crossroad, 'BOUNDS')

    return crossroad


def add_crossroad_curve(curve_names: list, points: list, crossroad_point: Vector):
    direction_unit_vectors = []
    for curve_name in curve_names:
        road_curve = bpy.data.objects.get(curve_name)
        curve_point = closest_curve_point(road_curve, crossroad_point)

        # Find the closest handle of the curve point with respect to the crossing point
        left_handle = curve_point.handle_left + road_curve.location
        right_handle = curve_point.handle_right + road_curve.location
        closest_handle = closest_point([left_handle, right_handle], crossroad_point)

        # Calculate the direction of the curve point and its handle as unit vector
        # for later calculation of the start/end point of the crossroad curve
        direction = closest_handle - (curve_point.co + road_curve.location)
        direction.normalize()

        # Append the normalized direction vector to the list
        direction_unit_vectors.append(direction)

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

    for i in range(len(spline.bezier_points)):
        # Use the vector length to obtain an offset dependent on the kerbs in direction of its road curve
        # and add it to the point
        new_co = points[i] + vector.length / 2 * direction_unit_vectors[i]
        # Set both bezier point handles to the new coordinate
        crv.splines[0].bezier_points[i].handle_left = new_co
        crv.splines[0].bezier_points[i].handle_right = new_co

    # Create a new object based on the curve and link it to its collection
    curve = bpy.data.objects.new(f"Crossroad_Curve_{curve_names[0]}_{curve_names[1]}", crv)
    link_to_collection(curve, "Crossroad Curves")

    # Create a line mesh from the curve (needed for crossroad plane) and link it to its collection
    curve_to_mesh(curve)


def crossing_curves(crossroad_point: bpy.types.Object, crossroad: bool = False):
    curves = []
    curves_number = crossroad_point.get("Number of Curves")

    if curves_number:
        curves_number = int(curves_number)

        if curves_number > 1:
            for i in range(curves_number):
                if crossroad:
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


def crossing_points():
    markers = objects_from_collection("Crossing Points")
    return [marker for marker in markers if marker.visible_get()]

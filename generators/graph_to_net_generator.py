import bpy
import bmesh
import math

from mathutils import Vector

from roadGen.utils.curve_management import sort_curves
from roadGen.utils.mesh_management import set_origin


class RG_GraphToNetGenerator:
    def __init__(self, graph):
        self.graph = graph

    def generate(self):
        visualize_curves(self.graph)
        visualize_crossing_points(self.graph)


# ------------------------------------------------------------------------
#    Helper Methods
# ------------------------------------------------------------------------


def get_intersection_with_circle(
        first_point: Vector, second_point: Vector, circle_midpoint: Vector, circle_radius: float):
    vec = second_point - first_point

    # Coefficients of the quadratic equation for intersection calculation
    A = vec[0]**2 + vec[1]**2
    B = 2 * (vec[0] * (first_point[0] - circle_midpoint[0]) + vec[1] * (first_point[1] - circle_midpoint[1]))
    C = (first_point[0] - circle_midpoint[0])**2 + (first_point[1] - circle_midpoint[1])**2 - circle_radius**2
    discriminant = B**2 - 4 * A * C

    # There are two intersections of a vector with a circle (also with t = (-B - sqrt_discriminant) / (2 * A))
    # but only the first is relevant
    sqrt_discriminant = math.sqrt(discriminant)
    t = (-B + sqrt_discriminant) / (2 * A)

    return Vector((first_point[0] + t * vec[0], first_point[1] + t * vec[1], 0.0))


def visualize_crossing_points(graph):
    # Create a default cube as a mesh for a crossing point
    cube_mesh = bpy.data.meshes.new("Crossing_Point")
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=5.0)
    bm.to_mesh(cube_mesh)
    bm.free()

    # Get the collection of the crossing points
    crossing_points = bpy.data.collections.get("Crossing Points")

    if crossing_points is None:
        # Create a new collection if there is none
        crossing_points = bpy.data.collections.new("Crossing Points")
        bpy.context.scene.collection.children.link(crossing_points)

    # Iterate over all nodes of the graph
    for node in graph.nodes:
        if [*node.border_neighbors]:
            # Ignore the node if it is part of the border
            continue

        if node.curves:
            # Create a crossing point mesh if there are curves that belong to it
            crossing_point = bpy.data.objects.new("Crossing_Point", cube_mesh)
            crossing_points.objects.link(crossing_point)
            crossing_point.location = node.co.to_3d()

            # Sort the curves belonging to the crossing point
            reference_point = crossing_point.location
            sorted_curves = sort_curves(node.curves, reference_point)

            # Add for each sorted curve a custom property in the crossing point mesh
            for i, curve in enumerate(sorted_curves):
                crossing_point[f"Curve {i+1}"] = curve.name

            # Add also a custom property with the number of curves that belong to the crossing point
            crossing_point["Number of Curves"] = str(len(sorted_curves))


def visualize_curves(graph):
    curves = {}

    # Create a copy of all edges of the graph
    undirected_edges = [*graph.edges].copy()

    try:
        # Try to get the Curves collection and delete all objects in it to have a clear start
        curves_collection = bpy.data.collections["Curves"]
        bpy.ops.object.select_all(action='DESELECT')

        for curve in curves_collection.objects:
            curve.select_set(True)

        bpy.ops.object.delete()
    except Exception:
        # Create a new Curves collection and link it to the scene if there is none
        curves_collection = bpy.data.collections.new("Curves")
        bpy.context.scene.collection.children.link(curves_collection)

    index = 0

    # Iterate over all nodes (crossing points) in the graph
    for node in graph.nodes:
        # Iterate over all edges (curves) of each node
        for edge in node.edges:
            if edge in undirected_edges:
                # Edit the edge if we have not visited it yet and remember it (i.e. delete it from the list)
                undirected_edges.remove(edge)

                # The size of crossroad refers to the distance between the first/last point of the edge (curve)
                # and the node (cube/crossing point)
                crossroad_size = 16.0

                # Get the points of the edge (curve) and create a copy of it
                edge_points = edge.connection
                edge_points_copy = edge_points.copy()

                # Calculate the (direction) vector between the first point and the last point of the edge
                first_point = edge_points[0].to_3d()
                last_point = edge_points[-1].to_3d()
                vec = last_point - first_point

                # Skip edges that are too small
                if vec.length < crossroad_size * 2:
                    continue

                if len(edge_points) == 2:
                    # If there are only two points that belong to the edge, we can simply adjust these points
                    vec.normalize()
                    edge_points_copy[0] = first_point + vec * crossroad_size
                    edge_points_copy[1] = last_point - vec * crossroad_size
                else:
                    # If there are more than two points, we have to iterate from the begin and from the end
                    # and check whether we need to remove points or we can adjust them
                    for x in range(2):
                        # Remember the first/last point of the edge and set this point to the previous edge point as a reference
                        point = first_point if x == 0 else last_point
                        previous_edge_point = point

                        # Iterate over all edge points
                        for i in range(len(edge_points)):
                            # Calculate the vector between the current point and the first/last point
                            idx = i if x == 0 else -i - 1
                            edge_point = edge_points[idx].to_3d()
                            vec = edge_point - point

                            if vec.length < crossroad_size:
                                # Remove the point if it is too close to first/last point
                                edge_points_copy.popleft() if x == 0 else edge_points_copy.pop()

                                previous_edge_point = edge_point

                                continue
                            else:
                                # Add a new point with updated coordinates
                                # when a point is reached that is far enough away from the first/last point
                                # and when it is not too close to the last added point
                                new_co = get_intersection_with_circle(previous_edge_point, edge_point, point, crossroad_size)

                                last_added_point = edge_points_copy[0] if x == 0 else edge_points_copy[-1]

                                if (last_added_point.to_3d() - new_co).length > 0.001:
                                    edge_points_copy.appendleft(new_co) if x == 0 else edge_points_copy.append(new_co)

                                break

                if len(edge_points_copy) < 2:
                    # Skip resized edges with less than two points
                    continue
                elif len(edge_points_copy) == 2:
                    # Also skip resized edges that are too small
                    first_point = edge_points_copy[0].to_3d()
                    last_point = edge_points_copy[-1].to_3d()

                    if (last_point - first_point).length < crossroad_size:
                        continue

                # Add a curve object in the scene
                curve_name = "Curve_" + str(index).zfill(3)
                obj = visualize_one_curve(edge_points_copy, curves_collection, curve_name)

                # Remember the curve object for the edge
                curves[edge] = obj.name

                if edge.major:
                    obj["Major"] = True

                index += 1

            # Add the curve object of the edge to its corresponding node
            curve = curves.get(edge)

            if curve:
                node.curves.append(curve)


def visualize_one_curve(points: list, curves_collection: bpy.types.Collection, curve_name: str):
    curve = bpy.data.curves.new("Curve", 'CURVE')
    curve.splines.new('BEZIER')
    curve_spline = curve.splines.active
    curve_spline.bezier_points.add(len(points) - 1)

    obj = bpy.data.objects.new(curve_name, curve)
    curves_collection.objects.link(obj)

    for i in range(len(points)):
        curve_spline.bezier_points[i].co = points[i].to_3d()
        curve_spline.bezier_points[i].handle_right_type = 'VECTOR'
        curve_spline.bezier_points[i].handle_left_type = 'VECTOR'

    set_origin(obj)

    return obj

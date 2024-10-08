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
    cube_mesh = bpy.data.meshes.new("Crossing_Point")
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=5.0)
    bm.to_mesh(cube_mesh)
    bm.free()
    crossing_points = bpy.data.collections.get("Crossing Points")

    if crossing_points is None:
        crossing_points = bpy.data.collections.new("Crossing Points")
        bpy.context.scene.collection.children.link(crossing_points)

    for node in graph.nodes:
        if [*node.border_neighbors]:
            continue

        if node.curves:
            crossing_point = bpy.data.objects.new("Crossing_Point", cube_mesh)
            crossing_points.objects.link(crossing_point)
            crossing_point.location = node.co.to_3d()

            reference_point = crossing_point.location
            sorted_curves = sort_curves(node.curves, reference_point)

            for i, curve in enumerate(sorted_curves):
                crossing_point[f"Curve {i+1}"] = curve.name

            crossing_point["Number of Curves"] = str(len(sorted_curves))


def visualize_curves(graph):
    undirected_edges = [*graph.edges].copy()
    curves = {}

    try:
        curves_collection = bpy.data.collections["Curves"]
        bpy.ops.object.select_all(action='DESELECT')

        for curve in curves_collection.objects:
            curve.select_set(True)

        bpy.ops.object.delete()
    except Exception:
        curves_collection = bpy.data.collections.new("Curves")
        bpy.context.scene.collection.children.link(curves_collection)

    index = 0

    for node in graph.nodes:
        for edge in node.edges:
            if edge in undirected_edges:
                crossroad_size = 16.0

                undirected_edges.remove(edge)

                edge_points = edge.connection
                edge_points_copy = edge_points.copy()

                first_point = edge_points[0].to_3d()
                last_point = edge_points[-1].to_3d()
                vec = last_point - first_point

                # Skip edges that are too small
                if vec.length < crossroad_size * 2:
                    continue

                if len(edge_points) == 2:
                    # If there are only two points, we can simply adjust the points
                    vec.normalize()
                    edge_points_copy[0] = first_point + vec * crossroad_size
                    edge_points_copy[1] = last_point - vec * crossroad_size
                else:
                    # If there are more than two points, we have to iterate from the begin and from the end
                    # and check whether we need to remove points or we can adjust them
                    for x in range(2):
                        point = first_point if x == 0 else last_point
                        previous_edge_point = point

                        for i in range(len(edge_points)):
                            idx = i if x == 0 else -i - 1
                            edge_point = edge_points[idx].to_3d()
                            vec = edge_point - point

                            if vec.length < crossroad_size:
                                previous_edge_point = edge_point

                                # Remove the point if it is too close to begin/end point
                                edge_points_copy.popleft() if x == 0 else edge_points_copy.pop()

                                continue
                            else:
                                # Add a new point with updated coordinates
                                # when a point is reached that is far enough away from the begin/end point
                                # and when it is not too close to the last added point
                                new_co = get_intersection_with_circle(previous_edge_point, edge_point, point, crossroad_size)

                                last_added_point = edge_points_copy[0] if x == 0 else edge_points_copy[-1]

                                if (last_added_point.to_3d() - new_co).length > 0.001:
                                    edge_points_copy.appendleft(new_co) if x == 0 else edge_points_copy.append(new_co)

                                break

                # Skip edges with less than two points
                if len(edge_points_copy) < 2:
                    continue
                elif len(edge_points_copy) == 2:
                    first_point = edge_points_copy[0].to_3d()
                    last_point = edge_points_copy[-1].to_3d()

                    # Also skip resized edges that are too small
                    if (last_point - first_point).length < crossroad_size:
                        continue

                curve_name = "Curve_" + str(index).zfill(3)

                obj = visualize_one_curve(edge_points_copy, curves_collection, curve_name)
                curves[edge] = obj.name

                if edge.major:
                    obj["Major"] = True

                index += 1

            curve = curves.get(edge)

            if curve:
                node.curves.append(curve)


def visualize_one_curve(points, curves_collection, curve_name):
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

import bpy

from mathutils import Vector

from roadGen.generators.geometry_generator import RG_GeometryGenerator
from roadGen.road import RG_Road
from roadGen.utils.curve_management import get_closest_curve_point
from roadGen.utils.mesh_management import apply_transform, create_mesh_from_vertices, curve_to_mesh
from roadGen.utils.collection_management import get_crossing_curves, get_crossing_points, link_to_collection


class RG_RoadGenerator(RG_GeometryGenerator):
    def __init__(self):
        self.roads = []

    def add_geometry(self, curve: bpy.types.Object):
        if curve.data.dimensions == "2D":
            curve.data.dimensions = "3D"

        # Increase (or decrease) the resolution of the curve
        curve.data.resolution_u = 32
        curve.name = curve.name.replace(".", "_")

        # Select the curve and apply its rotation and scale
        # but without its location and its properties such as radius
        apply_transform(curve, location=False, properties=False)

        # Create a line mesh copy of the curve
        curve_to_mesh(curve)

        road = RG_Road(curve)
        add_road_lanes(road)
        self.roads.append(road)


# ------------------------------------------------------------------------
#    Helper Methods
# ------------------------------------------------------------------------


def add_road_lanes(road: RG_Road):
    for side in ["Left", "Right"]:
        curve = road.curve
        lane_number = road.left_lanes if side == "Left" else road.right_lanes
        bezier_points = curve.data.splines[0].bezier_points
        reverse = False

        # Create the left side backwards/reversed
        if side == "Left":
            reverse = True

        turning_lane_is_required = is_turning_lane_required(road, side)

        # If there is a turning lane distance and a turning lane is required, the index of the bezier point is calculated
        # that represent the start for the tuning lane
        if side == "Left" and road.left_turning_lane_distance and turning_lane_is_required:
            turning_lane_start_index = calculate_turning_lane_start_index(bezier_points, road.left_turning_lane_distance, reverse)
            road.has_left_turning_lane = True
        elif side == "Right" and road.right_turning_lane_distance and turning_lane_is_required:
            turning_lane_start_index = calculate_turning_lane_start_index(bezier_points, road.right_turning_lane_distance, reverse)
            road.has_right_turning_lane = True
        else:
            # Set the start index to -1 if there is no turning lane or not enough space for it, so that no extra lane is added
            turning_lane_start_index = -1

        crv = create_new_curve(bezier_points, road.lane_width, lane_number, turning_lane_start_index, reverse)
        new_curve = bpy.data.objects.new(f"{curve.name}_{side}", crv)
        new_curve.location = curve.location
        link_to_collection(new_curve, "Curves")

        # Update the scene to get correctly positioned objects
        bpy.context.view_layer.update()

        if side == "Left":
            road.curve_left = new_curve
        else:
            road.curve_right = new_curve

        # Create a line mesh for the created side curve
        side_curve = bpy.data.objects.get(new_curve.name)
        side_line_mesh = curve_to_mesh(side_curve)

        vertices = []

        # Add all vertices of the created line mesh to a list of vertices
        for vertex in side_line_mesh.data.vertices:
            v = side_line_mesh.matrix_world @ vertex.co
            vertex_vec = Vector((v.x, v.y, 0.0))
            vertices.append(vertex_vec)

        # Get the line mesh of the original curve
        curve_line_mesh = bpy.data.objects.get(f"Line_Mesh_{curve.name}")
        line_mesh_vertices = curve_line_mesh.data.vertices

        # The left side was created backwards, so we can iterate forwards over the original curve mesh,
        # only for the right side we have to iterate backwards (i.e. reverse the indices)
        indices = range(len(line_mesh_vertices))

        if not reverse:
            indices = reversed(indices)

        # Add all vertices of the line mesh of the original curve to the list of vertices
        for i in indices:
            vertex = curve_line_mesh.matrix_world @ line_mesh_vertices[i].co
            vertex_vec = Vector((vertex.x, vertex.y, 0.0))
            vertices.append(vertex_vec)

        create_mesh_from_vertices(vertices, "Road Lane", f"{side}_{curve.name}", 0.1)


def calculate_turning_lane_start_index(points: list, distance: float, reverse: bool):
    # Return 0 as start index if the road is too small so that the whole road get an extra lane
    if (points[0].co - points[-1].co).length <= distance:
        return 0

    length = 0
    start_index = 0

    indices = range(len(points))

    if reverse:
        indices = reversed(indices)

    for i in indices:
        index = i - 1 if reverse else i + 1
        length += (points[index].co - points[i].co).length

        if length >= distance:
            start_index = index
            break

    return start_index


def create_new_curve(bezier_points: list, lane_width: float, lane_number: int, turning_lane_start_index: int, reverse: bool):
    # Create a new curve and change its curve type to 3D and increase its resolution
    curve = bpy.data.curves.new("curve", 'CURVE')
    curve.dimensions = "3D"
    curve.resolution_u = 32

    # Create a new spline for the new created curve
    spline = curve.splines.new(type='BEZIER')

    new_bezier_points = spline.bezier_points
    bezier_points_number = len(bezier_points)

    # Add one spline bezier point for each point minus one (there is already one point by default)
    new_bezier_points.add(bezier_points_number - 1)

    indices = range(bezier_points_number)

    if reverse:
        indices = reversed(indices)

    # Calculate for each index the new (shifted) coordinates for each bezier_point of the new curve
    for i in indices:
        vec = bezier_points[i].handle_right - bezier_points[i].co
        vec.normalize()

        # Invert the orthogonal vector for the left side
        orthogonal_vector = Vector((vec.y, -vec.x, 0.0)) if reverse else Vector((-vec.y, vec.x, 0.0))

        # For the left side, we iterate reverse, so that the first curve points must be shifted more
        # than the rest, which is smaller than the passed index (opposite for the right side)
        extra_lane_condition = (i >= turning_lane_start_index) if reverse else (i <= turning_lane_start_index)

        # Calculate the shift offset depending on reverse or not
        if turning_lane_start_index == -1:
            offset = lane_width * lane_number
        elif extra_lane_condition or turning_lane_start_index == 0:
            offset = lane_width * (lane_number + 1)
        else:
            offset = lane_width * lane_number

        shift = orthogonal_vector * offset

        # Calculate the index for the current point of the new curve
        new_index = bezier_points_number - 1 - i if reverse else i

        # Set the coordinates of the current point
        new_bezier_points[new_index].co = bezier_points[i].co + shift

        # Set the left handle of the current point
        correct_handle = bezier_points[i].handle_right if reverse else bezier_points[i].handle_left
        new_bezier_points[new_index].handle_left = correct_handle + shift

        # Set the right handle of the current point
        correct_handle = bezier_points[i].handle_left if reverse else bezier_points[i].handle_right
        new_bezier_points[new_index].handle_right = correct_handle + shift

    return curve


def is_turning_lane_required(road, side):
    crossroad_points = get_crossing_points()

    # Iterate over all crossroad points to find the point that belongs to the current road
    for crossroad_point in crossroad_points:
        curves = get_crossing_curves(crossroad_point)
        curve_names = [curve.name for curve in curves]
        curves_number = len(curves)
        curve = road.curve

        if not road.right_neighbour_curve:
            right_neighbour_curve = get_right_neighbour_curve_of_curve(curve, crossroad_point, curves_number, side)
            road.right_neighbour_curve = right_neighbour_curve

        # Return False if the current road is a major road that splits into two roads so that no turning lane is required
        if curves_number - 1 == 2 and curve.get("Major"):
            return False

        # Only return True if there are more than two roads that belong to the crossroad point,
        # if we found the correct crossroad point and if there is a right neighbour curve for the current road/curve
        if curves_number > 2 and curve.name in curve_names and road.right_neighbour_curve:
            return True

    return False


def get_right_neighbour_curve_of_curve(
        curve: bpy.types.Object, crossroad_point: bpy.types.Object, total_number_of_curves: int, side: str):
    # Iterate over all curves that belong to the passed crossroad point
    # to find the index of the passed curve in the properties of the crossroad point
    for i in range(1, total_number_of_curves + 1):
        crv_name = crossroad_point.get(f"Curve {i}")
        crv = bpy.data.objects.get(crv_name)

        # Get the right neighbour of the passed curve when we reached the correct curve in properties of the crossroad point
        if crv.name == curve.name:
            neighbour_index = i + 1 if i < total_number_of_curves else 1
            right_neighbour_curve_name = crossroad_point.get(f"Curve {neighbour_index}")
            right_neighbour_curve = bpy.data.objects.get(right_neighbour_curve_name)

            if right_neighbour_curve:
                reference_point = crossroad_point.location
                curve_point = get_closest_curve_point(curve, reference_point, True)
                first_point = curve.matrix_world @ curve.data.splines[0].bezier_points[0].co
                last_point = curve.matrix_world @ curve.data.splines[0].bezier_points[-1].co

                # Only possibly return the right neighbour curve if it is the correct side
                if side == "Left" and curve_point == last_point or side == "Right" and curve_point == first_point:
                    # Get the normalized direction vector for the curve point and the crossroad point
                    direction = reference_point - curve_point
                    direction.normalize()

                    # Get the normalized direction vector for the curve point of the right neighbour and the crossroad point
                    right_neighbour_point = get_closest_curve_point(right_neighbour_curve, reference_point, True)
                    right_neighbour_direction = reference_point - right_neighbour_point
                    right_neighbour_direction.normalize()

                    # Calculate the cross product between the two direction vectors to check
                    # whether the right neighbour is really right to the current road and not, for example, straight
                    cross_prod = right_neighbour_direction.cross(direction)

                    # Round the z-axis of the cross product to obtain also a not quite exact right-hand curve
                    # (or to avoid floating point issues)
                    if round(cross_prod.z, 2) < 0:
                        return bpy.data.objects.get(right_neighbour_curve_name)

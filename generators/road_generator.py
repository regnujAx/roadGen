import bpy
import math

from mathutils import geometry, Vector

from roadGen.generators.geometry_generator import RG_GeometryGenerator
from roadGen.road import RG_Road
from roadGen.utils.curve_management import get_closest_curve_point, get_total_curve_length
from roadGen.utils.collection_management import get_crossing_curves, get_crossing_points, link_to_collection
from roadGen.utils.mesh_management import apply_transform, create_mesh_from_vertices, curve_to_mesh


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
        apply_transform(curve, rotation=True, scale=True)

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

        # Create the right side backwards/reversed
        if side == "Right":
            reverse = True

        turning_lane_distance = 0.0
        turning_lane_is_required = is_turning_lane_required(road, side)

        if side == "Left" and road.left_turning_lane_distance and turning_lane_is_required:
            road.has_left_turning_lane = True
            turning_lane_distance = road.left_turning_lane_distance
        elif side == "Right" and road.right_turning_lane_distance and turning_lane_is_required:
            road.has_right_turning_lane = True
            turning_lane_distance = road.right_turning_lane_distance

        crv = create_new_curve(bezier_points, turning_lane_distance, road.lane_width, lane_number, reverse)
        new_curve = bpy.data.objects.new(f"{curve.name}_{side}", crv)
        new_curve.location = curve.location
        link_to_collection(new_curve, "Curves")

        # Update the scene to get correctly positioned objects
        bpy.context.view_layer.update()

        if side == "Left":
            road.left_curve = new_curve
        else:
            road.right_curve = new_curve

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

        # Add all vertices of the line mesh of the original curve reversed to the list of vertices
        for i in reversed(range(len(line_mesh_vertices))):
            vertex = curve_line_mesh.matrix_world @ line_mesh_vertices[i].co
            vertex_vec = Vector((vertex.x, vertex.y, 0.0))
            vertices.append(vertex_vec)

        # The vertices for the left side should be ordered reverse for mesh generation
        create_mesh_from_vertices(vertices, "Road Lane", f"{curve.name}_{side}", 0.1, reverse=not reverse)


def create_new_curve(
        original_bezier_points: list, turning_lane_distance: float, lane_width: float, lane_number: int, reverse: bool):
    # Create a new curve and change its curve type to 3D and increase its resolution
    curve = bpy.data.curves.new("curve", 'CURVE')
    curve.dimensions = "3D"
    curve.resolution_u = 32

    original_bezier_points_number = len(original_bezier_points)

    create_new_spline(curve, original_bezier_points_number)

    bezier_points = curve.splines[0].bezier_points

    first_index = original_bezier_points_number - 1
    last_index = 0

    if reverse:
        first_index = 0
        last_index = original_bezier_points_number - 1

    # Remember the indices of "sharp" vertices (i.e. the angle between the handle vectors of a vertex is smaller then 135°)
    sharp_vertex_indices = []

    first_widening_index, last_widening_index = get_widening_indices_by_calculating_new_bezier_points(
        bezier_points, original_bezier_points, first_index, turning_lane_distance,
        lane_width, lane_number, reverse, sharp_vertex_indices)

    correct_index = last_index if reverse else first_index

    end = original_bezier_points[correct_index].co

    last_vec = (original_bezier_points[correct_index].handle_left - end if reverse
                else original_bezier_points[correct_index].handle_right - end)

    end_shift_offset = lane_width * lane_number + 15.0

    intersection_at_end, last_intersection_index = get_intersection_at_end_with_point_index(
        bezier_points, last_vec, end, end_shift_offset, reverse)

    # Create a new curve with updated points if there is an intersection with the future road lane end
    if intersection_at_end:
        new_coords = []

        for i in range(last_intersection_index + 1):
            new_coords.append(bezier_points[i].co.copy())

        new_coords.append(intersection_at_end)

        new_coords_number = len(new_coords)

        create_new_spline(curve, new_coords_number)

        new_bezier_points = curve.splines[0].bezier_points

        for i in range(new_coords_number):
            new_bezier_points[i].co = new_coords[i]

        bezier_points = new_bezier_points

    # Delete the unnecessary points if there are points between the begin and the end point of widening
    if (first_widening_index and
            (last_widening_index or last_widening_index == 0) and
            abs(last_widening_index - first_widening_index) > 1):
        new_coords = []

        # Iterate over all points, but keep only points that are not part of the widening
        for i in range(len(bezier_points)):
            is_not_part_of_widening = ((i <= first_widening_index or i >= last_widening_index) if reverse
                                       else (i >= first_widening_index or i <= last_widening_index))

            if is_not_part_of_widening:
                new_coords.append(bezier_points[i].co.copy())

        new_coords_number = len(new_coords)

        create_new_spline(curve, new_coords_number)

        new_bezier_points = curve.splines[0].bezier_points

        # Update the coordinates and the handles of the new points
        for i in range(new_coords_number):
            new_bezier_points[i].co = new_coords[i]

            if i == new_coords_number - 1 and intersection_at_end:
                if reverse:
                    new_bezier_points[i].handle_left = new_bezier_points[i].co + last_vec
                    new_bezier_points[i].handle_right = new_bezier_points[i].co - last_vec
                else:
                    new_bezier_points[i].handle_left = new_bezier_points[i].co - last_vec
                    new_bezier_points[i].handle_right = new_bezier_points[i].co + last_vec
            else:
                new_bezier_points[i].handle_left_type = 'AUTO'
                new_bezier_points[i].handle_right_type = 'AUTO'

            correct_index = first_widening_index if reverse else last_widening_index

            # Change only the type of the correct handle
            if i == correct_index:
                new_bezier_points[i].handle_left_type = 'VECTOR'
            elif i == correct_index + 1:
                new_bezier_points[i].handle_right_type = 'VECTOR'

        bezier_points = new_bezier_points

    # Find the self-intersection of the current curve (if there is one) and correct its points
    for start_index in sharp_vertex_indices:
        point_indices = get_bezier_point_indices_in_distance(bezier_points, start_index, lane_width * lane_number)

        self_intersection, index_before_self_intersection, number_of_points_to_remove = get_self_intersection(
            bezier_points, point_indices)

        if self_intersection:
            points = list(curve.splines[0].bezier_points)

            create_new_spline(curve, original_bezier_points_number - number_of_points_to_remove)

            new_bezier_points = curve.splines[0].bezier_points

            new_bezier_points_number = len(new_bezier_points)

            # Update the coordinates and handles of the new points
            for i in range(new_bezier_points_number):
                old_index = i if i <= index_before_self_intersection else i + number_of_points_to_remove

                new_bezier_points[i].co = points[old_index].co
                new_bezier_points[i].handle_left_type = points[old_index].handle_left_type
                new_bezier_points[i].handle_left = points[old_index].handle_left
                new_bezier_points[i].handle_right_type = points[old_index].handle_right_type
                new_bezier_points[i].handle_right = points[old_index].handle_right
        else:
            # Update the same points on the other side (the side without a self-intersection) to obtain a smoother curve
            for i in point_indices:
                bezier_points[i].handle_left_type = 'AUTO'
                bezier_points[i].handle_right_type = 'AUTO'

    return curve


def create_new_spline(curve: bpy.types.Object, new_bezier_points_number: int):
    # Delete the existing spline(s) and create a new one
    curve.splines.clear()
    spline = curve.splines.new(type='BEZIER')
    spline.bezier_points.add(new_bezier_points_number - 1)


def get_intersection_at_end_with_point_index(
        bezier_points: list, last_vec: Vector, end: Vector, end_shift_offset: float, reverse: bool):
    last_orthogonal_vector = Vector((-last_vec.y, last_vec.x, 0.0)) if reverse else Vector((last_vec.y, -last_vec.x, 0.0))

    # Find another point (far enough) to check if there is an intersection between the current curve and the road lane end
    end_shift = last_orthogonal_vector.normalized() * end_shift_offset
    end_shifted = end + end_shift

    intersection_at_end = None
    last_i = 0

    for i in range(len(bezier_points) - 1):
        p1 = bezier_points[i].co
        p2 = bezier_points[i + 1].co

        intersection = geometry.intersect_line_line_2d(p1, p2, end, end_shifted)

        threshold = 0.0001

        if intersection:
            intersection = intersection.to_3d()

            # It is only a correct intersection if the intersection found is not at (or very close to) the last point
            if (p1 - intersection).length > threshold and (p2 - intersection).length > threshold:
                intersection_at_end = intersection
                last_i = i

    return intersection_at_end, last_i


def get_bezier_point_indices_in_distance(bezier_points: list, start_index: int, distance: float):
    length = 0
    end_index = 0
    bezier_points_number = len(bezier_points)

    for i in range(bezier_points_number - 1):
        if i >= start_index:
            vec_length = (bezier_points[i].co - bezier_points[i + 1].co).length
            length += vec_length

            end_index = i + 1

            if length > distance:
                break

    start = start_index - (end_index - start_index) if start_index - (end_index - start_index) >= 0 else 0
    stop = end_index + 1 if end_index + 1 <= bezier_points_number else bezier_points_number

    return [i for i in range(start, stop)]


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
                if side == "Left" and curve_point == first_point or side == "Right" and curve_point == last_point:
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
                    if round(cross_prod.z, 1) < 0:
                        right_neighbour_first_point = (right_neighbour_curve.matrix_world @
                                                       right_neighbour_curve.data.splines[0].bezier_points[0].co)

                        if right_neighbour_point == right_neighbour_first_point:
                            right_neighbour_closest_side = "Right"
                        else:
                            right_neighbour_closest_side = "Left"

                        return f"{right_neighbour_curve_name}_{right_neighbour_closest_side}"

    return ""


def get_self_intersection(new_bezier_points: list, point_indices: list):
    for i in range(len(point_indices) - 1):
        p1, p2 = new_bezier_points[point_indices[i]].co, new_bezier_points[point_indices[i + 1]].co

        for j in range(i + 2, len(point_indices) - 1):
            p3, p4 = new_bezier_points[point_indices[j]].co, new_bezier_points[point_indices[j + 1]].co

            intersection = geometry.intersect_line_line_2d(p1, p2, p3, p4)

            if intersection:
                return intersection.to_3d(), point_indices[i], j - i

    return None, None, None


def get_widening_indices_by_calculating_new_bezier_points(
        new_bezier_points: list, original_bezier_points: list, first_index: int, turning_lane_distance: float,
        lane_width: float, lane_number: int, reverse: bool, sharp_vertex_indices: list):
    length = 0
    total_curve_length = get_total_curve_length(bezier_points=original_bezier_points)

    # "widening" means the part of the turning lane that is evenly widened until the turning lane is as wide as a road lane
    first_widening_index = None
    last_widening_index = None
    widening_distance = 10

    indices = range(len(original_bezier_points))

    if reverse:
        indices = list(reversed(indices))

    # Calculate for each index the new (shifted) coordinates for each bezier point of the new curve
    for i in indices:
        if turning_lane_distance == 0:
            # No turning lane
            offset = lane_width * lane_number
        elif total_curve_length < turning_lane_distance + widening_distance:
            # Turning lane for the whole curve if the curve is smaller than a turning lane with widening
            offset = lane_width * (lane_number + 1)
        else:
            # Calculate turning lane offset for each point
            if i != first_index:
                vector = (original_bezier_points[i - 1].co - original_bezier_points[i].co if reverse
                          else original_bezier_points[i + 1].co - original_bezier_points[i].co)
                length += vector.length

                # Remember only the first indices of the widening
                if length >= turning_lane_distance and not last_widening_index and last_widening_index != 0:
                    last_widening_index = i
                elif length >= turning_lane_distance + widening_distance and not first_widening_index:
                    first_widening_index = i

                if length < turning_lane_distance or length - vector.length < turning_lane_distance:
                    offset = lane_width * (lane_number + 1)
                elif length < turning_lane_distance + widening_distance and length >= turning_lane_distance:
                    # Calculate the offset depending on the position in the widening if it is part of the widening
                    interpolation_factor = (length - turning_lane_distance) / widening_distance
                    offset = lane_width * (lane_number + 1) - (interpolation_factor * lane_width)
                else:
                    offset = lane_width * lane_number
            else:
                offset = lane_width * lane_number

        left_vec = original_bezier_points[i].handle_left - original_bezier_points[i].co
        right_vec = original_bezier_points[i].handle_right - original_bezier_points[i].co

        angle = left_vec.angle(right_vec)

        sharpness_threshold = math.radians(135)

        # Append the index to a list if its vertex is "sharp"
        if angle < sharpness_threshold:
            sharp_vertex_indices.append(i)

        vec = left_vec if reverse else right_vec
        vec.normalize()

        orthogonal_vector = Vector((-vec.y, vec.x, 0.0))
        shift = orthogonal_vector * offset

        # Set the coordinate and the handles of the current bezier point (left and right sides have the same order as original)
        new_bezier_points[i].co = original_bezier_points[i].co + shift
        new_bezier_points[i].handle_left = original_bezier_points[i].handle_left + shift
        new_bezier_points[i].handle_right = original_bezier_points[i].handle_right + shift

    return first_widening_index, last_widening_index


def is_turning_lane_required(road: RG_Road, side: str):
    crossroad_points = get_crossing_points()
    curve = road.curve

    # Iterate over all crossroad points to find the point that belongs to the current road
    for crossroad_point in crossroad_points:
        curves = get_crossing_curves(crossroad_point)
        curve_names = [curve.name for curve in curves]

        if curve.name in curve_names:
            curves_number = len(curves)

            right_neighbour = get_right_neighbour_curve_of_curve(curve, crossroad_point, curves_number, side)

            if right_neighbour and right_neighbour.rpartition('_')[0] in curve_names:
                if side == "Left" and not road.right_neighbour_of_left_curve:
                    road.right_neighbour_of_left_curve = right_neighbour
                elif side == "Right" and not road.right_neighbour_of_right_curve:
                    road.right_neighbour_of_right_curve = right_neighbour

                # Return False if the current road is a major road that splits into two roads
                # so that no turning lane is required
                if curves_number - 1 == 2 and curve.get("Major"):
                    return False

                # Only return True if there are more than two roads that belong to the crossroad point,
                # if we found the correct crossroad point and if there is a right neighbour curve for the current road/curve
                if (curves_number > 2 and curve.name in curve_names and
                        (side == "Left" and road.right_neighbour_of_left_curve or
                         side == "Right" and road.right_neighbour_of_right_curve)):
                    return True

    return False

import bpy

from mathutils import Vector

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

        crv = create_new_curve(bezier_points, road.lane_width, lane_number, turning_lane_distance, reverse)
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

        create_mesh_from_vertices(vertices, "Road Lane", f"{curve.name}_{side}", 0.1)


def create_new_curve(bezier_points: list, lane_width: float, lane_number: int, turning_lane_distance: float, reverse: bool):
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
    first_index = bezier_points_number - 1
    last_index = 0

    if reverse:
        indices = list(reversed(indices))
        first_index = 0
        last_index = bezier_points_number - 1

    # "widening" means the part of the turning lane that is evenly widened until the turning lane is as wide as a road lane
    first_widening_index = None
    last_widening_index = None
    widening_distance = 10

    length = 0
    total_curve_length = get_total_curve_length(bezier_points=bezier_points)

    # Calculate for each index the new (shifted) coordinates for each bezier point of the new curve
    for i in indices:
        if turning_lane_distance == 0.0:
            # No turning lane
            offset = lane_width * lane_number
        elif total_curve_length < turning_lane_distance + widening_distance:
            # Turning lane for the whole curve if the curve is smaller than a turning lane with widening
            offset = lane_width * (lane_number + 1)
        else:
            # Calculate turning lane offset for each point
            if i != first_index:
                vector = (bezier_points[i - 1].co - bezier_points[i].co if reverse
                          else bezier_points[i + 1].co - bezier_points[i].co)
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

        vec = (bezier_points[i].handle_left - bezier_points[i].co if reverse
               else bezier_points[i].handle_right - bezier_points[i].co)
        vec.normalize()

        orthogonal_vector = Vector((-vec.y, vec.x, 0.0))
        shift = orthogonal_vector * offset

        # Set the coordinate and the handles of the current bezier point (left and right sides have the same order as original)
        new_bezier_points[i].co = bezier_points[i].co + shift
        new_bezier_points[i].handle_left = bezier_points[i].handle_left + shift
        new_bezier_points[i].handle_right = bezier_points[i].handle_right + shift

    correct_index = last_index if reverse else first_index

    end = bezier_points[correct_index].co

    last_vec = bezier_points[correct_index].handle_left - end if reverse else bezier_points[correct_index].handle_right - end
    last_orthogonal_vector = Vector((-last_vec.y, last_vec.x, 0.0)) if reverse else Vector((last_vec.y, -last_vec.x, 0.0))

    intersection = None
    last_i = 0

    for i in range(len(new_bezier_points) - 1):
        p1 = new_bezier_points[i].co
        p2 = new_bezier_points[i + 1].co

        intersec = get_intersection(end, last_orthogonal_vector, p1, p2)

        if intersec:
            intersection = intersec
            last_i = i

    if intersection:
        new_coords = []

        for i in range(0, last_i + 1):
            new_coords.append(new_bezier_points[i].co.copy())

        new_coords.append(intersection)

        new_coords_number = len(new_coords)

        curve.splines.clear()
        spline = curve.splines.new(type='BEZIER')

        bezier_points = spline.bezier_points

        bezier_points.add(new_coords_number - 1)
        for i in range(new_coords_number):
            bezier_points[i].co = new_coords[i]

        new_bezier_points = bezier_points

    if first_widening_index and (last_widening_index or last_widening_index == 0):
        if abs(last_widening_index - first_widening_index) > 1:
            # Delete the unnecessary points if there are points between the begin and end point of widening
            new_coords = []

            # Iterate over all points, but keep only points that are not part of the widening
            for i in range(len(new_bezier_points)):
                is_not_part_of_widening = ((i <= first_widening_index or i >= last_widening_index) if reverse
                                           else (i >= first_widening_index or i <= last_widening_index))

                if is_not_part_of_widening:
                    new_coords.append(new_bezier_points[i].co.copy())

            new_coords_number = len(new_coords)

            # Delete the existing spline and create a new one
            curve.splines.clear()
            spline = curve.splines.new(type='BEZIER')

            bezier_points = spline.bezier_points

            bezier_points.add(new_coords_number - 1)

            # Update the coordinates and handles of the new points
            for i in range(new_coords_number):
                bezier_points[i].co = new_coords[i]

                if i == new_coords_number - 1 and intersection:
                    handle_co = bezier_points[i].co + last_vec

                    if reverse:
                        bezier_points[i].handle_left = handle_co
                        bezier_points[i].handle_right_type = 'AUTO'
                    else:
                        bezier_points[i].handle_right = handle_co
                        bezier_points[i].handle_left_type = 'AUTO'
                else:
                    bezier_points[i].handle_left_type = 'AUTO'
                    bezier_points[i].handle_right_type = 'AUTO'

                correct_index = first_widening_index if reverse else last_widening_index

                # Change only the type of the correct handle
                if i == correct_index:
                    bezier_points[i].handle_left_type = 'VECTOR'
                elif i == correct_index + 1:
                    bezier_points[i].handle_right_type = 'VECTOR'

    return curve


def get_intersection(start_point: Vector, direction: Vector, first_point: Vector, second_point: Vector):
    # Calculate the vector between the start points
    vec = first_point - start_point

    # Get the direction of the line, i.e. the two passed points
    line_direction = second_point - first_point

    cross_length = direction.cross(line_direction).length

    threshold = 0.0001

    if cross_length < threshold:
        return None

    # Calculate the interpolation factor
    t = (vec.x * direction.y - vec.y * direction.x) / cross_length

    if threshold <= t <= 1 - threshold:
        # Calculate and return the intersection point on the line
        return first_point + t * line_direction
    else:
        return None


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

            if right_neighbour and right_neighbour.name in curve_names:
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
                        return bpy.data.objects.get(right_neighbour_curve_name)

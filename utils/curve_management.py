import bpy

from mathutils import Vector


def get_closest_curve_point(curve: bpy.types.Object, reference_point: Vector, in_global_co: bool = False):
    # Get the curve end points in world space
    m = curve.matrix_world
    first_curve_point = curve.data.splines[0].bezier_points[0]
    last_curve_point = curve.data.splines[0].bezier_points[-1]
    first_curve_point_co = m @ first_curve_point.co
    last_curve_point_co = m @ last_curve_point.co

    point = get_closest_point([first_curve_point_co, last_curve_point_co], reference_point)

    if in_global_co:
        return first_curve_point_co if point == first_curve_point_co else last_curve_point_co

    return first_curve_point if point == first_curve_point_co else last_curve_point


def get_closest_point(points: list, reference_point: Vector):
    closest_point = points[0]

    for i in range(len(points) - 1):
        point = points[i + 1]
        vector_1 = closest_point - reference_point
        vector_2 = point - reference_point

        if vector_2.length < vector_1.length:
            closest_point = point

    return closest_point


def get_total_curve_length(curve: bpy.types.Object = None, bezier_points: list = None):
    total_length = 0

    if curve:
        bezier_points = curve.data.splines[0].bezier_points

    for i in range(len(bezier_points) - 1):
        total_length += (bezier_points[i].co - bezier_points[i + 1].co).length

    return total_length


def get_visible_curves():
    # Get all visible (not hidden) curves
    objects = bpy.context.scene.objects
    return [obj for obj in objects if obj.type == "CURVE" and obj.visible_get()]


def sort_curves(curve_names: list, reference_point: Vector):
    direction_vectors = []
    # Calculate for each curve a direction vector from curve to reference point
    for curve_name in curve_names:
        curve = bpy.data.objects.get(curve_name)

        if not curve:
            return []

        curve_point_co = get_closest_curve_point(curve, reference_point, True)
        direction_vector = curve_point_co - reference_point

        # Save each curve and its direction vector
        direction_vectors.append((curve, direction_vector))

    reference_vector = direction_vectors[0][1]
    # Resize the vector to use the angle_signed method from mathutils.Vector that expects 2D vectors
    reference_vector.resize_2d()

    angles = []
    # Calculate the clockwise angle for each direction vector (the first direction vector is the origin/start)
    for vector in direction_vectors:
        vector[1].resize_2d()
        vec = vector[1] - reference_vector
        angle = reference_vector.angle_signed(vec) if vec.length != 0 else 0.0
        angles.append(angle)

    # Check whether the lines cross straight and swap the order (set one angle to -1) if they do
    if len(angles) == 2 and round(angles[1], 2) == 3.14:
        angles[1] = -1

    vectors_and_angles = []
    for vector, angle in zip(direction_vectors, angles):
        vectors_and_angles.append((vector[0], angle))

    # Sort the direction vectors counter-clockwise according to angle and extract the corresponding curves
    vectors_and_angles.sort(key=lambda x: x[1], reverse=True)
    sorted_curves = [curve for curve, _ in vectors_and_angles]

    return sorted_curves

import bpy
import math

from mathutils import Vector

from roadGen.utils.mesh_management import closest_curve_point


def sort_curves(curves: list, reference_point: Vector):
    direction_vectors = []
    # Calculate for each curve a direction vector from curve to reference point
    for curve in curves:
        curve_point = closest_curve_point(curve, reference_point)
        curve_point_co = curve.matrix_world @ curve_point.co
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
        v = vector[1] - reference_vector
        length = math.sqrt(sum(i**2 for i in v))

        angle = reference_vector.angle_signed(v) if length != 0 else 0.0
        angles.append(angle)

    # Check whether the lines cross straight and swap the order (set one angle to -1) if they do
    if len(angles) == 2 and round(angles[1], 2) == 3.14:
        angles[1] = -1

    vectors_and_angles = []
    for vector, angle in zip(direction_vectors, angles):
        vectors_and_angles.append((vector[0], angle))

    # Sort the direction vectors according to angle and extract the corresponding curves
    vectors_and_angles.sort(key=lambda x: x[1])
    sorted_curves = [curve for curve, _ in vectors_and_angles]

    return sorted_curves


def visible_curves():
    # Get all visible (not hidden) curves
    objects = bpy.context.scene.objects
    return [obj for obj in objects if obj.type == "CURVE" and obj.visible_get()]

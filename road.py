import bpy

from roadGen.utils.curve_management import get_closest_curve_point, get_closest_point


class RG_Road:
    def __init__(self, curve: bpy.types.Object):
        self.curve = curve
        self.curve_left = None
        self.curve_right = None
        self.lane_width = self.curve.get("Lane Width")
        self.left_lanes = self.curve.get("Left Lanes")
        self.right_lanes = self.curve.get("Right Lanes")
        self.left_turning_lane_distance = self.curve.get("Left Turning Lane Distance")
        self.right_turning_lane_distance = self.curve.get("Right Turning Lane Distance")
        self.lamp_distance = self.curve.get("Lamp Distance")
        self.has_left_turning_lane = False
        self.has_right_turning_lane = False
        self.kerb_mesh_template = None
        self.kerbs = []
        self.right_neighbour_curve = None
        self.sidewalk_mesh_template = None
        self.sidewalks = {}

    def dropped_positions(self, side: str):
        return [int(x) for x in self.curve.get(f"{side} Dropped Kerbs").split(",")]

    def get_right_curve(self):
        # Get the closest point to the reference point of both side curves
        left_curve_point = get_closest_curve_point(self.curve_left, self.right_neighbour_curve.location, True)
        right_curve_point = get_closest_curve_point(self.curve_right, self.right_neighbour_curve.location, True)
        closest_point = get_closest_point([left_curve_point, right_curve_point], self.right_neighbour_curve.location)

        for side in ["Left", "Right"]:
            side_curve = self.curve_left if side == "Left" else self.curve_right
            point = closest_point - side_curve.location
            bezier_points = side_curve.data.splines[0].bezier_points

            # For each bezier point of the side curve, calculate the distance between it and the closest point
            # and return the corresponding side curve if it the same point, i.e. the distance is smaller than a threshold
            for bezier_point in bezier_points:
                if (bezier_point.co - point).length < 0.0001:
                    return side_curve

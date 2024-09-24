import bpy


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
        self.sidewalk_mesh_template = None
        self.sidewalks = {}

    def dropped_positions(self, side: str):
        return [int(x) for x in self.curve.get(f"{side} Dropped Kerbs").split(",")]

import bpy


class CG_Road:
    def __init__(self, curve: bpy.types.Object):
        self.curve = curve
        self.lane_width = self.curve["Lane Width"]
        self.left_lanes = self.curve["Left Lanes"]
        self.right_lanes = self.curve["Right Lanes"]
        self.road_lanes_left = []
        self.road_lanes_right = []
        self.kerbs = []
        self.sidewalks = {}

    def dropped_positions(self, side: str):
        return [int(x) for x in self.curve[f"{side} Dropped Kerbs"].split(",")]

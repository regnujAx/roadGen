import bpy


class RG_Road:
    def __init__(self, curve: bpy.types.Object):
        self.curve = curve
        self.lane_width = self.curve["Lane Width"]
        self.left_lanes = self.curve["Left Lanes"]
        self.right_lanes = self.curve["Right Lanes"]
        self.lamp_distance = self.curve["Lamp Distance"]
        self.road_lane_mesh_template_inside = None
        self.road_lane_mesh_template_left = None
        self.road_lane_mesh_template_right = None
        self.road_lanes_left = []
        self.road_lanes_right = []
        self.kerb_mesh_template = None
        self.kerbs = []
        self.sidewalk_mesh_template = None
        self.sidewalks = {}

    def dropped_positions(self, side: str):
        return [int(x) for x in self.curve[f"{side} Dropped Kerbs"].split(",")]

    # ToDo: Check if it is still required
    def width_per_side(self, side: str):
        road_lanes = self.road_lanes_left if side == "Left" else self.road_lanes_right
        return self.lane_width * road_lanes + self.kerb_mesh_template.dimensions[1] + self.sidewalk_mesh_template.dimensions[1]

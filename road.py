import bpy

from .utils.mesh_management import add_mesh_to_curve


class CG_Road:
    def __init__(self, curve: bpy.types.Object):
        self.curve = curve
        self.lane_width = self.curve["Lane Width"]
        self.left_lanes = self.curve["Left Lanes"]
        self.right_lanes = self.curve["Right Lanes"]
        self.road_lanes_left = []
        self.road_lanes_right = []
        self.kerbs = []
        self.sidewalks = []

    def add_road_lanes(self):
        road_lane_mesh_template_inside = bpy.data.objects.get("Road_Lane_Inside")

        for side in ["Left", "Right"]:
            road_lane_mesh_template_outside = bpy.data.objects.get(f"Road_Lane_Border_{side}")

            if road_lane_mesh_template_outside and road_lane_mesh_template_inside:
                lane_number = self.left_lanes if side == "Left" else self.right_lanes

                for i in range(lane_number):
                    template = road_lane_mesh_template_outside if i == lane_number - 1 else road_lane_mesh_template_inside
                    index = i + 1 if side == "Left" else -i
                    mesh = add_mesh_to_curve(template, self.curve, f"Road_Lane_{side}", self.lane_width, index)

                    if side == "Left":
                        self.road_lanes_left.append(mesh)
                    else:
                        self.road_lanes_right.append(mesh)
            else:
                print("Check whether the objects Road_Lane_Border_Left, Road_Lane_Border_Right "
                      "and Road_Lane_Inside are present. At least one is missing.")

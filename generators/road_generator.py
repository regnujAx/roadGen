import bpy

from .geometry_generator import CG_GeometryGenerator
from ..road import CG_Road
from ..utils.mesh_management import add_mesh_to_curve, apply_transform


class CG_RoadGenerator(CG_GeometryGenerator):
    def __init__(self):
        self.roads = []

    def add_geometry(self, curve: bpy.types.Object):
        if curve.dimensions == "2D":
            curve.dimensions = "3D"

        # Increase (or decrease) the resolution of the curve
        curve.data.resolution_u = 32
        curve.name = curve.name.replace(".", "_")

        # Select the curve and apply its rotation and scale
        # but without its location and its properties such as radius
        apply_transform(curve, location=False, properties=False)

        road = CG_Road(curve)
        add_road_lanes(road)
        self.roads.append(road)


# ------------------------------------------------------------------------
#    Helper Methods
# ------------------------------------------------------------------------


def add_road_lanes(road: CG_Road):
    road_lane_mesh_template_inside = bpy.data.objects.get("Road_Lane_Inside")

    for side in ["Left", "Right"]:
        road_lane_mesh_template_outside = bpy.data.objects.get(f"Road_Lane_Border_{side}")

        if road_lane_mesh_template_outside and road_lane_mesh_template_inside:
            lane_number = road.left_lanes if side == "Left" else road.right_lanes

            for i in range(lane_number):
                template = road_lane_mesh_template_outside if i == lane_number - 1 else road_lane_mesh_template_inside
                index = i + 1 if side == "Left" else -i
                mesh = add_mesh_to_curve(template, road.curve, f"Road_Lane_{side}", road.lane_width, index)

                if side == "Left":
                    road.road_lanes_left.append(mesh)
                else:
                    road.road_lanes_right.append(mesh)
        else:
            print("Check whether the objects Road_Lane_Border_Left, Road_Lane_Border_Right "
                  "and Road_Lane_Inside are present. At least one is missing.")

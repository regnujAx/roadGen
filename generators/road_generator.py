import bpy

from .geometry_generator import RG_GeometryGenerator
from ..road import RG_Road
from ..utils.mesh_management import add_mesh_to_curve, apply_transform, curve_to_mesh


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

        road = RG_Road(curve)
        add_road_lanes(road)
        self.roads.append(road)

        # Create a line mesh copy of the curve
        curve_to_mesh(curve)


# ------------------------------------------------------------------------
#    Helper Methods
# ------------------------------------------------------------------------


def add_road_lanes(road: RG_Road):
    road_lane_mesh_template_inside = bpy.data.objects.get("Road_Lane_Inside")

    if not road.road_lane_mesh_template_inside:
        road.road_lane_mesh_template_inside = road_lane_mesh_template_inside

    for side in ["Left", "Right"]:
        road_lane_mesh_template_outside = bpy.data.objects.get(f"Road_Lane_Border_{side}")

        if not road.road_lane_mesh_template_left and side == "Left":
            road.road_lane_mesh_template_left = road_lane_mesh_template_outside
        elif not road.road_lane_mesh_template_right and side == "Right":
            road.road_lane_mesh_template_right = road_lane_mesh_template_outside

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

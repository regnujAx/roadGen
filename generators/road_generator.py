import bpy

from roadGen.generators.geometry_generator import RG_GeometryGenerator
from roadGen.road import RG_Road
from roadGen.utils.mesh_management import add_mesh_to_curve, apply_transform, curve_to_mesh


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
    if not road.road_lane_mesh_template:
        road.road_lane_mesh_template = bpy.data.objects.get("Road_Lane")

    if road.road_lane_mesh_template:
        for side in ["Left", "Right"]:
            lane_number = road.left_lanes if side == "Left" else road.right_lanes

            for i in range(lane_number):
                template = road.road_lane_mesh_template if i == lane_number - 1 else road.road_lane_mesh_template
                index = -i if side == "Left" else i + 1
                mesh = add_mesh_to_curve(template, road.curve, f"Road_Lane_{side}", road.lane_width, index)

                if side == "Left":
                    road.road_lanes_left.append(mesh)
                else:
                    road.road_lanes_right.append(mesh)
    else:
        print("Check whether the object Road_Lane is present. It is missing.")

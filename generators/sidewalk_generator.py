import bpy

from ..road import CG_Road
from ..utils.mesh_management import add_mesh_to_curve, separate_array_meshes


class CG_SidewalkGenerator:
    def __init__(self, curve: bpy.types.Object = None, road: CG_Road = None, sidewalk_mesh_template: bpy.types.Object = None):
        self.curve = curve
        self.road = road
        self.sidewalk_mesh_template = sidewalk_mesh_template if sidewalk_mesh_template else bpy.data.objects.get("Sidewalk")

        if not self.sidewalk_mesh_template:
            print("Check whether the object Sidewalk is present, it is missing.")

    def add_sidewalks(self):
        for side in ["Left", "Right"]:
            index = self.road.left_lanes if side == "Left" else -self.road.right_lanes
            offset = bpy.data.objects.get("Kerb").dimensions[1]
            mesh = add_mesh_to_curve(
                self.sidewalk_mesh_template, self.road.curve, f"Sidewalk_{side}", self.road.lane_width, index, offset)

            if self.road:
                self.road.sidewalks.append(mesh)

            separate_array_meshes(mesh)

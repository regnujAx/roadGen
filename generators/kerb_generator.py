import bpy

from ..road import CG_Road
from ..utils.mesh_management import add_line_following_mesh, add_mesh_to_curve, edit_mesh_at_positions


class CG_KerbGenerator:
    def __init__(self, curve: bpy.types.Object = None, road: CG_Road = None, kerb_mesh_template: bpy.types.Object = None):
        self.curve = curve
        self.road = road
        self.kerb_mesh_template = kerb_mesh_template if kerb_mesh_template else bpy.data.objects.get("Kerb")

        if not self.kerb_mesh_template:
            print("Check whether the object Kerb is present, it is missing.")

    def add_kerb(self, side: str = None):
        if self.curve:
            mesh = add_mesh_to_curve(self.kerb_mesh_template, self.curve, "Kerb", 0.0, 0)
        elif self.road and side:
            index = self.road.left_lanes if side == "Left" else -self.road.right_lanes
            mesh = add_mesh_to_curve(self.kerb_mesh_template, self.road.curve, f"Kerb_{side}", self.road.lane_width, index)

            self.road.kerbs.append(mesh)

            mesh_name = "Kerb_" + side + "_" + self.road.curve.name
            add_line_following_mesh(mesh_name)

            if self.road.curve[f"{side} Dropped Kerbs"]:
                positions = self.road.dropped_positions(side)
                edit_mesh_at_positions(mesh_name, positions)

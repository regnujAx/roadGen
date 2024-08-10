import bpy

from .geometry_generator import RG_GeometryGenerator
from ..road import RG_Road
from ..utils.mesh_management import add_line_following_mesh, add_mesh_to_curve, edit_mesh_at_positions


class RG_KerbGenerator(RG_GeometryGenerator):
    def __init__(self, kerb_mesh_template: bpy.types.Object = None):
        self.kerb_mesh_template = kerb_mesh_template if kerb_mesh_template else bpy.data.objects.get("Kerb")

        if not self.kerb_mesh_template:
            print("Check whether the object Kerb is present, it is missing.")

    def add_geometry(self, curve: bpy.types.Object = None, road: RG_Road = None, side: str = None):
        if curve:
            mesh = add_mesh_to_curve(self.kerb_mesh_template, curve, "Kerb", 0.0, 0)
        elif road and side:
            index = road.left_lanes if side == "Left" else -road.right_lanes
            mesh = add_mesh_to_curve(self.kerb_mesh_template, road.curve, f"Kerb_{side}", road.lane_width, index)

            road.kerbs.append(mesh)

            mesh_name = "Kerb_" + side + "_" + road.curve.name
            add_line_following_mesh(mesh_name)

            if road.curve[f"{side} Dropped Kerbs"]:
                positions = road.dropped_positions(side)
                edit_mesh_at_positions(mesh_name, positions)

import bpy

from roadGen.generators.geometry_generator import RG_GeometryGenerator
from roadGen.road import RG_Road
from roadGen.utils.mesh_management import add_line_following_mesh, add_mesh_to_curve, edit_mesh_at_positions


class RG_KerbGenerator(RG_GeometryGenerator):
    def __init__(self, mesh_template: bpy.types.Object = None):
        self.mesh_template = mesh_template if mesh_template else bpy.data.objects.get("Kerb")

        if not self.mesh_template:
            print("Check whether the object Kerb exists. It is missing.")

    def add_geometry(self, curve: bpy.types.Object = None, road: RG_Road = None, side: str = None):
        if curve:
            # Add a kerb for a crossroad curve
            mesh = add_mesh_to_curve(self.mesh_template, curve, "Kerb", 0.0, 0)
        elif road and side:
            if not road.kerb_mesh_template:
                road.kerb_mesh_template = self.mesh_template

            # Add a kerb for a road
            index = -road.left_lanes if side == "Left" else road.right_lanes
            mesh = add_mesh_to_curve(self.mesh_template, road.curve, f"Kerb_{side}", road.lane_width, index)

            road.kerbs.append(mesh)

            mesh_name = "Kerb_" + side + "_" + road.curve.name
            add_line_following_mesh(mesh_name)

            if road.curve[f"{side} Dropped Kerbs"]:
                positions = road.dropped_positions(side)
                edit_mesh_at_positions(mesh_name, positions)

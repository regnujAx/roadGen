import bpy

from roadGen.generators.geometry_generator import RG_GeometryGenerator
from roadGen.road import RG_Road
from roadGen.utils.mesh_management import add_mesh_to_curve, edit_mesh_at_positions


class RG_KerbGenerator(RG_GeometryGenerator):
    def __init__(self, mesh_template: bpy.types.Object = None):
        self.mesh_template = mesh_template if mesh_template else bpy.data.objects.get("Kerb")

        if not self.mesh_template:
            print("Check whether the object Kerb exists. It is missing.")

    def add_geometry(self, curve: bpy.types.Object = None, road: RG_Road = None, side: str = None):
        # The kerb has to be on the other side of a crossroad curve and the right side
        index = -1

        if road:
            if not road.kerb_mesh_template:
                road.kerb_mesh_template = self.mesh_template

            if side == "Left" and road.left_curve:
                curve = road.left_curve
                index = 1
            elif side == "Right" and road.right_curve:
                curve = road.right_curve

        name = curve.name
        mesh = add_mesh_to_curve(self.mesh_template, curve, f"Kerb_{name}", index)

        if road:
            road.kerbs.append(mesh)

            if road.curve.get(f"{side} Dropped Kerbs"):
                positions = road.dropped_positions(side)
                edit_mesh_at_positions(f"Kerb_{name}", positions, name)

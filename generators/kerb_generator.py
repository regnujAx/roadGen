import bpy

from ..road import CG_Road
from ..utils.collection_management import hide_collection
from ..utils.mesh_management import add_line_following_mesh, add_object_to_mesh, add_mesh_to_curve


class CG_KerbGenerator:
    def __init__(self, curve: bpy.types.Object = None, road: CG_Road = None, kerb_mesh_template: bpy.types.Object = None):
        self.curve = curve
        self.road = road
        self.kerb_mesh_template = kerb_mesh_template if kerb_mesh_template else bpy.data.objects.get("Kerb")

        if not self.kerb_mesh_template:
            print("Check whether the object Kerb is present, it is missing.")

    def add_kerb_to_curve(self):
        if self.curve:
            add_mesh_to_curve(self.kerb_mesh_template, self.curve, "Kerb", 0.0, 0)

    def add_kerbs_to_road(self):
        if self.road:
            # Get the curve's custom properties
            lane_width = self.road.lane_width if self.road else 0.0
            left_lanes = self.road.left_lanes if self.road else 1
            right_lanes = self.road.right_lanes if self.road else 1

            if self.kerb_mesh_template:
                for side in ["Left", "Right"]:
                    index = left_lanes if side == "Left" else -right_lanes
                    mesh = add_mesh_to_curve(self.kerb_mesh_template, self.road.curve, f"Kerb_{side}", lane_width, index)

                    if self.road:
                        self.road.kerbs.append(mesh)

                    mesh_name = "Kerb_" + side + "_" + self.road.curve.name
                    add_line_following_mesh(mesh_name)

                    if self.road.curve[f"{side} Dropped Kerbs"]:
                        positions = [int(x) for x in self.road.curve[f"{side} Dropped Kerbs"].split(",")]
                        add_object_to_mesh(mesh_name, positions)

                # Hide the Line Meshes collection in Viewport
                hide_collection("Line Meshes")

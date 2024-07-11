import bpy

from ..road import CG_Road
from ..utils.mesh_management import apply_transform


class CG_RoadGenerator:
    def __init__(self, curves: list):
        self.curves = curves
        self.kerb_mesh_template = bpy.data.objects.get("Kerb")
        self.roads = []

    def add_roads(self):
        if not self.kerb_mesh_template:
            print("Check whether the object Kerb is present, it is missing.")

        for curve in self.curves:
            if curve.dimensions == "2D":
                curve.dimensions = "3D"
            curve.name = curve.name.replace(".", "_")
            # Select the curve and apply its rotation and scale
            # but without its location and its properties such as radius
            apply_transform(curve, location=False, properties=False)

            road = CG_Road(curve)
            road.add_road_lanes()
            self.roads.append(road)

from ..road import CG_Road
from ..utils.mesh_management import apply_transform


class CG_RoadGenerator:
    def __init__(self, curves: list):
        self.curves = curves
        self.roads = []

    def add_roads(self):
        for curve in self.curves:
            if curve.dimensions == "2D":
                curve.dimensions = "3D"
            # Increase (or decrease) the resolution of the curve
            curve.data.resolution_u = 32
            curve.name = curve.name.replace(".", "_")
            # Select the curve and apply its rotation and scale
            # but without its location and its properties such as radius
            apply_transform(curve, location=False, properties=False)

            road = CG_Road(curve)
            road.add_road_lanes()
            self.roads.append(road)

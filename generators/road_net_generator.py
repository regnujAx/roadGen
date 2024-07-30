from .crossroad_generator import CG_CrossroadGenerator
from .data_generator import CG_DataGenerator
from .kerb_generator import CG_KerbGenerator
from .road_generator import CG_RoadGenerator
from .sidewalk_generator import CG_SidewalkGenerator
from ..utils.collection_management import crossing_points, hide_collection


class CG_RoadNetGenerator:
    def __init__(self, curves: list):
        self.curves = curves

    def create(self):
        datamanager = CG_DataGenerator()
        datamanager.create_road_data()

        road_generator = CG_RoadGenerator()
        for curve in self.curves:
            road_generator.add_geometry(curve)

        kerb_generator = CG_KerbGenerator()
        sidewalk_generator = CG_SidewalkGenerator()

        for road in road_generator.roads:
            for side in ["Left", "Right"]:
                kerb_generator.add_geometry(road=road, side=side)
                sidewalk_generator.add_geometry(road=road, side=side)

        crossroad_generator = CG_CrossroadGenerator(kerb_generator, sidewalk_generator)

        for crossing_point in crossing_points():
            crossroad_generator.add_geometry(crossing_point)

        # sidewalk_generator.correct_sidewalks()

        hide_collection("Line Meshes")
        hide_collection("Crossroad Curves")

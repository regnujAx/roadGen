from .crossroad_generator import CG_CrossroadGenerator
from .data_generator import CG_DataGenerator
from .kerb_generator import CG_KerbGenerator
from .road_generator import CG_RoadGenerator


class CG_RoadNetGenerator:
    def __init__(self, curves: list):
        self.curves = curves

    def create(self):
        datamanager = CG_DataGenerator()
        datamanager.create_road_data()

        road_generator = CG_RoadGenerator(self.curves)
        road_generator.add_roads()

        for road in road_generator.roads:
            kerb_generator = CG_KerbGenerator(road=road)
            kerb_generator.add_kerbs_to_road()

        crossroad_generator = CG_CrossroadGenerator()
        crossroad_generator.add_crossroads()

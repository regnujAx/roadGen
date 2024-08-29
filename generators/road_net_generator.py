from .crossroad_generator import RG_CrossroadGenerator
from .data_generator import RG_DataGenerator
from .graph_to_net_generator import RG_GraphToNetGenerator
from .kerb_generator import RG_KerbGenerator
from .object_generator import RG_ObjectGenerator
from .road_generator import RG_RoadGenerator
from .sidewalk_generator import RG_SidewalkGenerator
from ..utils.collection_management import crossing_points
from ..utils.curve_management import visible_curves


class RG_RoadNetGenerator:
    def __init__(self, crossroad_offset: float = 0.0, graph=None):
        self.crossroad_offset = crossroad_offset
        self.graph = graph

    def generate(self):
        # Visualize the graph in Blender
        if self.graph:
            graph_to_net_generator = RG_GraphToNetGenerator(self.crossroad_offset, self.graph)
            graph_to_net_generator.generate()

        curves = visible_curves()

        # Create road data
        datamanager = RG_DataGenerator(curves)
        datamanager.create_road_data()

        # Visualize roads in Blender
        road_generator = RG_RoadGenerator()
        for curve in curves:
            road_generator.add_geometry(curve)

        # Visualize kerbs, sidewalks and objects in Blender
        kerb_generator = RG_KerbGenerator()
        sidewalk_generator = RG_SidewalkGenerator()
        object_generator = RG_ObjectGenerator()

        for road in road_generator.roads:
            for side in ["Left", "Right"]:
                kerb_generator.add_geometry(road=road, side=side)
                offset = road.kerb_mesh_template.dimensions[1]
                sidewalk_generator.add_geometry(road=road, side=side, offset=offset)
                object_generator.add_geometry(road=road, side=side)

        # Visualize crossroads in Blender
        crossroad_generator = RG_CrossroadGenerator(kerb_generator, sidewalk_generator)

        for crossing_point in crossing_points():
            crossroad_generator.add_geometry(crossing_point)

        # sidewalk_generator.correct_sidewalks()

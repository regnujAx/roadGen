from time import time

from .crossroad_generator import RG_CrossroadGenerator
from .data_generator import RG_DataGenerator
from .graph_to_net_generator import RG_GraphToNetGenerator
from .kerb_generator import RG_KerbGenerator
from .object_generator import RG_ObjectGenerator
from .road_generator import RG_RoadGenerator
from .sidewalk_generator import RG_SidewalkGenerator
from ..utils.collection_management import crossing_points, objects_from_collection
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

        print("\n\n--- Starting road net generation ---")

        # Create road data
        print("\n- Starting generation of road data -")

        t = time()

        datamanager = RG_DataGenerator(curves)
        datamanager.create_road_data()

        print(f"Road data generation completed in {time() - t:.2f}s")

        # Visualize roads in Blender
        print("\n- Starting generation of roads -")

        t = time()

        road_generator = RG_RoadGenerator()
        for curve in curves:
            road_generator.add_geometry(curve)

        roads = road_generator.roads

        print(f"Road generation ({len(roads)} in total) completed in {time() - t:.2f}s")

        # Visualize kerbs in Blender
        kerb_generator = RG_KerbGenerator()
        add_geometry_and_measure_time(kerb_generator, roads, "kerb")

        # Visualize sidewalks in Blender
        offset = kerb_generator.mesh_template.dimensions[1]
        sidewalk_generator = RG_SidewalkGenerator(offset=offset)
        add_geometry_and_measure_time(sidewalk_generator, roads, "sidewalk")

        # Visualize objects in Blender
        object_generator = RG_ObjectGenerator()
        add_geometry_and_measure_time(object_generator, roads, "object")

        # Visualize crossroads in Blender
        print("\n- Starting generation of crossroads -")

        t = time()

        crossroad_points = crossing_points()
        crossroad_generator = RG_CrossroadGenerator(kerb_generator, sidewalk_generator)

        for crossroad_point in crossroad_points:
            crossroad_generator.add_geometry(crossroad_point)

        print(f"Crossroad generation ({len(crossroad_points)} in total) completed in {time() - t:.2f}s")

        # sidewalk_generator.correct_sidewalks()


# ------------------------------------------------------------------------
#    Helper Method
# ------------------------------------------------------------------------


def add_geometry_and_measure_time(generator, roads: list, geometry_type: str):
    print(f"\n- Starting generation of {geometry_type}s -")

    counter = 0
    t = time()

    for road in roads:
        for side in ["Left", "Right"]:
            generator.add_geometry(road=road, side=side)
            counter += 1

        if counter % 10 == 0 and geometry_type != "object":
            print(f"\t{counter} {geometry_type}s added")

    subcollections = True if geometry_type == "sidewalk" else False
    objects = objects_from_collection(f"{generator.mesh_template.name}s", subcollections)

    print(f"{geometry_type.title()} generation ({len(objects)} in total) completed in {time() - t:.2f}s")

from time import time

from roadGen.generators.building_generator import RG_BuildingGenerator
from roadGen.generators.crossroad_generator import RG_CrossroadGenerator
from roadGen.generators.data_generator import RG_DataGenerator
from roadGen.generators.graph_to_net_generator import RG_GraphToNetGenerator
from roadGen.generators.kerb_generator import RG_KerbGenerator
from roadGen.generators.lot_generator import RG_LotGenerator
from roadGen.generators.road_furniture_generator import RG_RoadFurnitureGenerator
from roadGen.generators.road_generator import RG_RoadGenerator
from roadGen.generators.sidewalk_generator import RG_SidewalkGenerator
from roadGen.utils.collection_management import count_objects_in_collections, get_crossing_curves, get_crossing_points
from roadGen.utils.curve_management import get_visible_curves


class RG_RoadNetGenerator:
    def __init__(self, graph=None):
        self.graph = graph

    def generate(self):
        # Visualize the graph in Blender
        if self.graph:
            graph_to_net_generator = RG_GraphToNetGenerator(self.graph)
            graph_to_net_generator.generate()

        curves = get_visible_curves()

        start = time()

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
        add_geometry_with_roads_and_measure_time(kerb_generator, roads, "kerb")

        # Visualize sidewalks in Blender
        offset = kerb_generator.mesh_template.dimensions[1]
        sidewalk_generator = RG_SidewalkGenerator(offset=offset)
        add_geometry_with_roads_and_measure_time(sidewalk_generator, roads, "sidewalk")

        # Visualize crossroads in Blender
        crossroad_points = get_crossing_points()

        if crossroad_points:
            print("\n- Starting generation of crossroads -")

            counter = 0
            t = time()

            crossroad_generator = RG_CrossroadGenerator()

            for crossroad_point in crossroad_points:
                # Get the original curves to generate the crossroad as such to check if there are more than one
                curves = get_crossing_curves(crossroad_point)

                if len(curves) > 1:
                    crossroad_generator.add_geometry(curves, crossroad_point)

                    # Get the curves of the crossroad to generate kerbs and sidewalks
                    crossroad_curves = crossroad_generator.crossroads[f"Crossroad_{crossroad_point.name}"]

                    for curve in crossroad_curves:
                        kerb_generator.add_geometry(curve=curve)
                        sidewalk_generator.add_geometry(curve=curve)

                    counter += 1

                if counter % 10 == 0:
                    print(f"\t{counter} crossroads added")

            print(f"Crossroad generation ({counter} in total) completed in {time() - t:.2f}s")

        # sidewalk_generator.correct_sidewalks()

        # Visualize road furniture in Blender
        road_furniture_generator = RG_RoadFurnitureGenerator(["Street Lamp", "Street Name Sign", "Traffic Light", "Traffic Sign"])
        add_geometry_with_roads_and_measure_time(road_furniture_generator, roads, "road furniture object")

        # Visualize lots (areas between the roads) in Blender
        lot_generator = RG_LotGenerator(roads)
        add_geometry_and_measure_time(lot_generator, "lot")

        # Visualize buildings in Blender
        building_generator = RG_BuildingGenerator(lot_generator.lots)
        add_geometry_and_measure_time(building_generator, "building")

        print(f"\n--- Overall road net generation time: {time() - start:.2f}s ---")


# ------------------------------------------------------------------------
#    Helper Method
# ------------------------------------------------------------------------


def add_geometry_and_measure_time(generator, geometry_type: str):
    t = time()

    generator.add_geometry()

    plural_geometry_type = geometry_type + "s"
    generated_meshes = getattr(generator, plural_geometry_type)

    if generated_meshes:
        print(f"\n- Starting generation of {geometry_type}s -")
        print(f"{geometry_type.capitalize()} generation ({len(generated_meshes)} in total) completed in {time() - t:.2f}s")


def add_geometry_with_roads_and_measure_time(generator, roads: list, geometry_type: str):
    print(f"\n- Starting generation of {geometry_type}s -")

    counter = 0
    t = time()

    for road in roads:
        for side in ["Left", "Right"]:
            generator.add_geometry(road=road, side=side)
            counter += 1

        if counter % 10 == 0 and geometry_type != "road furniture object":
            print(f"\t{counter} {geometry_type}s added")

    with_subcollections = False if geometry_type == "sidewalk" else True

    if geometry_type == "road furniture object":
        collection_names = [object_name + "s" for object_name in generator.road_furniture_object_names]
        emptys = True
    else:
        collection_names = [f"{generator.mesh_template.name}s"]
        emptys = False

    generated_objects_number = count_objects_in_collections(collection_names, with_subcollections, emptys)

    print(f"{geometry_type.capitalize()} generation ({generated_objects_number} in total) completed in {time() - t:.2f}s")

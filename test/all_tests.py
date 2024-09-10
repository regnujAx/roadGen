# Run in a command line tool (like git bash):
# "C:\Program Files\Blender Foundation\Blender 3.6\blender.exe" -b -noaudio --addons roadGen --python test/all_tests.py -- -v

import bpy
import unittest

from roadGen.generators.data_generator import RG_DataGenerator
from roadGen.generators.road_generator import RG_RoadGenerator
from roadGen.generators.kerb_generator import RG_KerbGenerator
from roadGen.generators.sidewalk_generator import RG_SidewalkGenerator
from roadGen.generators.crossroad_generator import RG_CrossroadGenerator
from roadGen.utils.collection_management import crossing_points, delete_collections_with_objects
from roadGen.utils.curve_management import visible_curves


# ------------------------------------------------------------------------
#    Helper Methods
# ------------------------------------------------------------------------


def add_kerbs(roads: list):
    kerb_generator = RG_KerbGenerator()

    for road in roads:
        for side in ["Left", "Right"]:
            kerb_generator.add_geometry(road=road, side=side)


def cleanup():
    for collection_name in ["Crossroads", "Kerbs", "Line Meshes", "Road Lanes"]:
        collection = bpy.data.collections.get(collection_name)

        if collection is not None:
            # Find all objects in the collection, delete them and delete the collection
            objects = [obj for obj in collection.objects]

            while objects:
                bpy.data.objects.remove(objects.pop())

            bpy.data.collections.remove(collection)


def delete_custom_properties(object: bpy.types.Object):
    for custom_prop_name in list(object.keys()):
        del object[custom_prop_name]


# ------------------------------------------------------------------------
#    Tests
# ------------------------------------------------------------------------


class TestRoadDataCreation(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.open_mainfile(filepath="test/test_data/test_scene.blend")

        self.curve = bpy.data.objects.get("Curve_000")
        self.datamanager = RG_DataGenerator([self.curve])

        bpy.ops.object.select_all(action="DESELECT")

        delete_custom_properties(self.curve)

    def test_roadDataCreationWithNoInitialData(self):
        self.assertIsNone(self.curve.get("Lane Width"))
        self.assertIsNone(self.curve.get("Left Lanes"))
        self.assertIsNone(self.curve.get("Right Lanes"))
        self.assertIsNone(self.curve.get("Lamp Distance"))
        self.assertIsNone(self.curve.get("Left Dropped Kerbs"))
        self.assertIsNone(self.curve.get("Right Dropped Kerbs"))

        self.datamanager.create_road_data()

        self.assertEqual(self.curve["Lane Width"], 2.5)
        self.assertEqual(self.curve["Left Lanes"], 1)
        self.assertEqual(self.curve["Right Lanes"], 1)
        self.assertEqual(self.curve["Lamp Distance"], 10.0)
        self.assertEqual(self.curve["Left Dropped Kerbs"], "5")
        self.assertEqual(self.curve["Right Dropped Kerbs"], "15,30")

    def test_roadDataCreationWithInitialData(self):
        self.datamanager.create_road_data()

        self.curve["Left Lanes"] = 2
        self.curve["Right Lanes"] = 2
        self.curve["Lamp Distance"] = 50.0

        self.datamanager.create_road_data()

        self.assertEqual(self.curve["Lane Width"], 2.5)
        self.assertEqual(self.curve["Left Lanes"], 2)
        self.assertEqual(self.curve["Right Lanes"], 2)
        self.assertEqual(self.curve["Lamp Distance"], 50.0)
        self.assertEqual(self.curve["Left Dropped Kerbs"], "5")
        self.assertEqual(self.curve["Right Dropped Kerbs"], "15,30")


class TestRoadCreationAndDeletion(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.open_mainfile(filepath="test/test_data/test_scene.blend")

        self.curve = bpy.data.objects.get("Curve_000")
        self.curves = visible_curves()

        cleanup()
        self.datamanager = RG_DataGenerator(self.curves)
        self.datamanager.create_road_data()
        self.road_generator = RG_RoadGenerator()

    def test_assignAndCreateOneRoad(self):
        self.road_generator.add_geometry(self.curve)

        add_kerbs(self.road_generator.roads)

        self.assertIsNotNone(bpy.data.objects.get("Road_Lane_Left_Curve_000"))
        self.assertIsNotNone(bpy.data.objects.get("Road_Lane_Right_Curve_000"))
        self.assertIsNotNone(bpy.data.objects.get("Kerb_Left_Curve_000"))
        self.assertIsNotNone(bpy.data.objects.get("Kerb_Right_Curve_000"))
        self.assertIsNotNone(bpy.data.objects.get("Line_Mesh_Kerb_Left_Curve_000"))
        self.assertIsNotNone(bpy.data.objects.get("Line_Mesh_Kerb_Right_Curve_000"))

    def test_CreateAllRoads(self):
        for curve in self.curves:
            self.road_generator.add_geometry(curve)

        add_kerbs(self.road_generator.roads)

        self.assertIsNotNone(bpy.data.objects.get("Road_Lane_Left_Curve_000"))
        self.assertIsNotNone(bpy.data.objects.get("Road_Lane_Left_Curve_001"))
        self.assertIsNotNone(bpy.data.objects.get("Road_Lane_Left_Curve_002"))
        self.assertIsNotNone(bpy.data.objects.get("Road_Lane_Left_Curve_003"))

    def test_deleteAll(self):
        for curve in self.curves:
            self.road_generator.add_geometry(curve)

        add_kerbs(self.road_generator.roads)

        self.assertIsNotNone(bpy.data.collections.get("Road Lanes"))
        self.assertIsNotNone(bpy.data.collections.get("Kerbs"))
        self.assertIsNotNone(bpy.data.collections.get("Line Meshes"))

        collections = ["Kerbs", "Line Meshes", "Road Lanes"]

        delete_collections_with_objects(collections)

        self.assertIsNone(bpy.data.collections.get("Road Lanes"))
        self.assertIsNone(bpy.data.collections.get("Kerbs"))
        self.assertIsNone(bpy.data.collections.get("Line Meshes"))

    def test_CreateAllOperator(self):
        bpy.ops.rg.create_all()

        self.assertIsNotNone(bpy.data.objects.get("Road_Lane_Left_Curve_000"))
        self.assertIsNotNone(bpy.data.objects.get("Road_Lane_Left_Curve_001"))
        self.assertIsNotNone(bpy.data.objects.get("Road_Lane_Left_Curve_002"))
        self.assertIsNotNone(bpy.data.objects.get("Road_Lane_Left_Curve_003"))

    def test_deleteAllOperator(self):
        for curve in self.curves:
            self.road_generator.add_geometry(curve)

        add_kerbs(self.road_generator.roads)

        self.assertIsNotNone(bpy.data.collections.get("Road Lanes"))
        self.assertIsNotNone(bpy.data.collections.get("Kerbs"))
        self.assertIsNotNone(bpy.data.collections.get("Line Meshes"))

        bpy.ops.rg.delete_all()

        self.assertIsNone(bpy.data.collections.get("Road Lanes"))
        self.assertIsNone(bpy.data.collections.get("Kerbs"))
        self.assertIsNone(bpy.data.collections.get("Line Meshes"))


class TestCrossroadCreation(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.open_mainfile(filepath="test/test_data/test_scene.blend")

        self.crossroad_points = crossing_points()
        self.curves = visible_curves()

        cleanup()
        self.datamanager = RG_DataGenerator(self.curves)
        self.datamanager.create_road_data()
        self.road_generator = RG_RoadGenerator()

        for curve in self.curves:
            self.road_generator.add_geometry(curve)

        self.kerb_generator = RG_KerbGenerator()
        self.sidewalk_generator = RG_SidewalkGenerator()

    def test_createCrossroad(self):
        crossroad_generator = RG_CrossroadGenerator(self.kerb_generator, self.sidewalk_generator)

        for crossroad_point in self.crossroad_points:
            crossroad_generator.add_geometry(crossroad_point)

        self.assertIsNotNone(bpy.data.collections.get("Crossroads"))

        for node in self.crossroad_points:
            self.assertIsNotNone(bpy.data.objects.get(f"Crossroad_{node.name}"))


if __name__ == "__main__":
    import sys

    sys.argv = [__file__] + (sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    unittest.main()

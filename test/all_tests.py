# Run in a command line tool (like git bash):
# "C:\Program Files\Blender Foundation\Blender 3.6\blender.exe" -b -noaudio
# --addons roadGen --python test\all_tests.py -- -v

import bpy
import unittest

from roadGen.generators.data_generator import RG_DataGenerator
from roadGen.generators.road_generator import RG_RoadGenerator
from roadGen.generators.kerb_generator import RG_KerbGenerator
from roadGen.generators.crossroad_generator import RG_CrossroadGenerator
from roadGen.utils.collection_management import delete_collections_with_objects
from roadGen.utils.curve_management import visible_curves


# ------------------------------------------------------------------------
#    Helper Methods
# ------------------------------------------------------------------------


def add_kerbs(roads: list):
    for road in roads:
        kerb_generator = RG_KerbGenerator(road=road)
        for side in ["Left", "Right"]:
            kerb_generator.add_kerb(side)


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

        self.curve1 = bpy.data.objects.get("BezierCurve")
        self.curve2 = bpy.data.objects.get("BezierCurve.001")
        self.datamanager = RG_DataGenerator()

        bpy.ops.object.select_all(action="DESELECT")

        delete_custom_properties(self.curve1)
        delete_custom_properties(self.curve2)

    def test_roadDataCreationWithNoInitialData(self):
        self.assertIsNone(self.curve1.get("Lane Width"))
        self.assertIsNone(self.curve1.get("Left Lanes"))
        self.assertIsNone(self.curve1.get("Right Lanes"))
        self.assertIsNone(self.curve1.get("Lamp Distance"))
        self.assertIsNone(self.curve1.get("Left Dropped Kerbs"))
        self.assertIsNone(self.curve1.get("Right Dropped Kerbs"))

        self.datamanager.create_road_data()

        self.assertEqual(self.curve1["Lane Width"], 2.5)
        self.assertEqual(self.curve1["Left Lanes"], 1)
        self.assertEqual(self.curve1["Right Lanes"], 1)
        self.assertEqual(self.curve1["Lamp Distance"], 10.0)
        self.assertEqual(self.curve1["Left Dropped Kerbs"], "5")
        self.assertEqual(self.curve1["Right Dropped Kerbs"], "15,30")

    def test_roadDataCreationWithInitialData(self):
        self.datamanager.create_road_data()

        self.curve2["Left Lanes"] = 2
        self.curve2["Right Lanes"] = 2
        self.curve2["Lamp Distance"] = 50.0

        self.datamanager.create_road_data()

        self.assertEqual(self.curve2["Lane Width"], 2.5)
        self.assertEqual(self.curve2["Left Lanes"], 2)
        self.assertEqual(self.curve2["Right Lanes"], 2)
        self.assertEqual(self.curve2["Lamp Distance"], 50.0)
        self.assertEqual(self.curve2["Left Dropped Kerbs"], "5")
        self.assertEqual(self.curve2["Right Dropped Kerbs"], "15,30")

    def test_roadDataCreationOperatorWithNoInitialData(self):
        self.assertIsNone(self.curve1.get("Lane Width"))
        self.assertIsNone(self.curve1.get("Left Lanes"))
        self.assertIsNone(self.curve1.get("Right Lanes"))
        self.assertIsNone(self.curve1.get("Lamp Distance"))
        self.assertIsNone(self.curve1.get("Left Dropped Kerbs"))
        self.assertIsNone(self.curve1.get("Right Dropped Kerbs"))

        bpy.ops.rg.create_road_data()

        self.assertEqual(self.curve1["Lane Width"], 2.5)
        self.assertEqual(self.curve1["Left Lanes"], 1)
        self.assertEqual(self.curve1["Right Lanes"], 1)
        self.assertEqual(self.curve1["Lamp Distance"], 10.0)
        self.assertEqual(self.curve1["Left Dropped Kerbs"], "5")
        self.assertEqual(self.curve1["Right Dropped Kerbs"], "15,30")

    def test_roadDataCreationOperatorWithInitialData(self):
        bpy.ops.rg.create_road_data()

        self.curve2["Left Lanes"] = 2
        self.curve2["Right Lanes"] = 2
        self.curve2["Lamp Distance"] = 50.0

        bpy.ops.rg.create_road_data()

        self.assertEqual(self.curve2["Lane Width"], 2.5)
        self.assertEqual(self.curve2["Left Lanes"], 2)
        self.assertEqual(self.curve2["Right Lanes"], 2)
        self.assertEqual(self.curve2["Lamp Distance"], 50.0)
        self.assertEqual(self.curve2["Left Dropped Kerbs"], "5")
        self.assertEqual(self.curve2["Right Dropped Kerbs"], "15,30")


class TestRoadCreationAndDeletion(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.open_mainfile(filepath="test/test_data/test_scene.blend")

        self.collection = bpy.data.collections.get("TestCollection")
        self.curve = bpy.data.objects.get("BezierCurve")
        self.curves = visible_curves()
        self.road_properties = bpy.context.scene.road_props

        cleanup()
        bpy.ops.rg.create_road_data()

    def test_assignAndCreateOneRoad(self):
        road_generator_one_curve = RG_RoadGenerator([self.curve])
        road_generator_one_curve.add_roads()

        add_kerbs(road_generator_one_curve.roads)

        self.assertIsNotNone(bpy.data.objects.get("Road_Lane_Left_BezierCurve"))
        self.assertIsNotNone(bpy.data.objects.get("Road_Lane_Right_BezierCurve"))
        self.assertIsNotNone(bpy.data.objects.get("Kerb_Left_BezierCurve"))
        self.assertIsNotNone(bpy.data.objects.get("Kerb_Right_BezierCurve"))
        self.assertIsNotNone(bpy.data.objects.get("Line_Mesh_Kerb_Left_BezierCurve"))
        self.assertIsNotNone(bpy.data.objects.get("Line_Mesh_Kerb_Right_BezierCurve"))

    def test_assignAndCreateOneCollection(self):
        curves = [obj for obj in self.collection.objects if obj.type == "CURVE" and obj.visible_get()]

        road_generator_one_collection = RG_RoadGenerator(curves)
        road_generator_one_collection.add_roads()

        add_kerbs(road_generator_one_collection.roads)

        self.assertIsNotNone(bpy.data.objects.get("Road_Lane_Left_BezierCurve_001"))
        self.assertIsNotNone(bpy.data.objects.get("Road_Lane_Left_RoadLine"))

    def test_CreateAllRoads(self):
        road_generator_all_curves = RG_RoadGenerator(self.curves)
        road_generator_all_curves.add_roads()

        add_kerbs(road_generator_all_curves.roads)

        self.assertIsNotNone(bpy.data.objects.get("Road_Lane_Left_BezierCurve"))
        self.assertIsNotNone(bpy.data.objects.get("Road_Lane_Left_BezierCurve_001"))
        self.assertIsNotNone(bpy.data.objects.get("Road_Lane_Left_RoadLine"))

    def test_deleteAll(self):
        road_generator_all_curves = RG_RoadGenerator(self.curves)
        road_generator_all_curves.add_roads()

        add_kerbs(road_generator_all_curves.roads)

        self.assertIsNotNone(bpy.data.collections.get("Road Lanes"))
        self.assertIsNotNone(bpy.data.collections.get("Kerbs"))
        self.assertIsNotNone(bpy.data.collections.get("Line Meshes"))

        collections = ["Kerbs", "Line Meshes", "Road Lanes"]

        delete_collections_with_objects(collections)

        self.assertIsNone(bpy.data.collections.get("Road Lanes"))
        self.assertIsNone(bpy.data.collections.get("Kerbs"))
        self.assertIsNone(bpy.data.collections.get("Line Meshes"))

    def test_assignAndCreateOneRoadOperator(self):
        self.road_properties.curve = self.curve

        bpy.ops.rg.create_one_road()

        self.assertIsNotNone(bpy.data.objects.get("Road_Lane_Left_BezierCurve"))
        self.assertIsNotNone(bpy.data.objects.get("Road_Lane_Right_BezierCurve"))
        self.assertIsNotNone(bpy.data.objects.get("Kerb_Left_BezierCurve"))
        self.assertIsNotNone(bpy.data.objects.get("Kerb_Right_BezierCurve"))
        self.assertIsNotNone(bpy.data.objects.get("Line_Mesh_Kerb_Left_BezierCurve"))
        self.assertIsNotNone(bpy.data.objects.get("Line_Mesh_Kerb_Right_BezierCurve"))

    def test_assignAndCreateOneCollectionOperator(self):
        self.road_properties.collection = self.collection

        bpy.ops.rg.create_roads_from_collection()

        self.assertIsNotNone(bpy.data.objects.get("Road_Lane_Left_BezierCurve_001"))
        self.assertIsNotNone(bpy.data.objects.get("Road_Lane_Left_RoadLine"))

    def test_CreateAllRoadsOperator(self):
        bpy.ops.rg.create_roads()

        self.assertIsNotNone(bpy.data.objects.get("Road_Lane_Left_BezierCurve"))
        self.assertIsNotNone(bpy.data.objects.get("Road_Lane_Left_BezierCurve_001"))
        self.assertIsNotNone(bpy.data.objects.get("Road_Lane_Left_RoadLine"))

    def test_deleteAllOperator(self):
        bpy.ops.rg.create_roads()

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

        self.crossroadCollection = bpy.data.collections.get("CrossroadCollection")
        self.nodesCollection = bpy.data.collections.get("Nodes")

        cleanup()
        bpy.ops.rg.create_road_data()
        bpy.ops.rg.create_roads()

    def test_createCrossroad(self):
        crossroad_generator = RG_CrossroadGenerator()
        crossroad_generator.add_crossroads()

        self.assertIsNotNone(bpy.data.collections.get("Crossroads"))
        for node in self.nodesCollection.objects:
            self.assertIsNotNone(bpy.data.objects.get(f"Crossroad_{node.name}"))

    def test_createCrossroadOperator(self):
        bpy.ops.rg.create_crossroads()

        self.assertIsNotNone(bpy.data.collections.get("Crossroads"))
        for node in self.nodesCollection.objects:
            self.assertIsNotNone(bpy.data.objects.get(f"Crossroad_{node.name}"))


if __name__ == "__main__":
    import sys

    sys.argv = [__file__] + (sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    unittest.main()

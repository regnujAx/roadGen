# Run in a command line tool (like git bash):
# 'C:\Program Files\Blender Foundation\Blender 3.6\blender.exe' -b -noaudio --addons cityGen --python test\all_tests.py -- -v

import bpy
import unittest

from cityGen.datamanager import CG_DataManager
from cityGen.generators.roadGenerator import CG_RoadGenerator
from cityGen.generators.crossroadGenerator import CG_CrossroadGenerator
from cityGen.util import delete, get_visible_curves


def cleanup():
    for collection_name in ["Crossroads", "Kerbs", "Line Meshes", "Road Lanes"]:
        collection = bpy.data.collections.get(collection_name)

        if collection is not None:
            # Find all objects in the collection, delete them and delete the collection
            objects = [obj for obj in collection.objects]

            while objects:
                bpy.data.objects.remove(objects.pop())

            bpy.data.collections.remove(collection)


def deleteCustomProperties(object):
    for custom_prop_name in list(object.keys()):
        del object[custom_prop_name]


class TestRoadDataCreation(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.open_mainfile(filepath="test/test_data/test_scene.blend")

        self.curve1 = bpy.data.objects.get("BezierCurve")
        self.curve2 = bpy.data.objects.get("BezierCurve.001")
        self.datamanager = CG_DataManager()

        bpy.ops.object.select_all(action="DESELECT")

        deleteCustomProperties(self.curve1)
        deleteCustomProperties(self.curve2)

    def test_roadDataCreationWithNoInitialData(self):
        self.assertIsNone(self.curve1.get("Lane Width"))
        self.assertIsNone(self.curve1.get("Left Lanes"))
        self.assertIsNone(self.curve1.get("Right Lanes"))
        self.assertIsNone(self.curve1.get("Lantern Distance"))
        self.assertIsNone(self.curve1.get("Left Dropped Kerbs"))
        self.assertIsNone(self.curve1.get("Right Dropped Kerbs"))

        self.datamanager.createRoadData()

        self.assertEqual(self.curve1["Lane Width"], 2.5)
        self.assertEqual(self.curve1["Left Lanes"], 1)
        self.assertEqual(self.curve1["Right Lanes"], 1)
        self.assertEqual(self.curve1["Lantern Distance"], 10.0)
        self.assertEqual(self.curve1["Left Dropped Kerbs"], "5")
        self.assertEqual(self.curve1["Right Dropped Kerbs"], "15,30")

    def test_roadDataCreationWithInitialData(self):
        self.datamanager.createRoadData()

        self.curve2["Left Lanes"] = 2
        self.curve2["Right Lanes"] = 2
        self.curve2["Lantern Distance"] = 50.0

        self.datamanager.createRoadData()

        self.assertEqual(self.curve2["Lane Width"], 2.5)
        self.assertEqual(self.curve2["Left Lanes"], 2)
        self.assertEqual(self.curve2["Right Lanes"], 2)
        self.assertEqual(self.curve2["Lantern Distance"], 50.0)
        self.assertEqual(self.curve2["Left Dropped Kerbs"], "5")
        self.assertEqual(self.curve2["Right Dropped Kerbs"], "15,30")

    def test_roadDataCreationOperatorWithNoInitialData(self):
        self.assertIsNone(self.curve1.get("Lane Width"))
        self.assertIsNone(self.curve1.get("Left Lanes"))
        self.assertIsNone(self.curve1.get("Right Lanes"))
        self.assertIsNone(self.curve1.get("Lantern Distance"))
        self.assertIsNone(self.curve1.get("Left Dropped Kerbs"))
        self.assertIsNone(self.curve1.get("Right Dropped Kerbs"))

        bpy.ops.cg.create_road_data()

        self.assertEqual(self.curve1["Lane Width"], 2.5)
        self.assertEqual(self.curve1["Left Lanes"], 1)
        self.assertEqual(self.curve1["Right Lanes"], 1)
        self.assertEqual(self.curve1["Lantern Distance"], 10.0)
        self.assertEqual(self.curve1["Left Dropped Kerbs"], "5")
        self.assertEqual(self.curve1["Right Dropped Kerbs"], "15,30")

    def test_roadDataCreationOperatorWithInitialData(self):
        bpy.ops.cg.create_road_data()

        self.curve2["Left Lanes"] = 2
        self.curve2["Right Lanes"] = 2
        self.curve2["Lantern Distance"] = 50.0

        bpy.ops.cg.create_road_data()

        self.assertEqual(self.curve2["Lane Width"], 2.5)
        self.assertEqual(self.curve2["Left Lanes"], 2)
        self.assertEqual(self.curve2["Right Lanes"], 2)
        self.assertEqual(self.curve2["Lantern Distance"], 50.0)
        self.assertEqual(self.curve2["Left Dropped Kerbs"], "5")
        self.assertEqual(self.curve2["Right Dropped Kerbs"], "15,30")


class TestRoadCreationAndDeletion(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.open_mainfile(filepath="test/test_data/test_scene.blend")

        self.collection = bpy.data.collections.get("TestCollection")
        self.curve = bpy.data.objects.get("BezierCurve")
        self.curves = get_visible_curves()
        self.road_properties = bpy.context.scene.road_props

        cleanup()
        bpy.ops.cg.create_road_data()

    def test_assignAndCreateOneRoad(self):
        road_generator_one_curve = CG_RoadGenerator([self.curve])
        road_generator_one_curve.add_roads()

        self.assertIsNotNone(bpy.data.objects.get("Road_Lane_Left_BezierCurve"))
        self.assertIsNotNone(bpy.data.objects.get("Road_Lane_Right_BezierCurve"))
        self.assertIsNotNone(bpy.data.objects.get("Kerb_Left_BezierCurve"))
        self.assertIsNotNone(bpy.data.objects.get("Kerb_Right_BezierCurve"))
        self.assertIsNotNone(bpy.data.objects.get("Line_Mesh_Kerb_Left_BezierCurve"))
        self.assertIsNotNone(bpy.data.objects.get("Line_Mesh_Kerb_Right_BezierCurve"))

    def test_assignAndCreateOneCollection(self):
        curves = [obj for obj in self.collection.objects if obj.type == "CURVE" and obj.visible_get()]
        road_generator_one_collection = CG_RoadGenerator(curves)
        road_generator_one_collection.add_roads()

        self.assertIsNotNone(bpy.data.objects.get("Road_Lane_Left_BezierCurve_001"))
        self.assertIsNotNone(bpy.data.objects.get("Road_Lane_Left_RoadLine"))

    def test_CreateAllRoads(self):
        road_generator_all_curves = CG_RoadGenerator(self.curves)
        road_generator_all_curves.add_roads()

        self.assertIsNotNone(bpy.data.objects.get("Road_Lane_Left_BezierCurve"))
        self.assertIsNotNone(bpy.data.objects.get("Road_Lane_Left_BezierCurve_001"))
        self.assertIsNotNone(bpy.data.objects.get("Road_Lane_Left_RoadLine"))

    def test_deleteAll(self):
        road_generator_all_curves = CG_RoadGenerator(self.curves)
        road_generator_all_curves.add_roads()

        self.assertIsNotNone(bpy.data.collections.get("Road Lanes"))
        self.assertIsNotNone(bpy.data.collections.get("Kerbs"))
        self.assertIsNotNone(bpy.data.collections.get("Line Meshes"))

        collections = ["Kerbs", "Line Meshes", "Road Lanes"]

        delete(collections)

        self.assertIsNone(bpy.data.collections.get("Road Lanes"))
        self.assertIsNone(bpy.data.collections.get("Kerbs"))
        self.assertIsNone(bpy.data.collections.get("Line Meshes"))

    def test_assignAndCreateOneRoadOperator(self):
        self.road_properties.curve = self.curve

        bpy.ops.cg.create_one_road()

        self.assertIsNotNone(bpy.data.objects.get("Road_Lane_Left_BezierCurve"))
        self.assertIsNotNone(bpy.data.objects.get("Road_Lane_Right_BezierCurve"))
        self.assertIsNotNone(bpy.data.objects.get("Kerb_Left_BezierCurve"))
        self.assertIsNotNone(bpy.data.objects.get("Kerb_Right_BezierCurve"))
        self.assertIsNotNone(bpy.data.objects.get("Line_Mesh_Kerb_Left_BezierCurve"))
        self.assertIsNotNone(bpy.data.objects.get("Line_Mesh_Kerb_Right_BezierCurve"))

    def test_assignAndCreateOneCollectionOperator(self):
        self.road_properties.collection = self.collection

        bpy.ops.cg.create_roads_from_collection()

        self.assertIsNotNone(bpy.data.objects.get("Road_Lane_Left_BezierCurve_001"))
        self.assertIsNotNone(bpy.data.objects.get("Road_Lane_Left_RoadLine"))

    def test_CreateAllRoadsOperator(self):
        bpy.ops.cg.create_roads()

        self.assertIsNotNone(bpy.data.objects.get("Road_Lane_Left_BezierCurve"))
        self.assertIsNotNone(bpy.data.objects.get("Road_Lane_Left_BezierCurve_001"))
        self.assertIsNotNone(bpy.data.objects.get("Road_Lane_Left_RoadLine"))

    def test_deleteAllOperator(self):
        bpy.ops.cg.create_roads()

        self.assertIsNotNone(bpy.data.collections.get("Road Lanes"))
        self.assertIsNotNone(bpy.data.collections.get("Kerbs"))
        self.assertIsNotNone(bpy.data.collections.get("Line Meshes"))

        bpy.ops.cg.delete_all()

        self.assertIsNone(bpy.data.collections.get("Road Lanes"))
        self.assertIsNone(bpy.data.collections.get("Kerbs"))
        self.assertIsNone(bpy.data.collections.get("Line Meshes"))


class TestCrossroadCreation(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.open_mainfile(filepath="test/test_data/test_scene.blend")

        self.crossroadCollection = bpy.data.collections.get("CrossroadCollection")
        self.nodesCollection = bpy.data.collections.get("Nodes")

        cleanup()
        bpy.ops.cg.create_road_data()
        bpy.ops.cg.create_roads()

    def test_createCrossroad(self):
        crossroad_generator = CG_CrossroadGenerator()
        crossroad_generator.add_crossroads()

        self.assertIsNotNone(bpy.data.collections.get("Crossroads"))
        for node in self.nodesCollection.objects:
            self.assertIsNotNone(bpy.data.objects.get(f"Crossroad_{node.name}"))

    def test_createCrossroadOperator(self):
        bpy.ops.cg.create_crossroads()

        self.assertIsNotNone(bpy.data.collections.get("Crossroads"))
        for node in self.nodesCollection.objects:
            self.assertIsNotNone(bpy.data.objects.get(f"Crossroad_{node.name}"))


if __name__ == '__main__':
    import sys

    sys.argv = [__file__] + (sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    unittest.main()

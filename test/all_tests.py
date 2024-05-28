# Run in a command line tool (like git bash):
# 'C:\Program Files\Blender Foundation\Blender 3.6\blender.exe' -b -noaudio
# --addons cityGen --python test\all_tests.py -- -v

import unittest
import bpy


def deleteCustomProperties(object):
    for custom_prop_name in list(object.keys()):
        del object[custom_prop_name]


def cleanup():
    for collection_name in ["Road Lanes", "Kerbs", "Line Meshes"]:
        collection = bpy.data.collections.get(collection_name)

        if collection is not None:
            # Find all objects in the collection, delete them and delete the collection
            objects = [obj for obj in collection.objects]

            while objects:
                bpy.data.objects.remove(objects.pop())

            bpy.data.collections.remove(collection)


class TestRoadDataCreation(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.open_mainfile(filepath="test/test_data/test_scene.blend")

        self.curve1 = bpy.data.objects.get("BezierCurve")
        self.curve2 = bpy.data.objects.get("BezierCurve.001")

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

        bpy.ops.cg.create_road_data()

        self.assertEqual(self.curve1["Lane Width"], 2.5)
        self.assertEqual(self.curve1["Left Lanes"], 1)
        self.assertEqual(self.curve1["Right Lanes"], 1)
        self.assertEqual(self.curve1["Lantern Distance"], 10.0)
        self.assertEqual(self.curve1["Left Dropped Kerbs"], "5")
        self.assertEqual(self.curve1["Right Dropped Kerbs"], "15,30")

    def test_roadDataCreationWithInitialData(self):
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

        self.curve = bpy.data.objects.get("BezierCurve")
        self.road_properties = bpy.context.scene.road_props
        self.collection = bpy.data.collections.get("TestCollection")

        cleanup()
        bpy.ops.cg.create_road_data()

    def test_assignAndCreateOneRoad(self):
        self.road_properties.curve = self.curve

        bpy.ops.cg.create_one_road()

        self.assertIsNotNone(bpy.data.objects.get("Road_Lane_Left_BezierCurve"))
        self.assertIsNotNone(bpy.data.objects.get("Road_Lane_Right_BezierCurve"))
        self.assertIsNotNone(bpy.data.objects.get("Kerb_Left_BezierCurve"))
        self.assertIsNotNone(bpy.data.objects.get("Kerb_Right_BezierCurve"))
        self.assertIsNotNone(bpy.data.objects.get("Line_Mesh_Kerb_Left_BezierCurve"))
        self.assertIsNotNone(bpy.data.objects.get("Line_Mesh_Kerb_Right_BezierCurve"))

    def test_assignAndCreateOneCollection(self):
        self.road_properties.collection = self.collection

        bpy.ops.cg.create_roads_from_collection()

        self.assertIsNotNone(bpy.data.objects.get("Road_Lane_Left_BezierCurve_001"))
        self.assertIsNotNone(bpy.data.objects.get("Road_Lane_Left_RoadLine"))

    def test_CreateAllRoads(self):
        bpy.ops.cg.create_roads()

        self.assertIsNotNone(bpy.data.objects.get("Road_Lane_Left_BezierCurve"))
        self.assertIsNotNone(bpy.data.objects.get("Road_Lane_Left_BezierCurve_001"))
        self.assertIsNotNone(bpy.data.objects.get("Road_Lane_Left_RoadLine"))

    def test_deleteAll(self):
        bpy.ops.cg.create_roads()

        self.assertIsNotNone(bpy.data.collections.get("Road Lanes"))
        self.assertIsNotNone(bpy.data.collections.get("Kerbs"))
        self.assertIsNotNone(bpy.data.collections.get("Line Meshes"))

        bpy.ops.cg.delete_all()

        self.assertIsNone(bpy.data.collections.get("Road Lanes"))
        self.assertIsNone(bpy.data.collections.get("Kerbs"))
        self.assertIsNone(bpy.data.collections.get("Line Meshes"))


if __name__ == '__main__':
    import sys

    sys.argv = [__file__] + (
        sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    unittest.main()

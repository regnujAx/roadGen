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
        deleteCustomProperties(self.curve1)

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
        deleteCustomProperties(self.curve2)

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

        self.curve1 = bpy.data.objects.get("BezierCurve")
        self.curve2 = bpy.data.objects.get("BezierCurve.001")
        self.road_line = bpy.data.objects.get("RoadLine")
        self.road_properties = bpy.context.scene.road_props
        self.collection = bpy.data.collections.get("TestCollection")

        cleanup()
        bpy.ops.cg.create_road_data()

    def test_assignAndCreateOneRoad(self):
        cleanup()

        self.road_properties.curve = self.curve1

        bpy.ops.cg.create_one_road()

        road_lane_left = bpy.data.objects.get("Road_Lane_Left_BezierCurve")
        road_lane_right = bpy.data.objects.get("Road_Lane_Right_BezierCurve")
        kerb_left = bpy.data.objects.get("Kerb_Left_BezierCurve")
        kerb_right = bpy.data.objects.get("Kerb_Right_BezierCurve")
        line_mesh_left = bpy.data.objects.get("Line_Mesh_Kerb_Left_BezierCurve")
        line_mesh_right = bpy.data.objects.get("Line_Mesh_Kerb_Right_BezierCurve")

        self.assertIsNotNone(road_lane_left)
        self.assertIsNotNone(road_lane_right)
        self.assertIsNotNone(kerb_left)
        self.assertIsNotNone(kerb_right)
        self.assertIsNotNone(line_mesh_left)
        self.assertIsNotNone(line_mesh_right)


    def test_assignAndCreateOneCollection(self):
        cleanup()

        self.road_properties.collection = self.collection

        bpy.ops.cg.create_roads_from_collection()

        road_lane_left_curve2 = bpy.data.objects.get("Road_Lane_Left_BezierCurve_001")
        road_lane_left_road_line = bpy.data.objects.get("Road_Lane_Left_RoadLine")

        self.assertIsNotNone(road_lane_left_curve2)
        self.assertIsNotNone(road_lane_left_road_line)

    def test_CreateAllRoads(self):
        cleanup()

        bpy.ops.cg.create_roads()

        road_lane_left = bpy.data.objects.get("Road_Lane_Left_BezierCurve")
        road_lane_left_curve2 = bpy.data.objects.get("Road_Lane_Left_BezierCurve_001")
        road_lane_left_road_line = bpy.data.objects.get("Road_Lane_Left_RoadLine")

        self.assertIsNotNone(road_lane_left)
        self.assertIsNotNone(road_lane_left_curve2)
        self.assertIsNotNone(road_lane_left_road_line)
            
    def test_deleteAll(self):
        bpy.ops.cg.create_roads()

        road_mesh_collection = bpy.data.collections.get("Road Lanes")
        kerb_mesh_collection = bpy.data.collections.get("Kerbs")
        line_mesh_collection = bpy.data.collections.get("Line Meshes")

        self.assertIsNotNone(road_mesh_collection)
        self.assertIsNotNone(kerb_mesh_collection)
        self.assertIsNotNone(line_mesh_collection)

        bpy.ops.cg.delete_all()

        deleted_road_mesh_collection = bpy.data.collections.get("Road Lanes")
        deleted_kerb_mesh_collection = bpy.data.collections.get("Kerbs")
        deleted_line_mesh_collection = bpy.data.collections.get("Line Meshes")

        self.assertIsNone(deleted_road_mesh_collection)
        self.assertIsNone(deleted_kerb_mesh_collection)
        self.assertIsNone(deleted_line_mesh_collection)


if __name__ == '__main__':
    import sys
    import os
    sys.argv = [__file__] + (
        sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    unittest.main()

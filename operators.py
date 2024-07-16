import bpy

from .generators.data_generator import CG_DataGenerator
from .generators.crossroad_generator import CG_CrossroadGenerator
from .generators.kerb_generator import CG_KerbGenerator
from .generators.road_generator import CG_RoadGenerator
from .generators.road_net_generator import CG_RoadNetGenerator
from .utils.collection_management import delete_collections_with_objects
from .utils.curve_management import visible_curves


# ------------------------------------------------------------------------
#    Operators
# ------------------------------------------------------------------------


class CG_CreateAll(bpy.types.Operator):
    """Create roads, kerbs and crossroads for all visible curves in the scene"""
    bl_label = "Create All"
    bl_idname = "cg.create_all"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        curves = visible_curves()

        road_net_generator = CG_RoadNetGenerator(curves)
        road_net_generator.create()

        return {"FINISHED"}


class CG_CreateCrossroads(bpy.types.Operator):
    """Create crossroads for all curves in the scene"""
    bl_label = "Create Crossroads"
    bl_idname = "cg.create_crossroads"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        crossroad_generator = CG_CrossroadGenerator()
        crossroad_generator.add_crossroads()

        return {"FINISHED"}


class CG_CreateOneRoad(bpy.types.Operator):
    """Create one road from a specified curve in the scene"""
    bl_label = "Create One Road"
    bl_idname = "cg.create_one_road"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        road_props = context.scene.road_props
        curve = road_props.curve

        if curve is None:
            show_message_box("No curve selected!", "Please select a curve if you want to use this feature.")
            self.report({"INFO"}, "Please select a curve if you want to use this feature.")

            return {"FINISHED"}

        road_generator = CG_RoadGenerator([curve])
        road_generator.add_roads()

        add_kerbs(road_generator.roads)

        return {"FINISHED"}


class CG_CreateRoadData(bpy.types.Operator):
    """Create road data for all visible (not hidden) curves in the scene"""
    bl_label = "Create Road Data"
    bl_idname = "cg.create_road_data"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        datamanager = CG_DataGenerator()
        datamanager.create_road_data()

        return {"FINISHED"}


class CG_CreateRoads(bpy.types.Operator):
    """Create roads from all visible (not hidden) curves in the scene"""
    bl_label = "Create All Roads"
    bl_idname = "cg.create_roads"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        curves = visible_curves()

        road_generator = CG_RoadGenerator(curves)
        road_generator.add_roads()

        add_kerbs(road_generator.roads)

        return {"FINISHED"}


class CG_CreateRoadsFromCollection(bpy.types.Operator):
    """Create roads from a specified collection"""
    bl_label = "Create Roads from Collection"
    bl_idname = "cg.create_roads_from_collection"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        road_props = context.scene.road_props
        collection = road_props.collection
        curves = [obj for obj in collection.objects if obj.type == "CURVE" and obj.visible_get()]

        if collection is None:
            show_message_box("No collection selected!", "Please select a collection if you want to use this feature.")
            self.report({"INFO"}, "Please select a collection if you want to use this feature.")

            return {"FINISHED"}

        road_generator = CG_RoadGenerator(curves)
        road_generator.add_roads()

        add_kerbs(road_generator.roads)

        return {"FINISHED"}


class CG_DeleteAll(bpy.types.Operator):
    """Delete all created meshes and the collections themselves"""
    bl_label = "Delete All"
    bl_idname = "cg.delete_all"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        collections = ["Crossroad Curves", "Crossroads", "Kerbs", "Line Meshes", "Road Lanes", "Sidewalks"]

        delete_collections_with_objects(collections)

        return {"FINISHED"}

    def invoke(self, context, event):
        wm = context.window_manager

        return wm.invoke_confirm(self, event)


# ------------------------------------------------------------------------
#    Helper Methods
# ------------------------------------------------------------------------


def show_message_box(title: str = "Message Box", message: str = "", icon: str = "INFO"):
    def draw(self, context):
        self.layout.label(text=message)

    bpy.context.window_manager.popup_menu(draw, title=title, icon=icon)


def add_kerbs(roads: list):
    for road in roads:
        kerb_generator = CG_KerbGenerator(road=road)
        kerb_generator.add_kerbs_to_road()

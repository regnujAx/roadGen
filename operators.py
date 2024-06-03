import bpy


# from . import config
from .datamanager import CG_DataManager
from .util import add_crossroads, add_roads, delete, get_visible_curves, show_message_box


# ------------------------------------------------------------------------
#    Operators
# ------------------------------------------------------------------------

class CG_CreateOneRoad(bpy.types.Operator):
    """Create one road from a specified curve in the scene"""
    bl_label = "Create One Road"
    bl_idname = "cg.create_one_road"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        road_props = context.scene.road_props
        curve = road_props.curve

        if curve is None:
            show_message_box("No curve selected!", "Please select a curve if you want to use this feature.")
            self.report({'INFO'}, "Please select a curve if you want to use this feature.")

            return {'FINISHED'}

        return add_roads([curve])


class CG_CreateRoadsFromCollection(bpy.types.Operator):
    """Create roads from a specified collection"""
    bl_label = "Create Roads from Collection"
    bl_idname = "cg.create_roads_from_collection"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        road_props = context.scene.road_props
        collection = road_props.collection
        curves = [obj for obj in collection.objects if obj.type == "CURVE" and obj.visible_get()]

        if collection is None:
            show_message_box("No collection selected!", "Please select a collection if you want to use this feature.")
            self.report({'INFO'}, "Please select a collection if you want to use this feature.")

            return {'FINISHED'}

        return add_roads(curves)


class CG_CreateRoads(bpy.types.Operator):
    """Create roads from all visible (not hidden) curves in the scene"""
    bl_label = "Create All Roads"
    bl_idname = "cg.create_roads"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        curves = get_visible_curves()

        return add_roads(curves)


class CG_CreateRoadData(bpy.types.Operator):
    """Create road data for all curves in the scene"""
    bl_label = "Create Road Data"
    bl_idname = "cg.create_road_data"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        curves = get_visible_curves()

        datamanager = CG_DataManager(curves)
        datamanager.createRoadData()

        return {'FINISHED'}


class CG_DeleteAll(bpy.types.Operator):
    """Delete all created meshes and the collections themselves"""
    bl_label = "Delete All"
    bl_idname = "cg.delete_all"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        collections = ["Crossroads", "Kerbs", "Line Meshes", "Road Lanes"]

        return delete(collections)

    def invoke(self, context, event):
        wm = context.window_manager

        return wm.invoke_confirm(self, event)


class CG_CreateCrossroads(bpy.types.Operator):
    """Create crossroads for all curves in the scene"""
    bl_label = "Create Crossroads"
    bl_idname = "cg.create_crossroads"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        return add_crossroads()

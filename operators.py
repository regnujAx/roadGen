import bpy

from roadGen.generators.road_net_generator import RG_RoadNetGenerator
from roadGen.utils.collection_management import delete_collections_with_objects, switch_collections_visibility


# ------------------------------------------------------------------------
#    Operators
# ------------------------------------------------------------------------


class RG_CreateAll(bpy.types.Operator):
    """Create roads, kerbs, crossroads and sidewalks for all visible curves in the scene"""
    bl_label = "Create All"
    bl_idname = "rg.create_all"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        road_net_generator = RG_RoadNetGenerator()
        road_net_generator.generate()

        collection_names = ["Crossing Points", "Crossroad Curves", "Line Meshes"]

        switch_collections_visibility(collection_names)

        return {"FINISHED"}


class RG_DeleteAll(bpy.types.Operator):
    """Delete all created meshes and the collections themselves"""
    bl_label = "Delete All"
    bl_idname = "rg.delete_all"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        collection_names = ["Crossroad Curves", "Crossroads", "Kerbs", "Line Meshes", "Road Lanes", "Sidewalks", "Street Lamps"]

        delete_collections_with_objects(collection_names)
        switch_collections_visibility(["Crossing Points"])

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

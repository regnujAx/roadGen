# To use this add-on you have to zip the directory containing this file (cityGen)
# and install the zip in the .blend file.
# To install the add-on open your .blend file and go to Edit -> Preferences -> Add-ons -> Install.
# Navigate to the directory where the zip-file is located that contains the cityGen directory and select it.
# The add-on should now listed and you have to enable it by clicking the checkbox.
# If you don't see it, select User in the dropdown.
# When enabled, you can use it in the 3D Viewport Object Mode.


bl_info = {
    "name": "CityGen",
    "author": "Alexander Junger",
    "version": (1, 0),
    "blender": (3, 6, 11),
    "location": "View3D > Toolbar > CityGen",
    "category": "Object",
    "description": "Generate a procedural city."
}


# ------------------------------------------------------------------------
#    General and Blender Dependent Imports
# ------------------------------------------------------------------------


import bpy
import os
import sys

from importlib import reload


# Make sure imports work even when main folder is named differently
if __name__ != "cityGen":
    sys.modules["cityGen"] = sys.modules[__name__]

# ------------------------------------------------------------------------
#    Project Dependent Imports
# ------------------------------------------------------------------------


dir = os.path.dirname(os.path.abspath(__file__))

if dir not in sys.path:
    sys.path.append(dir)


from . import (operators, properties)
from .generators import crossroad_generator, data_generator, kerb_generator, road_generator, road_net_generator
from .utils import collection_management, curve_management, mesh_management

reload(collection_management)
reload(curve_management)
reload(mesh_management)
reload(operators)
reload(properties)
reload(crossroad_generator)
reload(data_generator)
reload(kerb_generator)
reload(road_generator)
reload(road_net_generator)

from .operators import (
    CG_CreateAll,
    CG_CreateCrossroads,
    CG_CreateOneRoad,
    CG_CreateRoadData,
    CG_CreateRoads,
    CG_CreateRoadsFromCollection,
    CG_DeleteAll)
from .properties import CG_RoadProperties


# ------------------------------------------------------------------------
#    Panel in Object Mode
# ------------------------------------------------------------------------


class CG_RoadPanel(bpy.types.Panel):
    bl_label = "Road Generation"
    bl_idname = "citygen_road_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "CityGen"
    bl_context = "objectmode"
    bl_order = 1

    def draw(self, context):
        layout = self.layout
        road_props = context.scene.road_props

        row = layout.row()
        row.prop(road_props, "curve")
        row.operator("cg.create_one_road")

        row = layout.row()
        row.prop(road_props, "collection")
        row.operator("cg.create_roads_from_collection")

        layout.operator("cg.create_all")
        layout.operator("cg.create_road_data")
        layout.operator("cg.create_roads")
        layout.operator("cg.create_crossroads")
        layout.operator("cg.delete_all")


# class CG_BuildingPanel(bpy.types.Panel):
#     bl_label = "Building Generation"
#     bl_idname = "citygen_building_panel"
#     bl_space_type = "VIEW_3D"
#     bl_region_type = "UI"
#     bl_category = "CityGen"
#     bl_context = "objectmode"
#     bl_order = 1

#     def draw(self, context):
#         layout = self.layout

# ------------------------------------------------------------------------
#    Registration of Properties, Operators and the Panel
# ------------------------------------------------------------------------


classes = (
    CG_RoadProperties,
    CG_CreateAll,
    CG_CreateCrossroads,
    CG_CreateOneRoad,
    CG_CreateRoadData,
    CG_CreateRoads,
    CG_CreateRoadsFromCollection,
    CG_DeleteAll,
    CG_RoadPanel,
    # CG_BuildingPanel
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.road_props = bpy.props.PointerProperty(type=CG_RoadProperties)


def unregister():
    del bpy.types.Scene.road_props

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

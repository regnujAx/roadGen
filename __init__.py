### To use this add-on you have to zip the directory containing this file (CityGen) 
### and the scripts directory (inside the CityGen directory) and install the zip in the .blend file.
### To install the add-on open your .blend file and go to Edit -> Preferences -> Add-ons -> Install.
### Navigate to the directory where the zip-file is located that contains the CityGen directory and the scripts directory and select it.
### The add-on should now listed and you have to enable it by clicking the checkbox. If you don't see it, select User in the dropdown.
### When enabled, you can use it in the 3D Viewport Object Mode.


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


# ------------------------------------------------------------------------
#    Project Dependent Imports
# ------------------------------------------------------------------------

dir = os.path.dirname(os.path.abspath(__file__))

if not dir in sys.path:
  sys.path.append(dir)


from . import (operators, properties, util)

reload(util)
reload(operators)
reload(properties)

from .properties import *
from .operators import *


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

    layout.prop(road_props, "lane_width")

    row = layout.row()
    row.prop(road_props, "left_lanes")
    row.prop(road_props, "right_lanes")
    
    row = layout.row()
    row.prop(road_props, "curve")
    row.operator("cg.create_one_road")

    row = layout.row()
    row.prop(road_props, "collection")
    row.operator("cg.create_roads_from_collection")

    layout.operator("cg.create_roads")
    layout.operator("cg.delete_all")


# ------------------------------------------------------------------------
#    Registration of Properties, Operators and the Panel
# ------------------------------------------------------------------------

classes = (
  CG_RoadProperties,
  CG_CreateOneRoad,
  CG_CreateRoadsFromCollection,
  CG_CreateRoads,
  CG_DeleteRoads,
  CG_RoadPanel
)

def register():
  for cls in classes:
    bpy.utils.register_class(cls)

  bpy.types.Scene.road_props = bpy.props.PointerProperty(type=CG_RoadProperties)

def unregister():
  del bpy.types.Scene.road_props

  for cls in reversed(classes):
    bpy.utils.unregister_class(cls)

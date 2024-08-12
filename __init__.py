# To use this add-on you have to zip the directory containing this file (roadGen)
# and install the zip in the .blend file.
# To install the add-on open your .blend file and go to Edit -> Preferences -> Add-ons -> Install.
# Navigate to the directory where the zip-file is located that contains the roadGen directory and select it.
# The add-on should now listed and you have to enable it by clicking the checkbox.
# If you don't see it, select User in the dropdown.
# When enabled, you can use it in the 3D Viewport Object Mode.


bl_info = {
    "name": "RoadGen",
    "author": "Alexander Junger",
    "version": (1, 0),
    "blender": (3, 6, 12),
    "location": "View3D > Toolbar > RoadGen",
    "category": "Object",
    "description": "Generate a procedural road network."
}


# ------------------------------------------------------------------------
#    General and Blender Dependent Imports
# ------------------------------------------------------------------------


import bpy
import os
import sys

from importlib import reload


# Make sure imports work even when main folder is named differently
if __name__ != "roadGen":
    sys.modules["roadGen"] = sys.modules[__name__]

# ------------------------------------------------------------------------
#    Project Dependent Imports
# ------------------------------------------------------------------------


dir = os.path.dirname(os.path.abspath(__file__))

if dir not in sys.path:
    sys.path.append(dir)


from . import operators
from .generators import crossroad_generator, data_generator, geometry_generator, kerb_generator, road_generator, road_net_generator
from .utils import collection_management, curve_management, mesh_management

reload(collection_management)
reload(curve_management)
reload(mesh_management)
reload(operators)
reload(crossroad_generator)
reload(data_generator)
reload(geometry_generator)
reload(kerb_generator)
reload(road_generator)
reload(road_net_generator)

from .operators import RG_CreateAll, RG_DeleteAll


# ------------------------------------------------------------------------
#    Panel in Object Mode
# ------------------------------------------------------------------------


class RG_RoadPanel(bpy.types.Panel):
    bl_label = "Road Generation"
    bl_idname = "roadGen_road_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "RoadGen"
    bl_context = "objectmode"

    def draw(self, context):
        layout = self.layout
        layout.operator("rg.create_all")
        layout.operator("rg.delete_all")


# ------------------------------------------------------------------------
#    Registration of Operators and Panel
# ------------------------------------------------------------------------


classes = (
    RG_CreateAll,
    RG_DeleteAll,
    RG_RoadPanel
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

import bpy

from ..road import RG_Road
from ..utils.mesh_management import add_objects


class RG_ObjectGenerator():
    def __init__(self, object_mesh_template: bpy.types.Object = None):
        self.object_mesh_template = object_mesh_template if object_mesh_template else bpy.data.objects.get("Street Lamp")
        print("self.object_mesh_template:", self.object_mesh_template)

        if not self.object_mesh_template:
            print("Check whether the object you want to add exists. It is missing.")

    def add_geometry(self, road: RG_Road = None, side: str = None):
        offset = road.sidewalk_mesh_template.dimensions[1]
        offset *= -1 if side == "Right" else 1
        add_objects(road.curve, side, self.object_mesh_template, road.lamp_distance, offset)

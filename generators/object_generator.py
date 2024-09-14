import bpy

from roadGen.road import RG_Road
from roadGen.utils.mesh_management import add_objects


class RG_ObjectGenerator():
    def __init__(self, object_names: list):
        self.object_templates = []
        for object_name in object_names:
            object = bpy.data.objects.get(object_name)
            if object:
                self.object_templates.append(object)
            else:
                print(f"The object with the name {object_name} cannot be found. "
                      "Check whether the object you want to add exists.")
        print("self.object_templates:", self.object_templates)

    def add_geometry(self, road: RG_Road = None, side: str = None):
        offset = road.sidewalk_mesh_template.dimensions[1]
        offset *= -1 if side == "Right" else 1
        for object_template in self.object_templates:
            add_objects(object_template, road.curve, side, road.lamp_distance, offset)

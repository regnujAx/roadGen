from roadGen.road import RG_Road
from roadGen.utils.mesh_management import add_objects_to_road


class RG_ObjectGenerator():
    def __init__(self, object_names: list):
        self.object_names = object_names

    def add_geometry(self, road: RG_Road = None, side: str = None):
        offset = road.sidewalk_mesh_template.dimensions[1]
        height = road.sidewalk_mesh_template.dimensions[2]

        for object_name in self.object_names:
            add_objects_to_road(object_name, road, side, offset, height)

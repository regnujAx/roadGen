from roadGen.road import RG_Road
from roadGen.utils.mesh_management import add_objects_to_road


class RG_RoadFurnitureGenerator():
    def __init__(self, road_furniture_object_names: list):
        self.road_furniture_object_names = road_furniture_object_names

    def add_geometry(self, road: RG_Road = None, side: str = None):
        offset = road.sidewalk_mesh_template.dimensions[1]
        height = road.sidewalk_mesh_template.dimensions[2]

        for road_furniture_object_name in self.road_furniture_object_names:
            add_objects_to_road(road_furniture_object_name, road, side, offset, height)

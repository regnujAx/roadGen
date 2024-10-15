import bpy

from mathutils import Vector

from roadGen.generators.geometry_generator import RG_GeometryGenerator
from roadGen.road import RG_Road
from roadGen.utils.collection_management import get_objects_from_collection
from roadGen.utils.mesh_management import create_mesh_from_vertices


class RG_LotGenerator(RG_GeometryGenerator):
    def __init__(self, roads: list):
        self.roads = roads
        self.lots = []

    def add_geometry(self):
        lot_counter = 0
        roads_copy = {"Left": self.roads.copy(), "Right": self.roads.copy()}

        for road in self.roads:
            for side in ["Left", "Right"]:
                if road in roads_copy[side]:
                    roads, lot_vertices = get_lot_roads_and_vertices(self.roads, road, side)

                    if roads and lot_vertices:
                        unique_lot_vertices = remove_close_vertices(lot_vertices)
                        height = road.sidewalk_mesh_template.dimensions[2]

                        lot = create_mesh_from_vertices(unique_lot_vertices, "Lot", f"{lot_counter}", height)

                        if lot:
                            self.lots.append(lot)
                            lot_counter += 1

                        for side in roads:
                            for road in roads[side]:
                                if road in roads_copy[side]:
                                    roads_copy[side].remove(road)


# ------------------------------------------------------------------------
#    Helper Methods
# ------------------------------------------------------------------------


def append_sidewalk_vertices_to_lot(sidewalk_meshes: list, lot_vertices: list, curve: bpy.types.Object, side: str = "Right"):
    indices = range(len(sidewalk_meshes))

    if side == "Left":
        indices = list(reversed(indices))

    direction_for_vertices_order = (curve.data.splines[0].bezier_points[0].handle_right -
                                    curve.data.splines[0].bezier_points[0].co)

    for i in indices:
        mesh = sidewalk_meshes[i]

        if i < 2 or i == len(sidewalk_meshes) - 1 and side == "Left":
            outside_indices = get_outside_bottom_indices(mesh, side, direction_for_vertices_order)

        for index in outside_indices:
            global_vertex_co = mesh.matrix_world @ mesh.data.vertices[index].co
            global_vertex_co.z = 0.0
            lot_vertices.append(global_vertex_co)


def get_lot_roads_and_vertices(roads: list, start_road: RG_Road, side: str):
    lot_roads = {"Left": [], "Right": []}
    lot_vertices = []
    road = start_road

    while True:
        right_neighbour = None

        if side == "Left" and road.left_curve:
            curve = road.left_curve

            if road.right_neighbour_of_left_curve:
                right_neighbour = bpy.data.objects.get(road.right_neighbour_of_left_curve)
        elif side == "Right" and road.right_curve:
            curve = road.right_curve

            if road.right_neighbour_of_right_curve:
                right_neighbour = bpy.data.objects.get(road.right_neighbour_of_right_curve)

        sidewalk_meshes = road.sidewalks[side]

        append_sidewalk_vertices_to_lot(sidewalk_meshes, lot_vertices, curve, side)

        if right_neighbour and road not in lot_roads[side]:
            lot_roads[side].append(road)
            road_of_right_neighbour = get_road_by_curve(roads, right_neighbour)

            if road_of_right_neighbour:

                crossroad_curve_name = "Crossroad_Curve_" + curve.name + "_" + right_neighbour.name
                crossroad_curve = bpy.data.objects.get(crossroad_curve_name)
                sidewalk_meshes = get_objects_from_collection(f"Sidewalk_{crossroad_curve_name}")

                append_sidewalk_vertices_to_lot(sidewalk_meshes, lot_vertices, crossroad_curve)

                road = road_of_right_neighbour

                if road == start_road:
                    break

                side = "Left" if "Left" in right_neighbour.name else "Right"
        else:
            break

    # Only return the found roads and vertices if the start road has been reached again
    # and more than 2 roads belong to the lot
    if road == start_road and len(lot_roads["Left"]) + len(lot_roads["Right"]) > 2:
        return lot_roads, lot_vertices

    return None, None


def get_outside_bottom_indices(mesh: bpy.types.Object, side: str, direction_for_vertices_order: Vector):
    outside_indices = []

    vertex_group = mesh.vertex_groups.get(f"Outside_{side}")

    if vertex_group:
        for vertex in mesh.data.vertices:
            # Check whether the vertex is part of the vertex group
            for group in vertex.groups:
                if group.group == vertex_group.index:
                    outside_indices.append(vertex.index)

    outside_vertices = [mesh.data.vertices[index] for index in outside_indices]

    outside_indices = sort_vertex_indices(outside_vertices, direction_for_vertices_order)

    return list(reversed(outside_indices)) if side == "Left" else outside_indices


def get_road_by_curve(roads: list, curve: bpy.types.Object):
    for road in roads:
        if road.curve.name == curve.name.rpartition('_')[0]:
            return road

    return None


def remove_close_vertices(vertices: list):
    threshold = 0.01
    unique_vertices = []

    for i in range(len(vertices) - 1):
        distance = (vertices[i] - vertices[i + 1]).length

        if distance > threshold:
            unique_vertices.append(vertices[i])

    return unique_vertices


def sort_vertex_indices(vertices: list, direction: Vector):
    # Save all vertices in a list with their indices and their calculated dot product with the reference direction vector
    vertices = [(v.index, v.co.dot(direction)) for v in vertices]

    # Sort the list by the dot products
    vertices.sort(key=lambda x: x[1])

    # Return only the indices of the vertices
    return [v[0] for v in vertices]

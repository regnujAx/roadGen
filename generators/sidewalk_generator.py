import bpy
import math

from ..road import CG_Road
from ..utils.collection_management import objects_from_collection
from ..utils.mesh_management import add_mesh_to_curve, create_kdtree, separate_array_meshes


class CG_SidewalkGenerator:
    def __init__(self, curve: bpy.types.Object = None, road: CG_Road = None, sidewalk_mesh_template: bpy.types.Object = None):
        self.curve = curve
        self.road = road
        self.sidewalk_mesh_template = sidewalk_mesh_template if sidewalk_mesh_template else bpy.data.objects.get("Sidewalk")

        if not self.sidewalk_mesh_template:
            print("Check whether the object Sidewalk is present, it is missing.")

    def add_sidewalk(self, side: str = None):
        offset = bpy.data.objects.get("Kerb").dimensions[1]

        if self.curve:
            kerb_mesh_name = "Kerb_" + self.curve.name

            mesh = add_mesh_to_curve(self.sidewalk_mesh_template, self.curve, "Sidewalk", 0.0, 0, offset)
        elif self.road:
            kerb_mesh_name = "Kerb_" + side + "_" + self.road.curve.name

            index = self.road.left_lanes if side == "Left" else -self.road.right_lanes
            mesh = add_mesh_to_curve(
                self.sidewalk_mesh_template, self.road.curve, f"Sidewalk_{side}", self.road.lane_width, index, offset)

        drop_sidewalk(mesh, kerb_mesh_name)

        separate_array_meshes(mesh)

        # Add the sidewalk meshes to the Road
        if self.road:
            meshes = objects_from_collection(mesh.name)
            self.road.sidewalks[side] = meshes


def drop_sidewalk(mesh: bpy.types.Object, kerb_mesh_name: str, drop_depth: float = 0.115):
    kerb_mesh = bpy.data.objects.get(kerb_mesh_name)
    vertices = [vertex.co for vertex in kerb_mesh.data.vertices]

    # Find all dropped vertices of the kerb
    dropped_vertices = []
    for vertex in vertices:
        # Have a small threshold for finding the correct vertices due to the mesh structure and rounding issues
        depth_threshold = 0.00001
        if vertex.z <= drop_depth + depth_threshold and vertex.z >= drop_depth - depth_threshold:
            dropped_vertices.append(vertex + kerb_mesh.location)

    num = len(dropped_vertices)

    # Filter the dropped vertices by comparing three successively vertices to find one vertex per pair of vertices
    filtered_dropped_vertices = []
    for i in range(num - 2):
        vertex_1 = dropped_vertices[i]
        vertex_2 = dropped_vertices[i+1]
        vertex_3 = dropped_vertices[i+2]

        # Adjust the height to find better the upper vertices
        vertex_1.z = 0.25
        vertex_2.z = 0.25
        vertex_3.z = 0.25

        # Calculate the distances between the two pairs of vertices
        vector_1 = vertex_2 - vertex_1
        vector_2 = vertex_3 - vertex_1
        distance_1 = math.sqrt(sum(i**2 for i in vector_1))
        distance_2 = math.sqrt(sum(i**2 for i in vector_2))

        # Only use the current vertex if its distance to the other two vertices is large enough
        distance_threshold = 0.15
        if distance_1 >= distance_threshold and distance_2 >= distance_threshold:
            filtered_dropped_vertices.append(vertex_1)

        # Add also a vertex for the last pair of vertices (the last is sufficient)
        if i == num - 3 and distance_2 >= distance_threshold:
            filtered_dropped_vertices.append(vertex_3)

    mesh_vertices = [vertex.co for vertex in mesh.data.vertices]
    kd_tree = create_kdtree(mesh_vertices, len(mesh_vertices))

    # For each filtered dropped kerb vertex, find the correct sidewalk vertex/vertices and drop it/they as well
    for dropped_vertex in filtered_dropped_vertices:
        for (co, index, dist) in kd_tree.find_n(dropped_vertex - mesh.location, 2):
            vertex = mesh_vertices[index]

            # Decrease the height only for the upper vertices
            if vertex.z > 0.2:
                vertex.z -= 0.135

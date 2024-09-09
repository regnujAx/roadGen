import bpy
import math

from mathutils import Vector

from roadGen.generators.geometry_generator import RG_GeometryGenerator
from roadGen.road import RG_Road
from roadGen.utils.collection_management import first_and_last_objects_from_collections, link_to_collection, objects_from_collection
from roadGen.utils.mesh_management import (
    add_mesh_to_curve,
    apply_modifiers,
    create_kdtree,
    intersecting_meshes,
    separate_array_meshes,
    set_origin)


class RG_SidewalkGenerator(RG_GeometryGenerator):
    def __init__(self, mesh_template: bpy.types.Object = None, offset: float = 0.0):
        self.offset = offset
        self.sidewalks = {}
        self.mesh_template = mesh_template if mesh_template else bpy.data.objects.get("Sidewalk")

        if not self.mesh_template:
            print("Check whether the object Sidewalk exists. It is missing.")

    def add_geometry(self, curve: bpy.types.Object = None, road: RG_Road = None, side: str = None):
        if curve:
            kerb_mesh_name = "Kerb_" + curve.name

            mesh = add_mesh_to_curve(self.mesh_template, curve, "Sidewalk", 0.0, 0, self.offset)
        elif road:
            if not road.sidewalk_mesh_template:
                road.sidewalk_mesh_template = self.mesh_template

            curve = road.curve
            kerb_mesh_name = "Kerb_" + side + "_" + road.curve.name

            index = road.left_lanes if side == "Left" else -road.right_lanes
            mesh = add_mesh_to_curve(
                self.mesh_template, road.curve, f"Sidewalk_{side}", road.lane_width, index, self.offset)

        if curve.name not in self.sidewalks:
            self.sidewalks[curve.name] = []
        self.sidewalks[curve.name].append(mesh.name)

        drop_sidewalk(mesh, kerb_mesh_name)

        separate_array_meshes(mesh)

        # Add the sidewalk meshes to the Road
        if road:
            meshes = objects_from_collection(mesh.name)
            road.sidewalks[side] = meshes

    # ToDo: Check if it is still required
    def correct_sidewalks(self):
        collections = [collection for collections in list(self.sidewalks.values()) for collection in collections]

        number_of_meshes = 5
        meshes = first_and_last_objects_from_collections(collections, number_of_meshes)
        mesh_intersections = intersecting_meshes(meshes)

        edit_meshes = []
        for mesh in mesh_intersections.keys():
            edit_meshes.append(mesh)
            intersections = mesh_intersections[mesh]
            collection_name = mesh.users_collection[0].name

            for intersected_mesh in intersections:
                if intersected_mesh not in edit_meshes:
                    # Create a copy of the current mesh
                    mesh_copy = mesh.copy()
                    mesh_copy.data = mesh.data.copy()

                    # Add a boolean intersect modifier to the mesh copy with the current intersected mesh as reference object
                    # to get the intersecting part(s) of the two meshes
                    intersect_modifier = mesh_copy.modifiers.new("Bool", 'BOOLEAN')
                    intersect_modifier.operation = 'INTERSECT'
                    intersect_modifier.object = intersected_mesh

                    # Link the mesh copy to its collection, apply its modifiers and update the origin
                    link_to_collection(mesh_copy, collection_name)
                    apply_modifiers(mesh_copy)
                    set_origin(mesh_copy)
                    # Scale the mesh copy a little bit up to get better results for the next step
                    mesh_copy.scale = Vector((1.001, 1.001, 1.001))

                    # Add a boolean difference modifier to the original mesh with the mesh copy as reference object
                    # to remove the intersecting part(s), i.e. the mesh copy, from the original mesh
                    diff_modifier = mesh.modifiers.new("Bool", 'BOOLEAN')
                    diff_modifier.operation = 'DIFFERENCE'
                    diff_modifier.object = mesh_copy
                    apply_modifiers(mesh)

                    # Delete the mesh copy
                    bpy.data.objects.remove(mesh_copy)


# ------------------------------------------------------------------------
#    Helper Methods
# ------------------------------------------------------------------------


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

import bpy
import bmesh
import math
import random

from mathutils import Vector

from roadGen.generators.geometry_generator import RG_GeometryGenerator
from roadGen.utils.collection_management import link_to_collection
from roadGen.utils.mesh_management import apply_transform


class RG_BuildingGenerator(RG_GeometryGenerator):
    def __init__(self, building_areas):
        self.building_areas = building_areas
        self.buildings = []

    def add_geometry(self):
        bm = bmesh.new()

        for building_area in self.building_areas:
            new_building_mesh = bpy.data.meshes.new(name="Building")

            bm.from_mesh(building_area.data)

            # Remove all vertices with an angle < 50° to its neighbours with limited dissolve
            # to get a low resolution mesh that is more suitable for Buildify
            bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(50), verts=bm.verts, edges=bm.edges)

            # Create a new object based on the new mesh and update its location
            new_building_obj = bpy.data.objects.new("Building", new_building_mesh)
            new_building_obj.location = building_area.location

            # Link the new object to its collection and append it to the class list
            link_to_collection(new_building_obj, "Buildings")
            self.buildings.append(new_building_obj)

            # Write the BMesh data to the new mesh
            bm.to_mesh(new_building_mesh)

            # Scale the new object a little bit down and apply it
            new_building_obj.scale = Vector((0.95, 0.95, 0.95))

            apply_transform(new_building_obj, scale=True)

            # Add a geometry nodes modifier
            modifier = new_building_obj.modifiers.new("Building", "NODES")

            # Locate the building node tree
            building_node_tree = bpy.data.node_groups["building"]

            # Update the modifier's node group with the building node tree
            modifier.node_group = building_node_tree

            # Change the input parameter for the geometry node
            min_number_of_floors = random.randint(1, 3)
            max_number_of_floors = random.randint(2, 8)

            modifier["Input_6"] = min_number_of_floors
            modifier["Input_7"] = max_number_of_floors

            bm.clear()

        bm.free()

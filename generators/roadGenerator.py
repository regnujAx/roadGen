import bpy
import bmesh
import mathutils

from ..util import add_mesh_to_curve, apply_transform, create_kdtree, find_closest_points, hide_collection, link_to_collection


class CG_RoadGenerator:
    def __init__(self, curves):
        self.curves = curves
        self.kerb_mesh_template = bpy.data.objects.get("Kerb")

    def add_roads(self):
        if not self.kerb_mesh_template:
            print("Check whether the object Kerb is present, it is missing.")

        for curve in self.curves:
            if curve.dimensions == "2D":
                curve.dimensions = "3D"
            curve.name = curve.name.replace(".", "_")
            # Select the curve and apply its rotation and scale
            # but without its location and its properties such as radius
            apply_transform(curve, location=False, properties=False)

            # Get the curve's custom properties
            lane_width = curve["Lane Width"]
            left_lanes = curve["Left Lanes"]
            right_lanes = curve["Right Lanes"]

            add_road_lanes(curve, "Left", left_lanes, lane_width)
            add_road_lanes(curve, "Right", right_lanes, lane_width)

            if self.kerb_mesh_template:
                for side in ["Left", "Right"]:
                    index = left_lanes if side == "Left" else -right_lanes
                    add_mesh_to_curve(self.kerb_mesh_template, curve, f"Kerb_{side}", lane_width, index)

                    mesh_name = "Kerb_" + side + "_" + curve.name
                    add_line_following_mesh(mesh_name)

                    if curve[f"{side} Dropped Kerbs"]:
                        positions = [int(x) for x in curve[f"{side} Dropped Kerbs"].split(",")]
                        add_object_to_mesh(mesh_name, positions)

        # Hide the Line Meshes collection in Viewport
        hide_collection("Line Meshes")


# ------------------------------------------------------------------------
#    Helper Methods
# ------------------------------------------------------------------------


def add_line_following_mesh(mesh_name: str):
    mesh = bpy.data.objects.get(mesh_name)
    bm = bmesh.new()
    bm.from_mesh(mesh.data)

    top_faces_center = []
    # Calculate centers for all faces and save only the "top" (highest z-coordinate) faces
    for face in bm.faces:
        center = face.calc_center_median()

        if center[2] >= 0.24999:
            top_faces_center.append(center)

    bm.free()

    line_mesh_name = "Line_Mesh_" + mesh_name
    # Add a new mesh
    new_mesh = bpy.data.meshes.new("new_mesh")
    # Add a new object (line mesh) using the new mesh
    line_mesh = bpy.data.objects.new(line_mesh_name, new_mesh)

    # Deselect all selected objects to ensure that no object is selected
    for object in bpy.context.selected_objects:
        object.select_set(False)

    # Link the line mesh to the correct colletion
    collection_name = "Line Meshes"
    link_to_collection(line_mesh, collection_name)

    line_mesh.select_set(True)

    points = find_closest_points(top_faces_center, top_faces_center[0])

    bm = bmesh.new()
    # Add the top faces centers as vertices to the new mesh
    for (co, index, dist) in points:
        bm.verts.new(co)

    # Ensure internal data needed for int subscription is initialized with vertices, e.g. bm.verts[index]
    bm.verts.ensure_lookup_table()

    for i in range(len(bm.verts) - 1):
        # Add a new edge with the current vertex and the closest next vertex
        bm.edges.new((bm.verts[i], bm.verts[i+1]))

    # Fill line mesh's data with the BMesh
    bm.to_mesh(line_mesh.data)
    bm.free()

    # Deselect the line mesh and update its location
    line_mesh.select_set(False)
    line_mesh.location = mesh.location


def add_object_to_mesh(mesh_name: str, positions: list):
    mesh = bpy.data.objects.get(mesh_name)
    line_mesh_name = "Line_Mesh_" + mesh_name
    line_mesh = bpy.data.objects.get(line_mesh_name)

    # Create a BMesh from the line mesh for edge length calculation
    mesh_eval_data = line_mesh.data
    bm_line = bmesh.new()
    bm_line.from_mesh(mesh_eval_data)

    object_position = None
    for pos in positions:
        p = pos
        total_length = 0

        # Iterate over all line mesh edges to find its position, which corresponds to the given position
        for edge in bm_line.edges:
            edge_length = edge.calc_length()
            total_length += edge_length

            # Calculate the position on the line mesh when a position is reached
            if total_length > pos:
                v0 = edge.verts[0]
                v1 = edge.verts[1]
                vec = mathutils.Vector(v1.co) - mathutils.Vector(v0.co)
                unit_vec = vec / edge_length
                object_position = v0.co + unit_vec * p
                break

            p -= edge_length

        # Edit the mesh at the reached position
        if object_position:
            vertices_co = [vertex.co for vertex in mesh.data.vertices]

            kd = create_kdtree(vertices_co, len(vertices_co))

            # Decrease the "height" (z-coordinate) of all vertices in a certain radius that are higher than 0
            radius = 2
            for (co, index, dist) in kd.find_range(object_position, radius):
                vertex_co = vertices_co[index]

                if vertex_co.z > 0.1:
                    vertex_co.z -= 0.135

    bm_line.free()


def add_road_lanes(curve: bpy.types.Object, side: str, lane_number: int, lane_width: float):
    road_lane_mesh_template_outside = bpy.data.objects.get(f"Road_Lane_Border_{side}")
    road_lane_mesh_template_inside = bpy.data.objects.get("Road_Lane_Inside")

    if road_lane_mesh_template_outside and road_lane_mesh_template_inside:
        for i in range(lane_number):
            template = road_lane_mesh_template_outside if i == lane_number - 1 else road_lane_mesh_template_inside
            index = i + 1 if side == "Left" else -i
            add_mesh_to_curve(template, curve, f"Road_Lane_{side}", lane_width, index)
    else:
        print("Check whether the objects Road_Lane_Border_Left, Road_Lane_Border_Right and Road_Lane_Inside are present. "
              "At least one is missing.")

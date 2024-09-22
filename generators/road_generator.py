import bpy

from mathutils import Vector

from roadGen.generators.geometry_generator import RG_GeometryGenerator
from roadGen.road import RG_Road
from roadGen.utils.mesh_management import apply_transform, curve_to_mesh, extrude_mesh, set_origin
from roadGen.utils.collection_management import link_to_collection


class RG_RoadGenerator(RG_GeometryGenerator):
    def __init__(self):
        self.roads = []

    def add_geometry(self, curve: bpy.types.Object):
        if curve.data.dimensions == "2D":
            curve.data.dimensions = "3D"

        # Increase (or decrease) the resolution of the curve
        curve.data.resolution_u = 32
        curve.name = curve.name.replace(".", "_")

        # Select the curve and apply its rotation and scale
        # but without its location and its properties such as radius
        apply_transform(curve, location=False, properties=False)

        # Create a line mesh copy of the curve
        curve_to_mesh(curve)

        road = RG_Road(curve)
        add_road_lanes(road)
        self.roads.append(road)


# ------------------------------------------------------------------------
#    Helper Methods
# ------------------------------------------------------------------------


def add_road_lanes(road: RG_Road):
    for side in ["Left", "Right"]:
        curve = road.curve
        lane_number = road.left_lanes if side == "Left" else road.right_lanes
        bezier_points = curve.data.splines[0].bezier_points
        total_length = curve.data.splines[0].calc_length()

        reverse = False

        # Create the left side backwards/reversed
        if side == "Left":
            reverse = True

        # If there is a turning lane and it is enough space for it, the index of the bezier point is calculated
        # to find a start for the tuning lane
        if side == "Left" and road.left_turning_lane_distance and total_length > road.left_turning_lane_distance * 1.5:
            extra_lane_start_index = calculate_start_index_with_distance(bezier_points, road.left_turning_lane_distance, reverse)
        elif side == "Right" and road.right_turning_lane_distance and total_length > road.right_turning_lane_distance * 1.5:
            extra_lane_start_index = calculate_start_index_with_distance(bezier_points, road.right_turning_lane_distance, reverse)
        else:
            # Set the start index to 0 if there is no turning lane or not enough space for it, so that no extra lane is added
            extra_lane_start_index = 0
        print("curve.name:", curve.name)
        print("extra_lane_start_index:", extra_lane_start_index)
        crv = create_new_curve(bezier_points, road.lane_width, lane_number, extra_lane_start_index, reverse)
        new_curve = bpy.data.objects.new(f"{curve.name}_{side}", crv)
        new_curve.location = curve.location
        link_to_collection(new_curve, "Curves")
        print("new_curve.name:", new_curve.name)

        if side == "Left":
            road.curve_left = new_curve
        else:
            road.curve_right = new_curve

        # Update the scene to get correctly positioned objects
        bpy.context.view_layer.update()

        # Create a line mesh for the created side curve
        side_curve = bpy.data.objects.get(new_curve.name)
        side_line_mesh = curve_to_mesh(side_curve)

        vertices = []

        # Add all vertices of the created line mesh to a list of vertices
        for vertex in side_line_mesh.data.vertices:
            v = side_line_mesh.matrix_world @ vertex.co
            vertex_vec = Vector((v.x, v.y, 0.0))
            vertices.append(vertex_vec)

        # Get the line mesh of the original curve
        curve_line_mesh = bpy.data.objects.get(f"Line_Mesh_{curve.name}")
        line_mesh_vertices = curve_line_mesh.data.vertices

        # The left side was created backwards, so we can iterate forwards over the original curve mesh,
        # only for the right side we have to iterate backwards
        indices = range(len(line_mesh_vertices))

        if not reverse:
            indices = reversed(indices)

        # Add all vertices of the line mesh of the original curve to the list of vertices
        for i in indices:
            vertex = curve_line_mesh.matrix_world @ line_mesh_vertices[i].co
            vertex_vec = Vector((vertex.x, vertex.y, 0.0))
            vertices.append(vertex_vec)

        # Create the face (only one) based on the vertices for the road lane plane
        face = []
        faces = []
        for index in range(len(vertices)):
            face.append(index)
        faces.append(face)

        # Create the road lane plane and link it to its corresponding collection
        mesh = bpy.data.meshes.new("Road Lane Mesh")
        mesh.from_pydata(vertices, [], faces)

        road_lane = bpy.data.objects.new(f"Road_Lanes_{side}_{curve.name}", mesh)
        link_to_collection(road_lane, "Road Lanes")

        # Extrude the road lane plane so it is a 3D mesh
        extrude_mesh(road_lane, 0.1)

        # Set the origin to the center of the mesh (Hint: This overwrites the location.)
        set_origin(road_lane, 'BOUNDS')


def calculate_start_index_with_distance(points: list, distance: float, reverse: bool):
    length = 0
    start_index = 0

    indices = range(len(points) - 1)

    if reverse:
        indices = reversed(indices)

    for i in indices:
        length += (points[i + 1].co - points[i].co).length

        if length >= distance:
            start_index = i + 1
            break

    return start_index


def create_new_curve(bezier_points: list, lane_width: float, lane_number: int, extra_lane_start_index: int, reverse: bool):
    # Create a new curve and change its curve type to 3D and increase its resolution
    curve = bpy.data.curves.new("curve", 'CURVE')
    curve.dimensions = "3D"
    curve.resolution_u = 32

    # Create a new spline for the new created curve
    spline = curve.splines.new(type='BEZIER')

    new_bezier_points = spline.bezier_points
    bezier_points_number = len(bezier_points)

    # Add one spline bezier point for each point minus one (there is already one point by default)
    new_bezier_points.add(bezier_points_number - 1)

    indices = range(bezier_points_number)

    if reverse:
        indices = reversed(indices)

    print("indices:", indices)
    # Calculate for each index the new (shifted) coordinates for each bezier_point of the new curve
    for i in indices:
        vec = bezier_points[i].handle_right - bezier_points[i].co
        vec.normalize()

        orthogonal_vector = Vector((-vec.y, vec.x, 0))

        # Calculate the shift offset depending on iteration (reverse or not)
        if reverse:
            # Invert the orthogonal vector (for the left side)
            orthogonal_vector = -orthogonal_vector

            # For the left side, we iterate reverse, so that the first curve points must be shifted more
            # than the rest, which is smaller than the passed index
            offset = lane_width * (lane_number + 1) if i >= extra_lane_start_index else lane_width * lane_number
        else:
            offset = lane_width * (lane_number + 1) if i <= extra_lane_start_index else lane_width * lane_number

        if extra_lane_start_index == 0:
            offset = lane_width * lane_number

        print("offset:", offset)
        print("orthogonal_vector:", orthogonal_vector)
        shift = orthogonal_vector * offset
        print("shift:", shift)

        # Calculate the index for the current point of the new curve
        new_index = bezier_points_number - 1 - i if reverse else i
        print("new_index:", new_index)

        print("bezier_points[i].co:", bezier_points[i].co)
        # Set the coordinates of the current point
        new_bezier_points[new_index].co = bezier_points[i].co + shift

        # Set the left handle of the current point
        correct_handle = bezier_points[i].handle_right if reverse else bezier_points[i].handle_left
        new_bezier_points[new_index].handle_left = correct_handle + shift

        # Set the right handle of the current point
        correct_handle = bezier_points[i].handle_left if reverse else bezier_points[i].handle_right
        new_bezier_points[new_index].handle_right = correct_handle + shift

    return curve

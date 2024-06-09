import bpy
import bmesh
import numpy as np

from mathutils import kdtree, Vector


# ------------------------------------------------------------------------
#    Helper Functions
# ------------------------------------------------------------------------


def add_crossroad(curves: list, crossing_point: bpy.types.Object, height: float = 0.1):
    vertices = []
    vertices_to_remove = []
    for curve in curves:
        # Cast a ray from the crossing point to find the correct face and vertices of the curve
        bottom_vertices = get_outer_bottom_vertices(curve, crossing_point)
        # Add the outer bottom vertices to a list for every curve
        vertices_to_remove.extend(bottom_vertices)

    number_of_vertices = len(vertices_to_remove)
    # Mark one point as reference for distance calculation
    reference_point = crossing_point.location
    # Iterate over all vertices and collect the vertices in the correct order for the crossroad plane
    for i in range(number_of_vertices):
        if i < number_of_vertices - 1:
            vertex_0 = vertices_to_remove[0]
            vertex_1 = vertices_to_remove[1]
            # Get the closest vertex with respect to the reference point
            vertex = get_closest_point(vertex_0, vertex_1, reference_point)
            # Remove the closest vertex from the list
            vertex_to_remove = vertex_0 if vertex == vertex_0 else vertex_1
            # Set the current point as reference_point for the next iteration (to find the closest point)
            reference_point = vertex
        else:
            # Use the remaining vertex and then remove it
            vertex = vertices_to_remove[0]
            vertex_to_remove = vertex

        vertices_to_remove.remove(vertex_to_remove)
        vertex_vec = Vector((vertex.x, vertex.y, 0.0))
        vertices.append(vertex_vec)

    # Create the face (only one) based on the vertices for the crossroad plane
    # (Assumption: All vertices are in the correct order.)
    faces = []
    face = []
    for index in range(len(vertices)):
        face.append(index)
    faces.append(face)

    # Create the crossroad plane and link it to its corresponding collection
    mesh = bpy.data.meshes.new("Crossroad Mesh")
    mesh.from_pydata(vertices, [], faces)
    crossroad_name = "Crossroad_" + crossing_point.name
    crossroad = bpy.data.objects.new(crossroad_name, mesh)
    link_to_collection(crossroad, "Crossroads")

    # Edit the crossroad plane
    bpy.context.view_layer.objects.active = crossroad
    bpy.ops.object.mode_set(mode='EDIT')

    # Extrude the crossroad plane so it is a 3D mesh
    bpy.ops.mesh.extrude_region_move(TRANSFORM_OT_translate={"value": (0.0, 0.0, height)})
    bpy.ops.object.mode_set(mode='OBJECT')

    # Set the origin to the center of the mesh (Hint: This overwrites the location.)
    set_origin(crossroad)


def add_crossroads():
    crossing_points = get_crossing_points()
    for crossing_point in crossing_points:
        curves_number = int(crossing_point["Number of Curves"])
        curves = []

        for i in range(curves_number):
            curve_name = crossing_point[f"Curve {i+1}"]
            if curve_name:
                curve = bpy.data.objects[curve_name]
                curves.append(curve)

        add_crossroad(curves, crossing_point)

    return {'FINISHED'}


def add_mesh_to_curve(mesh_template: bpy.types.Object, curve: bpy.types.Object, name: str, lane_width: float, index: int):
    mesh = mesh_template.copy()
    mesh.data = mesh_template.data.copy()
    mesh.name = name + "_" + curve.name

    # Translate the created mesh according to the lane width and the number of lanes per road side (i.e. index)
    if "Lane" in name:
        vec = Vector((0.0, lane_width * index - lane_width/2, 0.0))
        mesh.dimensions[1] = lane_width
    elif "Kerb" in name:
        # Keep for kerbs the original z location
        sign = -1 if index < 0 else 1
        vec = Vector((0.0, lane_width * index + (sign * mesh.dimensions[1]/2), mesh.location[2]))
    mesh.location += vec

    # Apply the correct curve for the mesh modifiers
    mesh.modifiers['Array'].curve = curve
    mesh.modifiers['Curve'].object = curve

    # Add the created mesh to the correct collection
    collection_name = "Road Lanes" if "Road_Lane" in name else "Kerbs"
    link_to_collection(mesh, collection_name)

    # Set the mesh as active object and apply its modifiers
    bpy.context.view_layer.objects.active = mesh
    for modifier in mesh.modifiers:
        bpy.ops.object.modifier_apply(modifier=modifier.name)

    # Select the mesh and apply its transforms (i.e. translation, rotation, scale)
    apply_transform(mesh)


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


def add_roads(curves: list):
    kerb_mesh_template = bpy.data.objects.get("Kerb")

    # if road_lane_mesh_template_left and road_lane_mesh_template_right and road_lane_mesh_template_inside:
    for curve in curves:
        if curve.dimensions == "2D":
            curve.dimensions = "3D"
        curve.name = curve.name.replace(".", "_")
        # Select the curve and apply its transforms (i.e. translation, rotation, scale)
        # but without its properties such as radius
        apply_transform(curve, False)

        # Get the curve's custom properties
        lane_width = curve["Lane Width"]
        left_lanes = curve["Left Lanes"]
        right_lanes = curve["Right Lanes"]

        add_road_lanes(curve, "Left", left_lanes, lane_width)
        add_road_lanes(curve, "Right", right_lanes, lane_width)

        if kerb_mesh_template:
            for side in ["Left", "Right"]:
                index = left_lanes if side == "Left" else -right_lanes
                add_mesh_to_curve(kerb_mesh_template, curve, f"Kerb_{side}", lane_width, index)

                mesh_name = "Kerb_" + side + "_" + curve.name
                add_line_following_mesh(mesh_name)

                if curve[f"{side} Dropped Kerbs"]:
                    positions = [int(x) for x in curve[f"{side} Dropped Kerbs"].split(",")]
                    add_object_to_mesh(mesh_name, positions)
        else:
            print("Check whether the object Kerb is present, it is missing.")

    return {'FINISHED'}


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

    # Deselect all objects to be sure that no object is selected
    bpy.ops.object.select_all(action='DESELECT')

    # Link the line mesh to the correct colletion
    collection_name = "Line Meshes"
    link_to_collection(line_mesh, collection_name)
    # Hide the Line Meshes collection in Viewport
    bpy.context.view_layer.layer_collection.children[collection_name].hide_viewport = True

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
                vec = Vector(v1.co) - Vector(v0.co)
                unit_vec = vec / edge_length
                object_position = v0.co + unit_vec * p
                break

            p -= edge_length

        if object_position:
            # Edit the mesh
            bpy.context.view_layer.objects.active = mesh
            bpy.ops.object.mode_set(mode='EDIT')
            # Create a BMesh (for editing) from mesh data
            mesh_data = bpy.context.edit_object.data
            bm = bmesh.from_edit_mesh(mesh_data)
            bm.verts.ensure_lookup_table()

            bm_vertices = [vert.co for vert in bm.verts]

            kd = create_kdtree(bm_vertices, len(bm_vertices))

            # Decrease the "height" (z-coordinate) of all vertices in a certain radius that are higher than 0
            radius = 2
            for (co, index, dist) in kd.find_range(object_position, radius):
                vertex = bm.verts[index]

                if vertex.co[2] > 0.1:
                    vertex.co[2] -= 0.135

            bm.free()
            bpy.ops.object.mode_set(mode='OBJECT')

    bm_line.free()


def apply_transform(object: bpy.types.Object, properties: bool = True):
    object.select_set(True)
    bpy.ops.object.transform_apply(properties=properties)
    object.select_set(False)


def calculate_ray_cast(origin: Vector, closest_curve_point: Vector):
    # Calculate the direction for the ray cast and set its z-coordinat to 0.0 to make it easier to find the correct face
    direction = closest_curve_point - origin
    direction.z = 0.0

    depsgraph = bpy.context.view_layer.depsgraph
    # Return only the normal of the hit face (i.e. the third element of the tuple)
    return bpy.context.scene.ray_cast(depsgraph, origin, direction)[2]


def create_kdtree(list, size):
    # Create a KD-Tree to perform a spatial search
    kd = kdtree.KDTree(size)
    for i, v in enumerate(list):
        kd.insert(v, i)

    # Balance (build) the KD-Tree
    kd.balance()

    return kd


def delete(collections):
    for collection_name in collections:
        objects = get_objects_from_collection(collection_name)

        while objects:
            bpy.data.objects.remove(objects.pop())

        remove_collection(collection_name)

    return {'FINISHED'}


def find_closest_points(list, reference_point: Vector):
    num_vertices = len(list)
    kd = create_kdtree(list, num_vertices)
    # Sort the points by distance to the reference point and return them
    return kd.find_n(reference_point, num_vertices)


def get_closest_curve_point(curve: bpy.types.Object, reference_point: Vector):
    first_curve_point = curve.data.splines[0].bezier_points[0].co
    end_curve_point = curve.data.splines[0].bezier_points[-1].co
    return get_closest_point(first_curve_point, end_curve_point, reference_point)


def get_closest_point(point_1: Vector, point_2: Vector, reference_point: Vector):
    distance_1 = np.sqrt(np.sum([
        (point_1.x - reference_point.x)**2,
        (point_1.y - reference_point.y)**2,
        (point_1.z - reference_point.z)**2]))
    distance_2 = np.sqrt(np.sum([
        (point_2.x - reference_point.x)**2,
        (point_2.y - reference_point.y)**2,
        (point_2.z - reference_point.z)**2]))
    return point_1 if distance_1 < distance_2 else point_2


def get_coplanar_faces(object, normal, road_height=0.1, threshold=0.001):
    return [f for f in object.data.polygons if f.normal.angle(normal) < threshold and f.center.z < road_height]


def get_crossing_points():
    return get_objects_from_collection("Nodes")


def get_line_meshes(curve_name: str):
    left_line = bpy.data.objects.get(f"Line_Mesh_Kerb_Left_{curve_name}")
    right_line = bpy.data.objects.get(f"Line_Mesh_Kerb_Right_{curve_name}")
    return left_line, right_line


def get_objects_from_collection(collection_name: str):
    collection = bpy.data.collections.get(collection_name)

    if collection:
        # Find all objects in the collection
        objects = [obj for obj in collection.objects]
        return objects

    return []


def get_outer_bottom_vertices(curve: bpy.types.Object, crossing_point):
    # Take the crossing point as the origin for the ray cast
    origin = crossing_point.location.xyz

    # Figure out the correct curve point
    closest_curve_point = get_closest_curve_point(curve, origin)

    # Determine the normal of the hit face when casting a ray from the origin to the correct curve point
    normal = calculate_ray_cast(origin, closest_curve_point)

    # Determine the road lane meshes corresponding to the curve
    road_lanes = get_objects_from_collection("Road Lanes")
    curve_road_lanes = [road_lane for road_lane in road_lanes if road_lane.name.endswith(curve.name)]

    z_threshold = 0.0001
    bottom_vertices = []

    # Iterate over all road lanes of the curve
    for curve_road_lane in curve_road_lanes:
        vertices = []
        faces = get_coplanar_faces(curve_road_lane, normal)

        for face in faces:
            # Iterate over all edges of each coplanar face and collect the bottom vertices
            for (index_0, index_1) in face.edge_keys:
                vertex_0 = curve_road_lane.data.vertices[index_0].co
                vertex_1 = curve_road_lane.data.vertices[index_1].co
                delta_z = abs(vertex_0.z - vertex_1.z)

                if delta_z <= z_threshold:
                    if vertex_0 not in vertices and vertex_0.z <= 0.001:
                        vertices.append(vertex_0)
                    if vertex_1 not in vertices and vertex_1.z <= 0.001:
                        vertices.append(vertex_1)

        vertices = find_closest_points(vertices, closest_curve_point)

        # Append only the furthest vertex
        bottom_vertices.append(vertices[-1][0])

    return bottom_vertices


def get_visible_curves():
    # Select all visible (not hidden) curves
    objects = bpy.context.scene.objects
    return [obj for obj in objects if obj.type == "CURVE" and obj.visible_get()]


def link_to_collection(mesh: bpy.types.Object, collection_name: str):
    collection = bpy.data.collections.get(collection_name)

    if collection is None:
        collection = bpy.data.collections.new(collection_name)
        bpy.context.scene.collection.children.link(collection)

    collection.objects.link(mesh)


def remove_collection(collection_name: str):
    collection = bpy.data.collections.get(collection_name)

    if collection:
        bpy.data.collections.remove(collection)


def set_origin(object: bpy.types.Object):
    object.select_set(True)
    bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center='BOUNDS')
    object.select_set(False)


def show_message_box(title="Message Box", message="", icon='INFO'):
    def draw(self, context):
        self.layout.label(text=message)

    bpy.context.window_manager.popup_menu(draw, title=title, icon=icon)

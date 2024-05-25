import bpy
import bmesh
import mathutils


# ------------------------------------------------------------------------
#    Helper Functions
# ------------------------------------------------------------------------

def add_mesh_to_curve(mesh_template: bpy.types.Object, curve: bpy.types.Object, name: str, lane_width: float, index: int):
  mesh = mesh_template.copy()
  mesh.data = mesh_template.data.copy()
  mesh.name = name + "_" + curve.name

  # Translate the created mesh according to the lane width and the number of lanes per road side (i.e. index)
  if "Lane" in name:
    vec = mathutils.Vector((0.0, lane_width * index - lane_width/2, 0.0))
    mesh.dimensions[1] = lane_width
  elif "Kerb" in name:
    # Keep for kerbs the original z location
    sign = -1 if index < 0 else 1
    vec = mathutils.Vector((0.0, lane_width * index + (sign * mesh.dimensions[1]/2), mesh.location[2]))
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

  # Select the mesh and apply its transformations (i.e. translation, rotation, scale)
  mesh.select_set(True)
  bpy.ops.object.transform_apply()
  mesh.select_set(False)


def add_roads(curves: list):
  road_lane_mesh_template_left = bpy.data.objects.get("Road_Lane_Border_Left")
  road_lane_mesh_template_right = bpy.data.objects.get("Road_Lane_Border_Right")
  road_lane_mesh_template_inside = bpy.data.objects.get("Road_Lane_Inside")
  kerb_mesh_template = bpy.data.objects.get("Kerb")

  if road_lane_mesh_template_left and road_lane_mesh_template_right and road_lane_mesh_template_inside:
    for curve in curves:
      curve.name = curve.name.replace(".", "_")
      # Select the curve and apply its transformations (i.e. translation, rotation, scale)
      # but without its properties such as radius
      curve.select_set(True)
      bpy.ops.object.transform_apply(properties=False)
      curve.select_set(False)

      # Get the curve's custom properties
      lane_width = curve["Lane Width"]
      left_lanes = curve["Left Lanes"]
      right_lanes = curve["Right Lanes"]

      for i in range(left_lanes):
        template = road_lane_mesh_template_left if i == left_lanes - 1 else road_lane_mesh_template_inside
        add_mesh_to_curve(template, curve, "Road_Lane_Left", lane_width, i + 1)
      for i in range(right_lanes):
        template = road_lane_mesh_template_right if i == right_lanes - 1 else road_lane_mesh_template_inside
        add_mesh_to_curve(template, curve, "Road_Lane_Right", lane_width, -i)

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

  else:
    print("Check whether the objects Road_Lane_Border_Left, Road_Lane_Border_Right and Road_Lane_Inside are present. At least one is missing.")

  return {'FINISHED'}


def add_line_following_mesh(mesh_name: str):
  mesh = bpy.data.objects.get(mesh_name)
  bm = bmesh.new()
  bm.from_mesh(mesh.data)

  top_faces_center = []
  # Calculate centers for all faces and save only the "top" (highest z-coordinate) faces
  for face in bm.faces:
    center = face.calc_center_median()

    if center[2] >= 0.1999:
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

  # Create a KD-Tree to perform a spatial search
  size = len(top_faces_center)
  kd = mathutils.kdtree.KDTree(size)
  for i, v in enumerate(top_faces_center):
    kd.insert(v.xyz, i)

  # Balance (build) the KD-Tree
  kd.balance()

  bm = bmesh.new()
  # Take the first point of the top faces centers, 
  # calculate the distances of all other points to it 
  # and add them as vertices to the new mesh
  for (co, index, dist) in kd.find_n(top_faces_center[0], size):
    bm.verts.new(co)

  # Ensure internal data needed for int subscription is initialized with verts, e.g. bm.verts[index]
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
        vec = mathutils.Vector(v1.co) - mathutils.Vector(v0.co)
        unit_vec = vec / edge_length
        object_position = v0.co + unit_vec * p
        break

      p -= edge_length

    if object_position:
      # Edit the mesh
      bpy.context.view_layer.objects.active = mesh
      bpy.ops.object.mode_set(mode = 'EDIT')
      # Create a BMesh (for editing) from mesh data
      mesh_data = bpy.context.edit_object.data
      bm = bmesh.from_edit_mesh(mesh_data)
      bm.verts.ensure_lookup_table()

      # Create a KD-Tree to perform a spatial search
      kd = mathutils.kdtree.KDTree(len(bm.verts))
      for i, v in enumerate(bm.verts):
        kd.insert(v.co, i)

      # Balance (build) the KD-Tree
      kd.balance()

      # Decrease the "height" (z-coordinate) of all vertices in a certain radius that are higher than 0
      radius = 2
      for (co, index, dist) in kd.find_range(object_position, radius):
        vertex = bm.verts[index]

        if vertex.co[2] > 0:
          vertex.co[2] -= 0.135

      bm.free()
      bpy.ops.object.mode_set(mode = 'OBJECT')

  bm_line.free()


def delete(collections):
  for collection_name in collections:
    collection = bpy.data.collections.get(collection_name)

    if collection is not None:
      # Find all objects in the collection, delete them and delete the collection
      objects = [obj for obj in collection.objects]

      while objects:
        bpy.data.objects.remove(objects.pop())

      bpy.data.collections.remove(collection)
  
  return {'FINISHED'}


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


def show_message_box(title="Message Box", message="", icon='INFO'):
  def draw(self, context):
    self.layout.label(text=message)

  bpy.context.window_manager.popup_menu(draw, title=title, icon=icon)

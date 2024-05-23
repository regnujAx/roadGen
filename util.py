import bpy
import bmesh
import math
import mathutils

from mathutils import Vector


# ------------------------------------------------------------------------
#    Helper Functions
# ------------------------------------------------------------------------

def add_mesh_to_curve(mesh_template: bpy.types.Object, name: str, lane_width: float, curve: bpy.types.Object, index: int):
  mesh = mesh_template.copy()
  mesh.data = mesh_template.data.copy()
  mesh.name = name + "_" + curve.name.replace(".", "_")

  # Translate the created mesh according to the lane width and the number of lanes per road side (i.e. index)
  if "Lane" in name:
    vec = mathutils.Vector((0.0, lane_width * index - lane_width/2, 0.0))
    mesh.dimensions[1] = lane_width
  elif "Kerb" in name:
    # Keep for kerbs the original z location
    sign = -1 if index < 0 else 1
    vec = mathutils.Vector((0.0, lane_width * index + (sign * mesh.dimensions[1]/2), mesh.location[2]))
  mesh.location = curve.location + vec

  # Apply the correct curve for the mesh modifiers
  mesh.modifiers['Array'].curve = curve
  mesh.modifiers['Curve'].object = curve

  # Add the created mesh to the correct collection
  collection_name = "Road Lanes" if "Road_Lane" in name else "Kerbs"
  collection = bpy.data.collections.get(collection_name)

  if collection is None:
    collection = bpy.data.collections.new(collection_name)
    bpy.context.scene.collection.children.link(collection)

  collection.objects.link(mesh)

  # Select the mesh and apply its modifiers
  bpy.context.view_layer.objects.active = mesh
  for modifier in mesh.modifiers:
    bpy.ops.object.modifier_apply(modifier=modifier.name)


def add_roads(curves: list):
  road_lane_mesh_template_left = bpy.data.objects.get("Road_Lane_Border_Left")
  road_lane_mesh_template_right = bpy.data.objects.get("Road_Lane_Border_Right")
  road_lane_mesh_template_inside = bpy.data.objects.get("Road_Lane_Inside")
  kerb_mesh_template = bpy.data.objects.get("Kerb")

  if road_lane_mesh_template_left and road_lane_mesh_template_right and road_lane_mesh_template_inside:
    for curve in curves:
      curve.select_set(True)
      bpy.ops.object.transform_apply(properties=False)
      curve.select_set(False)

      lane_width = curve["Lane Width"]
      left_lanes = curve["Left Lanes"]
      right_lanes = curve["Right Lanes"]

      for i in range(left_lanes):
        template = road_lane_mesh_template_left if i == left_lanes - 1 else road_lane_mesh_template_inside
        add_mesh_to_curve(template, "Road_Lane_Left", lane_width, curve, -i)
      for i in range(right_lanes):
        template = road_lane_mesh_template_right if i == right_lanes - 1 else road_lane_mesh_template_inside
        add_mesh_to_curve(template, "Road_Lane_Right", lane_width, curve, i + 1)
      
      if kerb_mesh_template:
        for side in ["Left", "Right"]:
          index = -left_lanes if side == "Left" else right_lanes
          add_mesh_to_curve(kerb_mesh_template, f"Kerb_{side}", lane_width, curve, index)

          if curve[f"{side} Dropped Kerbs"]:
            positions = [int(x) for x in curve[f"{side} Dropped Kerbs"].split(",")]
            print(side, ":", positions)
            add_dropped_kerbs_to_curve(curve, positions, side)
      else:
        print("Check whether the object Kerb is present, it is missing.")
        
  else:
    print("Check whether the objects Road_Lane_Border_Left, Road_Lane_Border_Right and Road_Lane_Inside are present. At least one is missing.")

  return {'FINISHED'}


def add_dropped_kerbs_to_curve(curve: bpy.types.Object, positions: list, side: str):
  mesh = bpy.data.meshes.new_from_object(curve)
  curve_mesh = bpy.data.objects.new("Mesh_" + side + "_" + curve.name, mesh)
  curve_mesh.matrix_world = curve.matrix_world
  mat = curve_mesh.matrix_world
  bpy.context.collection.objects.link(curve_mesh)

  meshEvalData = curve_mesh.data
  bm_curve = bmesh.new()
  bm_curve.from_mesh(meshEvalData)

  dropped_kerb_pos = None
  for pos in positions:
    p = pos
    total_length = 0

    for edge in bm_curve.edges:
      edge_length = edge.calc_length()
      total_length += edge_length
      if total_length > pos:
        v0 = edge.verts[0]
        v1 = edge.verts[1]
        vec = Vector(v1.co) - Vector(v0.co)
        unit_vec = vec / edge_length
        dropped_kerb_pos = mat @ v0.co + unit_vec * p
        break
      p -= edge_length

  bm_curve.clear()

  if dropped_kerb_pos:
    kerb_mesh = bpy.data.objects.get("Kerb_" + side + "_" + curve.name)
    bpy.context.view_layer.objects.active = kerb_mesh
    bpy.ops.object.mode_set(mode = 'EDIT')
    m = bpy.context.edit_object.data
    bm_kerb = bmesh.from_edit_mesh(m)
    bm_kerb.verts.ensure_lookup_table()

    kd = mathutils.kdtree.KDTree(len(bm_kerb.verts))
    for i, v in enumerate(bm_kerb.verts):
      kd.insert(v.co, i)

    kd.balance()

    for (co, index, dist) in kd.find_range(dropped_kerb_pos, 2):
      vertex = bm_kerb.verts[index]
      if vertex.co[2] > 0:
          vertex.co[2] -= 0.135
    bpy.ops.object.mode_set(mode = 'OBJECT')


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


def show_message_box(title="Message Box", message="", icon='INFO'):
  def draw(self, context):
    self.layout.label(text=message)

  bpy.context.window_manager.popup_menu(draw, title=title, icon=icon)

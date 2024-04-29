import bpy
import mathutils


# ------------------------------------------------------------------------
#    Helper Functions
# ------------------------------------------------------------------------

def add_road_lane(road_lane_mesh_template: bpy.types.Object, lane_width: float, curve: bpy.types.Object, index: int):
  road_lane_mesh = road_lane_mesh_template.copy()
  road_lane_mesh.data = road_lane_mesh_template.data.copy()
  road_lane_mesh.name = "Road_Lane_" + curve.name.replace(".", "_") 

  # Translate the created lane according to the lane width and the number of lanes per road side
  vec = mathutils.Vector((0.0, lane_width * index, 0.0))
  road_lane_mesh.location = curve.location + vec
  road_lane_mesh.dimensions[1] = lane_width

  # Apply the correct curve for mesh modifier
  road_lane_mesh.modifiers['Array'].curve = curve
  road_lane_mesh.modifiers['Curve'].object = curve

  # Add the created road lane mesh to the collection 'Road Lanes'
  collection = bpy.data.collections.get('Road Lanes')
  
  if collection is None:
    collection = bpy.data.collections.new("Road Lanes")
    bpy.context.scene.collection.children.link(collection)

  collection.objects.link(road_lane_mesh)

  # Select the road lane mesh and apply the modifiers
  bpy.context.view_layer.objects.active = road_lane_mesh
  for modifier in road_lane_mesh.modifiers:
    bpy.ops.object.modifier_apply(modifier=modifier.name)

def add_roads(curves: list, lane_width: float, left_lanes: int, right_lanes: int):
  road_lane_mesh_template_left = bpy.data.objects.get("Road_Lane_Border_Left")
  road_lane_mesh_template_right = bpy.data.objects.get("Road_Lane_Border_Right")
  road_lane_mesh_template_inside = bpy.data.objects.get("Road_Lane_Inside")

  if road_lane_mesh_template_left and road_lane_mesh_template_right:
    for curve in curves:
      for i in range(left_lanes):
        template = road_lane_mesh_template_left if i == 0 else road_lane_mesh_template_inside
        add_road_lane(template, lane_width, curve, -i)
      for i in range(right_lanes):
        template = road_lane_mesh_template_right if i == right_lanes - 1 else road_lane_mesh_template_inside
        add_road_lane(template, lane_width, curve, i + 1)

  return {'FINISHED'}

def show_message_box(title="Message Box", message="", icon='INFO'):
  def draw(self, context):
    self.layout.label(text=message)

  bpy.context.window_manager.popup_menu(draw, title=title, icon=icon)

import bpy

from .util import add_roads, show_message_box


# ------------------------------------------------------------------------
#    Operators
# ------------------------------------------------------------------------

class CG_CreateOneRoad(bpy.types.Operator):
  """Create one road from a specified curve in the scene"""
  bl_label = "Create One Road"
  bl_idname = "cg.create_one_road"
  bl_options = {'REGISTER', 'UNDO'}

  def execute(self, context):
    road_props = context.scene.road_props
    lane_width = road_props.lane_width
    left_lanes = road_props.left_lanes
    right_lanes = road_props.right_lanes
    curve = road_props.curve

    if curve is None:
      show_message_box("No curve selected!", "Please select a curve if you want to use this feature.")
      self.report({'INFO'}, "Please select a curve if you want to use this feature.")

      return {'FINISHED'}

    return add_roads([curve], lane_width, left_lanes, right_lanes)

class CG_CreateRoadsFromCollection(bpy.types.Operator):
  """Create roads from a specified collection"""
  bl_label = "Create Roads from Collection"
  bl_idname = "cg.create_roads_from_collection"
  bl_options = {'REGISTER', 'UNDO'}

  def execute(self, context):
    road_props = context.scene.road_props
    lane_width = road_props.lane_width
    left_lanes = road_props.left_lanes
    right_lanes = road_props.right_lanes
    collection = road_props.collection
    curves = [obj for obj in collection.objects if obj.type == "CURVE" and obj.visible_get()]

    if collection is None:
      show_message_box("No collection selected!", "Please select a collection if you want to use this feature.")
      self.report({'INFO'}, "Please select a collection if you want to use this feature.")

      return {'FINISHED'}

    return add_roads(curves, lane_width, left_lanes, right_lanes)

class CG_CreateRoads(bpy.types.Operator):
  """Create roads from all visible (not hidden) curves in the scene"""
  bl_label = "Create All Roads"
  bl_idname = "cg.create_roads"
  bl_options = {'REGISTER', 'UNDO'}

  def execute(self, context):
    # Select all visible (not hidden) curves
    objects = bpy.context.scene.objects
    curves = [obj for obj in objects if obj.type == "CURVE" and obj.visible_get()]

    road_props = context.scene.road_props
    lane_width = road_props.lane_width
    left_lanes = road_props.left_lanes
    right_lanes = road_props.right_lanes

    return add_roads(curves, lane_width, left_lanes, right_lanes)

class CG_DeleteRoads(bpy.types.Operator):
  """Delete all created roads in the collection 'Road Lanes' and the collection itself"""
  bl_label = "Delete All Roads"
  bl_idname = "cg.delete_all"
  bl_options = {'REGISTER', 'UNDO'}

  def execute(self, context):
    collection = bpy.data.collections.get('Road Lanes')

    if collection is not None:
      # Find all objects in the collection, delete them and delete the collection
      objects = [obj for obj in collection.objects]

      while objects:
        bpy.data.objects.remove(objects.pop())

      bpy.data.collections.remove(collection)

    return {'FINISHED'}

  def invoke(self, context, event):
    wm = context.window_manager

    return wm.invoke_confirm(self, event)

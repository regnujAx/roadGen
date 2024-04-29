import bpy


def is_visible_curve(self, object):
  return object.type == "CURVE" and object.visible_get()


# ------------------------------------------------------------------------
#    Properties
# ------------------------------------------------------------------------

class CG_RoadProperties(bpy.types.PropertyGroup):
  lane_width : bpy.props.FloatProperty(
    name="Lane Width",
    description="Width of each road lane in meter (between 1.0 and 4.0 meter)",
    soft_min=1.0,
    soft_max=4.0,
    default=2.5
  )

  left_lanes : bpy.props.IntProperty(
    name="Left Lanes",
    description="Number (between 0 and 4) of driving lanes on the left road side",
    soft_min=0,
    soft_max=4,
    default=1
  )

  right_lanes : bpy.props.IntProperty(
    name="Right Lanes",
    description="Number (between 0 and 4) of driving lanes on the right road side",
    soft_min=0,
    soft_max=4,
    default=1
  )
  
  curve : bpy.props.PointerProperty(
    type=bpy.types.Object,
    name="Curve",
    description="Select a visible (not hidden) curve for road generation",
    poll=is_visible_curve
  )

  collection : bpy.props.PointerProperty(
    type=bpy.types.Collection,
    name="Collection",
    description="Select a collection for road generation"
  )

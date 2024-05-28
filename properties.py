import bpy


def is_visible_curve(self, object):
    return object.type == "CURVE" and object.visible_get()


# ------------------------------------------------------------------------
#    Properties
# ------------------------------------------------------------------------

class CG_RoadProperties(bpy.types.PropertyGroup):
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

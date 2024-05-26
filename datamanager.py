import bpy


class CG_DataManager():
  def __init__(self, curves):
    self.curves = curves
  
  def createCrossroadData(self):
    return {'FINISHED'}

  def createRoadData(self):
    for curve in self.curves:
      if curve.get("Lane Width") is None:
        curve["Lane Width"] = 2.50
        # Edit the propertiy
        property_manager = curve.id_properties_ui("Lane Width")
        property_manager.update(soft_min=1, soft_max=4, subtype='DISTANCE')
      if curve.get("Left Lanes") is None:
        curve["Left Lanes"] = 1
        property_manager = curve.id_properties_ui("Left Lanes")
        property_manager.update(soft_min=1, soft_max=4)
      if curve.get("Right Lanes") is None:
        curve["Right Lanes"] = 1
        property_manager = curve.id_properties_ui("Right Lanes")
        property_manager.update(soft_min=1, soft_max=4)
      if curve.get("Lantern Distance") is None:
        curve["Lantern Distance"] = 10.0
        property_manager = curve.id_properties_ui("Lantern Distance")
        property_manager.update(soft_min=1, soft_max=5000, subtype='DISTANCE')
      if curve.get("Left Dropped Kerbs") is None:
        curve["Left Dropped Kerbs"] = "5"
        property_manager = curve.id_properties_ui("Left Dropped Kerbs")
        property_manager.update(description="Indicates where (in meters, separated by commas) there is a dropped kerb on the left-hand side of the road")
      if curve.get("Right Dropped Kerbs") is None:
        curve["Right Dropped Kerbs"] = "15,30"
        property_manager = curve.id_properties_ui("Right Dropped Kerbs")
        property_manager.update(description="Indicates where (in meters, separated by commas) there is a dropped kerb on the right-hand side of the road")

    return {'FINISHED'}


import bpy


class CG_DataManager():
  def __init__(self, curves):
    self.curves = curves
  
  def createCrossroadData(self):
    return {'FINISHED'}

  def createRoadData(self):
    for curve in self.curves:
      curve["Lane Width"] = 2.50
      curve["Left Lanes"] = 1
      curve["Right Lanes"] = 1
      curve["Lantern Distance"] = 10.0
      curve["Left Dropped Kerbs"] = "5"
      curve["Right Dropped Kerbs"] = "15,30"

      # Edit the properties
      property_manager = curve.id_properties_ui("Lane Width")
      property_manager.update(soft_min=1, soft_max=4, subtype='DISTANCE')
      property_manager = curve.id_properties_ui("Left Lanes")
      property_manager.update(soft_min=1, soft_max=4)
      property_manager = curve.id_properties_ui("Right Lanes")
      property_manager.update(soft_min=1, soft_max=4)
      property_manager = curve.id_properties_ui("Lantern Distance")
      property_manager.update(soft_min=1, soft_max=5000, subtype='DISTANCE')
      property_manager = curve.id_properties_ui("Left Dropped Kerbs")
      property_manager.update(description="Indicates where (in meters, separated by commas) there is a dropped kerb on the left-hand side of the road")
      property_manager = curve.id_properties_ui("Right Dropped Kerbs")
      property_manager.update(description="Indicates where (in meters, separated by commas) there is a dropped kerb on the right-hand side of the road")

    return {'FINISHED'}


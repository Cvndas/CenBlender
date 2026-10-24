bl_info = {
    "name": "CenFoliage",
    "author": "Lrodas",
    "version": (1, 1),
    "blender": (4, 4, 0),
    "location": "View3D > Sidebar > Cen Tab",
    "description": "Exporting points to json.",
    "category": "Cen Tools",
}

import bpy
import CenLib
import os
import json
import time

from bpy.types import Context, Panel

PLANT_DOMINATION_THRESHOLD = 0.98


def GetAllInstanceObjects():
    collections = CenLib.GetCollectionsByPattern("-Instances")
    if collections is None or len(collections) == 0:
        CenLib.PopupError("Failed to find any collections with -Instances in the name")
        return None

    allObjects = []
    for col in collections:
        for obj in CenLib.GetObjectsInCollection(col):
            allObjects.append(obj)

    return allObjects


def SetMinimumDensity(context: Context, instanceTargetName: str, densityValueMin: float, densityValueMax: float):
    objects = GetAllInstanceObjects()
    if not objects:
        return CenLib.Cancelled()

    for obj in objects:
        for mod in CenLib.GetModifiers(obj):
            if ModIsInstancePainter(mod):
                if mod.name == instanceTargetName:
                    property = CenLib.GetGeometryNodeField(mod, "Density")
                    # Clamp the density between the min and max values
                    property.value = max(densityValueMin, min(densityValueMax, property.value))

    CenLib.PopupPrint(f"Clamped density for type {instanceTargetName} to {densityValueMin:.3f} - {densityValueMax:.3f}")
    return CenLib.Finished()


def ApplyMinimumDistanceToAll(context: Context, distanceValue: float):
    objects = GetAllInstanceObjects()
    if not objects:
        return CenLib.Cancelled()

    for obj in objects:
        for mod in CenLib.GetModifiers(obj):
            if ModIsInstancePainter(mod):
                CenLib.GetGeometryNodeField(mod, "Distance Min").value = distanceValue

    CenLib.PopupPrint(f"Set the minimum distance for all instances to {distanceValue:.3f}")
    return CenLib.Finished()


def MakeRoomForSelected(makesRoom: str, forValue: str):
    for obj in CenLib.GetSelectedObjects():
        makesRoomGroup = CenLib.GetVertexGroup(obj, makesRoom)
        forGroup = CenLib.GetVertexGroup(obj, forValue)

        if not makesRoomGroup or not forGroup:
            continue

        submissiveGroupIndex = makesRoomGroup.index
        dominatorGroupIndex = forGroup.index

        for vertex in obj.data.vertices:
            for vertexGroupValue in vertex.groups:
                if vertexGroupValue.group == submissiveGroupIndex:
                    dominatesThisVertex = False
                    for otherVertexGroupValue in vertex.groups:
                        if otherVertexGroupValue.group == dominatorGroupIndex and otherVertexGroupValue.weight >= PLANT_DOMINATION_THRESHOLD:
                            dominatesThisVertex = True
                            break

                    if dominatesThisVertex:
                        obj.vertex_groups[submissiveGroupIndex].remove([vertex.index])


def DeleteInstancePainter(instancePainterName: str):
    objects = CenLib.GetSelectedObjects()
    deletedCount = 0
    for obj in objects:
        for mod in list(CenLib.GetModifiers(obj)):
            if ModIsInstancePainter(mod) and mod.name == instancePainterName:
                CenLib.DeleteModifier(mod)
                deletedCount += 1

    CenLib.PopupPrint(f"Deleted InstancePainter '{instancePainterName}' from {deletedCount} modifier(s)")
    return CenLib.Finished()


def DeleteVertexGroup(vertexGroupName: str):
    objects = CenLib.GetSelectedObjects()
    deletedCount = 0
    for obj in objects:
        group = CenLib.GetVertexGroup(obj, vertexGroupName)
        if group:
            obj.vertex_groups.remove(group)
            deletedCount += 1

    CenLib.PopupPrint(f"Deleted Vertex Group '{vertexGroupName}' from {deletedCount} object(s)")
    return CenLib.Finished()


def RunInstancer_Selected(context: Context):
    objects = CenLib.GetSelectedObjects()
    return RunInstancer(context, objects, False)


def RunInstancer_All(context: Context):
    collections = CenLib.GetCollectionsByPattern("-Instances")
    if collections is None or len(collections) == 0:
        CenLib.PopupError("Failed to find any collections with -Instances in the name")
        return CenLib.Cancelled()

    allObjects = []
    for col in collections:
        for obj in CenLib.GetObjectsInCollection(col):
            allObjects.append(obj)
            
    

    return RunInstancer(context, allObjects, True)


def RunInstancer(context: Context, objects, deleteOld):
    start_FullTime = time.time()
    outputPath = context.scene.output_directory_path
    if not outputPath:
        CenLib.PopupError("Forgot to set an output path")
        return CenLib.Cancelled()

    if deleteOld:
        for oldFile in os.listdir(outputPath):
            if oldFile.endswith(".json") or oldFile.endswith(".json.meta"):
                fileToRemove = os.path.join(outputPath, oldFile)
                if os.path.isfile(fileToRemove):
                    os.remove(fileToRemove)

    absolutePath = bpy.path.abspath(outputPath)
    if not os.path.exists(absolutePath):
        CenLib.PopupError("Path did not exist.")
        return CenLib.Cancelled()

    originalSelected = CenLib.GetSelectedObjects()
    originalActive = CenLib.GetActiveObject()

    for obj in objects:
        if not CenLib.IsTransformApplied(obj):
            CenLib.PopupError(f"Transform wasn't applied on {obj.name}")
            return CenLib.Cancelled()


    modsToReActivate = CenLib.DisableAllActiveModifiers(objects)

    objectIndex = 1
    for obj in objects:
        print('\n')
        print(f"Exporting the instances for object {objectIndex} of {len(objects)}: {obj.name}...")
        startTime = time.time()
        ProcessAndExportInstancesOfObject(obj, outputPath)
        endTime = time.time()
        timeSpent = endTime - startTime
        print(f"Exported all instances for {obj.name} in {timeSpent:.2f} seconds")
        print('\n')

        totalSpentSoFar = time.time() - start_FullTime
        estimatedTotal = totalSpentSoFar / objectIndex * len(objects)
        remaining = estimatedTotal - totalSpentSoFar

        remainingMinutes = remaining / 60

        print(
            f"So far: {totalSpentSoFar:.2f} seconds. Expected remaining time: {remaining:.2f} seconds, or {remainingMinutes} minutes")
        objectIndex += 1

    if originalSelected:
        for ogSel in originalSelected:
            CenLib.SelectObject(ogSel)

    if originalActive:
        CenLib.SelectObject(originalActive)

    CenLib.EnableListOfModifiers(modsToReActivate)
    
    end_FullTime = time.time()
    fullElapsed = end_FullTime - start_FullTime
    CenLib.PopupPrint(f"Successfully exported the instances of {len(objects)} objects in {fullElapsed:.2f} seconds")

    return CenLib.Finished()


def ProcessAndExportInstancesOfObject(obj, outputPath):
    modList = []
    for mod in CenLib.GetModifiers(obj):
        if CenLib.IsGeonodeModifier(mod):
            if CenLib.GetGeonodeTypeName(mod) == "InstancePainter":
                modList.append(mod)
                CenLib.MakeModifierInactive(mod)

    seed = 0

    cleanSlateDuple = CenLib.DuplicateObject(obj)
    for mod in list(CenLib.GetModifiers(cleanSlateDuple)):
        if not CenLib.IsGeonodeModifier(mod):
            CenLib.DeleteModifier(mod)

    for mainObjectFoliage in modList:
        print(f"    Processing modifier {mainObjectFoliage.name} of {obj.name}...")
        seed += 1
        CenLib.ClearSelection()
        vertexGroup = CenLib.GetGeometryNodeField(mainObjectFoliage, "WeightPaint Vertex Group Name")
        if not CenLib.VertexGroupHasWeight(obj, vertexGroup.value):
            print(f"        Vertex group {vertexGroup.value} on {obj.name} has no weight, so it's being skipped")
            continue

        dupe = CenLib.DuplicateObject(cleanSlateDuple)
        try:
            dupeMod = CenLib.GetModifier(dupe, mainObjectFoliage.name, 0)
            CenLib.MakeModifierActive(dupeMod)
            CenLib.GetGeometryNodeField(dupeMod, "Seed").value = seed
            CenLib.GetGeometryNodeField(dupeMod, "Exporting Points").value = True
            region = obj.name
            instanceType = dupeMod.name
            fileName = f"{region}--{instanceType}.json"
            filePath = os.path.join(outputPath, fileName)

            for otherMod in list(CenLib.GetModifiers(dupe)):
                if otherMod.name != dupeMod.name:
                    CenLib.DeleteModifier(otherMod)

            CenLib.ConvertToMesh(dupe)
            vertexCoordinates = CenLib.GetVertexCoordinatesInWorldSpace(dupe)

            if len(vertexCoordinates) == 0:
                print(f"        {vertexGroup.name} on {obj.name} would produce no points, so it's being skipped")
                continue

            positions = {}
            arr = []
            for vertex in vertexCoordinates:
                # arr.append({"x": vertex.x, "y": vertex.z, "z": vertex.y})
                arr.append({
                    "x": round(vertex.x, 4),
                    "y": round(vertex.z, 4),
                    "z": round(vertex.y, 4)
                })
            positions["Positions"] = arr

            with open(filePath, "w") as outputJsonFile:
                json.dump(positions, outputJsonFile, indent=1)

        except Exception as e:
            CenLib.PopupError(f"An error occurred while processing {obj}, modifier {mainObjectFoliage.name}: {e}")

        finally:
            CenLib.DeleteObject(dupe)


    CenLib.DeleteObject(cleanSlateDuple)
    


def ModIsInstancePainter(mod):
    return CenLib.IsGeonodeModifier(mod) and CenLib.GetGeonodeTypeName(mod) == "InstancePainter"


def ShareInstances():
    configsToShare = {}
    objectsToShareWith = GetAllInstanceObjects()
    for obj in objectsToShareWith:
        for mod in CenLib.GetModifiers(obj):
            if ModIsInstancePainter(mod):
                if mod.name not in configsToShare:
                    density = CenLib.GetGeometryNodeField(mod, "Density").value
                    vertexGroupName = CenLib.GetGeometryNodeField(mod, "WeightPaint Vertex Group Name").value
                    nodeGroup = mod.node_group
                    configsToShare[mod.name] = InstanceConfig(density, vertexGroupName, nodeGroup)

    for obj in objectsToShareWith:
        for configName, config in configsToShare.items():
            alreadyHasModifier = False
            for mod in CenLib.GetModifiers(obj):
                if ModIsInstancePainter(mod):
                    if mod.name == configName:
                        alreadyHasModifier = True
                        break
            if alreadyHasModifier:
                continue

            copiedMod = obj.modifiers.new(name=configName, type='NODES')
            copiedMod.node_group = config.nodeGroup
            CenLib.MakeModifierInactive(copiedMod)
            CenLib.GetGeometryNodeField(copiedMod, "Density").value = config.density
            CenLib.GetGeometryNodeField(copiedMod, "WeightPaint Vertex Group Name").value = config.vertexGroupName

            CenLib.AddVertexGroupIfNotPresent(obj, config.vertexGroupName)

    CenLib.PopupPrint("Shared all addons!")
    return CenLib.Finished()


class InstanceConfig:
    def __init__(self, density, vertexGroupName, nodeGroup):
        self.density = density
        self.vertexGroupName = vertexGroupName
        self.nodeGroup = nodeGroup


class CENINSTANCER_OT_SetMinimumDensity(bpy.types.Operator):
    bl_idname = "ceninstancer.set_minimum_density"
    bl_label = "Clamp Density"
    bl_description = "Clamp the density for instance painting between the min and max values"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        densityName = context.scene.ceninstancer_density_name
        densityValueMin = context.scene.ceninstancer_density_min
        densityValueMax = context.scene.ceninstancer_density_max
        SetMinimumDensity(context, densityName, densityValueMin, densityValueMax)
        return CenLib.Finished()


class CENINSTANCER_OT_ApplyMinimumDistance(bpy.types.Operator):
    bl_idname = "ceninstancer.apply_minimum_distance_to_all"
    bl_label = "Apply Minimum Distance to All"
    bl_description = "Apply the minimum distance to all objects"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        distanceValue = context.scene.ceninstancer_distance_value
        ApplyMinimumDistanceToAll(context, distanceValue)
        return CenLib.Finished()


class CENINSTANCER_OT_MakeRoomForSelected(bpy.types.Operator):
    bl_idname = "ceninstancer.make_room_for_selected"
    bl_label = "Make Room For - Selected"
    bl_description = "Make room on selected objects in the scene"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        makesRoom = context.scene.ceninstancer_makes_room
        forValue = context.scene.ceninstancer_for_value
        MakeRoomForSelected(makesRoom, forValue)
        return CenLib.Finished()


class CENINSTANCER_OT_DeleteInstancePainter(bpy.types.Operator):
    bl_idname = "ceninstancer.delete_instance_painter"
    bl_label = "Delete InstancePainter"
    bl_description = "Delete the specified InstancePainter modifier from selected objects"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        instancePainterName = context.scene.ceninstancer_delete_painter_name
        DeleteInstancePainter(instancePainterName)
        return CenLib.Finished()


class CENINSTANCER_OT_DeleteVertexGroups(bpy.types.Operator):
    bl_idname = "ceninstancer.delete_vertex_groups"
    bl_label = "Delete Vertex Groups"
    bl_description = "Delete the specified vertex group from selected objects"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        vertexGroupName = context.scene.ceninstancer_delete_vertex_group_name
        DeleteVertexGroup(vertexGroupName)
        return CenLib.Finished()


class CenInstancerPanel(Panel):
    bl_label = "CenFoliage"
    bl_idname = "VIEW3D_PT_CenFoliage"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Centradigon"

    def draw(self, context: Context):
        layout = self.layout

        # Metadata box at the top
        box = layout.box()
        selectedObjects = CenLib.GetSelectedObjects()
        activeObj = CenLib.GetActiveObject()
        box.label(text=f"Selected Objects: {len(selectedObjects)}", icon="SELECT_SET")
        box.label(text=f"Active Object: {activeObj.name if activeObj else '<none>'}", icon="OBJECT_DATA")

        layout.separator()

        colLayout = layout.column(align=False)

        colLayout.prop(context.scene, "output_directory_path")

        colLayout.separator()

        colLayout.operator("wm.export_for_selected_objects")
        colLayout.operator("wm.export_for_all_objects")

        colLayout.separator()

        colLayout.operator("wm.share_instances_throughout_collection")

        colLayout.separator()
        colLayout.label(text="Density Clamping:", icon="SETTINGS")
        colLayout.prop(context.scene, "ceninstancer_density_name")

        # Two sliders side-by-side
        row = colLayout.row(align=True)
        row.prop(context.scene, "ceninstancer_density_min", text="Min")
        row.prop(context.scene, "ceninstancer_density_max", text="Max")

        colLayout.operator("ceninstancer.set_minimum_density", icon="MODIFIER")

        colLayout.separator()
        colLayout.label(text="Minimum Distance Settings:", icon="DRIVER_DISTANCE")
        colLayout.prop(context.scene, "ceninstancer_distance_value")
        colLayout.operator("ceninstancer.apply_minimum_distance_to_all", icon="MODIFIER")

        colLayout.separator()
        colLayout.label(text="Plant Domination:", icon="SETTINGS")
        colLayout.prop(context.scene, "ceninstancer_makes_room")
        colLayout.prop(context.scene, "ceninstancer_for_value")

        row = colLayout.row(align=True)
        row.operator("ceninstancer.make_room_for_selected", icon="OBJECT_DATA")

        colLayout.separator()
        colLayout.label(text="Deletion Tools:", icon="TRASH")
        colLayout.prop(context.scene, "ceninstancer_delete_painter_name")
        colLayout.operator("ceninstancer.delete_instance_painter", icon="REMOVE")

        colLayout.separator()
        colLayout.prop(context.scene, "ceninstancer_delete_vertex_group_name")
        colLayout.operator("ceninstancer.delete_vertex_groups", icon="REMOVE")


class ShareInstanceTypesThroughoutCollection(bpy.types.Operator):
    bl_idname = "wm.share_instances_throughout_collection"
    bl_label = "Share Instances"

    def execute(self, context):
        return ShareInstances()


class ExportForSelectedObjects(bpy.types.Operator):
    bl_idname = "wm.export_for_selected_objects"
    bl_label = "Export Instances: SELECTED"

    def execute(self, context):
        return RunInstancer_Selected(context)


class ExportForAllObjects(bpy.types.Operator):
    bl_idname = "wm.export_for_all_objects"
    bl_label = "Export: ALL"

    def execute(self, context):
        return RunInstancer_All(context)


def register() -> None:
    bpy.utils.register_class(CenInstancerPanel)
    bpy.utils.register_class(ExportForSelectedObjects)
    bpy.utils.register_class(ExportForAllObjects)
    bpy.utils.register_class(ShareInstanceTypesThroughoutCollection)
    bpy.utils.register_class(CENINSTANCER_OT_SetMinimumDensity)
    bpy.utils.register_class(CENINSTANCER_OT_ApplyMinimumDistance)
    bpy.utils.register_class(CENINSTANCER_OT_MakeRoomForSelected)
    bpy.utils.register_class(CENINSTANCER_OT_DeleteInstancePainter)
    bpy.utils.register_class(CENINSTANCER_OT_DeleteVertexGroups)

    bpy.types.Scene.output_directory_path = bpy.props.StringProperty(
        name="Output",
        description="Choose the folder corresponding to the level associated with this .blend file..",
        subtype="FILE_PATH",
    )

    bpy.types.Scene.ceninstancer_density_name = bpy.props.StringProperty(
        name="Density Instance Name",
        description="Name of the geometry nodes field to modify",
        default="Density",
    )

    bpy.types.Scene.ceninstancer_density_min = bpy.props.FloatProperty(
        name="Min Density",
        description="Minimum value to clamp the density to",
        default=20.0,
        min=0.0,
        max=100.0,
        step=0.01,
    )

    bpy.types.Scene.ceninstancer_density_max = bpy.props.FloatProperty(
        name="Max Density",
        description="Maximum value to clamp the density to",
        default=100.0,
        min=0.0,
        max=100.0,
        step=0.01,
    )

    bpy.types.Scene.ceninstancer_distance_value = bpy.props.FloatProperty(
        name="Distance Value",
        description="Value for the minimum distance",
        default=1.0,
        min=0.0,
        max=100.0,
        step=0.01,
    )

    bpy.types.Scene.ceninstancer_makes_room = bpy.props.StringProperty(
        name="Makes Room",
        description="What makes room",
        default="",
    )

    bpy.types.Scene.ceninstancer_for_value = bpy.props.StringProperty(
        name="For",
        description="What the room is for",
        default="",
    )

    bpy.types.Scene.ceninstancer_delete_painter_name = bpy.props.StringProperty(
        name="Painter to Delete",
        description="Name of the InstancePainter modifier to delete from selected objects",
        default="",
    )

    bpy.types.Scene.ceninstancer_delete_vertex_group_name = bpy.props.StringProperty(
        name="Vertex Group to Delete",
        description="Name of the vertex group to delete from selected objects",
        default="",
    )


def unregister() -> None:
    bpy.utils.unregister_class(CenInstancerPanel)
    bpy.utils.unregister_class(ExportForSelectedObjects)
    bpy.utils.unregister_class(ExportForAllObjects)
    bpy.utils.unregister_class(ShareInstanceTypesThroughoutCollection)
    bpy.utils.unregister_class(CENINSTANCER_OT_SetMinimumDensity)
    bpy.utils.unregister_class(CENINSTANCER_OT_ApplyMinimumDistance)
    bpy.utils.unregister_class(CENINSTANCER_OT_MakeRoomForSelected)
    bpy.utils.unregister_class(CENINSTANCER_OT_DeleteInstancePainter)
    bpy.utils.unregister_class(CENINSTANCER_OT_DeleteVertexGroups)

    del bpy.types.Scene.output_directory_path
    del bpy.types.Scene.ceninstancer_density_name
    del bpy.types.Scene.ceninstancer_density_min
    del bpy.types.Scene.ceninstancer_density_max
    del bpy.types.Scene.ceninstancer_distance_value
    del bpy.types.Scene.ceninstancer_makes_room
    del bpy.types.Scene.ceninstancer_for_value
    del bpy.types.Scene.ceninstancer_delete_painter_name
    del bpy.types.Scene.ceninstancer_delete_vertex_group_name


def RunFromScript() -> None:
    print("Welcome from the script little cro. How are you, little vro?")
    register()


if __name__ == "__main__":
    RunFromScript()
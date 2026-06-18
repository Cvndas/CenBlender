bl_info = {
    "name": "CenInstancer",
    "author": "Lrodas",
    "version": (1, 1),
    "blender": (4, 4, 0),
    "location": "View3D > Sidebar > Centradigon Tab",
    "description": "Exporting points to json.",
    "category": "Centradigon Tools",
}

from typing import Type

import bpy
import CenLib
import json
import os
import time

from bpy.types import Context, Panel
from mathutils import Vector
from typing import List, Optional

KEY_DENSITY = "Socket_3"
KEY_VERTEX_GROUP = "Socket_10"
KEY_DISTANCE_MIN = "Socket_11"
KEY_EXPORTING_POINTS = "Socket_9"
KEY_SEED = "Socket_4"

PLANT_DOMINATION_THRESHOLD = 0.6



def AddUniqueInstancePaintersToList(collectedModifiers, host):
    for newMod in CenLib.GetModifiers(host):
        if newMod.type != "NODES":
            continue

        if not newMod.node_group or newMod.node_group.name != "InstancePainter":
            continue

        modAlreadyCollected = False
        for previousMod, _ in collectedModifiers:
            if previousMod.name == newMod.name:
                modAlreadyCollected = True
                break
        if modAlreadyCollected:
            continue

        collectedModifiers.append((newMod, ComputeAvgEdgeLen(host)))




def ComputeAvgEdgeLen(targetObj):
    if targetObj.type != "MESH":
        print("Target object " + targetObj.name + " was not a mesh type object.")
        return 0.0

    meshData = targetObj.data
    totalLen = 0.0

    if not meshData.edges:
        print("Target object " + targetObj.name + "didn't have valid edges.")
        return 0.0

    edgeCount = 0
    for edge in meshData.edges:
        v1, v2 = (
            meshData.vertices[edge.vertices[0]].co,
            meshData.vertices[edge.vertices[1]].co,
        )
        totalLen += (v2 - v1).length
        edgeCount += 1
        if edgeCount > 20000:
            break

    averageLen = totalLen / edgeCount
    return averageLen


def AddAllUniqueInstancePaintersIfNotAlreadyPresent(
    uniqueInstancePainterModifiers, c
):
    for uniqueMod, edgeLenOfOriginal in uniqueInstancePainterModifiers:
        modifierAlreadyPresent = False
        for existingMod in c.modifiers:
            if existingMod.name == uniqueMod.name:
                modifierAlreadyPresent = True
                break

        if modifierAlreadyPresent:
            continue

        copiedMod = c.modifiers.new(name=uniqueMod.name, type=uniqueMod.type)
        copiedMod.show_viewport = False
        copiedMod.show_render = False

        nodeTree = uniqueMod.node_group
        copiedMod.node_group = nodeTree

        copiedMod[KEY_VERTEX_GROUP] = uniqueMod[KEY_VERTEX_GROUP]
        copiedMod[KEY_DISTANCE_MIN] = uniqueMod[KEY_DISTANCE_MIN]

        edgeLenOfThis = ComputeAvgEdgeLen(c)
        copiedDensity = uniqueMod[KEY_DENSITY]
        rawDifference = edgeLenOfThis - edgeLenOfOriginal
        adjustedDifference = rawDifference / 3
        adjustedThisLen = edgeLenOfOriginal + adjustedDifference

        adjustedDensity = copiedDensity * adjustedThisLen / edgeLenOfOriginal
        copiedMod[KEY_DENSITY] = adjustedDensity


def AddAllUniqueVertexGroupsIfNotAlreadyPresent(
    uniqueVertexGroupNames, targetObject
):
    existingVertexGroupNames = set()
    for existingVg in targetObject.vertex_groups:
        if existingVg.name not in existingVertexGroupNames:
            existingVertexGroupNames.add(existingVg.name)

    for uniqueVg in uniqueVertexGroupNames:
        if uniqueVg not in existingVertexGroupNames:
            targetObject.vertex_groups.new(name=uniqueVg)
            existingVertexGroupNames.add(uniqueVg)


def ShareInstances():

    old = bpy.context.preferences.edit.use_global_undo
    bpy.context.preferences.edit.use_global_undo = False

    try:
        collectionsToShareWith = CenLib.GetCollectionsByPattern("-Instances")
        objectsToShareWith = []
        for colToShareWith in collectionsToShareWith:
            objectsToShareWith += CenLib.GetObjectsInCollection(colToShareWith)

        uniqueInstancePainterModifiers = []
        uniqueVertexGroupNames = set()

        for obj in objectsToShareWith:
            AddUniqueInstancePaintersToList(uniqueInstancePainterModifiers, obj)

            vertexGroupsOnObject = CenLib.GetVertexGroupNames(obj)
            for vGroup in vertexGroupsOnObject:
                if vGroup not in uniqueVertexGroupNames:
                    uniqueVertexGroupNames.add(vGroup)


        for obj in objectsToShareWith:
            AddAllUniqueInstancePaintersIfNotAlreadyPresent(
                uniqueInstancePainterModifiers, c
            )
            AddAllUniqueVertexGroupsIfNotAlreadyPresent(
                uniqueVertexGroupNames, c
            )
            print("Added instance painters and vertex groups to object " + c.name)

        print("And we're done!")

    finally:
        bpy.context.preferences.edit.use_global_undo = old

    return CenLib.Finished()


def FindAllInstancers()->List[bpy.types.Modifier]:
    allInstancers = []
    allObjects = CenLib.GetAllObjects()
    for obj in allObjects:
        for mod in CenLib.GetModifiers(obj):
            if CenLib.IsGeonodeModifier(mod):
                if CenLib.GetGeonodeTypeName(mod) == "InstancePainter":
                    allInstancers.append(mod)

    return allInstancers


def SetMinimumDensity(context: Context, densityName: str, densityValue: float):
    for instancer in FindAllInstancers():
        if instancer.name == densityName:
            instancer[KEY_DENSITY] = densityValue

def MakeRoomFor(obj: bpy.types.Object, makesRoom: str, forValue: str):
    makesRoomGroup = CenLib.GetVertexGroup(obj, makesRoom)
    forGroup = CenLib.GetVertexGroup(obj, forValue)

    if not makesRoomGroup or not forGroup:
        return

    makeRoomIndex = makesRoomGroup.index
    forIndex = forGroup.index

    
    for vertex in obj.data.vertices:
        for vertexGroup in vertex.groups:
            if vertexGroup.group == makeRoomIndex:

                hasForWeight = False
                for g in vertex.groups:
                    if g.group == forIndex and g.weight >= PLANT_DOMINATION_THRESHOLD:
                        hasForWeight = True
                        break

                if hasForWeight:
                    obj.vertex_groups[makeRoomIndex].remove([vertex.index])
                    break

    obj.data.update()
        

def MakeRoomForSelected(makesRoom: str, forValue: str):
    for selected in CenLib.GetSelectedObjects():
        MakeRoomFor(selected, makesRoom, forValue)


def MakeRoomForAll(makesRoom: str, forValue: str):
    for obj in CenLib.GetAllObjects():
        MakeRoomFor(obj, makesRoom, forValue)


def RunInstancer(context: Context, exportMode: str):
    outputPath = context.scene.output_directory_path
    if not outputPath:
        CenLib.PopupError("Forgot to send output path!")
        return CenLib.Cancelled()

    absolutePath = bpy.path.abspath(outputPath)
    if not os.path.exists(absolutePath):
        CenLib.PopupError("Path did not exist.")
        return CenLib.Cancelled()
    print("Will put the files in " + absolutePath)

    levelName = context.scene.level_name

    if not levelName:
        CenLib.PopupError("Forgot to set the level name!")
        return CenLib.Cancelled()

    objectsToExport = []

    if exportMode == "SELECTED":
        objectsToExport = CenLib.GetSelectedObjects()
        if not objectsToExport:
            CenLib.PopupError("No mesh objects selected!")
            return CenLib.Cancelled()
        print(f"Exporting {len(objectsToExport)} selected object(s)")

    elif exportMode == "ALL":
        instancesCollections = CenLib.GetCollectionsByPattern("Instances")
        if len(instancesCollections) == 0:
            CenLib.PopupError(
                "There are no collections that have Instances in the name"
            )
            return CenLib.Cancelled()

        objectsToExport = []
        for instCol in instancesCollections:
            for obj in CenLib.GetObjectsInCollection(instCol):
                objectsToExport.append(obj)

        if not objectsToExport:
            CenLib.PopupError("No mesh objects found in the active collection!")
            return CenLib.Cancelled()
        print(
            f"Exporting {len(objectsToExport)} object(s) from collections '{', '.join(i.name for i in instancesCollections)}'"
        )

    else:
        CenLib.PopupError(f"Invalid export mode: {exportMode}")
        return CenLib.Cancelled()

    deletePrevious = exportMode == "ALL"

    if ExportInstances(absolutePath, levelName, objectsToExport, deletePrevious):
        return CenLib.Finished()
    else:
        return CenLib.Cancelled()


def HasInstancePainter(obj: bpy.types.Object) -> bool:
    return any(
        mod.type == "NODES"
        and mod.node_group
        and mod.node_group.name == "InstancePainter"
        for mod in obj.modifiers
    )


def ExportInstances(
    directoryPath, levelName, objectsToExport, deletePrevious
) -> bool:
    print("\n=====================\nStart of ExportInstances\n")
    startTime = time.time()

    if deletePrevious:
        DeletePreviousJsonFiles(directoryPath)

    instObjList = []
    for obj in objectsToExport:
        if HasInstancePainter(obj):
            instObjList.append(obj)

    if not instObjList:
        CenLib.PopupError("No objects with InstancePainter modifiers found. Aborting")
        return False

    instObjModlistTuple = []

    for instObj in instObjList:
        modList = []
        for mod in instObj.modifiers:
            if CenLib.IsGeonodeModifier(mod):
                if CenLib.GetGeonodeTypeName(mod) == "InstancePainter":
                    modList.append(mod)
        instObjModlistTuple.append((instObj, modList))

    print("The instance objects and their instance types: ")
    for instObj, modlist in instObjModlistTuple:
        print("   " + instObj.name + ": " + ", ".join(mod.name for mod in modlist))

    print("\n\n=====GENERATING INSTANCES...=====")
    for instObj, modlist in instObjModlistTuple:
        objectName = instObj.name
        seed = 0
        for mod in modlist:
            seed += 1
            CenLib.ClearSelection()

            modWasActiveBefore = CenLib.ModifierIsActive(mod)
            if modWasActiveBefore == False:
                print(
                    "Modifier " + mod.name + " was inactive before. Activating it pre-dupe."
                )
                CenLib.MakeModifierActive(mod)

            mod[KEY_EXPORTING_POINTS] = False

            duplicateObject = CenLib.DuplicateObject(instObj)
            dupeMod = CenLib.GetModifier(duplicateObject, mod.name, 0)
            dupeMod[KEY_SEED] = seed
            dupeMod[KEY_EXPORTING_POINTS] = True

            if modWasActiveBefore == False:
                CenLib.MakeModifierInactive(mod)

            region = instObj.name
            instanceType = mod.name
            fileName = f"{levelName}--{region}--{instanceType}.json"
            filePath = os.path.join(directoryPath, fileName)

            CenLib.ConvertToMesh(duplicateObject)

            vertexCoordinates = [v.co.copy() for v in duplicateObject.data.vertices]
            for coord in vertexCoordinates:
                coord += duplicateObject.location

            WriteVertexCoordinatesToJson(vertexCoordinates, filePath)
            CenLib.DeleteObject(duplicateObject)

    endTime = time.time()
    timeElapsed = endTime - startTime
    print(f"---Done! Time taken: {timeElapsed:.2f} seconds.")
    return True




def CreateListOfAllInstanceableObjects():
    instanceableObjects = [
        obj
        for obj in bpy.data.objects
        if any(
            mod.type == "NODES"
            and mod.node_group
            and mod.node_group.name == "InstancePainter"
            for mod in obj.modifiers
        )
    ]
    return instanceableObjects


def WriteVertexCoordinatesToJson(vertexCoordinates, filePath):
    positions = {}
    theArray = []
    vertexExists = False
    for v in vertexCoordinates:
        vertexExists = True
        theArray.append({"x": v.x, "y": v.z, "z": v.y})
    positions["Positions"] = theArray

    if vertexExists:
        with open(filePath, "w") as outputJsonFile:
            json.dump(positions, outputJsonFile, indent=4)


def DeletePreviousJsonFiles(directoryPath):
    for oldFile in os.listdir(directoryPath):
        if oldFile.endswith(".json") or oldFile.endswith(".json.meta"):
            fileToRemove = os.path.join(directoryPath, oldFile)
            if os.path.isfile(fileToRemove):
                os.remove(fileToRemove)


class CENINSTANCER_OT_SetMinimumDensity(bpy.types.Operator):
    bl_idname = "ceninstancer.set_minimum_density"
    bl_label = "Set Minimum Density"
    bl_description = "Set the minimum density for instance painting"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        densityName = context.scene.ceninstancer_density_name
        densityValue = context.scene.ceninstancer_density_value
        SetMinimumDensity(context, densityName, densityValue)
        return CenLib.Finished()


class CENINSTANCER_OT_MakeRoomForSelected(bpy.types.Operator):
    bl_idname = "ceninstancer.make_room_for_selected"
    bl_label = "Make Room For - Selected"
    bl_description = "Make room for selected objects in the scene"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        makesRoom = context.scene.ceninstancer_makes_room
        forValue = context.scene.ceninstancer_for_value
        MakeRoomForSelected(makesRoom, forValue)
        return CenLib.Finished()


class CENINSTANCER_OT_MakeRoomForAll(bpy.types.Operator):
    bl_idname = "ceninstancer.make_room_for_all"
    bl_label = "Make Room For - All"
    bl_description = "Make room for all objects in the scene"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        makesRoom = context.scene.ceninstancer_makes_room
        forValue = context.scene.ceninstancer_for_value
        MakeRoomForAll(makesRoom, forValue)
        return CenLib.Finished()


class CenInstancerPanel(Panel):
    bl_label = "CenInstancer"
    bl_idname = "VIEW3D_PT_Ceninstancer"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Centradigon"

    def draw(self, context: Context):
        layout = self.layout
        colLayout = layout.column(align=False)
        
        # Display selected object
        activeObj = CenLib.GetActiveObject()
        colLayout.label(text=f"Selected: {activeObj.name if activeObj else '<none>'}")
        
        colLayout.separator()
        
        colLayout.prop(context.scene, "output_directory_path")
        colLayout.prop(context.scene, "level_name")

        colLayout.separator()

        colLayout.operator("wm.export_for_selected_objects")
        colLayout.operator("wm.export_for_all_objects")

        colLayout.separator()

        colLayout.operator("wm.share_instances_throughout_collection")

        colLayout.separator()
        colLayout.label(text="Minimum Density Settings:", icon="SETTINGS")
        colLayout.prop(context.scene, "ceninstancer_density_name")
        colLayout.prop(context.scene, "ceninstancer_density_value")
        colLayout.operator("ceninstancer.set_minimum_density", icon="MODIFIER")

        colLayout.separator()
        colLayout.label(text="Plant Domination:", icon="SETTINGS")
        colLayout.prop(context.scene, "ceninstancer_makes_room")
        colLayout.prop(context.scene, "ceninstancer_for_value")
        
        row = colLayout.row(align=True)
        row.operator("ceninstancer.make_room_for_selected", icon="OBJECT_DATA")
        row.operator("ceninstancer.make_room_for_all", icon="WORLD")


class PrintOutputPath(bpy.types.Operator):
    bl_idname = "wm.print_output_path"
    bl_label = "Echo absolute output path"

    def execute(self, context):
        if not context.scene.output_directory_path:
            print("You forgot to set the output path!")
        else:
            print(
                "Absolute output path: "
                + bpy.path.abspath(context.scene.output_directory_path)
            )

        return CenLib.Finished()


class ShareInstanceTypesThroughoutCollection(bpy.types.Operator):
    bl_idname = "wm.share_instances_throughout_collection"
    bl_label = "Share Instances"

    def execute(self, context):
        return ShareInstances()


class ExportForSelectedObjects(bpy.types.Operator):
    bl_idname = "wm.export_for_selected_objects"
    bl_label = "Export Instances: SELECTED"

    def execute(self, context):
        return RunInstancer(context, exportMode="SELECTED")


class ExportForAllObjects(bpy.types.Operator):
    bl_idname = "wm.export_for_all_objects"
    bl_label = "Export instances: ALL"

    def execute(self, context):
        return RunInstancer(context, exportMode="ALL")


def register() -> None:
    bpy.utils.register_class(CenInstancerPanel)
    bpy.utils.register_class(PrintOutputPath)
    bpy.utils.register_class(ExportForSelectedObjects)
    bpy.utils.register_class(ExportForAllObjects)
    bpy.utils.register_class(ShareInstanceTypesThroughoutCollection)
    bpy.utils.register_class(CENINSTANCER_OT_SetMinimumDensity)
    bpy.utils.register_class(CENINSTANCER_OT_MakeRoomForSelected)
    bpy.utils.register_class(CENINSTANCER_OT_MakeRoomForAll)

    bpy.types.Scene.output_directory_path = bpy.props.StringProperty(
        name="Output",
        description="Choose the folder corresponding to the level associated with this .blend file..",
        subtype="FILE_PATH",
    )

    bpy.types.Scene.level_name = bpy.props.StringProperty(
        name="Level", description="Write the name of the level"
    )

    bpy.types.Scene.ceninstancer_density_name = bpy.props.StringProperty(
        name="Density Name",
        description="Name of the density to set",
        default="",
    )

    bpy.types.Scene.ceninstancer_density_value = bpy.props.FloatProperty(
        name="Density Value",
        description="Value for the minimum density",
        default=20,
        min=0.0,
        max=100,
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


def unregister() -> None:
    bpy.utils.unregister_class(CenInstancerPanel)
    bpy.utils.unregister_class(PrintOutputPath)
    bpy.utils.unregister_class(ExportForSelectedObjects)
    bpy.utils.unregister_class(ExportForAllObjects)
    bpy.utils.unregister_class(ShareInstanceTypesThroughoutCollection)
    bpy.utils.unregister_class(CENINSTANCER_OT_SetMinimumDensity)
    bpy.utils.unregister_class(CENINSTANCER_OT_MakeRoomForSelected)
    bpy.utils.unregister_class(CENINSTANCER_OT_MakeRoomForAll)
    
    del bpy.types.Scene.output_directory_path
    del bpy.types.Scene.level_name
    del bpy.types.Scene.ceninstancer_density_name
    del bpy.types.Scene.ceninstancer_density_value
    del bpy.types.Scene.ceninstancer_makes_room
    del bpy.types.Scene.ceninstancer_for_value


def RunFromScript() -> None:
    print("Welcome from the script little cro. How are you, little vro?")
    register()


if __name__ == "__main__":
    RunFromScript()

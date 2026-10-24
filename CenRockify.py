bl_info = {
    "name": "CenRockify",
    "author": "Lrodas",
    "version": (1, 0),
    "blender": (4, 4, 0),
    "location": "View3D > Sidebar > Cen Tab",
    "description": "Duplicate rocks and setup LODs",
    "category": "Cen Tools",
}

import bpy
import CenLib
import os
import time
from bpy.props import StringProperty, PointerProperty, FloatProperty
from bpy.types import PropertyGroup


# ----------------- Properties -----------------

class CENROCKIFY_PG_settings(PropertyGroup):
    export_path: StringProperty(
        name="Output Dir",
        description="Directory to export rocks to",
        subtype="DIR_PATH",
        default="",
    )
    cell_size: FloatProperty(
        name="Cell Size",
        description="Cell size for clustering",
        default=25,
        min=0.0,
    )
    lod0_decimate_ratio: FloatProperty(
        name="LOD0 Decimate Ratio",
        description="Decimate ratio for LOD0",
        default=0.5,
        min=0.0,
        max=1.0,
    )
    lod1_decimate_ratio: FloatProperty(
        name="LOD1 Decimate Ratio",
        description="Decimate ratio for LOD1",
        default=0.1,
        min=0.0,
        max=1.0,
    )


# ----------------- Core Functions -----------------

def IsRockPainterModifier(mod):
    return CenLib.IsGeonodeModifier(mod) and CenLib.GetGeonodeTypeName(mod) == "RockPainter_V2"


def SetupRockModifiersOnMirrorObject(object):
    for modifier in list(object.modifiers):
        if IsRockPainterModifier(modifier):
            CenLib.MakeModifierActive(modifier)
            CenLib.GetGeometryNodeField(modifier, "Rocks Only").value = True
        else:
            object.modifiers.remove(modifier)


def GetRockObjectsInsideCollection(collection):
    objectsWithRocks = []
    for obj in CenLib.GetObjectsInCollection(collection):
        rockPaintersOnObjectFound = 0
        for modifier in obj.modifiers:
            if IsRockPainterModifier(modifier):
                if rockPaintersOnObjectFound > 0:
                    CenLib.DeleteModifier(modifier)
                else:
                    objectsWithRocks.append(obj)
                    CenLib.MakeModifierInactive(modifier)
                    rockPaintersOnObjectFound += 1

    return objectsWithRocks


def GeneratePreview():
    state = CenLib.TransitionToExportableState()

    activeCollection = CenLib.GetActiveCollection()
    if activeCollection is None or activeCollection.name == "Scene Collection":
        CenLib.PopupError("Please select a valid collection")
        return CenLib.Cancelled()

    objectsWithRocks = GetRockObjectsInsideCollection(activeCollection)

    originalModsToReActivate = CenLib.DisableAllActiveModifiers(objectsWithRocks)

    previewCollectionName = f"RockPreviews-Of-{activeCollection.name}-(Mirrors_Geometry)"
    previewCollection = CenLib.GetOrCreateCollection(previewCollectionName)
    allPreviewsCollection = CenLib.GetOrCreateCollection("Rock Mirror Previews")
    CenLib.MakeCollectionChildOf(previewCollection, allPreviewsCollection)
    oldPreviews = CenLib.GetObjectsInCollection(previewCollection)
    for oldPreview in oldPreviews:
        CenLib.DeleteObject(oldPreview)

    rockIndex = 0
    for obj in objectsWithRocks:
        rockIndex += 1
        dupe = CenLib.DuplicateObject_LinkData(obj)
        dupe.name = f"RockPreview-Of-{activeCollection.name}_Part{rockIndex}"
        CenLib.MoveToCollection(dupe, previewCollection)
        SetupRockModifiersOnMirrorObject(dupe)

    CenLib.EnableListOfModifiers(originalModsToReActivate)

    elapsed = CenLib.RestoreStateAfterExport(state)
    CenLib.PopupPrint(f"Generated the rock previews in {elapsed:.3f} seconds!")
    return CenLib.Finished()


def ExportRocks(directory, cellSize, lod0DecimateRatio, lod1DecimateRatio, context):
    state = CenLib.TransitionToExportableState()
    startTime = time.time()

    activeCollection = CenLib.GetActiveCollection()
    if activeCollection is None or activeCollection.name == "Scene Collection":
        CenLib.PopupError("Please select a valid collection")
        return CenLib.Cancelled()

    if "Mirror" in activeCollection.name:
        CenLib.PopupError(
            f"You probably selected the wrong collection, as it has Mirrors in the name ({activeCollection.name})")
        return CenLib.Cancelled()

    objectsWithRocks = GetRockObjectsInsideCollection(activeCollection)
    workshopCollection = CenLib.CreateCollection("TEMPORARY_WORKSHOP_COLLECTION")

    originalModsToReActivate = CenLib.DisableAllActiveModifiers(objectsWithRocks)
    print(f"Deactivated all original modifiers... ({(time.time() - startTime):.3f} seconds...)")

    rockIndex = 0
    for obj in objectsWithRocks:
        rockIndex += 1
        dupe = CenLib.DuplicateObject(obj)
        dupe.name = f"RockField-Of-{activeCollection.name}_Part{rockIndex}"
        CenLib.MoveToCollection(dupe, workshopCollection)
        SetupRockModifiersOnMirrorObject(dupe)
        CenLib.ConvertToMesh(dupe)

    print(f"Duplicated objects into the workshop collection... ({(time.time() - startTime):.3f} seconds...)")

    joined = CenLib.JoinObjects(CenLib.GetObjectsInCollection(workshopCollection))
    print(f"Joined the objects...({(time.time() - startTime):.3f} seconds...)")
    # Workshop is now filled with big fields of rocks. Let's separate, then cluster
    CenLib.SeparateLoose(joined)
    print(f"Separated loose... ({(time.time() - startTime):.3f} seconds...)")
    # for bigRockField in CenLib.GetObjectsInCollection(workshopCollection):
    #     CenLib.SeparateLoose(bigRockField)  # They stay in the same collection so we don't need to explicitly collect

    # Time to cluster! 
    CenLib.ClusterObjectsInInputCollection(workshopCollection, cellSize)
    print(f"Generated the clusters... ({(time.time() - startTime):.3f} seconds...)")

    # Creating the LODs 
    clusterIndex = 0;
    clusters = CenLib.GetObjectsInCollection(workshopCollection)
    for lod0 in clusters:
        clusterIndex += 1
        totalTimeSpent = time.time() - startTime
        print(
            f"Processing cluster {clusterIndex} of {len(clusters)}... (Total time spent: {totalTimeSpent:.3f} seconds)")
        lod0.name = f"RockCluster_{activeCollection.name}_Part{clusterIndex}-V_LOD0"

        CenLib.ApplyTransforms(lod0)
        CenLib.SetOriginToWorldOrigin(lod0)

        lod1 = CenLib.DuplicateObject(lod0, False)
        lod1.name = f"RockCluster_{activeCollection.name}_Part{clusterIndex}-V_LOD1"

        lod0Decimate = CenLib.AddModifier(lod0, "Lod0Decimate", 'DECIMATE')
        lod1Decimate = CenLib.AddModifier(lod1, "Lod1Decimate", 'DECIMATE')
        CenLib.SetModifierProperty(lod0Decimate, 'ratio', lod0DecimateRatio)
        CenLib.SetModifierProperty(lod1Decimate, 'ratio', lod1DecimateRatio)

        filePath_Lod0 = os.path.join(directory, f"{lod0.name}.fbx")
        filePath_Lod1 = os.path.join(directory, f"{lod1.name}.fbx")

        CenLib.ExportFbx(filePath_Lod0, lod0)
        CenLib.ExportFbx(filePath_Lod1, lod1)
        CenLib.DeleteObject(lod0)
        CenLib.DeleteObject(lod1)

    CenLib.DeleteCollection(workshopCollection)

    print(f"Processed all clusters! Making original modifiers active now ({(time.time() - startTime):.3f} seconds...)")
    for mod in originalModsToReActivate:
        CenLib.MakeModifierActive(mod)
    print(f"Made all original modifiers active! ({(time.time() - startTime):.3f} seconds...)")

    elapsed = CenLib.RestoreStateAfterExport(state)

    CenLib.PopupPrint(f"Exported the rock previews in {elapsed:.3f} seconds!")
    return CenLib.Finished()


def SpreadRockPainter(replace_existing=True):
    state = CenLib.TransitionToExportableState()
    activeCollection = CenLib.GetActiveCollection()
    selectedObjects = CenLib.GetSelectedObjects()
    activeObject = CenLib.GetActiveObject()

    if activeObject is None and (selectedObjects is None or len(selectedObjects) == 0):
        CenLib.PopupError("Error: No object selected")
        return CenLib.Cancelled()

    if activeObject is not None:
        selectedObj = activeObject
    else:
        selectedObj = selectedObjects[0]

    if not CenLib.IsInCollection(selectedObj, activeCollection):
        CenLib.PopupError(
            f"Error: The selected object {selectedObj.name} is not part of collection {activeCollection.name}")
        return CenLib.Cancelled()

    hasRockPainter = False
    sourceModifier = None
    for modifier in selectedObj.modifiers:
        if IsRockPainterModifier(modifier):
            hasRockPainter = True
            sourceModifier = modifier
            break

    if not hasRockPainter:
        CenLib.PopupError("Error: Selected object does not have RockPainter_V2 modifier")
        return CenLib.Cancelled()

    socketValuesToCopy = [
        "Overall Scale",
        "Min Scale Multiplier",
        "Max Scale Multiplier",
        "Rock Collection",
        "Distance Min",
        "Density Max",
        "Seed",
        "Shift Rocks Up"
    ]

    sourceNodeGroup = sourceModifier.node_group
    objectsModified = 0
    for obj in CenLib.GetObjectsInCollection(activeCollection):
        if obj == selectedObj:
            continue

        if replace_existing:
            # Removing old
            for modifier in list(obj.modifiers):
                if IsRockPainterModifier(modifier):
                    obj.modifiers.remove(modifier)
        else:
            # Skipping if it already had a rockpainter modifier
            alreadyHas = False
            for modifier in obj.modifiers:
                if IsRockPainterModifier(modifier):
                    alreadyHas = True
                    break
            if alreadyHas:
                continue

        newModifier = CenLib.AddModifier(obj, "RockPainter_V2", "NODES")
        newModifier.node_group = sourceNodeGroup
        for socketValueToCopy in socketValuesToCopy:
            CenLib.GetGeometryNodeField(newModifier, socketValueToCopy).value = CenLib.GetGeometryNodeField(
                sourceModifier, socketValueToCopy).value

        CenLib.MakeModifierInactive(newModifier)
        objectsModified += 1

        CenLib.AddVertexGroupIfNotPresent(obj, "BigRocks")

    if objectsModified == 0 and replace_existing:
        print(
            "WARNING: Objects modified was 0. To use this modifier, do the following: Select the object whose RockPainter_V2 you want to spread to objects in the SELECTED TARGET collection"
        )
    print(
        f"Spread RockPainter_V2 to {objectsModified} objects in collection '{activeCollection.name}'"
    )

    elapsed = CenLib.RestoreStateAfterExport(state)
    CenLib.PopupPrint(f"Completed the spread of RockPainter in {elapsed:.3f} seconds!")
    return CenLib.Finished()


def ResetRocksVertexGroups():
    selected = CenLib.GetSelectedObjects()
    count = 0
    for obj in selected:
        CenLib.RemoveVertexGroup(obj, "BigRocks")
        CenLib.AddVertexGroupIfNotPresent(obj, "BigRocks")
        count += 1

    CenLib.PopupPrint(f"Reset the BigRocks vertex group on {count} objects")
    return CenLib.Finished()


# ----------------- Operators & Panel -----------------


class ROCKPAINTER_LODDER_OT_GeneratePreview(bpy.types.Operator):
    bl_idname = "object.rockpainter_generate_preview"
    bl_label = "Generate Previews for Active Collection"
    bl_description = "Generate a preview of the rocks"

    def execute(self, context):
        GeneratePreview()
        return {"FINISHED"}


class ROCKPAINTER_LODDER_OT_ExportRocks(bpy.types.Operator):
    bl_idname = "object.rockpainter_export_rocks"
    bl_label = "Export Rocks"
    bl_description = "Export the rocks to the specified path"

    def execute(self, context):
        path = context.scene.cenrockify.export_path
        cellSize = context.scene.cenrockify.cell_size
        lod0DecimateRatio = context.scene.cenrockify.lod0_decimate_ratio
        lod1DecimateRatio = context.scene.cenrockify.lod1_decimate_ratio
        ExportRocks(path, cellSize, lod0DecimateRatio, lod1DecimateRatio, context)
        return {"FINISHED"}


class ROCKPAINTER_LODDER_OT_Spread(bpy.types.Operator):
    bl_idname = "object.rockpainter_spread"
    bl_label = "Spread RockPainter"
    bl_description = "Spread RockPainter_V2 from selected object to all others in collection (replaces existing)"

    def execute(self, context):
        SpreadRockPainter(replace_existing=True)
        return {"FINISHED"}


class ROCKPAINTER_LODDER_OT_Merge(bpy.types.Operator):
    bl_idname = "object.rockpainter_merge"
    bl_label = "Merge RockPainter"
    bl_description = (
        "Add RockPainter_V2 to objects that don't have it (keeps existing ones)"
    )

    def execute(self, context):
        SpreadRockPainter(replace_existing=False)
        return {"FINISHED"}


class ROCKPAINTER_LODDER_OT_ResetVertexGroups(bpy.types.Operator):
    bl_idname = "object.rockpainter_reset_vertex_groups"
    bl_label = "Reset Rocks Vertex Groups"
    bl_description = "Reset BigRocks vertex groups for selected objects"

    def execute(self, context):
        ResetRocksVertexGroups()
        return {"FINISHED"}


class ROCKPAINTER_LODDER_PT_Panel(bpy.types.Panel):
    bl_label = "CenRockify"
    bl_idname = "VIEW3D_PT_rockpainter_lodder"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Centradigon"

    def draw(self, context):
        layout = self.layout
        settings = context.scene.cenrockify

        # Display active collection and selected object count in a box
        active_layer = context.view_layer.active_layer_collection
        box = layout.box()
        if active_layer:
            col_name = active_layer.collection.name

            # Count selected mesh objects
            selected_objects = CenLib.GetSelectedObjects()
            mesh_selected = [obj for obj in selected_objects if obj.type == 'MESH']

            box.label(
                text=f"Collection: {col_name}", icon="OUTLINER_COLLECTION"
            )
            box.label(text=f"Selected Objects: {len(mesh_selected)}", icon="SELECT_SET")
        else:
            box.label(text="Collection: <none>", icon="OUTLINER_COLLECTION")
            box.label(text="Selected Objects: 0", icon="SELECT_SET")

        layout.prop(settings, "export_path")
        layout.operator("object.rockpainter_generate_preview", text="Generate Preview")
        layout.prop(settings, "cell_size")
        layout.prop(settings, "lod0_decimate_ratio")
        layout.prop(settings, "lod1_decimate_ratio")
        layout.separator()

        layout.operator("object.rockpainter_export_rocks", text="Export Rocks")
        layout.separator()
        layout.operator(
            "object.rockpainter_spread", text="Spread RockPainter (Replace Existing)"
        )
        layout.operator(
            "object.rockpainter_merge", text="Spread RockPainter (Keep Existing)"
        )
        layout.separator()
        layout.operator("object.rockpainter_reset_vertex_groups", text="Reset Rocks Vertex Groups")


# ----------------- Registration -----------------

classes = [
    CENROCKIFY_PG_settings,
    ROCKPAINTER_LODDER_OT_GeneratePreview,
    ROCKPAINTER_LODDER_OT_ExportRocks,
    ROCKPAINTER_LODDER_OT_Spread,
    ROCKPAINTER_LODDER_OT_Merge,
    ROCKPAINTER_LODDER_OT_ResetVertexGroups,
    ROCKPAINTER_LODDER_PT_Panel,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.cenrockify = PointerProperty(type=CENROCKIFY_PG_settings)


def unregister():
    del bpy.types.Scene.cenrockify
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()

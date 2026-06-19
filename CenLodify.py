bl_info = {
    "name": "CenLodify",
    "author": "Lrodas",
    "version": (1, 0, 0),
    "blender": (4, 0, 0),
    "location": "3D Viewport > Sidebar (N) > CenLodify",
    "description": "Convert -Parts collections to -CenLods, or update existing -CenLods",
    "category": "Object",
}

import os
import time

import bpy
import CenLib
from bpy.props import BoolProperty, PointerProperty, StringProperty
from bpy.types import PropertyGroup

def BringIntoParts():
    selected = CenLib.GetSelectedObjects()
    if not selected:
        CenLib.PopupError("No objects selected")
        return CenLib.Cancelled()
    
    active = CenLib.GetActiveObject()
    if not active:
        CenLib.PopupError("No active object")
        return CenLib.Cancelled()
    
    base_name = active.name
    suffixes_to_remove = ["-V", "-V_LOD0", "-V_LOD1", "_V", "_V_LOD0", "_V_LOD1"]
    for suffix in suffixes_to_remove:
        if base_name.endswith(suffix):
            base_name = base_name.removesuffix(suffix)
            break
    
    parts_collection_name = base_name + "-Parts"
    
    existing = CenLib.GetCollectionByName(parts_collection_name)
    if existing:
        CenLib.PopupError(f"Collection {parts_collection_name} already exists")
        return CenLib.Cancelled()
    
    parts_collection = CenLib.CreateCollection(parts_collection_name)
    
    for obj in selected:
        CenLib.MoveToCollection(obj, parts_collection)
    
    CenLib.SetCollectionToActive(parts_collection)
    CenLib.PopupPrint(f"Moved {len(selected)} objects into {parts_collection_name}")
    return CenLib.Finished()

def ConvertPartCollectionToLodCollection():
    partCollection = CenLib.GetActiveCollection()
    if not partCollection or partCollection.name.endswith("-Parts") == False:
        CenLib.PopupError("Active collection did not end with -Parts")
        return CenLib.Cancelled()

    CenLib.MakeCollectionVisible(partCollection)
    CenLib.ClearSelection() 

    lodCollectionName = partCollection.name.removesuffix("-Parts") + "-CenLods"

    existingLodCollection = CenLib.GetCollectionByName(lodCollectionName)
    if existingLodCollection:
        existingLodCollection.name = "OLDVERSION_" + existingLodCollection.name
        existingLodObjects = CenLib.GetObjectsInCollection(existingLodCollection)
        for existingLod in existingLodObjects:
            existingLod.name = "OLDVERSION_" + existingLod.name

        CenLib.ExcludeCollection(existingLodCollection)

    lodCollection = CenLib.CreateCollection(lodCollectionName)
    originalPartObjects = CenLib.GetObjectsInCollection(partCollection)
    for original in originalPartObjects:
        dupe = CenLib.DuplicateObject(original)
        CenLib.ApplyAllModifiersOnObject(dupe)
        CenLib.MoveToCollection(dupe, lodCollection)

    joined = CenLib.JoinObjects(CenLib.GetObjectsInCollection(lodCollection))
    if joined == None:
        CenLib.PopupError("Attempted to join 0 objects.")
    CenLib.SetOriginToWorldOrigin(joined)
    CenLib.ApplyScale(joined)
    CenLib.ApplyRotation(joined)

    joined.name = lodCollectionName.removesuffix("-CenLods") + "-V_LOD0"
    lod0 = joined
    lod1 = CreateLod1Object(lod0)

    CenLib.MakeObjectHidden(lod0)

    CenLib.ExcludeCollection(partCollection)

    return CenLib.Finished()

def UpdateLods():
    if CenLib.IsInLocalView():
        CenLib.PopupError("Exit local view first")
        return CenLib.Cancelled()
    lodCollection = CenLib.GetActiveCollection()
    if not lodCollection or not lodCollection.name.endswith("-CenLods"):
        CenLib.PopupError("Active collection didn't end with -CenLods")
        return CenLib.Cancelled()

    CenLib.MakeCollectionVisible(lodCollection)
    lod1Object = None
    lod0Object = None
    oldRatio = 0.5
    for obj in CenLib.GetObjectsInCollection(lodCollection):
        if obj.name.endswith("-V_LOD1"):
            lod1Object = obj
        elif obj.name.endswith("-V_LOD0"):
            lod0Object = obj

    if not lod0Object:
        CenLib.PopupError("Failed to find the lod0 object in " + lodCollection.name)
        return CenLib.Cancelled()

    if lod1Object:
        oldLod1Decimate = CenLib.GetModifier(lod1Object, "Lod1Decimate", 0)
        if oldLod1Decimate:
            oldRatio = CenLib.GetModifierValue(oldLod1Decimate, "ratio")
        CenLib.DeleteObject(lod1Object)

    newLod1 = CreateLod1Object(lod0Object)
    newLod1Decimate = CenLib.GetModifier(newLod1, "Lod1Decimate")
    CenLib.SetModifierProperty(newLod1Decimate, "ratio", oldRatio)

    return CenLib.Finished()

def MakeLod1Collection():
    start = time.time()
    originalCollection = CenLib.GetActiveCollection()
    if originalCollection.name.endswith("_LOD0") == False:
        CenLib.PopupError(
            f"Selected collection {originalCollection.name} did not end ith _LOD0! Aborting..."
        )
        return CenLib.Cancelled()

    originalObjects = CenLib.GetObjectsInCollection(originalCollection)
    for og in originalObjects:
        if og.name.endswith("_LOD0") == False:
            CenLib.PopupError(
                f"Object from original collection {og.name} did not end with _LOD0! Aborting..."
            )
            return CenLib.Cancelled()

    dupeName = originalCollection.name.replace("_LOD0", "_LOD1")
    previousLod1Collection = CenLib.GetCollectionByName(dupeName)
    if previousLod1Collection is not None:
        CenLib.DeleteCollection(previousLod1Collection)

    dupedCollection = CenLib.DuplicateCollection(originalCollection, dupeName)
    toParentTo = CenLib.GetParentOfCollection(originalCollection)
    CenLib.MakeCollectionChildOf(dupedCollection, toParentTo)

    duplicatedObjects = CenLib.GetObjectsInCollection(dupedCollection)
    for dupe in duplicatedObjects:
        decimateMod = CenLib.AddModifier(dupe, "Lod1Decimate", "DECIMATE")
        CenLib.SetModifierProperty(decimateMod, "ratio", 0.3)
        dupe.name = dupe.name.split("_LOD0")[0] + "_LOD1"
        CenLib.SelectObject(
            dupe
        )

    end = time.time()
    CenLib.PopupPrint(f"Completed Make Lod1 Collection! It took {end - start} seconds!")
    return CenLib.Finished()

def NameLod0sInCollection():
    targetCollection = CenLib.GetActiveCollection()
    if targetCollection.name.endswith("_LOD0") == False:
        CenLib.PopupError(
            f"Selected collection {targetCollection.name} doesn't end with _LOD0! Aborting..."
        )
        return CenLib.Cancelled()

    objsToBeNamed = CenLib.GetObjectsInCollection(targetCollection)
    nameTemplate = targetCollection.name.split("_LOD")[0] + "["
    objectIndex = 1
    for obj in objsToBeNamed:
        obj.name = f"{nameTemplate}{objectIndex}]-V_LOD0"
        objectIndex += 1

    CenLib.PopupPrint(f"Completed Name Lod1s In Collection!")
    return CenLib.Finished()

def CreateLod1Object(lod0: bpy.types.Object)-> bpy.types.Object:
    lod1 = CenLib.DuplicateObject(lod0)
    CenLib.ConvertToMesh(lod1)
    decimate = CenLib.AddModifier(lod1, "Lod1Decimate", "DECIMATE")
    CenLib.SetModifierProperty(decimate, "decimate_type", "COLLAPSE")
    CenLib.SetModifierProperty(decimate, "ratio", 0.5)
    lod1.name = lod0.name.removesuffix("_LOD0") + "_LOD1"
    return lod1

class CENLODIFY_OT_BringIntoParts(bpy.types.Operator):
    bl_idname = "cenlodify.bring_into_parts"
    bl_label = "Bring into Parts"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        BringIntoParts()
        return CenLib.Finished()

class CENLODIFY_OT_ConvertParts(bpy.types.Operator):
    bl_idname = "cenlodify.convert_parts"
    bl_label = "Convert -Parts to -CenLods"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        ConvertPartCollectionToLodCollection()
        return CenLib.Finished()

class CENLODIFY_OT_UpdateLods(bpy.types.Operator):
    bl_idname = "cenlodify.update_lods"
    bl_label = "Update -CenLods"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        UpdateLods()
        return CenLib.Finished()

class CENLODIFY_OT_MakeLod1(bpy.types.Operator):
    bl_idname = "cenlodify.make_lod1"
    bl_label = "Make LOD1 Collection"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        MakeLod1Collection()
        return CenLib.Finished()

class CENLODIFY_OT_NameLod0s(bpy.types.Operator):
    bl_idname = "cenlodify.name_lod0s"
    bl_label = "Name LOD0s in collection"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        NameLod0sInCollection()
        return CenLib.Finished()

class CENLODIFY_PT_panel(bpy.types.Panel):
    bl_label = "CenLodify"
    bl_idname = "CENLODIFY_PT_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Centradigon"

    def draw(self, context):
        layout = self.layout
        col = (
            context.view_layer.active_layer_collection.collection
            if context.view_layer.active_layer_collection
            else None
        )
        layout.label(text=f"Active: {col.name if col else '<none>'}")
        layout.separator()

        layout.operator("cenlodify.bring_into_parts", icon="IMPORT")
        layout.operator("cenlodify.convert_parts", icon="MOD_BOOLEAN")
        layout.operator("cenlodify.update_lods", icon="FILE_REFRESH")
        layout.separator()
        layout.operator("cenlodify.name_lod0s", icon="OUTLINER_OB_FONT")
        layout.operator("cenlodify.make_lod1", icon="ADD")

classes = (
    CENLODIFY_OT_BringIntoParts,
    CENLODIFY_OT_ConvertParts,
    CENLODIFY_OT_UpdateLods,
    CENLODIFY_OT_MakeLod1,
    CENLODIFY_OT_NameLod0s,
    CENLODIFY_PT_panel,
)

def register():
    for c in classes:
        bpy.utils.register_class(c)

def unregister():
    for c in reversed(classes):
        bpy.utils.unregister_class(c)

if __name__ == "__main__":
    register()
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

# ---------- helpers ----------


def findLayerCollection(layer, targetCollection):
    if layer.collection == targetCollection:
        return layer
    for child in layer.children:
        hit = findLayerCollection(child, targetCollection)
        if hit:
            return hit


def ApplyModsOnObject(obj):
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    if bpy.context.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.convert(target="MESH")
    obj.select_set(False)
    bpy.context.view_layer.objects.active = None


def JoinObjectsTogether(objects):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objects:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.object.join()
    return bpy.context.view_layer.objects.active


def SetOriginToWorldOrigin(targetObject):
    if bpy.context.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    cur = bpy.context.scene.cursor
    prev = cur.location.copy()
    cur.location = (0, 0, 0)
    bpy.context.view_layer.objects.active = targetObject
    targetObject.select_set(True)
    bpy.ops.object.origin_set(type="ORIGIN_CURSOR")
    cur.location = prev
    targetObject.select_set(False)
    bpy.context.view_layer.objects.active = None


def ApplyScaleAndRotation(targetObject):
    bpy.context.view_layer.objects.active = targetObject
    targetObject.select_set(True)

    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

    targetObject.select_set(False)
    bpy.context.view_layer.objects.active = None


def LinkIntoSameCollection(victim, invader):
    for col in victim.users_collection:
        col.objects.link(invader)


def CreateLod1Object(lod0Object):
    lod1 = lod0Object.copy()
    if lod0Object.data:
        lod1.data = lod0Object.data.copy()
    LinkIntoSameCollection(lod0Object, lod1)
    dec = lod1.modifiers.new(name="Lod1Decimate", type="DECIMATE")
    dec.decimate_type = "COLLAPSE"
    dec.ratio = 0.5
    lod1.name = lod0Object.name.removesuffix("_LOD0") + "_LOD1"
    return lod1


def _iter_objects_recursive(col, seen_ptrs):
    # Yield all unique objects in this collection and its children
    for obj in col.objects:
        pid = obj.as_pointer()
        if pid not in seen_ptrs:
            seen_ptrs.add(pid)
            yield obj
    for child in col.children:
        yield from _iter_objects_recursive(child, seen_ptrs)


def ConvertPartCollectionToLodCollection():
    partsCollection = bpy.context.view_layer.active_layer_collection.collection
    if not partsCollection.name.endswith("-Parts"):
        CenLib.PopupError(
            f'The selected collection "{partsCollection.name}" does not end with "-Parts"'
        )
        return {"CANCELLED"}

    bpy.ops.object.select_all(action="DESELECT")

    # New collection name: "XXX-Parts" -> "XXX-V"
    lodCollectionName = partsCollection.name.removesuffix("-Parts") + "-CenLods"

    # if the lodcollection already existed, create a new collection instead, to prevent overwriting the old on accident
    existingLodCollection = bpy.data.collections.get(lodCollectionName)
    if existingLodCollection:
        lodCollectionName = (
            lodCollectionName.removesuffix("-CenLods") + "_NEW_FROM_PARTS-CenLods"
        )

    lodCollection = bpy.data.collections.new(lodCollectionName)
    bpy.context.scene.collection.children.link(lodCollection)

    duped = []
    seen_ptrs = set()
    partsCollectionObjects = list(_iter_objects_recursive(partsCollection, seen_ptrs))
    for obj in partsCollectionObjects:
        d = obj.copy()
        if obj.data:
            d.data = obj.data.copy()
        lodCollection.objects.link(d)
        ApplyModsOnObject(d)
        duped.append(d)

    if not duped:
        CenLib.PopupError("No objects found to convert in the -Parts collection.")
        return {"CANCELLED"}

    joined = JoinObjectsTogether(duped)
    SetOriginToWorldOrigin(joined)
    ApplyScaleAndRotation(joined)

    joined.name = lodCollectionName.removesuffix("-CenLods") + "-V_LOD0"
    lod0 = joined
    lod1 = CreateLod1Object(lod0)

    # Hide the hi-poly (LOD0) by default
    lod0.hide_set(True)

    # Hide the original parts collection in the active view layer
    parts_layer = findLayerCollection(
        bpy.context.view_layer.layer_collection, partsCollection
    )
    if parts_layer:
        parts_layer.exclude = True

    return {"FINISHED"}


def UpdateLods():
    lodCollection = bpy.context.view_layer.active_layer_collection.collection
    if not lodCollection.name.endswith("-CenLods"):
        CenLib.PopupError(
            f'The selected collection "{lodCollection.name}" does not end with "-CenLods"'
        )
        return {"CANCELLED"}

    lod1 = next((o for o in lodCollection.objects if o.name.endswith("_LOD1")), None)
    if lod1 is None:
        CenLib.PopupError(
            f'Failed to find an object ending with "_LOD1" in "{lodCollection.name}"'
        )
        return {"CANCELLED"}

    oldDecimate = lod1.modifiers.get("Lod1Decimate")
    if not oldDecimate or oldDecimate.type != "DECIMATE":
        CenLib.PopupError(f'Could not find "Lod1Decimate" (DECIMATE) on "{lod1.name}"')
        return {"CANCELLED"}

    old_ratio = oldDecimate.ratio

    # Remove old LOD1
    bpy.data.objects.remove(lod1, do_unlink=True)

    lod0 = next((o for o in lodCollection.objects if o.name.endswith("_LOD0")), None)
    if lod0 is None:
        CenLib.PopupError(
            f'Failed to find an object ending with "_LOD0" in "{lodCollection.name}"'
        )
        return {"CANCELLED"}

    newLod1 = CreateLod1Object(lod0)
    newDec = newLod1.modifiers.get("Lod1Decimate")
    newDec.ratio = old_ratio

    lod0.hide_set(True)
    return {"FINISHED"}


def MakeLod1Collection():
    start = time.time()
    originalCollection = CenLib.GetActiveCollection()
    if originalCollection.name.endswith("_LOD0") == False:
        CenLib.PopupError(
            f"Selected collection {originalCollection.name} did not end ith _LOD0! Aborting..."
        )
        return {"CANCELLED"}

    originalObjects = CenLib.GetObjectsInCollection(originalCollection)
    for og in originalObjects:
        if og.name.endswith("_LOD0") == False:
            CenLib.PopupError(
                f"Object from original collection {og.name} did not end with _LOD0! Aborting..."
            )
            return {"CANCELLED"}

    dupeName = originalCollection.name.replace("_LOD0", "_LOD1")
    dupedCollection = CenLib.DuplicateCollection(originalCollection, dupeName)

    duplicatedObjects = CenLib.GetObjectsInCollection(dupedCollection)
    for dupe in duplicatedObjects:
        decimateMod = CenLib.AddModifier(dupe, "Lod1Decimate", "DECIMATE")
        CenLib.SetModifierProperty(dupe, "Lod1Decimate", 0, "ratio", 0.3)
        dupe.name = dupe.name.split("_LOD0")[0] + "_LOD1"
        CenLib.SelectObject(
            dupe
        )  # Selecting, so that after running it's easy to set the decimate value

    end = time.time()
    CenLib.PopupPrint(f"Completed Make Lod1 Collection! It took {end - start} seconds!")
    return {"FINISHED"}


def NameLod0sInCollection():
    targetCollection = CenLib.GetActiveCollection()
    if targetCollection.name.endswith("_LOD0") == False:
        CenLib.PopupError(
            f"Selected collection {targetCollection.name} doesn't end with _LOD0! Aborting..."
        )
        return {"CANCELLED"}

    objsToBeNamed = CenLib.GetObjectsInCollection(targetCollection)
    nameTemplate = targetCollection.split("_LOD")[0] + "["
    objectIndex = 1
    for obj in objsToBeNamed:
        obj.name = f"{nameTemplate}{objectIndex}]-V_LOD0"
        objectIndex += 1

    CenLib.PopupPrint(f"Completed Name Lod1s In Collection!")
    return {"FINISHED"}


# ---------- UI ----------
class CENLODIFY_OT_MakeLod1(bpy.types.Operator):
    bl_idname = "cenlodify.make_lod1"
    bl_label = "Make LOD1 Collection"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        MakeLod1Collection()
        return {"FINISHED"}


class CENLODIFY_OT_NameLod0s(bpy.types.Operator):
    bl_idname = "cenlodify.name_lod0s"
    bl_label = "Name LOD0s in collection"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        NameLod0sInCollection()
        return {"FINISHED"}


class CENLODIFY_OT_process(bpy.types.Operator):
    bl_idname = "cenlodify.process"
    bl_label = "Convert / Update LODs"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        col = context.view_layer.active_layer_collection.collection
        name = col.name if col else "<none>"
        if not col:
            CenLib.PopupError("No active collection selected.")
            return {"CANCELLED"}

        if name.endswith("-Parts"):
            return ConvertPartCollectionToLodCollection()
        elif name.endswith("-CenLods"):
            return UpdateLods()
        else:
            CenLib.PopupError('Active collection must end with "-Parts" or "-CenLods".')
            return {"CANCELLED"}


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

        layout.operator("cenlodify.process", icon="MOD_DECIM")
        layout.operator("cenlodify.name_lod0s", icon="OUTLINER_OB_FONT")
        layout.operator("cenlodify.make_lod1", icon="ADD")


# ---------- register ----------

classes = (
    CENLODIFY_OT_process,
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

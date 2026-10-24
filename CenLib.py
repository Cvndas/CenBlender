bl_info = {
    "name": "CenLib",
    "author": "Lrodas",
    "version": (1, 0),
    "blender": (4, 0, 0),
    "location": "Global",
    "description": "Utility library for Blender addons",
    "category": "Development",
}

import os
from typing import List, Optional
import mathutils
import math
from mathutils import Vector, Euler

import bpy
import time


def Cancelled():
    return {"CANCELLED"}


def Finished():
    return {"FINISHED"}


class UserState:
    def __init__(self, previouslyActive, wasInEditMode, wasInLocalView, previouslySelected):
        self.previouslyActive = previouslyActive
        self.previouslySelected = previouslySelected
        self.wasInEditMode = wasInEditMode
        self.wasInLocalView = wasInLocalView
        self.startTime = time.time()


def TransitionToExportableState():
    state = UserState(GetActiveObject(), IsInEditMode(), IsInLocalView(),
                      GetSelectedObjects())
    ExitLocalView()
    EnterObjectMode()
    return state


def RestoreStateAfterExport(state):
    for sel in state.previouslySelected:
        SelectObject(sel)

    if state.previouslyActive:
        SelectObject(state.previouslyActive)
    if state.wasInLocalView:
        EnterLocalView()
    if state.wasInEditMode:
        EnterEditMode()

    return time.time() - state.startTime


def GetObjectPosition(obj: bpy.types.Object) -> mathutils.Vector:
    return obj.matrix_world.translation


def GetAllObjects() -> List[bpy.types.Object]:
    return list(bpy.data.objects)


def GetModifierOwner(mod: bpy.types.Modifier) -> bpy.types.Object:
    return mod.id_data


def GetVertexCoordinatesInWorldSpace(obj: bpy.types.Object) -> List[Vector]:
    return [v.co + obj.location for v in obj.data.vertices]


def GetVertexGroupNames(obj: bpy.types.Object):
    allNames = []
    for vertexGroup in obj.vertex_groups:
        allNames.append(vertexGroup.name)
    return allNames


def VertexGroupHasWeight(obj: bpy.types.Object, groupName: str) -> bool:
    group = GetVertexGroup(obj, groupName)
    if group is None:
        return False

    for vertex in obj.data.vertices:
        for assignment in vertex.groups:
            if assignment.group == group.index and assignment.weight > 0.0:
                return True
    return False


def GetVertexGroup(obj: bpy.types.Object, groupName: str):
    return obj.vertex_groups.get(groupName)


def RemoveVertexGroup(obj: bpy.types.Object, groupName: str) -> None:
    group = obj.vertex_groups.get(groupName)
    if group is not None:
        obj.vertex_groups.remove(group)


def AddVertexGroupIfNotPresent(obj: bpy.types.Object, groupName: str) -> None:
    if groupName not in obj.vertex_groups:
        obj.vertex_groups.new(name=groupName)


def DisableAllActiveModifiers(listOfObjects: List[bpy.types.Object]) -> List[bpy.types.Modifier]:
    previouslyActive = []
    for obj in listOfObjects:
        for mod in GetModifiers(obj):
            if ModifierIsActive(mod):
                previouslyActive.append(mod)
                MakeModifierInactive(mod)
                
    return previouslyActive
        
def EnableListOfModifiers(listOfModifiers: List[bpy.types.Object]) -> None:
    for mod in listOfModifiers:
        MakeModifierActive(mod)
    


def GetAllActiveModifiers(targetObject: bpy.types.Object) -> List[bpy.types.Modifier]:
    """Returns a list of all active (viewport-visible) modifiers on the given object."""
    activeModifiers = []

    if not targetObject:
        return activeModifiers

    for mod in targetObject.modifiers:
        if ModifierIsActive(mod):
            activeModifiers.append(mod)

    return activeModifiers


def GetParentCollection(collection: bpy.types.Collection) -> Optional[bpy.types.Collection]:
    """
    Get the immediate parent collection of a given collection.

    Args:
        collection: The collection to find the parent of

    Returns:
        Optional[bpy.types.Collection]: The parent collection if found, None otherwise
    """
    if not collection:
        PopupError("No collection provided")
        return None

    # Check if collection is directly in the scene root
    if collection.name in bpy.context.scene.collection.children:
        return bpy.context.scene.collection

    # Search through all collections to find which one has this as a child
    for parent in bpy.data.collections:
        if collection.name in parent.children:
            return parent

    return None


def GetDirectChildCollections(parentCollection: bpy.types.Collection) -> List[bpy.types.Collection]:
    """
    Get the direct (immediate) child collections of a given collection.
    Does not recurse into grandchildren.

    Args:
        parentCollection: The collection whose direct children to retrieve

    Returns:
        List[bpy.types.Collection]: The direct child collections, or [] if none/invalid
    """
    if not parentCollection:
        return []

    return list(parentCollection.children)


def GetAllChildCollections(parentCollection: bpy.types.Collection) -> List[bpy.types.Collection]:
    """
    Get all descendant collections (children, grandchildren, etc.) of a given collection.
    Recurses through the full hierarchy.

    Args:
        parentCollection: The collection whose descendants to retrieve

    Returns:
        List[bpy.types.Collection]: All descendant collections, or [] if none/invalid
    """
    if not parentCollection:
        return []

    result = []

    def RecursiveCollect(collection: bpy.types.Collection) -> None:
        for child in collection.children:
            result.append(child)
            RecursiveCollect(child)

    RecursiveCollect(parentCollection)
    return result


def MoveToCollection(obj: bpy.types.Object, target_collection: bpy.types.Collection) -> bool:
    if not obj or not target_collection:
        PopupError("Object or collection not provided")
        return False

    for col in obj.users_collection:
        col.objects.unlink(obj)

    target_collection.objects.link(obj)
    return True


def ApplyAllModifiersOnObject(obj: bpy.types.Object) -> None:
    SelectExclusive(obj)
    if GetCurrentMode() != "OBJECT":
        EnterMode("OBJECT")
    ConvertToMesh(obj)


def ApplyModifier(mod: bpy.types.Modifier) -> None:
    obj = GetModifierOwner(mod)
    with bpy.context.temp_override(object=obj, active_object=obj):
        bpy.ops.object.modifier_apply(modifier=mod.name)


def IsTransformApplied(obj: bpy.types.Object) -> bool:
    # scale is applied if every axis is 1.0
    scaleApplied: bool = all(abs(s - 1.0) < 1e-6 for s in obj.scale)

    # rotation is applied if the euler is (0, 0, 0)
    rotationApplied: bool = all(abs(a) < 1e-6 for a in obj.rotation_euler)

    return scaleApplied and rotationApplied


def ApplyTransforms(targetObject: bpy.types.Object) -> None:
    ApplyScale(targetObject)
    ApplyRotation(targetObject)


def ApplyScale(targetObject: bpy.types.Object) -> None:
    SelectExclusive(targetObject)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    ClearSelection()


def ApplyRotation(targetObject: bpy.types.Object) -> None:
    SelectExclusive(targetObject)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
    ClearSelection()


def SetOriginToWorldOrigin(targetObject: bpy.types.Object) -> None:
    if GetCurrentMode() != "OBJECT":
        EnterMode("OBJECT")

    cur = bpy.context.scene.cursor
    prev = cur.location.copy()
    cur.location = (0, 0, 0)
    bpy.context.view_layer.objects.active = targetObject
    targetObject.select_set(True)
    bpy.ops.object.origin_set(type="ORIGIN_CURSOR")
    cur.location = prev
    targetObject.select_set(False)
    bpy.context.view_layer.objects.active = None


def SetOriginToMass(targetObject: bpy.types.Object) -> None:
    if GetCurrentMode() != "OBJECT":
        EnterMode("OBJECT")

    bpy.context.view_layer.objects.active = targetObject
    targetObject.select_set(True)

    # "VOLUME" calculates the center of mass based on the volume of the mesh
    bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="VOLUME")

    targetObject.select_set(False)
    bpy.context.view_layer.objects.active = None


def SetOriginToGeometry(targetObject: bpy.types.Object) -> None:
    if GetCurrentMode() != "OBJECT":
        EnterMode("OBJECT")

    bpy.context.view_layer.objects.active = targetObject
    targetObject.select_set(True)

    # "MEDIAN" calculates the median of the vertices (the default Geometry option in the UI)
    bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="MEDIAN")

    targetObject.select_set(False)
    bpy.context.view_layer.objects.active = None

def JoinObjects(objects):
    if not objects:
        return None
    if len(objects) == 1:
        return objects[0]
    target = objects[0]
    with bpy.context.temp_override(
            object=target,
            active_object=target,
            selected_objects=objects,
            selected_editable_objects=objects,
    ):
        bpy.ops.object.join()
    return target

# def JoinObjects(objects: List[bpy.types.Object]) -> Optional[bpy.types.Object]:
#     if objects is None or len(objects) == 0:
#         return None
# 
#     ClearSelection()
#     for o in objects[1:]:
#         SelectObject(o)
#     SelectObject(objects[0])
# 
#     bpy.ops.object.join()
#     return GetActiveObject()


def GetCurrentMode() -> str:
    return bpy.context.mode


def IsEditingNLA() -> bool:
    if hasattr(bpy.context.scene, "is_nla_tweakmode"):
        return bpy.context.scene.is_nla_tweakmode
    return False


# Snapshot taken by ExitEditingNLA(), consumed by EnterEditingNLA()
_nlaTweakState = {}


def _FindTweakedStrip(ad):
    """While in tweak mode, find the (track, strip) being edited."""
    candidates = []
    for track in ad.nla_tracks:
        for strip in track.strips:
            if strip.action == ad.action:
                candidates.append((track, strip))

    if not candidates:
        return None, None

    # Prefer the strip flagged active, then the active track
    for track, strip in candidates:
        if strip.active:
            return track, strip
    for track, strip in candidates:
        if track.active:
            return track, strip
    return candidates[0]


def ExitEditingNLA() -> bool:
    global _nlaTweakState
    exited = False
    state = {}

    for obj in bpy.context.scene.objects:
        ad = obj.animation_data
        if ad is None:
            continue

        # Record what's needed to get back in, before we change anything
        soloTracks = [t.name for t in ad.nla_tracks if t.is_solo]

        if ad.use_tweak_mode:
            track, strip = _FindTweakedStrip(ad)
            state[obj.name] = {
                "track": track.name if track else None,
                "strip": strip.name if strip else None,
                "solo": soloTracks,
            }
            ad.use_tweak_mode = False
            exited = True

        for track in ad.nla_tracks:
            track.is_solo = False

    # Only overwrite the snapshot if we actually exited something,
    # so a second call doesn't wipe it
    if exited:
        _nlaTweakState = state

    return exited


def ReEnterEditingNLA() -> bool:
    """
    Re-enter the tweak mode that ExitEditingNLA() left.
    Returns True if tweak mode was re-entered on at least one object.
    """
    global _nlaTweakState
    entered = False

    for objName, info in _nlaTweakState.items():
        obj = bpy.data.objects.get(objName)
        if obj is None or obj.animation_data is None:
            continue

        ad = obj.animation_data
        if ad.use_tweak_mode:
            continue

        track = ad.nla_tracks.get(info["track"]) if info["track"] else None
        strip = track.strips.get(info["strip"]) if track and info["strip"] else None
        if track is None or strip is None:
            continue

        # Tweak mode enters on the active track's active/selected strip.
        # strip.active is read-only, so drive it through selection instead.
        for t in ad.nla_tracks:
            t.select = False
            for s in t.strips:
                s.select = False

        ad.nla_tracks.active = track
        track.select = True
        strip.select = True

        try:
            ad.use_tweak_mode = True
            entered = True
        except Exception as e:
            print(f"EnterEditingNLA failed for {objName}: {e}")
            continue

        # Only ever assign True. Assigning False to a non-solo track
        # clears the solo flag on the whole animation data.
        for name in info["solo"]:
            t = ad.nla_tracks.get(name)
            if t is not None:
                t.is_solo = True

    if entered:
        _nlaTweakState = {}

    return entered


# def ExitEditingNLA() -> bool:
#     exited = False
#
#     for obj in bpy.context.scene.objects:
#         ad = obj.animation_data
#         if ad is None:
#             continue
#
#         # Leave tweak mode on every object that's in it
#         if ad.use_tweak_mode:
#             ad.use_tweak_mode = False
#             exited = True
#
#         # Re-enable everything so all strips are evaluated/exported
#         for track in ad.nla_tracks:
#             track.is_solo = False
#
#     return exited


def ExportFbx(filepath, obj):
    prevSelected = GetSelectedObjects()
    prevActive = GetActiveObject()
    wasHidden = ObjectIsHidden(obj)

    try:
        MakeObjectVisible(obj)
        ClearSelection()
        SelectObject(obj)

        # Export
        bpy.ops.export_scene.fbx(
            filepath=filepath,
            use_selection=True,
            use_visible=True,  # Now works because we unhid the object
            object_types={"MESH"},
            use_triangles=True,
            axis_forward="Y",
            axis_up="Z",
            apply_scale_options="FBX_SCALE_ALL",
            mesh_smooth_type="FACE",
            use_mesh_modifiers=True,
            add_leaf_bones=False,
            bake_anim=False,
            path_mode="AUTO",
        )
        return True

    except Exception as e:
        PopupError(f"Export failed for {obj.name}: {str(e)}")
        return False

    finally:
        # Restore hide state
        if wasHidden:
            MakeObjectHidden(obj)

        # Restore selection state
        ClearSelection()
        for obj in prevSelected:
            SelectObject(obj)

        if ObjectExists(prevActive):
            SelectObject(prevActive)


def IsInLocalView() -> bool:
    return getattr(bpy.context.space_data, "local_view", None) is not None


def EnterLocalView() -> None:
    if IsInLocalView():
        return
    bpy.ops.view3d.localview()


def ExitLocalView() -> None:
    if not IsInLocalView():
        return
    bpy.ops.view3d.localview()


def EnterObjectMode() -> None:
    if bpy.context.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")


def EnterEditMode() -> None:
    if bpy.context.mode != "EDIT":
        bpy.ops.object.mode_set(mode="EDIT")


def EnterPoseMode() -> None:
    if bpy.context.mode != "POSE":
        bpy.ops.object.mode_set(mode="POSE")


def EnterMode(modeToEnter: str) -> None:
    bpy.ops.object.mode_set(mode=modeToEnter)


def ObjectIsMesh(obj):
    return obj.type == 'MESH'

def ObjectHasModifiers(obj):
    return len(obj.modifiers) > 0

def ConvertToMesh(obj: bpy.types.Object) -> None:
    if not ObjectHasModifiers(obj) and ObjectIsMesh(obj):
        return
    activeObjectBefore = GetActiveObject()
    selectionBefore = GetSelectedObjects()

    SelectExclusive(obj)
    bpy.ops.object.convert(target="MESH")
    ClearSelection()

    for prevSelection in selectionBefore:
        SelectObject(prevSelection)
    if ObjectExists(activeObjectBefore):
        SelectObject(activeObjectBefore)


# Serves as a bpy reference, or can be called
def RenameCollection(col: bpy.types.Collection, newName: str) -> None:
    col.name = newName


# Serves as a bpy reference, or can be called
def RenameObject(obj: bpy.types.Object, newName: str) -> None:
    obj.name = newName


def PopupError(msg: str) -> None:
    def draw(self, _):
        self.layout.label(text=msg)

    bpy.context.window_manager.popup_menu(draw, title="Error!", icon="ERROR")


def PopupPrint(msg: str) -> None:
    def draw(self, _):
        self.layout.label(text=msg)

    bpy.context.window_manager.popup_menu(draw, title="Addon Output", icon="INFO")


def CreateCollection(collectionName: str) -> bpy.types.Collection:
    existing = bpy.data.collections.get(collectionName)
    if existing:
        raise Exception(
            f"Collection {collectionName} already existed. Is this a bug, or should you have called GetOrCreateCollection() instead?")
    newCollection = bpy.data.collections.new(collectionName)
    bpy.context.scene.collection.children.link(newCollection)
    return newCollection


def GetOrCreateCollection(collection_name: str) -> bpy.types.Collection:
    collection = bpy.data.collections.get(collection_name)
    if not collection:
        collection = bpy.data.collections.new(collection_name)
        bpy.context.scene.collection.children.link(collection)
    return collection


def DuplicateObject_LinkData(objectToDupe: bpy.types.Object) -> bpy.types.Object:
    newObject = objectToDupe.copy()
    newObject.data = objectToDupe.data
    bpy.context.collection.objects.link(newObject)
    return newObject


def DuplicateObjectWithModifiersDisabled(targetObject: bpy.types.Object):
    raise ValueError("This doesn't work, due to weird blender dependency graph shit. Don't use it. Batch-disable"
                     "all modifiers for all objects you're working with before even doing a single dupe.")
    originallyActive = GetAllActiveModifiers(targetObject)
    for mod in originallyActive:
        MakeModifierInactive(mod)

    # bpy.context.view_layer.update()   

    dupe = DuplicateObject(targetObject)
    for mod in originallyActive:
        MakeModifierActive(mod)
    return dupe


def DuplicateObject(targetObject: bpy.types.Object, useSameNameAsOriginal: bool = False) -> Optional[bpy.types.Object]:
    if not targetObject:
        PopupError("No object provided")
        return None

    newObject = targetObject.copy()
    if targetObject.data:
        newObject.data = targetObject.data.copy()

    for collection in targetObject.users_collection:
        collection.objects.link(newObject)

    if useSameNameAsOriginal:
        # Let Blender handle the naming with automatic increment
        newObject.name = targetObject.name
    else:
        newObject.name = f"{targetObject.name}_Copy"

    return newObject


def DuplicateCollection(srcCollection: bpy.types.Collection, newName: Optional[str] = None) -> Optional[
    bpy.types.Collection]:
    if not srcCollection:
        PopupError("No collection provided")
        return None

    if not newName:
        newName = f"{srcCollection.name}_Copy"

    newCollection = bpy.data.collections.new(newName)
    bpy.context.scene.collection.children.link(newCollection)

    objMap = {}
    for obj in srcCollection.objects:
        newObj = obj.copy()
        if obj.data:
            newObj.data = obj.data.copy()
        newObj.name = f"{obj.name}_Copy"

        newCollection.objects.link(newObj)
        objMap[obj] = newObj

    for childCollection in srcCollection.children:
        duplicatedChild = DuplicateCollection(
            childCollection, f"{childCollection.name}_Dupe"
        )

        if duplicatedChild:
            if duplicatedChild.name in bpy.context.scene.collection.children:
                bpy.context.scene.collection.children.unlink(duplicatedChild)
            newCollection.children.link(duplicatedChild)

    for oldObj, newObj in objMap.items():
        if oldObj.parent and oldObj.parent in objMap:
            newObj.parent = objMap[oldObj.parent]
            newObj.matrix_parent_inverse = oldObj.matrix_parent_inverse.copy()

    return newCollection


def DeleteModifier(modifierToDelete: bpy.types.Modifier) -> None:
    GetModifierOwner(modifierToDelete).modifiers.remove(modifierToDelete)


def DeleteObject(objectToDelete: bpy.types.Object):
    bpy.data.objects.remove(objectToDelete, do_unlink=True)


def GetObjectRotation(objectToRead: bpy.types.Object):
    return objectToRead.rotation_euler


def GetObjectScale(objectToRead: bpy.types.Object):
    return objectToRead.scale


def ModifyScale(objectToModify, newScale):
    objectToModify.scale = newScale


def ModifyRotation(objectToModify: bpy.types.Object, newRotation):
    """Set the rotation of an object"""
    objectToModify.rotation_euler = newRotation


def EnterGrabMode():
    """Enter grab/move mode for selected objects"""
    # Set to object mode first if needed
    if bpy.context.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")

    # Enter grab mode
    bpy.ops.transform.translate('INVOKE_DEFAULT')


def GetObjectsInCollection(targetCollection: bpy.types.Collection) -> List[bpy.types.Object]:
    if not targetCollection:
        return []

    objectList = []

    def RecursiveCollect(collection: bpy.types.Collection) -> None:
        for obj in collection.objects:
            objectList.append(obj)
        for childCollection in collection.children:
            RecursiveCollect(childCollection)

    RecursiveCollect(targetCollection)
    return objectList


def SelectExclusive(object: bpy.types.Object) -> None:
    ClearSelection()
    SelectObject(object)


def SelectObject(object: bpy.types.Object) -> None:
    if object is None:
        return
    object.select_set(True)
    bpy.context.view_layer.objects.active = object


def DeselectObject(obj: bpy.types.Object) -> None:
    obj.select_set(False)
    if bpy.context.view_layer.objects.active == obj:
        bpy.context.view_layer.objects.active = None


def ClearSelection() -> None:
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active = None


def GetLayerCollection(target_collection: bpy.types.Collection) -> Optional[bpy.types.LayerCollection]:
    view_layer = bpy.context.view_layer

    def find_layer_collection(layer_collection, target):
        if layer_collection.collection == target:
            return layer_collection
        for child in layer_collection.children:
            result = find_layer_collection(child, target)
            if result:
                return result
        return None

    return find_layer_collection(view_layer.layer_collection, target_collection)


def ObjectIsHidden(obj: bpy.types.Object) -> bool:
    return not ObjectIsVisible(obj)


def ObjectIsVisible(obj: bpy.types.Object) -> bool:
    if not obj:
        return False

    if obj.hide_get():
        return False

    if obj.hide_viewport:
        return False

    viewLayer = bpy.context.view_layer

    def is_collection_excluded(collection):
        layerCollection = GetLayerCollection(collection)
        if layerCollection and layerCollection.exclude:
            return True
        if collection.hide_viewport:
            return True
        return False

    for collection in obj.users_collection:
        if is_collection_excluded(collection):
            return False

    return True


def MakeObjectVisible(obj: bpy.types.Object) -> None:
    obj.hide_set(False)


def MakeObjectHidden(obj: bpy.types.Object) -> None:
    obj.hide_set(True)


def MakeCollectionVisible(targetCollection: bpy.types.Collection) -> None:
    """Make a collection visible in the viewport (recursively)"""

    def set_visible_recursive(layer_collection):
        layer_collection.hide_viewport = False
        layer_collection.exclude = False
        for child in layer_collection.children:
            set_visible_recursive(child)

    layer_collection = GetLayerCollection(targetCollection)
    if layer_collection:
        set_visible_recursive(layer_collection)


def SetCollectionToActive(targetCollection: bpy.types.Collection) -> bool:
    if not targetCollection:
        print("No collection provided")
        return False

    viewLayer = bpy.context.view_layer

    def find_layer_collection(layer_collection, target):
        if layer_collection.collection == target:
            return layer_collection
        for child in layer_collection.children:
            result = find_layer_collection(child, target)
            if result:
                return result
        return None

    layerCollection = find_layer_collection(viewLayer.layer_collection, targetCollection)

    if layerCollection:
        viewLayer.active_layer_collection = layerCollection
        return True

    return False


def GetActiveCollection() -> Optional[bpy.types.Collection]:
    return bpy.context.view_layer.active_layer_collection.collection


def GetCollectionByName(collectionName: str) -> Optional[bpy.types.Collection]:
    return bpy.data.collections.get(collectionName)


def IsInCollection_Direct(obj: bpy.types.Object, collection: bpy.types.Collection):
    if not obj or not collection:
        return False
    return obj in collection.objects


def IsInCollection(obj: bpy.types.Object, collection: bpy.types.Collection):
    if not obj or not collection:
        return False
    return obj in GetObjectsInCollection(collection)


def GetObjectsByPattern_CaseInsensitive(pattern: str) -> List[bpy.types.Object]:
    result = []
    for obj in bpy.data.objects:
        if pattern.lower() in obj.name.lower():
            result.append(obj)
    return result


def GetObjectsByPattern(pattern: str) -> List[bpy.types.Object]:
    result = []
    for obj in bpy.data.objects:
        if pattern in obj.name:
            result.append(obj)
    return result


def GetCollectionsByPattern(pattern: str) -> List[bpy.types.Collection]:
    result = []
    for collection in bpy.data.collections:
        if pattern in collection.name:
            result.append(collection)
    return result


def IsInObjectMode() -> bool:
    """
    Check whether Blender is currently in Object Mode.

    Returns:
        bool: True if the current mode is "OBJECT", False otherwise.
    """
    return bpy.context.mode == "OBJECT"


def IsInEditMode() -> bool:
    """
    Check whether Blender is currently in an Edit Mode.

    Covers all edit variants (mesh, armature, curve, etc.), since
    bpy.context.mode reports them with different suffixes.

    Returns:
        bool: True if the current mode is any EDIT_* mode, False otherwise.
    """
    return bpy.context.mode.startswith("EDIT")


def IsInPoseMode() -> bool:
    """
    Check whether Blender is currently in Pose Mode.

    Returns:
        bool: True if the current mode is "POSE", False otherwise.
    """
    return bpy.context.mode == "POSE"


def ExcludeCollection(targetCollection: bpy.types.Collection) -> bool:
    if not targetCollection:
        PopupError("No collection provided")
        return False

    viewLayer = bpy.context.view_layer

    def find_layer_collection(layer_collection, target):
        if layer_collection.collection == target:
            return layer_collection
        for child in layer_collection.children:
            result = find_layer_collection(child, target)
            if result:
                return result
        return None

    layerCollection = find_layer_collection(viewLayer.layer_collection, targetCollection)

    if layerCollection:
        layerCollection.exclude = True
        return True
    return False


def GetCurrentFileName(includeExtension: bool = False) -> str:
    if not bpy.data.filepath:
        return ""

    fileName = os.path.splitext(os.path.basename(bpy.data.filepath))[0]

    if includeExtension:
        fileName += ".blend"

    return fileName


def CollectionWasIncluded(targetCollection: bpy.types.Collection) -> bool:
    return not CollectionWasExcluded(targetCollection)


def CollectionWasExcluded(targetCollection: bpy.types.Collection) -> bool:
    if not targetCollection:
        return False

    layerCollection = GetLayerCollection(targetCollection)

    if layerCollection:
        return layerCollection.exclude
    return False


def IncludeCollection(targetCollection: bpy.types.Collection) -> bool:
    if not targetCollection:
        PopupError("No collection provided")
        return False

    layerCollection = GetLayerCollection(targetCollection)

    if layerCollection:
        layerCollection.exclude = False
        return True
    return False


def ObjectExists(obj: Optional[bpy.types.Object]) -> bool:
    return obj is not None and obj.name in bpy.data.objects


def GetActiveObject() -> bpy.types.Object:
    return bpy.context.view_layer.objects.active


def GetSelectedObjects() -> List[bpy.types.Object]:
    return bpy.context.selected_objects


def GetModifierValue(mod: bpy.types.Modifier, propertyName: str) -> any:
    return getattr(mod, propertyName)


def SetModifierProperty(mod: bpy.types.Modifier, propertyName: str, value: any) -> None:
    setattr(mod, propertyName, value)


def AddModifier(obj: bpy.types.Object, userSpecifiedName: str, internalType: str) -> bpy.types.Modifier:
    return obj.modifiers.new(name=userSpecifiedName, type=internalType)


def GetModifiers(obj: bpy.types.Object):
    return obj.modifiers


def IsGeonodeModifier(mod: bpy.types.Modifier) -> bool:
    return mod.type == "NODES" and mod.node_group


def GetGeonodeTypeName(geonodeMod: bpy.types.Modifier) -> str:
    return geonodeMod.node_group.name


def GetGeometryNodeField(mod: bpy.types.Modifier, name: str):
    for item in mod.node_group.interface.items_tree:
        if item.item_type == 'SOCKET' and item.in_out == 'INPUT' and item.name == name:
            return getattr(mod.properties.inputs, item.identifier)
    raise ValueError(f"No input socket named '{name}'")


def PrintAllGeometryNodeFieldNames(mod: bpy.types.Modifier) -> None:
    lines = [
        f"{item.name} ({item.identifier})"
        for item in mod.node_group.interface.items_tree
        if item.item_type == 'SOCKET' and item.in_out == 'INPUT'
    ]
    PopupPrint("\n".join(lines))


def Lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def GetModifiertype(mod: bpy.types.Modifier):
    return mod.type


def GetModifier(obj: bpy.types.Object, userSpecifiedName: str, modifierIndex: int = 0) -> Optional[bpy.types.Modifier]:
    matches = [m for m in obj.modifiers if m.name == userSpecifiedName]
    if matches and modifierIndex < len(matches):
        return matches[modifierIndex]
    return None


def GetParentOfCollection(collection: bpy.types.Collection) -> Optional[bpy.types.Collection]:
    """
    Get the immediate parent collection of a given collection.

    Args:
        collection: The collection to find the parent of

    Returns:
        Optional[bpy.types.Collection]: The parent collection if found, None otherwise
    """
    if not collection:
        PopupError("No collection provided")
        return None

    # Check if collection is directly in the scene root
    if collection.name in bpy.context.scene.collection.children:
        return bpy.context.scene.collection

    # Search through all collections to find which one has this as a child
    for parent in bpy.data.collections:
        if collection.name in parent.children:
            return parent

    return None


def MakeCollectionChildOf(target: bpy.types.Collection, collectionToBecomeChildOf: bpy.types.Collection) -> bool:
    """
    Make a collection a child of another collection.

    Args:
        target: The collection to move as a child
        collectionToBecomeChildOf: The parent collection

    Returns:
        bool: True if successful, False otherwise
    """
    if not target or not collectionToBecomeChildOf:
        PopupError("Target collection or parent collection not provided")
        return False

    # Check if target is already a child of the parent
    if target.name in collectionToBecomeChildOf.children:
        return True

    # Check if target is the same as parent (prevent self-parenting)
    if target == collectionToBecomeChildOf:
        PopupError("Cannot make a collection a child of itself")
        return False

    # Check if parent is a descendant of target (prevent circular parenting)
    def is_descendant(parent: bpy.types.Collection, potential_child: bpy.types.Collection) -> bool:
        for child in parent.children:
            if child == potential_child:
                return True
            if is_descendant(child, potential_child):
                return True
        return False

    if is_descendant(target, collectionToBecomeChildOf):
        PopupError("Cannot create circular collection hierarchy")
        return False

    # Remove target from its current parent(s)
    # Remove from scene root if present
    if target.name in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.unlink(target)

    # Remove from any other parent collections
    for parent in bpy.data.collections:
        if target.name in parent.children:
            parent.children.unlink(target)

    # Link target as child of the new parent
    collectionToBecomeChildOf.children.link(target)

    return True


def ModifierIsActive(mod: bpy.types.Modifier) -> bool:
    return mod.show_viewport


def MakeModifierActive(mod: bpy.types.Modifier) -> None:
    mod.show_viewport = True
    mod.show_render = True


def MakeModifierInactive(mod: bpy.types.Modifier) -> None:
    mod.show_viewport = False
    mod.show_render = False


def PinModifierToLast(modifier: bpy.types.Modifier) -> None:
    modifier.use_pin_to_last = True


def UnpinAllModifiers(obj: bpy.types.Object) -> None:
    for mod in obj.modifiers:
        mod.use_pin_to_last = False


def DeleteCollection(col: bpy.types.Collection) -> None:
    """Delete a collection and all its contents (objects and child collections)"""
    if not col:
        PopupError("No collection provided")
        return

    # Get all objects in the collection (including nested)
    objects_to_delete = GetObjectsInCollection(col)

    # Delete all objects
    for obj in objects_to_delete:
        if ObjectExists(obj):
            DeleteObject(obj)

    # Remove the collection from all parents
    for parent in bpy.data.collections:
        if col.name in parent.children:
            parent.children.unlink(col)

    # Remove from scene root if present
    if col.name in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.unlink(col)

    # Finally, remove the collection itself
    bpy.data.collections.remove(col)


def SeparateLoose(originalObject: bpy.types.Object) -> List[bpy.types.Object]:
    """
    Separates an object into its loose parts.
    Returns a list of the resulting objects (including the original).
    """
    if not originalObject or originalObject.type != 'MESH':
        return []

    # Track which objects existed before separation
    objectsBefore = set(bpy.data.objects)

    # Store user selection/active state
    prevActive = GetActiveObject()
    prevSelected = GetSelectedObjects()

    # Select only our target object
    SelectExclusive(originalObject)

    # Enter Edit Mode (required for mesh.separate)
    if GetCurrentMode() != "EDIT":
        EnterMode("EDIT")

    # Separate by loose parts
    bpy.ops.mesh.separate(type='LOOSE')

    # Go back to Object Mode
    EnterObjectMode()

    # Find what new objects were created
    newObjects = list(set(bpy.data.objects) - objectsBefore)

    # The original object is part of the result, so add it back in
    result = [originalObject] + newObjects

    # Restore user selection/active state
    ClearSelection()
    for sel in prevSelected:
        if ObjectExists(sel):
            SelectObject(sel)
    if ObjectExists(prevActive):
        SelectObject(prevActive)

    return result


def ClusterObjectsInInputCollection(collectionToCluster, cellSize):
    baskets = {}
    for obj in GetObjectsInCollection(collectionToCluster):
        ConvertToMesh(obj)  

        # Median center computed from the vertices, instead of origin_set just to read a position
        verts = obj.data.vertices
        if len(verts) == 0:
            continue
        center = sum((v.co for v in verts), Vector()) / len(verts)
        position = obj.matrix_world @ center

        key = GetKey(position, cellSize)
        baskets.setdefault(key, []).append(obj)

    clusterIndex = 0
    for clusterList in baskets.values():
        clusterIndex += 1
        cluster = JoinObjects(clusterList)
        cluster.name = f"{collectionToCluster.name}_Cluster{clusterIndex}"

def GenerateNewClusteredCollection(originalCollection, cellSize):
    clusterCollection = DuplicateCollection(originalCollection, "WORKING_GATHER_COLLECTION")
    ClusterObjectsInInputCollection(clusterCollection, cellSize)
    return clusterCollection

# def GenerateNewClusteredCollection(originalCollection, cellSize):
#     clusterCollection = DuplicateCollection(originalCollection, "WORKING_GATHER_COLLECTION")
#     baskets = {}
#     for obj in GetObjectsInCollection(clusterCollection):
#         ConvertToMesh(obj)
#         SetOriginToGeometry(obj)
#         position = GetObjectPosition(obj)
#         key = GetKey(position, cellSize)
#         if key not in baskets:
#             baskets[key] = []
#         baskets[key].append(obj)
# 
#     clusterIndex = 0
#     for clusterList in baskets.values():
#         clusterIndex += 1
#         cluster = JoinObjects(clusterList)
#         cluster.name = f"{originalCollection.name}_Cluster{clusterIndex}"
# 
#     return clusterCollection


def GetKey(rawPosition, cellSize):
    return (
        math.floor(rawPosition.x / cellSize),
        math.floor(rawPosition.z / cellSize),
        math.floor(rawPosition.y / cellSize)
    )


def register() -> None:
    print("CenLib loaded")


def unregister() -> None:
    print("CenLib unloaded")


if __name__ == "__main__":
    register()

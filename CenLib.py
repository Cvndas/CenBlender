

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

import bpy

def Cancelled():
    return {"CANCELLED"}

def Finished():
    return {"FINISHED"}

def GetAllObjects()->List[bpy.types.Object]:
    return list(bpy.data.objects)


def GetModifierOwner(mod: bpy.types.Modifier)->bpy.types.Object:
    return mod.id_data
    
def GetVertexGroupNames(obj: bpy.types.Object):
    allNames = []
    for vertexGroup in obj.vertex_groups:
        allNames.append(vertexGroup.name)
    return allNames

def GetVertexGroup(obj: bpy.types.Object, groupName: str):
    return obj.vertex_groups.get(groupName)

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


def JoinObjects(objects: List[bpy.types.Object]) -> Optional[bpy.types.Object]:
    if objects is None or len(objects) == 0:
        return None

    ClearSelection()
    for o in objects[1:]:
        SelectObject(o)
    SelectObject(objects[0])

    bpy.ops.object.join()
    return GetActiveObject()

def GetCurrentMode()->str:
    return bpy.context.mode

def IsEditingNLA()->bool:
    if hasattr(bpy.context.scene, "is_nla_tweakmode"):
        return bpy.context.scene.is_nla_tweakmode
    return False

def IsInLocalView()->bool:
    return getattr(bpy.context.space_data, "local_view", None) is not None

def EnterObjectMode()-> None:
    if bpy.context.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")

def EnterMode(modeToEnter: str)->None:
    bpy.ops.object.mode_set(mode=modeToEnter)

def ConvertToMesh(obj: bpy.types.Object) -> None:
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
        raise Exception(f"Collection {collectionName} already existed. Is this a bug, or should you have called GetOrCreateCollection() instead?")
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




def DuplicateCollection(srcCollection: bpy.types.Collection, newName: Optional[str] = None) -> Optional[bpy.types.Collection]:
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




def GetCollectionsByPattern(pattern: str) -> List[bpy.types.Collection]:
    result = []
    for collection in bpy.data.collections:
        if pattern in collection.name:
            result.append(collection)
    return result



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

def IsGeonodeModifier(mod: bpy.types.Modifier)-> bool:
    return mod.type == "NODES" and mod.node_group

def GetGeonodeTypeName(geonodeMod: bpy.types.Modifier)->str:
    return geonodeMod.node_group.name

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

def ModifierIsActive(mod: bpy.types.Modifier)->bool:
    return mod.show_viewport

def MakeModifierActive(mod: bpy.types.Modifier)-> None:
    mod.show_viewport = True

def MakeModifierInactive(mod: bpy.types.Modifier)-> None:
    mod.show_viewport = False

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

def register() -> None:
    print("CenLib loaded")


def unregister() -> None:
    print("CenLib unloaded")


if __name__ == "__main__":
    register()
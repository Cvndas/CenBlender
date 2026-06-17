

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

def MoveToCollection(obj: bpy.types.Object, target_collection: bpy.types.Collection) -> bool:
    if not obj or not target_collection:
        PopupError("Object or collection not provided")
        return False
    
    for col in obj.users_collection:
        col.objects.unlink(obj)
    
    target_collection.objects.link(obj)
    return True





def PopupError(msg: str) -> None:
    def draw(self, _):
        self.layout.label(text=msg)

    bpy.context.window_manager.popup_menu(draw, title="Error!", icon="ERROR")


def PopupPrint(msg: str) -> None:
    def draw(self, _):
        self.layout.label(text=msg)

    bpy.context.window_manager.popup_menu(draw, title="Addon Output", icon="INFO")


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
    bpy.data.object.remove(objectToDelete, do_unlink=True)

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
        PopupError("No collection provided")
        return []

    objectList = []

    def RecursiveCollect(collection: bpy.types.Collection) -> None:
        for obj in collection.objects:
            objectList.append(obj)
        for childCollection in collection.children:
            RecursiveCollect(childCollection)

    RecursiveCollect(targetCollection)
    return objectList

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


def IsVisible(obj: bpy.types.Object) -> bool:
    if not obj:
        return False
    
    if obj.hide_get():
        return False
    
    if obj.hide_viewport:
        return False
    
    viewLayer = bpy.context.view_layer
    
    def find_layer_collection(layer_collection, target_collection):
        if layer_collection.collection == target_collection:
            return layer_collection
        for child in layer_collection.children:
            result = find_layer_collection(child, target_collection)
            if result:
                return result
        return None
    
    def is_collection_excluded(collection):
        layerCollection = find_layer_collection(viewLayer.layer_collection, collection)
        if layerCollection and layerCollection.exclude:
            return True
        if collection.hide_viewport:
            return True
        return False
    
    for collection in obj.users_collection:
        if is_collection_excluded(collection):
            return False
    
    return True

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
        return layerCollection.exclude
    return False


def IncludeCollection(targetCollection: bpy.types.Collection) -> bool:
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
        layerCollection.exclude = False
        return True
    return False

def GetActiveObject() -> bpy.types.Object:
    return bpy.context.view_layer.objects.active

def GetSelectedObjects() -> List[bpy.types.Object]:
    return bpy.context.selected_objects


def SetModifierProperty(obj: bpy.types.Object, userSpecifiedName: str, modifierIndex: int, propertyName: str, value: any) -> None:
    matches = [m for m in obj.modifiers if m.name == userSpecifiedName]
    if matches and modifierIndex < len(matches):
        setattr(matches[modifierIndex], propertyName, value)


def AddModifier(obj: bpy.types.Object, userSpecifiedName: str, internalModifierName: str) -> bpy.types.Modifier:
    return obj.modifiers.new(name=userSpecifiedName, type=internalModifierName)


def GetModifier(obj: bpy.types.Object, userSpecifiedName: str, modifierIndex: int = 0) -> Optional[bpy.types.Modifier]:
    matches = [m for m in obj.modifiers if m.name == userSpecifiedName]
    if matches and modifierIndex < len(matches):
        return matches[modifierIndex]
    return None


def PinModifierToLast(modifier: bpy.types.Modifier) -> None:
    modifier.use_pin_to_last = True


def HideFromViewport(objects: List[bpy.types.Object]) -> None:
    for obj in objects:
        obj.hide_set(True)


def register() -> None:
    print("CenLib loaded")


def unregister() -> None:
    print("CenLib unloaded")


if __name__ == "__main__":
    register()
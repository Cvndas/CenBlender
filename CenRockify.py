bl_info = {
    "name": "CenRockify",
    "author": "Lrodas",
    "version": (1, 0),
    "blender": (4, 4, 0),
    "location": "View3D > Sidebar > Centradigon Tab",
    "description": "Duplicate rocks and setup LODs",
    "category": "Centradigon Tools",
}

import bpy
import CenLib

# ----------------- Core Functions -----------------


def SetupModifier(object):
    for modifier in list(object.modifiers):
        if modifier.type == "NODES" and modifier.node_group:
            if modifier.node_group.name == "RockPainter_V2":
                modifier.show_viewport = True
                modifier.show_render = True
                modifier["Socket_11"] = True
            else:
                object.modifiers.remove(modifier)
        else:
            object.modifiers.remove(modifier)


def RockPainterLodder():
    if CenLib.IsInLocalView():
        CenLib.PopupError("Exit local view first")
        return CenLib.Cancelled()

    activeCollection = bpy.context.collection
    if activeCollection is None:
        CenLib.PopupError("No active collection")
        return

    objectsWithRockpainter = []
    for obj in activeCollection.objects:
        rockPaintersOnObjectFound = 0
        for modifier in obj.modifiers:
            if modifier.type == "NODES" and modifier.node_group:
                if modifier.node_group.name == "RockPainter_V2":
                    if rockPaintersOnObjectFound > 0:
                        obj.modifiers.remove(modifier)
                    else:
                        objectsWithRockpainter.append(obj)
                        modifier.show_viewport = False
                        modifier.show_render = False
                        rockPaintersOnObjectFound += 1

    rockCollectionName = f"{activeCollection.name}-Template"
    paintedRocksCollection = CenLib.GetOrCreateCollection(rockCollectionName)
    oldRocks = CenLib.GetObjectsInCollection(paintedRocksCollection)
    for oldRock in oldRocks:
        CenLib.DeleteObject(oldRock)

    rockIndex = 0
    for obj in objectsWithRockpainter:
        dupeLod0 = CenLib.DuplicateObject_LinkData(obj)
        dupeLod1 = CenLib.DuplicateObject_LinkData(obj)
        dupeLod0.name = f"Rock{rockCollectionName}_{rockIndex}-V_LOD0"
        dupeLod1.name = f"Rock{rockCollectionName}_{rockIndex}-V_LOD1"
        CenLib.MoveToCollection(dupeLod0, paintedRocksCollection)
        CenLib.MoveToCollection(dupeLod1, paintedRocksCollection)
        SetupModifier(dupeLod0)
        SetupModifier(dupeLod1)

        for mod in obj.modifiers:
            if mod.use_pin_to_last:
                CenLib.PopupError(f"Error: A modifier on {obj.name} was pinned. This will cause problems with CenRockify")

        decimator = dupeLod1.modifiers.new(name="RockLod1Decimate", type="DECIMATE")
        decimator.ratio = 0.1
        CenLib.PinModifierToLast(decimator)

        rockIndex += 1


def SpreadRockPainter(replace_existing=True):
    if CenLib.IsInLocalView():
        CenLib.PopupError("Exit local view first")
        return CenLib.Cancelled()

    activeCollection = CenLib.GetActiveCollection()
    selectedObjects = CenLib.GetSelectedObjects()

    if selectedObjects is None or len(selectedObjects) == 0:
        print("Error: No object selected")
        return

    selectedObj = selectedObjects[0]

    hasRockPainter = False
    sourceModifier = None
    for modifier in selectedObj.modifiers:
        if modifier.type == "NODES" and modifier.node_group:
            if modifier.node_group.name == "RockPainter_V2":
                hasRockPainter = True
                sourceModifier = modifier
                break

    if not hasRockPainter:
        print("Error: Selected object does not have RockPainter_V2 modifier")
        return

    sockets_to_copy = [2, 3, 4, 5, 6, 7, 8, 9, 10]
    socket_values = {}
    for socket in sockets_to_copy:
        socket_key = f"Socket_{socket}"
        if socket_key in sourceModifier:
            socket_values[socket_key] = sourceModifier[socket_key]

    sourceNodeGroup = sourceModifier.node_group

    objectsModified = 0
    for obj in CenLib.GetObjectsInCollection(activeCollection):
        if obj == selectedObj:
            continue

        if replace_existing:
            for modifier in list(obj.modifiers):
                if modifier.type == "NODES" and modifier.node_group:
                    if modifier.node_group.name == "RockPainter_V2":
                        obj.modifiers.remove(modifier)
        else:
            already_has = False
            for modifier in obj.modifiers:
                if modifier.type == "NODES" and modifier.node_group:
                    if modifier.node_group.name == "RockPainter_V2":
                        already_has = True
                        break
            if already_has:
                continue

        newModifier = obj.modifiers.new(name="RockPainter_V2", type="NODES")
        newModifier.node_group = sourceNodeGroup

        for socket_key, value in socket_values.items():
            newModifier[socket_key] = value

        newModifier.show_viewport = True
        newModifier.show_render = True
        objectsModified += 1

        vertexGroups = CenLib.GetVertexGroupNames(obj) 
        if "BigRocks" not in vertexGroups:
            obj.vertex_groups.new(name="BigRocks")

    if objectsModified == 0 and replace_existing:
        print(
            "WARNING: Objects modified was 0. To use this modifier, do the following: Select the object whose RockPainter_V2 you want to spread to objects in the SELECTED TARGET collection"
        )
    print(
        f"Spread RockPainter_V2 to {objectsModified} objects in collection '{activeCollection.name}'"
    )


# ----------------- Operators & Panel -----------------


class ROCKPAINTER_LODDER_OT_Run(bpy.types.Operator):
    bl_idname = "object.rockpainter_lodder"
    bl_label = "CenRockify"
    bl_description = "Duplicate objects with RockPainter_V2 and setup LODs"

    def execute(self, context):
        RockPainterLodder()
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


class ROCKPAINTER_LODDER_PT_Panel(bpy.types.Panel):
    bl_label = "CenRockify"
    bl_idname = "VIEW3D_PT_rockpainter_lodder"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Centradigon"

    def draw(self, context):
        layout = self.layout
        
        active_layer = context.view_layer.active_layer_collection
        if active_layer:
            col_name = active_layer.collection.name
            objects = CenLib.GetObjectsInCollection(CenLib.GetActiveCollection())
            layout.label(text=f"Active: {col_name}")
            layout.label(text=f"Objects: {len(objects)}")
        else:
            layout.label(text="Active: <none>")
        
        layout.separator()
        
        layout.operator("object.rockpainter_lodder", text="Run LOD Setup")
        layout.separator()
        layout.operator(
            "object.rockpainter_spread", text="Spread RockPainter (Replace Existing)"
        )
        layout.operator(
            "object.rockpainter_merge", text="Spread RockPainter (Keep Existing)"
        )


# ----------------- Registration -----------------

classes = [
    ROCKPAINTER_LODDER_OT_Run,
    ROCKPAINTER_LODDER_OT_Spread,
    ROCKPAINTER_LODDER_OT_Merge,
    ROCKPAINTER_LODDER_PT_Panel,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
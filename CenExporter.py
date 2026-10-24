bl_info = {
    "name": "CenExporter",
    "author": "Lrodas",
    "version": (1, 0, 0),
    "blender": (4, 0, 0),
    "location": "3D Viewport > Sidebar (N) > CenExporter",
    "description": "Export each object in active collection to 5 different paths with one click each",
    "category": "Import-Export",
}

import os
import CenLib
import time

import bpy
from bpy.props import PointerProperty, StringProperty, FloatProperty
from bpy.types import PropertyGroup


def Get_Active_Visual_Collision_Collections():
    active = CenLib.GetActiveCollection()
    if not active:
        CenLib.PopupError("No collection was active")
        return None, None, None

    if active.name == "Scene Collection":
        CenLib.PopupError("The active collection was the Scene Collection, which is most definitely a mistake.")
        return None, None, None

    collision = None
    visual = None
    for childCollection in CenLib.GetDirectChildCollections(active):
        if childCollection.name == "Visual":
            visual = childCollection
        elif childCollection.name == "Collision":
            collision = childCollection
        else:
            CenLib.PopupError(
                f"Unrecognized child collection: {childCollection.name}. It must be either Visual or Collision")

    return active, visual, collision


def ExportToPath(path_property_name, context, doCollection):
    state = CenLib.TransitionToExportableState()

    settings = context.scene.cenexporter
    path = getattr(settings, path_property_name, "")

    if not path:
        CenLib.PopupError(
            f"No path set for {path_property_name.replace('_path', '').title()}"
        )
        return CenLib.Cancelled()

    # Expand blender path variables
    directory = bpy.path.abspath(path)

    # Check if directory exists
    if not os.path.exists(directory):
        CenLib.PopupError(f"Directory does not exist: {directory}")
        return CenLib.Cancelled()

    # Get objects from active collection
    if doCollection:
        objects = CenLib.GetObjectsInCollection(CenLib.GetActiveCollection())
        if not objects:
            CenLib.PopupError(f"No objects were in the collection {CenLib.GetActiveCollection().name}")
            return CenLib.Cancelled()
    else:
        objects = CenLib.GetSelectedObjects()
        if not objects:
            CenLib.PopupError("No objects were selected")
            return CenLib.Cancelled()

    # Store all objects' hide states to restore later
    hideStates = {}
    for obj in objects:
        hideStates[obj] = CenLib.ObjectIsHidden(obj)

    try:
        # Export each object individually
        successCount = 0
        for obj in objects:
            # Create filename from object name
            filename = f"{obj.name}.fbx"
            filepath = os.path.join(directory, filename)

            if CenLib.ExportFbx(filepath, obj):
                successCount += 1

        # Report results
        if successCount == len(objects):
            CenLib.PopupPrint(
                f"Successfully exported all {successCount} objects to:\n{directory}"
            )
        else:
            CenLib.PopupPrint(
                f"Exported {successCount} of {len(objects)} objects to:\n{directory}"
            )

        return CenLib.Finished()

    finally:
        # Restore all hide states
        for obj, wasHidden in hideStates.items():
            if wasHidden:
                CenLib.MakeObjectHidden(obj)
            else:
                CenLib.MakeObjectVisible(obj)
        CenLib.RestoreStateAfterExport(state)


def ExportCollectionAsObject(path_property_name, context):
    state = CenLib.TransitionToExportableState()
    activeCollection = CenLib.GetActiveCollection()
    if activeCollection.name == "Scene Collection":
        CenLib.PopupError(
            "This addon does not support exporting Scene Collection, which is the collection currently active")
        return CenLib.Cancelled()
    dupeCollection = CenLib.DuplicateCollection(activeCollection)
    objects = CenLib.GetObjectsInCollection(dupeCollection)

    for obj in objects:
        CenLib.ConvertToMesh(obj)

    joined = CenLib.JoinObjects(objects)
    CenLib.SetOriginToWorldOrigin(joined)
    CenLib.ApplyScale(joined)
    CenLib.ApplyRotation(joined)

    settings = context.scene.cenexporter
    path = getattr(settings, path_property_name, "")

    if not path:
        CenLib.PopupError(
            f"No path set for {path_property_name.replace('_path', '').title()}"
        )
        return CenLib.Cancelled()

    directory = bpy.path.abspath(path)

    # Check if directory exists
    if not os.path.exists(directory):
        CenLib.PopupError(f"Directory does not exist: {directory}")
        return CenLib.Cancelled()

    joined.name = activeCollection.name + "-V_LOD0"
    filepath = os.path.join(directory, f"{activeCollection.name}.fbx")
    CenLib.ExportFbx(filepath, joined)

    CenLib.DeleteCollection(dupeCollection)

    CenLib.PopupPrint(f"Exported {activeCollection.name} as object!")
    CenLib.RestoreStateAfterExport(state)

    return CenLib.Finished()


def ExportCollectionAsUnifiedLodPair(path_property_name, context, lod1Density):
    startTime = time.time()
    state = CenLib.TransitionToExportableState()

    activeCollection, visualCollection, collisionCollection = Get_Active_Visual_Collision_Collections()
    if not visualCollection:
        CenLib.PopupError(f"Did not find a direct-child collection of {activeCollection.name} named Visual")
        return CenLib.Cancelled()

    # Visuals
    visualCollectionDupe = CenLib.DuplicateCollection(visualCollection)
    objects = CenLib.GetObjectsInCollection(visualCollectionDupe)

    for obj in objects:
        CenLib.ConvertToMesh(obj)

    joined = CenLib.JoinObjects(objects)
    CenLib.SetOriginToWorldOrigin(joined)
    CenLib.ApplyScale(joined)
    CenLib.ApplyRotation(joined)

    lod0 = joined
    lod1 = CenLib.DuplicateObject(lod0)

    decimateMod = CenLib.AddModifier(lod1, "Lod1Decimate", "DECIMATE")
    CenLib.SetModifierProperty(decimateMod, "ratio", lod1Density)

    lod0.name = activeCollection.name + "-V_LOD0"
    lod1.name = activeCollection.name + "-V_LOD1"

    ExportObject(path_property_name, context, lod0)
    ExportObject(path_property_name, context, lod1)

    CenLib.DeleteCollection(visualCollectionDupe)

    # Collision 
    if collisionCollection:
        collisionCollectionDupe = CenLib.DuplicateCollection(collisionCollection)
        allCollisionObjects = CenLib.GetObjectsInCollection(collisionCollectionDupe)

        for collision in allCollisionObjects:
            CenLib.ConvertToMesh(collision)

        joinedCollision = CenLib.JoinObjects(allCollisionObjects)
        CenLib.SetOriginToWorldOrigin(joinedCollision)
        CenLib.ApplyScale(joinedCollision)
        CenLib.ApplyRotation(joinedCollision)

        joinedCollision.name = activeCollection.name + "-C"
        ExportObject(path_property_name, context, joinedCollision)

        CenLib.DeleteCollection(collisionCollectionDupe)

    totalSeconds = time.time() - startTime
    CenLib.PopupPrint(
        f"Successfully exported the collection as a unified lod pair! It took {totalSeconds:.3f} seconds.")
    CenLib.RestoreStateAfterExport(state)

    return CenLib.Finished()


def ExportCollectionAsDisjointLodPairs(path_property_name, context, lod1Density):
    startTime = time.time()
    state = CenLib.TransitionToExportableState()

    activeCollection, visualCollection, collisionCollection = Get_Active_Visual_Collision_Collections()
    if not visualCollection:
        CenLib.PopupError(f"Did not find a direct-child collection of {activeCollection.name} named Visual")
        return CenLib.Cancelled()

    # Visuals 
    dupeCollection = CenLib.DuplicateCollection(visualCollection, "WORKING_DUPE_COLLECTION")
    baseName = activeCollection.name
    partIndex = 0
    for lod0 in CenLib.GetObjectsInCollection(dupeCollection):
        partIndex += 1
        lod0.name = f"{baseName}_Part{partIndex}-V_LOD0"
        CenLib.ConvertToMesh(lod0)

        CenLib.SetOriginToWorldOrigin(lod0)
        CenLib.ApplyRotation(lod0)
        CenLib.ApplyScale(lod0)

        lod1 = CenLib.DuplicateObject(lod0, False)
        lod1.name = f"{baseName}_Part{partIndex}-V_LOD1"
        decimateMod = CenLib.AddModifier(lod1, "Lod1Decimate", "DECIMATE")
        CenLib.SetModifierProperty(decimateMod, "ratio", lod1Density)

        ExportObject(path_property_name, context, lod0)
        ExportObject(path_property_name, context, lod1)

    CenLib.DeleteCollection(dupeCollection)

    # Collision
    if collisionCollection is not None:
        collisionIndex = 0
        for collisionObj in CenLib.GetObjectsInCollection(collisionCollection):
            collisionIndex += 1
            collisionDupe = CenLib.DuplicateObject(collisionObj)
            collisionName = f"{baseName}_CollisionPart{collisionIndex}-C"
            collisionDupe.name = collisionName
            CenLib.SetOriginToWorldOrigin(collisionDupe)
            CenLib.ApplyRotation(collisionDupe)
            CenLib.ApplyScale(collisionDupe)

            ExportObject(path_property_name, context, collisionDupe)
            CenLib.DeleteObject(collisionDupe)

    totalTime = time.time() - startTime
    CenLib.PopupPrint(
        f"Successfully exported {activeCollection.name} as a series of {partIndex} disjoint LOD pairs! It took {totalTime:.3f} seconds.")
    CenLib.RestoreStateAfterExport(state)
    return CenLib.Finished()


def ExportCollectionAsClusteredLodPairs(path_property_name, context, lod1Density, cellSize):
    return _ClusteredLodPairs(path_property_name, context, lod1Density, cellSize, False)


def SplitThenCollectionAsClusteredLodPairs(path_property_name, context, lod1Density, cellSize):
    return _ClusteredLodPairs(path_property_name, context, lod1Density, cellSize, True)
    
def _ClusteredLodPairs(path_property_name, context, lod1Density, cellSize, splitFirst):
    state = CenLib.TransitionToExportableState()
    startTime = time.time()
    activeCollection = CenLib.GetActiveCollection()

    if not activeCollection or activeCollection.name == "Scene Collection":
        CenLib.PopupError("Please select a valid collection first")
        return CenLib.Cancelled()

    workingCollection = CenLib.DuplicateCollection(activeCollection, False)
    workingCollection.name = "TEMPORARY_WORKING_COLLECTION"


    print(f"Duplicated into the working collection ({(time.time() - startTime):.3f} seconds")

    for obj in CenLib.GetObjectsInCollection(workingCollection):
        CenLib.ConvertToMesh(obj)
        if splitFirst:
            CenLib.SeparateLoose(obj)

    print(f"Converted the input objects to mesh ({(time.time() - startTime):.3f} seconds")
    CenLib.ClusterObjectsInInputCollection(workingCollection, cellSize)
    print(f"Clustered the working collection ({(time.time() - startTime):.3f} seconds")

    partIndex = 0
    clusters = CenLib.GetObjectsInCollection(workingCollection)
    for lod0 in clusters:
        partIndex += 1
        lod1 = CenLib.DuplicateObject(lod0, False)
        lod0.name = f"{activeCollection.name}Clustered_Part{partIndex}-V_LOD0"
        lod1.name = f"{activeCollection.name}Clustered_Part{partIndex}-V_LOD1"

        dec = CenLib.AddModifier(lod1, "lod1Decimate", 'DECIMATE')
        CenLib.SetModifierProperty(dec, 'ratio', lod1Density)

        CenLib.SetOriginToWorldOrigin(lod0)
        CenLib.SetOriginToWorldOrigin(lod1)
        CenLib.ApplyTransforms(lod0)
        CenLib.ApplyTransforms(lod1)

        ExportObject(path_property_name, context, lod0)
        ExportObject(path_property_name, context, lod1)
        print(f"Exported part {partIndex} of {len(clusters)} ({(time.time() - startTime):.3f} seconds")

    CenLib.DeleteCollection(workingCollection)

    elapsed = CenLib.RestoreStateAfterExport(state)
    CenLib.PopupPrint(f"Successfully exported {activeCollection.name} in {elapsed:.3f} seconds!")
    return CenLib.Finished()


def ExportObject(path_property_name, context, object):
    settings = context.scene.cenexporter
    path = getattr(settings, path_property_name, "")

    if not path:
        CenLib.PopupError(
            f"No path set for {path_property_name.replace('_path', '').title()}"
        )
        return CenLib.Cancelled()

    directory = bpy.path.abspath(path)

    # Check if directory exists
    if not os.path.exists(directory):
        CenLib.PopupError(f"Directory does not exist: {directory}")
        return CenLib.Cancelled()

    filepath = os.path.join(directory, f"{object.name}.fbx")
    CenLib.ExportFbx(filepath, object)
    return CenLib.Finished()


def GeneratePreviewOfCollection(path_property_name, context):
    activeCollection = CenLib.GetActiveCollection()
    if not activeCollection or activeCollection.name == "Scene Collection":
        CenLib.PopupError("Please select a valid collection first")
        return CenLib.Cancelled()


    workingCollection = CenLib.DuplicateCollection(activeCollection)
    workingObjects = CenLib.GetObjectsInCollection(workingCollection)
    for obj in workingObjects:
        CenLib.ConvertToMesh(obj)

    joined = CenLib.JoinObjects(workingObjects)


    previewObjectName = f"{activeCollection.name}-Preview"
    previewCollection = CenLib.GetOrCreateCollection("PREVIEWS")

    for obj in CenLib.GetObjectsInCollection(previewCollection):
        if obj.name == previewObjectName:
            CenLib.DeleteObject(obj)

    joined.name = previewObjectName
    CenLib.MoveToCollection(joined, previewCollection)
    CenLib.DeleteCollection(workingCollection)
    return CenLib.Finished()




# ---------- operators ----------
class CENEXPORTER_OT_export_path1(bpy.types.Operator):
    bl_idname = "cenexporter.export_path1"
    bl_label = "Export Collection to Path 1"
    bl_options = {"REGISTER"}

    def execute(self, context):
        return ExportToPath("path1", context, True)


class CENEXPORTER_OT_export_selection_path1(bpy.types.Operator):
    bl_idname = "cenexporter.export_selection_path1"
    bl_label = "Export Selection to Path 1"
    bl_options = {"REGISTER"}

    def execute(self, context):
        return ExportToPath("path1", context, False)


class CENEXPORTER_OT_export_collection_as_object1(bpy.types.Operator):
    bl_idname = "cenexporter.export_collection_as_object1"
    bl_label = "Export Collection as Object to Path 1"
    bl_options = {"REGISTER"}

    def execute(self, context):
        return ExportCollectionAsObject("path1", context)


class CENEXPORTER_OT_export_collection_as_lod_pair(bpy.types.Operator):
    bl_idname = "cenexporter.export_collection_as_lod_pair"
    bl_label = "Export Collection as LOD Pair"
    bl_options = {"REGISTER"}

    def execute(self, context):
        lod1Density = context.scene.cenexporter.lod1_density
        return ExportCollectionAsUnifiedLodPair("path1", context, lod1Density)


class CENEXPORTER_OT_export_collection_as_disjoint_lod_pairs(bpy.types.Operator):
    bl_idname = "cenexporter.export_collection_as_disjoint_lod_pairs"
    bl_label = "Export Collection as Disjoint LOD Pairs"
    bl_options = {"REGISTER"}

    def execute(self, context):
        lod1Density = context.scene.cenexporter.lod1_density
        return ExportCollectionAsDisjointLodPairs("path1", context, lod1Density)


class CENEXPORTER_OT_export_collection_as_clustered_lod_pairs(bpy.types.Operator):
    bl_idname = "cenexporter.export_collection_as_clustered_lod_pairs"
    bl_label = "Export Collection as Clustered LOD Pairs"
    bl_options = {"REGISTER"}

    def execute(self, context):
        lod1Density = context.scene.cenexporter.lod1_density
        cellSize = context.scene.cenexporter.cell_size
        return ExportCollectionAsClusteredLodPairs("path1", context, lod1Density, cellSize)


class CENEXPORTER_OT_split_then_collision_as_clustered_lod_pairs(bpy.types.Operator):
    bl_idname = "cenexporter.split_then_collision_as_clustered_lod_pairs"
    bl_label = "Split then Collection as Clustered LOD Pairs"
    bl_options = {"REGISTER"}

    def execute(self, context):
        lod1Density = context.scene.cenexporter.lod1_density
        cellSize = context.scene.cenexporter.cell_size
        return SplitThenCollectionAsClusteredLodPairs("path1", context, lod1Density, cellSize)


class CENEXPORTER_OT_generate_preview(bpy.types.Operator):
    bl_idname = "cenexporter.generate_preview"
    bl_label = "Generate Preview of Collection"
    bl_options = {"REGISTER"}

    def execute(self, context):
        return GeneratePreviewOfCollection("path1", context)


class CENEXPORTER_OT_pick_path1(bpy.types.Operator):
    bl_idname = "cenexporter.pick_path1"
    bl_label = "Choose Path 1"
    bl_options = {"REGISTER"}

    directory: StringProperty(subtype="DIR_PATH")

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        if self.directory:
            context.scene.cenexporter.path1 = self.directory
        return CenLib.Finished()


# ---------- properties ----------
class CENEXPORTER_PG_settings(PropertyGroup):
    path1: StringProperty(
        name="",
        description="Export directory 1",
        default="",
        subtype="NONE",
    )
    lod1_density: FloatProperty(
        name="LOD1 Density",
        description="Density value for LOD1 export",
        default=0.5,
        min=0.0,
        max=1.0,
        subtype="FACTOR",
    )
    cell_size: FloatProperty(
        name="Cell Size",
        description="Cell size used for clustered LOD pair export",
        default=25,
        min=0.0,
        subtype="DISTANCE",
    )


# ---------- UI panel ----------
class CENEXPORTER_PT_panel(bpy.types.Panel):
    bl_label = "CenExporter"
    bl_idname = "CENEXPORTER_PT_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Exports"

    def draw(self, context):
        layout = self.layout
        settings = context.scene.cenexporter

        # Display active collection and object info in a box
        active_layer = context.view_layer.active_layer_collection
        box = layout.box()
        if active_layer:
            col_name = active_layer.collection.name
            # Count mesh objects
            objects = CenLib.GetObjectsInCollection(CenLib.GetActiveCollection())

            # Determine object display name (active object or "Multiple")
            selected_objects = CenLib.GetSelectedObjects()
            mesh_selected = [obj for obj in selected_objects if obj.type == 'MESH']

            if len(mesh_selected) == 1:
                obj_name = mesh_selected[0].name
            elif len(mesh_selected) > 1:
                obj_name = "Multiple"
            else:
                obj_name = "None"

            box.label(
                text=f"Collection: {col_name}", icon="OUTLINER_COLLECTION"
            )
            box.label(text=f"Objects in Collection: {len(objects)}", icon="OBJECT_DATA")
            box.label(text=f"Active Object: {obj_name}", icon="OBJECT_DATA")
            box.label(text=f"Selected Objects: {len(mesh_selected)}", icon="SELECT_SET")
        else:
            box.label(text="Collection: <none>", icon="OUTLINER_COLLECTION")
            box.label(text="Object: None", icon="OBJECT_DATA")

        layout.separator()

        # Path 1
        row = layout.row(align=True)
        row.prop(settings, "path1", text="")
        row.operator("cenexporter.pick_path1", text="", icon="FILE_FOLDER")

        # Three buttons, each on its own full row
        layout.operator("cenexporter.export_selection_path1", text="Selection as Individual Objects", icon="SELECT_SET")
        layout.operator("cenexporter.export_path1", text="Collection as Individual Objects", icon="OUTLINER_COLLECTION")
        layout.operator("cenexporter.export_collection_as_object1", text="Collection as Single Object",
                        icon="OUTLINER_COLLECTION")

        layout.separator()

        # LOD1 Density field
        layout.prop(settings, "lod1_density", text="LOD1 Density")

        # Collection as LOD Pair button
        layout.operator("cenexporter.export_collection_as_lod_pair", text="Collection as Unified LOD Pair",
                        icon="OUTLINER_COLLECTION")

        # Collection as Disjoint LOD Pairs button
        layout.operator("cenexporter.export_collection_as_disjoint_lod_pairs", text="Collection as Disjoint LOD Pairs",
                        icon="OUTLINER_COLLECTION")

        layout.separator()

        # Cell Size field
        layout.prop(settings, "cell_size", text="Cell Size")

        # Collection as Clustered LOD Pairs button
        layout.operator("cenexporter.export_collection_as_clustered_lod_pairs",
                        text="Collection as Clustered LOD Pairs",
                        icon="OUTLINER_COLLECTION")

        # Split then Collision as Clustered LOD Pairs button
        layout.operator("cenexporter.split_then_collision_as_clustered_lod_pairs",
                        text="Split then Collision as Clustered LOD Pairs",
                        icon="OUTLINER_COLLECTION")

        layout.separator()

        # Generate Preview of Collection button
        layout.operator("cenexporter.generate_preview",
                        text="Generate Preview of Collection",
                        icon="RESTRICT_VIEW_OFF")


# ---------- registration ----------
classes = (
    CENEXPORTER_PG_settings,
    CENEXPORTER_OT_export_path1,
    CENEXPORTER_OT_export_selection_path1,
    CENEXPORTER_OT_export_collection_as_object1,
    CENEXPORTER_OT_export_collection_as_lod_pair,
    CENEXPORTER_OT_export_collection_as_disjoint_lod_pairs,
    CENEXPORTER_OT_export_collection_as_clustered_lod_pairs,
    CENEXPORTER_OT_split_then_collision_as_clustered_lod_pairs,
    CENEXPORTER_OT_generate_preview,
    CENEXPORTER_OT_pick_path1,
    CENEXPORTER_PT_panel,
)


def register():
    for c in classes:
        bpy.utils.register_class(c)
    bpy.types.Scene.cenexporter = PointerProperty(type=CENEXPORTER_PG_settings)


def unregister():
    del bpy.types.Scene.cenexporter
    for c in reversed(classes):
        bpy.utils.unregister_class(c)


if __name__ == "__main__":
    register()
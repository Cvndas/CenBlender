bl_info = {
    "name": "CenLevelExport",
    "author": "Lrodas",
    "version": (1, 0, 0),
    "blender": (4, 0, 0),
    "location": "3D Viewport > Sidebar (N) > Level Export",
    "description": "Export multiple collections as single FBX files with one click",
    "category": "Import-Export",
}

import bpy
import os
import CenLib
import time
from bpy.props import StringProperty, PointerProperty, IntProperty, CollectionProperty
from bpy.types import PropertyGroup, Operator, Panel




def ExportCollectionToFBX(collectionName, filepath):
    """Export a collection as a single FBX file"""
    collection = CenLib.GetCollectionByName(collectionName)
    if not collection:
        CenLib.PopupError(f"Collection '{collectionName}' not found!")
        return False
    
    objectsInCollection = CenLib.GetObjectsInCollection(collection)
    if not objectsInCollection:
        CenLib.PopupError(f"No mesh objects found in collection '{collectionName}'")
        return False
    
    prevSelected = CenLib.GetSelectedObjects()
    prevActive = CenLib.GetActiveObject()
    
    try:
        CenLib.ClearSelection()
        for obj in objectsInCollection:
            CenLib.SelectObject(obj)
        
        bpy.ops.export_scene.fbx(
            filepath=filepath,
            use_selection=True,
            use_visible=True,
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
        CenLib.PopupError(f"Export failed for {collectionName}: {str(e)}")
        return False
        
    finally:
        CenLib.ClearSelection()
        for obj in prevSelected:
            if (CenLib.ObjectExists(obj)):
                CenLib.SelectObject(obj)

        if CenLib.ObjectExists(prevActive):
            CenLib.SelectObject(prevActive)


def ExportSingleSlot(collectionName, filepath):
    if not collectionName or not filepath:
        CenLib.PopupError("Both collection name and file path must be set!")
        return False
    
    absolutePath = bpy.path.abspath(filepath)
    
    directory = os.path.dirname(absolutePath)
    if directory and not os.path.exists(directory):
        CenLib.PopupError(f"Directory does not exist: {directory}")
        return False
    
    return ExportCollectionToFBX(collectionName, absolutePath)


def ExportAllSlots(context):
    """Export all configured slots"""
    T_start = time.time()
    settings = context.scene.cenlevelexport
    
    successCount = 0
    total = 0
    
    for slot in settings.slots:
        if not slot.collection_name or not slot.filepath:
            continue
        
        total += 1
        absolutePath = bpy.path.abspath(slot.filepath)
        
        directory = os.path.dirname(absolutePath)
        if directory and not os.path.exists(directory):
            CenLib.PopupError(f"Directory does not exist: {directory}")
            continue
        
        if ExportCollectionToFBX(slot.collection_name, absolutePath):
            successCount += 1
    
    if total == 0:
        CenLib.PopupError("No slots configured with both collection name and file path!")
        return CenLib.Cancelled()
    
    if successCount == total:
        CenLib.PopupPrint(f"Successfully exported all {successCount} collections! It took {round(time.time() - T_start)} seconds.")
    else:
        CenLib.PopupPrint(f"Exported {successCount} of {total} collections. Check error messages for details.")
    
    return CenLib.Finished()


# ---------- properties ----------
class CENLEVELEXPORT_SlotItem(PropertyGroup):
    collection_name: StringProperty(
        name="",
        description="Collection name to export",
        default="",
    )
    filepath: StringProperty(
        name="",
        description="Output file path (FBX)",
        default="",
        subtype="FILE_PATH",
    )


class CENLEVELEXPORT_PG_settings(PropertyGroup):
    slots: CollectionProperty(type=CENLEVELEXPORT_SlotItem)


# ---------- operators ----------
class CENLEVELEXPORT_OT_export_all(bpy.types.Operator):
    bl_idname = "cenlevelexport.export_all"
    bl_label = "Export All Slots"
    bl_description = "Export all configured collections"
    bl_options = {"REGISTER"}
    
    def execute(self, context):
        return ExportAllSlots(context)


class CENLEVELEXPORT_OT_export_slot(bpy.types.Operator):
    bl_idname = "cenlevelexport.export_slot"
    bl_label = "Export"
    bl_description = "Export this collection"
    bl_options = {"REGISTER"}
    
    index: IntProperty()
    
    def execute(self, context):
        settings = context.scene.cenlevelexport
        slot = settings.slots[self.index]
        T_start = time.time()
        if ExportSingleSlot(slot.collection_name, slot.filepath):
            CenLib.PopupPrint(f"Successfully exported '{slot.collection_name}'! It took {round(time.time() - T_start)} seconds")
        return CenLib.Finished()


class CENLEVELEXPORT_OT_add_slot(bpy.types.Operator):
    bl_idname = "cenlevelexport.add_slot"
    bl_label = "Add Slot"
    bl_description = "Add a new export slot"
    bl_options = {"REGISTER", "UNDO"}
    
    def execute(self, context):
        settings = context.scene.cenlevelexport
        settings.slots.add()
        return CenLib.Finished()


class CENLEVELEXPORT_OT_remove_slot(bpy.types.Operator):
    bl_idname = "cenlevelexport.remove_slot"
    bl_label = "Remove Slot"
    bl_description = "Remove the last export slot"
    bl_options = {"REGISTER", "UNDO"}
    
    def execute(self, context):
        settings = context.scene.cenlevelexport
        if len(settings.slots) > 0:
            settings.slots.remove(len(settings.slots) - 1)
        return CenLib.Finished()


# ---------- UI panel ----------
class CENLEVELEXPORT_PT_panel(bpy.types.Panel):
    bl_label = "CenLevelExport"
    bl_idname = "CENLEVELEXPORT_PT_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Level Export"
    
    def draw(self, context):
        layout = self.layout
        settings = context.scene.cenlevelexport
        
        # Export All button
        layout.operator("cenlevelexport.export_all", icon="EXPORT")
        
        # Add/Remove buttons
        row = layout.row(align=True)
        row.operator("cenlevelexport.add_slot", icon="ADD")
        row.operator("cenlevelexport.remove_slot", icon="REMOVE")
        
        layout.separator()
        
        # Scrollable area with a box for each slot
        col = layout.column(align=True)
        
        # Only show up to 20 slots at a time to avoid UI overload
        visibleSlots = min(len(settings.slots), 20)
        
        for i in range(visibleSlots):
            slot = settings.slots[i]
            
            box = col.box()
            
            # Collection name row
            row = box.row(align=True)
            row.prop(slot, "collection_name", text="")
            
            # File path row with folder picker built-in
            row = box.row(align=True)
            row.prop(slot, "filepath", text="")
            
            # Export button row
            row = box.row(align=True)
            op = row.operator("cenlevelexport.export_slot", text="Export", icon="EXPORT")
            op.index = i
        
        # Show message if no slots
        if len(settings.slots) == 0:
            box = col.box()
            box.label(text="No slots configured. Add one with the + button.", icon="INFO")


# ---------- registration ----------
classes = [
    CENLEVELEXPORT_SlotItem,
    CENLEVELEXPORT_PG_settings,
    CENLEVELEXPORT_OT_export_all,
    CENLEVELEXPORT_OT_export_slot,
    CENLEVELEXPORT_OT_add_slot,
    CENLEVELEXPORT_OT_remove_slot,
    CENLEVELEXPORT_PT_panel,
]


def register():
    for c in classes:
        bpy.utils.register_class(c)
    bpy.types.Scene.cenlevelexport = PointerProperty(type=CENLEVELEXPORT_PG_settings)


def unregister():
    del bpy.types.Scene.cenlevelexport
    for c in reversed(classes):
        bpy.utils.unregister_class(c)


if __name__ == "__main__":
    register()

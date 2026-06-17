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
from bpy.props import StringProperty, PointerProperty, IntProperty, CollectionProperty
from bpy.types import PropertyGroup, Operator, Panel

NUM_SLOTS = 35


# ---------- helpers ----------
def popup_error(msg):
    def draw(self, _):
        self.layout.label(text=msg)
    bpy.context.window_manager.popup_menu(draw, title="CenLevelExport Error!", icon="ERROR")


def popup_info(msg):
    def draw(self, _):
        self.layout.label(text=msg)
    bpy.context.window_manager.popup_menu(draw, title="CenLevelExport", icon="INFO")


def get_objects_from_collection(collection):
    """Recursively get all mesh objects from a collection"""
    objects = []
    if not collection:
        return objects
    
    for obj in collection.objects:
        if obj.type == "MESH":
            objects.append(obj)
    
    for child_collection in collection.children:
        objects.extend(get_objects_from_collection(child_collection))
    
    return objects


def export_collection_to_fbx(collection_name, filepath):
    """Export a collection as a single FBX file"""
    collection = bpy.data.collections.get(collection_name)
    if not collection:
        popup_error(f"Collection '{collection_name}' not found!")
        return False
    
    objects = get_objects_from_collection(collection)
    if not objects:
        popup_error(f"No mesh objects found in collection '{collection_name}'")
        return False
    
    prev_selected = [obj for obj in bpy.context.selected_objects]
    prev_active = bpy.context.view_layer.objects.active
    
    hide_states = {}
    all_objects = []
    
    def collect_and_unhide_recursive(col):
        for obj in col.objects:
            if obj.type == "MESH":
                all_objects.append(obj)
                hide_states[obj] = obj.hide_get()
                obj.hide_set(False)
        for child in col.children:
            collect_and_unhide_recursive(child)
    
    try:
        collect_and_unhide_recursive(collection)
        
        bpy.ops.object.select_all(action="DESELECT")
        for obj in all_objects:
            obj.select_set(True)
        
        if all_objects:
            bpy.context.view_layer.objects.active = all_objects[0]
        
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
        popup_error(f"Export failed for {collection_name}: {str(e)}")
        return False
        
    finally:
        for obj, was_hidden in hide_states.items():
            if obj.name in bpy.data.objects:
                obj.hide_set(was_hidden)
        
        bpy.ops.object.select_all(action="DESELECT")
        for obj in prev_selected:
            if obj.name in bpy.data.objects:
                obj.select_set(True)
        if prev_active and prev_active.name in bpy.data.objects:
            bpy.context.view_layer.objects.active = prev_active


def export_single_slot(collection_name, filepath):
    """Export a single slot"""
    if not collection_name or not filepath:
        popup_error("Both collection name and file path must be set!")
        return False
    
    absolute_path = bpy.path.abspath(filepath)
    
    directory = os.path.dirname(absolute_path)
    if directory and not os.path.exists(directory):
        popup_error(f"Directory does not exist: {directory}")
        return False
    
    return export_collection_to_fbx(collection_name, absolute_path)


def export_all_slots(context):
    """Export all configured slots"""
    settings = context.scene.cenlevelexport
    
    success_count = 0
    total = 0
    
    for slot in settings.slots:
        if not slot.collection_name or not slot.filepath:
            continue
        
        total += 1
        absolute_path = bpy.path.abspath(slot.filepath)
        
        directory = os.path.dirname(absolute_path)
        if directory and not os.path.exists(directory):
            popup_error(f"Directory does not exist: {directory}")
            continue
        
        if export_collection_to_fbx(slot.collection_name, absolute_path):
            success_count += 1
    
    if total == 0:
        popup_error("No slots configured with both collection name and file path!")
        return {"CANCELLED"}
    
    if success_count == total:
        popup_info(f"Successfully exported all {success_count} collections!")
    else:
        popup_info(f"Exported {success_count} of {total} collections. Check error messages for details.")
    
    return {"FINISHED"}


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
    active_index: IntProperty(default=0)
    scroll_offset: IntProperty(default=0)


# ---------- operators ----------
class CENLEVELEXPORT_OT_export_all(bpy.types.Operator):
    bl_idname = "cenlevelexport.export_all"
    bl_label = "Export All Slots"
    bl_description = "Export all configured collections"
    bl_options = {"REGISTER"}
    
    def execute(self, context):
        return export_all_slots(context)


class CENLEVELEXPORT_OT_export_slot(bpy.types.Operator):
    bl_idname = "cenlevelexport.export_slot"
    bl_label = "Export"
    bl_description = "Export this collection"
    bl_options = {"REGISTER"}
    
    index: IntProperty()
    
    def execute(self, context):
        settings = context.scene.cenlevelexport
        slot = settings.slots[self.index]
        if export_single_slot(slot.collection_name, slot.filepath):
            popup_info(f"Successfully exported '{slot.collection_name}'!")
        return {"FINISHED"}


class CENLEVELEXPORT_OT_add_slot(bpy.types.Operator):
    bl_idname = "cenlevelexport.add_slot"
    bl_label = "Add Slot"
    bl_description = "Add a new export slot"
    bl_options = {"REGISTER", "UNDO"}
    
    def execute(self, context):
        settings = context.scene.cenlevelexport
        settings.slots.add()
        return {"FINISHED"}


class CENLEVELEXPORT_OT_remove_slot(bpy.types.Operator):
    bl_idname = "cenlevelexport.remove_slot"
    bl_label = "Remove Slot"
    bl_description = "Remove the last export slot"
    bl_options = {"REGISTER", "UNDO"}
    
    def execute(self, context):
        settings = context.scene.cenlevelexport
        if len(settings.slots) > 0:
            settings.slots.remove(len(settings.slots) - 1)
        return {"FINISHED"}


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
        visible_slots = min(len(settings.slots), 20)
        
        for i in range(visible_slots):
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
    
    # Add default slots
    settings = bpy.context.scene.cenlevelexport
    if len(settings.slots) == 0:
        for _ in range(NUM_SLOTS):
            settings.slots.add()


def unregister():
    del bpy.types.Scene.cenlevelexport
    for c in reversed(classes):
        bpy.utils.unregister_class(c)


if __name__ == "__main__":
    register()

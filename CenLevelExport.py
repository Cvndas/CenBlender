# Vibe coded by deepseek. I don't believe blender has such a thing as an Array
# like how Unity's editor tools work. Therefore, all the entries are hardcoded.
# An AI should be able to add more slots in case it is ever necessary.

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
from bpy.props import StringProperty, PointerProperty
from bpy.types import PropertyGroup, Operator, Panel


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
    # Find the collection
    collection = bpy.data.collections.get(collection_name)
    if not collection:
        popup_error(f"Collection '{collection_name}' not found!")
        return False
    
    # Get all mesh objects in the collection
    objects = get_objects_from_collection(collection)
    if not objects:
        popup_error(f"No mesh objects found in collection '{collection_name}'")
        return False
    
    # Store current selection state
    prev_selected = [obj for obj in bpy.context.selected_objects]
    prev_active = bpy.context.view_layer.objects.active
    
    # Store all objects' hide states
    hide_states = {}
    all_objects = []
    
    # We need to unhide objects in the collection so they export properly
    def collect_and_unhide_recursive(col):
        for obj in col.objects:
            if obj.type == "MESH":
                all_objects.append(obj)
                hide_states[obj] = obj.hide_get()
                obj.hide_set(False)
        for child in col.children:
            collect_and_unhide_recursive(child)
    
    try:
        # Unhide all objects in the collection
        collect_and_unhide_recursive(collection)
        
        # Select all objects in the collection
        bpy.ops.object.select_all(action="DESELECT")
        for obj in all_objects:
            obj.select_set(True)
        
        if all_objects:
            bpy.context.view_layer.objects.active = all_objects[0]
        
        # Export as single FBX
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
        # Restore hide states
        for obj, was_hidden in hide_states.items():
            if obj.name in bpy.data.objects:
                obj.hide_set(was_hidden)
        
        # Restore selection state
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
    
    # Check if directory exists
    directory = os.path.dirname(absolute_path)
    if directory and not os.path.exists(directory):
        popup_error(f"Directory does not exist: {directory}")
        return False
    
    # Export
    return export_collection_to_fbx(collection_name, absolute_path)


def export_all_slots(context):
    """Export all configured slots"""
    settings = context.scene.cenlevelexport
    
    slots = [
        (settings.collection1, settings.path1),
        (settings.collection2, settings.path2),
        (settings.collection3, settings.path3),
        (settings.collection4, settings.path4),
        (settings.collection5, settings.path5),
        (settings.collection6, settings.path6),
        (settings.collection7, settings.path7),
        (settings.collection8, settings.path8),
        (settings.collection9, settings.path9),
        (settings.collection10, settings.path10),
        (settings.collection11, settings.path11),
        (settings.collection12, settings.path12),
        (settings.collection13, settings.path13),
        (settings.collection14, settings.path14),
        (settings.collection15, settings.path15),
        (settings.collection16, settings.path16),
        (settings.collection17, settings.path17),
        (settings.collection18, settings.path18),
        (settings.collection19, settings.path19),
        (settings.collection20, settings.path20),
        (settings.collection21, settings.path21),
        (settings.collection22, settings.path22),
        (settings.collection23, settings.path23),
        (settings.collection24, settings.path24),
        (settings.collection25, settings.path25),
        (settings.collection26, settings.path26),
        (settings.collection27, settings.path27),
        (settings.collection28, settings.path28),
        (settings.collection29, settings.path29),
        (settings.collection30, settings.path30),
        (settings.collection31, settings.path31),
        (settings.collection32, settings.path32),
        (settings.collection33, settings.path33),
        (settings.collection34, settings.path34),
        (settings.collection35, settings.path35),
    ]
    
    success_count = 0
    total = 0
    
    for collection_name, filepath in slots:
        if not collection_name or not filepath:
            continue
        
        total += 1
        absolute_path = bpy.path.abspath(filepath)
        
        # Check if directory exists
        directory = os.path.dirname(absolute_path)
        if directory and not os.path.exists(directory):
            popup_error(f"Directory does not exist: {directory}")
            continue
        
        # Export
        if export_collection_to_fbx(collection_name, absolute_path):
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
class CENLEVELEXPORT_PG_settings(PropertyGroup):
    # 35 collection name slots
    collection1: StringProperty(
        name="",
        description="Collection name to export",
        default="",
    )
    collection2: StringProperty(
        name="",
        description="Collection name to export",
        default="",
    )
    collection3: StringProperty(
        name="",
        description="Collection name to export",
        default="",
    )
    collection4: StringProperty(
        name="",
        description="Collection name to export",
        default="",
    )
    collection5: StringProperty(
        name="",
        description="Collection name to export",
        default="",
    )
    collection6: StringProperty(
        name="",
        description="Collection name to export",
        default="",
    )
    collection7: StringProperty(
        name="",
        description="Collection name to export",
        default="",
    )
    collection8: StringProperty(
        name="",
        description="Collection name to export",
        default="",
    )
    collection9: StringProperty(
        name="",
        description="Collection name to export",
        default="",
    )
    collection10: StringProperty(
        name="",
        description="Collection name to export",
        default="",
    )
    collection11: StringProperty(
        name="",
        description="Collection name to export",
        default="",
    )
    collection12: StringProperty(
        name="",
        description="Collection name to export",
        default="",
    )
    collection13: StringProperty(
        name="",
        description="Collection name to export",
        default="",
    )
    collection14: StringProperty(
        name="",
        description="Collection name to export",
        default="",
    )
    collection15: StringProperty(
        name="",
        description="Collection name to export",
        default="",
    )
    collection16: StringProperty(
        name="",
        description="Collection name to export",
        default="",
    )
    collection17: StringProperty(
        name="",
        description="Collection name to export",
        default="",
    )
    collection18: StringProperty(
        name="",
        description="Collection name to export",
        default="",
    )
    collection19: StringProperty(
        name="",
        description="Collection name to export",
        default="",
    )
    collection20: StringProperty(
        name="",
        description="Collection name to export",
        default="",
    )
    collection21: StringProperty(
        name="",
        description="Collection name to export",
        default="",
    )
    collection22: StringProperty(
        name="",
        description="Collection name to export",
        default="",
    )
    collection23: StringProperty(
        name="",
        description="Collection name to export",
        default="",
    )
    collection24: StringProperty(
        name="",
        description="Collection name to export",
        default="",
    )
    collection25: StringProperty(
        name="",
        description="Collection name to export",
        default="",
    )
    collection26: StringProperty(
        name="",
        description="Collection name to export",
        default="",
    )
    collection27: StringProperty(
        name="",
        description="Collection name to export",
        default="",
    )
    collection28: StringProperty(
        name="",
        description="Collection name to export",
        default="",
    )
    collection29: StringProperty(
        name="",
        description="Collection name to export",
        default="",
    )
    collection30: StringProperty(
        name="",
        description="Collection name to export",
        default="",
    )
    collection31: StringProperty(
        name="",
        description="Collection name to export",
        default="",
    )
    collection32: StringProperty(
        name="",
        description="Collection name to export",
        default="",
    )
    collection33: StringProperty(
        name="",
        description="Collection name to export",
        default="",
    )
    collection34: StringProperty(
        name="",
        description="Collection name to export",
        default="",
    )
    collection35: StringProperty(
        name="",
        description="Collection name to export",
        default="",
    )
    
    # 35 output file paths
    path1: StringProperty(
        name="",
        description="Output file path (FBX)",
        default="",
        subtype="NONE",
    )
    path2: StringProperty(
        name="",
        description="Output file path (FBX)",
        default="",
        subtype="NONE",
    )
    path3: StringProperty(
        name="",
        description="Output file path (FBX)",
        default="",
        subtype="NONE",
    )
    path4: StringProperty(
        name="",
        description="Output file path (FBX)",
        default="",
        subtype="NONE",
    )
    path5: StringProperty(
        name="",
        description="Output file path (FBX)",
        default="",
        subtype="NONE",
    )
    path6: StringProperty(
        name="",
        description="Output file path (FBX)",
        default="",
        subtype="NONE",
    )
    path7: StringProperty(
        name="",
        description="Output file path (FBX)",
        default="",
        subtype="NONE",
    )
    path8: StringProperty(
        name="",
        description="Output file path (FBX)",
        default="",
        subtype="NONE",
    )
    path9: StringProperty(
        name="",
        description="Output file path (FBX)",
        default="",
        subtype="NONE",
    )
    path10: StringProperty(
        name="",
        description="Output file path (FBX)",
        default="",
        subtype="NONE",
    )
    path11: StringProperty(
        name="",
        description="Output file path (FBX)",
        default="",
        subtype="NONE",
    )
    path12: StringProperty(
        name="",
        description="Output file path (FBX)",
        default="",
        subtype="NONE",
    )
    path13: StringProperty(
        name="",
        description="Output file path (FBX)",
        default="",
        subtype="NONE",
    )
    path14: StringProperty(
        name="",
        description="Output file path (FBX)",
        default="",
        subtype="NONE",
    )
    path15: StringProperty(
        name="",
        description="Output file path (FBX)",
        default="",
        subtype="NONE",
    )
    path16: StringProperty(
        name="",
        description="Output file path (FBX)",
        default="",
        subtype="NONE",
    )
    path17: StringProperty(
        name="",
        description="Output file path (FBX)",
        default="",
        subtype="NONE",
    )
    path18: StringProperty(
        name="",
        description="Output file path (FBX)",
        default="",
        subtype="NONE",
    )
    path19: StringProperty(
        name="",
        description="Output file path (FBX)",
        default="",
        subtype="NONE",
    )
    path20: StringProperty(
        name="",
        description="Output file path (FBX)",
        default="",
        subtype="NONE",
    )
    path21: StringProperty(
        name="",
        description="Output file path (FBX)",
        default="",
        subtype="NONE",
    )
    path22: StringProperty(
        name="",
        description="Output file path (FBX)",
        default="",
        subtype="NONE",
    )
    path23: StringProperty(
        name="",
        description="Output file path (FBX)",
        default="",
        subtype="NONE",
    )
    path24: StringProperty(
        name="",
        description="Output file path (FBX)",
        default="",
        subtype="NONE",
    )
    path25: StringProperty(
        name="",
        description="Output file path (FBX)",
        default="",
        subtype="NONE",
    )
    path26: StringProperty(
        name="",
        description="Output file path (FBX)",
        default="",
        subtype="NONE",
    )
    path27: StringProperty(
        name="",
        description="Output file path (FBX)",
        default="",
        subtype="NONE",
    )
    path28: StringProperty(
        name="",
        description="Output file path (FBX)",
        default="",
        subtype="NONE",
    )
    path29: StringProperty(
        name="",
        description="Output file path (FBX)",
        default="",
        subtype="NONE",
    )
    path30: StringProperty(
        name="",
        description="Output file path (FBX)",
        default="",
        subtype="NONE",
    )
    path31: StringProperty(
        name="",
        description="Output file path (FBX)",
        default="",
        subtype="NONE",
    )
    path32: StringProperty(
        name="",
        description="Output file path (FBX)",
        default="",
        subtype="NONE",
    )
    path33: StringProperty(
        name="",
        description="Output file path (FBX)",
        default="",
        subtype="NONE",
    )
    path34: StringProperty(
        name="",
        description="Output file path (FBX)",
        default="",
        subtype="NONE",
    )
    path35: StringProperty(
        name="",
        description="Output file path (FBX)",
        default="",
        subtype="NONE",
    )


# ---------- operators ----------
class CENLEVELEXPORT_OT_export_all(bpy.types.Operator):
    bl_idname = "cenlevelexport.export_all"
    bl_label = "Export All Slots"
    bl_description = "Export all configured collections"
    bl_options = {"REGISTER"}
    
    def execute(self, context):
        return export_all_slots(context)


class CENLEVELEXPORT_OT_export_slot1(bpy.types.Operator):
    bl_idname = "cenlevelexport.export_slot1"
    bl_label = "Export"
    bl_description = "Export this collection"
    bl_options = {"REGISTER"}
    
    def execute(self, context):
        settings = context.scene.cenlevelexport
        if export_single_slot(settings.collection1, settings.path1):
            popup_info(f"Successfully exported '{settings.collection1}'!")
        return {"FINISHED"}


class CENLEVELEXPORT_OT_export_slot2(bpy.types.Operator):
    bl_idname = "cenlevelexport.export_slot2"
    bl_label = "Export"
    bl_description = "Export this collection"
    bl_options = {"REGISTER"}
    
    def execute(self, context):
        settings = context.scene.cenlevelexport
        if export_single_slot(settings.collection2, settings.path2):
            popup_info(f"Successfully exported '{settings.collection2}'!")
        return {"FINISHED"}


class CENLEVELEXPORT_OT_export_slot3(bpy.types.Operator):
    bl_idname = "cenlevelexport.export_slot3"
    bl_label = "Export"
    bl_description = "Export this collection"
    bl_options = {"REGISTER"}
    
    def execute(self, context):
        settings = context.scene.cenlevelexport
        if export_single_slot(settings.collection3, settings.path3):
            popup_info(f"Successfully exported '{settings.collection3}'!")
        return {"FINISHED"}


class CENLEVELEXPORT_OT_export_slot4(bpy.types.Operator):
    bl_idname = "cenlevelexport.export_slot4"
    bl_label = "Export"
    bl_description = "Export this collection"
    bl_options = {"REGISTER"}
    
    def execute(self, context):
        settings = context.scene.cenlevelexport
        if export_single_slot(settings.collection4, settings.path4):
            popup_info(f"Successfully exported '{settings.collection4}'!")
        return {"FINISHED"}


class CENLEVELEXPORT_OT_export_slot5(bpy.types.Operator):
    bl_idname = "cenlevelexport.export_slot5"
    bl_label = "Export"
    bl_description = "Export this collection"
    bl_options = {"REGISTER"}
    
    def execute(self, context):
        settings = context.scene.cenlevelexport
        if export_single_slot(settings.collection5, settings.path5):
            popup_info(f"Successfully exported '{settings.collection5}'!")
        return {"FINISHED"}


class CENLEVELEXPORT_OT_export_slot6(bpy.types.Operator):
    bl_idname = "cenlevelexport.export_slot6"
    bl_label = "Export"
    bl_description = "Export this collection"
    bl_options = {"REGISTER"}
    
    def execute(self, context):
        settings = context.scene.cenlevelexport
        if export_single_slot(settings.collection6, settings.path6):
            popup_info(f"Successfully exported '{settings.collection6}'!")
        return {"FINISHED"}


class CENLEVELEXPORT_OT_export_slot7(bpy.types.Operator):
    bl_idname = "cenlevelexport.export_slot7"
    bl_label = "Export"
    bl_description = "Export this collection"
    bl_options = {"REGISTER"}
    
    def execute(self, context):
        settings = context.scene.cenlevelexport
        if export_single_slot(settings.collection7, settings.path7):
            popup_info(f"Successfully exported '{settings.collection7}'!")
        return {"FINISHED"}


class CENLEVELEXPORT_OT_export_slot8(bpy.types.Operator):
    bl_idname = "cenlevelexport.export_slot8"
    bl_label = "Export"
    bl_description = "Export this collection"
    bl_options = {"REGISTER"}
    
    def execute(self, context):
        settings = context.scene.cenlevelexport
        if export_single_slot(settings.collection8, settings.path8):
            popup_info(f"Successfully exported '{settings.collection8}'!")
        return {"FINISHED"}


class CENLEVELEXPORT_OT_export_slot9(bpy.types.Operator):
    bl_idname = "cenlevelexport.export_slot9"
    bl_label = "Export"
    bl_description = "Export this collection"
    bl_options = {"REGISTER"}
    
    def execute(self, context):
        settings = context.scene.cenlevelexport
        if export_single_slot(settings.collection9, settings.path9):
            popup_info(f"Successfully exported '{settings.collection9}'!")
        return {"FINISHED"}


class CENLEVELEXPORT_OT_export_slot10(bpy.types.Operator):
    bl_idname = "cenlevelexport.export_slot10"
    bl_label = "Export"
    bl_description = "Export this collection"
    bl_options = {"REGISTER"}
    
    def execute(self, context):
        settings = context.scene.cenlevelexport
        if export_single_slot(settings.collection10, settings.path10):
            popup_info(f"Successfully exported '{settings.collection10}'!")
        return {"FINISHED"}


class CENLEVELEXPORT_OT_export_slot11(bpy.types.Operator):
    bl_idname = "cenlevelexport.export_slot11"
    bl_label = "Export"
    bl_description = "Export this collection"
    bl_options = {"REGISTER"}
    
    def execute(self, context):
        settings = context.scene.cenlevelexport
        if export_single_slot(settings.collection11, settings.path11):
            popup_info(f"Successfully exported '{settings.collection11}'!")
        return {"FINISHED"}


class CENLEVELEXPORT_OT_export_slot12(bpy.types.Operator):
    bl_idname = "cenlevelexport.export_slot12"
    bl_label = "Export"
    bl_description = "Export this collection"
    bl_options = {"REGISTER"}
    
    def execute(self, context):
        settings = context.scene.cenlevelexport
        if export_single_slot(settings.collection12, settings.path12):
            popup_info(f"Successfully exported '{settings.collection12}'!")
        return {"FINISHED"}


class CENLEVELEXPORT_OT_export_slot13(bpy.types.Operator):
    bl_idname = "cenlevelexport.export_slot13"
    bl_label = "Export"
    bl_description = "Export this collection"
    bl_options = {"REGISTER"}
    
    def execute(self, context):
        settings = context.scene.cenlevelexport
        if export_single_slot(settings.collection13, settings.path13):
            popup_info(f"Successfully exported '{settings.collection13}'!")
        return {"FINISHED"}


class CENLEVELEXPORT_OT_export_slot14(bpy.types.Operator):
    bl_idname = "cenlevelexport.export_slot14"
    bl_label = "Export"
    bl_description = "Export this collection"
    bl_options = {"REGISTER"}
    
    def execute(self, context):
        settings = context.scene.cenlevelexport
        if export_single_slot(settings.collection14, settings.path14):
            popup_info(f"Successfully exported '{settings.collection14}'!")
        return {"FINISHED"}


class CENLEVELEXPORT_OT_export_slot15(bpy.types.Operator):
    bl_idname = "cenlevelexport.export_slot15"
    bl_label = "Export"
    bl_description = "Export this collection"
    bl_options = {"REGISTER"}
    
    def execute(self, context):
        settings = context.scene.cenlevelexport
        if export_single_slot(settings.collection15, settings.path15):
            popup_info(f"Successfully exported '{settings.collection15}'!")
        return {"FINISHED"}


class CENLEVELEXPORT_OT_export_slot16(bpy.types.Operator):
    bl_idname = "cenlevelexport.export_slot16"
    bl_label = "Export"
    bl_description = "Export this collection"
    bl_options = {"REGISTER"}
    
    def execute(self, context):
        settings = context.scene.cenlevelexport
        if export_single_slot(settings.collection16, settings.path16):
            popup_info(f"Successfully exported '{settings.collection16}'!")
        return {"FINISHED"}


class CENLEVELEXPORT_OT_export_slot17(bpy.types.Operator):
    bl_idname = "cenlevelexport.export_slot17"
    bl_label = "Export"
    bl_description = "Export this collection"
    bl_options = {"REGISTER"}
    
    def execute(self, context):
        settings = context.scene.cenlevelexport
        if export_single_slot(settings.collection17, settings.path17):
            popup_info(f"Successfully exported '{settings.collection17}'!")
        return {"FINISHED"}


class CENLEVELEXPORT_OT_export_slot18(bpy.types.Operator):
    bl_idname = "cenlevelexport.export_slot18"
    bl_label = "Export"
    bl_description = "Export this collection"
    bl_options = {"REGISTER"}
    
    def execute(self, context):
        settings = context.scene.cenlevelexport
        if export_single_slot(settings.collection18, settings.path18):
            popup_info(f"Successfully exported '{settings.collection18}'!")
        return {"FINISHED"}


class CENLEVELEXPORT_OT_export_slot19(bpy.types.Operator):
    bl_idname = "cenlevelexport.export_slot19"
    bl_label = "Export"
    bl_description = "Export this collection"
    bl_options = {"REGISTER"}
    
    def execute(self, context):
        settings = context.scene.cenlevelexport
        if export_single_slot(settings.collection19, settings.path19):
            popup_info(f"Successfully exported '{settings.collection19}'!")
        return {"FINISHED"}


class CENLEVELEXPORT_OT_export_slot20(bpy.types.Operator):
    bl_idname = "cenlevelexport.export_slot20"
    bl_label = "Export"
    bl_description = "Export this collection"
    bl_options = {"REGISTER"}
    
    def execute(self, context):
        settings = context.scene.cenlevelexport
        if export_single_slot(settings.collection20, settings.path20):
            popup_info(f"Successfully exported '{settings.collection20}'!")
        return {"FINISHED"}


class CENLEVELEXPORT_OT_export_slot21(bpy.types.Operator):
    bl_idname = "cenlevelexport.export_slot21"
    bl_label = "Export"
    bl_description = "Export this collection"
    bl_options = {"REGISTER"}
    
    def execute(self, context):
        settings = context.scene.cenlevelexport
        if export_single_slot(settings.collection21, settings.path21):
            popup_info(f"Successfully exported '{settings.collection21}'!")
        return {"FINISHED"}


class CENLEVELEXPORT_OT_export_slot22(bpy.types.Operator):
    bl_idname = "cenlevelexport.export_slot22"
    bl_label = "Export"
    bl_description = "Export this collection"
    bl_options = {"REGISTER"}
    
    def execute(self, context):
        settings = context.scene.cenlevelexport
        if export_single_slot(settings.collection22, settings.path22):
            popup_info(f"Successfully exported '{settings.collection22}'!")
        return {"FINISHED"}


class CENLEVELEXPORT_OT_export_slot23(bpy.types.Operator):
    bl_idname = "cenlevelexport.export_slot23"
    bl_label = "Export"
    bl_description = "Export this collection"
    bl_options = {"REGISTER"}
    
    def execute(self, context):
        settings = context.scene.cenlevelexport
        if export_single_slot(settings.collection23, settings.path23):
            popup_info(f"Successfully exported '{settings.collection23}'!")
        return {"FINISHED"}


class CENLEVELEXPORT_OT_export_slot24(bpy.types.Operator):
    bl_idname = "cenlevelexport.export_slot24"
    bl_label = "Export"
    bl_description = "Export this collection"
    bl_options = {"REGISTER"}
    
    def execute(self, context):
        settings = context.scene.cenlevelexport
        if export_single_slot(settings.collection24, settings.path24):
            popup_info(f"Successfully exported '{settings.collection24}'!")
        return {"FINISHED"}


class CENLEVELEXPORT_OT_export_slot25(bpy.types.Operator):
    bl_idname = "cenlevelexport.export_slot25"
    bl_label = "Export"
    bl_description = "Export this collection"
    bl_options = {"REGISTER"}
    
    def execute(self, context):
        settings = context.scene.cenlevelexport
        if export_single_slot(settings.collection25, settings.path25):
            popup_info(f"Successfully exported '{settings.collection25}'!")
        return {"FINISHED"}


class CENLEVELEXPORT_OT_export_slot26(bpy.types.Operator):
    bl_idname = "cenlevelexport.export_slot26"
    bl_label = "Export"
    bl_description = "Export this collection"
    bl_options = {"REGISTER"}
    
    def execute(self, context):
        settings = context.scene.cenlevelexport
        if export_single_slot(settings.collection26, settings.path26):
            popup_info(f"Successfully exported '{settings.collection26}'!")
        return {"FINISHED"}


class CENLEVELEXPORT_OT_export_slot27(bpy.types.Operator):
    bl_idname = "cenlevelexport.export_slot27"
    bl_label = "Export"
    bl_description = "Export this collection"
    bl_options = {"REGISTER"}
    
    def execute(self, context):
        settings = context.scene.cenlevelexport
        if export_single_slot(settings.collection27, settings.path27):
            popup_info(f"Successfully exported '{settings.collection27}'!")
        return {"FINISHED"}


class CENLEVELEXPORT_OT_export_slot28(bpy.types.Operator):
    bl_idname = "cenlevelexport.export_slot28"
    bl_label = "Export"
    bl_description = "Export this collection"
    bl_options = {"REGISTER"}
    
    def execute(self, context):
        settings = context.scene.cenlevelexport
        if export_single_slot(settings.collection28, settings.path28):
            popup_info(f"Successfully exported '{settings.collection28}'!")
        return {"FINISHED"}


class CENLEVELEXPORT_OT_export_slot29(bpy.types.Operator):
    bl_idname = "cenlevelexport.export_slot29"
    bl_label = "Export"
    bl_description = "Export this collection"
    bl_options = {"REGISTER"}
    
    def execute(self, context):
        settings = context.scene.cenlevelexport
        if export_single_slot(settings.collection29, settings.path29):
            popup_info(f"Successfully exported '{settings.collection29}'!")
        return {"FINISHED"}


class CENLEVELEXPORT_OT_export_slot30(bpy.types.Operator):
    bl_idname = "cenlevelexport.export_slot30"
    bl_label = "Export"
    bl_description = "Export this collection"
    bl_options = {"REGISTER"}
    
    def execute(self, context):
        settings = context.scene.cenlevelexport
        if export_single_slot(settings.collection30, settings.path30):
            popup_info(f"Successfully exported '{settings.collection30}'!")
        return {"FINISHED"}


class CENLEVELEXPORT_OT_export_slot31(bpy.types.Operator):
    bl_idname = "cenlevelexport.export_slot31"
    bl_label = "Export"
    bl_description = "Export this collection"
    bl_options = {"REGISTER"}
    
    def execute(self, context):
        settings = context.scene.cenlevelexport
        if export_single_slot(settings.collection31, settings.path31):
            popup_info(f"Successfully exported '{settings.collection31}'!")
        return {"FINISHED"}


class CENLEVELEXPORT_OT_export_slot32(bpy.types.Operator):
    bl_idname = "cenlevelexport.export_slot32"
    bl_label = "Export"
    bl_description = "Export this collection"
    bl_options = {"REGISTER"}
    
    def execute(self, context):
        settings = context.scene.cenlevelexport
        if export_single_slot(settings.collection32, settings.path32):
            popup_info(f"Successfully exported '{settings.collection32}'!")
        return {"FINISHED"}


class CENLEVELEXPORT_OT_export_slot33(bpy.types.Operator):
    bl_idname = "cenlevelexport.export_slot33"
    bl_label = "Export"
    bl_description = "Export this collection"
    bl_options = {"REGISTER"}
    
    def execute(self, context):
        settings = context.scene.cenlevelexport
        if export_single_slot(settings.collection33, settings.path33):
            popup_info(f"Successfully exported '{settings.collection33}'!")
        return {"FINISHED"}


class CENLEVELEXPORT_OT_export_slot34(bpy.types.Operator):
    bl_idname = "cenlevelexport.export_slot34"
    bl_label = "Export"
    bl_description = "Export this collection"
    bl_options = {"REGISTER"}
    
    def execute(self, context):
        settings = context.scene.cenlevelexport
        if export_single_slot(settings.collection34, settings.path34):
            popup_info(f"Successfully exported '{settings.collection34}'!")
        return {"FINISHED"}


class CENLEVELEXPORT_OT_export_slot35(bpy.types.Operator):
    bl_idname = "cenlevelexport.export_slot35"
    bl_label = "Export"
    bl_description = "Export this collection"
    bl_options = {"REGISTER"}
    
    def execute(self, context):
        settings = context.scene.cenlevelexport
        if export_single_slot(settings.collection35, settings.path35):
            popup_info(f"Successfully exported '{settings.collection35}'!")
        return {"FINISHED"}


class CENLEVELEXPORT_OT_pick_path1(bpy.types.Operator):
    bl_idname = "cenlevelexport.pick_path1"
    bl_label = "Choose Path 1"
    bl_options = {"REGISTER"}
    
    filepath: StringProperty(subtype="FILE_PATH")
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}
    
    def execute(self, context):
        if self.filepath:
            context.scene.cenlevelexport.path1 = self.filepath
        return {"FINISHED"}


class CENLEVELEXPORT_OT_pick_path2(bpy.types.Operator):
    bl_idname = "cenlevelexport.pick_path2"
    bl_label = "Choose Path 2"
    bl_options = {"REGISTER"}
    
    filepath: StringProperty(subtype="FILE_PATH")
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}
    
    def execute(self, context):
        if self.filepath:
            context.scene.cenlevelexport.path2 = self.filepath
        return {"FINISHED"}


class CENLEVELEXPORT_OT_pick_path3(bpy.types.Operator):
    bl_idname = "cenlevelexport.pick_path3"
    bl_label = "Choose Path 3"
    bl_options = {"REGISTER"}
    
    filepath: StringProperty(subtype="FILE_PATH")
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}
    
    def execute(self, context):
        if self.filepath:
            context.scene.cenlevelexport.path3 = self.filepath
        return {"FINISHED"}


class CENLEVELEXPORT_OT_pick_path4(bpy.types.Operator):
    bl_idname = "cenlevelexport.pick_path4"
    bl_label = "Choose Path 4"
    bl_options = {"REGISTER"}
    
    filepath: StringProperty(subtype="FILE_PATH")
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}
    
    def execute(self, context):
        if self.filepath:
            context.scene.cenlevelexport.path4 = self.filepath
        return {"FINISHED"}


class CENLEVELEXPORT_OT_pick_path5(bpy.types.Operator):
    bl_idname = "cenlevelexport.pick_path5"
    bl_label = "Choose Path 5"
    bl_options = {"REGISTER"}
    
    filepath: StringProperty(subtype="FILE_PATH")
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}
    
    def execute(self, context):
        if self.filepath:
            context.scene.cenlevelexport.path5 = self.filepath
        return {"FINISHED"}


class CENLEVELEXPORT_OT_pick_path6(bpy.types.Operator):
    bl_idname = "cenlevelexport.pick_path6"
    bl_label = "Choose Path 6"
    bl_options = {"REGISTER"}
    
    filepath: StringProperty(subtype="FILE_PATH")
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}
    
    def execute(self, context):
        if self.filepath:
            context.scene.cenlevelexport.path6 = self.filepath
        return {"FINISHED"}


class CENLEVELEXPORT_OT_pick_path7(bpy.types.Operator):
    bl_idname = "cenlevelexport.pick_path7"
    bl_label = "Choose Path 7"
    bl_options = {"REGISTER"}
    
    filepath: StringProperty(subtype="FILE_PATH")
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}
    
    def execute(self, context):
        if self.filepath:
            context.scene.cenlevelexport.path7 = self.filepath
        return {"FINISHED"}


class CENLEVELEXPORT_OT_pick_path8(bpy.types.Operator):
    bl_idname = "cenlevelexport.pick_path8"
    bl_label = "Choose Path 8"
    bl_options = {"REGISTER"}
    
    filepath: StringProperty(subtype="FILE_PATH")
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}
    
    def execute(self, context):
        if self.filepath:
            context.scene.cenlevelexport.path8 = self.filepath
        return {"FINISHED"}


class CENLEVELEXPORT_OT_pick_path9(bpy.types.Operator):
    bl_idname = "cenlevelexport.pick_path9"
    bl_label = "Choose Path 9"
    bl_options = {"REGISTER"}
    
    filepath: StringProperty(subtype="FILE_PATH")
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}
    
    def execute(self, context):
        if self.filepath:
            context.scene.cenlevelexport.path9 = self.filepath
        return {"FINISHED"}


class CENLEVELEXPORT_OT_pick_path10(bpy.types.Operator):
    bl_idname = "cenlevelexport.pick_path10"
    bl_label = "Choose Path 10"
    bl_options = {"REGISTER"}
    
    filepath: StringProperty(subtype="FILE_PATH")
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}
    
    def execute(self, context):
        if self.filepath:
            context.scene.cenlevelexport.path10 = self.filepath
        return {"FINISHED"}


class CENLEVELEXPORT_OT_pick_path11(bpy.types.Operator):
    bl_idname = "cenlevelexport.pick_path11"
    bl_label = "Choose Path 11"
    bl_options = {"REGISTER"}
    
    filepath: StringProperty(subtype="FILE_PATH")
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}
    
    def execute(self, context):
        if self.filepath:
            context.scene.cenlevelexport.path11 = self.filepath
        return {"FINISHED"}


class CENLEVELEXPORT_OT_pick_path12(bpy.types.Operator):
    bl_idname = "cenlevelexport.pick_path12"
    bl_label = "Choose Path 12"
    bl_options = {"REGISTER"}
    
    filepath: StringProperty(subtype="FILE_PATH")
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}
    
    def execute(self, context):
        if self.filepath:
            context.scene.cenlevelexport.path12 = self.filepath
        return {"FINISHED"}


class CENLEVELEXPORT_OT_pick_path13(bpy.types.Operator):
    bl_idname = "cenlevelexport.pick_path13"
    bl_label = "Choose Path 13"
    bl_options = {"REGISTER"}
    
    filepath: StringProperty(subtype="FILE_PATH")
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}
    
    def execute(self, context):
        if self.filepath:
            context.scene.cenlevelexport.path13 = self.filepath
        return {"FINISHED"}


class CENLEVELEXPORT_OT_pick_path14(bpy.types.Operator):
    bl_idname = "cenlevelexport.pick_path14"
    bl_label = "Choose Path 14"
    bl_options = {"REGISTER"}
    
    filepath: StringProperty(subtype="FILE_PATH")
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}
    
    def execute(self, context):
        if self.filepath:
            context.scene.cenlevelexport.path14 = self.filepath
        return {"FINISHED"}


class CENLEVELEXPORT_OT_pick_path15(bpy.types.Operator):
    bl_idname = "cenlevelexport.pick_path15"
    bl_label = "Choose Path 15"
    bl_options = {"REGISTER"}
    
    filepath: StringProperty(subtype="FILE_PATH")
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}
    
    def execute(self, context):
        if self.filepath:
            context.scene.cenlevelexport.path15 = self.filepath
        return {"FINISHED"}


class CENLEVELEXPORT_OT_pick_path16(bpy.types.Operator):
    bl_idname = "cenlevelexport.pick_path16"
    bl_label = "Choose Path 16"
    bl_options = {"REGISTER"}
    
    filepath: StringProperty(subtype="FILE_PATH")
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}
    
    def execute(self, context):
        if self.filepath:
            context.scene.cenlevelexport.path16 = self.filepath
        return {"FINISHED"}


class CENLEVELEXPORT_OT_pick_path17(bpy.types.Operator):
    bl_idname = "cenlevelexport.pick_path17"
    bl_label = "Choose Path 17"
    bl_options = {"REGISTER"}
    
    filepath: StringProperty(subtype="FILE_PATH")
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}
    
    def execute(self, context):
        if self.filepath:
            context.scene.cenlevelexport.path17 = self.filepath
        return {"FINISHED"}


class CENLEVELEXPORT_OT_pick_path18(bpy.types.Operator):
    bl_idname = "cenlevelexport.pick_path18"
    bl_label = "Choose Path 18"
    bl_options = {"REGISTER"}
    
    filepath: StringProperty(subtype="FILE_PATH")
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}
    
    def execute(self, context):
        if self.filepath:
            context.scene.cenlevelexport.path18 = self.filepath
        return {"FINISHED"}


class CENLEVELEXPORT_OT_pick_path19(bpy.types.Operator):
    bl_idname = "cenlevelexport.pick_path19"
    bl_label = "Choose Path 19"
    bl_options = {"REGISTER"}
    
    filepath: StringProperty(subtype="FILE_PATH")
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}
    
    def execute(self, context):
        if self.filepath:
            context.scene.cenlevelexport.path19 = self.filepath
        return {"FINISHED"}


class CENLEVELEXPORT_OT_pick_path20(bpy.types.Operator):
    bl_idname = "cenlevelexport.pick_path20"
    bl_label = "Choose Path 20"
    bl_options = {"REGISTER"}
    
    filepath: StringProperty(subtype="FILE_PATH")
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}
    
    def execute(self, context):
        if self.filepath:
            context.scene.cenlevelexport.path20 = self.filepath
        return {"FINISHED"}


class CENLEVELEXPORT_OT_pick_path21(bpy.types.Operator):
    bl_idname = "cenlevelexport.pick_path21"
    bl_label = "Choose Path 21"
    bl_options = {"REGISTER"}
    
    filepath: StringProperty(subtype="FILE_PATH")
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}
    
    def execute(self, context):
        if self.filepath:
            context.scene.cenlevelexport.path21 = self.filepath
        return {"FINISHED"}


class CENLEVELEXPORT_OT_pick_path22(bpy.types.Operator):
    bl_idname = "cenlevelexport.pick_path22"
    bl_label = "Choose Path 22"
    bl_options = {"REGISTER"}
    
    filepath: StringProperty(subtype="FILE_PATH")
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}
    
    def execute(self, context):
        if self.filepath:
            context.scene.cenlevelexport.path22 = self.filepath
        return {"FINISHED"}


class CENLEVELEXPORT_OT_pick_path23(bpy.types.Operator):
    bl_idname = "cenlevelexport.pick_path23"
    bl_label = "Choose Path 23"
    bl_options = {"REGISTER"}
    
    filepath: StringProperty(subtype="FILE_PATH")
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}
    
    def execute(self, context):
        if self.filepath:
            context.scene.cenlevelexport.path23 = self.filepath
        return {"FINISHED"}


class CENLEVELEXPORT_OT_pick_path24(bpy.types.Operator):
    bl_idname = "cenlevelexport.pick_path24"
    bl_label = "Choose Path 24"
    bl_options = {"REGISTER"}
    
    filepath: StringProperty(subtype="FILE_PATH")
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}
    
    def execute(self, context):
        if self.filepath:
            context.scene.cenlevelexport.path24 = self.filepath
        return {"FINISHED"}


class CENLEVELEXPORT_OT_pick_path25(bpy.types.Operator):
    bl_idname = "cenlevelexport.pick_path25"
    bl_label = "Choose Path 25"
    bl_options = {"REGISTER"}
    
    filepath: StringProperty(subtype="FILE_PATH")
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}
    
    def execute(self, context):
        if self.filepath:
            context.scene.cenlevelexport.path25 = self.filepath
        return {"FINISHED"}


class CENLEVELEXPORT_OT_pick_path26(bpy.types.Operator):
    bl_idname = "cenlevelexport.pick_path26"
    bl_label = "Choose Path 26"
    bl_options = {"REGISTER"}
    
    filepath: StringProperty(subtype="FILE_PATH")
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}
    
    def execute(self, context):
        if self.filepath:
            context.scene.cenlevelexport.path26 = self.filepath
        return {"FINISHED"}


class CENLEVELEXPORT_OT_pick_path27(bpy.types.Operator):
    bl_idname = "cenlevelexport.pick_path27"
    bl_label = "Choose Path 27"
    bl_options = {"REGISTER"}
    
    filepath: StringProperty(subtype="FILE_PATH")
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}
    
    def execute(self, context):
        if self.filepath:
            context.scene.cenlevelexport.path27 = self.filepath
        return {"FINISHED"}


class CENLEVELEXPORT_OT_pick_path28(bpy.types.Operator):
    bl_idname = "cenlevelexport.pick_path28"
    bl_label = "Choose Path 28"
    bl_options = {"REGISTER"}
    
    filepath: StringProperty(subtype="FILE_PATH")
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}
    
    def execute(self, context):
        if self.filepath:
            context.scene.cenlevelexport.path28 = self.filepath
        return {"FINISHED"}


class CENLEVELEXPORT_OT_pick_path29(bpy.types.Operator):
    bl_idname = "cenlevelexport.pick_path29"
    bl_label = "Choose Path 29"
    bl_options = {"REGISTER"}
    
    filepath: StringProperty(subtype="FILE_PATH")
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}
    
    def execute(self, context):
        if self.filepath:
            context.scene.cenlevelexport.path29 = self.filepath
        return {"FINISHED"}


class CENLEVELEXPORT_OT_pick_path30(bpy.types.Operator):
    bl_idname = "cenlevelexport.pick_path30"
    bl_label = "Choose Path 30"
    bl_options = {"REGISTER"}
    
    filepath: StringProperty(subtype="FILE_PATH")
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}
    
    def execute(self, context):
        if self.filepath:
            context.scene.cenlevelexport.path30 = self.filepath
        return {"FINISHED"}


class CENLEVELEXPORT_OT_pick_path31(bpy.types.Operator):
    bl_idname = "cenlevelexport.pick_path31"
    bl_label = "Choose Path 31"
    bl_options = {"REGISTER"}
    
    filepath: StringProperty(subtype="FILE_PATH")
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}
    
    def execute(self, context):
        if self.filepath:
            context.scene.cenlevelexport.path31 = self.filepath
        return {"FINISHED"}


class CENLEVELEXPORT_OT_pick_path32(bpy.types.Operator):
    bl_idname = "cenlevelexport.pick_path32"
    bl_label = "Choose Path 32"
    bl_options = {"REGISTER"}
    
    filepath: StringProperty(subtype="FILE_PATH")
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}
    
    def execute(self, context):
        if self.filepath:
            context.scene.cenlevelexport.path32 = self.filepath
        return {"FINISHED"}


class CENLEVELEXPORT_OT_pick_path33(bpy.types.Operator):
    bl_idname = "cenlevelexport.pick_path33"
    bl_label = "Choose Path 33"
    bl_options = {"REGISTER"}
    
    filepath: StringProperty(subtype="FILE_PATH")
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}
    
    def execute(self, context):
        if self.filepath:
            context.scene.cenlevelexport.path33 = self.filepath
        return {"FINISHED"}


class CENLEVELEXPORT_OT_pick_path34(bpy.types.Operator):
    bl_idname = "cenlevelexport.pick_path34"
    bl_label = "Choose Path 34"
    bl_options = {"REGISTER"}
    
    filepath: StringProperty(subtype="FILE_PATH")
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}
    
    def execute(self, context):
        if self.filepath:
            context.scene.cenlevelexport.path34 = self.filepath
        return {"FINISHED"}


class CENLEVELEXPORT_OT_pick_path35(bpy.types.Operator):
    bl_idname = "cenlevelexport.pick_path35"
    bl_label = "Choose Path 35"
    bl_options = {"REGISTER"}
    
    filepath: StringProperty(subtype="FILE_PATH")
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}
    
    def execute(self, context):
        if self.filepath:
            context.scene.cenlevelexport.path35 = self.filepath
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
        
        # Export All button at TOP
        layout.operator("cenlevelexport.export_all", icon="EXPORT")
        layout.separator()
        
        # Slot 1
        box = layout.box()
        row = box.row(align=True)
        row.prop(settings, "collection1", text="")
        row = box.row(align=True)
        row.prop(settings, "path1", text="")
        row.operator("cenlevelexport.pick_path1", text="", icon="FILE_FOLDER")
        row = box.row(align=True)
        row.operator("cenlevelexport.export_slot1", icon="EXPORT")
        
        # Slot 2
        box = layout.box()
        row = box.row(align=True)
        row.prop(settings, "collection2", text="")
        row = box.row(align=True)
        row.prop(settings, "path2", text="")
        row.operator("cenlevelexport.pick_path2", text="", icon="FILE_FOLDER")
        row = box.row(align=True)
        row.operator("cenlevelexport.export_slot2", icon="EXPORT")
        
        # Slot 3
        box = layout.box()
        row = box.row(align=True)
        row.prop(settings, "collection3", text="")
        row = box.row(align=True)
        row.prop(settings, "path3", text="")
        row.operator("cenlevelexport.pick_path3", text="", icon="FILE_FOLDER")
        row = box.row(align=True)
        row.operator("cenlevelexport.export_slot3", icon="EXPORT")
        
        # Slot 4
        box = layout.box()
        row = box.row(align=True)
        row.prop(settings, "collection4", text="")
        row = box.row(align=True)
        row.prop(settings, "path4", text="")
        row.operator("cenlevelexport.pick_path4", text="", icon="FILE_FOLDER")
        row = box.row(align=True)
        row.operator("cenlevelexport.export_slot4", icon="EXPORT")
        
        # Slot 5
        box = layout.box()
        row = box.row(align=True)
        row.prop(settings, "collection5", text="")
        row = box.row(align=True)
        row.prop(settings, "path5", text="")
        row.operator("cenlevelexport.pick_path5", text="", icon="FILE_FOLDER")
        row = box.row(align=True)
        row.operator("cenlevelexport.export_slot5", icon="EXPORT")
        
        # Slot 6
        box = layout.box()
        row = box.row(align=True)
        row.prop(settings, "collection6", text="")
        row = box.row(align=True)
        row.prop(settings, "path6", text="")
        row.operator("cenlevelexport.pick_path6", text="", icon="FILE_FOLDER")
        row = box.row(align=True)
        row.operator("cenlevelexport.export_slot6", icon="EXPORT")
        
        # Slot 7
        box = layout.box()
        row = box.row(align=True)
        row.prop(settings, "collection7", text="")
        row = box.row(align=True)
        row.prop(settings, "path7", text="")
        row.operator("cenlevelexport.pick_path7", text="", icon="FILE_FOLDER")
        row = box.row(align=True)
        row.operator("cenlevelexport.export_slot7", icon="EXPORT")
        
        # Slot 8
        box = layout.box()
        row = box.row(align=True)
        row.prop(settings, "collection8", text="")
        row = box.row(align=True)
        row.prop(settings, "path8", text="")
        row.operator("cenlevelexport.pick_path8", text="", icon="FILE_FOLDER")
        row = box.row(align=True)
        row.operator("cenlevelexport.export_slot8", icon="EXPORT")
        
        # Slot 9
        box = layout.box()
        row = box.row(align=True)
        row.prop(settings, "collection9", text="")
        row = box.row(align=True)
        row.prop(settings, "path9", text="")
        row.operator("cenlevelexport.pick_path9", text="", icon="FILE_FOLDER")
        row = box.row(align=True)
        row.operator("cenlevelexport.export_slot9", icon="EXPORT")
        
        # Slot 10
        box = layout.box()
        row = box.row(align=True)
        row.prop(settings, "collection10", text="")
        row = box.row(align=True)
        row.prop(settings, "path10", text="")
        row.operator("cenlevelexport.pick_path10", text="", icon="FILE_FOLDER")
        row = box.row(align=True)
        row.operator("cenlevelexport.export_slot10", icon="EXPORT")
        
        # Slot 11
        box = layout.box()
        row = box.row(align=True)
        row.prop(settings, "collection11", text="")
        row = box.row(align=True)
        row.prop(settings, "path11", text="")
        row.operator("cenlevelexport.pick_path11", text="", icon="FILE_FOLDER")
        row = box.row(align=True)
        row.operator("cenlevelexport.export_slot11", icon="EXPORT")
        
        # Slot 12
        box = layout.box()
        row = box.row(align=True)
        row.prop(settings, "collection12", text="")
        row = box.row(align=True)
        row.prop(settings, "path12", text="")
        row.operator("cenlevelexport.pick_path12", text="", icon="FILE_FOLDER")
        row = box.row(align=True)
        row.operator("cenlevelexport.export_slot12", icon="EXPORT")
        
        # Slot 13
        box = layout.box()
        row = box.row(align=True)
        row.prop(settings, "collection13", text="")
        row = box.row(align=True)
        row.prop(settings, "path13", text="")
        row.operator("cenlevelexport.pick_path13", text="", icon="FILE_FOLDER")
        row = box.row(align=True)
        row.operator("cenlevelexport.export_slot13", icon="EXPORT")
        
        # Slot 14
        box = layout.box()
        row = box.row(align=True)
        row.prop(settings, "collection14", text="")
        row = box.row(align=True)
        row.prop(settings, "path14", text="")
        row.operator("cenlevelexport.pick_path14", text="", icon="FILE_FOLDER")
        row = box.row(align=True)
        row.operator("cenlevelexport.export_slot14", icon="EXPORT")
        
        # Slot 15
        box = layout.box()
        row = box.row(align=True)
        row.prop(settings, "collection15", text="")
        row = box.row(align=True)
        row.prop(settings, "path15", text="")
        row.operator("cenlevelexport.pick_path15", text="", icon="FILE_FOLDER")
        row = box.row(align=True)
        row.operator("cenlevelexport.export_slot15", icon="EXPORT")
        
        # Slot 16
        box = layout.box()
        row = box.row(align=True)
        row.prop(settings, "collection16", text="")
        row = box.row(align=True)
        row.prop(settings, "path16", text="")
        row.operator("cenlevelexport.pick_path16", text="", icon="FILE_FOLDER")
        row = box.row(align=True)
        row.operator("cenlevelexport.export_slot16", icon="EXPORT")
        
        # Slot 17
        box = layout.box()
        row = box.row(align=True)
        row.prop(settings, "collection17", text="")
        row = box.row(align=True)
        row.prop(settings, "path17", text="")
        row.operator("cenlevelexport.pick_path17", text="", icon="FILE_FOLDER")
        row = box.row(align=True)
        row.operator("cenlevelexport.export_slot17", icon="EXPORT")
        
        # Slot 18
        box = layout.box()
        row = box.row(align=True)
        row.prop(settings, "collection18", text="")
        row = box.row(align=True)
        row.prop(settings, "path18", text="")
        row.operator("cenlevelexport.pick_path18", text="", icon="FILE_FOLDER")
        row = box.row(align=True)
        row.operator("cenlevelexport.export_slot18", icon="EXPORT")
        
        # Slot 19
        box = layout.box()
        row = box.row(align=True)
        row.prop(settings, "collection19", text="")
        row = box.row(align=True)
        row.prop(settings, "path19", text="")
        row.operator("cenlevelexport.pick_path19", text="", icon="FILE_FOLDER")
        row = box.row(align=True)
        row.operator("cenlevelexport.export_slot19", icon="EXPORT")
        
        # Slot 20
        box = layout.box()
        row = box.row(align=True)
        row.prop(settings, "collection20", text="")
        row = box.row(align=True)
        row.prop(settings, "path20", text="")
        row.operator("cenlevelexport.pick_path20", text="", icon="FILE_FOLDER")
        row = box.row(align=True)
        row.operator("cenlevelexport.export_slot20", icon="EXPORT")
        
        # Slot 21
        box = layout.box()
        row = box.row(align=True)
        row.prop(settings, "collection21", text="")
        row = box.row(align=True)
        row.prop(settings, "path21", text="")
        row.operator("cenlevelexport.pick_path21", text="", icon="FILE_FOLDER")
        row = box.row(align=True)
        row.operator("cenlevelexport.export_slot21", icon="EXPORT")
        
        # Slot 22
        box = layout.box()
        row = box.row(align=True)
        row.prop(settings, "collection22", text="")
        row = box.row(align=True)
        row.prop(settings, "path22", text="")
        row.operator("cenlevelexport.pick_path22", text="", icon="FILE_FOLDER")
        row = box.row(align=True)
        row.operator("cenlevelexport.export_slot22", icon="EXPORT")
        
        # Slot 23
        box = layout.box()
        row = box.row(align=True)
        row.prop(settings, "collection23", text="")
        row = box.row(align=True)
        row.prop(settings, "path23", text="")
        row.operator("cenlevelexport.pick_path23", text="", icon="FILE_FOLDER")
        row = box.row(align=True)
        row.operator("cenlevelexport.export_slot23", icon="EXPORT")
        
        # Slot 24
        box = layout.box()
        row = box.row(align=True)
        row.prop(settings, "collection24", text="")
        row = box.row(align=True)
        row.prop(settings, "path24", text="")
        row.operator("cenlevelexport.pick_path24", text="", icon="FILE_FOLDER")
        row = box.row(align=True)
        row.operator("cenlevelexport.export_slot24", icon="EXPORT")
        
        # Slot 25
        box = layout.box()
        row = box.row(align=True)
        row.prop(settings, "collection25", text="")
        row = box.row(align=True)
        row.prop(settings, "path25", text="")
        row.operator("cenlevelexport.pick_path25", text="", icon="FILE_FOLDER")
        row = box.row(align=True)
        row.operator("cenlevelexport.export_slot25", icon="EXPORT")
        
        # Slot 26
        box = layout.box()
        row = box.row(align=True)
        row.prop(settings, "collection26", text="")
        row = box.row(align=True)
        row.prop(settings, "path26", text="")
        row.operator("cenlevelexport.pick_path26", text="", icon="FILE_FOLDER")
        row = box.row(align=True)
        row.operator("cenlevelexport.export_slot26", icon="EXPORT")
        
        # Slot 27
        box = layout.box()
        row = box.row(align=True)
        row.prop(settings, "collection27", text="")
        row = box.row(align=True)
        row.prop(settings, "path27", text="")
        row.operator("cenlevelexport.pick_path27", text="", icon="FILE_FOLDER")
        row = box.row(align=True)
        row.operator("cenlevelexport.export_slot27", icon="EXPORT")
        
        # Slot 28
        box = layout.box()
        row = box.row(align=True)
        row.prop(settings, "collection28", text="")
        row = box.row(align=True)
        row.prop(settings, "path28", text="")
        row.operator("cenlevelexport.pick_path28", text="", icon="FILE_FOLDER")
        row = box.row(align=True)
        row.operator("cenlevelexport.export_slot28", icon="EXPORT")
        
        # Slot 29
        box = layout.box()
        row = box.row(align=True)
        row.prop(settings, "collection29", text="")
        row = box.row(align=True)
        row.prop(settings, "path29", text="")
        row.operator("cenlevelexport.pick_path29", text="", icon="FILE_FOLDER")
        row = box.row(align=True)
        row.operator("cenlevelexport.export_slot29", icon="EXPORT")
        
        # Slot 30        box = layout.box()
        row = box.row(align=True)
        row.prop(settings, "collection30", text="")
        row = box.row(align=True)
        row.prop(settings, "path30", text="")
        row.operator("cenlevelexport.pick_path30", text="", icon="FILE_FOLDER")
        row = box.row(align=True)
        row.operator("cenlevelexport.export_slot30", icon="EXPORT")
        
        # Slot 31
        box = layout.box()
        row = box.row(align=True)
        row.prop(settings, "collection31", text="")
        row = box.row(align=True)
        row.prop(settings, "path31", text="")
        row.operator("cenlevelexport.pick_path31", text="", icon="FILE_FOLDER")
        row = box.row(align=True)
        row.operator("cenlevelexport.export_slot31", icon="EXPORT")
        
        # Slot 32
        box = layout.box()
        row = box.row(align=True)
        row.prop(settings, "collection32", text="")
        row = box.row(align=True)
        row.prop(settings, "path32", text="")
        row.operator("cenlevelexport.pick_path32", text="", icon="FILE_FOLDER")
        row = box.row(align=True)
        row.operator("cenlevelexport.export_slot32", icon="EXPORT")
        
        # Slot 33
        box = layout.box()
        row = box.row(align=True)
        row.prop(settings, "collection33", text="")
        row = box.row(align=True)
        row.prop(settings, "path33", text="")
        row.operator("cenlevelexport.pick_path33", text="", icon="FILE_FOLDER")
        row = box.row(align=True)
        row.operator("cenlevelexport.export_slot33", icon="EXPORT")
        
        # Slot 34
        box = layout.box()
        row = box.row(align=True)
        row.prop(settings, "collection34", text="")
        row = box.row(align=True)
        row.prop(settings, "path34", text="")
        row.operator("cenlevelexport.pick_path34", text="", icon="FILE_FOLDER")
        row = box.row(align=True)
        row.operator("cenlevelexport.export_slot34", icon="EXPORT")
        
        # Slot 35
        box = layout.box()
        row = box.row(align=True)
        row.prop(settings, "collection35", text="")
        row = box.row(align=True)
        row.prop(settings, "path35", text="")
        row.operator("cenlevelexport.pick_path35", text="", icon="FILE_FOLDER")
        row = box.row(align=True)
        row.operator("cenlevelexport.export_slot35", icon="EXPORT")


# ---------- registration ----------
classes = (
    CENLEVELEXPORT_PG_settings,
    CENLEVELEXPORT_OT_export_all,
    CENLEVELEXPORT_OT_export_slot1,
    CENLEVELEXPORT_OT_export_slot2,
    CENLEVELEXPORT_OT_export_slot3,
    CENLEVELEXPORT_OT_export_slot4,
    CENLEVELEXPORT_OT_export_slot5,
    CENLEVELEXPORT_OT_export_slot6,
    CENLEVELEXPORT_OT_export_slot7,
    CENLEVELEXPORT_OT_export_slot8,
    CENLEVELEXPORT_OT_export_slot9,
    CENLEVELEXPORT_OT_export_slot10,
    CENLEVELEXPORT_OT_export_slot11,
    CENLEVELEXPORT_OT_export_slot12,
    CENLEVELEXPORT_OT_export_slot13,
    CENLEVELEXPORT_OT_export_slot14,
    CENLEVELEXPORT_OT_export_slot15,
    CENLEVELEXPORT_OT_export_slot16,
    CENLEVELEXPORT_OT_export_slot17,
    CENLEVELEXPORT_OT_export_slot18,
    CENLEVELEXPORT_OT_export_slot19,
    CENLEVELEXPORT_OT_export_slot20,
    CENLEVELEXPORT_OT_export_slot21,
    CENLEVELEXPORT_OT_export_slot22,
    CENLEVELEXPORT_OT_export_slot23,
    CENLEVELEXPORT_OT_export_slot24,
    CENLEVELEXPORT_OT_export_slot25,
    CENLEVELEXPORT_OT_export_slot26,
    CENLEVELEXPORT_OT_export_slot27,
    CENLEVELEXPORT_OT_export_slot28,
    CENLEVELEXPORT_OT_export_slot29,
    CENLEVELEXPORT_OT_export_slot30,
    CENLEVELEXPORT_OT_export_slot31,
    CENLEVELEXPORT_OT_export_slot32,
    CENLEVELEXPORT_OT_export_slot33,
    CENLEVELEXPORT_OT_export_slot34,
    CENLEVELEXPORT_OT_export_slot35,
    CENLEVELEXPORT_OT_pick_path1,
    CENLEVELEXPORT_OT_pick_path2,
    CENLEVELEXPORT_OT_pick_path3,
    CENLEVELEXPORT_OT_pick_path4,
    CENLEVELEXPORT_OT_pick_path5,
    CENLEVELEXPORT_OT_pick_path6,
    CENLEVELEXPORT_OT_pick_path7,
    CENLEVELEXPORT_OT_pick_path8,
    CENLEVELEXPORT_OT_pick_path9,
    CENLEVELEXPORT_OT_pick_path10,
    CENLEVELEXPORT_OT_pick_path11,
    CENLEVELEXPORT_OT_pick_path12,
    CENLEVELEXPORT_OT_pick_path13,
    CENLEVELEXPORT_OT_pick_path14,
    CENLEVELEXPORT_OT_pick_path15,
    CENLEVELEXPORT_OT_pick_path16,
    CENLEVELEXPORT_OT_pick_path17,
    CENLEVELEXPORT_OT_pick_path18,
    CENLEVELEXPORT_OT_pick_path19,
    CENLEVELEXPORT_OT_pick_path20,
    CENLEVELEXPORT_OT_pick_path21,
    CENLEVELEXPORT_OT_pick_path22,
    CENLEVELEXPORT_OT_pick_path23,
    CENLEVELEXPORT_OT_pick_path24,
    CENLEVELEXPORT_OT_pick_path25,
    CENLEVELEXPORT_OT_pick_path26,
    CENLEVELEXPORT_OT_pick_path27,
    CENLEVELEXPORT_OT_pick_path28,
    CENLEVELEXPORT_OT_pick_path29,
    CENLEVELEXPORT_OT_pick_path30,
    CENLEVELEXPORT_OT_pick_path31,
    CENLEVELEXPORT_OT_pick_path32,
    CENLEVELEXPORT_OT_pick_path33,
    CENLEVELEXPORT_OT_pick_path34,
    CENLEVELEXPORT_OT_pick_path35,
    CENLEVELEXPORT_PT_panel,
)


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
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

import bpy
from bpy.props import PointerProperty, StringProperty
from bpy.types import PropertyGroup


# ---------- helpers ----------
def popup_error(msg):
    def draw(self, _):
        self.layout.label(text=msg)

    bpy.context.window_manager.popup_menu(
        draw, title="CenExporter Error!", icon="ERROR"
    )


def popup_info(msg):
    def draw(self, _):
        self.layout.label(text=msg)

    bpy.context.window_manager.popup_menu(draw, title="CenExporter", icon="INFO")


def get_active_collection_objects():
    """Get all mesh objects in the active collection (including children)"""
    active_layer = bpy.context.view_layer.active_layer_collection
    if not active_layer:
        return []

    active_collection = active_layer.collection

    # Recursively get all mesh objects in the collection
    def get_objects_recursive(collection):
        objects = []
        for obj in collection.objects:
            if obj.type == "MESH":
                objects.append(obj)
        for child in collection.children:
            objects.extend(get_objects_recursive(child))
        return objects

    return get_objects_recursive(active_collection)


def export_fbx(filepath, obj):
    """Export a single object to FBX at the specified filepath"""
    # Store current selection state
    prev_selected = [obj for obj in bpy.context.selected_objects]
    prev_active = bpy.context.view_layer.objects.active

    # Store current hide state
    was_hidden = obj.hide_get()

    try:
        # Unhide the object if it's hidden
        if was_hidden:
            obj.hide_set(False)

        # Select only the object we want to export
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj

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
        popup_error(f"Export failed for {obj.name}: {str(e)}")
        return False

    finally:
        # Restore hide state
        if was_hidden:
            obj.hide_set(True)

        # Restore selection state
        bpy.ops.object.select_all(action="DESELECT")
        for obj in prev_selected:
            if obj.name in bpy.data.objects:
                obj.select_set(True)
        if prev_active and prev_active.name in bpy.data.objects:
            bpy.context.view_layer.objects.active = prev_active


def export_to_path(path_property_name, context):
    """Generic export function that uses the path from a property"""
    settings = context.scene.cenexporter
    path = getattr(settings, path_property_name, "")

    if not path:
        popup_error(
            f"No path set for {path_property_name.replace('_path', '').title()}"
        )
        return {"CANCELLED"}

    # Expand blender path variables
    directory = bpy.path.abspath(path)

    # Check if directory exists
    if not os.path.exists(directory):
        popup_error(f"Directory does not exist: {directory}")
        return {"CANCELLED"}

    # Get objects from active collection
    objects = get_active_collection_objects()
    if not objects:
        return {"CANCELLED"}

    # Store all objects' hide states to restore later
    hide_states = {}
    for obj in objects:
        hide_states[obj] = obj.hide_get()

    try:
        # Export each object individually
        success_count = 0
        for obj in objects:
            # Create filename from object name
            filename = f"{obj.name}.fbx"
            filepath = os.path.join(directory, filename)

            if export_fbx(filepath, obj):
                success_count += 1

        # Report results
        if success_count == len(objects):
            popup_info(
                f"Successfully exported all {success_count} objects to:\n{directory}"
            )
        else:
            popup_info(
                f"Exported {success_count} of {len(objects)} objects to:\n{directory}"
            )

        return {"FINISHED"}

    finally:
        # Restore all hide states
        for obj, was_hidden in hide_states.items():
            if obj.name in bpy.data.objects:
                obj.hide_set(was_hidden)


# ---------- operators ----------
class CENEXPORTER_OT_export_path1(bpy.types.Operator):
    bl_idname = "cenexporter.export_path1"
    bl_label = "Export to Path 1"
    bl_options = {"REGISTER"}

    def execute(self, context):
        return export_to_path("path1", context)


class CENEXPORTER_OT_export_path2(bpy.types.Operator):
    bl_idname = "cenexporter.export_path2"
    bl_label = "Export to Path 2"
    bl_options = {"REGISTER"}

    def execute(self, context):
        return export_to_path("path2", context)


class CENEXPORTER_OT_export_path3(bpy.types.Operator):
    bl_idname = "cenexporter.export_path3"
    bl_label = "Export to Path 3"
    bl_options = {"REGISTER"}

    def execute(self, context):
        return export_to_path("path3", context)


class CENEXPORTER_OT_export_path4(bpy.types.Operator):
    bl_idname = "cenexporter.export_path4"
    bl_label = "Export to Path 4"
    bl_options = {"REGISTER"}

    def execute(self, context):
        return export_to_path("path4", context)


class CENEXPORTER_OT_export_path5(bpy.types.Operator):
    bl_idname = "cenexporter.export_path5"
    bl_label = "Export to Path 5"
    bl_options = {"REGISTER"}

    def execute(self, context):
        return export_to_path("path5", context)


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
        return {"FINISHED"}


class CENEXPORTER_OT_pick_path2(bpy.types.Operator):
    bl_idname = "cenexporter.pick_path2"
    bl_label = "Choose Path 2"
    bl_options = {"REGISTER"}

    directory: StringProperty(subtype="DIR_PATH")

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        if self.directory:
            context.scene.cenexporter.path2 = self.directory
        return {"FINISHED"}


class CENEXPORTER_OT_pick_path3(bpy.types.Operator):
    bl_idname = "cenexporter.pick_path3"
    bl_label = "Choose Path 3"
    bl_options = {"REGISTER"}

    directory: StringProperty(subtype="DIR_PATH")

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        if self.directory:
            context.scene.cenexporter.path3 = self.directory
        return {"FINISHED"}


class CENEXPORTER_OT_pick_path4(bpy.types.Operator):
    bl_idname = "cenexporter.pick_path4"
    bl_label = "Choose Path 4"
    bl_options = {"REGISTER"}

    directory: StringProperty(subtype="DIR_PATH")

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        if self.directory:
            context.scene.cenexporter.path4 = self.directory
        return {"FINISHED"}


class CENEXPORTER_OT_pick_path5(bpy.types.Operator):
    bl_idname = "cenexporter.pick_path5"
    bl_label = "Choose Path 5"
    bl_options = {"REGISTER"}

    directory: StringProperty(subtype="DIR_PATH")

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        if self.directory:
            context.scene.cenexporter.path5 = self.directory
        return {"FINISHED"}


# ---------- properties ----------
class CENEXPORTER_PG_settings(PropertyGroup):
    path1: StringProperty(
        name="",
        description="Export directory 1",
        default="",
        subtype="NONE",
    )
    path2: StringProperty(
        name="",
        description="Export directory 2",
        default="",
        subtype="NONE",
    )
    path3: StringProperty(
        name="",
        description="Export directory 3",
        default="",
        subtype="NONE",
    )
    path4: StringProperty(
        name="",
        description="Export directory 4",
        default="",
        subtype="NONE",
    )
    path5: StringProperty(
        name="",
        description="Export directory 5",
        default="",
        subtype="NONE",
    )


# ---------- UI panel ----------
class CENEXPORTER_PT_panel(bpy.types.Panel):
    bl_label = "CenExporter"
    bl_idname = "CENEXPORTER_PT_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Centradigon"

    def draw(self, context):
        layout = self.layout
        settings = context.scene.cenexporter

        # Display active collection
        active_layer = context.view_layer.active_layer_collection
        if active_layer:
            col_name = active_layer.collection.name
            # Count mesh objects
            objects = get_active_collection_objects()
            layout.label(text=f"Active: {col_name}")
            layout.label(text=f"Objects: {len(objects)}")
        else:
            layout.label(text="Active: <none>")

        layout.separator()

        # Path 1
        row = layout.row(align=True)
        row.prop(settings, "path1", text="")
        row.operator("cenexporter.pick_path1", text="", icon="FILE_FOLDER")
        layout.operator("cenexporter.export_path1", icon="EXPORT")
        layout.separator()

        # Path 2
        row = layout.row(align=True)
        row.prop(settings, "path2", text="")
        row.operator("cenexporter.pick_path2", text="", icon="FILE_FOLDER")
        layout.operator("cenexporter.export_path2", icon="EXPORT")
        layout.separator()

        # Path 3
        row = layout.row(align=True)
        row.prop(settings, "path3", text="")
        row.operator("cenexporter.pick_path3", text="", icon="FILE_FOLDER")
        layout.operator("cenexporter.export_path3", icon="EXPORT")
        layout.separator()

        # Path 4
        row = layout.row(align=True)
        row.prop(settings, "path4", text="")
        row.operator("cenexporter.pick_path4", text="", icon="FILE_FOLDER")
        layout.operator("cenexporter.export_path4", icon="EXPORT")
        layout.separator()

        # Path 5
        row = layout.row(align=True)
        row.prop(settings, "path5", text="")
        row.operator("cenexporter.pick_path5", text="", icon="FILE_FOLDER")
        layout.operator("cenexporter.export_path5", icon="EXPORT")


# ---------- registration ----------
classes = (
    CENEXPORTER_PG_settings,
    CENEXPORTER_OT_export_path1,
    CENEXPORTER_OT_export_path2,
    CENEXPORTER_OT_export_path3,
    CENEXPORTER_OT_export_path4,
    CENEXPORTER_OT_export_path5,
    CENEXPORTER_OT_pick_path1,
    CENEXPORTER_OT_pick_path2,
    CENEXPORTER_OT_pick_path3,
    CENEXPORTER_OT_pick_path4,
    CENEXPORTER_OT_pick_path5,
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

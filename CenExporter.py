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

import bpy
from bpy.props import PointerProperty, StringProperty
from bpy.types import PropertyGroup




def ExportFbx(filepath, obj):
    prevSelected = CenLib.GetSelectedObjects()
    prevActive = CenLib.GetActiveObject()
    wasHidden = CenLib.ObjectIsHidden(obj) 

    try:
        CenLib.MakeObjectVisible(obj)
        CenLib.ClearSelection()
        CenLib.SelectObject(obj)

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
        CenLib.PopupError(f"Export failed for {obj.name}: {str(e)}")
        return False

    finally:
        # Restore hide state
        if wasHidden:
            CenLib.MakeObjectHidden(obj)

        # Restore selection state
        CenLib.ClearSelection()
        for obj in prevSelected:
            CenLib.SelectObject(obj)
        
        if CenLib.ObjectExists(prevActive):
            CenLib.SelectObject(prevActive)


def ExportToPath(path_property_name, context):
    if CenLib.IsInLocalView():
        CenLib.PopupError("Exit local view first")
        return CenLib.Cancelled()

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
    objects = CenLib.GetObjectsInCollection(CenLib.GetActiveCollection())
    if not objects:
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

            if ExportFbx(filepath, obj):
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


# ---------- operators ----------
class CENEXPORTER_OT_export_path1(bpy.types.Operator):
    bl_idname = "cenexporter.export_path1"
    bl_label = "Export to Path 1"
    bl_options = {"REGISTER"}

    def execute(self, context):
        return ExportToPath("path1", context)


class CENEXPORTER_OT_export_path2(bpy.types.Operator):
    bl_idname = "cenexporter.export_path2"
    bl_label = "Export to Path 2"
    bl_options = {"REGISTER"}

    def execute(self, context):
        return ExportToPath("path2", context)


class CENEXPORTER_OT_export_path3(bpy.types.Operator):
    bl_idname = "cenexporter.export_path3"
    bl_label = "Export to Path 3"
    bl_options = {"REGISTER"}

    def execute(self, context):
        return ExportToPath("path3", context)


class CENEXPORTER_OT_export_path4(bpy.types.Operator):
    bl_idname = "cenexporter.export_path4"
    bl_label = "Export to Path 4"
    bl_options = {"REGISTER"}

    def execute(self, context):
        return ExportToPath("path4", context)


class CENEXPORTER_OT_export_path5(bpy.types.Operator):
    bl_idname = "cenexporter.export_path5"
    bl_label = "Export to Path 5"
    bl_options = {"REGISTER"}

    def execute(self, context):
        return ExportToPath("path5", context)


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
        return CenLib.Finished()


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
        return CenLib.Finished()


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
        return CenLib.Finished()


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
        return CenLib.Finished()


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
            objects = CenLib.GetObjectsInCollection(CenLib.GetActiveCollection())
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

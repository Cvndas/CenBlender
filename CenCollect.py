bl_info = {
    "name": "CenCollect",
    "author": "Lrodas",
    "version": (1, 0, 0),
    "blender": (4, 0, 0),
    "location": "3D Viewport > Sidebar (N) > Centradigon",
    "description": "Gather and export objects using presets",
    "category": "Import-Export",
}

import bpy
import CenLib
import math
from bpy.props import StringProperty, PointerProperty, FloatProperty, IntProperty, CollectionProperty
from bpy.types import PropertyGroup, Operator, Panel


# ---------- logic functions ----------
def GatherPreset(presetName: str, cellSize: float, outputDirectory: str):
    """Gathers objects based on the preset settings."""
    state = CenLib.TransitionToExportableState()

    activeCollection = CenLib.GetActiveCollection()
    if not activeCollection or activeCollection.name == "Scene Collection":
        CenLib.PopupError("Please select a valid collection")
        return CenLib.Cancelled()
    
    clusterCollection = CenLib.GenerateNewClusteredCollection(activeCollection, cellSize)

    # CenLib.DeleteCollection(clusterCollection)
    elapsed = CenLib.RestoreStateAfterExport(state)
    CenLib.PopupPrint(f"Completed the gathering with preset {presetName} in {elapsed:.3f} seconds!")
    return CenLib.Finished()




def GatherAndExportPreset(presetName: str, cellSize: float, outputDirectory: str):
    """Gathers and exports objects based on the preset settings."""
    print(f"Gathering and Exporting: Preset={presetName}, CellSize={cellSize}, OutDir={outputDirectory}")
    pass


# ---------- properties ----------
class CENCOLLECT_PresetItem(PropertyGroup):
    preset_name: StringProperty(
        name="",
        description="Name of the preset",
        default="",
    )
    cell_size: FloatProperty(
        name="Cell Size",
        description="Cell size for gathering",
        default=1.0,
        min=0.0,
    )


class CENCOLLECT_PG_settings(PropertyGroup):
    output_directory: StringProperty(
        name="Output Directory",
        description="Directory to export files to",
        default="",
        subtype="DIR_PATH",
    )
    presets: CollectionProperty(type=CENCOLLECT_PresetItem)


# ---------- operators ----------
class CENCOLLECT_OT_add_preset(bpy.types.Operator):
    bl_idname = "cencollect.add_preset"
    bl_label = "Add Preset"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        context.scene.cencollect.presets.add()
        return {'FINISHED'}


class CENCOLLECT_OT_remove_preset(bpy.types.Operator):
    bl_idname = "cencollect.remove_preset"
    bl_label = "Remove Preset"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        settings = context.scene.cencollect
        if len(settings.presets) > 0:
            settings.presets.remove(len(settings.presets) - 1)
        return {'FINISHED'}


class CENCOLLECT_OT_gather(bpy.types.Operator):
    bl_idname = "cencollect.gather"
    bl_label = "Gather"
    bl_options = {"REGISTER"}

    index: IntProperty()

    def execute(self, context):
        settings = context.scene.cencollect
        preset = settings.presets[self.index]
        GatherPreset(preset.preset_name, preset.cell_size, settings.output_directory)
        return {'FINISHED'}


class CENCOLLECT_OT_gather_and_export(bpy.types.Operator):
    bl_idname = "cencollect.gather_and_export"
    bl_label = "Gather and Export"
    bl_options = {"REGISTER"}

    index: IntProperty()

    def execute(self, context):
        settings = context.scene.cencollect
        preset = settings.presets[self.index]
        GatherAndExportPreset(preset.preset_name, preset.cell_size, settings.output_directory)
        return {'FINISHED'}


# ---------- UI panel ----------
class CENCOLLECT_PT_panel(bpy.types.Panel):
    bl_label = "CenCollect"
    bl_idname = "CENCOLLECT_PT_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Centradigon"

    def draw(self, context):
        layout = self.layout

        # Metadata box at the top
        box = layout.box()

        # Active Collection
        active_layer = context.view_layer.active_layer_collection
        col_name = active_layer.collection.name if active_layer else "<none>"
        box.label(text=f"Active Collection: {col_name}", icon="OUTLINER_COLLECTION")
        # 
        # # Selected / Active Objects
        # selectedObjects = CenLib.GetSelectedObjects()
        # activeObj = CenLib.GetActiveObject()
        # box.label(text=f"Selected Objects: {len(selectedObjects)}", icon="SELECT_SET")
        # box.label(text=f"Active Object: {activeObj.name if activeObj else '<none>'}", icon="OBJECT_DATA")

        layout.separator()

        settings = context.scene.cencollect

        # Output Directory
        layout.prop(settings, "output_directory")

        layout.separator()

        # Add/Remove buttons
        row = layout.row(align=True)
        row.operator("cencollect.add_preset", icon="ADD")
        row.operator("cencollect.remove_preset", icon="REMOVE")

        layout.separator()

        # Scrollable area with a box for each preset
        col = layout.column(align=True)

        # Only show up to 20 presets at a time to avoid UI overload
        visiblePresets = min(len(settings.presets), 20)

        for i in range(visiblePresets):
            preset = settings.presets[i]

            box = col.box()

            # Preset name row
            row = box.row(align=True)
            row.prop(preset, "preset_name", text="")

            # Cell size row
            row = box.row(align=True)
            row.prop(preset, "cell_size", text="Cell Size")

            # Buttons row
            row = box.row(align=True)
            op1 = row.operator("cencollect.gather", text="Gather", icon="IMPORT")
            op1.index = i
            op2 = row.operator("cencollect.gather_and_export", text="Gather and Export", icon="EXPORT")
            op2.index = i

        # Show message if no presets
        if len(settings.presets) == 0:
            box = col.box()
            box.label(text="No presets configured. Add one with the + button.", icon="INFO")


# ---------- registration ----------
classes = [
    CENCOLLECT_PresetItem,
    CENCOLLECT_PG_settings,
    CENCOLLECT_OT_add_preset,
    CENCOLLECT_OT_remove_preset,
    CENCOLLECT_OT_gather,
    CENCOLLECT_OT_gather_and_export,
    CENCOLLECT_PT_panel,
]


def register():
    for c in classes:
        bpy.utils.register_class(c)
    bpy.types.Scene.cencollect = PointerProperty(type=CENCOLLECT_PG_settings)


def unregister():
    del bpy.types.Scene.cencollect
    for c in reversed(classes):
        bpy.utils.unregister_class(c)


if __name__ == "__main__":
    register()

bl_info = {
    "name": "CenNamer",
    "author": "You",
    "version": (1, 0, 0),
    "blender": (5, 2, 0),
    "location": "View3D > Sidebar > Centradigon",
    "description": "Naming helpers",
    "category": "Object",
}

import bpy
import CenLib


# --- Core logic ---

def NamePrefabPreviews() -> None:
    selected = CenLib.GetSelectedObjects()
    if selected is None or len(selected) == 0:
        CenLib.PopupError("None selected")
        return

    for obj in selected:
        mod = CenLib.GetModifier(obj, "CenUnitify_PrefabPreview", 0)
        if mod:
            objectName = CenLib.GetGeometryNodeField(mod, "Object").value.name
            targetName = objectName.split("-V", 1)[0]
            targetName = targetName.split(-Preview, 1)[0]
            obj.name = targetName


def GiveFoliageValidNames_RemoveLater() -> None:
    selected = CenLib.GetSelectedObjects()
    if selected is None or len(selected) == 0:
        CenLib.PopupError("None selected")
        return

    for obj in selected:
        for mod in list(CenLib.GetModifiers(obj)):
            if CenLib.IsGeonodeModifier(mod) and CenLib.GetGeonodeTypeName(mod) == "InstancePainter":
                originalName = mod.name
                if originalName == "Pebbles_A" or originalName == "Pebbles":
                    mod.name = "Pebbles_OnRoad_A"
                parts = originalName.split("[", 1)
                if len(parts) > 1:
                    newName = f"{parts[0]}_A"
                    mod.name = newName

                newParts = mod.name.split("_A.")
                if len(newParts) > 1:
                    mod.name = f"{newParts[0]}_B"

                newParts = mod.name.split("_B.")
                if len(newParts) > 1:
                    mod.name = f"{newParts[0]}_A"

                itsADuplicate = len(mod.name.split(".0")) > 1
                if itsADuplicate:
                    obj.modifiers.remove(mod)


# --- Operators ---

class CENNAMER_OT_NamePrefabPreview(bpy.types.Operator):
    bl_idname = "cennamer.name_prefab_preview"
    bl_label = "Name Prefab Preview"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        NamePrefabPreviews()
        return {'FINISHED'}


class CENNAMER_OT_GiveFoliageValidNames(bpy.types.Operator):
    bl_idname = "cennamer.give_foliage_valid_names"
    bl_label = "Give Foliage Valid Names"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        GiveFoliageValidNames_RemoveLater()
        return {'FINISHED'}


# --- UI ---

class CENNAMER_PT_Panel(bpy.types.Panel):
    bl_label = "CenNamer"
    bl_idname = "CENNAMER_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Centradigon"

    def draw(self, context):
        layout = self.layout
        layout.operator("cennamer.name_prefab_preview", text="Name Prefab Preview")
        layout.operator("cennamer.give_foliage_valid_names", text="Give Foliage Valid Names_REMOVE_LATER")


classes = (
    CENNAMER_OT_NamePrefabPreview,
    CENNAMER_OT_GiveFoliageValidNames,
    CENNAMER_PT_Panel,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()

bl_info = {
    "name": "CenRandomDupe",
    "author": "Lrodas",
    "version": (1, 0, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Object Context Menu, N Panel > Centradigon",
    "description": "Randomly duplicate selected objects with random transforms",
    "category": "Object",
}

import bpy
import random
import CenLib
from bpy.types import Operator, Panel, PropertyGroup
from bpy.props import FloatProperty


# ---------- properties ----------
class CenRandomDupeProperties(PropertyGroup):
    max_scale_difference: FloatProperty(
        name="Max Scale Difference",
        description="Maximum scale difference (random between 1 - this and 1 + this)",
        default=0.5,
        min=0.01,
        max=1,
        step=0.1,
    )


# ---------- main function ----------
def CenRandomDupe(context):
    props = context.scene.cen_random_dupe_props
    maxScale = 1 + props.max_scale_difference
    minScale = 1 - props.max_scale_difference

    dupeTarget = CenLib.GetActiveObject()
    if not dupeTarget:
        CenLib.PopupError("No object was active")
        return CenLib.Cancelled()

    dupedObject = CenLib.DuplicateObject(dupeTarget, True)

    CenLib.ClearSelection()
    CenLib.SelectObject(dupedObject)

    currentScale = CenLib.GetObjectScale(dupedObject)
    newScaleValue = currentScale.x
    newScaleValue *= random.uniform(minScale, maxScale)

    newScale = currentScale
    newScale.x = newScaleValue
    newScale.y = newScaleValue
    newScale.z = newScaleValue

    currentRotation = CenLib.GetObjectRotation(dupedObject)
    newRotation = currentRotation
    newRotation.z = random.uniform(0, 360)

    CenLib.ModifyScale(dupedObject, newScale)
    CenLib.ModifyRotation(dupedObject, newRotation)

    CenLib.EnterGrabMode()


# ---------- operator ----------
class OBJECT_OT_CenRandomDupe(Operator):
    bl_idname = "object.cen_random_dupe"
    bl_label = "CenRandomDupe"
    bl_description = "Randomly duplicate selected objects with random transforms"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        CenRandomDupe(context)
        return {"FINISHED"}


# ---------- N panel ----------
class VIEW3D_PT_CenRandomDupe(Panel):
    bl_label = "CenRandomDupe"
    bl_idname = "VIEW3D_PT_CenRandomDupe"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Centradigon"

    def draw(self, context):
        layout = self.layout
        props = context.scene.cen_random_dupe_props
        
        layout.prop(props, "max_scale_difference")
        layout.separator()
        layout.operator("object.cen_random_dupe", icon="DUPLICATE")


# ---------- menu registration ----------
def menu_func(self, context):
    self.layout.operator(OBJECT_OT_CenRandomDupe.bl_idname)


# ---------- keymap registration ----------
addon_keymaps = []


# ---------- registration ----------
classes = (
    CenRandomDupeProperties,
    OBJECT_OT_CenRandomDupe,
    VIEW3D_PT_CenRandomDupe,
)


def register():
    for c in classes:
        bpy.utils.register_class(c)
    
    bpy.types.Scene.cen_random_dupe_props = bpy.props.PointerProperty(type=CenRandomDupeProperties)
    
    # Add to object context menu (right-click in object mode)
    bpy.types.VIEW3D_MT_object_context_menu.append(menu_func)
    
    # Add to object menu (top bar)
    bpy.types.VIEW3D_MT_object.append(menu_func)
    
    # Add keymap for Ctrl+D
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        km = kc.keymaps.new(name='Object Mode', space_type='EMPTY')
        kmi = km.keymap_items.new(OBJECT_OT_CenRandomDupe.bl_idname, 'D', 'PRESS', ctrl=True)
        addon_keymaps.append((km, kmi))


def unregister():
    # Remove keymap
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()
    
    # Remove from menus
    bpy.types.VIEW3D_MT_object_context_menu.remove(menu_func)
    bpy.types.VIEW3D_MT_object.remove(menu_func)
    
    del bpy.types.Scene.cen_random_dupe_props
    
    for c in reversed(classes):
        bpy.utils.unregister_class(c)


if __name__ == "__main__":
    register()
bl_info = {
    "name": "CenAnimate",
    "author": "Lrodas",
    "version": (1, 0),
    "blender": (4, 5, 0),
    "location": "View3D > Sidebar > Centradigon Tab",
    "description": "Safely export animations to Unity, for the game \"The Pact of Centradigon\"",
    "category": "Centradigon Tools",
}

import bpy
import CenLib
import time
from bpy.types import Panel, Context
from typing import Type

class CenAnimatePanel(Panel):
    bl_label = "CenAnimate"
    bl_idname = "VIEW3D_PT_CenAnimate"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Centradigon"

    def draw(self, context : Context):
        layout = self.layout
        col_layout = layout.column(align=False)

        col_layout.prop(context.scene, "output_directory_path")
        # col_layout.prop(context.scene, "output_name")

        col_layout.separator_spacer()

        col_layout.operator("wm.export_animation")
        col_layout.operator("wm.export_meshes")



class ExportAnimation(bpy.types.Operator):
    bl_idname = "wm.export_animation"
    bl_label = "Safely Export Animation"

    def execute(self, context):
        if not context.scene.output_directory_path:
            CenLib.PopupError("You forgot to set the output path!")
        else:
            return ExportAnimation(context.scene.output_directory_path)

class ExportMeshes(bpy.types.Operator):
    bl_idname = "wm.export_meshes"
    bl_label = "Export Meshes"

    def execute(self, context):
        if not context.scene.output_directory_path:
            CenLib.PopupError("You forgot to set the output path!")
            return CenLib.Cancelled()
        return ExportMeshes(context.scene.output_directory_path)


classes = [
    ExportAnimation,
    ExportMeshes,
    CenAnimatePanel,
]

def register() -> None:
    for c in classes:
        bpy.utils.register_class(c)


    # Link this prop to scene, accessed in Draw and later
    bpy.types.Scene.output_directory_path = bpy.props.StringProperty(
        name="Output",
        description="Choose the output folder",
        subtype='FILE_PATH'
    )

    # bpy.types.Scene.output_name = bpy.props.StringProperty(
    #     name="Name",
    #     description="The name for the output fbx file"
    # )

    print("Registered CenAnimate...")

def unregister() -> None:
    for c in classes:
        bpy.utils.unregister_class(c)

    del bpy.types.Scene.output_directory_path

    print("Unregistered CenAnimate")








## ::: -------------------------:: Implementation ::------------------------- ::: //

import os





def ExportAnimation(dir : str):
    start = time.time()
    print("Running ExportAnimation()")
    if not dir:
        CenLib.PopupError("Forgot to set output!")
        return CenLib.Cancelled()

    cenAnimateCollection = None

    # First, find all collections with "CenAnimate" in the name
    cenAnimateCollections = CenLib.GetCollectionsByPattern("AnimExport")
    # If exactly one match, use it
    if len(cenAnimateCollections) == 1:
        cenAnimateCollection = cenAnimateCollections[0]
    # If multiple matches, check current selected collection
    elif len(cenAnimateCollections) > 1:
        activeCollection = CenLib.GetActiveCollection()
        if "CenAnimate" in activeCollection.name:
            cenAnimateCollection = activeCollection
        else:
            CenLib.PopupError("Multiple collections contain \"AnimExport\" in their name, and the currently selected collection does not contain \"CenAnimate\"")
            return CenLib.Cancelled()
    # If no matches
    else:
        CenLib.PopupError("Failed to find collection with \"AnimExport\" in its name")
        return CenLib.Cancelled()


    temporarilyExcluded = []
    for dontExport in CenLib.GetCollectionsByPattern("DontExportAnim"):
        if CenLib.CollectionWasExcluded(dontExport) == False:
            CenLib.ExcludeCollection(dontExport)
            temporarilyExcluded.append(dontExport)

    if CenLib.IsInLocalView():
        CenLib.PopupError("You're in local view. Please exit first")
        return CenLib.Cancelled()

    directArmatureObjects = []

    for obj in CenLib.GetObjectsInCollection(cenAnimateCollection):
        if obj.type == "ARMATURE":
            directArmatureObjects.append(obj)

    if len(directArmatureObjects) > 1:
        CenLib.PopupError("Found two competing armature objects in " + cenAnimateCollection.name)
        return CenLib.Cancelled()
    if len(directArmatureObjects) < 1:
        CenLib.PopupError("Didn't find an armature object in " + cenAnimateCollection.name)
        return CenLib.Cancelled()

    armatureObj = directArmatureObjects[0]

    # Hardcoded exception to the rule because Eledon's scale is fucked up...
    # A mistake I don't want to ever make again.
    if any(abs(s - 1.0) > 1e-6 for s in armatureObj.scale) and armatureObj.name != "PlayerArmature" and armatureObj.name != "Armature_SheepRegular" and armatureObj.name != "LredaBothArmature":
        CenLib.PopupError(f"Armature scale wasn't (1, 1, 1), but {armatureObj.scale}")
        return CenLib.Cancelled()


    absoluteDir = bpy.path.abspath(dir)
    if not absoluteDir:
        CenLib.PopupError("Forgot to set output path")
        return CenLib.Cancelled()

    try:
        view_layer_objs = bpy.context.view_layer.objects
        fileName = cenAnimateCollection.name
        filePath = os.path.join(absoluteDir, f"{fileName}.fbx")

        CenLib.EnterObjectMode()
        CenLib.ClearSelection()

        # Being in NLA is known to cause corruption or missing animations
        if CenLib.IsEditingNLA():
            CenLib.PopupError("Please exit the action you're currently editing.")
            return CenLib.Cancelled()

        # Selecting everything to be included in the export
        CenLib.SelectObject(armatureObj)
        for c in armatureObj.children:
            if CenLib.ObjectIsVisible(c):
                CenLib.SelectObject(c)

        bpy.ops.export_scene.fbx(
            filepath=filePath,
            use_selection=True,
            bake_anim_simplify_factor=0.0,
            use_visible=True,
            object_types={"MESH", "ARMATURE"},
            use_triangles=True,
            axis_forward="Y",
            axis_up="Z",
            apply_scale_options="FBX_SCALE_ALL",
            mesh_smooth_type="FACE",
            use_mesh_modifiers=True,
            add_leaf_bones=False,
            bake_anim=True,
            bake_anim_use_all_actions=False,
            bake_anim_use_nla_strips=True,
            path_mode="AUTO",
        )

        for c in armatureObj.children:
            if CenLib.ObjectIsVisible(c):
                CenLib.DeselectObject(c)

        CenLib.ClearSelection()


    except Exception as e:
        CenLib.PopupError("An error occurred: " + str(e))
        return CenLib.Cancelled()

    finally:
        for c in temporarilyExcluded:
            CenLib.IncludeCollection(c)


    end = time.time()
    CenLib.PopupPrint(f"Completed Export Animation! It took {(end - start):.1f} seconds! (We excluded {", ".join([col.name for col in temporarilyExcluded])})")

    return CenLib.Finished()

def ExportMeshes(dir: str):
    start = time.time()

    CenLib.ClearSelection()
    possibleCollections = CenLib.GetCollectionsByPattern("MeshExport")
    if len(possibleCollections) != 1:
        CenLib.PopupError(f"Found {len(possibleCollections)} collections with MeshExport in the name. There should be just one.")
        return CenLib.Cancelled()

    targetCollection = possibleCollections[0]
    CenLib.SetCollectionToActive(targetCollection)

    absoluteDir = bpy.path.abspath(dir)
    if not absoluteDir:
        CenLib.PopupError("Forgot to set output path")
        return CenLib.Cancelled()

    fileName = targetCollection.name
    fullPath = os.path.join(absoluteDir, f"{fileName}.fbx")


    bpy.ops.export_scene.fbx(
        filepath=fullPath,
        use_selection=False,
        use_active_collection=True,
        use_visible=False,
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

    end = time.time()
    CenLib.PopupPrint(f"Completed Export Meshes! It took {(end - start):.1f} seconds!")
    return CenLib.Finished()

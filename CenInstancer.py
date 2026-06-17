bl_info = {
    "name": "CenInstancer",
    "author": "Lrodas",
    "version": (1, 1),
    "blender": (4, 4, 0),
    "location": "View3D > Sidebar > Centradigon Tab",
    "description": "Exporting points to json.",
    "category": "Centradigon Tools",
}

from typing import Type

import bpy
import CenLib
from bpy.types import Context, Panel


# Inheriting from Panel to create out own panel in the side bar.
class CenInstancerPanel(Panel):
    bl_label = "CenInstancer"
    bl_idname = "VIEW3D_PT_Ceninstancer"
    bl_space_type = "VIEW_3D"  # Make it go into the 3D viewport, and...
    bl_region_type = "UI"  # Make it go into the side panel
    bl_category = "Centradigon"  # The name of the side panel category

    def draw(self, context: Context):
        layout = self.layout
        col_layout = layout.column(align=False)
        col_layout.prop(
            context.scene, "output_directory_path"
        )  # Shows a property thats defined in register
        col_layout.prop(
            context.scene, "level_name"
        )  # Shows the property for the level name

        col_layout.separator_spacer()

        col_layout.operator("wm.export_for_selected_objects")
        col_layout.operator("wm.export_for_all_objects")

        col_layout.separator_spacer()

        col_layout.operator("wm.share_instances_throughout_collection")


class PrintOutputPath(bpy.types.Operator):
    bl_idname = "wm.print_output_path"
    bl_label = "Echo absolute output path"

    def execute(self, context):
        if not context.scene.output_directory_path:
            print("You forgot to set the output path!")
        else:
            print(
                "Absolute output path: "
                + bpy.path.abspath(context.scene.output_directory_path)
            )

        return {"FINISHED"}


class ShareInstanceTypesThroughoutCollection(bpy.types.Operator):
    bl_idname = "wm.share_instances_throughout_collection"
    bl_label = "Share Instances"

    def execute(self, context):
        return share_instances()


class ExportForSelectedObjects(bpy.types.Operator):
    bl_idname = "wm.export_for_selected_objects"
    bl_label = "Export Instances: SELECTED"

    def execute(self, context):
        return run_instancer(context, export_mode="SELECTED")


class ExportForAllObjects(bpy.types.Operator):
    bl_idname = "wm.export_for_all_objects"
    bl_label = "Export instances: ALL"

    def execute(self, context):
        return run_instancer(context, export_mode="ALL")


def register() -> None:
    bpy.utils.register_class(CenInstancerPanel)
    bpy.utils.register_class(PrintOutputPath)
    bpy.utils.register_class(ExportForSelectedObjects)
    bpy.utils.register_class(ExportForAllObjects)
    bpy.utils.register_class(ShareInstanceTypesThroughoutCollection)

    # Creates the output path as a string property that lives in the .blend file.
    bpy.types.Scene.output_directory_path = bpy.props.StringProperty(
        name="Output",
        description="Choose the folder corresponding to the level associated with this .blend file..",
        subtype="FILE_PATH",
    )

    bpy.types.Scene.level_name = bpy.props.StringProperty(
        name="Level", description="Write the name of the level"
    )


def unregister() -> None:
    bpy.utils.unregister_class(CenInstancerPanel)
    bpy.utils.unregister_class(PrintOutputPath)
    bpy.utils.unregister_class(ExportForSelectedObjects)
    bpy.utils.unregister_class(ExportForAllObjects)
    bpy.utils.unregister_class(ShareInstanceTypesThroughoutCollection)
    del bpy.types.Scene.output_directory_path
    del bpy.types.Scene.level_name


def RunFromScript() -> None:
    print("Welcome from the script little cro. How are you, little vro?")
    register()


if __name__ == "__main__":
    RunFromScript()


# Enough with the extension boiler plate: Now for the actual code

import json
import os
import time

from mathutils import Vector


def popup_error(msg: str):
    def draw(self, _):
        self.layout.label(text=msg)

    bpy.context.window_manager.popup_menu(
        draw, title="CenInstancer Error!", icon="ERROR"
    )


def _iter_objects_recursive(target_collection, seen_ptrs):
    for obj in target_collection.objects:
        pid = obj.as_pointer()
        if pid not in seen_ptrs:
            seen_ptrs.add(pid)
            yield obj

    # Recursive call into all children
    for child in target_collection.children:
        yield from _iter_objects_recursive(child, seen_ptrs)


def add_unique_instance_painters_to_list(collected_modifiers, host):
    for new_mod in host.modifiers:
        if new_mod.type != "NODES":
            continue

        if not new_mod.node_group or new_mod.node_group.name != "InstancePainter":
            continue

        # Skip it if it already existed
        mod_already_collected = False
        for previous_mod, _ in collected_modifiers:
            if previous_mod.name == new_mod.name:
                mod_already_collected = True
                mod_already_collected = True
                break
        if mod_already_collected:
            continue

        collected_modifiers.append((new_mod, compute_avg_edge_len(host)))


def add_unique_vertex_group_names_to_set(collected_names, host):
    for vertex_group in host.vertex_groups:
        if vertex_group.name not in collected_names:
            collected_names.add(vertex_group.name)


def compute_avg_edge_len(target_obj):
    if target_obj.type != "MESH":
        print("Target object " + target_obj.name + " was not a mesh type object.")
        return 0.0

    mesh_data = target_obj.data

    total_len = 0.0

    if not mesh_data.edges:
        print("Target object " + target_obj.name + "didn't have valid edges.")
        return 0.0

    edge_count = 0
    for edge in mesh_data.edges:
        v1, v2 = (
            mesh_data.vertices[edge.vertices[0]].co,
            mesh_data.vertices[edge.vertices[1]].co,
        )
        total_len += (v2 - v1).length
        edge_count += 1
        if edge_count > 20000:
            break

    average_len = total_len / edge_count
    # print("Average len for object " + target_obj.name + " is " + str(average_len))

    return average_len


def add_all_unique_instance_painters_if_not_already_present(
    unique_instance_painter_modifiers, c
):
    for unique_mod, edge_len_of_original in unique_instance_painter_modifiers:
        modifier_already_present: bool = False
        for existing_mod in c.modifiers:
            if existing_mod.name == unique_mod.name:
                modifier_already_present = True
                break

        if modifier_already_present:
            continue

        # Modifier did not yet exist. Let's copy it, and put it on.
        copied_mod = c.modifiers.new(name=unique_mod.name, type=unique_mod.type)
        copied_mod.show_viewport = False
        copied_mod.show_render = False

        node_tree = unique_mod.node_group
        copied_mod.node_group = node_tree

        # Copying weight paint name
        copied_mod["Socket_10"] = unique_mod["Socket_10"]

        # Copying distance min
        copied_mod["Socket_11"] = unique_mod["Socket_11"]

        # Modifying density according to edge len
        edge_len_of_this = compute_avg_edge_len(c)
        copied_density = unique_mod["Socket_3"]
        raw_difference = edge_len_of_this - edge_len_of_original
        adjusted_difference = raw_difference / 3
        adjusted_this_len = edge_len_of_original + adjusted_difference

        adjusted_density = copied_density * adjusted_this_len / edge_len_of_original
        # adjusted_density = copied_density
        copied_mod["Socket_3"] = adjusted_density


def add_all_unique_vertex_groups_if_not_already_present(
    unique_vertex_group_names, target_object
):
    existing_vertex_group_names = set()
    for existing_vg in target_object.vertex_groups:
        if existing_vg.name not in existing_vertex_group_names:
            existing_vertex_group_names.add(existing_vg.name)

    for unique_vg in unique_vertex_group_names:
        if unique_vg not in existing_vertex_group_names:
            target_object.vertex_groups.new(name=unique_vg)
            existing_vertex_group_names.add(unique_vg)


def share_instances():
    err = {"CANCELLED"}

    old = bpy.context.preferences.edit.use_global_undo
    bpy.context.preferences.edit.use_global_undo = False

    try:
        targetCollection = bpy.context.view_layer.active_layer_collection
        if not targetCollection or not targetCollection.name.endswith("Instances"):
            popup_error(
                "Active collection "
                + targetCollection.name
                + ' does not end with "Instances". Make sure you select the right collection.'
            )
            return err

        seen = set()
        collection_children = [
            c
            for c in _iter_objects_recursive(targetCollection.collection, seen)
            if c.type == "MESH"
        ]

        unique_instance_painter_modifiers = []
        unique_vertex_group_names = set()

        for c in collection_children:
            print("Found child: " + c.name)
            add_unique_instance_painters_to_list(unique_instance_painter_modifiers, c)
            add_unique_vertex_group_names_to_set(unique_vertex_group_names, c)
            print("Gathered instance painters and vertex groups from object " + c.name)

        print("Completed gathering unique instance painters and vertex group names")

        for c in collection_children:
            add_all_unique_instance_painters_if_not_already_present(
                unique_instance_painter_modifiers, c
            )
            add_all_unique_vertex_groups_if_not_already_present(
                unique_vertex_group_names, c
            )
            print("Added instance painters and vertex groups to object " + c.name)

        print("And we're done!")

    finally:
        bpy.context.preferences.edit.use_global_undo = old

    return {"FINISHED"}


def run_instancer(context: Context, export_mode: str):
    output_path = context.scene.output_directory_path
    if not output_path:
        popup_error("Forgot to send output path!")
        return {"CANCELLED"}

    absolute_path = bpy.path.abspath(output_path)
    if not os.path.exists(absolute_path):
        popup_error("Path did not exist.")
        return {"CANCELLED"}
    print("Will put the files in " + absolute_path)

    level_name = context.scene.level_name

    if not level_name:
        popup_error("Forgot to set the level name!")
        return {"CANCELLED"}

    # Get the list of objects to export based on mode
    objects_to_export = []

    if export_mode == "SELECTED":
        objects_to_export = CenLib.GetSelectedObjects()
        if not objects_to_export:
            popup_error("No mesh objects selected!")
            return {"CANCELLED"}
        print(f"Exporting {len(objects_to_export)} selected object(s)")

    elif export_mode == "ALL":
        instancesCollections = CenLib.GetCollectionsByPattern("Instances")
        if len(instancesCollections) == 0:
            CenLib.PopupError(
                "There are no collections that have Instances in the name"
            )
            return CenLib.Cancelled

        # Get all mesh objects in the active collection (including children)

        seen = set()
        objects_to_export = []
        for instCol in instancesCollections:
            for obj in CenLib.GetObjectsInCollection(instCol):
                objects_to_export.append(obj)

        if not objects_to_export:
            CenLib.PopupError("No mesh objects found in the active collection!")
            return CenLib.Cancelled
        print(
            f"Exporting {len(objects_to_export)} object(s) from collections '{', '.join(i.name for i in instancesCollections)}'"
        )

    else:
        popup_error(f"Invalid export mode: {export_mode}")
        return {"CANCELLED"}

    # Delete previous JSON files only for ALL mode
    delete_previous = export_mode == "ALL"

    if export_instances(absolute_path, level_name, objects_to_export, delete_previous):
        return {"FINISHED"}
    else:
        return {"CANCELLED"}


def _unique_seed(seed: int, used: set[int]) -> int:
    s = int(seed) if isinstance(seed, (int, float)) else 0
    while s in used:
        s += 1
    used.add(s)
    return s


def export_instances(
    directory_path, level_name, objects_to_export, delete_previous
) -> bool:
    print("\n=====================\nStart of export_instances_v2\n")
    start_time = time.time()

    if delete_previous:
        delete_previous_json_files(directory_path)

    # Filter objects to only those that have at least one InstancePainter modifier
    inst_obj_list = []
    for obj in objects_to_export:
        has_instance_painter = any(
            mod.type == "NODES"
            and mod.node_group
            and mod.node_group.name == "InstancePainter"
            for mod in obj.modifiers
        )
        if has_instance_painter:
            inst_obj_list.append(obj)

    if not inst_obj_list:
        print("No objects with InstancePainter modifiers found. Aborting")
        return False

    instobj_modlist_tuple = []

    for inst_obj in inst_obj_list:
        instobj_modlist_tuple.append(
            attach_list_of_instance_painter_modifiers(inst_obj)
        )

    print("The instance objects and their instance types: ")
    for inst_obj, modlist in instobj_modlist_tuple:
        print("   " + inst_obj.name + ": " + ", ".join(mod.name for mod in modlist))

    print("\n\n=====GENERATING INSTANCES...=====")
    for inst_obj, modlist in instobj_modlist_tuple:
        object_name = inst_obj.name

        # Little gpt-generated hack to update seed, due to weird for loop. Why did I write such shitty code.
        if "___used_seeds" not in locals():
            ___used_seeds = {}
        used_for_obj = ___used_seeds.setdefault(object_name, set())

        write_coords_with_duping(
            modlist, inst_obj, level_name, directory_path, used_for_obj
        )

    end_time = time.time()
    time_elapsed = end_time - start_time
    print(f"---Done! Time taken: {time_elapsed:.2f} seconds.")
    return True


def write_coords_with_duping(
    modlist, inst_obj, level_name, directory_path, used_for_obj
):
    for mod in modlist:
        bpy.ops.object.select_all(action="DESELECT")

        mod_was_active_before = mod.show_viewport == True
        if mod_was_active_before == False:
            print(
                "Modifier " + mod.name + " was inactive before. Activating it pre-dupe."
            )
            mod.show_viewport = True

        seed_key = "Socket_4"
        current_seed = mod.get(seed_key, 0)
        uniqueSeed = _unique_seed(current_seed, used_for_obj)
        mod[seed_key] = uniqueSeed

        mod["Socket_9"] = True  # Exporting Points for this modifier
        duplicate_object = inst_obj.copy()
        duplicate_object.data = inst_obj.data.copy()
        bpy.context.view_layer.layer_collection.collection.objects.link(
            duplicate_object
        )
        print("Duplicated the object")

        # -- I  think this does nothing, as export-points makes those points exclusive
        # might want to disable all decimate modifiers on the duplicate.
        # for dup_mods in duplicate_object.modifiers:
        #     if dup_mods.type == 'DECIMATE':
        #         dup_mods.show_viewport = False
        #         dup_mods.show_render = False

        # Toggling this back on the original mod now that the dupe is complete.
        mod["Socket_9"] = False

        if mod_was_active_before == False:
            print(
                "Modifier "
                + mod.name
                + " was inactive before. De-activating it post-dupe."
            )
            mod.show_viewport = False

        region = inst_obj.name
        instance_type = mod.name
        file_name = f"{level_name}--{region}--{instance_type}.json"
        file_path = os.path.join(directory_path, file_name)

        inst_obj.select_set(False)
        print("Deselected the original object")

        duplicate_object.select_set(True)
        bpy.context.view_layer.objects.active = duplicate_object
        print("Selected the duplicate object")
        bpy.ops.object.convert(target="MESH", keep_original=False)
        print("Converted the duplicate object to mesh")

        vertex_coordinates = [v.co.copy() for v in duplicate_object.data.vertices]
        for coord in vertex_coordinates:
            coord += duplicate_object.location

        write_vertex_coordinates_to_json(vertex_coordinates, file_path)

        bpy.data.objects.remove(duplicate_object, do_unlink=True)
        bpy.ops.object.delete()
        print("Deleted the duplicate object for this iteration.")
        print("")


def create_list_of_all_instanceable_objects():
    # if it has at least one InstancePainter node group on it, it fits.
    instanceable_objects = [
        obj
        for obj in bpy.data.objects
        if any(
            mod.type == "NODES"
            and mod.node_group
            and mod.node_group.name == "InstancePainter"
            for mod in obj.modifiers
        )
    ]
    return instanceable_objects


def attach_list_of_instance_painter_modifiers(instance_object):
    mod_list = []
    for mod in instance_object.modifiers:
        if mod.type == "NODES" and mod.node_group:
            if mod.node_group.name == "InstancePainter":
                mod_list.append(mod)
    return (instance_object, mod_list)


def write_vertex_coordinates_to_json(vertex_coordinates, file_path):
    positions = {}
    the_array = []
    vertexExists = False
    for v in vertex_coordinates:
        vertexExists = True
        the_array.append({"x": v.x, "y": v.z, "z": v.y})
    positions["Positions"] = the_array

    if vertexExists:
        with open(file_path, "w") as output_json_file:
            json.dump(positions, output_json_file, indent=4)


def delete_previous_json_files(directory_path):
    for old_file in os.listdir(directory_path):
        if old_file.endswith(".json") or old_file.endswith(".json.meta"):
            file_to_remove = os.path.join(directory_path, old_file)
            if os.path.isfile(file_to_remove):
                os.remove(file_to_remove)

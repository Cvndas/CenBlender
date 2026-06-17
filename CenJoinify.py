bl_info = {
    "name": "CenJoinify",
    "author": "Lrodas",
    "version": (1, 0),
    "blender": (4, 5, 0),
    "location": "View3D > Sidebar > Centradigon Tab",
    "description": "Group objects from selected collection into chunks by origin and join them",
    "category": "Centradigon Tools",
}

from collections import defaultdict
from math import floor

import bpy

# ======================== PROPERTIES ========================


class CenJoinifyProperties(bpy.types.PropertyGroup):
    chunk_size: bpy.props.FloatProperty(
        name="Chunk Size",
        description="Size of each chunk in meters",
        default=200.0,
        min=1.0,
        max=1000.0,
        step=10,
        unit="LENGTH",
    )


# ======================== PANEL ========================


class CENTRADIGON_PT_CenJoinify(bpy.types.Panel):
    bl_label = "CenJoinify"
    bl_idname = "VIEW3D_PT_CenJoinify"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Centradigon"

    def draw(self, context):
        layout = self.layout
        props = context.scene.cenjoinify_props

        # Show currently selected collection
        selected_collection = None
        if hasattr(bpy.context, "collection") and bpy.context.collection:
            selected_collection = bpy.context.collection
        else:
            selected_collection = bpy.context.scene.collection

        box = layout.box()
        box.label(
            text=f"Selected: {selected_collection.name}", icon="OUTLINER_COLLECTION"
        )

        layout.separator()

        col = layout.column(align=True)
        col.prop(props, "chunk_size")

        col.separator()

        row = col.row(align=True)
        row.operator("cenjoinify.scan_collection", icon="VIEWZOOM")
        row.operator("cenjoinify.join_by_chunk", icon="AUTOMERGE_ON")


# ======================== OPERATORS ========================


def get_chunk_key(location, chunk_size):
    """Return chunk coordinates (x, y, z) for a given location"""
    x = floor(location.x / chunk_size)
    y = floor(location.y / chunk_size)
    z = floor(location.z / chunk_size)
    return (x, y, z)


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


class CENJOINIFY_OT_ScanCollection(bpy.types.Operator):
    """Scan the selected collection and report how many objects per chunk"""

    bl_idname = "cenjoinify.scan_collection"
    bl_label = "Scan Collection"
    bl_description = "Scan the selected collection and report chunk distribution"

    def execute(self, context):
        props = context.scene.cenjoinify_props

        # Get selected collection
        if hasattr(bpy.context, "collection") and bpy.context.collection:
            target_collection = bpy.context.collection
        else:
            target_collection = bpy.context.scene.collection

        if not target_collection:
            self.report(
                {"ERROR"}, "No collection selected. Select one in the Outliner."
            )
            return {"CANCELLED"}

        # Get all mesh objects
        objects = get_objects_from_collection(target_collection)

        if not objects:
            self.report(
                {"WARNING"}, f"No mesh objects found in '{target_collection.name}'"
            )
            return {"CANCELLED"}

        # Group by chunk
        chunks = defaultdict(list)
        chunk_size = props.chunk_size

        for obj in objects:
            key = get_chunk_key(obj.location, chunk_size)
            chunks[key].append(obj)

        # Report results
        self.report(
            {"INFO"},
            f"Collection '{target_collection.name}': {len(objects)} objects, {len(chunks)} chunks",
        )

        # Print detailed report to console
        print(f"\n=== CenJoinify Scan: {target_collection.name} ===")
        print(f"Chunk size: {chunk_size}m")
        print(f"Total objects: {len(objects)}")
        print(f"Total chunks: {len(chunks)}")
        print("\nChunk distribution:")

        joinable = 0
        singles = 0

        for key, obj_list in sorted(chunks.items()):
            count = len(obj_list)
            if count >= 2:
                joinable += count
                print(f"  {key}: {count} objects (will be joined into 1 object)")
            else:
                singles += 1
                print(f"  {key}: {count} object (will be renamed)")

        print(f"\nSummary:")
        print(f"  Objects to join: {joinable}")
        print(f"  Single objects: {singles}")
        print("=" * 50)

        return {"FINISHED"}


class CENJOINIFY_OT_JoinByChunk(bpy.types.Operator):
    """Join objects by chunk and rename all objects"""

    bl_idname = "cenjoinify.join_by_chunk"
    bl_label = "Join by Chunk"
    bl_description = "Join all objects in the same chunk and rename them"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        props = context.scene.cenjoinify_props

        # Get selected collection
        if hasattr(bpy.context, "collection") and bpy.context.collection:
            target_collection = bpy.context.collection
        else:
            target_collection = bpy.context.scene.collection

        if not target_collection:
            self.report(
                {"ERROR"}, "No collection selected. Select one in the Outliner."
            )
            return {"CANCELLED"}

        # Get all mesh objects
        objects = get_objects_from_collection(target_collection)

        if not objects:
            self.report(
                {"WARNING"}, f"No mesh objects found in '{target_collection.name}'"
            )
            return {"CANCELLED"}

        # Group by chunk
        chunks = defaultdict(list)
        chunk_size = props.chunk_size

        for obj in objects:
            key = get_chunk_key(obj.location, chunk_size)
            chunks[key].append(obj)

        # Store original mode
        original_mode = context.mode

        # Switch to object mode if needed
        if original_mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")

        # Track processed objects
        processed_names = set()
        collection_name = target_collection.name

        # Join chunks with 2+ objects
        chunk_index = 1

        for chunk_key, obj_list in chunks.items():
            if len(obj_list) < 2:
                continue

            self.report(
                {"INFO"}, f"Joining {len(obj_list)} objects in chunk {chunk_key}"
            )

            # Deselect all
            bpy.ops.object.select_all(action="DESELECT")

            # Select all objects in this chunk
            for obj in obj_list:
                if obj.name in bpy.data.objects:
                    obj.select_set(True)
                    processed_names.add(obj.name)

            # Set active object
            if obj_list and obj_list[0].name in bpy.data.objects:
                context.view_layer.objects.active = obj_list[0]

            # Join them
            bpy.ops.object.join()

            # Rename the joined object - single object represents whole chunk
            if context.active_object:
                context.active_object.name = (
                    f"{collection_name}[{chunk_index}_joined]-V_LOD0"
                )
                processed_names.add(context.active_object.name)

            chunk_index += 1

        # Rename single objects (chunks with 1 object)
        for chunk_key, obj_list in chunks.items():
            if len(obj_list) != 1:
                continue

            obj = obj_list[0]
            if obj.name in bpy.data.objects and obj.name not in processed_names:
                # For single objects, it's object 1 of 1 in its chunk
                obj.name = f"{collection_name}[{chunk_index}_1]-V_LOD0"
                processed_names.add(obj.name)
                chunk_index += 1

        # Final report
        self.report(
            {"INFO"},
            f"Done! Processed {len(chunks)} chunks, renamed {len(processed_names)} objects",
        )

        print(f"\n=== CenJoinify Complete ===")
        print(f"Collection: {collection_name}")
        print(f"Total chunks processed: {len(chunks)}")
        print(f"Total objects after operation: {len(processed_names)}")
        print("=" * 40)

        return {"FINISHED"}


# ======================== REGISTRATION ========================

classes = [
    CenJoinifyProperties,
    CENTRADIGON_PT_CenJoinify,
    CENJOINIFY_OT_ScanCollection,
    CENJOINIFY_OT_JoinByChunk,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.cenjoinify_props = bpy.props.PointerProperty(
        type=CenJoinifyProperties
    )
    print("Registered CenJoinify")


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    del bpy.types.Scene.cenjoinify_props
    print("Unregistered CenJoinify")


if __name__ == "__main__":
    register()

"""
Ekspor aset vegetasi ke GLB untuk pratinjau 3D di Remotion.

Jalankan dari root repo:
    "D:\\Blender Foundation\\Blender 5.2\\blender.exe" -b assets\\env\\vegetation.blend ^
        --python scripts\\export-vegetation-glb.py

Hasil:
    motion/public/models/env-palm.glb
    motion/public/models/env-mangrove.glb

Origin kedua aset dikembalikan ke (0, 0, 0) saat ekspor, supaya di three.js
tinggal ditempatkan memakai koordinat Blender lewat B(x, y, z) = [x, z, -y].
"""

import bpy
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "motion", "public", "models")
os.makedirs(OUT_DIR, exist_ok=True)


def deselect_all():
    for obj in bpy.context.view_layer.objects:
        obj.select_set(False)


def export_collection(collection_name, filepath, offset_to_origin=()):
    collection = bpy.data.collections[collection_name]
    objects = [obj for obj in collection.objects if obj.type == "MESH"]

    saved = {obj.name: obj.location.copy() for obj in objects}
    if offset_to_origin:
        for obj in objects:
            obj.location = offset_to_origin

    deselect_all()
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]

    bpy.ops.export_scene.gltf(
        filepath=filepath,
        export_format="GLB",
        use_selection=True,
        export_apply=True,
        export_animations=False,
        export_yup=True,
    )

    for obj in objects:
        obj.location = saved[obj.name]
    deselect_all()
    print("EXPORTED", filepath, "objects", [obj.name for obj in objects])


export_collection(
    "ENV_veg_coconut-palm",
    os.path.join(OUT_DIR, "env-palm.glb"),
)
export_collection(
    "ENV_veg_mangrove",
    os.path.join(OUT_DIR, "env-mangrove.glb"),
    offset_to_origin=(0.0, 0.0, 0.0),
)

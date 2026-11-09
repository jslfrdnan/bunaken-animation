"""
Ekspor ulang `env-surface.glb` dari `assets/env/surface.blend` setelah
pohon placeholder diganti.

Jalankan dari root repo:
    "D:\\Blender Foundation\\Blender 5.2\\blender.exe" -b assets\\env\\surface.blend ^
        --python scripts\\export-surface-glb.py

Hasil: motion/public/models/env-surface.glb
"""

import bpy
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "motion", "public", "models", "env-surface.glb")

collection = bpy.data.collections["ENV_surface"]
objects = [
    obj
    for obj in collection.objects
    if obj.type == "MESH" and obj.name != "ENV_surface_water-placeholder"
]

for obj in bpy.context.view_layer.objects:
    obj.select_set(False)
for obj in objects:
    obj.select_set(True)
bpy.context.view_layer.objects.active = objects[0]

os.makedirs(os.path.dirname(OUT), exist_ok=True)
bpy.ops.export_scene.gltf(
    filepath=OUT,
    export_format="GLB",
    use_selection=True,
    export_apply=True,
    export_animations=False,
    export_yup=True,
)
print("EXPORTED", OUT, "objects", len(objects))
print("MESHES", len(bpy.data.meshes), "MATERIALS", len(bpy.data.materials))

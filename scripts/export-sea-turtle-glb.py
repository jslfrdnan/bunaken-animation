"""
Ekspor `assets/env/sea_turtle.blend` ke `motion/public/models/sea-turtle.glb`.

Jalankan dari root repo:
    "D:\\Blender Foundation\\Blender 5.2\\blender.exe" -b assets\\env\\sea_turtle.blend ^
        --python scripts\\export-sea-turtle-glb.py
"""

import bpy
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "motion", "public", "models", "sea-turtle.glb")

objects = [
    obj
    for obj in bpy.data.objects
    if obj.type == "MESH" and obj.name != "Ground"
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

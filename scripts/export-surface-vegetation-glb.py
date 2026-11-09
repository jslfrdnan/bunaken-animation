"""
Ekspor `surface-vegetation.blend` ke `env-surface.glb` untuk pratinjau
Remotion: pulau + 360 kelapa + 40 mangrove.

Latar `ENV_veg_mangrove-bg` (1.450 pohon mangrove penuh, ~14 juta vertex)
sengaja tidak ikut: untuk pratinjau three.js itu terlalu berat. Latar tetap
ada di file Blender untuk render final.

Jalankan dari root repo:
    "D:\\Blender Foundation\\Blender 5.2\\blender.exe" -b assets\\env\\surface-vegetation.blend ^
        --python scripts\\export-surface-vegetation-glb.py

Hasil: motion/public/models/env-surface.glb
"""

import bpy
import os
import shutil
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "motion", "public", "models", "env-surface.glb")
BACKUP = os.path.join(tempfile.gettempdir(), "env-surface-before-vegetation.glb")

if os.path.exists(OUT):
    shutil.copy2(OUT, BACKUP)
    print("BACKUP", BACKUP)

targets = [
    obj
    for obj in bpy.data.collections["ENV_surface"].objects
    if obj.type == "MESH" and obj.name != "ENV_surface_water-placeholder"
]
targets += [
    obj
    for obj in bpy.data.collections["ENV_veg_palms"].objects
    if obj.type == "MESH"
]
targets += [
    obj
    for obj in bpy.data.collections["ENV_veg_mangroves"].objects
    if obj.type == "MESH"
]

bpy.ops.object.select_all(action="DESELECT")
for obj in targets:
    obj.select_set(True)
bpy.context.view_layer.objects.active = targets[0]

os.makedirs(os.path.dirname(OUT), exist_ok=True)
bpy.ops.export_scene.gltf(
    filepath=OUT,
    export_format="GLB",
    use_selection=True,
    export_apply=True,
    export_animations=False,
    export_yup=True,
)
print("EXPORTED", OUT, "objects", len(targets))

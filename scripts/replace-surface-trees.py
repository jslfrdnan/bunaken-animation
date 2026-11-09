"""
Ganti 26 objek `ENV_surface_tree_*` placeholder di surface.blend dengan
pohon kelapa/mangrove dari vegetation.blend.

Jalankan dari root repo:
    "D:\\Blender Foundation\\Blender 5.2\\blender.exe" -b ^
        --python scripts/replace-surface-trees.py

Hasil: assets/env/surface.blend (langsung ditimpa; backup di folder temp)
"""

import bpy
import math
import os
import random
import shutil
import tempfile
from mathutils import Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SURFACE = os.path.join(ROOT, "assets", "env", "surface.blend")
VEGETATION = os.path.join(ROOT, "assets", "env", "vegetation.blend")

BACKUP = os.path.join(tempfile.gettempdir(), "surface-before-trees-v2.blend")
shutil.copy2(SURFACE, BACKUP)
print("BACKUP", BACKUP)

bpy.ops.wm.open_mainfile(filepath=SURFACE)
scene = bpy.context.scene
collection = bpy.data.collections["ENV_surface"]
island = bpy.data.objects["ENV_surface_island"]

# ---------------------------------------------------------------------------
# impor aset vegetasi
# ---------------------------------------------------------------------------

with bpy.data.libraries.load(VEGETATION, link=False) as (source, target):
    target.objects = [
        "ENV_veg_palm-trunk",
        "ENV_veg_palm-fronds",
        "ENV_veg_palm-coconuts",
        "ENV_veg_mangrove-wood",
        "ENV_veg_mangrove-canopy",
    ]

temp = bpy.data.collections.new("TEMP_import")
scene.collection.children.link(temp)
for obj in target.objects:
    temp.objects.link(obj)


def join_parts(objects, name):
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.object.join()
    joined = bpy.context.view_layer.objects.active
    joined.name = name
    return joined


palm_parts = [
    bpy.data.objects["ENV_veg_palm-trunk"],
    bpy.data.objects["ENV_veg_palm-fronds"],
    bpy.data.objects["ENV_veg_palm-coconuts"],
]
palm = join_parts(palm_parts, "ENV_surface_palm")

mangrove_parts = [
    bpy.data.objects["ENV_veg_mangrove-wood"],
    bpy.data.objects["ENV_veg_mangrove-canopy"],
]
# di vegetation.blend mangrove digeser ke x=14 untuk pratinjau; kembalikan ke 0
for obj in mangrove_parts:
    obj.location = (0.0, 0.0, 0.0)
mangrove = join_parts(mangrove_parts, "ENV_surface_mangrove")

for obj in (palm, mangrove):
    temp.objects.unlink(obj)
    collection.objects.link(obj)

bpy.data.collections.remove(temp)

# pastikan origin gabungan ada di pangkal batang
for obj in (palm, mangrove):
    obj.location = (0.0, 0.0, 0.0)
    obj.rotation_euler = (0.0, 0.0, 0.0)
    obj.scale = (1.0, 1.0, 1.0)

# ---------------------------------------------------------------------------
# ganti placeholder
# ---------------------------------------------------------------------------

trees = sorted(
    (obj for obj in collection.objects if obj.name.startswith("ENV_surface_tree_")),
    key=lambda obj: obj.name,
)
print("PLACEHOLDERS", len(trees))

random.seed(20261108)


def add_tree(source, name, x, y, sxz, sz):
    hit, location, normal, index = island.ray_cast(
        Vector((x, y, 150.0)), Vector((0.0, 0.0, -1.0))
    )
    if not hit or location.z < 0.05:
        print("SKIP", name, round(x, 1), round(y, 1))
        return None

    new = source.copy()
    new.data = source.data  # mesh dipakai bersama, bukan diduplikasi
    new.name = name
    collection.objects.link(new)
    new.location = (x, y, location.z - 0.06)
    new.rotation_mode = "XYZ"
    new.rotation_euler = (0.0, 0.0, random.uniform(0.0, math.tau))
    new.scale = (sxz, sxz, sz)
    return new


# 26 placeholder diganti pohon kelapa; skala Z lebih besar supaya tinggi
# batang realistis (15-17 m) dan tajuknya tidak ikut melebar berlebihan.
for old in trees:
    suffix = old.name.rsplit("_", 1)[-1]
    x, y, _ = old.location
    add_tree(
        palm,
        f"ENV_surface_palm_{suffix}",
        x,
        y,
        random.uniform(1.15, 1.35),
        random.uniform(1.45, 1.75),
    )
    bpy.data.objects.remove(old, do_unlink=True)

# deretan tambahan di pantai dan lereng supaya terlihat dari kamera aerial
EXTRA_PALMS = [
    (-120, 8),
    (-105, 6),
    (-90, 10),
    (-75, 5),
    (-60, 9),
    (-45, 6),
    (65, 7),
    (80, 9),
    (95, 6),
    (110, 10),
    (-80, 25),
    (-60, 30),
    (-50, 28),
    (60, 30),
    (80, 26),
    (-120, 60),
    (-70, 70),
    (-20, 60),
    (30, 55),
    (90, 65),
    (130, 50),
    (-140, 90),
    (0, 90),
    (70, 100),
]
for index, (x, y) in enumerate(EXTRA_PALMS):
    add_tree(
        palm,
        f"ENV_surface_palm_x{index:02d}",
        x,
        y,
        random.uniform(1.10, 1.30),
        random.uniform(1.35, 1.65),
    )

# mangrove di garis air, jauh dari dermaga dan kampung
EXTRA_MANGROVES = [(-130, 3), (-115, 2), (-100, 3), (70, 3), (85, 2), (100, 3)]
for index, (x, y) in enumerate(EXTRA_MANGROVES):
    add_tree(
        mangrove,
        f"ENV_surface_mangrove_{index:02d}",
        x,
        y,
        random.uniform(1.00, 1.20),
        random.uniform(1.10, 1.35),
    )

# objek sumber tidak dipakai lagi; hapus supaya tidak ikut terekspor
bpy.data.objects.remove(palm, do_unlink=True)
bpy.data.objects.remove(mangrove, do_unlink=True)

bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=SURFACE)
print("SAVED", SURFACE)
print("TREES", len([o for o in collection.objects if o.name.startswith("ENV_surface_palm_") or o.name.startswith("ENV_surface_mangrove_")]))

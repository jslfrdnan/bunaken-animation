"""
Tambah dua spesies ikan terumbu ke reef.blend:
  ENV_reef_fish_damselfish  (kuning, dari geometri goropa)
  ENV_reef_fish_surgeon    (hitam, dari geometri goropa)

Jalankan dari root repo:
    "D:\\Blender Foundation\\Blender 5.2\\blender.exe" -b ^
        --python scripts/add-reef-fish.py
"""

import bpy
import os
import shutil
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REEF = os.path.join(ROOT, "assets", "env", "reef.blend")
BACKUP = os.path.join(tempfile.gettempdir(), "reef-before-fish.blend")

shutil.copy2(REEF, BACKUP)
print("BACKUP", BACKUP)

bpy.ops.wm.open_mainfile(filepath=REEF)
collection = bpy.data.collections["ENV_reef"]


def srgb(hexstr):
    h = hexstr.lstrip("#")
    values = [int(h[i : i + 2], 16) / 255.0 for i in (0, 2, 4)]

    def to_linear(u):
        return u / 12.92 if u <= 0.04045 else ((u + 0.055) / 1.055) ** 2.4

    return tuple(to_linear(v) for v in values) + (1.0,)


def material(name, hexcol, roughness=0.55):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.diffuse_color = srgb(hexcol)
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = srgb(hexcol)
    bsdf.inputs["Roughness"].default_value = roughness
    return mat


body = bpy.data.objects["ENV_reef_fish_goropa-merah"]


def add_species(suffix, body_hex, fin_hex, location):
    bpy.ops.object.select_all(action="DESELECT")
    body.select_set(True)
    for child in body.children:
        child.select_set(True)
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.duplicate(linked=False)

    dup = bpy.context.view_layer.objects.active
    dup.name = f"ENV_reef_fish_{suffix}"
    dup.data.name = f"ENV_reef_{suffix}_body"
    dup.location = location

    for child in dup.children:
        if "dorsal" in child.name:
            child.name = f"ENV_reef_fish_{suffix}_dorsal"
        elif "tail" in child.name:
            child.name = f"ENV_reef_fish_{suffix}_tail"

    body_mat = material(f"MAT_fish_{suffix}", body_hex)
    fin_mat = material(f"MAT_fin_{suffix}", fin_hex)
    dup.data.materials.clear()
    dup.data.materials.append(body_mat)
    for child in dup.children:
        child.data.materials.clear()
        child.data.materials.append(fin_mat)

    print("ADDED", dup.name, [c.name for c in dup.children])


add_species("damselfish", "#D9A62E", "#C9972E", (2.4, -1.5, 0.8))
add_species("surgeon", "#2B2B33", "#22222A", (3.4, -0.7, 1.1))

bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=REEF)
print("SAVED", REEF)

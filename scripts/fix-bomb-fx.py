"""
Menurunkan intensitas FX ledakan Scene 2 shot 020 agar tidak neon.

- MAT_fx_ring  : cyan terang -> krem tulang #F2E9DC, emission 1,4
- MAT_fx_flash : flash putih penuh -> krem, emission 3,0 dan ukuran diperkecil
"""

import bpy

FILE = r"D:/Tugas Semester 5/Grafika Komputer/Project-Animasi/scenes/scene-2_shot-020_bom_v001.blend"


def srgb(hexstr):
    h = hexstr.lstrip("#")
    vals = [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]

    def lin(u):
        return u / 12.92 if u <= 0.04045 else ((u + 0.055) / 1.055) ** 2.4

    return tuple(lin(v) for v in vals) + (1.0,)


bpy.ops.wm.open_mainfile(filepath=FILE)

ring = bpy.data.materials.get("MAT_fx_ring")
if ring and ring.use_nodes:
    for n in ring.node_tree.nodes:
        if n.type in {"BSDF_PRINCIPLED", "EMISSION"}:
            col = n.inputs.get("Color") or n.inputs.get("Base Color")
            if col:
                col.default_value = srgb("#F2E9DC")
            for key in ("Emission Color", "Emission Strength", "Strength", "Alpha"):
                inp = n.inputs.get(key)
                if inp is not None:
                    inp.default_value = 1.4 if key != "Alpha" else 0.55
    print("ring diubah")

flash = bpy.data.materials.get("MAT_fx_flash")
if flash and flash.use_nodes:
    for n in flash.node_tree.nodes:
        if n.type in {"BSDF_PRINCIPLED", "EMISSION"}:
            col = n.inputs.get("Color") or n.inputs.get("Base Color")
            if col:
                col.default_value = srgb("#F2E9DC")
            for key in ("Emission Strength", "Strength"):
                inp = n.inputs.get(key)
                if inp is not None:
                    inp.default_value = 3.0
    print("flash diubah")

# perkecil bola kilatan
for ob in bpy.data.objects:
    if ob.name.startswith("FX_flash"):
        ob.scale = tuple(s * 0.6 for s in ob.scale)
        print("flash obj", ob.name, "diperkecil")

bpy.ops.wm.save_as_mainfile(filepath=FILE)
print("SAVED", FILE)

"""Generator awan low-poly buatan sendiri untuk scene 1 (langit pagi Bunaken).

Awan dibuat dengan menggabungkan beberapa ico-sphere low-poly menjadi gumpalan
(cumulus) yang pipih di bawah dan menggembung di atas, lalu di-flat-shade dan diberi
sedikit noise displacement agar siluetnya bergerigi khas low-poly. Bukan aset pihak
ketiga — memenuhi syarat "unsur grafika buatan sendiri".

Jalankan di dalam Blender (aset.blend terbuka):
    exec(open(r"D:\\Tugas Semester 5\\Grafika Komputer\\Project\\skrip\\awan_lowpoly.py").read())
atau lewat Blender MCP. Fungsi utama: buat_awan_set() -> membuat collection "Aset_Awan"
berisi 3 variasi awan (Awan_A/B/C) yang bisa di-link & disebar di scene 1.
"""
import random

import bpy
from mathutils import Vector

PALET_AWAN = (0.92, 0.94, 0.97, 1.0)  # putih kebiruan lembut, selaras palet langit pagi


def _material_awan():
    mat = bpy.data.materials.get("M_Awan")
    if mat:
        return mat
    mat = bpy.data.materials.new("M_Awan")
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = PALET_AWAN
    # sedikit emisi agar awan tetap cerah di sisi bayangan (gaya low-poly, bukan PBR ketat)
    if "Emission Color" in bsdf.inputs:
        bsdf.inputs["Emission Color"].default_value = PALET_AWAN
        bsdf.inputs["Emission Strength"].default_value = 0.08
    for nama in ("Roughness",):
        if nama in bsdf.inputs:
            bsdf.inputs[nama].default_value = 1.0
    return mat


def _satu_awan(nama, gumpalan, seed):
    """Buat satu awan dengan menggabungkan beberapa ico-sphere low-poly lalu join."""
    rng = random.Random(seed)
    potongan = []
    for gx, gy, gz, r in gumpalan:
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=r, location=(gx, gy, gz))
        o = bpy.context.active_object
        # pipihkan alas: tekan vertex di bawah pusat gumpalan agar dasar awan rata
        for v in o.data.vertices:
            if v.co.z < 0:
                v.co.z *= 0.35
        o.scale.z = rng.uniform(0.75, 0.95)
        potongan.append(o)
    for o in bpy.context.selected_objects:
        o.select_set(False)
    for o in potongan:
        o.select_set(True)
    bpy.context.view_layer.objects.active = potongan[0]
    bpy.ops.object.join()
    awan = bpy.context.active_object
    awan.name = nama
    awan.data.name = nama
    # gabung vertex berdekatan & flat shade
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.remove_doubles(threshold=0.08)
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.shade_flat()
    # origin ke dasar tengah
    bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="BOUNDS")
    awan.data.materials.clear()
    awan.data.materials.append(_material_awan())
    return awan


def buat_awan_set():
    sc = bpy.context.scene
    if "Aset_Awan" not in bpy.data.collections:
        c = bpy.data.collections.new("Aset_Awan"); sc.collection.children.link(c)
    tgt = bpy.data.collections["Aset_Awan"]

    # 3 variasi gumpalan: (x, y, z, radius) relatif, satuan meter
    variasi = {
        "Awan_A": [(0, 0, 0, 2.2), (2.4, 0.3, 0.4, 1.7), (-2.2, -0.2, 0.3, 1.9),
                   (1.1, 0.1, 1.1, 1.5), (-0.9, 0.2, 1.0, 1.3)],
        "Awan_B": [(0, 0, 0, 1.6), (1.6, 0.0, 0.2, 1.3), (-1.5, 0.1, 0.2, 1.4),
                   (0.3, 0.1, 0.9, 1.1)],
        "Awan_C": [(0, 0, 0, 3.0), (3.2, 0.2, 0.3, 2.2), (-3.0, -0.1, 0.3, 2.4),
                   (6.0, 0.0, 0.1, 1.6), (-5.6, 0.1, 0.1, 1.5), (1.4, 0.2, 1.4, 1.8)],
    }
    dibuat = []
    for i, (nama, gumpalan) in enumerate(variasi.items()):
        if nama in bpy.data.objects:
            bpy.data.objects.remove(bpy.data.objects[nama])
        awan = _satu_awan(nama, gumpalan, seed=100 + i)
        for c in list(awan.users_collection):
            c.objects.unlink(awan)
        tgt.objects.link(awan)
        awan.location = Vector((i * 12 - 12, 30, 18))  # dijajarkan untuk pratinjau
        dibuat.append(awan.name)
    return dibuat


if __name__ == "__main__":
    print("Awan dibuat:", buat_awan_set())

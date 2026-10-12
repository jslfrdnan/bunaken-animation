"""Poles aset bersama di aset.blend (dijalankan di Blender saat aset.blend terbuka).

- Perahu  : tambah cadik (outrigger) + mesin → katinting
- Rumah   : angkat jadi panggung + tiang + atap seng + dinding kayu
- Papan   : tambah teks "TAMAN NASIONAL BUNAKEN"
- Dermaga : tint railing biru-abu → kayu
- Semua   : flat shading

Idempoten: objek tambahan diberi awalan "MOD_" dan dihapus dulu bila skrip diulang.
Catatan: banyak aset memakai tekstur gambar, jadi penyeragaman warna penuh via base
color tidak mungkin; nada natural (kayu/hijau) yang ada sudah cukup menyatu.
"""
import math

import bpy
import bmesh
from mathutils import Vector


def flat_material(nama, warna, rough=1.0, metal=0.0, emis=None):
    mat = bpy.data.materials.get(nama)
    if mat is None:
        mat = bpy.data.materials.new(nama)
        mat.use_nodes = True
    b = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (*warna, 1.0)
    if "Roughness" in b.inputs: b.inputs["Roughness"].default_value = rough
    if "Metallic" in b.inputs: b.inputs["Metallic"].default_value = metal
    if emis and "Emission Color" in b.inputs:
        b.inputs["Emission Color"].default_value = (*emis, 1.0)
        b.inputs["Emission Strength"].default_value = 1.0
    return mat


def _cyl(coll, nama, p0, p1, r, mat, seg=8):
    p0, p1 = Vector(p0), Vector(p1)
    axis = p1 - p0
    length = axis.length
    me = bpy.data.meshes.new(nama)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r, radius2=r, depth=length)
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(nama, me)
    o.data.materials.append(mat)
    # arahkan +Z ke axis
    o.rotation_mode = "QUATERNION"
    o.rotation_quaternion = axis.to_track_quat("Z", "Y")
    o.location = (p0 + p1) / 2
    for p in me.polygons: p.use_smooth = False
    coll.objects.link(o)
    return o


def _box(coll, nama, center, size, mat):
    me = bpy.data.meshes.new(nama)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(nama, me)
    o.scale = size
    o.location = center
    o.data.materials.append(mat)
    for p in me.polygons: p.use_smooth = False
    coll.objects.link(o)
    return o


def _hapus_mod(coll):
    for o in list(coll.objects):
        if o.name.startswith("MOD_"):
            bpy.data.objects.remove(o, do_unlink=True)


def poles_perahu():
    c = bpy.data.collections["Aset_Perahu"]
    _hapus_mod(c)
    cx, cy = 34.0, 0.0
    bambu = flat_material("MOD_Bambu", (0.80, 0.68, 0.40))
    kayu = flat_material("MOD_KayuGelap", (0.42, 0.26, 0.14))
    mesin_m = flat_material("MOD_Mesin", (0.14, 0.14, 0.16))
    merah = flat_material("MOD_MerahMesin", (0.6, 0.12, 0.1))
    ztop = 0.18
    # dua boom melintang (X) di depan & belakang
    for j, by in enumerate((cy - 1.2, cy + 1.2)):
        _cyl(c, f"MOD_Boom_{j}", (cx - 2.5, by, ztop), (cx + 2.5, by, ztop), 0.06, bambu)
    # dua pelampung (ama) sejajar lambung, kiri & kanan
    for s, sx in enumerate((cx - 2.3, cx + 2.3)):
        f = _box(c, f"MOD_Ama_{s}", (sx, cy, -0.05), (0.18, 3.2, 0.22), kayu)
        # runcingkan ujung dengan skala taper sederhana via edit
    # mesin katinting di buritan (y = -2.3)
    _box(c, "MOD_MesinBlok", (cx, cy - 2.35, 0.25), (0.34, 0.5, 0.42), mesin_m)
    _box(c, "MOD_MesinTutup", (cx, cy - 2.35, 0.5), (0.3, 0.42, 0.12), merah)
    # batang baling-baling panjang menjorok ke air (long-tail)
    _cyl(c, "MOD_Shaft", (cx, cy - 2.4, 0.2), (cx, cy - 3.6, -0.5), 0.045, mesin_m)
    _box(c, "MOD_Baling", (cx, cy - 3.6, -0.5), (0.22, 0.06, 0.22), mesin_m)


def poles_rumah():
    c = bpy.data.collections["Aset_RumahPanggung"]
    _hapus_mod(c)
    root = bpy.data.objects.get("RumahPanggung_root")
    H = 1.6
    # angkat rumah jadi panggung (sekali saja — tandai lewat custom prop)
    if root and not root.get("mod_panggung"):
        root.location.z += H
        root["mod_panggung"] = 1
    kayu = flat_material("MOD_KayuTiang", (0.42, 0.28, 0.16))
    seng = flat_material("MOD_Seng", (0.60, 0.64, 0.67), rough=0.5, metal=0.3)
    dinding = flat_material("MOD_DindingKayu", (0.72, 0.55, 0.34))
    # tiang panggung di sudut footprint (center 20,0 ; half 2.3), dari tanah ke lantai
    for sx in (-2.3, 2.3):
        for sy in (-2.3, 2.3):
            _cyl(c, f"MOD_Tiang_{sx}_{sy}", (20 + sx, sy, 0.0), (20 + sx, sy, H + 1.1), 0.18, kayu, seg=8)
    _cyl(c, "MOD_TiangTengah", (20, 0, 0.0), (20, 0, H + 1.1), 0.18, kayu, seg=8)
    # ganti material: atap (objek tertinggi) -> seng, dinding -> kayu
    tertinggi = max((o for o in c.objects if o.type == "MESH" and not o.name.startswith("MOD_")),
                    key=lambda o: o.matrix_world.translation.z, default=None)
    for o in c.objects:
        if o.type != "MESH" or o.name.startswith("MOD_"):
            continue
        cz = o.matrix_world.translation.z
        baru = seng if o is tertinggi else dinding
        o.data.materials.clear()
        o.data.materials.append(baru)
        for p in o.data.polygons: p.use_smooth = False


def poles_papan():
    c = bpy.data.collections["Aset_Papan"]
    for o in list(c.objects):
        if o.name.startswith("MOD_"):
            if o.data and o.name.startswith("MOD_Teks"):
                bpy.data.curves.remove(o.data)
            else:
                bpy.data.objects.remove(o, do_unlink=True)
    tinta = flat_material("MOD_Tinta", (0.12, 0.08, 0.05))
    cur = bpy.data.curves.new("MOD_TeksPapan", type="FONT")
    cur.body = "TAMAN NASIONAL\nBUNAKEN"
    cur.align_x = "CENTER"; cur.align_y = "CENTER"
    cur.size = 0.16
    cur.extrude = 0.004
    o = bpy.data.objects.new("MOD_Teks", cur)
    o.data.materials.append(tinta)
    o.location = (28.0, -0.055, 0.52)
    o.rotation_euler = (math.radians(90), 0, 0)   # berdiri menghadap -Y
    c.objects.link(o)


def poles_dermaga():
    # tint railing biru-abu -> kayu agar selaras palet
    ganti = {"mat16.001": (0.55, 0.40, 0.24), "mat17.001": (0.40, 0.28, 0.18),
             "mat22.001": (0.58, 0.44, 0.28), "mat12.001": (0.86, 0.70, 0.40)}
    for nama, warna in ganti.items():
        m = bpy.data.materials.get(nama)
        if m and m.use_nodes:
            b = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
            if b: b.inputs["Base Color"].default_value = (*warna, 1.0)


def flat_semua():
    for c in bpy.data.collections:
        if not c.name.startswith("Aset_"):
            continue
        for o in c.objects:
            if o.type == "MESH":
                for p in o.data.polygons:
                    p.use_smooth = False


def poles():
    poles_perahu()
    poles_rumah()
    poles_papan()
    poles_dermaga()
    flat_semua()
    # perbarui instance_offset karena rumah terangkat & ada geometri baru
    from mathutils import Vector as V
    for c in bpy.data.collections:
        if not c.name.startswith("Aset_"):
            continue
        meshes = [o for o in c.objects if o.type == "MESH"]
        if not meshes:
            continue
        pts = [o.matrix_world @ V(cc) for o in meshes for cc in o.bound_box]
        c.instance_offset = ((min(p.x for p in pts) + max(p.x for p in pts)) / 2,
                             (min(p.y for p in pts) + max(p.y for p in pts)) / 2,
                             min(p.z for p in pts))
    print("Poles selesai.")


if __name__ == "__main__":
    poles()

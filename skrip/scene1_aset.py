"""Tata aset desa nelayan di Scene 1 dengan me-link collection dari aset.blend.

Desa diletakkan di pesisir utara (sisi +Y) Pulau Bunaken, menghadap Manado Tua &
laut lepas, agar sesuai alur kamera (flyover pesisir → ikuti perahu → menukik ke laut).
Aset di-LINK (bukan append) sebagai collection instance, sehingga perubahan di
aset.blend otomatis ikut ke scene ini.
"""
import math
import random

import bpy
from mathutils import Vector

ASET_BLEND = r"D:\Tugas Semester 5\Grafika Komputer\Project\blender\aset.blend"
KATEGORI = ["Aset_Kelapa", "Aset_Bakau", "Aset_RumahPanggung", "Aset_Papan",
            "Aset_Perahu", "Aset_Nelayan", "Aset_Burung", "Aset_Awan", "Aset_Dermaga"]

# pusat desa di pesisir +Y pulau (shoreline ~ y=45)
DESA = Vector((6.0, 40.0, 0.0))


def link_collections():
    perlu = [n for n in KATEGORI
             if not (n in bpy.data.collections and bpy.data.collections[n].library)]
    if perlu:
        with bpy.data.libraries.load(ASET_BLEND, link=True) as (src, dst):
            dst.collections = [n for n in perlu if n in src.collections]
    out = {}
    for n in KATEGORI:
        c = next((c for c in bpy.data.collections if c.name == n and c.library), None)
        out[n] = c
    return out


def instance(coll, parent, name, loc, rot=(0, 0, 0), scale=1.0):
    e = bpy.data.objects.new(name, None)
    e.instance_type = "COLLECTION"
    e.instance_collection = coll
    e.location = Vector(loc)
    e.rotation_euler = rot
    e.scale = (scale, scale, scale)
    e.empty_display_size = 0.5
    parent.objects.link(e)
    return e


def place_assets(height):
    sc = bpy.context.scene
    links = link_collections()
    grp = bpy.data.collections.get("Aset_Scene1")
    if grp is None:
        grp = bpy.data.collections.new("Aset_Scene1")
        sc.collection.children.link(grp)
    else:
        for o in list(grp.objects):
            bpy.data.objects.remove(o, do_unlink=True)

    rng = random.Random(7)

    def z_at(x, y):
        return height(x, y)

    # --- Dermaga: dari pantai menjulur ke arah laut (+Y) di atas reef flat ---
    dx, dy = DESA.x - 4, DESA.y + 6
    instance(links["Aset_Dermaga"], grp, "Dermaga", (dx, dy, -0.2), rot=(0, 0, math.radians(90)), scale=1.1)

    # --- Rumah panggung: 3 di tepi darat belakang dermaga ---
    for i, (ox, oy) in enumerate([(-8, -2), (4, -4), (14, 0)]):
        x, y = DESA.x + ox, DESA.y + oy
        z = max(z_at(x, y), 0.2)
        instance(links["Aset_RumahPanggung"], grp, f"Rumah_{i}", (x, y, z),
                 rot=(0, 0, rng.uniform(-0.5, 0.5)), scale=rng.uniform(0.9, 1.1))

    # --- Papan Taman Nasional di tepi jalan masuk desa ---
    instance(links["Aset_Papan"], grp, "Papan_TN", (DESA.x - 16, DESA.y - 3, max(z_at(DESA.x-16, DESA.y-3), 0.3)),
             rot=(0, 0, math.radians(20)), scale=1.4)

    # --- Perahu: satu tertambat di dermaga, satu di air siap berangkat ---
    instance(links["Aset_Perahu"], grp, "Perahu_tambat", (dx + 4, dy + 2, -0.15),
             rot=(0, 0, math.radians(95)), scale=1.0)
    perahu_jalan = instance(links["Aset_Perahu"], grp, "Perahu_jalan", (DESA.x + 10, DESA.y + 20, -0.15),
                            rot=(0, 0, math.radians(70)), scale=1.0)

    # --- Nelayan di perahu yang berangkat ---
    instance(links["Aset_Nelayan"], grp, "Nelayan", (DESA.x + 10.3, DESA.y + 19.4, 0.35),
             rot=(0, 0, math.radians(70)), scale=1.0)

    # --- Kelapa: sebar di tepi pulau (hindari area desa) ---
    ICX, ICY, IA, IB = 0.0, -10.0, 90.0, 55.0
    n = 0
    tries = 0
    while n < 28 and tries < 400:
        tries += 1
        a = rng.uniform(0, 2 * math.pi)
        r = rng.uniform(0.45, 0.92)
        x = ICX + math.cos(a) * IA * r
        y = ICY + math.sin(a) * IB * r
        z = z_at(x, y)
        if not (0.8 < z < 9.0):
            continue
        if (Vector((x, y, 0)) - DESA).length < 14:   # sisakan ruang desa
            continue
        instance(links["Aset_Kelapa"], grp, f"Kelapa_{n}", (x, y, z - 0.2),
                 rot=(0, 0, rng.uniform(0, 6.28)), scale=rng.uniform(0.7, 1.15))
        n += 1

    # --- Bakau: rumpun di pesisir -X pulau (rawa) ---
    for i in range(7):
        x = -70 + rng.uniform(-6, 6)
        y = ICY + rng.uniform(-18, 18)
        z = z_at(x, y)
        z = min(max(z, -0.6), 1.2)
        instance(links["Aset_Bakau"], grp, f"Bakau_{i}", (x, y, z),
                 rot=(0, 0, rng.uniform(0, 6.28)), scale=rng.uniform(0.8, 1.2))

    # --- Burung: kawanan camar di langit ---
    for i in range(6):
        instance(links["Aset_Burung"], grp, f"Burung_{i}",
                 (rng.uniform(-40, 60), rng.uniform(10, 90), rng.uniform(22, 38)),
                 rot=(0, 0, rng.uniform(0, 6.28)), scale=rng.uniform(1.0, 1.8))

    # --- Awan: tinggi di langit utara (ke arah horizon), jauh dari pulau ---
    for i in range(7):
        instance(links["Aset_Awan"], grp, f"Awan_{i}",
                 (rng.uniform(-240, 240), rng.uniform(120, 340), rng.uniform(135, 195)),
                 rot=(0, 0, rng.uniform(0, 6.28)), scale=rng.uniform(2.2, 4.2))

    print("Aset ditempatkan:", len(grp.objects), "instance")
    return grp

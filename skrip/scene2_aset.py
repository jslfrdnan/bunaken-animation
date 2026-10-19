"""Sebar karang/anemon di dinding drop-off + tempatkan ikan (Scene 2).

Aset di-LINK dari aset.blend sebagai collection instance. Karang disebar pada muka
dinding (DindingDropoff): tiap instance diorientasikan mengikuti normal muka dinding
(tumbuh keluar). Ikan badut ditaruh dekat anemon, lionfish sebagai aksen.
"""
import math
import random

import bpy
from mathutils import Vector

ASET_BLEND = r"D:\Tugas Semester 5\Grafika Komputer\Project\blender\aset.blend"
KARANG = ["Aset_KarangMeja", "Aset_KarangOtak", "Aset_KarangKipas", "Aset_Anemon"]
IKAN = ["Aset_IkanBadut", "Aset_IkanLalosi"]
# wilayah lantai reef yang terlihat kamera (x, y)
X_MIN, X_MAX = -40.0, 40.0
Y_MIN, Y_MAX = -7.0, 40.0


def link_collections(names):
    perlu = [n for n in names if not (n in bpy.data.collections and bpy.data.collections[n].library)]
    if perlu:
        with bpy.data.libraries.load(ASET_BLEND, link=True) as (src, dst):
            dst.collections = [n for n in perlu if n in src.collections]
    return {n: next((c for c in bpy.data.collections if c.name == n and c.library), None) for n in names}


def instance(coll, parent, name, loc, rot, scale):
    e = bpy.data.objects.new(name, None)
    e.instance_type = "COLLECTION"; e.instance_collection = coll
    e.location = Vector(loc); e.rotation_euler = rot; e.scale = (scale, scale, scale)
    e.empty_display_size = 0.3
    parent.objects.link(e)
    return e


def place_assets():
    sc = bpy.context.scene
    links = link_collections(KARANG + IKAN)
    grp = bpy.data.collections.get("Aset_Scene2")
    if grp is None:
        grp = bpy.data.collections.new("Aset_Scene2"); sc.collection.children.link(grp)
    else:
        for o in list(grp.objects):
            bpy.data.objects.remove(o, do_unlink=True)

    floor = bpy.data.objects["ReefFlat"]
    mw = floor.matrix_world
    rng = random.Random(21)

    # kumpulkan muka lantai reef dalam wilayah kamera (semua menghadap atas)
    faces = []
    for p in floor.data.polygons:
        c = mw @ p.center
        if X_MIN <= c.x <= X_MAX and Y_MIN <= c.y <= Y_MAX:
            faces.append(c)
    rng.shuffle(faces)

    anemon_pos = []
    n_karang = 0
    for c in faces:
        if n_karang >= 90:
            break
        if rng.random() > 0.45:            # kerapatan
            continue
        kat = rng.choices(KARANG, weights=[3, 3, 2, 2])[0]
        # karang tumbuh tegak ke atas (+Z), sedikit miring acak
        rot = (rng.uniform(-0.18, 0.18), rng.uniform(-0.18, 0.18), rng.uniform(0, 6.28))
        scale = rng.uniform(0.5, 1.3)
        pos = c + Vector((0, 0, 0.05))
        instance(links[kat], grp, f"Karang_{n_karang}", pos, rot, scale)
        if kat == "Aset_Anemon":
            anemon_pos.append(pos + Vector((0, 0, 0.3)))
        n_karang += 1

    # ikan badut dekat anemon (simbiosis)
    nb = 0
    for ap in anemon_pos[:8]:
        for _ in range(rng.randint(1, 3)):
            off = Vector((rng.uniform(-1, 1), rng.uniform(0.3, 1.5), rng.uniform(-0.6, 0.6)))
            instance(links["Aset_IkanBadut"], grp, f"Badut_{nb}", ap + off,
                     (0, 0, rng.uniform(0, 6.28)), rng.uniform(0.8, 1.3))
            nb += 1

    # lionfish aksen: 2 melayang di atas reef flat
    for i, (x, y) in enumerate([(6, 14), (-10, 6)]):
        instance(links["Aset_IkanLalosi"], grp, f"Lionfish_{i}", (x, y, -6.5),
                 (0, 0, rng.uniform(0, 6.28)), rng.uniform(1.0, 1.4))

    print(f"Scatter: {n_karang} karang, {nb} badut, 2 lionfish ({len(grp.objects)} instance)")
    return grp


if __name__ == "__main__":
    place_assets()

"""update-scene-2-4-v001.py — perbarui Scene 2–4 dengan aset baru (15 Nov 2026).

Shot lama DIBACA ULANG lewat `bpy.data.libraries.load(link=False)` lalu disunting
di tempat (tanpa `open_mainfile` / `read_factory_settings`).

  s2-010  island-detail_v003 + perahu Haris (haris-boat) + kamera wide horizon rendah
  s2-020  FX bom bawah laut (gelembung, kilatan, cincin tekanan, kolom gelembung,
          puing, 12 cakalang ber-rig kabur) — dibangun ulang dari nol
  s2-030  jaring menangkap ikan: 6 ikan ber-rig tersangkut, 20 ikan kabur
  s2-090  island-detail_v003 + crowd_v003 + Daniel rig naik perahu Haris
  s3-030  island-detail_v003 + crowd_v003
  s3-090  island-detail_v003 + crowd_v003 (mannequin pengelola tetap jauh)
  s4-010  island-detail_v003 + crowd_v003 + buoy oranye
  s4-060  island-detail_v003 + Daniel + 3 anak asli CRW_C01–C03 + jaring
  s4-070  reef-dense_v003 + tiga sekolah ber-rig, penyu tetap

Cara pakai di Blender MCP (satu tahap per eksekusi):
    ns = {"__name__": "__main__"}
    exec(compile(open(path).read(), path, "exec"), ns)
    ns["stage"]("s2-010")
"""

import bpy
import datetime
import importlib.util
import math
import os
import re
import shutil
import sys
from mathutils import Euler, Matrix, Vector

ROOT = r"D:/Tugas Semester 5/Grafika Komputer/Project-Animasi"
ASSETS = ROOT + "/assets"
SCENES = ROOT + "/scenes"
STILLS = ROOT + "/renders/stills"
TMP = ROOT + "/renders/tmp"
LOGPATH = ROOT + "/renders/logs/technical.log"

P_ISLAND3 = ASSETS + "/env/island-detail_v003.blend"
P_CROWD3 = ASSETS + "/char/crowd_v003.blend"
P_REEF3 = ASSETS + "/env/reef-dense_v003.blend"
P_REEF = ASSETS + "/env/reef.blend"
P_DAMAGED = ASSETS + "/env/reef-damaged.blend"
P_NET = ASSETS + "/props/fishing-net-spread.blend"
P_BUOY = ASSETS + "/props/mooring-buoy.blend"
P_HARIS_BOAT = ASSETS + "/props/haris-boat.blend"
P_BOATS = ASSETS + "/props/boats.blend"
P_DANIEL = ASSETS + "/char/daniel_rig_v001.blend"
P_NARA = ASSETS + "/char/nara_rig_v002.blend"
P_HARIS = ASSETS + "/char/haris_rig_v001.blend"

FISH = {
    "cakalang": {
        "path": ASSETS + "/env/fish-cakalang-rig_v002.blend",
        "arm": "CHR_cakalang_rig",
        "mesh": "ENV_fish_cakalang",
        "extra": ["ENV_fish_cakalang_tail", "ENV_fish_cakalang_pectoral",
                  "ENV_fish_cakalang_dorsal"],
    },
    "kakatua": {
        "path": ASSETS + "/env/fish-kakatua_v002.blend",
        "arm": "CHR_fish_kakatua_rig",
        "mesh": "ENV_fish_kakatua",
        "extra": [],
    },
    "damselfish": {
        "path": ASSETS + "/env/fish-damselfish_v002.blend",
        "arm": "CHR_fish_damselfish_rig",
        "mesh": "ENV_fish_damselfish",
        "extra": [],
    },
}

SHOTS = {
    "s2-010": ("scene-2_shot-010_haris-subuh_v001.blend", 96, 2),
    "s2-020": ("scene-2_shot-020_bom_v001.blend", 96, 2),
    "s2-030": ("scene-2_shot-030_jaring-dasar_v001.blend", 96, 2),
    "s2-090": ("scene-2_shot-090_daniel-naik_v001.blend", 96, 2),
    "s3-030": ("scene-3_shot-030_nara-kumpulkan_v001.blend", 96, 3),
    "s3-090": ("scene-3_shot-090_warga-temui_v001.blend", 96, 3),
    "s4-010": ("scene-4_shot-010_warga-siapkan-buoy_v001.blend", 96, 4),
    "s4-060": ("scene-4_shot-060_daniel-ajari_v001.blend", 96, 4),
    "s4-070": ("scene-4_shot-070_penyu-kembali_v001.blend", 72, 4),
}

ISLAND_COLLS = ("ENV_island-detail", "ENV_island-detail_context")
ISLAND_PAT = ("ENV_detail_", "ENV_surface_", "ENV_shop_")


# ------------------------------------------------------------------ util


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


lib = _load("s4lib", ROOT + "/scripts/build-scene-4-shots.py")
s1 = _load("s1lib", ROOT + "/scripts/build-scene-1-detail-shots.py")


def log(phase, line):
    os.makedirs(os.path.dirname(LOGPATH), exist_ok=True)
    stamp = datetime.datetime.now().strftime("%H:%M")
    with open(LOGPATH, "a", encoding="utf-8") as fh:
        fh.write("[%s] %s - %s\n" % (stamp, phase, line))
    print("[log]", phase, line)


def wipe():
    lib.wipe()
    scn = bpy.context.scene
    scn.name = "wipe"
    print("wipe: %d objek sisa, file %s"
          % (len(bpy.data.objects), bpy.data.filepath))
    return scn


def setup_scene(name, frame_end):
    scn = bpy.context.scene
    scn.name = name
    scn.render.resolution_x = 1920
    scn.render.resolution_y = 1080
    scn.render.resolution_percentage = 100
    scn.render.fps = 24
    scn.render.fps_base = 1.0
    scn.view_settings.view_transform = "Standard"
    scn.render.film_transparent = False
    try:
        scn.render.engine = "BLENDER_EEVEE"
    except TypeError:
        pass
    if hasattr(scn, "eevee") and hasattr(scn.eevee, "taa_render_samples"):
        scn.eevee.taa_render_samples = 32
    scn.frame_start = 1
    scn.frame_end = frame_end
    scn.frame_set(1)
    return scn


def purge_orphans(passes=2):
    for _ in range(passes):
        for db in (bpy.data.meshes, bpy.data.materials, bpy.data.armatures,
                   bpy.data.curves, bpy.data.cameras, bpy.data.lights,
                   bpy.data.worlds, bpy.data.actions, bpy.data.collections,
                   bpy.data.images):
            for block in list(db):
                try:
                    if block.users == 0 and not block.use_fake_user:
                        db.remove(block)
                except Exception:
                    pass


def append_blend(path, colls=None, set_world=True):
    """Append (link=False) koleksi + objek lepas + world dari `path`."""
    before_obj = set(bpy.data.objects.keys())
    before_world = set(bpy.data.worlds.keys())
    with bpy.data.libraries.load(path, link=False) as (src, dst):
        want_c = [c for c in (colls if colls is not None else src.collections)
                  if c in src.collections]
        dst.collections = list(want_c)
    scn = bpy.context.scene
    top = [ch.name for ch in scn.collection.children]
    for name in want_c:
        c = bpy.data.collections.get(name)
        if c is None:
            continue
        nested = any(c.name in [ch.name for ch in other.children]
                     for other in bpy.data.collections if other.name != name)
        if not nested and c.name not in top:
            scn.collection.children.link(c)
    with bpy.data.libraries.load(path, link=False) as (src, dst):
        dst.objects = [n for n in src.objects if n not in bpy.data.objects]
    with bpy.data.libraries.load(path, link=False) as (src, dst):
        dst.worlds = [n for n in src.worlds if n not in bpy.data.worlds]
    for ob in bpy.data.objects:
        if len(ob.users_collection) == 0:
            scn.collection.objects.link(ob)
    new_worlds = [bpy.data.worlds[n] for n in bpy.data.worlds.keys()
                  if n not in before_world]
    if new_worlds and set_world:
        scn.world = new_worlds[0]
    new_objs = [bpy.data.objects[n] for n in bpy.data.objects.keys()
                if n not in before_obj]
    print("APPEND %s -> colls=%s obj=%d"
          % (os.path.basename(path), want_c, len(new_objs)))
    return new_objs


def append_asset(path, colls):
    """Append aset lalu buang kamera/lampu/lantai preview aset."""
    new = append_blend(path, colls, set_world=False)
    new = lib.live_objects(new)
    killed = lib.purge_lights_cameras(new)
    new = lib.live_objects(new)
    prev = bpy.data.collections.get("PREVIEW")
    victims = [o for o in new if o.name.startswith(("PREVIEW", "CAM_preview"))]
    if prev is not None:
        victims.extend(list(prev.all_objects))
    for ob in victims:
        if ob.name in bpy.data.objects:
            bpy.data.objects.remove(ob, do_unlink=True)
    if prev is not None:
        bpy.data.collections.remove(prev)
    purge_orphans()
    new = [o for o in lib.live_objects(new) if o.name in bpy.data.objects]
    print("  append_asset %s: %d objek (kamera/lampu dibuang: %d)"
          % (os.path.basename(path), len(new), len(killed)))
    return new


def get_cam(name=None):
    scn = bpy.context.scene
    cams = [o for o in bpy.data.objects if o.type == "CAMERA"]
    if name:
        ob = bpy.data.objects.get(name)
        if ob is not None and ob.type == "CAMERA":
            scn.camera = ob
            return ob
    mine = [o for o in cams if o.name.startswith("CAM_shot")]
    ob = sorted(mine, key=lambda o: o.name)[0] if mine else (cams[0] if cams else None)
    scn.camera = ob
    print("kamera aktif:", ob.name if ob else None,
          "| semua:", [o.name for o in cams])
    return ob


def shot_world(name, hexcol, strength=1.0):
    scn = bpy.context.scene
    w = bpy.data.worlds.get(name)
    if w is None:
        w = lib.add_world(name, hexcol, strength=strength)
    scn.world = w
    return w


def look_at(ob, target):
    """Arahkan objek ke target. rotation_mode dipaksa XYZ supaya keyframe euler
    benar-benar dipakai (kamera lama di beberapa shot masih QUATERNION)."""
    if ob.rotation_mode != "XYZ":
        ob.rotation_mode = "XYZ"
    lib.look_at(ob, target)


def set_interp(mode="BEZIER"):
    s1.set_interp(mode)


def bbox_center(ob):
    m = ob.matrix_world
    pts = [m @ Vector(c) for c in ob.bound_box]
    return sum(pts, Vector()) / 8.0, pts


def bbox_of(names):
    pts = []
    for n in names:
        ob = bpy.data.objects.get(n)
        if ob is not None and ob.type == "MESH":
            pts.extend(bbox_center(ob)[1])
    if not pts:
        return None, None
    xs = [p.x for p in pts]
    ys = [p.y for p in pts]
    zs = [p.z for p in pts]
    return (Vector((min(xs), min(ys), min(zs))), Vector((max(xs), max(ys), max(zs))))


def cam_frame(cam):
    m = cam.matrix_world
    fwd = (m.to_3x3() @ Vector((0.0, 0.0, -1.0))).normalized()
    return fwd


def yaw_toward(d):
    """Yaw supaya sumbu -Y lokal objek menghadap vektor d (aset ikan hadap -Y)."""
    d = Vector((d.x, d.y))
    if d.length < 1e-6:
        return 0.0
    return math.atan2(d.x, -d.y)


# --------------------------------------------------------------- island


def island_objs():
    found = {}
    for cn in ISLAND_COLLS:
        c = bpy.data.collections.get(cn)
        if c is not None:
            for ob in c.all_objects:
                if "water" in ob.name.lower():
                    continue
                found[ob.name] = ob
    for ob in bpy.data.objects:
        if ob.name.startswith(ISLAND_PAT) and "water" not in ob.name.lower():
            found[ob.name] = ob
    return list(found.values())


def _is_water(ob):
    n = ob.name.lower()
    return ("water" in n or "sea-surface" in n) and "volume" not in n


def swap_island():
    """Ganti/pasang island-detail_v003 di scene aktif (delta 0 kalau belum ada)."""
    had_water = [o.name for o in bpy.data.objects if _is_water(o) and o.type == "MESH"]
    objs = island_objs()
    old = {ob.name: (ob.matrix_world.copy(), ob.parent.name if ob.parent else None)
           for ob in objs}
    print("ISLAND lama: %d objek" % len(objs))
    for ob in list(objs):
        bpy.data.objects.remove(ob, do_unlink=True)
    for cn in ISLAND_COLLS + ("ENV_surface",):
        c = bpy.data.collections.get(cn)
        if c is not None:
            bpy.data.collections.remove(c)
    purge_orphans()

    new = append_asset(P_ISLAND3, list(ISLAND_COLLS))
    # bidang air milik shot dipertahankan; bidang air bawaan island dibuang
    water = [o for o in new if _is_water(o)]
    if not had_water:
        water = []
    wnames = []
    for ob in water:
        try:
            wnames.append(ob.name)
        except ReferenceError:
            pass
    for ob in water:
        if ob.name in bpy.data.objects:
            bpy.data.objects.remove(ob, do_unlink=True)
    new = [o for o in lib.live_objects(new) if o.name in bpy.data.objects]
    if water:
        print("bidang air bawaan island dibuang:", wnames)
    if not old:
        print("ISLAND v003: tidak ada island lama → ditempatkan di origin aset")
        log("MODEL", "island-detail_v003 dipasang (tanpa island lama, origin aset)")
        return new
    common = [n for n in old if n in bpy.data.objects]
    ref = None
    for cand in ["CTL_island-detail"] + common:
        ob = bpy.data.objects.get(cand)
        if ob is not None and ob.parent is None and cand in old:
            ref = cand
            break
    if ref is None and common:
        ref = common[0]
        print("   acuan jatuh ke objek umum:", ref)
    if ref is None:
        raise RuntimeError("tidak ada objek acuan untuk menghitung offset island")
    delta = old[ref][0] @ bpy.data.objects[ref].matrix_world.inverted()
    for ob in new:
        if ob.parent is None:
            ob.matrix_world = delta @ ob.matrix_world
    err = 0.0
    fixed = 0
    for n in common:
        ob = bpy.data.objects.get(n)
        if ob is None:
            continue
        d = (ob.matrix_world.translation - old[n][0].translation).length
        err = max(err, d)
        if d > 1e-4:
            ob.matrix_world = old[n][0]
            fixed += 1
    new = [o for o in lib.live_objects(new) if o.name in bpy.data.objects]
    shops = [o.name for o in new if o.name.startswith("ENV_shop_")]
    ds = delta.translation
    print("ISLAND v003: acuan=%s delta=(%.2f, %.2f, %.2f) | baru=%d | shop=%d | err_max=%.3f fixed=%d"
          % (ref, ds.x, ds.y, ds.z, len(new), len(shops), err, fixed))
    log("MODEL", "island-detail_v003 dipasang (acuan %s, shop %d objek)" % (ref, len(shops)))
    return new


# ---------------------------------------------------------------- crowd


def face_name(char):
    return "CHR_crowd_face-" + char.replace("CRW_", "crw-").lower()


def swap_crowd(keep_chars, place_fn=None, use_old=True):
    """Ganti crowd lama dengan crowd_v003; `keep_chars` = daftar nama CRW_*."""
    olds = {ob.name: ob.matrix_world.copy() for ob in bpy.data.objects
            if ob.name.startswith(("CRW_", "CTL_crowd", "CHR_crowd_"))}
    for ob in [o for o in bpy.data.objects
               if o.name.startswith(("CRW_", "CTL_crowd", "CHR_crowd_"))]:
        bpy.data.objects.remove(ob, do_unlink=True)
    c = bpy.data.collections.get("CHR_crowd")
    if c is not None:
        bpy.data.collections.remove(c)
    purge_orphans()
    print("crowd lama dibuang: %d objek" % len(olds))

    new = append_asset(P_CROWD3, ["CHR_crowd"])
    new = lib.live_objects(new)
    keep = set(["CTL_crowd"] + list(keep_chars) + [face_name(c) for c in keep_chars])
    drop = [o for o in new if o.name not in keep]
    for ob in drop:
        bpy.data.objects.remove(ob, do_unlink=True)
    purge_orphans()
    new = [o for o in lib.live_objects(new) if o.name in bpy.data.objects]

    moved = 0
    placed = 0
    for i, ob in enumerate(sorted([o for o in new if o.name.startswith("CRW_")],
                                  key=lambda o: o.name)):
        base = olds.get(ob.name) if use_old else None
        if base is not None:
            ob.matrix_world = base
            moved += 1
        elif place_fn is not None:
            place_fn(i, ob)
            placed += 1
    bpy.context.view_layer.update()
    print("crowd_v003: %d karakter (pertahankan posisi %d, ditempatkan baru %d)"
          % (len([o for o in new if o.name.startswith("CRW_")]), moved, placed))
    log("ANIM", "crowd_v003 dipasang: %s" % ", ".join(sorted(keep_chars)))
    return new


def pier_info():
    bnd = bbox_of(["ENV_surface_pier-deck"])
    if bnd[0] is None:
        print("pier deck tidak ketemu")
        return None
    lo, hi = bnd
    print("pier deck: x %.1f..%.1f y %.1f..%.1f z %.2f..%.2f"
          % (lo.x, hi.x, lo.y, hi.y, lo.z, hi.z))
    return lo, hi


# ------------------------------------------------------------ fish rigs


PROTO = {}


def clear_proto():
    """Buang objek proto (data mesh/armature tetap hidup lewat klon)."""
    for kind, (objs, _info) in list(PROTO.items()):
        for ob in objs.values():
            try:
                if ob.name in bpy.data.objects:
                    bpy.data.objects.remove(ob, do_unlink=True)
            except ReferenceError:
                pass
    PROTO.clear()
    c = bpy.data.collections.get("ENV_fish")
    if c is not None:
        bpy.data.collections.remove(c)
    for ob in [o for o in bpy.data.objects if len(o.users_collection) == 0
               and o.name.startswith("CTL_fish")]:
        bpy.data.objects.remove(ob, do_unlink=True)
    purge_orphans()
    print("proto ikan dibuang (data tetap dipakai klon)")


def load_fish_proto(kind):
    """Append satu aset ikan ber-rig, kembalikan objek proto (tanpa kamera/lampu)."""
    info = FISH[kind]
    cached = PROTO.get(kind)
    if cached is not None:
        objs = cached[0]
        alive = True
        for ob in objs.values():
            try:
                if ob.name not in bpy.data.objects:
                    alive = False
            except ReferenceError:
                alive = False
        if alive:
            return cached
    new = append_asset(info["path"], ["ENV_fish"])
    new = [o for o in lib.live_objects(new) if o.name in bpy.data.objects]
    objs = {}
    for key in [info["arm"], info["mesh"]] + info["extra"] + ["CTL_fish"]:
        ob = bpy.data.objects.get(key)
        if ob is not None:
            objs[key] = ob
    arm = objs.get(info["arm"])
    if arm is None:
        raise RuntimeError("armature %s tidak ada di %s" % (info["arm"], info["path"]))
    if arm.animation_data and arm.animation_data.action:
        arm.animation_data.action.use_fake_user = True
    print("  proto %s: arm=%s bones=%d mesh=%s extra=%s"
          % (kind, arm.name, len(arm.data.bones), info["mesh"],
             [k for k in info["extra"] if k in objs]))
    PROTO[kind] = (objs, info)
    return objs, info


def clone_set(objs, suffix, coll):
    """Duplikat dangkal satu set objek (data dibagi) → file tetap kecil."""
    items = list(objs.values())
    mapping = {}
    for ob in items:
        nb = ob.copy()
        try:
            nb.data = ob.data
        except AttributeError:
            pass
        nb.name = ob.name + suffix
        coll.objects.link(nb)
        nb.parent = None
        nb.parent_type = "OBJECT"
        nb.parent_bone = ""
        mapping[ob.name] = nb
    for ob in items:
        nb = mapping[ob.name]
        if ob.parent is not None and ob.parent.name in mapping:
            nb.parent = mapping[ob.parent.name]
            nb.parent_type = ob.parent_type
            nb.parent_bone = ob.parent_bone
            nb.matrix_parent_inverse = ob.matrix_parent_inverse.copy()
        nb.matrix_basis = ob.matrix_basis.copy()
        for mod in getattr(nb, "modifiers", ()):
            if mod.type == "ARMATURE" and mod.object is not None:
                tgt = mapping.get(mod.object.name)
                if tgt is not None:
                    mod.object = tgt
    return mapping


def clear_fx_fish(tags=("FX_caught", "FX_flee", "FX_school", "FX_pivot")):
    """Buang klon ikan FX dari eksekusi sebelumnya supaya tidak dobel."""
    victims = [o for o in bpy.data.objects
               if o.name.startswith(tags) or "pivot-" in o.name]
    for c in list(bpy.data.collections):
        if c.name.startswith("FX_fish"):
            victims.extend(list(c.all_objects))
            bpy.data.collections.remove(c)
    names = []
    for ob in victims:
        try:
            names.append(ob.name)
        except ReferenceError:
            pass
    for n in sorted(set(names)):
        if n in bpy.data.objects:
            bpy.data.objects.remove(bpy.data.objects[n], do_unlink=True)
    purge_orphans()
    print("klon ikan FX dibersihkan: %d objek" % len(set(names)))


def fx_collection(name="FX_fish"):
    coll = bpy.data.collections.get(name)
    if coll is None:
        coll = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(coll)
    return coll


def spawn_fish(kind, index, pos, yaw, scale=1.0, coll=None, tag="FX"):
    """Satu ikan ber-rig lengkap; kembalikan pivot (empty) yang dianimasikan."""
    coll = coll or fx_collection()
    proto, info = load_fish_proto(kind)
    suffix = "_%s_%s%02d" % (tag, kind, index)
    mapping = clone_set(proto, suffix, coll)
    root = mapping.get("CTL_fish")
    if root is None:
        root = mapping[info["arm"]]
    root.name = "%s_pivot-%s_%02d" % (tag, kind, index)
    root.animation_data_clear()
    root.parent = None
    root.rotation_mode = "XYZ"
    root.location = pos
    root.rotation_euler = (0.0, 0.0, yaw)
    root.scale = (scale, scale, scale)
    arm = mapping[info["arm"]]
    arm.name = "%s_%s_%02d_rig" % (tag, kind, index)
    mesh = mapping.get(info["mesh"])
    if mesh is not None:
        mesh.name = "%s_%s_%02d_mesh" % (tag, kind, index)
        d = mesh.dimensions
        if index == 1:
            print("   ukuran %s: %.2f x %.2f x %.2f m"
                  % (kind, d.x, d.y, d.z))
    root["fish_kind"] = kind
    return root, mapping


def key_pivot(piv, keys, rot=None):
    """keys = [(frame, Vector loc)]; rot = [(frame, (rx,ry,rz))] opsional."""
    set_interp("BEZIER")
    piv.rotation_mode = "XYZ"
    base = piv.rotation_euler.copy()
    for f, loc in keys:
        piv.location = loc
        piv.keyframe_insert("location", frame=f)
    if rot:
        for f, r in rot:
            piv.rotation_euler = r
            piv.keyframe_insert("rotation_euler", frame=f)
    else:
        piv.rotation_euler = base
        piv.keyframe_insert("rotation_euler", frame=keys[0][0])


# ------------------------------------------------------------- save/still


def drop_libraries():
    for lby in list(bpy.data.libraries):
        try:
            bpy.data.libraries.remove(lby)
        except Exception as exc:
            print("library tidak bisa dilepas:", lby.filepath, exc)


def save_shot(key):
    scn = bpy.context.scene
    filename = SHOTS[key][0]
    src = os.path.join(SCENES, filename)
    bak = src.replace("_v001.blend", "_v000.blend")
    if os.path.exists(src) and not os.path.exists(bak):
        shutil.copy2(src, bak)
        print("BACKUP:", os.path.basename(bak))
    scn.frame_set(1)
    drop_libraries()
    bpy.ops.wm.save_as_mainfile(filepath=src)
    size = os.path.getsize(src)
    print("SAVED %s (%d bytes)" % (os.path.basename(src), size))
    return size


def still(shot_key, frame=48, percent=50, samples=24, tag=None):
    """Still representatif dengan world + shader air look resmi per scene."""
    scn = bpy.context.scene
    scene_id = SHOTS[shot_key][2]
    out = os.path.join(STILLS, "anim-%s_v001.png" % (tag or shot_key))
    os.makedirs(STILLS, exist_ok=True)
    try:
        wname, water = apply_preview_look(scn, scene_id)
        scn.frame_set(int(frame))
        render_png(scn, out, percent=percent, samples=samples)
        print("STILL %s f%d: %s | world=%s water=%s"
              % (shot_key, frame, os.path.exists(out), wname, water))
    except Exception as exc:
        import traceback
        print("still gagal %s: %r" % (shot_key, exc))
        traceback.print_exc(file=sys.stdout)
    scn.frame_set(1)


LOOK_FILES = {2: "scene-2-look.blend", 3: "scene-3-look.blend", 4: "scene-4-look.blend"}
_WATER_TOKENS_EXCLUDE = ("volume", "fog", "mist", "kabut")


def ensure_look_world(scene_id):
    name = "WLD_scene-%d" % scene_id
    if name in bpy.data.worlds:
        return bpy.data.worlds[name]
    path = os.path.join(ASSETS, "look", LOOK_FILES[scene_id])
    with bpy.data.libraries.load(path, link=False) as (src, dst):
        dst.worlds = [n for n in src.worlds if n == name][:1]
    w = bpy.data.worlds.get(name)
    if w is not None:
        w.use_fake_user = True
    print("look world disiapkan:", name, w is not None)
    return w


def ensure_water_material():
    name = "SHD_water-surface_v002"
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    path = os.path.join(ASSETS, "look", "scene-1-look_v003.blend")
    if not os.path.exists(path):
        return None
    with bpy.data.libraries.load(path, link=False) as (src, dst):
        dst.materials = [n for n in src.materials if n == name][:1]
    mat = bpy.data.materials.get(name)
    if mat is not None:
        mat.use_fake_user = True
    return mat


def _is_water_object(ob):
    toks = [t for t in re.split(r"[^a-z0-9]+", ob.name.lower()) if t]
    is_water = any(t.startswith("water") or t == "sea" for t in toks)
    if not is_water:
        return False
    return not any(h in t for t in toks for h in _WATER_TOKENS_EXCLUDE)


def apply_preview_look(scn, scene_id):
    """World look scene-N + shader air, hanya di memori (file shot tidak disimpan)."""
    w = ensure_look_world(scene_id)
    if w is not None:
        scn.world = w
    mat = ensure_water_material()
    touched = []
    if mat is not None:
        for ob in list(scn.objects):
            if ob.type != "MESH" or not hasattr(ob.data, "materials"):
                continue
            if not _is_water_object(ob):
                continue
            if len(ob.data.materials) == 0:
                ob.data.materials.append(mat)
            else:
                for i in range(len(ob.data.materials)):
                    ob.data.materials[i] = mat
            touched.append(ob.name)
    scn.view_settings.view_transform = "Standard"
    return (w.name if w is not None else None), touched


def render_png(scn, out, percent=50, samples=24):
    try:
        scn.render.engine = "BLENDER_EEVEE"
    except TypeError:
        pass
    scn.render.resolution_x = 1920
    scn.render.resolution_y = 1080
    scn.render.resolution_percentage = int(percent)
    scn.render.image_settings.file_format = "PNG"
    scn.render.image_settings.color_mode = "RGBA"
    if hasattr(scn, "eevee") and hasattr(scn.eevee, "taa_render_samples"):
        scn.eevee.taa_render_samples = int(samples)
    scn.render.filepath = out
    bpy.ops.render.render(write_still=True)
    return out


def summary(key):
    scn = bpy.context.scene
    objs = list(bpy.data.objects)
    arms = [o for o in objs if o.type == "ARMATURE"]
    no_coll = [o.name for o in objs if len(o.users_collection) == 0]
    print("SUMMARY %s | mesh=%d arm=%d cam=%d light=%d | %dx%d %dfps vt=%s range=%d-%d"
          % (key,
             len([o for o in objs if o.type == "MESH"]), len(arms),
             len([o for o in objs if o.type == "CAMERA"]),
             len([o for o in objs if o.type == "LIGHT"]),
             scn.render.resolution_x, scn.render.resolution_y,
             scn.render.fps, scn.view_settings.view_transform,
             scn.frame_start, scn.frame_end))
    print("   armature di koleksi:", [(a.name, [c.name for c in a.users_collection],
                                      len(a.data.bones)) for a in arms])
    if no_coll:
        print("   PERINGATAN objek tanpa koleksi:", no_coll)


def open_shot(key):
    wipe()
    filename, fend, _ = SHOTS[key]
    scn = setup_scene(filename[:-6], fend)
    append_blend(os.path.join(SCENES, filename))
    cams = sorted([o for o in bpy.data.objects if o.type == "CAMERA"],
                  key=lambda o: o.name)
    if cams:
        scn.camera = cams[0]
    print("kamera dari file:", scn.camera.name if scn.camera else None,
          "| semua:", [c.name for c in cams])
    scn.frame_set(1)
    return scn


# =========================================================== s2-010


def stage_s2_010():
    scn = open_shot("s2-010")
    swap_island()

    # perahu Haris (tanpa kanopi, cat pudar) menggantikan perahu bercadik
    old_root = bpy.data.objects.get("PRP_boat_haris-root")
    old_loc = old_root.matrix_world.translation.copy() if old_root else Vector((0.0, -228.0, 0.0))
    old_rot = old_root.matrix_world.to_euler() if old_root else Euler((0.0, 0.0, 0.28))
    for ob in [o for o in bpy.data.objects
               if o.name.startswith(("PRP_boat", "PRP_haris-boat"))]:
        bpy.data.objects.remove(ob, do_unlink=True)
    for cn in ("PRP_boats", "PRP_haris-boat"):
        c = bpy.data.collections.get(cn)
        if c is not None:
            bpy.data.collections.remove(c)
    purge_orphans()
    boat = append_asset(P_HARIS_BOAT, ["PRP_haris-boat"])
    for ob in boat:
        if ob.parent is None:
            ob.matrix_world = Matrix.Translation(old_loc) @ old_rot.to_matrix().to_4x4() \
                @ ob.matrix_world
    print("perahu Haris: %d objek di (%.1f, %.1f, %.1f)"
          % (len(boat), old_loc.x, old_loc.y, old_loc.z))

    shot_world("WLD_s2-010", "#0F5C63", 0.9)
    cam = get_cam("CAM_s2-010")
    cam.animation_data_clear()
    cam.data.lens = 30.0
    hull = bpy.data.objects.get("PRP_haris-boat_hull")
    look_pt = bbox_center(hull)[0] if hull is not None else Vector((0, -228, 0))
    dist = 58.0
    fwd = Vector((look_pt.x, look_pt.y, 0.0)) - Vector((1.2, -112.0, 0.0))
    fwd.z = 0.0
    fwd.normalize()
    start = look_pt - fwd * dist
    start.z = 2.2
    end = start + fwd * 3.2
    end.z = 2.25

    # pandang menengadah: horizon turun ke sepertiga bawah frame
    def aim_from(loc, pitch=5.5, d=160.0):
        p = Vector((loc.x, loc.y, 0.0)) + fwd * d
        p.z = loc.z + d * math.tan(math.radians(pitch))
        return p

    aim1 = aim_from(start)
    aim2 = aim_from(end)
    set_interp("BEZIER")
    for f, loc, tgt in ((1, start, aim1), (96, end, aim2)):
        cam.location = loc
        look_at(cam, tgt)
        cam.keyframe_insert("location", frame=f)
        cam.keyframe_insert("rotation_euler", frame=f)
    from bpy_extras.object_utils import world_to_camera_view as w2c
    cam.location = start
    look_at(cam, aim1)
    bpy.context.view_layer.update()
    v = w2c(scn, cam, look_pt)
    print("kamera wide: loc (%.1f, %.1f, %.1f) lens %.0f mm | perahu di layar (%.2f, %.2f), jarak %.0f m"
          % (start.x, start.y, start.z, cam.data.lens, v.x, v.y,
             (look_pt - start).length))

    get_cam("CAM_s2-010")
    size = save_shot("s2-010")
    summary("s2-010")
    log("ANIM", "s2-010 island v003 + perahu Haris + kamera wide 30mm horizon rendah (%d bytes)" % size)
    still("s2-010", 48)
    return True


# =========================================================== s2-020 bom


def srgb(hexstr):
    return lib.srgb(hexstr)


def emissive(name, hexcol, strength=6.0, alpha=1.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        if n.type == "BSDF_PRINCIPLED":
            nt.nodes.remove(n)
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    emit = nt.nodes.new("ShaderNodeEmission")
    emit.inputs["Color"].default_value = srgb(hexcol)
    emit.inputs["Strength"].default_value = strength
    nt.links.new(emit.outputs["Emission"], out.inputs["Surface"])
    mat.diffuse_color = srgb(hexcol)
    if alpha < 1.0:
        mat.blend_method = "BLEND"
    return mat, emit


def simple_mat(name, hexcol, roughness=0.6, alpha=1.0):
    return lib.material(name, hexcol, roughness=roughness, alpha=alpha)


def sphere(name, radius, loc, mat, coll, segments=10, rings=6):
    mesh = bpy.data.meshes.new(name)
    bm_verts = []
    bm_faces = []
    # bola UV sederhana
    for i in range(rings + 1):
        phi = math.pi * i / rings
        for j in range(segments):
            th = 2.0 * math.pi * j / segments
            bm_verts.append((radius * math.sin(phi) * math.cos(th),
                             radius * math.sin(phi) * math.sin(th),
                             radius * math.cos(phi)))
    for i in range(rings):
        for j in range(segments):
            a = i * segments + j
            b = i * segments + (j + 1) % segments
            c = (i + 1) * segments + (j + 1) % segments
            d = (i + 1) * segments + j
            bm_faces.append((a, b, c, d))
    mesh.from_pydata(bm_verts, [], bm_faces)
    mesh.materials.append(mat)
    mesh.update()
    ob = bpy.data.objects.new(name, mesh)
    coll.objects.link(ob)
    ob.location = loc
    return ob


def torus(name, major, minor, loc, mat, coll, segments=48, ring=12):
    verts, faces = [], []
    for i in range(segments):
        u = 2 * math.pi * i / segments
        for j in range(ring):
            v = 2 * math.pi * j / ring
            r = major + minor * math.cos(v)
            verts.append((r * math.cos(u), r * math.sin(u), minor * math.sin(v)))
    for i in range(segments):
        i2 = (i + 1) % segments
        for j in range(ring):
            j2 = (j + 1) % ring
            faces.append((i * ring + j, i2 * ring + j, i2 * ring + j2, i * ring + j2))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.materials.append(mat)
    mesh.update()
    ob = bpy.data.objects.new(name, mesh)
    coll.objects.link(ob)
    ob.location = loc
    return ob


def stage_s2_020():
    scn = open_shot("s2-020")

    # buang FX lama (termasuk sisa FX bom versi sebelumnya & ikutannya)
    old_fx = [o for o in bpy.data.objects
              if o.name.startswith(("FX_", "ENV_bird"))
              or "_FX_" in o.name or "_fx_" in o.name]
    for c in list(bpy.data.collections):
        if c.name.startswith("FX_"):
            old_fx.extend([o for o in c.all_objects if o not in old_fx])
            bpy.data.collections.remove(c)
    print("FX lama dibuang: %d objek" % len(old_fx))
    for ob in old_fx:
        try:
            bpy.data.objects.remove(ob, do_unlink=True)
        except ReferenceError:
            pass
    # dasar laut + karang dari eksekusi sebelumnya dibuang supaya tidak menumpuk
    dup = [o for o in bpy.data.objects if o.name.startswith(("ENV_reef", "ENV_seabed"))]
    for ob in dup:
        try:
            bpy.data.objects.remove(ob, do_unlink=True)
        except ReferenceError:
            pass
    for cn in ("ENV_reef", "ENV_reef-damaged"):
        c = bpy.data.collections.get(cn)
        if c is not None:
            bpy.data.collections.remove(c)
    print("dasar laut/karang lama dibuang:", len(dup))
    purge_orphans()

    fx = bpy.data.collections.new("FX_bomb-underwater")
    scn.collection.children.link(fx)

    B = Vector((0.0, 7.6, -6.4))          # titik ledakan
    SAND_Z = -8.2

    # ---- dasar laut + karang rusak + karang hidup di latar
    sand = lib.material("MAT_fx_seabed", "#E8D5B0", roughness=0.94)
    lib.make_plane("ENV_seabed", 70.0, SAND_Z, sand)
    dmg = append_asset(P_DAMAGED, ["ENV_reef-damaged"])
    dmg = lib.live_objects(dmg)
    layout = {
        "ENV_reef_damaged-rubble_a": ((1.9, 6.6, SAND_Z), 24),
        "ENV_reef_damaged-rubble_b": ((-2.4, 8.4, SAND_Z), -38),
        "ENV_reef_damaged-rubble_c": ((0.7, 9.4, SAND_Z), 66),
        "ENV_reef_damaged-bomb": ((-3.6, 7.2, SAND_Z), 12),
        "ENV_reef_damaged-net": ((3.8, 8.2, SAND_Z), -20),
    }
    for name, (loc, rz) in layout.items():
        ob = bpy.data.objects.get(name)
        if ob is not None:
            ob.location = loc
            ob.rotation_euler = (0.0, 0.0, math.radians(rz))
    reef = append_asset(P_REEF, ["ENV_reef"])
    reef = lib.live_objects(reef)
    for ob in list(reef):
        if ob.name.startswith(("ENV_reef_fish", "ENV_reef_turtle")):
            if ob.name in bpy.data.objects:
                bpy.data.objects.remove(ob, do_unlink=True)
    reef = [o for o in lib.live_objects(reef) if o.name in bpy.data.objects]
    for ob in reef:
        if ob.parent is None:
            ob.location = (ob.location.x * 2.2 - 6.0, ob.location.y * 1.4 + 11.0,
                           SAND_Z + 0.05)
            ob.scale = (1.7, 1.7, 1.7)
    print("dasar laut: puing %d + karang %d objek" % (len(dmg), len(reef)))

    # ---- material FX
    mat_bub = simple_mat("MAT_fx_bubble", "#F2E9DC", roughness=0.22, alpha=0.62)
    mat_flash, emit_flash = emissive("MAT_fx_flash", "#D9FBFF", strength=18.0)
    mat_ring, emit_ring = emissive("MAT_fx_ring", "#5FE3F0", strength=1.6, alpha=0.8)
    mat_deb = simple_mat("MAT_fx_debris", "#8A8F8C", roughness=0.9)

    # ---- gelembung awal (f1–12 naik pelan)
    for i in range(10):
        ang = 2 * math.pi * i / 10.0
        r = 0.5 + 0.5 * (i % 3)
        p = B + Vector((math.cos(ang) * r, math.sin(ang) * r * 0.6, -0.5 - 0.14 * i))
        b = sphere("FX_amb-bubble_%02d" % i, 0.08 + 0.015 * (i % 4), p, mat_bub, fx)
        b.scale = (1, 1, 1)
        set_interp("BEZIER")
        b.keyframe_insert("location", frame=1)
        b.location = p + Vector((0.05 * math.sin(i), 0.04 * math.cos(i), 1.5 + 0.12 * i))
        b.keyframe_insert("location", frame=12)
        b.location = b.location + Vector((-0.1, 0.06, 0.9))
        b.keyframe_insert("location", frame=96)
        b.keyframe_insert("scale", frame=1)
        b.scale = (1.2, 1.2, 1.2)
        b.keyframe_insert("scale", frame=96)

    # ---- kilatan: bola emissive kecil (bukan bidang penuh frame) f12–18
    flash = sphere("FX_bomb_flash", 0.5, B, mat_flash, fx, segments=16, rings=10)
    set_interp("BEZIER")
    for f, s in ((1, 0.001), (11, 0.001), (13, 1.0), (16, 1.35), (18, 1.7),
                 (21, 1.9), (23, 0.001)):
        flash.scale = (s, s, s)
        flash.keyframe_insert("scale", frame=f)
    for f, st in ((1, 0.0), (11, 0.0), (13, 22.0), (16, 12.0), (18, 3.0), (22, 0.0)):
        emit_flash.inputs["Strength"].default_value = st
        emit_flash.inputs["Strength"].keyframe_insert("default_value", frame=f)
    # cahaya kilatan: menerangi karang & ikan sesaat (bukan volumetrik)
    ldata = bpy.data.lights.new("FX_bomb_flashlight", "POINT")
    ldata.color = (0.85, 0.97, 1.0)
    ldata.shadow_soft_size = 1.2
    lamp = bpy.data.objects.new("FX_bomb_flashlight", ldata)
    fx.objects.link(lamp)
    lamp.location = B
    for f, e in ((1, 0.0), (11, 0.0), (13, 9000.0), (16, 5000.0), (20, 900.0), (26, 0.0)):
        ldata.energy = e
        ldata.keyframe_insert("energy", frame=f)

    # ---- cincin tekanan: torus skala 0,2 → 6 m (f12–34)
    ring = torus("FX_bomb_ring", 1.0, 0.06, B, mat_ring, fx, segments=56, ring=10)
    ring.rotation_euler = (math.radians(90), 0.0, 0.0)   # bidang cincin menghadap kamera
    for f, s in ((1, 0.001), (11, 0.001), (12, 0.2), (22, 2.6), (34, 6.0),
                 (37, 6.2), (40, 0.001)):
        ring.scale = (s, s, s)
        ring.keyframe_insert("scale", frame=f)
    for f, st in ((1, 0.0), (11, 0.0), (12, 1.7), (20, 1.3), (30, 0.6),
                  (36, 0.1), (38, 0.0)):
        emit_ring.inputs["Strength"].default_value = st
        emit_ring.inputs["Strength"].keyframe_insert("default_value", frame=f)
    print("cincin tekanan: torus radius 1,0 m, skala 0,2 → 6,0 m (f12–34)")

    # ---- kolom gelembung (f18–60) 48 bola
    n_bcol = 48
    for i in range(n_bcol):
        ang = 2 * math.pi * (i * 0.618) % (2 * math.pi)
        r = 0.35 + 0.9 * ((i * 37) % 100) / 100.0
        p0 = B + Vector((math.cos(ang) * r, math.sin(ang) * r * 0.8, -0.9))
        b = sphere("FX_bcol_%02d" % i, 0.09 + 0.012 * (i % 5), p0, mat_bub, fx)
        f0 = 18 + (i % 6) * 2
        f1 = f0 + 26
        f2 = min(60 + (i % 8), 74)
        top = Vector((p0.x * 1.25, p0.y * 1.25, -1.4))
        set_interp("BEZIER")
        b.scale = (0.001, 0.001, 0.001)
        b.location = p0
        b.keyframe_insert("scale", frame=1)
        b.keyframe_insert("location", frame=1)
        b.scale = (1.0, 1.0, 1.0)
        b.keyframe_insert("scale", frame=f0)
        b.location = p0 + Vector((0, 0, 0.5))
        b.keyframe_insert("location", frame=f0)
        b.location = top
        b.keyframe_insert("location", frame=f1)
        b.scale = (0.001, 0.001, 0.001)
        b.keyframe_insert("scale", frame=f2)
        b.keyframe_insert("location", frame=f2)

    # ---- puing karang berhamburan (f12–60)
    src = [bpy.data.objects.get(n) for n in
           ("ENV_reef_damaged-rubble_a", "ENV_reef_damaged-rubble_b",
            "ENV_reef_damaged-rubble_c")]
    src = [o for o in src if o is not None]
    for i in range(12):
        base = Vector((((i * 53) % 100) / 100.0 - 0.5,
                       ((i * 29) % 100) / 100.0 - 0.5, 0.0))
        dirv = Vector((base.x, base.y, 1.0)).normalized()
        p0 = B + dirv * 0.6
        ob = bpy.data.objects.new("FX_debris_%02d" % i, src[i % len(src)].data)
        fx.objects.link(ob)
        dist = 3.2 + 0.9 * (i % 4)
        p1 = B + dirv * dist
        p1.z = max(SAND_Z + 0.12, p1.z + 1.6 - 0.4 * (i % 3))
        set_interp("BEZIER")
        ob.location = p0
        ob.scale = (0.35, 0.35, 0.35)
        ob.rotation_euler = (0, 0, 0)
        ob.keyframe_insert("location", frame=1)
        ob.keyframe_insert("scale", frame=1)
        ob.keyframe_insert("rotation_euler", frame=1)
        ob.scale = (0.55, 0.55, 0.55)
        ob.location = p0 + dirv * 0.4
        ob.keyframe_insert("location", frame=12)
        ob.keyframe_insert("scale", frame=12)
        ob.location = p1
        ob.rotation_euler = (math.radians(150 + i * 30), math.radians(i * 40),
                             math.radians(i * 25))
        ob.keyframe_insert("location", frame=34)
        ob.keyframe_insert("rotation_euler", frame=34)
        land = Vector((p1.x * 1.15, p1.y * 1.05, SAND_Z + 0.06))
        ob.location = land
        ob.keyframe_insert("location", frame=58)
    print("puing: 12 potong karang dilempar (f12–58)")

    # ---- 12 ikan cakalang ber-rig kabur
    for i in range(12):
        ang = 2 * math.pi * i / 12.0 + 0.22
        r0 = 2.0 + 0.5 * (i % 3)
        p0 = B + Vector((math.cos(ang) * r0, math.sin(ang) * r0 * 0.55,
                         -0.9 + 0.5 * ((i % 4) - 1.5)))
        d = Vector((math.cos(ang), math.sin(ang), 0.35 + 0.12 * (i % 3)))
        d.normalize()
        piv, _ = spawn_fish("cakalang", i + 1, p0, yaw_toward(d), scale=1.0,
                            coll=fx, tag="FX")
        key_pivot(piv,
                  [(1, p0),
                   (11, p0 + d * 0.25),
                   (22, p0 + d * 3.4),
                   (40, p0 + d * 8.6 + Vector((0, 0, 0.5))),
                   (70, p0 + d * 15.0 + Vector((0, 0, 1.2))),
                   (96, p0 + d * 18.5 + Vector((0, 0, 1.6)))])

    # ---- kamera bawah permukaan menghadap titik ledakan (jarak ±12 m)
    cam = get_cam("CAM_s2-020")
    cam.data.lens = 34.0
    start = Vector((0.8, -4.2, -3.0))
    end = Vector((0.5, -3.2, -3.05))
    cam.location = start
    look_at(cam, B + Vector((-0.3, 0, 0.3)))
    set_interp("BEZIER")
    for f, loc, tgt in ((1, start, B + Vector((-0.4, 0, 0.25))),
                        (96, end, B + Vector((-0.1, 0, 0.4)))):
        cam.location = loc
        look_at(cam, tgt)
        cam.keyframe_insert("location", frame=f)
        cam.keyframe_insert("rotation_euler", frame=f)
    print("kamera bawah air z=-3,0 m, jarak %.1f m ke titik ledakan, lens 34 mm, tanpa shake"
          % (start - B).length)

    # ---- lampu pengisi supaya karang & ikan terbaca (bukan volumetrik)
    fdata = bpy.data.lights.new("LGT_water-fill", "AREA")
    fdata.energy = 900.0
    fdata.size = 9.0
    fdata.color = (0.72, 0.88, 0.95)
    fill = bpy.data.objects.new("LGT_water-fill", fdata)
    scn.collection.objects.link(fill)
    fill.location = (-4.5, -4.0, -1.0)
    look_at(fill, B)
    print("lampu pengisi area 900 W di atas-kiri kamera")

    shot_world("WLD_s2-020", "#0F5C63", 1.25)
    scn.frame_set(1)
    clear_proto()
    size = save_shot("s2-020")
    summary("s2-020")
    log("ANIM", "s2-020 FX bom bawah laut: kilatan f12-18, cincin tekanan 0,2->6 m, 48 gelembung, 12 puing, 12 cakalang kabur (%d bytes)" % size)
    still("s2-020", 16)
    still("s2-020", 40, tag="s2-020-f40")
    return True


# =========================================================== s2-030 jaring


def stage_s2_030():
    scn = open_shot("s2-030")

    # ---- akar sapuan jaring
    root = bpy.data.objects.get("PRP_net-sweep-root")
    if root is None:
        root = bpy.data.objects.new("PRP_net-sweep-root", None)
        scn.collection.objects.link(root)
    net_objs = [o for o in bpy.data.objects
                if o.name.startswith(("PRP_gear_net", "PRP_net-sweep"))]
    root.animation_data_clear()
    for ob in net_objs:
        if ob is root:
            continue
        mw = ob.matrix_world.copy()
        ob.parent = root
        ob.matrix_parent_inverse = root.matrix_world.inverted()
        ob.matrix_world = mw
    root.rotation_mode = "XYZ"
    root.location = (0.0, root.location.y, root.location.z)
    bpy.context.view_layer.update()
    nb = bbox_of([o.name for o in net_objs if o.type == "MESH"])
    print("jaring: %d objek, bbox %s .. %s" % (len(net_objs), nb[0], nb[1]))

    # ---- ikan lama (tak ber-rig) dibuang supaya tidak dobel
    clear_fx_fish()
    old_fish = [o for o in bpy.data.objects
                if "_fish_" in o.name or "_fish-" in o.name]
    for c in list(bpy.data.collections):
        if c.name.startswith("FX_fish"):
            old_fish.extend(list(c.all_objects))
            bpy.data.collections.remove(c)
    for ob in [o for o in bpy.data.objects
               if o.name.startswith(("FX_caught", "FX_flee", "FX_school"))
               or "pivot-" in o.name]:
        old_fish.append(ob)
    names = []
    for ob in old_fish:
        try:
            names.append(ob.name)
        except ReferenceError:
            pass
    for n in sorted(set(names)):
        if n in bpy.data.objects:
            bpy.data.objects.remove(bpy.data.objects[n], do_unlink=True)
    purge_orphans()
    print("ikan lama dibuang: %d objek" % len(set(names)))

    fx = fx_collection("FX_fish")
    net_top = nb[1].z if nb[1] else 0.6
    print("net top z = %.2f" % net_top)

    # ---- 6 ikan tersangkut (3 cakalang, 3 kakatua), menempel di jaring
    caught = []
    plan = [("cakalang", 1), ("cakalang", 2), ("cakalang", 3),
            ("kakatua", 4), ("kakatua", 5), ("kakatua", 6)]
    offs = [(-1.15, 0.10), (-0.35, -0.18), (0.55, 0.16),
            (-0.85, -0.12), (0.20, 0.20), (1.05, -0.06)]
    for (kind, idx), (ox, oy) in zip(plan, offs):
        piv, _ = spawn_fish(kind, idx, Vector((0.0, 0.0, 0.0)),
                            yaw_toward(Vector((1, 0.12))), scale=0.9,
                            coll=fx, tag="FX_caught")
        # menempel di jaring: koordinat lokal root jaring (ikut bergerak)
        piv.parent = root
        piv.matrix_parent_inverse = Matrix.Identity(4)
        piv.location = (ox, oy, 0.06)
        piv.rotation_euler = (0.0, 0.0, yaw_toward(Vector((1.0, 0.12))))
        base_local = piv.location.copy()
        set_interp("BEZIER")
        for f in (1, 12, 24, 36, 48, 60, 72, 84, 96):
            w = math.sin((f / 96.0) * math.tau * 2.0 + idx)
            piv.location = base_local + Vector((0.02 * w, 0.03 * w, 0.025 * w))
            piv.rotation_euler = (0.0, math.radians(4.0) * w, piv.rotation_euler.z)
            piv.keyframe_insert("location", frame=f)
            piv.keyframe_insert("rotation_euler", frame=f)
        caught.append(piv)
    print("ikan tersangkut: %d (%s)" % (len(caught), [p.name for p in caught]))

    # ---- 20 ikan lain kabur ke arah berlawanan (−X)
    flee = []
    for i in range(20):
        kind = "cakalang" if i < 12 else "kakatua"
        idx = 100 + i
        sx = -0.6 + 2.4 * ((i * 37) % 100) / 100.0
        sy = -1.4 + 3.0 * ((i * 61) % 100) / 100.0
        sz = 0.8 + 1.5 * ((i * 17) % 100) / 100.0
        p0 = Vector((sx, sy, sz))
        d = Vector((-1.0, 0.10 * math.sin(i), 0.18 + 0.1 * ((i % 3) - 1)))
        d.normalize()
        piv, _ = spawn_fish(kind, idx, p0, yaw_toward(d), scale=0.9,
                            coll=fx, tag="FX_flee")
        key_pivot(piv,
                  [(1, p0),
                   (10, p0 + d * 0.3),
                   (30, p0 + d * 5.4 + Vector((0, 0, 0.4))),
                   (60, p0 + d * 11.0 + Vector((0, 0, 0.9))),
                   (96, p0 + d * 15.0 + Vector((0, 0, 1.3)))])
        flee.append(piv)
    print("ikan kabur: %d (12 cakalang + 8 kakatua)" % len(flee))

    # ---- karang meja/boulder yang menutup jalur kamera dipindah ke belakang
    moved = []
    for nm, (dx, dy) in {"ENV_reef_table_00": (3.2, 7.5),
                         "ENV_reef_table_01": (-1.0, 4.0),
                         "ENV_reef_table-coral": (2.4, 8.2),
                         "ENV_reef_boulder-coral": (-3.4, 6.4)}.items():
        ob = bpy.data.objects.get(nm)
        if ob is not None and ob.parent is None:
            ob.location = (ob.location.x + dx, ob.location.y + dy, ob.location.z)
            moved.append(nm)
    print("karang penghalang dipindah:", moved)

    # ---- sapuan jaring kiri → kanan (menyapu dekat dasar)
    y0, z0 = root.location.y, root.location.z - 0.22
    root.location = (root.location.x, y0, z0)
    sweep = [(1, -3.2), (24, -1.3), (48, 0.4), (72, 2.0), (96, 3.6)]
    set_interp("BEZIER")
    for f, x in sweep:
        root.location = (x, y0 + 0.06 * math.sin(f / 12.0), z0 + 0.03 * math.sin(f / 9.0))
        root.keyframe_insert("location", frame=f)
        root.rotation_euler = (0.0, 0.0, math.radians(2.5) * math.sin(f / 20.0))
        root.keyframe_insert("rotation_euler", frame=f)
    print("sapuan jaring: x -3,2 → +3,6 m (f1–96)")

    def net_x(f):
        for (f0, x0), (f1, x1) in zip(sweep, sweep[1:]):
            if f <= f1:
                u = (f - f0) / float(f1 - f0)
                return x0 + (x1 - x0) * u
        return sweep[-1][1]

    # ---- kamera tracking rendah: mengikuti jaring dengan jeda
    cam = get_cam("CAM_s2-030")
    cam.data.lens = 26.0
    cam.animation_data_clear()
    set_interp("BEZIER")
    tt = next((c for c in cam.constraints if c.type == "TRACK_TO" and c.target), None)
    print("constraint kamera dibuang:", tt.target.name if tt else None)
    for c in list(cam.constraints):
        cam.constraints.remove(c)
    for f in (1, 24, 48, 72, 96):
        nx = net_x(f)
        loc = Vector((nx * 0.35 - 0.5, -3.9, 0.88))
        tgt = Vector((nx, 0.4, 0.62))
        cam.location = loc
        look_at(cam, tgt)
        cam.keyframe_insert("location", frame=f)
        cam.keyframe_insert("rotation_euler", frame=f)
    from bpy_extras.object_utils import world_to_camera_view as w2c
    for f in (1, 60, 96):
        scn.frame_set(f)
        bpy.context.view_layer.update()
        v = w2c(scn, cam, Vector((net_x(f), 0.6, 0.8)))
        print("   f%-3d jaring x=%.2f | ndc (%.2f, %.2f)"
              % (f, net_x(f), v.x, v.y))
    scn.frame_set(1)
    print("kamera tracking rendah: z 0,95 m, lens 26 mm")

    shot_world("WLD_s2-030", "#0F5C63", 1.35)
    scn.frame_set(1)
    clear_proto()
    size = save_shot("s2-030")
    summary("s2-030")
    log("ANIM", "s2-030 jaring sapu x -3,2->+3,6, 6 ikan tersangkut (3 cakalang/3 kakatua), 20 ikan kabur (%d bytes)" % size)
    still("s2-030", 60)
    return True


# =========================================================== s2-090


def daniel_rig():
    """Ganti CHR_daniel apa pun dengan daniel_rig_v001 (armature di koleksi)."""
    olds = {o.name: o.matrix_world.copy() for o in bpy.data.objects
            if o.name.startswith(("CHR_daniel", "CTL_daniel"))}
    for ob in [o for o in bpy.data.objects
               if o.name.startswith(("CHR_daniel", "CTL_daniel"))]:
        bpy.data.objects.remove(ob, do_unlink=True)
    c = bpy.data.collections.get("CHR_daniel")
    if c is not None:
        bpy.data.collections.remove(c)
    purge_orphans()
    new = append_asset(P_DANIEL, ["CHR_daniel"])
    new = [o for o in lib.live_objects(new) if o.name in bpy.data.objects]
    arms = [o for o in new if o.type == "ARMATURE"]
    print("Daniel rig: %d objek, armature %s di koleksi %s (bone %d)"
          % (len(new), [a.name for a in arms],
             [c.name for a in arms for c in a.users_collection],
             len(arms[0].data.bones) if arms else 0))
    base = olds.get("CHR_daniel_rig") or next(iter(olds.values()), None)
    print("   posisi lama tersedia:", list(olds.keys())[:4])
    return new, arms[0] if arms else None, base


def stage_s2_090():
    scn = open_shot("s2-090")
    swap_island()
    new, arm, base = daniel_rig()
    root = bpy.data.objects.get("CTL_daniel") or arm
    if base is not None and root is not None:
        root.matrix_world = Matrix.Translation(base.translation)

    # posisi perahu Haris + dermaga
    hull = bbox_of([n for n in ("PRP_haris-boat_deck", "PRP_haris-boat_hull",
                                "PRP_haris-boat_thwart-mid")
                    if bpy.data.objects.get(n)])
    deck_z = None
    deck_c = None
    for n in ("PRP_haris-boat_deck", "PRP_haris-boat_thwart-mid", "PRP_haris-boat_hull"):
        ob = bpy.data.objects.get(n)
        if ob is not None:
            c, pts = bbox_center(ob)
            deck_c = c
            deck_z = max(p.z for p in pts)
            print("%s: pusat (%.2f, %.2f, %.2f) atas z=%.2f" % (n, c.x, c.y, c.z, deck_z))
            break
    pi = pier_info()

    cam = get_cam("CAM_shot-090")
    print("kamera 090:", cam.name, "loc", tuple(round(v, 2) for v in cam.matrix_world.translation))
    if deck_c is not None and root is not None:
        # Daniel melangkah dari dermaga ke dek perahu Haris
        fwd = cam_frame(cam)
        fwd.z = 0.0
        fwd.normalize()
        start = deck_c - fwd * 1.9
        start.z = (deck_z or 0.6) - 0.22
        end = deck_c + Vector((0, 0, 0.05))
        set_interp("BEZIER")
        keys = [(1, start), (18, start + (end - start) * 0.25),
                (34, start + (end - start) * 0.55),
                (52, start + (end - start) * 0.82),
                (72, end), (96, end + (end - start) * 0.05)]
        root.rotation_mode = "XYZ"
        yaw = yaw_toward(end - start)
        for f, loc in keys:
            lift = 0.0
            if f in (34, 52):
                lift = 0.16
            root.location = Vector((loc.x, loc.y, loc.z + lift))
            root.keyframe_insert("location", frame=f)
            root.rotation_euler = (math.radians(6.0), 0.0, yaw)
            root.keyframe_insert("rotation_euler", frame=f)
        print("Daniel: naik perahu (%.2f, %.2f, %.2f) → (%.2f, %.2f, %.2f)"
              % (start.x, start.y, start.z, end.x, end.y, end.z))

    # warga di dermaga: 10 dewasa menghadap perahu (di ujung dermaga, dalam frame)
    def place(i, ob):
        if pi is None:
            return
        lo, hi = pi
        y = -96.0 - 1.4 * (i % 5)
        x = -1.55 if i % 2 == 0 else 1.55
        x += 0.35 * ((i // 2) % 2)
        ob.location = (x, y, hi.z)
        ob.rotation_euler = (0.0, 0.0, math.radians(178 + 8 * (i % 3)))

    swap_crowd(["CRW_%02d" % i for i in range(1, 11)], place, use_old=False)

    shot_world("WLD_s2-090", "#0F5C63", 0.95)
    scn.frame_set(1)
    size = save_shot("s2-090")
    summary("s2-090")
    log("ANIM", "s2-090 island v003 + crowd_v003 10 dewasa + Daniel rig naik perahu Haris (%d bytes)" % size)
    still("s2-090", 56)
    return True


def camera_side(cam, target, dist):
    """Titik di sisi kamera, `dist` m dari target (untuk penempatan)."""
    d = (cam.matrix_world.translation - target)
    d.z = 0.0
    if d.length < 1e-5:
        return target.x
    return (target + d.normalized() * dist).x


# =========================================================== s3-030


def stage_s3_030():
    scn = open_shot("s3-030")
    swap_island()

    def place(i, ob):
        pi = pier_info()
        if pi is None:
            return
        lo, hi = pi
        t = (i + 1) / 13.0
        ob.location = (lo.x + (hi.x - lo.x) * t,
                       lo.y + (hi.y - lo.y) * 0.4,
                       hi.z)
        ob.rotation_euler = (0.0, 0.0, math.radians(80 + 20 * (i % 3)))

    swap_crowd(["CRW_%02d" % i for i in range(1, 13)], place)
    scn.frame_set(1)
    size = save_shot("s3-030")
    summary("s3-030")
    log("ANIM", "s3-030 island v003 + crowd_v003 12 dewasa (%d bytes)" % size)
    still("s3-030", 48)
    return True


# =========================================================== s3-090


def stage_s3_090():
    scn = open_shot("s3-090")
    swap_island()

    man = [o.name for o in bpy.data.objects if o.name.startswith("MAN_")]
    print("mannequin pengelola (dibiarkan):", man)

    def place(i, ob):
        pi = pier_info()
        if pi is None:
            return
        lo, hi = pi
        t = (i + 1) / 13.0
        ob.location = (lo.x + (hi.x - lo.x) * t,
                       lo.y + (hi.y - lo.y) * 0.45,
                       hi.z)
        ob.rotation_euler = (0.0, 0.0, math.radians(70 + 25 * (i % 3)))

    swap_crowd(["CRW_%02d" % i for i in range(1, 13)], place)
    scn.frame_set(1)
    size = save_shot("s3-090")
    summary("s3-090")
    log("ANIM", "s3-090 island v003 + crowd_v003 12 dewasa, pengelola mannequin tetap jauh (%d bytes)" % size)
    still("s3-090", 48)
    return True


# =========================================================== s4-010


def stage_s4_010():
    scn = open_shot("s4-010")
    swap_island()

    buoy = [o for o in bpy.data.objects if o.name.startswith("PRP_buoy")]
    body = bpy.data.objects.get("PRP_buoy_body")
    if body is not None:
        mats = [m.name for m in body.data.materials]
        col = body.data.materials[0].diffuse_color if body.data.materials else None
        print("buoy: %d objek, body material %s warna %.3f/%.3f/%.3f"
              % (len(buoy), mats, col[0], col[1], col[2]) if col else "buoy body tanpa material")
    else:
        print("PERINGATAN: PRP_buoy_body tidak ada")

    def place(i, ob):
        pi = pier_info()
        if pi is None:
            return
        lo, hi = pi
        t = (i + 1) / 11.0
        ob.location = (lo.x + (hi.x - lo.x) * t,
                       lo.y + (hi.y - lo.y) * 0.35,
                       hi.z)
        ob.rotation_euler = (0.0, 0.0, math.radians(95 + 15 * (i % 3)))

    swap_crowd(["CRW_%02d" % i for i in range(1, 11)], place)
    scn.frame_set(1)
    size = save_shot("s4-010")
    summary("s4-010")
    log("ANIM", "s4-010 island v003 + crowd_v003 10 dewasa + buoy oranye (%d bytes)" % size)
    still("s4-010", 48)
    return True


# =========================================================== s4-060


def stage_s4_060():
    scn = open_shot("s4-060")
    swap_island()
    new, arm, base = daniel_rig()
    root = bpy.data.objects.get("CTL_daniel") or arm
    if base is not None and root is not None:
        root.matrix_world = Matrix.Translation(base.translation)

    net = bpy.data.objects.get("PRP_gear_fishnet")
    if net is not None:
        c, pts = bbox_center(net)
        print("jaring anyam: pusat (%.2f, %.2f, %.2f)" % (c.x, c.y, c.z))
    else:
        c = Vector((0, 0, 0))
        print("PRP_gear_fishnet tidak ada")

    dan_pos = root.matrix_world.translation.copy() if root else c

    def place(i, ob):
        ang = math.radians(-60 + 45 * i)
        off = Vector((math.cos(ang) * 1.05, math.sin(ang) * 0.55, 0.0))
        ob.location = dan_pos + off
        ob.rotation_euler = (0.0, 0.0, math.radians(200 + 18 * i))

    swap_crowd(["CRW_C01", "CRW_C02", "CRW_C03"], place)
    scn.frame_set(1)
    size = save_shot("s4-060")
    summary("s4-060")
    log("ANIM", "s4-060 island v003 + Daniel + 3 anak CRW_C01-C03 anyam jaring (%d bytes)" % size)
    still("s4-060", 48)
    return True


# =========================================================== s4-070


def stage_s4_070():
    scn = open_shot("s4-070")

    # buang reef lama
    old = [o for o in bpy.data.objects
           if o.name.startswith(("ENV_reef_", "ENV_school_"))]
    for ob in old:
        bpy.data.objects.remove(ob, do_unlink=True)
    for cn in ("ENV_reef",):
        c = bpy.data.collections.get(cn)
        if c is not None:
            bpy.data.collections.remove(c)
    purge_orphans()
    print("reef lama dibuang: %d objek" % len(old))

    turtle = bpy.data.objects.get("CTL_turtle")
    scn.frame_set(36)          # posisi penyu di tengah shot (dipakai untuk jangkar karang)
    bpy.context.view_layer.update()
    t_pos = turtle.matrix_world.translation.copy() if turtle else Vector((0, 0, 1.4))
    print("penyu tetap: %s di f36 (%.2f, %.2f, %.2f)"
          % (turtle.name if turtle else None, t_pos.x, t_pos.y, t_pos.z))

    reef = append_asset(P_REEF3, ["ENV_reef-dense"])
    reef = [o for o in lib.live_objects(reef) if o.name in bpy.data.objects]
    # sekolah tak ber-rig bawaan aset dibuang (diganti sekolah ber-rig di bawah)
    drop = [o for o in reef if o.name.startswith("ENV_school_")]
    for ob in drop:
        if ob.name in bpy.data.objects:
            bpy.data.objects.remove(ob, do_unlink=True)
    for cn in ("ENV_school_cakalang", "ENV_school_kakatua", "ENV_school_damselfish"):
        c = bpy.data.collections.get(cn)
        if c is not None:
            bpy.data.collections.remove(c)
    purge_orphans()
    reef = [o for o in lib.live_objects(reef) if o.name in bpy.data.objects]
    print("sekolah bawaan aset dibuang:", len(drop))
    ctl = bpy.data.objects.get("CTL_reef-dense")
    mats = sorted({m.name for o in reef if o.type == "MESH" for m in o.data.materials if m})
    print("reef-dense_v003: %d objek, material %s" % (len(reef), mats[:6]))
    lo, hi = bbox_of([o.name for o in reef if o.type == "MESH"])
    if lo is not None:
        print("   bbox semua %.1f..%.1f / %.1f..%.1f / %.1f..%.1f"
              % (lo.x, hi.x, lo.y, hi.y, lo.z, hi.z))
    clo, chi = bbox_of([o.name for o in bpy.data.objects
                        if o.name.startswith("ENV_dense_coral") and o.type == "MESH"])
    if ctl is not None and clo is not None:
        # perbesar rumpun supaya terbaca di lensa sempit 42 mm
        ctl.scale = (2.2, 2.2, 2.2)
        bpy.context.view_layer.update()
        clo, chi = bbox_of([o.name for o in bpy.data.objects
                            if o.name.startswith("ENV_dense_coral") and o.type == "MESH"])
        cx = (clo.x + chi.x) * 0.5
        cy = (clo.y + chi.y) * 0.5
        dz = (t_pos.z - 0.35) - chi.z
        ctl.location = (ctl.location.x + (t_pos.x - cx),
                        ctl.location.y + (t_pos.y - 0.2 - cy),
                        ctl.location.z + dz)
        print("   karang (coral) %.1f..%.1f / %.1f..%.1f / %.1f..%.1f | geser dx %.2f dy %.2f dz %.2f skala 2,2"
              % (clo.x, chi.x, clo.y, chi.y, clo.z, chi.z,
                 t_pos.x - cx, t_pos.y - 0.2 - cy, dz))
        bpy.context.view_layer.update()
        from bpy_extras.object_utils import world_to_camera_view as w2c
        cam0 = scn.camera
        scn.frame_set(36)
        bpy.context.view_layer.update()
        v = w2c(scn, cam0, Vector((t_pos.x, t_pos.y - 0.2, t_pos.z - 1.4)))
        print("   ndc titik karang di f36: (%.2f, %.2f) z=%.2f" % (v.x, v.y, v.z))
        scn.frame_set(1)

    fx = fx_collection("FX_fish")
    clear_fx_fish()
    fx = fx_collection("FX_fish")
    plan = [("cakalang", 14, 0.055), ("kakatua", 10, 0.05), ("damselfish", 16, 0.035)]
    for kind, n, _s in plan:
        for i in range(n):
            idx = 100 + i
            ang = 2 * math.pi * (i * 0.618) % (2 * math.pi)
            r = 2.4 + 1.6 * ((i * 31) % 100) / 100.0
            p0 = Vector((math.cos(ang) * r - 4.0, math.sin(ang) * r * 0.7,
                         t_pos.z + 0.4 + 0.9 * ((i % 4) - 1.5)))
            d = Vector((1.0, 0.20 * math.sin(i), 0.05 * math.cos(i)))
            d.normalize()
            piv, _ = spawn_fish(kind, idx, p0, yaw_toward(d), scale=1.0,
                                coll=fx, tag="FX_school")
            key_pivot(piv,
                      [(1, p0),
                       (24, p0 + d * 2.2),
                       (48, p0 + d * 5.0 + Vector((0, 0, 0.2))),
                       (72, p0 + d * 8.2 + Vector((0, 0, 0.3)))])
    print("tiga sekolah ber-rig: 14 cakalang + 10 kakatua + 16 damselfish")

    scn.frame_set(1)
    clear_proto()
    size = save_shot("s4-070")
    summary("s4-070")
    log("ANIM", "s4-070 reef-dense_v003 + 3 sekolah ber-rig (40 ikan), penyu tetap (%d bytes)" % size)
    still("s4-070", 36)
    return True


# ============================================================ verifikasi


def verify(key, frames=(48,), percent=50):
    scn = open_shot(key)
    objs = list(bpy.data.objects)
    fname, fend, scene_id = SHOTS[key]
    path = os.path.join(SCENES, fname)
    print("== VERIFY %s | %d objek | %d bytes | colls=%s"
          % (fname, len(objs), os.path.getsize(path),
             [c.name for c in bpy.data.collections]))
    print("   world=%s cam=%s lens=%s | %dx%d %dfps vt=%s range=%d-%d"
          % (scn.world.name if scn.world else None,
             scn.camera.name if scn.camera else None,
             round(scn.camera.data.lens, 1) if scn.camera else None,
             scn.render.resolution_x, scn.render.resolution_y, scn.render.fps,
             scn.view_settings.view_transform, scn.frame_start, scn.frame_end))
    shop = [o.name for o in objs if o.name.startswith("ENV_shop_")]
    crowd = sorted({o.name for o in objs if o.name.startswith("CRW_")})
    arms = [o for o in objs if o.type == "ARMATURE"]
    print("   fasad shop=%d | crowd=%d %s" % (len(shop), len(crowd), crowd[:6]))
    print("   armature=%d %s" % (len(arms), [(a.name, [c.name for c in a.users_collection])
                                             for a in arms][:6]))
    if key == "s2-020":
        ring = bpy.data.objects.get("FX_bomb_ring")
        flash = bpy.data.objects.get("FX_bomb_flash")
        cols = [o.name for o in objs if o.name.startswith("FX_bcol_")]
        fish = [o.name for o in objs if "pivot-cakalang" in o.name]
        print("   cincin=%s kilatan=%s kolom gelembung=%d ikan=%d"
              % (ring is not None, flash is not None, len(cols), len(fish)))
        if ring is not None:
            for f in (12, 16, 24, 34):
                scn.frame_set(f)
                bpy.context.view_layer.update()
                print("     f%-3d skala cincin %.2f m" % (f, ring.matrix_world.to_scale().x))
        scn.frame_set(16)
    if key == "s2-030":
        caught = [o for o in objs if "pivot-" in o.name and "caught" in o.name]
        flee = [o for o in objs if "pivot-" in o.name and "flee" in o.name]
        root = bpy.data.objects.get("PRP_net-sweep-root")
        print("   tersangkut=%d %s" % (len(caught), [o.name for o in caught]))
        print("   kabur=%d" % len(flee))
        if root is not None:
            for f in (1, 60, 96):
                scn.frame_set(f)
                bpy.context.view_layer.update()
                print("     f%-3d jaring x=%.2f" % (f, root.matrix_world.translation.x))
        scn.frame_set(60)
    if key == "s4-070":
        kinds = {}
        for o in objs:
            if "pivot-" in o.name:
                kinds[o.name.split("pivot-")[1].split("_")[0]] = \
                    kinds.get(o.name.split("pivot-")[1].split("_")[0], 0) + 1
        print("   sekolah ber-rig:", kinds, "| penyu:", "CTL_turtle" in bpy.data.objects)
    for f in frames:
        still(key, f, percent=percent)
    scn.frame_set(1)


def stage_verify_a():
    verify("s2-010")
    verify("s3-030")
    log("VERIFY", "s2-010 & s3-030 dibaca ulang dari disk + still 50%")
    return True


def stage_verify_b():
    verify("s2-020", frames=(16, 40))
    log("VERIFY", "s2-020 dibaca ulang; cincin tekanan diperiksa f12/16/24/34; still f16 & f40")
    return True


def stage_verify_c():
    verify("s2-030", frames=(60,))
    log("VERIFY", "s2-030 dibaca ulang; 6 ikan tersangkut, 20 kabur; still f60")
    return True


def stage_verify_d():
    verify("s2-090")
    verify("s3-090")
    log("VERIFY", "s2-090 & s3-090 dibaca ulang + still 50%")
    return True


def stage_verify_e():
    verify("s4-010")
    verify("s4-060")
    verify("s4-070")
    log("VERIFY", "s4-010/060/070 dibaca ulang + still 50%")
    return True


DISPATCH = {
    "s2-010": stage_s2_010,
    "s2-020": stage_s2_020,
    "s2-030": stage_s2_030,
    "s2-090": stage_s2_090,
    "s3-030": stage_s3_030,
    "s3-090": stage_s3_090,
    "s4-010": stage_s4_010,
    "s4-060": stage_s4_060,
    "s4-070": stage_s4_070,
    "verify-a": stage_verify_a,
    "verify-b": stage_verify_b,
    "verify-c": stage_verify_c,
    "verify-d": stage_verify_d,
    "verify-e": stage_verify_e,
}


def stage(name):
    return DISPATCH[name]()


if __name__ == "__main__" and "STAGE" in globals():
    stage(globals()["STAGE"])


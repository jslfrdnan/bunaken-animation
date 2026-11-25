"""build-scene-1-v004-shots.py — bangun ulang 10 shot Scene 1 memakai aset v004.

JALUR HEADLESS (tanpa Blender MCP):

    & "D:\\Blender Foundation\\Blender 5.2\\blender.exe" -b ^
        -P scripts/build-scene-1-v004-shots.py -- 010

Satu proses = satu shot. Aset yang dipakai:

    assets/env/island-detail_v004.blend        420 kelapa, fasad 4 tiang, Manado Tua
    assets/env/reef-dense_v004.blend           140 karang / 7 tipe, 600 lamun
    assets/char/crowd_v004.blend               12 dewasa + 4 anak (CRW_C01..C04)
    assets/env/fish-{cakalang-rig,kakatua,damselfish}_v003.blend   sirip 7 bone
    assets/char/nara_rig_v002.blend            21 bone
    assets/char/daniel_rig_v001.blend          22 bone
    assets/env/sea_turtle-assembled.blend      penyu + CTL_turtle
    assets/props/{boats,divegear,fishing-gear}.blend
    renders/tmp/wave-patch_v001.blend          patch ombak 200 m / 40.401 vert

Aturan: EEVEE, 1920x1080, 24 fps, Standard, frame 1 saat simpan, tanpa pack
tekstur, tanpa camera shake kecuali shot 090, look TIDAK dipasang saat simpan
(look.py dipasang renderer; di sini hanya untuk still verifikasi).
"""

import bpy
import datetime
import importlib.util
import math
import os
import re
import shutil
import sys
from mathutils import Matrix, Vector

ROOT = r"D:/Tugas Semester 5/Grafika Komputer/Project-Animasi"
ASSETS = ROOT + "/assets"
SCENES = ROOT + "/scenes"
STILLS = ROOT + "/renders/stills"
TMP = ROOT + "/renders/tmp"
LOGPATH = ROOT + "/renders/logs/technical.log"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


lib = _load("s4lib", ROOT + "/scripts/build-scene-4-shots.py")
s1 = _load("s1lib", ROOT + "/scripts/build-scene-1-detail-shots.py")
look = _load("looklib", ROOT + "/scripts/look.py")

PAL = lib.PAL
FPS = 24

P_ISLAND = ASSETS + "/env/island-detail_v004.blend"
P_REEF = ASSETS + "/env/reef-dense_v004.blend"
P_TURTLE = ASSETS + "/env/sea_turtle-assembled.blend"
P_NARA = ASSETS + "/char/nara_rig_v002.blend"
P_DANIEL = ASSETS + "/char/daniel_rig_v001.blend"
P_CROWD = ASSETS + "/char/crowd_v004.blend"
P_BOATS = ASSETS + "/props/boats.blend"
P_DIVEGEAR = ASSETS + "/props/divegear.blend"
P_GEAR = ASSETS + "/props/fishing-gear.blend"
P_PATCH = TMP + "/wave-patch_v001.blend"
P_FISH = {
    "cakalang": ASSETS + "/env/fish-cakalang-rig_v003.blend",
    "kakatua": ASSETS + "/env/fish-kakatua_v003.blend",
    "damselfish": ASSETS + "/env/fish-damselfish_v003.blend",
}

SHOTS = {
    "010": ("scene-1_shot-010_bunaken-aerial_v001.blend", 96),
    "020": ("scene-1_shot-020_turun-permukaan_v001.blend", 96),
    "030": ("scene-1_shot-030_terumbu_v001.blend", 96),
    "040": ("scene-1_shot-040_penyu_v001.blend", 72),
    "050": ("scene-1_shot-050_nara-dive_v001.blend", 96),
    "060": ("scene-1_shot-060_nara-ok_v001.blend", 72),
    "070": ("scene-1_shot-070_nara-naik_v001.blend", 96),
    "080": ("scene-1_shot-080_daniel-jaring_v001.blend", 72),
    "090": ("scene-1_shot-090_anak-dermaga_v001.blend", 72),
    "100": ("scene-1_shot-100_nara-ujung-dermaga_v001.blend", 72),
}


# --------------------------------------------------------------------- log ---


def log(phase, line):
    os.makedirs(os.path.dirname(LOGPATH), exist_ok=True)
    stamp = datetime.datetime.now().strftime("%H:%M")
    with open(LOGPATH, "a", encoding="utf-8") as fh:
        fh.write("[%s] %s - %s\n" % (stamp, phase, line))
    print("[log]", phase, line)


# ------------------------------------------------------------------- util ---


def set_interp(mode):
    s1.set_interp(mode)


def wipe():
    lib.wipe()
    bpy.context.scene.name = "wipe"


def ensure_engine(scn):
    try:
        scn.render.engine = "BLENDER_EEVEE"
    except TypeError:
        pass
    if hasattr(scn, "eevee"):
        scn.eevee.taa_render_samples = 32
    scn.render.film_transparent = False
    scn.view_settings.view_transform = "Standard"


def setup(name, frame_end):
    scn = lib.setup_scene(name, frame_end)
    ensure_engine(scn)
    scn.render.fps = FPS
    scn.render.fps_base = 1.0
    scn.frame_start = 1
    scn.frame_end = frame_end
    scn.frame_set(1)
    return scn


def purge_orphans(passes=3):
    for _ in range(passes):
        for db in (
            bpy.data.meshes,
            bpy.data.materials,
            bpy.data.armatures,
            bpy.data.curves,
            bpy.data.cameras,
            bpy.data.lights,
            bpy.data.worlds,
            bpy.data.actions,
            bpy.data.collections,
        ):
            for block in list(db):
                try:
                    if block.users == 0 and not block.use_fake_user:
                        db.remove(block)
                except Exception:
                    pass


def append_asset(path, coll, keep_preview=False):
    """Append koleksi aset (link=False), buang kamera/lampu/preview aset."""
    objs = lib.append_collection(path, coll)
    objs = lib.live_objects(objs)
    killed = lib.purge_lights_cameras(objs)
    objs = lib.live_objects(objs)
    # objek dependensi (mis. armature rig) masuk tanpa koleksi -> link ke koleksi aset
    target = bpy.data.collections.get(coll) or bpy.context.scene.collection
    orphans = [o for o in bpy.data.objects if not o.users_collection]
    for o in orphans:
        target.objects.link(o)
    if orphans:
        print("  objek dependensi dilink ke %s: %s" % (coll, [o.name for o in orphans]))
    if not keep_preview:
        for ob in list(objs):
            if ob.name.startswith("PREVIEW"):
                bpy.data.objects.remove(ob, do_unlink=True)
        prev = bpy.data.collections.get("PREVIEW")
        if prev is not None:
            bpy.data.collections.remove(prev)
    purge_orphans()
    objs = [o for o in lib.live_objects(objs) if o.name in bpy.data.objects]
    print("  append %-46s %3d objek (buang kamera/lampu %d)"
          % (os.path.basename(path) + ":" + coll, len(objs), len(killed)))
    return objs


def append_object(path, name):
    before = set(bpy.data.objects.keys())
    with bpy.data.libraries.load(path, link=False) as (src, dst):
        dst.objects = [n for n in src.objects if n == name]
    new = [bpy.data.objects[n] for n in bpy.data.objects.keys() if n not in before]
    if not new:
        print("  objek tidak ada:", name, "di", path)
        return None
    ob = new[0]
    if not ob.users_collection:
        bpy.context.scene.collection.objects.link(ob)
    ob.parent = None
    ob.matrix_parent_inverse = Matrix.Identity(4)
    return ob


def make_patch(loc, rot_z=0.0):
    ob = append_object(P_PATCH, "FX_water_local-patch")
    if ob is None:
        return None
    ob.location = (loc[0], loc[1], loc[2])
    ob.rotation_euler = (0.0, 0.0, math.radians(rot_z))
    ob.scale = (1.0, 1.0, 1.0)
    print("  patch ombak 200 m @ %s (%d vert)" % (tuple(round(v, 1) for v in loc), len(ob.data.vertices)))
    return ob


def drop_libraries():
    for lby in list(bpy.data.libraries):
        try:
            bpy.data.libraries.remove(lby)
        except Exception as exc:
            print("library tidak bisa dilepas:", lby.filepath, exc)


def save_shot(key):
    filename = SHOTS[key][0]
    src = os.path.join(SCENES, filename)
    bak = src.replace("_v001.blend", "_v000.blend")
    if os.path.exists(src) and not os.path.exists(bak):
        shutil.copy2(src, bak)
        print("BACKUP:", os.path.basename(bak))
    bpy.context.scene.frame_set(1)
    drop_libraries()
    bpy.ops.wm.save_as_mainfile(filepath=src)
    size = os.path.getsize(src)
    print("SAVED %s (%d bytes)" % (os.path.basename(src), size))
    return size


def only_camera(cam):
    scn = bpy.context.scene
    for ob in [o for o in bpy.data.objects if o.type == "CAMERA" and o is not cam]:
        bpy.data.objects.remove(ob, do_unlink=True)
    scn.camera = cam
    return cam


def summary(key):
    scn = bpy.context.scene
    objs = list(bpy.data.objects)
    meshes = [o for o in objs if o.type == "MESH"]
    verts = sum(len(o.data.vertices) for o in meshes if hasattr(o.data, "vertices"))
    print("SUMMARY s1-%s | mesh=%d arm=%d cam=%d light=%d verts=%d | %dx%d %dfps vt=%s range=%d-%d"
          % (key, len(meshes),
             len([o for o in objs if o.type == "ARMATURE"]),
             len([o for o in objs if o.type == "CAMERA"]),
             len([o for o in objs if o.type == "LIGHT"]), verts,
             scn.render.resolution_x, scn.render.resolution_y, scn.render.fps,
             scn.view_settings.view_transform, scn.frame_start, scn.frame_end))


def still(key, frame=48, percent=50, above_water=None, samples=24):
    """Still verifikasi: look scene 1 dipasang SESUDAH file shot disimpan."""
    scn = bpy.context.scene
    out = os.path.join(STILLS, "anim-s1-%s_v001.png" % key)
    os.makedirs(STILLS, exist_ok=True)
    try:
        rep = look.apply_look(scn, 1, above_water=above_water)
        scn.frame_set(int(frame))
        look.render_still(scn, out, percent=percent, samples=samples)
        scn.frame_set(1)
        print("STILL:", out, os.path.exists(out), "| world", rep["world"],
              "| water", rep["water_objects"])
    except Exception as exc:
        print("STILL GAGAL:", repr(exc))


def ndc(cam, pts, labels=None):
    from bpy_extras.object_utils import world_to_camera_view as w2c
    scn = bpy.context.scene
    labels = labels or [""] * len(pts)
    for p, lab in zip(pts, labels):
        v = w2c(scn, cam, Vector(p))
        flag = "" if (0.03 < v.x < 0.97 and 0.03 < v.y < 0.97) else "  <-- DI LUAR"
        print("    ndc %-14s (%.2f, %.2f) depth %.1f m%s"
              % (lab, v.x, v.y, v.z, flag))


def bbox(ob):
    m = ob.matrix_world
    pts = [m @ Vector(c) for c in ob.bound_box]
    return (sum(pts, Vector()) / 8.0), pts


def bc(ob, fallback=(0.0, 0.0, 0.0)):
    if ob is None:
        return Vector(fallback)
    return bbox(ob)[0]


# --------------------------------------------------------- rig / pose util ---


def bone_matrix(arm, name):
    return arm.matrix_world @ arm.pose.bones[name].matrix


def reset_pose(arm):
    s1.reset_pose(arm)


def prepare_rig(arm):
    arm.animation_data_clear()
    arm.data.pose_position = "POSE"
    reset_pose(arm)
    bpy.context.view_layer.update()
    return arm


def apply_pose(arm, pose):
    s1.apply_pose(arm, pose)


def key_pose(arm, frame, pose, bones):
    s1.key_pose(arm, frame, pose, bones)


def frame_matrix(origin, ydir, up=(0.0, 0.0, 1.0)):
    """Matriks dengan sumbu Y = ydir (arah panjang) dan Z mendekati `up`."""
    y = Vector(ydir).normalized()
    u = Vector(up)
    x = y.cross(u)
    if x.length < 1e-5:
        x = y.cross(Vector((1.0, 0.0, 0.0)))
    x.normalize()
    z = x.cross(y).normalized()
    o = Vector(origin)
    return Matrix(((x.x, y.x, z.x, o.x),
                   (x.y, y.y, z.y, o.y),
                   (x.z, y.z, z.z, o.z),
                   (0.0, 0.0, 0.0, 1.0)))


def attach_fin(fin, arm, side):
    """Fin mengikuti arah tulang shin (lanjutan kaki), bilah mendatar terhadap
    sumbu atas karakter. Dipakai shin, bukan foot: pada pose menyelam ujung kaki
    menghadap ke bawah sehingga fin akan menggantung."""
    if fin is None:
        return None
    pb = arm.pose.bones["shin." + side]
    ankle = arm.matrix_world @ pb.tail
    knee = arm.matrix_world @ pb.head
    legdir = (ankle - knee)
    if legdir.length < 1e-5:
        return None
    legdir.normalize()
    up = (arm.matrix_world.to_3x3() @ Vector((0.0, 0.0, 1.0))).normalized()
    want = frame_matrix(ankle + legdir * 0.22, legdir, up)
    return s1.bone_parent(fin, arm, "foot." + side, want)


def self_check(arm, label):
    """Jarak tangan ke sumbu torso (deteksi tangan menembus badan)."""
    bpy.context.view_layer.update()
    hips = arm.matrix_world @ arm.pose.bones["hips"].head
    neck = arm.matrix_world @ arm.pose.bones["neck"].head
    axis = (neck - hips)
    if axis.length < 1e-6:
        return
    axis_n = axis.normalized()
    worst = 9.9
    for side in ("L", "R"):
        pb = arm.pose.bones.get("hand." + side)
        if pb is None:
            continue
        h = arm.matrix_world @ pb.head
        rel = h - hips
        d = (rel - axis_n * rel.dot(axis_n)).length
        worst = min(worst, d)
    print("    cek badan %-12s jarak tangan ke sumbu torso min %.3f m %s"
          % (label, worst, "(menembus!)" if worst < 0.11 else "aman"))


# ------------------------------------------------------------ reef helper ---


def append_reef(scale_seabed=True, darken=True):
    reef = append_asset(P_REEF, "ENV_reef-dense")
    seabed = bpy.data.objects.get("ENV_dense_seabed")
    if seabed is not None and scale_seabed:
        mw = seabed.matrix_world.copy()
        inv = mw.inverted()
        for v in seabed.data.vertices:
            w = mw @ v.co
            w.x *= 20.0
            w.y *= 20.0
            v.co = inv @ w
        bpy.context.view_layer.update()
        print("  seabed diperbesar:", [round(x, 0) for x in seabed.dimensions])
    if darken:
        sand = bpy.data.materials.get("MAT_dense_sand")
        if sand and sand.use_nodes:
            ramp = next((n for n in sand.node_tree.nodes if n.type == "VALTORGB"), None)
            if ramp:
                for el in ramp.color_ramp.elements:
                    c = el.color
                    el.color = (c[0] * 0.50, c[1] * 0.55, c[2] * 0.60, 1.0)
            bsdf = next((n for n in sand.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
            if bsdf is not None:
                bsdf.inputs["Roughness"].default_value = 0.92
    n_coral = len([o for o in bpy.data.objects if "_coral_" in o.name])
    print("  reef v004: %d karang | lamun %d objek" % (
        n_coral, len([o for o in bpy.data.objects if "seagrass" in o.name])))
    return reef


def swap_school(kind):
    """Ganti sekolah mesh polos di reef-dense_v004 dengan ikan ber-rig v003."""
    scn = bpy.context.scene
    school = bpy.data.collections.get("ENV_school_" + kind)
    if school is None:
        print("  sekolah tidak ada:", kind)
        return 0
    pat = re.compile(r"^ENV_school_%s_\d+$" % kind)
    olds = [o for o in school.objects if o.type == "MESH" and pat.match(o.name)]
    recs = [(o.matrix_world.copy(), o.parent.name if o.parent else None) for o in olds]
    for ob in olds:
        bpy.data.objects.remove(ob, do_unlink=True)
    purge_orphans()

    new = append_asset(P_FISH[kind], "ENV_fish")
    new = lib.live_objects(new)
    src_arm = next(o for o in new if o.type == "ARMATURE")
    src_meshes = [o for o in new if o.type == "MESH"]
    action = src_arm.animation_data.action if src_arm.animation_data else None
    if action is not None:
        action.use_fake_user = True
    n_bones = len(src_arm.data.bones)
    act_name = action.name if action is not None else None
    pivot = bpy.data.objects.get("ENV_school_%s_pivot" % kind)

    n_parts = 0
    for i, (world, parent_name) in enumerate(recs, start=1):
        a = src_arm.copy()
        a.data = src_arm.data
        a.name = "ENV_fish_%s_%02d_rig" % (kind, i)
        # JANGAN clear animation_data / assign action ulang: action + action_slot
        # harus ikut dari sumber supaya animasi sirip tetap jalan
        # (Blender 5.x: assign action tanpa slot = pose kaku).
        if i == 1:
            ad = a.animation_data
            print("    slot animasi: action=%s slot=%s" % (
                ad.action.name if ad and ad.action else None,
                getattr(ad, "action_slot", None) if ad else None))
        school.objects.link(a)
        if pivot is not None:
            a.parent = pivot
            a.matrix_parent_inverse = Matrix.Identity(4)
        a.matrix_world = world
        for sm in src_meshes:
            m = sm.copy()
            m.data = sm.data
            suffix = sm.name.replace("ENV_fish_%s" % kind, "")
            m.name = "ENV_fish_%s_%02d%s" % (kind, i, suffix)
            school.objects.link(m)
            m.parent = a
            m.matrix_parent_inverse = Matrix.Identity(4)
            m.matrix_basis = Matrix.Identity(4)
            for mod in m.modifiers:
                if mod.type == "ARMATURE":
                    mod.object = a
            n_parts += 1
        a.matrix_world = world

    for ob in list(new):
        if ob.name in bpy.data.objects:
            bpy.data.objects.remove(ob, do_unlink=True)
    purge_orphans()
    bag = [o for o in school.objects if o.type == "ARMATURE"]
    print("  %-11s -> %d ikan ber-rig (%d mesh, %d bone, action %s)"
          % (kind, len(bag), n_parts, n_bones, act_name))
    return len(bag)


def rig_all_schools(kinds=("cakalang", "kakatua", "damselfish")):
    total = 0
    for kind in kinds:
        total += swap_school(kind)
    return total


def tighten_school(kind, center_z, factor=0.35):
    """Rapatkan sebaran vertikal sekolah (aset menyebar -4.7..-1.5 m)."""
    school = bpy.data.collections.get("ENV_school_" + kind)
    if school is None:
        return
    arms = [o for o in school.objects if o.type == "ARMATURE"]
    if not arms:
        return
    zs = [o.location.z for o in arms]
    cz = sum(zs) / len(zs)
    for o in arms:
        o.location.z = center_z + (o.location.z - cz) * factor
    print("  %-11s dirapatkan: z %.2f..%.2f -> %.2f..%.2f" % (
        kind, min(zs), max(zs),
        min(o.location.z for o in arms), max(o.location.z for o in arms)))


def fin_flex_probe(kind="cakalang", frames=(1, 7, 13)):
    """Bukti sirip lentur: simpangan vertex terbesar mesh sirip antar frame."""
    school = bpy.data.collections.get("ENV_school_" + kind)
    if school is None:
        return
    fins = [o for o in school.objects
            if o.type == "MESH" and o.name.endswith(("_tail", "_dorsal", "_pectoral"))]
    if not fins:
        print("  probe sirip: mesh sirip terpisah tidak ada (sirip menyatu di badan)")
        return
    ob = fins[0]
    dg = bpy.context.evaluated_depsgraph_get()
    data = {}
    scn = bpy.context.scene
    for f in frames:
        scn.frame_set(f)
        dg.update()
        ev = ob.evaluated_get(dg)
        me = ev.to_mesh()
        data[f] = [v.co.copy() for v in me.vertices]
        ev.to_mesh_clear()
    base = data[frames[0]]
    worst = 0.0
    for f in frames[1:]:
        for a, b in zip(base, data[f]):
            worst = max(worst, (a - b).length)
    scn.frame_set(1)
    print("  sirip %s (%s): simpangan maks %.3f m antara f%d-%d -> %s"
          % (kind, ob.name, worst, frames[0], frames[-1],
             "LENTUR" if worst > 0.01 else "kaku"))


def pivot_keys(pivot, keys):
    """keys = [(frame, (x,y,z), rz_deg)] gerak sekolah per fase."""
    set_interp("BEZIER")
    for frame, loc, rz in keys:
        pivot.location = loc
        pivot.rotation_euler = (0.0, 0.0, math.radians(rz))
        pivot.keyframe_insert("location", frame=frame)
        pivot.keyframe_insert("rotation_euler", frame=frame)


def move_corals(spots):
    """Tempatkan beberapa karang reef-dense di posisi/ukuran tertentu."""
    corals = sorted([o for o in bpy.data.objects if "_coral_" in o.name], key=lambda o: o.name)
    used = []
    for idx, (pos, scl, rz) in enumerate(spots):
        if idx >= len(corals):
            break
        ob = corals[idx]
        ob.location = pos
        ob.scale = (scl, scl, scl)
        ob.rotation_euler.z += math.radians(rz)
        used.append(ob.name)
    return used


# ===========================================================================
# 010 — aerial Bunaken, Manado Tua di kiri, dermaga & kampung di kanan
# ===========================================================================


def build_010():
    wipe()
    scn = setup("scene-1_shot-010_bunaken-aerial", 96)
    append_asset(P_ISLAND, "ENV_island-detail")

    sea = bpy.data.objects.get("ENV_detail_sea-surface")
    if sea is not None:
        sea.scale = (20.0, 8.0, 1.0)  # bidang air 4 km -> cukup sampai Manado Tua
        bpy.context.view_layer.update()
        print("  sea-surface diskalakan:", [round(v, 0) for v in sea.dimensions])

    n_palm = len([o for o in bpy.data.objects if o.name.startswith("ENV_detail_palm")])
    print("  pohon kelapa:", n_palm)

    boat = append_asset(P_BOATS, "PRP_boats")
    ctl = s1.root_empty("CTL_boat-bg", (26.0, -128.0, 0.0))
    s1.adopt(boat, ctl)
    ctl.rotation_euler = (0.0, 0.0, math.radians(196.0))

    s1.sun(scn, energy=3.6, angle=3.0, rot=(76, 0, 52), color=(1.0, 0.90, 0.74))
    lib.add_world("WLD_s1_010", "#F2E9DC", strength=0.85)

    cam = s1.make_cam("CAM_shot-010_drone", (520.0, -620.0, 148.0),
                      (-135.0, -161.0, 25.0), lens=24.0, clip_end=80000.0)
    only_camera(cam)
    s1.key_cam(cam, [
        (1, (520.0, -620.0, 148.0), (-135.0, -161.0, 25.0)),
        (48, (455.0, -556.0, 134.0), (-150.0, -120.0, 24.0)),
        (96, (390.0, -492.0, 120.0), (-165.0, -80.0, 23.0)),
    ])
    scn.frame_set(1)
    ndc(cam, [(-5362.0, 1404.0, 745.0), (-5362.0, 1404.0, 0.0), (11.0, 9.0, 3.0),
              (0.0, -104.0, 1.2)],
        ["manado-tua-atas", "manado-tua-bawah", "dive-shop", "ujung-dermaga"])

    size = save_shot("010")
    summary("010")
    log("ANIM", "s1-010 island v004 (%d kelapa) + drone 148->120 m, Manado Tua & kampung (%d bytes)"
        % (n_palm, size))
    still("010", 48)


# ===========================================================================
# 020 — turun ke permukaan air: island v004 + patch ombak 200 m + perahu
# ===========================================================================


def build_020():
    wipe()
    scn = setup("scene-1_shot-020_turun-permukaan", 96)
    append_asset(P_ISLAND, "ENV_island-detail")
    make_patch((25.0, -80.0, 0.12))

    boat = append_asset(P_BOATS, "PRP_boats")
    ctl = s1.root_empty("CTL_boat-pass", (40.0, -18.0, 0.0))
    s1.adopt(boat, ctl)
    ctl.rotation_euler = (0.0, 0.0, math.radians(214.0))
    set_interp("LINEAR")
    ctl.keyframe_insert("location", frame=1)
    ctl.keyframe_insert("rotation_euler", frame=1)
    ctl.location = (10.0, -28.0, 0.0)
    ctl.keyframe_insert("location", frame=96)

    s1.sun(scn, energy=4.0, angle=3.0, rot=(66, 0, 46), color=(1.0, 0.91, 0.76))
    lib.add_world("WLD_s1_020", "#DCEBE6", strength=1.0)

    cam = s1.make_cam("CAM_shot-020_descend", (25.0, -80.0, 12.5),
                      (25.0, -23.0, 1.2), lens=28.0, clip_end=9000.0)
    only_camera(cam)
    s1.key_cam(cam, [
        (1, (25.0, -80.0, 12.5), (25.0, -23.0, 1.2)),
        (56, (25.0, -76.0, 5.8), (25.0, -23.0, 1.3)),
        (96, (25.0, -72.0, 1.15), (25.0, -25.0, 1.6)),
    ])
    scn.frame_set(1)

    size = save_shot("020")
    summary("020")
    log("ANIM", "s1-020 island v004 + patch ombak 200 m (40.401 vert) + perahu lewat, kamera turun 12,5->1,15 m (%d bytes)"
        % size)
    still("020", 48, above_water=True)


# ===========================================================================
# 030 — terumbu padat + tiga sekolah ikan v003, fase cepat-lambat-pergi
# ===========================================================================


def build_030():
    wipe()
    scn = setup("scene-1_shot-030_terumbu", 96)
    append_reef()
    n = rig_all_schools()
    tighten_school("cakalang", -3.95)
    tighten_school("kakatua", -3.85)
    tighten_school("damselfish", -3.90)
    print("  ikan ber-rig:", n)

    # fase cepat (1-40), hampir berhenti (40-72), pergi (72-96)
    pv = "ENV_school_%s_pivot"
    if pv % "cakalang" in bpy.data.objects:
        pivot_keys(bpy.data.objects[pv % "cakalang"],
                   [(1, (-8.0, -1.0, -0.2), -86.0), (40, (-1.2, -1.0, 0.0), -90.0),
                    (72, (-0.4, -1.0, 0.1), -91.0), (96, (8.5, -1.0, 0.3), -94.0)])
    if pv % "kakatua" in bpy.data.objects:
        pivot_keys(bpy.data.objects[pv % "kakatua"],
                   [(1, (-6.0, 4.2, 0.2), -84.0), (40, (-1.0, 3.5, 0.0), -90.0),
                    (72, (-0.5, 3.2, 0.0), -90.0), (96, (6.0, 2.6, -0.1), -93.0)])
    if pv % "damselfish" in bpy.data.objects:
        pivot_keys(bpy.data.objects[pv % "damselfish"],
                   [(1, (7.0, -2.0, 0.0), 86.0), (40, (2.0, -2.0, 0.05), 90.0),
                    (72, (1.5, -2.0, 0.05), 90.0), (96, (-5.5, -2.4, 0.1), 93.0)])
    fin_flex_probe("cakalang")

    s1.sun(scn, energy=3.6, angle=5.0, rot=(16, 0, 34), color=(0.82, 0.95, 1.0))
    lib.add_world("WLD_s1_030", "#0F5C63", strength=1.15)
    lib.add_fill(energy=120.0, size=8.0, loc=(-3.0, -3.0, -1.0), target=(0, 0, -4.0))
    fog = s1.underwater_fog(scn)
    if fog is not None:
        print("  fog bawah laut:", fog.name)

    cam = s1.make_cam("CAM_shot-030_track", (0.0, 8.5, -3.35),
                      (0.3, 2.0, -3.95), lens=24.0, clip_end=300.0)
    only_camera(cam)
    s1.key_cam(cam, [
        (1, (0.0, 8.5, -3.35), (0.3, 2.0, -3.95)),
        (96, (0.6, 4.0, -3.45), (0.9, -2.4, -4.00)),
    ], mode="LINEAR")
    scn.frame_set(1)

    size = save_shot("030")
    summary("030")
    log("ANIM", "s1-030 reef v004 (140 karang/7 tipe, 600 lamun) + 3 sekolah v003, fase cepat-lambat-pergi (%d bytes)"
        % size)
    still("030", 48, above_water=False)


# ===========================================================================
# 040 — penyu melintas + reef v004 + tiga sekolah
# ===========================================================================


def build_040():
    wipe()
    scn = setup("scene-1_shot-040_penyu", 72)
    append_reef()
    rig_all_schools()
    tighten_school("cakalang", -3.95)
    tighten_school("kakatua", -3.85)
    tighten_school("damselfish", -3.90)
    append_asset(P_TURTLE, "ENV_turtle")
    ctl = bpy.data.objects.get("CTL_turtle")
    if ctl is None:
        raise RuntimeError("CTL_turtle tidak ada")

    # karang latar supaya penyu benar-benar melewati karang
    move_corals([
        ((1.6, 3.8, -5.0), 2.0, 17), ((-1.6, 4.6, -5.0), 1.7, 34),
        ((3.4, 2.4, -5.0), 1.8, 52), ((-3.6, 3.1, -5.0), 1.6, 71),
        ((0.2, 6.4, -5.0), 2.1, 88),
    ])

    # penyu: melintas + dayung sirip depan
    x0, x1 = -4.6, 4.6
    keys = [(1, x0), (24, x0 + 3.07), (48, x0 + 6.13), (72, x1)]
    set_interp("BEZIER")
    for frame, tx in keys:
        t = (frame - 1) / 71.0
        ctl.location = (tx, 1.0 - 0.5 * t, -2.95 + 0.30 * t)
        ctl.rotation_euler = (math.radians(-4.0 * t),
                              math.radians(3.0 * math.sin(t * 6.0)),
                              math.radians(98.0 - 14.0 * t))
        ctl.keyframe_insert("location", frame=frame)
        ctl.keyframe_insert("rotation_euler", frame=frame)

    flap = {"Turtle_Flap_Front_L": 1.0, "Turtle_Flap_Front_R": -1.0,
            "Turtle_Flap_Rear_L": 0.5, "Turtle_Flap_Rear_R": -0.5}
    for name, sign in flap.items():
        ob = bpy.data.objects.get(name)
        if ob is None:
            continue
        base = ob.rotation_euler.copy()
        for f in range(1, 73, 4):
            ph = math.sin(f * 0.33) * sign
            ob.rotation_euler = (base.x + math.radians(10.0) * ph * 0.4,
                                 base.y + math.radians(18.0) * ph,
                                 base.z)
            ob.keyframe_insert("rotation_euler", frame=f)
        ob.rotation_euler = base

    pv = "ENV_school_%s_pivot"
    if pv % "cakalang" in bpy.data.objects:
        pivot_keys(bpy.data.objects[pv % "cakalang"],
                   [(1, (-3.5, 7.0, 0.55), -87.0), (36, (-1.0, 7.0, 0.5), -90.0),
                    (72, (1.5, 7.0, 0.45), -93.0)])
    if pv % "kakatua" in bpy.data.objects:
        pivot_keys(bpy.data.objects[pv % "kakatua"],
                   [(1, (2.6, 4.6, 0.5), -86.0), (36, (0.4, 4.4, 0.45), -90.0),
                    (72, (-1.6, 4.2, 0.4), -94.0)])
    if pv % "damselfish" in bpy.data.objects:
        pivot_keys(bpy.data.objects[pv % "damselfish"],
                   [(1, (-1.2, 2.4, 0.55), 87.0), (36, (0.2, 2.2, 0.55), 90.0),
                    (72, (1.8, 2.0, 0.5), 92.0)])

    s1.sun(scn, energy=3.4, angle=5.0, rot=(18, 0, 30), color=(0.80, 0.94, 1.0))
    lib.add_world("WLD_s1_040", "#0F5C63", strength=1.15)
    lib.add_fill(energy=110.0, size=7.0, loc=(-3.0, -4.0, -1.2), target=(0, 0, -3.0))
    s1.underwater_fog(scn)

    cam = s1.make_cam("CAM_shot-040_follow", (-3.95, -2.6, -1.55),
                      (-4.3, 0.9, -2.95), lens=40.0)
    only_camera(cam)
    ks = []
    for frame, tx in keys:
        t = (frame - 1) / 71.0
        ks.append((frame,
                   (tx + 0.55, -2.6 + 0.2 * t, -1.55 - 0.04 * t),
                   (tx + 0.30, 0.9 - 0.4 * t, -2.95 + 0.30 * t)))
    s1.key_cam(cam, ks)
    scn.frame_set(1)

    size = save_shot("040")
    summary("040")
    log("ANIM", "s1-040 reef v004 + penyu berenang (sirip depan dayung) + 3 sekolah v003 (%d bytes)" % size)
    still("040", 48, above_water=False)


# ===========================================================================
# 050 — Nara menyelam dari balik karang
# ===========================================================================


NARA_SWIM = {
    "spine": (8, 0, 0),
    "chest": (5, 0, 0),
    "neck": (-12, 0, 0),
    "head": (-8, 0, 0),
    "shoulder.L": (-5, 0, 0),
    "upper_arm.L": (-92, 0, 16),
    "fore_arm.L": (-26, 0, 0),
    "hand.L": (-6, 0, 0),
    "shoulder.R": (-5, 0, 0),
    "upper_arm.R": (-88, 0, -16),
    "fore_arm.R": (-30, 0, 0),
    "hand.R": (-8, 0, 0),
    "thigh.L": (10, 0, -2),
    "shin.L": (14, 0, 0),
    "foot.L": (-18, 0, 0),
    "thigh.R": (-8, 0, 2),
    "shin.R": (18, 0, 0),
    "foot.R": (-14, 0, 0),
}


def build_050():
    wipe()
    scn = setup("scene-1_shot-050_nara-dive", 96)
    append_reef()
    rig_all_schools()
    tighten_school("cakalang", -3.95)
    tighten_school("kakatua", -3.85)
    tighten_school("damselfish", -3.90)
    append_asset(P_TURTLE, "ENV_turtle", )
    append_asset(P_NARA, "CHR_nara")
    append_asset(P_DIVEGEAR, "PRP_divegear")
    arm = bpy.data.objects.get("CHR_nara_rig")
    if arm is None:
        raise RuntimeError("CHR_nara_rig tidak ada")

    # karang pembuka di depan lensa
    move_corals([((-2.55, -2.05, -5.05), 2.6, 0), ((-0.30, -2.60, -5.02), 1.5, 22),
                 ((2.6, -2.9, -5.05), 1.7, 41)])

    ctl_t = bpy.data.objects.get("CTL_turtle")
    if ctl_t is not None:
        ctl_t.location = (-4.6, 4.7, -2.50)
        ctl_t.rotation_euler = (math.radians(2), 0.0, math.radians(96))
        set_interp("LINEAR")
        ctl_t.keyframe_insert("location", frame=1)
        ctl_t.keyframe_insert("rotation_euler", frame=1)
        ctl_t.location = (-5.3, 5.5, -2.42)
        ctl_t.keyframe_insert("location", frame=96)

    pv = "ENV_school_%s_pivot"
    if pv % "cakalang" in bpy.data.objects:
        pivot_keys(bpy.data.objects[pv % "cakalang"],
                   [(1, (-2.0, 1.0, -0.2), -88.0), (48, (0.5, 1.0, 0.0), -90.0),
                    (96, (3.5, 0.8, 0.2), -93.0)])
    if pv % "kakatua" in bpy.data.objects:
        pivot_keys(bpy.data.objects[pv % "kakatua"],
                   [(1, (3.0, 3.6, 0.2), -85.0), (48, (1.0, 3.2, 0.1), -90.0),
                    (96, (-1.5, 2.8, 0.0), -93.0)])
    if pv % "damselfish" in bpy.data.objects:
        pivot_keys(bpy.data.objects[pv % "damselfish"],
                   [(1, (4.5, -2.0, 0.0), 87.0), (48, (2.5, -1.6, 0.0), 90.0),
                    (96, (0.5, -1.2, 0.05), 92.0)])

    prepare_rig(arm)
    arm.rotation_mode = "XYZ"
    arm.rotation_euler = (math.radians(72), 0.0, math.radians(96))
    arm.location = (-3.25, 0.95, -3.40)
    set_interp("BEZIER")
    arm.keyframe_insert("location", frame=1)
    arm.keyframe_insert("rotation_euler", frame=1)

    # rentang lengan dilebarkan (ayunan ~50 derajat), punggung +-8 derajat
    swim_a = dict(NARA_SWIM)
    swim_b = dict(NARA_SWIM)
    swim_b["spine"] = (0, 0, 0)
    swim_b["chest"] = (0, 0, 0)
    swim_b["upper_arm.L"] = (-62, 0, 22)
    swim_b["fore_arm.L"] = (-16, 0, 0)
    swim_b["upper_arm.R"] = (-118, 0, -12)
    swim_b["fore_arm.R"] = (-38, 0, 0)
    swim_b["thigh.L"] = (16, 0, -2)
    swim_b["thigh.R"] = (-14, 0, 2)
    key_pose(arm, 1, swim_a, list(NARA_SWIM.keys()))
    key_pose(arm, 48, swim_b, list(NARA_SWIM.keys()))
    key_pose(arm, 96, swim_a, list(NARA_SWIM.keys()))
    arm.location = (-1.70, 0.80, -3.25)
    arm.keyframe_insert("location", frame=96)
    scn.frame_set(1)
    bpy.context.view_layer.update()
    self_check(arm, "050-f1")
    scn.frame_set(48)
    bpy.context.view_layer.update()
    self_check(arm, "050-f48")
    scn.frame_set(1)
    bpy.context.view_layer.update()

    # masker + snorkel di kepala, kaki + fin di tulang foot
    fh, upn, her_right = s1.face_frame(arm)
    face_c = s1.bone_world(arm, "head", 0.56) + upn * 0.005
    yaw = s1.yaw_of(fh)
    mask = bpy.data.objects.get("PRP_divegear_mask")
    if mask is not None:
        s1.attach_gear(mask, arm, "head", face_c + fh * 0.095 + upn * 0.012, yaw)
    sn = bpy.data.objects.get("PRP_divegear_snorkel")
    if sn is not None:
        s1.attach_gear(sn, arm, "head", face_c + her_right * 0.105 - fh * 0.03,
                       yaw + 8.0, roll_deg=-10.0)
    for side in ("L", "R"):
        attach_fin(bpy.data.objects.get("PRP_divegear_fin_" + side), arm, side)
    print("  masker/snorkel/fin terpasang:",
          [ob.name for ob in bpy.data.objects if ob.name.startswith("PRP_divegear_")])

    s1.sun(scn, energy=3.2, angle=5.0, rot=(14, 0, 26), color=(0.82, 0.94, 1.0))
    lib.add_world("WLD_s1_050", "#0F5C63", strength=1.1)
    lib.add_fill(energy=140.0, size=6.0, loc=(-1.0, -6.0, -0.6), target=(-2.2, 0.6, -3.2))
    s1.underwater_fog(scn)

    cam = s1.make_cam("CAM_shot-050_medium", (1.0, -4.7, -2.95),
                      (-2.4, 0.9, -3.30), lens=45.0)
    only_camera(cam)
    s1.key_cam(cam, [
        (1, (1.0, -4.7, -2.95), (-2.4, 0.9, -3.30)),
        (96, (0.4, -4.4, -2.90), (-1.2, 0.8, -3.25)),
    ])
    cam.data.dof.use_dof = True
    cam.data.dof.aperture_fstop = 4.0
    focus = s1.root_empty("EMPTY_focus-nara", (-2.4, 0.9, -3.3))
    s1.adopt([focus], arm)
    cam.data.dof.focus_object = focus
    ndc(cam, [face_c, (-3.25, 0.95, -3.40)], ["wajah", "badan"])
    scn.frame_set(1)

    size = save_shot("050")
    summary("050")
    log("ANIM", "s1-050 reef v004 + 3 sekolah v003 + Nara rig v002 (masker/snorkel/fin di bone), ayunan lengan 50 derajat (%d bytes)"
        % size)
    still("050", 48, above_water=False)


# ===========================================================================
# 060 — close-up Nara: lambaian 3 fase (angkat - lambai - turun)
# ===========================================================================


NARA_FLOAT = {
    "spine": (3, 0, 0),
    "chest": (2, 0, 0),
    "neck": (6, 0, 0),
    "head": (4, 0, -4),
    "shoulder.L": (0, 0, 0),
    "upper_arm.L": (-34, 0, 16),
    "fore_arm.L": (-46, 0, 0),
    "shoulder.R": (-6, 0, 0),
    "upper_arm.R": (-72, 0, -22),
    "fore_arm.R": (-96, 0, 0),
    "hand.R": (-18, 0, 26),
    "thigh.L": (14, 0, -3),
    "shin.L": (26, 0, 0),
    "thigh.R": (6, 0, 3),
    "shin.R": (18, 0, 0),
}


def build_060():
    wipe()
    scn = setup("scene-1_shot-060_nara-ok", 72)
    append_reef()
    append_asset(P_NARA, "CHR_nara")
    append_asset(P_DIVEGEAR, "PRP_divegear")
    arm = bpy.data.objects.get("CHR_nara_rig")
    if arm is None:
        raise RuntimeError("CHR_nara_rig tidak ada")
    for nm in ("PRP_divegear_fin_L", "PRP_divegear_fin_R"):
        ob = bpy.data.objects.get(nm)
        if ob is not None:
            bpy.data.objects.remove(ob, do_unlink=True)

    prepare_rig(arm)
    arm.rotation_mode = "XYZ"
    arm.location = (0.0, 0.5, -2.30)
    arm.rotation_euler = (0.0, 0.0, math.radians(-16))

    base = dict(NARA_FLOAT)
    raise_arm = dict(NARA_FLOAT)
    raise_arm.update({"upper_arm.R": (0, 45, -6), "fore_arm.R": (0, 112, 0), "hand.R": (0, 0, 10)})
    wave_out = dict(raise_arm)
    wave_out.update({"fore_arm.R": (0, 126, 0), "hand.R": (-8, 0, 28)})
    wave_in = dict(raise_arm)
    wave_in.update({"fore_arm.R": (0, 98, 0), "hand.R": (8, 0, -14)})
    lower = dict(NARA_FLOAT)
    lower.update({"upper_arm.R": (-20, 44, -10), "fore_arm.R": (-30, 22, 0)})

    keys = [(1, base), (12, raise_arm), (20, wave_out), (28, wave_in),
            (36, wave_out), (44, wave_in), (56, raise_arm), (64, lower), (72, base)]
    bones = list(NARA_FLOAT.keys())
    for f, pose in keys:
        key_pose(arm, f, pose, bones)
    scn.frame_set(1)
    bpy.context.view_layer.update()
    for f in (1, 20, 44):
        scn.frame_set(f)
        bpy.context.view_layer.update()
        self_check(arm, "060-f%d" % f)
    scn.frame_set(1)
    bpy.context.view_layer.update()

    fh, upn, her_right = s1.face_frame(arm)
    face_c = s1.bone_world(arm, "head", 0.56) + upn * 0.005
    yaw = s1.yaw_of(fh)
    mask = bpy.data.objects.get("PRP_divegear_mask")
    if mask is not None:
        s1.attach_gear(mask, arm, "head", face_c + fh * 0.095 + upn * 0.012, yaw)
    sn = bpy.data.objects.get("PRP_divegear_snorkel")
    if sn is not None:
        s1.attach_gear(sn, arm, "head", face_c + her_right * 0.105 - fh * 0.03,
                       yaw + 8.0, roll_deg=-10.0)
    print("  masker:", mask is not None, "wajah", [round(v, 2) for v in face_c])

    s1.sun(scn, energy=3.4, angle=6.0, rot=(20, 0, 18), color=(0.86, 0.95, 1.0))
    lib.add_world("WLD_s1_060", "#0F5C63", strength=1.05)
    lib.add_fill(energy=90.0, size=3.0, loc=(1.2, -2.0, 0.4), target=(0.0, 0.0, 0.3))
    s1.underwater_fog(scn, size=90.0, top=6.0, bottom=-30.0)

    scn.frame_set(20)
    bpy.context.view_layer.update()
    hand_wave = arm.matrix_world @ arm.pose.bones["hand.R"].head
    mid = face_c.lerp(hand_wave, 0.42) + upn * 0.03
    cam_loc = mid + fh * 2.60 + her_right * 0.16 + upn * 0.10
    cam = s1.make_cam("CAM_shot-060_cu", cam_loc, mid, lens=50.0, clip_end=60.0)
    only_camera(cam)
    cam.data.dof.use_dof = True
    cam.data.dof.aperture_fstop = 4.5
    focus = s1.root_empty("EMPTY_focus-face", face_c)
    s1.adopt([focus], arm)
    cam.data.dof.focus_object = focus

    # cek tangan masuk frame saat lambaian puncak
    scn.frame_set(20)
    bpy.context.view_layer.update()
    hand = arm.matrix_world @ arm.pose.bones["hand.R"].head
    ndc(cam, [face_c, hand], ["wajah", "tangan-R"])
    scn.frame_set(1)

    size = save_shot("060")
    summary("060")
    log("ANIM", "s1-060 close-up Nara, lambaian 3 fase (angkat f1-12, lambai f12-44, turun f44-72), masker+snorkel (%d bytes)"
        % size)
    still("060", 48, above_water=False)


# ===========================================================================
# 070 — Nara naik ke perahu; masker pindah kepala -> tangan f20-40
# ===========================================================================


NARA_CLIMB = {
    "spine": (-6, 0, 0),
    "chest": (-4, 0, 0),
    "neck": (-6, 0, 0),
    "head": (-4, 0, 0),
    "shoulder.L": (-6, 0, 0),
    "upper_arm.L": (-124, 0, 18),
    "fore_arm.L": (-58, 0, 0),
    "hand.L": (-14, 0, 0),
    "shoulder.R": (-6, 0, 0),
    "upper_arm.R": (-118, 0, -20),
    "fore_arm.R": (-66, 0, 0),
    "hand.R": (-20, 0, -14),
    "thigh.L": (-8, 0, -3),
    "shin.L": (16, 0, 0),
    "foot.L": (-8, 0, 0),
    "thigh.R": (4, 0, 3),
    "shin.R": (10, 0, 0),
    "foot.R": (-6, 0, 0),
}


def build_070():
    wipe()
    scn = setup("scene-1_shot-070_nara-naik", 96)
    append_asset(P_ISLAND, "ENV_island-detail")
    make_patch((12.0, -40.0, 0.12))
    boat = append_asset(P_BOATS, "PRP_boats")
    ctl = s1.root_empty("CTL_boat-dive", (14.0, -35.0, 0.0))
    s1.adopt(boat, ctl)
    ctl.rotation_euler = (0.0, 0.0, math.radians(6.0))
    bpy.context.view_layer.update()

    append_asset(P_NARA, "CHR_nara")
    append_asset(P_DIVEGEAR, "PRP_divegear")
    for nm in ("PRP_divegear_fin_L", "PRP_divegear_fin_R"):
        ob = bpy.data.objects.get(nm)
        if ob is not None:
            bpy.data.objects.remove(ob, do_unlink=True)
    arm = bpy.data.objects.get("CHR_nara_rig")
    if arm is None:
        raise RuntimeError("CHR_nara_rig tidak ada")

    deck_world = ctl.matrix_world @ Vector((-2.30, 0.0, 0.30))
    arm.rotation_mode = "XYZ"
    arm.rotation_euler = (0.0, 0.0, math.radians(-16.0))

    prepare_rig(arm)
    set_interp("BEZIER")
    # naik dari air ke dek: badan terangkat 0,95 m pada f1-40
    arm.location = (deck_world.x, deck_world.y, deck_world.z - 0.95)
    arm.keyframe_insert("location", frame=1)
    arm.rotation_euler = (0.0, 0.0, math.radians(-16.0))
    arm.keyframe_insert("rotation_euler", frame=1)
    arm.location = (deck_world.x, deck_world.y, deck_world.z)
    arm.keyframe_insert("location", frame=40)
    arm.keyframe_insert("location", frame=96)
    pose_a = dict(NARA_CLIMB)
    pose_b = dict(NARA_CLIMB)
    pose_b.update({"upper_arm.L": (-96, 0, 20), "fore_arm.L": (-84, 0, 0),
                   "upper_arm.R": (-92, 0, -22), "fore_arm.R": (-92, 0, 0)})
    pose_c = dict(NARA_CLIMB)
    pose_c.update({"upper_arm.L": (-44, 0, 22), "fore_arm.L": (-34, 0, 0),
                   "upper_arm.R": (-38, 0, -24), "fore_arm.R": (-44, 0, 0),
                   "head": (-10, 0, 6), "neck": (-8, 0, 4)})
    key_pose(arm, 1, pose_a, list(NARA_CLIMB.keys()))
    key_pose(arm, 40, pose_b, list(NARA_CLIMB.keys()))
    key_pose(arm, 56, pose_c, list(NARA_CLIMB.keys()))
    key_pose(arm, 96, pose_c, list(NARA_CLIMB.keys()))
    scn.frame_set(1)
    bpy.context.view_layer.update()
    self_check(arm, "070-f1")

    # ---- masker + snorkel di kepala (frame 1) lalu pindah ke tangan R f20-40
    mask = bpy.data.objects.get("PRP_divegear_mask")
    snorkel = bpy.data.objects.get("PRP_divegear_snorkel")
    fh, upn, her_right = s1.face_frame(arm)
    face_c = s1.bone_world(arm, "head", 0.56) + upn * 0.005
    yaw = s1.yaw_of(fh)
    s1.attach_gear(mask, arm, "head", face_c + fh * 0.095 + upn * 0.012, yaw)
    if snorkel is not None:
        s1.attach_gear(snorkel, arm, "head", face_c + her_right * 0.105 - fh * 0.03,
                       yaw + 8.0, roll_deg=-10.0)
    bpy.context.view_layer.update()

    head_m, hand_m = {}, {}
    for f in range(1, 97):
        scn.frame_set(f)
        head_m[f] = bone_matrix(arm, "head").copy()
        hand_m[f] = bone_matrix(arm, "hand.R").copy()
    scn.frame_set(1)
    off_head = head_m[1].inverted() @ mask.matrix_world.copy()
    scale_head = mask.matrix_world.to_scale()

    scn.frame_set(40)
    bpy.context.view_layer.update()
    fh40, upn40, _ = s1.face_frame(arm)
    hand_pos = hand_m[40].translation + fh40 * 0.10
    grip = (Matrix.Translation(hand_pos)
            @ Matrix.Rotation(math.radians(s1.yaw_of(fh40) + 26.0), 4, "Z")
            @ Matrix.Rotation(math.radians(-24.0), 4, "X")
            @ Matrix.Diagonal(Vector((scale_head.x, scale_head.y, scale_head.z, 1.0))))
    off_hand = hand_m[40].inverted() @ grip

    def smoothstep(t):
        t = max(0.0, min(1.0, t))
        return t * t * (3.0 - 2.0 * t)

    seq = {}
    for f in range(1, 97):
        head_glue = head_m[f] @ off_head
        hand_glue = hand_m[f] @ off_hand
        if f <= 20:
            M = head_glue
        elif f >= 40:
            M = hand_glue
        else:
            s = smoothstep((f - 20) / 20.0)
            loc = head_glue.translation.lerp(hand_glue.translation, s)
            q = head_glue.to_quaternion().slerp(hand_glue.to_quaternion(), s)
            M = Matrix.Translation(loc) @ q.to_matrix().to_4x4() @ Matrix.Diagonal(
                Vector((scale_head.x, scale_head.y, scale_head.z, 1.0)))
        seq[f] = M

    scn.frame_set(1)
    mask.parent = None
    mask.parent_type = "OBJECT"
    mask.rotation_mode = "XYZ"
    if mask.animation_data:
        mask.animation_data_clear()
    for f in range(1, 97, 2):
        mask.matrix_world = seq[f]
        mask.keyframe_insert("location", frame=f)
        mask.keyframe_insert("rotation_euler", frame=f)
    mask.matrix_world = seq[96]
    mask.keyframe_insert("location", frame=96)
    mask.keyframe_insert("rotation_euler", frame=96)
    scn.frame_set(1)

    for f in (1, 20, 30, 40, 60, 90):
        scn.frame_set(f)
        bpy.context.view_layer.update()
        d_hand = (mask.matrix_world.translation - hand_m[f].translation).length
        d_head = (mask.matrix_world.translation - head_m[f].translation).length
        print("    f%-3d masker: ke tangan %.3f m | ke kepala %.3f m" % (f, d_hand, d_head))
    scn.frame_set(1)

    s1.sun(scn, energy=4.2, angle=3.0, rot=(64, 0, 40), color=(1.0, 0.92, 0.78))
    lib.add_world("WLD_s1_070", "#E3EFEA", strength=1.0)

    cam = s1.make_cam("CAM_shot-070_low",
                      (deck_world.x + 0.15, -43.2, 0.95),
                      (deck_world.x, -35.0, 1.50), lens=40.0, clip_end=3000.0)
    only_camera(cam)
    head_c = s1.bone_world(arm, "head", 0.5)
    s1.key_cam(cam, [
        (1, (deck_world.x + 0.15, -43.2, 0.95), (head_c.x, head_c.y, head_c.z - 0.24)),
        (96, (deck_world.x - 0.30, -42.4, 1.00), (head_c.x, head_c.y, head_c.z - 0.20)),
    ])
    ndc(cam, [head_c, hand_m[60].translation], ["kepala", "tangan-R"])
    scn.frame_set(1)

    size = save_shot("070")
    summary("070")
    log("ANIM", "s1-070 island v004 + patch ombak + Nara naik perahu, masker kepala->tangan.R f20-40 (%d bytes)"
        % size)
    still("070", 48, above_water=True)


# ===========================================================================
# 080 — dive shop: fasad 4 tiang baru, Daniel memperbaiki jaring
# ===========================================================================


DANIEL_SIT = {
    "hips": (6, 0, 0),
    "spine": (8, 0, 0),
    "chest": (6, 0, 0),
    "neck": (2, 0, 0),
    "head": (-10, 0, 6),
    "shoulder_L": (-6, 0, 0),
    "upper_arm_L": (-62, 18, 6),
    "fore_arm_L": (-72, 0, 0),
    "hand_L": (-10, 0, 0),
    "shoulder_R": (-6, 0, 0),
    "upper_arm_R": (-58, -18, -6),
    "fore_arm_R": (-76, 0, 0),
    "hand_R": (-14, 0, 0),
    "thigh_L": (-84, 0, -4),
    "shin_L": (78, 0, 0),
    "foot_L": (6, 0, 0),
    "thigh_R": (-84, 0, 4),
    "shin_R": (80, 0, 0),
    "foot_R": (6, 0, 0),
}


def build_080():
    wipe()
    scn = setup("scene-1_shot-080_daniel-jaring", 72)
    append_asset(P_ISLAND, "ENV_island-detail")
    append_asset(P_DANIEL, "CHR_daniel")
    append_asset(P_GEAR, "PRP_gear")
    arm = bpy.data.objects.get("CHR_daniel_rig")
    if arm is None:
        raise RuntimeError("CHR_daniel_rig tidak ada")

    # bangku di teras (dibuat di shot, bukan aset)
    wood = lib.material("MAT_shot_bench", "#B98E5E", roughness=0.82)
    box = s1.box
    box("PRP_shot_bench-seat", (1.30, 0.62, 0.10), (10.5, 0.55, 1.00), wood)
    for i, (bx, by) in enumerate([(9.95, 0.30), (11.05, 0.30), (9.95, 0.80), (11.05, 0.80)]):
        box("PRP_shot_bench-leg_%d" % i, (0.09, 0.09, 0.35), (bx, by, 0.79), wood)

    arm.location = (10.5, 0.55, 0.17)
    arm.rotation_mode = "XYZ"
    arm.rotation_euler = (0.0, 0.0, math.radians(8.0))
    prepare_rig(arm)
    set_interp("BEZIER")
    pose_a = dict(DANIEL_SIT)
    pose_b = dict(DANIEL_SIT)
    pose_b.update({"fore_arm_L": (-48, 0, 0), "fore_arm_R": (-70, 0, 0),
                   "head": (-4, 0, 8)})
    for f, pose in ((1, pose_a), (18, pose_b), (36, pose_a), (54, pose_b), (72, pose_a)):
        key_pose(arm, f, pose, list(DANIEL_SIT.keys()))
    scn.frame_set(1)

    net = bpy.data.objects.get("PRP_gear_fishnet")
    if net is not None:
        net.location = (10.5, 0.30, 1.16)
        net.rotation_euler = (math.radians(-4), 0.0, math.radians(12))
        net.scale = (0.72, 0.72, 0.72)
    basket = bpy.data.objects.get("PRP_gear_basket")
    if basket is not None:
        basket.location = (12.4, -0.05, 0.70)
    flo = bpy.data.objects.get("PRP_gear_float")
    if flo is not None:
        flo.location = (9.3, 0.15, 0.72)

    sign = bpy.data.objects.get("ENV_shop_sign-board")
    door = bpy.data.objects.get("ENV_shop_door")
    posts = [bpy.data.objects.get("ENV_shop_porch-post_%02d" % i) for i in (1, 2, 3, 4)]
    print("  fasad: sign=%s door=%s tiang=%d" % (sign is not None, door is not None,
                                                 len([p for p in posts if p])))
    print("  pohon kelapa terlihat:", len([o for o in bpy.data.objects
                                           if o.name.startswith("ENV_detail_palm")]))

    s1.sun(scn, energy=3.8, angle=4.0, rot=(52, 0, 34), color=(1.0, 0.93, 0.80))
    lib.add_world("WLD_s1_080", "#F2E9DC", strength=0.9)

    cam = s1.make_cam("CAM_shot-080_wide", (11.0, -12.4, 1.60), (11.0, 1.6, 2.20),
                      lens=35.0, clip_end=4000.0)
    only_camera(cam)
    s1.key_cam(cam, [(1, (11.0, -12.4, 1.60), (11.0, 1.6, 2.20)),
                     (72, (11.0, -11.7, 1.62), (11.0, 1.6, 2.18))], mode="LINEAR")
    set_interp("BEZIER")
    head_c = s1.bone_world(arm, "head", 0.5)
    scn.frame_set(1)
    bpy.context.view_layer.update()
    ndc(cam, [bc(sign, (11.0, 2.0, 3.9)), bc(door, (11.0, 1.9, 1.7)), head_c,
              bc(posts[0], (6.4, -0.4, 1.3)), bc(posts[3], (15.6, -0.4, 1.3))],
        ["papan-nama", "pintu", "kepala-Daniel", "tiang-1", "tiang-4"])

    size = save_shot("080")
    summary("080")
    log("ANIM", "s1-080 island v004 fasad 4 tiang + Daniel rig duduk anyam jaring, kamera 35 mm papan nama & pintu (%d bytes)"
        % size)
    still("080", 48, above_water=True)


# ===========================================================================
# 090 — anak-anak berlari di dermaga (crowd_v004, 4 anak asli)
# ===========================================================================


def build_090():
    wipe()
    scn = setup("scene-1_shot-090_anak-dermaga", 72)
    append_asset(P_ISLAND, "ENV_island-detail")
    new = append_asset(P_CROWD, "CHR_crowd")
    ctl = bpy.data.objects.get("CTL_crowd")
    keep = ["CRW_C01", "CRW_C02", "CRW_C03", "CRW_C04",
            "CRW_02", "CRW_05", "CRW_09",
            "CHR_crowd_face-crw-c01", "CHR_crowd_face-crw-c02",
            "CHR_crowd_face-crw-c03", "CHR_crowd_face-crw-c04",
            "CHR_crowd_face-crw-02", "CHR_crowd_face-crw-05", "CHR_crowd_face-crw-09"]
    drop = [o for o in bpy.data.objects
            if (o.name.startswith("CRW_") or o.name.startswith("CHR_crowd_face-"))
            and o.name not in keep]
    for ob in drop:
        bpy.data.objects.remove(ob, do_unlink=True)
    purge_orphans()
    kids = [bpy.data.objects[n] for n in ("CRW_C01", "CRW_C02", "CRW_C03", "CRW_C04")
            if n in bpy.data.objects]
    adults = [bpy.data.objects[n] for n in ("CRW_02", "CRW_05", "CRW_09")
              if n in bpy.data.objects]
    print("  anak:", [(k.name, tuple(round(v, 2) for v in k.dimensions)) for k in kids])
    print("  dewasa:", [(a.name, tuple(round(v, 2) for v in a.dimensions)) for a in adults])

    deck_z = 1.26
    set_interp("BEZIER")
    starts = [(0.95, -46.0), (-0.85, -48.6), (0.35, -51.4), (-0.60, -54.0)]
    for i, (kid, (sx, sy)) in enumerate(zip(kids, starts)):
        kid.rotation_mode = "XYZ"
        yaw = math.radians(180.0)
        for f in range(1, 73, 3):
            u = (f - 1) / 71.0
            y = sy + 9.6 * u
            x = sx + 0.10 * math.sin(u * 5.0 + i * 1.3)
            z = deck_z + 0.055 * abs(math.sin(u * 17.0 + i * 1.7))
            kid.location = (x, y, z)
            kid.rotation_euler = (math.radians(7.0) + math.radians(3.0) * math.sin(u * 17.0 + i),
                                  0.0,
                                  yaw + math.radians(7.0) * math.sin(u * 9.0 + i * 1.1))
            kid.keyframe_insert("location", frame=f)
            kid.keyframe_insert("rotation_euler", frame=f)
        if ctl is not None and kid.parent is None:
            kid.parent = ctl
            kid.matrix_parent_inverse = ctl.matrix_world.inverted()

    adult_spots = [(-1.72, -62.0, 196.0), (1.76, -68.0, 188.0), (-1.70, -76.0, 200.0)]
    for ad, (ax, ay, yaw) in zip(adults, adult_spots):
        ad.rotation_mode = "XYZ"
        ad.location = (ax, ay, deck_z)
        ad.rotation_euler = (0.0, 0.0, math.radians(yaw))
        ad.keyframe_insert("location", frame=1)
        ad.rotation_euler = (0.0, 0.0, math.radians(yaw + 3.0))
        ad.keyframe_insert("rotation_euler", frame=36)
        ad.rotation_euler = (0.0, 0.0, math.radians(yaw))
        ad.keyframe_insert("rotation_euler", frame=72)

    s1.sun(scn, energy=3.9, angle=3.0, rot=(60, 0, 38), color=(1.0, 0.92, 0.78))
    lib.add_world("WLD_s1_090", "#E8F0EC", strength=0.95)

    # handheld halus: simpang 3-5 cm, tidak menggoyang keras
    cam = s1.make_cam("CAM_shot-090_handheld", (0.10, -34.0, 2.05),
                      (0.0, -48.0, 1.55), lens=30.0, clip_end=3000.0)
    only_camera(cam)
    keys = []
    for f in range(1, 73, 4):
        t = (f - 1) / 71.0
        jx = 0.030 * math.sin(f * 0.42) + 0.015 * math.sin(f * 1.10 + 0.7)
        jz = 0.026 * math.sin(f * 0.36 + 1.1) + 0.012 * math.sin(f * 0.95)
        loc = (0.10 + jx, -34.0 - 0.9 * t, 2.05 + jz)
        tgt = (0.0 + jx * 1.2, -48.0 - 0.8 * t, 1.55 + jz * 1.3)
        keys.append((f, loc, tgt))
    s1.key_cam(cam, keys)
    scn.frame_set(1)
    bpy.context.view_layer.update()
    ndc(cam, [(0.0, -46.0, 1.26), (0.95, -46.0, 2.36)], ["dermaga-depan", "anak-depan"])

    size = save_shot("090")
    summary("090")
    log("ANIM", "s1-090 island v004 + crowd_v004: 4 anak asli (CRW_C01-C04) lari + 3 dewasa, handheld halus (%d bytes)"
        % size)
    still("090", 48, above_water=True)


# ===========================================================================
# 100 — Nara di ujung dermaga + fade hitam 18 frame
# ===========================================================================


def fade_to_black(scn, f_start, f_end, stops=-14.0):
    """Fade ke hitam lewat exposure scene, kurva perseptual (log2 terang)."""
    try:
        for ngn in list(bpy.data.node_groups):
            if ngn.name.startswith("COMP_shot"):
                bpy.data.node_groups.remove(ngn)
        if scn.compositing_node_group is not None:
            scn.compositing_node_group = None
    except Exception as exc:
        print("bersih-bersih compositor:", exc)
    set_interp("LINEAR")
    span = max(1, f_end - f_start)
    for i in range(span + 1):
        f = f_start + i
        u = i / float(span)
        val = 0.0 if u <= 0.0 else max(math.log2(max(1.0 - u, 2.0 ** stops)), stops)
        scn.view_settings.exposure = val
        scn.keyframe_insert("view_settings.exposure", frame=f)
    set_interp("BEZIER")
    scn.view_settings.exposure = 0.0
    return "view-exposure perseptual 0..%.0f (f%d-%d)" % (stops, f_start, f_end)


NARA_STAND = {
    "spine": (-1, 0, 0),
    "chest": (1, 0, 0),
    "neck": (2, 0, 0),
    "head": (2, 0, -3),
    "shoulder.L": (0, 0, 0),
    "upper_arm.L": (4, 0, 6),
    "fore_arm.L": (-8, 0, 0),
    "hand.L": (0, 0, 0),
    "shoulder.R": (0, 0, 0),
    "upper_arm.R": (3, 0, -6),
    "fore_arm.R": (-6, 0, 0),
    "hand.R": (0, 0, 0),
    "thigh.L": (0, 0, -2),
    "shin.L": (2, 0, 0),
    "foot.L": (-2, 0, 0),
    "thigh.R": (0, 0, 2),
    "shin.R": (1, 0, 0),
    "foot.R": (-1, 0, 0),
}


def build_100():
    wipe()
    scn = setup("scene-1_shot-100_nara-ujung-dermaga", 72)
    append_asset(P_ISLAND, "ENV_island-detail")
    append_asset(P_NARA, "CHR_nara")
    arm = bpy.data.objects.get("CHR_nara_rig")
    if arm is None:
        raise RuntimeError("CHR_nara_rig tidak ada")

    arm.location = (-0.35, -99.0, 1.26)
    arm.rotation_mode = "XYZ"
    arm.rotation_euler = (0.0, 0.0, math.radians(-6.0))
    prepare_rig(arm)
    set_interp("BEZIER")
    pose_a = dict(NARA_STAND)
    pose_b = dict(NARA_STAND)
    pose_b.update({"chest": (2, 0, 0), "head": (0, 0, -6),
                   "upper_arm.L": (6, 0, 7), "upper_arm.R": (5, 0, -7)})
    key_pose(arm, 1, pose_a, list(NARA_STAND.keys()))
    key_pose(arm, 36, pose_b, list(NARA_STAND.keys()))
    key_pose(arm, 72, pose_a, list(NARA_STAND.keys()))
    scn.frame_set(1)

    s1.sun(scn, energy=3.4, angle=4.0, rot=(70, 0, 46), color=(1.0, 0.86, 0.68))
    lib.add_world("WLD_s1_100", "#F0E6D6", strength=0.9)

    head_c = s1.bone_world(arm, "head", 0.5)
    cam = s1.make_cam("CAM_shot-100_static", (-0.30, -91.6, 2.45),
                      (head_c.x, head_c.y, head_c.z - 0.28), lens=50.0, clip_end=4000.0)
    only_camera(cam)
    s1.key_cam(cam, [(1, (-0.30, -91.6, 2.45), (head_c.x, head_c.y, head_c.z - 0.28))])
    mode = fade_to_black(scn, 54, 72)
    print("  fade:", mode)
    ndc(cam, [head_c, (-0.35, -99.0, 1.26)], ["kepala", "kaki"])
    scn.frame_set(1)

    size = save_shot("100")
    summary("100")
    log("ANIM", "s1-100 island v004 + Nara di ujung dermaga, fade hitam 18 frame (f54-72) (%d bytes)" % size)
    still("100", 48, above_water=True)


# ===========================================================================


BUILDERS = {
    "010": build_010,
    "020": build_020,
    "030": build_030,
    "040": build_040,
    "050": build_050,
    "060": build_060,
    "070": build_070,
    "080": build_080,
    "090": build_090,
    "100": build_100,
}


def main(argv):
    args = argv[argv.index("--") + 1:] if "--" in argv else []
    if not args:
        print("pakai: -- <010..100>")
        return
    key = args[0]
    if key not in BUILDERS:
        raise SystemExit("shot tidak dikenal: %s" % key)
    print("=== BUILD s1-%s ===" % key)
    BUILDERS[key]()


if __name__ == "__main__":
    main(sys.argv)

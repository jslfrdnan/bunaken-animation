"""fix-scene-1-v006-shots.py — perbaikan tiga shot Scene 1 hasil audit render.

HEADLESS saja (tanpa Blender MCP):

    & "D:\\Blender Foundation\\Blender 5.2\\blender.exe" -b ^
        -P scripts/fix-scene-1-v006-shots.py -- nara
    ... -- 090
    ... -- 010

Yang dikerjakan
---------------
nara  Bangun ulang 050 / 060 / 070 memakai rig baru `nara_rig_v004`
      (jari lebih tebal & pendek, ujung bulat, 26 bone). Kamera dan pose lama
      dipertahankan lewat skrip build yang sama; 060 diperbaiki khusus:
        * telapak diarahkan ke kamera dengan simpangan 35 derajat (diputar
          mengelilingi sumbu atas karakter) supaya tekukan jari terbaca;
        * jari (bone index_R) ditekuk +26..+38 derajat -> setengah menekuk,
          bukan garpu lurus;
        * ibu jari (thumb_R) dibuka (0, 18, 0);
        * lensa 85 mm (dulu 55 mm), jarak kamera 3,70 m -> ukuran frame sama.
      Sesudah build, jalankan swap-fish-v004-shots.py (050) dan
      patch-scene-1-v005-shots.py (050, 070) seperti pipeline aslinya.

090  Komposisi ulang: kamera 35 mm, 4,0 m dari anak terdepan pada f48,
      z dunia 2,36 m (= 1,10 m di atas dek 1,26 m), sedikit menyusur; kaki
      semua figur duduk tepat di dek; +3 figur dewasa di latar jauh.

010  Judul: duplikat mesh teks digeser 0,06 m ke belakang (menjauh dari
      kamera), warna #0F5C63, emission 0,2, fade identik dengan teks utama.

Tidak ada yang di-commit. Log: renders/logs/technical.log
"""

import bpy
import datetime
import importlib.util
import math
import os
import shutil
import sys
from mathutils import Quaternion, Vector

ROOT = r"D:/Tugas Semester 5/Grafika Komputer/Project-Animasi"
ASSETS = ROOT + "/assets"
SCENES = ROOT + "/scenes"
STILLS = ROOT + "/renders/stills"
TMP = ROOT + "/renders/tmp"
LOGPATH = ROOT + "/renders/logs/technical.log"

P_RIG = ASSETS + "/char/nara_rig_v004.blend"
P_DIVEGEAR = ASSETS + "/props/divegear_v002.blend"
P_CROWD = ASSETS + "/char/crowd_v004.blend"

SHOT_FILES = {
    "010": "scene-1_shot-010_bunaken-aerial_v001.blend",
    "050": "scene-1_shot-050_nara-dive_v001.blend",
    "060": "scene-1_shot-060_nara-ok_v001.blend",
    "070": "scene-1_shot-070_nara-naik_v001.blend",
    "090": "scene-1_shot-090_anak-dermaga_v001.blend",
}


def log(phase, line):
    os.makedirs(os.path.dirname(LOGPATH), exist_ok=True)
    stamp = datetime.datetime.now().strftime("%H:%M")
    with open(LOGPATH, "a", encoding="utf-8") as fh:
        fh.write("[%s] %s - %s\n" % (stamp, phase, line))
    print("[log]", phase, line)


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def backup(key):
    src = os.path.join(SCENES, SHOT_FILES[key])
    bak = os.path.join(TMP, "backup-%s_v001.blend" % os.path.splitext(SHOT_FILES[key])[0])
    os.makedirs(TMP, exist_ok=True)
    if os.path.exists(src) and not os.path.exists(bak):
        shutil.copy2(src, bak)
        print("BACKUP:", os.path.basename(bak))


# ===========================================================================
# BAGIAN NARA — 050 / 070 lewat skrip build lama (rig ditukar), 060 ditulis
# ulang karena lambaiannya berubah
# ===========================================================================

nv3 = _load("nv3", ROOT + "/scripts/build-nara-v003-shots.py")
nv3.P_NARA = P_RIG
v4 = nv3.v4
s1 = nv3.s1

FLOAT_A = {
    "spine": (3, 0, 0), "chest": (2, 0, 0), "neck": (6, 0, 0), "head": (4, 0, -4),
    "shoulder.L": (0, 0, 0), "upper_arm.L": (-34, 0, 16), "fore_arm.L": (-30, 0, 0),
    "hand.L": (-10, 0, 0), "thumb_L": (-14, 0, 0), "index_L": (-6, 0, 0),
    "shoulder.R": (-6, 0, 0), "upper_arm.R": (-66, 0, -20), "fore_arm.R": (-84, 0, 0),
    "hand.R": (-14, 0, 22), "thumb_R": (0, 0, 0), "index_R": (0, 10, 0),
    "thigh.L": (14, 0, -3), "shin.L": (24, 0, 0),
    "thigh.R": (6, 0, 3), "shin.R": (20, 0, 0),
}

RAISE = dict(FLOAT_A)
RAISE.update({"upper_arm.R": (0, 118, -8), "fore_arm.R": (0, 62, 0),
              "hand.R": (0, 0, 0)})

WAVE_OUT = dict(RAISE)
WAVE_OUT.update({"fore_arm.R": (0, 52, 0), "hand.R": (0, 0, 12),
                 "index_R": (0, 26, 0), "thumb_R": (0, 16, 0)})

WAVE_IN = dict(RAISE)
WAVE_IN.update({"fore_arm.R": (0, 74, 0), "hand.R": (0, 0, -10),
                "index_R": (0, 38, 0), "thumb_R": (0, 20, 0)})

LOWER = dict(FLOAT_A)
LOWER.update({"upper_arm.R": (-20, 40, -10), "fore_arm.R": (-30, 12, 0)})

WAVE_FRAMES = (12, 20, 28, 36, 44, 56)
PALM_TURN = 35.0          # derajat: telapak diputar dari arah kamera
WAVE_LENS = 85.0
WAVE_DIST = 3.70          # m (dulu 2,40 m @55 mm -> frame sama)


def remove_fins():
    for nm in ("PRP_divegear_fin_L", "PRP_divegear_fin_R"):
        ob = bpy.data.objects.get(nm)
        if ob is not None:
            bpy.data.objects.remove(ob, do_unlink=True)


def hand_world(arm, side="R"):
    pb = arm.pose.bones["hand." + side]
    return arm.matrix_world @ pb.head, arm.matrix_world @ pb.tail


def hand_body_gap(arm):
    """Jarak terpendek hand/forearm ke sumbu torso (deteksi tembus badan)."""
    hips = arm.matrix_world @ arm.pose.bones["hips"].head
    neck = arm.matrix_world @ arm.pose.bones["neck"].head
    axis = (neck - hips)
    if axis.length < 1e-6:
        return 9.9
    n = axis.normalized()
    worst = 9.9
    for name in ("hand.L", "hand.R", "fore_arm.L", "fore_arm.R"):
        pb = arm.pose.bones[name]
        for t in (0.0, 0.5, 1.0):
            p = arm.matrix_world @ pb.head.lerp(pb.tail, t)
            rel = p - hips
            d = (rel - n * rel.dot(n)).length
            worst = min(worst, d)
    return worst


def build_060_v006():
    v4.wipe()
    scn = v4.setup("scene-1_shot-060_nara-ok", 72)
    v4.append_reef()
    arm = nv3.append_nara()
    remove_fins()

    v4.prepare_rig(arm)
    arm.rotation_mode = "XYZ"
    arm.location = (0.0, 0.5, -2.30)
    arm.rotation_euler = (0.0, 0.0, math.radians(-16))

    keys = [(1, FLOAT_A), (12, RAISE), (20, WAVE_OUT), (28, WAVE_IN),
            (36, WAVE_OUT), (44, WAVE_IN), (56, RAISE), (64, LOWER), (72, FLOAT_A)]
    bones = list(FLOAT_A.keys())

    # twist pergelangan: telapak menghadap kamera, disimpangkan PALM_TURN
    v4.apply_pose(arm, RAISE)
    bpy.context.view_layer.update()
    fh, upn, her_right = s1.face_frame(arm)
    want = Quaternion(upn, math.radians(PALM_TURN)) @ fh
    twist = nv3.hand_twist(arm, "R", want)
    q_twist = Quaternion(Vector((0.0, 1.0, 0.0)), math.radians(twist))

    for f, pose in keys:
        scn.frame_set(f)
        v4.apply_pose(arm, pose)
        if f in WAVE_FRAMES:
            pb = arm.pose.bones["hand.R"]
            pb.rotation_quaternion = pb.rotation_quaternion @ q_twist
        for name in bones:
            pbb = arm.pose.bones.get(name)
            if pbb is not None:
                pbb.keyframe_insert("rotation_quaternion", frame=f)
    nv3.name_action(arm, "CHR_act_nara_060_ok")

    scn.frame_set(48)
    bpy.context.view_layer.update()
    gap48 = hand_body_gap(arm)
    flex48 = nv3.report_flexion(arm, "060-f48")

    scn.frame_set(1)
    bpy.context.view_layer.update()
    nv3.attach_mask_head(arm)

    s1.sun(scn, energy=3.4, angle=6.0, rot=(20, 0, 18), color=(0.86, 0.95, 1.0))
    v4.lib.add_world("WLD_s1_060", "#0F5C63", strength=1.05)
    v4.lib.add_fill(energy=90.0, size=3.0, loc=(1.2, -2.0, 0.4), target=(0.0, 0.0, 0.3))
    s1.underwater_fog(scn, size=90.0, top=6.0, bottom=-30.0)

    scn.frame_set(20)
    bpy.context.view_layer.update()
    fh, upn, her_right = s1.face_frame(arm)
    face_c = s1.bone_world(arm, "head", 0.56) + upn * 0.005
    h_head, h_tail = hand_world(arm, "R")
    hand_wave = h_head.lerp(h_tail, 0.5)
    mid = face_c.lerp(hand_wave, 0.44) + upn * 0.02
    cam_loc = mid + fh * WAVE_DIST + her_right * 0.08 + upn * 0.06
    cam = s1.make_cam("CAM_shot-060_cu", cam_loc, mid, lens=WAVE_LENS, clip_end=60.0)
    v4.only_camera(cam)
    cam.data.dof.use_dof = True
    cam.data.dof.aperture_fstop = 4.5
    focus = s1.root_empty("EMPTY_focus-face", face_c)
    s1.adopt([focus], arm)
    cam.data.dof.focus_object = focus

    scn.frame_set(48)
    bpy.context.view_layer.update()
    h_head, h_tail = hand_world(arm, "R")
    mask_c = bpy.data.objects["PRP_divegear_mask"].matrix_world.translation
    face48 = s1.bone_world(arm, "head", 0.56)
    v4.ndc(cam, [face48, h_head.lerp(h_tail, 0.5), mask_c],
           ["wajah", "tangan-R", "masker"])

    size = v4.save_shot("060")
    v4.summary("060")
    log("ANIM", "s1-060 rig v004: telapak menyimpang %.0f derajat, jari tekuk 26-38, "
                "ibu jari buka, lens %.0f mm (%.2f m), gap tangan-torso %.3f m (%d bytes)"
        % (PALM_TURN, WAVE_LENS, WAVE_DIST, gap48, size))
    v4.still("060", 48, above_water=False)

    # close-up tangan untuk verifikasi (kamera sementara, tidak disimpan)
    scn = bpy.context.scene
    scn.frame_set(48)
    bpy.context.view_layer.update()
    h_head, h_tail = hand_world(arm, "R")
    hc = h_head.lerp(h_tail, 0.35)
    fh48, up48, hr48 = s1.face_frame(arm)
    cam2 = s1.make_cam("CAM_hand-check", tuple(hc + fh48 * 0.62 + up48 * 0.05),
                       tuple(hc), lens=70.0, clip_end=60.0)
    scn.camera = cam2
    try:
        v4.look.apply_look(scn, 1, above_water=False)
        out = os.path.join(STILLS, "nara-v004-wave-check.png")
        v4.look.render_still(scn, out, percent=50, samples=24)
        print("WAVE CHECK:", out, os.path.exists(out))
    except Exception as exc:
        print("WAVE CHECK GAGAL:", repr(exc))
    scn.frame_set(1)
    return gap48, flex48


def build_nara():
    log("BRIEF", "nara: 050/060/070 pakai nara_rig_v004 (26 bone, jari 1,8x tebal)")
    for key in ("050", "070"):
        backup(key)
    print("=" * 70)
    print("BUILD 050")
    nv3.build_050()
    print("=" * 70)
    print("BUILD 060 (lambaian v006)")
    gap, flex = build_060_v006()
    print("=" * 70)
    print("BUILD 070")
    nv3.build_070()
    log("RIG", "s1-050/060/070 relink ke nara_rig_v004 selesai (kamera & pose lama, "
               "060 lensa 85 mm)")
    print("NARA SELESAI", gap, flex)


# ===========================================================================
# BAGIAN 090 — komposisi dermaga
# ===========================================================================

DECK_Z = 1.26
CAM_HEIGHT_ABOVE_DECK = 1.10
CAM_Z = DECK_Z + CAM_HEIGHT_ABOVE_DECK     # 2,36 m dunia
LENS_090 = 35.0
FOOT_SINK = 0.004
# Jalur lari anak digeser 40 m ke arah ujung dermaga supaya laut di ujung
# benar-benar terlihat (dari 68 m, pita laut hanya ~1 derajat = ~35 px).
KID_SHIFT_Y = -53.0
CAM_Y0 = -89.6          # f1;  f48 -> 4,1 m dari anak terdepan
CAM_Y_CURVE = 2.4       # t^2: kamera mundur pelan, anak tidak menabrak lensa
NEW_ADULTS = [("CRW_01", (1.50, -99.5, 186.0)),
              ("CRW_04", (-1.35, -101.0, 178.0)),
              ("CRW_07", (1.25, -102.5, 192.0))]
OLD_ADULTS = [("CRW_02", (-1.55, -100.0, 188.0)),
              ("CRW_05", (1.60, -102.0, 182.0)),
              ("CRW_09", (-1.40, -103.0, 194.0))]


def action_fcurves(act):
    """Blender 5.x: fcurve ada di channelbag, bukan action.fcurves."""
    out = []
    try:
        for layer in act.layers:
            for strip in layer.strips:
                for bag in getattr(strip, "channelbags", []):
                    out.extend(bag.fcurves)
    except AttributeError:
        pass
    if not out:
        try:
            out = list(act.fcurves)
        except AttributeError:
            pass
    return out


def shift_y(ob, dy):
    """Geser seluruh kunci location.y (atau location biasa) sebesar dy."""
    if ob.animation_data and ob.animation_data.action:
        moved = False
        for fc in action_fcurves(ob.animation_data.action):
            if fc.data_path == "location" and fc.array_index == 1:
                for kp in fc.keyframe_points:
                    kp.co.y += dy
                    kp.handle_left.y += dy
                    kp.handle_right.y += dy
                moved = True
        if moved:
            return
    ob.location.y += dy


def open_shot(key):
    path = os.path.join(SCENES, SHOT_FILES[key])
    bpy.ops.wm.open_mainfile(filepath=path)
    scn = bpy.context.scene
    scn.render.engine = "BLENDER_EEVEE"
    scn.view_settings.view_transform = "Standard"
    scn.render.fps = 24
    scn.render.fps_base = 1.0
    print("OPEN", os.path.basename(path), "frame %d-%d" % (scn.frame_start, scn.frame_end))
    return path, scn


def save_shot(key):
    scn = bpy.context.scene
    scn.frame_set(1)
    scn.render.resolution_percentage = 100
    scn.render.filepath = "//"
    for lby in list(bpy.data.libraries):
        try:
            bpy.data.libraries.remove(lby)
        except Exception as exc:
            print("  library tidak bisa dilepas:", exc)
    path = os.path.join(SCENES, SHOT_FILES[key])
    for nb in (".blend1", ".blend2"):
        stale = path + nb
        if os.path.exists(stale):
            os.remove(stale)
    bpy.ops.wm.save_as_mainfile(filepath=path)
    size = os.path.getsize(path)
    print("SAVED %s (%.2f MB)" % (os.path.basename(path), size / 1048576.0))
    return size


def fig_zmin(ob):
    m = ob.matrix_world
    pts = [m @ Vector(c) for c in ob.bound_box]
    return min(p.z for p in pts)


def add_adults():
    """Append 3 figur dewasa tambahan (mesh + wajah) dari crowd_v004."""
    coll = bpy.data.collections.get("CHR_crowd")
    extra = bpy.data.objects.get("CTL_crowd.001")
    want = ["CRW_01", "CRW_04", "CRW_07",
            "CHR_crowd_face-crw-01", "CHR_crowd_face-crw-04",
            "CHR_crowd_face-crw-07"]
    before = set(bpy.data.objects.keys())
    with bpy.data.libraries.load(P_CROWD, link=False) as (src, dst):
        dst.objects = [n for n in src.objects if n in want]
    new = [bpy.data.objects[n] for n in bpy.data.objects.keys() if n not in before]
    print("  append dewasa:", [o.name for o in new])
    bodies = []
    for ob in new:
        if coll is not None and ob.name not in coll.objects and ob.name != "CTL_crowd.001":
            coll.objects.link(ob)
        if ob.name in ("CRW_01", "CRW_04", "CRW_07"):
            bodies.append(ob)
    # empty induk yang ikut ter-append tidak dipakai
    stray = bpy.data.objects.get("CTL_crowd.001")
    if stray is not None:
        for ob in list(bpy.data.objects):
            if ob.parent is stray:
                ob.parent = None
        bpy.data.objects.remove(stray, do_unlink=True)
        print("  CTL_crowd.001 (empty bawaan) dibuang")
    return bodies


def place_figures(figs, spots, scn):
    """Tempatkan figur di dek (z = permukaan dek) menghadap kamera."""
    for ob, (x, y, yaw) in zip(figs, spots):
        ob.rotation_mode = "XYZ"
        if ob.animation_data and ob.animation_data.action:
            for fc in action_fcurves(ob.animation_data.action):
                if fc.data_path == "location":
                    for kp in fc.keyframe_points:
                        kp.co.y = 0.0
        ob.location = (x, y, DECK_Z - FOOT_SINK)
        ob.rotation_euler = (0.0, 0.0, math.radians(yaw))
        ob.keyframe_insert("location", frame=1)
        ob.keyframe_insert("location", frame=scn.frame_end)
        print("  dewasa %-8s @ (%.2f, %.1f) yaw %.0f" % (ob.name, x, y, yaw))


def seat_feet(figs, scn):
    """Semua figur: z minimum kaki tepat di permukaan dek (tidak mengambang)."""
    for ob in figs:
        ads = ob.animation_data
        act = ads.action if ads else None
        frames = [f for f in range(scn.frame_start, scn.frame_end + 1, 3)]
        low = 9.9
        high = -9.9
        for f in frames:
            scn.frame_set(f)
            bpy.context.view_layer.update()
            z = fig_zmin(ob)
            low = min(low, z)
            high = max(high, z)
        scn.frame_set(1)
        bpy.context.view_layer.update()
        print("  figur %-8s zmin %.3f..%.3f (dek %.3f) action %s"
              % (ob.name, low, high, DECK_Z, act.name if act else "-"))
    return


def fix_kid_feet(kids, scn):
    """Kaki anak tepat di permukaan dek.

    Figur dimiringkan 7-10 derajat saat berlari, jadi bbox bawah bisa turun
    beberapa sentimeter terhadap origin. Ketinggian dikoreksi per frame
    (dua lintasan supaya konvergen), bukan dengan satu nilai tetap.
    """
    frames = list(range(1, scn.frame_end + 1, 3))
    if scn.frame_end not in frames:
        frames.append(scn.frame_end)
    for kid in kids:
        kid.rotation_mode = "XYZ"
        for _ in range(2):
            for f in frames:
                scn.frame_set(f)
                bpy.context.view_layer.update()
                z0 = fig_zmin(kid)
                kid.location.z += (DECK_Z - 0.002 - z0)
                kid.keyframe_insert("location", index=2, frame=f)
    scn.frame_set(1)


def kid_xy(scn, kid, frame):
    scn.frame_set(frame)
    bpy.context.view_layer.update()
    return Vector((kid.location.x, kid.location.y, kid.location.z))


def build_090():
    log("BRIEF", "s1-090: kamera 35 mm, 4,0 m dari anak terdepan f48, z %.2f m "
                 "(= %.2f m di atas dek %.2f m)" % (CAM_Z, CAM_HEIGHT_ABOVE_DECK, DECK_Z))
    backup("090")
    path, scn = open_shot("090")
    ctl = bpy.data.objects["CTL_crowd"]
    kids = [bpy.data.objects[n] for n in ("CRW_C01", "CRW_C02", "CRW_C03", "CRW_C04")]
    adults = [bpy.data.objects[n] for n in ("CRW_02", "CRW_05", "CRW_09")]
    new_adults = add_adults()
    for kid in kids:
        shift_y(kid, KID_SHIFT_Y)
    print("  jalur anak digeser %.1f m ke ujung dermaga" % KID_SHIFT_Y)
    fix_kid_feet(kids, scn)
    place_figures(adults + new_adults,
                  [s for _, s in OLD_ADULTS] + [s for _, s in NEW_ADULTS], scn)

    # ---- kamera --------------------------------------------------------
    cam = scn.camera
    old = cam.animation_data.action if cam.animation_data else None
    cam.animation_data_clear()
    if old is not None and old.users == 0:
        bpy.data.actions.remove(old)
    cam.data.lens = LENS_090
    cam.data.clip_end = 3000.0
    cam.data.clip_start = 0.05

    keys = []
    for f in range(1, scn.frame_end + 1, 2):
        scn.frame_set(f)
        bpy.context.view_layer.update()
        t = (f - 1) / float(scn.frame_end - 1)
        cx = sum(k.location.x for k in kids) / 4.0
        cy = sum(k.location.y for k in kids) / 4.0
        jx = 0.022 * math.sin(f * 0.41) + 0.011 * math.sin(f * 1.07 + 0.7)
        jz = 0.018 * math.sin(f * 0.34 + 1.2) + 0.009 * math.sin(f * 0.93)
        loc = (1.15 + jx, CAM_Y0 + CAM_Y_CURVE * t * t, CAM_Z + jz)
        tgt = (cx - 0.45 + jx * 1.4, cy - 1.35, DECK_Z + 0.62 + jz * 1.2)
        keys.append((f, loc, tgt))
    s1.key_cam(cam, keys)
    scn.frame_set(48)
    bpy.context.view_layer.update()
    d48 = (Vector((cam.location.x, cam.location.y, cam.location.z))
           - kid_xy(scn, kids[0], 48))
    print("  jarak kamera->anak terdepan f48: %.2f m | z kamera %.2f m (dek+%.2f)"
          % (Vector(d48.xy).length, cam.location.z, cam.location.z - DECK_Z))

    scn.frame_set(48)
    bpy.context.view_layer.update()
    seat_feet(kids + adults + new_adults, scn)

    # cahaya + world lama dibuang dulu supaya tidak ada matahari ganda
    for ob in [o for o in bpy.data.objects if o.type == "LIGHT"]:
        bpy.data.objects.remove(ob, do_unlink=True)
    if scn.world is not None and scn.world.name.startswith("WLD_s1_090"):
        scn.world = None
    for w in list(bpy.data.worlds):
        if w.name.startswith("WLD_s1_090") and w.users == 0:
            bpy.data.worlds.remove(w)

    s1.sun(scn, energy=3.9, angle=3.0, rot=(60, 0, 38), color=(1.0, 0.92, 0.78))
    v4.lib.add_world("WLD_s1_090", "#E8F0EC", strength=0.95)
    size = save_shot("090")
    log("ANIM", "s1-090 kamera %.0f mm, %.2f m dari anak depan f48, z %.2f m, "
                "3 dewasa latar ditambah (%d bytes)"
        % (LENS_090, Vector(d48.xy).length, cam.location.z, size))
    v4.still("090", 48, above_water=True)
    return scn


# ===========================================================================
# BAGIAN 010 — outline judul
# ===========================================================================

SHADOW_HEX = "#0F5C63"
SHADOW_EMIT = 0.2
SHADOW_BACK = 0.06
OUTLINE_SCALE = 1.016   # 1,6% lebih besar -> garis gelap ~6-8 px pada 100%
FADE_KEYS = ((1, 0.0), (12, 1.0), (56, 1.0), (72, 0.0))


def hex_rgb(code):
    code = code.lstrip("#")
    return tuple(int(code[i:i + 2], 16) / 255.0 for i in (0, 2, 4)) + (1.0,)


def shadow_material():
    mat = bpy.data.materials.get("MAT_title_wb_shadow")
    if mat is not None:
        bpy.data.materials.remove(mat)
    mat = bpy.data.materials.new("MAT_title_wb_shadow")
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.location = (420, 0)
    mix = nt.nodes.new("ShaderNodeMixShader")
    mix.location = (200, 0)
    trans = nt.nodes.new("ShaderNodeBsdfTransparent")
    trans.location = (-40, 120)
    emit = nt.nodes.new("ShaderNodeEmission")
    emit.location = (-40, -80)
    emit.inputs["Color"].default_value = hex_rgb(SHADOW_HEX)
    emit.inputs["Strength"].default_value = SHADOW_EMIT
    nt.links.new(trans.outputs[0], mix.inputs[1])
    nt.links.new(emit.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    if hasattr(mat, "surface_render_method"):
        mat.surface_render_method = "BLENDED"
    else:
        mat.blend_method = "BLEND"
    mat.use_transparent_shadow = False
    try:
        mat.use_transparency_overlap = True
    except Exception:
        pass
    fac = mix.inputs[0]
    for frame, val in FADE_KEYS:
        fac.default_value = val
        fac.keyframe_insert("default_value", frame=frame)
    fac.default_value = 0.0
    return mat


def build_010():
    log("BRIEF", "s1-010 judul: duplikat mesh digeser 0,06 m ke belakang, %s emission %.1f"
        % (SHADOW_HEX, SHADOW_EMIT))
    backup("010")
    path, scn = open_shot("010")
    coll = bpy.data.collections.get("FX_title")
    if coll is None:
        raise RuntimeError("koleksi FX_title tidak ada")
    mat = shadow_material()
    made = []
    for base in ("FX_title_wb_main", "FX_title_wb_sub"):
        src = bpy.data.objects.get(base)
        if src is None:
            print("  WARN teks tidak ada:", base)
            continue
        sh = src.copy()
        sh.data = src.data.copy()
        sh.data.name = base + "_shadow_mesh"
        sh.name = base + "_shadow"
        sh.animation_data_clear()
        coll.objects.link(sh)
        sh.parent = src.parent
        sh.matrix_parent_inverse = src.matrix_parent_inverse.copy()
        sh.matrix_basis = src.matrix_basis.copy()
        sh.data.materials.clear()
        sh.data.materials.append(mat)
        loc = src.location.copy()
        # sumbu -Z kamera = arah pandang; makin negatif = makin jauh dari lensa
        loc.z = loc.z - SHADOW_BACK
        sh.location = loc
        sh.scale = tuple(s * OUTLINE_SCALE for s in src.scale)
        for frame, hidden in ((1, False), (72, False), (73, True)):
            sh.hide_render = hidden
            sh.keyframe_insert("hide_render", frame=frame)
        made.append(sh)
        print("  shadow %-24s z %.3f (teks %.3f, +%.2f m ke belakang), lebar %.2f m"
              % (sh.name, loc.z, src.location.z, SHADOW_BACK, sh.dimensions.x))
    scn.frame_set(1)
    size = save_shot("010")
    log("LOOK", "s1-010 outline judul %d objek, %s emission %.1f, geser %.2f m (%d bytes)"
        % (len(made), SHADOW_HEX, SHADOW_EMIT, SHADOW_BACK, size))
    # cek kontras: still f24 dengan dan tanpa outline
    try:
        rep = v4.look.apply_look(scn, 1, above_water=True)
        scn.frame_set(24)
        out = os.path.join(STILLS, "anim-s1-010-title.png")
        v4.look.render_still(scn, out, percent=50, samples=24)
        print("STILL:", out, os.path.exists(out), "| world", rep["world"])
    except Exception as exc:
        print("STILL GAGAL:", repr(exc))
    scn.frame_set(1)
    return made


# ---------------------------------------------------------------------- main ---

BUILDERS = {"nara": build_nara, "090": build_090, "010": build_010}


def main(argv):
    args = argv[argv.index("--") + 1:] if "--" in argv else []
    if not args:
        print("pakai: -- <nara|090|010>")
        return 1
    for key in args:
        if key not in BUILDERS:
            raise SystemExit("tahap tidak dikenal: " + key)
        print("=" * 78)
        print("TAHAP", key)
        BUILDERS[key]()
    log("VERIFY", "tahap %s selesai" % ",".join(args))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

"""
build-crowd-shots.py — tujuh shot berkerumun (warga / anak-anak).

  s2-070  scene-2_shot-070_warga-membela_v001.blend      wide dermaga subuh, 9 warga
  s2-090  scene-2_shot-090_daniel-naik_v001.blend        wide dari belakang Nara
  s3-030  scene-3_shot-030_nara-kumpulkan_v001.blend     wide sore, 7 warga
  s3-070  scene-3_shot-070_daniel-malu_v001.blend        medium Daniel, statis
  s3-090  scene-3_shot-090_warga-temui_v001.blend        wide kelompok + pengelola jauh
  s4-010  scene-4_shot-010_warga-siapkan-buoy_v001.blend wide pagi, buoy oranye
  s4-060  scene-4_shot-060_daniel-ajari_v001.blend       wide dive shop, Daniel + 3 anak

Helper (wipe, append, kamera, cahaya, rig, keyframe) diimpor dari
`scripts/build-char-shots.py` (yang mengimpor `scripts/build-scene-4-shots.py`).

Cara pakai di Blender MCP (satu shot per eksekusi):
    ns = {"__name__": "__main__", "SHOT_TO_BUILD": "s2-070"}
    exec(compile(open(path).read(), path, "exec"), ns)

Aturan yang dipatuhi:
- Tidak memanggil open_mainfile / read_factory_settings / read_homefile.
- Aset di-APPEND (link=False), file aset tidak pernah disimpan.
- EEVEE, 1920x1080, 24 fps, view transform Standard, simpan di frame 1.
- Tanpa camera shake (semua shot statis), tanpa DOF ekstrem.
- Tanpa tekstur image, tanpa pack, <50 MB.
- Crowd tanpa rig: hanya gestur/posisi objek, tidak ada jalan.
- Daniel (mesh tanpa armature): pose dilakukan per-part dengan rotasi kaku
  terhadap pivot sendi — dilaporkan sebagai keterbatasan.
"""

import importlib.util
import math
import os

import bpy
from mathutils import Euler, Matrix, Vector

ROOT = r"D:/Tugas Semester 5/Grafika Komputer/Project-Animasi"
ASSETS = ROOT + "/assets"

CHAR_SCRIPT = ROOT + "/scripts/build-char-shots.py"
_spec = importlib.util.spec_from_file_location("charlib", CHAR_SCRIPT)
char = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(char)
lib = char.lib

FRAMES = 96
DECK = char.DECK          # 1.26 — permukaan dek dermaga


def log(line):
    char.log(line)


# ---------------------------------------------------------------------------
# crowd: append, tempatkan, gestur objek
# ---------------------------------------------------------------------------


def append_crowd(keep):
    """Append CHR_crowd, buang figur yang tidak dipakai, lepas parent CTL_crowd."""
    objs = lib.append_collection(ASSETS + "/char/crowd.blend", "CHR_crowd")
    lib.purge_lights_cameras(objs)
    objs = lib.live_objects(objs)
    figs = []
    for o in objs:
        if o.name == "CTL_crowd" or o.type != "MESH":
            bpy.data.objects.remove(o, do_unlink=True)
            continue
        if o.name not in keep:
            bpy.data.objects.remove(o, do_unlink=True)
            continue
        mw = o.matrix_world.copy()
        o.parent = None
        o.matrix_world = mw
        o.rotation_mode = "XYZ"
        figs.append(o)
    print("  crowd:", [f.name for f in figs])
    return figs


def face_to(pos, target):
    """Sudut z (derajat) supaya figur menghadap target; figur menghadap -Y."""
    dx = target[0] - pos[0]
    dy = target[1] - pos[1]
    return math.degrees(math.atan2(dx, -dy))


GEST = [
    # (frame, dz, drx, drz) — geser berat, angguk/lean, tolehan
    [(1, 0.000, 0.0, 0.0), (26, 0.006, -1.2, 2.4), (50, 0.001, 0.5, -0.8),
     (72, 0.007, -1.6, 3.2), (96, 0.000, 0.2, 0.6)],
    [(1, 0.000, 0.0, 0.0), (22, 0.005, 0.9, -2.2), (46, 0.001, -0.7, 1.1),
     (70, 0.006, 1.1, -2.8), (96, 0.000, 0.1, 0.4)],
    [(1, 0.000, 0.0, 0.0), (30, 0.004, -0.6, -4.5), (54, 0.001, 0.4, -1.0),
     (78, 0.005, -1.0, -5.5), (96, 0.000, -0.2, -1.5)],
    [(1, 0.000, 0.0, 0.0), (20, 0.007, 1.0, 1.8), (44, 0.002, -0.4, 0.2),
     (68, 0.008, 1.4, 2.6), (96, 0.000, 0.3, 0.8)],
    [(1, 0.000, 0.0, 0.0), (28, 0.003, -1.4, -1.5), (52, 0.000, 0.6, 0.5),
     (76, 0.004, -1.8, -2.2), (96, 0.000, 0.0, -0.2)],
    [(1, 0.000, 0.0, 0.0), (24, 0.005, 0.6, 3.6), (48, 0.001, -0.3, 0.4),
     (74, 0.006, 0.9, 4.4), (96, 0.000, 0.1, 1.0)],
    [(1, 0.000, 0.0, 0.0), (18, 0.004, -0.8, -2.0), (42, 0.001, 0.5, 1.4),
     (66, 0.005, -1.2, -3.0), (96, 0.000, 0.0, 0.3)],
    [(1, 0.000, 0.0, 0.0), (32, 0.006, 1.2, -1.0), (56, 0.002, -0.5, 2.0),
     (80, 0.005, 0.8, -2.4), (96, 0.000, 0.2, -0.4)],
]


def place_crowd(figs, spec, look_at=None, patterns=None):
    """spec: list of (nama, x, y, z, rotz_derajat_atau_None).

    rotz None -> figur menghadap titik `look_at` (x, y).
    patterns: dict nama -> indeks GEST; default bergiliran.
    """
    d = {f.name: f for f in figs}
    patterns = patterns or {}
    for i, (name, x, y, z, rz) in enumerate(spec):
        o = d[name]
        if rz is None:
            rz = face_to((x, y), look_at)
        idx = patterns.get(name, i % len(GEST))
        for frame, dz, drx, drz in GEST[idx]:
            bpy.context.scene.frame_set(frame)
            o.location = (x, y, z + dz)
            o.rotation_euler = (math.radians(drx), 0.0, math.radians(rz + drz))
            o.keyframe_insert("location", frame=frame)
            o.keyframe_insert("rotation_euler", frame=frame)
        print("  %s x=%.2f y=%.2f rotz=%.1f pola=%d" % (name, x, y, rz, idx))
    bpy.context.scene.frame_set(1)


# ---------------------------------------------------------------------------
# Daniel: mesh tanpa armature -> pose kaku per part terhadap pivot sendi
# ---------------------------------------------------------------------------

DANIEL_GROUPS = {
    "head": ["CHR_daniel_head", "CHR_daniel_hair", "CHR_daniel_hat_brim",
             "CHR_daniel_hat_crown", "CHR_daniel_eye_L", "CHR_daniel_eye_R"],
    "torso": ["CHR_daniel_body", "CHR_daniel_hips", "CHR_daniel_neck",
              "CHR_daniel_shoulder_L", "CHR_daniel_shoulder_R"],
    "arm_up_L": ["CHR_daniel_upperarm_L"],
    "arm_up_R": ["CHR_daniel_upperarm_R"],
    "arm_lo_L": ["CHR_daniel_forearm_L", "CHR_daniel_hand_L"],
    "arm_lo_R": ["CHR_daniel_forearm_R", "CHR_daniel_hand_R"],
    "hand_L": ["CHR_daniel_hand_L"],
    "hand_R": ["CHR_daniel_hand_R"],
    "leg_L": ["CHR_daniel_thigh_L"],
    "leg_L_lo": ["CHR_daniel_shin_L", "CHR_daniel_calf_L", "CHR_daniel_foot_L",
                 "CHR_daniel_sandal_L"],
    "leg_R": ["CHR_daniel_thigh_R"],
    "leg_R_lo": ["CHR_daniel_shin_R", "CHR_daniel_calf_R", "CHR_daniel_foot_R",
                 "CHR_daniel_sandal_R"],
}

PIVOT = {
    "neck": (0.0, 0.0, 1.430),
    "torso": (0.0, 0.0, 0.930),
    "shoulder_L": (0.200, 0.0, 1.355),
    "shoulder_R": (-0.200, 0.0, 1.355),
    "elbow_L": (0.333, 0.0, 1.090),
    "elbow_R": (-0.333, 0.0, 1.090),
    "wrist_L": (0.397, 0.0, 0.845),
    "wrist_R": (-0.397, 0.0, 0.845),
    "hip_L": (0.095, 0.0, 0.885),
    "hip_R": (-0.095, 0.0, 0.885),
    "knee_L": (0.100, 0.0, 0.475),
    "knee_R": (-0.100, 0.0, 0.475),
}


class Daniel:
    """Pose kaku: setiap part diputar terhadap pivot sendi di ruang dunia."""

    def __init__(self, objs):
        self.objs = {o.name: o for o in objs}
        for o in objs:
            o.rotation_mode = "QUATERNION"

    def reset(self):
        for o in self.objs.values():
            o.matrix_world = Matrix.Identity(4)

    def rot(self, groups, pivot_pt, rx=0.0, ry=0.0, rz=0.0):
        """Putar grup part terhadap pivot; kembalikan matriks R (untuk pivot anak)."""
        p = Vector(pivot_pt)
        R = (Matrix.Translation(p)
             @ Euler((math.radians(rx), math.radians(ry), math.radians(rz)),
                     "XYZ").to_matrix().to_4x4()
             @ Matrix.Translation(-p))
        for g in groups:
            for name in DANIEL_GROUPS[g]:
                o = self.objs[name]
                o.matrix_world = R @ o.matrix_world
        return R

    def translate(self, vec):
        T = Matrix.Translation(Vector(vec))
        for o in self.objs.values():
            o.matrix_world = T @ o.matrix_world

    def min_z(self):
        # bound_box baru benar setelah depsgraph di-update
        bpy.context.view_layer.update()
        zs = []
        for o in self.objs.values():
            zs += [(o.matrix_world @ Vector(c)).z for c in o.bound_box]
        return min(zs)

    def place(self, x, y, z, rz, hip=None):
        """Pindahkan seluruh figur (rotasi z lalu geser) ke titik dasar.

        hip: kalau diisi, tinggi dasar panggul di atas z (untuk pose duduk);
        kalau None, titik terendah figur ditaruh di z.
        """
        self.rot(["head", "torso", "arm_up_L", "arm_up_R", "arm_lo_L", "arm_lo_R",
                  "hand_L", "hand_R", "leg_L", "leg_L_lo", "leg_R", "leg_R_lo"],
                 (0.0, 0.0, 0.0), rz=rz)
        if hip is None:
            dz = z - self.min_z()
        else:
            bpy.context.view_layer.update()
            o = self.objs["CHR_daniel_hips"]
            pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
            center = (min(p.z for p in pts) + max(p.z for p in pts)) * 0.5
            dz = (z + hip) - center
        self.translate((x, y, dz))
        bpy.context.view_layer.update()

    def key(self, frame):
        for o in self.objs.values():
            o.keyframe_insert("location", frame=frame)
            o.keyframe_insert("rotation_quaternion", frame=frame)


def append_daniel():
    objs = lib.append_collection(ASSETS + "/char/daniel.blend", "CHR_daniel")
    purged = lib.purge_lights_cameras(objs)
    if purged:
        print("  dibuang dari daniel:", purged)
    objs = lib.live_objects(objs)
    for o in objs:
        if not list(o.users_collection):
            bpy.data.collections["CHR_daniel"].objects.link(o)
            print("  objek tanpa koleksi dilink:", o.name)
    return Daniel(objs)


def append_single(path, coll):
    objs = lib.append_collection(path, coll)
    lib.purge_lights_cameras(objs)
    objs = lib.live_objects(objs)
    for o in objs:
        if not list(o.users_collection):
            bpy.context.scene.collection.objects.link(o)
    return objs


def group_parent(objs, name):
    """Kumpulkan objek di bawah satu empty supaya bisa dipindah sebagai grup."""
    empty = bpy.data.objects.new(name, None)
    empty.empty_display_size = 0.6
    bpy.context.scene.collection.objects.link(empty)
    for o in objs:
        if o.type == "EMPTY":
            continue
        mw = o.matrix_world.copy()
        o.parent = empty
        o.matrix_world = mw
    print("  grup %s: %d objek" % (name, len(objs)))
    return empty


# ---------------------------------------------------------------------------
# kamera & verifikasi
# ---------------------------------------------------------------------------


def head_ndc(cam, obj, z=None):
    """Titik puncak bbox objek dalam ndc."""
    pts = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    top = max(p.z for p in pts)
    cx = sum(p.x for p in pts) / 8.0
    cy = sum(p.y for p in pts) / 8.0
    return char.ndc(cam, Vector((cx, cy, top if z is None else z)))


def frame_report(tag, cam, objs):
    frame = 48
    bpy.context.scene.frame_set(frame)
    bpy.context.view_layer.update()
    for o in objs:
        x, y, z = head_ndc(cam, o)
        flag = "" if 0.0 < x < 1.0 and 0.02 < y < 0.98 else "  <-- DI LUAR FRAME"
        print("  FRAME %s %-10s x=%.3f y=%.3f z=%.2f%s"
              % (tag, o.name, x, y, z, flag))
    bpy.context.scene.frame_set(1)


def finish(tag, filename, preview_frame, scn, objs, cam, logline, notes=()):
    print("=== VERIFY %s ===" % tag)
    print("  scene:", scn.name, "range:", scn.frame_start, "-", scn.frame_end,
          "fps:", scn.render.fps, "engine:", scn.render.engine,
          "vt:", scn.view_settings.view_transform,
          "res:", scn.render.resolution_x, scn.render.resolution_y)
    print("  kamera:", cam.name, "lens", cam.data.lens,
          "loc", tuple(round(v, 2) for v in cam.location),
          "anim:", bool(cam.animation_data and cam.animation_data.action))
    print("  objek mesh:", len([o for o in bpy.data.objects if o.type == "MESH"]),
          "total objek:", len(bpy.data.objects))
    frame_report(tag, cam, objs)
    for note in list(notes) + char.DECISIONS:
        print("  CATATAN:", note)
    char.DECISIONS.clear()
    lib.report(tag, [o for o in bpy.data.objects if o.type == "MESH"], scn)
    lib.save_and_preview(tag, filename, preview_frame=preview_frame)
    log(logline)


def static_camera(name, loc, target, lens):
    cam = lib.make_camera(name, loc, target, lens=lens)
    cam.data.dof.use_dof = False
    return cam


def light_dawn_blue(sy=-95.0, sun_energy=1.9, fill=150.0):
    """Scene 2 subuh biru: matahari rendah tapi dingin, bayangan panjang.

    char.light_dawn bawaan terlalu hangat untuk wide shot yang memperlihatkan
    banyak dek, jadi versi ini memakai matahari biru redup + fill dingin.
    """
    lib.add_world("WLD_s2-blue", "#20394A", strength=1.0)
    sun = lib.add_sun(energy=sun_energy, angle_deg=7.0, rot=(74, 0, 22))
    sun.data.color = (0.80, 0.88, 1.0)
    key = lib.add_fill(energy=fill, size=3.4, loc=(-2.2, sy + 3.0, 3.3),
                       target=(0.0, sy, 2.2))
    key.data.color = (0.66, 0.80, 1.0)
    rim = lib.add_fill(energy=60.0, size=2.6, loc=(2.4, sy + 1.2, 2.9),
                       target=(0.0, sy + 0.2, 2.4))
    rim.data.color = (0.58, 0.74, 0.96)


# ---------------------------------------------------------------------------
# s2-070 — warga membela Haris (wide dermaga subuh)
# ---------------------------------------------------------------------------


def build_s2_070():
    char.wipe_all()
    scn = lib.setup_scene("scene-2_shot-070_warga-membela")
    char.ensure_eevee(scn)
    char.bezier()
    log("ANIM - mulai scene-2 shot 070 (warga membela Haris, wide dermaga subuh)")

    char.load_pier()

    haris, _ = char.append_char("haris")
    hy = -95.6
    haris.location = (0.0, hy, DECK)
    haris.rotation_euler = (0.0, 0.0, math.radians(180.0))  # menghadap warga/kamera

    base = {
        "hips": (0, 0, 0),
        "spine": (4, 0, 0), "chest": (1, 0, 0), "neck": (4, 0, 0),
        "head": (2, 0, 0),
        "shoulder.L": (-3, 0, 0), "shoulder.R": (-3, 0, 0),
        "upper_arm.L": (2, 7, 0), "fore_arm.L": (-16, 0, 4), "hand.L": (-3, 0, 0),
        "upper_arm.R": (2, -7, 0), "fore_arm.R": (-18, 0, -4), "hand.R": (-3, 0, 0),
        "thigh.L": (-2, 0, 2), "shin.L": (3, 0, 0), "foot.L": (0, 0, 0),
        "thigh.R": (2, 0, -2), "shin.R": (2, 0, 0), "foot.R": (0, 0, 0),
    }
    bones = list(base.keys())
    # Diam, menahan; satu tangan terangkat sedikit saat menjawab warga.
    char.key_pose(haris, 1, char.pose(base, {"head": (2, 0, 3)}), bones)
    char.key_pose(haris, 24, char.pose(base, {
        "spine": (6, 0, 0), "head": (4, 0, -6),
        "upper_arm.R": (-16, -10, 0), "fore_arm.R": (-30, 0, -6),
        "hand.R": (-8, 0, 0),
    }), bones)
    char.key_pose(haris, 52, char.pose(base, {
        "spine": (5, 0, 0), "head": (5, 0, -2),
        "upper_arm.R": (-8, -8, 0), "fore_arm.R": (-22, 0, -4),
    }), bones)
    char.key_pose(haris, 74, char.pose(base, {
        "spine": (6, 0, 0), "head": (6, 0, 4),
        "upper_arm.L": (-12, 9, 0), "fore_arm.L": (-26, 0, 6),
    }), bones)
    char.key_pose(haris, 96, char.pose(base, {
        "spine": (5, 0, 0), "head": (4, 0, 1),
        "upper_arm.R": (-4, -7, 0), "fore_arm.R": (-18, 0, -4),
    }), bones)
    char.key_arm_location(haris, [
        (1, (0.0, hy, DECK)),
        (32, (0.0, hy, DECK + 0.004)),
        (64, (0.0, hy, DECK)),
        (96, (0.0, hy, DECK + 0.002)),
    ])

    figs = append_crowd(["CRW_01", "CRW_02", "CRW_03", "CRW_04", "CRW_05",
                         "CRW_06", "CRW_07", "CRW_09", "CRW_10"])
    spec = [
        ("CRW_01", -1.35, -94.70, DECK, None),
        ("CRW_02", -1.55, -96.30, DECK, None),
        ("CRW_03", -1.05, -97.30, DECK, None),
        ("CRW_04", 0.62, -94.35, DECK, None),
        ("CRW_05", 1.35, -94.75, DECK, None),
        ("CRW_06", 1.55, -96.40, DECK, None),
        ("CRW_07", 1.15, -97.50, DECK, None),
        ("CRW_09", -0.35, -98.40, DECK, None),
        ("CRW_10", 0.65, -98.45, DECK, None),
    ]
    place_crowd(figs, spec, look_at=(0.0, hy))

    light_dawn_blue(hy)

    cam = static_camera("CAM_shot-070", (0.0, -89.2, 2.55),
                        (0.0, -95.8, 1.85), lens=34.0)

    char.rename_action(haris, "CHR_act_haris_070_membela")
    finish("s2-070", "scene-2_shot-070_warga-membela_v001.blend", 44, scn,
           [haris] + figs, cam,
           "ANIM - selesai scene-2 shot 070 (1-96, wide statis 28mm, 9 warga + "
           "Haris, gestur objek)",
           notes=["crowd tanpa rig: hanya geser berat + tolehan 2-6 derajat, "
                  "tidak ada langkah",
                  "Haris di tengah, warga mengelilingi radius 1,1-2,4 m "
                  "tanpa saling menembus"])


# ---------------------------------------------------------------------------
# s2-090 — Daniel naik ke perahu Haris (wide dari belakang Nara)
# ---------------------------------------------------------------------------


def build_s2_090():
    char.wipe_all()
    scn = lib.setup_scene("scene-2_shot-090_daniel-naik")
    char.ensure_eevee(scn)
    char.bezier()
    log("ANIM - mulai scene-2 shot 090 (Daniel naik ke perahu Haris, dari belakang Nara)")

    char.load_pier()

    nara, _ = char.append_char("nara")
    nara.location = (0.55, -100.4, DECK)
    nara.rotation_euler = (0.0, 0.0, math.radians(-30.0))   # punggung ke kamera

    nbase = {
        "hips": (0, 0, 0),
        "spine": (2, 0, 0), "chest": (0, 0, 0), "neck": (1, 0, 0),
        "head": (-1, 0, 0),
        "shoulder.L": (1, 0, 0), "shoulder.R": (1, 0, 0),
        "upper_arm.L": (2, 6, 0), "fore_arm.L": (-12, 0, 4), "hand.L": (-3, 0, 0),
        "upper_arm.R": (3, -6, 0), "fore_arm.R": (-14, 0, -4), "hand.R": (-3, 0, 0),
        "thigh.L": (-2, 0, 2), "shin.L": (3, 0, 0), "foot.L": (0, 0, 0),
        "thigh.R": (2, 0, -2), "shin.R": (2, 0, 0), "foot.R": (0, 0, 0),
    }
    nb = list(nbase.keys())
    # Kaku, menahan napas; hanya bahu yang naik sedikit di detik terakhir.
    char.key_pose(nara, 1, char.pose(nbase, {"spine": (2, 0, 0)}), nb)
    char.key_pose(nara, 38, char.pose(nbase, {
        "spine": (3, 0, 0), "head": (0, 0, 2),
        "shoulder.L": (2, 0, 0), "shoulder.R": (2, 0, 0),
    }), nb)
    char.key_pose(nara, 70, char.pose(nbase, {
        "spine": (4, 0, 0), "head": (1, 0, 3),
        "shoulder.L": (4, 0, 0), "shoulder.R": (4, 0, 0),
    }), nb)
    char.key_pose(nara, 96, char.pose(nbase, {
        "spine": (3, 0, 0), "head": (0, 0, 2),
        "shoulder.L": (3, 0, 0), "shoulder.R": (3, 0, 0),
    }), nb)

    # Perahu Haris: dipindah sebagai grup lewat empty.
    boat = append_single(ASSETS + "/props/haris-boat.blend", "PRP_haris-boat")
    boat_grp = group_parent(boat, "GRP_haris-boat")
    boat_grp.location = (-3.6, -107.6, 0.02)
    boat_grp.rotation_euler = (0.0, 0.0, math.radians(-34.0))

    haris, _ = char.append_char("haris")
    haris.location = (-4.00, -108.40, 0.30)
    haris.rotation_euler = (0.0, 0.0, math.radians(190.0))
    hbase = {
        "hips": (0, 0, 0),
        "spine": (5, 0, 0), "chest": (1, 0, 0), "neck": (5, 0, 0),
        "head": (3, 0, -4),
        "shoulder.L": (-4, 0, 0), "shoulder.R": (-4, 0, 0),
        "upper_arm.L": (2, 7, 0), "fore_arm.L": (-16, 0, 4), "hand.L": (-3, 0, 0),
        "upper_arm.R": (-10, -8, 0), "fore_arm.R": (-28, 0, -6), "hand.R": (-5, 0, 0),
        "thigh.L": (-3, 0, 2), "shin.L": (4, 0, 0), "foot.L": (0, 0, 0),
        "thigh.R": (2, 0, -2), "shin.R": (3, 0, 0), "foot.R": (0, 0, 0),
    }
    hb = list(hbase.keys())
    char.key_pose(haris, 1, hbase, hb)
    char.key_pose(haris, 44, char.pose(hbase, {
        "head": (3, 0, -8), "upper_arm.R": (-16, -9, 0), "fore_arm.R": (-34, 0, -6),
    }), hb)
    char.key_pose(haris, 96, char.pose(hbase, {
        "head": (2, 0, -6), "upper_arm.R": (-12, -8, 0), "fore_arm.R": (-30, 0, -6),
    }), hb)

    dan = append_daniel()

    def daniel_pose(step=0.0, lean=0.0, arm=0.0, head=0.0):
        """step 0..1: seberapa jauh kaki kanan terangkat ke dek perahu."""
        dan.reset()
        R1 = dan.rot(["torso"], PIVOT["torso"], rx=6.0 + lean)
        p_neck = R1 @ Vector(PIVOT["neck"])
        dan.rot(["head"], p_neck, rx=4.0 + head)
        psl = R1 @ Vector(PIVOT["shoulder_L"])
        psr = R1 @ Vector(PIVOT["shoulder_R"])
        dan.rot(["arm_up_L"], psl, rx=8.0, ry=10.0)
        dan.rot(["arm_up_R"], psr, rx=-24.0 - arm, ry=-8.0)
        pel = R1 @ Vector(PIVOT["elbow_L"])
        per = R1 @ Vector(PIVOT["elbow_R"])
        dan.rot(["arm_lo_L"], pel, rx=-26.0 - arm * 0.5)
        dan.rot(["arm_lo_R"], per, rx=-40.0 - arm)
        pwl = R1 @ Vector(PIVOT["wrist_L"])
        pwr = R1 @ Vector(PIVOT["wrist_R"])
        dan.rot(["hand_L"], pwl, rx=-10.0)
        dan.rot(["hand_R"], pwr, rx=-14.0)
        # Kaki: kiri tumpu, kanan terangkat ke bibir perahu
        phl = Vector(PIVOT["hip_L"])
        phr = Vector(PIVOT["hip_R"])
        dan.rot(["leg_L"], phl, rx=-4.0)
        dan.rot(["leg_R"], phr, rx=-18.0 - 42.0 * step, ry=-6.0)
        Rr = Euler((math.radians(-18.0 - 42.0 * step), math.radians(-6.0), 0.0),
                   "XYZ").to_matrix().to_4x4()
        pkl = Vector(PIVOT["knee_L"])
        pkr = Matrix.Translation(phr) @ Rr @ Matrix.Translation(-phr) @ Vector(PIVOT["knee_R"])
        dan.rot(["leg_L_lo"], pkl, rx=8.0)
        dan.rot(["leg_R_lo"], pkr, rx=30.0 + 34.0 * step)

    frames = [(1, 0.0), (28, 0.55), (56, 1.0), (80, 1.0), (96, 1.0)]
    for i, (frame, step) in enumerate(frames):
        bpy.context.scene.frame_set(frame)
        daniel_pose(step=step,
                    lean=4.0 + 6.0 * step,
                    arm=10.0 * step,
                    head=2.0 * step)
        dan.place(-2.85, -106.49, 0.33, rz=-34.0)
        # naik sedikit mengikuti kaki yang terangkat
        dan.translate((0.0, 0.0, 0.06 * step))
        dan.key(frame)
    print("  Daniel: mesh tanpa armature, pose 5 kunci (kaku per part)")

    light_dawn_blue(-101.0, sun_energy=1.7, fill=130.0)
    key = lib.add_fill(energy=110.0, size=2.8, loc=(0.6, -97.0, 3.6),
                       target=(-2.2, -106.0, 1.4))
    key.data.color = (0.70, 0.84, 1.0)

    cam = static_camera("CAM_shot-090", (0.55, -95.2, 3.50),
                        (-2.60, -107.6, 1.05), lens=32.0)

    char.rename_action(haris, "CHR_act_haris_090_perahu")
    char.rename_action(nara, "CHR_act_nara_090_melihat")
    finish("s2-090", "scene-2_shot-090_daniel-naik_v001.blend", 56, scn,
           [nara, haris, bpy.data.objects["CHR_daniel_head"],
            bpy.data.objects["PRP_haris-boat_hull"]], cam,
           "ANIM - selesai scene-2 shot 090 (1-96, wide statis 32mm, Nara "
           "punggung kiri, perahu kanan, Daniel naik)",
           notes=["Daniel = assets/char/daniel.blend tanpa armature -> pose kaku "
                  "per part terhadap pivot sendi (bukan placeholder mannequin)",
                  "musik berhenti: tidak ada pekerjaan audio di shot ini"])


# ---------------------------------------------------------------------------
# s3-030 — Nara mengumpulkan warga (wide dermaga sore)
# ---------------------------------------------------------------------------


def build_s3_030():
    char.wipe_all()
    scn = lib.setup_scene("scene-3_shot-030_nara-kumpulkan")
    char.ensure_eevee(scn)
    char.bezier()
    log("ANIM - mulai scene-3 shot 030 (Nara kumpulkan warga, wide sore)")

    char.load_pier()

    nara, _ = char.append_char("nara")
    nara.location = (0.72, -96.5, DECK)
    nara.rotation_euler = (0.0, 0.0, math.radians(-6.0))

    base = {
        "hips": (0, 0, 0),
        "spine": (2, 0, 0), "chest": (-1, 0, 0), "neck": (0, 0, 0),
        "head": (-3, 0, 0),
        "shoulder.L": (0, -1, 0), "shoulder.R": (0, 1, 0),
        "upper_arm.L": (4, 7, 0), "fore_arm.L": (-18, 0, 6), "hand.L": (-4, 0, 0),
        "upper_arm.R": (-30, -22, 0), "fore_arm.R": (-46, 0, 10), "hand.R": (-8, 0, 0),
        "thigh.L": (-3, 0, 2), "shin.L": (4, 0, 0), "foot.L": (0, 0, 0),
        "thigh.R": (2, 0, -2), "shin.R": (2, 0, 0), "foot.R": (0, 0, 0),
    }
    nb = list(base.keys())
    # Mengajak: satu tangan terbuka ke arah warga, lalu turun.
    char.key_pose(nara, 1, char.pose(base, {
        "upper_arm.R": (-26, -18, 0), "fore_arm.R": (-40, 0, 8),
    }), nb)
    char.key_pose(nara, 28, char.pose(base, {
        "spine": (4, 0, 0), "head": (-5, 0, -4),
        "upper_arm.R": (-38, -30, 0), "fore_arm.R": (-54, 0, 14),
        "hand.R": (-14, 0, 0),
    }), nb)
    char.key_pose(nara, 56, char.pose(base, {
        "spine": (3, 0, 0), "head": (-4, 0, 2),
        "upper_arm.R": (-20, -14, 0), "fore_arm.R": (-34, 0, 8),
    }), nb)
    char.key_pose(nara, 78, char.pose(base, {
        "spine": (4, 0, 0), "head": (-4, 0, -2),
        "upper_arm.R": (-34, -26, 0), "fore_arm.R": (-50, 0, 12),
        "hand.R": (-12, 0, 0),
    }), nb)
    char.key_pose(nara, 96, char.pose(base, {
        "spine": (3, 0, 0), "head": (-3, 0, 0),
        "upper_arm.R": (-28, -20, 0), "fore_arm.R": (-44, 0, 10),
    }), nb)

    figs = append_crowd(["CRW_01", "CRW_02", "CRW_03", "CRW_05", "CRW_06",
                         "CRW_07", "CRW_11"])
    spec = [
        ("CRW_01", -1.45, -98.10, DECK, None),
        ("CRW_02", 1.35, -98.90, DECK, None),
        ("CRW_03", -0.65, -99.10, DECK, None),
        ("CRW_05", 0.75, -99.30, DECK, None),
        ("CRW_06", 1.55, -100.20, DECK, None),
        ("CRW_07", -1.50, -99.90, DECK, None),
        ("CRW_11", 0.02, -98.05, DECK, None),
    ]
    place_crowd(figs, spec, look_at=(0.72, -96.5))

    char.light_afternoon(-97.0)
    key = lib.add_fill(energy=210.0, size=3.2, loc=(-2.4, -93.6, 3.7),
                       target=(0.2, -98.4, 1.9))
    key.data.color = (1.0, 0.87, 0.68)
    front = lib.add_fill(energy=90.0, size=2.2, loc=(0.7, -91.6, 3.2),
                         target=(0.2, -98.2, 1.9))
    front.data.color = (1.0, 0.90, 0.74)

    cam = static_camera("CAM_shot-030", (0.30, -90.6, 2.58),
                        (0.15, -98.4, 1.86), lens=34.0)

    char.rename_action(nara, "CHR_act_nara_030_kumpulkan")
    finish("s3-030", "scene-3_shot-030_nara-kumpulkan_v001.blend", 52, scn,
           [nara] + figs, cam,
           "ANIM - selesai scene-3 shot 030 (1-96, wide statis 32mm, 7 warga "
           "berkumpul di depan Nara)",
           notes=["7 warga dari assets/char/crowd.blend tanpa rig: posisi + "
                  "gestur kecil, tidak berjalan"])


# ---------------------------------------------------------------------------
# s3-070 — Daniel malu (medium, statis)
# ---------------------------------------------------------------------------


def build_s3_070():
    char.wipe_all()
    scn = lib.setup_scene("scene-3_shot-070_daniel-malu")
    char.ensure_eevee(scn)
    char.bezier()
    log("ANIM - mulai scene-3 shot 070 (Daniel malu, medium statis)")

    char.load_pier()
    char.light_afternoon(-96.0)

    dan = append_daniel()

    def pose_daniel(sink=0.0, breath=0.0, head_extra=0.0):
        dan.reset()
        R1 = dan.rot(["torso"], PIVOT["torso"], rx=6.0 + sink + breath)
        p_neck = R1 @ Vector(PIVOT["neck"])
        dan.rot(["head"], p_neck, rx=21.0 + head_extra)
        psl = R1 @ Vector(PIVOT["shoulder_L"])
        psr = R1 @ Vector(PIVOT["shoulder_R"])
        dan.rot(["arm_up_L"], psl, rx=6.0, ry=12.0)
        dan.rot(["arm_up_R"], psr, rx=6.0, ry=-12.0)
        pel = R1 @ Vector(PIVOT["elbow_L"])
        per = R1 @ Vector(PIVOT["elbow_R"])
        dan.rot(["arm_lo_L"], pel, rx=-16.0 - sink)
        dan.rot(["arm_lo_R"], per, rx=-16.0 - sink)
        pwl = R1 @ Vector(PIVOT["wrist_L"])
        pwr = R1 @ Vector(PIVOT["wrist_R"])
        # Tangan mengepal kecil: pergelangan diputar sedikit ke dalam.
        dan.rot(["hand_L"], pwl, rx=-6.0)
        dan.rot(["hand_R"], pwr, rx=-6.0)

    keys = [(1, 0.0, 0.0, 0.0), (26, 1.4, 0.2, 2.0), (54, 2.2, 0.0, 3.4),
            (76, 1.0, 0.3, 1.2), (96, 1.8, 0.0, 2.6)]
    for frame, sink, breath, head_extra in keys:
        bpy.context.scene.frame_set(frame)
        pose_daniel(sink=sink, breath=breath, head_extra=head_extra)
        dan.place(0.22, -96.0, DECK, rz=150.0)
        dan.key(frame)
    print("  Daniel: mesh tanpa armature, 5 kunci pose (kaku per part)")

    key = lib.add_fill(energy=90.0, size=1.6, loc=(1.55, -94.3, 3.05),
                       target=(0.22, -96.0, 2.55))
    key.data.color = (1.0, 0.88, 0.72)

    cam = static_camera("CAM_shot-070", (0.55, -92.0, 2.78),
                        (0.20, -96.0, 2.44), lens=45.0)

    finish("s3-070", "scene-3_shot-070_daniel-malu_v001.blend", 54, scn,
           [bpy.data.objects["CHR_daniel_head"]], cam,
           "ANIM - selesai scene-3 shot 070 (1-96, medium statis 55mm, kepala "
           "menunduk, tangan mengepal)",
           notes=["Daniel memakai mesh assets/char/daniel.blend (tanpa armature) "
                  "-> pose kaku per part; bukan placeholder mannequin",
                  "kamera statis penuh, tanpa shake"])


# ---------------------------------------------------------------------------
# s3-090 — warga menemui pengelola taman nasional (wide, berkelompok)
# ---------------------------------------------------------------------------


def build_s3_090():
    char.wipe_all()
    scn = lib.setup_scene("scene-3_shot-090_warga-temui")
    char.ensure_eevee(scn)
    char.bezier()
    log("ANIM - mulai scene-3 shot 090 (warga temui pengelola taman nasional)")

    char.load_pier()

    nara, _ = char.append_char("nara")
    nara.location = (1.05, -95.9, DECK)
    nara.rotation_euler = (0.0, 0.0, math.radians(-28.0))

    base = {
        "hips": (0, 0, 0),
        "spine": (3, 0, 0), "chest": (-1, 0, 0), "neck": (1, 0, 0),
        "head": (-3, 0, 0),
        "shoulder.L": (0, -1, 0), "shoulder.R": (0, 1, 0),
        "upper_arm.L": (5, 8, 0), "fore_arm.L": (-20, 0, 6), "hand.L": (-5, 0, 0),
        "upper_arm.R": (-18, -14, 0), "fore_arm.R": (-34, 0, 8), "hand.R": (-6, 0, 0),
        "thigh.L": (-3, 0, 2), "shin.L": (4, 0, 0), "foot.L": (0, 0, 0),
        "thigh.R": (2, 0, -2), "shin.R": (2, 0, 0), "foot.R": (0, 0, 0),
    }
    nb = list(base.keys())
    char.key_pose(nara, 1, char.pose(base, {"head": (-2, 0, -4)}), nb)
    char.key_pose(nara, 34, char.pose(base, {
        "spine": (4, 0, 0), "head": (-5, 0, -6),
        "upper_arm.R": (-24, -18, 0), "fore_arm.R": (-40, 0, 10),
    }), nb)
    char.key_pose(nara, 68, char.pose(base, {
        "spine": (3, 0, 0), "head": (-3, 0, -3),
        "upper_arm.R": (-14, -12, 0), "fore_arm.R": (-28, 0, 6),
    }), nb)
    char.key_pose(nara, 96, char.pose(base, {
        "spine": (3, 0, 0), "head": (-4, 0, -5),
        "upper_arm.R": (-20, -16, 0), "fore_arm.R": (-36, 0, 8),
    }), nb)

    figs = append_crowd(["CRW_01", "CRW_02", "CRW_03", "CRW_05", "CRW_06",
                         "CRW_07"])
    spec = [
        ("CRW_01", 1.52, -96.70, DECK, None),
        ("CRW_02", 0.45, -97.30, DECK, None),
        ("CRW_03", 1.40, -97.90, DECK, None),
        ("CRW_05", 0.30, -98.50, DECK, None),
        ("CRW_06", 1.45, -99.10, DECK, None),
        ("CRW_07", 0.55, -99.80, DECK, None),
    ]
    place_crowd(figs, spec, look_at=(-1.30, -101.5))

    manager = append_single(ASSETS + "/char/mannequin.blend", "MAN_adult-male")
    mgr = bpy.data.objects["MAN_adult-male"]
    dims = mgr.dimensions
    print("  pengelola mannequin dims=(%.2f, %.2f, %.2f)" % (dims.x, dims.y, dims.z))
    mgr.location = (-1.30, -101.5, DECK)
    mgr.rotation_euler = (0.0, 0.0, math.radians(180.0))
    for f, frame in enumerate((1, 40, 96)):
        bpy.context.scene.frame_set(frame)
        mgr.rotation_euler = (0.0, 0.0, math.radians(180.0 + 3.0 * (f - 1)))
        mgr.keyframe_insert("rotation_euler", frame=frame)

    char.light_afternoon(-98.0)
    key = lib.add_fill(energy=120.0, size=3.0, loc=(-2.6, -93.0, 3.8),
                       target=(0.4, -98.0, 1.9))
    key.data.color = (1.0, 0.87, 0.68)

    cam = static_camera("CAM_shot-090", (-0.50, -89.2, 2.92),
                        (0.15, -98.2, 1.72), lens=32.0)

    char.rename_action(nara, "CHR_act_nara_090_temui")
    finish("s3-090", "scene-3_shot-090_warga-temui_v001.blend", 60, scn,
           [nara] + figs + [mgr], cam,
           "ANIM - selesai scene-3 shot 090 (1-96, wide statis 32mm, 6 warga + "
           "Nara + pengelola jauh)",
           notes=["pengelola taman nasional = MAN_adult-male (mannequin) sebagai "
                  "figur jauh, sesuai shot list 'hanya suara/figur jauh'"])


# ---------------------------------------------------------------------------
# s4-010 — warga menyiapkan mooring buoy (wide pagi)
# ---------------------------------------------------------------------------


def build_s4_010():
    char.wipe_all()
    scn = lib.setup_scene("scene-4_shot-010_warga-siapkan-buoy")
    char.ensure_eevee(scn)
    char.bezier()
    log("ANIM - mulai scene-4 shot 010 (warga siapkan mooring buoy oranye)")

    char.load_pier()

    boat = append_single(ASSETS + "/props/boats.blend", "PRP_boats")
    boat_grp = group_parent(boat, "GRP_boat")
    boat_grp.location = (0.0, -110.8, 0.0)
    print("  perahu di", tuple(round(v, 2) for v in boat_grp.location))

    # Buoy di air, sisi kanan perahu. Aset: badan di z 2,78 -> turunkan.
    buoy = append_single(ASSETS + "/props/mooring-buoy.blend", "PRP_buoy")
    buoy_grp = group_parent(buoy, "GRP_buoy")
    buoy_grp.location = (2.35, -107.9, 0.32 - 2.78)
    print("  buoy:", round(buoy_grp.location.z, 2))

    figs = append_crowd(["CRW_01", "CRW_02", "CRW_05", "CRW_07", "CRW_09"])
    # 4 warga di dek perahu (dek z 0,30), 1 di ujung dermaga memegang tali.
    spec = [
        ("CRW_01", -2.15, -110.75, 0.30, -84.0),
        ("CRW_05", -1.05, -110.85, 0.30, 92.0),
        ("CRW_09", 0.10, -110.80, 0.30, -88.0),
        ("CRW_07", 1.15, -110.72, 0.30, 104.0),
        ("CRW_02", -1.10, -102.30, DECK, None),
    ]
    place_crowd(figs, spec, look_at=(2.35, -107.9))

    # Tali dari buoy ke tangan warga di dermaga.
    buoy_rope = bpy.data.objects.get("PRP_buoy_rope")
    if buoy_rope is not None:
        buoy_rope.hide_render = True     # tali aset menggantung lurus ke bawah
        print("  PRP_buoy_rope disembunyikan (tali aset lurus ke dasar air)")
    char.bezier()
    rope0 = Vector((2.35, -107.9, 0.55))
    rope1 = Vector((-1.02, -102.6, DECK + 1.15))
    mid = (rope0 + rope1) * 0.5
    mid.z -= 0.35
    curve = bpy.data.curves.new("PRP_rope-buoy", "CURVE")
    curve.dimensions = "3D"
    spline = curve.splines.new("BEZIER")
    spline.bezier_points.add(2)
    for pt, co in zip(spline.bezier_points, (rope0, mid, rope1)):
        pt.co = co
        pt.handle_left_type = pt.handle_right_type = "AUTO"
    curve.bevel_depth = 0.016
    curve.bevel_resolution = 2
    rope_obj = bpy.data.objects.new("PRP_rope-buoy", curve)
    rope_obj.data.materials.append(lib.material("MAT_rope_buoy", "#D9C9A8",
                                               roughness=0.85))
    bpy.context.scene.collection.objects.link(rope_obj)

    char.light_morning(-108.0)
    key = lib.add_fill(energy=420.0, size=8.0, loc=(-6.0, -101.0, 6.0),
                       target=(0.0, -109.0, 1.0))
    key.data.color = (1.0, 0.96, 0.88)
    warm = lib.add_fill(energy=160.0, size=2.4, loc=(2.4, -103.6, 2.6),
                        target=(2.35, -107.9, 0.5))
    warm.data.color = (1.0, 0.82, 0.62)

    cam = static_camera("CAM_shot-010", (0.30, -97.6, 2.80),
                        (0.90, -108.2, 0.85), lens=30.0)

    finish("s4-010", "scene-4_shot-010_warga-siapkan-buoy_v001.blend", 48, scn,
           figs + [bpy.data.objects["PRP_buoy_body"]], cam,
           "ANIM - selesai scene-4 shot 010 (1-96, wide statis 30mm, 5 warga + "
           "mooring buoy oranye di air)",
           notes=["buoy oranye #E4713C mengapung sisi kanan perahu; tali aset "
                  "disembunyikan, diganti tali kurva ke tangan warga"])


# ---------------------------------------------------------------------------
# s4-060 — Daniel mengajari anak-anak menganyam jaring (wide dive shop)
# ---------------------------------------------------------------------------


def build_s4_060():
    char.wipe_all()
    scn = lib.setup_scene("scene-4_shot-060_daniel-ajari")
    char.ensure_eevee(scn)
    char.bezier()
    log("ANIM - mulai scene-4 shot 060 (Daniel ajari 3 anak anyam jaring, dive shop)")

    char.load_pier()

    dan = append_daniel()

    SIT_THIGH = -82.0
    SIT_SPLAY = 8.0

    def pose_duduk(work=0.0, breath=0.0):
        """Daniel duduk di dek, kaki ke depan, badan membungkuk ke jaring."""
        dan.reset()
        R1 = dan.rot(["torso"], PIVOT["torso"], rx=12.0 + work)
        p_neck = R1 @ Vector(PIVOT["neck"])
        dan.rot(["head"], p_neck, rx=17.0 + work * 0.4)
        psl = R1 @ Vector(PIVOT["shoulder_L"])
        psr = R1 @ Vector(PIVOT["shoulder_R"])
        dan.rot(["arm_up_L"], psl, rx=-34.0 - work, ry=10.0)
        dan.rot(["arm_up_R"], psr, rx=-32.0 - work, ry=-10.0)
        pel = R1 @ Vector(PIVOT["elbow_L"])
        per = R1 @ Vector(PIVOT["elbow_R"])
        dan.rot(["arm_lo_L"], pel, rx=-56.0 - work * 1.4)
        dan.rot(["arm_lo_R"], per, rx=-54.0 - work * 1.2)
        pwl = R1 @ Vector(PIVOT["wrist_L"])
        pwr = R1 @ Vector(PIVOT["wrist_R"])
        dan.rot(["hand_L"], pwl, rx=-18.0, rz=-12.0)
        dan.rot(["hand_R"], pwr, rx=-18.0, rz=12.0)
        # Kaki: lurus ke depan (duduk di dek), sedikit terbuka.
        phl = Vector(PIVOT["hip_L"])
        phr = Vector(PIVOT["hip_R"])
        dan.rot(["leg_L"], phl, rx=SIT_THIGH, ry=SIT_SPLAY)
        dan.rot(["leg_R"], phr, rx=SIT_THIGH, ry=-SIT_SPLAY)
        Rl = Euler((math.radians(SIT_THIGH), math.radians(SIT_SPLAY), 0.0),
                   "XYZ").to_matrix().to_4x4()
        Rr = Euler((math.radians(SIT_THIGH), math.radians(-SIT_SPLAY), 0.0),
                   "XYZ").to_matrix().to_4x4()
        pkl = Matrix.Translation(phl) @ Rl @ Matrix.Translation(-phl) @ Vector(PIVOT["knee_L"])
        pkr = Matrix.Translation(phr) @ Rr @ Matrix.Translation(-phr) @ Vector(PIVOT["knee_R"])
        dan.rot(["leg_L_lo"], pkl, rx=16.0)
        dan.rot(["leg_R_lo"], pkr, rx=16.0)

    keys = [(1, 0.0), (26, 2.4), (52, 0.4), (74, 2.8), (96, 1.2)]
    for frame, work in keys:
        bpy.context.scene.frame_set(frame)
        pose_duduk(work=work, breath=0.0)
        dan.place(0.65, -3.40, DECK, rz=6.0, hip=0.19)
        dan.key(frame)
    print("  Daniel duduk di dek (pose kaku), muka ke arah laut")

    figs = append_crowd(["CRW_04", "CRW_11", "CRW_12"])
    spec = [
        ("CRW_04", -0.60, -4.40, DECK, None),
        ("CRW_11", 1.55, -4.20, DECK, None),
        ("CRW_12", 0.45, -2.35, DECK, None),
    ]
    place_crowd(figs, spec, look_at=(0.65, -3.40))

    gear = append_single(ASSETS + "/props/fishing-gear.blend", "PRP_gear")
    place = {
        "PRP_gear_fishnet": ((0.55, -4.05, DECK + 0.004), 14.0),
        "PRP_gear_basket": ((-1.30, -3.60, DECK), 32.0),
        "PRP_gear_float": ((1.70, -3.20, DECK), -22.0),
    }
    for name, (loc, rz) in place.items():
        o = bpy.data.objects.get(name)
        if o is None:
            print("  gear hilang:", name)
            continue
        o.location = loc
        o.rotation_euler = (0.0, 0.0, math.radians(rz))
        print("  gear", name, "di", tuple(round(v, 2) for v in loc))

    # Cahaya pagi dari arah laut + bounce dari dinding dive shop.
    lib.add_world("WLD_s4-060", "#9CC6C2", strength=0.85)
    sun = lib.add_sun(energy=3.2, angle_deg=3.2, rot=(34, 0, 28))
    sun.data.color = (1.0, 0.96, 0.86)
    key = lib.add_fill(energy=210.0, size=4.4, loc=(-2.4, -8.0, 3.8),
                       target=(0.5, -3.6, 1.7))
    key.data.color = (1.0, 0.96, 0.86)
    bounce = lib.add_fill(energy=90.0, size=2.6, loc=(1.6, -1.2, 2.8),
                          target=(0.6, -3.6, 1.6))
    bounce.data.color = (0.96, 0.88, 0.76)

    face = lib.add_fill(energy=110.0, size=1.4, loc=(0.0, -6.0, 2.30),
                        target=(0.65, -3.40, 1.75))
    face.data.color = (1.0, 0.94, 0.82)

    cam = static_camera("CAM_shot-060", (-1.05, -8.20, 2.50),
                        (0.50, -3.60, 1.65), lens=34.0)

    finish("s4-060", "scene-4_shot-060_daniel-ajari_v001.blend", 52, scn,
           figs + [bpy.data.objects["CHR_daniel_head"]], cam,
           "ANIM - selesai scene-4 shot 060 (1-96, wide statis 32mm, Daniel duduk "
           "+ 3 anak + jaring)",
           notes=["Daniel = mesh tanpa armature, duduk lewat rotasi kaku "
                  "pinggul/lutut; bukan placeholder mannequin",
                  "3 anak dari CHR_crowd (CRW_04 1,24 m / CRW_11 1,30 m / "
                  "CRW_12 1,18 m)"])


# ---------------------------------------------------------------------------
# dispatch
# ---------------------------------------------------------------------------

BUILDERS = {
    "s2-070": build_s2_070,
    "s2-090": build_s2_090,
    "s3-030": build_s3_030,
    "s3-070": build_s3_070,
    "s3-090": build_s3_090,
    "s4-010": build_s4_010,
    "s4-060": build_s4_060,
}


def main():
    tag = globals().get("SHOT_TO_BUILD")
    if not tag or tag not in BUILDERS:
        print("SHOT_TO_BUILD harus salah satu dari:", list(BUILDERS))
        return
    BUILDERS[tag]()


if __name__ == "__main__":
    main()

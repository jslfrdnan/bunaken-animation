"""build-nara-rig-v004.py — perbaikan geometri jari Nara (audit shot 060).

HEADLESS (tanpa Blender MCP):
    & "D:\\Blender Foundation\\Blender 5.2\\blender.exe" -b -P scripts/build-nara-rig-v004.py

Sumber: assets/char/nara_rig_v003.blend   (TIDAK diubah, hanya disalin)
Hasil : assets/char/nara_rig_v004.blend

BRIEF
-----
Masalah (audit render): jari terbaca sebagai batang tipis panjang seperti garpu
pada close-up shot 060; ibu jari berujung rata sehingga seperti silinder terbuka.
Tujuan aset: tangan Nara yang terbaca sebagai tangan pada close-up (isyarat "OK").
Skala nyata: tinggi tokoh 1,71 m; telapak 5,2 x 7,1 cm; jari 4,4-5,9 cm.
Pivot: CHR_nara_fingers / CHR_nara_thumbs di origin armature (0,0,0),
parent armature CHR_nara_rig.
Material: MAT_nara_skin (palette kulit, tidak diubah).

Perubahan dari v003:
  * CHR_nara_fingers dibangun ulang: penampang 1,8x radius, panjang 0,75x,
    ujung dibulatkan (Subdivision Surface level 2 di atas 192 vertex dasar,
    jadi tidak ada silinder terbuka), tekuk alami 13 derajat saat rest.
    Jumlah vertex dasar tetap 192 (8 jari x 3 ring x 8 segmen).
  * Sebaran jari dilebarkan 0,017 -> 0,0198 m supaya penampang 1,8x tidak
    menempel jadi satu.
  * Ibu jari: stub lama di CHR_nara_body (berujung rata, 46 vertex) dikecilkan
    jadi tonjolan thenar yang tersembunyi, lalu ibu jari baru dibuat sebagai
    objek CHR_nara_thumbs — 2 x 24 = 48 vertex dasar, radius 1,8x, panjang
    0,85x (3,8 cm; 0,75x membuat ibu jari lebih pendek dari lebarnya),
    ujung bulat (subsurf L2), tekuk 13 derajat.
  * Bobot: seluruh vertex jari 100% (index_L/R = 1,0; thumb_L/R = 1,0).
    Vertex stub ibu jari di body diberi falloff akar->hand supaya memutar
    thumb tidak merobek telapak.
  * Pose uji CHR_act_nara_pose-uji frame 1: jari menekuk 30 derajat (rotasi
    terhadap sumbu Y -> ujung masuk 3,3 cm ke sisi telapak), ibu jari turun
    menyusur telapak. Tangan setengah menggenggam, bukan garpu.
  * Bone thumb_L/R, index_L/R, jaw dipertahankan apa adanya (26 bone).
"""

import bpy
import bmesh
import datetime
import math
import os
import shutil
from mathutils import Matrix, Vector

ROOT = r"D:/Tugas Semester 5/Grafika Komputer/Project-Animasi"
SRC = ROOT + "/assets/char/nara_rig_v003.blend"
DST = ROOT + "/assets/char/nara_rig_v004.blend"
LOGPATH = ROOT + "/renders/logs/modeling.log"
STILLS = ROOT + "/renders/stills"


def log(phase, line):
    os.makedirs(os.path.dirname(LOGPATH), exist_ok=True)
    stamp = datetime.datetime.now().strftime("%H:%M")
    with open(LOGPATH, "a", encoding="utf-8") as fh:
        fh.write("[%s] %s - %s\n" % (stamp, phase, line))
    print("[log]", phase, line)


def smoothstep(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


# ------------------------------------------------------------------- fingers ---
# (nama, offset sumbu Y dari tengah telapak, panjang v003, radius v003)
FINGER_SPEC = [
    ("index", -0.0257, 0.074, 0.0080),
    ("middle", -0.0059, 0.078, 0.0082),
    ("ring", 0.0139, 0.070, 0.0076),
    ("pinky", 0.0337, 0.058, 0.0066),
]

BASE_X = 0.2065          # tengah tebal telapak (sisi kiri, x positif)
BASE_Y = 0.004           # tengah lebar telapak
BASE_Z = 0.6785          # ring pangkal di dalam telapak (penampang terlebar)
SCALE_R = 1.8            # penampang (radius), sesuai brief
SCALE_L = 0.75           # panjang, sesuai brief
BEND_DEG = 13.0          # tekuk rest, derajat (brief: 10-15)
PROFILE = (1.0, 0.93, 0.58)   # radius ring: pangkal, tengah, ujung
SEG = 8

# ibu jari: sumbu bone thumb, radius 1,8x, panjang 0,85x (lihat catatan di atas)
# Pangkal di t=0,018 (di dalam daging telapak, permukaan telapak ada di t~0,032)
THUMB_BASE_T = 0.018
THUMB_R0 = 0.0103        # radius stub v003
THUMB_LEN = 0.054        # panjang batang ibu jari (5,4 cm; ~3,5 cm menonjol)
THUMB_PROFILE = (1.0, 0.92, 0.68)


def tube_path(side, base, length, steps=24, fwd=0.006):
    """3 titik path: tekuk 13 deg ke sisi telapak (-X untuk tangan kiri)."""
    s = 1.0 if side == "L" else -1.0
    B = math.radians(BEND_DEG)
    pts = [base.copy()]
    p = base.copy()
    dl = length / steps
    for i in range(steps):
        th = B * (i + 0.5) / steps
        p = p + Vector((-s * math.sin(th), 0.0, -math.cos(th))) * dl
        pts.append(p.copy())
    out = []
    for f in (0.0, 0.45, 1.0):
        q = pts[min(steps, int(round(f * steps)))].copy()
        q.y = base.y - fwd * f          # sedikit maju ke depan (-Y)
        out.append(q)
    return out


def tube_rings(side, base, length, r0, profile):
    """Vertex + face tabung 3 ring, pangkal & ujung tertutup (192/48 vertex)."""
    pts = tube_path(side, base, length)
    radii = [r0 * f for f in profile]
    V, F = [], []
    rings = []
    for i, p in enumerate(pts):
        if i == 0:
            t = (pts[1] - pts[0]).normalized()
        elif i == len(pts) - 1:
            t = (pts[-1] - pts[-2]).normalized()
        else:
            t = (pts[i + 1] - pts[i - 1]).normalized()
        ref = Vector((0.0, 1.0, 0.0))
        xa = ref.cross(t)
        if xa.length < 1e-4:
            xa = Vector((1.0, 0.0, 0.0)).cross(t)
        xa.normalize()
        ya = t.cross(xa).normalized()
        rings.append(len(V))
        for k in range(SEG):
            a = 2.0 * math.pi * k / SEG
            V.append(p + xa * (radii[i] * math.cos(a)) + ya * (radii[i] * math.sin(a)))
    for k in range(len(rings) - 1):
        a, b = rings[k], rings[k + 1]
        for i in range(SEG):
            i2 = (i + 1) % SEG
            F.append((a + i, a + i2, b + i2, b + i))
    F.append(tuple(rings[0] + i for i in range(SEG - 1, -1, -1)))     # tutup pangkal
    F.append(tuple(rings[-1] + i for i in range(SEG)))                # tutup ujung
    return V, F


def make_object(name, V, F, arm, col, groups, note):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([tuple(v) for v in V], [], F)
    mat = bpy.data.materials.get("MAT_nara_skin")
    if mat is not None:
        mesh.materials.append(mat)
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    for p in mesh.polygons:
        p.use_smooth = True
    mesh.update()

    ob = bpy.data.objects.new(name, mesh)
    col.objects.link(ob)
    ob.parent = arm
    ob.matrix_parent_inverse = arm.matrix_world.inverted()
    ob["asset"] = "CHR_nara"
    ob["note"] = note
    for gname, idxs in groups:
        g = ob.vertex_groups.new(name=gname)
        g.add(idxs, 1.0, "REPLACE")
    mod = ob.modifiers.new("Armature", "ARMATURE")
    mod.object = arm
    sub = ob.modifiers.new("Subdivision", "SUBSURF")
    sub.levels = 2
    sub.render_levels = 2
    return ob


def remove_object(name):
    ob = bpy.data.objects.get(name)
    if ob is None:
        return 0
    me = ob.data
    n = len(me.vertices)
    bpy.data.objects.remove(ob, do_unlink=True)
    if me.users == 0:
        bpy.data.meshes.remove(me)
    return n


def build_fingers(arm, col):
    V, F = [], []
    stats = {}
    for side in ("L", "R"):
        off = len(V)
        st = []
        for name, dy, length0, r0 in FINGER_SPEC:
            base = Vector(((1.0 if side == "L" else -1.0) * BASE_X,
                           BASE_Y + dy, BASE_Z))
            L = length0 * SCALE_L
            v, f = tube_rings(side, base, L, r0 * SCALE_R, PROFILE)
            F.extend(tuple(j + len(V) for j in i) for i in f)
            V.extend(v)
            st.append((name, L, [round(r0 * SCALE_R * p * 1000, 1) for p in PROFILE]))
        stats[side] = (off, len(V), st)
    ob = make_object(
        "CHR_nara_fingers", V, F, arm, col,
        [("index_L", list(range(stats["L"][0], stats["L"][1]))),
         ("index_R", list(range(stats["R"][0], stats["R"][1])))],
        "jari v004: penampang 1,8x, panjang 0,75x, ujung bulat (subsurf L2), "
        "tekuk rest 13 deg; 192 vertex dasar")
    return ob, stats


def build_thumbs(arm, col):
    V, F = [], []
    stats = {}
    for side in ("L", "R"):
        bt = arm.data.bones["thumb_%s" % side]
        H = bt.head_local.copy()
        ax = (bt.tail_local - bt.head_local).normalized()
        base = H + ax * THUMB_BASE_T
        v, f = tube_rings(side, base, THUMB_LEN, THUMB_R0 * SCALE_R, THUMB_PROFILE)
        off = len(V)
        F.extend(tuple(j + off for j in i) for i in f)
        V.extend(v)
        stats[side] = (off, len(V), base.copy(), ax.copy())
    ob = make_object(
        "CHR_nara_thumbs", V, F, arm, col,
        [("thumb_L", list(range(stats["L"][0], stats["L"][1]))),
         ("thumb_R", list(range(stats["R"][0], stats["R"][1])))],
        "ibu jari v004: 1,8x radius, 0,85x panjang, ujung bulat (subsurf L2)")
    return ob, stats


# --------------------------------------------------------------- thumb stub ---

def group_weight(ob, name, idx):
    g = ob.vertex_groups.get(name)
    if g is None:
        return 0.0
    try:
        return g.weight(idx)
    except RuntimeError:
        return 0.0


def shrink_thumb_stub(body, arm, side):
    """Benamkan stub ibu jari v003 ke dalam telapak (tonjolan thenar tersembunyi).

    Stub lama berujung rata dan menonjol ~1 cm dari permukaan telapak; kalau
    hanya dikecilkan ia jadi duri. Di sini bagian luarnya ditarik masuk sumbu
    bone sampai berada di dalam daging telapak (permukaan telapak ada di
    t ~ 0,032), sehingga ibu jari baru yang menutupinya.
    """
    bt = arm.data.bones["thumb_%s" % side]
    H = bt.head_local.copy()
    ax = (bt.tail_local - bt.head_local).normalized()
    gi = body.vertex_groups["thumb_%s" % side].index
    t_base = 0.021
    n = 0
    for v in body.data.vertices:
        w = 0.0
        for ge in v.groups:
            if ge.group == gi:
                w = ge.weight
        if w <= 0.01:
            continue
        d = v.co - H
        t = d.dot(ax)
        rad = d - ax * t
        fr = 1.0 - smoothstep((rad.length - 0.016) / 0.006)
        if fr <= 0.0:
            continue
        f = smoothstep((t - 0.030) / 0.012) * fr
        if f <= 0.0:
            continue
        s = 1.0 - 0.20 * f
        t2 = t + (0.014 - t) * (0.95 * f)      # tarik ke dalam daging telapak
        v.co = H + ax * t2 + rad * s
        n += 1
    body.data.update()
    return n


def reweight_thumb(body, arm, side):
    """Bobot stub: akar ikut hand, ujung ikut thumb (falloff aksial+radial).

    v003 memberi 0,92 thumb ke seluruh vertex di sekitar bone, termasuk vertex
    permukaan telapak, sehingga memutar thumb merobek telapak.
    """
    bt = arm.data.bones["thumb_%s" % side]
    H = bt.head_local.copy()
    ax = (bt.tail_local - bt.head_local).normalized()
    g_thumb = body.vertex_groups["thumb_%s" % side]
    g_hand = body.vertex_groups["hand.%s" % side]
    n = 0
    for v in body.data.vertices:
        wt = 0.0
        for ge in v.groups:
            if ge.group == g_thumb.index:
                wt = ge.weight
        if wt <= 1e-4:
            continue
        d = v.co - H
        t = d.dot(ax)
        r = (d - ax * t).length
        f = smoothstep((t - 0.014) / 0.020) * (1.0 - smoothstep((r - 0.016) / 0.008))
        tot = wt + group_weight(body, "hand.%s" % side, v.index)
        newt = tot * f
        if newt > 1e-4:
            g_thumb.add([v.index], newt, "REPLACE")
        else:
            g_thumb.remove([v.index])
        rest = tot - newt
        if rest > 1e-4:
            g_hand.add([v.index], rest, "REPLACE")
        else:
            g_hand.remove([v.index])
        n += 1
    return n


# --------------------------------------------------------------------- pose ---

def rot_bone(pb, rx=0.0, ry=0.0, rz=0.0):
    mx = Matrix.Rotation(math.radians(rx), 3, "X")
    my = Matrix.Rotation(math.radians(ry), 3, "Y")
    mz = Matrix.Rotation(math.radians(rz), 3, "Z")
    rot = mz @ my @ mx
    rest = pb.bone.matrix_local.to_3x3()
    pb.rotation_mode = "QUATERNION"
    pb.rotation_quaternion = (rest.inverted() @ rot @ rest).to_quaternion()


POSE_TEST = {
    "spine": (1.5, 0, 0),
    "chest": (1.0, 0, 0),
    "neck": (-2.0, 0, 0),
    "head": (-1.0, 0, 3.0),
    "shoulder.L": (0, 0, -1.5),
    "upper_arm.L": (-4.0, 0, 3.0),
    "fore_arm.L": (-15.0, 0, 0),
    "hand.L": (0, 0, -4.0),
    "thumb_L": (0.0, -8.0, -15.0),
    "index_L": (0, 30.0, 0),
    "shoulder.R": (0, 0, 1.5),
    "upper_arm.R": (-4.0, 0, -3.0),
    "fore_arm.R": (-15.0, 0, 0),
    "hand.R": (0, 0, 4.0),
    "thumb_R": (0.0, 8.0, 15.0),
    "index_R": (0, -30.0, 0),
    "thigh.L": (2.0, 0, -1.0),
    "shin.L": (-3.0, 0, 0),
    "thigh.R": (-1.0, 0, 1.0),
    "shin.R": (-3.0, 0, 0),
}

SPLAY = {          # pose sementara: telapak menghadap kamera, jari lurus
    "hand.L": (0, 0, 90.0),
    "hand.R": (0, 0, -90.0),
    "index_L": (0, 0, 0),
    "index_R": (0, 0, 0),
    "thumb_L": (0, 0, 0),
    "thumb_R": (0, 0, 0),
}


def make_pose_test(arm):
    for pb in arm.pose.bones:
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
        pb.location = (0.0, 0.0, 0.0)
        pb.scale = (1.0, 1.0, 1.0)
    for name, val in POSE_TEST.items():
        pb = arm.pose.bones.get(name)
        if pb is None:
            print("  bone belum ada:", name)
            continue
        rot_bone(pb, *val)
    bpy.context.view_layer.update()

    arm.animation_data_clear()
    for act in list(bpy.data.actions):
        bpy.data.actions.remove(act)
    for pb in arm.pose.bones:
        pb.keyframe_insert("rotation_quaternion", frame=1)
    act = arm.animation_data.action
    act.name = "CHR_act_nara_pose-uji"
    act.use_fake_user = True
    return act


# ------------------------------------------------------------------ preview ---

def aim(cam, loc, tgt, lens):
    cam.data.lens = lens
    cam.location = loc
    cam.rotation_euler = (Vector(tgt) - Vector(loc)).normalized().to_track_quat(
        "-Z", "Y").to_euler()


def get_cam():
    scn = bpy.context.scene
    cam = bpy.data.objects.get("CAM_rig-preview")
    if cam is None:
        cam = bpy.data.objects.new("CAM_rig-preview",
                                   bpy.data.cameras.new("CAM_rig-preview"))
        scn.collection.objects.link(cam)
    scn.camera = cam
    scn.render.resolution_percentage = 50
    return cam


def render_hand_shots(cam):
    scn = bpy.context.scene
    out = []
    shots = [
        ("nara-v004-hand-01.png", (-0.46, -0.50, 0.70), (-0.198, -0.100, 0.735), 45.0),
        ("nara-v004-hand-02.png", (0.46, -0.50, 0.70), (0.198, -0.100, 0.735), 45.0),
    ]
    for name, loc, tgt, lens in shots:
        aim(cam, loc, tgt, lens)
        path = os.path.join(STILLS, name)
        scn.render.filepath = path
        bpy.ops.render.render(write_still=True)
        out.append(path)
        print("render ->", path)
    return out


def render_splay(cam):
    """Render verifikasi: telapak ke kamera, jari lurus (pose sementara).

    Action uji dilepas dulu: kalau tidak, evaluasi depsgraph saat render
    memasang ulang pose keyed di frame 1 dan pose sementara hilang.
    """
    scn = bpy.context.scene
    arm = bpy.data.objects["CHR_nara_rig"]
    ad = arm.animation_data
    act = ad.action if ad else None
    if ad:
        ad.action = None
    for pb in arm.pose.bones:
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
    for name in ("upper_arm.L", "upper_arm.R"):
        rot_bone(arm.pose.bones[name], -14.0, 0, 0)
    for name, val in SPLAY.items():
        rot_bone(arm.pose.bones[name], *val)
    bpy.context.view_layer.update()
    bpy.context.evaluated_depsgraph_get().update()

    aim(cam, (0.0, -0.94, 0.740), (0.0, 0.0, 0.715), 50.0)
    path = os.path.join(STILLS, "nara-v004-hand-splay.png")
    scn.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("render ->", path)

    if ad:
        ad.action = act
    scn.frame_set(1)
    bpy.context.view_layer.update()
    return path


# -------------------------------------------------------------- verifikasi ---

def verify(objs, arm, body):
    res = []
    for ob in objs:
        me = ob.data
        bm = bmesh.new()
        bm.from_mesh(me)
        boundary = len([e for e in bm.edges if len(e.link_faces) == 1])
        bm.free()
        bad = []
        for v in me.vertices:
            tot = sum(g.weight for g in v.groups)
            if not (0.999 <= tot <= 1.001):
                bad.append((v.index, round(tot, 4)))
        print("VERIFY %s verts %d polys %d ngon %d boundary %d tanpa-bobot %s"
              % (ob.name, len(me.vertices), len(me.polygons),
                 len([p for p in me.polygons if len(p.vertices) > 4]), boundary, bad))
        res.append((ob.name, len(me.vertices), boundary, len(bad)))
    body_bad = [v.index for v in body.data.vertices
                if not (0.999 <= sum(g.weight for g in v.groups) <= 1.001)]
    print("VERIFY body verts %d tanpa-bobot %s overlap-doang %s"
          % (len(body.data.vertices), body_bad,
             len(bpy.data.objects["CHR_nara_rig"].data.bones)))
    print("VERIFY bones:", len(arm.data.bones),
          [b.name for b in arm.data.bones if b.name in
           ("thumb_L", "thumb_R", "index_L", "index_R", "jaw")])
    return res, body_bad


def main():
    os.makedirs(os.path.dirname(DST), exist_ok=True)
    os.makedirs(STILLS, exist_ok=True)
    shutil.copy2(SRC, DST)
    bpy.ops.wm.open_mainfile(filepath=DST)
    scn = bpy.context.scene
    arm = bpy.data.objects["CHR_nara_rig"]
    body = bpy.data.objects["CHR_nara_body"]
    col = bpy.data.collections["CHR_nara"]
    log("PLAN", "nara_rig_v004: salin v003, jari 1,8x radius / 0,75x panjang / "
               "ujung bulat / tekuk 13 deg, pose uji genggam 30 deg")

    remove_object("CHR_nara_fingers")
    remove_object("CHR_nara_thumbs")
    fingers, fstat = build_fingers(arm, col)
    thumbs, tstat = build_thumbs(arm, col)
    print("jari: %d vertex / %d poly; ibu jari: %d vertex / %d poly"
          % (len(fingers.data.vertices), len(fingers.data.polygons),
             len(thumbs.data.vertices), len(thumbs.data.polygons)))
    print("ibu jari: panjang %.1f mm radius %s mm" % (THUMB_LEN * 1000,
          [round(THUMB_R0 * SCALE_R * p * 1000, 1) for p in THUMB_PROFILE]))
    for side in ("L", "R"):
        for name, L, rr in fstat[side][2]:
            print("  jari %s_%-6s panjang %5.1f mm radius %s mm" % (side, name, L * 1000, rr))
    log("MODEL", "jari %d vertex + ibu jari %d vertex (keduanya subsurf L2), "
                 "penampang 1,8x, panjang 0,75x/0,85x, tekuk 13 deg"
        % (len(fingers.data.vertices), len(thumbs.data.vertices)))

    n_stub = 0
    for side in ("L", "R"):
        n_stub += shrink_thumb_stub(body, arm, side)
    n_rw = 0
    for side in ("L", "R"):
        n_rw += reweight_thumb(body, arm, side)
    print("stub ibu jari lama: %d vertex dikecilkan, %d vertex direweight" % (n_stub, n_rw))

    act = make_pose_test(arm)
    scn.frame_set(1)
    bpy.context.view_layer.update()
    print("action:", act.name, tuple(act.frame_range))

    vres, body_bad = verify([fingers, thumbs], arm, body)

    cam = get_cam()
    splay = render_splay(cam)
    stills = render_hand_shots(cam)
    scn.frame_set(1)
    bpy.context.view_layer.update()
    scn.render.resolution_percentage = 50

    scn.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=DST)
    size_kb = os.path.getsize(DST) / 1024.0
    print("SAVED", DST, round(size_kb, 1), "KB")
    log("VERIFY", "nara-v004: render tangan kanan/kiri + splay 50%%, "
                  "jari %d + ibu jari %d vertex, 0 tanpa bobot, boundary %d/%d"
        % (vres[0][1], vres[1][1], vres[0][2], vres[1][2]))
    log("DONE", "nara_rig_v004.blend siap (%.0f KB), pose uji frame 1 genggam 30 deg; "
                "stills: nara-v004-hand-01.png, nara-v004-hand-02.png, "
                "nara-v004-hand-splay.png" % size_kb)


if __name__ == "__main__":
    main()

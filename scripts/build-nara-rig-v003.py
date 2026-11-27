"""build-nara-rig-v003.py — rig Nara v003 (tambah jari, rahang, loop sendi).

HEADLESS:
    & "D:\\Blender Foundation\\Blender 5.2\\blender.exe" -b -P scripts/build-nara-rig-v003.py

Sumber: assets/char/nara_rig_v002.blend  (TIDAK diubah)
Hasil : assets/char/nara_rig_v003.blend

Perubahan dari v002:
  * 21 bone -> 26 bone: + thumb_L, thumb_R, index_L, index_R, jaw
  * satu ring pemisah di atas & di bawah siku dan lutut (bisect_plane pada
    geometri band sendi saja, bukan seluruh mesh) — 2 ring per sendi supaya
    tekukan 25-35 derajat tidak patah
  * geometri jari (4 jari per tangan) sebagai objek CHR_nara_fingers,
    di-skin ke index_*/hand_*
  * bobot: ujung ibu jari -> thumb_*, kipas jari -> index_*, dagu/bibir
    bawah -> jaw (falloff halus dari z 1,535)
  * pose uji CHR_act_nara_pose-uji frame 1: berdiri rileks, siku 15 derajat,
    tangan setengah menggenggam
  * rambut, mata, dan jam selam di v002 sudah BONE-parent (head / hand.L),
    jadi tidak diubah.

Catatan: file v002 tidak pernah disimpan ulang; skrip menyalinnya lebih dulu.
"""

import bpy
import bmesh
import datetime
import math
import os
import shutil
from mathutils import Matrix, Vector

ROOT = r"D:/Tugas Semester 5/Grafika Komputer/Project-Animasi"
SRC = ROOT + "/assets/char/nara_rig_v002.blend"
DST = ROOT + "/assets/char/nara_rig_v003.blend"
LOGPATH = ROOT + "/renders/logs/technical.log"
STILLS = ROOT + "/renders/stills"


def log(phase, line):
    os.makedirs(os.path.dirname(LOGPATH), exist_ok=True)
    stamp = datetime.datetime.now().strftime("%H:%M")
    with open(LOGPATH, "a", encoding="utf-8") as fh:
        fh.write("[%s] %s - %s\n" % (stamp, phase, line))
    print("[log]", phase, line)


# --------------------------------------------------------------------- mesh ---


def count_ngons(mesh):
    return len([p for p in mesh.polygons if len(p.vertices) > 4])


def add_ring_cut(bm, zplane, lo, hi, xmin):
    """bisect_plane hanya pada face band sendi -> satu ring baru, quad bersih."""
    faces = []
    for f in bm.faces:
        vs = [v.co for v in f.verts]
        if all(lo <= c.z <= hi for c in vs) and min(abs(c.x) for c in vs) > xmin:
            faces.append(f)
    if not faces:
        return 0
    geom = set()
    for f in faces:
        geom.add(f)
        geom.update(f.edges)
        geom.update(f.verts)
    bmesh.ops.bisect_plane(
        bm, geom=list(geom), dist=1e-5,
        plane_co=Vector((0.0, 0.0, zplane)), plane_no=Vector((0.0, 0.0, 1.0)),
        clear_inner=False, clear_outer=False)
    return len(faces)


def add_joint_loops(body):
    """Ring di atas+bawah siku (z 1,142 / 1,010) dan lutut (0,522 / 0,452)."""
    bm = bmesh.new()
    bm.from_mesh(body.data)
    bm.verts.layers.deform.verify()
    cuts = [
        (1.142, 1.062, 1.220, 0.11),
        (1.010, 0.945, 1.078, 0.13),
        (0.522, 0.465, 0.575, 0.03),
        (0.452, 0.423, 0.478, 0.03),
    ]
    total = 0
    for z, lo, hi, xmin in cuts:
        total += add_ring_cut(bm, z, lo, hi, xmin)
    # ratakan ngon kecil yang lahir di band sendi
    ngons = [f for f in bm.faces if len(f.verts) > 4 and
             min(abs(v.co.x) for v in f.verts) > 0.03 and
             (0.40 < f.calc_center_median().z < 1.25)]
    if ngons:
        bmesh.ops.triangulate(bm, faces=ngons)
    bm.to_mesh(body.data)
    bm.free()
    body.data.update()
    return total, len(ngons)


# ------------------------------------------------------------------- fingers ---

FINGER_SPEC = [
    ("index", -0.026, -0.003, 0.074, 0.0080, 0.0044),
    ("middle", -0.009, -0.001, 0.078, 0.0082, 0.0046),
    ("ring", 0.008, 0.001, 0.070, 0.0076, 0.0042),
    ("pinky", 0.024, 0.004, 0.058, 0.0066, 0.0036),
]

PALM_TIP = (0.205, 0.008, 0.664)   # ujung telapak sisi kiri (x positif)


def finger_mesh(side):
    s = 1.0 if side == "L" else -1.0
    cx, cy, cz = PALM_TIP
    V, F = [], []
    groups = {}
    seg = 8
    for name, dy, dx, length, r0, r1 in FINGER_SPEC:
        start = len(V)
        base = Vector((s * (cx + dx), cy + dy, cz + 0.014))
        mid = Vector((s * (cx + dx * 1.4), cy + dy - 0.005, cz - length * 0.55))
        tip = Vector((s * (cx + dx * 1.8), cy + dy - 0.008, cz - length))
        pts = [base, mid, tip]
        radii = [r0, r0 * 0.95, r1]
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
            for k in range(seg):
                a = 2.0 * math.pi * k / seg
                V.append(p + xa * (radii[i] * math.cos(a)) + ya * (radii[i] * math.sin(a)))
        for k in range(len(rings) - 1):
            a, b = rings[k], rings[k + 1]
            for i in range(seg):
                i2 = (i + 1) % seg
                F.append((a + i, a + i2, b + i2, b + i))
        F.append(tuple(rings[0] + i for i in range(seg - 1, -1, -1)))
        F.append(tuple(rings[-1] + i for i in range(seg)))
        groups[name] = (start, len(V))
    return V, F, groups


def build_fingers(arm, col):
    V, F, ranges = [], [], {}
    for side in ("L", "R"):
        v, f, groups = finger_mesh(side)
        off = len(V)
        V.extend(v)
        F.extend(tuple(i + off for i in fa) for fa in f)
        ranges[side] = {n: (a + off, b + off) for n, (a, b) in groups.items()}

    mesh = bpy.data.meshes.new("CHR_nara_fingers")
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

    ob = bpy.data.objects.new("CHR_nara_fingers", mesh)
    col.objects.link(ob)
    ob.parent = arm
    ob.matrix_parent_inverse = arm.matrix_world.inverted()
    ob["asset"] = "CHR_nara"
    ob["note"] = "jari v003; kipas 4 jari -> index_*, ibu jari -> thumb_*"

    for side in ("L", "R"):
        gi = ob.vertex_groups.new(name="index_%s" % side)
        for name, (a, b) in ranges[side].items():
            gi.add(list(range(a, b)), 1.0, "REPLACE")
    mod = ob.modifiers.new("Armature", "ARMATURE")
    mod.object = arm
    return ob, mesh


# -------------------------------------------------------------------- bones ---

NEW_BONES = {
    "jaw": dict(head=(0.0, 0.022, 1.508), tail=(0.0, -0.078, 1.478), parent="head"),
    "thumb_L": dict(head=(0.196, -0.008, 0.772), tail=(0.180, -0.052, 0.722),
                    parent="hand.L"),
    "thumb_R": dict(head=(-0.196, -0.008, 0.772), tail=(-0.180, -0.052, 0.722),
                    parent="hand.R"),
    "index_L": dict(head=(0.202, -0.018, 0.660), tail=(0.202, -0.026, 0.586),
                    parent="hand.L"),
    "index_R": dict(head=(-0.202, -0.018, 0.660), tail=(-0.202, -0.026, 0.586),
                    parent="hand.R"),
}


def add_bones(arm):
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    eb = arm.data.edit_bones
    for name, spec in NEW_BONES.items():
        if name in eb:
            eb.remove(eb[name])
        b = eb.new(name)
        b.head = Vector(spec["head"])
        b.tail = Vector(spec["tail"])
        b.parent = eb[spec["parent"]]
        b.use_connect = False
    bpy.ops.object.mode_set(mode="OBJECT")
    return [b.name for b in arm.data.bones]


# ------------------------------------------------------------------ weights ---

def seg_dist(p, a, b):
    ab = b - a
    d = ab.length_squared
    t = 0.0
    if d > 1e-12:
        t = max(0.0, min(1.0, (p - a).dot(ab) / d))
    return (p - (a + ab * t)).length


def group_weight(ob, name, idx):
    g = ob.vertex_groups.get(name)
    if g is None:
        return 0.0
    try:
        return g.weight(idx)
    except RuntimeError:
        return 0.0


def transfer_thumb(body, arm):
    n = 0
    for side in ("L", "R"):
        bt = arm.data.bones["thumb_%s" % side]
        bh = arm.data.bones["hand.%s" % side]
        g_hand = body.vertex_groups.get("hand.%s" % side)
        g_thumb = body.vertex_groups.get("thumb_%s" % side)
        if g_hand is None or g_thumb is None:
            continue
        for v in body.data.vertices:
            if not (0.70 < v.co.z < 0.80) or abs(v.co.x) < 0.16:
                continue
            w = group_weight(body, "hand.%s" % side, v.index)
            if w <= 0.0:
                continue
            dt = seg_dist(v.co, bt.head_local, bt.tail_local)
            dh = seg_dist(v.co, bh.head_local, bh.tail_local)
            if dt + 0.004 < dh:
                g_thumb.add([v.index], w * 0.92, "REPLACE")
                if w * 0.08 > 1e-4:
                    g_hand.add([v.index], w * 0.08, "REPLACE")
                else:
                    g_hand.remove([v.index])
                n += 1
    return n


def transfer_jaw(body):
    g_head = body.vertex_groups.get("head")
    g_jaw = body.vertex_groups.get("jaw")
    if g_head is None or g_jaw is None:
        return 0

    def smooth(t):
        t = max(0.0, min(1.0, t))
        return t * t * (3.0 - 2.0 * t)

    n = 0
    for v in body.data.vertices:
        if v.co.z > 1.535 or v.co.z < 1.44 or v.co.y > 0.03:
            continue
        w_head = group_weight(body, "head", v.index)
        if w_head <= 0.0:
            continue
        f = smooth((1.535 - v.co.z) / 0.055) * smooth((0.030 - v.co.y) / 0.030)
        if f <= 0.01:
            continue
        g_jaw.add([v.index], w_head * f, "REPLACE")
        rest = w_head * (1.0 - f)
        if rest > 1e-4:
            g_head.add([v.index], rest, "REPLACE")
        else:
            g_head.remove([v.index])
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
    "thumb_L": (-28.0, 0, 0),
    "index_L": (-34.0, 0, 0),
    "shoulder.R": (0, 0, 1.5),
    "upper_arm.R": (-4.0, 0, -3.0),
    "fore_arm.R": (-15.0, 0, 0),
    "hand.R": (0, 0, 4.0),
    "thumb_R": (-28.0, 0, 0),
    "index_R": (-34.0, 0, 0),
    "thigh.L": (2.0, 0, -1.0),
    "shin.L": (-3.0, 0, 0),
    "thigh.R": (-1.0, 0, 1.0),
    "shin.R": (-3.0, 0, 0),
}


def flexion(arm, a, b, c):
    """Sudut tekuk di sendi b: 0 = lurus, 90 = siku terlipat penuh."""
    pa = arm.matrix_world @ arm.pose.bones[a].head
    pb = arm.matrix_world @ arm.pose.bones[b].head
    pc = arm.matrix_world @ arm.pose.bones[c].head
    v1 = (pa - pb).normalized()
    v2 = (pc - pb).normalized()
    return 180.0 - math.degrees(math.acos(max(-1.0, min(1.0, v1.dot(v2)))))


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


# ----------------------------------------------------------------- preview ---


def render_previews():
    scn = bpy.context.scene
    cam = bpy.data.objects.get("CAM_rig-preview")
    if cam is None:
        cam = bpy.data.objects.new("CAM_rig-preview",
                                   bpy.data.cameras.new("CAM_rig-preview"))
        scn.collection.objects.link(cam)
    scn.camera = cam
    scn.render.resolution_percentage = 50
    out = []
    shots = [
        ("nara-rig-v003_pose-uji-01.png", (0.05, -4.30, 1.05), (0.0, 0.0, 0.90), 45.0),
        ("nara-rig-v003_pose-uji-02.png", (-2.35, -2.75, 1.35), (0.0, 0.0, 0.90), 45.0),
        ("nara-rig-v003_hands.png", (0.62, -1.05, 0.80), (0.02, 0.0, 0.72), 70.0),
    ]
    for name, loc, tgt, lens in shots:
        cam.data.lens = lens
        cam.location = loc
        cam.rotation_euler = (Vector(tgt) - Vector(loc)).normalized().to_track_quat(
            "-Z", "Y").to_euler()
        path = os.path.join(STILLS, name)
        scn.render.filepath = path
        bpy.ops.render.render(write_still=True)
        out.append(path)
        print("render ->", path)
    scn.render.resolution_percentage = 100
    return out


# -------------------------------------------------------------------- main ---


def main():
    os.makedirs(os.path.dirname(DST), exist_ok=True)
    shutil.copy2(SRC, DST)
    bpy.ops.wm.open_mainfile(filepath=DST)
    scn = bpy.context.scene
    arm = bpy.data.objects["CHR_nara_rig"]
    body = bpy.data.objects["CHR_nara_body"]
    col = bpy.data.collections["CHR_nara"]
    print("SUMBER bone:", len(arm.data.bones), "vertex body:", len(body.data.vertices))

    n_before, ngon_before = len(body.data.vertices), count_ngons(body.data)
    faces, tri = add_joint_loops(body)
    print("loop sendi: %d face dipotong/ring, %d ngon kecil ditriangulasi; "
          "vertex %d -> %d, ngon %d -> %d"
          % (faces, tri, n_before, len(body.data.vertices), ngon_before,
             count_ngons(body.data)))

    fingers, fmesh = build_fingers(arm, col)
    print("jari:", len(fmesh.vertices), "vertex,", len(fmesh.polygons), "poly")

    bones = add_bones(arm)
    print("bone total:", len(bones))
    for name in ("thumb_L", "thumb_R", "index_L", "index_R", "jaw"):
        if body.vertex_groups.get(name) is None:
            body.vertex_groups.new(name=name)

    n_thumb = transfer_thumb(body, arm)
    n_jaw = transfer_jaw(body)
    print("bobot: %d vertex ibu jari -> thumb, %d vertex dagu -> jaw" % (n_thumb, n_jaw))
    print("bone-parent aset:", [
        (o.name, o.parent_type, o.parent_bone)
        for o in bpy.data.objects if o.type == "MESH" and o.parent_type == "BONE"])

    act = make_pose_test(arm)
    scn.frame_set(1)
    bpy.context.view_layer.update()
    stats = {
        "siku_L": flexion(arm, "upper_arm.L", "fore_arm.L", "hand.L"),
        "siku_R": flexion(arm, "upper_arm.R", "fore_arm.R", "hand.R"),
        "lutut_L": flexion(arm, "thigh.L", "shin.L", "foot.L"),
        "lutut_R": flexion(arm, "thigh.R", "shin.R", "foot.R"),
    }
    print("pose uji:", {k: round(v, 1) for k, v in stats.items()})

    # bukti rambut/mata ikut kepala: putar kepala 25 derajat
    def bbox_center(name):
        ob = bpy.data.objects[name]
        pts = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
        return sum(pts, Vector()) / 8.0

    eye_before = bbox_center("CHR_nara_eye_l")
    pb = arm.pose.bones["head"]
    q = pb.rotation_quaternion.copy()
    rot_bone(pb, 0, 0, 25)
    bpy.context.view_layer.update()
    eye_after = bbox_center("CHR_nara_eye_l")
    pb.rotation_quaternion = q
    bpy.context.view_layer.update()
    print("mata ikut kepala 25 deg: %.3f m" % (eye_after - eye_before).length)
    print("action:", act.name, act.frame_range[:])
    print("bone:", [b.name for b in arm.data.bones])

    stills = render_previews()

    scn.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=DST)
    print("SAVED", DST, os.path.getsize(DST) / 1024.0, "KB")
    log("RIG", "nara_rig_v003: 26 bone (+thumb/index/jaw), ring sendi siku+lutut, "
              "jari %d vert, pose uji siku %.0f/%.0f lutut %.0f/%.0f"
        % (len(fmesh.vertices), stats["siku_L"], stats["siku_R"],
           stats["lutut_L"], stats["lutut_R"]))
    print("STILLS", stills)


if __name__ == "__main__":
    main()

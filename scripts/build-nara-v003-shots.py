"""build-nara-v003-shots.py — bangun ulang shot 050 / 060 / 070 Scene 1.

    & "D:\\Blender Foundation\\Blender 5.2\\blender.exe" -b ^
        -P scripts/build-nara-v003-shots.py -- 050

HEADLESS, tanpa Blender MCP. Rig karakter: nara_rig_v003 (26 bone),
peralatan: divegear_v002. Karang / lamun / ikan / look tidak diubah —
shot memakai reef-dense_v004, sekolah v003, penyu, island-detail v004 dan
look.py yang sama seperti build-scene-1-v004-shots.py.

Perubahan pokok:
  050  pose menyelam: siku 25-35 derajat, lutut 20-30 derajat, kaki menendang
       bergantian, masker+snorkel di kepala, fin di tumit (bukan melayang)
  060  close-up, lambaian dengan telapak terbuka + jari, masker+snorkel
  070  re-stage: pinggang Nara di z 0 (setengah badan di air), tangan kanan
       memegang dek perahu, tangan kiri memegang masker (terlihat sejak f1),
       snorkel masih di kepala, kamera low angle dari air
"""

import bpy
import datetime
import importlib.util
import math
import os
import sys
from mathutils import Matrix, Quaternion, Vector

ROOT = r"D:/Tugas Semester 5/Grafika Komputer/Project-Animasi"
ASSETS = ROOT + "/assets"
STILLS = ROOT + "/renders/stills"
LOGPATH = ROOT + "/renders/logs/technical.log"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


v4 = _load("s1v4", ROOT + "/scripts/build-scene-1-v004-shots.py")
s1 = v4.s1
look = v4.look
lib = v4.lib

P_NARA = ASSETS + "/char/nara_rig_v003.blend"
P_DIVEGEAR = ASSETS + "/props/divegear_v002.blend"
P_REEF = v4.P_REEF
P_TURTLE = v4.P_TURTLE
P_ISLAND = v4.P_ISLAND
P_BOATS = v4.P_BOATS

SHOTS = {
    "050": ("scene-1_shot-050_nara-dive_v001.blend", 96),
    "060": ("scene-1_shot-060_nara-ok_v001.blend", 72),
    "070": ("scene-1_shot-070_nara-naik_v001.blend", 96),
}


def log(phase, line):
    os.makedirs(os.path.dirname(LOGPATH), exist_ok=True)
    stamp = datetime.datetime.now().strftime("%H:%M")
    with open(LOGPATH, "a", encoding="utf-8") as fh:
        fh.write("[%s] %s - %s\n" % (stamp, phase, line))
    print("[log]", phase, line)


# --------------------------------------------------------------------- util ---


def setup(name, frame_end):
    return v4.setup(name, frame_end)


def name_action(arm, name):
    ad = arm.animation_data
    if ad and ad.action:
        ad.action.name = name
        ad.action.use_fake_user = True
        print("    action:", ad.action.name, ad.action.frame_range[:])


def append_nara():
    v4.append_asset(P_NARA, "CHR_nara")
    v4.append_asset(P_DIVEGEAR, "PRP_divegear")
    arm = bpy.data.objects.get("CHR_nara_rig")
    if arm is None:
        raise RuntimeError("CHR_nara_rig tidak ada")
    print("  rig v003 bone:", len(arm.data.bones),
          "| divegear v002:",
          [o.name for o in bpy.data.objects if o.name.startswith("PRP_divegear_")])
    return arm


def flexion(arm, a, b, c):
    pa = arm.matrix_world @ arm.pose.bones[a].head
    pb = arm.matrix_world @ arm.pose.bones[b].head
    pc = arm.matrix_world @ arm.pose.bones[c].head
    v1 = (pa - pb).normalized()
    v2 = (pc - pb).normalized()
    return 180.0 - math.degrees(math.acos(max(-1.0, min(1.0, v1.dot(v2)))))


def report_flexion(arm, label):
    d = {
        "siku_L": flexion(arm, "upper_arm.L", "fore_arm.L", "hand.L"),
        "siku_R": flexion(arm, "upper_arm.R", "fore_arm.R", "hand.R"),
        "lutut_L": flexion(arm, "thigh.L", "shin.L", "foot.L"),
        "lutut_R": flexion(arm, "thigh.R", "shin.R", "foot.R"),
    }
    print("    %-12s siku L/R %.1f/%.1f  lutut L/R %.1f/%.1f"
          % (label, d["siku_L"], d["siku_R"], d["lutut_L"], d["lutut_R"]))
    return d


def ik_arm(arm, side, target, pole=None):
    """IK 2-bone sementara lalu di-bake ke pose bone (tanpa constraint sisa)."""
    scn = bpy.context.scene
    tgt = bpy.data.objects.new("TMP_ik_%s" % side, None)
    scn.collection.objects.link(tgt)
    tgt.location = Vector(target)
    if pole is not None:
        pol = bpy.data.objects.new("TMP_pole_%s" % side, None)
        scn.collection.objects.link(pol)
        pol.location = Vector(pole)

    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="POSE")
    pbf = arm.pose.bones["fore_arm." + side]
    con = pbf.constraints.new("IK")
    con.target = tgt
    con.chain_count = 2
    con.use_tail = True
    if pole is not None:
        con.pole_target = pol
        con.pole_angle = math.radians(-90.0)
    bpy.context.view_layer.update()

    chain = ["upper_arm." + side, "fore_arm." + side]
    mats = {name: arm.pose.bones[name].matrix.copy() for name in chain}
    pbf.constraints.remove(con)
    bpy.context.view_layer.update()
    for name in chain:                      # induk dulu, lalu anak
        pb = arm.pose.bones[name]
        pb.matrix = mats[name]
        bpy.context.view_layer.update()
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.data.objects.remove(tgt, do_unlink=True)
    if pole is not None:
        bpy.data.objects.remove(pol, do_unlink=True)
    bpy.context.view_layer.update()


def hand_twist(arm, side, want_dir):
    """Putar pergelangan pada sumbu tulang supaya telapak menghadap want_dir."""
    pb = arm.pose.bones["hand." + side]
    base = pb.rotation_quaternion.copy()
    rest_x = pb.bone.matrix_local.to_3x3().inverted() @ Vector((1.0, 0.0, 0.0))
    want = Vector(want_dir).normalized()
    best = (-2.0, 0)
    for deg in range(-180, 180, 5):
        pb.rotation_quaternion = base @ Quaternion(Vector((0.0, 1.0, 0.0)),
                                                   math.radians(deg))
        bpy.context.view_layer.update()
        n = (arm.matrix_world @ pb.matrix).to_3x3() @ rest_x
        d = n.normalized().dot(want)
        if d > best[0]:
            best = (d, deg)
    pb.rotation_quaternion = base @ Quaternion(Vector((0.0, 1.0, 0.0)),
                                               math.radians(best[1]))
    bpy.context.view_layer.update()
    print("    twist hand.%s %.0f deg (dot %.2f)" % (side, best[1], best[0]))
    return best[1]


def aim_hand(arm, side, want_dir):
    """Arahkan tulang hand ke arah dunia want_dir (tanpa mengubah ujungnya)."""
    pb = arm.pose.bones["hand." + side]
    M = pb.matrix.copy()
    R = arm.matrix_world.to_3x3()
    want = (R.inverted() @ Vector(want_dir)).normalized()
    cur = (M.to_3x3() @ Vector((0.0, 1.0, 0.0))).normalized()
    q = cur.rotation_difference(want)
    new3 = (q.to_matrix() @ M.to_3x3()).to_4x4()
    new3.translation = M.translation
    pb.matrix = new3
    bpy.context.view_layer.update()


def foot_matrix(arm, side):
    """Matriks fin: origin di TUMIT, mengikuti rotasi tulang foot apa adanya.

    Geometri fin v002 sudah dibangun sejajar sumbu armature saat rest
    (tumit di origin, bilah ke -Y), jadi transform rest->pose tulang foot
    dipakai langsung tanpa mencari sumbu lagi.
    """
    pb = arm.pose.bones["foot." + side]
    sx = 1.0 if side == "L" else -1.0
    heel_rest = Vector((sx * 0.088, 0.058, 0.004))
    M = arm.matrix_world @ pb.matrix @ pb.bone.matrix_local.inverted() @ \
        Matrix.Translation(heel_rest)
    heel_world = M.translation.copy()
    return M, heel_world


def attach_fins(arm):
    out = []
    for side in ("L", "R"):
        fin = bpy.data.objects.get("PRP_divegear_fin_" + side)
        if fin is None:
            continue
        M, heel = foot_matrix(arm, side)
        s1.bone_parent(fin, arm, "foot." + side, M)
        out.append((side, heel))
        print("    fin %s: tumit di (%.2f, %.2f, %.2f)"
              % (side, heel.x, heel.y, heel.z))
    return out


def attach_mask_head(arm):
    mask = bpy.data.objects.get("PRP_divegear_mask")
    sn = bpy.data.objects.get("PRP_divegear_snorkel")
    fh, upn, her_right = s1.face_frame(arm)
    face_c = s1.bone_world(arm, "head", 0.56) + upn * 0.005
    yaw = s1.yaw_of(fh)
    if mask is not None:
        s1.attach_gear(mask, arm, "head", face_c + fh * 0.095 + upn * 0.012, yaw)
    if sn is not None:
        mouth = face_c - upn * 0.058 + her_right * 0.048 + fh * 0.004
        s1.attach_gear(sn, arm, "head", mouth, yaw + 6.0, roll_deg=-8.0)
    bpy.context.view_layer.update()
    return face_c, mask, sn


# ===========================================================================
# 050 — menyelam santai, siku 25-35, lutut 20-30, kaki bergantian
# ===========================================================================

DIVE_A = {
    "spine": (7, 0, 0),
    "chest": (4, 0, 0),
    "neck": (-11, 0, 0),
    "head": (-9, 0, 0),
    "shoulder.L": (-4, 0, 0),
    "upper_arm.L": (-52, 0, 16),
    "fore_arm.L": (-31, 0, 0),
    "hand.L": (-6, 0, 0),
    "thumb_L": (-12, 0, 0),
    "index_L": (-10, 0, 0),
    "shoulder.R": (-4, 0, 0),
    "upper_arm.R": (-102, 0, -14),
    "fore_arm.R": (-28, 0, 0),
    "hand.R": (-8, 0, 0),
    "thumb_R": (-12, 0, 0),
    "index_R": (-10, 0, 0),
    "thigh.L": (20, 0, -3),
    "shin.L": (25, 0, 0),
    "foot.L": (-16, 0, 0),
    "thigh.R": (-13, 0, 3),
    "shin.R": (23, 0, 0),
    "foot.R": (-13, 0, 0),
}

DIVE_B = {
    "spine": (6, 0, 0),
    "chest": (3, 0, 0),
    "neck": (-10, 0, 0),
    "head": (-8, 0, 0),
    "shoulder.L": (-4, 0, 0),
    "upper_arm.L": (-102, 0, 12),
    "fore_arm.L": (-28, 0, 0),
    "hand.L": (-6, 0, 0),
    "thumb_L": (-12, 0, 0),
    "index_L": (-10, 0, 0),
    "shoulder.R": (-4, 0, 0),
    "upper_arm.R": (-54, 0, -16),
    "fore_arm.R": (-31, 0, 0),
    "hand.R": (-8, 0, 0),
    "thumb_R": (-12, 0, 0),
    "index_R": (-10, 0, 0),
    "thigh.L": (-13, 0, -3),
    "shin.L": (23, 0, 0),
    "foot.L": (-13, 0, 0),
    "thigh.R": (20, 0, 3),
    "shin.R": (25, 0, 0),
    "foot.R": (-16, 0, 0),
}


def build_050():
    v4.wipe()
    scn = setup("scene-1_shot-050_nara-dive", 96)
    v4.append_reef()
    v4.rig_all_schools()
    v4.tighten_school("cakalang", -3.95)
    v4.tighten_school("kakatua", -3.85)
    v4.tighten_school("damselfish", -3.90)
    v4.append_asset(P_TURTLE, "ENV_turtle")
    arm = append_nara()

    v4.move_corals([((-2.55, -2.05, -5.05), 2.6, 0), ((-0.30, -2.60, -5.02), 1.5, 22),
                    ((2.6, -2.9, -5.05), 1.7, 41)])

    ctl_t = bpy.data.objects.get("CTL_turtle")
    if ctl_t is not None:
        ctl_t.location = (-4.6, 4.7, -2.50)
        ctl_t.rotation_euler = (math.radians(2), 0.0, math.radians(96))
        v4.set_interp("LINEAR")
        ctl_t.keyframe_insert("location", frame=1)
        ctl_t.keyframe_insert("rotation_euler", frame=1)
        ctl_t.location = (-5.3, 5.5, -2.42)
        ctl_t.keyframe_insert("location", frame=96)

    pv = "ENV_school_%s_pivot"
    if pv % "cakalang" in bpy.data.objects:
        v4.pivot_keys(bpy.data.objects[pv % "cakalang"],
                      [(1, (-2.0, 1.0, -0.2), -88.0), (48, (0.5, 1.0, 0.0), -90.0),
                       (96, (3.5, 0.8, 0.2), -93.0)])
    if pv % "kakatua" in bpy.data.objects:
        v4.pivot_keys(bpy.data.objects[pv % "kakatua"],
                      [(1, (3.0, 3.6, 0.2), -85.0), (48, (1.0, 3.2, 0.1), -90.0),
                       (96, (-1.5, 2.8, 0.0), -93.0)])
    if pv % "damselfish" in bpy.data.objects:
        v4.pivot_keys(bpy.data.objects[pv % "damselfish"],
                      [(1, (4.5, -2.0, 0.0), 87.0), (48, (2.5, -1.6, 0.0), 90.0),
                       (96, (0.5, -1.2, 0.05), 92.0)])

    v4.prepare_rig(arm)
    arm.rotation_mode = "XYZ"
    arm.rotation_euler = (math.radians(72), 0.0, math.radians(96))
    arm.location = (-3.25, 0.95, -3.40)
    v4.set_interp("BEZIER")
    arm.keyframe_insert("location", frame=1)
    arm.keyframe_insert("rotation_euler", frame=1)

    bones = list(DIVE_A.keys())
    v4.key_pose(arm, 1, DIVE_A, bones)
    v4.key_pose(arm, 24, DIVE_B, bones)
    v4.key_pose(arm, 48, DIVE_A, bones)
    v4.key_pose(arm, 72, DIVE_B, bones)
    v4.key_pose(arm, 96, DIVE_A, bones)
    arm.location = (-1.70, 0.80, -3.25)
    arm.keyframe_insert("location", frame=96)
    name_action(arm, "CHR_act_nara_050_dive")
    scn.frame_set(48)
    bpy.context.view_layer.update()
    flex = report_flexion(arm, "050-f48")

    scn.frame_set(1)
    bpy.context.view_layer.update()
    attach_mask_head(arm)
    fins = attach_fins(arm)

    s1.sun(scn, energy=3.2, angle=5.0, rot=(14, 0, 26), color=(0.82, 0.94, 1.0))
    lib.add_world("WLD_s1_050", "#0F5C63", strength=1.1)
    lib.add_fill(energy=140.0, size=6.0, loc=(-1.0, -6.0, -0.6),
                 target=(-2.2, 0.6, -3.2))
    s1.underwater_fog(scn)

    cam = s1.make_cam("CAM_shot-050_medium", (1.0, -4.7, -2.95),
                      (-2.4, 0.9, -3.30), lens=45.0)
    v4.only_camera(cam)
    s1.key_cam(cam, [
        (1, (1.0, -4.7, -2.95), (-2.4, 0.9, -3.30)),
        (96, (0.4, -4.4, -2.90), (-1.2, 0.8, -3.25)),
    ])
    cam.data.dof.use_dof = True
    cam.data.dof.aperture_fstop = 4.0
    focus = s1.root_empty("EMPTY_focus-nara", (-2.4, 0.9, -3.3))
    s1.adopt([focus], arm)
    cam.data.dof.focus_object = focus
    scn.frame_set(1)

    size = v4.save_shot("050")
    v4.summary("050")
    log("ANIM", "s1-050 rig v003 + divegear v002: siku %.0f/%.0f, lutut %.0f/%.0f, "
                "fin di tumit, masker+snorkel di kepala (%d bytes)"
        % (flex["siku_L"], flex["siku_R"], flex["lutut_L"], flex["lutut_R"], size))
    v4.still("050", 48, above_water=False)

    # close-up kaki: bukti fin menempel
    scn = bpy.context.scene
    scn.frame_set(48)
    bpy.context.view_layer.update()
    pr = arm.pose.bones["foot.R"]
    foot_w = arm.matrix_world @ pr.head.lerp(pr.tail, 0.5)
    cam2 = s1.make_cam("CAM_fin-check", (foot_w.x + 0.75, foot_w.y - 0.75, foot_w.z + 0.35),
                       tuple(foot_w), lens=70.0)
    bpy.context.scene.camera = cam2
    try:
        look.apply_look(scn, 1, above_water=False)
        out = os.path.join(STILLS, "nara-fin-check.png")
        look.render_still(scn, out, percent=50, samples=24)
        print("FIN CHECK:", out, os.path.exists(out))
    except Exception as exc:
        print("FIN CHECK GAGAL:", repr(exc))
    scn.frame_set(1)


# ===========================================================================
# 060 — close-up, lambaian telapak terbuka
# ===========================================================================

FLOAT_A = {
    "spine": (3, 0, 0),
    "chest": (2, 0, 0),
    "neck": (6, 0, 0),
    "head": (4, 0, -4),
    "shoulder.L": (0, 0, 0),
    "upper_arm.L": (-34, 0, 16),
    "fore_arm.L": (-30, 0, 0),
    "hand.L": (-10, 0, 0),
    "thumb_L": (-14, 0, 0),
    "index_L": (-6, 0, 0),
    "shoulder.R": (-6, 0, 0),
    "upper_arm.R": (-66, 0, -20),
    "fore_arm.R": (-84, 0, 0),
    "hand.R": (-14, 0, 22),
    "thumb_R": (0, 0, 0),
    "index_R": (0, 0, 0),
    "thigh.L": (14, 0, -3),
    "shin.L": (24, 0, 0),
    "thigh.R": (6, 0, 3),
    "shin.R": (20, 0, 0),
}

WAVE_A = dict(FLOAT_A)
WAVE_A.update({
    "upper_arm.R": (0, 118, -8),
    "fore_arm.R": (0, 62, 0),
    "hand.R": (0, 0, 0),
    "thumb_R": (0, 0, 18),
    "index_R": (4, 0, 0),
})


def build_060():
    v4.wipe()
    scn = setup("scene-1_shot-060_nara-ok", 72)
    v4.append_reef()
    arm = append_nara()
    for nm in ("PRP_divegear_fin_L", "PRP_divegear_fin_R"):
        ob = bpy.data.objects.get(nm)
        if ob is not None:
            bpy.data.objects.remove(ob, do_unlink=True)

    v4.prepare_rig(arm)
    arm.rotation_mode = "XYZ"
    arm.location = (0.0, 0.5, -2.30)
    arm.rotation_euler = (0.0, 0.0, math.radians(-16))

    base = dict(FLOAT_A)
    wave_out = dict(WAVE_A)
    wave_out.update({"fore_arm.R": (0, 52, 0), "hand.R": (0, 0, 12)})
    wave_in = dict(WAVE_A)
    wave_in.update({"fore_arm.R": (0, 74, 0), "hand.R": (0, 0, -10),
                    "index_R": (-6, 0, 0)})
    lower = dict(FLOAT_A)
    lower.update({"upper_arm.R": (-20, 40, -10), "fore_arm.R": (-30, 12, 0)})

    keys = [(1, base), (12, WAVE_A), (20, wave_out), (28, wave_in),
            (36, wave_out), (44, wave_in), (56, WAVE_A), (64, lower), (72, base)]
    bones = list(FLOAT_A.keys())

    # twist telapak: hadap kamera (depan karakter) — dihitung pada pose lambai
    v4.apply_pose(arm, WAVE_A)
    scn.frame_set(20)
    bpy.context.view_layer.update()
    fh, upn, her_right = s1.face_frame(arm)
    twist = hand_twist(arm, "R", fh)
    q_twist = Quaternion(Vector((0.0, 1.0, 0.0)), math.radians(twist))
    for f, pose in keys:
        scn.frame_set(f)
        v4.apply_pose(arm, pose)
        if f in (12, 20, 28, 36, 44, 56):
            pb = arm.pose.bones["hand.R"]
            pb.rotation_quaternion = pb.rotation_quaternion @ q_twist
        for name in bones:
            pbb = arm.pose.bones.get(name)
            if pbb is not None:
                pbb.keyframe_insert("rotation_quaternion", frame=f)
    name_action(arm, "CHR_act_nara_060_ok")
    scn.frame_set(1)
    bpy.context.view_layer.update()
    flex = report_flexion(arm, "060-f1")

    attach_mask_head(arm)

    s1.sun(scn, energy=3.4, angle=6.0, rot=(20, 0, 18), color=(0.86, 0.95, 1.0))
    lib.add_world("WLD_s1_060", "#0F5C63", strength=1.05)
    lib.add_fill(energy=90.0, size=3.0, loc=(1.2, -2.0, 0.4), target=(0.0, 0.0, 0.3))
    s1.underwater_fog(scn, size=90.0, top=6.0, bottom=-30.0)

    scn.frame_set(20)
    bpy.context.view_layer.update()
    fh, upn, her_right = s1.face_frame(arm)
    face_c = s1.bone_world(arm, "head", 0.56) + upn * 0.005
    hand_wave = arm.matrix_world @ arm.pose.bones["hand.R"].tail
    mid = face_c.lerp(hand_wave, 0.42) + upn * 0.02
    cam_loc = mid + fh * 2.40 + her_right * 0.08 + upn * 0.06
    cam = s1.make_cam("CAM_shot-060_cu", cam_loc, mid, lens=55.0, clip_end=60.0)
    v4.only_camera(cam)
    cam.data.dof.use_dof = True
    cam.data.dof.aperture_fstop = 4.5
    focus = s1.root_empty("EMPTY_focus-face", face_c)
    s1.adopt([focus], arm)
    cam.data.dof.focus_object = focus
    scn.frame_set(20)
    bpy.context.view_layer.update()
    hand = arm.matrix_world @ arm.pose.bones["hand.R"].head
    mask_c = bpy.data.objects["PRP_divegear_mask"].matrix_world.translation
    v4.ndc(cam, [face_c, hand, mask_c], ["wajah", "tangan-R", "masker"])
    scn.frame_set(1)

    size = v4.save_shot("060")
    v4.summary("060")
    log("ANIM", "s1-060 rig v003: lambaian telapak terbuka + jari, twist %.0f deg, "
                "masker+snorkel v002 (%d bytes)" % (twist, size))
    v4.still("060", 48, above_water=False)


# ===========================================================================
# 070 — setengah badan di air, tangan kanan di dek, masker di tangan kiri
# ===========================================================================

HANG = {
    "spine": (-4, 0, 0),
    "chest": (-2, 0, 0),
    "neck": (-8, 0, 0),
    "head": (-6, 0, 6),
    "shoulder.L": (-4, 0, 0),
    "shoulder.R": (4, 0, 0),
    "thigh.L": (18, 0, -4),
    "shin.L": (26, 0, 0),
    "foot.L": (-8, 0, 0),
    "thigh.R": (-10, 0, 4),
    "shin.R": (20, 0, 0),
    "foot.R": (-6, 0, 0),
}


def build_070():
    v4.wipe()
    scn = setup("scene-1_shot-070_nara-naik", 96)
    v4.append_asset(P_ISLAND, "ENV_island-detail")
    v4.make_patch((12.0, -40.0, 0.12))
    boat_objs = v4.append_asset(P_BOATS, "PRP_boats")
    ctl = s1.root_empty("CTL_boat-dive", (14.0, -35.0, -0.22))
    s1.adopt(boat_objs, ctl)
    ctl.rotation_euler = (0.0, 0.0, math.radians(6.0))
    bpy.context.view_layer.update()

    arm = append_nara()
    for nm in ("PRP_divegear_fin_L", "PRP_divegear_fin_R"):
        ob = bpy.data.objects.get(nm)
        if ob is not None:
            bpy.data.objects.remove(ob, do_unlink=True)

    # --- tempat berpijak: pinggang (hips z 0,92) di permukaan air z 0 -----
    root = Vector((13.10, -35.95, -0.921))
    arm.rotation_mode = "XYZ"
    arm.location = root
    arm.rotation_euler = (0.0, 0.0, math.radians(-8.0))
    v4.prepare_rig(arm)
    v4.apply_pose(arm, HANG)
    bpy.context.view_layer.update()

    # --- dek perahu: titik pegangan di bibir gunwale ---------------------
    grip_local = Vector((-1.00, -0.44, 0.87))
    grip = ctl.matrix_world @ grip_local
    print("    pegangan gunwale dunia:", [round(v, 3) for v in grip])
    wrist_target = grip + Vector((0.01, -0.07, 0.05))
    ik_arm(arm, "R", wrist_target, pole=(root.x - 0.9, root.y + 0.2, root.z + 0.5))
    aim_hand(arm, "R", Vector((0.05, 0.25, -1.0)))
    # telapak mencengkeram bibir perahu
    s1.rot_bone(arm.pose.bones["thumb_R"], -42.0, 0.0, 0.0)
    s1.rot_bone(arm.pose.bones["index_R"], -48.0, 0.0, 0.0)
    bpy.context.view_layer.update()

    hand_r_world = arm.matrix_world @ arm.pose.bones["hand.R"].head
    print("    wrist R ke pegangan: %.3f m" % (hand_r_world - grip).length)

    # --- tangan kiri memegang masker di depan dada ------------------------
    chest = s1.bone_world(arm, "chest", 0.5)
    fh, upn, her_right = s1.face_frame(arm)
    her_left = -her_right
    s1.rot_bone(arm.pose.bones["upper_arm.L"], -45.0, 0.0, 16.0)
    s1.rot_bone(arm.pose.bones["fore_arm.L"], -90.0, 0.0, 0.0)
    s1.rot_bone(arm.pose.bones["hand.L"], -6.0, 0.0, -6.0)
    s1.rot_bone(arm.pose.bones["thumb_L"], -30.0, 0.0, 0.0)
    s1.rot_bone(arm.pose.bones["index_L"], -34.0, 0.0, 0.0)
    bpy.context.view_layer.update()

    cam_loc = Vector((root.x - 1.05, root.y - 3.40, 0.32))
    cam_tgt = Vector((root.x - 0.02, root.y + 0.05, 0.44))
    mask = bpy.data.objects.get("PRP_divegear_mask")
    if mask is not None:
        hand_l = arm.matrix_world @ arm.pose.bones["hand.L"].head
        mask_pos = hand_l + fh * 0.075 + upn * 0.045
        to_cam = cam_loc - mask_pos
        yaw_cam = math.degrees(math.atan2(to_cam.x, -to_cam.y))
        print("    masker pos:", [round(v, 2) for v in mask_pos], "yaw", round(yaw_cam, 0))
        s1.attach_gear(mask, arm, "hand.L", mask_pos, yaw_cam, pitch_deg=-12.0)
    sn = bpy.data.objects.get("PRP_divegear_snorkel")
    if sn is not None:
        face_c = s1.bone_world(arm, "head", 0.56) + upn * 0.005
        mouth = face_c - upn * 0.058 + her_right * 0.048 + fh * 0.004
        s1.attach_gear(sn, arm, "head", mouth, s1.yaw_of(fh) + 6.0, roll_deg=-8.0)

    # kunci pose statis (pegangan tidak lepas)
    keys = list(HANG.keys()) + ["upper_arm.L", "fore_arm.L", "hand.L",
                                "upper_arm.R", "fore_arm.R", "hand.R",
                                "thumb_R", "index_R", "thumb_L", "index_L"]
    for pb in arm.pose.bones:
        if pb.name in keys:
            pb.keyframe_insert("rotation_quaternion", frame=1)
    arm.keyframe_insert("location", frame=1)
    arm.keyframe_insert("rotation_euler", frame=1)
    name_action(arm, "CHR_act_nara_070_naik")

    scn.frame_set(1)
    bpy.context.view_layer.update()
    hw = arm.matrix_world @ arm.pose.bones["hips"].head
    print("    pinggang Nara z = %.3f m" % hw.z)
    if mask is not None:
        hand_l = arm.matrix_world @ arm.pose.bones["hand.L"].head
        hand_r = arm.matrix_world @ arm.pose.bones["hand.R"].head
        mc = mask.matrix_world.translation
        print("    masker -> hand.L %.3f m | hand.R %.3f m | z %.2f"
              % ((mc - hand_l).length, (mc - hand_r).length, mc.z))

    s1.sun(scn, energy=4.2, angle=3.0, rot=(64, 0, 40), color=(1.0, 0.92, 0.78))
    lib.add_world("WLD_s1_070", "#E3EFEA", strength=1.0)

    head_c = s1.bone_world(arm, "head", 0.55)
    cam = s1.make_cam("CAM_shot-070_low", tuple(cam_loc), tuple(cam_tgt),
                      lens=42.0, clip_end=3000.0)
    v4.only_camera(cam)
    s1.key_cam(cam, [
        (1, tuple(cam_loc), tuple(cam_tgt)),
        (96, (cam_loc.x + 0.15, cam_loc.y + 0.18, cam_loc.z + 0.03),
         (cam_tgt.x + 0.05, cam_tgt.y, cam_tgt.z + 0.04)),
    ])
    bpy.context.view_layer.update()
    v4.ndc(cam, [head_c, (mask.matrix_world.translation if mask else head_c),
                 grip, (root.x, root.y, 0.0)],
           ["kepala", "masker", "dek", "air"])
    scn.frame_set(1)
    v4.ndc(cam, [head_c, (mask.matrix_world.translation if mask else head_c),
                 grip, (root.x, root.y, 0.0)],
           ["kepala", "masker", "dek", "air"])
    scn.frame_set(1)

    size = v4.save_shot("070")
    v4.summary("070")
    log("ANIM", "s1-070 re-stage: pinggang z 0, tangan kanan di gunwale, "
                "masker di tangan kiri sejak f1, kamera low angle (%d bytes)" % size)
    v4.still("070", 48, above_water=True)


BUILDERS = {"050": build_050, "060": build_060, "070": build_070}


def main(argv):
    args = argv[argv.index("--") + 1:] if "--" in argv else []
    if not args:
        print("pakai: -- <050|060|070>")
        return
    for key in args:
        if key not in BUILDERS:
            raise SystemExit("shot tidak dikenal: %s" % key)
        print("=== BUILD s1-%s ===" % key)
        BUILDERS[key]()


if __name__ == "__main__":
    main(sys.argv)






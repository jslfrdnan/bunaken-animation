# build-nara-rig.py — rig dasar Nara (blockout) untuk Warisan Bunaken.
#
# Dijalankan DI DALAM Blender lewat Blender MCP (live instance).
# Membuat file BARU assets/char/nara_rig.blend:
#   - append koleksi CHR_nara dari assets/char/nara.blend (tidak menyentuh file itu)
#   - armature humanoid dasar (hips, spine, neck, head, shoulder/upper/fore/hand,
#     thigh/shin/foot kiri-kanan) dengan automatic weights
#   - 2 pose uji: rest (T-pose bawaan model) + pose menyelam (lengan ke depan,
#     badan condong, kaki ke belakang) — pose menyelam dikunci jadi action
#     "CHR_act_nara_pose-swim" di frame 1
#   - render preview ke renders/stills/ (gitignored)
# Idempoten: aman dijalankan ulang dari file kosong.
#
# Batas: ini rig DASAR untuk unblock animasi. Rigging halus (wajah, jari,
# stretch & squash, control curves) tetap tugas Ciputra Lumi.

import bpy
import math
import mathutils
import os

ROOT = r"D:\Tugas Semester 5\Grafika Komputer\Project-Animasi"
SRC = os.path.join(ROOT, "assets", "char", "nara.blend")
DST = os.path.join(ROOT, "assets", "char", "nara_rig.blend")

# ---------------------------------------------------------------- helpers

def fresh_file():
    # CATATAN: jangan pakai bpy.ops.wm.read_factory_settings() di live session
    # Blender MCP — itu mematikan socket add-on ("Not connected to Blender").
    # Wipe manual di bawah setara dan aman.
    scn = bpy.context.scene
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for c in list(bpy.data.collections):
        if c is not scn.collection:
            bpy.data.collections.remove(c)
    for a in list(bpy.data.armatures):
        bpy.data.armatures.remove(a)
    for m in list(bpy.data.meshes):
        bpy.data.meshes.remove(m)
    for ma in list(bpy.data.materials):
        bpy.data.materials.remove(ma)
    for l in list(bpy.data.lights):
        bpy.data.lights.remove(l)
    for cam in list(bpy.data.cameras):
        bpy.data.cameras.remove(cam)
    for act in list(bpy.data.actions):
        bpy.data.actions.remove(act)
    scn.world = None
    for w in list(bpy.data.worlds):
        bpy.data.worlds.remove(w)

    try:
        scn.render.engine = "BLENDER_EEVEE"
    except TypeError as e:
        raise RuntimeError("engine EEVEE tidak tersedia: %s" % e)
    scn.render.resolution_x = 1920
    scn.render.resolution_y = 1080
    scn.render.fps = 24
    scn.view_settings.view_transform = "Standard"
    scn.frame_set(1)
    # world preview netral
    world = bpy.data.worlds.new("WLD_rig-preview")
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.18, 0.19, 0.21, 1.0)
    bg.inputs["Strength"].default_value = 1.0
    scn.world = world

def append_nara():
    # bersihkan sisa append sebelumnya (idempoten; koleksi hasil
    # libraries.load(link=False) bersifat lokal sehingga c.library None)
    for c in list(bpy.data.collections):
        if c is not bpy.context.scene.collection:
            bpy.data.collections.remove(c)
    for o in list(bpy.data.objects):
        if not o.users_collection:
            bpy.data.objects.remove(o)

    with bpy.data.libraries.load(SRC, link=False) as (src, dst):
        dst.collections = ["CHR_nara"]
    col = next((c for c in bpy.data.collections if c.name == "CHR_nara"), None)
    if col is None:
        raise RuntimeError("koleksi CHR_nara tidak ditemukan di nara.blend")
    bpy.context.scene.collection.children.link(col)
    # daftar part mesh
    parts = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    # buang objek kamera/lampu yang ikut ke-append (kalau ada)
    for o in list(bpy.context.scene.objects):
        if o.type in ("CAMERA", "LIGHT"):
            bpy.data.objects.remove(o, do_unlink=True)
    return parts

def bbox_world(obj):
    pts = [obj.matrix_world @ mathutils.Vector(c) for c in obj.bound_box]
    xs = [p.x for p in pts]; ys = [p.y for p in pts]; zs = [p.z for p in pts]
    return {
        "min": mathutils.Vector((min(xs), min(ys), min(zs))),
        "max": mathutils.Vector((max(xs), max(ys), max(zs))),
        "corners": pts,
    }

def center_of(parts, name):
    obj = next((o for o in parts if o.name == name), None)
    if obj is None:
        raise RuntimeError("part tidak ditemukan: %s" % name)
    bb = bbox_world(obj)
    return (bb["min"] + bb["max"]) * 0.5, bb

def farthest(corners, ref):
    best = corners[0]
    bestd = -1.0
    for c in corners:
        d = (c - ref).length_squared
        if d > bestd:
            bestd = d
            best = c
    return mathutils.Vector(best)

def closest(corners, ref):
    best = corners[0]
    bestd = float("inf")
    for c in corners:
        d = (c - ref).length_squared
        if d < bestd:
            bestd = d
            best = c
    return mathutils.Vector(best)

# ---------------------------------------------------------------- armature

def build_armature(parts):
    _, hips_bb = center_of(parts, "CHR_nara_hips")
    body_c, _ = center_of(parts, "CHR_nara_body")
    neck_c, _ = center_of(parts, "CHR_nara_neck")
    head_c, head_bb = center_of(parts, "CHR_nara_head")
    eye_l, _ = center_of(parts, "CHR_nara_eye_L")
    eye_r, _ = center_of(parts, "CHR_nara_eye_R")

    hips_c = (hips_bb["min"] + hips_bb["max"]) * 0.5
    head_top = head_bb["max"]

    # arah hadap dari posisi mata relatif kepala
    facing = ((eye_l + eye_r) * 0.5 - head_c)
    facing.z = 0.0
    if facing.length < 1e-4:
        facing = mathutils.Vector((0.0, -1.0, 0.0))
    facing.normalize()

    arm_data = bpy.data.armatures.new("CHR_nara_rig")
    arm_obj = bpy.data.objects.new("CHR_nara_rig", arm_data)
    bpy.context.scene.collection.objects.link(arm_obj)
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode="EDIT")
    eb = arm_data.edit_bones

    def bone(name, head, tail):
        b = eb.new(name)
        b.head = head
        b.tail = tail
        return b

    # tulang belakang
    bone("hips", hips_c, body_c)
    bone("spine", body_c, neck_c)
    bone("neck", neck_c, head_c)
    bone("head", head_c, mathutils.Vector((head_c.x, head_c.y, head_top.z)))

    side_parts = {}
    for side in ("L", "R"):
        sh_c, _ = center_of(parts, "CHR_nara_shoulder_%s" % side)
        ua_c, ua_bb = center_of(parts, "CHR_nara_upperarm_%s" % side)
        fa_c, fa_bb = center_of(parts, "CHR_nara_forearm_%s" % side)
        ha_c, ha_bb = center_of(parts, "CHR_nara_hand_%s" % side)
        th_c, th_bb = center_of(parts, "CHR_nara_thigh_%s" % side)
        shin_c, shin_bb = center_of(parts, "CHR_nara_shin_%s" % side)
        ft_c, ft_bb = center_of(parts, "CHR_nara_foot_%s" % side)

        elbow = farthest(ua_bb["corners"], sh_c)
        wrist = farthest(fa_bb["corners"], elbow)
        hand_tip = farthest(ha_bb["corners"], wrist)
        hip_top = farthest(th_bb["corners"], shin_c)      # ujung atas paha
        knee = closest(shin_bb["corners"], th_c)          # lutut
        ankle = farthest(shin_bb["corners"], th_c)        # pergelangan
        toe = farthest(ft_bb["corners"], ankle)
        heel = closest(ft_bb["corners"], ankle)

        bone("shoulder.%s" % side, neck_c, sh_c)
        bone("upper_arm.%s" % side, sh_c, elbow)
        bone("fore_arm.%s" % side, elbow, wrist)
        bone("hand.%s" % side, wrist, hand_tip)
        bone("thigh.%s" % side, hip_top, knee)
        bone("shin.%s" % side, knee, ankle)
        bone("foot.%s" % side, heel, toe)
        side_parts[side] = (sh_c, elbow, wrist, hand_tip, hip_top, knee, ankle, heel, toe)

    # hirarki
    eb["spine"].parent = eb["hips"]
    eb["neck"].parent = eb["spine"]
    eb["head"].parent = eb["neck"]
    for side in ("L", "R"):
        eb["shoulder.%s" % side].parent = eb["spine"]
        eb["upper_arm.%s" % side].parent = eb["shoulder.%s" % side]
        eb["fore_arm.%s" % side].parent = eb["upper_arm.%s" % side]
        eb["hand.%s" % side].parent = eb["fore_arm.%s" % side]
        eb["thigh.%s" % side].parent = eb["hips"]
        eb["shin.%s" % side].parent = eb["thigh.%s" % side]
        eb["foot.%s" % side].parent = eb["shin.%s" % side]

    bpy.ops.object.mode_set(mode="OBJECT")
    return arm_obj, facing

def parent_meshes(parts, arm_obj):
    """Parent SEMUA mesh per-objek (menghindari satu blok operator panjang
    yang bisa membuat live session MCP timeout). Return (n_auto, n_envelope)."""
    bpy.ops.object.mode_set(mode="OBJECT")
    n_auto = 0
    n_env = 0
    for o in parts:
        bpy.ops.object.select_all(action="DESELECT")
        o.select_set(True)
        arm_obj.select_set(True)
        bpy.context.view_layer.objects.active = arm_obj
        try:
            bpy.ops.object.parent_set(type="ARMATURE_AUTO")
            n_auto += 1
        except RuntimeError:
            try:
                bpy.ops.object.parent_set(type="ARMATURE_ENVELOPE")
                n_env += 1
            except RuntimeError:
                pass  # part gagal ter-parent, dilaporkan di bawah
    bpy.ops.object.select_all(action="DESELECT")
    skipped = [o.name for o in parts if not o.parent]
    return n_auto, n_env, skipped

# ---------------------------------------------------------------- pose uji

def pose_quat(pb, axis_world, angle):
    axis_local = pb.bone.matrix_local.to_3x3().inverted() @ axis_world
    axis_local.normalize()
    pb.rotation_mode = "QUATERNION"
    pb.rotation_quaternion = mathutils.Quaternion(axis_local, angle)

def world_tail(arm_obj, pb):
    return arm_obj.matrix_world @ pb.tail

def apply_swim_pose(arm_obj, facing):
    bpy.ops.object.mode_set(mode="POSE")
    pbs = arm_obj.pose.bones
    z_axis = mathutils.Vector((0, 0, 1))
    # sumbu horizontal tegak lurus facing: rotasi sekitar sumbu ini = pitch
    pitch_axis = mathutils.Vector((-facing.y, facing.x, 0.0))

    rest_hands = {side: world_tail(arm_obj, pbs["hand.%s" % side]).copy() for side in ("L", "R")}
    rest_feet = {side: world_tail(arm_obj, pbs["foot.%s" % side]).copy() for side in ("L", "R")}
    hips_tail = world_tail(arm_obj, pbs["hips"]).copy()

    # Blockout Nara arms-down (bukan T-pose): ayunkan lengan ke DEPAN
    # lewat rotasi sekitar pitch_axis di sendi bahu.
    for side in ("L", "R"):
        pose_quat(pbs["upper_arm.%s" % side], pitch_axis, -1.45)
        pose_quat(pbs["fore_arm.%s" % side], pitch_axis, 0.12)
        pose_quat(pbs["hand.%s" % side], pitch_axis, 0.0)

    # badan condong ke depan, kepala diangkat melihat ke depan
    pose_quat(pbs["spine"], pitch_axis, -0.30)
    pose_quat(pbs["neck"], pitch_axis, 0.45)
    pose_quat(pbs["head"], pitch_axis, 0.15)

    # kaki tertinggal ke belakang (ekstensi pinggul + tekuk lutut)
    for side in ("L", "R"):
        pose_quat(pbs["thigh.%s" % side], pitch_axis, 0.55)
        pose_quat(pbs["shin.%s" % side], pitch_axis, -0.40)
        pose_quat(pbs["foot.%s" % side], pitch_axis, 0.20)

    bpy.context.view_layer.update()

    # verifikasi numerik: tangan maju, kaki mundur
    def moved_ok(rest, now, want_forward):
        d = now - rest
        d.z = 0.0
        if d.length < 1e-4:
            return False
        return (d.dot(facing) > 0) == want_forward

    hands_ok = all(
        moved_ok(rest_hands[s], world_tail(arm_obj, pbs["hand.%s" % s]), True)
        for s in ("L", "R")
    )
    feet_ok = all(
        moved_ok(rest_feet[s], world_tail(arm_obj, pbs["foot.%s" % s]), False)
        for s in ("L", "R")
    )
    return hands_ok, feet_ok, rest_hands, rest_feet, hips_tail

def store_pose_action(arm_obj):
    bpy.ops.object.mode_set(mode="POSE")
    for pb in arm_obj.pose.bones:
        pb.keyframe_insert(data_path="rotation_quaternion", frame=1)
    bpy.ops.object.mode_set(mode="OBJECT")
    if arm_obj.animation_data and arm_obj.animation_data.action:
        arm_obj.animation_data.action.name = "CHR_act_nara_pose-swim"
        arm_obj.animation_data.action.use_fake_user = True

# ---------------------------------------------------------------- kamera & render

def camera_front(arm_obj, facing, head_c):
    scene = bpy.context.scene
    cam = bpy.data.objects.new("CAM_preview", bpy.data.cameras.new("CAM_preview"))
    scene.collection.objects.link(cam)
    cam.location = head_c + facing * 2.8 + mathutils.Vector((0, 0, 0.35))
    aim = head_c - mathutils.Vector((0, 0, 0.25))
    cam.rotation_euler = (aim - cam.location).to_track_quat("-Z", "Y").to_euler()
    scene.camera = cam
    return cam

def camera_side(arm_obj, facing, head_c):
    scene = bpy.context.scene
    cam = scene.camera
    side = mathutils.Vector((-facing.y, facing.x, 0.0))
    cam.location = head_c + side * 2.8 + mathutils.Vector((0, 0, 0.35))
    aim = head_c - mathutils.Vector((0, 0, 0.25))
    cam.rotation_euler = (aim - cam.location).to_track_quat("-Z", "Y").to_euler()

def lights():
    scene = bpy.context.scene
    key = bpy.data.objects.new("LGT_rig-key", bpy.data.lights.new("LGT_rig-key", "AREA"))
    key.location = (1.6, -2.2, 2.6)
    key.data.energy = 60.0
    scene.collection.objects.link(key)
    fill = bpy.data.objects.new("LGT_rig-fill", bpy.data.lights.new("LGT_rig-fill", "AREA"))
    fill.location = (-1.8, -1.4, 1.6)
    fill.data.energy = 25.0
    scene.collection.objects.link(fill)

def render(name):
    scene = bpy.context.scene
    scene.render.filepath = os.path.join(ROOT, "renders", "stills", name)
    scene.render.image_settings.file_format = "PNG"
    bpy.ops.render.render(write_still=True)
    print("RENDER OK:", name)

# ---------------------------------------------------------------- main

def main():
    fresh_file()
    parts = append_nara()
    print("PARTS:", len(parts))

    arm_obj, facing = build_armature(parts)
    n_auto, n_env, skipped = parent_meshes(parts, arm_obj)
    print("WEIGHTS: auto=%d envelope=%d skipped=%s" % (n_auto, n_env, skipped))
    print("FACING: %.2f %.2f" % (facing.x, facing.y))

    _, head_bb = center_of(parts, "CHR_nara_head")
    head_c = (head_bb["min"] + head_bb["max"]) * 0.5
    lights()
    camera_front(arm_obj, facing, head_c)

    zs = []
    for o in parts:
        bb = bbox_world(o)
        zs += [bb["min"].z, bb["max"].z]
    print("HEIGHT: %.2f m" % (max(zs) - min(zs)))
    print("BONES:", [b.name for b in arm_obj.data.bones])

    # pose uji 1: rest (T-pose bawaan model)
    render("nara-rig-pose-01-rest-front.png")

    # pose uji 2: menyelam
    hands_ok, feet_ok, rest_hands, rest_feet, hips_tail = apply_swim_pose(arm_obj, facing)
    print("VERIFY hands_ok=%s feet_ok=%s" % (hands_ok, feet_ok))
    if not (hands_ok and feet_ok):
        # flip arah dan coba sekali lagi
        bpy.ops.object.mode_set(mode="POSE")
        pitch_axis = mathutils.Vector((-facing.y, facing.x, 0.0))
        pbs = arm_obj.pose.bones
        if not hands_ok:
            for side in ("L", "R"):
                pose_quat(pbs["upper_arm.%s" % side], pitch_axis, 2.9)
                pose_quat(pbs["fore_arm.%s" % side], pitch_axis, -0.24)
        if not feet_ok:
            for side in ("L", "R"):
                pose_quat(pbs["thigh.%s" % side], pitch_axis, -1.1)
                pose_quat(pbs["shin.%s" % side], pitch_axis, 0.8)
                pose_quat(pbs["foot.%s" % side], pitch_axis, -0.4)
        bpy.context.view_layer.update()
        hands_ok = all(
            (world_tail(arm_obj, arm_obj.pose.bones["hand.%s" % s]) - rest_hands[s]).dot(facing) > 0
            for s in ("L", "R")
        )
        print("VERIFY retry hands_ok=%s" % hands_ok)

    render("nara-rig-pose-02-swim-front.png")
    camera_side(arm_obj, facing, head_c)
    render("nara-rig-pose-03-swim-side.png")

    store_pose_action(arm_obj)
    bpy.context.scene.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=DST)
    print("SAVED:", DST)
    print("DONE")

main()

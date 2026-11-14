"""
Rig renang untuk ikan cakalang — file BARU, file asal tidak diubah.

Hasil: assets/env/fish-cakalang-rig.blend
  scene "fish-cakalang-rig"
    koleksi ENV_fish                       (hasil append dari fish-cakalang.blend)
      +-- empty CTL_fish
      +-- CHR_cakalang_rig                 armature 7 bone (baru)
      +-- ENV_fish_cakalang                 badan + kepala + mata
      +-- ENV_fish_cakalang_dorsal          sirip punggung + finlet
      +-- ENV_fish_cakalang_tail            ekor bercabang
      +-- ENV_fish_cakalang_pectoral        sirip dada + perut + anal
    koleksi PREVIEW                        kamera + lampu + lantai

Sumber mesh: assets/env/fish-cakalang.blend (dibangun build-fish-cakalang.py),
di-append `link=False`. File asal TIDAK diubah — semua rig/animation ada di
file ini saja.

Orientasi mesh asal: hadap -Y (moncong di -Y), total 0,70 m, origin di tengah
badan, z 0 = garis tengah.

Rig: CHR_cakalang_rig — root, spine_01, spine_02, tail_01, tail_02,
pectoral_L, pectoral_R. Automatic weights per objek; root = kontrol
(use_deform False). Sirip dada (|x| > 0,04 di objek pectoral) dikaku-kan ke
bone pectoral supaya bisa mengepak; sirip perut & anal tetap ikut bobot auto.

Action: ENV_act_cakalang_swim, frame 1-32 loop (ekor ±10°, badan ±4°,
sirip dada ±6°).

Skrip IDEMPOTEN terhadap datablock miliknya dan MENYIMPAN file di akhir.
Tanpa open_mainfile / read_factory_settings / read_homefile; file aktif
dilepas lewat save_as_mainfile ke renders/tmp/_wipe.blend.
"""

import bpy
import os
import math
import datetime
from math import sin, pi, radians
from mathutils import Vector, Quaternion

HEX_GROUND = "#2E383A"
L = 0.70                  # panjang total cakalang
N_FRAMES = 32

BONES = [
    ("root", (0.0, 0.0, 0.0), (0.0, 0.0, 0.050), None, False),
    ("spine_01", (0.0, -0.280, 0.0), (0.0, -0.070, 0.0), "root", True),
    ("spine_02", (0.0, -0.070, 0.0), (0.0, 0.090, 0.0), "spine_01", True),
    ("tail_01", (0.0, 0.090, 0.0), (0.0, 0.240, 0.0), "spine_02", True),
    ("tail_02", (0.0, 0.240, 0.0), (0.0, 0.365, 0.0), "tail_01", True),
    ("pectoral_L", (0.045, -0.185, -0.008), (0.108, -0.135, -0.024), "spine_01", True),
    ("pectoral_R", (-0.045, -0.185, -0.008), (-0.108, -0.135, -0.024), "spine_01", True),
]

CHAIN = ["spine_01", "spine_02", "tail_01", "tail_02"]

SWIM = [
    ("tail_02", 10.0, (0, 0, 1), 0.0),
    ("tail_01", 10.0, (0, 0, 1), 55.0),
    ("spine_02", 4.0, (0, 0, 1), 150.0),
    ("spine_01", 2.0, (0, 0, 1), 215.0),
    ("pectoral_L", 6.0, (0, 1, 0), 0.0),
    ("pectoral_R", 6.0, (0, 1, 0), 180.0),
]

PARTS = ["ENV_fish_cakalang", "ENV_fish_cakalang_dorsal",
         "ENV_fish_cakalang_tail", "ENV_fish_cakalang_pectoral"]


# ---------------------------------------------------------------------------
# utilitas
# ---------------------------------------------------------------------------


def srgb(hexstr):
    h = hexstr.lstrip("#")
    values = [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]

    def to_linear(u):
        return u / 12.92 if u <= 0.04045 else ((u + 0.055) / 1.055) ** 2.4

    return tuple(to_linear(v) for v in values) + (1.0,)


def material(name, hexcol, roughness=0.7, spec=0.3):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    col = srgb(hexcol)
    mat.diffuse_color = col
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = col
    bsdf.inputs["Roughness"].default_value = roughness
    spec_in = bsdf.inputs.get("Specular IOR Level") or bsdf.inputs.get("Specular")
    if spec_in is not None:
        spec_in.default_value = spec
    return mat


def set_engine(scn):
    last = None
    for cand in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scn.render.engine = cand
            return cand
        except TypeError as err:
            last = err
    print("PERINGATAN: gagal set EEVEE:", last)
    return scn.render.engine


def repo_root():
    try:
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    except NameError:
        return os.getcwd()


def log(line):
    path = os.path.join(repo_root(), "renders", "logs", "modeling.log")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    stamp = datetime.datetime.now().strftime("%H:%M")
    with open(path, "a", encoding="utf-8") as fh:
        fh.write("[%s] %s\n" % (stamp, line))


def release_and_wipe():
    tmp = os.path.join(repo_root(), "renders", "tmp", "_wipe.blend")
    os.makedirs(os.path.dirname(tmp), exist_ok=True)
    try:
        bpy.context.preferences.filepaths.save_version = 0
    except Exception:
        pass
    if bpy.data.filepath and os.path.abspath(bpy.data.filepath) != os.path.abspath(tmp):
        bpy.ops.wm.save_as_mainfile(filepath=tmp)

    scn = bpy.context.scene
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for col in list(bpy.data.collections):
        bpy.data.collections.remove(col)
    for s in list(bpy.data.scenes):
        if s is not scn:
            bpy.data.scenes.remove(s)
    for blocks in (bpy.data.meshes, bpy.data.materials, bpy.data.cameras,
                   bpy.data.lights, bpy.data.armatures, bpy.data.actions,
                   bpy.data.curves, bpy.data.node_groups, bpy.data.worlds,
                   bpy.data.images):
        for b in list(blocks):
            try:
                blocks.remove(b)
            except Exception:
                pass
    return scn


def setup_scene(scn):
    scn.name = "fish-cakalang-rig"
    scn.render.resolution_x = 1920
    scn.render.resolution_y = 1080
    scn.render.resolution_percentage = 100
    scn.render.fps = 24
    scn.render.fps_base = 1.0
    scn.view_settings.view_transform = "Standard"
    try:
        scn.view_settings.look = "None"
    except TypeError:
        pass
    scn.frame_start = 1
    scn.frame_end = N_FRAMES
    scn.frame_set(1)
    engine = set_engine(scn)
    try:
        scn.eevee.taa_render_samples = 24
    except AttributeError:
        pass
    scn.render.image_settings.file_format = "PNG"
    scn.render.image_settings.color_mode = "RGBA"
    scn.render.film_transparent = False
    scn["asset"] = "fish-cakalang-rig"
    scn["asset_note"] = ("Cakalang 0,70 m + rig 7 bone + action renang 1-32. Mesh "
                         "di-append dari fish-cakalang.blend; file asal tidak diubah.")
    return scn, engine


def append_collection(path, name):
    with bpy.data.libraries.load(path, link=False) as (df, dt):
        if name not in df.collections:
            raise RuntimeError("%s tidak punya koleksi %s" % (path, name))
        dt.collections = [name]
    return bpy.data.collections.get(name)


def setup_preview(scn):
    prev = bpy.data.collections.new("PREVIEW")
    scn.collection.children.link(prev)

    ground_mat = material("MAT_preview_fish-ground", HEX_GROUND, roughness=0.95,
                          spec=0.1)
    gz = -0.62 * L
    s = 12.0 * L
    mesh = bpy.data.meshes.new("PREVIEW_ground")
    mesh.from_pydata([(-s, -s, gz), (s, -s, gz), (s, s, gz), (-s, s, gz)],
                     [], [(0, 1, 2, 3)])
    mesh.materials.append(ground_mat)
    mesh.update()
    prev.objects.link(bpy.data.objects.new("PREVIEW_ground", mesh))

    cam_data = bpy.data.cameras.new("CAM_preview")
    cam_data.lens = 55.0
    cam_data.clip_start = max(0.001, 0.006 * L)
    cam_data.clip_end = 100.0
    cam = bpy.data.objects.new("CAM_preview", cam_data)
    prev.objects.link(cam)
    cam.location = (0.92, -0.60, 0.19)
    cam.rotation_euler = (Vector((0, 0.005, 0)) - cam.location).normalized(
    ).to_track_quat("-Z", "Y").to_euler()
    scn.camera = cam

    key = bpy.data.objects.new("LGT_preview-key",
                               bpy.data.lights.new("LGT_preview-key", "SUN"))
    prev.objects.link(key)
    key.data.energy = 1.8
    key.data.angle = math.radians(20)
    key.rotation_euler = (math.radians(46), 0.0, math.radians(30))

    k = (L / 0.45) ** 2
    fill = bpy.data.objects.new("LGT_preview-fill",
                                bpy.data.lights.new("LGT_preview-fill", "AREA"))
    prev.objects.link(fill)
    fill.data.energy = 26.0 * k
    fill.data.size = 1.5 * L
    fill.location = (-1.8 * L, -1.5 * L, 1.1 * L)
    fill.rotation_euler = (Vector((0, 0, 0)) - fill.location).normalized(
    ).to_track_quat("-Z", "Y").to_euler()

    rim = bpy.data.objects.new("LGT_preview-rim",
                               bpy.data.lights.new("LGT_preview-rim", "AREA"))
    prev.objects.link(rim)
    rim.data.energy = 45.0 * k
    rim.data.size = 1.3 * L
    rim.location = (1.8 * L, 1.8 * L, 1.5 * L)
    rim.rotation_euler = (Vector((0, 0, 0)) - rim.location).normalized(
    ).to_track_quat("-Z", "Y").to_euler()

    world = bpy.data.worlds.new("WLD_fish-preview")
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.055, 0.068, 0.075, 1.0)
    bg.inputs["Strength"].default_value = 1.0
    scn.world = world
    return cam


# ---------------------------------------------------------------------------
# rig + bobot
# ---------------------------------------------------------------------------


def build_rig(col, ctl):
    arm_data = bpy.data.armatures.new("CHR_cakalang_rig")
    arm_obj = bpy.data.objects.new("CHR_cakalang_rig", arm_data)
    col.objects.link(arm_obj)
    if ctl is not None:
        arm_obj.parent = ctl
        arm_obj.matrix_parent_inverse = ctl.matrix_world.inverted()
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = arm_obj
    arm_obj.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    eb = arm_data.edit_bones
    for name, head, tail, parent, deform in BONES:
        b = eb.new(name)
        b.head = Vector(head)
        b.tail = Vector(tail)
        b.use_deform = deform
        if parent:
            b.parent = eb[parent]
    bpy.ops.object.mode_set(mode="OBJECT")
    arm_obj.show_in_front = True
    arm_obj["asset"] = "CHR_cakalang_rig"
    arm_obj["note"] = ("root kontrol (use_deform False), 6 bone deform; "
                       "hadap -Y, ekor di +Y")
    return arm_obj


def count_unweighted(obj):
    return sum(1 for v in obj.data.vertices
               if sum(g.weight for g in v.groups) < 1e-4)


def tent_weights(obj, chain):
    arm = obj.parent
    centers = []
    for name in chain:
        bone = arm.data.bones[name]
        centers.append((name, (bone.head_local.y + bone.tail_local.y) * 0.5))
    centers.sort(key=lambda c: c[1])
    groups = {}
    for name, _ in centers:
        groups[name] = obj.vertex_groups.get(name) or obj.vertex_groups.new(name=name)
    fixed = 0
    for v in obj.data.vertices:
        y = v.co.y
        if sum(g.weight for g in v.groups) > 1e-4:
            continue
        if y <= centers[0][1]:
            groups[centers[0][0]].add([v.index], 1.0, "REPLACE")
        elif y >= centers[-1][1]:
            groups[centers[-1][0]].add([v.index], 1.0, "REPLACE")
        else:
            for k in range(len(centers) - 1):
                y0 = centers[k][1]
                y1 = centers[k + 1][1]
                if y0 <= y <= y1:
                    t = (y - y0) / (y1 - y0)
                    groups[centers[k][0]].add([v.index], 1.0 - t, "REPLACE")
                    groups[centers[k + 1][0]].add([v.index], t, "REPLACE")
                    break
        fixed += 1
    return fixed


def bind_parts(parts, arm_obj):
    """Parent tiap mesh ke armature dengan automatic weights (per objek)."""
    bpy.ops.object.mode_set(mode="OBJECT")
    n_auto = 0
    n_env = 0
    failed = []
    bad_before = {}
    fixed_total = 0
    for obj in parts:
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        arm_obj.select_set(True)
        bpy.context.view_layer.objects.active = arm_obj
        try:
            bpy.ops.object.parent_set(type="ARMATURE_AUTO")
            n_auto += 1
        except RuntimeError as err:
            print("PERINGATAN auto weights gagal pada %s: %s" % (obj.name, err))
            try:
                bpy.ops.object.parent_set(type="ARMATURE_ENVELOPE")
                n_env += 1
            except RuntimeError:
                failed.append(obj.name)
                obj.parent = arm_obj
                obj.modifiers.new("Armature", "ARMATURE").object = arm_obj
        bad_before[obj.name] = count_unweighted(obj)
    bpy.ops.object.select_all(action="DESELECT")
    # fallback: isi bobot yang kosong dengan interpolasi antar bone
    for obj in parts:
        if count_unweighted(obj):
            fixed_total += tent_weights(obj, CHAIN)
    return n_auto, n_env, failed, bad_before, fixed_total


def assign_rigid_side(obj, bone_pos, bone_neg, threshold=0.04):
    """Sirip dada kaku ke bone pectoral berdasarkan tanda x."""
    vg_l = obj.vertex_groups.get(bone_pos) or obj.vertex_groups.new(name=bone_pos)
    vg_r = obj.vertex_groups.get(bone_neg) or obj.vertex_groups.new(name=bone_neg)
    idx_l, idx_r = [], []
    for v in obj.data.vertices:
        if v.co.x > threshold:
            idx_l.append(v.index)
        elif v.co.x < -threshold:
            idx_r.append(v.index)
    for other in obj.vertex_groups:
        if other.name not in (bone_pos, bone_neg):
            other.remove(idx_l + idx_r)
    vg_l.add(idx_l, 1.0, "REPLACE")
    vg_r.add(idx_r, 1.0, "REPLACE")
    return len(idx_l), len(idx_r)


# ---------------------------------------------------------------------------
# action renang
# ---------------------------------------------------------------------------


def action_fcurves(act):
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


def make_swim_action(arm_obj, act_name, n_frames, spec):
    bpy.ops.object.select_all(action="DESELECT")
    arm_obj.select_set(True)
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode="POSE")
    pbs = arm_obj.pose.bones
    for pb in pbs:
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)

    frames = list(range(1, n_frames + 2, 2))
    if frames[-1] != n_frames + 1:
        frames.append(n_frames + 1)
    n_keys = 0
    for f in frames:
        t = (f - 1) / float(n_frames)
        for bname, amp, axis, phase in spec:
            pb = pbs[bname]
            ang = radians(amp) * sin(2.0 * pi * t + radians(phase))
            ax = pb.bone.matrix_local.to_3x3().inverted() @ Vector(axis)
            ax.normalize()
            pb.rotation_quaternion = Quaternion(ax, ang)
            pb.keyframe_insert(data_path="rotation_quaternion", frame=f)
            n_keys += 1
    bpy.ops.object.mode_set(mode="OBJECT")

    ad = arm_obj.animation_data
    act = ad.action if ad else None
    if act is None:
        return None, 0, 0
    act.name = act_name
    act.use_fake_user = True
    try:
        act.use_frame_range = True
        act.frame_start = 1
        act.frame_end = n_frames
    except Exception:
        pass
    fcs = action_fcurves(act)
    for fc in fcs:
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"
    return act, n_keys, len(fcs)


def render_previews(shots):
    scn = bpy.context.scene
    cam = scn.camera
    out_dir = os.path.join(repo_root(), "renders", "stills")
    os.makedirs(out_dir, exist_ok=True)
    scn.render.resolution_percentage = 50
    paths = []
    for name, loc, tgt, lens, frame in shots:
        scn.frame_set(frame)
        cam.location = loc
        cam.data.lens = lens
        cam.rotation_euler = (Vector(tgt) - Vector(loc)).normalized().to_track_quat(
            "-Z", "Y").to_euler()
        path = os.path.join(out_dir, name + ".png")
        scn.render.filepath = path
        bpy.ops.render.render(write_still=True)
        paths.append(path)
        print("render ->", path)
    scn.render.resolution_percentage = 100
    scn.frame_set(1)
    return paths


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main():
    src = os.path.join(repo_root(), "assets", "env", "fish-cakalang.blend")
    if not os.path.exists(src):
        raise RuntimeError("file asal tidak ada: %s" % src)

    scn = release_and_wipe()
    scn, engine = setup_scene(scn)
    log("MCP - Blender siap; scene fish-cakalang-rig diset (EEVEE, 1920x1080, 24 fps, Standard)")

    col = append_collection(src, "ENV_fish")
    if col is None:
        raise RuntimeError("append koleksi ENV_fish gagal")
    scn.collection.children.link(col)
    ctl = bpy.data.objects.get("CTL_fish")

    parts = []
    for name in PARTS:
        obj = bpy.data.objects.get(name)
        if obj is None:
            raise RuntimeError("objek %s tidak ditemukan setelah append" % name)
        parts.append(obj)
    log("MODEL - append ENV_fish dari fish-cakalang.blend: %s"
        % ", ".join(o.name for o in parts))

    arm_obj = build_rig(col, ctl)
    n_auto, n_env, failed, bad_before, fixed = bind_parts(parts, arm_obj)
    n_l, n_r = assign_rigid_side(parts[3], "pectoral_L", "pectoral_R", 0.04)
    bad_after = {o.name: count_unweighted(o) for o in parts}
    log("RIG - CHR_cakalang_rig %d bone; auto %d/%d, envelope %d, gagal %s; "
        "tanpa bobot %s -> %s (fallback %d), sirip dada kaku L%d R%d"
        % (len(arm_obj.data.bones), n_auto, len(parts), n_env, failed or "-",
           bad_before, bad_after, fixed, n_l, n_r))

    act, n_keys, n_fc = make_swim_action(arm_obj, "ENV_act_cakalang_swim",
                                         N_FRAMES, SWIM)
    log("ANIM - ENV_act_cakalang_swim 1-%d loop: %d key, %d fcurve"
        % (N_FRAMES, n_keys, n_fc))

    setup_preview(scn)

    bpy.context.view_layer.update()
    xs, ys, zs = [], [], []
    for obj in parts:
        for c in obj.bound_box:
            p = obj.matrix_world @ Vector(c)
            xs.append(p.x)
            ys.append(p.y)
            zs.append(p.z)
    print("=== RINGKASAN fish-cakalang-rig ===")
    print("bagian:", [(o.name, len(o.data.vertices)) for o in parts])
    print("panjang=%.3f m lebar=%.3f tinggi=%.3f"
          % (max(ys) - min(ys), max(xs) - min(xs), max(zs) - min(zs)))
    print("bone:", [b.name for b in arm_obj.data.bones])
    print("bone deform:", [b.name for b in arm_obj.data.bones if b.use_deform])
    print("armature di koleksi:", [c.name for c in arm_obj.users_collection])
    print("action:", act.name if act else None,
          "range:", tuple(act.frame_range) if act else None)
    print("engine=%s vt=%s res=%dx%d fps=%d frame=%d"
          % (engine, scn.view_settings.view_transform, scn.render.resolution_x,
             scn.render.resolution_y, scn.render.fps, scn.frame_current))

    target = os.path.join(repo_root(), "assets", "env", "fish-cakalang-rig.blend")
    bpy.ops.wm.save_as_mainfile(filepath=target, check_existing=False)
    print("saved:", target, "%.1f KB" % (os.path.getsize(target) / 1024.0))
    log("MODEL - fish-cakalang-rig.blend disimpan (%.0f KB)"
        % (os.path.getsize(target) / 1024.0))

    shots = [
        ("cakalang-rig_preview-01", (1.43, -0.93, 0.30), (0.0, 0.005, 0.0),
         55.0, 6),
        ("cakalang-rig_preview-02", (-1.12, 1.03, 0.56), (0.0, 0.04, 0.0),
         55.0, 18),
    ]
    paths = render_previews(shots)
    log("VERIFY - cakalang-rig_preview-01 (frame 6) / -02 (frame 18) 50%%: %s"
        % ", ".join(os.path.basename(p) for p in paths))


if __name__ == "__main__":
    main()

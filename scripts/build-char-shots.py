"""
build-char-shots.py — tujuh shot karakter memakai rig baru
(`nara_rig_v002.blend`, `haris_rig_v001.blend`).

  s2-060  scene-2_shot-060_nara-protes_v001.blend      dua orang, dermaga pagi biru
  s2-080  scene-2_shot-080_haris-menjawab_v001.blend   close-up Haris, statis
  s3-040  scene-3_shot-040_konfrontasi_v001.blend      dua orang, sore hangat, push-in
  s3-060  scene-3_shot-060_haris-diam_v001.blend       close-up Haris, statis, hening
  s3-080  scene-3_shot-080_nara-rencana_v001.blend     medium Nara, statis
  s4-040  scene-4_shot-040_haris-keramba_v001.blend    Haris di keramba rumput laut
  s4-050  scene-4_shot-050_haris-pemandu_v001.blend    Haris pemandu, tracking halus

Helper umum diimpor dari `scripts/build-scene-4-shots.py` (wipe, setup_scene,
append_collection, material, make_plane, kamera, report, save_and_preview).

Cara pakai di Blender MCP (satu shot per eksekusi):
    ns = {"__name__": "__main__", "SHOT_TO_BUILD": "s2-060"}
    exec(compile(open(path).read(), path, "exec"), ns)

Aturan yang dipatuhi:
- Tidak memanggil open_mainfile / read_factory_settings / read_homefile.
- Data di-wipe manual; file aktif dilepas lewat renders/tmp/_wipe.blend.
- Aset di-APPEND (link=False). File aset tidak pernah disimpan.
- EEVEE, 1920x1080, 24 fps, view transform Standard, simpan di frame 1.
- Tanpa camera shake kecuali s2-060 (handheld sangat halus, di dermaga).
- Tanpa DOF ekstrem, tanpa tekstur image, tanpa pack, <50 MB.
- Rig 21 bone tanpa facial: ekspresi diganti bahasa tubuh + sudut kamera.
"""

import datetime
import importlib.util
import math
import os

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Matrix, Vector

ROOT = r"D:/Tugas Semester 5/Grafika Komputer/Project-Animasi"
ASSETS = ROOT + "/assets"
LOGPATH = ROOT + "/renders/logs/technical.log"

_spec = importlib.util.spec_from_file_location(
    "shot_lib", ROOT + "/scripts/build-scene-4-shots.py"
)
lib = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(lib)

PAL = lib.PAL
FRAMES = 96
DECK = 1.26          # tinggi permukaan dek dermaga (ENV_surface_pier-deck)
SUBJ_Y = -95.0       # posisi aksi di dermaga (dekat ujung, latar laut terbuka)
DECISIONS = []       # catatan kendala yang dilaporkan di akhir tiap shot


# ---------------------------------------------------------------------------
# utilitas
# ---------------------------------------------------------------------------


def wipe_all():
    """wipe() + lepas library yang tersisa.

    Append (link=False) di Blender 5.x meninggalkan datablock Library; selama
    library itu hidup, save_as_mainfile menolak menimpa file yang sama
    ("Cannot overwrite used library").
    """
    lib.wipe()
    for item in list(bpy.data.libraries):
        try:
            bpy.data.libraries.remove(item)
        except Exception as exc:
            print("  library dilewati:", exc)


def log(line):
    os.makedirs(os.path.dirname(LOGPATH), exist_ok=True)
    stamp = datetime.datetime.now().strftime("%H:%M")
    with open(LOGPATH, "a", encoding="utf-8") as fh:
        fh.write("[%s] %s\n" % (stamp, line))
    print("[log]", line)


def bezier():
    try:
        bpy.context.preferences.edit.keyframe_new_interpolation_type = "BEZIER"
    except Exception as exc:  # pragma: no cover
        print("tidak bisa set interpolasi:", exc)


def ensure_eevee(scn):
    sebelum = scn.render.engine
    for name in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scn.render.engine = name
            break
        except TypeError:
            continue
    try:
        scn.eevee.taa_render_samples = 24
    except Exception as exc:
        print("  taa_samples dilewati:", exc)
    scn.render.film_transparent = False
    print("  engine:", scn.render.engine, "(sebelum:", sebelum, ")")


def rot_bone(pb, rx=0.0, ry=0.0, rz=0.0, order="XYZ"):
    """Putar pose bone (derajat) pada sumbu ruang armature.

    Sumbu armature: X = kiri-kanan, Y = depan-belakang, Z = atas.
    Karakter menghadap -Y. Untuk bone yang menunjuk ke atas (spine/neck/head)
    +rx = menunduk; untuk bone yang menunjuk ke bawah (lengan/kaki) -rx =
    mengayun ke depan.
    """
    mx = Matrix.Rotation(math.radians(rx), 3, "X")
    my = Matrix.Rotation(math.radians(ry), 3, "Y")
    mz = Matrix.Rotation(math.radians(rz), 3, "Z")
    rot = (mz @ mx @ my) if order == "YXZ" else (mz @ my @ mx)
    rest = pb.bone.matrix_local.to_3x3()
    pb.rotation_mode = "QUATERNION"
    pb.rotation_quaternion = (rest.inverted() @ rot @ rest).to_quaternion()


def reset_pose(arm):
    for pb in arm.pose.bones:
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
        pb.location = (0.0, 0.0, 0.0)
        pb.scale = (1.0, 1.0, 1.0)


def apply_pose(arm, p):
    reset_pose(arm)
    for name, val in p.items():
        if len(val) >= 4:
            rot_bone(arm.pose.bones[name], val[0], val[1], val[2], val[3])
        else:
            rot_bone(arm.pose.bones[name], val[0], val[1], val[2])
    bpy.context.view_layer.update()


def key_pose(arm, frame, p, bones):
    bpy.context.scene.frame_set(frame)
    apply_pose(arm, p)
    for name in bones:
        arm.pose.bones[name].keyframe_insert("rotation_quaternion", frame=frame)


def pose(base, over):
    d = dict(base)
    d.update(over)
    return d


def mirror_arms(p):
    """Cerminkan pose kiri-kanan (L<->R, ry & rz dibalik).

    Dipakai kalau tokoh diputar 180 derajat relatif terhadap pose dasar,
    supaya gestur tetap berada di sisi yang menghadap kamera.
    """
    out = {}
    for key, val in p.items():
        if key.endswith(".L"):
            nk = key[:-2] + ".R"
        elif key.endswith(".R"):
            nk = key[:-2] + ".L"
        else:
            nk = key
        if len(val) >= 4:
            out[nk] = (val[0], -val[1], -val[2], val[3])
        else:
            out[nk] = (val[0], -val[1], -val[2])
    return out


def append_char(kind):
    """Append rig baru (bukan yang lama). Action uji dilepas, tidak dihapus."""
    if kind == "nara":
        path, coll = ASSETS + "/char/nara_rig_v002.blend", "CHR_nara"
    elif kind == "haris":
        path, coll = ASSETS + "/char/haris_rig_v001.blend", "CHR_haris"
    else:
        raise ValueError(kind)
    objs = lib.append_collection(path, coll)
    purged = lib.purge_lights_cameras(objs)
    if purged:
        print("  dibuang dari rig:", purged)
    objs = lib.live_objects(objs)
    # PENTING: armature dari file rig TIDAK berada di koleksi mana pun saat
    # di-append. Objek tanpa koleksi hilang saat .blend disimpan, jadi harus
    # dilink ke scene collection lebih dulu.
    for o in objs:
        try:
            colls = list(o.users_collection)
        except ReferenceError:
            continue
        if not colls:
            target = bpy.data.collections.get("CHR_%s" % kind)
            if target is None:
                target = bpy.context.scene.collection
            target.objects.link(o)
            print("  objek tanpa koleksi dilink ke", target.name, ":", o.name)
    arm = bpy.data.objects["CHR_%s_rig" % kind]
    if arm.animation_data and arm.animation_data.action:
        act = arm.animation_data.action
        arm.animation_data.action = None
        print("  action uji dilepas:", act.name)
    return arm, objs


def rename_action(arm, name):
    act = arm.animation_data.action if arm.animation_data else None
    if act is not None:
        act.name = name
        act.use_fake_user = True
        print("  ACTION:", act.name)
    return act


def key_cam_path(cam, keys):
    bezier()
    for frame, loc, target in keys:
        bpy.context.scene.frame_set(frame)
        cam.location = loc
        lib.look_at(cam, target)
        cam.keyframe_insert("location", frame=frame)
        cam.keyframe_insert("rotation_euler", frame=frame)


def key_arm_location(arm, keys):
    bezier()
    for frame, loc in keys:
        bpy.context.scene.frame_set(frame)
        arm.location = loc
        arm.keyframe_insert("location", frame=frame)


def ndc(cam, p):
    v = world_to_camera_view(bpy.context.scene, cam, p)
    return v.x, v.y, v.z


def bone_world(arm, name, tail=False):
    pb = arm.pose.bones[name]
    return arm.matrix_world @ (pb.tail if tail else pb.head)


def side_check(cam, left_arm, right_arm, tag):
    """Pastikan tokoh kiri benar-benar di kiri frame (ndc.x lebih kecil)."""
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()
    lx = ndc(cam, bone_world(left_arm, "head"))[0]
    rx = ndc(cam, bone_world(right_arm, "head"))[0]
    ok = lx < rx
    print("  SIDE %s: ndc kiri=%.3f kanan=%.3f -> %s"
          % (tag, lx, rx, "OK" if ok else "TERBALIK, kamera dicerminkan"))
    return ok


def frame_check(tag, cam, arms):
    bpy.context.scene.frame_set(48)
    bpy.context.view_layer.update()
    for arm in arms:
        for bone in ("head", "chest", "hips"):
            x, y, z = ndc(cam, bone_world(arm, bone))
            flag = "" if 0.02 < x < 0.98 and 0.02 < y < 0.98 else "  <-- DI LUAR FRAME"
            print("  FRAME %s %s.%s: x=%.3f y=%.3f z=%.2f%s"
                  % (tag, arm.name, bone, x, y, z, flag))
    bpy.context.scene.frame_set(1)


def hairline_check(tag, cam, arms):
    """Tinggi kepala di frame (untuk memastikan bukan close-up terpotong)."""
    for arm in arms:
        x, y, _ = ndc(cam, bone_world(arm, "head", tail=True))
        print("  HEAD-TOP %s: x=%.3f y=%.3f" % (tag, x, y))


def verify(tag, scn, arms, cam):
    print("=== VERIFY %s ===" % tag)
    print("  scene:", scn.name, "frames:", scn.frame_start, "-", scn.frame_end,
          "fps:", scn.render.fps, "engine:", scn.render.engine,
          "vt:", scn.view_settings.view_transform,
          "res:", scn.render.resolution_x, scn.render.resolution_y)
    print("  camera:", cam.name, "lens", cam.data.lens,
          "loc", tuple(round(v, 2) for v in cam.location))
    for arm in arms:
        act = arm.animation_data.action if arm.animation_data else None
        print("  %s action:" % arm.name, act.name if act else None,
              "range", tuple(round(v) for v in act.frame_range) if act else None)
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()
    for arm in arms:
        for n in ("head", "hand.L", "hand.R"):
            h = bone_world(arm, n)
            print("    %s %s world: (%.2f, %.2f, %.2f)"
                  % (arm.name, n, h.x, h.y, h.z))
    print("  objek mesh:", len([o for o in bpy.data.objects if o.type == "MESH"]),
          "total objek:", len(bpy.data.objects))


def finish(tag, filename, preview_frame, scn, arms, cam, logline):
    verify(tag, scn, arms, cam)
    frame_check(tag, cam, arms)
    hairline_check(tag, cam, arms)
    for note in DECISIONS:
        print("  CATATAN:", note)
    lib.report(tag, [o for o in bpy.data.objects if o.type == "MESH"], scn)
    lib.save_and_preview(tag, filename, preview_frame=preview_frame)
    log(logline)


# ---------------------------------------------------------------------------
# cahaya per scene
# ---------------------------------------------------------------------------


def tame_water():
    """Redam kilau cermin placeholder air (bukan aset final look dev).

    Hanya menyentuh salinan material di dalam file shot, bukan file aset.
    """
    mat = bpy.data.materials.get("MAT_water_placeholder")
    if mat is None or not mat.use_nodes:
        print("  MAT_water_placeholder tidak ada")
        return
    bsdf = next((n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf is None:
        return
    bsdf.inputs["Roughness"].default_value = 0.62
    spec = bsdf.inputs.get("Specular IOR Level") or bsdf.inputs.get("Specular")
    if spec is not None:
        spec.default_value = 0.12
    print("  kilau air direndam (roughness 0.62)")


def load_pier():
    pier = lib.append_collection(ASSETS + "/env/surface.blend", "ENV_surface")
    lib.purge_lights_cameras(pier)
    pier = lib.live_objects(pier)
    tame_water()
    print("  dermaga:", len(pier), "objek")
    return pier



def add_rope(name, p0, p1, radius=0.013, hexcol="#D9C9A8"):
    """Tali lurus sederhana (silinder) antara dua titik — dipakai shot keramba."""
    a, b = Vector(p0), Vector(p1)
    d = b - a
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=8, radius=radius, depth=d.length, location=(a + b) * 0.5
    )
    obj = bpy.context.active_object
    obj.name = name
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = d.normalized().to_track_quat("Z", "Y")
    obj.data.materials.append(lib.material("MAT_rope_hemp", hexcol, roughness=0.85))
    return obj


def light_dawn(sy=SUBJ_Y):
    """Scene 2 subuh: biru dingin, kontras tinggi, rim hangat tipis dari laut."""
    lib.add_world("WLD_s2", "#2A4A57", strength=1.05)
    sun = lib.add_sun(energy=3.6, angle_deg=5.0, rot=(71, 0, 12))
    sun.data.color = (1.0, 0.86, 0.76)
    key = lib.add_fill(energy=130.0, size=2.4, loc=(-2.1, sy + 2.6, 3.15),
                       target=(0.1, sy + 0.4, 2.62))
    key.data.color = (0.74, 0.86, 1.0)
    bounce = lib.add_fill(energy=60.0, size=2.0, loc=(1.6, sy + 0.6, 1.50),
                          target=(0.0, sy + 0.3, 2.40))
    bounce.data.color = (0.58, 0.74, 0.92)


def light_afternoon(sy=SUBJ_Y):
    """Scene 3 sore: satu sumber hangat rendah (+X), bayangan panjang."""
    lib.add_world("WLD_s3", "#243038", strength=0.55)
    sun = lib.add_sun(energy=3.6, angle_deg=3.0, rot=(79, 0, 100))
    sun.data.color = (1.0, 0.72, 0.46)
    key = lib.add_fill(energy=150.0, size=2.2, loc=(-2.0, sy + 2.5, 3.05),
                       target=(0.05, sy + 0.4, 2.60))
    key.data.color = (1.0, 0.86, 0.66)
    rim = lib.add_fill(energy=60.0, size=2.4, loc=(2.8, sy + 0.2, 3.30),
                       target=(0.0, sy + 0.2, 2.65))
    rim.data.color = (0.72, 0.86, 0.95)


def light_morning(sy=SUBJ_Y):
    """Scene 4 pagi: cerah, cahaya dari atas, saturasi kembali."""
    lib.add_world("WLD_s4", "#8FBDBB", strength=0.75)
    sun = lib.add_sun(energy=4.3, angle_deg=3.5, rot=(36, 0, 34))
    sun.data.color = (1.0, 0.94, 0.84)
    key = lib.add_fill(energy=280.0, size=3.4, loc=(-2.4, sy + 2.8, 4.20),
                       target=(0.0, sy + 0.4, 2.55))
    key.data.color = (1.0, 0.96, 0.88)
    rim = lib.add_fill(energy=70.0, size=2.6, loc=(2.6, sy + 0.3, 3.20),
                       target=(0.0, sy + 0.2, 2.60))
    rim.data.color = (0.78, 0.94, 0.98)


# ---------------------------------------------------------------------------
# s2-060 — Nara protes Haris di dermaga, pagi biru
# ---------------------------------------------------------------------------


def build_s2_060():
    wipe_all()
    scn = lib.setup_scene("scene-2_shot-060_nara-protes")
    ensure_eevee(scn)
    bezier()
    log("ANIM — mulai scene-2 shot 060 (Nara protes Haris, dermaga pagi biru)")

    load_pier()

    nara, _ = append_char("nara")
    nara.location = (0.66, SUBJ_Y, DECK)    # kanan dunia = kiri frame
    nara.rotation_euler = (0.0, 0.0, math.radians(-90.0))
    haris, _ = append_char("haris")
    haris.location = (-0.70, SUBJ_Y, DECK)
    haris.rotation_euler = (0.0, 0.0, math.radians(90.0))

    # Pose ditulis untuk tokoh menghadap -Y; Nara diputar 180 relatif ke Haris,
    # jadi pose-nya dicerminkan agar gestur tetap di sisi yang menghadap kamera.
    nbase = {
        "hips": (0, 0, 0),
        "spine": (4, 0, 0), "chest": (1, 0, 0), "neck": (1, 0, 0),
        "head": (-3, 0, 0),
        "shoulder.L": (0, -2, 0), "shoulder.R": (0, 2, 0),
        "upper_arm.L": (5, 6, 0), "fore_arm.L": (-16, 0, 4), "hand.L": (-4, 0, 0),
        "upper_arm.R": (-28, -12, 0), "fore_arm.R": (-86, 0, 10), "hand.R": (-10, 0, 0),
        "thigh.L": (-3, 0, 2), "shin.L": (4, 0, 0), "foot.L": (0, 0, 0),
        "thigh.R": (2, 0, -2), "shin.R": (2, 0, 0), "foot.R": (0, 0, 0),
    }
    nb = list(nbase.keys())
    key_pose(nara, 1, mirror_arms(pose(nbase, {"head": (-2, 0, 0)})), nb)
    key_pose(nara, 30, mirror_arms(pose(nbase, {
        "spine": (6, 0, 0), "head": (-7, 0, -2),
        "upper_arm.R": (-32, -13, 0), "fore_arm.R": (-92, 0, 14),
        "hips": (0, 0, -3),
    })), nb)
    key_pose(nara, 58, mirror_arms(pose(nbase, {
        "spine": (3, 0, 0), "head": (-1, 0, 0),
        "upper_arm.R": (-24, -11, 0), "fore_arm.R": (-78, 0, 8),
        "hips": (0, 0, 2),
    })), nb)
    key_pose(nara, 80, mirror_arms(pose(nbase, {
        "spine": (6, 0, 0), "head": (-6, 0, -3),
        "upper_arm.R": (-33, -13, 0), "fore_arm.R": (-88, 0, 12),
        "hips": (0, 0, -2),
    })), nb)
    key_pose(nara, 96, mirror_arms(pose(nbase, {
        "spine": (4, 0, 0), "head": (-3, 0, -1),
        "upper_arm.R": (-28, -12, 0), "fore_arm.R": (-84, 0, 10),
    })), nb)

    # Haris: bahu turun, kepala agak menunduk, tangan di sisi badan.
    hbase = {
        "hips": (0, 0, 0),
        "spine": (5, 0, 0), "chest": (2, 0, 0), "neck": (5, 0, 0),
        "head": (4, 0, 0),
        "shoulder.L": (-4, 0, 0), "shoulder.R": (-4, 0, 0),
        "upper_arm.L": (2, 7, 0), "fore_arm.L": (-14, 0, 4), "hand.L": (-2, 0, 0),
        "upper_arm.R": (2, -7, 0), "fore_arm.R": (-16, 0, -4), "hand.R": (-2, 0, 0),
        "thigh.L": (-2, 0, 2), "shin.L": (3, 0, 0), "foot.L": (0, 0, 0),
        "thigh.R": (2, 0, -2), "shin.R": (2, 0, 0), "foot.R": (0, 0, 0),
    }
    hb = list(hbase.keys())
    key_pose(haris, 1, pose(hbase, {"head": (3, 0, 2)}), hb)
    key_pose(haris, 34, pose(hbase, {
        "spine": (7, 0, 0), "head": (7, 0, -8),
        "upper_arm.L": (4, 7, 0), "fore_arm.L": (-18, 0, 4),
    }), hb)
    key_pose(haris, 62, pose(hbase, {"head": (3, 0, -2)}), hb)
    key_pose(haris, 82, pose(hbase, {
        "spine": (6, 0, 0), "head": (8, 0, -3),
    }), hb)
    key_pose(haris, 96, pose(hbase, {"head": (4, 0, 1)}), hb)

    light_dawn()

    # Handheld SANGAT halus: drift 4 mm sepanjang shot, bukan goyang.
    cam = lib.make_camera("CAM_shot-060", (-0.35, SUBJ_Y + 3.15, 2.58),
                          (0.02, SUBJ_Y, 2.60), lens=42.0)
    key_cam_path(cam, [
        (1, (-0.350, SUBJ_Y + 3.150, 2.580), (0.02, SUBJ_Y, 2.60)),
        (24, (-0.347, SUBJ_Y + 3.154, 2.577), (0.02, SUBJ_Y, 2.60)),
        (48, (-0.353, SUBJ_Y + 3.147, 2.583), (0.02, SUBJ_Y, 2.60)),
        (72, (-0.348, SUBJ_Y + 3.152, 2.579), (0.02, SUBJ_Y, 2.60)),
        (96, (-0.351, SUBJ_Y + 3.149, 2.581), (0.02, SUBJ_Y, 2.60)),
    ])
    side_check(cam, nara, haris, "s2-060")

    rename_action(nara, "CHR_act_nara_060_protes")
    rename_action(haris, "CHR_act_haris_060_jawab")
    DECISIONS.append("ekspresi wajah tidak bisa (rig tanpa facial) -> "
                     "bahasa tubuh + sudut kamera")
    finish("s2-060", "scene-2_shot-060_nara-protes_v001.blend", 30, scn,
           [nara, haris], cam,
           "ANIM — selesai scene-2 shot 060 (1-96, dermaga pagi biru, "
           "handheld 4 mm, action nara_060 + haris_060)")


# ---------------------------------------------------------------------------
# s2-080 — close-up Haris menjawab
# ---------------------------------------------------------------------------


def build_s2_080():
    wipe_all()
    scn = lib.setup_scene("scene-2_shot-080_haris-menjawab")
    ensure_eevee(scn)
    bezier()
    log("ANIM — mulai scene-2 shot 080 (close-up Haris menjawab)")

    load_pier()

    haris, _ = append_char("haris")
    haris.location = (-0.15, SUBJ_Y, DECK)
    haris.rotation_euler = (0.0, 0.0, math.radians(166.0))

    base = {
        "hips": (0, 0, 0),
        "spine": (5, 0, 0), "chest": (2, 0, 0), "neck": (6, 0, 0),
        "head": (3, 0, -3),
        "shoulder.L": (-5, 0, 0), "shoulder.R": (-5, 0, 0),
        "upper_arm.L": (3, 7, 0), "fore_arm.L": (-15, 0, 4), "hand.L": (-2, 0, 0),
        "upper_arm.R": (-32, -9, 0), "fore_arm.R": (-42, 0, 8), "hand.R": (-6, 0, 0),
        "thigh.L": (-2, 0, 2), "shin.L": (3, 0, 0), "foot.L": (0, 0, 0),
        "thigh.R": (2, 0, -2), "shin.R": (2, 0, 0), "foot.R": (0, 0, 0),
    }
    bones = list(base.keys())
    # Tangan mulai setinggi pinggang lalu turun; kepala menoleh sedikit.
    key_pose(haris, 1, pose(base, {
        "head": (3, 0, -2), "upper_arm.R": (-30, -9, 0), "fore_arm.R": (-40, 0, 8),
    }), bones)
    key_pose(haris, 20, pose(base, {
        "head": (5, 0, -9), "neck": (6, 0, -2),
        "upper_arm.R": (-34, -10, 0), "fore_arm.R": (-46, 0, 10),
    }), bones)
    key_pose(haris, 46, pose(base, {
        "head": (4, 0, -6), "spine": (6, 0, 0),
        "upper_arm.R": (-18, -8, 0), "fore_arm.R": (-26, 0, 6),
    }), bones)
    key_pose(haris, 70, pose(base, {
        "head": (6, 0, -3), "spine": (6, 0, 0),
        "upper_arm.R": (0, -7, 0), "fore_arm.R": (-14, 0, -2),
    }), bones)
    key_pose(haris, 96, pose(base, {
        "head": (4, 0, -4), "spine": (5, 0, 0),
        "upper_arm.R": (1, -7, 0), "fore_arm.R": (-12, 0, -2),
    }), bones)

    # Napas: 4 mm naik-turun lewat objek armature (bukan scale).
    key_arm_location(haris, [
        (1, (-0.15, SUBJ_Y, DECK)),
        (30, (-0.15, SUBJ_Y, DECK + 0.004)),
        (60, (-0.15, SUBJ_Y, DECK)),
        (96, (-0.15, SUBJ_Y, DECK + 0.002)),
    ])

    light_dawn()
    key = lib.add_fill(energy=55.0, size=1.2, loc=(-1.05, SUBJ_Y + 1.65, 3.00),
                       target=(-0.15, SUBJ_Y, 2.82))
    key.data.color = (0.88, 0.93, 1.0)

    cam = lib.make_camera("CAM_shot-080", (0.08, SUBJ_Y + 2.15, 2.80),
                          (-0.15, SUBJ_Y, 2.80), lens=85.0)
    cam.data.dof.use_dof = False  # tanpa DOF ekstrem

    rename_action(haris, "CHR_act_haris_080_menjawab")
    DECISIONS.append("close-up tanpa facial: lelah disampaikan lewat bahu turun, "
                     "kepala menunduk, tangan turun")
    finish("s2-080", "scene-2_shot-080_haris-menjawab_v001.blend", 48, scn,
           [haris], cam,
           "ANIM — selesai scene-2 shot 080 (1-96, close-up statis 85mm, "
           "action haris_080_menjawab)")


# ---------------------------------------------------------------------------
# s3-040 — konfrontasi, dermaga sore, push-in kecil
# ---------------------------------------------------------------------------


def build_s3_040():
    wipe_all()
    scn = lib.setup_scene("scene-3_shot-040_konfrontasi")
    ensure_eevee(scn)
    bezier()
    log("ANIM — mulai scene-3 shot 040 (konfrontasi Nara-Haris, sore)")

    load_pier()

    nara, _ = append_char("nara")
    nara.location = (0.70, SUBJ_Y, DECK)    # kanan dunia = kiri frame
    nara.rotation_euler = (0.0, 0.0, math.radians(-90.0))
    haris, _ = append_char("haris")
    haris.location = (-0.72, SUBJ_Y, DECK)
    haris.rotation_euler = (0.0, 0.0, math.radians(90.0))

    nbase = {
        "hips": (0, 0, 0),
        "spine": (3, 0, 0), "chest": (-2, 0, 0), "neck": (0, 0, 0),
        "head": (-5, 0, 0),
        "shoulder.L": (0, -2, 0), "shoulder.R": (0, 2, 0),
        "upper_arm.L": (4, 6, 0), "fore_arm.L": (-15, 0, 4), "hand.L": (-4, 0, 0),
        "upper_arm.R": (-52, -14, 0), "fore_arm.R": (-58, 0, 8), "hand.R": (-6, 0, 0),
        "thigh.L": (-3, 0, 2), "shin.L": (4, 0, 0), "foot.L": (0, 0, 0),
        "thigh.R": (2, 0, -2), "shin.R": (2, 0, 0), "foot.R": (0, 0, 0),
    }
    nb = list(nbase.keys())
    key_pose(nara, 1, mirror_arms(pose(nbase, {"head": (-4, 0, 0), "spine": (2, 0, 0)})), nb)
    key_pose(nara, 34, mirror_arms(pose(nbase, {
        "spine": (5, 0, 0), "head": (-7, 0, -3),
        "upper_arm.R": (-57, -15, 0), "fore_arm.R": (-49, 0, 10),
    })), nb)
    key_pose(nara, 66, mirror_arms(pose(nbase, {
        "spine": (4, 0, 0), "head": (-5, 0, -1),
        "upper_arm.R": (-50, -13, 0), "fore_arm.R": (-61, 0, 8),
    })), nb)
    key_pose(nara, 96, mirror_arms(pose(nbase, {
        "spine": (3, 0, 0), "head": (-6, 0, -2),
        "upper_arm.R": (-54, -14, 0), "fore_arm.R": (-56, 0, 9),
    })), nb)

    # Haris bertahan: tangan terlipat rendah di depan perut, kepala menunduk.
    hbase = {
        "hips": (0, 0, 0),
        "spine": (6, 0, 0), "chest": (2, 0, 0), "neck": (6, 0, 0),
        "head": (6, 0, 0),
        "shoulder.L": (-5, 0, 0), "shoulder.R": (-5, 0, 0),
        "upper_arm.L": (1, 8, 0), "fore_arm.L": (-24, 0, 6), "hand.L": (-4, 0, 0),
        "upper_arm.R": (1, -8, 0), "fore_arm.R": (-26, 0, -6), "hand.R": (-4, 0, 0),
        "thigh.L": (-2, 0, 2), "shin.L": (3, 0, 0), "foot.L": (0, 0, 0),
        "thigh.R": (2, 0, -2), "shin.R": (2, 0, 0), "foot.R": (0, 0, 0),
    }
    hb = list(hbase.keys())
    key_pose(haris, 1, pose(hbase, {"head": (5, 0, 2)}), hb)
    key_pose(haris, 38, pose(hbase, {
        "head": (7, 0, -5), "spine": (7, 0, 0),
        "fore_arm.L": (-28, 0, 6), "fore_arm.R": (-30, 0, -6),
    }), hb)
    key_pose(haris, 70, pose(hbase, {"head": (6, 0, -2)}), hb)
    key_pose(haris, 96, pose(hbase, {"head": (8, 0, -4), "spine": (6, 0, 0)}), hb)

    light_afternoon()
    key = lib.add_fill(energy=90.0, size=2.6, loc=(-2.2, SUBJ_Y + 2.4, 3.6),
                       target=(0.0, SUBJ_Y, 2.5))
    key.data.color = (1.0, 0.86, 0.66)

    cam = lib.make_camera("CAM_shot-040", (-0.30, SUBJ_Y + 2.95, 2.58),
                          (0.0, SUBJ_Y, 2.60), lens=42.0)
    keys = [
        (1, (-0.30, SUBJ_Y + 2.95, 2.58), (0.0, SUBJ_Y, 2.60)),
        (96, (-0.27, SUBJ_Y + 2.61, 2.565), (0.0, SUBJ_Y, 2.60)),
    ]
    key_cam_path(cam, keys)
    side_check(cam, nara, haris, "s3-040")

    rename_action(nara, "CHR_act_nara_040_konfrontasi")
    rename_action(haris, "CHR_act_haris_040_bertahan")
    DECISIONS.append("push-in kamera 0,34 m (statis selain itu), "
                     "tanpa handheld di shot ini")
    finish("s3-040", "scene-3_shot-040_konfrontasi_v001.blend", 60, scn,
           [nara, haris], cam,
           "ANIM — selesai scene-3 shot 040 (1-96, dua orang sore hangat, "
           "push-in 0,34 m)")


# ---------------------------------------------------------------------------
# s3-060 — Haris diam (close-up, hening)
# ---------------------------------------------------------------------------


def build_s3_060():
    wipe_all()
    scn = lib.setup_scene("scene-3_shot-060_haris-diam")
    ensure_eevee(scn)
    bezier()
    log("ANIM — mulai scene-3 shot 060 (Haris diam, close-up hening)")

    load_pier()

    haris, _ = append_char("haris")
    haris.location = (0.0, SUBJ_Y, DECK)
    haris.rotation_euler = (0.0, 0.0, math.radians(172.0))

    base = {
        "hips": (0, 0, 0),
        "spine": (7, 0, 0), "chest": (3, 0, 0), "neck": (7, 0, 0),
        "head": (6, 0, -2),
        "shoulder.L": (-7, 0, 0), "shoulder.R": (-7, 0, 0),
        "upper_arm.L": (3, 7, 0), "fore_arm.L": (-16, 0, 4), "hand.L": (-2, 0, 0),
        "upper_arm.R": (3, -7, 0), "fore_arm.R": (-14, 0, -4), "hand.R": (-2, 0, 0),
        "thigh.L": (-2, 0, 2), "shin.L": (3, 0, 0), "foot.L": (0, 0, 0),
        "thigh.R": (2, 0, -2), "shin.R": (2, 0, 0), "foot.R": (0, 0, 0),
    }
    bones = list(base.keys())
    # Hanya napas + mata (lewat tolehan mikro). Tidak ada gestur membela diri.
    key_pose(haris, 1, pose(base, {
        "spine": (7, 0, 0), "chest": (3, 0, 0), "head": (6, 0, -2),
        "shoulder.L": (-7, 0, 0), "shoulder.R": (-7, 0, 0),
    }), bones)
    key_pose(haris, 26, pose(base, {
        "spine": (7.8, 0, 0), "chest": (3.6, 0, 0), "head": (6.6, 0, -3.6),
        "shoulder.L": (-8, 0, 0), "shoulder.R": (-8, 0, 0),
        "neck": (7.4, 0, -1),
    }), bones)
    key_pose(haris, 54, pose(base, {
        "spine": (6.8, 0, 0), "chest": (2.8, 0, 0), "head": (5.4, 0, -1.2),
        "shoulder.L": (-6.4, 0, 0), "shoulder.R": (-6.4, 0, 0),
    }), bones)
    key_pose(haris, 78, pose(base, {
        "spine": (7.6, 0, 0), "chest": (3.4, 0, 0), "head": (6.4, 0, -4.4),
        "shoulder.L": (-7.8, 0, 0), "shoulder.R": (-7.8, 0, 0),
        "neck": (7.2, 0, -1.6),
    }), bones)
    key_pose(haris, 96, pose(base, {
        "spine": (7.2, 0, 0), "chest": (3.2, 0, 0), "head": (6.2, 0, -3.0),
        "shoulder.L": (-7.2, 0, 0), "shoulder.R": (-7.2, 0, 0),
    }), bones)

    light_afternoon()
    key = lib.add_fill(energy=55.0, size=1.2, loc=(-1.05, SUBJ_Y + 1.70, 3.00),
                       target=(0.0, SUBJ_Y, 2.76))
    key.data.color = (1.0, 0.86, 0.66)

    # Statis penuh: satu kunci kamera saja, tanpa gerak.
    cam = lib.make_camera("CAM_shot-060", (0.18, SUBJ_Y + 2.15, 2.78),
                          (0.0, SUBJ_Y, 2.78), lens=85.0)
    cam.data.dof.use_dof = False

    rename_action(haris, "CHR_act_haris_060_diam")
    DECISIONS.append("kamera statis penuh (tanpa keyframe gerak)")
    DECISIONS.append("mata tidak bisa dianimasikan (mesh mata menempel ke bone "
                     "head) -> diam diganti napas + tolehan mikro 2-4 derajat")
    finish("s3-060", "scene-3_shot-060_haris-diam_v001.blend", 48, scn,
           [haris], cam,
           "ANIM — selesai scene-3 shot 060 (1-96, close-up statis 85mm, "
           "napas + tolehan mikro, action haris_060_diam)")


# ---------------------------------------------------------------------------
# s3-080 — medium Nara mengubah rencana
# ---------------------------------------------------------------------------


def build_s3_080():
    wipe_all()
    scn = lib.setup_scene("scene-3_shot-080_nara-rencana")
    ensure_eevee(scn)
    bezier()
    log("ANIM — mulai scene-3 shot 080 (Nara mengubah rencana)")

    load_pier()

    nara, _ = append_char("nara")
    nara.location = (0.0, SUBJ_Y, DECK)
    nara.rotation_euler = (0.0, 0.0, math.radians(196.0))

    base = {
        "hips": (0, 0, 0),
        "spine": (1, 0, 0), "chest": (-3, 0, 0), "neck": (0, 0, 0),
        "head": (-4, 0, 0),
        "shoulder.L": (0, -2, 0), "shoulder.R": (0, 2, 0),
        "upper_arm.L": (3, 6, 0), "fore_arm.L": (-14, 0, 4), "hand.L": (-4, 0, 0),
        "upper_arm.R": (-26, -38, 0), "fore_arm.R": (-46, 0, 8), "hand.R": (-10, 0, 0),
        "thigh.L": (-3, 0, 2), "shin.L": (4, 0, 0), "foot.L": (0, 0, 0),
        "thigh.R": (2, 0, -2), "shin.R": (2, 0, 0), "foot.R": (0, 0, 0),
    }
    bones = list(base.keys())
    key_pose(nara, 1, pose(base, {
        "head": (-3, 0, 0), "upper_arm.R": (-22, -34, 0), "fore_arm.R": (-40, 0, 8),
    }), bones)
    # Satu gerakan tangan kecil: telapak terbuka, tegas, lalu turun.
    key_pose(nara, 30, pose(base, {
        "spine": (2, 0, 0), "head": (-6, 0, -2),
        "upper_arm.R": (-32, -44, 0), "fore_arm.R": (-56, 0, 12),
        "hand.R": (-16, 0, 0),
    }), bones)
    key_pose(nara, 52, pose(base, {
        "spine": (3, 0, 0), "head": (-5, 0, -3),
        "upper_arm.R": (-30, -42, 0), "fore_arm.R": (-44, 0, 14),
        "hand.R": (-20, 0, 0),
    }), bones)
    key_pose(nara, 76, pose(base, {
        "spine": (2, 0, 0), "head": (-4, 0, -1),
        "upper_arm.R": (-24, -36, 0), "fore_arm.R": (-48, 0, 10),
    }), bones)
    key_pose(nara, 96, pose(base, {
        "spine": (2, 0, 0), "head": (-5, 0, -2),
        "upper_arm.R": (-22, -35, 0), "fore_arm.R": (-46, 0, 9),
    }), bones)

    key_arm_location(nara, [
        (1, (0.0, SUBJ_Y, DECK)),
        (34, (0.0, SUBJ_Y, DECK + 0.004)),
        (70, (0.0, SUBJ_Y, DECK)),
        (96, (0.0, SUBJ_Y, DECK + 0.002)),
    ])

    light_afternoon()
    key = lib.add_fill(energy=85.0, size=1.6, loc=(-1.50, SUBJ_Y + 1.70, 3.10),
                       target=(0.0, SUBJ_Y, 2.60))
    key.data.color = (1.0, 0.86, 0.68)

    cam = lib.make_camera("CAM_shot-080", (0.45, SUBJ_Y + 2.30, 2.58),
                          (0.0, SUBJ_Y, 2.60), lens=55.0)
    cam.data.dof.use_dof = False

    rename_action(nara, "CHR_act_nara_080_rencana")
    DECISIONS.append("kamera statis; ketegasan lewat dagu naik + satu gestur "
                     "tangan, bukan ekspresi wajah")
    finish("s3-080", "scene-3_shot-080_nara-rencana_v001.blend", 40, scn,
           [nara], cam,
           "ANIM — selesai scene-3 shot 080 (1-96, medium statis 55mm, "
           "action nara_080_rencana)")


# ---------------------------------------------------------------------------
# s4-040 — Haris bekerja di keramba rumput laut
# ---------------------------------------------------------------------------


def build_s4_040():
    wipe_all()
    scn = lib.setup_scene("scene-4_shot-040_haris-keramba")
    ensure_eevee(scn)
    bezier()
    log("ANIM — mulai scene-4 shot 040 (Haris bekerja di keramba rumput laut)")

    sea = lib.material("MAT_sea_surface", "#15807A", roughness=0.34)
    lib.make_plane("ENV_sea", 4000.0, 0.0, sea)

    farm = lib.append_collection(ASSETS + "/env/seaweed-farm.blend",
                                 "ENV_seaweed-farm")
    lib.purge_lights_cameras(farm)
    farm = lib.live_objects(farm)
    for obj in farm:
        obj.location = (0.10, -0.90, 0.0)
        obj.rotation_euler = (0.0, 0.0, math.radians(4.0))
    print("  keramba:", [o.name for o in farm])

    # gear (jaring, keranjang) tidak dipakai: di keramba tidak ada platform
    # untuk meletakkannya, jadi akan terlihat mengapung.

    haris, _ = append_char("haris")
    haris.location = (0.0, -2.90, -0.48)    # mengarungi air setinggi paha
    haris.rotation_euler = (0.0, 0.0, math.radians(0.0))

    # Membungkuk ke arah tali/tanaman, kedua tangan bekerja di depan perut.
    base = {
        "hips": (2, 0, 0),
        "spine": (16, 0, 0), "chest": (6, 0, 0), "neck": (6, 0, 0),
        "head": (12, 0, 0),
        "shoulder.L": (-8, 0, 0), "shoulder.R": (-8, 0, 0),
        "upper_arm.L": (-36, 12, 0), "fore_arm.L": (-52, 0, 10), "hand.L": (-10, 0, 0),
        "upper_arm.R": (-34, -12, 0), "fore_arm.R": (-50, 0, -10), "hand.R": (-10, 0, 0),
        "thigh.L": (-6, 0, 3), "shin.L": (8, 0, 0), "foot.L": (-2, 0, 0),
        "thigh.R": (-4, 0, -3), "shin.R": (7, 0, 0), "foot.R": (-1, 0, 0),
    }
    bones = list(base.keys())
    # Dua tangan bekerja bergantian di tali; badan ikut bergoyang sedikit.
    key_pose(haris, 1, pose(base, {
        "fore_arm.R": (-46, 0, -10), "hand.R": (-6, 0, 0),
        "fore_arm.L": (-56, 0, 10), "hand.L": (-14, 0, 0),
    }), bones)
    key_pose(haris, 24, pose(base, {
        "spine": (18, 0, 0), "head": (14, 0, -3),
        "fore_arm.R": (-58, 0, -12), "hand.R": (-16, 0, 0),
        "fore_arm.L": (-44, 0, 8), "hand.L": (-6, 0, 0),
    }), bones)
    key_pose(haris, 48, pose(base, {
        "spine": (15, 0, 0), "head": (11, 0, 2),
        "fore_arm.R": (-48, 0, -9), "hand.R": (-8, 0, 0),
        "fore_arm.L": (-56, 0, 11), "hand.L": (-14, 0, 0),
    }), bones)
    key_pose(haris, 72, pose(base, {
        "spine": (18, 0, 0), "head": (14, 0, -2),
        "fore_arm.R": (-58, 0, -12), "hand.R": (-16, 0, 0),
        "fore_arm.L": (-44, 0, 8), "hand.L": (-6, 0, 0),
    }), bones)
    key_pose(haris, 96, pose(base, {
        "spine": (16, 0, 0), "head": (12, 0, 0),
        "fore_arm.R": (-50, 0, -10), "hand.R": (-10, 0, 0),
        "fore_arm.L": (-52, 0, 10), "hand.L": (-10, 0, 0),
    }), bones)

    light_morning(-2.9)
    key = lib.add_fill(energy=150.0, size=2.0, loc=(2.60, -5.20, 2.20),
                       target=(0.0, -3.20, 1.00))
    key.data.color = (1.0, 0.96, 0.86)

    cam = lib.make_camera("CAM_shot-040", (2.20, -5.20, 1.05),
                          (0.0, -3.10, 0.82), lens=40.0)
    cam.data.dof.use_dof = False

    # Tali dari palang keramba ke kedua tangan (subjek sedang mengikat rumput).
    scn.frame_set(1)
    apply_pose(haris, pose(base, {
        "fore_arm.R": (-46, 0, -10), "hand.R": (-6, 0, 0),
        "fore_arm.L": (-56, 0, 10), "hand.L": (-14, 0, 0),
    }))
    for side in ("hand.L", "hand.R"):
        h = bone_world(haris, side)
        add_rope("PRP_rope-" + side.replace(".", "-"),
                 (h.x, -2.42, 1.16), (h.x, h.y, h.z))
        print("  tali", side, "->", tuple(round(v, 2) for v in h))

    rename_action(haris, "CHR_act_haris_040_keramba")
    DECISIONS.append("kamera statis; pekerjaan tangan dibaca dari gerak "
                     "lengan bawah bergantian")
    finish("s4-040", "scene-4_shot-040_haris-keramba_v001.blend", 36, scn,
           [haris], cam,
           "ANIM — selesai scene-4 shot 040 (1-96, medium statis 40mm, "
           "tangan bekerja, action haris_040_keramba)")


# ---------------------------------------------------------------------------
# s4-050 — Haris pemandu wisata, tracking halus
# ---------------------------------------------------------------------------


def build_s4_050():
    wipe_all()
    scn = lib.setup_scene("scene-4_shot-050_haris-pemandu")
    ensure_eevee(scn)
    bezier()
    log("ANIM — mulai scene-4 shot 050 (Haris pemandu, tracking halus)")

    load_pier()

    haris, _ = append_char("haris")
    haris.rotation_euler = (0.0, 0.0, math.radians(-6.0))
    Y0, Y1 = SUBJ_Y, SUBJ_Y - 1.2     # berjalan pelan ke arah laut (-Y)

    base = {
        "hips": (0, 0, 0),
        "spine": (3, 0, 0), "chest": (-1, 0, 0), "neck": (2, 0, 0),
        "head": (-2, 0, 3),
        "shoulder.L": (-2, 0, 0), "shoulder.R": (-2, 0, 0),
        "upper_arm.L": (-8, 6, 0), "fore_arm.L": (-20, 0, 4), "hand.L": (-4, 0, 0),
        "upper_arm.R": (6, -6, 0), "fore_arm.R": (-18, 0, -4), "hand.R": (-4, 0, 0),
        "thigh.L": (-4, 0, 2), "shin.L": (4, 0, 0), "foot.L": (0, 0, 0),
        "thigh.R": (2, 0, -2), "shin.R": (3, 0, 0), "foot.R": (0, 0, 0),
    }
    bones = list(base.keys())

    # Langkah lambat: kiri-maju, kanan-maju, kiri-maju. Ujung shot berhenti
    # dengan berat di kaki kanan (bukan potongan langkah).
    key_pose(haris, 1, pose(base, {}), bones)
    key_pose(haris, 12, pose(base, {
        "thigh.L": (-16, 0, 2), "shin.L": (6, 0, 0), "foot.L": (-4, 0, 0),
        "thigh.R": (11, 0, -2), "shin.R": (16, 0, 0),
        "upper_arm.L": (-14, 6, 0), "upper_arm.R": (12, -6, 0),
        "spine": (4, 0, -2), "head": (-2, 0, 2),
    }), bones)
    key_pose(haris, 36, pose(base, {
        "thigh.L": (-15, 0, 2), "shin.L": (5, 0, 0), "foot.L": (-3, 0, 0),
        "thigh.R": (12, 0, -2), "shin.R": (17, 0, 0),
        "upper_arm.L": (-13, 6, 0), "upper_arm.R": (13, -6, 0),
        "spine": (4, 0, -2), "head": (-3, 0, 2),
        # tangan kiri mulai menunjuk ke arah laut
        "upper_arm.L": (-40, -24, 0), "fore_arm.L": (-24, 0, 6),
        "hand.L": (-10, 0, 0),
    }), bones)
    key_pose(haris, 60, pose(base, {
        "thigh.R": (-15, 0, -2), "shin.R": (5, 0, 0), "foot.R": (-3, 0, 0),
        "thigh.L": (12, 0, 2), "shin.L": (17, 0, 0),
        "upper_arm.R": (12, -6, 0),
        "upper_arm.L": (-46, -28, 0), "fore_arm.L": (-18, 0, 8),
        "hand.L": (-12, 0, 0),
        "spine": (3, 0, 2), "head": (-4, 0, 4),
    }), bones)
    key_pose(haris, 84, pose(base, {
        "thigh.L": (-9, 0, 2), "shin.L": (5, 0, 0),
        "thigh.R": (5, 0, -2), "shin.R": (9, 0, 0),
        "upper_arm.L": (-30, -18, 0), "fore_arm.L": (-26, 0, 6),
        "head": (-3, 0, 3),
    }), bones)
    key_pose(haris, 96, pose(base, {
        "thigh.L": (-5, 0, 2), "shin.L": (4, 0, 0),
        "thigh.R": (3, 0, -2), "shin.R": (5, 0, 0),
        "upper_arm.L": (-12, 4, 0), "fore_arm.L": (-22, 0, 5),
        "head": (-2, 0, 2),
    }), bones)

    # Jalan pelan 1,2 m dengan kecepatan rata: 9 kunci berjarak sama.
    key_arm_location(haris, [
        (1, (0.0, Y0, DECK)),
        (12, (0.0, Y0 - 0.15, DECK + 0.008)),
        (24, (0.0, Y0 - 0.30, DECK)),
        (36, (0.0, Y0 - 0.45, DECK + 0.008)),
        (48, (0.0, Y0 - 0.60, DECK)),
        (60, (0.0, Y0 - 0.75, DECK + 0.008)),
        (72, (0.0, Y0 - 0.90, DECK)),
        (84, (0.0, Y0 - 1.05, DECK + 0.006)),
        (96, (0.0, Y1, DECK)),
    ])

    light_morning(SUBJ_Y - 2.8)   # key di sisi kamera (Haris menghadap -Y)

    # Tracking: kamera mundur sejajar subjek (jarak tetap ~2,9 m).
    cam = lib.make_camera("CAM_shot-050", (0.50, Y0 - 2.90, 2.46),
                          (0.0, Y0, 2.60), lens=45.0)
    key_cam_path(cam, [
        (1, (0.50, Y0 - 2.90, 2.46), (0.0, Y0, 2.60)),
        (48, (0.50, Y0 - 0.60 - 2.90, 2.45), (0.0, Y0 - 0.60, 2.59)),
        (96, (0.50, Y1 - 2.90, 2.43), (0.0, Y1, 2.58)),
    ])

    rename_action(haris, "CHR_act_haris_050_pemandu")
    DECISIONS.append("rig tanpa facial: senyum tipis diganti dagu sedikit naik + "
                     "tolehan 3-4 derajat, bukan rotasi mulut")
    finish("s4-050", "scene-4_shot-050_haris-pemandu_v001.blend", 64, scn,
           [haris], cam,
           "ANIM — selesai scene-4 shot 050 (1-96, medium tracking mundur 1,2 m, "
           "action haris_050_pemandu)")


# ---------------------------------------------------------------------------
# dispatch
# ---------------------------------------------------------------------------

BUILDERS = {
    "s2-060": build_s2_060,
    "s2-080": build_s2_080,
    "s3-040": build_s3_040,
    "s3-060": build_s3_060,
    "s3-080": build_s3_080,
    "s4-040": build_s4_040,
    "s4-050": build_s4_050,
}


def main():
    tag = globals().get("SHOT_TO_BUILD")
    if not tag or tag not in BUILDERS:
        print("SHOT_TO_BUILD harus salah satu dari:", list(BUILDERS))
        return
    BUILDERS[tag]()


if __name__ == "__main__":
    main()

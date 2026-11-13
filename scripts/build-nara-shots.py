"""
build-nara-shots.py — empat shot yang hanya membutuhkan rig Nara (Scene 3 & 4).

  s3-010  scene-3_shot-010_nara-rekam_v001.blend      Nara menyelam + kamera bawah air
  s3-050  scene-3_shot-050_buku-utang_v001.blend      close-up tangan + buku utang
  s3-100  scene-3_shot-100_kalimat-kunci_v001.blend   close-up 3/4, kepala menoleh
  s4-080  scene-4_shot-080_nara-dermaga_v001.blend    Nara di ujung dermaga, dari belakang

Helper umum diimpor dari `scripts/build-scene-4-shots.py` (wipe, setup_scene,
append_collection, material, kamera, key_camera, report, save_and_preview).

Cara pakai di Blender MCP (satu shot per eksekusi):
    ns = {"__name__": "__main__", "SHOT_TO_BUILD": "s3-010"}
    exec(compile(open(path).read(), path, "exec"), ns)

Aturan yang dipatuhi:
- Tidak memanggil open_mainfile / read_factory_settings (mematikan socket add-on).
- Data di-wipe manual; file aktif dilepas lewat renders/tmp/_wipe.blend.
- Aset di-APPEND (link=False).
- EEVEE, 1920x1080, 24 fps, view transform Standard, simpan di frame 1.
- Tanpa camera shake, tanpa DOF ekstrem, tanpa tekstur image.
- Rig Nara tanpa jari & tanpa facial: pose modest, properti ditempel ke tangan
  lewat bone-parent (PRP_camera → hand.R, PRP_book → hand.R).
"""

import datetime
import importlib.util
import math
import os

import bpy
from mathutils import Euler, Matrix, Vector

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


# ---------------------------------------------------------------------------
# utilitas tambahan (pose, bone-parent, log)
# ---------------------------------------------------------------------------


def log(line):
    os.makedirs(os.path.dirname(LOGPATH), exist_ok=True)
    stamp = datetime.datetime.now().strftime("%H:%M")
    with open(LOGPATH, "a", encoding="utf-8") as fh:
        fh.write("[%s] %s\n" % (stamp, line))
    print("[log]", line)


def bezier():
    """Interpolasi default halus (bukan linear) untuk gerak organik."""
    try:
        bpy.context.preferences.edit.keyframe_new_interpolation_type = "BEZIER"
    except Exception as exc:  # pragma: no cover
        print("tidak bisa set interpolasi:", exc)


def rot_bone(pb, rx=0.0, ry=0.0, rz=0.0, order="XYZ"):
    """Putar pose bone sebesar (rx, ry, rz) derajat pada sumbu ruang armature.

    Sumbu armature: X = kiri-kanan tubuh, Y = belakang-depan, Z = atas.
    `order` menentukan urutan penerapan (huruf pertama = diterapkan lebih dulu).
    "XYZ" = Rz@Ry@Rx (default), "YXZ" = Rz@Rx@Ry (untuk menutup lengan ke badan).
    """
    mx = Matrix.Rotation(math.radians(rx), 3, "X")
    my = Matrix.Rotation(math.radians(ry), 3, "Y")
    mz = Matrix.Rotation(math.radians(rz), 3, "Z")
    if order == "YXZ":
        rot = mz @ mx @ my
    else:
        rot = mz @ my @ mx
    rest = pb.bone.matrix_local.to_3x3()
    pb.rotation_mode = "QUATERNION"
    pb.rotation_quaternion = (rest.inverted() @ rot @ rest).to_quaternion()


def reset_pose(arm):
    for pb in arm.pose.bones:
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
        pb.location = (0.0, 0.0, 0.0)
        pb.scale = (1.0, 1.0, 1.0)


def apply_pose(arm, pose):
    reset_pose(arm)
    for name, val in pose.items():
        if len(val) >= 4:
            rot_bone(arm.pose.bones[name], val[0], val[1], val[2], val[3])
        else:
            rot_bone(arm.pose.bones[name], val[0], val[1], val[2])
    bpy.context.view_layer.update()


def key_pose(arm, frame, pose, bones):
    bpy.context.scene.frame_set(frame)
    apply_pose(arm, pose)
    for name in bones:
        arm.pose.bones[name].keyframe_insert("rotation_quaternion", frame=frame)


def merge(base, **over):
    pose = dict(base)
    pose.update(over)
    return pose


def bone_head(arm, name):
    return arm.matrix_world @ arm.pose.bones[name].head


def bone_tail(arm, name):
    return arm.matrix_world @ arm.pose.bones[name].tail


def bone_parent(objs, arm, bone_name, world_matrix):
    """Tempel objek ke bone (bukan parent ke armature) supaya ikut deformasi."""
    bpy.context.view_layer.update()
    pairs = [(o, o.matrix_world.copy()) for o in objs]
    for obj, _ in pairs:
        obj.parent = arm
        obj.parent_type = "BONE"
        obj.parent_bone = bone_name
    bpy.context.view_layer.update()
    for obj, m in pairs:
        obj.matrix_world = world_matrix @ m


def append_objects(blend_path, names):
    """Append objek tertentu saja (file tetap ringan)."""
    before = set(bpy.data.objects.keys())
    with bpy.data.libraries.load(blend_path, link=False) as (src, dst):
        dst.objects = [n for n in names if n in src.objects]
    new = [bpy.data.objects[n] for n in bpy.data.objects.keys() if n not in before]
    for obj in new:
        if not obj.users_collection:
            bpy.context.scene.collection.objects.link(obj)
    return new


def emission_material(name, hexcol, strength=0.6):
    """Material datar (emission) untuk backdrop/latar — tidak ikut bayangan."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    for node in list(nt.nodes):
        nt.nodes.remove(node)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    emi = nt.nodes.new("ShaderNodeEmission")
    emi.inputs["Color"].default_value = lib.srgb(hexcol)
    emi.inputs["Strength"].default_value = strength
    nt.links.new(emi.outputs["Emission"], out.inputs["Surface"])
    mat.diffuse_color = lib.srgb(hexcol)
    return mat


def add_backdrop(name, loc, rot_deg, size, hexcol, strength=0.55):
    """Bidang datar di belakang subjek supaya horizon laut tidak terbaca."""
    mat = emission_material("MAT_backdrop_" + name, hexcol, strength)
    mesh = bpy.data.meshes.new(name)
    s = size * 0.5
    mesh.from_pydata(
        [(-s, -s, 0.0), (s, -s, 0.0), (s, s, 0.0), (-s, s, 0.0)], [], [(0, 1, 2, 3)]
    )
    mesh.materials.append(mat)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    obj.location = loc
    obj.rotation_euler = tuple(math.radians(v) for v in rot_deg)
    obj.visible_shadow = False
    bpy.context.scene.collection.objects.link(obj)
    return obj


def murky_floor(name, hex_face, hex_water, roughness=0.94, mix_amt=0.85):
    """Lantai yang memudar jadi warna air di sudut landai (menghapus garis horizon)."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = lib.srgb(hex_face)
    bsdf.inputs["Roughness"].default_value = roughness
    emi = nt.nodes.new("ShaderNodeEmission")
    emi.inputs["Color"].default_value = lib.srgb(hex_water)
    emi.inputs["Strength"].default_value = 0.9
    fres = nt.nodes.new("ShaderNodeFresnel")
    fres.inputs["IOR"].default_value = 1.33
    mul = nt.nodes.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    mul.inputs[1].default_value = mix_amt
    mix = nt.nodes.new("ShaderNodeMixShader")
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    nt.links.new(fres.outputs["Fac"], mul.inputs[0])
    nt.links.new(mul.outputs["Value"], mix.inputs["Fac"])
    nt.links.new(bsdf.outputs["BSDF"], mix.inputs[1])
    nt.links.new(emi.outputs["Emission"], mix.inputs[2])
    nt.links.new(mix.outputs["Shader"], out.inputs["Surface"])
    mat.diffuse_color = lib.srgb(hex_face)
    return mat


def append_nara():
    objs = lib.append_collection(ASSETS + "/char/nara_rig.blend", "CHR_nara")
    lib.purge_lights_cameras(objs)
    objs = lib.live_objects(objs)
    arm = bpy.data.objects["CHR_nara_rig"]
    if arm.animation_data:
        act = arm.animation_data.action
        arm.animation_data.action = None
        if act is not None and act.name == "CHR_act_nara_pose-swim":
            try:
                act.use_fake_user = False
                bpy.data.actions.remove(act)
            except Exception as exc:
                print("action uji tetap ada:", exc)
    return arm, objs


def rename_action(arm, name):
    act = arm.animation_data.action if arm.animation_data else None
    if act is not None:
        act.name = name
        act.use_fake_user = True
        print("ACTION:", act.name)
    return act


def key_cam_path(cam, keys):
    """keys = [(frame, loc, target), ...] — Bezier halus."""
    bezier()
    for frame, loc, target in keys:
        bpy.context.scene.frame_set(frame)
        cam.location = loc
        lib.look_at(cam, target)
        cam.keyframe_insert("location", frame=frame)
        cam.keyframe_insert("rotation_euler", frame=frame)


def verify(tag, scn, arm, cam):
    print("=== VERIFY %s ===" % tag)
    print("  scene:", scn.name, "frames:", scn.frame_start, "-", scn.frame_end,
          "fps:", scn.render.fps, "engine:", scn.render.engine,
          "vt:", scn.view_settings.view_transform,
          "res:", scn.render.resolution_x, scn.render.resolution_y)
    print("  camera:", cam.name, "lens", cam.data.lens, "loc",
          tuple(round(v, 2) for v in cam.location))
    act = arm.animation_data.action if arm.animation_data else None
    print("  action:", act.name if act else None,
          "range", tuple(act.frame_range) if act else None)
    bpy.context.scene.frame_set(1)
    print("  arm loc f1:", tuple(round(v, 2) for v in arm.location),
          "rot x:", round(math.degrees(arm.rotation_euler.x), 1))
    for n in ("head", "hand.L", "hand.R"):
        h = bone_head(arm, n)
        print("  %s head world: (%.2f, %.2f, %.2f)" % (n, h.x, h.y, h.z))
    print("  objek mesh:", len([o for o in bpy.data.objects if o.type == "MESH"]),
          "total objek:", len(bpy.data.objects))


# ---------------------------------------------------------------------------
# scene-3 shot 010 — Nara menyelam merekam karang rusak
# ---------------------------------------------------------------------------


def build_s3_010():
    lib.wipe()
    scn = lib.setup_scene("scene-3_shot-010_nara-rekam")
    bezier()
    log("ANIM — mulai scene-3 shot 010 (Nara menyelam + kamera bawah air)")

    sand = murky_floor("MAT_seabed_sand", PAL["sand"], "#12505C", roughness=0.94)
    lib.make_plane("ENV_seabed", 200.0, 0.0, sand)
    add_backdrop("ENV_water-backdrop", (-16.0, 0.0, 8.0), (90.0, 0.0, 90.0),
                 120.0, "#14606B", strength=0.7)

    # Karang rusak + puing: berada di sisi -X (latar kamera tracking).
    dmg = lib.append_collection(ASSETS + "/env/reef-damaged.blend", "ENV_reef-damaged")
    lib.purge_lights_cameras(dmg)
    dmg = lib.live_objects(dmg)
    layout = {
        "ENV_reef_damaged-rubble_a": ((-1.7, 1.9, 0.30), 24, 1.20),
        "ENV_reef_damaged-rubble_b": ((-2.0, -0.6, 0.45), -38, 1.35),
        "ENV_reef_damaged-rubble_c": ((-2.9, -2.8, 0.25), 70, 1.10),
        "ENV_reef_damaged-bomb": ((-3.4, 3.6, 0.22), 14, 0.90),
        "ENV_reef_damaged-net": ((-2.4, 0.9, 0.55), -20, 1.00),
    }
    for name, (loc, rz, sc) in layout.items():
        obj = bpy.data.objects.get(name)
        if obj:
            obj.location = loc
            obj.rotation_euler = (0.0, 0.0, math.radians(rz))
            obj.scale = (sc, sc, sc)

    # Karang hidup jauh di belakang untuk kedalaman (bukan subjek).
    reef = lib.append_collection(ASSETS + "/env/reef.blend", "ENV_reef")
    lib.purge_lights_cameras(reef)
    for name in list(bpy.data.objects.keys()):
        if name.startswith("ENV_reef_turtle"):
            bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)
    reef = lib.live_objects(reef)
    for obj in reef:
        if obj.name.startswith(("ENV_reef_branching", "ENV_reef_boulder", "ENV_reef_table")):
            obj.location = (obj.location.x - 8.5, obj.location.y + 7.0, obj.location.z)
            obj.scale = (1.6, 1.6, 1.6)
        elif obj.name.startswith("ENV_reef_fish"):
            obj.location = (obj.location.x - 9.0, obj.location.y + 12.0, obj.location.z + 1.8)

    arm, _ = append_nara()
    # Nara horizontal: +90 derajat pada X → kepala ke -Y, dada menghadap dasar.
    arm.rotation_euler = (math.radians(90.0), 0.0, 0.0)

    base = {
        "hips": (0, 0, 0),
        "spine": (2, 0, 0),
        "neck": (-16, 0, 0),
        "head": (-8, 0, 0),
        "shoulder.L": (-6, 0, 0),
        "shoulder.R": (-6, 0, 0),
        "upper_arm.L": (-70, 0, 14),
        "upper_arm.R": (-70, 0, -14),
        "fore_arm.L": (-22, 0, 8),
        "fore_arm.R": (-22, 0, -8),
        "hand.L": (-6, 0, 0),
        "hand.R": (-6, 0, 0),
        "thigh.L": (5, 0, 2),
        "thigh.R": (5, 0, -2),
        "shin.L": (-8, 0, 0),
        "shin.R": (-12, 0, 0),
        "foot.L": (10, 0, 0),
        "foot.R": (12, 0, 0),
    }
    bones = list(base.keys())

    p1 = dict(base)
    p2 = dict(base)
    p2["spine"] = (4, 0, 0)
    p2["neck"] = (-14, 0, 0)
    p2["thigh.L"] = (11, 0, 2)
    p2["thigh.R"] = (0, 0, -2)
    p2["shin.L"] = (-16, 0, 0)
    p2["shin.R"] = (-6, 0, 0)
    p2["upper_arm.L"] = (-72, 0, 14)
    p2["upper_arm.R"] = (-68, 0, -14)

    p3 = dict(base)
    p3["spine"] = (1, 0, 0)
    p3["neck"] = (-17, 0, 0)
    p3["thigh.L"] = (0, 0, 2)
    p3["thigh.R"] = (10, 0, -2)
    p3["shin.L"] = (-5, 0, 0)
    p3["shin.R"] = (-18, 0, 0)
    p3["upper_arm.L"] = (-69, 0, 14)
    p3["upper_arm.R"] = (-71, 0, -14)

    key_pose(arm, 1, p1, bones)
    key_pose(arm, 40, p2, bones)
    key_pose(arm, 72, p3, bones)
    key_pose(arm, 96, merge(base, spine=(3, 0, 0)), bones)

    # Geser pelan ke -Y (0,25 m/s): drifting, bukan sprint.
    for frame, y in ((1, 1.28), (96, 0.22)):
        scn.frame_set(frame)
        arm.location = (0.0, y, 2.30)
        arm.keyframe_insert("location", frame=frame)

    # Properti: housing kamera bawah air menempel di tangan kanan, lensa ke bawah.
    scn.frame_set(1)
    apply_pose(arm, p1)
    hl = bone_head(arm, "hand.L")
    hr = bone_head(arm, "hand.R")
    mid = (hl + hr) * 0.5
    target = mid + Vector((0.0, -0.02, -0.10))
    cam_prop = lib.append_collection(ASSETS + "/props/underwater-camera.blend", "PRP_camera")
    lib.purge_lights_cameras(cam_prop)
    cam_prop = lib.live_objects(cam_prop)
    prop_mat = (
        Matrix.Translation(target)
        @ Euler((math.radians(90.0), 0.0, math.radians(4.0)), "XYZ").to_matrix().to_4x4()
    )
    bone_parent(cam_prop, arm, "hand.R", prop_mat)
    print("kamera prop di:", tuple(round(v, 3) for v in target))

    lib.add_world("WLD_s3-010", "#0F5C63", strength=1.3)
    sun = lib.add_sun(energy=4.2, angle_deg=8.0, rot=(34, 0, -28))
    sun.data.color = (1.0, 0.86, 0.68)
    fill = lib.add_fill(energy=160.0, size=9.0, loc=(3.2, -3.6, 4.6), target=(0, 0, 1.2))
    fill.data.color = (0.62, 0.86, 0.90)

    cam = lib.make_camera("CAM_shot-010", (3.72, 0.42, 2.42), (0.0, 0.42, 2.26), lens=45.0)
    key_cam_path(cam, [
        (1, (3.72, 0.42, 2.42), (0.0, 0.42, 2.26)),
        (48, (3.68, -0.10, 2.39), (0.0, -0.10, 2.25)),
        (96, (3.64, -0.63, 2.36), (0.0, -0.63, 2.26)),
    ])

    verify("s3-010", scn, arm, cam)
    rename_action(arm, "CHR_act_nara_010_rekam")
    lib.report("s3-010", [o for o in bpy.data.objects if o.type == "MESH"], scn)
    lib.save_and_preview("s3-010", "scene-3_shot-010_nara-rekam_v001.blend", preview_frame=48)
    log("ANIM — selesai scene-3 shot 010 (1-96, CAM_shot-010 tracking samping)")


# ---------------------------------------------------------------------------
# scene-3 shot 050 — close-up buku utang di dalam perahu
# ---------------------------------------------------------------------------


def build_s3_050():
    lib.wipe()
    scn = lib.setup_scene("scene-3_shot-050_buku-utang")
    bezier()
    log("ANIM — mulai scene-3 shot 050 (close-up tangan + buku utang)")

    sea = lib.material("MAT_sea_surface", "#0A333C", roughness=0.32)
    lib.make_plane("ENV_sea", 600.0, 0.0, sea)

    boat = lib.append_collection(ASSETS + "/props/boats.blend", "PRP_boats")
    lib.purge_lights_cameras(boat)
    boat = lib.live_objects(boat)

    arm, _ = append_nara()
    arm.location = (0.0, 0.34, 0.30)   # berdiri di dek perahu (dek z 0,30)
    arm.rotation_euler = (0.0, 0.0, math.radians(8.0))

    base = {
        "hips": (0, 0, 0),
        "spine": (18, 0, 0),
        "neck": (4, 0, -6),
        "head": (-14, 0, -4),
        "shoulder.L": (-6, 0, 0),
        "shoulder.R": (-6, 0, 0),
        "upper_arm.L": (-66, 26, 0, "YXZ"),
        "upper_arm.R": (-62, -26, 0, "YXZ"),
        "fore_arm.L": (-30, 0, -12),
        "fore_arm.R": (-32, 0, 12),
        "hand.L": (-16, 8, 0),
        "hand.R": (-14, -8, 0),
        "thigh.L": (-6, 0, 3),
        "thigh.R": (-6, 0, -3),
        "shin.L": (6, 0, 0),
        "shin.R": (5, 0, 0),
        "foot.L": (0, 0, 0),
        "foot.R": (0, 0, 0),
    }
    bones = list(base.keys())

    # Nada "menemukan": badan menunduk, lalu buku diangkat sedikit ke arah kamera.
    p1 = dict(base)
    p1["spine"] = (20, 0, 0)
    p1["head"] = (-9, 0, -4)

    p2 = dict(base)
    p2["spine"] = (18, 0, 0)
    p2["head"] = (-18, 0, -6)
    p2["hand.L"] = (-18, 8, 0)
    p2["hand.R"] = (-16, -8, 0)

    key_pose(arm, 1, p1, bones)
    key_pose(arm, 44, base, bones)
    key_pose(arm, 72, p2, bones)
    key_pose(arm, 96, p2, bones)

    # Buku menempel di tangan kanan (rig tanpa jari: buku diletakkan di telapak).
    scn.frame_set(1)
    apply_pose(arm, p1)
    hl = bone_head(arm, "hand.L")
    hr = bone_head(arm, "hand.R")
    mid = (hl + hr) * 0.5
    target = mid + Vector((0.0, -0.10, 0.02))
    book = lib.append_collection(ASSETS + "/props/debt-book.blend", "PRP_book")
    lib.purge_lights_cameras(book)
    book = lib.live_objects(book)
    book_mat = (
        Matrix.Translation(target)
        @ Euler((math.radians(72.0), 0.0, math.radians(-14.0)), "XYZ").to_matrix().to_4x4()
    )
    bone_parent(book, arm, "hand.R", book_mat)
    pts = []
    for obj in book:
        for corner in obj.bound_box:
            pts.append(obj.matrix_world @ Vector(corner))
    book_center = sum(pts, Vector()) / len(pts)
    print("buku di:", tuple(round(v, 3) for v in target),
          "| pusat buku:", tuple(round(v, 3) for v in book_center),
          "| tangan L", tuple(round(v, 2) for v in hl),
          "| tangan R", tuple(round(v, 2) for v in hr))

    # Sore hangat, perahu gelap di latar.
    lib.add_world("WLD_s3-050", "#0B2A31", strength=0.40)
    sun = lib.add_sun(energy=1.5, angle_deg=6.0, rot=(62, 0, 132))
    sun.data.color = (1.0, 0.80, 0.58)
    key = lib.add_fill(energy=42.0, size=1.3,
                       loc=(target.x + 0.95, target.y - 0.55, target.z + 0.50),
                       target=(target.x, target.y, target.z))
    key.data.color = (1.0, 0.88, 0.72)
    rim = lib.add_fill(energy=22.0, size=2.0,
                       loc=(target.x - 1.3, target.y + 0.95, target.z + 0.8),
                       target=(target.x, target.y, target.z))
    rim.data.color = (0.60, 0.84, 0.88)

    # Close-up: kamera statis + push-in halus, dibidik ke buku/tangan.
    aim = book_center + Vector((0.0, 0.0, 0.06))
    cam0 = book_center + Vector((0.14, -1.14, 0.15))
    cam1 = book_center + Vector((0.12, -1.02, 0.13))
    cam = lib.make_camera("CAM_shot-050", cam0, aim, lens=50.0)
    key_cam_path(cam, [
        (1, cam0, aim),
        (96, cam1, aim),
    ])

    verify("s3-050", scn, arm, cam)
    rename_action(arm, "CHR_act_nara_050_buku")
    lib.report("s3-050", [o for o in bpy.data.objects if o.type == "MESH"], scn)
    lib.save_and_preview("s3-050", "scene-3_shot-050_buku-utang_v001.blend", preview_frame=72)
    log("ANIM — selesai scene-3 shot 050 (1-96, CAM_shot-050 push-in halus)")


# ---------------------------------------------------------------------------
# scene-3 shot 100 — close-up kalimat kunci
# ---------------------------------------------------------------------------


def build_s3_100():
    lib.wipe()
    scn = lib.setup_scene("scene-3_shot-100_kalimat-kunci")
    bezier()
    log("ANIM — mulai scene-3 shot 100 (close-up 3/4 kalimat kunci)")

    pier = append_objects(
        ASSETS + "/env/surface.blend",
        ["ENV_surface_pier-deck", "ENV_surface_pier-posts", "ENV_surface_pier-railing",
         "ENV_surface_water-placeholder"],
    )
    print("dermaga:", [o.name for o in pier])

    arm, _ = append_nara()
    arm.location = (0.0, -70.0, 1.26)   # berdiri di dek dermaga (z 0,94–1,26)
    arm.rotation_euler = (0.0, 0.0, math.radians(-6.0))

    base = {
        "hips": (0, 0, 0),
        "spine": (2, 0, 0),
        "neck": (-2, 0, -6),
        "head": (-3, 0, -10),
        "shoulder.L": (0, 0, 0),
        "shoulder.R": (-3, 0, 0),
        "upper_arm.L": (4, 0, 6),
        "upper_arm.R": (-24, 0, -10),
        "fore_arm.L": (-6, 0, 4),
        "fore_arm.R": (-52, 0, -16),
        "hand.L": (0, 0, 0),
        "hand.R": (-10, 0, -8),
        "thigh.L": (0, 0, 2),
        "thigh.R": (0, 0, -2),
        "shin.L": (1, 0, 0),
        "shin.R": (1, 0, 0),
        "foot.L": (0, 0, 0),
        "foot.R": (0, 0, 0),
    }
    bones = list(base.keys())

    p1 = dict(base)
    p1["neck"] = (-1, 0, -14)
    p1["head"] = (-2, 0, -18)
    p1["upper_arm.R"] = (-16, 0, -8)
    p1["fore_arm.R"] = (-34, 0, -12)

    p2 = dict(base)
    p2["spine"] = (4, 0, 0)
    p2["neck"] = (-4, 0, 4)
    p2["head"] = (-5, 0, 9)
    p2["upper_arm.R"] = (-30, 0, -12)
    p2["fore_arm.R"] = (-58, 0, -18)

    p3 = dict(base)
    p3["spine"] = (3, 0, 0)
    p3["neck"] = (-3, 0, 9)
    p3["head"] = (-4, 0, 14)
    p3["upper_arm.R"] = (-20, 0, -9)
    p3["fore_arm.R"] = (-44, 0, -14)

    key_pose(arm, 1, p1, bones)
    key_pose(arm, 34, base, bones)
    key_pose(arm, 62, p2, bones)
    key_pose(arm, 96, p3, bones)

    # Napas: naik-turun dada sangat kecil (tidak boleh terlihat seperti goyang).
    for frame, dz in ((1, 0.0), (30, 0.006), (62, 0.0), (96, 0.005)):
        scn.frame_set(frame)
        arm.location = (0.0, -70.0, 1.26 + dz)
        arm.keyframe_insert("location", frame=frame)

    lib.add_world("WLD_s3-100", "#0F5C63", strength=0.7)
    sun = lib.add_sun(energy=2.1, angle_deg=5.0, rot=(56, 0, 118))
    sun.data.color = (1.0, 0.82, 0.60)
    key = lib.add_fill(energy=70.0, size=1.4, loc=(1.55, -71.30, 3.10), target=(0.0, -70.05, 2.80))
    key.data.color = (1.0, 0.90, 0.78)
    fill = lib.add_fill(energy=22.0, size=3.0, loc=(-1.8, -68.6, 2.4), target=(0.0, -70.0, 2.6))
    fill.data.color = (0.62, 0.86, 0.90)

    # Bingkai 3/4 dari depan, statis; kepala di sepertiga atas.
    cam = lib.make_camera("CAM_shot-100", (1.05, -71.35, 2.92), (-0.12, -70.05, 2.80), lens=58.0)
    key_cam_path(cam, [
        (1, (1.05, -71.35, 2.92), (-0.12, -70.05, 2.80)),
        (96, (1.03, -71.38, 2.90), (-0.12, -70.05, 2.80)),
    ])

    verify("s3-100", scn, arm, cam)
    rename_action(arm, "CHR_act_nara_100_kalimat")
    lib.report("s3-100", [o for o in bpy.data.objects if o.type == "MESH"], scn)
    lib.save_and_preview("s3-100", "scene-3_shot-100_kalimat-kunci_v001.blend", preview_frame=62)
    log("ANIM — selesai scene-3 shot 100 (1-96, CAM_shot-100 statis 3/4)")


# ---------------------------------------------------------------------------
# scene-4 shot 080 — Nara di ujung dermaga (dari belakang)
# ---------------------------------------------------------------------------


def build_s4_080():
    lib.wipe()
    scn = lib.setup_scene("scene-4_shot-080_nara-dermaga")
    bezier()
    log("ANIM — mulai scene-4 shot 080 (Nara di ujung dermaga)")

    pier = append_objects(
        ASSETS + "/env/surface.blend",
        ["ENV_surface_pier-deck", "ENV_surface_pier-posts", "ENV_surface_pier-railing",
         "ENV_surface_water-placeholder"],
    )
    print("dermaga:", [o.name for o in pier])
    # Air: material sementara yang lebih pekat supaya garis horizon terbaca.
    water = lib.material("MAT_sea_s4-080", "#1C7E8C", roughness=0.16)
    for obj in pier:
        if obj.name.startswith("ENV_surface_water-placeholder"):
            obj.data.materials.clear()
            obj.data.materials.append(water)

    arm, _ = append_nara()
    arm.location = (0.0, -102.6, 1.26)   # ujung dermaga, kaki di dek
    arm.rotation_euler = (0.0, 0.0, math.radians(2.0))   # menghadap -Y (laut)

    base = {
        "hips": (0, 0, 0),
        "spine": (0, 0, 0),
        "neck": (0, 0, 0),
        "head": (-2, 0, 0),
        "shoulder.L": (0, 0, 0),
        "shoulder.R": (0, 0, 0),
        "upper_arm.L": (6, 0, 4),
        "upper_arm.R": (6, 0, -4),
        "fore_arm.L": (-4, 0, 3),
        "fore_arm.R": (-4, 0, -3),
        "hand.L": (0, 0, 0),
        "hand.R": (0, 0, 0),
        "thigh.L": (0, 0, 2),
        "thigh.R": (0, 0, -2),
        "shin.L": (1, 0, 0),
        "shin.R": (1, 0, 0),
        "foot.L": (0, 0, 0),
        "foot.R": (0, 0, 0),
    }
    bones = list(base.keys())

    # Satu tarikan napas penuh sepanjang 4 detik: sangat halus.
    p1 = dict(base)
    p1["spine"] = (0.5, 0, 0)
    p1["shoulder.L"] = (1.5, 0, 0)
    p1["shoulder.R"] = (1.5, 0, 0)
    p2 = dict(base)
    p2["spine"] = (-1.6, 0, 0)
    p2["shoulder.L"] = (-2.2, 0, 0)
    p2["shoulder.R"] = (-2.2, 0, 0)
    p2["neck"] = (-1.4, 0, 0)
    p2["head"] = (-3.2, 0, 0)
    p3 = dict(base)
    p3["spine"] = (0.4, 0, 0)
    p3["shoulder.L"] = (0.8, 0, 0)
    p3["shoulder.R"] = (0.8, 0, 0)

    key_pose(arm, 1, p1, bones)
    key_pose(arm, 50, p2, bones)
    key_pose(arm, 96, p3, bones)

    lib.add_world("WLD_s4-080", "#BFD9DE", strength=0.6)
    sun = lib.add_sun(energy=5.2, angle_deg=3.0, rot=(32, 0, 8))
    sun.data.color = (1.0, 0.94, 0.84)
    bounce = lib.add_fill(energy=42.0, size=8.0, loc=(1.0, -100.0, 3.0), target=(0.0, -102.6, 2.4))
    bounce.data.color = (0.72, 0.88, 0.92)

    # Medium dari belakang (pinggang ke atas), statis; gerak kamera maksimal 8 mm.
    cam = lib.make_camera("CAM_shot-080", (1.25, -99.60, 2.80), (0.0, -102.6, 2.30), lens=45.0)
    key_cam_path(cam, [
        (1, (1.25, -99.60, 2.80), (0.0, -102.6, 2.30)),
        (50, (1.25, -99.592, 2.796), (0.0, -102.6, 2.306)),
        (96, (1.25, -99.60, 2.804), (0.0, -102.6, 2.298)),
    ])

    verify("s4-080", scn, arm, cam)
    rename_action(arm, "CHR_act_nara_080_berdiri")
    lib.report("s4-080", [o for o in bpy.data.objects if o.type == "MESH"], scn)
    lib.save_and_preview("s4-080", "scene-4_shot-080_nara-dermaga_v001.blend", preview_frame=50)
    log("ANIM — selesai scene-4 shot 080 (1-96, CAM_shot-080 statis dari belakang)")


# ---------------------------------------------------------------------------
# dispatcher
# ---------------------------------------------------------------------------

BUILDERS = {
    "s3-010": build_s3_010,
    "s3-050": build_s3_050,
    "s3-100": build_s3_100,
    "s4-080": build_s4_080,
}

if "SHOT_TO_BUILD" in globals():
    which = globals()["SHOT_TO_BUILD"]
    if which not in BUILDERS:
        raise SystemExit("shot tidak dikenal: %s" % which)
    BUILDERS[which]()

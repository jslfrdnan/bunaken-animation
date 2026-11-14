"""
build-scene-1-detail-shots.py — bangun ulang 10 shot Scene 1 memakai aset detail
baru (14 Nov 2026) dan rig v002.

  s1-010  scene-1_shot-010_bunaken-aerial_v001.blend       1-96
  s1-020  scene-1_shot-020_turun-permukaan_v001.blend     1-96
  s1-030  scene-1_shot-030_terumbu_v001.blend             1-96
  s1-040  scene-1_shot-040_penyu_v001.blend               1-72
  s1-050  scene-1_shot-050_nara-dive_v001.blend           1-96
  s1-060  scene-1_shot-060_nara-ok_v001.blend             1-72
  s1-070  scene-1_shot-070_nara-naik_v001.blend           1-96
  s1-080  scene-1_shot-080_daniel-jaring_v001.blend       1-72
  s1-090  scene-1_shot-090_anak-dermaga_v001.blend        1-72
  s1-100  scene-1_shot-100_nara-ujung-dermaga_v001.blend  1-72

Aset baru yang wajib dipakai:
  assets/env/island-detail.blend            ENV_island-detail (+ _context)
  assets/env/reef-dense.blend               ENV_reef-dense
  assets/env/sea_turtle-assembled.blend     ENV_turtle + CTL_turtle
  assets/char/nara_rig_v002.blend           CHR_nara_rig (21 bone)
  assets/char/daniel_rig_v001.blend         CHR_daniel_rig (22 bone)
  assets/char/crowd.blend                   CRW_01..CRW_12
  assets/props/boats.blend                  PRP_boats
  assets/props/divegear.blend               PRP_divegear
  assets/env/surface.blend                  ENV_surface (shot dekat dermaga)

Cara pakai di Blender MCP (satu shot per eksekusi):
    ns = {"__name__": "__main__", "SHOT_TO_BUILD": "010"}
    exec(compile(open(path).read(), path, "exec"), ns)

Aturan yang dipatuhi:
- Tidak memanggil open_mainfile / read_factory_settings / read_homefile.
- Data di-wipe manual; file aktif dilepas lewat renders/tmp/_wipe.blend.
- Aset di-APPEND (link=False) lalu diverifikasi ada di koleksi scene.
- EEVEE, 1920x1080, 24 fps, view transform Standard, disimpan di frame 1.
- Tanpa tekstur gambar, tanpa pack, tanpa camera shake kecuali shot 090.
- Tidak mengubah file aset; versi lama shot disimpan sebagai *_v000.blend.
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
LOGPATH = ROOT + "/renders/logs/technical.log"

_spec = importlib.util.spec_from_file_location(
    "s4lib", ROOT + "/scripts/build-scene-4-shots.py"
)
lib = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(lib)

PAL = lib.PAL
FPS = 24

# path aset
P_ISLAND = ASSETS + "/env/island-detail.blend"
P_REEF = ASSETS + "/env/reef-dense.blend"
P_TURTLE = ASSETS + "/env/sea_turtle-assembled.blend"
P_SURFACE = ASSETS + "/env/surface.blend"
P_NARA = ASSETS + "/char/nara_rig_v002.blend"
P_DANIEL = ASSETS + "/char/daniel_rig_v001.blend"
P_CROWD = ASSETS + "/char/crowd.blend"
P_BOATS = ASSETS + "/props/boats.blend"
P_DIVEGEAR = ASSETS + "/props/divegear.blend"
P_GEAR = ASSETS + "/props/fishing-gear.blend"


# ---------------------------------------------------------------------------
# log & util
# ---------------------------------------------------------------------------


def log(line):
    os.makedirs(os.path.dirname(LOGPATH), exist_ok=True)
    stamp = datetime.datetime.now().strftime("%H:%M")
    with open(LOGPATH, "a", encoding="utf-8") as fh:
        fh.write("[%s] %s\n" % (stamp, line))
    print("[log]", line)


def set_interp(mode):
    try:
        bpy.context.preferences.edit.keyframe_new_interpolation_type = mode
    except Exception as exc:
        print("interpolasi tidak bisa diset:", exc)


def backup(shot_name, filename):
    """Salin shot lama ke *_v000.blend sebelum ditimpa."""
    dst = os.path.join(SCENES, filename)
    bak = os.path.join(SCENES, filename.replace("_v001.blend", "_v000.blend"))
    if os.path.exists(dst) and not os.path.exists(bak):
        shutil.copy2(dst, bak)
        print("BACKUP:", os.path.basename(bak))


def save_shot(shot_name, filename):
    backup(shot_name, filename)
    scn = bpy.context.scene
    scn.frame_set(1)
    path = os.path.join(SCENES, filename)
    bpy.ops.wm.save_as_mainfile(filepath=path)
    size = os.path.getsize(path)
    print("SAVED:", path, size, "bytes")
    log("ANIM - %s selesai (%s, %d bytes)" % (shot_name, filename, size))


def preview_world(scn, above_water=True):
    """Pasang world look dev scene 1 untuk still pratinjau (tidak disimpan)."""
    p = ASSETS + "/look/scene-1-look_v002.blend"
    want = "WLD_scene-1_surface" if above_water else "WLD_scene-1"
    if want not in bpy.data.worlds:
        with bpy.data.libraries.load(p, link=False) as (src, dst):
            dst.worlds = [n for n in src.worlds if n == want]
    w = bpy.data.worlds.get(want)
    if w is None:
        print("world look tidak ketemu:", want)
        return None
    w.use_fake_user = True
    scn.world = w
    return w


def preview_water(scn):
    """Ganti material objek air dengan shader air look dev (hanya di sesi ini)."""
    p = ASSETS + "/look/scene-1-look_v002.blend"
    name = "SHD_water-surface"
    if name not in bpy.data.materials:
        with bpy.data.libraries.load(p, link=False) as (src, dst):
            dst.materials = [n for n in src.materials if n == name]
    mat = bpy.data.materials.get(name)
    if mat is None:
        return []
    mat.use_fake_user = True
    touched = []
    for ob in scn.objects:
        if ob.type != "MESH" or not hasattr(ob.data, "materials"):
            continue
        toks = [t for t in re.split(r"[^a-z0-9]+", ob.name.lower()) if t]
        if not any(t == "water" or t.startswith("water") or t == "sea" for t in toks):
            continue
        if any(t in ("volume", "fog", "mist") for t in toks):
            continue
        if len(ob.data.materials) == 0:
            ob.data.materials.append(mat)
        else:
            for i in range(len(ob.data.materials)):
                ob.data.materials[i] = mat
        touched.append(ob.name)
    return touched


def look_still(shot_name, preview_frame, look_scene=1, above_water=None, percent=50):
    """Still representatif: world + shader air look dev dipasang SESUDAH simpan.

    File shot tetap bersih (world lokal) supaya `scripts/look.py` di renderer
    tidak memakai world SHD/WLD basi dari file shot.
    """
    scn = bpy.context.scene
    out = os.path.join(STILLS, "anim-%s_v001.png" % shot_name)
    try:
        os.makedirs(STILLS, exist_ok=True)
        if above_water is None:
            cam = scn.camera
            above_water = bool(cam is not None and cam.matrix_world.translation.z > 0.5)
        w = preview_world(scn, above_water=above_water)
        water = preview_water(scn)
        scn.view_settings.view_transform = "Standard"
        scn.frame_set(int(preview_frame))
        scn.render.resolution_percentage = int(percent)
        scn.render.image_settings.file_format = "PNG"
        scn.render.image_settings.color_mode = "RGBA"
        if hasattr(scn, "eevee"):
            scn.eevee.taa_render_samples = 32
        scn.render.filepath = out
        bpy.ops.render.render(write_still=True)
        scn.frame_set(1)
        print(
            "STILL:",
            out,
            os.path.exists(out),
            "| world",
            w.name if w else None,
            "| above_water",
            above_water,
            "| water_obj",
            water,
        )
    except Exception as exc:
        print("look still gagal:", repr(exc))


def finish(shot_name, filename, preview_frame=1, look_scene=1, above_water=None):
    scn = bpy.context.scene
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    total_v = sum(len(o.data.vertices) for o in meshes if hasattr(o.data, "vertices"))
    print(
        "SUMMARY %s | mesh=%d armature=%d camera=%d light=%d verts=%d | engine=%s vt=%s res=%dx%d fps=%d range=%d-%d"
        % (
            shot_name,
            len(meshes),
            len([o for o in bpy.data.objects if o.type == "ARMATURE"]),
            len([o for o in bpy.data.objects if o.type == "CAMERA"]),
            len([o for o in bpy.data.objects if o.type == "LIGHT"]),
            total_v,
            scn.render.engine,
            scn.view_settings.view_transform,
            scn.render.resolution_x,
            scn.render.resolution_y,
            scn.render.fps,
            scn.frame_start,
            scn.frame_end,
        )
    )
    scn.frame_set(1)
    save_shot(shot_name, filename)
    look_still(shot_name, preview_frame, look_scene=look_scene, above_water=above_water)


def append(path, coll, purge=True):
    objs = lib.append_collection(path, coll)
    if purge:
        killed = lib.purge_lights_cameras(objs)
        if killed:
            print("dibuang %s: %d objek" % (coll, len(killed)))
    # objek dependensi (mis. armature rig) bisa masuk tanpa koleksi apa pun
    target = bpy.data.collections.get(coll) or bpy.context.scene.collection
    orphans = [o for o in bpy.data.objects if not o.users_collection]
    for o in orphans:
        target.objects.link(o)
    if orphans:
        print("dilink ke %s: %s" % (coll, [o.name for o in orphans]))
    return lib.live_objects(objs)


def ensure_engine(scn):
    try:
        scn.render.engine = "BLENDER_EEVEE"
    except TypeError:
        pass
    if hasattr(scn, "eevee"):
        scn.eevee.taa_render_samples = 32
    scn.render.film_transparent = False


def look_at(ob, target):
    """Aim kamera tanpa degenerasi roll (arah mendatar sejajar sumbu Y)."""
    fwd = Vector(target) - Vector(ob.location)
    if fwd.length < 1e-6:
        return
    fwd.normalize()
    up = Vector((0.0, 0.0, 1.0))
    if abs(fwd.dot(up)) > 0.9995:
        up = Vector((0.0, 1.0, 0.0))
    right = fwd.cross(up)
    if right.length < 1e-6:
        right = fwd.cross(Vector((1.0, 0.0, 0.0)))
    right.normalize()
    up2 = right.cross(fwd).normalized()
    mat = Matrix(
        (
            (right.x, up2.x, -fwd.x, 0.0),
            (right.y, up2.y, -fwd.y, 0.0),
            (right.z, up2.z, -fwd.z, 0.0),
            (0.0, 0.0, 0.0, 1.0),
        )
    )
    ob.rotation_mode = "XYZ"
    ob.rotation_euler = mat.to_euler("XYZ")


def make_cam(name, loc, target, lens=35.0, clip_end=400.0):
    cam_data = bpy.data.cameras.new(name)
    cam_data.lens = lens
    cam_data.sensor_width = 36.0
    cam_data.clip_start = 0.05
    cam_data.clip_end = clip_end
    cam = bpy.data.objects.new(name, cam_data)
    cam.location = loc
    bpy.context.scene.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    look_at(cam, target)
    return cam


def key_cam(cam, keys, mode="BEZIER"):
    set_interp(mode)
    for frame, loc, tgt in keys:
        cam.location = loc
        look_at(cam, tgt)
        cam.keyframe_insert("location", frame=frame)
        cam.keyframe_insert("rotation_euler", frame=frame)


def key_loc(ob, keys, mode="BEZIER"):
    set_interp(mode)
    for frame, loc in keys:
        ob.location = loc
        ob.keyframe_insert("location", frame=frame)


def sun(scn, energy=3.5, angle=4.0, rot=(60, 0, 40), color=(1.0, 0.94, 0.82)):
    ob = lib.add_sun(energy=energy, angle_deg=angle, rot=rot)
    ob.data.color = color
    return ob


def world(scn, hexcol, strength=1.0, name="WLD_shot"):
    return lib.add_world(name, hexcol, strength=strength)


def root_empty(name, loc=(0, 0, 0)):
    """Empty pengontrol untuk menggerakkan gerombolan objek (perahu, penyu)."""
    ctl = bpy.data.objects.new(name, None)
    ctl.empty_display_size = 0.6
    ctl.location = loc
    bpy.context.scene.collection.objects.link(ctl)
    return ctl


def adopt(objs, ctl):
    """Parent objek ke ctl tanpa mengubah posisi dunia."""
    for ob in objs:
        if ob.parent is None:
            ob.parent = ctl
            ob.matrix_parent_inverse = ctl.matrix_world.inverted()
    return objs


# ---------------------------------------------------------------------------
# pose helper (sama dengan build-nara-shots.py)
# ---------------------------------------------------------------------------


def rot_bone(pb, rx=0.0, ry=0.0, rz=0.0, order="XYZ"):
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


def apply_pose(arm, pose):
    reset_pose(arm)
    for name, val in pose.items():
        pb = arm.pose.bones.get(name)
        if pb is None:
            print("bone tidak ada:", name)
            continue
        rot_bone(pb, val[0], val[1], val[2], val[3]) if len(val) >= 4 else rot_bone(
            pb, val[0], val[1], val[2]
        )
    bpy.context.view_layer.update()


def key_pose(arm, frame, pose, bones):
    bpy.context.scene.frame_set(frame)
    apply_pose(arm, pose)
    for name in bones:
        pb = arm.pose.bones.get(name)
        if pb is not None:
            pb.keyframe_insert("rotation_quaternion", frame=frame)


def bone_world(arm, name, t=0.5):
    pb = arm.pose.bones[name]
    return arm.matrix_world @ (pb.head.lerp(pb.tail, t))


def bone_parent(ob, arm, bone_name, world_matrix):
    """Tempel objek ke satu bone (ikut deformasi) memakai matriks dunia."""
    bpy.context.view_layer.update()
    want = world_matrix.copy()
    ob.parent = arm
    ob.parent_type = "BONE"
    ob.parent_bone = bone_name
    bpy.context.view_layer.update()
    ob.matrix_world = want
    return ob


def prepare_rig(arm, action_name):
    """Lepas action aset, siapkan pose bersih."""
    arm.animation_data_clear()
    arm.data.pose_position = "POSE"
    reset_pose(arm)
    bpy.context.view_layer.update()
    return arm


# ---------------------------------------------------------------------------
# shot 010 — aerial Bunaken
# ---------------------------------------------------------------------------


def build_010():
    lib.wipe()
    scn = lib.setup_scene("scene-1_shot-010_bunaken-aerial", 96)
    ensure_engine(scn)

    det = append(P_ISLAND, "ENV_island-detail")
    if not any(o.name.startswith("ENV_surface_pier") for o in det):
        append(P_ISLAND, "ENV_island-detail_context")
    print("island-detail objek:", len(det))

    # bidang air diperbesar sampai Manado Tua (x -7154) masuk horizon
    sea = bpy.data.objects.get("ENV_detail_sea-surface")
    if sea:
        mw = sea.matrix_world.copy()
        inv = mw.inverted()
        for v in sea.data.vertices:
            w = mw @ v.co
            w.x *= 20.0
            w.y *= 8.0
            v.co = inv @ w
        bpy.context.view_layer.update()
        print("sea-surface diperbesar:", [round(x, 0) for x in sea.dimensions])

    sun(scn, energy=3.6, angle=3.0, rot=(76, 0, 52), color=(1.0, 0.90, 0.74))
    world(scn, "#F2E9DC", strength=0.85, name="WLD_s1_010")

    cam = make_cam(
        "CAM_shot-010_drone",
        (500.0, -380.0, 148.0),
        (10.0, 25.0, 26.0),
        lens=30.0,
        clip_end=60000.0,
    )
    key_cam(
        cam,
        [
            (1, (500.0, -380.0, 148.0), (10.0, 25.0, 26.0)),
            (48, (415.0, -315.0, 134.0), (2.0, 20.0, 25.0)),
            (96, (330.0, -250.0, 120.0), (-4.0, 16.0, 24.0)),
        ],
    )
    scn.frame_set(1)
    finish("s1-010", "scene-1_shot-010_bunaken-aerial_v001.blend", preview_frame=1)


# ---------------------------------------------------------------------------
# shot 020 — turun ke permukaan air
# ---------------------------------------------------------------------------


def ripple_water(mat, scale=3.0, strength=0.35, roughness=0.28, hexcol=None, spec=0.22):
    """Beri riak halus pada material air (salinan lokal milik shot, bukan aset)."""
    if mat is None:
        return
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf is None:
        return
    tex = nt.nodes.new("ShaderNodeTexCoord")
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = scale
    if "Detail" in noise.inputs:
        noise.inputs["Detail"].default_value = 4.0
    bmp = nt.nodes.new("ShaderNodeBump")
    bmp.inputs["Strength"].default_value = strength
    nt.links.new(tex.outputs["Object"], noise.inputs["Vector"])
    nt.links.new(noise.outputs["Fac"], bmp.inputs["Height"])
    nt.links.new(bmp.outputs["Normal"], bsdf.inputs["Normal"])
    bsdf.inputs["Roughness"].default_value = roughness
    spec_in = bsdf.inputs.get("Specular IOR Level") or bsdf.inputs.get("Specular")
    if spec_in is not None:
        spec_in.default_value = spec
    if hexcol:
        bsdf.inputs["Base Color"].default_value = lib.srgb(hexcol)
    mat.diffuse_color = bsdf.inputs["Base Color"].default_value
    return mat


def underwater_fog(scn, size=460.0, top=8.0, bottom=-70.0):
    """Kotak volumetrik air memakai material volume look dev (SHD_water_volume)."""
    p = ASSETS + "/look/scene-1-look_v002.blend"
    name = "SHD_water_volume"
    if name not in bpy.data.materials:
        with bpy.data.libraries.load(p, link=False) as (src, dst):
            dst.materials = [n for n in src.materials if n == name]
    mat = bpy.data.materials.get(name)
    if mat is None:
        print("material volume tidak ada")
        return None
    mat.use_fake_user = True
    r = size * 0.5
    mesh = bpy.data.meshes.new("FX_water_volume")
    z0, z1 = bottom, top
    verts = [
        (-r, -r, z0), (r, -r, z0), (r, r, z0), (-r, r, z0),
        (-r, -r, z1), (r, -r, z1), (r, r, z1), (-r, r, z1),
    ]
    faces = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    mesh.from_pydata(verts, [], faces)
    mesh.materials.append(mat)
    mesh.update()
    ob = bpy.data.objects.new("FX_water_volume", mesh)
    scn.collection.objects.link(ob)
    return ob


def build_020():
    lib.wipe()
    scn = lib.setup_scene("scene-1_shot-020_turun-permukaan", 96)
    ensure_engine(scn)

    append(P_SURFACE, "ENV_surface")
    water = bpy.data.objects.get("ENV_surface_water-placeholder")
    if water and water.data.materials:
        ripple_water(water.data.materials[0], roughness=0.14, hexcol="#1FA3A3")
        print("air diberi riak:", water.data.materials[0].name)

    boat = append(P_BOATS, "PRP_boats")
    ctl = root_empty("CTL_boat-pass", (40.0, -18.0, 0.0))
    adopt(boat, ctl)
    ctl.rotation_euler = (0.0, 0.0, math.radians(214.0))
    set_interp("LINEAR")
    ctl.keyframe_insert("location", frame=1)
    ctl.rotation_euler = (0.0, 0.0, math.radians(214.0))
    ctl.keyframe_insert("rotation_euler", frame=1)
    ctl.location = (10.0, -28.0, 0.0)
    ctl.keyframe_insert("location", frame=96)

    sun(scn, energy=4.0, angle=3.0, rot=(66, 0, 46), color=(1.0, 0.91, 0.76))
    world(scn, "#DCEBE6", strength=1.0, name="WLD_s1_020")

    cam = make_cam(
        "CAM_shot-020_descend",
        (25.0, -80.0, 12.5),
        (25.0, -23.0, 1.2),
        lens=28.0,
        clip_end=8000.0,
    )
    key_cam(
        cam,
        [
            (1, (25.0, -80.0, 12.5), (25.0, -23.0, 1.2)),
            (56, (25.0, -76.0, 5.8), (25.0, -23.0, 1.3)),
            (96, (25.0, -72.0, 1.15), (25.0, -25.0, 1.6)),
        ],
    )
    scn.frame_set(1)
    finish("s1-020", "scene-1_shot-020_turun-permukaan_v001.blend", preview_frame=1)


# ---------------------------------------------------------------------------
# shot 030 — terumbu padat
# ---------------------------------------------------------------------------


def build_030():
    lib.wipe()
    scn = lib.setup_scene("scene-1_shot-030_terumbu", 96)
    ensure_engine(scn)

    reef = append(P_REEF, "ENV_reef-dense")
    print("reef-dense objek:", len(reef))

    # dasar pasir diperbesar supaya tepi patch 26 m tidak terlihat sebagai garis
    seabed = bpy.data.objects.get("ENV_dense_seabed")
    if seabed:
        mw = seabed.matrix_world.copy()
        inv = mw.inverted()
        for v in seabed.data.vertices:
            w = mw @ v.co
            w.x *= 20.0
            w.y *= 20.0
            v.co = inv @ w
        bpy.context.view_layer.update()
        print("seabed diperbesar:", [round(x, 0) for x in seabed.dimensions])

    # pasir digelapkan sedikit supaya tidak memantulkan cahaya permukaan
    sand = bpy.data.materials.get("MAT_dense_sand")
    if sand and sand.use_nodes:
        ramp = next((n for n in sand.node_tree.nodes if n.type == "VALTORGB"), None)
        if ramp:
            for el in ramp.color_ramp.elements:
                c = el.color
                el.color = (c[0] * 0.50, c[1] * 0.55, c[2] * 0.60, 1.0)
        bsdf = next((n for n in sand.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if bsdf:
            bsdf.inputs["Roughness"].default_value = 0.92

    # ikan cakalang: goyang halus + hanyut pelan searah sumbu tubuh
    set_interp("BEZIER")
    for ob in [o for o in bpy.data.objects if "cakalang" in o.name]:
        dim = ob.dimensions.copy()
        axis = "x" if dim.x >= dim.y else "y"
        base = ob.location.copy()
        base_rot = ob.rotation_euler.copy()
        for frame, off, sway in ((1, 0.0, 0.0), (32, 0.35, 4.0), (64, 0.75, -4.0), (96, 1.10, 0.0)):
            loc = base.copy()
            loc.z += 0.06 * math.sin(frame * 0.09)
            if axis == "x":
                loc.x += off
            else:
                loc.y += off
            ob.location = loc
            ob.rotation_euler = (
                base_rot.x,
                base_rot.y,
                base_rot.z + math.radians(sway * 0.5),
            )
            ob.keyframe_insert("location", frame=frame)
            ob.keyframe_insert("rotation_euler", frame=frame)

    sun(scn, energy=3.6, angle=5.0, rot=(16, 0, 34), color=(0.82, 0.95, 1.0))
    world(scn, "#0F5C63", strength=1.15, name="WLD_s1_030")
    lib.add_fill(energy=120.0, size=8.0, loc=(-3.0, -3.0, -1.0), target=(0, 0, -4.0))
    fog = underwater_fog(scn)
    print("fog:", fog.name if fog else None)

    cam = make_cam(
        "CAM_shot-030_track",
        (0.0, 8.5, -3.35),
        (0.3, 2.0, -3.95),
        lens=24.0,
        clip_end=300.0,
    )
    key_cam(
        cam,
        [
            (1, (0.0, 8.5, -3.35), (0.3, 2.0, -3.95)),
            (96, (0.6, 4.0, -3.45), (0.9, -2.4, -4.00)),
        ],
        mode="LINEAR",
    )
    set_interp("BEZIER")
    scn.frame_set(1)
    finish("s1-030", "scene-1_shot-030_terumbu_v001.blend", preview_frame=48)


# ---------------------------------------------------------------------------
# shot 040 — penyu melintas
# ---------------------------------------------------------------------------


def build_040():
    lib.wipe()
    scn = lib.setup_scene("scene-1_shot-040_penyu", 72)
    ensure_engine(scn)

    append(P_REEF, "ENV_reef-dense")
    tut = append(P_TURTLE, "ENV_turtle", purge=False)
    ctl = bpy.data.objects.get("CTL_turtle")
    if ctl is None:
        raise RuntimeError("CTL_turtle tidak ada")
    print("turtle objek:", len(tut))

    x0, x1 = -4.6, 4.6
    keys = [(1, x0), (24, x0 + 3.07), (48, x0 + 6.13), (72, x1)]
    set_interp("BEZIER")
    for frame, tx in keys:
        t = (frame - 1) / 71.0
        ctl.location = (tx, 1.0 - 0.5 * t, -2.95 + 0.30 * t)
        ctl.rotation_euler = (
            math.radians(-4.0 * t),
            math.radians(3.0 * math.sin(t * 6.0)),
            math.radians(98.0 - 14.0 * t),
        )
        ctl.keyframe_insert("location", frame=frame)
        ctl.keyframe_insert("rotation_euler", frame=frame)

    sun(scn, energy=3.4, angle=5.0, rot=(18, 0, 30), color=(0.80, 0.94, 1.0))
    world(scn, "#0F5C63", strength=1.15, name="WLD_s1_040")
    lib.add_fill(energy=110.0, size=7.0, loc=(-3.0, -4.0, -1.2), target=(0, 0, -3.0))
    underwater_fog(scn)

    # karang latar supaya penyu benar-benar "melewati karang"
    corals = sorted([o for o in bpy.data.objects if "_coral_" in o.name], key=lambda o: o.name)
    for idx, (pos, scl) in enumerate(
        [
            ((1.6, 3.8, -5.0), 2.0),
            ((-1.6, 4.6, -5.0), 1.7),
            ((3.4, 2.4, -5.0), 1.8),
            ((-3.6, 3.1, -5.0), 1.6),
            ((0.2, 6.4, -5.0), 2.1),
        ]
    ):
        if idx < len(corals):
            corals[idx].location = pos
            corals[idx].scale = (scl, scl, scl)
            corals[idx].rotation_euler.z += math.radians(17 * idx)

    cam = make_cam(
        "CAM_shot-040_follow", (-3.8, -3.9, -1.35), (-4.1, 1.0, -2.85), lens=40.0
    )
    ks = []
    for frame, tx in keys:
        t = (frame - 1) / 71.0
        ks.append(
            (
                frame,
                (tx + 0.7, -3.9 + 0.2 * t, -1.35 - 0.05 * t),
                (tx + 0.4, 1.0 - 0.4 * t, -3.00 + 0.30 * t),
            )
        )
    key_cam(cam, ks)
    scn.frame_set(1)
    finish("s1-040", "scene-1_shot-040_penyu_v001.blend", preview_frame=36)


# ---------------------------------------------------------------------------
# shot 050 — Nara menyelam
# ---------------------------------------------------------------------------


NARA_SWIM = {
    "spine": (7, 0, 0),
    "chest": (4, 0, 0),
    "neck": (-10, 0, 0),
    "head": (-8, 0, 0),
    "shoulder.L": (-4, 0, 0),
    "upper_arm.L": (-96, 0, 12),
    "fore_arm.L": (-24, 0, 0),
    "hand.L": (-6, 0, 0),
    "shoulder.R": (-4, 0, 0),
    "upper_arm.R": (-90, 0, -14),
    "fore_arm.R": (-30, 0, 0),
    "hand.R": (-8, 0, 0),
    "thigh.L": (8, 0, -2),
    "shin.L": (12, 0, 0),
    "foot.L": (-16, 0, 0),
    "thigh.R": (-6, 0, 2),
    "shin.R": (16, 0, 0),
    "foot.R": (-12, 0, 0),
}


def build_050():
    lib.wipe()
    scn = lib.setup_scene("scene-1_shot-050_nara-dive", 96)
    ensure_engine(scn)

    append(P_REEF, "ENV_reef-dense")
    tut = append(P_TURTLE, "ENV_turtle", purge=False)
    nara = append(P_NARA, "CHR_nara", purge=True)
    arm = bpy.data.objects.get("CHR_nara_rig")
    if arm is None:
        raise RuntimeError("CHR_nara_rig tidak ada")

    # karang pembuka di depan lensa: Nara muncul dari baliknya
    corals = sorted([o for o in bpy.data.objects if "_coral_" in o.name], key=lambda o: o.name)
    for idx, (pos, scl) in enumerate(
        [((-2.55, -2.05, -5.05), 2.6), ((-0.30, -2.60, -5.02), 1.5), ((2.6, -2.9, -5.05), 1.7)]
    ):
        if idx < len(corals):
            corals[idx].location = pos
            corals[idx].scale = (scl, scl, scl)

    # penyu di belakang (soft focus), sejajar arah pandang kamera
    ctl_t = bpy.data.objects.get("CTL_turtle")
    ctl_t.location = (-4.6, 4.7, -2.50)
    ctl_t.rotation_euler = (math.radians(2), 0.0, math.radians(96))
    set_interp("LINEAR")
    ctl_t.keyframe_insert("location", frame=1)
    ctl_t.keyframe_insert("rotation_euler", frame=1)
    ctl_t.location = (-5.3, 5.5, -2.42)
    ctl_t.keyframe_insert("location", frame=96)

    prepare_rig(arm, "CHR_act_s1-050")
    arm.rotation_mode = "XYZ"
    arm.rotation_euler = (math.radians(70), 0.0, math.radians(95))
    arm.location = (-3.25, 0.95, -3.40)
    set_interp("BEZIER")
    arm.keyframe_insert("location", frame=1)
    arm.rotation_euler = (math.radians(70), 0.0, math.radians(95))
    arm.keyframe_insert("rotation_euler", frame=1)

    breathe = dict(NARA_SWIM)
    swim_a = dict(NARA_SWIM)
    swim_b = dict(NARA_SWIM)
    swim_b["upper_arm.L"] = (-104, 0, 14)
    swim_b["upper_arm.R"] = (-82, 0, -16)
    swim_b["thigh.L"] = (12, 0, -2)
    swim_b["thigh.R"] = (-10, 0, 2)
    key_pose(arm, 1, swim_a, list(NARA_SWIM.keys()))
    key_pose(arm, 48, swim_b, list(NARA_SWIM.keys()))
    key_pose(arm, 96, swim_a, list(NARA_SWIM.keys()))
    arm.location = (-1.70, 0.80, -3.25)
    arm.keyframe_insert("location", frame=96)

    sun(scn, energy=3.2, angle=5.0, rot=(14, 0, 26), color=(0.82, 0.94, 1.0))
    world(scn, "#0F5C63", strength=1.1, name="WLD_s1_050")
    lib.add_fill(energy=140.0, size=6.0, loc=(-1.0, -6.0, -0.6), target=(-2.2, 0.6, -3.2))
    underwater_fog(scn)

    cam = make_cam(
        "CAM_shot-050_medium", (1.0, -4.7, -2.95), (-2.4, 0.9, -3.30), lens=45.0
    )
    key_cam(
        cam,
        [
            (1, (1.0, -4.7, -2.95), (-2.4, 0.9, -3.30)),
            (96, (0.4, -4.4, -2.90), (-1.2, 0.8, -3.25)),
        ],
    )
    cam.data.dof.use_dof = True
    cam.data.dof.aperture_fstop = 4.0
    focus = root_empty("EMPTY_focus-nara", (-2.4, 0.9, -3.3))
    adopt([focus], arm)
    cam.data.dof.focus_object = focus

    scn.frame_set(1)
    finish("s1-050", "scene-1_shot-050_nara-dive_v001.blend", preview_frame=48)


# ---------------------------------------------------------------------------
# shot 060 — close-up masker + isyarat OK
# ---------------------------------------------------------------------------


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


def face_frame(arm):
    """Arah hadap mendatar karakter + sumbu atas & sisi kanannya (dunia)."""
    R = arm.matrix_world.to_3x3()
    fwd = R @ Vector((0.0, -1.0, 0.0))
    up = R @ Vector((0.0, 0.0, 1.0))
    fh = Vector((fwd.x, fwd.y, 0.0))
    if fh.length < 1e-6:
        fh = Vector((0.0, -1.0, 0.0))
    fh.normalize()
    upn = up.normalized()
    return fh, upn, fh.cross(upn)


def yaw_of(direction):
    return math.degrees(math.atan2(direction.x, -direction.y))


def attach_gear(obj, arm, bone, world_pos, yaw_deg, pitch_deg=0.0, roll_deg=0.0):
    """Tempel objek ke bone dengan orientasi dunia yang ditentukan manual."""
    if obj is None:
        return None
    want = (
        Matrix.Translation(Vector(world_pos))
        @ Matrix.Rotation(math.radians(yaw_deg), 4, "Z")
        @ Matrix.Rotation(math.radians(pitch_deg), 4, "X")
        @ Matrix.Rotation(math.radians(roll_deg), 4, "Y")
    )
    return bone_parent(obj, arm, bone, want)


def attach_mask(arm, bone, translate, rot_z_deg, scale=1.0):
    mask = bpy.data.objects.get("PRP_divegear_mask")
    if mask is None:
        return None
    bpy.context.view_layer.update()
    basis = arm.matrix_world @ arm.pose.bones[bone].matrix
    want = basis @ Matrix.Translation(Vector(translate)) @ Matrix.Rotation(
        math.radians(rot_z_deg), 4, "Z"
    )
    want = want @ Matrix.Diagonal(Vector((scale, scale, scale, 1.0)))
    bone_parent(mask, arm, bone, want)
    return mask


def build_060():
    lib.wipe()
    scn = lib.setup_scene("scene-1_shot-060_nara-ok", 72)
    ensure_engine(scn)

    append(P_REEF, "ENV_reef-dense")
    nara = append(P_NARA, "CHR_nara", purge=True)
    gear = append(P_DIVEGEAR, "PRP_divegear", purge=True)
    arm = bpy.data.objects.get("CHR_nara_rig")
    if arm is None:
        raise RuntimeError("CHR_nara_rig tidak ada")

    prepare_rig(arm, "CHR_act_s1-060")
    arm.rotation_mode = "XYZ"
    arm.location = (0.0, 0.0, -1.35)
    arm.rotation_euler = (0.0, 0.0, math.radians(-16))
    bpy.context.view_layer.update()

    pose_a = dict(NARA_FLOAT)
    pose_b = dict(NARA_FLOAT)
    pose_b["hand.R"] = (-26, 0, 34)
    pose_b["fore_arm.R"] = (-90, 0, 0)
    key_pose(arm, 1, pose_a, list(NARA_FLOAT.keys()))
    key_pose(arm, 30, pose_b, list(NARA_FLOAT.keys()))
    key_pose(arm, 72, pose_a, list(NARA_FLOAT.keys()))
    scn.frame_set(1)
    bpy.context.view_layer.update()

    fh, upn, her_right = face_frame(arm)
    face_c = bone_world(arm, "head", 0.56) + upn * 0.005
    yaw = yaw_of(fh)
    # fin tidak dipakai di shot ini
    for nm in ("PRP_divegear_fin_L", "PRP_divegear_fin_R"):
        ob = bpy.data.objects.get(nm)
        if ob:
            bpy.data.objects.remove(ob, do_unlink=True)
    mask = attach_gear(
        bpy.data.objects.get("PRP_divegear_mask"),
        arm,
        "head",
        face_c + fh * 0.095 + upn * 0.012,
        yaw,
        pitch_deg=0.0,
    )
    print("masker terpasang:", mask is not None, [round(v, 3) for v in face_c])
    sn = bpy.data.objects.get("PRP_divegear_snorkel")
    if sn:
        attach_gear(sn, arm, "head", face_c + her_right * 0.105 - fh * 0.03, yaw + 8.0, roll_deg=-10.0)

    sun(scn, energy=3.4, angle=6.0, rot=(20, 0, 18), color=(0.86, 0.95, 1.0))
    world(scn, "#0F5C63", strength=1.05, name="WLD_s1_060")
    lib.add_fill(energy=90.0, size=3.0, loc=(1.2, -2.0, 0.4), target=(0.0, 0.0, 0.3))
    underwater_fog(scn, size=90.0, top=6.0, bottom=-30.0)

    bpy.context.view_layer.update()
    cam_loc = face_c + fh * 1.95 + her_right * 0.30 + upn * 0.02
    cam = make_cam("CAM_shot-060_cu", cam_loc, face_c + upn * 0.01, lens=85.0, clip_end=50.0)
    cam.data.dof.use_dof = True
    cam.data.dof.aperture_fstop = 5.6
    focus = root_empty("EMPTY_focus-face", face_c)
    adopt([focus], arm)
    cam.data.dof.focus_object = focus
    print("kamera cu:", [round(v, 2) for v in cam_loc], "wajah:", [round(v, 2) for v in face_c])

    scn.frame_set(1)
    finish("s1-060", "scene-1_shot-060_nara-ok_v001.blend", preview_frame=30)


# ---------------------------------------------------------------------------
# shot 070 — Nara naik ke perahu
# ---------------------------------------------------------------------------


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
    lib.wipe()
    scn = lib.setup_scene("scene-1_shot-070_nara-naik", 96)
    ensure_engine(scn)

    append(P_SURFACE, "ENV_surface")
    boat = append(P_BOATS, "PRP_boats")
    ctl = root_empty("CTL_boat-dive", (14.0, -35.0, 0.0))
    adopt(boat, ctl)
    ctl.rotation_euler = (0.0, 0.0, math.radians(6.0))
    bpy.context.view_layer.update()

    nara = append(P_NARA, "CHR_nara", purge=True)
    append(P_DIVEGEAR, "PRP_divegear", purge=True)
    for nm in ("PRP_divegear_fin_L", "PRP_divegear_fin_R"):
        ob = bpy.data.objects.get(nm)
        if ob:
            bpy.data.objects.remove(ob, do_unlink=True)
    arm = bpy.data.objects.get("CHR_nara_rig")
    if arm is None:
        raise RuntimeError("CHR_nara_rig tidak ada")

    # dek perahu: lokal (-2.30, 0.0, 0.30) -> dunia
    deck_world = ctl.matrix_world @ Vector((-2.30, 0.0, 0.30))
    arm.location = deck_world
    arm.rotation_mode = "XYZ"
    arm.rotation_euler = (0.0, 0.0, math.radians(-16.0))

    prepare_rig(arm, "CHR_act_s1-070")
    set_interp("BEZIER")
    pose_a = dict(NARA_CLIMB)
    pose_b = dict(NARA_CLIMB)
    pose_b["upper_arm.L"] = (-96, 0, 20)
    pose_b["fore_arm.L"] = (-84, 0, 0)
    pose_b["upper_arm.R"] = (-92, 0, -22)
    pose_b["fore_arm.R"] = (-92, 0, 0)
    pose_c = dict(NARA_CLIMB)
    pose_c["upper_arm.L"] = (-52, 0, 24)
    pose_c["fore_arm.L"] = (-58, 0, 0)
    pose_c["upper_arm.R"] = (-46, 0, -26)
    pose_c["fore_arm.R"] = (-64, 0, 0)
    pose_c["head"] = (-10, 0, 6)
    pose_c["neck"] = (-8, 0, 4)
    key_pose(arm, 1, pose_a, list(NARA_CLIMB.keys()))
    key_pose(arm, 40, pose_b, list(NARA_CLIMB.keys()))
    key_pose(arm, 96, pose_c, list(NARA_CLIMB.keys()))
    scn.frame_set(1)
    bpy.context.view_layer.update()
    # masker sudah dilepas: dipegang tangan kanan
    hand_pos = bone_world(arm, "hand.R", 0.75)
    fh, upn, her_right = face_frame(arm)
    mask = attach_gear(
        bpy.data.objects.get("PRP_divegear_mask"),
        arm,
        "hand.R",
        hand_pos + fh * 0.10,
        yaw_of(fh) + 26.0,
        pitch_deg=-24.0,
    )
    print("masker di tangan:", mask is not None, [round(v, 2) for v in hand_pos])

    sun(scn, energy=4.2, angle=3.0, rot=(64, 0, 40), color=(1.0, 0.92, 0.78))
    world(scn, "#E3EFEA", strength=1.0, name="WLD_s1_070")

    cam = make_cam(
        "CAM_shot-070_low",
        (deck_world.x + 0.10, -40.4, 0.60),
        (deck_world.x, -35.0, 1.50),
        lens=35.0,
        clip_end=3000.0,
    )
    head_c = bone_world(arm, "head", 0.5)
    key_cam(
        cam,
        [
            (1, (deck_world.x + 0.10, -40.4, 0.60), (head_c.x, head_c.y, head_c.z - 0.30)),
            (96, (deck_world.x - 0.40, -39.9, 0.66), (head_c.x, head_c.y, head_c.z - 0.24)),
        ],
    )
    scn.frame_set(1)
    finish(
        "s1-070",
        "scene-1_shot-070_nara-naik_v001.blend",
        preview_frame=72,
        above_water=True,
    )


# ---------------------------------------------------------------------------
# shot 080 — Pak Daniel memperbaiki jaring
# ---------------------------------------------------------------------------


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


def box(name, size, center, mat, rot_z=0.0):
    """Kotak sederhana dari from_pydata (untuk bangku/teras)."""
    sx, sy, sz = [v * 0.5 for v in size]
    cx, cy, cz = center
    verts = [
        (-sx, -sy, -sz), (sx, -sy, -sz), (sx, sy, -sz), (-sx, sy, -sz),
        (-sx, -sy, sz), (sx, -sy, sz), (sx, sy, sz), (-sx, sy, sz),
    ]
    faces = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.materials.append(mat)
    mesh.update()
    ob = bpy.data.objects.new(name, mesh)
    ob.location = (cx, cy, cz)
    ob.rotation_euler = (0.0, 0.0, math.radians(rot_z))
    bpy.context.scene.collection.objects.link(ob)
    return ob


def append_any(path, preferred=None):
    """Append koleksi pertama (atau `preferred`) dari file aset."""
    with bpy.data.libraries.load(path, link=False) as (src, dst):
        names = list(src.collections)
        pick = preferred if preferred in names else (names[0] if names else None)
        if pick is None:
            return []
        dst.collections = [pick]
    coll = bpy.data.collections.get(pick)
    if coll is not None and coll.name not in [c.name for c in bpy.context.scene.collection.children]:
        bpy.context.scene.collection.children.link(coll)
    objs = lib.live_objects(list(coll.objects)) if coll else []
    lib.purge_lights_cameras(objs)
    return lib.live_objects(objs)


def build_080():
    lib.wipe()
    scn = lib.setup_scene("scene-1_shot-080_daniel-jaring", 72)
    ensure_engine(scn)

    append(P_SURFACE, "ENV_surface")
    dan = append(P_DANIEL, "CHR_daniel", purge=True)
    gear = append(P_GEAR, "PRP_gear", purge=True)
    sign = append_any(ASSETS + "/props/dive-shop-sign.blend", "PRP_sign")
    print("papan nama:", [o.name for o in sign])
    arm = bpy.data.objects.get("CHR_daniel_rig")
    if arm is None:
        raise RuntimeError("CHR_daniel_rig tidak ada")

    # teras kayu di depan dive shop (set dressing shot, bukan aset)
    deck_mat = lib.material("MAT_terrace_wood", "#C9A77C", roughness=0.82)
    lib.make_plane("PRP_terrace_deck", 15.0, 0.62, deck_mat, center=(8.5, -3.4))
    for i, (px, py) in enumerate([(2.2, -6.2), (7.4, -6.2), (14.6, -6.2), (2.2, -1.0), (14.6, -1.0)]):
        box("PRP_terrace_post_%02d" % i, (0.24, 0.24, 0.62), (px, py, 0.31), deck_mat)
    box("PRP_bench_seat", (1.15, 0.52, 0.10), (8.0, -4.35, 1.07), deck_mat)
    for i, (bx, by) in enumerate([(7.55, -4.55), (8.45, -4.55), (7.55, -4.15), (8.45, -4.15)]):
        box("PRP_bench_leg_%d" % i, (0.08, 0.08, 0.40), (bx, by, 0.87), deck_mat)

    arm.location = (8.0, -4.35, 0.17)
    arm.rotation_mode = "XYZ"
    arm.rotation_euler = (0.0, 0.0, math.radians(20.0))
    prepare_rig(arm, "CHR_act_s1-080")
    set_interp("BEZIER")

    pose_a = dict(DANIEL_SIT)
    pose_b = dict(DANIEL_SIT)
    pose_b["fore_arm_L"] = (-48, 0, 0)
    pose_b["fore_arm_R"] = (-70, 0, 0)
    pose_b["head"] = (-4, 0, 8)
    key_pose(arm, 1, pose_a, list(DANIEL_SIT.keys()))
    key_pose(arm, 24, pose_b, list(DANIEL_SIT.keys()))
    key_pose(arm, 48, pose_a, list(DANIEL_SIT.keys()))
    key_pose(arm, 72, pose_b, list(DANIEL_SIT.keys()))

    # jaring di pangkuan, keranjang di lantai teras
    net = bpy.data.objects.get("PRP_gear_fishnet")
    if net:
        net.location = (8.0, -4.62, 1.16)
        net.rotation_euler = (math.radians(-4), 0.0, math.radians(12))
        net.scale = (0.72, 0.72, 0.72)
    basket = bpy.data.objects.get("PRP_gear_basket")
    if basket:
        basket.location = (9.15, -4.85, 0.62)
    flo = bpy.data.objects.get("PRP_gear_float")
    if flo:
        flo.location = (7.05, -4.35, 0.68)
    for ob in sign:
        if ob.parent is None:
            ob.location = (ob.location.x + 4.4, ob.location.y - 3.0, ob.location.z + 0.62)

    sun(scn, energy=3.8, angle=4.0, rot=(52, 0, 34), color=(1.0, 0.93, 0.80))
    world(scn, "#F2E9DC", strength=0.9, name="WLD_s1_080")

    cam = make_cam(
        "CAM_shot-080_wide", (9.3, -12.4, 1.72), (8.0, -4.1, 1.22), lens=40.0, clip_end=3000.0
    )
    key_cam(cam, [(1, (9.3, -12.4, 1.72), (8.0, -4.1, 1.22))], mode="LINEAR")
    set_interp("BEZIER")
    scn.frame_set(1)
    finish(
        "s1-080",
        "scene-1_shot-080_daniel-jaring_v001.blend",
        preview_frame=24,
        above_water=True,
    )


# ---------------------------------------------------------------------------
# shot 090 — anak-anak berlari di dermaga
# ---------------------------------------------------------------------------


def build_090():
    lib.wipe()
    scn = lib.setup_scene("scene-1_shot-090_anak-dermaga", 72)
    ensure_engine(scn)

    append(P_SURFACE, "ENV_surface")
    crowd = append(P_CROWD, "CHR_crowd", purge=False)
    kids = [bpy.data.objects[n] for n in ("CRW_09", "CRW_10", "CRW_11", "CRW_12")]
    deck_z = 1.26
    starts = [(0.95, -44.0), (-0.85, -45.4), (0.35, -50.0), (-0.55, -51.6)]
    set_interp("BEZIER")
    for kid, (sx, sy) in zip(kids, starts):
        kid.rotation_mode = "XYZ"
        kid.rotation_euler = (0.0, 0.0, math.radians(180.0))
        for f, off in ((1, 0.0), (18, 2.4), (36, 5.0), (54, 7.6), (72, 9.6)):
            kid.location = (sx + 0.10 * math.sin(f * 0.35), sy + off, deck_z + 0.035 * abs(math.sin(f * 0.5)))
            kid.rotation_euler = (0.0, 0.0, math.radians(180.0) + math.radians(3.0 * math.sin(f * 0.22)))
            kid.keyframe_insert("location", frame=f)
            kid.keyframe_insert("rotation_euler", frame=f)

    sun(scn, energy=3.9, angle=3.0, rot=(60, 0, 38), color=(1.0, 0.92, 0.78))
    world(scn, "#E8F0EC", strength=0.95, name="WLD_s1_090")

    cam = make_cam(
        "CAM_shot-090_handheld", (0.1, -24.5, 2.30), (0.0, -34.0, 1.75), lens=28.0, clip_end=3000.0
    )
    keys = []
    for f in range(1, 73, 6):
        t = (f - 1) / 71.0
        jx = 0.055 * math.sin(f * 0.70) + 0.03 * math.sin(f * 1.9)
        jz = 0.045 * math.sin(f * 0.55 + 1.1)
        loc = (0.1 + jx, -24.5 - 1.6 * t, 2.30 + jz)
        tgt = (0.0 + jx * 1.6, -34.0 - 1.2 * t, 1.75 + jz * 1.4)
        keys.append((f, loc, tgt))
    key_cam(cam, keys, mode="BEZIER")
    scn.frame_set(1)
    finish("s1-090", "scene-1_shot-090_anak-dermaga_v001.blend", preview_frame=36)


# ---------------------------------------------------------------------------
# shot 100 — Nara di ujung dermaga + fade hitam
# ---------------------------------------------------------------------------


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


def fade_to_black(scn, f_start, f_end):
    """Fade ke hitam lewat compositor (Blender 5.x: compositing_node_group)."""
    try:
        for ngn in list(bpy.data.node_groups):
            if ngn.name.startswith("COMP_shot"):
                bpy.data.node_groups.remove(ngn)
        ng = bpy.data.node_groups.new("COMP_shot-fade", "CompositorNodeTree")
        ng.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
        rl = ng.nodes.new("CompositorNodeRLayers")
        ex = ng.nodes.new("CompositorNodeExposure")
        out = ng.nodes.new("NodeGroupOutput")
        rl.location = (-400, 0)
        ex.location = (-120, 0)
        out.location = (160, 0)
        ng.links.new(rl.outputs["Image"], ex.inputs["Image"])
        ng.links.new(ex.outputs["Image"], out.inputs[0])
        scn.compositing_node_group = ng
        scn.use_nodes = True
        set_interp("LINEAR")
        sock = ex.inputs["Exposure"]
        sock.default_value = 0.0
        sock.keyframe_insert("default_value", frame=f_start)
        sock.default_value = -10.0
        sock.keyframe_insert("default_value", frame=f_end)
        set_interp("BEZIER")
        return "compositor-exposure"
    except Exception as exc:
        print("compositor fade gagal:", repr(exc))
        return "gagal"


def build_100():
    lib.wipe()
    scn = lib.setup_scene("scene-1_shot-100_nara-ujung-dermaga", 72)
    ensure_engine(scn)

    append(P_SURFACE, "ENV_surface")
    nara = append(P_NARA, "CHR_nara", purge=True)
    arm = bpy.data.objects.get("CHR_nara_rig")
    if arm is None:
        raise RuntimeError("CHR_nara_rig tidak ada")

    arm.location = (-0.35, -99.0, 1.26)
    arm.rotation_mode = "XYZ"
    arm.rotation_euler = (0.0, 0.0, math.radians(-6.0))
    arm.scale = (1.0, 1.0, 1.0)
    prepare_rig(arm, "CHR_act_s1-100")
    set_interp("BEZIER")
    pose_a = dict(NARA_STAND)
    pose_b = dict(NARA_STAND)
    pose_b["chest"] = (2, 0, 0)
    pose_b["head"] = (0, 0, -6)
    pose_b["upper_arm.L"] = (6, 0, 7)
    pose_b["upper_arm.R"] = (5, 0, -7)
    key_pose(arm, 1, pose_a, list(NARA_STAND.keys()))
    key_pose(arm, 36, pose_b, list(NARA_STAND.keys()))
    key_pose(arm, 72, pose_a, list(NARA_STAND.keys()))

    sun(scn, energy=3.4, angle=4.0, rot=(70, 0, 46), color=(1.0, 0.86, 0.68))
    world(scn, "#F0E6D6", strength=0.9, name="WLD_s1_100")

    head_c = bone_world(arm, "head", 0.5)
    cam = make_cam(
        "CAM_shot-100_static",
        (-0.30, -91.6, 2.45),
        (head_c.x, head_c.y, head_c.z - 0.28),
        lens=50.0,
        clip_end=4000.0,
    )
    key_cam(cam, [(1, (-0.30, -91.6, 2.45), (head_c.x, head_c.y, head_c.z - 0.28))])
    mode = fade_to_black(scn, 54, 72)
    print("fade mode:", mode)
    scn.frame_set(1)
    finish("s1-100", "scene-1_shot-100_nara-ujung-dermaga_v001.blend", preview_frame=36)


# ---------------------------------------------------------------------------
# dispatcher
# ---------------------------------------------------------------------------


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


def main(which):
    which = str(which)
    if which not in BUILDERS:
        raise SystemExit("shot tidak dikenal: %s" % which)
    print("=== BUILD s1-%s ===" % which)
    BUILDERS[which]()


if "SHOT_TO_BUILD" in globals():
    main(globals()["SHOT_TO_BUILD"])

"""
Membangun tiga shot Scene 4 yang tidak membutuhkan model karakter:
  shot 020  buoy dipasang dari permukaan (perahu + mooring buoy)
  shot 030  kerangka transplantasi karang ditanam di dasar
  shot 070  penyu kembali melewati karang

Hasil: scenes/scene-4_shot-020_buoy-dipasang_v001.blend
       scenes/scene-4_shot-030_kerangka-karang_v001.blend
       scenes/scene-4_shot-070_penyu-kembali_v001.blend

Cara pakai di Blender MCP (satu shot per eksekusi):
    ns = {"__name__": "__main__", "SHOT_TO_BUILD": "020"}
    exec(compile(open(path).read(), path, "exec"), ns)

Aturan yang dipatuhi:
- Tidak memanggil open_mainfile / read_factory_settings (mematikan socket add-on).
- Data Blender di-wipe manual sebelum tiap shot.
- Aset di-APPEND (bukan link) supaya objek bisa dianimasikan.
- EEVEE, 1920x1080, 24 fps, view transform Standard, simpan di frame 1.
- Tanpa tekstur image, tanpa pack, <50 MB.

Catatan: ini previz. World/look dev final tetap milik Vaughn Toy di
assets/look/scene-1-look.blend.
"""

import bpy
import math
import os
from mathutils import Vector

ROOT = r"D:/Tugas Semester 5/Grafika Komputer/Project-Animasi"
ASSETS = ROOT + "/assets"
SCENES = ROOT + "/scenes"
STILLS = ROOT + "/renders/stills"

PAL = {
    "teal": "#1FA3A3",
    "deep": "#0F5C63",
    "reef": "#3E8E6E",
    "orange": "#E4713C",
    "sand": "#E8D5B0",
    "bone": "#F2E9DC",
    "ink": "#06181C",
}

FPS = 24
FRAMES = 96


# ---------------------------------------------------------------------------
# utilitas umum
# ---------------------------------------------------------------------------


def srgb(hexstr):
    h = hexstr.lstrip("#")
    values = [int(h[i : i + 2], 16) / 255.0 for i in (0, 2, 4)]

    def to_linear(u):
        return u / 12.92 if u <= 0.04045 else ((u + 0.055) / 1.055) ** 2.4

    return tuple(to_linear(v) for v in values) + (1.0,)


def material(name, hexcol, roughness=0.6, metallic=0.0, alpha=1.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.use_backface_culling = False
    mat.diffuse_color = srgb(hexcol)
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = srgb(hexcol)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    if alpha < 1.0:
        bsdf.inputs["Alpha"].default_value = alpha
        mat.blend_method = "BLEND"
    spec = bsdf.inputs.get("Specular IOR Level") or bsdf.inputs.get("Specular")
    if spec is not None:
        spec.default_value = 0.4
    return mat


def wipe():
    for db in (
        bpy.data.objects, bpy.data.collections, bpy.data.meshes, bpy.data.materials,
        bpy.data.cameras, bpy.data.lights, bpy.data.worlds, bpy.data.actions,
        bpy.data.armatures, bpy.data.curves, bpy.data.images,
    ):
        for block in list(db):
            try:
                db.remove(block)
            except Exception:
                pass
    # Kalau file yang terbuka adalah file aset yang mau di-append, lepaskan dulu:
    # libraries.load menolak "Cannot load from the current blend file".
    if bpy.data.filepath:
        tmp_dir = os.path.join(ROOT, "renders", "tmp")
        os.makedirs(tmp_dir, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(tmp_dir, "_wipe.blend"))


def setup_scene(name, frame_end=FRAMES):
    scn = bpy.context.scene
    scn.name = name
    scn.render.resolution_x = 1920
    scn.render.resolution_y = 1080
    scn.render.resolution_percentage = 100
    scn.render.fps = FPS
    scn.render.fps_base = 1.0
    scn.view_settings.view_transform = "Standard"
    scn.frame_start = 1
    scn.frame_end = frame_end
    scn.frame_set(1)
    return scn


def append_collection(blend_path, coll_name):
    """Append (copy) satu koleksi dari file aset. Kembalikan daftar objek baru."""
    before = set(bpy.data.objects.keys())
    with bpy.data.libraries.load(blend_path, link=False) as (src, dst):
        if coll_name not in src.collections:
            raise RuntimeError(f"{coll_name} tidak ada di {blend_path}")
        dst.collections = [coll_name]
    coll = dst.collections[0]
    scn = bpy.context.scene
    if coll.name not in scn.collection.children:
        scn.collection.children.link(coll)
    return [bpy.data.objects[n] for n in bpy.data.objects.keys() if n not in before]


def append_collections(blend_path, coll_names):
    objs = []
    for name in coll_names:
        objs.extend(append_collection(blend_path, name))
    return objs


def purge_lights_cameras(objs):
    removed = []
    for obj in list(objs):
        if obj.type in {"LIGHT", "CAMERA"}:
            removed.append(obj.name)
            bpy.data.objects.remove(obj, do_unlink=True)
    return removed


def live_objects(objs):
    """Buang referensi ke objek yang sudah dihapus (StructRNA removed)."""
    names = []
    for obj in objs:
        try:
            names.append(obj.name)
        except ReferenceError:
            pass
    return [bpy.data.objects[n] for n in names if n in bpy.data.objects]


def make_plane(name, size, z, mat, center=(0.0, 0.0)):
    mesh = bpy.data.meshes.new(name)
    s = size * 0.5
    cx, cy = center
    mesh.from_pydata(
        [(cx - s, cy - s, z), (cx + s, cy - s, z), (cx + s, cy + s, z), (cx - s, cy + s, z)],
        [], [(0, 1, 2, 3)],
    )
    mesh.materials.append(mat)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def add_sun(energy=3.2, angle_deg=6.0, rot=(48, 0, 26)):
    light = bpy.data.lights.new("LGT_sun", "SUN")
    light.energy = energy
    light.angle = math.radians(angle_deg)
    obj = bpy.data.objects.new("LGT_sun", light)
    obj.rotation_euler = (math.radians(rot[0]), math.radians(rot[1]), math.radians(rot[2]))
    bpy.context.scene.collection.objects.link(obj)
    return obj


def add_fill(energy=200.0, size=6.0, loc=(-4, -5, 3), target=(0, 0, 0.6)):
    light = bpy.data.lights.new("LGT_fill", "AREA")
    light.energy = energy
    light.size = size
    obj = bpy.data.objects.new("LGT_fill", light)
    obj.location = loc
    obj.rotation_euler = (Vector(target) - Vector(loc)).normalized().to_track_quat(
        "-Z", "Y"
    ).to_euler()
    bpy.context.scene.collection.objects.link(obj)
    return obj


def add_world(name, color, strength=1.0):
    world = bpy.data.worlds.new(name)
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = srgb(color)
    bg.inputs["Strength"].default_value = strength
    bpy.context.scene.world = world
    return world


def look_at(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).normalized().to_track_quat(
        "-Z", "Y"
    ).to_euler()


def make_camera(name, loc, target, lens=40.0):
    cam_data = bpy.data.cameras.new(name)
    cam_data.lens = lens
    obj = bpy.data.objects.new(name, cam_data)
    obj.location = loc
    look_at(obj, target)
    bpy.context.scene.collection.objects.link(obj)
    bpy.context.scene.camera = obj
    return obj


def _linear_keys():
    """Blender 5.x memakai layered action; set default interpolasi lewat preferensi."""
    try:
        bpy.context.preferences.edit.keyframe_new_interpolation_type = "LINEAR"
    except Exception as exc:
        print("tidak bisa set interpolasi linear:", exc)


def key_camera(cam, f0, f1, loc0, loc1, tgt0, tgt1):
    """Dua keyframe kamera dengan interpolasi linear supaya gerak rata."""
    _linear_keys()
    for frame, loc, tgt in ((f0, loc0, tgt0), (f1, loc1, tgt1)):
        cam.location = loc
        look_at(cam, tgt)
        cam.keyframe_insert("location", frame=frame)
        cam.keyframe_insert("rotation_euler", frame=frame)


def key_object_motion(obj, f0, f1, loc0, loc1, rot0=None, rot1=None):
    _linear_keys()
    for frame, loc in ((f0, loc0), (f1, loc1)):
        obj.location = loc
        obj.keyframe_insert("location", frame=frame)
    if rot0 is not None:
        for frame, rot in ((f0, rot0), (f1, rot1)):
            obj.rotation_euler = rot
            obj.keyframe_insert("rotation_euler", frame=frame)


def report(shot, objs, scn):
    print(f"=== RINGKASAN shot {shot} ===")
    for obj in objs:
        if obj.type == "MESH":
            d = obj.dimensions
            print(f"  {obj.name}: verts={len(obj.data.vertices)} "
                  f"dims=({d.x:.2f}, {d.y:.2f}, {d.z:.2f})")
    print("engine:", scn.render.engine, "vt:", scn.view_settings.view_transform,
          "res:", scn.render.resolution_x, scn.render.resolution_y,
          "fps:", scn.render.fps, "range:", scn.frame_start, "-", scn.frame_end)


def save_and_preview(shot, filename, preview_frame=None):
    scn = bpy.context.scene
    scn.frame_set(1)
    path = os.path.join(SCENES, filename)
    bpy.ops.wm.save_as_mainfile(filepath=path)
    print("SAVED:", path, os.path.getsize(path), "bytes")

    if preview_frame is not None:
        os.makedirs(STILLS, exist_ok=True)
        scn.frame_set(preview_frame)
        scn.render.resolution_percentage = 50
        scn.render.image_settings.file_format = "PNG"
        tag = shot if str(shot).startswith("s") else f"s4-{shot}"
        out = os.path.join(STILLS, f"anim-{tag}_v001.png")
        scn.render.filepath = out[:-4]
        bpy.ops.render.render(write_still=True)
        print("RENDER:", out, os.path.getsize(out) if os.path.exists(out) else "MISSING")
        scn.frame_set(1)


# ---------------------------------------------------------------------------
# shot 020 — buoy dipasang dari permukaan
# ---------------------------------------------------------------------------


def build_020():
    wipe()
    scn = setup_scene("scene-4_shot-020_buoy-dipasang")

    sea_mat = material("MAT_sea_surface", PAL["teal"], roughness=0.18)
    make_plane("ENV_sea", 6000.0, 0.0, sea_mat)

    boat_objs = append_collection(ASSETS + "/props/boats.blend", "PRP_boats")
    buoy_objs = append_collection(ASSETS + "/props/mooring-buoy.blend", "PRP_buoy")
    purged = purge_lights_cameras(buoy_objs)
    if purged:
        print("dibuang dari buoy:", purged)
    boat_objs = live_objects(boat_objs)
    buoy_objs = live_objects(buoy_objs)

    # Perahu di belakang-kiri buoy, haluan menghadap kamera.
    boat_root = next((o for o in boat_objs if o.name.endswith("_hull")), boat_objs[0])
    for obj in boat_objs:
        obj.location.x += -3.2
        obj.location.y += 2.6
        obj.location.z += 0.0
    for obj in boat_objs:
        obj.rotation_euler.z = math.radians(28)

    # Buoy: badan bola di asset berada di z 2,80 dengan tali 2,4 m ke dasar.
    # Untuk shot permukaan, buoy diturunkan supaya badan mengapung di z 0,28.
    for obj in buoy_objs:
        obj.location.z -= 2.52
        obj.location.x += 0.9
        obj.location.y += -0.4

    add_world("WLD_s4-020", "#0F5C63", strength=0.9)
    add_sun(energy=3.6, angle_deg=4.0, rot=(58, 0, 18))
    add_fill(energy=380.0, size=9.0, loc=(-7, -9, 5), target=(0, 0, 0.4))

    cam = make_camera("CAM_shot-020", (7.4, -6.2, 2.35), (0.4, 0.0, 0.35), lens=42.0)
    key_camera(
        cam, 1, FRAMES,
        (8.0, -6.8, 2.5), (6.4, -5.4, 2.15),
        (0.2, 0.0, 0.30), (0.6, 0.2, 0.42),
    )

    report("020", [o for o in bpy.data.objects if o.type == "MESH"], scn)
    print("preview-frame referensi boat_root:", boat_root.name)
    save_and_preview("020", "scene-4_shot-020_buoy-dipasang_v001.blend", preview_frame=48)


# ---------------------------------------------------------------------------
# shot 030 — kerangka transplantasi karang di dasar
# ---------------------------------------------------------------------------


def build_030():
    wipe()
    scn = setup_scene("scene-4_shot-030_kerangka-karang")

    sand_mat = material("MAT_seabed_sand", PAL["sand"], roughness=0.92)
    make_plane("ENV_seabed", 40.0, 0.0, sand_mat)

    frame_objs = append_collection(ASSETS + "/props/coral-frame.blend", "PRP_coral-frame")
    purged = purge_lights_cameras(frame_objs)
    if purged:
        print("dibuang dari coral-frame:", purged)
    frame_objs = live_objects(frame_objs)
    for obj in frame_objs:
        obj.location = (0.0, 0.0, 0.06)
        obj.rotation_euler.z = math.radians(-12)

    # Puing & karang rusak di sekitar rangka (konteks pemulihan).
    rubble_objs = append_collection(ASSETS + "/env/reef-damaged.blend", "ENV_reef-damaged")
    purged = purge_lights_cameras(rubble_objs)
    placements = {
        "ENV_reef_damaged-rubble_a": ((2.4, 1.5, 0.0), 22),
        "ENV_reef_damaged-rubble_b": ((-2.8, -1.2, 0.0), -40),
        "ENV_reef_damaged-rubble_c": ((1.2, -2.6, 0.0), 65),
        "ENV_reef_damaged-bomb": ((-5.4, 2.2, 0.0), 12),
        "ENV_reef_damaged-net": ((4.6, -1.8, 0.0), -18),
    }
    for name, (loc, rz) in placements.items():
        obj = bpy.data.objects.get(name)
        if obj:
            obj.location = loc
            obj.rotation_euler = (0.0, 0.0, math.radians(rz))

    # Karang hidup di latar belakang, penyu & lampu placeholder dibuang.
    reef_objs = append_collection(ASSETS + "/env/reef.blend", "ENV_reef")
    purged = purge_lights_cameras(reef_objs)
    if purged:
        print("dibuang dari reef:", purged)
    for name in list(bpy.data.objects.keys()):
        if name.startswith("ENV_reef_turtle"):
            bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)
    reef_objs = live_objects(reef_objs)
    for obj in reef_objs:
        if not obj.name.startswith("ENV_reef_fish") and not obj.name.startswith("ENV_reef_turtle"):
            obj.location = (obj.location.x * 1.2 - 8.5, obj.location.y * 1.2 + 9.0, obj.location.z)
            obj.scale = (1.45, 1.45, 1.45)

    # Ikan dipindah jauh ke belakang supaya tidak menutupi rangka.
    for obj in reef_objs:
        if obj.name.startswith("ENV_reef_fish"):
            obj.location = (obj.location.x * 2.0 - 2.0, obj.location.y + 11.0, obj.location.z + 2.2)
            obj.scale = (0.9, 0.9, 0.9)

    add_world("WLD_s4-030", "#0F5C63", strength=1.5)
    add_sun(energy=4.2, angle_deg=10.0, rot=(24, 0, 8))
    add_fill(energy=140.0, size=8.0, loc=(-4, -6, 5), target=(0, 0, 0.4))

    cam = make_camera("CAM_shot-030", (3.1, -3.0, 1.15), (0.0, 0.0, 0.42), lens=40.0)
    key_camera(
        cam, 1, FRAMES,
        (3.5, -3.3, 1.22), (2.7, -2.5, 1.02),
        (0.0, 0.0, 0.40), (0.1, 0.0, 0.46),
    )

    report("030", [o for o in bpy.data.objects if o.type == "MESH"], scn)
    save_and_preview("030", "scene-4_shot-030_kerangka-karang_v001.blend", preview_frame=48)


# ---------------------------------------------------------------------------
# shot 070 — penyu kembali
# ---------------------------------------------------------------------------


def build_070():
    wipe()
    scn = setup_scene("scene-4_shot-070_penyu-kembali", frame_end=72)

    add_world("WLD_s4-070", "#1FA3A3", strength=1.6)
    add_sun(energy=4.5, angle_deg=12.0, rot=(20, 0, -10))
    add_fill(energy=120.0, size=6.0, loc=(-3, -4, 4), target=(0, 0, 1.6))

    # Penyu sudah disusun utuh oleh @modelling di file terpisah:
    # assets/env/sea_turtle-assembled.blend → koleksi ENV_turtle, 34 mesh
    # di-parent ke empty CTL_turtle, menghadap -Y, z 0 = titik terendah.
    turtle_objs = append_collection(ASSETS + "/env/sea_turtle-assembled.blend", "ENV_turtle")
    turtle_objs = live_objects(turtle_objs)
    pivot = bpy.data.objects.get("CTL_turtle")
    if pivot is None:
        raise RuntimeError("CTL_turtle tidak ditemukan di sea_turtle-assembled.blend")
    print("penyu: n=", len(turtle_objs), "pivot", pivot.name)
    base_rot = math.radians(90.0)  # hadap -Y diputar ke arah lintasan +X

    # Karang hidup sebagai latar, tanpa penyu placeholder.
    reef_objs = append_collection(ASSETS + "/env/reef.blend", "ENV_reef")
    purge_lights_cameras(reef_objs)
    for name in list(bpy.data.objects.keys()):
        if name.startswith("ENV_reef_turtle"):
            bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)
    reef_objs = live_objects(reef_objs)
    for obj in bpy.data.objects:
        if obj.name.startswith(("ENV_reef_fish", "ENV_reef_branching", "ENV_reef_boulder",
                                "ENV_reef_table")):
            obj.location = (obj.location.x, obj.location.y + 3.2, obj.location.z - 1.4)

    # Gerak penyu: melintas dari kiri ke kanan, sedikit naik.
    key_object_motion(pivot, 1, 72, (-3.0, 0.2, 1.35), (3.2, -0.4, 1.62),
                      rot0=(0.0, 0.0, base_rot),
                      rot1=(math.radians(-3), 0.0, base_rot - math.radians(6)))

    cam = make_camera("CAM_shot-070", (0.0, -4.4, 1.75), (0.0, 0.0, 1.45), lens=42.0)
    key_camera(
        cam, 1, 72,
        (-0.8, -4.3, 1.80), (0.8, -4.4, 1.70),
        (-0.4, 0.0, 1.42), (0.6, 0.0, 1.50),
    )

    report("070", [o for o in bpy.data.objects if o.type == "MESH"], scn)
    save_and_preview("070", "scene-4_shot-070_penyu-kembali_v001.blend", preview_frame=36)


# ---------------------------------------------------------------------------
# dispatcher
# ---------------------------------------------------------------------------


def main(which):
    builders = {"020": build_020, "030": build_030, "070": build_070}
    if which not in builders:
        raise SystemExit(f"shot tidak dikenal: {which}")
    builders[which]()


if "SHOT_TO_BUILD" in globals():
    main(globals()["SHOT_TO_BUILD"])

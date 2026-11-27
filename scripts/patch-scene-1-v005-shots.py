"""patch-scene-1-v005-shots.py — pasang aset v005 ke shot Scene 1 + judul shot 010.

Headless saja (tanpa Blender MCP):

    & "D:\\Blender Foundation\\Blender 5.2\\blender.exe" -b ^
        -P scripts/patch-scene-1-v005-shots.py -- 010 [--work] [--no-title] [--no-still]

Yang dikerjakan (tidak membangun ulang shot; file shot v001 dibuka lalu ditambal):

  010/020/070/080/090/100  island-detail_v004 -> _v005 (30 rumah, jalan 265 m,
                           426 kelapa, Manado Tua 2.400 kartu)
  030/040/050              reef-dense_v004 -> _v005 (140 karang, meja <= 1,16 m,
                           600 rumpun lamun, 3 sekolah)
  010                      kamera drone z 85 -> 70 m (push-in), lensa 24 mm,
                           + judul mesh "WARISAN BUNAKEN" + subjudul, f1-72

Yang TIDAK disentuh: ikan v004, rig Nara v003, turtle, perahu, crowd, Daniel,
kamera shot lain, look (dipasang renderer lewat scripts/look.py).

--work menyimpan hasil ke renders/tmp/work-<shot>.blend (untuk iterasi);
tanpa --work hasil ditulis ke scenes/ dan file lama dicadangkan ke
renders/tmp/backup-<nama shot>_v001.blend.
"""

import bpy
import datetime
import importlib.util
import math
import os
import shutil
import sys

from mathutils import Matrix, Vector

ROOT = r"D:/Tugas Semester 5/Grafika Komputer/Project-Animasi"
ASSETS = ROOT + "/assets"
SCENES = ROOT + "/scenes"
STILLS = ROOT + "/renders/stills"
TMP = ROOT + "/renders/tmp"
LOGPATH = ROOT + "/renders/logs/technical.log"

P_ISLAND = ASSETS + "/env/island-detail_v005.blend"
P_REEF = ASSETS + "/env/reef-dense_v005.blend"
COLL_ISLAND = "ENV_island-detail"
COLL_REEF = "ENV_reef-dense"
TABLE_MAX_DIA = 1.20

SHOTS = {
    "010": "scene-1_shot-010_bunaken-aerial_v001.blend",
    "020": "scene-1_shot-020_turun-permukaan_v001.blend",
    "030": "scene-1_shot-030_terumbu_v001.blend",
    "040": "scene-1_shot-040_penyu_v001.blend",
    "050": "scene-1_shot-050_nara-dive_v001.blend",
    "070": "scene-1_shot-070_nara-naik_v001.blend",
    "080": "scene-1_shot-080_daniel-jaring_v001.blend",
    "090": "scene-1_shot-090_anak-dermaga_v001.blend",
    "100": "scene-1_shot-100_nara-ujung-dermaga_v001.blend",
}
ISLAND_SHOTS = ("010", "020", "070", "080", "090", "100")
REEF_SHOTS = ("030", "040", "050")

# override karang v004 yang dipasang skrip lama (move_corals) — dipakai ulang
REEF_SPOTS = {
    "040": {"ENV_dense_coral_0000": ((1.6, 3.8, -5.0), 2.0, 17.0),
            "ENV_dense_coral_0001": ((-1.6, 4.6, -5.0), 1.7, 34.0),
            "ENV_dense_coral_0002": ((3.4, 2.4, -5.0), 1.8, 52.0),
            "ENV_dense_coral_0003": ((-3.6, 3.1, -5.0), 1.6, 71.0),
            "ENV_dense_coral_0004": ((0.2, 6.4, -5.0), 2.1, 88.0)},
    "050": {"ENV_dense_coral_0000": ((-2.55, -2.05, -5.05), 2.6, 0.0),
            "ENV_dense_coral_0001": ((-0.30, -2.60, -5.02), 1.5, 22.0)},
}

# kamera 010: arah tetap (kampung -> Manado Tua), jarak + pitch baru
CAM_DIST = 300.0          # m horizontal kamera -> pusat kampung (v004: 836 m)
CAM_YAW = 5.0             # derajat, putar ke kiri (Manado Tua) supaya masuk frame
CAM_PITCH = 11.0          # derajat turun (perlu curam supaya kampung tidak tertutup kelapa)
CAM_Z0, CAM_Z1 = 85.0, 70.0
CAM_LENS = 24.0
VIL = Vector((0.0, 34.0, 0.0))
CAM_U0 = (VIL.xy - Vector((520.0, -620.0)).xy).normalized()

TITLE_TEXT = "WARISAN BUNAKEN"
SUBTITLE_TEXT = "Sebuah animasi 3D"
TITLE_HEX = "#F2E9DC"
TITLE_EMIT = 0.8
TITLE_CAP = 1.5           # m tinggi huruf pada jarak kamera
TITLE_DIST = 16.0         # m di depan kamera
TITLE_Y = -3.6            # m (ruang kamera, + naik) pusat judul
TITLE_SUB_CAP = 0.30
TITLE_IN, TITLE_HOLD_END, TITLE_OUT = 1, 56, 72


def log(phase, line):
    os.makedirs(os.path.dirname(LOGPATH), exist_ok=True)
    stamp = datetime.datetime.now().strftime("%H:%M")
    with open(LOGPATH, "a", encoding="utf-8") as fh:
        fh.write("[%s] %s - %s\n" % (stamp, phase, line))
    print("[log]", phase, line)


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


lib = _load("s4lib", ROOT + "/scripts/build-scene-4-shots.py")
s1 = _load("s1lib", ROOT + "/scripts/build-scene-1-detail-shots.py")
look = _load("looklib", ROOT + "/scripts/look.py")


def hex_rgb(code):
    code = code.lstrip("#")
    return tuple(int(code[i:i + 2], 16) / 255.0 for i in (0, 2, 4)) + (1.0,)


# ------------------------------------------------------------------- util ---


def purge_orphans(passes=3):
    for _ in range(passes):
        for db in (bpy.data.meshes, bpy.data.materials, bpy.data.armatures,
                   bpy.data.curves, bpy.data.cameras, bpy.data.lights,
                   bpy.data.collections):
            for block in list(db):
                try:
                    if block.users == 0 and not block.use_fake_user:
                        db.remove(block)
                except Exception:
                    pass


def drop_libraries():
    for lby in list(bpy.data.libraries):
        try:
            bpy.data.libraries.remove(lby)
        except Exception as exc:
            print("  library tidak bisa dilepas:", lby.filepath, exc)


def open_shot(key):
    src = os.path.join(SCENES, SHOTS[key])
    bpy.ops.wm.open_mainfile(filepath=src)
    scn = bpy.context.scene
    scn.render.resolution_percentage = 100
    scn.render.engine = "BLENDER_EEVEE"
    scn.view_settings.view_transform = "Standard"
    scn.render.fps = 24
    scn.render.fps_base = 1.0
    scn.frame_set(1)
    print("OPEN", os.path.basename(src), "| frame %d-%d" % (scn.frame_start, scn.frame_end))
    return src, scn


def remove_collections(names):
    """Hapus objek + koleksi (beserta anaknya) dan kembalikan jumlah objek."""
    colls = [bpy.data.collections.get(n) for n in names]
    colls = [c for c in colls if c is not None]
    order = []
    seen = set()

    def walk(c):
        if c.name in seen:
            return
        seen.add(c.name)
        for ch in c.children:
            walk(ch)
        order.append(c)

    for c in colls:
        walk(c)
    doomed = set()
    for c in order:
        for ob in list(c.objects):
            doomed.add(ob.name)
    for nm in doomed:
        ob = bpy.data.objects.get(nm)
        if ob is not None:
            bpy.data.objects.remove(ob, do_unlink=True)
    for c in order:
        if c.name in bpy.data.collections:
            bpy.data.collections.remove(c)
    purge_orphans()
    return len(doomed)


def append_collection(path, name):
    before = set(bpy.data.objects.keys())
    with bpy.data.libraries.load(path, link=False) as (src, dst):
        if name not in src.collections:
            raise RuntimeError("%s tidak ada di %s" % (name, path))
        dst.collections = [name]
    coll = dst.collections[0]
    scn = bpy.context.scene
    if coll.name not in scn.collection.children:
        scn.collection.children.link(coll)
    new = [bpy.data.objects[n] for n in bpy.data.objects.keys() if n not in before]
    cams = [o.name for o in new if o.type in {"CAMERA", "LIGHT"}]
    for nm in cams:
        bpy.data.objects.remove(bpy.data.objects[nm], do_unlink=True)
    for nm in [o.name for o in new if o.name.startswith("PREVIEW")]:
        bpy.data.objects.remove(bpy.data.objects[nm], do_unlink=True)
    prev = bpy.data.collections.get("PREVIEW")
    if prev is not None:
        bpy.data.collections.remove(prev)
    purge_orphans()
    new = [o for o in new if o.name in bpy.data.objects]
    print("  append %-24s -> %-28s %3d objek (kamera/lampu dibuang: %s)"
          % (os.path.basename(path), coll.name, len(new), cams or "-"))
    return coll, new


def world_centre(ob):
    pts = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    return sum(pts, Vector()) / 8.0


# ----------------------------------------------------------- tukar pulau ---


def swap_island(key, sea_scale=None):
    old = remove_collections([COLL_ISLAND, COLL_ISLAND + "_context"])
    coll, objs = append_collection(P_ISLAND, COLL_ISLAND)
    bpy.context.view_layer.update()

    houses = [o for o in bpy.data.objects if o.name.startswith("ENV_detail_houses")]
    road = bpy.data.objects.get("ENV_detail_road")
    palm_coast = [o for o in bpy.data.objects if o.name.startswith("ENV_detail_palm-coast")]
    palm_house = [o for o in bpy.data.objects if o.name.startswith("ENV_detail_palm-house")]
    palm_extra = [o for o in bpy.data.objects if o.name.startswith("ENV_detail_palm-extra")]
    veg = bpy.data.objects.get("ENV_detail_manado-tua_veg")
    mt = bpy.data.objects.get("ENV_detail_manado-tua")
    n_palm = len([o for o in bpy.data.objects if o.name.startswith("ENV_detail_palm")])
    print("  pulau v005: %d rumah, jalan %s, kelapa %d (pesisir %d + rumah %d + sebaran %d), "
          "Manado Tua %s (%.0f m, kartu %d)"
          % (len(houses), "ada" if road else "TIDAK ADA", n_palm, len(palm_coast),
             len(palm_house), len(palm_extra), "ada" if mt else "TIDAK ADA",
             mt.dimensions.z if mt else 0.0,
             len(veg.data.polygons) if veg else 0))
    print("  objek lama dibuang: %d" % old)

    if sea_scale is not None:
        sea = bpy.data.objects.get("ENV_detail_sea-surface")
        if sea is not None:
            sea.scale = sea_scale
            bpy.context.view_layer.update()
            print("  sea-surface diskalakan:", [round(v, 0) for v in sea.dimensions])
    return coll


# ----------------------------------------------------------- tukar terumbu ---


def stretch_seabed():
    """v004/v005: bidang pasir 26 m di-regang 20x20 (jadi 520 m) di dalam mesh."""
    seabed = bpy.data.objects.get("ENV_dense_seabed")
    if seabed is None:
        print("  seabed tidak ada")
        return None
    mw = seabed.matrix_world.copy()
    inv = mw.inverted()
    for v in seabed.data.vertices:
        w = mw @ v.co
        w.x *= 20.0
        w.y *= 20.0
        v.co = inv @ w
    bpy.context.view_layer.update()
    print("  seabed diperbesar:", [round(x, 0) for x in seabed.dimensions])
    return seabed


def darken_sand():
    sand = bpy.data.materials.get("MAT_dense_sand")
    if sand is None or not sand.use_nodes:
        print("  MAT_dense_sand tidak ada")
        return
    ramp = next((n for n in sand.node_tree.nodes if n.type == "VALTORGB"), None)
    if ramp:
        for el in ramp.color_ramp.elements:
            c = el.color
            el.color = (c[0] * 0.50, c[1] * 0.55, c[2] * 0.60, 1.0)
    bsdf = next((n for n in sand.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf is not None:
        bsdf.inputs["Roughness"].default_value = 0.92
    print("  MAT_dense_sand digelapkan (ramp x0,50/0,55/0,60, rough 0,92)")


def swap_reef(key):
    coll = bpy.data.collections.get(COLL_REEF)
    ctl = bpy.data.objects.get("CTL_reef-dense")
    if coll is None or ctl is None:
        raise RuntimeError("koleksi/CTL terumbu tidak ada di shot %s" % key)

    olds = [o for o in coll.objects if o.name.startswith("ENV_dense_")]
    print("  karang/lamun lama: %d objek" % len(olds))
    for ob in olds:
        bpy.data.objects.remove(ob, do_unlink=True)
    purge_orphans()
    before = set(bpy.data.objects.keys())

    with bpy.data.libraries.load(P_REEF, link=False) as (src, dst):
        want = [n for n in src.objects if n.startswith("ENV_dense_")]
        print("  aset v005 berisi %d objek ENV_dense_*" % len(want))
        dst.objects = want
    new = [bpy.data.objects[n] for n in bpy.data.objects.keys() if n not in before]
    print("  objek v005 masuk: %d" % len(new))
    for ob in new:
        if ob.name not in coll.objects:
            coll.objects.link(ob)
        ob.parent = ctl
        ob.matrix_parent_inverse = Matrix.Identity(4)
    bpy.context.view_layer.update()
    cor = [o for o in bpy.data.objects if o.name.startswith("ENV_dense_coral_")]
    print("  terumbu v005: %d karang, lamun %s" % (
        len(cor), "ada" if bpy.data.objects.get("ENV_dense_seagrass") else "TIDAK ADA"))

    stretch_seabed()
    darken_sand()

    spots = REEF_SPOTS.get(key, {})
    for nm, (loc, scl, rz) in spots.items():
        ob = bpy.data.objects.get(nm)
        if ob is None:
            print("  WARN karang", nm, "tidak ada")
            continue
        ob.location = loc
        ob.scale = (scl, scl, scl)
        ob.rotation_euler.z += math.radians(rz)
        bpy.context.view_layer.update()
        if "table" in ob.data.name:
            dia = max(ob.dimensions.x, ob.dimensions.y)
            if dia > TABLE_MAX_DIA:
                f = TABLE_MAX_DIA / dia
                ob.scale = tuple(v * f for v in ob.scale)
                bpy.context.view_layer.update()
                print("  %s meja dipotong %.2f -> %.2f m" % (nm, dia, max(ob.dimensions.x, ob.dimensions.y)))
        print("  tempat karang %-24s %s skala %.2f" % (nm, tuple(round(v, 2) for v in loc), scl))

    tables = sorted(max(o.dimensions.x, o.dimensions.y) for o in cor if "table" in o.data.name)
    alls = sorted(max(o.dimensions.x, o.dimensions.y) for o in cor)
    print("  meja terbesar: %.2f m (%d meja) | karang terbesar: %.2f m | terkecil %.2f m"
          % (tables[-1] if tables else 0, len(tables), alls[-1], alls[0]))
    return {"corals": len(cor), "table_max": tables[-1] if tables else 0.0,
            "coral_max": alls[-1], "table_min": tables[0] if tables else 0.0}


# --------------------------------------------------------------- kamera 010 ---


def cam_010(scn):
    cam = scn.camera
    old_act = cam.animation_data.action if cam.animation_data else None
    cam.animation_data_clear()
    if old_act is not None and old_act.users == 0:
        bpy.data.actions.remove(old_act)
    cam.data.lens = CAM_LENS
    a = math.radians(CAM_YAW)
    u = Vector((CAM_U0.x * math.cos(a) - CAM_U0.y * math.sin(a),
                CAM_U0.x * math.sin(a) + CAM_U0.y * math.cos(a)))
    tan_p = math.tan(math.radians(CAM_PITCH))
    d2 = CAM_DIST * CAM_Z1 / CAM_Z0           # pitch tetap -> push-in murni

    keys = []
    for frame, z, d in ((1, CAM_Z0, CAM_DIST), (96, CAM_Z1, d2)):
        px, py = VIL.x - u.x * d, VIL.y - u.y * d
        tgt = (px + u.x * 200.0, py + u.y * 200.0, z - 200.0 * tan_p)
        keys.append((frame, (px, py, z), tgt))
    set_interp = s1.set_interp
    set_interp("BEZIER")
    for frame, loc, tgt in keys:
        cam.location = loc
        s1.look_at(cam, tgt)
        cam.keyframe_insert("location", frame=frame)
        cam.keyframe_insert("rotation_euler", frame=frame)
    print("  kamera 010: z %.0f -> %.0f m, jarak kampung %.0f -> %.0f m, lens %.0f mm, "
          "pitch %.1f deg, yaw +%.1f deg"
          % (CAM_Z0, CAM_Z1, CAM_DIST, d2, CAM_LENS, CAM_PITCH, CAM_YAW))
    act = cam.animation_data.action if cam.animation_data else None
    if act is not None:
        act.name = "CAM_shot-010_droneAction"
    return cam


CAM_POINTS = {
    "kampung-barat": (-48.0, 49.0, 2.0),
    "kampung-timur": (50.0, 19.0, 2.0),
    "jalan-tengah": (4.3, 23.8, 0.5),
    "dive-shop": (11.0, 1.9, 3.0),
    "dermaga-ujung": (0.0, -104.0, 1.0),
    "manado-tua-puncak": (-5362.0, 1404.0, 745.0),
    "manado-tua-kiri": (-6300.0, 2200.0, 0.0),
}


def check_cam(scn, frames=(1, 48, 96)):
    from bpy_extras.object_utils import world_to_camera_view as w2c
    cam = scn.camera
    out = {}
    for f in frames:
        scn.frame_set(f)
        row = {}
        for lab, p in CAM_POINTS.items():
            v = w2c(scn, cam, Vector(p))
            row[lab] = (round(v.x, 3), round(v.y, 3))
        out[f] = row
        print("  ndc f%-3d %s" % (f, "  ".join("%s=%.2f/%.2f" % (k.split("-")[0][:5], v[0], v[1])
                                              for k, v in row.items())))
    scn.frame_set(1)
    return out


# ----------------------------------------------------------------- judul 010 ---


def text_mesh(name, body, cap_height, coll):
    cu = bpy.data.curves.new(name, type="FONT")
    cu.body = body
    cu.align_x = "CENTER"
    cu.align_y = "CENTER"
    cu.size = 1.0
    cu.extrude = 0.0
    ob = bpy.data.objects.new(name, cu)
    coll.objects.link(ob)
    bpy.context.view_layer.objects.active = ob
    for o in bpy.context.selected_objects:
        o.select_set(False)
    ob.select_set(True)
    bpy.ops.object.convert(target="MESH")
    ob = bpy.data.objects[name]
    bpy.context.view_layer.update()
    s = cap_height / ob.dimensions.y
    ob.scale = (s, s, s)
    bpy.context.view_layer.update()
    ob.data.name = name + "_mesh"
    print("  teks %-22s '%s' -> mesh %d vert, tinggi %.2f m, lebar %.2f m"
          % (name, body, len(ob.data.vertices), ob.dimensions.y, ob.dimensions.x))
    return ob


def title_material():
    mat = bpy.data.materials.new("MAT_title_wb")
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.location = (420, 0)
    mix = nt.nodes.new("ShaderNodeMixShader")
    mix.location = (200, 0)
    trans = nt.nodes.new("ShaderNodeBsdfTransparent")
    trans.location = (-40, 120)
    emit = nt.nodes.new("ShaderNodeEmission")
    emit.location = (-40, -80)
    emit.inputs["Color"].default_value = hex_rgb(TITLE_HEX)
    emit.inputs["Strength"].default_value = TITLE_EMIT
    nt.links.new(trans.outputs[0], mix.inputs[1])
    nt.links.new(emit.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    if hasattr(mat, "surface_render_method"):
        mat.surface_render_method = "BLENDED"
    else:
        mat.blend_method = "BLEND"
    mat.use_transparent_shadow = False
    try:
        mat.use_transparency_overlap = True
    except Exception:
        pass
    return mat, mix


def add_title_010(scn):
    cam = scn.camera
    coll = bpy.data.collections.get("FX_title")
    if coll is None:
        coll = bpy.data.collections.new("FX_title")
        scn.collection.children.link(coll)
    for ob in list(coll.objects):
        bpy.data.objects.remove(ob, do_unlink=True)

    main = text_mesh("FX_title_wb_main", TITLE_TEXT, TITLE_CAP, coll)
    sub = text_mesh("FX_title_wb_sub", SUBTITLE_TEXT, TITLE_SUB_CAP, coll)
    mat, mix = title_material()
    for ob in (main, sub):
        ob.data.materials.clear()
        ob.data.materials.append(mat)
        ob.parent = cam
        ob.matrix_parent_inverse = Matrix.Identity(4)

    gap = 0.26
    main.location = (0.0, TITLE_Y, -TITLE_DIST)
    sub.location = (0.0, TITLE_Y - TITLE_CAP * 0.5 - gap - TITLE_SUB_CAP * 0.5, -TITLE_DIST)

    fac = mix.inputs[0]
    keys = ((1, 0.0), (12, 1.0), (TITLE_HOLD_END, 1.0), (TITLE_OUT, 0.0))
    for frame, val in keys:
        fac.default_value = val
        fac.keyframe_insert("default_value", frame=frame)
    for ob in (main, sub):
        for frame, hidden in ((1, False), (TITLE_OUT, False), (TITLE_OUT + 1, True)):
            ob.hide_render = hidden
            ob.keyframe_insert("hide_render", frame=frame)
    scn.frame_set(1)
    w = main.dimensions.x
    print("  judul: '%s' cap %.2f m lebar %.2f m + '%s' cap %.2f m, jarak %.0f m dari kamera, "
          "fade 1-12 / 56-72, emission %.1f, %s"
          % (TITLE_TEXT, main.dimensions.y, w, SUBTITLE_TEXT, sub.dimensions.y, TITLE_DIST,
             TITLE_EMIT, TITLE_HEX))
    return main, sub


# -------------------------------------------------------------------- simpan ---


def save(key, src, work=False, backup=True):
    scn = bpy.context.scene
    scn.frame_set(1)
    scn.render.resolution_percentage = 100
    scn.render.filepath = "//"
    drop_libraries()
    if work:
        out = os.path.join(TMP, "work-%s.blend" % key)
    else:
        out = src
        if backup:
            stem = os.path.splitext(os.path.basename(src))[0]
            bak = os.path.join(TMP, "backup-%s.blend" % stem)
            if not os.path.exists(bak):
                shutil.copy2(src, bak)
                print("BACKUP:", os.path.basename(bak))
    for nb in (".blend1", ".blend2"):
        stale = out + nb
        if os.path.exists(stale):
            os.remove(stale)
    bpy.ops.wm.save_as_mainfile(filepath=out)
    size = os.path.getsize(out)
    print("SAVED %s (%.2f MB)" % (os.path.basename(out), size / 1048576.0))
    return out, size


def summary(key):
    scn = bpy.context.scene
    objs = list(bpy.data.objects)
    meshes = [o for o in objs if o.type == "MESH"]
    verts = sum(len(o.data.vertices) for o in meshes)
    print("SUMMARY s1-%s | obj=%d mesh=%d arm=%d cam=%d light=%d verts=%d | %dx%d %dfps vt=%s "
          "range=%d-%d"
          % (key, len(objs), len(meshes), len([o for o in objs if o.type == "ARMATURE"]),
             len([o for o in objs if o.type == "CAMERA"]),
             len([o for o in objs if o.type == "LIGHT"]), verts,
             scn.render.resolution_x, scn.render.resolution_y, scn.render.fps,
             scn.view_settings.view_transform, scn.frame_start, scn.frame_end))


def still(path, frame, percent=50, above_water=None, samples=24):
    scn = bpy.context.scene
    os.makedirs(os.path.dirname(path), exist_ok=True)
    rep = look.apply_look(scn, 1, above_water=above_water)
    scn.frame_set(int(frame))
    look.render_still(scn, path, percent=percent, samples=samples)
    scn.frame_set(1)
    print("STILL:", path, os.path.exists(path), "| world", rep["world"].name
          if hasattr(rep["world"], "name") else rep["world"])


# ---------------------------------------------------------------------- main ---


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    keys = []
    for a in args:
        keys.extend(x for x in a.split(",") if x)
    work = "--work" in argv
    title = "--no-title" not in argv
    do_still = "--no-still" not in argv
    if not keys or keys == ["all"]:
        keys = list(SHOTS)
    log("PLAN", "patch s1 v005: %s | kamera 010 z %.0f->%.0f m jarak %.0f m judul f1-72"
        % (",".join(keys), CAM_Z0, CAM_Z1, CAM_DIST))

    for key in keys:
        print("=" * 78)
        print("SHOT", key)
        src, scn = open_shot(key)
        info = {}
        if key in ISLAND_SHOTS:
            swap_island(key, sea_scale=(20.0, 8.0, 1.0) if key == "010" else None)
        if key in REEF_SHOTS:
            info = swap_reef(key)
        if key == "010":
            cam_010(scn)
            check_cam(scn)
            if title:
                add_title_010(scn)
        out, size = save(key, src, work=work)
        summary(key)

        if do_still:
            if key == "010":
                still(os.path.join(STILLS, "anim-s1-010_v001.png"), 48)
                if title:
                    still(os.path.join(STILLS, "anim-s1-010-title.png"), 24)
            elif key in ("030", "050"):
                still(os.path.join(STILLS, "anim-s1-%s_v001.png" % key), 48,
                      above_water=False)
            elif "--check" in argv:
                still(os.path.join(TMP, "check-%s.png" % key), 24,
                      percent=25, above_water=None)
        log("LOOK", "s1-%s: %s -> v005, %.2f MB%s"
            % (key, "island-detail" if key in ISLAND_SHOTS else "reef-dense",
               size / 1048576.0,
               " | meja maks %.2f m" % info["table_max"] if info else ""))
    log("DONE", "patch s1 v005 selesai: %d shot (%s)" % (len(keys), ",".join(keys)))
    return 0


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    sys.exit(main(argv))


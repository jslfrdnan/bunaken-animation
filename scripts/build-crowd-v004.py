"""Build assets/char/crowd_v004.blend — empat anak berproporsi anak sungguhan.

v004 (25 Nov 2026) — permintaan Director: `CRW_C01`–`CRW_C04` dibuat ulang.
Versi v003 memang memakai basis `child`, tetapi spesifikasinya masih mewarisi
proporsi dewasa (kaki 51 % tinggi, lengan 35 %, bahu lebar). v004 memakai
spesifikasi anak baru di `scripts/build-crowd.py`:

    tinggi basis   1,25 m, kepala 0,2156 m  -> **5,80 kepala**
    bahu           span 0,274 m (22 % tinggi; dewasa 25 %)
    lengan         0,360 m (29 % tinggi; dewasa 36 %)
    kaki           0,558 m dari pinggul (45 % tinggi; dewasa 51 %)
    pinggang       lebih tinggi relatif, perut anak sedikit menonjol
    kaki/telapak   lebih pendek dan kecil

Angka tinggi akhir tetap: **1,10 / 1,18 / 1,25 / 1,30 m**. Wajah dibuat ulang
dengan fungsi wajah v002 yang sama (2 bola mata + kelopak + hidung + mulut),
jadi tiap anak tetap punya `CHR_crowd_face-crw-cNN`.

12 figur dewasa v003 dan `CTL_crowd` tidak diubah; hanya 4 anak + 4 wajahnya
yang diganti. Material memakai palette §2 yang sudah ada (tanpa tekstur).

Setelan: EEVEE, 1920x1080, 24 fps, Standard, frame 1, tanpa pack, idempoten.

    blender -b -P scripts/build-crowd-v004.py
"""
import bpy
import importlib.util
import math
import os
import time

try:
    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
except NameError:
    ROOT = r"D:\Tugas Semester 5\Grafika Komputer\Project-Animasi"

CHAR_DIR = os.path.join(ROOT, "assets", "char")
SRC = os.path.join(CHAR_DIR, "crowd_v003.blend")
OUT = os.path.join(CHAR_DIR, "crowd_v004.blend")
WIPE = os.path.join(ROOT, "renders", "tmp", "_wipe.blend")
STILLS = os.path.join(ROOT, "renders", "stills")
LOG = os.path.join(ROOT, "renders", "logs", "modeling.log")

# spesifikasi anak sungguhan (meter, tinggi basis 1,25 m) ------------------
CHILD_SPEC = {
    "height": 1.25,
    "torso": [
        (0.498, 0.092, 0.067),
        (0.590, 0.107, 0.076),
        (0.700, 0.096, 0.069),
        (0.810, 0.100, 0.072),
        (0.900, 0.104, 0.074),
        (0.966, 0.098, 0.070),
        (0.994, 0.064, 0.050),
    ],
    "torso_exp": 2.5,
    "neck": (0.968, 1.045, 0.0365),
    "head": ((0.0, 0.0, 1.1420), (0.0805, 0.0945, 0.1078)),
    "arm": [
        (0.094, 0.000, 0.958, 0.037),
        (0.124, 0.004, 0.790, 0.026),
        (0.145, 0.008, 0.598, 0.020),
    ],
    "leg": [
        (0.068, 0.000, 0.558, 0.060),
        (0.072, 0.010, 0.308, 0.042),
        (0.074, 0.013, 0.072, 0.028),
    ],
    "foot": (0.074, 0.050, -0.114, [
        (0.050, 0.030, 0.023),
        (0.019, 0.036, 0.029),
        (-0.048, 0.038, 0.026),
        (-0.114, 0.030, 0.014),
    ]),
}

# (nama, tinggi, kulit, atasan, bawahan, rok?, rambut panjang?)
CHILDREN = [
    ("CRW_C01", 1.10, "skin-alt", "teal", "sand", False, True),
    ("CRW_C02", 1.18, "skin", "orange", "teal-deep", False, False),
    ("CRW_C03", 1.25, "skin", "cream", "teal-deep", False, False),
    ("CRW_C04", 1.30, "skin-alt", "sand", "grey", False, True),
]
CHILD_PLACE = [(-1.60, -2.30), (-0.55, -2.45), (0.50, -2.35), (1.55, -2.50)]


def log(line):
    stamp = time.strftime("%H:%M")
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as fh:
            fh.write("[%s] %s\n" % (stamp, line))
    except Exception as err:  # pragma: no cover
        print("peringatan log:", err)
    print("[%s] %s" % (stamp, line))


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def wipe():
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
                   bpy.data.images, bpy.data.fonts):
        for b in list(blocks):
            try:
                blocks.remove(b)
            except Exception:
                pass
    return scn


def purge_libraries():
    for lib in list(bpy.data.libraries):
        try:
            bpy.data.libraries.remove(lib)
        except Exception as err:
            print("PERINGATAN library masih dipakai:", lib.filepath, err)


def drop_render_result():
    for img in list(bpy.data.images):
        if img.type == "RENDER_RESULT":
            try:
                bpy.data.images.remove(img)
            except Exception as err:
                print("peringatan render result:", err)


def proportions(spec):
    """Rasio proporsi penting (persen tinggi) untuk laporan."""
    h = spec["height"]
    shoulder = 2.0 * (spec["arm"][0][0] + spec["arm"][0][3] * 1.16)
    arm_len = spec["arm"][0][2] - spec["arm"][2][2]
    leg_len = spec["leg"][0][2]
    head_h = spec["head"][1][2] * 2.0
    return {
        "kepala": round(h / head_h, 2),
        "bahu_pct": round(100.0 * shoulder / h, 1),
        "bahu_m": round(shoulder, 3),
        "lengan_pct": round(100.0 * arm_len / h, 1),
        "lengan_m": round(arm_len, 3),
        "kaki_pct": round(100.0 * leg_len / h, 1),
        "kaki_m": round(leg_len, 3),
    }


# --------------------------------------------------------------------- setup
os.makedirs(os.path.dirname(WIPE), exist_ok=True)
os.makedirs(STILLS, exist_ok=True)
try:
    bpy.context.preferences.filepaths.save_version = 0
except Exception:
    pass

scn = wipe()
if bpy.data.filepath and os.path.abspath(bpy.data.filepath) != os.path.abspath(WIPE):
    bpy.ops.wm.save_as_mainfile(filepath=WIPE)
scn.name = "crowd-v004"

with bpy.data.libraries.load(SRC, link=False) as (df, dt):
    src_cols = list(df.collections)
    src_objs = list(df.objects)
    src_worlds = list(df.worlds)
    dt.collections = src_cols
    dt.objects = src_objs
    dt.worlds = src_worlds

col = bpy.data.collections.get("CHR_crowd")
if col is None:
    raise RuntimeError("koleksi CHR_crowd tidak terbawa append")
if col.name not in [c.name for c in scn.collection.children]:
    scn.collection.children.link(col)
for other in bpy.data.collections:
    if other.name == "PREVIEW" and other.name not in [c.name for c in scn.collection.children]:
        scn.collection.children.link(other)
for w in bpy.data.worlds:
    scn.world = w
    break
ctl = bpy.data.objects.get("CTL_crowd")
if ctl is None:
    raise RuntimeError("CTL_crowd tidak ada")

# ------------------------------------------- buang 4 anak + 4 wajah v003
doomed = []
for ob in list(col.objects):
    if ob.name.startswith("CRW_C0"):
        doomed.append(ob)
    elif ob.name.startswith("CHR_crowd_face-crw-c"):
        doomed.append(ob)
names_doomed = sorted(o.name for o in doomed)
meshes_doomed = [o.data for o in doomed if o.type == "MESH"]
for ob in doomed:
    bpy.data.objects.remove(ob, do_unlink=True)
for me in meshes_doomed:
    if me.users == 0:
        bpy.data.meshes.remove(me)
print("dibuang dari v003:", names_doomed)

adults = sorted([o for o in col.objects
                 if o.type == "MESH" and o.name.startswith("CRW_")
                 and not o.name.startswith("CRW_C")], key=lambda o: o.name)
faces = [o for o in col.objects if o.name.startswith("CHR_crowd_face")]
print("dewasa v003:", len(adults), "| wajah tersisa:", len(faces))
if len(adults) != 12:
    raise RuntimeError("figur dewasa %d != 12" % len(adults))

# --------------------------------------- modul pembangun + spesifikasi anak
base_mod = load_module(os.path.join(ROOT, "scripts", "build-crowd.py"), "build_crowd_base")
face_mod = load_module(os.path.join(ROOT, "scripts", "build-crowd-v002.py"), "build_crowd_face")

ADULT_PROP = proportions(base_mod.SPECS["male"])
OLD_CHILD_PROP = proportions(dict(base_mod.SPECS["child"]))
base_mod.SPECS["child"] = CHILD_SPEC
face_mod.SPECS["child"]["head"] = CHILD_SPEC["head"]
face_mod.SPECS["child"]["height"] = CHILD_SPEC["height"]
NEW_PROP = proportions(CHILD_SPEC)
print("proporsi dewasa:", ADULT_PROP)
print("proporsi anak v003:", OLD_CHILD_PROP)
print("proporsi anak v004:", NEW_PROP)

mats = {}
for slot, name in (("skin", "MAT_crowd_skin"), ("skin-alt", "MAT_crowd_skin-alt"),
                   ("hair", "MAT_crowd_hair"), ("teal", "MAT_crowd_teal"),
                   ("teal-deep", "MAT_crowd_teal-deep"), ("cream", "MAT_crowd_cream"),
                   ("sand", "MAT_crowd_sand"), ("orange", "MAT_crowd_orange"),
                   ("grey", "MAT_crowd_grey"), ("dark", "MAT_crowd_dark")):
    m = bpy.data.materials.get(name)
    if m is None:
        raise RuntimeError("material %s tidak ada" % name)
    mats[slot] = m

sample_face = next(o for o in faces if o.name.startswith("CHR_crowd_face"))
m_skin_ref, m_eye, m_mouth, m_sclera = sample_face.data.materials[0:4]

new_figs, new_faces = [], []
for (name, height, skin, shirt, bottom, skirt, long_hair), (px, py) in \
        zip(CHILDREN, CHILD_PLACE):
    fig = base_mod.build_figure(name, "child", height, skin, shirt, bottom,
                                skirt, long_hair, col, mats)
    fig.location = (px, py, 0.0)
    fig.parent = ctl
    fig.matrix_parent_inverse = ctl.matrix_world.inverted()
    fig["part"] = "anak proporsi anak v004 (5,8 kepala)"
    fig["height_target_m"] = height
    fig["category"] = "anak"
    face, met = face_mod.build_face(fig, m_eye, m_mouth, m_sclera, col)
    new_figs.append(fig)
    new_faces.append(face)
    print("%-8s tinggi %.3f m  kepala %.3f m  rasio %.2f  verts figur %d wajah %d"
          % (fig.name, fig.dimensions.z, met[3] * 2.0,
             fig.dimensions.z / (met[3] * 2.0),
             len(fig.data.vertices), len(face.data.vertices)))
    if abs(fig.dimensions.z - height) > 0.003:
        raise RuntimeError("%s tinggi %.4f != %.2f" % (name, fig.dimensions.z, height))
    if abs(fig.location.z) > 1e-6:
        raise RuntimeError("%s origin z bukan 0" % name)

# ------------------------------------------- ukur bahu/lengan/kaki di mesh
def mesh_probe(fig):
    """Ukur bahu (lebar maks di ketinggian bahu) & rentang lengan/kaki di mesh."""
    mw = fig.matrix_world
    h = fig.dimensions.z
    sh_z = 0.958 / 1.25 * h
    xs = [abs((mw @ v.co).x) for v in fig.data.vertices
          if abs((mw @ v.co).z - sh_z) < 0.02]
    shoulder = 2.0 * max(xs) if xs else 0.0
    zmin = min((mw @ v.co).z for v in fig.data.vertices)
    zmax = max((mw @ v.co).z for v in fig.data.vertices)
    return round(shoulder, 3), round(h / (zmax - zmin), 3)


rows = []
for fig in new_figs:
    sh, _r = mesh_probe(fig)
    hz, hrx, hry, hrz = face_mod.head_metrics(fig)
    rows.append((fig.name, round(fig.dimensions.z, 3), round(hrz * 2.0, 4),
                 round(fig.dimensions.z / (hrz * 2.0), 2), sh,
                 round(100.0 * sh / fig.dimensions.z, 1)))
    print("%-8s tinggi %.3f | kepala %.4f (%.2f kepala) | bahu %.3f m (%.1f%%)"
          % rows[-1])

log("MODEL - crowd_v004: CRW_C01-C04 dibuat ulang dengan proporsi anak "
    "(kepala %.2f, bahu %.1f%%, lengan %.1f%%, kaki %.1f%% tinggi) - v003: "
    "kepala %.2f, bahu %.1f%%, lengan %.1f%%, kaki %.1f%%"
    % (NEW_PROP["kepala"], NEW_PROP["bahu_pct"], NEW_PROP["lengan_pct"],
       NEW_PROP["kaki_pct"], OLD_CHILD_PROP["kepala"], OLD_CHILD_PROP["bahu_pct"],
       OLD_CHILD_PROP["lengan_pct"], OLD_CHILD_PROP["kaki_pct"]))

# ------------------------------------------------------------- render setup
scn.frame_set(1)
scn.frame_start = 1
scn.frame_end = 1
scn.render.fps = 24
scn.render.resolution_x = 1920
scn.render.resolution_y = 1080
scn.render.resolution_percentage = 100
scn.view_settings.view_transform = "Standard"
try:
    scn.view_settings.look = "None"
except Exception:
    pass
scn.render.image_settings.file_format = "PNG"
for engine in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
    try:
        scn.render.engine = engine
        break
    except TypeError:
        continue
try:
    scn.eevee.taa_render_samples = 32
except Exception:
    pass

cam = bpy.data.objects.get("CAM_preview")
if cam is None:
    raise RuntimeError("CAM_preview tidak ada di PREVIEW v003")
scn.camera = cam


def look_at(obj, loc, target, lens):
    from mathutils import Vector
    obj.location = loc
    obj.data.lens = lens
    obj.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()


def render(path, loc, target, lens, pct=50):
    look_at(cam, loc, target, lens)
    scn.render.resolution_percentage = pct
    scn.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("RENDER", path, os.path.exists(path))


p1 = os.path.join(STILLS, "crowd-v004_preview-01.png")
p2 = os.path.join(STILLS, "crowd-v004_preview-02.png")
render(p1, (0.15, -7.20, 2.55), (0.0, 0.25, 1.05), 40.0)      # seluruh barisan
render(p2, (0.00, -6.30, 1.30), (0.00, -2.40, 0.62), 30.0)     # empat anak
log("VERIFY - crowd-v004 preview (skala 50%%): %s, %s"
    % (os.path.basename(p1), os.path.basename(p2)))

# ----------------------------------------------------------------- simpan
look_at(cam, (0.15, -7.20, 2.55), (0.0, 0.25, 1.05), 40.0)
scn.render.resolution_percentage = 100
scn.render.filepath = "//"
purge_libraries()
drop_render_result()
bpy.ops.wm.save_as_mainfile(filepath=OUT)
size_kb = round(os.path.getsize(OUT) / 1024.0)

print("=== RINGKASAN ===")
print("figur", len([o for o in col.objects if o.name.startswith("CRW_")]),
      "| wajah", len([o for o in col.objects
                      if o.name.startswith("CHR_crowd_face")]),
      "| objek koleksi", len(col.objects))
print("tinggi anak", [round(o.dimensions.z, 3) for o in new_figs])
print("lokasi anak", [(round(o.location.x, 2), round(o.location.y, 2),
                        round(o.location.z, 2)) for o in new_figs])
print("parent anak", [o.parent.name if o.parent else None for o in new_figs])
print("images", [i.name for i in bpy.data.images])
print("libraries", [l.filepath for l in bpy.data.libraries])
print("engine=%s vt=%s res=%dx%d fps=%d frame=%d"
      % (scn.render.engine, scn.view_settings.view_transform,
         scn.render.resolution_x, scn.render.resolution_y, scn.render.fps,
         scn.frame_current))
log("MODEL - crowd_v004.blend disimpan (%.0f KB, %d figur, %d wajah)"
    % (size_kb, len([o for o in col.objects if o.name.startswith("CRW_")]),
       len([o for o in col.objects if o.name.startswith("CHR_crowd_face")])))

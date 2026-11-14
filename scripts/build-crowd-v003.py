"""Build assets/char/crowd_v003.blend - crowd + 4 anak sungguhan.

v003 (14 Nov 2026) - salinan verbatim `crowd_v002.blend` (12 figur warga +
12 objek wajah + empty `CTL_crowd`, di-append `link=False`) ditambah **empat
anak** `CRW_C01`-`CRW_C04` yang dibangun dari nol dengan proporsi anak:

  nama    tinggi   atasan        bawahan     kulit      rambut
  CRW_C01 1,10 m   teal          sand        skin-alt   panjang
  CRW_C02 1,18 m   orange        teal-deep   skin       pendek
  CRW_C03 1,25 m   cream         teal-deep   skin       pendek
  CRW_C04 1,30 m   sand          grey        skin-alt   panjang

Proporsi 5,8 kepala (spesifikasi `child` di `scripts/build-crowd.py`: kepala
0,215 m untuk tubuh 1,25 m, diskalakan seragam), jadi kepala relatif besar -
bukan orang dewasa yang dikecilkan. Tiap anak punya objek wajah sendiri
(`CHR_crowd_face-crw-c01`..`-c04`): 2 bola mata + kelopak + hidung + mulut,
dibuat dengan fungsi wajah yang sama seperti v002.

Origin tiap anak di dasar (z 0,0), hadap -Y, di-parent ke `CTL_crowd` seperti
12 figur v002. Koleksi `CHR_crowd`. Material memakai palette PROJECT.md §2
yang sudah ada di file (tanpa tekstur, tanpa pack gambar).

Catatan: fungsi `build_figure` / `build_face` dipinjam dari
`scripts/build-crowd.py` dan `scripts/build-crowd-v002.py` (keduanya punya
penjaga `__main__`, jadi aman diimpor) supaya mesh dan wajah anak memakai
bahasa bentuk yang sama dengan figur dewasa.

Setelan file: EEVEE, 1920x1080, 24 fps, view transform Standard, frame 1.
Skrip idempoten (selalu mulai dari wipe, tanpa open_mainfile).

    blender -b --python scripts/build-crowd-v003.py
"""
import bpy
import importlib.util
import os
import time

try:
    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
except NameError:  # dijalankan lewat exec() MCP: __file__ tidak ada
    ROOT = r"D:\Tugas Semester 5\Grafika Komputer\Project-Animasi"

CHAR_DIR = os.path.join(ROOT, "assets", "char")
SRC = os.path.join(CHAR_DIR, "crowd_v002.blend")
OUT = os.path.join(CHAR_DIR, "crowd_v003.blend")
WIPE = os.path.join(ROOT, "renders", "tmp", "_wipe.blend")
STILLS = os.path.join(ROOT, "renders", "stills")
LOG = os.path.join(ROOT, "renders", "logs", "modeling.log")

# (nama, tinggi, basis, kulit, atasan, bawahan, rok?, rambut panjang?)
CHILDREN = [
    ("CRW_C01", 1.10, "child", "skin-alt", "teal", "sand", False, True),
    ("CRW_C02", 1.18, "child", "skin", "orange", "teal-deep", False, False),
    ("CRW_C03", 1.25, "child", "skin", "cream", "teal-deep", False, False),
    ("CRW_C04", 1.30, "child", "skin-alt", "sand", "grey", False, True),
]
# anak berdiri di depan barisan dewasa (x, y); origin z 0
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
    print("scratch:", bpy.data.filepath)
scn.name = "crowd-v003"

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
figs = sorted([o for o in col.objects if o.type == "MESH" and o.name.startswith("CRW_")],
              key=lambda o: o.name)
faces = [o for o in col.objects if o.name.startswith("CHR_crowd_face")]
print("append v002: %d figur, %d wajah, %d objek di %s"
      % (len(figs), len(faces), len(col.objects), col.name))
if len(figs) != 12 or len(faces) != 12:
    raise RuntimeError("isi v002 tidak sesuai: %d figur / %d wajah" % (len(figs), len(faces)))

# ------------------------------------------- modul pembangun figur & wajah
base_mod = load_module(os.path.join(ROOT, "scripts", "build-crowd.py"), "build_crowd_base")
face_mod = load_module(os.path.join(ROOT, "scripts", "build-crowd-v002.py"), "build_crowd_face")

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

# material wajah diambil dari wajah v002 (slot: kulit, mata, mulut, sklera)
sample_face = faces[0]
m_skin_ref, m_eye, m_mouth, m_sclera = sample_face.data.materials[0:4]
print("material wajah:", [m.name if m else None for m in (m_eye, m_mouth, m_sclera)])

# --------------------------------------------------------- 4 anak sungguhan
new_figs, new_faces = [], []
for (name, height, base, skin, shirt, bottom, skirt, long_hair), (px, py) in \
        zip(CHILDREN, CHILD_PLACE):
    fig = base_mod.build_figure(name, base, height, skin, shirt, bottom, skirt,
                                long_hair, col, mats)
    fig.location = (px, py, 0.0)
    fig.parent = ctl
    fig.matrix_parent_inverse = ctl.matrix_world.inverted()
    fig["part"] = "anak 5,8 kepala (v003)"
    face, met = face_mod.build_face(fig, m_eye, m_mouth, m_sclera, col)
    new_figs.append(fig)
    new_faces.append(face)
    print("%-8s tinggi=%.3f m  kepala z=%.3f r=(%.3f,%.3f,%.3f)  verts figur=%d wajah=%d"
          % (fig.name, fig.dimensions.z, met[0], met[1], met[2], met[3],
             len(fig.data.vertices), len(face.data.vertices)))
    if abs(fig.dimensions.z - height) > 0.002:
        raise RuntimeError("%s tinggi %.4f != %.2f" % (name, fig.dimensions.z, height))
    if abs(fig.location.z) > 1e-6:
        raise RuntimeError("%s origin z bukan 0" % name)

# rasio kepala per anak (tinggi / tinggi kepala) harus ~5,8
for fig, face in zip(new_figs, new_faces):
    hz, hrx, hry, hrz = face_mod.head_metrics(fig)
    print("%-8s tinggi %.3f m / kepala %.3f m = %.2f kepala"
          % (fig.name, fig.dimensions.z, hrz * 2.0, fig.dimensions.z / (hrz * 2.0)))

log("MODEL - crowd_v003: 4 anak baru CRW_C01-C04 (1,10/1,18/1,25/1,30 m, %.1f-%.1f "
    "kepala, %d wajah), 12 figur v002 tidak diubah"
    % (min(f.dimensions.z / (face_mod.head_metrics(f)[3] * 2.0) for f in new_figs),
       max(f.dimensions.z / (face_mod.head_metrics(f)[3] * 2.0) for f in new_figs),
       len(new_faces)))

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
    raise RuntimeError("CAM_preview tidak ada di PREVIEW v002")
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


p1 = os.path.join(STILLS, "crowd-v003_preview-01.png")
p2 = os.path.join(STILLS, "crowd-v003_preview-02.png")
render(p1, (0.15, -7.20, 2.55), (0.0, 0.25, 1.05), 40.0)
render(p2, (0.00, -4.10, 1.35), (0.00, -1.60, 0.72), 45.0)
log("VERIFY - crowd-v003 preview (skala 50%%): %s, %s"
    % (os.path.basename(p1), os.path.basename(p2)))

# ----------------------------------------------------------------- simpan
look_at(cam, (0.15, -7.20, 2.55), (0.0, 0.25, 1.05), 40.0)
scn.render.resolution_percentage = 100
scn.render.filepath = "//"
purge_libraries()
drop_render_result()
bpy.ops.wm.save_as_mainfile(filepath=OUT)
size_kb = round(os.path.getsize(OUT) / 1024.0)
log("MODEL - crowd_v003.blend disimpan (%.0f KB, %d objek di CHR_crowd)"
    % (size_kb, len(col.objects)))

print("=== RINGKASAN ===")
print("figur:", len([o for o in col.objects if o.name.startswith("CRW_")]),
      "| wajah:", len([o for o in col.objects if o.name.startswith("CHR_crowd_face")]),
      "| objek koleksi:", len(col.objects))
print("tinggi anak:", [round(o.dimensions.z, 3) for o in new_figs])
print("lokasi anak:", [(round(o.location.x, 2), round(o.location.y, 2),
                        round(o.location.z, 2)) for o in new_figs])
print("parent anak:", [o.parent.name if o.parent else None for o in new_figs])
print("images:", [i.name for i in bpy.data.images])
print("libraries:", [l.filepath for l in bpy.data.libraries])
print("engine=%s vt=%s res=%dx%d fps=%d frame=%d"
      % (scn.render.engine, scn.view_settings.view_transform,
         scn.render.resolution_x, scn.render.resolution_y, scn.render.fps,
         scn.frame_current))

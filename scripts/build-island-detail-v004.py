"""Build assets/env/island-detail_v004.blend — tiga perbaikan Scene 1.

v004 (25 Nov 2026) — permintaan Director:
  1. Pohon pesisir 150 -> **220 pohon**, skala 1,4–2,0, klaster 12–20 pohon,
     jarak pantai **8–22 m**, tajuk **1,3x** (v002/v003: 150 pohon, 1,25–1,75,
     klaster 9–16, 10–25 m, tajuk 1,2x). Tujuannya supaya dari kamera aerial
     120 m tajuk terbaca sebagai massa, bukan garis.
  2. Manado Tua: ridge/lembah lebih tegas — amplitudo displacement 36 m ->
     **50,4 m (+40 %)** dan tutupan vegetasi ditambah (1.400 -> 1.800 kartu,
     dibias ke punggung ridge). Puncak tetap **745 m**, lokasi tetap
     (-5362, 1404,2).
  3. Fasad dive shop simetris: teras digeser 5,00–15,00 -> **6,00–16,00**
     (sumbu pintu x = 11,00), tiang 3 -> **4** (2 kiri + 2 kanan), jadi
     pintu benar-benar di tengah. Jumlah objek fasad tetap **14**: objek
     `ENV_shop_trim` dilebur ke `ENV_shop_porch-deck` (balok tepi teras) dan
     `ENV_shop_porch-roof` (lis dinding), materialnya sama (MAT_detail_wood).

Tetap: 3.000 rumpun rumput, 200 kelapa sebaran campuran, 12 rumah kampung,
dermaga, bidang air 4 km, annex atap putih, dan seluruh isi v003 lain.

Sumber: `island-detail_v003.blend` di-append `link=False`, lalu hanya bagian
di atas yang dibangun ulang. Base Manado Tua diambil dari `surface.blend`
(mesh asli, bukan hasil displace v003) supaya ridge bisa dibuat ulang.

Setelan file: EEVEE, 1920x1080, 24 fps, view transform Standard, frame 1,
tanpa pack tekstur, tanpa library. Skrip idempoten (mulai dari wipe).
Lampu pratinjau dipasang hanya saat render lalu dihapus sebelum simpan.

    blender -b --python scripts/build-island-detail-v004.py
"""
import bpy
import bmesh
import math
import os
import random
import time

from mathutils import Vector

try:
    from mathutils.noise import noise as mnoise
except Exception:  # pragma: no cover
    def mnoise(v):
        return math.sin(v.x * 1.7) * math.cos(v.y * 1.3) * 0.5

try:
    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
except NameError:  # dieksekusi lewat exec(): __file__ tidak ada
    ROOT = r"D:\Tugas Semester 5\Grafika Komputer\Project-Animasi"

ENV_DIR = os.path.join(ROOT, "assets", "env")
SRC = os.path.join(ENV_DIR, "island-detail_v003.blend")
SURFACE = os.path.join(ENV_DIR, "surface.blend")
OUT = os.path.join(ENV_DIR, "island-detail_v004.blend")
WIPE = os.path.join(ROOT, "renders", "tmp", "_wipe.blend")
STILLS = os.path.join(ROOT, "renders", "stills")
LOG = os.path.join(ROOT, "renders", "logs", "modeling.log")

SEED = 20261125

# --- pohon pesisir ---------------------------------------------------------
COASTAL_COUNT = 220
COAST_D0, COAST_D1 = 8.0, 22.0          # jarak pantai (m)
CLUSTER_MIN, CLUSTER_MAX = 12, 20       # pohon per klaster
CLUSTER_GAP = 22.0                      # jarak minimum antar pusat klaster (m)
TREE_GAP = 2.30                         # jarak minimum antar pohon (m)
SCALE_MIN, SCALE_MAX = 1.40, 2.00
FROND_PREV, FROND_TARGET = 1.20, 1.30   # tajuk v003 -> v004

# --- Manado Tua -----------------------------------------------------------
MANADO_AMP = 36.0 * 1.40                # amplitudo ridge v002 36 m -> 50,4 m
MANADO_VEG = 1800                       # v003: 1.400 kartu
MANADO_PEAK = 745.0
RIDGE_LOW, RIDGE_HIGH = 0.35, 0.60      # ambang "punggung ridge"

# --- fasad dive shop ------------------------------------------------------
WALL_Y = 2.00
FRONT_Y = 1.90
FLOOR_Z = 0.62
DOOR_CX = 11.00
PORCH_X0, PORCH_X1 = 6.00, 16.00        # simetris terhadap pintu (sumbu 11,00)
PORCH_Y0 = -0.50
POSTS_X = (6.40, 9.40, 12.60, 15.60)    # 2 kiri + 2 kanan pintu
ROOF_Z0, ROOF_Z1 = 3.00, 3.20

BLOCKED = [
    (-10.0, -118.0, 10.0, 6.0),   # dermaga + tiang
    (-4.0, -6.0, 26.0, 20.0),     # dive shop
    (20.0, -2.0, 36.0, 14.0),     # annex atap putih
]


def log(line):
    stamp = time.strftime("%H:%M")
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as fh:
            fh.write("[%s] %s\n" % (stamp, line))
    except Exception as err:  # pragma: no cover
        print("peringatan log:", err)
    print("[%s] %s" % (stamp, line))


# --------------------------------------------------------------------- utils
def srgb(hex_color):
    h = hex_color.lstrip("#")
    out = []
    for i in (0, 2, 4):
        u = int(h[i:i + 2], 16) / 255.0
        out.append(u / 12.92 if u <= 0.04045 else ((u + 0.055) / 1.055) ** 2.4)
    return out


def set_input(node, name, value):
    if name in node.inputs:
        node.inputs[name].default_value = value


def get_or_make(name, hex_color, rough=0.85, metallic=0.0):
    mat = bpy.data.materials.get(name)
    if mat is not None:
        return mat
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    col = srgb(hex_color)
    set_input(bsdf, "Base Color", (col[0], col[1], col[2], 1.0))
    set_input(bsdf, "Roughness", rough)
    set_input(bsdf, "Metallic", metallic)
    mat.diffuse_color = (col[0], col[1], col[2], 1.0)
    return mat


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


def blocked(x, y, margin=0.0):
    for x0, y0, x1, y1 in BLOCKED:
        if x0 - margin <= x <= x1 + margin and y0 - margin <= y <= y1 + margin:
            return True
    return False


class Part:
    """Kumpulan kotak dalam satu objek mesh dengan beberapa slot material."""

    def __init__(self, name, coll, mats):
        self.name = name
        self.coll = coll
        self.mats = mats
        self.bm = bmesh.new()

    def box(self, x0, x1, y0, y1, z0, z1, mi=0, drop=0.0):
        zf = z1 - drop
        v = [self.bm.verts.new((x0, y0, z0)), self.bm.verts.new((x1, y0, z0)),
             self.bm.verts.new((x1, y1, z0)), self.bm.verts.new((x0, y1, z0)),
             self.bm.verts.new((x0, y0, zf)), self.bm.verts.new((x1, y0, zf)),
             self.bm.verts.new((x1, y1, z1)), self.bm.verts.new((x0, y1, z1))]
        quads = ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
                 (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7))
        for q in quads:
            try:
                f = self.bm.faces.new([v[i] for i in q])
                f.material_index = mi
            except ValueError:
                pass
        return self

    def boxc(self, cx, cy, cz, sx, sy, sz, mi=0, drop=0.0):
        return self.box(cx - sx * 0.5, cx + sx * 0.5, cy - sy * 0.5, cy + sy * 0.5,
                        cz - sz * 0.5, cz + sz * 0.5, mi, drop)

    def finish(self, bevel=0.0):
        bm = self.bm
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        if bevel > 0.0:
            try:
                bmesh.ops.bevel(bm, geom=list(bm.verts) + list(bm.edges),
                                offset=bevel, segments=1, affect="EDGES",
                                profile=0.5, clamp_overlap=True)
                bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
            except Exception as err:
                print("peringatan bevel", self.name, err)
        me = bpy.data.meshes.new(self.name)
        bm.to_mesh(me)
        bm.free()
        for m in self.mats:
            me.materials.append(m)
        for p in me.polygons:
            p.use_smooth = False
        ob = bpy.data.objects.new(self.name, me)
        self.coll.objects.link(ob)
        ob["part"] = "fasad dive shop v004 (simetris)"
        return ob


def add_camera(name, loc, target, lens, clip_end=30000.0):
    cam_data = bpy.data.cameras.new(name)
    cam_data.lens = lens
    cam_data.clip_start = 0.5
    cam_data.clip_end = clip_end
    cam = bpy.data.objects.new(name, cam_data)
    bpy.context.scene.collection.objects.link(cam)
    cam.location = loc
    cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return cam


def add_sun(name, direction, energy, angle=0.06):
    data = bpy.data.lights.new(name, "SUN")
    data.energy = energy
    data.angle = angle
    ob = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(ob)
    ob.rotation_euler = Vector(direction).to_track_quat("-Z", "Y").to_euler()
    return ob


def mesh_with_modifier(src_mesh, name, setup, coll):
    """Salin mesh, pasang modifier lewat `setup`, lalu jadikan mesh nyata."""
    ob = bpy.data.objects.new(name + "_tmp", src_mesh)
    coll.objects.link(ob)
    setup(ob)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    me.name = name
    bpy.data.objects.remove(ob, do_unlink=True)
    return me


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
scn.name = "island-detail"

with bpy.data.libraries.load(SRC, link=False) as (df, dt):
    src_cols = list(df.collections)
    src_objs = list(df.objects)
    src_worlds = list(df.worlds)
    dt.collections = src_cols
    dt.objects = src_objs
    dt.worlds = src_worlds

root = bpy.data.collections.get("ENV_island-detail")
ctx = bpy.data.collections.get("ENV_island-detail_context")
if root is None or ctx is None:
    raise RuntimeError("koleksi v003 tidak terbawa append")
if root.name not in [c.name for c in scn.collection.children]:
    scn.collection.children.link(root)
if ctx.name in [c.name for c in scn.collection.children]:
    scn.collection.children.unlink(ctx)          # ctx harus anak `root`, bukan scene
if ctx.name not in [c.name for c in root.children]:
    root.children.link(ctx)
for w in bpy.data.worlds:
    scn.world = w
    break

ctl = bpy.data.objects.get("CTL_island-detail")
island = bpy.data.objects.get("ENV_detail_island")
if ctl is None or island is None:
    raise RuntimeError("CTL_island-detail / ENV_detail_island tidak ada")
print("objects sesudah append:", len(bpy.data.objects))
log("MODEL - island-detail_v004: v003 di-append (%d objek), mulai 3 perbaikan"
    % len(bpy.data.objects))

# ------------------------------------------------------------ geometri pantai
def ray_obj(obj, x, y, ztop=2000.0, dist=6000.0):
    lx, ly = x - obj.location.x, y - obj.location.y
    hit, loc, nrm, idx = obj.ray_cast(Vector((lx, ly, ztop)),
                                      Vector((0.0, 0.0, -1.0)), distance=dist)
    if not hit:
        return None
    poly = obj.data.polygons[idx]
    return (Vector((loc.x + obj.location.x, loc.y + obj.location.y,
                    loc.z + obj.location.z)), nrm, poly.material_index)


_HCACHE = {}


def ground_at(x, y):
    key = (round(x, 1), round(y, 1))
    if key not in _HCACHE:
        _HCACHE[key] = ray_obj(island, x, y, ztop=800.0, dist=2000.0)
    return _HCACHE[key]


# pad rumah kampung dari bbox objek yang sudah ada (v003 menyimpan 12 rumah)
house_pads = []
for ob in bpy.data.objects:
    if not ob.name.startswith("ENV_detail_houses"):
        continue
    cos = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    xs = [v.x for v in cos]
    ys = [v.y for v in cos]
    house_pads.append((min(xs) - 1.0, min(ys) - 1.0, max(xs) + 1.0, max(ys) + 1.0))
print("pad rumah:", len(house_pads))

# ----------------------------------------------- 1. pohon pesisir 150 -> 220
old_coast = [o for o in bpy.data.objects if o.name.startswith("ENV_detail_palm-coast")]
old_names = [o.name for o in old_coast]
for o in old_coast:
    bpy.data.objects.remove(o, do_unlink=True)
print("pohon pesisir v003 dihapus:", len(old_names))

coast_me = None
for me in bpy.data.meshes:
    if me.name.startswith("ENV_veg_palm-coastal") and me.users <= 0:
        coast_me = me
        break
if coast_me is None:
    for me in bpy.data.meshes:
        if me.name.startswith("ENV_veg_palm-coastal"):
            coast_me = me
            break
if coast_me is None:
    raise RuntimeError("mesh ENV_veg_palm-coastal tidak ada di v003")

frond_slots = [i for i, m in enumerate(coast_me.materials)
               if m is not None and "frond" in m.name.lower()]
if not frond_slots:
    raise RuntimeError("slot material frond tidak ada di mesh pesisir")
frond_vids = set()
for poly in coast_me.polygons:
    if poly.material_index in frond_slots:
        frond_vids.update(poly.vertices)
crown_z = min(coast_me.vertices[i].co.z for i in frond_vids)
boost = FROND_TARGET / FROND_PREV
for i in frond_vids:
    co = coast_me.vertices[i].co
    co.x *= boost
    co.y *= boost
coast_me.update()
print("mesh pesisir: %d vert, slot frond %s, tajuk %.2fx (naik %.3fx dari v003)"
      % (len(coast_me.vertices), frond_slots, FROND_TARGET, boost))

# --- medan jarak ke garis pantai (chamfer 2 lintasan, kisi 3 m) ------------
COAST_STEP = 3.0
COAST_X0, COAST_X1 = -340.0, 445.0
COAST_Y0, COAST_Y1 = -70.0, 145.0
COAST_W = int((COAST_X1 - COAST_X0) / COAST_STEP) + 1
COAST_H = int((COAST_Y1 - COAST_Y0) / COAST_STEP) + 1
INF = 1e9
_dm = []
for _i in range(COAST_W):
    _x = COAST_X0 + _i * COAST_STEP
    _col = []
    for _j in range(COAST_H):
        _y = COAST_Y0 + _j * COAST_STEP
        _col.append(INF if ray_obj(island, _x, _y, ztop=800.0, dist=2000.0) else 0.0)
    _dm.append(_col)
for _i in range(COAST_W):
    for _j in range(COAST_H):
        _v = _dm[_i][_j]
        if _v == 0.0:
            continue
        if _i > 0:
            _v = min(_v, _dm[_i - 1][_j] + 1.0)
            if _j > 0:
                _v = min(_v, _dm[_i - 1][_j - 1] + 1.41421356)
            if _j < COAST_H - 1:
                _v = min(_v, _dm[_i - 1][_j + 1] + 1.41421356)
        if _j > 0:
            _v = min(_v, _dm[_i][_j - 1] + 1.0)
        _dm[_i][_j] = _v
for _i in range(COAST_W - 1, -1, -1):
    for _j in range(COAST_H - 1, -1, -1):
        _v = _dm[_i][_j]
        if _v == 0.0:
            continue
        if _i < COAST_W - 1:
            _v = min(_v, _dm[_i + 1][_j] + 1.0)
            if _j < COAST_H - 1:
                _v = min(_v, _dm[_i + 1][_j + 1] + 1.41421356)
            if _j > 0:
                _v = min(_v, _dm[_i + 1][_j - 1] + 1.41421356)
        if _j < COAST_H - 1:
            _v = min(_v, _dm[_i][_j + 1] + 1.0)
        _dm[_i][_j] = _v


def coast_dist(x, y):
    i = int(round((x - COAST_X0) / COAST_STEP))
    j = int(round((y - COAST_Y0) / COAST_STEP))
    if not (0 <= i < COAST_W and 0 <= j < COAST_H):
        return None
    v = _dm[i][j]
    if v >= INF:
        return None
    return v * COAST_STEP


print("medan jarak pantai %d x %d selesai" % (COAST_W, COAST_H))

random.seed(SEED)


def plan_clusters(total, lo, hi):
    """Ukuran klaster acak yang jumlahnya tepat `total` dan tiap klaster lo..hi."""
    sizes = []
    rem = total
    guard = 0
    while rem > hi and guard < 200:
        guard += 1
        n = random.randint(lo, hi)
        if rem - n < lo:
            n = rem - lo
        n = max(lo, min(hi, n))
        sizes.append(n)
        rem -= n
    if rem >= lo:
        sizes.append(rem)
        rem = 0
    else:
        need = lo - rem
        for i in range(len(sizes) - 1, -1, -1):
            take = min(hi - sizes[i], need)
            sizes[i] += take
            need -= take
            if need <= 0:
                break
        rem = 0
    assert sum(sizes) == total, (sum(sizes), total)
    assert all(lo <= s <= hi for s in sizes), sizes
    return sizes


CLUSTER_SIZES = plan_clusters(COASTAL_COUNT, CLUSTER_MIN, CLUSTER_MAX)
print("rencana klaster:", len(CLUSTER_SIZES), "klaster,",
      "ukuran", min(CLUSTER_SIZES), "-", max(CLUSTER_SIZES),
      "total", sum(CLUSTER_SIZES))

placed = 0
tries = 0
centres = []
tree_pos = []
scales = []
dists = []
cluster_sizes = []
while len(centres) < len(CLUSTER_SIZES) and tries < 12000:
    tries += 1
    cx = random.uniform(COAST_X0 + 5.0, COAST_X1 - 5.0)
    cy = random.uniform(COAST_Y0 + 5.0, COAST_Y1 - 5.0)
    if any((cx - a) ** 2 + (cy - b) ** 2 < CLUSTER_GAP ** 2 for a, b in centres):
        continue
    cdist = coast_dist(cx, cy)
    if cdist is None or not (COAST_D0 + 1.5 <= cdist <= COAST_D1 - 1.5):
        continue
    if blocked(cx, cy, margin=10.0):
        continue
    if any(x0 - 2.0 <= cx <= x1 + 2.0 and y0 - 2.0 <= cy <= y1 + 2.0
           for x0, y0, x1, y1 in house_pads):
        continue
    centres.append((cx, cy))
    want = CLUSTER_SIZES[len(centres) - 1]
    added = 0
    for _k in range(want * 20):
        if added >= want or placed >= COASTAL_COUNT:
            break
        ang = random.uniform(0.0, math.tau)
        rad = random.uniform(1.8, 9.0) * math.sqrt(random.random() + 1e-6)
        x, y = cx + math.cos(ang) * rad, cy + math.sin(ang) * rad
        hit = ground_at(x, y)
        if hit is None:
            continue
        p, nrm, _mi = hit
        if p.z < 0.10 or p.z > 26.0 or nrm.z < 0.28:
            continue
        if blocked(x, y, margin=5.0):
            continue
        if any(x0 <= x <= x1 and y0 <= y <= y1 for x0, y0, x1, y1 in house_pads):
            continue
        if any((x - px) ** 2 + (y - py) ** 2 < TREE_GAP ** 2 for px, py in tree_pos):
            continue
        d2 = coast_dist(x, y)
        if d2 is None or not (COAST_D0 <= d2 <= COAST_D1):
            continue
        scale = random.uniform(SCALE_MIN, SCALE_MAX)
        inst = bpy.data.objects.new("ENV_detail_palm-coast_%03d" % placed, coast_me)
        root.objects.link(inst)
        inst.location = (x, y, p.z - 0.05)
        inst.rotation_euler = (random.uniform(-0.05, 0.05),
                               random.uniform(-0.05, 0.05),
                               random.uniform(0.0, math.tau))
        inst.scale = (scale, scale, scale)
        inst.parent = ctl
        tree_pos.append((x, y))
        scales.append(scale)
        dists.append(d2)
        placed += 1
        added += 1
    cluster_sizes.append(added)

print("pohon pesisir v004:", placed, "klaster", len(centres), "tries", tries)
print("  skala %.2f - %.2f | jarak pantai %.1f - %.1f m | klaster %d - %d pohon"
      % (min(scales), max(scales), min(dists), max(dists),
         min(cluster_sizes), max(cluster_sizes)))
log("MODEL - pohon pesisir: 150 -> %d pohon, skala %.2f-%.2f, klaster %d-%d pohon, "
    "jarak pantai %.1f-%.1f m, tajuk %.1fx, %d klaster"
    % (placed, min(scales), max(scales), min(cluster_sizes), max(cluster_sizes),
       min(dists), max(dists), FROND_TARGET, len(centres)))
if placed != COASTAL_COUNT:
    log("BLOCKED - pohon pesisir hanya %d dari %d" % (placed, COASTAL_COUNT))

# --------------------------------------------------- 2. Manado Tua lebih tegas
old_manado = bpy.data.objects.get("ENV_detail_manado-tua")
old_veg = bpy.data.objects.get("ENV_detail_manado-tua_veg")
if old_manado is None:
    raise RuntimeError("ENV_detail_manado-tua tidak ada")
MANADO_LOC = old_manado.location.copy()
old_meshes = []
if old_veg is not None:
    old_meshes.append(old_veg.data)
    bpy.data.objects.remove(old_veg, do_unlink=True)
old_meshes.append(old_manado.data)

# base asli dari surface.blend (mesh belum di-displace)
with bpy.data.libraries.load(SURFACE, link=False) as (df, dt):
    dt.objects = ["ENV_surface_manado-tua"]
base_src = next((o for o in dt.objects if o is not None), None)
if base_src is None:
    raise RuntimeError("ENV_surface_manado-tua tidak ada di surface.blend")
base_copy = base_src.data.copy()
base_copy.name = "ENV_detail_manado-tua_src"
base_loc = base_src.location.copy()
for c in list(base_src.users_collection):
    c.objects.unlink(base_src)
bpy.data.objects.remove(base_src, do_unlink=True)
# buang koleksi sisa append surface.blend yang jadi kosong
for c in list(bpy.data.collections):
    if c in (root, ctx):
        continue
    if not c.objects and not c.children and \
            c.name not in [x.name for x in scn.collection.children]:
        bpy.data.collections.remove(c)
off = base_loc - MANADO_LOC
if off.length > 1e-4:
    for v in base_copy.vertices:
        v.co += off
    print("offset base Manado Tua %.2f m diterapkan" % off.length)


def _subdiv(ob):
    mod = ob.modifiers.new("subd", "SUBSURF")
    mod.subdivision_type = "SIMPLE"
    mod.levels = 1
    mod.render_levels = 1


sub_me = mesh_with_modifier(base_copy, "ENV_detail_manado-tua", _subdiv, root)
vmax = max(sub_me.vertices, key=lambda v: v.co.z)
peak = Vector((vmax.co.x, vmax.co.y, vmax.co.z))
R = max(math.hypot(v.co.x - peak.x, v.co.y - peak.y) for v in sub_me.vertices)
peak_before = peak.z
print("manado base: %d vert, puncak %.2f m, R %.1f m"
      % (len(sub_me.vertices), peak_before, R))

ridge_sum = [0.0, 0]
for v in sub_me.vertices:
    dx, dy = v.co.x - peak.x, v.co.y - peak.y
    r = math.hypot(dx, dy)
    ang = math.atan2(dy, dx)
    rn = min(1.0, r / R)
    h = v.co.z
    ridge = math.cos(ang * 14.0 + 0.6) * 0.62 + math.cos(ang * 7.0 - 1.1) * 0.38
    env = math.sin(math.pi * rn) ** 0.75
    peak_fade = min(1.0, max(0.0, (r - 70.0) / 180.0))
    coast_fade = min(1.0, max(0.0, (h - 6.0) / 40.0))
    disp = MANADO_AMP * env * ridge * peak_fade * coast_fade
    disp += 9.0 * mnoise(Vector((v.co.x * 0.0045, v.co.y * 0.0045, v.co.z * 0.003)))
    d = disp * peak_fade * coast_fade
    v.co.z += d
    ridge_sum[0] += abs(d)
    ridge_sum[1] += 1
for p in sub_me.polygons:
    p.use_smooth = True
sub_me.name = "ENV_detail_manado-tua_displaced"


def _manado_decimate(ob):
    mod = ob.modifiers.new("dec", "DECIMATE")
    mod.ratio = 0.55


detail_me = mesh_with_modifier(sub_me, "ENV_detail_manado-tua", _manado_decimate, root)
for p in detail_me.polygons:
    p.use_smooth = True
if detail_me.materials and detail_me.materials[0] is not None:
    detail_me.materials[0] = bpy.data.materials.get("MAT_detail_manado-vegetation") \
        or detail_me.materials[0]
peak_after = max(v.co.z for v in detail_me.vertices)
old_manado.data = detail_me
old_manado.location = MANADO_LOC
detail_me.name = "ENV_detail_manado-tua"
for me in old_meshes:
    if me.users == 0:
        bpy.data.meshes.remove(me)
if sub_me.users == 0:
    bpy.data.meshes.remove(sub_me)
if base_copy.users == 0:
    bpy.data.meshes.remove(base_copy)

mean_disp = ridge_sum[0] / max(ridge_sum[1], 1)
print("manado v004: amplitudo %.1f m (+40%%), |disp| rata-rata %.2f m, "
      "puncak %.2f m (target %.0f), lokasi %s"
      % (MANADO_AMP, mean_disp, peak_after, MANADO_PEAK,
         tuple(round(v, 1) for v in MANADO_LOC)))
log("MODEL - Manado Tua: ridge/lembah amplitudo 36 -> %.1f m (+40%%), %d vert, "
    "puncak %.1f m (tetap), lokasi %.0f/%.0f (tetap)"
    % (MANADO_AMP, len(detail_me.vertices), peak_after, MANADO_LOC.x, MANADO_LOC.y))
if abs(peak_after - MANADO_PEAK) > 2.0:
    log("BLOCKED - puncak Manado Tua bergeser ke %.1f m" % peak_after)

# --------------------------------- tutupan vegetasi Manado Tua (punggung ridge)
MAT_COVER = bpy.data.materials.get("MAT_detail_veg-cover")
MAT_COVER_D = bpy.data.materials.get("MAT_detail_veg-cover-dark")
if MAT_COVER is None or MAT_COVER_D is None:
    raise RuntimeError("material tutupan vegetasi tidak ada")

random.seed(SEED + 7)
manado = old_manado
bm = bmesh.new()
placed_v = 0
ridge_cards = 0
tries = 0
mx0, mx1 = MANADO_LOC.x - 1790.0, MANADO_LOC.x + 1790.0
my0, my1 = MANADO_LOC.y - 1650.0, MANADO_LOC.y + 1660.0
peak_local = Vector((peak.x, peak.y, 0.0))
while placed_v < MANADO_VEG and tries < 60000:
    tries += 1
    x = random.uniform(mx0, mx1)
    y = random.uniform(my0, my1)
    hit = ray_obj(manado, x, y, ztop=2200.0, dist=3200.0)
    if hit is None:
        continue
    p, nrm, _m = hit
    if p.z < 6.0 or p.z > 640.0 or nrm.z < 0.42:
        continue
    lx, ly = x - MANADO_LOC.x, y - MANADO_LOC.y
    ang = math.atan2(ly - peak.y, lx - peak.x)
    ridge = math.cos(ang * 14.0 + 0.6) * 0.62 + math.cos(ang * 7.0 - 1.1) * 0.38
    # punggung ridge (ridge > 0,35) selalu diterima; lembah lebih jarang
    if ridge > RIDGE_LOW:
        ridge_cards += 1
    elif random.random() > 0.42:
        continue
    if p.z > 520.0 and random.random() > 0.55:      # dekat puncak makin jarang
        continue
    w = random.uniform(16.0, 30.0) * (1.0 + 0.25 * max(0.0, ridge))
    hh = random.uniform(12.0, 24.0)
    yaw = random.uniform(0.0, math.tau)
    mi = 0 if random.random() < 0.70 else 1
    n = nrm.normalized()
    up = Vector((0.0, 0.0, 1.0))
    u = n.cross(up)
    if u.length < 1e-5:
        u = Vector((1.0, 0.0, 0.0))
    u.normalize()
    v = u.cross(n).normalized()
    cu, cv = math.cos(yaw), math.sin(yaw)
    ax, ay = u * (w * 0.5), v * (hh * 0.5)
    c0 = p + n * 0.6
    p0 = c0 - ax * cu - ay * cv
    p1 = c0 + ax * cu - ay * cv
    p2 = c0 + ax * cu + ay * cv
    p3 = c0 - ax * cu + ay * cv
    try:
        f = bm.faces.new([bm.verts.new(tuple(q)) for q in (p0, p1, p2, p3)])
        f.material_index = mi
    except ValueError:
        continue
    placed_v += 1

veg_me = bpy.data.meshes.new("ENV_detail_manado-tua_veg")
bm.to_mesh(veg_me)
bm.free()
veg_me.materials.append(MAT_COVER)
veg_me.materials.append(MAT_COVER_D)
veg_ob = bpy.data.objects.new("ENV_detail_manado-tua_veg", veg_me)
root.objects.link(veg_ob)
veg_ob.parent = ctl
print("manado veg v004:", placed_v, "kartu, %d di punggung ridge, vert %d"
      % (ridge_cards, len(veg_me.vertices)))
log("MODEL - Manado Tua vegetasi: 1.400 -> %d kartu (%d di punggung ridge)"
    % (placed_v, ridge_cards))

# ------------------------------------------- 3. fasad dive shop simetris
MAT_WOOD = get_or_make("MAT_detail_wood", "#E8D5B0", rough=0.82)
MAT_ROOF = get_or_make("MAT_detail_roof", "#E4713C", rough=0.62)

OLD_FACADE = ["ENV_shop_porch-deck", "ENV_shop_porch-roof", "ENV_shop_trim",
              "ENV_shop_porch-post_01", "ENV_shop_porch-post_02",
              "ENV_shop_porch-post_03"]
for n in OLD_FACADE:
    ob = bpy.data.objects.get(n)
    if ob is not None:
        me = ob.data
        bpy.data.objects.remove(ob, do_unlink=True)
        if me.users == 0:
            bpy.data.meshes.remove(me)
print("fasad lama dibuang:", [n for n in OLD_FACADE])

# --- teras kayu (balok tepi v003 dilebur ke sini, material sama) -----------
deck = Part("ENV_shop_porch-deck", ctx, [MAT_WOOD])
n_boards, gap = 8, 0.02
bw = ((WALL_Y - PORCH_Y0) - (n_boards - 1) * gap) / n_boards
for i in range(n_boards):
    y0 = PORCH_Y0 + i * (bw + gap)
    deck.box(PORCH_X0, PORCH_X1, y0, y0 + bw, FLOOR_Z - 0.07, FLOOR_Z, mi=0)
for bx in (6.35, 11.00, 15.65):                      # balok bawah papan (simetris)
    deck.box(bx - 0.10, bx + 0.10, PORCH_Y0 + 0.05, WALL_Y, FLOOR_Z - 0.20,
             FLOOR_Z - 0.07, mi=0)
deck.box(PORCH_X0, PORCH_X1, PORCH_Y0 - 0.06, PORCH_Y0, FLOOR_Z - 0.20,
         FLOOR_Z, mi=0)                              # balok tepi teras (eks trim)
deck_ob = deck.finish(bevel=0.004)

# --- 4 tiang: 2 kiri + 2 kanan pintu, simetris -----------------------------
posts = []
for i, cx in enumerate(POSTS_X, start=1):
    p = Part("ENV_shop_porch-post_%02d" % i, ctx, [MAT_WOOD])
    p.boxc(cx, -0.30, (FLOOR_Z + ROOF_Z0) * 0.5, 0.18, 0.18, ROOF_Z0 - FLOOR_Z, mi=0)
    p.boxc(cx, -0.30, FLOOR_Z + 0.05, 0.28, 0.28, 0.10, mi=0)      # alas tiang
    p.boxc(cx, -0.30, ROOF_Z0 - 0.05, 0.26, 0.26, 0.10, mi=0)      # kepala tiang
    p.boxc(cx, -0.30, 0.14, 0.18, 0.18, 1.06, mi=0)                # pancang ke air
    posts.append(p.finish(bevel=0.005))

# --- atap teras (lis dinding v003 dilebur ke sini) -------------------------
roof = Part("ENV_shop_porch-roof", ctx, [MAT_ROOF, MAT_WOOD])
roof.box(PORCH_X0 - 0.12, PORCH_X1 + 0.12, PORCH_Y0 - 0.32, 2.05,
         ROOF_Z0, ROOF_Z1, mi=0, drop=0.12)
roof.box(PORCH_X0 - 0.18, PORCH_X1 + 0.18, PORCH_Y0 - 0.38, PORCH_Y0 - 0.24,
         ROOF_Z0 - 0.12, ROOF_Z1, mi=1)
for cx in POSTS_X:
    roof.box(cx - 0.08, cx + 0.08, PORCH_Y0 - 0.24, WALL_Y,
             ROOF_Z0 - 0.12, ROOF_Z0, mi=1)
roof.box(WALL_Y - 0.05, WALL_Y, PORCH_X0, PORCH_X1, ROOF_Z0 - 0.16,
         ROOF_Z0 - 0.08, mi=1)                        # lis dinding (eks trim)
roof_ob = roof.finish(bevel=0.004)

facade = [o for o in bpy.data.objects if o.name.startswith("ENV_shop")]
print("objek fasad v004:", len(facade), sorted(o.name for o in facade))
left = [x for x in POSTS_X if x < DOOR_CX]
right = [x for x in POSTS_X if x > DOOR_CX]
print("tiang kiri", left, "kanan", right,
      "| offset kiri", [round(DOOR_CX - x, 2) for x in left],
      "kanan", [round(x - DOOR_CX, 2) for x in right])
log("MODEL - fasad dive shop: teras 5,00-15,00 -> 6,00-16,00 (sumbu pintu 11,00), "
    "tiang 3 -> 4 (2 kiri + 2 kanan), trim dilebur ke deck/roof, %d objek fasad"
    % len(facade))
if len(facade) != 14:
    log("BLOCKED - objek fasad %d, target 14" % len(facade))

# ------------------------------------------------------------------ kamera
cam_aerial = bpy.data.objects.get("CAM_detail_aerial")
if cam_aerial is None:
    cam_aerial = add_camera("CAM_detail_aerial", (170.0, -230.0, 120.0),
                            (-180.0, 130.0, 25.0), 24.0)
else:
    cam_aerial.location = (170.0, -230.0, 120.0)
    cam_aerial.data.lens = 24.0
cam_village = bpy.data.objects.get("CAM_detail_village")
if cam_village is None:
    cam_village = add_camera("CAM_detail_village", (95.0, -150.0, 68.0),
                             (-4.0, 26.0, 4.0), 45.0)
cam_facade = bpy.data.objects.get("CAM_shop-facade-01")
if cam_facade is None:
    cam_facade = add_camera("CAM_shop-facade-01", (11.0, -10.5, 2.55),
                            (11.0, 1.70, 2.15), 32.0)
scn.camera = cam_aerial
print("kamera aerial: z %.1f m, lens %.0f mm" % (cam_aerial.location.z, cam_aerial.data.lens))

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
scn.render.film_transparent = False
for engine in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
    try:
        scn.render.engine = engine
        break
    except TypeError:
        continue
try:
    scn.eevee.taa_render_samples = 24
except Exception:
    pass
print("engine:", scn.render.engine)

temp_lights = [add_sun("LGT_tmp-key", (-0.30, 0.78, -0.55), 3.4, 0.05),
               add_sun("LGT_tmp-fill", (0.62, 0.55, -0.30), 1.1, 0.4)]


def render(path, cam, pct=50):
    scn.camera = cam
    scn.render.resolution_percentage = pct
    scn.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("RENDER", path, os.path.exists(path))


p1 = os.path.join(STILLS, "island-detail-v004_preview-01.png")
p2 = os.path.join(STILLS, "island-detail-v004_preview-02.png")
p3 = os.path.join(STILLS, "island-detail-v004_facade-01.png")
render(p1, cam_aerial)
render(p2, cam_village)
render(p3, cam_facade)
for lt in temp_lights:
    bpy.data.objects.remove(lt, do_unlink=True)
log("VERIFY - render 50%%: %s (aerial 24 mm z 120 m), %s (kampung), %s (fasad)"
    % (os.path.basename(p1), os.path.basename(p2), os.path.basename(p3)))

# ----------------------------------------------------------------- simpan
scn.camera = cam_aerial
scn.render.resolution_percentage = 100
scn.render.filepath = "//"
purge_libraries()
drop_render_result()
bpy.ops.wm.save_as_mainfile(filepath=OUT)
size_mb = round(os.path.getsize(OUT) / 1048576.0, 2)

n_coast = len([o for o in bpy.data.objects if o.name.startswith("ENV_detail_palm-coast")])
n_extra = len([o for o in bpy.data.objects if o.name.startswith("ENV_detail_palm-extra")])
n_house = len([o for o in bpy.data.objects if o.name.startswith("ENV_detail_houses")])
grass = bpy.data.objects.get("ENV_detail_grass")
print("=== RINGKASAN ===")
print("pohon pesisir", n_coast, "| kelapa sebaran", n_extra,
      "| total kelapa", n_coast + n_extra)
print("rumput objek", grass.name if grass else None,
      "verts", len(grass.data.vertices) if grass else 0)
print("rumah", n_house, "| objek fasad", len(facade))
print("manado puncak", round(max(v.co.z for v in old_manado.data.vertices), 2),
      "| veg", len(veg_ob.data.vertices) // 4, "kartu")
print("images (harus 0)", [i.name for i in bpy.data.images])
print("libraries (harus 0)", [l.filepath for l in bpy.data.libraries])
print("lights (harus 0)", [o.name for o in bpy.data.objects if o.type == "LIGHT"])
print("dims:", round(scn.render.resolution_x * 0.5), "x",
      round(scn.render.resolution_y * 0.5), "preview")
log("MODEL - island-detail_v004.blend disimpan (%.2f MB, %d objek, %d pohon pesisir, "
    "%d rumah, %d objek fasad)" % (size_mb, len(bpy.data.objects), n_coast,
                                   n_house, len(facade)))
print("SELESAI", OUT, size_mb, "MB")

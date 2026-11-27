"""Build assets/env/island-detail_v005.blend — kampung terbaca dari aerial.

v005 (27 Nov 2026) — permintaan Director, tiga hal:

  1. **Kampung tak terbaca.** v004 hanya 12 rumah dalam 2 baris. v005 menambah
     **18 rumah kecil** di belakang deretan utama (total **30**), **1 jalan
     tanah utama** (mesh pita, menyambung dermaga -> deret depan -> deret
     belakang -> deret baru), dan **6 pohon kelapa** di sekitar rumah.
  2. **Pohon hanya di satu pantai.** Klaster pesisir v004 menumpuk di barat
     kampung. v005 menyebar 220 pohon pesisir ke **tiga sektor pantai**
     (barat / tengah-teluk / timur) dengan kuota klaster per sektor.
  3. **Manado Tua hijau rata.** Kartu vegetasi 1.800 -> **2.400**, ditambah
     variasi hijau gelap/terang: 4 tone kartu (dipilih menurut punggung
     ridge / lembah / ketinggian) dan material lereng gunung memakai gradien
     hijau + noise, bukan satu warna datar.

Tetap: 220 kelapa pesisir + 200 kelapa sebaran = 420, fasad dive shop 4 tiang,
dermaga, bidang air, 3.000 rumpun rumput, annex, dan seluruh isi v004 lain.

Sumber: `island-detail_v004.blend` dibuka langsung (file proyek sendiri), hanya
bagian di atas yang diubah, lalu disimpan sebagai v005 — v004 tidak ditimpa.

Setelan: EEVEE, 1920x1080, 24 fps, Standard, frame 1, tanpa pack, tanpa library.
Lampu pratinjau dipasang saat render lalu dihapus sebelum simpan.

    blender -b --python scripts/build-island-detail-v005.py
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
except NameError:
    ROOT = r"D:\Tugas Semester 5\Grafika Komputer\Project-Animasi"

ENV_DIR = os.path.join(ROOT, "assets", "env")
SRC = os.path.join(ENV_DIR, "island-detail_v004.blend")
OUT = os.path.join(ENV_DIR, "island-detail_v005.blend")
STILLS = os.path.join(ROOT, "renders", "stills")
LOG = os.path.join(ROOT, "renders", "logs", "modeling.log")

SEED = 20261127

# --- pohon pesisir ---------------------------------------------------------
COASTAL_COUNT = 220
COAST_D0, COAST_D1 = 8.0, 22.0
CLUSTER_MIN, CLUSTER_MAX = 12, 20
CLUSTER_GAP = 22.0
TREE_GAP = 2.30
SCALE_MIN, SCALE_MAX = 1.40, 2.00
HOUSE_PALMS = 6
# sektor pantai: (nama, x0, x1, kuota pohon)
SECTORS = [("barat", -340.0, -90.0, 74),
           ("tengah", -90.0, 60.0, 73),
           ("timur", 60.0, 445.0, 73)]

# --- kampung ---------------------------------------------------------------
SMALL_HOUSES = 18
ROW_A_Y, ROW_B_Y = 41.6, 48.8
ROW_A_X = (-44.0, -36.0, -28.0, -20.0, -12.0, -4.0, 4.0, 12.0, 20.0)
ROW_B_X = (-40.0, -32.0, -24.0, -16.0, -8.0, 0.0, 8.0, 16.0, 24.0)
ROAD_W = 3.00
ROAD_PTS = [
    (0.0, 1.8), (-2.4, 3.6), (-6.0, 5.2), (-10.5, 7.6), (-14.5, 10.2),
    (-24.0, 10.8), (-33.0, 11.2), (-38.6, 14.0), (-39.4, 20.0), (-39.2, 26.0),
    (-30.0, 25.8), (-12.0, 25.8), (10.0, 25.8), (32.0, 25.8), (50.0, 25.8),
    (54.0, 31.0), (54.0, 40.0), (52.0, 45.0), (40.0, 45.0), (20.0, 45.0),
    (0.0, 45.0), (-20.0, 45.0), (-38.0, 45.0), (-47.0, 44.0),
]

# --- Manado Tua -----------------------------------------------------------
MANADO_VEG = 2400
RIDGE_LOW, RIDGE_HIGH = 0.35, 0.60


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


class Part:
    """Kumpulan kotak/plat dalam satu objek mesh dengan beberapa slot material."""

    def __init__(self, name, coll, mats):
        self.name = name
        self.coll = coll
        self.mats = mats
        self.bm = bmesh.new()

    def box(self, x0, x1, y0, y1, z0, z1, mi=0):
        v = [self.bm.verts.new((x0, y0, z0)), self.bm.verts.new((x1, y0, z0)),
             self.bm.verts.new((x1, y1, z0)), self.bm.verts.new((x0, y1, z0)),
             self.bm.verts.new((x0, y0, z1)), self.bm.verts.new((x1, y0, z1)),
             self.bm.verts.new((x1, y1, z1)), self.bm.verts.new((x0, y1, z1))]
        for q in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
                  (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
            try:
                f = self.bm.faces.new([v[i] for i in q])
                f.material_index = mi
            except ValueError:
                pass
        return self

    def boxc(self, cx, cy, cz, sx, sy, sz, mi=0):
        return self.box(cx - sx * 0.5, cx + sx * 0.5, cy - sy * 0.5, cy + sy * 0.5,
                        cz - sz * 0.5, cz + sz * 0.5, mi)

    def face(self, pts, mi=0):
        try:
            f = self.bm.faces.new([self.bm.verts.new(p) for p in pts])
            f.material_index = mi
        except ValueError:
            pass
        return self

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
        return ob


# --------------------------------------------------------------------- setup
os.makedirs(STILLS, exist_ok=True)


def load_into_empty(path):
    """Muat file sumber tanpa open_mainfile (aman untuk sesi MCP).

    Semua objek/koleksi dihapus, lalu seluruh koleksi dari file sumber
    di-append dan di-link ke scene aktif.
    """
    scn = bpy.context.scene
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for coll in list(bpy.data.collections):
        bpy.data.collections.remove(coll)
    with bpy.data.libraries.load(path, link=False) as (src, dst):
        dst.collections = list(src.collections)
    children = {c.name for coll in dst.collections if coll for c in coll.children}
    for coll in dst.collections:
        if coll is not None and coll.name not in children:
            scn.collection.children.link(coll)
    for ob in bpy.data.objects:
        if not ob.users_collection:
            scn.collection.objects.link(ob)
    return scn


print("muat", SRC)
scn = load_into_empty(SRC)
root = bpy.data.collections.get("ENV_island-detail")
ctx = bpy.data.collections.get("ENV_island-detail_context")
ctl = bpy.data.objects.get("CTL_island-detail")
island = bpy.data.objects.get("ENV_detail_island")
manado = bpy.data.objects.get("ENV_detail_manado-tua")
if None in (root, ctx, ctl, island, manado):
    raise RuntimeError("struktur v004 tidak lengkap")
print("objek v004:", len(bpy.data.objects))
log("PLAN - island-detail_v005: 30 rumah + jalan tanah, palm 3 sektor, "
    "Manado Tua 2.400 kartu + variasi hijau")


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


BLOCKED = [
    (-10.0, -118.0, 10.0, 6.0),   # dermaga + tiang
    (-4.0, -6.0, 26.0, 20.0),     # dive shop
    (20.0, -2.0, 36.0, 14.0),     # annex atap putih
]


def blocked(x, y, margin=0.0):
    for x0, y0, x1, y1 in BLOCKED:
        if x0 - margin <= x <= x1 + margin and y0 - margin <= y <= y1 + margin:
            return True
    return False


# ------------------------------------------------------- pad rumah (v004 + baru)
house_pads = []
for ob in bpy.data.objects:
    if not ob.name.startswith("ENV_detail_houses"):
        continue
    cos = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    xs = [v.x for v in cos]
    ys = [v.y for v in cos]
    house_pads.append((min(xs), min(ys), max(xs), max(ys)))
print("pad rumah v004:", len(house_pads))

MAT_WALL = get_or_make("MAT_detail_wall", "#F2E9DC", rough=0.88)
MAT_WOOD = get_or_make("MAT_detail_wood", "#E8D5B0", rough=0.82)
MAT_ROOF = get_or_make("MAT_detail_roof", "#E4713C", rough=0.62)
MAT_GLASS = get_or_make("MAT_detail_window", "#0F5C63", rough=0.18)
MAT_ROAD = get_or_make("MAT_detail_road", "#C2A077", rough=0.98)

random.seed(SEED)
rng = random.Random(SEED)

# ============================================== 1. 18 rumah kecil di belakang
def build_small_house(name, cx, cy, gz, yaw):
    w = rng.uniform(4.0, 4.8)
    d = rng.uniform(3.1, 3.7)
    wh = rng.uniform(2.15, 2.40)
    floor_z = 0.42 + rng.uniform(-0.05, 0.06)
    rise = rng.uniform(0.95, 1.25)
    eave = floor_z + wh
    ridge = eave + rise
    p = Part(name, root, [MAT_WALL, MAT_WOOD, MAT_ROOF, MAT_GLASS])

    for px in (-w * 0.5 + 0.30, 0.0, w * 0.5 - 0.30):
        for py in (-d * 0.5 + 0.30, d * 0.5 - 0.30):
            p.boxc(px, py, (floor_z - 0.30) * 0.5, 0.15, 0.15, floor_z + 0.30, mi=1)
    p.boxc(0.0, 0.0, floor_z, w, d, 0.10, mi=1)                       # lantai
    p.boxc(0.0, -d * 0.5 + 0.065, floor_z + wh * 0.5, w, 0.13, wh, mi=0)
    p.boxc(0.0, d * 0.5 - 0.065, floor_z + wh * 0.5, w, 0.13, wh, mi=0)
    p.boxc(-w * 0.5 + 0.065, 0.0, floor_z + wh * 0.5, 0.13, d - 0.26, wh, mi=0)
    p.boxc(w * 0.5 - 0.065, 0.0, floor_z + wh * 0.5, 0.13, d - 0.26, wh, mi=0)

    dx = -w * 0.20
    yf = -d * 0.5
    p.boxc(dx, yf - 0.05, floor_z + 0.98, 0.85, 0.06, 1.96, mi=1)     # pintu
    p.boxc(dx, yf - 0.09, floor_z + 1.02, 1.06, 0.09, 2.10, mi=1)     # kusen
    for wx in (w * 0.24,):
        p.boxc(wx, yf - 0.035, floor_z + 1.48, 0.86, 0.05, 0.78, mi=3)
        p.boxc(wx, yf - 0.05, floor_z + 1.90, 0.98, 0.09, 0.10, mi=1)
        p.boxc(wx, yf - 0.05, floor_z + 1.06, 0.98, 0.09, 0.10, mi=1)
    sx = w * 0.5
    p.boxc(sx + 0.035, 0.30, floor_z + 1.48, 0.05, 0.86, 0.78, mi=3)
    p.boxc(sx + 0.05, 0.30, floor_z + 1.90, 0.09, 0.98, 0.10, mi=1)
    p.boxc(sx + 0.05, 0.30, floor_z + 1.06, 0.09, 0.98, 0.10, mi=1)

    vd = 1.20                                                          # teras
    p.box(0.0 - w * 0.5 * 0.96, w * 0.5 * 0.96, yf - vd, yf,
          floor_z - 0.06, floor_z, mi=1)
    for px in (-w * 0.42, w * 0.42):
        p.boxc(px, yf - vd + 0.12, (floor_z + eave) * 0.5, 0.10, 0.10,
               eave - floor_z, mi=1)
    p.box(w * -0.45, w * 0.45, yf - vd + 0.08, yf - vd + 0.15,
          floor_z + 0.82, floor_z + 0.88, mi=1)

    x0, x1 = -w * 0.5 - 0.30, w * 0.5 + 0.30                       # atap
    ey = d * 0.5 + 0.55
    p.face([(x0, -ey, eave), (x1, -ey, eave), (x1, 0.0, ridge),
            (x0, 0.0, ridge)], mi=2)
    p.face([(x1, ey, eave), (x0, ey, eave), (x0, 0.0, ridge),
            (x1, 0.0, ridge)], mi=2)
    p.boxc(0.0, 0.0, ridge + 0.04, 2 * x1, 0.22, 0.11, mi=2)
    gx = w * 0.5 + 0.28
    p.face([(-gx, -d * 0.5, eave - 0.04), (-gx, 0.0, ridge),
            (-gx, d * 0.5, eave - 0.04)], mi=2)
    p.face([(gx, -d * 0.5, eave - 0.04), (gx, d * 0.5, eave - 0.04),
            (gx, 0.0, ridge)], mi=2)

    ob = p.finish(bevel=0.004)
    ob.location = (cx, cy, gz)
    ob.rotation_euler = (0.0, 0.0, yaw)
    ob.parent = ctl
    return ob


spots = [(x, ROW_A_Y) for x in ROW_A_X] + [(x, ROW_B_Y) for x in ROW_B_X]
new_houses = []
idx = 13
for (hx, hy) in spots[:SMALL_HOUSES]:
    hit = ground_at(hx, hy)
    if hit is None:
        print("WARN rumah kecil tidak dapat tanah di", hx, hy)
        continue
    p, nrm, _mi = hit
    if nrm.z < 0.90:
        print("WARN rumah kecil di lereng", hx, hy, round(nrm.z, 2))
    name = "ENV_detail_houses_%02d" % idx
    ob = build_small_house(name, hx, hy, p.z, yaw=rng.uniform(-0.05, 0.05))
    new_houses.append(ob)
    house_pads.append((hx - 2.7, hy - 2.2, hx + 2.7, hy + 2.2))
    idx += 1

n_house = len([o for o in bpy.data.objects if o.name.startswith("ENV_detail_houses")])
print("rumah kecil baru:", len(new_houses), "| total rumah kampung:", n_house)
log("MODEL - kampung: 12 -> %d rumah (18 rumah kecil baru di y %.0f/%.0f)"
    % (n_house, ROW_A_Y, ROW_B_Y))
if n_house != 30:
    log("BLOCKED - rumah kampung %d, target 30" % n_house)

# ================================================== 2. jalan tanah utama
def catmull(points, per_seg=10):
    P = [points[0]] + list(points) + [points[-1]]
    out = []
    for i in range(len(P) - 3):
        p0, p1, p2, p3 = P[i], P[i + 1], P[i + 2], P[i + 3]
        last = i >= len(P) - 4
        n = per_seg + (1 if last else 0)
        for s in range(n):
            t = s / per_seg
            t2, t3 = t * t, t * t * t
            x = 0.5 * (2 * p1[0] + (-p0[0] + p2[0]) * t
                       + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2
                       + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3)
            y = 0.5 * (2 * p1[1] + (-p0[1] + p2[1]) * t
                       + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2
                       + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3)
            out.append((x, y))
    return out


road_centre = catmull(ROAD_PTS, per_seg=10)
# buang titik yang berdekatan (sisa sambungan segmen)
clean = [road_centre[0]]
for pt in road_centre[1:]:
    if math.hypot(pt[0] - clean[-1][0], pt[1] - clean[-1][1]) > 0.35:
        clean.append(pt)
road_centre = clean

road_bm = bmesh.new()
prev = None
road_len = 0.0
z_last = 0.30
bad = 0
for i, (x, y) in enumerate(road_centre):
    if i < len(road_centre) - 1:
        dx = road_centre[i + 1][0] - x
        dy = road_centre[i + 1][1] - y
    else:
        dx = x - road_centre[i - 1][0]
        dy = y - road_centre[i - 1][1]
    ln = math.hypot(dx, dy) or 1.0
    nx, ny = -dy / ln, dx / ln
    hit = ground_at(x, y)
    if hit is None:
        z = z_last
        bad += 1
    else:
        z = hit[0].z + 0.08
        z_last = z
    hw = ROAD_W * 0.5
    a = road_bm.verts.new((x + nx * hw, y + ny * hw, z))
    b = road_bm.verts.new((x - nx * hw, y - ny * hw, z))
    if prev is not None:
        try:
            f = road_bm.faces.new((prev[0], prev[1], b, a))
            f.material_index = 0
        except ValueError:
            pass
        road_len += ln
    prev = (a, b)

road_me = bpy.data.meshes.new("ENV_detail_road")
road_bm.to_mesh(road_me)
road_bm.free()
road_me.materials.append(MAT_ROAD)
for p in road_me.polygons:
    p.use_smooth = False
road = bpy.data.objects.new("ENV_detail_road", road_me)
root.objects.link(road)
road.parent = ctl

# cek jalan tidak menembus rumah
hits = 0
for i in range(0, len(road_centre), 3):
    x, y = road_centre[i]
    for x0, y0, x1, y1 in house_pads:
        if x0 <= x <= x1 and y0 <= y <= y1:
            hits += 1
            break
print("jalan: %.1f m, %d segmen, lebar %.2f m, %d titik tanpa tanah, %d titik di pad rumah"
      % (road_len, len(road_centre) - 1, ROAD_W, bad, hits))
log("MODEL - jalan tanah utama: %.0f m, lebar %.2f m, %d segmen, menyambung dermaga "
    "ke 3 deret rumah" % (road_len, ROAD_W, len(road_centre) - 1))

# ================================================== 3. pohon pesisir 3 sektor
old_coast = [o for o in bpy.data.objects if o.name.startswith("ENV_detail_palm-coast")]
for o in old_coast:
    bpy.data.objects.remove(o, do_unlink=True)
print("pohon pesisir v004 dihapus:", len(old_coast))

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
    raise RuntimeError("mesh ENV_veg_palm-coastal tidak ada")

# medan jarak ke garis pantai (chamfer 2 lintasan, kisi 3 m)
COAST_STEP = 3.0
COAST_X0, COAST_X1 = -340.0, 445.0
COAST_Y0, COAST_Y1 = -70.0, 145.0
COAST_W = int((COAST_X1 - COAST_X0) / COAST_STEP) + 1
COAST_H = int((COAST_Y1 - COAST_Y0) / COAST_STEP) + 1
INF = 1e9
_dm = []
for _i in range(COAST_W):
    _x = COAST_X0 + _i * COAST_STEP
    _dm.append([INF if ray_obj(island, _x, COAST_Y0 + _j * COAST_STEP,
                               ztop=800.0, dist=2000.0) else 0.0
                for _j in range(COAST_H)])
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


def plan_clusters(total, lo, hi):
    sizes = []
    rem = total
    guard = 0
    while rem > hi and guard < 200:
        guard += 1
        n = rng.randint(lo, hi)
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
    return sizes


placed = 0
tree_pos = []
sector_counts = {}
sector_clusters = {}
scales, dists = [], []
for sname, sx0, sx1, quota in SECTORS:
    sizes = plan_clusters(quota, CLUSTER_MIN, CLUSTER_MAX)
    centres = []
    n_sec = 0
    for want in sizes:
        tries = 0
        clu = None
        while clu is None and tries < 3000:
            tries += 1
            cx = rng.uniform(sx0 + 4.0, sx1 - 4.0)
            cy = rng.uniform(COAST_Y0 + 5.0, COAST_Y1 - 5.0)
            if any((cx - a) ** 2 + (cy - b) ** 2 < CLUSTER_GAP ** 2
                   for a, b in centres):
                continue
            cd = coast_dist(cx, cy)
            if cd is None or not (COAST_D0 + 1.5 <= cd <= COAST_D1 - 1.5):
                continue
            if blocked(cx, cy, margin=10.0):
                continue
            if any(x0 - 2.0 <= cx <= x1 + 2.0 and y0 - 2.0 <= cy <= y1 + 2.0
                   for x0, y0, x1, y1 in house_pads):
                continue
            clu = (cx, cy)
        if clu is None:
            print("WARN klaster gagal di sektor", sname)
            continue
        centres.append(clu)
        added = 0
        for _k in range(want * 25):
            if added >= want or placed >= COASTAL_COUNT:
                break
            ang = rng.uniform(0.0, math.tau)
            rad = rng.uniform(1.8, 9.0) * math.sqrt(rng.random() + 1e-6)
            x, y = clu[0] + math.cos(ang) * rad, clu[1] + math.sin(ang) * rad
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
            d2 = coast_dist(x, y)
            if d2 is None or not (COAST_D0 <= d2 <= COAST_D1):
                continue
            if any((x - px) ** 2 + (y - py) ** 2 < TREE_GAP ** 2
                   for px, py in tree_pos):
                continue
            scale = rng.uniform(SCALE_MIN, SCALE_MAX)
            inst = bpy.data.objects.new("ENV_detail_palm-coast_%03d" % placed,
                                        coast_me)
            root.objects.link(inst)
            inst.location = (x, y, p.z - 0.05)
            inst.rotation_euler = (rng.uniform(-0.05, 0.05),
                                   rng.uniform(-0.05, 0.05),
                                   rng.uniform(0.0, math.tau))
            inst.scale = (scale, scale, scale)
            inst.parent = ctl
            tree_pos.append((x, y))
            scales.append(scale)
            dists.append(d2)
            placed += 1
            added += 1
            n_sec += 1
    sector_counts[sname] = n_sec
    sector_clusters[sname] = len(centres)
    print("sektor %-7s %3d pohon, %d klaster (target %d)"
          % (sname, n_sec, len(centres), quota))

# --- isi kekurangan: sebar pohon susulan di sektor yang belum penuh ---------
fill_tries = 0
while placed < COASTAL_COUNT and fill_tries < 60000:
    fill_tries += 1
    deficit = [max(0, q - sector_counts.get(n, 0)) for n, _, _, q in SECTORS]
    total_def = sum(deficit)
    if total_def <= 0:
        break
    r = rng.uniform(0.0, total_def)
    pick = 0
    for i, d in enumerate(deficit):
        if r <= d:
            pick = i
            break
        r -= d
    sname, sx0, sx1, quota = SECTORS[pick]
    x = rng.uniform(sx0 + 4.0, sx1 - 4.0)
    y = rng.uniform(COAST_Y0 + 3.0, COAST_Y1 - 3.0)
    cd = coast_dist(x, y)
    if cd is None or not (6.0 <= cd <= 26.0):
        continue
    if blocked(x, y, margin=4.0):
        continue
    if any(x0 <= x <= x1 and y0 <= y <= y1 for x0, y0, x1, y1 in house_pads):
        continue
    hit = ground_at(x, y)
    if hit is None:
        continue
    p, nrm, _mi = hit
    if p.z < 0.10 or p.z > 26.0 or nrm.z < 0.28:
        continue
    if any((x - px) ** 2 + (y - py) ** 2 < (TREE_GAP * 0.78) ** 2
           for px, py in tree_pos):
        continue
    scale = rng.uniform(SCALE_MIN, SCALE_MAX)
    inst = bpy.data.objects.new("ENV_detail_palm-coast_%03d" % placed, coast_me)
    root.objects.link(inst)
    inst.location = (x, y, p.z - 0.05)
    inst.rotation_euler = (rng.uniform(-0.05, 0.05), rng.uniform(-0.05, 0.05),
                           rng.uniform(0.0, math.tau))
    inst.scale = (scale, scale, scale)
    inst.parent = ctl
    tree_pos.append((x, y))
    scales.append(scale)
    dists.append(cd)
    placed += 1
    sector_counts[sname] += 1

print("pohon pesisir v005:", placed, "| skala %.2f-%.2f | pantai %.1f-%.1f m"
      % (min(scales), max(scales), min(dists), max(dists)))
log("MODEL - pohon pesisir: %d pohon di 3 sektor (%s; klaster %s), skala %.2f-%.2f, "
    "jarak pantai %.1f-%.1f m"
    % (placed, ", ".join("%s %d" % (k, v) for k, v in sector_counts.items()),
       ", ".join("%s %d" % (k, v) for k, v in sector_clusters.items()),
       min(scales), max(scales), min(dists), max(dists)))
if placed != COASTAL_COUNT:
    log("BLOCKED - pohon pesisir %d dari %d" % (placed, COASTAL_COUNT))

# ------------------------------------------------- 6 kelapa di sekitar rumah
house_palm = 0
done_house = []
for ob in sorted(new_houses, key=lambda o: o.location.x):
    if house_palm >= HOUSE_PALMS:
        break
    for attempt in range(60):
        ang = rng.uniform(0.0, math.tau)
        rad = rng.uniform(3.6, 5.6)
        x = ob.location.x + math.cos(ang) * rad
        y = ob.location.y + math.sin(ang) * rad
        hit = ground_at(x, y)
        if hit is None:
            continue
        p, nrm, _mi = hit
        if p.z < 0.10 or nrm.z < 0.85:
            continue
        if any(x0 - 0.6 <= x <= x1 + 0.6 and y0 - 0.6 <= y <= y1 + 0.6
               for x0, y0, x1, y1 in house_pads):
            continue
        if any((x - px) ** 2 + (y - py) ** 2 < (TREE_GAP * 0.8) ** 2
               for px, py in tree_pos):
            continue
        d_road = min(math.hypot(x - rx, y - ry) for rx, ry in road_centre[::2])
        if d_road < ROAD_W * 0.5 + 1.0:
            continue
        scale = rng.uniform(1.45, 1.80)
        inst = bpy.data.objects.new("ENV_detail_palm-house_%02d" % house_palm,
                                    coast_me)
        root.objects.link(inst)
        inst.location = (x, y, p.z - 0.05)
        inst.rotation_euler = (rng.uniform(-0.04, 0.04), rng.uniform(-0.04, 0.04),
                               rng.uniform(0.0, math.tau))
        inst.scale = (scale, scale, scale)
        inst.parent = ctl
        tree_pos.append((x, y))
        house_palm += 1
        done_house.append(ob.name)
        break
print("kelapa dekat rumah:", house_palm, "di", done_house)
log("MODEL - kelapa dekat rumah: %d pohon (total kelapa %.0f)"
    % (house_palm, 220 + house_palm + 200))

# ==================================================== 4. Manado Tua: variasi
MAT_COVER = bpy.data.materials.get("MAT_detail_veg-cover")
MAT_COVER_D = bpy.data.materials.get("MAT_detail_veg-cover-dark")
if MAT_COVER is None or MAT_COVER_D is None:
    raise RuntimeError("material tutupan vegetasi tidak ada")
MAT_COVER_L = get_or_make("MAT_detail_veg-cover-light", "#4E9E7A", rough=0.95)
MAT_COVER_M = get_or_make("MAT_detail_veg-cover-mid", "#367A5F", rough=0.95)

old_veg = bpy.data.objects.get("ENV_detail_manado-tua_veg")
OLD_VEG_MESH = old_veg.data if old_veg is not None else None
if old_veg is not None:
    bpy.data.objects.remove(old_veg, do_unlink=True)
if OLD_VEG_MESH is not None and OLD_VEG_MESH.users == 0:
    bpy.data.meshes.remove(OLD_VEG_MESH)

MANADO_LOC = manado.location.copy()
vmax = max(manado.data.vertices, key=lambda v: v.co.z)
peak_local = Vector((vmax.co.x, vmax.co.y, 0.0))

bm = bmesh.new()
placed_v = 0
ridge_cards = 0
tries = 0
mi_count = [0, 0, 0, 0]
mx0, mx1 = MANADO_LOC.x - 1790.0, MANADO_LOC.x + 1790.0
my0, my1 = MANADO_LOC.y - 1650.0, MANADO_LOC.y + 1660.0
random.seed(SEED + 7)
while placed_v < MANADO_VEG and tries < 90000:
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
    ang = math.atan2(ly - peak_local.y, lx - peak_local.x)
    ridge = math.cos(ang * 14.0 + 0.6) * 0.62 + math.cos(ang * 7.0 - 1.1) * 0.38
    if ridge > RIDGE_LOW:
        ridge_cards += 1
    elif random.random() > 0.42:
        continue
    if p.z > 520.0 and random.random() > 0.55:
        continue
    w = random.uniform(16.0, 30.0) * (1.0 + 0.25 * max(0.0, ridge))
    hh = random.uniform(12.0, 24.0)
    yaw = random.uniform(0.0, math.tau)
    # tone: punggung ridge & ketinggian -> lebih terang, lembah -> lebih gelap
    t = 0.55 * max(0.0, min(1.0, (ridge + 1.0) * 0.5)) + 0.45 * min(1.0, p.z / 640.0)
    r = random.random()
    if r < 0.16 + 0.34 * t:
        mi = 2                        # terang
    elif r < 0.16 + 0.34 * t + 0.30 * (1.0 - t):
        mi = 1                        # gelap
    elif r < 0.80:
        mi = 0                        # dasar
    else:
        mi = 3                        # sedang
    mi_count[mi] += 1
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
for m in (MAT_COVER, MAT_COVER_D, MAT_COVER_L, MAT_COVER_M):
    veg_me.materials.append(m)
veg_ob = bpy.data.objects.new("ENV_detail_manado-tua_veg", veg_me)
root.objects.link(veg_ob)
veg_ob.parent = ctl
print("manado veg v005:", placed_v, "kartu,", ridge_cards, "di punggung ridge, tone",
      mi_count)
log("MODEL - Manado Tua vegetasi: 1.800 -> %d kartu (%d di punggung ridge), "
    "4 tone hijau %s" % (placed_v, ridge_cards, mi_count))

# -------------------------------------------- material lereng: gradien hijau
def slope_gradient_material(mat):
    nt = mat.node_tree
    nt.nodes.clear()
    nodes, links = nt.nodes, nt.links
    out = nodes.new("ShaderNodeOutputMaterial")
    out.location = (600, 0)
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (300, 0)
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    set_input(bsdf, "Roughness", 0.92)

    coord = nodes.new("ShaderNodeTexCoord")
    coord.location = (-900, 0)
    sep = nodes.new("ShaderNodeSeparateXYZ")
    sep.location = (-700, 100)
    links.new(coord.outputs["Generated"], sep.inputs["Vector"])

    n1 = nodes.new("ShaderNodeTexNoise")
    n1.location = (-700, -120)
    set_input(n1, "Scale", 0.006)
    set_input(n1, "Detail", 6.0)
    links.new(coord.outputs["Object"], n1.inputs["Vector"])
    n2 = nodes.new("ShaderNodeTexNoise")
    n2.location = (-700, -320)
    set_input(n2, "Scale", 0.05)
    set_input(n2, "Detail", 3.0)
    links.new(coord.outputs["Object"], n2.inputs["Vector"])

    def mul(a, b, loc):
        m = nodes.new("ShaderNodeMath")
        m.operation = "MULTIPLY"
        m.location = loc
        links.new(a, m.inputs[0])
        m.inputs[1].default_value = b
        return m.outputs[0]

    def add(a, b, loc):
        m = nodes.new("ShaderNodeMath")
        m.operation = "ADD"
        m.location = loc
        links.new(a, m.inputs[0])
        links.new(b, m.inputs[1])
        return m.outputs[0]

    h = mul(sep.outputs["Z"], 0.58, (-500, 120))
    a1 = mul(n1.outputs["Fac"], 0.28, (-500, -100))
    a2 = mul(n2.outputs["Fac"], 0.14, (-500, -300))
    fac = add(add(h, a1, (-300, 0), ), a2, (-120, 0))
    mr = nodes.new("ShaderNodeMapRange")
    mr.location = (60, 0)
    mr.clamp = True
    set_input(mr, "From Min", 0.0)
    set_input(mr, "From Max", 1.0)
    links.new(fac, mr.inputs["Value"])
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.location = (150, 120)
    cr = ramp.color_ramp
    cr.elements[0].position = 0.0
    cr.elements[0].color = (*srgb("#24523F"), 1.0)
    cr.elements[1].position = 1.0
    cr.elements[1].color = (*srgb("#58A683"), 1.0)
    mid = cr.elements.new(0.34)
    mid.color = (*srgb("#2D664F"), 1.0)
    mid2 = cr.elements.new(0.66)
    mid2.color = (*srgb("#3E8E6E"), 1.0)
    links.new(mr.outputs["Result"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])


MAT_MAN = bpy.data.materials.get("MAT_detail_manado-vegetation")
if MAT_MAN is None:
    raise RuntimeError("MAT_detail_manado-vegetation tidak ada")
slope_gradient_material(MAT_MAN)
print("material lereng Manado Tua: gradien 4 hijau + 2 noise (bukan warna datar)")
log("MODEL - Manado Tua material lereng: gradien hijau gelap(#24523F) -> terang"
    "(#58A683) + noise, menggantikan warna datar")

# ================================================================== kamera
cam_aerial = bpy.data.objects.get("CAM_detail_aerial")
if cam_aerial is None:
    cam_aerial = add_camera("CAM_detail_aerial", (170.0, -230.0, 120.0),
                            (-180.0, 130.0, 25.0), 24.0)
else:
    cam_aerial.location = (170.0, -230.0, 120.0)
    cam_aerial.data.lens = 24.0
    cam_aerial.rotation_euler = ((Vector((-180.0, 130.0, 25.0))
                                 - Vector((170.0, -230.0, 120.0)))
                                 .to_track_quat("-Z", "Y").to_euler())

cam_80 = bpy.data.objects.get("CAM_detail_aerial_080")
loc80 = (118.0, -186.0, 80.0)
tgt80 = (-6.0, 42.0, 8.0)
if cam_80 is None:
    cam_80 = add_camera("CAM_detail_aerial_080", loc80, tgt80, 24.0)
else:
    cam_80.location = loc80
    cam_80.data.lens = 24.0
    cam_80.rotation_euler = (Vector(tgt80) - Vector(loc80)).to_track_quat(
        "-Z", "Y").to_euler()

cam_village = bpy.data.objects.get("CAM_detail_village")
if cam_village is None:
    cam_village = add_camera("CAM_detail_village", (95.0, -150.0, 68.0),
                             (-4.0, 26.0, 4.0), 45.0)
print("kamera aerial: z %.0f m dan z %.0f m, lens %.0f mm"
      % (cam_aerial.location.z, cam_80.location.z, cam_aerial.data.lens))

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
print("engine:", scn.render.engine, "| fps", scn.render.fps,
      "| res", scn.render.resolution_x, scn.render.resolution_y,
      "| view", scn.view_settings.view_transform, "| frame", scn.frame_current)

temp_lights = [add_sun("LGT_tmp-key", (-0.30, 0.78, -0.55), 3.4, 0.05),
               add_sun("LGT_tmp-fill", (0.62, 0.55, -0.30), 1.1, 0.4)]


def render(path, cam, pct=50):
    scn.camera = cam
    scn.render.resolution_percentage = pct
    scn.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("RENDER", path, os.path.exists(path))


p1 = os.path.join(STILLS, "island-detail-v005_aerial-120.png")
p2 = os.path.join(STILLS, "island-detail-v005_aerial-080.png")
p3 = os.path.join(STILLS, "island-detail-v005_kampung.png")
render(p1, cam_aerial)
render(p2, cam_80)
render(p3, cam_village)
for lt in temp_lights:
    bpy.data.objects.remove(lt, do_unlink=True)
log("VERIFY - render 50%%: aerial 24 mm z 120 m (%s) dan z 80 m (%s) + kamera kampung"
    % (os.path.basename(p1), os.path.basename(p2)))

# ----------------------------------------------------------------- simpan
scn.camera = cam_aerial
scn.render.resolution_percentage = 100
scn.render.filepath = "//"
for img in list(bpy.data.images):
    if img.type == "RENDER_RESULT":
        try:
            bpy.data.images.remove(img)
        except Exception:
            pass
for lib in list(bpy.data.libraries):
    try:
        bpy.data.libraries.remove(lib)
    except Exception as err:
        print("PERINGATAN library masih dipakai:", lib.filepath, err)
bpy.ops.wm.save_as_mainfile(filepath=OUT)
size_mb = round(os.path.getsize(OUT) / 1048576.0, 2)

n_coast = len([o for o in bpy.data.objects
               if o.name.startswith("ENV_detail_palm-coast")])
n_house_palm = len([o for o in bpy.data.objects
                    if o.name.startswith("ENV_detail_palm-house")])
n_extra = len([o for o in bpy.data.objects
               if o.name.startswith("ENV_detail_palm-extra")])
print("=== RINGKASAN island-detail_v005 ===")
print("kelapa: pesisir", n_coast, "+ dekat rumah", n_house_palm,
      "+ sebaran", n_extra, "= total", n_coast + n_house_palm + n_extra)
print("rumah", n_house, "| jalan", round(road_len, 1), "m,", len(road_centre) - 1,
      "segmen | objek", len(bpy.data.objects))
print("manado veg", placed_v, "kartu, tone", mi_count,
      "| puncak", round(max(v.co.z for v in manado.data.vertices), 1), "m")
print("images (harus 0)", [i.name for i in bpy.data.images])
print("libraries (harus 0)", [l.filepath for l in bpy.data.libraries])
print("lights (harus 0)", [o.name for o in bpy.data.objects if o.type == "LIGHT"])
print("engine", scn.render.engine, "vt", scn.view_settings.view_transform,
      "res", scn.render.resolution_x, scn.render.resolution_y,
      "fps", scn.render.fps, "frame", scn.frame_current)
log("MODEL - island-detail_v005.blend disimpan (%.2f MB, %d rumah, jalan %.0f m, "
    "%d kelapa pesisir + %d dekat rumah, Manado Tua %d kartu)"
    % (size_mb, n_house, road_len, n_coast, n_house_palm, placed_v))
print("SELESAI", OUT, size_mb, "MB")

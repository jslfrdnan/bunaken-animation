"""
Bangun ulang tiga ikan Scene 1 — bentuk + rig 10 bone + action renang 32 frame.

Keluaran (dipanggil satu spesies per proses):
    assets/env/fish-kakatua_v004.blend
    assets/env/fish-damselfish_v004.blend
    assets/env/fish-cakalang-rig_v004.blend

    blender -b -P scripts/build-fish-v004.py -- --species kakatua
    blender -b -P scripts/build-fish-v004.py -- --species damselfish
    blender -b -P scripts/build-fish-v004.py -- --species cakalang

Perbaikan v004 (27 Nov 2026):
  1. Bentuk kakatua & damselfish dibangun ulang dari foto acuan: profil badan
     ber-station (dahi/paruh, punggung, batang ekor sempit), sirip menempel ke
     badan (pangkal masuk ke dalam badan), ekor bercabang, sirip dada kipas.
     Cakalang: bentuk dipertahankan, sirip punggung dirapikan (satu puncak,
     simetris, leading edge menyapu ke belakang).
  2. Orientasi tegas: moncong di -Y (maju = -Y), punggung di +Z (atas = +Z),
     objek tanpa rotasi/skala. Tidak ada cermin.
  3. Rig 10 bone: root (non-deform) + 9 deform
     (spine_01..03, tail_01..02, dorsal, jaw, pelvic_L/R).
     Automatic weights, lalu semua verteks tanpa bobot diisi; sirip punggung,
     rahang, pelvic, dada diberi bobot gradien supaya tidak kaku.
  4. Action renang 32 frame: spine_01/02/03 3/5/7 derajat fase berurutan,
     tail_01/02 10/16 derajat fase tertinggal, dorsal/jaw/pelvic halus.
     Empat varian fase (offset 0/8/16/24 frame): _p1.._p4.

Skrip idempoten: mengosongkan datablock lalu membangun ulang dari tabel.
Tidak memakai open_mainfile / read_factory_settings / read_homefile.
Tanpa tekstur, tanpa pack. EEVEE, 1920x1080, 24 fps, Standard, frame 1.
"""

import bpy
import bmesh
import os
import sys
import time
import math
from math import cos, sin, pi, copysign, radians, degrees, atan2
from mathutils import Vector, Quaternion

try:
    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
except NameError:
    ROOT = r"D:\Tugas Semester 5\Grafika Komputer\Project-Animasi"

LOG = os.path.join(ROOT, "renders", "logs", "modeling.log")
STILLS = os.path.join(ROOT, "renders", "stills")
TMP = os.path.join(ROOT, "renders", "tmp", "_wipe.blend")
ENV = os.path.join(ROOT, "assets", "env")

# palette PROJECT.md §2 + netral 14 Nov 2026
HEX_GREEN = "#3E8E6E"
HEX_TEAL = "#1FA3A3"
HEX_DEEP = "#0F5C63"
HEX_ORANGE = "#E4713C"
HEX_SAND = "#E8D5B0"
HEX_CREAM = "#F2E9DC"
HEX_EYE = "#2E383A"
HEX_GROUND = "#2E383A"

N_FRAMES = 32

CHAIN = ["spine_01", "spine_02", "spine_03", "tail_01", "tail_02"]
DEFORM = CHAIN + ["dorsal", "jaw", "pelvic_L", "pelvic_R"]

# (bone, amplitudo derajat, sumbu dunia, fase derajat)
# fase negatif = tertinggal (gelombang menjalar kepala -> ekor)
SWIM = [
    ("spine_01", 3.0, "Z", 0.0),
    ("spine_02", 5.0, "Z", -40.0),
    ("spine_03", 7.0, "Z", -80.0),
    ("tail_01", 10.0, "Z", -120.0),
    ("tail_02", 16.0, "Z", -160.0),
    ("dorsal", 2.2, "X", -60.0),
    ("jaw", 1.6, "X", -20.0),
    ("pelvic_L", 4.0, "X", -100.0),
    ("pelvic_R", 4.0, "X", -100.0),
]
PHASE_VARIANTS = [0, 8, 16, 24]


# ---------------------------------------------------------------------------
# log & utilitas umum
# ---------------------------------------------------------------------------


def log(msg):
    stamp = time.strftime("%H:%M")
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as fh:
            fh.write("[%s] %s\n" % (stamp, msg))
    except Exception as err:  # pragma: no cover
        print("PERINGATAN log:", err)
    print("[%s] %s" % (stamp, msg))


def srgb(hexstr):
    h = hexstr.lstrip("#")
    values = [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]

    def to_linear(u):
        return u / 12.92 if u <= 0.04045 else ((u + 0.055) / 1.055) ** 2.4

    return tuple(to_linear(v) for v in values) + (1.0,)


def material(name, hexcol, roughness=0.6, metallic=0.0, spec=0.5):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.use_backface_culling = False
    col = srgb(hexcol)
    mat.diffuse_color = col
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = col
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    spec_in = bsdf.inputs.get("Specular IOR Level") or bsdf.inputs.get("Specular")
    if spec_in is not None:
        spec_in.default_value = spec
    mat["source_hex"] = hexcol
    return mat


def superellipse(rx, ry, t, exp):
    ct, st = cos(t), sin(t)
    x = rx * copysign(abs(ct) ** (2.0 / exp), ct)
    y = ry * copysign(abs(st) ** (2.0 / exp), st)
    return x, y


def profile_at(table, y):
    if y <= table[0][0]:
        return table[0][1], table[0][2], table[0][3]
    if y >= table[-1][0]:
        return table[-1][1], table[-1][2], table[-1][3]
    for k in range(len(table) - 1):
        y0, rx0, rz0, cz0 = table[k]
        y1, rx1, rz1, cz1 = table[k + 1]
        if y0 <= y <= y1:
            t = (y - y0) / (y1 - y0)
            return (rx0 + (rx1 - rx0) * t,
                    rz0 + (rz1 - rz0) * t,
                    cz0 + (cz1 - cz0) * t)
    return table[-1][1], table[-1][2], table[-1][3]


def new_mesh_object(name, V, F, FM, FS, mats, collection):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(V, [], F)
    for m in mats:
        mesh.materials.append(m)
    for poly, mat_index, smooth in zip(mesh.polygons, FM, FS):
        poly.material_index = mat_index
        poly.use_smooth = smooth
    mesh.validate(verbose=False)
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    return obj


def loft_rings(rings, mats, V, F, FM, FS, smooth=True, cap_a=True, cap_b=True):
    starts = []
    for r in rings:
        starts.append(len(V))
        for p in r:
            V.append(Vector(p))
    n = len(rings[0])
    for k in range(len(rings) - 1):
        a, b = starts[k], starts[k + 1]
        m = mats[min(k, len(mats) - 1)]
        for i in range(n):
            i2 = (i + 1) % n
            F.append((a + i, a + i2, b + i2, b + i))
            FM.append(m)
            FS.append(smooth)
    if cap_a:
        F.append(tuple(starts[0] + i for i in range(n - 1, -1, -1)))
        FM.append(mats[0])
        FS.append(False)
    if cap_b:
        F.append(tuple(starts[-1] + i for i in range(n)))
        FM.append(mats[min(len(mats) - 1, len(rings) - 2)])
        FS.append(False)


def plate(stations, thickness, axis, mats, V, F, FM, FS, smooth=False):
    """Pelat sirip: stations = [(titik_A, titik_B)]; tebal ke arah `axis`."""
    n = Vector(axis).normalized() * (thickness * 0.5)
    rings = []
    for low, high in stations:
        low = Vector(low)
        high = Vector(high)
        rings.append([low - n, high - n, high + n, low + n])
    loft_rings(rings, mats, V, F, FM, FS, smooth=smooth)


def slab(outline, thickness, axis, mat, V, F, FM, FS, smooth=False):
    """Poligon planar + ketebalan (dipakai untuk segitiga finlet/ekor)."""
    n = Vector(axis).normalized() * (thickness * 0.5)
    base = len(V)
    for p in outline:
        V.append(Vector(p) - n)
    for p in outline:
        V.append(Vector(p) + n)
    m = len(outline)
    F.append(tuple(base + i for i in range(m - 1, -1, -1)))
    FM.append(mat)
    FS.append(False)
    F.append(tuple(base + m + i for i in range(m)))
    FM.append(mat)
    FS.append(False)
    for i in range(m):
        i2 = (i + 1) % m
        F.append((base + i, base + i2, base + m + i2, base + m + i))
        FM.append(mat)
        FS.append(smooth)


def ellipsoid(center, radii, mat, V, F, FM, FS, seg=12, rings_n=6):
    cx, cy, cz = center
    rx, ry, rz = radii
    top = len(V)
    V.append(Vector((cx, cy, cz + rz)))
    ring_starts = []
    for ir in range(1, rings_n):
        th = pi * ir / rings_n
        s, c = sin(th), cos(th)
        st = len(V)
        for i in range(seg):
            ph = 2.0 * pi * i / seg
            V.append(Vector((cx + rx * s * cos(ph), cy + ry * s * sin(ph),
                             cz + rz * c)))
        ring_starts.append(st)
    bot = len(V)
    V.append(Vector((cx, cy, cz - rz)))
    first = ring_starts[0]
    for i in range(seg):
        i2 = (i + 1) % seg
        F.append((top, first + i, first + i2))
        FM.append(mat)
        FS.append(True)
    for k in range(len(ring_starts) - 1):
        a, b = ring_starts[k], ring_starts[k + 1]
        for i in range(seg):
            i2 = (i + 1) % seg
            F.append((a + i, b + i, b + i2, a + i2))
            FM.append(mat)
            FS.append(True)
    last = ring_starts[-1]
    for i in range(seg):
        i2 = (i + 1) % seg
        F.append((bot, last + i2, last + i))
        FM.append(mat)
        FS.append(True)


def build_body_generic(table, seg, matfn, cap_a, cap_b):
    V, F, FM, FS = [], [], [], []
    starts = []
    for (y, rx, rz, cz) in table:
        starts.append(len(V))
        for i in range(seg):
            a, b = superellipse(rx, rz, 2.0 * pi * i / seg, 2.1)
            V.append(Vector((a, y, cz + b)))
    for k in range(len(starts) - 1):
        a, b = starts[k], starts[k + 1]
        for i in range(seg):
            i2 = (i + 1) % seg
            F.append((a + i, a + i2, b + i2, b + i))
            zc = (V[a + i].z + V[a + i2].z + V[b + i].z + V[b + i2].z) / 4.0
            yc = (V[a + i].y + V[a + i2].y + V[b + i].y + V[b + i2].y) / 4.0
            _, rz, cz = profile_at(table, yc)
            rel = (zc - cz) / rz if rz > 1e-9 else 0.0
            FM.append(matfn(k, i, yc, rel))
            FS.append(True)
    F.append(tuple(starts[0] + i for i in range(seg - 1, -1, -1)))
    FM.append(cap_a)
    FS.append(False)
    F.append(tuple(starts[-1] + i for i in range(seg)))
    FM.append(cap_b)
    FS.append(False)
    return V, F, FM, FS


def range_add(ranges, name, v0, vlist):
    ranges[name] = (v0, len(vlist))


# ---------------------------------------------------------------------------
# KAKATUA — parrotfish, 0,44 m
# ---------------------------------------------------------------------------

KAKATUA_BODY = [
    (-0.225, 0.009, 0.012, -0.004),
    (-0.221, 0.013, 0.020, -0.003),
    (-0.214, 0.017, 0.029, -0.002),
    (-0.204, 0.022, 0.038, -0.001),
    (-0.192, 0.027, 0.048, 0.000),
    (-0.176, 0.031, 0.058, 0.001),
    (-0.155, 0.034, 0.067, 0.002),
    (-0.128, 0.037, 0.074, 0.002),
    (-0.098, 0.039, 0.078, 0.002),
    (-0.065, 0.039, 0.079, 0.001),
    (-0.030, 0.038, 0.077, 0.000),
    (0.005, 0.036, 0.072, -0.001),
    (0.040, 0.033, 0.064, -0.002),
    (0.072, 0.029, 0.053, -0.002),
    (0.100, 0.024, 0.042, -0.001),
    (0.124, 0.019, 0.031, 0.000),
    (0.145, 0.014, 0.021, 0.001),
    (0.160, 0.011, 0.015, 0.002),
    (0.170, 0.009, 0.012, 0.002),
]


def build_kakatua(mats, col):
    S = {"green": 0, "teal": 1, "orange": 2, "cream": 3, "fin": 4, "eye": 5,
         "sand": 6}
    seg = 32

    def matfn(k, i, y, rel):
        # paruh: hanya ujung depan (krem tulang)
        if k == 0:
            return S["cream"]
        # pangkal ekor krem (ring terakhir sebelum sirip ekor)
        if k >= 17:
            return S["sand"]
        # garis pipi oranye tipis (satu baris di tengah sisi kepala)
        if 1 <= k <= 4 and i in (0, 15):
            return S["orange"]
        if rel <= -0.55:
            return S["teal"]
        return S["green"]

    table = KAKATUA_BODY
    V, F, FM, FS = build_body_generic(table, seg, matfn, S["cream"], S["green"])
    ranges = {}
    range_add(ranges, "body", 0, V)

    def body_top(y):
        _, rz, cz = profile_at(table, y)
        return cz + rz

    def body_bottom(y):
        _, rz, cz = profile_at(table, y)
        return cz - rz

    # --- mata: cincin krem tipis di belakang bola gelap
    v0 = len(V)
    for sx in (-1.0, 1.0):
        ellipsoid((sx * 0.0260, -0.172, 0.014), (0.0078, 0.0104, 0.0104),
                  S["cream"], V, F, FM, FS, seg=12, rings_n=6)
        ellipsoid((sx * 0.0268, -0.172, 0.014), (0.0074, 0.0100, 0.0100),
                  S["eye"], V, F, FM, FS, seg=12, rings_n=6)
    range_add(ranges, "body_eye", v0, V)

    # --- sirip punggung panjang: leading edge menyapu dari badan
    v0 = len(V)
    ys = [-0.110, -0.090, -0.065, -0.035, 0.000, 0.035, 0.070, 0.100, 0.125,
          0.145, 0.158]
    hs = [0.004, 0.016, 0.024, 0.028, 0.030, 0.029, 0.027, 0.024, 0.020,
          0.014, 0.007]
    stations = []
    for y, h in zip(ys, hs):
        base = body_top(y) - 0.010
        stations.append(((0.0, y, base), (0.0, y, base + h)))
    plate(stations, 0.0050, (1, 0, 0), [S["fin"]] * (len(stations) - 1),
          V, F, FM, FS)
    range_add(ranges, "dorsal", v0, V)

    # --- sirip anal panjang
    v0 = len(V)
    ys = [-0.050, -0.025, 0.005, 0.035, 0.065, 0.092, 0.118, 0.138]
    hs = [0.004, 0.014, 0.021, 0.024, 0.023, 0.019, 0.013, 0.006]
    stations = []
    for y, h in zip(ys, hs):
        base = body_bottom(y) + 0.008
        stations.append(((0.0, y, base), (0.0, y, base - h)))
    plate(stations, 0.0045, (1, 0, 0), [S["fin"]] * (len(stations) - 1),
          V, F, FM, FS)
    range_add(ranges, "anal", v0, V)

    # --- sirip perut (sepasang)
    v0 = len(V)
    for sx in (-1.0, 1.0):
        stations = [
            ((sx * 0.010, -0.086, -0.064), (sx * 0.010, -0.052, -0.064)),
            ((sx * 0.014, -0.076, -0.088), (sx * 0.014, -0.048, -0.088)),
            ((sx * 0.016, -0.066, -0.107), (sx * 0.016, -0.050, -0.107)),
        ]
        plate(stations, 0.0040, (1, 0, 0), [S["fin"]] * 2, V, F, FM, FS)
    range_add(ranges, "pelvic", v0, V)

    # --- sirip dada kipas biru: bidang hampir sagital, pangkal di dalam badan
    v0 = len(V)
    for sx in (-1.0, 1.0):
        stations = [
            ((sx * 0.030, -0.146, 0.002), (sx * 0.030, -0.120, -0.012)),
            ((sx * 0.038, -0.130, -0.012), (sx * 0.038, -0.098, -0.026)),
            ((sx * 0.046, -0.110, -0.026), (sx * 0.046, -0.080, -0.036)),
            ((sx * 0.051, -0.092, -0.034), (sx * 0.051, -0.074, -0.040)),
        ]
        plate(stations, 0.0030, (1, 0, 0), [S["fin"]] * 3, V, F, FM, FS)
    range_add(ranges, "pectoral", v0, V)

    # --- ekor bercabang: cuping menempel langsung ke batang ekor
    v0 = len(V)
    for sign in (1.0, -1.0):
        lobe = [
            ((0.0, 0.160, 0.000), (0.0, 0.160, 0.016)),
            ((0.0, 0.168, 0.001), (0.0, 0.168, 0.024)),
            ((0.0, 0.184, 0.003), (0.0, 0.184, 0.038)),
            ((0.0, 0.200, 0.008), (0.0, 0.200, 0.052)),
            ((0.0, 0.211, 0.020), (0.0, 0.211, 0.060)),
            ((0.0, 0.216, 0.032), (0.0, 0.216, 0.066)),
        ]
        if sign < 0:
            lobe = [((x, y, -hi), (x, y, -lo)) for ((x, y, lo), (x, y, hi)) in lobe]
        plate(lobe, 0.0080, (1, 0, 0),
              [S["green"], S["green"], S["green"], S["green"], S["orange"]],
              V, F, FM, FS)
    range_add(ranges, "caudal", v0, V)

    mats_list = [mats["green"], mats["teal"], mats["orange"], mats["cream"],
                 mats["fin"], mats["eye"], mats["sand"]]
    obj = new_mesh_object("ENV_fish_kakatua", V, F, FM, FS, mats_list, col)
    obj["part"] = "body+dorsal+anal+pelvic+pectoral+caudal+eye"
    return [{"obj": obj, "ranges": ranges}]


KAKATUA_BONES = [
    ("root", (0.0, 0.0, 0.0), (0.0, 0.0, 0.050), None, False),
    ("spine_01", (0.0, -0.190, 0.0), (0.0, -0.080, 0.0), "root", True),
    ("spine_02", (0.0, -0.080, 0.0), (0.0, 0.020, 0.0), "spine_01", True),
    ("spine_03", (0.0, 0.020, 0.0), (0.0, 0.108, 0.0), "spine_02", True),
    ("tail_01", (0.0, 0.108, 0.0), (0.0, 0.166, 0.0), "spine_03", True),
    ("tail_02", (0.0, 0.166, 0.0), (0.0, 0.218, 0.0), "tail_01", True),
    ("dorsal", (0.0, -0.020, 0.068), (0.0, 0.004, 0.094), "spine_02", True),
    ("jaw", (0.0, -0.198, -0.001), (0.0, -0.230, -0.011), "spine_01", True),
    ("pelvic_L", (0.012, -0.074, -0.064), (0.016, -0.060, -0.107), "spine_02", True),
    ("pelvic_R", (-0.012, -0.074, -0.064), (-0.016, -0.060, -0.107), "spine_02", True),
]


# ---------------------------------------------------------------------------
# DAMSELFISH — 0,10 m
# ---------------------------------------------------------------------------

DAMSELFISH_BODY = [
    (-0.050, 0.0022, 0.0030, -0.003),
    (-0.047, 0.0045, 0.0062, -0.002),
    (-0.043, 0.0075, 0.0112, -0.001),
    (-0.038, 0.0105, 0.0160, 0.000),
    (-0.031, 0.0130, 0.0200, 0.001),
    (-0.023, 0.0147, 0.0228, 0.002),
    (-0.014, 0.0153, 0.0240, 0.002),
    (-0.004, 0.0150, 0.0236, 0.001),
    (0.006, 0.0140, 0.0215, 0.000),
    (0.016, 0.0122, 0.0182, -0.001),
    (0.025, 0.0096, 0.0138, -0.001),
    (0.032, 0.0068, 0.0092, 0.000),
    (0.038, 0.0045, 0.0058, 0.001),
]


def build_damselfish(mats, col):
    S = {"blue": 0, "teal": 1, "sand": 2, "orange": 3, "eye": 4}
    seg = 28
    table = DAMSELFISH_BODY

    def body_top(y):
        _, rz, cz = profile_at(table, y)
        return cz + rz

    def body_bottom(y):
        _, rz, cz = profile_at(table, y)
        return cz - rz

    def matfn(k, i, y, rel):
        if rel >= 0.30:
            return S["teal"]          # highlight punggung
        return S["blue"]

    V, F, FM, FS = build_body_generic(table, seg, matfn, S["blue"], S["blue"])
    ranges = {}
    range_add(ranges, "body", 0, V)

    v0 = len(V)
    for sx in (-1.0, 1.0):
        ellipsoid((sx * 0.0103, -0.034, 0.007), (0.0042, 0.0058, 0.0058),
                  S["teal"], V, F, FM, FS, seg=12, rings_n=6)
        ellipsoid((sx * 0.0119, -0.034, 0.007), (0.0032, 0.0044, 0.0044),
                  S["eye"], V, F, FM, FS, seg=12, rings_n=6)
    range_add(ranges, "body_eye", v0, V)

    # sirip punggung tinggi
    v0 = len(V)
    ys = [-0.031, -0.022, -0.012, -0.002, 0.008, 0.018, 0.027, 0.034]
    hs = [0.004, 0.009, 0.013, 0.015, 0.014, 0.011, 0.007, 0.003]
    stations = []
    for y, h in zip(ys, hs):
        base = body_top(y) - 0.002
        stations.append(((0.0, y, base), (0.0, y, base + h)))
    plate(stations, 0.0018, (1, 0, 0), [S["blue"]] * (len(stations) - 1),
          V, F, FM, FS)
    rim = []
    for y, h in zip(ys, hs):
        base = body_top(y) - 0.002
        rim.append(((0.0, y, base + h - 0.0018), (0.0, y, base + h)))
    plate(rim, 0.0022, (1, 0, 0), [S["teal"]] * (len(rim) - 1), V, F, FM, FS)
    range_add(ranges, "dorsal", v0, V)

    # sirip anal
    v0 = len(V)
    ys = [-0.014, -0.004, 0.006, 0.016, 0.026, 0.032]
    hs = [0.004, 0.010, 0.014, 0.013, 0.009, 0.004]
    stations = []
    for y, h in zip(ys, hs):
        base = body_bottom(y) + 0.002
        stations.append(((0.0, y, base), (0.0, y, base - h)))
    plate(stations, 0.0016, (1, 0, 0), [S["blue"]] * (len(stations) - 1),
          V, F, FM, FS)
    range_add(ranges, "anal", v0, V)

    # sirip perut
    v0 = len(V)
    for sx in (-1.0, 1.0):
        stations = [
            ((sx * 0.0060, -0.026, -0.020), (sx * 0.0060, -0.016, -0.020)),
            ((sx * 0.0075, -0.023, -0.025), (sx * 0.0075, -0.014, -0.025)),
            ((sx * 0.0085, -0.020, -0.029), (sx * 0.0085, -0.013, -0.029)),
        ]
        plate(stations, 0.0012, (1, 0, 0), [S["blue"]] * 2, V, F, FM, FS)
    range_add(ranges, "pelvic", v0, V)

    # sirip dada kipas kecil
    v0 = len(V)
    for sx in (-1.0, 1.0):
        stations = [
            ((sx * 0.0100, -0.036, 0.002), (sx * 0.0100, -0.028, -0.003)),
            ((sx * 0.0165, -0.032, -0.003), (sx * 0.0165, -0.023, -0.008)),
            ((sx * 0.0225, -0.027, -0.008), (sx * 0.0225, -0.020, -0.011)),
        ]
        plate(stations, 0.0012, (1, 0, 0), [S["blue"]] * 2, V, F, FM, FS)
    range_add(ranges, "pectoral", v0, V)

    # ekor kuning-oranye (pangkal krem, ujung oranye), garpu dangkal
    v0 = len(V)
    base = [
        ((0.0, 0.031, -0.0045), (0.0, 0.032, 0.0045)),
        ((0.0, 0.035, -0.0055), (0.0, 0.036, 0.0055)),
    ]
    plate(base, 0.0032, (1, 0, 0), [S["sand"]], V, F, FM, FS)
    for sign in (1.0, -1.0):
        lobe = [
            ((0.0, 0.036, 0.000), (0.0, 0.036, 0.006)),
            ((0.0, 0.043, 0.000), (0.0, 0.043, 0.012)),
            ((0.0, 0.050, 0.000), (0.0, 0.050, 0.017)),
            ((0.0, 0.052, 0.001), (0.0, 0.052, 0.019)),
        ]
        if sign < 0:
            lobe = [((x, y, -hi), (x, y, -lo)) for ((x, y, lo), (x, y, hi)) in lobe]
        plate(lobe, 0.0026, (1, 0, 0), [S["sand"], S["sand"], S["orange"]],
              V, F, FM, FS)
    range_add(ranges, "caudal", v0, V)

    mats_list = [mats["blue"], mats["teal"], mats["sand"], mats["orange"],
                 mats["eye"]]
    obj = new_mesh_object("ENV_fish_damselfish", V, F, FM, FS, mats_list, col)
    obj["part"] = "body+dorsal+anal+pelvic+pectoral+caudal+eye"
    return [{"obj": obj, "ranges": ranges}]


DAMSELFISH_BONES = [
    ("root", (0.0, 0.0, 0.0), (0.0, 0.0, 0.012), None, False),
    ("spine_01", (0.0, -0.043, 0.0), (0.0, -0.020, 0.0), "root", True),
    ("spine_02", (0.0, -0.020, 0.0), (0.0, 0.004, 0.0), "spine_01", True),
    ("spine_03", (0.0, 0.004, 0.0), (0.0, 0.028, 0.0), "spine_02", True),
    ("tail_01", (0.0, 0.028, 0.0), (0.0, 0.040, 0.0), "spine_03", True),
    ("tail_02", (0.0, 0.040, 0.0), (0.0, 0.053, 0.0), "tail_01", True),
    ("dorsal", (0.0, -0.006, 0.022), (0.0, 0.004, 0.040), "spine_02", True),
    ("jaw", (0.0, -0.044, -0.002), (0.0, -0.053, -0.005), "spine_01", True),
    ("pelvic_L", (0.006, -0.022, -0.020), (0.008, -0.014, -0.036), "spine_02", True),
    ("pelvic_R", (-0.006, -0.022, -0.020), (-0.008, -0.014, -0.036), "spine_02", True),
]


# ---------------------------------------------------------------------------
# CAKALANG — skipjack tuna, 0,70 m (bentuk dipertahankan)
# ---------------------------------------------------------------------------

CAKALANG_BODY = [
    (-0.350, 0.007, 0.009, 0.000),
    (-0.335, 0.018, 0.028, 0.000),
    (-0.305, 0.031, 0.047, 0.002),
    (-0.265, 0.042, 0.062, 0.003),
    (-0.215, 0.050, 0.073, 0.003),
    (-0.155, 0.056, 0.080, 0.001),
    (-0.085, 0.058, 0.082, 0.000),
    (0.000, 0.055, 0.077, -0.002),
    (0.070, 0.047, 0.067, -0.002),
    (0.140, 0.037, 0.051, 0.000),
    (0.200, 0.025, 0.033, 0.004),
    (0.245, 0.016, 0.020, 0.006),
    (0.272, 0.011, 0.013, 0.008),
]


def build_cakalang(mats, col):
    S = {"back": 0, "belly": 1, "fin": 2, "eye": 3}
    seg = 28
    table = CAKALANG_BODY

    def body_top(y):
        _, rz, cz = profile_at(table, y)
        return cz + rz

    def body_bottom(y):
        _, rz, cz = profile_at(table, y)
        return cz - rz

    def matfn(k, i, y, rel):
        return S["back"] if rel > 0.03 else S["belly"]

    V, F, FM, FS = build_body_generic(table, seg, matfn, S["back"], S["back"])
    ranges = {}
    range_add(ranges, "body", 0, V)

    v0 = len(V)
    for sx in (-1.0, 1.0):
        ellipsoid((sx * 0.0326, -0.288, 0.016), (0.0072, 0.0104, 0.0104),
                  S["belly"], V, F, FM, FS, seg=14, rings_n=6)
        ellipsoid((sx * 0.0336, -0.288, 0.016), (0.0066, 0.0096, 0.0096),
                  S["eye"], V, F, FM, FS, seg=14, rings_n=6)
    range_add(ranges, "body_eye", v0, V)

    body = new_mesh_object("ENV_fish_cakalang", V, F, FM, FS,
                           [mats["back"], mats["belly"], mats["fin"],
                            mats["eye"]], col)
    body["part"] = "body+eye"

    # --- sirip punggung: satu puncak, simetris, leading edge menyapu
    V, F, FM, FS = [], [], [], []
    ys = [-0.160, -0.145, -0.128, -0.112, -0.095, -0.070, -0.040, -0.020]
    hs = [0.004, 0.060, 0.095, 0.105, 0.100, 0.075, 0.035, 0.004]
    stations = []
    for y, h in zip(ys, hs):
        base = body_top(y) - 0.008
        stations.append(((0.0, y, base), (0.0, y, base + h)))
    plate(stations, 0.010, (1, 0, 0), [S["fin"]] * (len(stations) - 1),
          V, F, FM, FS)
    # finlet punggung (7) menjelang ekor
    for i in range(7):
        y = 0.020 + i * 0.028
        h = 0.020 - i * 0.0018
        base_z = body_top(y) - 0.006
        tri = [(0.0, y, base_z),
               (0.0, y + 0.010, base_z + h),
               (0.0, y + 0.019, base_z)]
        slab(tri, 0.006, (1, 0, 0), S["fin"], V, F, FM, FS)
    dorsal = new_mesh_object("ENV_fish_cakalang_dorsal", V, F, FM, FS,
                             [mats["fin"]], col)
    dorsal["part"] = "dorsal+finlet"

    # --- ekor bercabang dalam
    V, F, FM, FS = [], [], [], []
    y_base = 0.266
    upper = [
        (0.0, y_base, 0.010),
        (0.0, 0.300, 0.048),
        (0.0, 0.340, 0.098),
        (0.0, 0.352, 0.090),
        (0.0, 0.316, 0.008),
    ]
    lower = [(x, y, -z) for (x, y, z) in upper]
    slab(upper, 0.010, (1, 0, 0), S["fin"], V, F, FM, FS)
    slab(lower, 0.010, (1, 0, 0), S["fin"], V, F, FM, FS)
    slab([(0.0, 0.258, 0.014), (0.0, 0.300, 0.010), (0.0, 0.258, -0.014)],
         0.012, (1, 0, 0), S["fin"], V, F, FM, FS)
    tail = new_mesh_object("ENV_fish_cakalang_tail", V, F, FM, FS,
                           [mats["fin"]], col)
    tail["part"] = "caudal"

    # --- dada + perut + anal + finlet anal (satu objek, sama seperti v003)
    V, F, FM, FS = [], [], [], []
    pranges = {}
    for sign, side in ((-1.0, "R"), (1.0, "L")):
        v0 = len(V)
        pect = [
            (sign * 0.045, -0.190, -0.008),
            (sign * 0.108, -0.150, -0.020),
            (sign * 0.100, -0.112, -0.026),
            (sign * 0.046, -0.132, -0.014),
        ]
        slab(pect, 0.006, (0, 0, 1), S["fin"], V, F, FM, FS)
        pranges["pectoral_" + side] = (v0, len(V))
        v0 = len(V)
        pelv = [
            (sign * 0.012, -0.070, body_bottom(-0.070) + 0.006),
            (sign * 0.028, -0.042, body_bottom(-0.042) + 0.006),
            (sign * 0.024, -0.020, -0.104),
            (sign * 0.012, -0.048, -0.098),
        ]
        slab(pelv, 0.005, (0, 0, 1), S["fin"], V, F, FM, FS)
        pranges["pelvic_" + side] = (v0, len(V))
    v0 = len(V)
    anal = [
        (0.0, 0.130, body_bottom(0.130) + 0.008),
        (0.0, 0.155, -0.062),
        (0.0, 0.196, body_bottom(0.196) + 0.006),
    ]
    slab(anal, 0.005, (1, 0, 0), S["fin"], V, F, FM, FS)
    for i in range(5):
        y = 0.190 + i * 0.016
        h = 0.016 - i * 0.0012
        base_z = body_bottom(y) + 0.004
        tri = [(0.0, y, base_z),
               (0.0, y + 0.006, base_z - h),
               (0.0, y + 0.013, base_z)]
        slab(tri, 0.004, (1, 0, 0), S["fin"], V, F, FM, FS)
    pranges["anal"] = (v0, len(V))
    pectoral = new_mesh_object("ENV_fish_cakalang_pectoral", V, F, FM, FS,
                               [mats["fin"]], col)
    pectoral["part"] = "pectoral+pelvic+anal"

    return [
        {"obj": body, "ranges": ranges},
        {"obj": dorsal, "ranges": {"dorsal": (0, len(dorsal.data.vertices))}},
        {"obj": tail, "ranges": {"caudal": (0, len(tail.data.vertices))}},
        {"obj": pectoral, "ranges": pranges},
    ]


CAKALANG_BONES = [
    ("root", (0.0, 0.0, 0.0), (0.0, 0.0, 0.050), None, False),
    ("spine_01", (0.0, -0.300, 0.0), (0.0, -0.140, 0.0), "root", True),
    ("spine_02", (0.0, -0.140, 0.0), (0.0, 0.010, 0.0), "spine_01", True),
    ("spine_03", (0.0, 0.010, 0.0), (0.0, 0.155, 0.0), "spine_02", True),
    ("tail_01", (0.0, 0.155, 0.0), (0.0, 0.270, 0.0), "spine_03", True),
    ("tail_02", (0.0, 0.270, 0.0), (0.0, 0.352, 0.0), "tail_01", True),
    ("dorsal", (0.0, -0.130, 0.066), (0.0, -0.112, 0.150), "spine_02", True),
    ("jaw", (0.0, -0.312, -0.004), (0.0, -0.356, -0.014), "spine_01", True),
    ("pelvic_L", (0.014, -0.062, -0.070), (0.020, -0.036, -0.100), "spine_02", True),
    ("pelvic_R", (-0.014, -0.062, -0.070), (-0.020, -0.036, -0.100), "spine_02", True),
]


# ---------------------------------------------------------------------------
# konfigurasi spesies
# ---------------------------------------------------------------------------

SPECIES = {
    "kakatua": {
        "scene": "fish-kakatua_v004",
        "out": "fish-kakatua_v004.blend",
        "arm": "CHR_fish_kakatua_rig",
        "build": build_kakatua,
        "bones": KAKATUA_BONES,
        "action": "ENV_act_kakatua_swim",
        "L": 0.439,
        "jaw_hinge": -0.198,
        "snout": -0.230,
        "cam": (0.66, -0.28, 0.29),
        "target": (0.0, 0.0, 0.004),
        "mats": [
            ("green", "MAT_kakatua_body", HEX_GREEN, 0.42, 0.38),
            ("teal", "MAT_kakatua_belly", HEX_TEAL, 0.40, 0.38),
            ("orange", "MAT_kakatua_line", HEX_ORANGE, 0.46, 0.34),
            ("cream", "MAT_kakatua_beak", HEX_CREAM, 0.44, 0.34),
            ("fin", "MAT_kakatua_fin", HEX_DEEP, 0.42, 0.40),
            ("eye", "MAT_kakatua_eye", HEX_EYE, 0.16, 0.62),
            ("sand", "MAT_kakatua_tail-base", HEX_CREAM, 0.44, 0.34),
        ],
        "note": ("parrotfish 0,44 m: badan oval memanjang, paruh krem, sirip "
                 "punggung panjang, ekor bercabang pangkal krem, sirip dada biru"),
    },
    "damselfish": {
        "scene": "fish-damselfish_v004",
        "out": "fish-damselfish_v004.blend",
        "arm": "CHR_fish_damselfish_rig",
        "build": build_damselfish,
        "bones": DAMSELFISH_BONES,
        "action": "ENV_act_damselfish_swim",
        "L": 0.103,
        "jaw_hinge": -0.044,
        "snout": -0.053,
        "cam": (0.200, -0.075, 0.055),
        "target": (0.0, 0.0, 0.001),
        "mats": [
            ("blue", "MAT_damselfish_body", HEX_DEEP, 0.40, 0.40),
            ("teal", "MAT_damselfish_highlight", HEX_TEAL, 0.38, 0.42),
            ("sand", "MAT_damselfish_tail", HEX_SAND, 0.44, 0.34),
            ("orange", "MAT_damselfish_tail-edge", HEX_ORANGE, 0.46, 0.34),
            ("eye", "MAT_damselfish_eye", HEX_EYE, 0.16, 0.62),
        ],
        "note": ("damselfish 0,10 m: badan pipih oval kecil, moncong runcing, "
                 "ekor kuning-oranye, biru + highlight teal"),
    },
    "cakalang": {
        "scene": "fish-cakalang-rig_v004",
        "out": "fish-cakalang-rig_v004.blend",
        "arm": "CHR_cakalang_rig",
        "build": build_cakalang,
        "bones": CAKALANG_BONES,
        "action": "ENV_act_cakalang_swim",
        "L": 0.702,
        "jaw_hinge": -0.312,
        "snout": -0.356,
        "cam": (1.05, -0.40, 0.30),
        "target": (0.0, 0.0, 0.004),
        "mats": [
            ("back", "MAT_fish_back", HEX_DEEP, 0.46, 0.32),
            ("belly", "MAT_fish_belly", HEX_CREAM, 0.40, 0.38),
            ("fin", "MAT_fish_fin", HEX_ORANGE, 0.50, 0.30),
            ("eye", "MAT_fish_eye", HEX_EYE, 0.18, 0.60),
        ],
        "note": ("skipjack 0,70 m: bentuk dipertahankan, sirip punggung "
                 "dirapikan (satu puncak simetris), ekor bercabang"),
    },
}


# ---------------------------------------------------------------------------
# scene, armature, bobot, action
# ---------------------------------------------------------------------------


def wipe_scene():
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


def setup_scene(scn, cfg):
    scn.name = cfg["scene"]
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
        scn.eevee.taa_render_samples = 32
    except AttributeError:
        pass
    scn.render.image_settings.file_format = "PNG"
    scn.render.image_settings.color_mode = "RGBA"
    scn.render.film_transparent = False
    scn["asset"] = cfg["scene"]
    scn["asset_note"] = cfg["note"]
    scn["facing"] = "-Y"
    scn["up"] = "+Z"
    scn["scale_note"] = "panjang total %.3f m; origin tengah badan" % cfg["L"]
    return scn, engine


def build_rig(col, ctl, cfg):
    arm_data = bpy.data.armatures.new(cfg["arm"])
    arm_obj = bpy.data.objects.new(cfg["arm"], arm_data)
    col.objects.link(arm_obj)
    if ctl is not None:
        arm_obj.parent = ctl
        arm_obj.matrix_parent_inverse = ctl.matrix_world.inverted()
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = arm_obj
    arm_obj.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    eb = arm_data.edit_bones
    for name, head, tail, parent, deform in cfg["bones"]:
        b = eb.new(name)
        b.head = Vector(head)
        b.tail = Vector(tail)
        b.use_deform = deform
        if parent:
            b.parent = eb[parent]
    bpy.ops.object.mode_set(mode="OBJECT")
    arm_obj.show_in_front = True
    arm_obj["asset"] = cfg["arm"]
    arm_obj["note"] = ("root kontrol (use_deform False), 9 bone deform; "
                       "hadap -Y, up +Z, ekor di +Y")
    arm_obj["facing"] = "-Y"
    arm_obj["up"] = "+Z"
    return arm_obj


def auto_bind(obj, arm_obj):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    arm_obj.select_set(True)
    bpy.context.view_layer.objects.active = arm_obj
    status = "auto"
    try:
        bpy.ops.object.parent_set(type="ARMATURE_AUTO")
    except RuntimeError as err:
        print("PERINGATAN automatic weights gagal pada %s: %s" % (obj.name, err))
        status = "gagal-auto"
        try:
            bpy.ops.object.parent_set(type="ARMATURE_ENVELOPE")
            status = "envelope"
        except RuntimeError as err2:
            print("PERINGATAN envelope gagal:", err2)
            obj.parent = arm_obj
            obj.matrix_parent_inverse = arm_obj.matrix_world.inverted()
            obj.modifiers.new("Armature", "ARMATURE").object = arm_obj
            status = "manual"
    bpy.ops.object.select_all(action="DESELECT")
    return status


def chain_centers(arm_obj):
    centers = []
    for name in CHAIN:
        b = arm_obj.data.bones[name]
        centers.append((name, (b.head_local.y + b.tail_local.y) * 0.5))
    centers.sort(key=lambda c: c[1])
    return centers


def chain_weights(y, centers):
    if y <= centers[0][1]:
        return {centers[0][0]: 1.0}
    if y >= centers[-1][1]:
        return {centers[-1][0]: 1.0}
    for k in range(len(centers) - 1):
        y0 = centers[k][1]
        y1 = centers[k + 1][1]
        if y0 <= y <= y1:
            t = (y - y0) / (y1 - y0)
            return {centers[k][0]: 1.0 - t, centers[k + 1][0]: t}
    return {centers[-1][0]: 1.0}


def collect_auto(obj):
    gname = {g.index: g.name for g in obj.vertex_groups}
    out = {}
    for v in obj.data.vertices:
        d = {}
        for g in v.groups:
            n = gname.get(g.group)
            if n in CHAIN and g.weight > 1e-4:
                d[n] = g.weight
        out[v.index] = d
    return out


def apply_weights(obj, ranges, arm_obj, cfg):
    centers = chain_centers(arm_obj)
    auto = collect_auto(obj)
    verts = obj.data.vertices
    final = {}

    def add(idx, w):
        d = final.setdefault(idx, {})
        for n, val in w.items():
            if val > 1e-5:
                d[n] = d.get(n, 0.0) + val

    for role, (v0, v1) in ranges.items():
        coords = [verts[i].co for i in range(v0, v1)]
        if not coords:
            continue
        if role in ("body", "body_eye"):
            for i in range(v0, v1):
                w = dict(auto.get(i) or {})
                if not w:
                    w = chain_weights(verts[i].co.y, centers)
                add(i, w)
            # rahang: ujung moncong ikut jaw, pangkal tetap spine_01
            if role == "body":
                for i in range(v0, v1):
                    co = verts[i].co
                    if co.y >= cfg["jaw_hinge"]:
                        continue
                    t = (cfg["jaw_hinge"] - co.y) / max(1e-6, cfg["jaw_hinge"] - cfg["snout"])
                    t = max(0.0, min(1.0, t))
                    wj = 0.75 * t
                    prev = final.get(i, {})
                    total = sum(prev.values()) or 1.0
                    scaled = {n: (v / total) * (1.0 - wj) for n, v in prev.items()}
                    scaled["jaw"] = wj
                    final[i] = scaled
        elif role == "dorsal":
            zmin = min(c.z for c in coords)
            zmax = max(c.z for c in coords)
            span = max(1e-6, zmax - zmin)
            for i in range(v0, v1):
                t = (verts[i].co.z - zmin) / span
                t = max(0.0, min(1.0, t))
                wd = 0.30 + 0.62 * t
                add(i, {"dorsal": wd, "spine_02": 1.0 - wd})
        elif role in ("pectoral", "pectoral_L", "pectoral_R"):
            xs = [abs(c.x) for c in coords]
            x0, x1 = min(xs), max(xs)
            span = max(1e-9, x1 - x0)
            for i in range(v0, v1):
                t = (abs(verts[i].co.x) - x0) / span
                t = max(0.0, min(1.0, t))
                w2 = 0.45 + 0.45 * t
                add(i, {"spine_02": w2, "spine_01": 1.0 - w2})
        elif role in ("pelvic", "pelvic_L", "pelvic_R"):
            zs = [c.z for c in coords]
            z0, z1 = max(zs), min(zs)
            span = max(1e-9, z0 - z1)
            bone = "pelvic_L" if role in ("pelvic", "pelvic_L") else "pelvic_R"
            if role == "pelvic":
                # satu range berisi sepasang: pilih bone dari tanda x
                bone = None
            for i in range(v0, v1):
                t = (z0 - verts[i].co.z) / span
                t = max(0.0, min(1.0, t))
                wb = 0.30 + 0.60 * t
                bn = bone or ("pelvic_L" if verts[i].co.x >= 0 else "pelvic_R")
                add(i, {bn: wb, "spine_02": 1.0 - wb})
        elif role in ("anal", "caudal"):
            for i in range(v0, v1):
                add(i, chain_weights(verts[i].co.y, centers))
        else:
            for i in range(v0, v1):
                add(i, chain_weights(verts[i].co.y, centers))

    for i in range(len(verts)):
        if not final.get(i):
            final[i] = chain_weights(verts[i].co.y, centers)

    for g in list(obj.vertex_groups):
        obj.vertex_groups.remove(g)
    groups = {n: obj.vertex_groups.new(name=n) for n in DEFORM}
    for idx, d in final.items():
        s = sum(d.values())
        if s <= 1e-9:
            continue
        for n, w in d.items():
            ww = w / s
            if ww > 1e-4:
                groups[n].add([idx], ww, "REPLACE")
    return final


def count_unweighted(obj):
    return sum(1 for v in obj.data.vertices
               if sum(g.weight for g in v.groups) < 1e-4)


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


def build_swim_actions(arm_obj, cfg):
    """Satu action dasar + empat varian fase (offset 0/8/16/24 frame)."""
    bpy.ops.object.select_all(action="DESELECT")
    arm_obj.select_set(True)
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode="POSE")
    pbs = arm_obj.pose.bones
    for pb in pbs:
        pb.rotation_mode = "QUATERNION"

    axes = {
        "X": Vector((1.0, 0.0, 0.0)),
        "Y": Vector((0.0, 1.0, 0.0)),
        "Z": Vector((0.0, 0.0, 1.0)),
    }
    ad = arm_obj.animation_data_create()
    made = []
    specs = [(cfg["action"], 0)]
    for k, off in enumerate(PHASE_VARIANTS):
        specs.append(("%s_p%d" % (cfg["action"], k + 1), off))

    for name, offset in specs:
        ad.action = None
        for pb in pbs:
            pb.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
        n_keys = 0
        for f in range(1, N_FRAMES + 2):
            t = ((f - 1 + offset) % N_FRAMES) / float(N_FRAMES)
            for bname, amp, axis, phase in SWIM:
                pb = pbs.get(bname)
                if pb is None:
                    continue
                ang = radians(amp) * sin(2.0 * pi * t + radians(phase))
                ax = pb.bone.matrix_local.to_3x3().inverted() @ axes[axis]
                ax.normalize()
                pb.rotation_quaternion = Quaternion(ax, ang)
                pb.keyframe_insert(data_path="rotation_quaternion", frame=f)
                n_keys += 1
        act = ad.action
        if act is None:
            raise RuntimeError("action tidak terbentuk: %s" % name)
        act.name = name
        act.use_fake_user = True
        try:
            act.use_frame_range = True
            act.frame_start = 1
            act.frame_end = N_FRAMES
        except Exception:
            pass
        for fc in action_fcurves(act):
            for kp in fc.keyframe_points:
                kp.interpolation = "LINEAR"
        made.append((name, n_keys, len(action_fcurves(act))))
        ad.action = None

    bpy.ops.object.mode_set(mode="OBJECT")
    ad.action = bpy.data.actions.get(cfg["action"])
    try:
        if ad.action and len(ad.action.slots):
            ad.action_slot = ad.action.slots[0]
    except Exception as err:
        print("PERINGATAN action_slot:", err)
    return made


# ---------------------------------------------------------------------------
# preview, ukur, render
# ---------------------------------------------------------------------------


def setup_preview(scn, cfg):
    prev = bpy.data.collections.new("PREVIEW")
    scn.collection.children.link(prev)
    L = cfg["L"]

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
    cam_data.lens = 50.0
    cam_data.clip_start = max(0.0005, 0.004 * L)
    cam_data.clip_end = 100.0
    cam = bpy.data.objects.new("CAM_preview", cam_data)
    prev.objects.link(cam)
    cam.location = cfg["cam"]
    cam.rotation_euler = (Vector(cfg["target"]) - cam.location).normalized(
    ).to_track_quat("-Z", "Y").to_euler()
    scn.camera = cam

    key = bpy.data.objects.new("LGT_preview-key",
                               bpy.data.lights.new("LGT_preview-key", "SUN"))
    prev.objects.link(key)
    key.data.energy = 2.0
    key.data.angle = radians(20)
    key.rotation_euler = (radians(46), 0.0, radians(30))

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


def eval_vert(obj, index):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    me = ev.to_mesh()
    p = obj.matrix_world @ me.vertices[index].co.copy()
    ev.to_mesh_clear()
    return p


def measure(parts, arm_obj, cfg, scn):
    """Amplitudo lokal, sudut ekor vs spine, perpindahan sirip, orientasi."""
    report = {}
    ad = arm_obj.animation_data
    base = bpy.data.actions.get(cfg["action"])
    if ad and base:
        ad.action = base
        if len(base.slots):
            ad.action_slot = base.slots[0]

    local_amp = {}
    tail_angles = {}
    spine_angles = {}
    for f in range(1, N_FRAMES + 1):
        scn.frame_set(f)
        bpy.context.view_layer.update()
        for bname, _, _, _ in SWIM:
            pb = arm_obj.pose.bones.get(bname)
            if pb is None:
                continue
            q = pb.rotation_quaternion
            ang = degrees(2.0 * atan2(Vector((q[1], q[2], q[3])).length, abs(q[0])))
            local_amp[bname] = max(local_amp.get(bname, 0.0), ang)
        mw = arm_obj.matrix_world

        def yaw(name):
            pb = arm_obj.pose.bones[name]
            head = mw @ pb.head
            tail = mw @ pb.tail
            d = (tail - head).normalized()
            return degrees(atan2(d.x, d.y))

        tsp = yaw("tail_02") - yaw("spine_01")
        while tsp > 180.0:
            tsp -= 360.0
        while tsp < -180.0:
            tsp += 360.0
        tail_angles[f] = tsp
        spine_angles[f] = yaw("spine_01")

    report["local_amp"] = local_amp
    report["tail_vs_spine"] = tail_angles
    report["spine_yaw"] = spine_angles
    report["max_tail_vs_spine"] = max(abs(v) for v in tail_angles.values())
    report["max_frame"] = max(tail_angles, key=lambda k: abs(tail_angles[k]))

    # perpindahan ujung sirip dada & punggung (frame 1 -> 9 / 17)
    obj0 = parts[0]["obj"]
    ranges = parts[0]["ranges"]
    samples = {}
    if "pectoral" in ranges:
        samples["pect_tip"] = (obj0, ranges["pectoral"][1] - 1)
    if "pectoral_L" in ranges:
        samples["pect_L_tip"] = (obj0, ranges["pectoral_L"][1] - 1)
    if "dorsal" in ranges:
        samples["dorsal_tip"] = (obj0, ranges["dorsal"][1] - 1)
    # untuk cakalang, dada ada di objek terpisah
    for part in parts:
        for role, (a, b) in part["ranges"].items():
            if role.startswith("pectoral") and role != "pectoral":
                samples[role + "_tip"] = (part["obj"], b - 1)
    disp = {}
    for label, (obj, idx) in samples.items():
        scn.frame_set(1)
        bpy.context.view_layer.update()
        p1 = eval_vert(obj, idx)
        scn.frame_set(9)
        bpy.context.view_layer.update()
        p9 = eval_vert(obj, idx)
        scn.frame_set(17)
        bpy.context.view_layer.update()
        p17 = eval_vert(obj, idx)
        disp[label] = (round((p9 - p1).length * 1000.0, 2),
                       round((p17 - p1).length * 1000.0, 2))
    report["fin_disp_mm"] = disp

    # julat lateral ujung ekor (cari range caudal di semua objek)
    tail_obj, tail_rng = None, None
    for part in parts:
        if "caudal" in part["ranges"]:
            tail_obj, tail_rng = part["obj"], part["ranges"]["caudal"]
    xs = []
    if tail_rng:
        verts = tail_obj.data.vertices
        idx = max(range(*tail_rng), key=lambda i: verts[i].co.y)
        for f in (1, 9, 17, 25):
            scn.frame_set(f)
            bpy.context.view_layer.update()
            xs.append(eval_vert(tail_obj, idx).x * 1000.0)
        report["tail_tip_x_mm"] = [round(v, 2) for v in xs]
        report["tail_tip_span_mm"] = round(max(xs) - min(xs), 2)

    # orientasi mesh (data asli, tanpa deformasi)
    allco = []
    for part in parts:
        o = part["obj"]
        allco.extend([o.matrix_world @ v.co for v in o.data.vertices])
    n = float(len(allco))
    centroid = Vector((sum(p.x for p in allco) / n,
                       sum(p.y for p in allco) / n,
                       sum(p.z for p in allco) / n))
    nose = min(allco, key=lambda p: p.y)
    top = max(allco, key=lambda p: p.z)
    fwd = (nose - centroid).normalized()
    up = (top - centroid).normalized()
    report["forward"] = tuple(round(v, 3) for v in fwd)
    report["up"] = tuple(round(v, 3) for v in up)
    report["dot_forward"] = round(fwd.dot(Vector((0, -1, 0))), 4)
    report["dot_up"] = round(up.dot(Vector((0, 0, 1))), 4)
    report["nose_y"] = round(nose.y, 4)
    report["tail_y"] = round(max(p.y for p in allco), 4)

    # normal badan mengarah keluar?
    o = parts[0]["obj"]
    me = o.data
    dots = []
    for poly in me.polygons[:200]:
        c = poly.center
        d = (c - centroid)
        if d.length > 1e-9:
            dots.append(poly.normal.dot(d.normalized()))
    report["outward_normals"] = round(sum(dots) / max(1, len(dots)), 3)
    scn.frame_set(1)
    bpy.context.view_layer.update()
    return report


def render_frames(scn, cfg, species):
    cam = scn.camera
    os.makedirs(STILLS, exist_ok=True)
    scn.render.resolution_percentage = 50
    paths = []
    for f in (1, 9, 17, 25):
        scn.frame_set(f)
        path = os.path.join(STILLS, "fish-v004-%s-f%02d.png" % (species, f))
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


def parse_args():
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []
    species = "kakatua"
    if "--species" in argv:
        species = argv[argv.index("--species") + 1]
    render = "--no-render" not in argv
    return species, render


def main():
    species, do_render = parse_args()
    if species not in SPECIES:
        raise SystemExit("spesies tidak dikenal: %s" % species)
    cfg = SPECIES[species]

    try:
        bpy.context.preferences.filepaths.save_version = 0
    except Exception:
        pass

    scn = wipe_scene()
    scn, engine = setup_scene(scn, cfg)
    log("MODEL - %s: scene %s diset (EEVEE, 1920x1080, 24 fps, Standard, 32 frame)"
        % (species, cfg["scene"]))

    mats = {}
    for key, name, hexcol, rough, spec in cfg["mats"]:
        mats[key] = material(name, hexcol, roughness=rough, spec=spec)

    root = bpy.data.collections.new("ENV_fish")
    scn.collection.children.link(root)

    ctl = bpy.data.objects.new("CTL_fish", None)
    ctl.empty_display_type = "PLAIN_AXES"
    ctl.empty_display_size = 0.45 if cfg["L"] > 0.3 else 0.11
    ctl["asset"] = cfg["scene"].rsplit("_v", 1)[0]
    ctl["note"] = "pivot induk; origin tengah badan, z 0 = garis tengah"
    ctl["facing"] = "-Y"
    ctl["up"] = "+Z"
    root.objects.link(ctl)

    parts = cfg["build"](mats, root)
    nv = sum(len(p["obj"].data.vertices) for p in parts)
    nf = sum(len(p["obj"].data.polygons) for p in parts)
    for p in parts:
        p["obj"].parent = ctl
        p["obj"].matrix_parent_inverse = ctl.matrix_world.inverted()
        p["obj"]["facing"] = "-Y"
        p["obj"]["up"] = "+Z"
    log("MODEL - %s: %d objek, %d verteks, %d muka, panjang %.3f m"
        % (species, len(parts), nv, nf, cfg["L"]))

    arm_obj = build_rig(root, ctl, cfg)

    status = {}
    for p in parts:
        status[p["obj"].name] = auto_bind(p["obj"], arm_obj)
    bad_before = {p["obj"].name: count_unweighted(p["obj"]) for p in parts}
    for p in parts:
        apply_weights(p["obj"], p["ranges"], arm_obj, cfg)
    bad_after = {p["obj"].name: count_unweighted(p["obj"]) for p in parts}
    log("RIG - %s: %d bone (%d deform), bind %s, tanpa bobot %s -> %s"
        % (species, len(arm_obj.data.bones),
           sum(1 for b in arm_obj.data.bones if b.use_deform),
           status, bad_before, bad_after))

    made = build_swim_actions(arm_obj, cfg)
    log("ANIM - %s: %d action 1-%d loop (%s)"
        % (species, len(made), N_FRAMES,
           ", ".join(m[0] for m in made)))

    cam = setup_preview(scn, cfg)
    rep = measure(parts, arm_obj, cfg, scn)

    amp_txt = ", ".join("%s %.1f" % (k, v) for k, v in rep["local_amp"].items())
    tail_txt = " ".join("f%d %.1f" % (f, rep["tail_vs_spine"][f])
                        for f in (1, 9, 17, 25))
    log("VERIFY - %s: amp lokal (%s) derajat; sudut ekor-vs-spine %s; "
        "maks %.1f derajat f%d; julat lateral ujung ekor %.1f mm"
        % (species, amp_txt, tail_txt, rep["max_tail_vs_spine"],
           rep["max_frame"], rep.get("tail_tip_span_mm", 0.0)))
    log("VERIFY - %s: maju %s (dot -Y %.3f), atas %s (dot +Z %.3f), "
        "moncong y %.3f ujung ekor y %.3f, normal keluar %.2f, tanpa bobot %s"
        % (species, rep["forward"], rep["dot_forward"], rep["up"],
           rep["dot_up"], rep["nose_y"], rep["tail_y"],
           rep["outward_normals"], bad_after))

    print("=== RINGKASAN %s ===" % species)
    print("objek:", [(p["obj"].name, len(p["obj"].data.vertices)) for p in parts])
    print("bones:", [b.name for b in arm_obj.data.bones])
    print("deform:", [b.name for b in arm_obj.data.bones if b.use_deform])
    print("actions:", [a.name for a in bpy.data.actions])
    print("forward:", rep["forward"], "dot -Y", rep["dot_forward"])
    print("up:", rep["up"], "dot +Z", rep["dot_up"])
    print("amp:", rep["local_amp"])
    print("tail vs spine:", {f: round(rep["tail_vs_spine"][f], 2)
                             for f in (1, 9, 17, 25)})
    print("max tail vs spine: %.2f @ f%d" % (rep["max_tail_vs_spine"],
                                             rep["max_frame"]))
    print("sirip bergerak (mm, f1->f9 / f1->f17):", rep["fin_disp_mm"])
    print("tail tip x (mm, f1/9/17/25):", rep.get("tail_tip_x_mm"))
    print("unweighted:", bad_after)
    print("engine=%s vt=%s res=%dx%d fps=%d frame=%d"
          % (engine, scn.view_settings.view_transform, scn.render.resolution_x,
             scn.render.resolution_y, scn.render.fps, scn.frame_current))

    target = os.path.join(ENV, cfg["out"])
    scn.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=target, check_existing=False)
    size_kb = os.path.getsize(target) / 1024.0
    print("saved:", target, "%.1f KB" % size_kb)
    log("DONE - %s: %s disimpan (%.0f KB, %d bone, 5 action, frame 1)"
        % (species, cfg["out"], size_kb, len(arm_obj.data.bones)))

    if do_render:
        paths = render_frames(scn, cfg, species)
        log("VERIFY - %s: render 50%% frame 1/9/17/25: %s"
            % (species, ", ".join(os.path.basename(p) for p in paths)))


if __name__ == "__main__":
    main()

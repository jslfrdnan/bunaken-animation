"""
Membangun crowd dermaga low-detail (12 figur) — BLOCKOUT, bukan desain tokoh.

Hasil: assets/char/crowd.blend
  scene "crowd"
    koleksi CHR_crowd
      +-- empty CTL_crowd           pivot induk, origin di dasar (z 0)
      +-- CRW_01 … CRW_12           satu objek mesh utuh per figur
    koleksi PREVIEW               kamera + lampu + lantai (bukan bagian aset)

Acuan: storyboard/refs/ref-crowd-dermaga_v001.jpg (HANYA komposisi keramaian di
dermaga: orang berdiri berkelompok, tinggi beragam, warna pakaian beragam).
Foto itu stok editorial — tidak ditiru figur per figur, tidak dipakai sebagai
tekstur/latar. Basis proporsi: assets/char/mannequin.blend (spesifikasi dewasa
pria 1,72 m, dewasa wanita 1,62 m, anak 1,25 m) yang diskalakan ke tinggi target.

Isi: 8 dewasa (4 pria, 4 wanita, tinggi 1,55–1,78 m) + 4 anak (1,10–1,30 m).
Tanpa ciri khas individu: tanpa wajah detail, tanpa aksesori, tanpa nama orang.
Pakaian hanya bidang warna palette; bentuk umum (kaus, celana, rok, sepatu).

Skala nyata, kaki di z 0, hadap -Y. Material palette PROJECT.md §2 tanpa tekstur:
  MAT_crowd_skin       #E8D5B0  pasir hangat
  MAT_crowd_skin-alt   #C7A985  bibir (kulit digelapkan)
  MAT_crowd_hair       #2E383A  netral gelap
  MAT_crowd_teal       #1FA3A3
  MAT_crowd_teal-deep  #0F5C63
  MAT_crowd_cream      #F2E9DC
  MAT_crowd_sand       #E8D5B0
  MAT_crowd_orange     #E4713C  aksen
  MAT_crowd_grey       #8A8F8C
  MAT_crowd_dark       #2E383A  alas kaki

Skrip IDEMPOTEN terhadap datablock miliknya dan MENYIMPAN file di akhir.
Tanpa open_mainfile / read_factory_settings / read_homefile; file aktif dilepas
lewat save_as_mainfile ke renders/tmp/_wipe.blend.
"""

import bpy
import bmesh
import os
import math
import datetime
from math import cos, sin, pi, copysign
from mathutils import Vector

# ---------------------------------------------------------------------------
# palette & konstanta
# ---------------------------------------------------------------------------

PAL = {
    "skin": "#E8D5B0",
    "skin-alt": "#C7A985",
    "hair": "#2E383A",
    "teal": "#1FA3A3",
    "teal-deep": "#0F5C63",
    "cream": "#F2E9DC",
    "sand": "#E8D5B0",
    "orange": "#E4713C",
    "grey": "#8A8F8C",
    "dark": "#2E383A",
}

# urutan slot material (sama untuk semua mesh)
SLOTS = ["skin", "skin-alt", "hair", "teal", "teal-deep", "cream", "sand",
         "orange", "grey", "dark"]
M = {name: i for i, name in enumerate(SLOTS)}

SEG_TORSO = 24
SEG_LIMB = 12
SEG_HEAD = 18
SEG_HAIR = 16
SEG_FOOT = 12
SEG_NECK = 12

HEX_GROUND = "#2E383A"

# ---------------------------------------------------------------------------
# spesifikasi proporsi dasar (dari build-mannequin.py, meter)
# ---------------------------------------------------------------------------

SPECS = {
    "male": {
        "height": 1.72,
        "torso": [
            (0.800, 0.132, 0.084),
            (0.900, 0.163, 0.099),
            (1.010, 0.140, 0.087),
            (1.120, 0.148, 0.093),
            (1.230, 0.163, 0.101),
            (1.330, 0.170, 0.103),
            (1.410, 0.163, 0.092),
            (1.440, 0.098, 0.070),
        ],
        "torso_exp": 2.4,
        "neck": (1.395, 1.515, 0.048),
        "head": ((0.0, 0.0, 1.6055), (0.077, 0.093, 0.1145)),
        "arm": [
            (0.158, 0.000, 1.400, 0.050),
            (0.205, 0.005, 1.075, 0.041),
            (0.236, 0.010, 0.780, 0.029),
        ],
        "leg": [
            (0.093, 0.000, 0.880, 0.086),
            (0.098, 0.012, 0.470, 0.058),
            (0.100, 0.016, 0.090, 0.036),
        ],
        "foot": (0.100, 0.072, -0.168, [
            (0.072, 0.040, 0.030),
            (0.030, 0.047, 0.038),
            (-0.070, 0.049, 0.033),
            (-0.168, 0.040, 0.018),
        ]),
    },
    "female": {
        "height": 1.62,
        "torso": [
            (0.780, 0.126, 0.081),
            (0.870, 0.156, 0.096),
            (0.980, 0.120, 0.078),
            (1.090, 0.133, 0.088),
            (1.200, 0.148, 0.096),
            (1.300, 0.153, 0.096),
            (1.375, 0.146, 0.086),
            (1.405, 0.090, 0.065),
        ],
        "torso_exp": 2.4,
        "neck": (1.330, 1.430, 0.043),
        "head": ((0.0, 0.0, 1.512), (0.072, 0.089, 0.108)),
        "arm": [
            (0.143, 0.000, 1.330, 0.045),
            (0.186, 0.005, 1.030, 0.036),
            (0.213, 0.010, 0.760, 0.026),
        ],
        "leg": [
            (0.088, 0.000, 0.855, 0.080),
            (0.092, 0.012, 0.455, 0.053),
            (0.094, 0.016, 0.086, 0.033),
        ],
        "foot": (0.094, 0.068, -0.158, [
            (0.068, 0.037, 0.028),
            (0.028, 0.044, 0.035),
            (-0.066, 0.046, 0.031),
            (-0.158, 0.037, 0.017),
        ]),
    },
    "child": {
        "height": 1.25,
        "torso": [
            (0.585, 0.094, 0.070),
            (0.660, 0.112, 0.079),
            (0.760, 0.098, 0.070),
            (0.860, 0.106, 0.076),
            (0.955, 0.112, 0.079),
            (1.005, 0.106, 0.073),
            (1.020, 0.070, 0.055),
        ],
        "torso_exp": 2.6,
        "neck": (0.985, 1.055, 0.038),
        "head": ((0.0, 0.0, 1.1425), (0.078, 0.091, 0.1075)),
        "arm": [
            (0.108, 0.000, 1.000, 0.040),
            (0.140, 0.004, 0.780, 0.028),
            (0.161, 0.008, 0.565, 0.022),
        ],
        "leg": [
            (0.070, 0.000, 0.635, 0.062),
            (0.074, 0.010, 0.340, 0.042),
            (0.076, 0.013, 0.072, 0.028),
        ],
        "foot": (0.076, 0.052, -0.118, [
            (0.052, 0.031, 0.024),
            (0.020, 0.037, 0.030),
            (-0.050, 0.039, 0.027),
            (-0.118, 0.031, 0.015),
        ]),
    },
}

# ---------------------------------------------------------------------------
# 12 figur: (nama, basis, tinggi target, kulit, atasan, bawahan, rok?, rambut panjang?)
# ---------------------------------------------------------------------------

FIGURES = [
    ("CRW_01", "male", 1.76, "skin", "grey", "teal-deep", False, False),
    ("CRW_02", "female", 1.63, "skin-alt", "teal", "sand", False, True),
    ("CRW_03", "male", 1.70, "skin-alt", "cream", "grey", False, False),
    ("CRW_04", "child", 1.24, "skin", "orange", "teal-deep", False, False),
    ("CRW_05", "female", 1.58, "skin", "cream", "teal-deep", True, True),
    ("CRW_06", "male", 1.78, "skin", "teal", "dark", False, False),
    ("CRW_07", "female", 1.66, "skin-alt", "sand", "teal", False, False),
    ("CRW_08", "child", 1.12, "skin", "teal", "grey", False, False),
    ("CRW_09", "male", 1.66, "skin", "sand", "teal-deep", False, False),
    ("CRW_10", "female", 1.55, "skin", "grey", "cream", True, True),
    ("CRW_11", "child", 1.30, "skin-alt", "cream", "teal-deep", False, False),
    ("CRW_12", "child", 1.18, "skin", "sand", "orange", False, False),
]

# penempatan panggung (x, y) — hanya pratinjau, origin tetap di dasar
PLACE = [
    (-2.45, 0.65), (-1.65, -0.30), (-0.90, 0.85), (-0.10, -0.10),
    (0.70, 0.72), (1.60, -0.22), (2.50, 0.60), (-2.00, 1.60),
    (0.10, 1.75), (1.80, 1.62), (-0.55, -1.20), (0.95, -1.30),
]

# ---------------------------------------------------------------------------
# utilitas mesh
# ---------------------------------------------------------------------------


def srgb(hexstr):
    h = hexstr.lstrip("#")
    values = [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]

    def to_linear(u):
        return u / 12.92 if u <= 0.04045 else ((u + 0.055) / 1.055) ** 2.4

    return tuple(to_linear(v) for v in values) + (1.0,)


def superellipse(rx, ry, t, exp):
    ct, st = cos(t), sin(t)
    x = rx * copysign(abs(ct) ** (2.0 / exp), ct)
    y = ry * copysign(abs(st) ** (2.0 / exp), st)
    return x, y


def ring(center, rx, ry, seg, exp=2.0):
    """Cincin horizontal (bidang XY) di ketinggian z."""
    cx, cy, cz = center
    out = []
    for i in range(seg):
        a, b = superellipse(rx, ry, 2.0 * pi * i / seg, exp)
        out.append(Vector((cx + a, cy + b, cz)))
    return out


def loft(V, F, FM, FS, rings, mat, smooth=True, cap_a=True, cap_b=True):
    starts = []
    for r in rings:
        starts.append(len(V))
        for p in r:
            V.append(Vector(p))
    n = len(rings[0])
    for k in range(len(rings) - 1):
        a, b = starts[k], starts[k + 1]
        for i in range(n):
            i2 = (i + 1) % n
            F.append((a + i, a + i2, b + i2, b + i))
            FM.append(mat)
            FS.append(smooth)
    if cap_a:
        F.append(tuple(starts[0] + i for i in range(n - 1, -1, -1)))
        FM.append(mat)
        FS.append(False)
    if cap_b:
        F.append(tuple(starts[-1] + i for i in range(n)))
        FM.append(mat)
        FS.append(False)
    return starts


def sweep_rings(pts, radii, seg, up=Vector((0, 1, 0)), exp=2.0):
    rings = []
    n = len(pts)
    for i, p in enumerate(pts):
        if i == 0:
            t = pts[1] - pts[0]
        elif i == n - 1:
            t = pts[-1] - pts[-2]
        else:
            t = pts[i + 1] - pts[i - 1]
        t = t.normalized()
        side = t.cross(up)
        if side.length < 1e-6:
            alt = Vector((1, 0, 0)) if abs(t.x) < 0.9 else Vector((0, 1, 0))
            side = t.cross(alt)
        side.normalize()
        up2 = side.cross(t).normalized()
        rx = radii[i]
        pts_ring = []
        for k in range(seg):
            a, b = superellipse(rx, rx, 2.0 * pi * k / seg, exp)
            pts_ring.append(p + side * a + up2 * b)
        rings.append(pts_ring)
    return rings


def ellipsoid(V, F, FM, FS, center, radii, seg=SEG_HEAD, rings_n=8, mat=0):
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


def foot(V, F, FM, FS, cx, y_heel, y_toe, widths, mat):
    starts = []
    for (y, rx, rz) in widths:
        starts.append(len(V))
        for i in range(SEG_FOOT):
            x, dz = superellipse(rx, rz, 2.0 * pi * i / SEG_FOOT, 2.6)
            V.append(Vector((cx + x, y, rz + dz)))
    for k in range(len(starts) - 1):
        a, b = starts[k], starts[k + 1]
        for i in range(SEG_FOOT):
            i2 = (i + 1) % SEG_FOOT
            F.append((a + i, a + i2, b + i2, b + i))
            FM.append(mat)
            FS.append(True)
    F.append(tuple(starts[0] + i for i in range(SEG_FOOT - 1, -1, -1)))
    FM.append(mat)
    FS.append(False)
    F.append(tuple(starts[-1] + i for i in range(SEG_FOOT)))
    FM.append(mat)
    FS.append(False)


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


def material(name, hexcol, roughness=0.62, spec=0.3):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.use_backface_culling = False
    col = srgb(hexcol)
    mat.diffuse_color = col
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = col
    bsdf.inputs["Roughness"].default_value = roughness
    spec_in = bsdf.inputs.get("Specular IOR Level") or bsdf.inputs.get("Specular")
    if spec_in is not None:
        spec_in.default_value = spec
    return mat


# ---------------------------------------------------------------------------
# pembangun figur
# ---------------------------------------------------------------------------


def scaled(spec, target_h):
    """Skalakan seluruh koordinat spesifikasi ke tinggi target."""
    k = target_h / spec["height"]

    def p3(p):
        return tuple(v * k for v in p)

    torso = [(z * k, rx * k, ry * k) for (z, rx, ry) in spec["torso"]]
    neck = tuple(v * k for v in spec["neck"])
    head = (p3(spec["head"][0]), p3(spec["head"][1]))
    arm = [(x * k, y * k, z * k, r * k) for (x, y, z, r) in spec["arm"]]
    leg = [(x * k, y * k, z * k, r * k) for (x, y, z, r) in spec["leg"]]
    fx, yh, yt, widths = spec["foot"]
    footp = (fx * k, yh * k, yt * k, [(y * k, rx * k, rz * k)
                                      for (y, rx, rz) in widths])
    return {
        "k": k,
        "height": target_h,
        "torso": torso,
        "torso_exp": spec["torso_exp"],
        "neck": neck,
        "head": head,
        "arm": arm,
        "leg": leg,
        "foot": footp,
    }


def build_figure(name, base, target_h, skin, shirt, bottom, skirt, long_hair,
                 col, mats):
    sp = scaled(SPECS[base], target_h)
    k = sp["k"]
    V, F, FM, FS = [], [], [], []
    M_SKIN = M[skin]
    M_HAIR = M["hair"]
    M_SHIRT = M[shirt]
    M_BOTTOM = M[bottom]
    M_SHOE = M["dark"]

    # --- torso (atasan) ----------------------------------------------------
    profile = sp["torso"]
    exp = sp["torso_exp"]
    loft(V, F, FM, FS,
         [ring((0.0, 0.0, z), rx, ry, SEG_TORSO, exp) for (z, rx, ry) in profile],
         mat=M_SHIRT)

    # --- leher -------------------------------------------------------------
    z0, z1, r = sp["neck"]
    loft(V, F, FM, FS,
         [ring((0.0, 0.0, z0), r, r, SEG_NECK, 2.0),
          ring((0.0, 0.0, z1), r, r, SEG_NECK, 2.0)],
         mat=M_SKIN, cap_a=False, cap_b=False)

    # --- kepala ------------------------------------------------------------
    hc, hr = sp["head"]
    ellipsoid(V, F, FM, FS, hc, hr, seg=SEG_HEAD, rings_n=8, mat=M_SKIN)

    # --- rambut: cangkang sedikit lebih besar, digeser ke belakang ---------
    hair_c = (hc[0], hc[1] + hr[1] * 0.14, hc[2] + hr[2] * 0.06)
    hair_r = (hr[0] * 1.07, hr[1] * 1.05, hr[2] * 1.0)
    ellipsoid(V, F, FM, FS, hair_c, hair_r, seg=SEG_HAIR, rings_n=6, mat=M_HAIR)
    if long_hair:
        # massa rambut di belakang kepala sampai tengkuk
        loft(V, F, FM, FS,
             [ring((0.0, hr[1] * 0.55, hc[2] - hr[2] * 0.05),
                   hr[0] * 0.85, hr[1] * 0.55, SEG_HAIR, 2.2),
              ring((0.0, hr[1] * 0.62, hc[2] - hr[2] * 0.85),
                   hr[0] * 0.80, hr[1] * 0.50, SEG_HAIR, 2.2),
              ring((0.0, hr[1] * 0.55, hc[2] - hr[2] * 1.6),
                   hr[0] * 0.70, hr[1] * 0.42, SEG_HAIR, 2.2)],
             mat=M_HAIR)

    # --- lengan: bahu -> siku -> pergelangan, plus lengan pendek -----------
    joints = sp["arm"]
    for sx in (-1.0, 1.0):
        pts = [Vector((sx * x, y, z)) for (x, y, z, r) in joints]
        radii = [r for (x, y, z, r) in joints]
        loft(V, F, FM, FS,
             sweep_rings(pts, radii, SEG_LIMB, up=Vector((0, 1, 0))),
             mat=M_SKIN)
        # lengan pendek kaus: tabung sedikit lebih besar di pangkal lengan
        sleeve_pts = [pts[0], pts[0].lerp(pts[1], 0.55)]
        sleeve_r = [radii[0] * 1.14, radii[0] * 1.06]
        loft(V, F, FM, FS,
             sweep_rings(sleeve_pts, sleeve_r, SEG_LIMB, up=Vector((0, 1, 0))),
             mat=M_SHIRT, cap_a=False, cap_b=False)
        # penutup bahu (menutup ujung lengan yang menonjol di bahu)
        ellipsoid(V, F, FM, FS, (pts[0].x, pts[0].y, pts[0].z),
                  (radii[0] * 1.16, radii[0] * 1.16, radii[0] * 1.05),
                  seg=SEG_LIMB, rings_n=5, mat=M_SHIRT)
        # tangan
        hx, hy, hz = pts[-1]
        ellipsoid(V, F, FM, FS, (hx, hy, hz - 0.055 * k),
                  (0.030 * k, 0.024 * k, 0.052 * k),
                  seg=10, rings_n=5, mat=M_SKIN)

    # --- kaki --------------------------------------------------------------
    ljoints = sp["leg"]
    hip_z = ljoints[0][2]
    knee_z = ljoints[1][2]
    for sx in (-1.0, 1.0):
        if skirt:
            # rok: kerucut dari pinggang ke lutut, kaki di bawahnya berkulit
            skirt_top = profile[0][0]
            loft(V, F, FM, FS,
                 [ring((0.0, 0.0, skirt_top + 0.02 * k),
                       profile[0][1] * 1.02, profile[0][2] * 1.02,
                       SEG_TORSO, exp),
                  ring((0.0, 0.0, (skirt_top + knee_z) * 0.5),
                       profile[0][1] * 1.35 + 0.02,
                       profile[0][2] * 1.35 + 0.02,
                       SEG_TORSO, exp),
                  ring((0.0, 0.0, knee_z - 0.02 * k),
                       profile[0][1] * 1.55,
                       profile[0][2] * 1.55,
                       SEG_TORSO, exp)],
                 mat=M_BOTTOM, cap_a=False, cap_b=False)
            lp = [Vector((sx * x, y, z)) for (x, y, z, r) in ljoints]
            lr = [r for (x, y, z, r) in ljoints]
            loft(V, F, FM, FS,
                 sweep_rings(lp, lr, SEG_LIMB, up=Vector((0, 1, 0))),
                 mat=M_SKIN)
        else:
            lp = [Vector((sx * x, y, z)) for (x, y, z, r) in ljoints]
            lr = [r for (x, y, z, r) in ljoints]
            loft(V, F, FM, FS,
                 sweep_rings(lp, lr, SEG_LIMB, up=Vector((0, 1, 0))),
                 mat=M_BOTTOM)
            # ujung celana di atas sepatu: sedikit lebih lebar
            cuff = [lp[2].lerp(lp[1], 0.12), lp[2]]
            loft(V, F, FM, FS,
                 sweep_rings(cuff, [lr[2] * 1.05, lr[2] * 1.05], SEG_LIMB,
                             up=Vector((0, 1, 0))),
                 mat=M_BOTTOM, cap_a=False, cap_b=False)
        fx, yh, yt, widths = sp["foot"]
        foot(V, F, FM, FS, sx * fx, yh, yt, widths, M_SHOE)

    # --- normalisasi tinggi: kaki tetap di z 0, ubun-ubun tepat target -----
    zmax = max(p.z for p in V)
    if zmax > 0:
        fix = target_h / zmax
        for p in V:
            p.z *= fix

    obj = new_mesh_object(name, V, F, FM, FS,
                          [mats[s] for s in SLOTS], col)
    obj["height_target_m"] = target_h
    obj["category"] = "anak" if base == "child" else (
        "dewasa-wanita" if base == "female" else "dewasa-pria")
    obj["facing"] = "-Y"
    obj["blockout"] = True
    return obj


# ---------------------------------------------------------------------------
# scene, preview, simpan
# ---------------------------------------------------------------------------


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


def setup_scene(scn):
    scn.name = "crowd"
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
    scn.frame_end = 48
    scn.frame_set(1)
    engine = set_engine(scn)
    try:
        scn.eevee.taa_render_samples = 24
    except AttributeError:
        pass
    scn.render.image_settings.file_format = "PNG"
    scn.render.image_settings.color_mode = "RGBA"
    scn.render.film_transparent = False
    scn["asset"] = "crowd"
    scn["asset_note"] = ("12 figur blockout warga dermaga: 8 dewasa + 4 anak, "
                         "satu mesh per figur, tanpa wajah detail, tanpa tekstur.")
    return scn, engine


def setup_preview(scn):
    prev = bpy.data.collections.new("PREVIEW")
    scn.collection.children.link(prev)

    ground_mat = material("MAT_preview_crowd-ground", HEX_GROUND, roughness=0.95,
                          spec=0.08)
    mesh = bpy.data.meshes.new("PREVIEW_ground")
    mesh.from_pydata(
        [(-14, -14, -0.002), (14, -14, -0.002), (14, 14, -0.002), (-14, 14, -0.002)],
        [], [(0, 1, 2, 3)],
    )
    mesh.materials.append(ground_mat)
    mesh.update()
    prev.objects.link(bpy.data.objects.new("PREVIEW_ground", mesh))

    cam_data = bpy.data.cameras.new("CAM_preview")
    cam_data.lens = 40.0
    cam = bpy.data.objects.new("CAM_preview", cam_data)
    prev.objects.link(cam)
    cam.location = (0.15, -7.20, 2.55)
    cam.rotation_euler = (Vector((0.0, 0.25, 1.05)) - cam.location).normalized(
    ).to_track_quat("-Z", "Y").to_euler()
    scn.camera = cam

    key = bpy.data.objects.new("LGT_preview-key",
                               bpy.data.lights.new("LGT_preview-key", "SUN"))
    prev.objects.link(key)
    key.data.energy = 2.1
    key.data.angle = math.radians(16)
    key.rotation_euler = (math.radians(50), 0.0, math.radians(28))

    fill = bpy.data.objects.new("LGT_preview-fill",
                                bpy.data.lights.new("LGT_preview-fill", "AREA"))
    prev.objects.link(fill)
    fill.data.energy = 420.0
    fill.data.size = 7.0
    fill.location = (-4.2, -6.0, 3.6)
    fill.rotation_euler = (Vector((0, 0.2, 1.0)) - fill.location).normalized(
    ).to_track_quat("-Z", "Y").to_euler()

    rim = bpy.data.objects.new("LGT_preview-rim",
                               bpy.data.lights.new("LGT_preview-rim", "AREA"))
    prev.objects.link(rim)
    rim.data.energy = 380.0
    rim.data.size = 6.0
    rim.location = (4.5, 5.0, 4.2)
    rim.rotation_euler = (Vector((0, 0, 1.2)) - rim.location).normalized(
    ).to_track_quat("-Z", "Y").to_euler()

    world = bpy.data.worlds.new("WLD_crowd-preview")
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.060, 0.074, 0.080, 1.0)
    bg.inputs["Strength"].default_value = 1.0
    scn.world = world
    return cam


def repo_root():
    try:
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    except NameError:
        return os.getcwd()


def log(line):
    path = os.path.join(repo_root(), "renders", "logs", "modeling.log")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    stamp = datetime.datetime.now().strftime("%H:%M")
    with open(path, "a", encoding="utf-8") as fh:
        fh.write("[%s] %s\n" % (stamp, line))


def release_and_wipe():
    tmp = os.path.join(repo_root(), "renders", "tmp", "_wipe.blend")
    os.makedirs(os.path.dirname(tmp), exist_ok=True)
    try:
        bpy.context.preferences.filepaths.save_version = 0
    except Exception:
        pass
    if bpy.data.filepath and os.path.abspath(bpy.data.filepath) != os.path.abspath(tmp):
        bpy.ops.wm.save_as_mainfile(filepath=tmp)

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
                   bpy.data.images):
        for b in list(blocks):
            try:
                blocks.remove(b)
            except Exception:
                pass
    return scn


def render_previews():
    scn = bpy.context.scene
    cam = scn.camera
    out_dir = os.path.join(repo_root(), "renders", "stills")
    os.makedirs(out_dir, exist_ok=True)
    shots = [
        ("crowd_preview-01", (0.15, -7.20, 2.55), (0.0, 0.25, 1.05), 40.0),
        ("crowd_preview-02", (5.20, -4.60, 2.30), (0.10, 0.30, 1.00), 42.0),
    ]
    scn.render.resolution_percentage = 50
    paths = []
    for name, loc, tgt, lens in shots:
        cam.location = loc
        cam.data.lens = lens
        cam.rotation_euler = (Vector(tgt) - Vector(loc)).normalized().to_track_quat(
            "-Z", "Y").to_euler()
        path = os.path.join(out_dir, name + ".png")
        scn.render.filepath = path
        bpy.ops.render.render(write_still=True)
        paths.append(path)
        print("render ->", path)
    scn.render.resolution_percentage = 100
    return paths


def main():
    scn = release_and_wipe()
    scn, engine = setup_scene(scn)
    log("MCP - Blender siap; scene crowd diset (EEVEE, 1920x1080, 24 fps, Standard)")

    mats = {
        "skin": material("MAT_crowd_skin", PAL["skin"], roughness=0.55, spec=0.25),
        "skin-alt": material("MAT_crowd_skin-alt", PAL["skin-alt"], roughness=0.55, spec=0.25),
        "hair": material("MAT_crowd_hair", PAL["hair"], roughness=0.62, spec=0.15),
        "teal": material("MAT_crowd_teal", PAL["teal"], roughness=0.72, spec=0.18),
        "teal-deep": material("MAT_crowd_teal-deep", PAL["teal-deep"], roughness=0.72, spec=0.18),
        "cream": material("MAT_crowd_cream", PAL["cream"], roughness=0.75, spec=0.15),
        "sand": material("MAT_crowd_sand", PAL["sand"], roughness=0.75, spec=0.15),
        "orange": material("MAT_crowd_orange", PAL["orange"], roughness=0.72, spec=0.18),
        "grey": material("MAT_crowd_grey", PAL["grey"], roughness=0.78, spec=0.14),
        "dark": material("MAT_crowd_dark", PAL["dark"], roughness=0.65, spec=0.20),
    }

    root = bpy.data.collections.new("CHR_crowd")
    scn.collection.children.link(root)

    ctl = bpy.data.objects.new("CTL_crowd", None)
    ctl.empty_display_type = "PLAIN_AXES"
    ctl.empty_display_size = 1.0
    ctl.location = (0.0, 0.0, 0.0)
    ctl["asset"] = "CHR_crowd"
    ctl["note"] = "pivot induk crowd; origin tiap figur di dasar (z 0), hadap -Y"
    root.objects.link(ctl)

    made = []
    for idx, (name, base, height, skin, shirt, bottom, skirt, long_hair) in \
            enumerate(FIGURES):
        obj = build_figure(name, base, height, skin, shirt, bottom, skirt,
                           long_hair, root, mats)
        x, y = PLACE[idx]
        obj.location = (x, y, 0.0)
        obj.parent = ctl
        obj.matrix_parent_inverse = ctl.matrix_world.inverted()
        made.append(obj)

    setup_preview(scn)

    total = 0
    print("=== RINGKASAN CHR_crowd ===")
    for obj in made:
        d = obj.dimensions
        v = len(obj.data.vertices)
        total += v
        print("%-8s verts=%4d faces=%4d tinggi=%.3f m  lebar=%.3f  %s"
              % (obj.name, v, len(obj.data.polygons), d.z, d.x,
                 obj["category"]))
    print("total verts:", total)
    print("figur:", len(made), "| material:", len(bpy.data.materials))
    print("engine=%s vt=%s res=%dx%d fps=%d frame=%d"
          % (engine, scn.view_settings.view_transform, scn.render.resolution_x,
             scn.render.resolution_y, scn.render.fps, scn.frame_current))

    target = os.path.join(repo_root(), "assets", "char", "crowd.blend")
    bpy.ops.wm.save_as_mainfile(filepath=target, check_existing=False)
    print("saved:", target, "%.1f KB" % (os.path.getsize(target) / 1024.0))
    log("MODEL - crowd.blend: 12 figur, %d vert total, tinggi %.2f-%.2f m"
        % (total, min(o["height_target_m"] for o in made),
           max(o["height_target_m"] for o in made)))

    paths = render_previews()
    log("VERIFY - crowd_preview-01/02 50%%: %s" % ", ".join(
        os.path.basename(p) for p in paths))


if __name__ == "__main__":
    main()

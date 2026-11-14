"""
Membangun mannequin blockout generik untuk previz — BUKAN desain karakter.

Hasil: assets/char/mannequin.blend
  koleksi CHR_mannequin
    +-- empty CTL_mannequin        (pivot, origin di dasar / z 0)
    +-- MAN_adult-male   (koleksi) -> mesh MAN_adult-male   1,72 m
    +-- MAN_adult-female (koleksi) -> mesh MAN_adult-female 1,62 m
    +-- MAN_child        (koleksi) -> mesh MAN_child        1,25 m
  koleksi PREVIEW (kamera + lampu + lantai; bukan bagian aset)

Ini placeholder pengisi shot previz selama character sheet manusia belum ada.
Tidak ada ciri khas tokoh siapa pun: tanpa wajah detail, tanpa kumis/topi/bekas
luka, tanpa pakaian. Hanya proporsi + ball joint supaya siluet terbaca.

Skala nyata (meter), arah hadap -Y (sama dengan nara_rig.blend), kaki di z 0.
Material: MAT_mannequin_body #8A8F8C (abu netral, permintaan Director — di luar
palette PROJECT.md §2) dan MAT_mannequin_accent #1FA3A3 (teal palette §2, hanya
sabuk + garis dada sebagai penanda arah depan). Tanpa tekstur image.

Praktis: tiga varian disusun berdampingan di sumbu X supaya bisa dipratinjau
sekaligus (offset objek 0 / 1,05 / 1,95 m). Setelah di-append sendiri-sendiri,
set lokasi objek ke (0, 0, 0) bila ingin menempel di origin.

Skrip ini IDEMPOTEN: datablock miliknya dibersihkan dulu tiap kali dijalankan.
Skrip TIDAK menyimpan file — penyimpanan dilakukan setelah verifikasi + render.
"""

import bpy
import os
import math
from math import cos, sin, pi, copysign
from mathutils import Vector

# ---------------------------------------------------------------------------
# konstanta
# ---------------------------------------------------------------------------

HEX_BODY = "#8A8F8C"     # abu netral (permintaan Director)
HEX_ACCENT = "#1FA3A3"   # teal laut, palette PROJECT.md §2

SEG_TORSO = 28
SEG_LIMB = 16
SEG_BALL = 14
SEG_NECK = 14
SEG_FOOT = 16   # genap: satu verteks jatuh tepat di titik terendah (sol z 0)

STAGE_X = {"adult-male": 0.0, "adult-female": 1.05, "child": 1.95}

OWN_PREFIX = (
    "CHR_mannequin", "MAN_", "CTL_mannequin", "MAT_mannequin_",
    "CAM_preview", "LGT_preview", "PREVIEW", "WLD_mannequin",
)
OWN_DATA_PREFIX = (
    "MAT_mannequin_", "MAT_preview_mannequin", "PREVIEW_", "CAM_preview",
    "LGT_preview", "WLD_mannequin", "MAN_", "CHR_mannequin",
)
STARTUP_DEFAULTS = ("Cube", "Light", "Camera")
JUNK_DATA = ("Material", "Dots Stroke")


# ---------------------------------------------------------------------------
# utilitas mesh
# ---------------------------------------------------------------------------


def srgb(hexstr):
    """hex sRGB -> linear RGBA (Blender menyimpan Base Color linear)."""
    h = hexstr.lstrip("#")
    values = [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]

    def to_linear(u):
        return u / 12.92 if u <= 0.04045 else ((u + 0.055) / 1.055) ** 2.4

    return tuple(to_linear(v) for v in values) + (1.0,)


def superellipse(rx, ry, t, exp):
    """Titik (x, y) pada superellipse; exp=2 -> elips, exp>2 -> makin kotak."""
    ct, st = cos(t), sin(t)
    x = rx * copysign(abs(ct) ** (2.0 / exp), ct)
    y = ry * copysign(abs(st) ** (2.0 / exp), st)
    return x, y


def loft(V, F, FM, FS, sections, seg, exp=2.0, mat=0,
         cap_bottom=True, cap_top=True, smooth=True):
    """Cincin horizontal di-Z; sections = [(cx, cy, z, rx, ry), ...]."""
    starts = []
    for (cx, cy, z, rx, ry) in sections:
        starts.append(len(V))
        for i in range(seg):
            x, y = superellipse(rx, ry, 2.0 * pi * i / seg, exp)
            V.append(Vector((cx + x, cy + y, z)))
    for k in range(len(starts) - 1):
        a, b = starts[k], starts[k + 1]
        for i in range(seg):
            i2 = (i + 1) % seg
            F.append((a + i, a + i2, b + i2, b + i))
            FM.append(mat)
            FS.append(smooth)
    if cap_bottom:
        F.append(tuple(starts[0] + i for i in range(seg - 1, -1, -1)))
        FM.append(mat)
        FS.append(False)
    if cap_top:
        F.append(tuple(starts[-1] + i for i in range(seg)))
        FM.append(mat)
        FS.append(False)
    return starts


def ellipsoid(V, F, FM, FS, center, radii, seg=SEG_BALL, rings=8, mat=0, smooth=True):
    """Bola/elipsoid kutub-atas."""
    cx, cy, cz = center
    rx, ry, rz = radii
    top = len(V)
    V.append(Vector((cx, cy, cz + rz)))
    ring_starts = []
    for ir in range(1, rings):
        th = pi * ir / rings
        s, c = sin(th), cos(th)
        st = len(V)
        for i in range(seg):
            ph = 2.0 * pi * i / seg
            V.append(Vector((cx + rx * s * cos(ph), cy + ry * s * sin(ph), cz + rz * c)))
        ring_starts.append(st)
    bot = len(V)
    V.append(Vector((cx, cy, cz - rz)))

    first = ring_starts[0]
    for i in range(seg):
        i2 = (i + 1) % seg
        F.append((top, first + i, first + i2))
        FM.append(mat)
        FS.append(smooth)
    for k in range(len(ring_starts) - 1):
        a, b = ring_starts[k], ring_starts[k + 1]
        for i in range(seg):
            i2 = (i + 1) % seg
            F.append((a + i, b + i, b + i2, a + i2))
            FM.append(mat)
            FS.append(smooth)
    last = ring_starts[-1]
    for i in range(seg):
        i2 = (i + 1) % seg
        F.append((bot, last + i2, last + i))
        FM.append(mat)
        FS.append(smooth)


def ball(V, F, FM, FS, center, r, mat=0, seg=SEG_BALL, rings=8):
    ellipsoid(V, F, FM, FS, center, (r, r, r), seg=seg, rings=rings, mat=mat)


def foot(V, F, FM, FS, cx, y_heel, y_toe, widths, mat=0):
    """Sepatu/alas kotak: cincin tegak-lurus Y, dasar rata di z 0.

    widths = [(y, rx, rz), ...] dari tumit ke ujung kaki (y menurun).
    """
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


def torso_profile(profile, z):
    """Interpolasi linear (rx, ry) badan pada ketinggian z."""
    pts = sorted(profile, key=lambda p: p[0])
    if z <= pts[0][0]:
        return pts[0][1], pts[0][2]
    if z >= pts[-1][0]:
        return pts[-1][1], pts[-1][2]
    for k in range(len(pts) - 1):
        z0, rx0, ry0 = pts[k]
        z1, rx1, ry1 = pts[k + 1]
        if z0 <= z <= z1:
            t = (z - z0) / (z1 - z0)
            return rx0 + (rx1 - rx0) * t, ry0 + (ry1 - ry0) * t
    return pts[-1][1], pts[-1][2]


def new_mesh_object(name, V, F, FM, FS, mats, collection):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(V, [], F)
    for m in mats:
        mesh.materials.append(m)
    for poly, mat_index, smooth in zip(mesh.polygons, FM, FS):
        poly.material_index = mat_index
        poly.use_smooth = smooth
    mesh.validate(verbose=False)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    return obj


# ---------------------------------------------------------------------------
# spesifikasi proporsi
# ---------------------------------------------------------------------------
#
# torso : [(z, rx, ry), ...] dari bawah ke atas (meter)
# neck  : (z0, z1, r)
# head  : ((cx, cy, cz), (rx, ry, rz))  -- tinggi kepala = 2*rz
# arm   : [(x, y, z, ball_r, limb_r), ...] bahu -> siku -> pergelangan
# hand  : [(x, y, z, rx, ry), ...] pergelangan -> ujung tangan
# leg   : [(x, y, z, ball_r, limb_r), ...] pinggul -> lutut -> pergelangan kaki
# foot  : (cx, y_heel, y_toe, [(y, rx, rz), ...])
# belt  : (z_pusat, setengah_tinggi)
# line  : (z0, z1, setengah_lebar)  garis dada penanda arah depan

SPECS = {
    "adult-male": {
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
        "head_seg": (20, 12),
        "arm": [
            (0.158, 0.000, 1.400, 0.048, 0.050),
            (0.205, 0.005, 1.075, 0.045, 0.041),
            (0.236, 0.010, 0.780, 0.032, 0.029),
        ],
        "hand": [
            (0.236, 0.010, 0.780, 0.030, 0.040),
            (0.240, 0.010, 0.730, 0.034, 0.047),
            (0.242, 0.010, 0.680, 0.031, 0.043),
            (0.242, 0.010, 0.648, 0.014, 0.018),
        ],
        "leg": [
            (0.093, 0.000, 0.880, 0.078, 0.086),
            (0.098, 0.012, 0.470, 0.062, 0.058),
            (0.100, 0.016, 0.090, 0.040, 0.036),
        ],
        "foot": (0.100, 0.072, -0.168, [
            (0.072, 0.040, 0.030),
            (0.030, 0.047, 0.038),
            (-0.070, 0.049, 0.033),
            (-0.168, 0.040, 0.018),
        ]),
        "belt": (1.005, 0.030),
        "line": (1.120, 1.410, 0.011),
    },
    "adult-female": {
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
        "head_seg": (20, 12),
        "arm": [
            (0.143, 0.000, 1.330, 0.043, 0.045),
            (0.186, 0.005, 1.030, 0.040, 0.036),
            (0.213, 0.010, 0.760, 0.028, 0.026),
        ],
        "hand": [
            (0.213, 0.010, 0.760, 0.027, 0.036),
            (0.217, 0.010, 0.715, 0.031, 0.043),
            (0.219, 0.010, 0.668, 0.028, 0.039),
            (0.219, 0.010, 0.638, 0.013, 0.016),
        ],
        "leg": [
            (0.088, 0.000, 0.855, 0.072, 0.080),
            (0.092, 0.012, 0.455, 0.057, 0.053),
            (0.094, 0.016, 0.086, 0.037, 0.033),
        ],
        "foot": (0.094, 0.068, -0.158, [
            (0.068, 0.037, 0.028),
            (0.028, 0.044, 0.035),
            (-0.066, 0.046, 0.031),
            (-0.158, 0.037, 0.017),
        ]),
        "belt": (0.975, 0.028),
        "line": (1.090, 1.375, 0.010),
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
        "head_seg": (20, 12),
        "arm": [
            (0.108, 0.000, 1.000, 0.040, 0.038),
            (0.140, 0.004, 0.780, 0.032, 0.028),
            (0.161, 0.008, 0.565, 0.024, 0.022),
        ],
        "hand": [
            (0.161, 0.008, 0.565, 0.023, 0.030),
            (0.164, 0.008, 0.531, 0.026, 0.035),
            (0.166, 0.008, 0.498, 0.024, 0.032),
            (0.166, 0.008, 0.478, 0.011, 0.014),
        ],
        "leg": [
            (0.070, 0.000, 0.635, 0.057, 0.062),
            (0.074, 0.010, 0.340, 0.046, 0.042),
            (0.076, 0.013, 0.072, 0.031, 0.028),
        ],
        "foot": (0.076, 0.052, -0.118, [
            (0.052, 0.031, 0.024),
            (0.020, 0.037, 0.030),
            (-0.050, 0.039, 0.027),
            (-0.118, 0.031, 0.015),
        ]),
        "belt": (0.755, 0.024),
        "line": (0.860, 1.000, 0.009),
    },
}


# ---------------------------------------------------------------------------
# pembangun badan
# ---------------------------------------------------------------------------


def build_body(spec, body_mat, accent_mat, collection, name):
    V, F, FM, FS = [], [], [], []
    MAT_BODY, MAT_ACCENT = 0, 1
    profile = spec["torso"]
    exp = spec["torso_exp"]

    # --- badan -------------------------------------------------------------
    loft(V, F, FM, FS,
         [(0.0, 0.0, z, rx, ry) for (z, rx, ry) in profile],
         SEG_TORSO, exp=exp, mat=MAT_BODY)

    # --- leher -------------------------------------------------------------
    z0, z1, r = spec["neck"]
    loft(V, F, FM, FS,
         [(0.0, 0.0, z0, r, r), (0.0, 0.0, z1, r, r)],
         SEG_NECK, exp=2.0, mat=MAT_BODY, cap_bottom=False, cap_top=False)

    # --- kepala ------------------------------------------------------------
    hseg, hrings = spec["head_seg"]
    ellipsoid(V, F, FM, FS, spec["head"][0], spec["head"][1],
              seg=hseg, rings=hrings, mat=MAT_BODY)

    # --- lengan (kiri & kanan) --------------------------------------------
    joints = spec["arm"]
    for sx in (-1.0, 1.0):
        for k, (x, y, z, br, sr) in enumerate(joints):
            ball(V, F, FM, FS, (sx * x, y, z), br, mat=MAT_BODY)
            if k < len(joints) - 1:
                nx, ny, nz, nbr, nsr = joints[k + 1]
                loft(V, F, FM, FS,
                     [(sx * x, y, z, sr, sr),
                      (sx * (x + nx) * 0.5, (y + ny) * 0.5, (z + nz) * 0.5,
                       (sr + nsr) * 0.5, (sr + nsr) * 0.5),
                      (sx * nx, ny, nz, nsr, nsr)],
                     SEG_LIMB, exp=2.0, mat=MAT_BODY,
                     cap_bottom=False, cap_top=False)
        # tangan
        loft(V, F, FM, FS,
             [(sx * x, y, z, rx, ry) for (x, y, z, rx, ry) in spec["hand"]],
             SEG_LIMB, exp=3.0, mat=MAT_BODY)

    # --- kaki (kiri & kanan) ----------------------------------------------
    ljoints = spec["leg"]
    for sx in (-1.0, 1.0):
        for k, (x, y, z, br, sr) in enumerate(ljoints):
            ball(V, F, FM, FS, (sx * x, y, z), br, mat=MAT_BODY)
            if k < len(ljoints) - 1:
                nx, ny, nz, nbr, nsr = ljoints[k + 1]
                loft(V, F, FM, FS,
                     [(sx * x, y, z, sr, sr),
                      (sx * (x + nx) * 0.5, (y + ny) * 0.5, (z + nz) * 0.5,
                       (sr + nsr) * 0.5, (sr + nsr) * 0.5),
                      (sx * nx, ny, nz, nsr, nsr)],
                     SEG_LIMB, exp=2.0, mat=MAT_BODY,
                     cap_bottom=False, cap_top=False)
        fx, y_heel, y_toe, widths = spec["foot"]
        foot(V, F, FM, FS, sx * fx, y_heel, y_toe, widths, mat=MAT_BODY)

    # --- aksen: sabuk ------------------------------------------------------
    bz, bh = spec["belt"]
    rx, ry = torso_profile(profile, bz)
    loft(V, F, FM, FS,
         [(0.0, 0.0, bz - bh, rx * 1.02 + 0.004, ry * 1.02 + 0.004),
          (0.0, 0.0, bz + bh, rx * 1.02 + 0.004, ry * 1.02 + 0.004)],
         SEG_TORSO, exp=exp, mat=MAT_ACCENT, cap_bottom=False, cap_top=False)

    # --- aksen: garis dada (penanda arah hadap -Y) -------------------------
    lz0, lz1, lw = spec["line"]
    rows = [lz0 + (lz1 - lz0) * i / 4.0 for i in range(5)]
    base = len(V)
    for z in rows:
        rx_z, ry_z = torso_profile(profile, z)
        y = -(ry_z + 0.003)
        V.append(Vector((-lw, y, z)))
        V.append(Vector((lw, y, z)))
    for i in range(len(rows) - 1):
        a = base + i * 2
        F.append((a, a + 1, a + 3, a + 2))
        FM.append(MAT_ACCENT)
        FS.append(True)

    return new_mesh_object(name, V, F, FM, FS, [body_mat, accent_mat], collection)


# ---------------------------------------------------------------------------
# material & scene
# ---------------------------------------------------------------------------


def material(name, hexcol, roughness=0.6, metallic=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.use_backface_culling = False
    mat.diffuse_color = srgb(hexcol)
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = srgb(hexcol)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    spec = bsdf.inputs.get("Specular IOR Level") or bsdf.inputs.get("Specular")
    if spec is not None:
        spec.default_value = 0.30
    return mat


def set_engine(scn):
    """EEVEE: identifier berubah antar versi, jadi jangan hardcode."""
    last = None
    for cand in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scn.render.engine = cand
            return cand
        except TypeError as err:
            last = err
    print("PERINGATAN: gagal set EEVEE:", last)
    return scn.render.engine


def setup_scene():
    scn = bpy.context.scene
    scn.name = "mannequin"
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
    scn.frame_end = 96
    scn.frame_set(1)
    engine = set_engine(scn)
    try:
        scn.eevee.taa_render_samples = 32
    except AttributeError:
        pass
    scn.render.image_settings.file_format = "PNG"
    scn.render.image_settings.color_mode = "RGBA"
    try:
        scn.render.image_settings.color_depth = "16"
    except TypeError:
        pass
    scn.render.film_transparent = False
    scn["previz_only"] = True
    scn["note"] = "mannequin placeholder previz; render final menunggu character sheet"
    return scn, engine


def setup_preview(scn):
    prev = bpy.data.collections.new("PREVIEW")
    scn.collection.children.link(prev)

    ground_mat = material("MAT_preview_mannequin-ground", "#2E383A", roughness=0.92)
    mesh = bpy.data.meshes.new("PREVIEW_ground")
    mesh.from_pydata(
        [(-16, -16, -0.003), (16, -16, -0.003), (16, 16, -0.003), (-16, 16, -0.003)],
        [], [(0, 1, 2, 3)],
    )
    mesh.materials.append(ground_mat)
    mesh.update()
    prev.objects.link(bpy.data.objects.new("PREVIEW_ground", mesh))

    cam_data = bpy.data.cameras.new("CAM_preview")
    cam_data.lens = 40.0
    cam = bpy.data.objects.new("CAM_preview", cam_data)
    prev.objects.link(cam)
    cam.location = (-1.10, -5.40, 1.95)
    cam.rotation_euler = (Vector((0.94, 0.0, 0.86)) - cam.location).normalized().to_track_quat(
        "-Z", "Y").to_euler()
    scn.camera = cam

    key = bpy.data.objects.new("LGT_preview-key", bpy.data.lights.new("LGT_preview-key", "SUN"))
    prev.objects.link(key)
    key.data.energy = 3.2
    key.data.angle = math.radians(6)
    key.rotation_euler = (math.radians(54), 0.0, math.radians(34))

    fill = bpy.data.objects.new("LGT_preview-fill", bpy.data.lights.new("LGT_preview-fill", "AREA"))
    prev.objects.link(fill)
    fill.data.energy = 320.0
    fill.data.size = 7.0
    fill.location = (-3.2, -5.6, 2.8)
    fill.rotation_euler = (Vector((0.9, 0, 1.0)) - fill.location).normalized().to_track_quat(
        "-Z", "Y").to_euler()

    rim = bpy.data.objects.new("LGT_preview-rim", bpy.data.lights.new("LGT_preview-rim", "AREA"))
    prev.objects.link(rim)
    rim.data.energy = 260.0
    rim.data.size = 5.0
    rim.location = (4.6, 3.6, 3.6)
    rim.rotation_euler = (Vector((0.9, 0, 1.2)) - rim.location).normalized().to_track_quat(
        "-Z", "Y").to_euler()

    world = bpy.data.worlds.new("WLD_mannequin-preview")
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.052, 0.066, 0.074, 1.0)
    bg.inputs["Strength"].default_value = 1.0
    scn.world = world
    return cam


# ---------------------------------------------------------------------------
# pembersihan (idempoten)
# ---------------------------------------------------------------------------


def cleanup():
    """Hapus datablock milik skrip ini + default startup, tanpa menyentuh file lain."""
    scn = bpy.context.scene
    # lepaskan world milik skrip supaya bisa dihapus (bukan sekadar jadi .001)
    if scn is not None and scn.world is not None and scn.world.name.startswith("WLD_mannequin"):
        scn.world = None
    if scn is not None and scn.camera is not None and scn.camera.name.startswith("CAM_preview"):
        scn.camera = None

    doomed = [o for o in bpy.data.objects
              if o.name.startswith(OWN_PREFIX) or o.name in STARTUP_DEFAULTS]
    for obj in doomed:
        for col in list(obj.users_collection):
            col.objects.unlink(obj)
        bpy.data.objects.remove(obj, do_unlink=True)

    for col in list(bpy.data.collections):
        if col.name.startswith(OWN_PREFIX):
            bpy.data.collections.remove(col)

    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.cameras,
                 bpy.data.lights, bpy.data.worlds):
        for block in list(coll):
            if block.name.startswith(OWN_DATA_PREFIX) and block.users == 0:
                coll.remove(block)

    for me in list(bpy.data.meshes):
        if me.name in ("Cube",) and me.users == 0:
            bpy.data.meshes.remove(me)

    # sisa default startup
    for col in list(bpy.data.collections):
        if col.name == "Collection" and not col.objects and not col.children:
            bpy.data.collections.remove(col)
    for wld in list(bpy.data.worlds):
        if wld.name == "World" and wld.users == 0:
            bpy.data.worlds.remove(wld)
    for coll in (bpy.data.materials, bpy.data.meshes):
        for block in list(coll):
            if block.name in JUNK_DATA and block.users == 0:
                coll.remove(block)


# ---------------------------------------------------------------------------
# render pratinjau
# ---------------------------------------------------------------------------


def repo_root():
    try:
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    except NameError:
        return os.path.dirname(os.path.dirname(bpy.data.filepath))


def render_previews():
    scn = bpy.context.scene
    cam = scn.camera
    out_dir = os.path.join(repo_root(), "renders", "stills")
    os.makedirs(out_dir, exist_ok=True)
    shots = [
        ("mannequin_preview-01", (-1.10, -5.40, 1.95), (0.94, 0.0, 0.86), 40.0),
        ("mannequin_preview-02", (4.90, 4.90, 2.35), (0.94, 0.0, 0.88), 45.0),
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


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main():
    cleanup()
    scn, engine = setup_scene()

    body_mat = material("MAT_mannequin_body", HEX_BODY, roughness=0.62)
    accent_mat = material("MAT_mannequin_accent", HEX_ACCENT, roughness=0.45)

    root = bpy.data.collections.new("CHR_mannequin")
    scn.collection.children.link(root)

    ctl = bpy.data.objects.new("CTL_mannequin", None)
    ctl.empty_display_type = "PLAIN_AXES"
    ctl.empty_display_size = 0.35
    ctl.location = (0.0, 0.0, 0.0)
    ctl["previz_only"] = True
    ctl["note"] = "pivot mannequin previz; origin di dasar (z 0)"
    root.objects.link(ctl)

    made = []
    for key in ("adult-male", "adult-female", "child"):
        name = "MAN_" + key
        col = bpy.data.collections.new(name)
        root.children.link(col)
        obj = build_body(SPECS[key], body_mat, accent_mat, col, name)
        obj.location = (STAGE_X[key], 0.0, 0.0)
        obj.parent = ctl
        obj.matrix_parent_inverse = ctl.matrix_world.inverted()
        obj["previz_only"] = True
        obj["height_target_m"] = SPECS[key]["height"]
        obj["facing"] = "-Y"
        made.append(obj)

    setup_preview(scn)

    print("=== RINGKASAN mannequin ===")
    total = 0
    for obj in made:
        d = obj.dimensions
        v = len(obj.data.vertices)
        total += v
        print(f"{obj.name}: verts={v} faces={len(obj.data.polygons)} "
              f"dims=({d.x:.3f}, {d.y:.3f}, {d.z:.3f}) m  stage_x={obj.location.x:.2f}")
    print("total verts:", total)
    print("materials:", [m.name for m in bpy.data.materials])
    print("collections:", [c.name for c in bpy.data.collections])
    print("engine:", engine, "vt:", scn.view_settings.view_transform,
          "res:", scn.render.resolution_x, "x", scn.render.resolution_y,
          "pct:", scn.render.resolution_percentage,
          "fps:", scn.render.fps, "frame:", scn.frame_current)
    return made


if __name__ == "__main__":
    main()

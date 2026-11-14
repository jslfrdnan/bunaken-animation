"""
Membangun ikan damselfish + rig renang 7 bone — blockout bentuk.

Hasil: assets/env/fish-damselfish.blend
  scene "fish-damselfish"
    koleksi ENV_fish
      +-- empty CTL_fish                       pivot induk, origin dunia (0,0,0)
      +-- CHR_fish_damselfish_rig              armature 7 bone
      +-- ENV_fish_damselfish                  badan + sirip + mata (satu mesh)
    koleksi PREVIEW                            kamera + lampu + lantai

Acuan bentuk & warna: storyboard/refs/ref-damselfish_v001.png (damselfish:
badan oval kecil, moncong meruncing, mata besar, badan biru cerah, ekor
kuning, sirip punggung biru panjang). Foto HANYA acuan proporsi/siluet &
warna — tidak dipakai sebagai tekstur, latar, atau image plane.

Skala nyata & orientasi (sama dengan fish-cakalang.blend):
  panjang total (moncong -> ujung ekor) ±0,10 m
  hadap -Y  (moncong di -Y, ekor di +Y)
  origin di tengah badan, z 0 = garis tengah badan
  tinggi badan maks ±0,021 m (kedalaman ±0,45 panjang badan)

Material (palette PROJECT.md §2, tanpa tekstur):
  MAT_damselfish_body      #0F5C63  teal dalam    badan
  MAT_damselfish_highlight #1FA3A3  teal          kilau sisi atas & kepala
  MAT_damselfish_tail      #E8D5B0  pasir hangat  ekor kuning
  MAT_damselfish_tail-edge #E4713C  oranye karang tepi ekor (aksen)
  MAT_damselfish_fin       #0F5C63  teal dalam    sirip
  MAT_damselfish_eye       #2E383A  netral gelap  mata

Rig: CHR_fish_damselfish_rig — root, spine_01, spine_02, tail_01, tail_02,
pectoral_L, pectoral_R. Automatic weights; root = kontrol (use_deform False).
Action: ENV_act_damselfish_swim, frame 1-20 loop (ekor ±18°, badan halus,
sirip dada mengepak ±14° — ikan kecil mengepak lebih cepat).

Skrip IDEMPOTEN terhadap datablock miliknya dan MENYIMPAN file di akhir.
Tanpa open_mainfile / read_factory_settings / read_homefile; file aktif
dilepas lewat save_as_mainfile ke renders/tmp/_wipe.blend.
"""

import bpy
import bmesh
import os
import math
import datetime
from math import cos, sin, pi, copysign, radians
from mathutils import Vector, Quaternion

# ---------------------------------------------------------------------------
# konstanta
# ---------------------------------------------------------------------------

HEX_BLUE = "#0F5C63"     # teal dalam, palette §2
HEX_TEAL = "#1FA3A3"     # teal laut, palette §2
HEX_YELLOW = "#E8D5B0"   # pasir hangat, palette §2
HEX_ORANGE = "#E4713C"   # oranye karang, palette §2 (aksen)
HEX_EYE = "#2E383A"      # netral gelap (14 Nov 2026)
HEX_GROUND = "#2E383A"

TOTAL_LEN = 0.10
BODY_LEN = 0.090
TAIL_TIP_Y = 0.052

SEG_BODY = 24
SEG_EYE = 12

SLOT = {"blue": 0, "teal": 1, "yellow": 2, "orange": 3, "eye": 4}
SLOT_ORDER = ["blue", "teal", "yellow", "orange", "eye"]
SLOT_MAT = {
    "blue": ("MAT_damselfish_body", HEX_BLUE, 0.40, 0.40),
    "teal": ("MAT_damselfish_highlight", HEX_TEAL, 0.38, 0.42),
    "yellow": ("MAT_damselfish_tail", HEX_YELLOW, 0.44, 0.34),
    "orange": ("MAT_damselfish_tail-edge", HEX_ORANGE, 0.46, 0.34),
    "eye": ("MAT_damselfish_eye", HEX_EYE, 0.16, 0.62),
}

# (y, rx, rz, cz) — moncong di -0,050, batang ekor di +0,040
BODY = [
    (-0.050, 0.0022, 0.0030, -0.001),
    (-0.046, 0.0048, 0.0068, -0.001),
    (-0.040, 0.0080, 0.0120, 0.000),
    (-0.032, 0.0110, 0.0165, 0.001),
    (-0.022, 0.0135, 0.0196, 0.001),
    (-0.010, 0.0146, 0.0206, 0.000),
    (0.002, 0.0142, 0.0200, -0.001),
    (0.014, 0.0125, 0.0166, -0.001),
    (0.026, 0.0095, 0.0112, 0.000),
    (0.034, 0.0060, 0.0070, 0.001),
    (0.040, 0.0040, 0.0046, 0.001),
]

Y0 = BODY[0][0]
Y1 = BODY[-1][0]

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
        FM.append(mats[-1])
        FS.append(False)


def plate(stations, thickness, axis, mats, V, F, FM, FS, smooth=True):
    n = Vector(axis).normalized() * (thickness * 0.5)
    rings = []
    for low, high in stations:
        low = Vector(low)
        high = Vector(high)
        rings.append([low - n, high - n, high + n, low + n])
    loft_rings(rings, mats, V, F, FM, FS, smooth=smooth)


def ellipsoid(center, radii, mat, V, F, FM, FS, seg=SEG_EYE, rings_n=6):
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


def body_profile(y):
    pts = BODY
    if y <= pts[0][0]:
        return pts[0][1], pts[0][2], pts[0][3]
    if y >= pts[-1][0]:
        return pts[-1][1], pts[-1][2], pts[-1][3]
    for k in range(len(pts) - 1):
        y0, rx0, rz0, cz0 = pts[k]
        y1, rx1, rz1, cz1 = pts[k + 1]
        if y0 <= y <= y1:
            t = (y - y0) / (y1 - y0)
            return (rx0 + (rx1 - rx0) * t,
                    rz0 + (rz1 - rz0) * t,
                    cz0 + (cz1 - cz0) * t)
    return pts[-1][1], pts[-1][2], pts[-1][3]


def body_top(y):
    rx, rz, cz = body_profile(y)
    return cz + rz


def body_bottom(y):
    rx, rz, cz = body_profile(y)
    return cz - rz


def body_mat(y, z, cz, rz):
    rel = (z - cz) / rz if rz > 1e-6 else 0.0
    # kilau teal di sisi atas badan & kepala
    if 0.24 <= rel <= 0.78:
        return SLOT["teal"]
    return SLOT["blue"]


# ---------------------------------------------------------------------------
# badan + sirip + mata
# ---------------------------------------------------------------------------


def build_body(V, F, FM, FS):
    starts = []
    for (y, rx, rz, cz) in BODY:
        starts.append(len(V))
        for i in range(SEG_BODY):
            a, b = superellipse(rx, rz, 2.0 * pi * i / SEG_BODY, 2.2)
            V.append(Vector((a, y, cz + b)))
    for k in range(len(starts) - 1):
        a, b = starts[k], starts[k + 1]
        for i in range(SEG_BODY):
            i2 = (i + 1) % SEG_BODY
            F.append((a + i, a + i2, b + i2, b + i))
            zc = (V[a + i].z + V[a + i2].z + V[b + i].z + V[b + i2].z) / 4.0
            yc = (V[a + i].y + V[a + i2].y + V[b + i].y + V[b + i2].y) / 4.0
            rx, rz, cz = body_profile(yc)
            FM.append(body_mat(yc, zc, cz, rz))
            FS.append(True)
    F.append(tuple(starts[0] + i for i in range(SEG_BODY - 1, -1, -1)))
    FM.append(SLOT["blue"])
    FS.append(False)
    F.append(tuple(starts[-1] + i for i in range(SEG_BODY)))
    FM.append(SLOT["blue"])
    FS.append(False)


def build_eyes(V, F, FM, FS):
    # mata besar khas damselfish, sedikit menonjol dari sisi kepala
    for sx in (-1.0, 1.0):
        ellipsoid((sx * 0.0082, -0.0340, 0.0055), (0.0034, 0.0046, 0.0046),
                  SLOT["teal"], V, F, FM, FS, seg=SEG_EYE, rings_n=6)
        ellipsoid((sx * 0.0098, -0.0344, 0.0055), (0.0027, 0.0035, 0.0035),
                  SLOT["eye"], V, F, FM, FS, seg=SEG_EYE, rings_n=6)


def build_dorsal(V, F, FM, FS):
    # sirip punggung panjang: dari belakang kepala sampai dekat ekor
    ys = [-0.034, -0.024, -0.012, 0.000, 0.012, 0.024, 0.034]
    hs = [0.0035, 0.0095, 0.0118, 0.0120, 0.0110, 0.0080, 0.0035]
    stations = []
    for y, h in zip(ys, hs):
        base = body_top(y) - 0.0012
        stations.append(((0.0, y, base), (0.0, y, base + h)))
    plate(stations, 0.0018, Vector((1, 0, 0)), [SLOT["blue"]] * (len(stations) - 1),
          V, F, FM, FS, smooth=False)
    # tepi teal tipis di atas sirip
    rim = []
    for y, h in zip(ys, hs):
        base = body_top(y) - 0.0012
        rim.append(((0.0, y, base + h - 0.0016), (0.0, y, base + h)))
    plate(rim, 0.0022, Vector((1, 0, 0)), [SLOT["teal"]] * (len(rim) - 1),
          V, F, FM, FS, smooth=False)


def build_anal(V, F, FM, FS):
    ys = [-0.014, -0.004, 0.008, 0.018, 0.028]
    hs = [0.0030, 0.0065, 0.0072, 0.0058, 0.0028]
    stations = []
    for y, h in zip(ys, hs):
        base = body_bottom(y) + 0.0012
        stations.append(((0.0, y, base), (0.0, y, base - h)))
    plate(stations, 0.0016, Vector((1, 0, 0)),
          [SLOT["blue"]] * (len(stations) - 1), V, F, FM, FS, smooth=False)


def build_pelvic(V, F, FM, FS):
    stations = [
        ((0.0, -0.026, body_bottom(-0.026) + 0.0010),
         (0.0, -0.026, body_bottom(-0.026) - 0.0022)),
        ((0.0, -0.020, body_bottom(-0.020) + 0.0010),
         (0.0, -0.020, body_bottom(-0.020) - 0.0060)),
        ((0.0, -0.014, body_bottom(-0.014) + 0.0010),
         (0.0, -0.014, body_bottom(-0.014) - 0.0030)),
    ]
    plate(stations, 0.0014, Vector((1, 0, 0)), [SLOT["blue"]] * 2, V, F, FM, FS,
          smooth=False)


def build_pectoral(sx, V, F, FM, FS):
    # sirip dada kecil, menyapu ke belakang-bawah
    ch = [
        ((sx * 0.0090, -0.0300, -0.0005), (sx * 0.0098, -0.0245, -0.0022)),
        ((sx * 0.0175, -0.0275, -0.0035), (sx * 0.0182, -0.0215, -0.0055)),
        ((sx * 0.0250, -0.0235, -0.0070), (sx * 0.0254, -0.0180, -0.0082)),
    ]
    plate(ch, 0.0012, Vector((0, 0, 1)), [SLOT["blue"]] * 2, V, F, FM, FS,
          smooth=False)


def build_caudal(V, F, FM, FS):
    # ekor kuning, sedikit bercabang; tepi oranye
    base = [
        ((0.0, 0.0320, -0.0042), (0.0, 0.0322, 0.0042)),
        ((0.0, 0.0380, -0.0060), (0.0, 0.0384, 0.0062)),
        ((0.0, 0.0430, -0.0078), (0.0, 0.0434, 0.0080)),
    ]
    plate(base, 0.0030, Vector((1, 0, 0)), [SLOT["yellow"]] * 2, V, F, FM, FS,
          smooth=False)

    for sign in (1.0, -1.0):
        lobe = [
            ((0.0, 0.0418, 0.0010), (0.0, 0.0420, 0.0084)),
            ((0.0, 0.0470, 0.0030), (0.0, 0.0474, 0.0126)),
            ((0.0, 0.0494, 0.0044), (0.0, 0.0498, 0.0142)),
            ((0.0, 0.0512, 0.0054), (0.0, 0.0516, 0.0152)),
        ]
        if sign < 0:
            lobe = [((x, y, -hi), (x, y, -lo)) for
                    ((x, y, lo), (x, y, hi)) in lobe]
        plate(lobe, 0.0026, Vector((1, 0, 0)),
              [SLOT["yellow"], SLOT["yellow"], SLOT["orange"]], V, F, FM, FS,
              smooth=False)


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


def setup_scene(scn, f_end):
    scn.name = "fish-damselfish"
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
    scn.frame_end = f_end
    scn.frame_set(1)
    engine = set_engine(scn)
    try:
        scn.eevee.taa_render_samples = 24
    except AttributeError:
        pass
    scn.render.image_settings.file_format = "PNG"
    scn.render.image_settings.color_mode = "RGBA"
    scn.render.film_transparent = False
    scn["asset"] = "fish-damselfish"
    scn["asset_note"] = ("Ikan damselfish 0,10 m + rig 7 bone, hadap -Y, origin "
                         "tengah badan. Acuan ref-damselfish_v001.png; palette §2.")
    return scn, engine


def setup_preview(scn, L):
    prev = bpy.data.collections.new("PREVIEW")
    scn.collection.children.link(prev)

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
    cam_data.lens = 55.0
    cam_data.clip_start = max(0.0008, 0.006 * L)
    cam_data.clip_end = 100.0
    cam = bpy.data.objects.new("CAM_preview", cam_data)
    prev.objects.link(cam)
    cam.location = (0.204, -0.133, 0.042)
    cam.rotation_euler = (Vector((0, 0.001, 0)) - cam.location).normalized(
    ).to_track_quat("-Z", "Y").to_euler()
    scn.camera = cam

    key = bpy.data.objects.new("LGT_preview-key",
                               bpy.data.lights.new("LGT_preview-key", "SUN"))
    prev.objects.link(key)
    key.data.energy = 1.8
    key.data.angle = math.radians(20)
    key.rotation_euler = (math.radians(46), 0.0, math.radians(30))

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


# ---------------------------------------------------------------------------
# rig + bobot
# ---------------------------------------------------------------------------

BONES = [
    ("root", (0.0, 0.0, 0.0), (0.0, 0.0, 0.010), None, False),
    ("spine_01", (0.0, -0.042, 0.0), (0.0, -0.008, 0.0), "root", True),
    ("spine_02", (0.0, -0.008, 0.0), (0.0, 0.014, 0.0), "spine_01", True),
    ("tail_01", (0.0, 0.014, 0.0), (0.0, 0.034, 0.0), "spine_02", True),
    ("tail_02", (0.0, 0.034, 0.0), (0.0, 0.052, 0.0), "tail_01", True),
    ("pectoral_L", (0.009, -0.030, -0.001), (0.025, -0.019, -0.008), "spine_01", True),
    ("pectoral_R", (-0.009, -0.030, -0.001), (-0.025, -0.019, -0.008), "spine_01", True),
]

CHAIN = ["spine_01", "spine_02", "tail_01", "tail_02"]


def build_rig(col, ctl):
    arm_data = bpy.data.armatures.new("CHR_fish_damselfish_rig")
    arm_obj = bpy.data.objects.new("CHR_fish_damselfish_rig", arm_data)
    col.objects.link(arm_obj)
    if ctl is not None:
        arm_obj.parent = ctl
        arm_obj.matrix_parent_inverse = ctl.matrix_world.inverted()
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = arm_obj
    arm_obj.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    eb = arm_data.edit_bones
    for name, head, tail, parent, deform in BONES:
        b = eb.new(name)
        b.head = Vector(head)
        b.tail = Vector(tail)
        b.use_deform = deform
        if parent:
            b.parent = eb[parent]
    bpy.ops.object.mode_set(mode="OBJECT")
    arm_obj.show_in_front = True
    arm_obj["asset"] = "CHR_fish_damselfish_rig"
    arm_obj["note"] = ("root kontrol (use_deform False), 6 bone deform; "
                       "hadap -Y, ekor di +Y")
    return arm_obj


def count_unweighted(obj):
    bad = 0
    for v in obj.data.vertices:
        if sum(g.weight for g in v.groups) < 1e-4:
            bad += 1
    return bad


def tent_weights(obj, chain):
    """Bobot fallback: interpolasi linear antar titik tengah bone (2 pengaruh)."""
    arm = obj.parent
    centers = []
    for name in chain:
        bone = arm.data.bones[name]
        centers.append((name, (bone.head_local.y + bone.tail_local.y) * 0.5))
    centers.sort(key=lambda c: c[1])
    groups = {}
    for name, _ in centers:
        groups[name] = obj.vertex_groups.get(name) or obj.vertex_groups.new(name=name)
    fixed = 0
    for v in obj.data.vertices:
        y = v.co.y
        if sum(g.weight for g in v.groups) > 1e-4:
            continue
        if y <= centers[0][1]:
            groups[centers[0][0]].add([v.index], 1.0, "REPLACE")
        elif y >= centers[-1][1]:
            groups[centers[-1][0]].add([v.index], 1.0, "REPLACE")
        else:
            for k in range(len(centers) - 1):
                y0 = centers[k][1]
                y1 = centers[k + 1][1]
                if y0 <= y <= y1:
                    t = (y - y0) / (y1 - y0)
                    groups[centers[k][0]].add([v.index], 1.0 - t, "REPLACE")
                    groups[centers[k + 1][0]].add([v.index], t, "REPLACE")
                    break
        fixed += 1
    return fixed


def assign_rigid(obj, bone_name, vert_range):
    vg = obj.vertex_groups.get(bone_name) or obj.vertex_groups.new(name=bone_name)
    idx = list(range(vert_range[0], vert_range[1]))
    for other in obj.vertex_groups:
        if other.name != bone_name:
            other.remove(idx)
    vg.add(idx, 1.0, "REPLACE")
    return len(idx)


def bind_armature(mesh_obj, arm_obj, ranges):
    bpy.ops.object.select_all(action="DESELECT")
    mesh_obj.select_set(True)
    arm_obj.select_set(True)
    bpy.context.view_layer.objects.active = arm_obj
    status = "auto"
    try:
        bpy.ops.object.parent_set(type="ARMATURE_AUTO")
    except RuntimeError as err:
        print("PERINGATAN automatic weights gagal:", err)
        status = "gagal-auto"
        try:
            bpy.ops.object.parent_set(type="ARMATURE_ENVELOPE")
            status = "envelope"
        except RuntimeError as err2:
            print("PERINGATAN envelope gagal:", err2)
            mesh_obj.parent = arm_obj
            mesh_obj.modifiers.new("Armature", "ARMATURE").object = arm_obj
            status = "manual"
    bpy.ops.object.select_all(action="DESELECT")

    bad_before = count_unweighted(mesh_obj)
    fixed = 0
    if bad_before:
        fixed = tent_weights(mesh_obj, CHAIN)
    n_l = assign_rigid(mesh_obj, "pectoral_L", ranges["pect_L"])
    n_r = assign_rigid(mesh_obj, "pectoral_R", ranges["pect_R"])
    bad_after = count_unweighted(mesh_obj)
    return status, bad_before, fixed, n_l + n_r, bad_after


# ---------------------------------------------------------------------------
# action renang
# ---------------------------------------------------------------------------

SWIM = [
    ("tail_02", 18.0, (0, 0, 1), 0.0),
    ("tail_01", 18.0, (0, 0, 1), 55.0),
    ("spine_02", 3.0, (0, 0, 1), 150.0),
    ("spine_01", 1.5, (0, 0, 1), 215.0),
    ("pectoral_L", 14.0, (0, 1, 0), 0.0),
    ("pectoral_R", 14.0, (0, 1, 0), 180.0),
]


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


def make_swim_action(arm_obj, act_name, n_frames, spec):
    bpy.ops.object.select_all(action="DESELECT")
    arm_obj.select_set(True)
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode="POSE")
    pbs = arm_obj.pose.bones
    for pb in pbs:
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)

    frames = list(range(1, n_frames + 2, 2))
    if frames[-1] != n_frames + 1:
        frames.append(n_frames + 1)
    n_keys = 0
    for f in frames:
        t = (f - 1) / float(n_frames)
        for bname, amp, axis, phase in spec:
            pb = pbs[bname]
            ang = radians(amp) * sin(2.0 * pi * t + radians(phase))
            ax = pb.bone.matrix_local.to_3x3().inverted() @ Vector(axis)
            ax.normalize()
            pb.rotation_quaternion = Quaternion(ax, ang)
            pb.keyframe_insert(data_path="rotation_quaternion", frame=f)
            n_keys += 1
    bpy.ops.object.mode_set(mode="OBJECT")

    ad = arm_obj.animation_data
    act = ad.action if ad else None
    if act is None:
        return None, 0, 0
    act.name = act_name
    act.use_fake_user = True
    try:
        act.use_frame_range = True
        act.frame_start = 1
        act.frame_end = n_frames
    except Exception:
        pass
    fcs = action_fcurves(act)
    for fc in fcs:
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"
    return act, n_keys, len(fcs)


# ---------------------------------------------------------------------------
# render
# ---------------------------------------------------------------------------


def render_previews(shots):
    scn = bpy.context.scene
    cam = scn.camera
    out_dir = os.path.join(repo_root(), "renders", "stills")
    os.makedirs(out_dir, exist_ok=True)
    scn.render.resolution_percentage = 50
    paths = []
    for name, loc, tgt, lens, frame in shots:
        scn.frame_set(frame)
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
    scn.frame_set(1)
    return paths


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main():
    L = TOTAL_LEN
    scn = release_and_wipe()
    scn, engine = setup_scene(scn, 20)
    log("MCP - Blender siap; scene fish-damselfish diset (EEVEE, 1920x1080, 24 fps, Standard)")

    mats = {}
    for key in SLOT_ORDER:
        name, hexcol, rough, spec = SLOT_MAT[key]
        mats[key] = material(name, hexcol, roughness=rough, spec=spec)

    root = bpy.data.collections.new("ENV_fish")
    scn.collection.children.link(root)

    ctl = bpy.data.objects.new("CTL_fish", None)
    ctl.empty_display_type = "PLAIN_AXES"
    ctl.empty_display_size = 0.05
    ctl["asset"] = "ENV_fish_damselfish"
    ctl["note"] = "pivot induk; origin di tengah badan, z 0 = garis tengah"
    ctl["facing"] = "-Y"
    root.objects.link(ctl)

    V, F, FM, FS = [], [], [], []
    ranges = {}

    v0 = len(V)
    build_body(V, F, FM, FS)
    ranges["body"] = (v0, len(V))

    v0 = len(V)
    build_eyes(V, F, FM, FS)
    ranges["eyes"] = (v0, len(V))

    v0 = len(V)
    build_dorsal(V, F, FM, FS)
    ranges["dorsal"] = (v0, len(V))

    v0 = len(V)
    build_anal(V, F, FM, FS)
    ranges["anal"] = (v0, len(V))

    v0 = len(V)
    build_pelvic(V, F, FM, FS)
    ranges["pelvic"] = (v0, len(V))

    v0 = len(V)
    build_pectoral(1.0, V, F, FM, FS)
    ranges["pect_L"] = (v0, len(V))

    v0 = len(V)
    build_pectoral(-1.0, V, F, FM, FS)
    ranges["pect_R"] = (v0, len(V))

    v0 = len(V)
    build_caudal(V, F, FM, FS)
    ranges["caudal"] = (v0, len(V))

    mesh_obj = new_mesh_object("ENV_fish_damselfish", V, F, FM, FS,
                               [mats[k] for k in SLOT_ORDER], root)
    mesh_obj.parent = ctl
    mesh_obj.matrix_parent_inverse = ctl.matrix_world.inverted()
    mesh_obj["asset"] = "ENV_fish_damselfish"
    mesh_obj["facing"] = "-Y"
    mesh_obj["note"] = "badan + sirip + mata satu mesh; 5 material palette §2"

    log("MODEL - damselfish: %d vert, %d muka, panjang %.3f m"
        % (len(V), len(F), max(v.y for v in V) - min(v.y for v in V)))

    arm_obj = build_rig(root, ctl)
    status, bad_before, fixed, n_pect, bad_after = bind_armature(
        mesh_obj, arm_obj, ranges)
    log("RIG - CHR_fish_damselfish_rig %d bone; bind=%s, tanpa bobot %d -> %d "
        "(fallback %d), sirip dada kaku %d"
        % (len(arm_obj.data.bones), status, bad_before, bad_after, fixed, n_pect))

    act, n_keys, n_fc = make_swim_action(arm_obj, "ENV_act_damselfish_swim", 20, SWIM)
    log("ANIM - ENV_act_damselfish_swim 1-20 loop: %d key, %d fcurve" % (n_keys, n_fc))

    setup_preview(scn, L)

    bpy.context.view_layer.update()
    bb = [mesh_obj.matrix_world @ Vector(c) for c in mesh_obj.bound_box]
    xs = [p.x for p in bb]
    ys = [p.y for p in bb]
    zs = [p.z for p in bb]
    print("=== RINGKASAN ENV_fish_damselfish ===")
    print("verts=%d faces=%d panjang=%.4f m lebar=%.4f tinggi=%.4f"
          % (len(mesh_obj.data.vertices), len(mesh_obj.data.polygons),
             max(ys) - min(ys), max(xs) - min(xs), max(zs) - min(zs)))
    print("bone:", [b.name for b in arm_obj.data.bones])
    print("bone deform:", [b.name for b in arm_obj.data.bones if b.use_deform])
    print("material:", [m.name for m in mesh_obj.data.materials])
    print("action:", act.name if act else None,
          "range:", tuple(act.frame_range) if act else None)
    print("engine=%s vt=%s res=%dx%d fps=%d frame=%d"
          % (engine, scn.view_settings.view_transform, scn.render.resolution_x,
             scn.render.resolution_y, scn.render.fps, scn.frame_current))

    target = os.path.join(repo_root(), "assets", "env", "fish-damselfish.blend")
    bpy.ops.wm.save_as_mainfile(filepath=target, check_existing=False)
    print("saved:", target, "%.1f KB" % (os.path.getsize(target) / 1024.0))
    log("MODEL - fish-damselfish.blend disimpan (%.0f KB)"
        % (os.path.getsize(target) / 1024.0))

    shots = [
        ("damselfish-rig_preview-01", (0.276, -0.180, 0.057), (0.0, 0.001, 0.0),
         55.0, 6),
        ("damselfish-rig_preview-02", (-0.216, 0.200, 0.109), (0.0, 0.007, 0.0),
         55.0, 18),
    ]
    paths = render_previews(shots)
    log("VERIFY - damselfish-rig_preview-01 (frame 6) / -02 (frame 18) 50%%: %s"
        % ", ".join(os.path.basename(p) for p in paths))


if __name__ == "__main__":
    main()

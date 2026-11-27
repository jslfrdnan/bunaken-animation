"""build-divegear-v002.py — peralatan snorkel Nara v002 (HEADLESS).

    & "D:\\Blender Foundation\\Blender 5.2\\blender.exe" -b -P scripts/build-divegear-v002.py

Hasil: assets/props/divegear_v002.blend
  PRP_divegear_mask      lensa dua + skirt + strap karet yang MENGIKAT kepala
  PRP_divegear_snorkel   tabung 0,33 m (v001 0,468 m), lebih tipis, tekuk ke
                         belakang, mulut tetap di origin
  PRP_divegear_fin_L/R   foot-pocket terbuka yang membungkus telapak,
                         origin di TUMIT (0,0,0), bilah ke -Y

Acuan: storyboard/refs/ref-divegear_v001.png (bentuk & warna saja).
Material palette PROJECT.md §2, tanpa tekstur.
"""

import bpy
import bmesh
import datetime
import math
import os
from math import cos, pi, sin
from mathutils import Vector

ROOT = r"D:/Tugas Semester 5/Grafika Komputer/Project-Animasi"
DST = ROOT + "/assets/props/divegear_v002.blend"
LOGPATH = ROOT + "/renders/logs/technical.log"
STILLS = ROOT + "/renders/stills"

HEX_BLACK = "#2E383A"
HEX_RUBBER = "#8A8F8C"
HEX_LENS = "#0F5C63"
HEX_GROUND = "#2E383A"

SEG_TUBE = 12
SEG_RIM = 10
SEG_SKIRT = 32
SEG_LENS = 20
SEG_BLADE = 16
SEG_POCKET = 18

STAGE = {
    "mask": Vector((-0.42, 0.06, 0.115)),
    "snorkel": Vector((0.02, 0.05, 0.0)),
    "fin_L": Vector((0.28, 0.30, 0.0)),
    "fin_R": Vector((0.56, 0.30, 0.0)),
}


def log(phase, line):
    os.makedirs(os.path.dirname(LOGPATH), exist_ok=True)
    stamp = datetime.datetime.now().strftime("%H:%M")
    with open(LOGPATH, "a", encoding="utf-8") as fh:
        fh.write("[%s] %s - %s\n" % (stamp, phase, line))
    print("[log]", phase, line)


# ------------------------------------------------------------------ helpers ---


def srgb(hexstr):
    h = hexstr.lstrip("#")
    v = [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]

    def lin(u):
        return u / 12.92 if u <= 0.04045 else ((u + 0.055) / 1.055) ** 2.4

    return tuple(lin(c) for c in v) + (1.0,)


def superellipse(rx, ry, t, exp):
    ct, st = cos(t), sin(t)
    x = rx * math.copysign(abs(ct) ** (2.0 / exp), ct)
    y = ry * math.copysign(abs(st) ** (2.0 / exp), st)
    return x, y


def ring(center, rx, rz, seg, exp=2.0):
    cx, cy, cz = center
    out = []
    for i in range(seg):
        a, b = superellipse(rx, rz, 2.0 * pi * i / seg, exp)
        out.append(Vector((cx + a, cy, cz + b)))
    return out


def loft(V, F, FM, FS, rings, mat, smooth=True, cap_a=True, cap_b=True,
         close_loop=False):
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
    if close_loop:
        a, b = starts[-1], starts[0]
        for i in range(n):
            i2 = (i + 1) % n
            F.append((a + i, a + i2, b + i2, b + i))
            FM.append(mat)
            FS.append(smooth)
        cap_a = cap_b = False
    if cap_a:
        F.append(tuple(starts[0] + i for i in range(n - 1, -1, -1)))
        FM.append(mat)
        FS.append(False)
    if cap_b:
        F.append(tuple(starts[-1] + i for i in range(n)))
        FM.append(mat)
        FS.append(False)
    return starts


def sweep(pts, radii, seg, up=Vector((0, 0, 1)), exp=2.0, closed=False):
    rings = []
    n = len(pts)
    for i, p in enumerate(pts):
        if closed:
            t = (pts[(i + 1) % n] - pts[i - 1])
        elif i == 0:
            t = pts[1] - pts[0]
        elif i == n - 1:
            t = pts[-1] - pts[-2]
        else:
            t = pts[i + 1] - pts[i - 1]
        t = t.normalized()
        side = t.cross(up)
        if side.length < 1e-6:
            alt = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((0, 1, 0))
            side = t.cross(alt)
        side.normalize()
        up2 = side.cross(t).normalized()
        rx, ry = radii[i]
        rings.append([p + side * superellipse(rx, ry, 2.0 * pi * k / seg, exp)[0]
                      + up2 * superellipse(rx, ry, 2.0 * pi * k / seg, exp)[1]
                      for k in range(seg)])
    return rings


def ellipsoid(V, F, FM, FS, center, radii, seg=16, rings_n=8, mat=0, smooth=True):
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


def material(name, hexcol, roughness=0.6, metallic=0.0, ior=1.45, spec=0.5):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.use_backface_culling = False
    col = srgb(hexcol)
    mat.diffuse_color = col
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = col
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    if "IOR" in bsdf.inputs:
        bsdf.inputs["IOR"].default_value = ior
    spec_in = bsdf.inputs.get("Specular IOR Level") or bsdf.inputs.get("Specular")
    if spec_in is not None:
        spec_in.default_value = spec
    return mat


# -------------------------------------------------------------------- masker ---


def build_mask(mats, col):
    V, F, FM, FS = [], [], [], []
    M_BLACK, M_RUBBER, M_LENS = 0, 1, 2

    # skirt: dari frame ke arah wajah
    skirt = [
        (0.004, 0.076, 0.038),
        (0.016, 0.081, 0.041),
        (0.030, 0.083, 0.043),
        (0.046, 0.084, 0.044),
    ]
    loft(V, F, FM, FS,
         [ring((0.0, y, 0.004), rx, rz, SEG_SKIRT, 2.3) for (y, rx, rz) in skirt],
         mat=M_BLACK, cap_a=False, cap_b=False)

    # kantong hidung
    ellipsoid(V, F, FM, FS, (0.0, 0.010, -0.032), (0.030, 0.028, 0.021),
              seg=18, rings_n=8, mat=M_BLACK)

    for sx in (-1.0, 1.0):
        cx = sx * 0.0425
        ellipsoid(V, F, FM, FS, (cx, -0.008, 0.008), (0.0355, 0.010, 0.028),
                  seg=SEG_LENS, rings_n=7, mat=M_LENS)
        path = []
        n = 28
        for i in range(n):
            a = 2.0 * pi * i / n
            x, z = superellipse(0.0405, 0.0320, a, 2.2)
            path.append(Vector((cx + x, -0.010, 0.008 + z)))
        rings = sweep(path, [(0.0072, 0.0072)] * n, SEG_RIM,
                      up=Vector((0, 1, 0)), closed=True)
        loft(V, F, FM, FS, rings, mat=M_BLACK, close_loop=True)

    # jembatan hidung
    loft(V, F, FM, FS,
         [ring((0.0, -0.012, 0.008), 0.014, 0.011, 14, 2.6),
          ring((0.0, 0.004, 0.008), 0.017, 0.013, 14, 2.6)],
         mat=M_BLACK)

    # ---- strap: satu pita karet menerus dari pelipis kiri ke pelipis kanan ----
    # kepala (relatif origin masker): pusat y +0,095, belakang y +0,188,
    # setengah lebar x 0,079-0,086 (termasuk cangkang rambut).
    strap = [
        (-0.088, 0.026, 0.004),
        (-0.093, 0.050, 0.002),
        (-0.090, 0.082, 0.000),
        (-0.074, 0.120, -0.002),
        (-0.044, 0.158, -0.004),
        (0.000, 0.178, -0.006),
        (0.044, 0.158, -0.004),
        (0.074, 0.120, -0.002),
        (0.090, 0.082, 0.000),
        (0.093, 0.050, 0.002),
        (0.088, 0.026, 0.004),
    ]
    pts = [Vector(p) for p in strap]
    rings = sweep(pts, [(0.0034, 0.0170)] * len(pts), 10, up=Vector((0, 0, 1)))
    loft(V, F, FM, FS, rings, mat=M_RUBBER)

    # gesper plastik di kedua pelipis
    for sx in (-1.0, 1.0):
        loft(V, F, FM, FS,
             [ring((sx * 0.090, 0.020, 0.004), 0.011, 0.019, 12, 3.0),
              ring((sx * 0.090, 0.038, 0.004), 0.010, 0.018, 12, 3.0)],
             mat=M_BLACK)
    # penjepit snorkel di strap kiri
    loft(V, F, FM, FS,
         [ring((-0.092, 0.070, 0.004), 0.008, 0.011, 10, 2.6),
          ring((-0.100, 0.070, 0.004), 0.008, 0.011, 10, 2.6)],
         mat=M_BLACK)

    obj = new_mesh_object("PRP_divegear_mask", V, F, FM, FS,
                          [mats["black"], mats["rubber"], mats["lens"]], col)
    obj.location = STAGE["mask"]
    obj["part"] = "mask"
    obj["pivot"] = "tengah lensa (strap mengikat kepala)"
    obj["facing"] = "-Y"
    obj["size_target_m"] = "0.18 x 0.10, strap keliling 0.19"
    return obj


# ------------------------------------------------------------------- snorkel ---

SNORKEL_SCALE = 0.33 / 0.468   # v002: total 0,33 m


def build_snorkel(mats, col):
    V, F, FM, FS = [], [], [], []
    M_BLACK, M_RUBBER = 0, 1
    k = SNORKEL_SCALE

    def z(v):
        return v * k

    # tabung utama: lebih tipis, tekuk ke belakang (y naik di ujung atas)
    tube_pts, tube_r = [], []
    n_main = 14
    for i in range(n_main):
        t = i / (n_main - 1.0)
        zz = z(0.100 + t * 0.305)
        x = 0.005 * sin(t * pi * 0.85)
        y = z(0.036 + 0.004 * t) + 0.048 * (t ** 2.2)
        tube_pts.append(Vector((x, y, zz)))
        tube_r.append((0.0104, 0.0104))
    loft(V, F, FM, FS,
         sweep(tube_pts, tube_r, SEG_TUBE, up=Vector((0, 1, 0))), mat=M_BLACK)

    # bagian bergelombang
    corr_pts, corr_r = [], []
    n_c = 24
    for i in range(n_c):
        t = i / (n_c - 1.0)
        zz = z(0.032 + t * 0.076)
        x = 0.002 * sin(t * pi)
        y = z(0.034 + 0.002 * t)
        bulge = 0.0132 if (i % 2 == 0) else 0.0108
        corr_pts.append(Vector((x, y, zz)))
        corr_r.append((bulge, bulge))
    loft(V, F, FM, FS,
         sweep(corr_pts, corr_r, SEG_TUBE, up=Vector((0, 1, 0))), mat=M_BLACK)

    # sambungan ke mouthpiece
    elbow = [
        Vector((0.0, 0.034, z(0.036))),
        Vector((0.0, 0.032, z(0.026))),
        Vector((0.0, 0.024, z(0.014))),
        Vector((0.0, 0.012, 0.006)),
    ]
    loft(V, F, FM, FS,
         sweep(elbow, [(0.0112, 0.0112)] * len(elbow), SEG_TUBE,
               up=Vector((0, 0, 1))), mat=M_RUBBER)

    # mouthpiece (origin di ujung mulut)
    mouth = [
        (0.010, 0.0125, 0.0115),
        (0.000, 0.0138, 0.0126),
        (-0.012, 0.0134, 0.0116),
        (-0.024, 0.0103, 0.0086),
        (-0.032, 0.0054, 0.0050),
    ]
    loft(V, F, FM, FS,
         [ring((0.0, y, 0.004), rx, rz, SEG_TUBE, 2.4) for (y, rx, rz) in mouth],
         mat=M_RUBBER)

    # kepala atas: penutup ramping, menyambung tepat di ujung tabung
    head = [
        (0.2856, 0.0104, 0.0104),
        (0.2920, 0.0150, 0.0110),
        (0.3000, 0.0172, 0.0104),
        (0.3100, 0.0160, 0.0086),
        (0.3180, 0.0110, 0.0062),
    ]
    loft(V, F, FM, FS,
         [ring((0.005, 0.076 + (zz - 0.2856) * 0.15, zz), rx, rz, 16, 2.8)
          for (zz, rx, rz) in head],
         mat=M_BLACK)
    # gerigi pelindung percikan
    for i in range(4):
        zz = 0.2995 + i * 0.0042
        yy = 0.076 + (zz - 0.2856) * 0.15
        loft(V, F, FM, FS,
             [ring((0.005, yy, zz), 0.0150, 0.0030, 8, 2.6),
              ring((0.005, yy, zz + 0.0022), 0.0140, 0.0026, 8, 2.6)],
             mat=M_BLACK)
    # klip tabung ke strap masker (z 0,135)
    loft(V, F, FM, FS,
         [ring((-0.002, 0.058, 0.135), 0.0085, 0.0115, 10, 2.6),
          ring((-0.002, 0.042, 0.135), 0.0085, 0.0115, 10, 2.6)],
         mat=M_BLACK)

    obj = new_mesh_object("PRP_divegear_snorkel", V, F, FM, FS,
                          [mats["black"], mats["rubber"]], col)
    obj.location = STAGE["snorkel"]
    obj["part"] = "snorkel"
    obj["pivot"] = "ujung mulut (mouthpiece) di origin"
    obj["facing"] = "-Y"
    obj["size_target_m"] = "0.33 panjang, tabung 0,021 tebal"
    return obj


# ---------------------------------------------------------------------- fin ---


def fin_geometry(mats, sx, col):
    """Foot-pocket membungkus telapak, origin di tumit (0,0,0), bilah ke -Y."""
    V, F, FM, FS = [], [], [], []
    M_BLACK, M_RUBBER = 0, 1

    def mir(p):
        return Vector((sx * p[0], p[1], p[2]))

    # --- pocket: sol + dinding samping + ujung kaki terbuka ----------------
    # (y, cz, rx, rz)  y=0 tumit, y=-0,172 bukaan jari
    pocket = [
        (0.012, 0.020, 0.012, 0.012),
        (0.002, 0.032, 0.032, 0.026),
        (-0.035, 0.045, 0.047, 0.038),
        (-0.080, 0.049, 0.052, 0.041),
        (-0.125, 0.047, 0.051, 0.040),
        (-0.160, 0.043, 0.048, 0.036),
        (-0.172, 0.041, 0.045, 0.034),
    ]
    rings = []
    for (y, cz, rx, rz) in pocket:
        rings.append([mir(p) for p in ring((0.0, y, cz), rx, rz, SEG_POCKET, 2.5)])
    loft(V, F, FM, FS, rings, mat=M_BLACK, cap_a=True, cap_b=False)
    # bibir karet di bukaan
    loft(V, F, FM, FS,
         [rings[-1],
          [mir(p) for p in ring((0.0, -0.178, 0.041), 0.047, 0.035, SEG_POCKET, 2.5)]],
         mat=M_RUBBER, cap_a=False, cap_b=False)

    # --- strap pergelangan: menempel di tumit, bukan cincin melayang ------
    path = []
    n = 22
    for i in range(n):
        a = 2.0 * pi * i / n
        x, z2 = superellipse(0.050, 0.030, a, 2.3)
        path.append(mir((x, -0.004, 0.050 + z2)))
    rings = sweep(path, [(0.0090, 0.0034)] * n, 8, up=Vector((0, 1, 0)),
                  closed=True)
    loft(V, F, FM, FS, rings, mat=M_RUBBER, close_loop=True)

    # --- bilah -------------------------------------------------------------
    blade = [
        (-0.172, 0.048, 0.0100, 0.034),
        (-0.240, 0.070, 0.0090, 0.035),
        (-0.320, 0.090, 0.0080, 0.037),
        (-0.400, 0.104, 0.0070, 0.041),
        (-0.480, 0.112, 0.0064, 0.047),
        (-0.545, 0.108, 0.0058, 0.054),
        (-0.585, 0.088, 0.0052, 0.061),
        (-0.605, 0.055, 0.0048, 0.066),
    ]
    rings = []
    for (y, hw, th, cz) in blade:
        rings.append([mir(p) for p in ring((0.0, y, cz), hw, th, SEG_BLADE, 3.2)])
    loft(V, F, FM, FS, rings, mat=M_BLACK, cap_a=False, cap_b=True)

    # --- rusuk samping + punggung tengah -----------------------------------
    rails = [(-0.200, 0.060, 0.035), (-0.300, 0.084, 0.037),
             (-0.400, 0.102, 0.041), (-0.500, 0.111, 0.050),
             (-0.575, 0.096, 0.058)]
    for side in (-1.0, 1.0):
        path = [mir((side * hw * 0.86, y, cz)) for (y, hw, cz) in rails]
        rings = sweep(path, [(0.0085, 0.0095)] * len(path), 8, up=Vector((0, 0, 1)))
        loft(V, F, FM, FS, rings, mat=M_BLACK)
    path = [mir((0.0, y, cz)) for (y, hw, th, cz) in blade[:6]]
    rings = sweep(path, [(0.0095, 0.0085)] * len(path), 8, up=Vector((0, 0, 1)))
    loft(V, F, FM, FS, rings, mat=M_BLACK)

    name = "PRP_divegear_fin_L" if sx > 0 else "PRP_divegear_fin_R"
    obj = new_mesh_object(name, V, F, FM, FS,
                          [mats["black"], mats["rubber"]], col)
    obj.location = STAGE["fin_L" if sx > 0 else "fin_R"]
    obj["part"] = "fin-L" if sx > 0 else "fin-R"
    obj["pivot"] = "tumit di origin (0,0,0); bilah ke -Y"
    obj["facing"] = "-Y"
    obj["size_target_m"] = "0.605 panjang"
    return obj


# --------------------------------------------------------- scene & preview ---


def set_engine(scn):
    for cand in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scn.render.engine = cand
            return cand
        except TypeError:
            pass
    return scn.render.engine


def setup_scene(scn):
    scn.name = "divegear"
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
        scn.eevee.taa_render_samples = 32
    except AttributeError:
        pass
    scn.render.image_settings.file_format = "PNG"
    scn.render.image_settings.color_mode = "RGBA"
    scn.render.film_transparent = False
    scn["asset"] = "divegear_v002"
    return scn, engine


def setup_preview(scn):
    prev = bpy.data.collections.new("PREVIEW")
    scn.collection.children.link(prev)

    ground_mat = material("MAT_preview_divegear-ground", HEX_GROUND, roughness=0.95,
                          spec=0.1)
    mesh = bpy.data.meshes.new("PREVIEW_ground")
    mesh.from_pydata([(-6, -6, -0.002), (6, -6, -0.002), (6, 6, -0.002),
                      (-6, 6, -0.002)], [], [(0, 1, 2, 3)])
    mesh.materials.append(ground_mat)
    mesh.update()
    prev.objects.link(bpy.data.objects.new("PREVIEW_ground", mesh))

    cam_data = bpy.data.cameras.new("CAM_preview")
    cam_data.lens = 50.0
    cam = bpy.data.objects.new("CAM_preview", cam_data)
    prev.objects.link(cam)
    cam.location = (0.02, -1.95, 0.62)
    cam.rotation_euler = (Vector((0.02, 0.0, 0.13)) - cam.location).normalized(
    ).to_track_quat("-Z", "Y").to_euler()
    scn.camera = cam

    key = bpy.data.objects.new("LGT_preview-key",
                               bpy.data.lights.new("LGT_preview-key", "SUN"))
    prev.objects.link(key)
    key.data.energy = 3.2
    key.data.angle = math.radians(22)
    key.rotation_euler = (math.radians(52), 0.0, math.radians(28))

    fill = bpy.data.objects.new("LGT_preview-fill",
                                bpy.data.lights.new("LGT_preview-fill", "AREA"))
    prev.objects.link(fill)
    fill.data.energy = 160.0
    fill.data.size = 2.2
    fill.location = (-1.6, -1.8, 1.3)
    fill.rotation_euler = (Vector((0, 0, 0.15)) - fill.location).normalized(
    ).to_track_quat("-Z", "Y").to_euler()

    rim = bpy.data.objects.new("LGT_preview-rim",
                               bpy.data.lights.new("LGT_preview-rim", "AREA"))
    prev.objects.link(rim)
    rim.data.energy = 210.0
    rim.data.size = 2.0
    rim.location = (1.7, 1.5, 1.4)
    rim.rotation_euler = (Vector((0.1, 0.0, 0.1)) - rim.location).normalized(
    ).to_track_quat("-Z", "Y").to_euler()

    world = bpy.data.worlds.new("WLD_divegear-preview")
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.075, 0.090, 0.098, 1.0)
    bg.inputs["Strength"].default_value = 1.0
    scn.world = world


def release_and_wipe():
    tmp = ROOT + "/renders/tmp/_wipe.blend"
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
    out_dir = STILLS
    os.makedirs(out_dir, exist_ok=True)
    shots = [
        ("divegear-v002_preview-01", (0.0, -1.95, 0.62), (0.03, 0.0, 0.13), 50.0),
        ("divegear-v002_preview-02", (-1.35, 1.15, 1.05), (0.03, 0.05, 0.10), 44.0),
        ("divegear-v002_preview-03", (0.30, -0.75, 0.30), (0.42, 0.20, 0.04), 60.0),
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

    mats = {
        "black": material("MAT_divegear_black", HEX_BLACK, roughness=0.68, spec=0.10),
        "rubber": material("MAT_divegear_rubber", HEX_RUBBER, roughness=0.92, spec=0.14),
        "lens": material("MAT_divegear_lens", HEX_LENS, roughness=0.10, ior=1.5, spec=0.5),
    }

    root = bpy.data.collections.new("PRP_divegear")
    scn.collection.children.link(root)
    ctl = bpy.data.objects.new("CTL_divegear", None)
    ctl.empty_display_type = "PLAIN_AXES"
    ctl.empty_display_size = 0.25
    root.objects.link(ctl)
    ctl["asset"] = "PRP_divegear"
    ctl["note"] = "v002: strap mengikat kepala, snorkel 0,33 m, fin origin di tumit"

    mask = build_mask(mats, root)
    snorkel = build_snorkel(mats, root)
    fin_l = fin_geometry(mats, 1.0, root)
    fin_r = fin_geometry(mats, -1.0, root)
    for obj in (mask, snorkel, fin_l, fin_r):
        obj.parent = ctl
        obj.matrix_parent_inverse = ctl.matrix_world.inverted()

    setup_preview(scn)

    print("=== RINGKASAN PRP_divegear v002 ===")
    for obj in (mask, snorkel, fin_l, fin_r):
        d = obj.dimensions
        print("%-26s verts=%5d dims=(%.3f, %.3f, %.3f) loc=(%.2f, %.2f, %.2f)"
              % (obj.name, len(obj.data.vertices), d.x, d.y, d.z,
                 obj.location.x, obj.location.y, obj.location.z))
    print("snorkel tinggi %.3f m (target 0.330)" % snorkel.dimensions.z)
    print("engine=%s res=%dx%d fps=%d" % (engine, scn.render.resolution_x,
                                          scn.render.resolution_y, scn.render.fps))

    bpy.ops.wm.save_as_mainfile(filepath=DST, check_existing=False)
    print("saved:", DST, "%.1f KB" % (os.path.getsize(DST) / 1024.0))
    log("MODEL", "divegear_v002: strap masker mengikat kepala, snorkel %.3f m, "
                 "fin origin tumit + foot-pocket, disimpan" % snorkel.dimensions.z)
    paths = render_previews()
    log("VERIFY", "divegear_v002 preview 50%%: %s"
        % ", ".join(os.path.basename(p) for p in paths))


if __name__ == "__main__":
    main()

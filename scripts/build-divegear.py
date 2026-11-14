"""
Membangun peralatan snorkel (masker, snorkel, sepasang fin) — blockout bersih.

Hasil: assets/props/divegear.blend
  scene "divegear"
    koleksi PRP_divegear
      +-- empty CTL_divegear          pivot induk, di origin dunia
      +-- PRP_divegear_mask           masker dua lensa + strap
      +-- PRP_divegear_snorkel        tabung + bagian bergelombang + mouthpiece
      +-- PRP_divegear_fin_L          fin kiri  (bilah lebar)
      +-- PRP_divegear_fin_R          fin kanan (cermin fin kiri)
    koleksi PREVIEW                   kamera + lampu + lantai (bukan bagian aset)

Acuan bentuk & warna: storyboard/refs/ref-divegear_v001.png (produk hitam di
latar putih: satu fin, masker dua lensa, snorkel dengan bagian bergelombang).
Foto hanya dibaca sebagai acuan proporsi/siluet — tidak dipakai sebagai
tekstur, latar, atau image plane. Skala mengikuti brief Director.

Skala nyata (meter):
  masker   ~0,18 lebar x 0,10 tinggi (tebal strap ke belakang ~0,20)
  snorkel  ~0,45 panjang total
  fin      ~0,60 panjang, bilah lebar ~0,23

Pivot (origin objek):
  masker  di tengah strap: pusat lensa, sumbu X/Z sama dengan lingkaran strap
  snorkel di ujung mulut (mouthpiece) — tabung tumbuh ke atas (+Z)
  fin     di pangkal kaki (tumit) di z 0, bilah menghadap -Y

Material (palette PROJECT.md §2 + netral 14 Nov 2026, tanpa tekstur):
  MAT_divegear_black  #2E383A  frame, tabung, bilah fin
  MAT_divegear_rubber #8A8F8C  skirt karet, strap, mouthpiece, gelang kaki
  MAT_divegear_lens   #0F5C63  kaca lensa teal gelap

Ketiga bagian diletakkan terpisah di sumbu X supaya bisa dipratinjau sekaligus.
Set location objek ke (0, 0, 0) setelah di-append bila ingin menempel di origin.

Skrip IDEMPOTEN terhadap datablock miliknya dan MENYIMPAN file di akhir.
Tidak memakai open_mainfile / read_factory_settings / read_homefile: file aktif
dilepas lewat save_as_mainfile ke renders/tmp/_wipe.blend dulu.
"""

import bpy
import bmesh
import os
import math
import datetime
from math import cos, sin, pi, copysign
from mathutils import Vector

# ---------------------------------------------------------------------------
# konstanta
# ---------------------------------------------------------------------------

HEX_BLACK = "#2E383A"    # netral gelap, palette §2 (14 Nov 2026)
HEX_RUBBER = "#8A8F8C"   # abu kain, palette §2
HEX_LENS = "#0F5C63"     # teal dalam, palette §2
HEX_GROUND = "#2E383A"

SEG_TUBE = 12
SEG_RIM = 10
SEG_SKIRT = 32
SEG_LENS = 20
SEG_BLADE = 16
SEG_POCKET = 18

OWN = ("PRP_divegear", "CTL_divegear", "MAT_divegear_", "MAT_preview_divegear",
       "CAM_preview", "LGT_preview", "PREVIEW", "WLD_divegear")

# posisi panggung pratinjau (bukan bagian aset)
STAGE = {
    "mask": Vector((-0.42, 0.06, 0.115)),
    "snorkel": Vector((0.02, 0.05, 0.0)),
    "fin_L": Vector((0.28, 0.16, 0.0)),
    "fin_R": Vector((0.54, 0.16, 0.0)),
}

# ---------------------------------------------------------------------------
# utilitas
# ---------------------------------------------------------------------------


def srgb(hexstr):
    """hex sRGB -> linear RGBA (Base Color Blender linear)."""
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


def ring(center, rx, rz, seg, exp=2.0):
    """Cincin pada bidang XZ (normal -Y), dipakai lensa/frame masker."""
    cx, cy, cz = center
    out = []
    for i in range(seg):
        a, b = superellipse(rx, rz, 2.0 * pi * i / seg, exp)
        out.append(Vector((cx + a, cy, cz + b)))
    return out


def loft(V, F, FM, FS, rings, mat, smooth=True, cap_a=True, cap_b=True,
         close_loop=False):
    """Sambung daftar cincin (jumlah titik sama) menjadi permukaan."""
    starts = []
    for r in rings:
        starts.append(len(V))
        for p in r:
            V.append(Vector(p))
    n = len(rings[0])
    pairs = list(range(len(rings) - 1))
    for k in pairs:
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
    """Cincin penampang bulat/elips mengikuti jalur 3D."""
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
        pts_ring = []
        for k in range(seg):
            a, b = superellipse(rx, ry, 2.0 * pi * k / seg, exp)
            pts_ring.append(p + side * a + up2 * b)
        rings.append(pts_ring)
    return rings


def ellipsoid(V, F, FM, FS, center, radii, seg=16, rings_n=8, mat=0,
              smooth=True):
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


# ---------------------------------------------------------------------------
# masker
# ---------------------------------------------------------------------------


def build_mask(mats, col):
    V, F, FM, FS = [], [], [], []
    M_BLACK, M_RUBBER, M_LENS = 0, 1, 2

    # --- skirt karet: dari depan (menutup frame) melebar ke arah wajah ------
    skirt = [
        (0.004, 0.076, 0.038),
        (0.016, 0.081, 0.041),
        (0.030, 0.083, 0.043),
        (0.046, 0.084, 0.044),
    ]
    loft(V, F, FM, FS,
         [ring((0.0, y, 0.004), rx, rz, SEG_SKIRT, 2.3)
          for (y, rx, rz) in skirt],
         mat=M_BLACK, cap_a=False, cap_b=False)

    # --- kantong hidung (bulge bawah tengah) --------------------------------
    ellipsoid(V, F, FM, FS, (0.0, 0.010, -0.032), (0.030, 0.028, 0.021),
              seg=18, rings_n=8, mat=M_BLACK)

    # --- dua lensa + frame --------------------------------------------------
    for sx in (-1.0, 1.0):
        cx = sx * 0.0425
        # kaca lensa: cembung tipis, menghadap -Y
        ellipsoid(V, F, FM, FS, (cx, -0.008, 0.008), (0.0355, 0.010, 0.028),
                  seg=SEG_LENS, rings_n=7, mat=M_LENS)
        # frame: tabung mengelilingi lensa
        path = []
        n = 28
        for i in range(n):
            a = 2.0 * pi * i / n
            x, z = superellipse(0.0405, 0.0320, a, 2.2)
            path.append(Vector((cx + x, -0.010, 0.008 + z)))
        rings = sweep(path, [(0.0072, 0.0072)] * n, SEG_RIM,
                      up=Vector((0, 1, 0)), closed=True)
        loft(V, F, FM, FS, rings, mat=M_BLACK, close_loop=True)

    # --- jembatan hidung ----------------------------------------------------
    loft(V, F, FM, FS,
         [ring((0.0, -0.012, 0.008), 0.014, 0.011, 14, 2.6),
          ring((0.0, 0.004, 0.008), 0.017, 0.013, 14, 2.6)],
         mat=M_BLACK)

    # --- strap karet: dua pita dari sisi frame ke belakang ------------------
    for sx in (-1.0, 1.0):
        path = [
            Vector((sx * 0.084, 0.030, 0.006)),
            Vector((sx * 0.086, 0.072, 0.002)),
            Vector((sx * 0.072, 0.122, -0.004)),
            Vector((sx * 0.042, 0.162, -0.010)),
            Vector((sx * 0.001, 0.180, -0.014)),
        ]
        rings = sweep(path, [(0.0215, 0.0040)] * len(path), 8,
                      up=Vector((0, 0, 1)))
        loft(V, F, FM, FS, rings, mat=M_BLACK)
        # gesper: tabung pendek di sisi frame
        loft(V, F, FM, FS,
             [ring((sx * 0.088, 0.022, 0.006), 0.012, 0.014, 10, 3.0),
              ring((sx * 0.088, 0.044, 0.006), 0.011, 0.013, 10, 3.0)],
             mat=M_BLACK)

    obj = new_mesh_object("PRP_divegear_mask", V, F, FM, FS,
                          [mats["black"], mats["rubber"], mats["lens"]], col)
    obj.location = STAGE["mask"]
    obj["part"] = "mask"
    obj["pivot"] = "tengah strap (pusat lensa)"
    obj["facing"] = "-Y"
    obj["size_target_m"] = "0.18 x 0.10"
    return obj


# ---------------------------------------------------------------------------
# snorkel
# ---------------------------------------------------------------------------


def build_snorkel(mats, col):
    V, F, FM, FS = [], [], [], []
    M_BLACK, M_RUBBER = 0, 1

    # --- tabung utama: sedikit melengkung, dari z 0,10 ke 0,405 -------------
    tube_pts, tube_r = [], []
    n_main = 12
    for i in range(n_main):
        t = i / (n_main - 1.0)
        z = 0.100 + t * 0.305
        x = 0.006 * sin(t * pi * 0.85)
        y = 0.036 + 0.004 * t
        tube_pts.append(Vector((x, y, z)))
        tube_r.append((0.0135, 0.0135))
    loft(V, F, FM, FS,
         sweep(tube_pts, tube_r, SEG_TUBE, up=Vector((0, 1, 0))),
         mat=M_BLACK)

    # --- bagian bergelombang (corrugated) z 0,030 .. 0,105 -----------------
    corr_pts, corr_r = [], []
    n_c = 26
    for i in range(n_c):
        t = i / (n_c - 1.0)
        z = 0.032 + t * 0.076
        x = 0.002 * sin(t * pi)
        y = 0.034 + 0.002 * t
        # tonjolan bergantian supaya terbaca sebagai tulang bergelombang
        bulge = 0.0175 if (i % 2 == 0) else 0.0142
        corr_pts.append(Vector((x, y, z)))
        corr_r.append((bulge, bulge))
    loft(V, F, FM, FS,
         sweep(corr_pts, corr_r, SEG_TUBE, up=Vector((0, 1, 0))),
         mat=M_BLACK)

    # --- sambungan ke mouthpiece (karet, siku) -----------------------------
    elbow = [
        Vector((0.0, 0.034, 0.036)),
        Vector((0.0, 0.032, 0.026)),
        Vector((0.0, 0.024, 0.014)),
        Vector((0.0, 0.012, 0.006)),
    ]
    loft(V, F, FM, FS,
         sweep(elbow, [(0.0140, 0.0140)] * len(elbow), SEG_TUBE,
               up=Vector((0, 0, 1))),
         mat=M_RUBBER)

    # --- mouthpiece: origin ada di ujung mulut (0, 0, 0) -------------------
    mouth = [
        (0.010, 0.0140, 0.0130),
        (0.000, 0.0155, 0.0142),
        (-0.012, 0.0150, 0.0130),
        (-0.024, 0.0115, 0.0095),
        (-0.032, 0.0060, 0.0055),
    ]
    loft(V, F, FM, FS,
         [ring((0.0, y, 0.004), rx, rz, SEG_TUBE, 2.4) for (y, rx, rz) in mouth],
         mat=M_RUBBER)

    # --- kepala atas: penutup melebar dengan punggung bergerigi ------------
    head = [
        (0.405, 0.0135, 0.0135),
        (0.414, 0.0200, 0.0145),
        (0.426, 0.0230, 0.0135),
        (0.440, 0.0215, 0.0110),
        (0.450, 0.0145, 0.0080),
    ]
    loft(V, F, FM, FS,
         [ring((0.006, 0.0385 + (z - 0.405) * 0.10, z), rx, rz, 16, 2.8)
          for (z, rx, rz) in head],
         mat=M_BLACK)
    # gerigi pelindung percikan di puncak
    for i in range(5):
        yy = 0.0335 + i * 0.0042
        loft(V, F, FM, FS,
             [ring((0.006, yy, 0.4435), 0.0175, 0.0035, 8, 2.6),
              ring((0.006, yy, 0.4505), 0.0165, 0.0030, 8, 2.6)],
             mat=M_BLACK)
    # klip tabung (penjepit ke masker)
    loft(V, F, FM, FS,
         [ring((0.0, 0.020, 0.165), 0.010, 0.0135, 10, 2.6),
          ring((0.0, 0.004, 0.165), 0.010, 0.0135, 10, 2.6)],
         mat=M_BLACK)

    obj = new_mesh_object("PRP_divegear_snorkel", V, F, FM, FS,
                          [mats["black"], mats["rubber"]], col)
    obj.location = STAGE["snorkel"]
    obj["part"] = "snorkel"
    obj["pivot"] = "ujung mulut (mouthpiece) di origin"
    obj["facing"] = "-Y"
    obj["size_target_m"] = "0.45 panjang"
    return obj


# ---------------------------------------------------------------------------
# fin
# ---------------------------------------------------------------------------


def fin_geometry(mats, sx, col):
    """Bangun satu fin; sx = +1 kiri, -1 kanan (cermin pada X)."""
    V, F, FM, FS = [], [], [], []
    M_BLACK, M_RUBBER = 0, 1

    def mir(p):
        return Vector((sx * p[0], p[1], p[2]))

    # --- foot pocket: tumit y +0,10 ke bukaan y -0,10 ----------------------
    pocket = [
        (0.100, 0.030, 0.026, 0.026),
        (0.075, 0.048, 0.042, 0.042),
        (0.030, 0.052, 0.046, 0.046),
        (-0.020, 0.051, 0.044, 0.044),
        (-0.070, 0.047, 0.038, 0.038),
        (-0.100, 0.044, 0.032, 0.032),
    ]
    rings = []
    for (y, rx, rz, cz) in pocket:
        pts = ring((0.0, y, cz), rx, rz, SEG_POCKET, 2.4)
        rings.append([mir(p) for p in pts])
    loft(V, F, FM, FS, rings, mat=M_BLACK)

    # --- gelang kaki (strap karet) mengelilingi pergelangan ----------------
    path = []
    n = 22
    for i in range(n):
        a = 2.0 * pi * i / n
        x, z = superellipse(0.055, 0.045, a, 2.3)
        path.append(mir((x, 0.052 + 0.010 * sin(a), 0.050 + z)))
    rings = sweep(path, [(0.0115, 0.0045)] * n, 8, up=Vector((0, 1, 0)),
                  closed=True)
    loft(V, F, FM, FS, rings, mat=M_RUBBER, close_loop=True)

    # --- bilah: lebar, tipis, ujung melengkung naik -----------------------
    blade = [
        (-0.080, 0.052, 0.0080, 0.036),
        (-0.140, 0.068, 0.0075, 0.036),
        (-0.200, 0.082, 0.0070, 0.037),
        (-0.260, 0.095, 0.0065, 0.038),
        (-0.320, 0.106, 0.0060, 0.040),
        (-0.380, 0.112, 0.0056, 0.043),
        (-0.430, 0.110, 0.0052, 0.047),
        (-0.470, 0.098, 0.0048, 0.051),
        (-0.495, 0.076, 0.0044, 0.055),
        (-0.510, 0.040, 0.0040, 0.058),
    ]
    rings = []
    for (y, hw, th, cz) in blade:
        pts = ring((0.0, y, cz), hw, th, SEG_BLADE, 3.2)
        rings.append([mir(p) for p in pts])
    loft(V, F, FM, FS, rings, mat=M_BLACK)
    # pangkal bilah menyatu ke pocket
    loft(V, F, FM, FS,
         [ring(mir((0.0, -0.070, 0.038)), 0.050, 0.011, SEG_BLADE, 3.0),
          ring(mir((0.0, -0.090, 0.037)), 0.054, 0.009, SEG_BLADE, 3.0)],
         mat=M_BLACK)

    # --- rusuk: dua rel sisi + satu punggungan tengah ---------------------
    rails = [
        (-0.075, 0.048), (-0.160, 0.070), (-0.250, 0.096),
        (-0.340, 0.112), (-0.420, 0.113), (-0.470, 0.098),
    ]
    for side in (-1.0, 1.0):
        path = [mir((side * (hw * 0.88), y, cz)) for (y, hw), (_, _, _, cz)
                in zip(rails, blade[1:len(rails) + 1])]
        rings = sweep(path, [(0.0090, 0.0105)] * len(path), 8,
                      up=Vector((0, 0, 1)))
        loft(V, F, FM, FS, rings, mat=M_BLACK)
    path = [mir((0.0, y, cz)) for (y, hw, th, cz) in blade[0:6]]
    rings = sweep(path, [(0.0100, 0.0090)] * len(path), 8, up=Vector((0, 0, 1)))
    loft(V, F, FM, FS, rings, mat=M_BLACK)

    name = "PRP_divegear_fin_L" if sx > 0 else "PRP_divegear_fin_R"
    obj = new_mesh_object(name, V, F, FM, FS,
                          [mats["black"], mats["rubber"]], col)
    obj.location = STAGE["fin_L" if sx > 0 else "fin_R"]
    obj["part"] = "fin-L" if sx > 0 else "fin-R"
    obj["pivot"] = "pangkal kaki / tumit di z 0"
    obj["facing"] = "-Y"
    obj["size_target_m"] = "0.60 panjang"
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
    scn["asset"] = "divegear"
    scn["asset_note"] = ("Masker, snorkel, sepasang fin. Acuan ref-divegear_v001.png; "
                         "bentuk & palette saja, tanpa tekstur.")
    return scn, engine


def setup_preview(scn):
    prev = bpy.data.collections.new("PREVIEW")
    scn.collection.children.link(prev)

    ground_mat = material("MAT_preview_divegear-ground", HEX_GROUND, roughness=0.95, spec=0.1)
    mesh = bpy.data.meshes.new("PREVIEW_ground")
    mesh.from_pydata(
        [(-6, -6, -0.002), (6, -6, -0.002), (6, 6, -0.002), (-6, 6, -0.002)],
        [], [(0, 1, 2, 3)],
    )
    mesh.materials.append(ground_mat)
    mesh.update()
    prev.objects.link(bpy.data.objects.new("PREVIEW_ground", mesh))

    cam_data = bpy.data.cameras.new("CAM_preview")
    cam_data.lens = 50.0
    cam = bpy.data.objects.new("CAM_preview", cam_data)
    prev.objects.link(cam)
    cam.location = (0.0, -2.10, 0.75)
    cam.rotation_euler = (Vector((0.02, 0.0, 0.16)) - cam.location).normalized(
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
        ("divegear_preview-01", (0.0, -1.95, 0.62), (0.02, 0.0, 0.13), 50.0),
        ("divegear_preview-02", (-1.35, 1.15, 1.05), (0.02, 0.02, 0.10), 44.0),
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
    log("MCP - Blender terbuka, render settings divegear diset (EEVEE, 1920x1080, 24 fps, Standard)")

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
    ctl.location = (0.0, 0.0, 0.0)
    ctl["asset"] = "PRP_divegear"
    ctl["note"] = "pivot induk; origin di dasar (z 0)"
    root.objects.link(ctl)

    mask = build_mask(mats, root)
    snorkel = build_snorkel(mats, root)
    fin_l = fin_geometry(mats, 1.0, root)
    fin_r = fin_geometry(mats, -1.0, root)

    for obj in (mask, snorkel, fin_l, fin_r):
        obj.parent = ctl
        obj.matrix_parent_inverse = ctl.matrix_world.inverted()

    setup_preview(scn)

    objs = (mask, snorkel, fin_l, fin_r)
    total = 0
    print("=== RINGKASAN PRP_divegear ===")
    for obj in objs:
        d = obj.dimensions
        v = len(obj.data.vertices)
        total += v
        print("%-26s verts=%5d faces=%5d dims=(%.3f, %.3f, %.3f) m  loc=(%.2f, %.2f, %.2f)"
              % (obj.name, v, len(obj.data.polygons), d.x, d.y, d.z,
                 obj.location.x, obj.location.y, obj.location.z))
    print("total verts:", total)
    print("materials:", [m.name for m in bpy.data.materials])
    print("collections:", [c.name for c in bpy.data.collections])
    print("engine=%s vt=%s res=%dx%d fps=%d frame=%d"
          % (engine, scn.view_settings.view_transform, scn.render.resolution_x,
             scn.render.resolution_y, scn.render.fps, scn.frame_current))

    target = os.path.join(repo_root(), "assets", "props", "divegear.blend")
    bpy.ops.wm.save_as_mainfile(filepath=target, check_existing=False)
    print("saved:", target, "%.1f KB" % (os.path.getsize(target) / 1024.0))
    log("MODEL - divegear.blend: masker + snorkel + 2 fin, %d vert total, disimpan" % total)

    paths = render_previews()
    log("VERIFY - divegear_preview-01/02 50%%: %s" % ", ".join(
        os.path.basename(p) for p in paths))


if __name__ == "__main__":
    main()

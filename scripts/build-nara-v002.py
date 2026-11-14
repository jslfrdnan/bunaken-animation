"""
Membangun blockout menengah Nara v002 (karakter manusia) — BUKAN sculpt final.

Hasil: assets/char/nara_v002.blend
  scene "nara"
    koleksi CHR_nara
      +-- empty CTL_nara         pivot, origin di dasar (z 0), hadap -Y
      +-- CHR_nara_*             29 mesh terpisah (kepala .. jam selam kiri)
    koleksi PREVIEW              kamera + lampu + lantai (bukan bagian aset)

Acuan bentuk & warna: storyboard/refs/ref-nara_v001.jpg (perempuan muda,
rambut hitam panjang, wajah oval, kulit cerah). Foto HANYA dibaca sebagai acuan
proporsi/warna — tidak dipakai sebagai tekstur, latar, atau image plane.
Rambut diikat ke belakang (satu ekor), tanpa kacamata, rash guard teal,
celana pendek, jam selam di tangan kiri (+X, sisi kiri tokoh).

Skala nyata (meter), tinggi total 1,68 m, proporsi +-7,5 kepala, kaki di z 0.
Material palette PROJECT.md §2 + warna yang diminta Director (#2E383A rambut,
#8A8F8C tidak dipakai di sini). Tanpa tekstur image, tanpa library eksternal.

Skrip ini IDEMPOTEN untuk datablock miliknya dan MENYIMPAN file di akhir.
Tidak pernah memakai open_mainfile / read_factory_settings / read_homefile:
file aktif dilepas dengan save_as_mainfile ke renders/tmp/_wipe.blend dulu,
lalu bpy.data di-wipe manual.
"""

import bpy
import bmesh
import os
import math
import datetime
from math import cos, sin, pi, copysign, radians, sqrt
from mathutils import Vector

# ---------------------------------------------------------------------------
# konstanta
# ---------------------------------------------------------------------------

HEIGHT = 1.68

HEX_SKIN = "#E8D5B0"      # pasir hangat, palette §2
HEX_LIP = "#C7A985"       # kulit digelapkan (turunan palette)
HEX_RASH = "#1FA3A3"      # teal laut, palette §2
HEX_SHORTS = "#0F5C63"    # teal dalam, palette §2
HEX_HAIR = "#2E383A"      # rambut (diminta Director)
HEX_EYE = "#2E383A"       # mata
HEX_WATCH = "#F2E9DC"     # krem tulang, palette §2
HEX_ACCENT = "#E4713C"    # oranye karang, palette §2
HEX_GROUND = "#2E383A"    # lantai pratinjau

SEG_BIG = 32
SEG_MID = 24
SEG_LIMB = 18
SEG_FOOT = 16
SEG_EYE = 14

OWN_PREFIX = ("CHR_nara", "CTL_nara", "NARA_", "MAT_nara_", "MAT_preview_nara",
              "CAM_preview", "LGT_preview", "PREVIEW", "WLD_nara")

# profil kepala absolut: (z, rx, ry) — oval, dagu menyempit, tanpa tekstur
HEAD = [
    (1.456, 0.030, 0.040),   # dagu
    (1.474, 0.055, 0.068),
    (1.494, 0.070, 0.083),
    (1.520, 0.077, 0.091),   # tulang pipi
    (1.550, 0.079, 0.093),
    (1.580, 0.079, 0.093),   # garis mata ~1,572
    (1.610, 0.077, 0.091),   # dahi
    (1.640, 0.070, 0.084),   # garis rambut ~1,634
    (1.664, 0.052, 0.064),
    (1.672, 0.030, 0.038),   # ubun-ubun tengkorak; rambut menutup sampai 1,68
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


def prof_rxry(z):
    """Interpolasi (rx, ry) profil kepala pada z absolut."""
    if z <= HEAD[0][0]:
        return HEAD[0][1], HEAD[0][2]
    if z >= HEAD[-1][0]:
        return HEAD[-1][1], HEAD[-1][2]
    for k in range(len(HEAD) - 1):
        z0, rx0, ry0 = HEAD[k]
        z1, rx1, ry1 = HEAD[k + 1]
        if z0 <= z <= z1:
            t = (z - z0) / (z1 - z0)
            return rx0 + (rx1 - rx0) * t, ry0 + (ry1 - ry0) * t
    return HEAD[-1][1], HEAD[-1][2]


def face_surface_y(x, z):
    """y permukaan wajah (negatif = depan) di (x, z)."""
    rx, ry = prof_rxry(z)
    if rx <= 1e-6:
        return 0.0
    u = min(0.999, (x / rx) ** 2)
    return -ry * sqrt(1.0 - u)


def loft(sections, seg=SEG_BIG, exp=2.0, mat=0, cap_bottom=True, cap_top=True,
         smooth=True, skip=None):
    """Cincin horizontal di-Z. sections = [(cx, cy, z, rx, ry), ...]."""
    V, F, FM, FS = [], [], [], []
    starts = []
    for (cx, cy, z, rx, ry) in sections:
        starts.append(len(V))
        for i in range(seg):
            x, y = superellipse(rx, ry, 2.0 * pi * i / seg, exp)
            V.append(Vector((cx + x, cy + y, z)))
    for k in range(len(starts) - 1):
        a, b = starts[k], starts[k + 1]
        cxa, cya, za, rxa, rya = sections[k]
        cxb, cyb, zb, rxb, ryb = sections[k + 1]
        for i in range(seg):
            i2 = (i + 1) % seg
            if skip is not None:
                xa, ya = superellipse(rxa, rya, 2.0 * pi * (i + 0.5) / seg, exp)
                xb, yb = superellipse(rxb, ryb, 2.0 * pi * (i + 0.5) / seg, exp)
                cen = Vector(((cxa + xa + cxb + xb) * 0.5,
                              (cya + ya + cyb + yb) * 0.5,
                              (za + zb) * 0.5))
                if skip(cen):
                    continue
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
    return V, F, FM, FS


def frame_axes(t):
    """Sumbu cincin yang stabil untuk path hampir vertikal (hindari twist 180°)."""
    t = Vector(t).normalized()
    ref = Vector((0.0, 1.0, 0.0))
    xa = ref.cross(t)
    if xa.length < 1e-4:
        ref = Vector((1.0, 0.0, 0.0))
        xa = ref.cross(t)
    xa.normalize()
    ya = t.cross(xa).normalized()
    return xa, ya


def tube(pts, radii, seg=SEG_LIMB, exp=2.0, mat=0, cap_a=True, cap_b=True,
         smooth=True):
    """Tabung mengikuti path; cincin tegak lurus arah path."""
    V, F, FM, FS = [], [], [], []
    rings = []
    n = len(pts)
    for i, p in enumerate(pts):
        if i == 0:
            t = pts[1] - pts[0]
        elif i == n - 1:
            t = pts[-1] - pts[-2]
        else:
            t = pts[i + 1] - pts[i - 1]
        xa, ya = frame_axes(t)
        rx, ry = radii[i]
        st = len(V)
        for k in range(seg):
            x, y = superellipse(rx, ry, 2.0 * pi * k / seg, exp)
            V.append(Vector(p) + xa * x + ya * y)
        rings.append(st)
    for k in range(len(rings) - 1):
        a, b = rings[k], rings[k + 1]
        for i in range(seg):
            i2 = (i + 1) % seg
            F.append((a + i, a + i2, b + i2, b + i))
            FM.append(mat)
            FS.append(smooth)
    if cap_a:
        F.append(tuple(rings[0] + i for i in range(seg - 1, -1, -1)))
        FM.append(mat)
        FS.append(False)
    if cap_b:
        F.append(tuple(rings[-1] + i for i in range(seg)))
        FM.append(mat)
        FS.append(False)
    return V, F, FM, FS


def tube_rings(pts, radii, seg=SEG_LIMB, exp=2.0):
    """Cincin tabung dihitung sekali; dipakai bersama oleh potongan atas/bawah."""
    V, rings = [], []
    n = len(pts)
    for i, p in enumerate(pts):
        if i == 0:
            t = pts[1] - pts[0]
        elif i == n - 1:
            t = pts[-1] - pts[-2]
        else:
            t = pts[i + 1] - pts[i - 1]
        t = Vector(t).normalized()
        xa, ya = frame_axes(t)
        rx, ry = radii[i]
        st = len(V)
        for k in range(seg):
            x, y = superellipse(rx, ry, 2.0 * pi * k / seg, exp)
            V.append(Vector(p) + xa * x + ya * y)
        rings.append(st)
    return V, rings


def part_from_rings(V, rings, i0, i1, seg, mat=0, cap_first=True, cap_last=True):
    """Ambil cincin i0..i1 dari tabung bersama (seam identik, tanpa sambungan patah)."""
    F, FM, FS = [], [], []
    for k in range(i0, i1):
        a, b = rings[k], rings[k + 1]
        for i in range(seg):
            i2 = (i + 1) % seg
            F.append((a + i, a + i2, b + i2, b + i))
            FM.append(mat)
            FS.append(True)
    if cap_first:
        a = rings[i0]
        F.append(tuple(a + i for i in range(seg - 1, -1, -1)))
        FM.append(mat)
        FS.append(False)
    if cap_last:
        b = rings[i1]
        F.append(tuple(b + i for i in range(seg)))
        FM.append(mat)
        FS.append(False)
    used = sorted({i for face in F for i in face})
    remap = {old: new for new, old in enumerate(used)}
    return ([V[i] for i in used],
            [tuple(remap[i] for i in face) for face in F], FM, FS)


def ellipsoid(center, radii, seg=SEG_MID, rings=12, mat=0, smooth=True):
    cx, cy, cz = center
    rx, ry, rz = radii
    V, F, FM, FS = [], [], [], []
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
    return V, F, FM, FS


def sphere_patch(center, radius, theta0, theta1, phi_c, phi_half,
                 seg=14, rings=5, mat=0, smooth=True):
    """Sepotong permukaan bola (kelopak mata). theta dari +Z, phi derajat."""
    cx, cy, cz = center
    V, F, FM, FS = [], [], [], []
    grid = []
    for j in range(rings):
        th = radians(theta0 + (theta1 - theta0) * j / (rings - 1))
        row = []
        for i in range(seg):
            ph = radians(phi_c - phi_half + 2.0 * phi_half * i / (seg - 1))
            row.append(len(V))
            V.append(Vector((cx + radius * sin(th) * cos(ph),
                             cy + radius * sin(th) * sin(ph),
                             cz + radius * cos(th))))
        grid.append(row)
    for j in range(rings - 1):
        for i in range(seg - 1):
            F.append((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
            FM.append(mat)
            FS.append(smooth)
    return V, F, FM, FS


def box(center, size, mat=0, rot_z=0.0):
    cx, cy, cz = center
    sx, sy, sz = size
    local = [(-sx / 2, -sy / 2, -sz / 2), (sx / 2, -sy / 2, -sz / 2),
             (sx / 2, sy / 2, -sz / 2), (-sx / 2, sy / 2, -sz / 2),
             (-sx / 2, -sy / 2, sz / 2), (sx / 2, -sy / 2, sz / 2),
             (sx / 2, sy / 2, sz / 2), (-sx / 2, sy / 2, sz / 2)]
    cr, sr = cos(rot_z), sin(rot_z)
    V = [Vector((cx + x * cr - y * sr, cy + x * sr + y * cr, cz + z)) for (x, y, z) in local]
    F = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5),
         (2, 3, 7, 6), (3, 0, 4, 7)]
    FM = [mat] * 6
    FS = [False] * 6
    return V, F, FM, FS


def foot(cx, sections, seg=SEG_FOOT, mat=0):
    """Kaki/kaki ayam: cincin tegak-lurus Y, dasar rata di z 0."""
    V, F, FM, FS = [], [], [], []
    starts = []
    for (y, rx, rz) in sections:
        starts.append(len(V))
        for i in range(seg):
            x, dz = superellipse(rx, rz, 2.0 * pi * i / seg, 2.6)
            V.append(Vector((cx + x, y, rz + dz)))
    for k in range(len(starts) - 1):
        a, b = starts[k], starts[k + 1]
        for i in range(seg):
            i2 = (i + 1) % seg
            F.append((a + i, a + i2, b + i2, b + i))
            FM.append(mat)
            FS.append(True)
    F.append(tuple(starts[0] + i for i in range(seg - 1, -1, -1)))
    FM.append(mat)
    FS.append(False)
    F.append(tuple(starts[-1] + i for i in range(seg)))
    FM.append(mat)
    FS.append(False)
    return V, F, FM, FS


def surface_band(zc, dz, x0, x1, mat=0, thick=0.008, arch=0.0,
                 samples=7, out=0.0028, taper=0.30):
    """Pita tipis yang menempel di permukaan wajah (alis, kumis, mulut)."""
    V, F, FM, FS = [], [], [], []
    cols = []
    for i in range(samples):
        t = i / (samples - 1)
        x = x0 + (x1 - x0) * t
        off = arch * (1.0 - (2.0 * t - 1.0) ** 2)
        dzl = dz * (1.0 - taper * (2.0 * t - 1.0) ** 2)
        zt = zc + dzl + off
        zb = zc - dzl + off
        yt = face_surface_y(x, zt) - out
        yb = face_surface_y(x, zb) - out
        it = yt + thick + out
        ib = yb + thick + out
        cols.append(len(V))
        V.extend([Vector((x, yt, zt)), Vector((x, yb, zb)),
                  Vector((x, it, zt)), Vector((x, ib, zb))])
    for i in range(samples - 1):
        a, b = cols[i], cols[i + 1]
        F.append((a + 0, a + 1, b + 1, b + 0))
        FM.append(mat)
        FS.append(True)
        F.append((a + 2, b + 2, b + 3, a + 3))
        FM.append(mat)
        FS.append(False)
        F.append((a + 0, b + 0, b + 2, a + 2))
        FM.append(mat)
        FS.append(False)
        F.append((a + 1, a + 3, b + 3, b + 1))
        FM.append(mat)
        FS.append(False)
    a = cols[0]
    F.append((a + 0, a + 2, a + 3, a + 1))
    FM.append(mat)
    FS.append(False)
    b = cols[-1]
    F.append((b + 0, b + 1, b + 3, b + 2))
    FM.append(mat)
    FS.append(False)
    return V, F, FM, FS


def add_object(name, data, mats, collection, recalc=True):
    V, F, FM, FS = data
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([tuple(v) for v in V], [], F)
    for m in mats:
        mesh.materials.append(m)
    for poly, mi, sm in zip(mesh.polygons, FM, FS):
        poly.material_index = mi
        poly.use_smooth = sm
    mesh.validate(verbose=False)
    mesh.update()
    if recalc:
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(mesh)
        bm.free()
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    return obj


def merge(*parts):
    """Gabung beberapa (V, F, FM, FS) dengan offset indeks."""
    V, F, FM, FS = [], [], [], []
    for (v, f, fm, fs) in parts:
        off = len(V)
        V.extend(v)
        F.extend(tuple(i + off for i in face) for face in f)
        FM.extend(fm)
        FS.extend(fs)
    return V, F, FM, FS


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
    last = None
    for cand in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scn.render.engine = cand
            return cand
        except TypeError as err:
            last = err
    print("PERINGATAN: gagal set EEVEE:", last)
    return scn.render.engine


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
    """Lepas file aktif (simpan salinan ke renders/tmp) lalu wipe bpy.data manual."""
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


def setup_scene(scn):
    scn.name = "nara"
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
    return scn, engine


def setup_preview(scn):
    prev = bpy.data.collections.new("PREVIEW")
    scn.collection.children.link(prev)

    ground_mat = material("MAT_preview_nara-ground", HEX_GROUND, roughness=0.92)
    mesh = bpy.data.meshes.new("PREVIEW_ground")
    mesh.from_pydata(
        [(-12, -12, -0.004), (12, -12, -0.004), (12, 12, -0.004), (-12, 12, -0.004)],
        [], [(0, 1, 2, 3)],
    )
    mesh.materials.append(ground_mat)
    mesh.update()
    prev.objects.link(bpy.data.objects.new("PREVIEW_ground", mesh))

    cam_data = bpy.data.cameras.new("CAM_preview")
    cam_data.lens = 45.0
    cam = bpy.data.objects.new("CAM_preview", cam_data)
    prev.objects.link(cam)
    cam.location = (1.95, -3.30, 1.35)
    cam.rotation_euler = (Vector((0.0, 0.0, 0.92)) - cam.location).normalized().to_track_quat(
        "-Z", "Y").to_euler()
    scn.camera = cam

    key = bpy.data.objects.new("LGT_preview-key", bpy.data.lights.new("LGT_preview-key", "SUN"))
    prev.objects.link(key)
    key.data.energy = 3.4
    key.data.angle = radians(8)
    key.rotation_euler = (radians(56), 0.0, radians(-38))

    fill = bpy.data.objects.new("LGT_preview-fill", bpy.data.lights.new("LGT_preview-fill", "AREA"))
    prev.objects.link(fill)
    fill.data.energy = 260.0
    fill.data.size = 6.0
    fill.location = (-3.0, -3.6, 2.6)
    fill.rotation_euler = (Vector((0.0, 0.0, 1.1)) - fill.location).normalized().to_track_quat(
        "-Z", "Y").to_euler()

    rim = bpy.data.objects.new("LGT_preview-rim", bpy.data.lights.new("LGT_preview-rim", "AREA"))
    prev.objects.link(rim)
    rim.data.energy = 300.0
    rim.data.size = 4.0
    rim.location = (2.8, 3.4, 3.2)
    rim.rotation_euler = (Vector((0.0, 0.0, 1.2)) - rim.location).normalized().to_track_quat(
        "-Z", "Y").to_euler()

    world = bpy.data.worlds.new("WLD_nara-preview")
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.048, 0.062, 0.070, 1.0)
    bg.inputs["Strength"].default_value = 1.0
    scn.world = world
    return cam


# ---------------------------------------------------------------------------
# bagian tubuh
# ---------------------------------------------------------------------------


def build_head(mats, col):
    obj = add_object("CHR_nara_head",
                     loft([(0.0, 0.0, z, rx, ry) for (z, rx, ry) in HEAD],
                          seg=SEG_BIG, exp=2.0, mat=0),
                     [mats["skin"]], col)

    # leher: dari pangkal tenggorokan ke rahang
    neck = loft([(0.0, 0.004, 1.392, 0.041, 0.044),
                 (0.0, 0.002, 1.432, 0.039, 0.042),
                 (0.0, 0.000, 1.470, 0.040, 0.044)],
                seg=SEG_MID, exp=2.0, mat=0,
                cap_bottom=False, cap_top=False)
    add_object("CHR_nara_neck", neck, [mats["skin"]], col)
    return obj


def build_body(mats, col):
    # badan: rash guard (kerah tinggi sampai pinggang, masuk ke celana)
    sections = [
        (0.0, 0.000, 0.928, 0.120, 0.078),
        (0.0, 0.000, 0.995, 0.126, 0.082),
        (0.0, 0.000, 1.070, 0.130, 0.085),
        (0.0, 0.000, 1.150, 0.138, 0.091),
        (0.0, 0.000, 1.225, 0.141, 0.090),
        (0.0, 0.000, 1.300, 0.149, 0.089),
        (0.0, 0.000, 1.352, 0.160, 0.087),
        (0.0, 0.000, 1.382, 0.150, 0.079),
        (0.0, 0.000, 1.400, 0.096, 0.066),
    ]
    body = loft(sections, seg=SEG_BIG, exp=2.15, mat=0, cap_bottom=False, cap_top=True)

    # lengan pendek rash guard: bola bahu + potongan lengan
    sleeves = []
    for s in (1.0, -1.0):
        sleeves.append(ellipsoid((s * 0.148, 0.0, 1.344), (0.053, 0.051, 0.053),
                                 seg=SEG_LIMB, rings=10, mat=0))
        sleeves.append(tube(
            [Vector((s * 0.150, 0.0, 1.350)), Vector((s * 0.166, 0.003, 1.302)),
             Vector((s * 0.178, 0.006, 1.252))],
            [(0.053, 0.051), (0.050, 0.048), (0.047, 0.045)],
            seg=SEG_LIMB, exp=2.0, mat=0, cap_a=False, cap_b=True))
    add_object("CHR_nara_body", merge(body, *sleeves), [mats["rash"]], col)

    # pinggul + celana pendek (menutup pangkal paha)
    hips = loft([(0.0, 0.0, 0.998, 0.152, 0.086),
                 (0.0, 0.0, 0.958, 0.166, 0.098),
                 (0.0, 0.0, 0.918, 0.172, 0.102),
                 (0.0, 0.0, 0.878, 0.168, 0.100),
                 (0.0, 0.0, 0.848, 0.152, 0.092)],
                seg=SEG_BIG, exp=2.2, mat=0, cap_bottom=False, cap_top=True)
    legs = []
    for s in (1.0, -1.0):
        legs.append(tube(
            [Vector((s * 0.080, 0.0, 0.862)), Vector((s * 0.082, 0.002, 0.780)),
             Vector((s * 0.084, 0.004, 0.690)), Vector((s * 0.084, 0.004, 0.628))],
            [(0.092, 0.096), (0.089, 0.093), (0.086, 0.090), (0.088, 0.091)],
            seg=SEG_MID, exp=2.1, mat=0, cap_a=False, cap_b=False))
    add_object("CHR_nara_shorts", merge(hips, *legs), [mats["shorts"]], col)


def build_arms(mats, col, made):
    for s, suf in ((1.0, "l"), (-1.0, "r")):
        pts = [Vector((s * 0.146, 0.000, 1.352)),
               Vector((s * 0.150, 0.000, 1.334)),
               Vector((s * 0.168, 0.004, 1.214)),
               Vector((s * 0.186, 0.008, 1.070)),
               Vector((s * 0.194, 0.010, 0.950)),
               Vector((s * 0.201, 0.013, 0.830)),
               Vector((s * 0.203, 0.014, 0.800))]
        radii = [(0.045, 0.043), (0.046, 0.044), (0.041, 0.039), (0.037, 0.036),
                 (0.033, 0.032), (0.026, 0.025), (0.024, 0.023)]
        V, rings = tube_rings(pts, radii, seg=SEG_LIMB)

        made.append(add_object("CHR_nara_arm-upper_" + suf,
                               part_from_rings(V, rings, 0, 3, SEG_LIMB,
                                               cap_first=True, cap_last=False),
                               [mats["skin"]], col, recalc=False))
        made.append(add_object("CHR_nara_arm-lower_" + suf,
                               part_from_rings(V, rings, 3, 6, SEG_LIMB,
                                               cap_first=False, cap_last=True),
                               [mats["skin"]], col, recalc=False))

        palm = merge(
            tube([Vector((s * 0.203, 0.014, 0.812)),
                  Vector((s * 0.205, 0.012, 0.756)),
                  Vector((s * 0.206, 0.010, 0.712)),
                  Vector((s * 0.206, 0.008, 0.680)),
                  Vector((s * 0.205, 0.006, 0.662))],
                 [(0.026, 0.033), (0.030, 0.040), (0.029, 0.040),
                  (0.026, 0.036), (0.012, 0.018)],
                 seg=SEG_LIMB, exp=2.6, mat=0),
            tube([Vector((s * 0.192, -0.012, 0.768)),
                  Vector((s * 0.184, -0.038, 0.741)),
                  Vector((s * 0.180, -0.050, 0.722))],
                 [(0.013, 0.013), (0.011, 0.011), (0.008, 0.008)],
                 seg=12, mat=0))
        made.append(add_object("CHR_nara_hand_" + suf, palm, [mats["skin"]], col))


def build_legs(mats, col, made):
    for s, suf in ((1.0, "l"), (-1.0, "r")):
        pts = [Vector((s * 0.079, 0.000, 0.936)),
               Vector((s * 0.082, 0.000, 0.905)),
               Vector((s * 0.084, 0.004, 0.700)),
               Vector((s * 0.085, 0.008, 0.570)),
               Vector((s * 0.086, 0.012, 0.470)),
               Vector((s * 0.087, 0.014, 0.430)),
               Vector((s * 0.087, 0.016, 0.380)),
               Vector((s * 0.087, 0.018, 0.300)),
               Vector((s * 0.088, 0.020, 0.210)),
               Vector((s * 0.088, 0.018, 0.120)),
               Vector((s * 0.088, 0.014, 0.060))]
        radii = [(0.078, 0.084), (0.075, 0.081), (0.064, 0.068), (0.057, 0.059),
                 (0.052, 0.053), (0.056, 0.055), (0.056, 0.053), (0.047, 0.045),
                 (0.040, 0.038), (0.035, 0.034), (0.032, 0.031)]
        V, rings = tube_rings(pts, radii, seg=SEG_LIMB)

        made.append(add_object("CHR_nara_thigh_" + suf,
                               part_from_rings(V, rings, 0, 4, SEG_LIMB,
                                               cap_first=True, cap_last=False),
                               [mats["skin"]], col, recalc=False))
        made.append(add_object("CHR_nara_calf_" + suf,
                               part_from_rings(V, rings, 4, 10, SEG_LIMB,
                                               cap_first=False, cap_last=False),
                               [mats["skin"]], col, recalc=False))

        ft = foot(s * 0.088, [(0.062, 0.034, 0.027), (0.020, 0.044, 0.033),
                              (-0.055, 0.045, 0.029), (-0.115, 0.040, 0.022),
                              (-0.150, 0.026, 0.011)],
                  seg=SEG_FOOT, mat=0)
        made.append(add_object("CHR_nara_foot_" + suf, ft, [mats["skin"]], col))


def build_hair(mats, col):
    """Cangkang rambut: radius menyusut ke dalam tengkorak di area wajah.

    Tidak ada quad yang dibuang, jadi garis rambut keluar sebagai kurva halus
    (perpotongan cangkang dengan kepala), bukan tangga.
    """
    seg = 56

    def opening(z):
        if z >= 1.638:
            return 0.0
        if z <= 1.500:
            return 72.0
        t = (1.638 - z) / (1.638 - 1.500)
        return 72.0 * (t ** 0.75)

    def ang_dist(phi_deg):
        d = abs((phi_deg + 90.0) % 360.0)
        return min(d, 360.0 - d)

    def smoothstep(t):
        t = max(0.0, min(1.0, t))
        return t * t * (3.0 - 2.0 * t)

    V, F, FM, FS = [], [], [], []
    zs = [1.456 + (1.672 - 1.456) * i / 33.0 for i in range(34)]
    zs.append(1.680)
    starts = []
    for z in zs:
        if z > 1.672:
            rx0, ry0, zz, a_deg, k = 0.030, 0.038, 1.680, 0.0, 0.27
        else:
            rx0, ry0 = prof_rxry(z)
            zz, a_deg, k = z + 0.001, opening(z), 1.0
        starts.append(len(V))
        for i in range(seg):
            ph = 2.0 * pi * i / seg
            d = ang_dist(math.degrees(ph))
            w = smoothstep((a_deg - d) / 13.0)
            s = (1.045 * (1.0 - w) + 0.900 * w) * k
            rx = rx0 * s + 0.003 * (1.0 - w) * k
            ry = ry0 * s + 0.004 * (1.0 - w) * k
            V.append(Vector((rx * cos(ph), 0.004 * (1.0 - w) + ry * sin(ph), zz)))
    for k2 in range(len(starts) - 1):
        a, b = starts[k2], starts[k2 + 1]
        for i in range(seg):
            i2 = (i + 1) % seg
            F.append((a + i, a + i2, b + i2, b + i))
            FM.append(0)
            FS.append(True)
    F.append(tuple(starts[-1] + i for i in range(seg)))
    FM.append(0)
    FS.append(False)
    shell = (V, F, FM, FS)

    # massa rambut di belakang kepala (supaya ikatan terbaca)
    mass = ellipsoid((0.0, 0.046, 1.545), (0.088, 0.076, 0.098),
                     seg=SEG_MID, rings=12, mat=0)

    # ekor rambut: ikat di belakang kepala, turun ke tengah punggung
    tail = tube([Vector((0.0, 0.082, 1.528)), Vector((0.0, 0.112, 1.468)),
                 Vector((0.0, 0.136, 1.392)), Vector((0.0, 0.142, 1.315)),
                 Vector((0.0, 0.136, 1.248)), Vector((0.0, 0.124, 1.206))],
                [(0.046, 0.040), (0.050, 0.043), (0.048, 0.041),
                 (0.040, 0.034), (0.028, 0.024), (0.011, 0.010)],
                seg=SEG_MID, mat=0)

    add_object("CHR_nara_hair", merge(shell, mass), [mats["hair"]], col)
    add_object("CHR_nara_hair-tail", tail, [mats["hair"]], col)


def build_face(mats, col, made):
    # mata: bola kecil yang hampir rata dengan wajah + kelopak atas
    for s, suf in ((1.0, "l"), (-1.0, "r")):
        c = (s * 0.031, -0.0755, 1.572)
        made.append(add_object("CHR_nara_eye_" + suf,
                               ellipsoid(c, (0.0115, 0.0115, 0.0115),
                                         seg=SEG_EYE, rings=10, mat=0),
                               [mats["eye"]], col))
        lid = sphere_patch(c, 0.0119, 6.0, 66.0, phi_c=-90.0, phi_half=62.0,
                           seg=SEG_EYE, rings=4, mat=0)
        add_object("CHR_nara_eye-lid_" + suf,
                   (lid[0], lid[1], lid[2], lid[3]), [mats["skin"]], col)

    # alis
    add_object("CHR_nara_brow_l",
               surface_band(1.598, 0.0032, 0.016, 0.052, mat=0, thick=0.008,
                            arch=0.0018, samples=7, taper=0.55),
               [mats["hair"]], col)
    add_object("CHR_nara_brow_r",
               surface_band(1.598, 0.0032, -0.052, -0.016, mat=0, thick=0.008,
                            arch=0.0018, samples=7, taper=0.55),
               [mats["hair"]], col)

    # hidung: baji kecil dari pangkal hidung ke ujung
    nose = tube([Vector((0.0, -0.080, 1.588)), Vector((0.0, -0.089, 1.566)),
                 Vector((0.0, -0.096, 1.546)), Vector((0.0, -0.093, 1.537))],
                [(0.008, 0.007), (0.009, 0.008), (0.011, 0.008), (0.007, 0.006)],
                seg=12, mat=0)
    add_object("CHR_nara_nose", nose, [mats["skin"]], col)

    # mulut: pita tipis melengkung, menyempit di ujung
    mouth = surface_band(1.509, 0.0038, -0.021, 0.021, mat=0, thick=0.006,
                         arch=0.002, samples=9, out=0.0022, taper=0.70)
    add_object("CHR_nara_mouth", mouth, [mats["lip"]], col)


def build_watch(mats, col):
    # jam selam tangan KIRI (+X): tali krem + aksen oranye
    strap = tube([Vector((0.2008, 0.0116, 0.838)), Vector((0.2012, 0.0118, 0.812)),
                  Vector((0.2016, 0.0120, 0.792))],
                 [(0.0285, 0.0285), (0.0288, 0.0288), (0.0282, 0.0282)],
                 seg=SEG_MID, mat=0, cap_a=False, cap_b=False)
    case = box((0.2345, 0.0120, 0.814), (0.014, 0.030, 0.026), mat=0)
    dial = box((0.2435, 0.0120, 0.814), (0.004, 0.020, 0.016), mat=1)
    add_object("CHR_nara_watch", merge(strap, case, dial),
               [mats["watch"], mats["accent"]], col)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main():
    scn = release_and_wipe()
    scn, engine = setup_scene(scn)

    mats = {
        "skin": material("MAT_nara_skin", HEX_SKIN, roughness=0.58),
        "lip": material("MAT_nara_lip", HEX_LIP, roughness=0.50),
        "rash": material("MAT_nara_rashguard", HEX_RASH, roughness=0.55),
        "shorts": material("MAT_nara_shorts", HEX_SHORTS, roughness=0.62),
        "hair": material("MAT_nara_hair", HEX_HAIR, roughness=0.42),
        "eye": material("MAT_nara_eye", HEX_EYE, roughness=0.22),
        "watch": material("MAT_nara_watch", HEX_WATCH, roughness=0.35),
        "accent": material("MAT_nara_watch-accent", HEX_ACCENT, roughness=0.40),
    }

    root = bpy.data.collections.new("CHR_nara")
    scn.collection.children.link(root)

    ctl = bpy.data.objects.new("CTL_nara", None)
    ctl.empty_display_type = "PLAIN_AXES"
    ctl.empty_display_size = 0.35
    ctl.location = (0.0, 0.0, 0.0)
    ctl["height_target_m"] = HEIGHT
    ctl["facing"] = "-Y"
    ctl["note"] = "pivot Nara; origin di dasar (z 0)"
    root.objects.link(ctl)

    made = []
    made.append(build_head(mats, root))
    build_body(mats, root)
    build_arms(mats, root, made)
    build_legs(mats, root, made)
    build_hair(mats, root)
    build_face(mats, root, made)
    build_watch(mats, root)

    for obj in root.objects:
        if obj is ctl:
            continue
        obj.parent = ctl
        obj.matrix_parent_inverse = ctl.matrix_world.inverted()
        obj["asset"] = "CHR_nara"
        obj["facing"] = "-Y"

    setup_preview(scn)

    objs = [o for o in root.objects if o.type == "MESH"]
    total = 0
    zmin = 1e9
    zmax = -1e9
    print("=== RINGKASAN CHR_nara (nara_v002) ===")
    for obj in sorted(objs, key=lambda o: o.name):
        d = obj.dimensions
        v = len(obj.data.vertices)
        total += v
        vz = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
        lz = min(p.z for p in vz)
        hz = max(p.z for p in vz)
        zmin = min(zmin, lz)
        zmax = max(zmax, hz)
        mats_used = ",".join(m.name for m in obj.data.materials if m)
        print("%-26s verts=%4d faces=%4d dims=(%.3f, %.3f, %.3f) z=%.3f..%.3f  %s"
              % (obj.name, v, len(obj.data.polygons), d.x, d.y, d.z, lz, hz, mats_used))
    print("total verts: %d" % total)
    print("tinggi aktual mesh: %.4f m (target %.2f)" % (zmax - zmin, HEIGHT))
    print("objek mesh: %d" % len(objs))
    print("material: %s" % [m.name for m in bpy.data.materials])
    print("engine=%s vt=%s res=%dx%d pct=%d fps=%d frame=%d"
          % (engine, scn.view_settings.view_transform, scn.render.resolution_x,
             scn.render.resolution_y, scn.render.resolution_percentage,
             scn.render.fps, scn.frame_current))

    target = os.path.join(repo_root(), "assets", "char", "nara_v002.blend")
    bpy.ops.wm.save_as_mainfile(filepath=target)
    print("saved:", target, os.path.getsize(target) / 1024.0, "KB")
    log("MODEL — nara_v002.blend: %d objek mesh, %d vert, tinggi %.3f m, disimpan"
        % (len(objs), total, zmax - zmin))


if __name__ == "__main__":
    main()

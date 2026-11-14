"""
Membangun aset environment Scene 2: hamparan terumbu hancur (puing + kerangka
karang pucat) di atas pasir.

Hasil: assets/env/reef-wrecked.blend (koleksi ENV_reef-wrecked)
  CTL_reef-wrecked        -> empty di (0,0,0), induk semua objek
  ENV_wreck_rubble_00..14 -> 15 klaster puing pecahan karang 0,3-1,5 m,
                             berserakan di area 20 x 20 m. Origin di dasar
                             klaster (z 0), objek diletakkan di titik sebarannya.
  ENV_wreck_skeleton_00..03 -> 4 kerangka karang bercabang tanpa jaringan
                             hidup (pucat), tinggi 0,8-1,4 m, origin di dasar.
  ENV_wreck_seabed        -> pasir 24 x 24 m sebagai datum (z 0), sedikit
                             bergelombang (-3..+0,6 cm) supaya tidak terasa
                             bidang datar buatan.

Warna: palette PROJECT.md §2 — krem tulang #F2E9DC, pasir hangat #E8D5B0, plus
abu #8A8F8C (netral tambahan) dan hijau pudar #316F58 sesuai brief aset.
Tidak ada warna di luar itu. Tanpa tekstur image.

Acuan: pengecualian environment lead 1 Nov 2026 (AGENTS.md §2.1) — panel
storyboard Scene 2 (hamparan karang hancur, shot 040-050) +
ref-reef-underwater_v001.jpg (bentuk karang bercabang) + palette. Foto hanya
acuan bentuk & warna, tidak pernah dipakai sebagai tekstur/latar.

Geometri prosedural (convex hull pecahan + tabung bercabang), tanpa modifier.
Skrip ini TIDAK menyimpan file; penyimpanan dilakukan setelah verifikasi.
"""

import bpy
import bmesh
import math
import random
from mathutils import Vector, Matrix

# ---------------------------------------------------------------------------
# palette (PROJECT.md §2 + netral tambahan)
# ---------------------------------------------------------------------------

PAL = {
    "teal": "#1FA3A3",
    "deep": "#0F5C63",
    "reef": "#3E8E6E",
    "orange": "#E4713C",
    "sand": "#E8D5B0",
    "bone": "#F2E9DC",
    "ash": "#8A8F8C",
    "dead-green": "#316F58",
}

C_BONE = PAL["bone"]
C_ASH = PAL["ash"]
C_GREEN = PAL["dead-green"]
C_SAND = PAL["sand"]

MAT_BONE, MAT_ASH, MAT_GREEN, MAT_SAND = range(4)

# sebaran
FIELD = 20.0          # area sebaran puing (m)
SEABED = 24.0         # datum pasir (m)
N_RUBBLE = 15
N_SKELETON = 4

# ---------------------------------------------------------------------------
# utilitas
# ---------------------------------------------------------------------------


def srgb(hexstr):
    """Hex sRGB -> linear RGBA."""
    h = hexstr.lstrip("#")
    values = [int(h[i : i + 2], 16) / 255.0 for i in (0, 2, 4)]

    def to_linear(u):
        return u / 12.92 if u <= 0.04045 else ((u + 0.055) / 1.055) ** 2.4

    return tuple(to_linear(v) for v in values) + (1.0,)


def material(name, hexcol, roughness=0.85, metallic=0.0, spec=0.2):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.use_backface_culling = False
    mat.diffuse_color = srgb(hexcol)
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = srgb(hexcol)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    sock = bsdf.inputs.get("Specular IOR Level") or bsdf.inputs.get("Specular")
    if sock is not None:
        sock.default_value = spec
    return mat


def new_object(name, verts, faces, mats, face_mats, face_smooth, collection):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    for m in mats:
        mesh.materials.append(m)
    for poly, mat_index, smooth in zip(mesh.polygons, face_mats, face_smooth):
        poly.material_index = mat_index
        poly.use_smooth = smooth
    mesh.validate(verbose=False)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    return obj


def add_tube(verts, faces, fmat, fsmooth, points, radii, sides, mat=0, smooth=True):
    """Tabung mengikuti polyline (parallel-transport frame)."""
    points = [Vector(p) for p in points]
    if len(points) < 2:
        return
    tangents = []
    for i, p in enumerate(points):
        if i == 0:
            t = points[1] - points[0]
        elif i == len(points) - 1:
            t = points[-1] - points[-2]
        else:
            t = points[i + 1] - points[i - 1]
        if t.length < 1e-9:
            t = Vector((0, 0, 1))
        tangents.append(t.normalized())

    hint = Vector((0, 0, 1))
    if abs(tangents[0].dot(hint)) > 0.95:
        hint = Vector((0, 1, 0))
    normal = tangents[0].cross(hint)
    if normal.length < 1e-6:
        normal = tangents[0].cross(Vector((1, 0, 0)))
    normals = [normal.normalized()]
    for i in range(1, len(points)):
        prev = normals[-1]
        t = tangents[i]
        n = prev - t * prev.dot(t)
        if n.length < 1e-6:
            n = t.cross(Vector((1, 0, 0)))
        if n.length < 1e-6:
            n = t.cross(Vector((0, 1, 0)))
        normals.append(n.normalized())

    base = len(verts)
    for i, p in enumerate(points):
        n = normals[i]
        b = tangents[i].cross(n)
        for j in range(sides):
            a = 2.0 * math.pi * j / sides
            verts.append(p + n * (math.cos(a) * radii[i]) + b * (math.sin(a) * radii[i]))
    for i in range(len(points) - 1):
        a_ring = base + i * sides
        b_ring = base + (i + 1) * sides
        for j in range(sides):
            j2 = (j + 1) % sides
            faces.append((a_ring + j, a_ring + j2, b_ring + j2, b_ring + j))
            fmat.append(mat)
            fsmooth.append(smooth)


def add_hull(verts, faces, fmat, fsmooth, pts, mat, smooth=False):
    """Convex hull dari titik acak -> pecahan bersegi."""
    bm = bmesh.new()
    for p in pts:
        bm.verts.new(p)
    bm.verts.ensure_lookup_table()
    bmesh.ops.convex_hull(bm, input=bm.verts[:], use_existing_faces=False)
    for v in [v for v in bm.verts if not v.link_faces]:
        bm.verts.remove(v)
    bm.verts.index_update()
    base = len(verts)
    verts.extend(v.co.copy() for v in bm.verts)
    for f in bm.faces:
        faces.append(tuple(base + v.index for v in f.verts))
        fmat.append(mat)
        fsmooth.append(smooth)
    bm.free()


def chunk_points(rng, size, n=(20, 30), spikes=2, spiky=1.35, flat_frac=0.0, cuts=1):
    """Titik pecahan: ellipsoid jitter + puncak tajam + bidang potong datar."""
    pts = []
    for _ in range(rng.randint(n[0], n[1])):
        u = rng.uniform(-1.0, 1.0)
        th = rng.uniform(0.0, 2.0 * math.pi)
        s = math.sqrt(max(0.0, 1.0 - u * u))
        r = rng.uniform(0.68, 1.0)
        pts.append(Vector((s * math.cos(th) * r, s * math.sin(th) * r, u * r)))
    for _ in range(spikes):
        u = rng.uniform(-1.0, 1.0)
        th = rng.uniform(0.0, 2.0 * math.pi)
        s = math.sqrt(max(0.0, 1.0 - u * u))
        f = rng.uniform(1.05, spiky)
        pts.append(Vector((s * math.cos(th) * f, s * math.sin(th) * f, u * f)))

    out = [Vector((p.x * size[0], p.y * size[1], p.z * size[2])) for p in pts]

    for _ in range(cuts):
        nrm = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-0.2, 1.0)))
        if nrm.length < 1e-6:
            continue
        nrm.normalize()
        extent = max(abs(nrm.x) * size[0], abs(nrm.y) * size[1], abs(nrm.z) * size[2])
        d = extent * rng.uniform(0.55, 0.92)
        for p in out:
            over = p.dot(nrm) - d
            if over > 0:
                p -= nrm * over

    if flat_frac > 0.0:
        zmin = -size[2] * flat_frac
        for p in out:
            p.z = max(p.z, zmin)
    return out


def place_chunk(verts, faces, fmat, fsmooth, rng, center, size, mat, rot=None,
                z_base=0.0, spikes=2, spiky=1.35, flat_frac=0.0, cuts=1,
                n=(20, 30), smooth=False):
    """Pecahan dengan titik terendah tepat di z_base (menempel dasar)."""
    pts = chunk_points(rng, size, n=n, spikes=spikes, spiky=spiky,
                       flat_frac=flat_frac, cuts=cuts)
    if rot is not None:
        pts = [rot @ p for p in pts]
    minz = min(p.z for p in pts)
    off = Vector((center[0], center[1], z_base - minz))
    add_hull(verts, faces, fmat, fsmooth, [p + off for p in pts], mat, smooth=smooth)


def axis_tilt(a, angle):
    """Rotasi +Z ke arah radial luar (sudut a pada bidang XY)."""
    axis = Vector((-math.sin(a), math.cos(a), 0.0))
    return Matrix.Rotation(angle, 3, axis)


def add_stump(verts, faces, fmat, fsmooth, rng, base_pt, direction, length,
              r0, r1, mat, sides=5):
    """Tunggul cabang karang yang patah: tabung meruncing + ujung berserabut."""
    d = Vector(direction).normalized()
    up = Vector((0, 0, 1))
    if abs(d.dot(up)) > 0.9:
        up = Vector((1, 0, 0))
    perp = d.cross(up).normalized()
    b2 = d.cross(perp).normalized()
    side = rng.choice([-1.0, 1.0])
    steps = 4
    pts, radii = [], []
    for i in range(steps + 1):
        t = i / steps
        p = Vector(base_pt) + d * (length * t) + perp * (0.09 * length * side
                                                        * math.sin(math.pi * t))
        pts.append(p)
        radii.append(r0 + (r1 - r0) * t)
    add_tube(verts, faces, fmat, fsmooth, pts, radii, sides, mat=mat, smooth=True)

    tip = pts[-1]
    tip_dir = (pts[-1] - pts[-2]).normalized()
    for k in range(2):
        a = 2.0 * math.pi * k / 2.0 + rng.uniform(-0.4, 0.4)
        out = perp * math.cos(a) + b2 * math.sin(a)
        end = tip + (tip_dir * 0.7 + out * rng.uniform(0.6, 1.05)).normalized() \
            * rng.uniform(0.03, 0.08)
        add_tube(verts, faces, fmat, fsmooth, [tip, (tip + end) * 0.5 + Vector((0, 0, 0.004)), end],
                 [r1 * 0.6, r1 * 0.35, 0.004], 4, mat=mat, smooth=True)


# ---------------------------------------------------------------------------
# ASET: klaster puing
# ---------------------------------------------------------------------------


def build_rubble_obj(rng, mats, col, idx):
    V, F, FM, FS = [], [], [], []
    # hijau pudar hanya aksen kecil; bongkahan besar tetap krem/abu
    big_pal = [MAT_BONE, MAT_ASH, MAT_BONE, MAT_ASH, MAT_ASH]
    mid_pal = [MAT_BONE, MAT_ASH, MAT_BONE, MAT_ASH, MAT_GREEN]

    # --- satu bongkahan utama (sampai 1,5 m) ------------------------------
    a = rng.uniform(0.0, 2.0 * math.pi)
    s = rng.uniform(0.50, 0.75)
    place_chunk(V, F, FM, FS, rng, (0.16 * math.cos(a), 0.16 * math.sin(a)),
                (s, s * rng.uniform(0.65, 0.95), s * rng.uniform(0.28, 0.50)),
                big_pal[rng.randrange(5)], rot=axis_tilt(a, rng.uniform(-0.25, 0.25)),
                z_base=0.0, spikes=3, spiky=1.45, flat_frac=0.65, cuts=2, n=(48, 72))

    # --- pecahan sedang di sekelilingnya ---------------------------------
    for i in range(rng.randint(6, 9)):
        a = rng.uniform(0.0, 2.0 * math.pi)
        rad = rng.uniform(0.25, 1.35)
        sz = rng.uniform(0.14, 0.32) * (1.15 - 0.40 * rad / 1.35)
        mat = mid_pal[(i + idx) % 5]
        if mat == MAT_GREEN and sz > 0.22:
            mat = MAT_ASH
        place_chunk(V, F, FM, FS, rng, (rad * math.cos(a), rad * math.sin(a)),
                    (sz, sz * rng.uniform(0.65, 1.05), sz * rng.uniform(0.35, 0.75)),
                    mat, rot=axis_tilt(a, rng.uniform(-0.30, 0.35)),
                    z_base=rng.choice([0.0, 0.0, 0.0, 0.012]),
                    spikes=2, spiky=1.40, flat_frac=0.70, cuts=1, n=(30, 44))

    # --- lempeng karang meja yang pecah (tipis, tapi tidak setipis kertas) -
    for _ in range(rng.randint(1, 2)):
        a = rng.uniform(0.0, 2.0 * math.pi)
        rad = rng.uniform(0.35, 1.10)
        sz = rng.uniform(0.26, 0.52)
        place_chunk(V, F, FM, FS, rng, (rad * math.cos(a), rad * math.sin(a)),
                    (sz, sz * rng.uniform(0.60, 0.90), rng.uniform(0.045, 0.085)),
                    MAT_BONE if rng.random() < 0.65 else MAT_ASH,
                    rot=axis_tilt(a, rng.uniform(0.05, 0.30)),
                    z_base=rng.uniform(0.0, 0.06), spikes=3, spiky=1.5,
                    cuts=1, n=(32, 44))

    # --- tunggul cabang patah -------------------------------------------
    for _ in range(rng.randint(3, 5)):
        a = rng.uniform(0.0, 2.0 * math.pi)
        rad = rng.uniform(0.25, 1.20)
        base = (rad * math.cos(a), rad * math.sin(a), 0.0)
        d = Vector((math.cos(a), math.sin(a), 0.0)) * rng.uniform(0.25, 0.75) \
            + Vector((0.0, 0.0, 1.0))
        add_stump(V, F, FM, FS, rng, base, d,
                  rng.uniform(0.16, 0.44), rng.uniform(0.030, 0.055),
                  rng.uniform(0.014, 0.024),
                  MAT_GREEN if rng.random() < 0.30 else MAT_BONE)

    # --- serpihan lepas yang terlempar jauh dari klaster ------------------
    for _ in range(rng.randint(2, 4)):
        a = rng.uniform(0.0, 2.0 * math.pi)
        rad = rng.uniform(1.55, 2.90)
        sz = rng.uniform(0.05, 0.17)
        place_chunk(V, F, FM, FS, rng, (rad * math.cos(a), rad * math.sin(a)),
                    (sz, sz * rng.uniform(0.6, 1.1), sz * rng.uniform(0.30, 0.60)),
                    MAT_BONE if rng.random() < 0.6 else MAT_ASH,
                    rot=axis_tilt(a, rng.uniform(-0.35, 0.35)),
                    z_base=0.0, spikes=2, spiky=1.5, flat_frac=0.6, cuts=1, n=(18, 26))

    # --- kerikil & sedimen kecil ----------------------------------------
    for _ in range(rng.randint(12, 20)):
        a = rng.uniform(0.0, 2.0 * math.pi)
        rad = rng.uniform(0.30, 2.40) * math.sqrt(rng.random())
        sz = rng.uniform(0.022, 0.070)
        place_chunk(V, F, FM, FS, rng, (rad * math.cos(a), rad * math.sin(a)),
                    (sz, sz * rng.uniform(0.7, 1.1), sz * rng.uniform(0.4, 0.8)),
                    MAT_BONE if rng.random() < 0.5 else MAT_ASH,
                    z_base=0.0, spikes=1, cuts=1, n=(14, 20))

    name = "ENV_wreck_rubble_%02d" % idx
    return new_object(name, V, F, mats, FM, FS, col)


# ---------------------------------------------------------------------------
# ASET: kerangka karang pucat
# ---------------------------------------------------------------------------


def build_skeleton_obj(rng, mats, col, idx, height):
    V, F, FM, FS = [], [], [], []

    def branch(base, direction, length, r0, r1, depth, mat):
        d = Vector(direction).normalized()
        up = Vector((0.0, 0.0, 1.0))
        if abs(d.dot(up)) > 0.92:
            up = Vector((1.0, 0.0, 0.0))
        perp = d.cross(up).normalized()
        lat = d.cross(perp).normalized()
        bend = perp * rng.uniform(-0.22, 0.22) * length
        steps = 5
        pts, radii = [], []
        for i in range(steps + 1):
            t = i / steps
            pts.append(Vector(base) + d * (length * t) + bend * (t * t))
            radii.append(r0 + (r1 - r0) * (t ** 0.85))
        # ujung runcing (bukan tabung terpotong rata)
        tip_dir = (pts[-1] - pts[-2]).normalized()
        pts.append(pts[-1] + tip_dir * (r1 * 1.8))
        radii.append(r1 * 0.22)
        add_tube(V, F, FM, FS, pts, radii, 6, mat=mat, smooth=True)

        if depth < 3:
            kids = 3 if depth == 0 else (2 if depth == 1 else 1)
            for _ in range(kids + rng.randint(0, 1)):
                t = rng.uniform(0.35, 0.90)
                b2 = Vector(base) + d * (length * t) + bend * (t * t)
                out = perp * rng.choice([-1.0, 1.0]) * rng.uniform(0.35, 1.0) \
                    + lat * rng.uniform(-0.7, 0.7)
                if out.length < 1e-6:
                    out = perp
                nd = (d * rng.uniform(0.45, 0.85) + out.normalized() * rng.uniform(0.6, 1.15))
                nd.normalize()
                rr = radii[min(len(radii) - 1, max(1, int(t * steps)))]
                branch(b2, nd, length * rng.uniform(0.34, 0.62),
                       rr * 0.78, rr * 0.50, depth + 1,
                       mat if rng.random() < 0.65 else (MAT_ASH if mat == MAT_BONE else MAT_BONE))

    pal = [MAT_BONE, MAT_ASH]
    m0 = pal[idx % 2]
    n_stem = rng.randint(3, 4)
    for k in range(n_stem):
        a = 2.0 * math.pi * k / n_stem + rng.uniform(-0.45, 0.45)
        rad0 = rng.uniform(0.0, 0.10)
        d = Vector((0.30 * math.cos(a), 0.30 * math.sin(a), 1.0))
        branch((rad0 * math.cos(a), rad0 * math.sin(a), 0.0), d,
               rng.uniform(0.20, 0.28), rng.uniform(0.020, 0.030),
               rng.uniform(0.012, 0.018), 0, m0)

    # skala seragam supaya tinggi total tepat
    zmax = max(p.z for p in V) if V else 1.0
    k = height / zmax if zmax > 1e-6 else 1.0
    V = [Vector((p.x * k, p.y * k, p.z * k)) for p in V]

    name = "ENV_wreck_skeleton_%02d" % idx
    return new_object(name, V, F, mats, FM, FS, col)


# ---------------------------------------------------------------------------
# ASET: pasir (datum)
# ---------------------------------------------------------------------------


def seabed_z(x, y):
    z = -0.012
    z += 0.013 * math.sin(0.72 * x + 0.45) * math.cos(0.58 * y - 0.2)
    z += 0.007 * math.sin(1.9 * x - 1.25 * y + 0.8)
    z += 0.004 * math.sin(8.5 * x) * math.cos(7.2 * y)
    return z


def build_seabed_obj(mats, col):
    V, F, FM, FS = [], [], [], []
    n = 48                     # 49 x 49 titik, sel 0,5 m
    half = SEABED / 2.0
    for i in range(n + 1):
        for j in range(n + 1):
            x = -half + SEABED * i / n
            y = -half + SEABED * j / n
            V.append(Vector((x, y, seabed_z(x, y))))
    for i in range(n):
        for j in range(n):
            a = i * (n + 1) + j
            b = a + 1
            c = a + (n + 1) + 1
            d = a + (n + 1)
            F.append((a, b, c, d))
            FM.append(MAT_SAND)
            FS.append(True)
    return new_object("ENV_wreck_seabed", V, F, mats, FM, FS, col)


# ---------------------------------------------------------------------------
# scene & pratinjau
# ---------------------------------------------------------------------------


def setup_scene(col_name):
    scn = bpy.context.scene
    scn.name = "reef-wrecked"
    for eng in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
        try:
            scn.render.engine = eng
            break
        except TypeError:
            continue
    scn.render.resolution_x = 1920
    scn.render.resolution_y = 1080
    scn.render.resolution_percentage = 100
    scn.render.fps = 24
    scn.render.fps_base = 1.0
    scn.view_settings.view_transform = "Standard"
    scn.frame_start = 1
    scn.frame_set(1)
    try:
        scn.eevee.taa_render_samples = 48
    except AttributeError:
        pass
    col = bpy.data.collections.new(col_name)
    scn.collection.children.link(col)
    return scn, col


def setup_preview(scn, cam_loc, cam_target, lens=32.0):
    prev = bpy.data.collections.new("PREVIEW")
    scn.collection.children.link(prev)

    cam_data = bpy.data.cameras.new("CAM_preview")
    cam_data.lens = lens
    cam_data.clip_start = 0.05
    cam_data.clip_end = 400.0
    cam = bpy.data.objects.new("CAM_preview", cam_data)
    prev.objects.link(cam)
    cam.location = cam_loc
    cam.rotation_euler = (Vector(cam_target) - Vector(cam_loc)).normalized().to_track_quat(
        "-Z", "Y"
    ).to_euler()
    scn.camera = cam

    key = bpy.data.objects.new("LGT_preview-key", bpy.data.lights.new("LGT_preview-key", "SUN"))
    prev.objects.link(key)
    key.data.energy = 1.7
    key.data.angle = math.radians(9)
    key.rotation_euler = (math.radians(48), 0.0, math.radians(34))

    fill = bpy.data.objects.new("LGT_preview-fill", bpy.data.lights.new("LGT_preview-fill", "AREA"))
    prev.objects.link(fill)
    fill.data.energy = 1100.0
    fill.data.size = 16.0
    fill.location = (-9.0, -13.0, 8.0)
    fill.rotation_euler = (Vector((0, 0, 0.4)) - fill.location).normalized().to_track_quat(
        "-Z", "Y"
    ).to_euler()

    rim = bpy.data.objects.new("LGT_preview-rim", bpy.data.lights.new("LGT_preview-rim", "AREA"))
    prev.objects.link(rim)
    rim.data.energy = 700.0
    rim.data.size = 12.0
    rim.location = (11.0, 9.0, 7.0)
    rim.rotation_euler = (Vector((0, 0, 0.4)) - rim.location).normalized().to_track_quat(
        "-Z", "Y"
    ).to_euler()

    world = bpy.data.worlds.new("WLD_reef-wrecked-preview")
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.045, 0.072, 0.082, 1.0)
    bg.inputs["Strength"].default_value = 1.0
    scn.world = world
    return cam


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main():
    scn, col = setup_scene("ENV_reef-wrecked")

    mats = [
        material("MAT_wreck_bone", C_BONE, roughness=0.82),
        material("MAT_wreck_ash", C_ASH, roughness=0.88),
        material("MAT_wreck_dead-green", C_GREEN, roughness=0.86),
        material("MAT_wreck_sand", C_SAND, roughness=0.95),
    ]

    ctl = bpy.data.objects.new("CTL_reef-wrecked", None)
    ctl.empty_display_type = "PLAIN_AXES"
    ctl.empty_display_size = 2.0
    ctl.location = (0.0, 0.0, 0.0)
    col.objects.link(ctl)

    seabed = build_seabed_obj(mats, col)

    # --- sebaran 15 klaster puing: grid 4x4 berjitter, 1 sel dikosongkan ---
    rng = random.Random(4101)
    cells = [(i, j) for i in range(4) for j in range(4)]
    rng.shuffle(cells)
    cells = sorted(cells[:N_RUBBLE])
    rubble = []
    for idx, (ci, cj) in enumerate(cells):
        step = FIELD / 4.0
        cx = -FIELD / 2.0 + step * (ci + 0.5) + rng.uniform(-1.3, 1.3)
        cy = -FIELD / 2.0 + step * (cj + 0.5) + rng.uniform(-1.3, 1.3)
        obj = build_rubble_obj(random.Random(4200 + idx), mats, col, idx)
        obj.location = (round(cx, 3), round(cy, 3), 0.0)
        obj.parent = ctl
        obj.matrix_parent_inverse.identity()
        rubble.append(obj)

    # --- 4 kerangka karang pucat ----------------------------------------
    spots = [(-2.80, 1.90), (2.40, -2.90), (4.60, 4.20), (-5.20, -4.40)]
    heights = [1.12, 0.84, 1.30, 1.00]
    skeletons = []
    for idx, ((sx, sy), h) in enumerate(zip(spots, heights)):
        obj = build_skeleton_obj(random.Random(4300 + idx), mats, col, idx, h)
        jx = sx + rng.uniform(-0.35, 0.35)
        jy = sy + rng.uniform(-0.35, 0.35)
        obj.location = (round(jx, 3), round(jy, 3), 0.0)
        obj.parent = ctl
        obj.matrix_parent_inverse.identity()
        skeletons.append(obj)

    seabed.parent = ctl
    seabed.matrix_parent_inverse.identity()

    bpy.context.view_layer.update()

    setup_preview(scn, (13.4, -16.2, 10.4), (0.0, 0.0, 0.30), lens=30.0)

    print("=== RINGKASAN reef-wrecked ===")
    total_v = 0
    for obj in [seabed] + rubble + skeletons:
        d = obj.dimensions
        total_v += len(obj.data.vertices)
        print(f"{obj.name}: verts={len(obj.data.vertices)} faces={len(obj.data.polygons)} "
              f"dims=({d.x:.2f}, {d.y:.2f}, {d.z:.2f}) m "
              f"loc={tuple(round(v,2) for v in obj.location)}")
    print("total verts:", total_v, "(batas 100000)")
    print("jumlah klaster puing:", len(rubble), "| kerangka:", len(skeletons))
    zs = [v.co.z for v in seabed.data.vertices]
    print(f"pasir z: {min(zs):.3f} .. {max(zs):.3f} m | luas {SEABED:.0f} x {SEABED:.0f} m")
    print("sebaran puing x:", round(min(o.location.x for o in rubble), 2),
          "..", round(max(o.location.x for o in rubble), 2),
          "| y:", round(min(o.location.y for o in rubble), 2),
          "..", round(max(o.location.y for o in rubble), 2))
    print("tinggi kerangka:", [round(o.dimensions.z, 2) for o in skeletons])
    print("materials:", [m.name for m in bpy.data.materials])
    print("collections:", [c.name for c in bpy.data.collections])
    print("engine:", scn.render.engine, "vt:", scn.view_settings.view_transform,
          "res:", scn.render.resolution_x, scn.render.resolution_y,
          "fps:", scn.render.fps, "frame:", scn.frame_current)
    print("autopack:", bpy.data.use_autopack)


main()

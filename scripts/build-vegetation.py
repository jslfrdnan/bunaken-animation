"""
Membangun aset vegetasi Scene 1: pohon kelapa dan pohon mangrove.

Jalankan dari root repo:
    "D:\\Blender Foundation\\Blender 5.2\\blender.exe" -b --python scripts/build-vegetation.py

Hasil: assets/env/vegetation.blend
  ENV_veg_coconut-palm  -> satu objek, origin di pangkal batang (z = 0)
  ENV_veg_mangrove      -> satu objek, origin di garis air (z = 0)

Semua geometri dibuat prosedural dari nol. Foto acuan hanya dibaca bentuk,
proporsi, dan warnanya; tidak ada bagian foto yang dipakai sebagai tekstur.
Acuan: storyboard/refs/ref-pohon-kelapa_v001.jpg,
       storyboard/refs/ref-pohon-mangrove_v001.jpg
"""

import bpy
import bmesh
import math
import os
import random
from mathutils import Vector, Matrix

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "env", "vegetation.blend")

# ---------------------------------------------------------------------------
# utilitas
# ---------------------------------------------------------------------------


def srgb(hexstr):
    """Hex sRGB -> linear RGBA, karena Base Color di Blender linear."""
    h = hexstr.lstrip("#")
    values = [int(h[i : i + 2], 16) / 255.0 for i in (0, 2, 4)]

    def to_linear(u):
        return u / 12.92 if u <= 0.04045 else ((u + 0.055) / 1.055) ** 2.4

    return tuple(to_linear(v) for v in values) + (1.0,)


def material(name, hexcol, roughness=0.8, metallic=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.use_backface_culling = False  # daun tipis perlu terlihat dari dua sisi
    mat.diffuse_color = srgb(hexcol)

    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = srgb(hexcol)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    spec = bsdf.inputs.get("Specular IOR Level") or bsdf.inputs.get("Specular")
    if spec is not None:
        spec.default_value = 0.35
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


def add_ico(verts, faces, mats, smooths, center, radius, scale=(1, 1, 1), subdiv=2, mat=0, smooth=True):
    """Icosphere sebagai bagian dari mesh lain (tanpa operator)."""
    bm = bmesh.new()
    try:
        bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=radius)
    except TypeError:  # Blender lama memakai diameter
        bmesh.ops.create_icosphere(bm, subdivisions=subdiv, diameter=radius * 2)
    bm.verts.ensure_lookup_table()

    base = len(verts)
    center = Vector(center)
    for v in bm.verts:
        p = Vector((v.co.x * scale[0], v.co.y * scale[1], v.co.z * scale[2]))
        verts.append(p + center)
    for f in bm.faces:
        faces.append(tuple(base + v.index for v in f.verts))
        mats.append(mat)
        smooths.append(smooth)
    bm.free()


def add_tube(
    verts,
    faces,
    mats,
    smooths,
    points,
    radii,
    sides,
    mat=0,
    cap_start=False,
    cap_end=False,
    mat_per_segment=None,
    smooth=True,
):
    """Tabung mengikuti polyline, memakai parallel-transport frame."""
    points = [Vector(p) for p in points]
    tangents = []
    for i, p in enumerate(points):
        if i == 0:
            t = points[1] - points[0]
        elif i == len(points) - 1:
            t = points[-1] - points[-2]
        else:
            t = points[i + 1] - points[i - 1]
        if t.length < 1e-8:
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
        seg_mat = mat_per_segment(i) if mat_per_segment else mat
        a_ring = base + i * sides
        b_ring = base + (i + 1) * sides
        for j in range(sides):
            j2 = (j + 1) % sides
            faces.append((a_ring + j, a_ring + j2, b_ring + j2, b_ring + j))
            mats.append(seg_mat)
            smooths.append(smooth)

    if cap_start:
        c = len(verts)
        verts.append(points[0])
        for j in range(sides):
            j2 = (j + 1) % sides
            faces.append((c, base + j2, base + j))
            mats.append(mat_per_segment(0) if mat_per_segment else mat)
            smooths.append(False)

    if cap_end:
        c = len(verts)
        verts.append(points[-1])
        last = base + (len(points) - 1) * sides
        for j in range(sides):
            j2 = (j + 1) % sides
            faces.append((c, last + j, last + j2))
            mats.append(mat_per_segment(len(points) - 2) if mat_per_segment else mat)
            smooths.append(False)


def add_quad(verts, faces, mats, smooths, p0, p1, p2, p3, mat=0, smooth=False):
    base = len(verts)
    verts.extend([p0, p1, p2, p3])
    faces.append((base, base + 1, base + 2, base + 3))
    mats.append(mat)
    smooths.append(smooth)


def bezier3(p0, p1, p2, steps):
    p0, p1, p2 = Vector(p0), Vector(p1), Vector(p2)
    out = []
    for i in range(steps):
        t = i / (steps - 1)
        out.append(p0 * ((1 - t) ** 2) + p1 * (2 * (1 - t) * t) + p2 * (t * t))
    return out


# ---------------------------------------------------------------------------
# scene kosong + material
# ---------------------------------------------------------------------------

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.name = "vegetation"
scene.unit_settings.system = "METRIC"
scene.unit_settings.scale_length = 1.0
scene.render.fps = 24
scene.render.resolution_x = 1920
scene.render.resolution_y = 1080
scene.render.resolution_percentage = 100
scene.view_settings.view_transform = "Standard"
try:
    scene.view_settings.look = "None"
except TypeError:
    pass

MAT_PALM_TRUNK = material("MAT_veg_palm-trunk", "#8A7A67", 0.88)
MAT_PALM_BAND = material("MAT_veg_palm-trunk-band", "#726457", 0.9)
MAT_PALM_CROWN = material("MAT_veg_palm-crown", "#6B5A3C", 0.9)
MAT_PALM_FROND = material("MAT_veg_palm-frond", "#3A7A56", 0.62)
MAT_PALM_FROND_YOUNG = material("MAT_veg_palm-frond-young", "#93A845", 0.6)
MAT_PALM_COCONUT = material("MAT_veg_palm-coconut", "#6A5638", 0.75)
MAT_PALM_COCONUT_GREEN = material("MAT_veg_palm-coconut-green", "#7A8440", 0.7)

MAT_MANGROVE_BARK = material("MAT_veg_mangrove-bark", "#746A5E", 0.9)
MAT_MANGROVE_ROOT = material("MAT_veg_mangrove-root", "#5B5248", 0.92)
MAT_MANGROVE_LEAF = material("MAT_veg_mangrove-leaf", "#2E5A3C", 0.62)
MAT_MANGROVE_LEAF_LIGHT = material("MAT_veg_mangrove-leaf-light", "#4C7A46", 0.6)

# ---------------------------------------------------------------------------
# koleksi
# ---------------------------------------------------------------------------

root_col = bpy.data.collections.new("ENV_veg")
scene.collection.children.link(root_col)

palm_col = bpy.data.collections.new("ENV_veg_coconut-palm")
root_col.children.link(palm_col)

mangrove_col = bpy.data.collections.new("ENV_veg_mangrove")
root_col.children.link(mangrove_col)

# ---------------------------------------------------------------------------
# pohon kelapa
# ---------------------------------------------------------------------------

rnd = random.Random(20261108)
PALM_H = 8.35

# --- batang ---
trunk_pts = []
trunk_radii = []
for i in range(91):
    t = i / 90.0
    x = 0.62 * (t ** 1.8) + 0.03 * math.sin(t * 6.0)
    y = 0.10 * (t ** 1.9)
    z = PALM_H * t
    r = 0.118 + 0.075 * math.exp(-t * 7.0) + 0.012 * ((1.0 - t) ** 2)
    r *= 1.0 + 0.014 * math.sin(i * 1.9)
    trunk_pts.append(Vector((x, y, z)))
    trunk_radii.append(r)

crown = trunk_pts[-1].copy()

palm_trunk_v = []
palm_trunk_f = []
palm_trunk_m = []
palm_trunk_s = []
add_tube(
    palm_trunk_v,
    palm_trunk_f,
    palm_trunk_m,
    palm_trunk_s,
    trunk_pts,
    trunk_radii,
    sides=10,
    cap_start=True,
    cap_end=True,
    mat_per_segment=lambda i: 1 if i % 3 == 0 else 0,
    smooth=True,
)

# akar serabut di pangkal batang, seperti di foto acuan
for i in range(7):
    az = i * 2.0 * math.pi / 7 + 0.25
    start = Vector((0.05 * math.cos(az), 0.05 * math.sin(az), 0.62))
    end = Vector((0.34 * math.cos(az), 0.34 * math.sin(az), -0.02))
    mid = Vector((0.22 * math.cos(az), 0.22 * math.sin(az), 0.28))
    pts = bezier3(start, mid, end, 7)
    radii = [0.055, 0.050, 0.045, 0.040, 0.034, 0.026, 0.016]
    add_tube(
        palm_trunk_v,
        palm_trunk_f,
        palm_trunk_m,
        palm_trunk_s,
        pts,
        radii,
        sides=6,
        mat=0,
        cap_end=True,
        smooth=True,
    )

# inti tajuk, menutup pertemuan pelepah
add_ico(
    palm_trunk_v,
    palm_trunk_f,
    palm_trunk_m,
    palm_trunk_s,
    crown + Vector((0, 0, -0.04)),
    0.30,
    scale=(1.0, 1.0, 0.85),
    mat=2,
    smooth=True,
)

palm_trunk = new_object(
    "ENV_veg_palm-trunk",
    palm_trunk_v,
    palm_trunk_f,
    [MAT_PALM_TRUNK, MAT_PALM_BAND, MAT_PALM_CROWN],
    palm_trunk_m,
    palm_trunk_s,
    palm_col,
)

# --- pelepah ---
palm_frond_v = []
palm_frond_f = []
palm_frond_m = []
palm_frond_s = []


def add_frond(azimuth, tilt, length, rise, droop, mat_index, leaf_pairs=28):
    """Satu pelepah: rachis + anak daun, dibangun lokal lalu diputar."""
    rot = (
        Matrix.Translation(crown)
        @ Matrix.Rotation(azimuth, 4, "Z")
        @ Matrix.Rotation(tilt, 4, "Y")
    )

    def rachis(t):
        return Vector(
            (
                length * t,
                0.0,
                rise * math.sin(math.pi * min(1.0, t * 0.9)) - droop * t * t,
            )
        )

    n_seg = 15
    pts = [rachis(i / n_seg) for i in range(n_seg + 1)]
    radii = [0.042 * ((1.0 - i / n_seg) ** 0.65) + 0.005 for i in range(n_seg + 1)]
    pts = [rot @ p for p in pts]
    add_tube(
        palm_frond_v,
        palm_frond_f,
        palm_frond_m,
        palm_frond_s,
        pts,
        radii,
        sides=4,
        mat=mat_index,
        cap_end=True,
        smooth=True,
    )

    for s in range(leaf_pairs):
        t = 0.12 + 0.83 * (s / (leaf_pairs - 1))
        p = rachis(t)
        t0 = max(0.0, t - 0.01)
        t1 = min(1.0, t + 0.01)
        tangent = (rachis(t1) - rachis(t0)).normalized()

        for side in (-1.0, 1.0):
            spread = 0.66 - 0.10 * t
            direction = (
                Vector((0.0, side, 0.0)) * math.cos(spread) + tangent * math.sin(spread)
            )
            direction.z -= 0.16 + 0.42 * t
            direction.normalize()

            blade = length * 0.205 * (0.72 + 0.40 * math.sin(math.pi * t))
            base = p + tangent * 0.012
            tip = base + direction * blade
            mid = base + direction * (blade * 0.52)
            perp = direction.cross(Vector((0, 0, 1)))
            if perp.length < 1e-5:
                perp = direction.cross(Vector((1, 0, 0)))
            perp.normalize()
            # lipat anak daun membentuk huruf V di sepanjang rachis
            normal = direction.cross(perp).normalized()
            twist = side * (0.42 - 0.14 * t)
            perp = perp * math.cos(twist) + normal * math.sin(twist)
            width = blade * 0.052

            add_quad(
                palm_frond_v,
                palm_frond_f,
                palm_frond_m,
                palm_frond_s,
                rot @ base,
                rot @ (mid + perp * width),
                rot @ tip,
                rot @ (mid - perp * width),
                mat=mat_index,
                smooth=False,
            )


N_FROND = 15
for i in range(N_FROND):
    az = i * 2.0 * math.pi / N_FROND + rnd.uniform(-0.10, 0.10)
    tilt = -0.55 + 1.20 * ((i * 0.61803398875) % 1.0)
    length = 3.55 + 0.80 * ((i * 0.381966) % 1.0)
    rise = 0.34 + 0.26 * rnd.random()
    droop = 0.92 + 0.55 * rnd.random() + max(0.0, tilt) * 0.65
    add_frond(az, tilt, length, rise, droop, mat_index=0)

# dua pelepah muda yang masih tegak di tengah tajuk
for i in range(2):
    add_frond(
        azimuth=0.9 + i * 2.6,
        tilt=-1.02 + i * 0.10,
        length=1.85 + i * 0.15,
        rise=0.42,
        droop=0.30,
        mat_index=1,
        leaf_pairs=18,
    )

palm_fronds = new_object(
    "ENV_veg_palm-fronds",
    palm_frond_v,
    palm_frond_f,
    [MAT_PALM_FROND, MAT_PALM_FROND_YOUNG],
    palm_frond_m,
    palm_frond_s,
    palm_col,
)

# --- kelapa ---
palm_coco_v = []
palm_coco_f = []
palm_coco_m = []
palm_coco_s = []
for i in range(9):
    az = i * 2.0 * math.pi / 9 + 0.2
    dist = 0.28 + 0.13 * rnd.random()
    center = crown + Vector(
        (math.cos(az) * dist, math.sin(az) * dist, -0.44 - 0.16 * rnd.random())
    )
    radius = 0.135 + 0.035 * rnd.random()
    add_ico(
        palm_coco_v,
        palm_coco_f,
        palm_coco_m,
        palm_coco_s,
        center,
        radius,
        scale=(1.0, 1.0, 1.18),
        subdiv=2,
        mat=0 if i % 3 else 1,
        smooth=True,
    )

palm_coconuts = new_object(
    "ENV_veg_palm-coconuts",
    palm_coco_v,
    palm_coco_f,
    [MAT_PALM_COCONUT, MAT_PALM_COCONUT_GREEN],
    palm_coco_m,
    palm_coco_s,
    palm_col,
)

# ---------------------------------------------------------------------------
# pohon mangrove
# ---------------------------------------------------------------------------

rnd = random.Random(4417)

mangrove_wood_v = []
mangrove_wood_f = []
mangrove_wood_m = []
mangrove_wood_s = []

# --- batang utama ---
trunk_pts = []
trunk_radii = []
for i in range(24):
    t = i / 23.0
    x = 0.10 * math.sin(t * 3.2) + 0.30 * (t ** 2)
    y = 0.06 * math.sin(t * 2.1 + 1.0) - 0.10 * t
    z = -0.12 + 2.37 * t
    r = 0.23 + 0.10 * math.exp(-t * 6.0) - 0.07 * t
    trunk_pts.append(Vector((x, y, z)))
    trunk_radii.append(r)

add_tube(
    mangrove_wood_v,
    mangrove_wood_f,
    mangrove_wood_m,
    mangrove_wood_s,
    trunk_pts,
    trunk_radii,
    sides=9,
    mat=0,
    cap_start=True,
    cap_end=False,
    smooth=True,
)

top = trunk_pts[-1].copy()

# --- cabang ---
cluster_centers = []


def grow_branch(start, azimuth, reach, rise, radius0, radius1, steps=10, mat=0):
    direction = Vector((math.cos(azimuth), math.sin(azimuth), 0.0))
    side = direction.cross(Vector((0, 0, 1)))
    p1 = start + direction * (reach * 0.55) + Vector((0, 0, rise * 0.30))
    p2 = start + direction * reach + Vector((0, 0, rise))
    pts = bezier3(start, p1, p2, steps)
    # sedikit kelok supaya tidak terlihat seperti pipa
    for j in range(1, steps - 1):
        pts[j] += side * (math.sin(j * 1.7 + azimuth * 3.0) * 0.035)
    radii = [radius0 + (radius1 - radius0) * (i / (steps - 1)) for i in range(steps)]
    add_tube(
        mangrove_wood_v,
        mangrove_wood_f,
        mangrove_wood_m,
        mangrove_wood_s,
        pts,
        radii,
        sides=7,
        mat=mat,
        cap_end=True,
        smooth=True,
    )
    return pts, p2


branch_azimuths = [0.45, 2.55, 4.35]
for index, az in enumerate(branch_azimuths):
    reach = 1.15 + 0.35 * rnd.random()
    rise = 2.05 + 0.40 * rnd.random()
    pts, tip = grow_branch(
        top + Vector((0, 0, -0.05 + 0.10 * index)),
        az,
        reach,
        rise,
        0.120,
        0.026,
    )
    for t_cluster in (0.62, 0.82, 0.97):
        cluster_centers.append(pts[int(t_cluster * (len(pts) - 1))])

    # dua cabang sekunder per cabang utama
    for k in range(2):
        t_start = 0.56 + 0.16 * k
        start = pts[int(t_start * (len(pts) - 1))]
        sub_az = az + (-0.85 if k == 0 else 0.85) + rnd.uniform(-0.18, 0.18)
        sub_pts, sub_tip = grow_branch(
            start,
            sub_az,
            0.55 + 0.25 * rnd.random(),
            0.62 + 0.25 * rnd.random(),
            0.058,
            0.014,
            steps=7,
        )
        cluster_centers.append(sub_pts[int(0.70 * (len(sub_pts) - 1))])
        cluster_centers.append(sub_tip)

# beberapa gumpalan di puncak, mengisi tajuk
for _ in range(4):
    az = rnd.uniform(0.0, 2.0 * math.pi)
    dist = rnd.uniform(0.20, 0.70)
    cluster_centers.append(
        top
        + Vector(
            (
                math.cos(az) * dist,
                math.sin(az) * dist,
                1.75 + rnd.uniform(-0.15, 0.40),
            )
        )
    )

# --- akar tunjang ---
N_ROOTS = 18
for i in range(N_ROOTS):
    az = i * 2.0 * math.pi / N_ROOTS + rnd.uniform(-0.12, 0.12)
    start_h = 0.48 + 0.42 * rnd.random()
    start = Vector(
        (
            0.17 * math.cos(az),
            0.17 * math.sin(az),
            start_h,
        )
    )
    end_r = 1.30 + 0.90 * rnd.random()
    end = Vector((math.cos(az) * end_r, math.sin(az) * end_r, -0.12))
    # kontrol di atas titik mulai: akar keluar hampir mendatar lalu melengkung
    control = Vector(
        (
            math.cos(az) * end_r * 0.62,
            math.sin(az) * end_r * 0.62,
            start_h + 0.16,
        )
    )
    pts = bezier3(start, control, end, 10)
    radii = [0.095 - 0.053 * (j / 9.0) for j in range(10)]
    add_tube(
        mangrove_wood_v,
        mangrove_wood_f,
        mangrove_wood_m,
        mangrove_wood_s,
        pts,
        radii,
        sides=6,
        mat=1,
        cap_end=True,
        smooth=True,
    )

# --- akar napas (pneumatofor) ---
for i in range(34):
    az = rnd.uniform(0, 2 * math.pi)
    dist = 0.8 + 2.6 * rnd.random()
    height = 0.16 + 0.60 * rnd.random()
    lean = Vector((rnd.uniform(-0.10, 0.10), rnd.uniform(-0.10, 0.10), 0.0))
    base = Vector((math.cos(az) * dist, math.sin(az) * dist, -0.10))
    pts = [base, base + Vector((0, 0, height * 0.55)) + lean * 0.5, base + Vector((0, 0, height)) + lean]
    radii = [0.034, 0.024, 0.010]
    add_tube(
        mangrove_wood_v,
        mangrove_wood_f,
        mangrove_wood_m,
        mangrove_wood_s,
        pts,
        radii,
        sides=5,
        mat=1,
        cap_end=True,
        smooth=True,
    )

mangrove_wood = new_object(
    "ENV_veg_mangrove-wood",
    mangrove_wood_v,
    mangrove_wood_f,
    [MAT_MANGROVE_BARK, MAT_MANGROVE_ROOT],
    mangrove_wood_m,
    mangrove_wood_s,
    mangrove_col,
)

# --- tajuk mangrove ---
mangrove_leaf_v = []
mangrove_leaf_f = []
mangrove_leaf_m = []
mangrove_leaf_s = []

for cluster_index, center in enumerate(cluster_centers):
    mat_index = 0 if cluster_index % 3 else 1

    # Tajuk dibentuk dari daun majemuk: satu tangkai dengan 6 anak daun
    # bulat kecil. Siluetnya lebih berdaun lebar daripada daun radial.
    for _ in range(20):
        theta = rnd.uniform(0.0, 2.0 * math.pi)
        phi = rnd.uniform(-0.40, 1.10)
        direction = Vector(
            (
                math.cos(theta) * math.cos(phi),
                math.sin(theta) * math.cos(phi),
                math.sin(phi) + 0.25,
            )
        ).normalized()

        stem_len = 0.26 + 0.17 * rnd.random()
        base = center + direction * rnd.uniform(0.02, 0.16)

        side = direction.cross(Vector((0, 0, 1)))
        if side.length < 1e-5:
            side = direction.cross(Vector((0, 1, 0)))
        side.normalize()

        droop = Vector((0.0, 0.0, -0.055))
        for li in range(6):
            t = 0.20 + 0.74 * (li / 5.0)
            stem_point = base + direction * (stem_len * t) + droop * (t * t)
            sign = 1.0 if li % 2 == 0 else -1.0
            leaf_dir = (
                side * (sign * 0.88)
                + direction * 0.34
                + Vector((0.0, 0.0, -0.10))
            ).normalized()

            leaf_len = 0.085 + 0.040 * rnd.random()
            width = leaf_len * 0.60
            tip = stem_point + leaf_dir * leaf_len
            mid = stem_point + leaf_dir * (leaf_len * 0.50)
            perp = leaf_dir.cross(direction)
            if perp.length < 1e-5:
                perp = leaf_dir.cross(Vector((0, 0, 1)))
            perp.normalize()

            b = len(mangrove_leaf_v)
            mangrove_leaf_v.extend([stem_point, mid + perp * width, tip, mid - perp * width])
            mangrove_leaf_f.append((b, b + 1, b + 2, b + 3))
            mangrove_leaf_m.append(mat_index)
            mangrove_leaf_s.append(False)

        # anak daun ujung
        stem_end = base + direction * stem_len + droop
        tip_dir = (direction + Vector((0.0, 0.0, -0.18))).normalized()
        leaf_len = 0.095 + 0.035 * rnd.random()
        width = leaf_len * 0.58
        tip = stem_end + tip_dir * leaf_len
        mid = stem_end + tip_dir * (leaf_len * 0.50)
        perp = tip_dir.cross(Vector((0, 0, 1)))
        if perp.length < 1e-5:
            perp = tip_dir.cross(Vector((0, 1, 0)))
        perp.normalize()
        b = len(mangrove_leaf_v)
        mangrove_leaf_v.extend([stem_end, mid + perp * width, tip, mid - perp * width])
        mangrove_leaf_f.append((b, b + 1, b + 2, b + 3))
        mangrove_leaf_m.append(mat_index)
        mangrove_leaf_s.append(False)

mangrove_canopy = new_object(
    "ENV_veg_mangrove-canopy",
    mangrove_leaf_v,
    mangrove_leaf_f,
    [MAT_MANGROVE_LEAF, MAT_MANGROVE_LEAF_LIGHT],
    mangrove_leaf_m,
    mangrove_leaf_s,
    mangrove_col,
)

# taruh mangrove di sebelah kelapa supaya file enak dilihat;
# origin objek tetap di pangkal batang (x lokal 0).
mangrove_wood.location = (14.0, 0.0, 0.0)
mangrove_canopy.location = (14.0, 0.0, 0.0)

# ---------------------------------------------------------------------------
# dunia, cahaya, kamera pratinjau
# ---------------------------------------------------------------------------

world = bpy.data.worlds.new("ENV_veg_world")
scene.world = world
world.use_nodes = True
bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
bg.inputs[0].default_value = srgb("#CBDDE4")
bg.inputs[1].default_value = 1.0

sun_data = bpy.data.lights.new("LGT_sun", type="SUN")
sun_data.energy = 3.4
sun_data.color = srgb("#FFE9C9")[:3]
sun_data.angle = math.radians(2.0)
sun = bpy.data.objects.new("LGT_sun", sun_data)
scene.collection.objects.link(sun)
sun.rotation_euler = (math.radians(55), math.radians(6), math.radians(35))

cam_data = bpy.data.cameras.new("CAM_preview")
cam_data.lens = 38.0
cam = bpy.data.objects.new("CAM_preview", cam_data)
scene.collection.objects.link(cam)
cam.location = (7.0, -21.0, 8.6)
direction = Vector((7.0, 0.0, 3.8)) - cam.location
cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
scene.camera = cam

# ---------------------------------------------------------------------------
# catatan di dalam file
# ---------------------------------------------------------------------------

note = bpy.data.texts.new("CATATAN")
note.write(
    "ASET VEGETASI SCENE 1\n"
    "====================\n\n"
    "ENV_veg_coconut-palm  pohon kelapa, origin di pangkal batang (z = 0),\n"
    "                      tinggi +-9.4 m, lebar tajuk +-7.6 m.\n"
    "ENV_veg_mangrove      pohon mangrove, origin di garis air (z = 0),\n"
    "                      tinggi +-4.9 m, lebar tajuk +-3.2 m.\n\n"
    "Skala: 1 unit = 1 meter. Tidak ada tekstur, semua material warna solid.\n"
    "Dibangun prosedural oleh scripts/build-vegetation.py.\n\n"
    "Acuan bentuk & warna (hanya dibaca, tidak dipakai sebagai tekstur):\n"
    "  storyboard/refs/ref-pohon-kelapa_v001.jpg\n"
    "  storyboard/refs/ref-pohon-mangrove_v001.jpg\n\n"
    "Warna mengikuti palette PROJECT.md pasal 2 (hijau #3E8E6E) dengan\n"
    "variasi natural untuk batang, daun muda, dan kelapa.\n"
)

# ---------------------------------------------------------------------------
# simpan
# ---------------------------------------------------------------------------

os.makedirs(os.path.dirname(OUT), exist_ok=True)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=OUT)

print("SAVED", OUT)
print("PALM objects", [o.name for o in palm_col.objects])
print("MANGROVE objects", [o.name for o in mangrove_col.objects])
for ob in list(palm_col.objects) + list(mangrove_col.objects):
    print(ob.name, "verts", len(ob.data.vertices), "faces", len(ob.data.polygons))

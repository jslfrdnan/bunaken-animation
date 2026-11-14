"""
Membangun aset environment Scene 2: terumbu rusak akibat bom & jaring dasar.

Hasil: assets/env/reef-damaged.blend (koleksi ENV_reef-damaged)
  ENV_reef_damaged-bomb     -> karang hancur total: gundukan pecah rendah,
                               serpihan tajam, patahan cabang, ring puing.
                               Origin di dasar (z 0), ±3,3 x 3,2 x 1,0 m
  ENV_reef_damaged-net      -> kepala karang dengan puncak terpotong rata +
                               tunggul patah + sisa jaring tersangkut.
                               Origin di dasar, ±2,3 x 2,0 x 0,95 m
  ENV_reef_damaged-rubble_a -> pecahan berserakan 0,4-0,9 m, ±1,7 x 1,5 x 0,4
  ENV_reef_damaged-rubble_b -> pecahan + lempeng 1,5 m, ±3,0 x 2,8 x 0,5
  ENV_reef_damaged-rubble_c -> pecahan + patahan cabang, ±1,7 x 1,6 x 0,6

Warna: turunan palette PROJECT.md §2 — hijau terumbu dipudarkan ke krem tulang
(karang bleached/pucat), teal dalam untuk sisa jaring. Tidak ada karang
pelangi, tidak ada oranye di aset ini.
Semua geometri prosedural, tanpa tekstur image.

Acuan: pengecualian environment lead 1 Nov 2026 (AGENTS.md §2.1) — panel
storyboard 2A/3A (storyboard-2shot-per-scene_v002.jpg) + foto
ref-reef-underwater_v001.jpg + palette. Foto hanya acuan bentuk & warna,
tidak pernah dipakai sebagai tekstur/latar.

Skrip ini TIDAK menyimpan file; penyimpanan dilakukan setelah verifikasi.
"""

import bpy
import bmesh
import math
import random
from mathutils import Vector, Matrix

# ---------------------------------------------------------------------------
# palette & turunannya (PROJECT.md §2)
# ---------------------------------------------------------------------------

PAL = {
    "teal": "#1FA3A3",
    "deep": "#0F5C63",
    "reef": "#3E8E6E",
    "orange": "#E4713C",
    "sand": "#E8D5B0",
    "bone": "#F2E9DC",
}


def hex_mix(a, b, t):
    """Campur dua warna sRGB (t=0 -> a, t=1 -> b), hasil hex uppercase."""
    ha = [int(a.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4)]
    hb = [int(b.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4)]
    return "".join("%02X" % int(round(x + (y - x) * t)) for x, y in zip(ha, hb))


# karang rusak: hijau terumbu dipudarkan ke krem tulang, bukan hue baru
C_BLEACH = hex_mix(hex_mix(PAL["bone"], PAL["sand"], 0.35), PAL["reef"], 0.07)
C_GREY = hex_mix(PAL["bone"], PAL["reef"], 0.45)     # hijau terumbu pudar
C_DEAD = hex_mix(hex_mix(C_GREY, PAL["deep"], 0.55), PAL["sand"], 0.18)
C_BONE = PAL["bone"]                                  # permukaan patah baru
C_SED = hex_mix(PAL["sand"], PAL["bone"], 0.35)      # debu sedimen
C_NET = PAL["deep"]                                   # sisa jaring

MAT_BLEACH, MAT_GREY, MAT_DEAD, MAT_BONE, MAT_SED, MAT_NET = range(6)

# ---------------------------------------------------------------------------
# utilitas (pola sama dengan scripts/build-fishing-gear.py)
# ---------------------------------------------------------------------------


def srgb(hexstr):
    """Hex sRGB -> linear RGBA."""
    h = hexstr.lstrip("#")
    values = [int(h[i : i + 2], 16) / 255.0 for i in (0, 2, 4)]

    def to_linear(u):
        return u / 12.92 if u <= 0.04045 else ((u + 0.055) / 1.055) ** 2.4

    return tuple(to_linear(v) for v in values) + (1.0,)


def material(name, hexcol, roughness=0.85, metallic=0.0):
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
        spec.default_value = 0.2
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


def add_tube(
    verts,
    faces,
    fmat,
    fsmooth,
    points,
    radii,
    sides,
    mat=0,
    smooth=True,
    cap_end=False,
):
    """Tabung mengikuti polyline (parallel-transport frame)."""
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
        a_ring = base + i * sides
        b_ring = base + (i + 1) * sides
        for j in range(sides):
            j2 = (j + 1) % sides
            faces.append((a_ring + j, a_ring + j2, b_ring + j2, b_ring + j))
            fmat.append(mat)
            fsmooth.append(smooth)

    if cap_end:
        last = base + (len(points) - 1) * sides
        c = len(verts)
        verts.append(points[-1])
        for j in range(sides):
            j2 = (j + 1) % sides
            faces.append((last + j, last + j2, c))
            fmat.append(mat)
            fsmooth.append(False)


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


def chunk_points(rng, size, n=(18, 26), spikes=2, spiky=1.30, flat_frac=0.0, cuts=1):
    """Titik pecahan: ellipsoid jitter + puncak tajam + bidang potong."""
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

    # bidang potong datar (permukaan patah baru)
    for _ in range(cuts):
        nrm = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-0.2, 1.0)))
        if nrm.length < 1e-6:
            continue
        nrm.normalize()
        extent = max(abs(nrm.x) * size[0], abs(nrm.y) * size[1], abs(nrm.z) * size[2])
        d = extent * rng.uniform(0.55, 0.9)
        for p in out:
            over = p.dot(nrm) - d
            if over > 0:
                p -= nrm * over

    if flat_frac > 0.0:
        zmin = -size[2] * flat_frac
        for p in out:
            p.z = max(p.z, zmin)
    return out


def place_chunk(
    verts,
    faces,
    fmat,
    fsmooth,
    rng,
    center,
    size,
    mat,
    rot=None,
    z_base=0.0,
    spikes=2,
    spiky=1.30,
    flat_frac=0.0,
    cuts=1,
    n=(18, 26),
    smooth=False,
):
    """Pecahan dengan titik terendah tepat di z_base (default: menempel dasar)."""
    pts = chunk_points(rng, size, n=n, spikes=spikes, spiky=spiky, flat_frac=flat_frac, cuts=cuts)
    if rot is not None:
        pts = [rot @ p for p in pts]
    minz = min(p.z for p in pts)
    off = Vector((center[0], center[1], z_base - minz))
    add_hull(verts, faces, fmat, fsmooth, [p + off for p in pts], mat, smooth=smooth)


def axis_tilt(a, angle):
    """Rotasi +Z ke arah radial luar (sudut a pada bidang XY)."""
    axis = Vector((-math.sin(a), math.cos(a), 0.0))
    return Matrix.Rotation(angle, 3, axis)


def add_stump(verts, faces, fmat, fsmooth, rng, base_pt, direction, length, r0, r1, mat,
              sides=6, branch=0.0, depth=0):
    """Tunggul cabang patah: tabung meruncing, ujung berserabut, kadang bercabang."""
    d = Vector(direction).normalized()
    up = Vector((0, 0, 1))
    if abs(d.dot(up)) > 0.9:
        up = Vector((1, 0, 0))
    perp = d.cross(up).normalized()
    b2 = d.cross(perp).normalized()
    side = rng.choice([-1.0, 1.0])
    steps = 5
    pts, radii = [], []
    for i in range(steps + 1):
        t = i / steps
        p = Vector(base_pt) + d * (length * t) + perp * (0.11 * length * side * math.sin(math.pi * t))
        pts.append(p)
        radii.append(r0 + (r1 - r0) * t)
    add_tube(verts, faces, fmat, fsmooth, pts, radii, sides, mat=mat, smooth=False)

    # ujung patah berserabut: 3 serpihan pendek dari bibir tabung
    tip = pts[-1]
    tip_dir = (pts[-1] - pts[-2]).normalized()
    for k in range(3):
        a = 2.0 * math.pi * k / 3.0 + rng.uniform(-0.25, 0.25)
        out = perp * math.cos(a) + b2 * math.sin(a)
        end = tip + (tip_dir * 0.7 + out * rng.uniform(0.6, 1.05)).normalized() * rng.uniform(0.04, 0.11)
        add_tube(verts, faces, fmat, fsmooth, [tip, tip + (end - tip) * 0.55, end],
                 [r1 * 0.60, r1 * 0.34, 0.004], 5, mat=mat, smooth=True)

    # cabang samping (membuat siluetnya terbaca "karang bercabang")
    if depth == 0 and rng.random() < branch:
        t = rng.uniform(0.30, 0.62)
        base2 = Vector(base_pt) + d * (length * t)
        out = (perp * side * rng.uniform(0.6, 1.0) + b2 * rng.uniform(-0.5, 0.5)).normalized()
        d2 = (d * 0.55 + out * 0.9).normalized()
        add_stump(verts, faces, fmat, fsmooth, rng, base2, d2,
                  length * rng.uniform(0.35, 0.60), r0 * 0.58, r1 * 0.52, mat,
                  sides=sides, branch=0.0, depth=1)


def add_head(verts, faces, fmat, fsmooth, rng, cx, cy, r_base, h, gx, gy, mat_side, mat_top, seg=20):
    """Kepala karang bergelombang dengan puncak dipotong rata (bidang miring tipis)."""
    # profil menggembung di kaki, puncak 0,8 r_base supaya "meja" lebar
    rings = ((0.0, 1.00), (0.13, 1.07), (0.28, 1.06), (0.43, 1.01),
             (0.58, 0.95), (0.73, 0.89), (0.87, 0.845), (1.0, 0.80))
    amp0 = 0.24
    ring_start = []
    for (t, rf) in rings:
        z = h * t
        start = len(verts)
        amp = amp0 * (1.0 - 0.45 * t)
        for k in range(seg):
            a = 2.0 * math.pi * k / seg
            r = r_base * rf * (1.0 + rng.uniform(-amp, amp))
            verts.append(Vector((cx + r * math.cos(a), cy + r * math.sin(a), z)))
        ring_start.append(start)
    for i in range(len(rings) - 1):
        a0, b0 = ring_start[i], ring_start[i + 1]
        for k in range(seg):
            k2 = (k + 1) % seg
            faces.append((a0 + k, a0 + k2, b0 + k2, b0 + k))
            fmat.append(mat_side)
            fsmooth.append(True)
    top = ring_start[-1]
    for k in range(seg):
        v = verts[top + k]
        v.z = h + gx * (v.x - cx) + gy * (v.y - cy)
    c = len(verts)
    verts.append(Vector((cx, cy, h)))
    for k in range(seg):
        k2 = (k + 1) % seg
        faces.append((top + k, top + k2, c))
        fmat.append(mat_top)
        fsmooth.append(False)


def scatter_pebbles(V, F, FM, FS, rng, count, r_in, r_out, s=(0.03, 0.08)):
    for _ in range(count):
        a = rng.uniform(0.0, 2.0 * math.pi)
        rad = rng.uniform(r_in, r_out)
        place_chunk(
            V, F, FM, FS, rng,
            (rad * math.cos(a), rad * math.sin(a)),
            (rng.uniform(*s), rng.uniform(*s), rng.uniform(*s) * 0.7),
            MAT_SED, z_base=0.0, spikes=1, n=(10, 14), cuts=1,
        )


# ---------------------------------------------------------------------------
# ASET: karang hancur oleh bom
# ---------------------------------------------------------------------------


def build_bomb(rng, mats, col):
    V, F, FM, FS = [], [], [], []

    palette = [MAT_BLEACH, MAT_GREY, MAT_BONE, MAT_SED, MAT_DEAD]

    # --- sebaran pecahan: padat di sekitar pusat, makin jarang ke tepi ----
    for i in range(52):
        a = rng.uniform(0.0, 2.0 * math.pi)
        rad = 1.40 * math.sqrt(rng.random())
        s = rng.uniform(0.055, 0.20) * (1.25 - 0.5 * rad / 1.40)
        z0 = 0.0 if rng.random() < 0.55 else rng.uniform(0.0, 0.11)
        place_chunk(
            V, F, FM, FS, rng,
            (rad * math.cos(a), rad * math.sin(a)),
            (s, s * rng.uniform(0.70, 1.05), s * rng.uniform(0.45, 0.80)),
            palette[i % 5],
            rot=axis_tilt(a, rng.uniform(-0.20, 0.30)),
            z_base=z0, spikes=3, spiky=1.5, flat_frac=0.70, cuts=1, n=(16, 22),
        )

    # --- ring puing padat (cincin ledakan) --------------------------------
    for i in range(18):
        a = 2.0 * math.pi * i / 18 + rng.uniform(-0.10, 0.10)
        rad = rng.uniform(0.95, 1.38)
        s = rng.uniform(0.09, 0.20)
        place_chunk(
            V, F, FM, FS, rng,
            (rad * math.cos(a), rad * math.sin(a)),
            (s, s * rng.uniform(0.72, 1.0), s * rng.uniform(0.45, 0.75)),
            palette[i % 5],
            rot=axis_tilt(a, rng.uniform(-0.10, 0.25)),
            z_base=0.0, spikes=2, spiky=1.45, flat_frac=0.72, cuts=1, n=(16, 22),
        )

    # --- bongkahan besar yang masih utuh sebagian -------------------------
    for i, (a, rad, s) in enumerate(((0.5, 0.42, 0.30), (2.4, 0.55, 0.36), (4.3, 0.72, 0.26),
                                     (5.6, 0.30, 0.24), (1.5, 1.05, 0.22))):
        place_chunk(V, F, FM, FS, rng,
                    (rad * math.cos(a), rad * math.sin(a)),
                    (s, s * rng.uniform(0.7, 1.0), s * rng.uniform(0.45, 0.7)),
                    [MAT_BLEACH, MAT_GREY, MAT_DEAD, MAT_BONE, MAT_GREY][i],
                    rot=axis_tilt(a, rng.uniform(-0.1, 0.2)),
                    z_base=0.0, spikes=3, spiky=1.4, flat_frac=0.72, cuts=1, n=(20, 28))

    # --- patahan cabang karang tersebar (sebagian rebah) ------------------
    for i in range(28):
        a = rng.uniform(0.0, 2.0 * math.pi)
        rad = rng.uniform(0.04, 1.15)
        droop = rng.uniform(0.0, 0.95)          # 0 = tegak, 0,95 = hampir rebah
        d = (math.cos(a) * droop, math.sin(a) * droop, 1.0)
        add_stump(
            V, F, FM, FS, rng,
            (rad * math.cos(a), rad * math.sin(a), rng.uniform(0.0, 0.09)),
            d, rng.uniform(0.12, 0.34), rng.uniform(0.022, 0.050), rng.uniform(0.012, 0.026),
            [MAT_BLEACH, MAT_GREY, MAT_BONE][i % 3],
            sides=6, branch=0.45,
        )

    # --- bilah/lempeng tajam yang masih berdiri --------------------------
    for i in range(7):
        a = 2.0 * math.pi * i / 7 + rng.uniform(-0.3, 0.3)
        rad = rng.uniform(0.25, 1.05)
        place_chunk(V, F, FM, FS, rng,
                    (rad * math.cos(a), rad * math.sin(a)),
                    (rng.uniform(0.11, 0.22), rng.uniform(0.022, 0.05), rng.uniform(0.09, 0.20)),
                    MAT_BONE if i % 2 else MAT_BLEACH,
                    rot=axis_tilt(a, rng.uniform(0.25, 0.75)),
                    z_base=0.0, spikes=3, spiky=1.8, n=(12, 18), cuts=1)

    scatter_pebbles(V, F, FM, FS, rng, 30, 0.25, 1.40)

    obj = new_object("ENV_reef_damaged-bomb", V, F, mats, FM, FS, col)
    return obj


# ---------------------------------------------------------------------------
# ASET: karang patah rata + sisa jaring
# ---------------------------------------------------------------------------


def add_net_patch(V, F, FM, FS, rng, head, spacing=0.10, twine=0.0030):
    """Fragmen jaring yang tersangkut miring di puncak karang, tepi sobek."""
    cx, cy = head["cx"], head["cy"]
    h, gx, gy = head["h"], head["gx"], head["gy"]
    r_top = head["r_base"] * 0.80
    ox, oy = 0.42 * r_top, -0.24 * r_top  # digeser ke satu sisi puncak
    reach = r_top * 1.20
    n = int(reach / spacing) + 1
    knots = {}
    for i in range(-n, n + 1):
        for j in range(-n, n + 1):
            x, y = i * spacing + ox, j * spacing + oy
            r = math.hypot(x, y)
            if r > reach:
                continue
            if r > r_top * 0.50 and rng.random() < 0.40:
                continue  # tepi sobek / lubang
            sag = 0.009 * (0.5 + 0.5 * math.sin(2.6 * x + 3.1 * y))
            if r <= r_top:
                z = h + gx * x + gy * y + 0.010 - sag
            else:
                z = h + gx * x + gy * y + 0.010 - sag - (r - r_top) * 1.05
            if z < 0.012:
                z = 0.012 + rng.uniform(0.0, 0.006)
            knots[(i, j)] = Vector((cx + x, cy + y, z))
    for (i, j), p in knots.items():
        for di, dj in ((1, 0), (0, 1)):
            q = knots.get((i + di, j + dj))
            if q is not None:
                add_tube(V, F, FM, FS, [p, q], [twine, twine], 5, mat=MAT_NET)
    # serat lepas yang menjuntai
    items = list(knots.items())
    for _ in range(8):
        (i, j), p = items[rng.randrange(len(items))]
        a = rng.uniform(0.0, 2.0 * math.pi)
        tip = p + Vector((0.12 * math.cos(a), 0.12 * math.sin(a), rng.uniform(-0.22, 0.02)))
        if tip.z < 0.008:
            tip.z = 0.008
        add_tube(V, F, FM, FS, [p, tip], [twine, twine * 0.75], 5, mat=MAT_NET)


def add_net_hang(V, F, FM, FS, rng, head, spacing=0.10, twine=0.0030):
    """Panel jaring menggantung di sisi karang (tersangkut lalu robek)."""
    cx, cy = head["cx"], head["cy"]
    r_top = head["r_base"] * 0.80
    top_z = head["h"] - 0.02
    z_bot = 0.16
    width = 0.62
    y = cy - r_top * 0.88
    ncol = int(width / spacing)
    nrow = int((top_z - z_bot) / spacing)
    knots = {}
    for i in range(ncol + 1):
        for j in range(nrow + 1):
            if j > nrow * 0.55 and rng.random() < 0.35:
                continue  # sobek di bawah
            x = cx - width / 2 + i * spacing
            z = top_z - j * spacing
            yy = y + 0.035 * math.sin(0.8 * i + 0.6 * j) + 0.05 * (j / max(nrow, 1))
            knots[(i, j)] = Vector((x, yy, max(z, 0.012)))
    for (i, j), p in knots.items():
        for di, dj in ((1, 0), (0, 1)):
            q = knots.get((i + di, j + dj))
            if q is not None:
                add_tube(V, F, FM, FS, [p, q], [twine, twine], 5, mat=MAT_NET)


def build_net_damage(rng, mats, col):
    V, F, FM, FS = [], [], [], []

    # dasar tempat karang tumbuh (gundukan tua yang menempel)
    place_chunk(V, F, FM, FS, rng, (0.0, 0.0), (0.80, 0.64, 0.18), MAT_DEAD,
                z_base=0.0, spikes=3, spiky=1.3, flat_frac=0.75, cuts=1, n=(20, 26))
    place_chunk(V, F, FM, FS, rng, (0.52, -0.40), (0.32, 0.26, 0.12), MAT_GREY,
                z_base=0.0, spikes=2, spiky=1.35, flat_frac=0.72, cuts=1, n=(16, 22))

    # kepala karang: puncak terpotong rata (jaring dasar / jangkar)
    head = dict(cx=0.08, cy=0.02, r_base=0.68, h=0.86, gx=0.05, gy=-0.055)
    add_head(V, F, FM, FS, rng, head["cx"], head["cy"], head["r_base"], head["h"],
             head["gx"], head["gy"], MAT_GREY, MAT_BONE, seg=20)

    # dua kepala karang kecil yang puncaknya juga terpotong rata
    add_head(V, F, FM, FS, rng, -0.54, -0.46, 0.38, 0.50, 0.04, 0.02, MAT_GREY, MAT_BONE, seg=14)
    add_head(V, F, FM, FS, rng, 0.58, 0.44, 0.32, 0.36, -0.05, 0.03, MAT_DEAD, MAT_BONE, seg=12)

    # tiga cuping karang di kaki supaya siluet tidak seperti drum
    for (a, rad, s, m) in ((0.4, 0.62, 0.26, MAT_GREY), (2.6, 0.58, 0.22, MAT_DEAD),
                           (4.6, 0.64, 0.20, MAT_GREY)):
        place_chunk(V, F, FM, FS, rng, (rad * math.cos(a), rad * math.sin(a)),
                    (s, s * 0.9, s * 0.65), m, z_base=0.0, spikes=3, spiky=1.35,
                    flat_frac=0.75, cuts=1, n=(18, 24))

    # tunggul patah: mengelompok di sisi kiri-belakang
    stumps = (
        ((-0.82, 0.16, 0.04), (0.24, 0.10, 1.0), 0.58, 0.095, 0.055, MAT_BLEACH),
        ((-0.66, 0.48, 0.03), (0.20, 0.16, 1.0), 0.46, 0.080, 0.046, MAT_GREY),
        ((-0.48, 0.76, 0.02), (-0.06, 0.30, 1.0), 0.36, 0.066, 0.038, MAT_BONE),
        ((-0.90, -0.24, 0.02), (0.28, -0.10, 1.0), 0.30, 0.062, 0.036, MAT_BLEACH),
        ((-0.52, -0.66, 0.02), (-0.10, -0.30, 1.0), 0.26, 0.056, 0.032, MAT_GREY),
        ((0.72, 0.42, 0.02), (0.34, 0.12, 1.0), 0.28, 0.058, 0.034, MAT_BLEACH),
    )
    for (bp, d, ln, r0, r1, m) in stumps:
        add_stump(V, F, FM, FS, rng, bp, d, ln, r0, r1, m, branch=0.8)

    # pecahan di kaki karang
    for i in range(12):
        a = rng.uniform(0.0, 2.0 * math.pi)
        rad = rng.uniform(0.45, 1.05)
        s = rng.uniform(0.07, 0.20)
        place_chunk(V, F, FM, FS, rng,
                    (rad * math.cos(a), rad * math.sin(a)),
                    (s, s * rng.uniform(0.7, 1.0), s * rng.uniform(0.45, 0.8)),
                    [MAT_BLEACH, MAT_GREY, MAT_BONE, MAT_DEAD][i % 4],
                    rot=axis_tilt(a, rng.uniform(-0.15, 0.25)),
                    z_base=0.0, spikes=2, spiky=1.45, flat_frac=0.7, cuts=1, n=(16, 22))

    # sisa jaring tersangkut di puncak rata + panel menggantung
    add_net_patch(V, F, FM, FS, rng, head)
    add_net_hang(V, F, FM, FS, rng, head)

    # helai jaring lepas di pasir
    for k in range(3):
        p0 = Vector((rng.uniform(-1.10, -0.50), rng.uniform(0.30, 0.90), 0.012))
        pts = []
        for s in range(9):
            t = s / 8.0
            pts.append(p0 + Vector((t * 0.65, -t * 0.32, 0.018 * math.sin(t * 7.0 + k))))
        add_tube(V, F, FM, FS, pts, [0.0030] * 9, 5, mat=MAT_NET)

    obj = new_object("ENV_reef_damaged-net", V, F, mats, FM, FS, col)
    return obj


# ---------------------------------------------------------------------------
# ASET: pecahan berserakan (3 varian)
# ---------------------------------------------------------------------------


def build_rubble(rng, mats, col, variant):
    V, F, FM, FS = [], [], [], []
    palette = [MAT_BLEACH, MAT_GREY, MAT_BONE, MAT_DEAD, MAT_SED]

    if variant == "a":
        # pecahan kecil-menengah, rapat, 0,35-0,9 m
        for i in range(11):
            a = 2.0 * math.pi * i / 11 + rng.uniform(-0.35, 0.35)
            rad = rng.uniform(0.06, 0.66)
            s = rng.uniform(0.17, 0.38)
            place_chunk(V, F, FM, FS, rng,
                        (rad * math.cos(a), rad * math.sin(a)),
                        (s * rng.uniform(0.85, 1.2), s * rng.uniform(0.7, 1.0), s * rng.uniform(0.55, 0.8)),
                        palette[i % 4], rot=axis_tilt(a, rng.uniform(-0.2, 0.25)),
                        z_base=0.0, spikes=3, spiky=1.5, flat_frac=0.7, cuts=1, n=(20, 28))
        scatter_pebbles(V, F, FM, FS, rng, 14, 0.10, 0.80)

    elif variant == "b":
        # lempeng karang meja besar 1,45 m + sebaran pecahan lebih luas
        place_chunk(V, F, FM, FS, rng, (0.0, 0.0), (0.72, 0.52, 0.13), MAT_BLEACH,
                    rot=axis_tilt(0.7, 0.20), z_base=0.02, spikes=4, spiky=1.6,
                    flat_frac=0.55, cuts=1, n=(24, 32))
        place_chunk(V, F, FM, FS, rng, (0.50, 0.36), (0.30, 0.24, 0.14), MAT_BONE,
                    rot=axis_tilt(2.4, 0.22), z_base=0.0, spikes=2, spiky=1.5,
                    flat_frac=0.65, cuts=1, n=(18, 24))
        for i in range(12):
            a = 2.0 * math.pi * i / 12 + rng.uniform(-0.25, 0.25)
            rad = rng.uniform(0.58, 1.35)
            s = rng.uniform(0.10, 0.24)
            place_chunk(V, F, FM, FS, rng,
                        (rad * math.cos(a), rad * math.sin(a)),
                        (s * rng.uniform(0.85, 1.25), s * rng.uniform(0.7, 1.0), s * rng.uniform(0.5, 0.85)),
                        palette[i % 5], rot=axis_tilt(a, rng.uniform(-0.2, 0.3)),
                        z_base=0.0, spikes=2, spiky=1.5, flat_frac=0.7, cuts=1, n=(18, 26))
        scatter_pebbles(V, F, FM, FS, rng, 16, 0.20, 1.45)

    else:  # "c" — pecahan + patahan cabang
        place_chunk(V, F, FM, FS, rng, (0.0, 0.0), (0.42, 0.34, 0.17), MAT_DEAD,
                    z_base=0.0, spikes=3, spiky=1.4, flat_frac=0.65, cuts=1, n=(20, 26))
        for i in range(7):
            a = 2.0 * math.pi * i / 7 + rng.uniform(-0.3, 0.3)
            rad = rng.uniform(0.16, 0.66)
            add_stump(V, F, FM, FS, rng,
                      (rad * math.cos(a), rad * math.sin(a), 0.02),
                      (math.cos(a) * 0.85, math.sin(a) * 0.85, 1.0),
                      rng.uniform(0.16, 0.42), rng.uniform(0.026, 0.048), rng.uniform(0.020, 0.042),
                      MAT_BLEACH if i % 2 else MAT_GREY, sides=7)
        for i in range(6):
            a = rng.uniform(0.0, 2.0 * math.pi)
            rad = rng.uniform(0.28, 0.78)
            s = rng.uniform(0.10, 0.24)
            place_chunk(V, F, FM, FS, rng,
                        (rad * math.cos(a), rad * math.sin(a)),
                        (s, s * rng.uniform(0.7, 1.0), s * rng.uniform(0.5, 0.85)),
                        palette[i % 5], rot=axis_tilt(a, rng.uniform(-0.15, 0.25)),
                        z_base=0.0, spikes=2, spiky=1.5, flat_frac=0.7, cuts=1, n=(18, 26))
        scatter_pebbles(V, F, FM, FS, rng, 10, 0.10, 0.80)

    obj = new_object(f"ENV_reef_damaged-rubble_{variant}", V, F, mats, FM, FS, col)
    return obj


# ---------------------------------------------------------------------------
# scene, pratinjau, world
# ---------------------------------------------------------------------------


def setup_scene(col_name):
    scn = bpy.context.scene
    scn.render.resolution_x = 1920
    scn.render.resolution_y = 1080
    scn.render.resolution_percentage = 100
    scn.render.fps = 24
    scn.render.fps_base = 1.0
    scn.view_settings.view_transform = "Standard"
    scn.frame_start = 1
    scn.frame_set(1)
    col = bpy.data.collections.new(col_name)
    scn.collection.children.link(col)
    return scn, col


def setup_preview(scn, cam_loc, cam_target, lens=42.0):
    """Kamera/lampu/lantai netral untuk verifikasi. Bukan look dev final."""
    prev = bpy.data.collections.new("PREVIEW")
    scn.collection.children.link(prev)

    ground_mat = material("MAT_preview-ground", "2E383A", roughness=0.95)
    mesh = bpy.data.meshes.new("PREVIEW_ground")
    mesh.from_pydata(
        [(-14, -14, -0.005), (14, -14, -0.005), (14, 14, -0.005), (-14, 14, -0.005)],
        [],
        [(0, 1, 2, 3)],
    )
    mesh.materials.append(ground_mat)
    mesh.update()
    ground = bpy.data.objects.new("PREVIEW_ground", mesh)
    prev.objects.link(ground)

    cam_data = bpy.data.cameras.new("CAM_env-preview")
    cam_data.lens = lens
    cam = bpy.data.objects.new("CAM_env-preview", cam_data)
    prev.objects.link(cam)
    cam.location = cam_loc
    cam.rotation_euler = (Vector(cam_target) - Vector(cam_loc)).normalized().to_track_quat(
        "-Z", "Y"
    ).to_euler()
    scn.camera = cam

    key = bpy.data.objects.new("LGT_preview-key", bpy.data.lights.new("LGT_preview-key", "SUN"))
    prev.objects.link(key)
    key.data.energy = 2.6
    key.data.angle = math.radians(6)
    key.rotation_euler = (math.radians(50), 0.0, math.radians(28))

    fill = bpy.data.objects.new("LGT_preview-fill", bpy.data.lights.new("LGT_preview-fill", "AREA"))
    prev.objects.link(fill)
    fill.data.energy = 160.0
    fill.data.size = 7.0
    fill.location = (-4.0, -7.0, 4.5)
    fill.rotation_euler = (Vector((2.0, 1.5, 0.4)) - fill.location).normalized().to_track_quat(
        "-Z", "Y"
    ).to_euler()

    rim = bpy.data.objects.new("LGT_preview-rim", bpy.data.lights.new("LGT_preview-rim", "AREA"))
    prev.objects.link(rim)
    rim.data.energy = 110.0
    rim.data.size = 6.0
    rim.location = (6.0, 4.5, 3.5)
    rim.rotation_euler = (Vector((2.0, 1.5, 0.5)) - rim.location).normalized().to_track_quat(
        "-Z", "Y"
    ).to_euler()

    world = bpy.data.worlds.new("WLD_reef-damaged-preview")
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.050, 0.078, 0.088, 1.0)
    bg.inputs["Strength"].default_value = 1.0
    scn.world = world
    return cam


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main():
    scn, col = setup_scene("ENV_reef-damaged")

    mats = [
        material("MAT_reef-damaged_coral-bleached", C_BLEACH, roughness=0.88),
        material("MAT_reef-damaged_coral-grey", C_GREY, roughness=0.90),
        material("MAT_reef-damaged_coral-dead", C_DEAD, roughness=0.92),
        material("MAT_reef-damaged_bone", C_BONE, roughness=0.80),
        material("MAT_reef-damaged_sediment", C_SED, roughness=0.95),
        material("MAT_reef-damaged_net", C_NET, roughness=0.55),
    ]

    bomb = build_bomb(random.Random(1201), mats, col)
    net = build_net_damage(random.Random(1202), mats, col)
    ra = build_rubble(random.Random(1203), mats, col, "a")
    rb = build_rubble(random.Random(1204), mats, col, "b")
    rc = build_rubble(random.Random(1205), mats, col, "c")

    # tata letak pratinjau: dua baris supaya semua varian terbaca
    bomb.location = (0.0, 0.0, 0.0)
    net.location = (4.10, 0.0, 0.0)
    ra.location = (7.05, 0.10, 0.0)
    rb.location = (-0.15, 3.80, 0.0)
    rc.location = (3.45, 3.85, 0.0)

    setup_preview(scn, (3.45, -8.3, 4.9), (3.45, 1.70, 0.30), lens=40.0)

    print("=== RINGKASAN reef-damaged ===")
    total_v = 0
    for obj in (bomb, net, ra, rb, rc):
        d = obj.dimensions
        total_v += len(obj.data.vertices)
        print(
            f"{obj.name}: verts={len(obj.data.vertices)} faces={len(obj.data.polygons)} "
            f"dims=({d.x:.2f}, {d.y:.2f}, {d.z:.2f}) m loc={tuple(round(v, 2) for v in obj.location)}"
        )
    print("total verts:", total_v)
    print("palette turunan: bleached=%s grey=%s dead=%s bone=%s sed=%s net=%s"
          % (C_BLEACH, C_GREY, C_DEAD, C_BONE, C_SED, C_NET))
    print("materials:", [m.name for m in bpy.data.materials])
    print("collections:", [c.name for c in bpy.data.collections])
    print("engine:", scn.render.engine, "vt:", scn.view_settings.view_transform,
          "res:", scn.render.resolution_x, scn.render.resolution_y, "fps:", scn.render.fps,
          "frame:", scn.frame_current)


main()

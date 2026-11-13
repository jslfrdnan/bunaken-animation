"""
Membangun aset props Scene 2 & 4: perahu Pak Haris (varian perahu bercadik).

Hasil: assets/props/haris-boat.blend (koleksi PRP_haris-boat)
  - PRP_boats di-APPEND dari assets/props/boats.blend (link=False, tidak diedit)
  - kanopi dibuang: *_canopy, *_canopy-trim, *_canopy-stay-*, *_post-*,
    balok kanopi *_beam-*, dan tali mast->kanopi *_rope-*
  - lambung dicat ulang putih pudar/abu (MAT_haris_hull-faded),
    garis papan jadi krem pudar (MAT_haris_stripe-worn)
  - PRP_haris-boat_basket  -> keranjang ikan anyaman di dek
  - PRP_haris-boat_netpile -> tumpukan jaring di dek

Origin di garis air (z 0), skala nyata. boats.blend TIDAK disentuh: semua
perubahan hanya di file baru ini. Tanpa tekstur image, tanpa pack.

Acuan: pengecualian environment/props lead 1 Nov 2026 (AGENTS.md §2.1) -
panel storyboard 2A/2B (perahu Haris, subuh & di dermaga) + ref-perahu-
bercadik_v001.jpg untuk bentuk/proporsi + palette PROJECT.md §2.
Tidak ada foto yang dipakai sebagai tekstur.

Skrip idempoten: mengosongkan bpy.data manual (TIDAK memakai open_mainfile),
lalu menyimpan ke assets/props/haris-boat.blend.
"""

import bpy
import math
import os
from mathutils import Vector

PAL = {
    "teal": "#1FA3A3",
    "deep": "#0F5C63",
    "reef": "#3E8E6E",
    "orange": "#E4713C",
    "sand": "#E8D5B0",
    "bone": "#F2E9DC",
    "mast_wood": "#8C6239",
    "rim_wood": "#3E2C20",
}

BOATS = r"D:\Tugas Semester 5\Grafika Komputer\Project-Animasi\assets\props\boats.blend"
OUT = r"D:\Tugas Semester 5\Grafika Komputer\Project-Animasi\assets\props\haris-boat.blend"

DECK_Z = 0.30
BASKET_XY = (-0.85, 0.06)
NET_XY = (-1.55, -0.02)

# ---------------------------------------------------------------------------
# utilitas
# ---------------------------------------------------------------------------


def srgb(hexstr):
    h = hexstr.lstrip("#")
    values = [int(h[i : i + 2], 16) / 255.0 for i in (0, 2, 4)]

    def to_linear(u):
        return u / 12.92 if u <= 0.04045 else ((u + 0.055) / 1.055) ** 2.4

    return tuple(to_linear(v) for v in values) + (1.0,)


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
        spec.default_value = 0.25
    return mat


def wipe_data():
    scn = bpy.context.scene
    scn.camera = None
    scn.world = None
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for col in list(bpy.data.collections):
        bpy.data.collections.remove(col)
    for extra in list(bpy.data.scenes)[1:]:
        bpy.data.scenes.remove(extra)
    for coll in (
        bpy.data.meshes,
        bpy.data.curves,
        bpy.data.materials,
        bpy.data.cameras,
        bpy.data.lights,
        bpy.data.worlds,
        bpy.data.actions,
        bpy.data.armatures,
        bpy.data.node_groups,
    ):
        for block in list(coll):
            if block.users == 0:
                coll.remove(block)


def add_box(V, F, FM, FS, x0, x1, y0, y1, z0, z1, mat=0, smooth=False):
    base = len(V)
    for z in (z0, z1):
        for y in (y0, y1):
            for x in (x0, x1):
                V.append(Vector((x, y, z)))
    faces = [
        (0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4),
        (2, 6, 7, 3), (0, 4, 6, 2), (1, 3, 7, 5),
    ]
    for f in faces:
        F.append(tuple(base + i for i in f))
        FM.append(mat)
        FS.append(smooth)


def add_tube(V, F, FM, FS, points, radii, sides, mat=0, smooth=True):
    points = [Vector(p) for p in points]
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

    base = len(V)
    for i, p in enumerate(points):
        n = normals[i]
        b = tangents[i].cross(n)
        for j in range(sides):
            a = 2.0 * math.pi * j / sides
            V.append(p + n * (math.cos(a) * radii[i]) + b * (math.sin(a) * radii[i]))
    for i in range(len(points) - 1):
        a_ring = base + i * sides
        b_ring = base + (i + 1) * sides
        for j in range(sides):
            j2 = (j + 1) % sides
            F.append((a_ring + j, a_ring + j2, b_ring + j2, b_ring + j))
            FM.append(mat)
            FS.append(smooth)


def new_object(name, V, F, mats, FM, FS, collection):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(V, [], F)
    for m in mats:
        mesh.materials.append(m)
    for poly, mi, sm in zip(mesh.polygons, FM, FS):
        poly.material_index = mi
        poly.use_smooth = sm
    mesh.validate(verbose=False)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    return obj


# ---------------------------------------------------------------------------
# keranjang ikan
# ---------------------------------------------------------------------------

M_BASKET, M_BASKET_DARK, M_FISH, M_FISH_TAIL = 0, 1, 2, 3


def build_basket(collection):
    V, F, FM, FS = [], [], [], []
    cx, cy = BASKET_XY
    z0 = DECK_Z
    h = 0.30
    r_bot, r_top = 0.145, 0.195
    sides = 24

    def radius_at(t):
        base = r_bot + (r_top - r_bot) * t
        return base * (1.0 + 0.035 * math.sin(math.pi * t))

    # dinding keranjang
    rings = [0.0, 0.33, 0.66, 1.0]
    ring_start = []
    for t in rings:
        start = len(V)
        ring_start.append(start)
        r = radius_at(t)
        for k in range(sides):
            a = 2.0 * math.pi * k / sides
            V.append(Vector((cx + r * math.cos(a), cy + r * math.sin(a), z0 + h * t)))
    for i in range(len(rings) - 1):
        a0, b0 = ring_start[i], ring_start[i + 1]
        for k in range(sides):
            k2 = (k + 1) % sides
            F.append((a0 + k, a0 + k2, b0 + k2, b0 + k))
            FM.append(M_BASKET)
            FS.append(True)

    # alas
    base_ring = ring_start[0]
    center = len(V)
    V.append(Vector((cx, cy, z0)))
    for k in range(sides):
        k2 = (k + 1) % sides
        F.append((center, base_ring + k2, base_ring + k))
        FM.append(M_BASKET)
        FS.append(False)

    # bibir atas
    rim_pts = []
    for k in range(sides + 1):
        a = 2.0 * math.pi * (k % sides) / sides
        r = radius_at(1.0)
        rim_pts.append(Vector((cx + r * math.cos(a), cy + r * math.sin(a), z0 + h)))
    add_tube(V, F, FM, FS, rim_pts, [0.012] * len(rim_pts), 6, mat=M_BASKET_DARK)

    # pita anyaman
    for t in (0.34, 0.62):
        pts = []
        r = radius_at(t) + 0.004
        for k in range(sides + 1):
            a = 2.0 * math.pi * (k % sides) / sides
            pts.append(Vector((cx + r * math.cos(a), cy + r * math.sin(a), z0 + h * t)))
        add_tube(V, F, FM, FS, pts, [0.0065] * len(pts), 5, mat=M_BASKET_DARK)

    # rusuk vertikal
    for k in range(12):
        a = 2.0 * math.pi * k / 12
        p0 = Vector((cx + radius_at(0.05) * math.cos(a), cy + radius_at(0.05) * math.sin(a), z0 + 0.02))
        p1 = Vector((cx + radius_at(0.95) * math.cos(a), cy + radius_at(0.95) * math.sin(a), z0 + h - 0.02))
        add_tube(V, F, FM, FS, [p0, p1], [0.0055, 0.0055], 5, mat=M_BASKET_DARK)

    # dua ikan di dalam keranjang (badan lonjong + ekor)
    for k, (ox, oy, tilt, length) in enumerate(
        ((-0.03, -0.02, 0.42, 0.175), (0.055, 0.035, -0.35, 0.155))
    ):
        bx, by = cx + ox, cy + oy
        bz = z0 + 0.235
        seg, ring = 10, 6
        body = []
        # badan: sumbu panjang miring ke atas, ekor di atas
        axis = Vector((math.sin(tilt) * 0.9, math.cos(tilt) * 0.25, 1.0)).normalized()
        side = Vector((math.cos(tilt), -math.sin(tilt), 0.0)).normalized()
        front = Vector((bx, by, bz)) + axis * (length * 0.5)
        back = Vector((bx, by, bz)) - axis * (length * 0.5)
        base = len(V)
        for i in range(seg + 1):
            t = i / seg
            p = back.lerp(front, t)
            w = 0.030 * math.sin(math.pi * t) + 0.004
            hgt = 0.040 * math.sin(math.pi * t) + 0.004
            for j in range(ring):
                a = 2.0 * math.pi * j / ring
                V.append(p + side * (w * math.cos(a)) + axis.cross(side) * (hgt * math.sin(a)))
        for i in range(seg):
            for j in range(ring):
                j2 = (j + 1) % ring
                F.append((base + i * ring + j, base + i * ring + j2,
                          base + (i + 1) * ring + j2, base + (i + 1) * ring + j))
                FM.append(M_FISH)
                FS.append(True)
        # ekor
        tail = front + axis * 0.045
        t1 = tail + side * 0.045 + axis * 0.045
        t2 = tail - side * 0.045 + axis * 0.045
        idx = len(V)
        V.extend([tail, t1, t2])
        F.append((idx, idx + 1, idx + 2))
        FM.append(M_FISH_TAIL)
        FS.append(False)

    return new_object("PRP_haris-boat_basket", V, F, [], FM, FS, collection)


# ---------------------------------------------------------------------------
# tumpukan jaring
# ---------------------------------------------------------------------------

M_NET, M_NET_ROPE = 0, 1

CELL = 0.055
R_TWINE = 0.0038
NET_SIZE = (0.58, 0.42)


def build_netpile(collection):
    V, F, FM, FS = [], [], [], []
    cx, cy = NET_XY
    z0 = DECK_Z
    e1 = Vector((0.70710678, 0.70710678))
    e2 = Vector((0.70710678, -0.70710678))
    layers = [
        dict(scale=1.00, dz=0.0, amp=0.100, ph=(0.0, 0.0), off=(0.0, 0.0)),
        dict(scale=0.78, dz=0.060, amp=0.090, ph=(1.4, 0.7), off=(0.035, 0.02)),
        dict(scale=0.50, dz=0.110, amp=0.060, ph=(2.6, 1.9), off=(-0.02, 0.01)),
    ]

    for cfg in layers:
        W = NET_SIZE[0] * cfg["scale"]
        D = NET_SIZE[1] * cfg["scale"]
        ox, oy = cfg["off"]
        ni = int((W / 2.0 + D / 2.0) / (CELL * 1.41421356)) + 2
        knots = {}
        for i in range(-ni, ni + 1):
            for j in range(-ni, ni + 1):
                x = cx + ox + i * CELL * e1.x + j * CELL * e2.x
                y = cy + oy + i * CELL * e1.y + j * CELL * e2.y
                if abs(x - (cx + ox)) <= W / 2.0 + CELL * 0.7 and abs(y - (cy + oy)) <= D / 2.0 + CELL * 0.7:
                    u = (x - (cx + ox)) / (W / 2.0)
                    v = (y - (cy + oy)) / (D / 2.0)
                    env = max(0.0, 1.0 - max(abs(u), abs(v))) ** 0.9
                    lift = 0.075 * math.exp(-((x - cx) ** 2 + (y - cy) ** 2) / (0.16 ** 2))
                    z = z0 + cfg["dz"] + lift + cfg["amp"] * env * (
                        0.55
                        + 0.45 * math.sin(9.0 * u + 2.0 * v + cfg["ph"][0])
                        * math.cos(7.0 * v + 1.3 + cfg["ph"][1])
                    )
                    knots[(i, j)] = Vector((x, y, max(z, z0 + 0.006)))
        for (i, j), p in knots.items():
            for di, dj in ((1, 0), (0, 1)):
                q = knots.get((i + di, j + dj))
                if q is None:
                    continue
                add_tube(V, F, FM, FS, [p, q], [R_TWINE, R_TWINE], 5, mat=M_NET)

    # tali pengikat lepas di atas tumpukan
    rope = []
    n = 16
    for k in range(n + 1):
        t = k / n
        x = cx - 0.16 + 0.32 * t
        y = cy + 0.10 * math.sin(2.4 * math.pi * t)
        z = z0 + 0.11 + 0.035 * math.sin(math.pi * t)
        rope.append(Vector((x, y, z)))
    add_tube(V, F, FM, FS, rope, [0.004] * len(rope), 5, mat=M_NET_ROPE)

    return new_object("PRP_haris-boat_netpile", V, F, [], FM, FS, collection)


# ---------------------------------------------------------------------------
# scene & pratinjau
# ---------------------------------------------------------------------------


def setup_scene():
    scn = bpy.context.scene
    scn.name = "haris-boat"
    scn.render.resolution_x = 1920
    scn.render.resolution_y = 1080
    scn.render.resolution_percentage = 100
    scn.render.fps = 24
    scn.render.fps_base = 1.0
    scn.frame_start = 1
    scn.frame_end = 240
    scn.frame_set(1)
    scn.view_settings.view_transform = "Standard"
    scn.view_settings.exposure = 0.0
    try:
        scn.render.engine = "BLENDER_EEVEE"
    except TypeError:
        pass
    if hasattr(scn, "eevee"):
        scn.eevee.taa_render_samples = 64
    return scn


def setup_preview(scn):
    prev = bpy.data.collections.new("PREVIEW")
    scn.collection.children.link(prev)

    wmat = material("MAT_preview-water", "#124B52", roughness=0.30)
    mesh = bpy.data.meshes.new("PREVIEW_water")
    s = 14.0
    mesh.from_pydata(
        [(-s, -s, -0.004), (s, -s, -0.004), (s, s, -0.004), (-s, s, -0.004)],
        [],
        [(0, 1, 2, 3)],
    )
    mesh.materials.append(wmat)
    mesh.update()
    prev.objects.link(bpy.data.objects.new("PREVIEW_water", mesh))

    cam_data = bpy.data.cameras.new("CAM_preview")
    cam_data.lens = 40.0
    cam = bpy.data.objects.new("CAM_preview", cam_data)
    prev.objects.link(cam)
    cam.location = (8.2, -8.8, 4.0)
    cam.rotation_euler = (
        Vector((0.0, 0.0, 0.9)) - cam.location
    ).normalized().to_track_quat("-Z", "Y").to_euler()
    scn.camera = cam

    key = bpy.data.objects.new("LGT_preview-key", bpy.data.lights.new("LGT_preview-key", "SUN"))
    prev.objects.link(key)
    key.data.energy = 3.0
    key.data.angle = math.radians(8)
    key.rotation_euler = (math.radians(52), 0.0, math.radians(35))

    fill = bpy.data.objects.new("LGT_preview-fill", bpy.data.lights.new("LGT_preview-fill", "AREA"))
    prev.objects.link(fill)
    fill.data.energy = 900.0
    fill.data.size = 8.0
    fill.location = (-7.0, -8.0, 6.0)
    fill.rotation_euler = (
        Vector((0.0, 0.0, 1.0)) - fill.location
    ).normalized().to_track_quat("-Z", "Y").to_euler()

    rim = bpy.data.objects.new("LGT_preview-rim", bpy.data.lights.new("LGT_preview-rim", "AREA"))
    prev.objects.link(rim)
    rim.data.energy = 500.0
    rim.data.size = 6.0
    rim.location = (8.0, 4.0, 5.0)
    rim.rotation_euler = (
        Vector((0.0, 0.0, 1.2)) - rim.location
    ).normalized().to_track_quat("-Z", "Y").to_euler()

    world = bpy.data.worlds.new("WLD_haris-boat-preview")
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.10, 0.14, 0.15, 1.0)
    bg.inputs["Strength"].default_value = 1.0
    scn.world = world
    return cam


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main():
    wipe_data()
    scn = setup_scene()

    # APPEND (bukan link) karena perahu akan dianimasikan
    with bpy.data.libraries.load(BOATS, link=False) as (src, dst):
        dst.collections = ["PRP_boats"]
    col = dst.collections[0]
    col.name = "PRP_haris-boat"
    scn.collection.children.link(col)

    # buang kanopi + turunannya
    removed = []
    for obj in list(col.objects):
        n = obj.name
        if any(k in n for k in ("_canopy", "_post-", "_beam-", "_rope-")):
            removed.append(n)
            bpy.data.objects.remove(obj, do_unlink=True)

    # rename objek sisa supaya khas varian Haris
    for obj in col.objects:
        if obj.name.startswith("PRP_boat_cadik_"):
            obj.name = obj.name.replace("PRP_boat_cadik_", "PRP_haris-boat_", 1)

    # material baru untuk lambung pudar
    m_hull = material("MAT_haris_hull-faded", "#D2D2C6", roughness=0.62)
    m_plank = material("MAT_haris_stripe-worn", "#D8D0BE", roughness=0.58)
    hull = bpy.data.objects["PRP_haris-boat_hull"]
    for i in range(len(hull.data.materials)):
        hull.data.materials[i] = m_hull
    for obj in col.objects:
        if "plank-0.34" in obj.name or "plank-0.63" in obj.name:
            for i in range(len(obj.data.materials)):
                obj.data.materials[i] = m_plank

    m_basket = material("MAT_haris_basket", PAL["sand"], roughness=0.82)
    m_basket_dark = material("MAT_haris_basket-dark", PAL["mast_wood"], roughness=0.72)
    m_fish = material("MAT_haris_fish", PAL["bone"], roughness=0.38)
    m_fish_tail = material("MAT_haris_fish-tail", PAL["teal"], roughness=0.45)
    basket = build_basket(col)
    for m in (m_basket, m_basket_dark, m_fish, m_fish_tail):
        basket.data.materials.append(m)

    m_net = material("MAT_haris_net", PAL["deep"], roughness=0.68)
    m_rope = material("MAT_haris_net-rope", PAL["sand"], roughness=0.85)
    netpile = build_netpile(col)
    for m in (m_net, m_rope):
        netpile.data.materials.append(m)

    # buang mesh & material yatim (kanopi) agar file bersih
    for me in list(bpy.data.meshes):
        if me.users == 0:
            bpy.data.meshes.remove(me)
    for m in list(bpy.data.materials):
        if m.users == 0:
            bpy.data.materials.remove(m)

    setup_preview(scn)

    scn["asset"] = "haris-boat"
    scn["asset_note"] = (
        "Varian perahu Pak Haris: kanopi dibuang, lambung putih pudar, "
        "keranjang ikan + tumpukan jaring di dek. Origin di garis air z 0."
    )

    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=OUT, check_existing=False)

    print("=== RINGKASAN haris-boat ===")
    print("objek aset:", len(col.objects))
    print("dibuang (kanopi):", len(removed))
    for n in removed:
        print("  -", n)
    for obj in (basket, netpile):
        d = obj.dimensions
        print(f"{obj.name:28s} verts={len(obj.data.vertices):5d} faces={len(obj.data.polygons):5d} "
              f"dims=({d.x:.3f}, {d.y:.3f}, {d.z:.3f}) m")
    hull = bpy.data.objects["PRP_haris-boat_hull"]
    lo = [min((hull.matrix_world @ Vector(c))[i] for c in hull.bound_box) for i in range(3)]
    hi = [max((hull.matrix_world @ Vector(c))[i] for c in hull.bound_box) for i in range(3)]
    print("hull bbox:", [round(v, 3) for v in lo], [round(v, 3) for v in hi])
    print("hull material:", [m.name for m in hull.data.materials])
    print("materials:", sorted(m.name for m in bpy.data.materials))
    print("collections:", [c.name for c in bpy.data.collections])
    print("engine:", scn.render.engine, "| vt:", scn.view_settings.view_transform,
          "| res:", scn.render.resolution_x, scn.render.resolution_y,
          "| fps:", scn.render.fps, "| frame:", scn.frame_current)
    print("saved:", OUT, "| size:", os.path.getsize(OUT), "bytes")


main()

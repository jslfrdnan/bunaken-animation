"""
Membangun aset environment Scene 4: keramba rumput laut (seaweed farm).

Hasil: assets/env/seaweed-farm.blend (koleksi ENV_seaweed-farm)
  ENV_seaweed-farm_rack   -> rangka bambu: 6 tiang (2 baris x 3 kolom), 2 rel
                             atas memanjang, 4 palang pendek, ikatan tali.
  ENV_seaweed-farm_line   -> 3 tali bentang di bawah permukaan (z -0,15)
                             + 6 tali penambat dari rel atas ke tali bentang.
  ENV_seaweed-farm_float  -> 5 pelampung kecil oranye di tali bentang.
  ENV_seaweed-farm_weed_a/b/c -> 3 rumpun rumput laut menggantung di tali
                             (pita-pita hijau, panjang 0,45-0,80 m).

Skala: petak 4,0 x 3,0 m, tiang menonjol 1,20 m di atas permukaan air.
Origin semua objek di (0,0,0) = permukaan air. Rumput menggantung ke bawah.

Warna: bambu pasir hangat #E8D5B0, tali krem tulang #F2E9DC, pelampung oranye
karang #E4713C (aksen), rumput hijau terumbu #3E8E6E dan teal dalam #0F5C63 —
palette PROJECT.md §2. Tanpa tekstur image.

Acuan: pengecualian environment lead 1 Nov 2026 (AGENTS.md §2.1) — panel
storyboard 4A (cerita: Haris beralih ke keramba rumput laut) +
ref-reef-underwater_v001.jpg (warna air) + palette. Tidak ada foto yang dipakai
sebagai tekstur.

Skrip ini TIDAK menyimpan file; penyimpanan dilakukan setelah verifikasi.
"""

import bpy
import math
import random
from mathutils import Vector

PAL = {
    "teal": "#1FA3A3",
    "deep": "#0F5C63",
    "reef": "#3E8E6E",
    "orange": "#E4713C",
    "sand": "#E8D5B0",
    "bone": "#F2E9DC",
}

MAT_BAMBOO, MAT_LINE, MAT_FLOAT, MAT_WEED, MAT_WEED_DARK = 0, 1, 2, 3, 4

W, D = 4.0, 3.0        # petak (m)
Z_TOP = 1.20           # tiang menonjol di atas air
Z_BOTTOM = -1.45       # ujung bawah tiang
Z_LINE = -0.15         # tali bentang di bawah permukaan
R_POST = 0.045
R_RAIL = 0.035
R_LINE = 0.008

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
        spec.default_value = 0.3
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


def add_tube(V, F, FM, FS, points, radii, sides, mat=0, smooth=True, caps=True):
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
    if caps:
        F.append(tuple(base + j for j in range(sides)))
        FM.append(mat)
        FS.append(False)
        last = base + (len(points) - 1) * sides
        F.append(tuple(last + j for j in reversed(range(sides))))
        FM.append(mat)
        FS.append(False)


def add_bamboo(V, F, FM, FS, p0, p1, r, sides=12, mat=0, nodes=4):
    """Tabung bambu dengan sedikit pembengkakan di ruas (node)."""
    p0, p1 = Vector(p0), Vector(p1)
    steps = max(6, nodes * 3)
    pts, radii = [], []
    for i in range(steps + 1):
        t = i / steps
        bump = 1.0 + 0.10 * math.sin(t * nodes * 2.0 * math.pi) ** 2
        pts.append(p0.lerp(p1, t))
        radii.append(r * bump)
    add_tube(V, F, FM, FS, pts, radii, sides, mat=mat)


def add_ribbon(V, F, FM, FS, top, length, width, rng, mat=0, segs=7, sway=0.06):
    """Satu helai rumput laut: pita menggantung, sedikit melengkung & menyempit."""
    top = Vector(top)
    dir_xy = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), 0))
    dir_xy = dir_xy.normalized() if dir_xy.length > 1e-6 else Vector((1, 0, 0))
    twist = rng.uniform(-0.5, 0.5)

    rows = []
    for i in range(segs + 1):
        t = i / segs
        z = top.z - length * t
        bend = sway * (t ** 1.7)
        cx = top.x + dir_xy.x * bend + math.sin(t * 3.1 + twist) * 0.012
        cy = top.y + dir_xy.y * bend + math.cos(t * 2.7 + twist) * 0.012
        # lebar menyempit, ujung runcing
        half = width * 0.5 * (1.0 - 0.82 * t)
        side = Vector((-dir_xy.y, dir_xy.x, 0)) * half
        rows.append((Vector((cx, cy, z)) - side, Vector((cx, cy, z)) + side))

    base = len(V)
    for a, b in rows:
        V.append(a)
        V.append(b)
    for i in range(segs):
        a0 = base + i * 2
        b0 = a0 + 2
        F.append((a0, a0 + 1, b0 + 1, b0))
        FM.append(mat)
        FS.append(True)
        # sisi belakang: winding terbalik supaya tidak tampak gelap
        F.append((b0, b0 + 1, a0 + 1, a0))
        FM.append(mat)
        FS.append(True)


# ---------------------------------------------------------------------------
# bagian-bagian
# ---------------------------------------------------------------------------


def post_positions():
    xs = (-W * 0.5, 0.0, W * 0.5)
    ys = (-D * 0.5, D * 0.5)
    return [(x, y) for x in xs for y in ys]


def build_rack(m_bamboo, m_line, collection):
    V, F, FM, FS = [], [], [], []

    for (x, y) in post_positions():
        add_bamboo(V, F, FM, FS, (x, y, Z_BOTTOM), (x, y, Z_TOP), R_POST,
                   mat=MAT_BAMBOO, nodes=6)
        # ujung atas tiang sedikit miring keluar (bambu dipotong)
        add_bamboo(V, F, FM, FS, (x, y, Z_TOP - 0.02),
                   (x * 1.02, y * 1.04, Z_TOP + 0.06), R_POST * 0.92,
                   mat=MAT_BAMBOO, nodes=1)

    # 2 rel atas memanjang
    for y in (-D * 0.5, D * 0.5):
        add_bamboo(V, F, FM, FS, (-W * 0.5, y, Z_TOP - 0.06),
                   (W * 0.5, y, Z_TOP - 0.06), R_RAIL, mat=MAT_BAMBOO, nodes=5)

    # 2 palang melintang di ujung + 1 di tengah
    for x in (-W * 0.5, 0.0, W * 0.5):
        add_bamboo(V, F, FM, FS, (x, -D * 0.5, Z_TOP - 0.10),
                   (x, D * 0.5, Z_TOP - 0.10), R_RAIL * 0.8, mat=MAT_BAMBOO, nodes=3)

    # ikatan tali di 4 sudut + tengah rel
    for (x, y) in post_positions():
        for dz in (-0.05, 0.02):
            ring = []
            seg = 12
            for k in range(seg + 1):
                a = 2.0 * math.pi * k / seg
                ring.append((x + (R_POST + 0.008) * math.cos(a),
                             y + (R_POST + 0.008) * math.sin(a),
                             Z_TOP - 0.06 + dz))
            add_tube(V, F, FM, FS, ring, [0.0055] * len(ring), 5,
                     mat=MAT_LINE, caps=False)

    return new_object("ENV_seaweed-farm_rack", V, F, [m_bamboo, m_line], FM, FS,
                      collection)


def build_lines(m_line, collection):
    V, F, FM, FS = [], [], [], []
    ys = (-0.92, 0.0, 0.92)

    for y in ys:
        # tali bentang sedikit melengkung (catenary) di bawah permukaan
        pts = []
        n = 18
        for i in range(n + 1):
            t = i / n
            x = -W * 0.5 + W * t
            sag = 0.10 * math.sin(math.pi * t)
            pts.append((x, y, Z_LINE - sag))
        add_tube(V, F, FM, FS, pts, [R_LINE] * len(pts), 6, mat=MAT_LINE,
                 caps=False)

        # tali penambat dari rel atas ke tali bentang di 3 titik
        for x in (-W * 0.5 + 0.05, 0.0, W * 0.5 - 0.05):
            y_rail = -D * 0.5 if y < 0 else (D * 0.5 if y > 0 else (D * 0.5 if y == 0 else y))
            add_tube(V, F, FM, FS,
                     [(x, y_rail, Z_TOP - 0.08), (x, y, Z_LINE - 0.02)],
                     [R_LINE * 0.85, R_LINE * 0.85], 5, mat=MAT_LINE, caps=False)

    return new_object("ENV_seaweed-farm_line", V, F, [m_line], FM, FS, collection)


def build_floats(m_float, m_line, collection):
    V, F, FM, FS = [], [], [], []
    spots = [(-1.35, -0.92), (1.30, -0.92), (-0.60, 0.0), (0.75, 0.0), (1.55, 0.92)]

    for (x, y) in spots:
        # pelampung: dua kerucut terpancung (bentuk pelampung tali)
        top = (x, y, Z_LINE + 0.055)
        bot = (x, y, Z_LINE + 0.015)
        add_tube(V, F, FM, FS, [bot, top], [0.032, 0.020], 12, mat=MAT_FLOAT)
        add_tube(V, F, FM, FS, [(x, y, Z_LINE + 0.055), (x, y, Z_LINE + 0.075)],
                 [0.020, 0.010], 10, mat=MAT_FLOAT)
        # tali pengikat pendek
        add_tube(V, F, FM, FS,
                 [(x, y, Z_LINE), (x, y, Z_LINE + 0.018)],
                 [0.006, 0.006], 5, mat=MAT_LINE, caps=False)

    return new_object("ENV_seaweed-farm_float", V, F, [m_float, m_line], FM, FS,
                      collection)


def build_weed(name, spots, m_weed, m_dark, collection, seed, ribbons=15):
    rng = random.Random(seed)
    V, F, FM, FS = [], [], [], []
    mats = [m_weed, m_dark]

    for (x, y) in spots:
        for k in range(ribbons):
            # sebaran titik gantung di sekitar tali
            px = x + rng.uniform(-0.34, 0.34)
            py = y + rng.uniform(-0.06, 0.06)
            length = rng.uniform(0.45, 0.85)
            width = rng.uniform(0.062, 0.105)
            mat_index = 0 if rng.random() < 0.72 else 1
            add_ribbon(V, F, FM, FS, (px, py, Z_LINE - 0.02), length, width, rng,
                       mat=mat_index, segs=7, sway=rng.uniform(0.04, 0.11))
            # tangkai kecil penghubung ke tali
            add_tube(V, F, FM, FS,
                     [(px, py, Z_LINE), (px, py, Z_LINE - 0.03)],
                     [0.004, 0.003], 4, mat=mat_index, caps=False)

    return new_object(name, V, F, mats, FM, FS, collection)


# ---------------------------------------------------------------------------
# scene & pratinjau
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
    scn.frame_end = 96
    scn.frame_set(1)
    col = bpy.data.collections.new(col_name)
    scn.collection.children.link(col)
    return scn, col


def setup_preview(scn, cam_loc, cam_target, lens=35.0):
    prev = bpy.data.collections.new("PREVIEW")
    scn.collection.children.link(prev)

    ground_mat = material("MAT_preview-ground", "1E2A2E", roughness=0.95)
    mesh = bpy.data.meshes.new("PREVIEW_ground")
    mesh.from_pydata(
        [(-14, -14, Z_BOTTOM - 0.02), (14, -14, Z_BOTTOM - 0.02),
         (14, 14, Z_BOTTOM - 0.02), (-14, 14, Z_BOTTOM - 0.02)],
        [], [(0, 1, 2, 3)],
    )
    mesh.materials.append(ground_mat)
    mesh.update()
    prev.objects.link(bpy.data.objects.new("PREVIEW_ground", mesh))

    # bidang air semi-transparan sebagai penanda permukaan z 0
    water_mat = material("MAT_preview-water", PAL["teal"], roughness=0.25)
    water_mat.blend_method = "BLEND"
    bsdf = next(n for n in water_mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Alpha"].default_value = 0.22
    wmesh = bpy.data.meshes.new("PREVIEW_water")
    wmesh.from_pydata(
        [(-7.5, -7.5, 0.0), (7.5, -7.5, 0.0), (7.5, 7.5, 0.0), (-7.5, 7.5, 0.0)],
        [], [(0, 1, 2, 3)],
    )
    wmesh.materials.append(water_mat)
    wmesh.update()
    prev.objects.link(bpy.data.objects.new("PREVIEW_water", wmesh))

    cam_data = bpy.data.cameras.new("CAM_preview")
    cam_data.lens = lens
    cam = bpy.data.objects.new("CAM_preview", cam_data)
    prev.objects.link(cam)
    cam.location = cam_loc
    cam.rotation_euler = (Vector(cam_target) - Vector(cam_loc)).normalized().to_track_quat(
        "-Z", "Y"
    ).to_euler()
    scn.camera = cam

    key = bpy.data.objects.new("LGT_preview-key", bpy.data.lights.new("LGT_preview-key", "SUN"))
    prev.objects.link(key)
    key.data.energy = 3.4
    key.data.angle = math.radians(5)
    key.rotation_euler = (math.radians(48), 0.0, math.radians(24))

    fill = bpy.data.objects.new("LGT_preview-fill", bpy.data.lights.new("LGT_preview-fill", "AREA"))
    prev.objects.link(fill)
    fill.data.energy = 320.0
    fill.data.size = 7.0
    fill.location = (-5.0, -6.0, 4.0)
    fill.rotation_euler = (Vector((0, 0, 0)) - fill.location).normalized().to_track_quat(
        "-Z", "Y"
    ).to_euler()

    rim = bpy.data.objects.new("LGT_preview-rim", bpy.data.lights.new("LGT_preview-rim", "AREA"))
    prev.objects.link(rim)
    rim.data.energy = 160.0
    rim.data.size = 5.0
    rim.location = (5.0, 4.0, 3.5)
    rim.rotation_euler = (Vector((0, 0, 0.4)) - rim.location).normalized().to_track_quat(
        "-Z", "Y"
    ).to_euler()

    world = bpy.data.worlds.new("WLD_seaweed-farm-preview")
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.10, 0.17, 0.19, 1.0)
    bg.inputs["Strength"].default_value = 1.0
    scn.world = world
    return cam


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main():
    scn, col = setup_scene("ENV_seaweed-farm")

    m_bamboo = material("MAT_seaweed_bamboo", PAL["sand"], roughness=0.78)
    m_line = material("MAT_seaweed_line", PAL["bone"], roughness=0.85)
    m_float = material("MAT_seaweed_float", PAL["orange"], roughness=0.45)
    m_weed = material("MAT_seaweed_weed", PAL["reef"], roughness=0.70)
    m_weed_dark = material("MAT_seaweed_weed-dark", PAL["deep"], roughness=0.70)

    rack = build_rack(m_bamboo, m_line, col)
    lines = build_lines(m_line, col)
    floats = build_floats(m_float, m_line, col)
    weed_a = build_weed("ENV_seaweed-farm_weed_a", [(-1.30, -0.92), (-0.55, 0.0)],
                        m_weed, m_weed_dark, col, seed=31)
    weed_b = build_weed("ENV_seaweed-farm_weed_b", [(0.35, 0.0), (-0.25, 0.92)],
                        m_weed, m_weed_dark, col, seed=47)
    weed_c = build_weed("ENV_seaweed-farm_weed_c", [(1.20, -0.92), (1.05, 0.92)],
                        m_weed, m_weed_dark, col, seed=59)

    setup_preview(scn, (5.6, -6.6, 3.4), (0.0, 0.0, -0.15), lens=34.0)

    print("=== RINGKASAN seaweed-farm ===")
    total_v = 0
    for obj in (rack, lines, floats, weed_a, weed_b, weed_c):
        d = obj.dimensions
        total_v += len(obj.data.vertices)
        print(f"{obj.name}: verts={len(obj.data.vertices)} faces={len(obj.data.polygons)} "
              f"dims=({d.x:.3f}, {d.y:.3f}, {d.z:.3f}) m")
    print("total verts:", total_v)
    print("materials:", [m.name for m in bpy.data.materials])
    print("collections:", [c.name for c in bpy.data.collections])
    print("engine:", scn.render.engine, "vt:", scn.view_settings.view_transform,
          "res:", scn.render.resolution_x, scn.render.resolution_y, "fps:", scn.render.fps,
          "frame:", scn.frame_current)


main()

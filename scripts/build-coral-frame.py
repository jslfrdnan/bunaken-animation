"""
Membangun aset props Scene 4: kerangka transplantasi karang (coral frame).

Hasil: assets/props/coral-frame.blend (koleksi PRP_coral-frame)
  PRP_coral-frame_rack     -> rangka pipa besi ringan 1,50 x 1,00 m, tinggi
                              0,35 m: 4 kaki, 2 rel memanjang, 3 rel melintang,
                              kisi kawat di atas, 4 pelat sambung.
  PRP_coral-frame_frag_a   -> karang bercabang kecil (staghorn) di atas rangka
  PRP_coral-frame_frag_b   -> karang massif kecil (boulder)
  PRP_coral-frame_frag_c   -> karang meja kecil di atas potongan pipa

Origin semua objek di (0,0,0) = dasar laut, rangka berdiri di z 0. Skala nyata.

Warna: besi gelap teal dalam #0F5C63, karang hijau terumbu #3E8E6E, krem tulang
#F2E9DC, aksen oranye karang #E4713C — palette PROJECT.md §2. Tanpa tekstur image.

Acuan: pengecualian environment/props lead 1 Nov 2026 (AGENTS.md §2.1) — panel
storyboard 4A (cerita: kerangka transplantasi karang ditanam di dasar) +
ref-reef-underwater_v001.jpg (bentuk karang) + palette. Tidak ada foto yang
dipakai sebagai tekstur.

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

MAT_METAL = 0
MAT_CORAL = 0
MAT_CORAL_DARK = 1

LEN_X = 1.50          # panjang rangka (m)
LEN_Y = 1.00          # lebar rangka (m)
H_RACK = 0.35         # tinggi rangka (m)
R_PIPE = 0.021        # jari-jari pipa
R_WIRE = 0.0045       # jari-jari kisi kawat

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


def add_uvsphere(V, F, FM, FS, center, r, seg=24, rings=14, mat=0, smooth=True,
                 squash=(1.0, 1.0, 1.0)):
    top = len(V)
    V.append(Vector((center[0], center[1], center[2] + r * squash[2])))
    ring_start = []
    for ir in range(1, rings):
        th = math.pi * ir / rings
        start = len(V)
        for isg in range(seg):
            ph = 2.0 * math.pi * isg / seg
            V.append(Vector((
                center[0] + r * squash[0] * math.sin(th) * math.cos(ph),
                center[1] + r * squash[1] * math.sin(th) * math.sin(ph),
                center[2] + r * squash[2] * math.cos(th),
            )))
        ring_start.append(start)
    bot = len(V)
    V.append(Vector((center[0], center[1], center[2] - r * squash[2])))

    first = ring_start[0]
    for isg in range(seg):
        isg2 = (isg + 1) % seg
        F.append((top, first + isg, first + isg2))
        FM.append(mat)
        FS.append(smooth)
    for k in range(len(ring_start) - 1):
        a0, b0 = ring_start[k], ring_start[k + 1]
        for isg in range(seg):
            isg2 = (isg + 1) % seg
            F.append((a0 + isg, b0 + isg, b0 + isg2, a0 + isg2))
            FM.append(mat)
            FS.append(smooth)
    last = ring_start[-1]
    for isg in range(seg):
        isg2 = (isg + 1) % seg
        F.append((bot, last + isg2, last + isg))
        FM.append(mat)
        FS.append(smooth)


def add_disc(V, F, FM, FS, center, r, thickness, seg=28, mat=0, smooth=True):
    cx, cy, cz = center
    base = len(V)
    top_ring, bot_ring = [], []
    for isg in range(seg):
        a = 2.0 * math.pi * isg / seg
        x, y = cx + r * math.cos(a), cy + r * math.sin(a)
        top_ring.append(len(V))
        V.append(Vector((x, y, cz + thickness * 0.5)))
        bot_ring.append(len(V))
        V.append(Vector((x, y, cz - thickness * 0.5)))
    ct = len(V)
    V.append(Vector((cx, cy, cz + thickness * 0.5)))
    cb = len(V)
    V.append(Vector((cx, cy, cz - thickness * 0.5)))
    for isg in range(seg):
        isg2 = (isg + 1) % seg
        F.append((ct, top_ring[isg], top_ring[isg2]))
        FM.append(mat)
        FS.append(smooth)
        F.append((cb, bot_ring[isg2], bot_ring[isg]))
        FM.append(mat)
        FS.append(smooth)
        F.append((top_ring[isg], bot_ring[isg], bot_ring[isg2], top_ring[isg2]))
        FM.append(mat)
        FS.append(smooth)


def add_branch(V, F, FM, FS, origin, direction, length, r0, r1, depth, rng,
               mat=0, spread=0.55):
    direction = Vector(direction).normalized()
    steps = max(2, int(length / 0.045))
    pts = []
    start = Vector(origin)
    bend = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(0.1, 0.9)))
    for i in range(steps + 1):
        t = i / steps
        p = start + direction * (length * t) + bend * (spread * 0.12 * t * t)
        pts.append(p)
    radii = [r0 + (r1 - r0) * (i / steps) for i in range(steps + 1)]
    add_tube(V, F, FM, FS, pts, radii, 7, mat=mat)
    if depth <= 0:
        return
    n_child = rng.randint(2, 3)
    for _ in range(n_child):
        idx = rng.randint(max(1, steps // 3), steps)
        base_p = pts[idx]
        axis = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(0.25, 1)))
        child_dir = (direction * 0.55 + axis.normalized() * 0.85).normalized()
        add_branch(
            V, F, FM, FS, base_p, child_dir, length * rng.uniform(0.36, 0.55),
            radii[idx] * 0.72, radii[idx] * 0.5, depth - 1, rng, mat=mat,
            spread=spread * 0.8,
        )


# ---------------------------------------------------------------------------
# bagian-bagian
# ---------------------------------------------------------------------------


def build_rack(m_metal, collection):
    V, F, FM, FS = [], [], [], []

    hx, hy = LEN_X * 0.5, LEN_Y * 0.5
    z_top = H_RACK

    # 4 kaki
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = sx * (hx - 0.04), sy * (hy - 0.04)
            add_tube(V, F, FM, FS,
                     [(x, y, 0.0), (x, y, z_top)], [R_PIPE, R_PIPE], 10, mat=MAT_METAL)
            # pelat kaki
            add_tube(V, F, FM, FS,
                     [(x, y, 0.0), (x, y, 0.012)], [R_PIPE * 2.1, R_PIPE * 2.1], 12,
                     mat=MAT_METAL)

    # 2 rel memanjang di atas
    for sy in (-1, 1):
        y = sy * (hy - 0.04)
        add_tube(V, F, FM, FS,
                 [(-hx, y, z_top), (hx, y, z_top)], [R_PIPE, R_PIPE], 10,
                 mat=MAT_METAL)

    # 3 rel melintang
    for x in (-hx + 0.04, 0.0, hx - 0.04):
        add_tube(V, F, FM, FS,
                 [(x, -hy, z_top), (x, hy, z_top)], [R_PIPE, R_PIPE], 10,
                 mat=MAT_METAL)

    # 4 sambungan (socket) di titik silang
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = sx * (hx - 0.04), sy * (hy - 0.04)
            add_tube(V, F, FM, FS,
                     [(x, y, z_top - 0.018), (x, y, z_top + 0.018)],
                     [R_PIPE * 1.45, R_PIPE * 1.45], 12, mat=MAT_METAL)

    # kisi kawat: 5 garis memanjang + 7 garis melintang, sedikit di bawah rel
    z_wire = z_top - 0.012
    for i in range(5):
        y = -hy + 0.10 + (LEN_Y - 0.20) * i / 4.0
        add_tube(V, F, FM, FS,
                 [(-hx + 0.05, y, z_wire), (hx - 0.05, y, z_wire)],
                 [R_WIRE, R_WIRE], 5, mat=MAT_METAL, caps=False)
    for i in range(7):
        x = -hx + 0.09 + (LEN_X - 0.18) * i / 6.0
        add_tube(V, F, FM, FS,
                 [(x, -hy + 0.05, z_wire), (x, hy - 0.05, z_wire)],
                 [R_WIRE, R_WIRE], 5, mat=MAT_METAL, caps=False)

    # 2 penyangga diagonal di sisi pendek (biar terbaca rangka, bukan meja)
    for sy in (-1, 1):
        y = sy * (hy - 0.04)
        add_tube(V, F, FM, FS,
                 [(-hx + 0.04, y, 0.02), (-0.30, y, z_top - 0.03)],
                 [R_PIPE * 0.72, R_PIPE * 0.72], 8, mat=MAT_METAL)
        add_tube(V, F, FM, FS,
                 [(hx - 0.04, y, 0.02), (0.30, y, z_top - 0.03)],
                 [R_PIPE * 0.72, R_PIPE * 0.72], 8, mat=MAT_METAL)

    return new_object("PRP_coral-frame_rack", V, F, [m_metal], FM, FS, collection)


def build_frag_branching(m_coral, m_dark, collection):
    rng = random.Random(7)
    V, F, FM, FS = [], [], [], []
    origin = Vector((-0.46, -0.20, H_RACK - 0.045))
    # potongan karang mati di dasar fragmen
    add_uvsphere(V, F, FM, FS, origin, 0.075, mat=MAT_CORAL_DARK,
                 squash=(1.15, 1.0, 0.55))
    for k in range(4):
        ang = 2.0 * math.pi * k / 4.0 + 0.4
        d = Vector((math.cos(ang) * 0.42, math.sin(ang) * 0.42, 1.0))
        add_branch(V, F, FM, FS,
                   origin + Vector((0, 0, 0.035)), d,
                   rng.uniform(0.13, 0.19), 0.019, 0.010, 1, rng, mat=MAT_CORAL)
    return new_object("PRP_coral-frame_frag_a", V, F, [m_coral, m_dark], FM, FS,
                      collection)


def build_frag_massive(m_coral, m_dark, collection):
    rng = random.Random(23)
    V, F, FM, FS = [], [], [], []
    cx, cy = 0.10, 0.18
    base_z = H_RACK - 0.03
    # bongkahan: 3 bola saling tumpang tindih dengan skala berbeda
    for (dx, dy, dz, r, sq) in (
        (0.0, 0.0, 0.055, 0.105, (1.05, 0.95, 0.72)),
        (0.075, 0.035, 0.085, 0.062, (1.0, 0.9, 0.85)),
        (-0.070, 0.045, 0.048, 0.052, (0.95, 1.0, 0.7)),
    ):
        add_uvsphere(V, F, FM, FS, (cx + dx, cy + dy, base_z + dz), r,
                     seg=20, rings=12, mat=MAT_CORAL, squash=sq)
    # beberapa tonjolan kecil di permukaan (polip)
    for _ in range(9):
        a = rng.uniform(0, 2 * math.pi)
        rr = rng.uniform(0.02, 0.09)
        add_uvsphere(V, F, FM, FS,
                     (cx + rr * math.cos(a), cy + rr * math.sin(a),
                      base_z + rng.uniform(0.10, 0.16)),
                     rng.uniform(0.014, 0.024), seg=10, rings=6, mat=MAT_CORAL)
    return new_object("PRP_coral-frame_frag_b", V, F, [m_coral, m_dark], FM, FS,
                      collection)


def build_frag_table(m_coral, m_dark, collection):
    V, F, FM, FS = [], [], [], []
    cx, cy = 0.46, -0.20
    base_z = H_RACK - 0.03
    # batang pendek
    add_tube(V, F, FM, FS,
             [(cx, cy, base_z), (cx, cy, base_z + 0.075)],
             [0.030, 0.022], 10, mat=MAT_CORAL_DARK)
    # meja: dua cakram bertumpuk
    add_disc(V, F, FM, FS, (cx, cy, base_z + 0.085), 0.125, 0.016, mat=MAT_CORAL)
    add_disc(V, F, FM, FS, (cx + 0.03, cy - 0.02, base_z + 0.100), 0.082, 0.012,
             mat=MAT_CORAL)
    return new_object("PRP_coral-frame_frag_c", V, F, [m_coral, m_dark], FM, FS,
                      collection)


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


def setup_preview(scn, cam_loc, cam_target, lens=45.0):
    prev = bpy.data.collections.new("PREVIEW")
    scn.collection.children.link(prev)

    ground_mat = material("MAT_preview-ground", "2E383A", roughness=0.95)
    mesh = bpy.data.meshes.new("PREVIEW_ground")
    mesh.from_pydata(
        [(-8, -8, -0.005), (8, -8, -0.005), (8, 8, -0.005), (-8, 8, -0.005)],
        [], [(0, 1, 2, 3)],
    )
    mesh.materials.append(ground_mat)
    mesh.update()
    prev.objects.link(bpy.data.objects.new("PREVIEW_ground", mesh))

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
    key.data.energy = 3.2
    key.data.angle = math.radians(6)
    key.rotation_euler = (math.radians(50), 0.0, math.radians(28))

    fill = bpy.data.objects.new("LGT_preview-fill", bpy.data.lights.new("LGT_preview-fill", "AREA"))
    prev.objects.link(fill)
    fill.data.energy = 160.0
    fill.data.size = 5.0
    fill.location = (-2.6, -3.4, 2.2)
    fill.rotation_euler = (Vector((0, 0, 0.4)) - fill.location).normalized().to_track_quat(
        "-Z", "Y"
    ).to_euler()

    rim = bpy.data.objects.new("LGT_preview-rim", bpy.data.lights.new("LGT_preview-rim", "AREA"))
    prev.objects.link(rim)
    rim.data.energy = 90.0
    rim.data.size = 4.0
    rim.location = (3.0, 2.4, 2.4)
    rim.rotation_euler = (Vector((0, 0, 0.4)) - rim.location).normalized().to_track_quat(
        "-Z", "Y"
    ).to_euler()

    world = bpy.data.worlds.new("WLD_coral-frame-preview")
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.07, 0.09, 0.10, 1.0)
    bg.inputs["Strength"].default_value = 1.0
    scn.world = world
    return cam


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main():
    scn, col = setup_scene("PRP_coral-frame")

    m_metal = material("MAT_coral-frame_metal", PAL["deep"], roughness=0.38, metallic=0.65)
    m_coral = material("MAT_coral-frame_coral", PAL["reef"], roughness=0.72)
    m_dark = material("MAT_coral-frame_coral-dead", PAL["bone"], roughness=0.85)
    m_accent = material("MAT_coral-frame_accent", PAL["orange"], roughness=0.55)

    rack = build_rack(m_metal, col)
    frag_a = build_frag_branching(m_coral, m_dark, col)
    frag_b = build_frag_massive(m_coral, m_dark, col)
    frag_c = build_frag_table(m_coral, m_dark, col)
    # pelat penanda oranye kecil di rel depan
    V, F, FM, FS = [], [], [], []
    add_tube(V, F, FM, FS, [(0.28, -LEN_Y * 0.5 + 0.02, H_RACK),
                            (0.28, -LEN_Y * 0.5 + 0.02, H_RACK + 0.075)],
             [0.008, 0.008], 6, mat=0)
    tag = new_object("PRP_coral-frame_tag", V, F, [m_accent], FM, FS, col)
    tag.hide_render = False

    setup_preview(scn, (2.35, -2.75, 1.60), (0.0, 0.0, 0.30), lens=44.0)

    print("=== RINGKASAN coral-frame ===")
    total_v = 0
    for obj in (rack, frag_a, frag_b, frag_c, tag):
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

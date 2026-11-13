"""
Membangun aset props Scene 2: jaring dasar (gillnet) yang terbentang di dasar.

Hasil: assets/props/fishing-net-spread.blend (koleksi PRP_gear)
  PRP_gear_net-spread -> jaring terbentang 4,0 x 3,0 m di dasar, pola belah
                         ketupat, mata 9,5 cm knot-ke-knot, tepi robek di tiga
                         tempat, satu sudut tergulung. Origin di dasar (z 0)
                         tepat di tengah jaring.
  PRP_gear_net-float  -> 9 pelampung kecil di tali ris sisi +Y
  PRP_gear_net-rope   -> tali ris keliling + tali pelampung + ujung tali putus

Warna: teal dalam (#0F5C63) untuk benang, krem tulang (#F2E9DC) untuk tali dan
pelampung — palette PROJECT.md §2. Tanpa tekstur image.
Semua geometri prosedural.

Acuan: pengecualian environment/props lead 1 Nov 2026 (AGENTS.md §2.1) —
panel storyboard 2A/3B (jaring dasar) + ref-perahu-bercadik_v001.jpg (warna
tali/pelampung) + palette. Foto hanya acuan bentuk & warna, bukan tekstur.

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

MAT_TWINE, MAT_ROPE = 0, 1

# ukuran jaring (m)
W, D = 4.0, 3.0
A = 0.095            # jarak knot (mata jaring 9,5 cm)
R_TWINE = 0.0028
R_ROPE = 0.0095

# lubang/robekan (x, y, radius)
HOLES = ((-1.32, 0.72, 0.34), (0.92, -0.62, 0.30), (1.58, 0.92, 0.24))

# ---------------------------------------------------------------------------
# utilitas
# ---------------------------------------------------------------------------


def srgb(hexstr):
    h = hexstr.lstrip("#")
    values = [int(h[i : i + 2], 16) / 255.0 for i in (0, 2, 4)]

    def to_linear(u):
        return u / 12.92 if u <= 0.04045 else ((u + 0.055) / 1.055) ** 2.4

    return tuple(to_linear(v) for v in values) + (1.0,)


def material(name, hexcol, roughness=0.8, metallic=0.0):
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


def add_tube(verts, faces, fmat, fsmooth, points, radii, sides, mat=0, smooth=True):
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


# ---------------------------------------------------------------------------
# permukaan jaring di dasar
# ---------------------------------------------------------------------------


def net_z(x, y):
    """Tinggi jaring: gelombang pasir + lipatan + sudut tergulung + tepi menumpuk."""
    z = 0.012
    z += 0.030 * math.sin(1.55 * x + 0.9) * math.cos(1.15 * y - 0.4)
    z += 0.014 * math.sin(2.4 * x - 1.7 * y + 0.3)
    z += 0.006 * math.sin(37.1 * x + 17.3 * y)
    # sudut tergulung (tersangkut saat ditarik)
    d = math.hypot(x + 1.55, y - 1.02)
    if d < 0.78:
        z += 0.30 * (1.0 - d / 0.78) ** 1.7
    # tepi menumpuk sedikit
    edge = max(abs(x) / (W / 2.0), abs(y) / (D / 2.0))
    if edge > 0.86:
        z += 0.035 * (edge - 0.86) / 0.14
    return max(z, 0.006)


def in_hole(x, y):
    for (hx, hy, hr) in HOLES:
        if (x - hx) ** 2 + (y - hy) ** 2 < hr * hr:
            return True
    return False


# ---------------------------------------------------------------------------
# jaring
# ---------------------------------------------------------------------------


def build_net(m_twine, collection):
    V, F, FM, FS = [], [], [], []
    e1 = Vector((0.70710678, 0.70710678))
    e2 = Vector((0.70710678, -0.70710678))

    N = int((W / 2.0 + D / 2.0) / (A * 0.70710678)) + 3
    knots = {}
    for i in range(-N, N + 1):
        for j in range(-N, N + 1):
            x = A * (i + j) * 0.70710678
            y = A * (i - j) * 0.70710678
            if abs(x) <= W / 2.0 and abs(y) <= D / 2.0:
                knots[(i, j)] = Vector((x, y, net_z(x, y)))

    # jalur benang arah e1 (j tetap) dan e2 (i tetap); segmen dipotong di lubang
    def emit_run(run):
        if len(run) >= 2:
            add_tube(V, F, FM, FS, run, [R_TWINE] * len(run), 4, mat=MAT_TWINE)

    for j in range(-N, N + 1):
        run = []
        for i in range(-N - 1, N + 2):
            p = knots.get((i, j))
            if p is None:
                if len(run) >= 2:
                    emit_run(run)
                run = []
                continue
            if run and in_hole(*(0.5 * (p.x + run[-1].x), 0.5 * (p.y + run[-1].y))):
                emit_run(run)
                run = [p]
                continue
            if in_hole(p.x, p.y) and len(run) >= 2:
                emit_run(run)
                run = []
                continue
            run.append(p)
        if len(run) >= 2:
            emit_run(run)

    for i in range(-N, N + 1):
        run = []
        for j in range(-N - 1, N + 2):
            p = knots.get((i, j))
            if p is None:
                if len(run) >= 2:
                    emit_run(run)
                run = []
                continue
            if run and in_hole(*(0.5 * (p.x + run[-1].x), 0.5 * (p.y + run[-1].y))):
                emit_run(run)
                run = [p]
                continue
            if in_hole(p.x, p.y) and len(run) >= 2:
                emit_run(run)
                run = []
                continue
            run.append(p)
        if len(run) >= 2:
            emit_run(run)

    # benang lepas di tepi robekan (ujung menggantung)
    rng = random.Random(2201)
    for (hx, hy, hr) in HOLES:
        for k in range(7):
            a = 2.0 * math.pi * k / 7 + rng.uniform(-0.3, 0.3)
            px, py = hx + (hr + 0.02) * math.cos(a), hy + (hr + 0.02) * math.sin(a)
            p0 = Vector((px, py, net_z(px, py)))
            tip = p0 + Vector((0.14 * math.cos(a + 0.5), 0.14 * math.sin(a + 0.5),
                               rng.uniform(-0.01, 0.04)))
            add_tube(V, F, FM, FS, [p0, (p0 + tip) * 0.5 + Vector((0, 0, 0.01)), tip],
                     [R_TWINE, R_TWINE * 0.8, R_TWINE * 0.5], 4, mat=MAT_TWINE)

    # benang tergulung di sudut yang tersangkut
    for k in range(9):
        a = rng.uniform(0.0, 2.0 * math.pi)
        r0 = rng.uniform(0.10, 0.55)
        x0, y0 = -1.55 + r0 * math.cos(a), 1.02 + r0 * math.sin(a)
        p0 = Vector((x0, y0, net_z(x0, y0) + 0.02))
        pts = []
        for s in range(6):
            t = s / 5.0
            x = x0 + 0.30 * t * math.cos(a + 2.1)
            y = y0 + 0.30 * t * math.sin(a + 2.1)
            pts.append(Vector((x, y, net_z(x, y) + 0.02 + 0.05 * math.sin(math.pi * t))))
        add_tube(V, F, FM, FS, pts, [R_TWINE] * 6, 4, mat=MAT_TWINE)

    return new_object("PRP_gear_net-spread", V, F, [m_twine], FM, FS, collection)


# ---------------------------------------------------------------------------
# tali ris keliling + tali pelampung
# ---------------------------------------------------------------------------


def build_rope(m_rope, collection):
    V, F, FM, FS = [], [], [], []

    def loop(points, radius):
        add_tube(V, F, FM, FS, points + [points[0]], [radius] * (len(points) + 1),
                 5, mat=MAT_ROPE)

    # keliling jaring (sedikit di dalam tepi)
    inset = 0.03
    side_x, side_y = W / 2.0 - inset, D / 2.0 - inset
    pts = []
    n = 42
    for k in range(n):  # +Y
        x = -side_x + 2.0 * side_x * k / n
        pts.append(Vector((x, side_y, net_z(x, side_y) + 0.012)))
    for k in range(n):  # +X
        y = side_y - 2.0 * side_y * k / n
        pts.append(Vector((side_x, y, net_z(side_x, y) + 0.012)))
    for k in range(n):  # -Y
        x = side_x - 2.0 * side_x * k / n
        pts.append(Vector((x, -side_y, net_z(x, -side_y) + 0.012)))
    for k in range(n):  # -X
        y = -side_y + 2.0 * side_y * k / n
        pts.append(Vector((-side_x, y, net_z(-side_x, y) + 0.012)))
    loop(pts, R_ROPE)

    # tali pelampung di sisi +Y: sedikit melengkung ke atas
    fl = []
    for k in range(49):
        x = -1.95 + 3.9 * k / 48
        z = net_z(x, 1.38) + 0.055 + 0.012 * math.cos(math.pi * x / 1.95)
        fl.append(Vector((x, 1.38, z)))
    add_tube(V, F, FM, FS, fl, [0.009] * len(fl), 5, mat=MAT_ROPE)

    # dua ujung tali putus yang menjuntai ke pasir
    for (p0, p1) in (((2.00, -1.40, 0.03), (2.48, -1.78, 0.012)),
                     ((-2.00, 1.30, 0.03), (-2.44, 1.72, 0.012))):
        pts2 = []
        for s in range(8):
            t = s / 7.0
            pts2.append(Vector((p0[0] + (p1[0] - p0[0]) * t,
                                p0[1] + (p1[1] - p0[1]) * t,
                                p0[2] + (p1[2] - p0[2]) * t + 0.05 * math.sin(math.pi * t))))
        add_tube(V, F, FM, FS, pts2, [0.008] * len(pts2), 5, mat=MAT_ROPE)

    return new_object("PRP_gear_net-rope", V, F, [m_rope], FM, FS, collection)


# ---------------------------------------------------------------------------
# pelampung kecil
# ---------------------------------------------------------------------------


def build_floats(m_rope, collection):
    V, F, FM, FS = [], [], [], []
    seg, rings = 12, 6
    for k in range(9):
        x = -1.72 + 3.44 * k / 8
        cz = net_z(x, 1.38) + 0.075
        base = len(V)
        for ir in range(rings + 1):
            th = math.pi * ir / rings
            for isg in range(seg):
                ph = 2.0 * math.pi * isg / seg
                p = Vector((math.sin(th) * math.cos(ph), math.sin(th) * math.sin(ph), math.cos(th)))
                # pelampung telur kecil, sumbu panjang mengikuti tali (X)
                V.append(Vector((x + p.x * 0.062, 1.38 + p.y * 0.042, cz + p.z * 0.042)))
        for ir in range(rings):
            for isg in range(seg):
                a = base + ir * seg + isg
                b = base + ir * seg + (isg + 1) % seg
                c = base + (ir + 1) * seg + (isg + 1) % seg
                d = base + (ir + 1) * seg + isg
                F.append((a, b, c, d))
                FM.append(MAT_ROPE)
                FS.append(True)

    return new_object("PRP_gear_net-float", V, F, [m_rope], FM, FS, collection)


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
    scn.frame_set(1)
    col = bpy.data.collections.new(col_name)
    scn.collection.children.link(col)
    return scn, col


def setup_preview(scn, cam_loc, cam_target, lens=42.0):
    prev = bpy.data.collections.new("PREVIEW")
    scn.collection.children.link(prev)

    ground_mat = material("MAT_preview-ground", "2E383A", roughness=0.95)
    mesh = bpy.data.meshes.new("PREVIEW_ground")
    mesh.from_pydata(
        [(-14, -14, -0.005), (14, -14, -0.005), (14, 14, -0.005), (-14, 14, -0.005)],
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
    key.data.energy = 2.8
    key.data.angle = math.radians(6)
    key.rotation_euler = (math.radians(48), 0.0, math.radians(26))

    fill = bpy.data.objects.new("LGT_preview-fill", bpy.data.lights.new("LGT_preview-fill", "AREA"))
    prev.objects.link(fill)
    fill.data.energy = 180.0
    fill.data.size = 7.0
    fill.location = (-4.0, -6.0, 4.0)
    fill.rotation_euler = (Vector((0, 0, 0.2)) - fill.location).normalized().to_track_quat(
        "-Z", "Y"
    ).to_euler()

    rim = bpy.data.objects.new("LGT_preview-rim", bpy.data.lights.new("LGT_preview-rim", "AREA"))
    prev.objects.link(rim)
    rim.data.energy = 90.0
    rim.data.size = 5.0
    rim.location = (5.0, 4.0, 3.0)
    rim.rotation_euler = (Vector((0, 0, 0.2)) - rim.location).normalized().to_track_quat(
        "-Z", "Y"
    ).to_euler()

    world = bpy.data.worlds.new("WLD_gear-preview")
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
    scn, col = setup_scene("PRP_gear")

    m_twine = material("MAT_gear-net_twine", PAL["deep"], roughness=0.55)
    m_rope = material("MAT_gear-net_rope", PAL["bone"], roughness=0.65)

    net = build_net(m_twine, col)
    rope = build_rope(m_rope, col)
    floats = build_floats(m_rope, col)

    setup_preview(scn, (0.0, -5.6, 3.6), (0.0, 0.0, 0.05), lens=40.0)

    print("=== RINGKASAN fishing-net-spread ===")
    total_v = 0
    for obj in (net, rope, floats):
        d = obj.dimensions
        total_v += len(obj.data.vertices)
        print(f"{obj.name}: verts={len(obj.data.vertices)} faces={len(obj.data.polygons)} "
              f"dims=({d.x:.2f}, {d.y:.2f}, {d.z:.2f}) m")
    print("total verts:", total_v)
    print("materials:", [m.name for m in bpy.data.materials])
    print("collections:", [c.name for c in bpy.data.collections])
    print("engine:", scn.render.engine, "vt:", scn.view_settings.view_transform,
          "res:", scn.render.resolution_x, scn.render.resolution_y, "fps:", scn.render.fps,
          "frame:", scn.frame_current)


main()

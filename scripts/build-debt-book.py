"""
Membangun aset props Scene 3: buku utang Pak Haris (debt book).

Hasil: assets/props/debt-book.blend (koleksi PRP_book)
  PRP_book_cover -> sampul kulit gelap 0,150 x 0,210 m, tebal 0,020 m, dibuka
                    datar menghadap ke atas; punggung buku di sisi -X,
                    dua papan sampul + punggung membulat.
  PRP_book_pages -> blok kertas krem 0,144 x 0,202 m x 0,014 m, sedikit
                    menjorok dari sampul, dengan garis tepi kertas.
  PRP_book_strap -> karet pengikat melintang + gesper kecil oranye.

Origin semua objek di (0,0,0) = dasar buku (buku tergeletak di permukaan).
Skala nyata. Dibuat untuk shot 050 Scene 3 (close-up tangan & buku).

Warna: kulit gelap #2E383A, kertas krem tulang #F2E9DC, karet teal dalam
#0F5C63, gesper oranye karang #E4713C — palette PROJECT.md §2. Tanpa tekstur.

Acuan: panel storyboard 3B (Nara menemukan buku utang di dalam perahu) +
palette. Tidak ada foto yang dipakai sebagai tekstur.

Skrip ini TIDAK menyimpan file; penyimpanan dilakukan setelah verifikasi.
"""

import bpy
import math
from mathutils import Vector

PAL = {
    "teal": "#1FA3A3",
    "deep": "#0F5C63",
    "reef": "#3E8E6E",
    "orange": "#E4713C",
    "sand": "#E8D5B0",
    "bone": "#F2E9DC",
    "dark": "#2E383A",
}

MAT_COVER, MAT_PAGES, MAT_STRAP, MAT_BUCKLE = 0, 1, 2, 3

W, D = 0.150, 0.210      # lebar (x) dan panjang (y) buku (m)
T_COVER = 0.0045         # tebal satu papan sampul
T_PAGES = 0.014          # tebal blok kertas
GAP = 0.0015             # celah kecil antara papan dan kertas

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


def add_tube(V, F, FM, FS, points, radii, sides, mat=0, smooth=True, caps=True,
             flat=None):
    """Tabung; flat=(a,b) memberi penampang persegi panjang (untuk karet)."""
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
            if flat is not None:
                fa, fb = flat
                ca = math.cos(a)
                sa = math.sin(a)
                da = math.copysign(abs(ca) ** 0.35, ca) * fa
                db = math.copysign(abs(sa) ** 0.35, sa) * fb
            else:
                da = math.cos(a) * radii[i]
                db = math.sin(a) * radii[i]
            V.append(p + n * da + b * db)
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


def add_box(V, F, FM, FS, center, half, mat=0, smooth=False, bevel=0.0):
    cx, cy, cz = center
    hx, hy, hz = half
    if bevel <= 0.0:
        base = len(V)
        for sx in (-1, 1):
            for sy in (-1, 1):
                for sz in (-1, 1):
                    V.append(Vector((cx + sx * hx, cy + sy * hy, cz + sz * hz)))
        # indeks: (sx,sy,sz) -> 0..7 dengan urutan x-major
        idx = {}
        k = 0
        for sx in (-1, 1):
            for sy in (-1, 1):
                for sz in (-1, 1):
                    idx[(sx, sy, sz)] = base + k
                    k += 1
        quads = [
            ((1, -1, -1), (1, 1, -1), (1, 1, 1), (1, -1, 1)),      # +X
            ((-1, 1, -1), (-1, -1, -1), (-1, -1, 1), (-1, 1, 1)),  # -X
            ((1, 1, -1), (-1, 1, -1), (-1, 1, 1), (1, 1, 1)),      # +Y
            ((-1, -1, -1), (1, -1, -1), (1, -1, 1), (-1, -1, 1)),  # -Y
            ((-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)),      # +Z
            ((-1, 1, -1), (1, 1, -1), (1, -1, -1), (-1, -1, -1)),  # -Z
        ]
        for q in quads:
            F.append(tuple(idx[c] for c in q))
            FM.append(mat)
            FS.append(smooth)
        return

    # kotak dengan sudut terpotong sederhana: 6 sisi grid + inset sudut
    seg = 3
    b = bevel
    face_defs = [
        ((0, 0, 1), (1, 0, 0), (0, 1, 0), (cx, cy, cz + hz), 1),
        ((0, 0, -1), (1, 0, 0), (0, -1, 0), (cx, cy, cz - hz), -1),
        ((1, 0, 0), (0, 1, 0), (0, 0, 1), (cx + hx, cy, cz), 1),
        ((-1, 0, 0), (0, -1, 0), (0, 0, 1), (cx - hx, cy, cz), -1),
        ((0, 1, 0), (-1, 0, 0), (0, 0, 1), (cx, cy + hy, cz), 1),
        ((0, -1, 0), (1, 0, 0), (0, 0, 1), (cx, cy - hy, cz), -1),
    ]
    for nrm, u_axis, v_axis, origin, sign in face_defs:
        nrm = Vector(nrm)
        u_axis = Vector(u_axis)
        v_axis = Vector(v_axis)
        hu = abs(u_axis.dot(Vector((hx, hy, hz))))
        hv = abs(v_axis.dot(Vector((hx, hy, hz))))
        base = len(V)
        for iu in range(seg + 1):
            fu = -1.0 + 2.0 * iu / seg
            for iv in range(seg + 1):
                fv = -1.0 + 2.0 * iv / seg
                p = Vector(origin) + u_axis * (hu * fu) + v_axis * (hv * fv)
                if abs(fu) > 0.999 and abs(fv) > 0.999:
                    p -= nrm * b
                    p -= u_axis * (math.copysign(b * 0.55, fu))
                    p -= v_axis * (math.copysign(b * 0.55, fv))
                V.append(p)
        for iu in range(seg):
            for iv in range(seg):
                a = base + iu * (seg + 1) + iv
                c = base + (iu + 1) * (seg + 1) + iv
                if sign > 0:
                    F.append((a, a + 1, c + 1, c))
                else:
                    F.append((a, c, c + 1, a + 1))
                FM.append(mat)
                FS.append(smooth)


# ---------------------------------------------------------------------------
# bagian-bagian
# ---------------------------------------------------------------------------


def build_cover(m_cover, collection):
    V, F, FM, FS = [], [], [], []
    mats = [m_cover]

    hx, hy = W * 0.5, D * 0.5
    z_pages0 = T_COVER + GAP          # bawah blok kertas
    z_pages1 = z_pages0 + T_PAGES     # atas blok kertas
    z_top = z_pages1 + GAP + T_COVER  # atas sampul

    # papan bawah
    add_box(V, F, FM, FS, (0, 0, T_COVER * 0.5), (hx, hy, T_COVER * 0.5),
            mat=MAT_COVER, bevel=0.0012)
    # papan atas
    add_box(V, F, FM, FS, (0, 0, z_top - T_COVER * 0.5), (hx, hy, T_COVER * 0.5),
            mat=MAT_COVER, bevel=0.0012)

    # punggung buku di -X: setengah silinder
    spine_pts = []
    r = (z_top) * 0.5
    cz = z_top * 0.5
    n = 12
    for i in range(n + 1):
        a = math.pi * 0.5 + math.pi * i / n
        spine_pts.append((-hx + 0.004 * math.cos(a) + 0.006,
                          0.0,
                          cz + (r + 0.004) * math.sin(a)))
    # punggung sebagai bilah vertikal melengkung (bukan tabung): dua baris
    base = len(V)
    for z_off in (-1, 1):
        for i in range(n + 1):
            a = math.pi * 0.5 + math.pi * i / n
            x = -hx - 0.0035 + 0.0035 * math.cos(a)
            z = cz + (r + 0.0025) * math.sin(a)
            V.append(Vector((x, z_off * hy, z)))
    for i in range(n):
        a0 = base + i
        b0 = base + (n + 1) + i
        F.append((a0, a0 + 1, b0 + 1, b0))
        FM.append(MAT_COVER)
        FS.append(True)

    return new_object("PRP_book_cover", V, F, mats, FM, FS, collection)


def build_pages(m_pages, collection):
    V, F, FM, FS = [], [], [], []
    mats = [m_pages]

    hx, hy = W * 0.5 - 0.003, D * 0.5 - 0.003
    z0 = T_COVER + GAP
    z1 = z0 + T_PAGES

    add_box(V, F, FM, FS, (0.0015, 0, (z0 + z1) * 0.5), (hx, hy, T_PAGES * 0.5),
            mat=MAT_PAGES, smooth=False)

    # garis tepi kertas di sisi +X (fore-edge): 4 alur tipis
    for k in range(4):
        zz = z0 + T_PAGES * (k + 0.5) / 4.0
        add_box(V, F, FM, FS, (hx + 0.0025, 0, zz),
                (0.0012, hy * 0.98, 0.0007), mat=MAT_PAGES, smooth=False)

    return new_object("PRP_book_pages", V, F, mats, FM, FS, collection)


def build_strap(m_strap, m_buckle, collection):
    V, F, FM, FS = [], [], [], []
    mats = [m_strap, m_buckle]

    hx, hy = W * 0.5, D * 0.5
    z_top = T_COVER + GAP + T_PAGES + GAP + T_COVER
    x_strap = 0.034

    # karet melintang: atas buku -> sisi +Y -> bawah buku, penampang pipih
    pts = []
    n = 8
    for i in range(n + 1):
        t = i / n
        y = -hy - 0.004 + (2 * hy + 0.008) * t
        pts.append((x_strap, y, z_top + 0.0035))
    add_tube(V, F, FM, FS, pts, [0.004] * len(pts), 8, mat=0,
             flat=(0.0045, 0.0018))

    # turun di kedua sisi
    for sy in (-1, 1):
        add_tube(V, F, FM, FS,
                 [(x_strap, sy * (hy + 0.004), z_top + 0.002),
                  (x_strap, sy * (hy + 0.005), -0.001)],
                 [0.004, 0.004], 8, mat=0, flat=(0.0045, 0.0018))

    # gesper: bingkai kecil oranye di atas
    bx, by, bz = x_strap, 0.028, z_top + 0.0035
    frame = []
    seg = 4
    for i in range(4):
        a0 = math.pi * 0.5 * i
        a1 = math.pi * 0.5 * (i + 1)
        frame.append(((bx + 0.011 * math.cos(a0), by + 0.007 * math.sin(a0), bz),
                      (bx + 0.011 * math.cos(a1), by + 0.007 * math.sin(a1), bz)))
    for p0, p1 in frame:
        add_tube(V, F, FM, FS, [p0, p1], [0.0016, 0.0016], 6, mat=1)

    return new_object("PRP_book_strap", V, F, mats, FM, FS, collection)


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


def setup_preview(scn, cam_loc, cam_target, lens=60.0):
    prev = bpy.data.collections.new("PREVIEW")
    scn.collection.children.link(prev)

    ground_mat = material("MAT_preview-ground", "24302F", roughness=0.95)
    mesh = bpy.data.meshes.new("PREVIEW_ground")
    mesh.from_pydata(
        [(-2, -2, -0.001), (2, -2, -0.001), (2, 2, -0.001), (-2, 2, -0.001)],
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
    key.data.energy = 3.0
    key.data.angle = math.radians(8)
    key.rotation_euler = (math.radians(46), 0.0, math.radians(-30))

    fill = bpy.data.objects.new("LGT_preview-fill", bpy.data.lights.new("LGT_preview-fill", "AREA"))
    prev.objects.link(fill)
    fill.data.energy = 40.0
    fill.data.size = 1.2
    fill.location = (-0.45, -0.5, 0.42)
    fill.rotation_euler = (Vector((0, 0, 0.02)) - fill.location).normalized().to_track_quat(
        "-Z", "Y"
    ).to_euler()

    rim = bpy.data.objects.new("LGT_preview-rim", bpy.data.lights.new("LGT_preview-rim", "AREA"))
    prev.objects.link(rim)
    rim.data.energy = 25.0
    rim.data.size = 0.8
    rim.location = (0.45, 0.45, 0.35)
    rim.rotation_euler = (Vector((0, 0, 0.02)) - rim.location).normalized().to_track_quat(
        "-Z", "Y"
    ).to_euler()

    world = bpy.data.worlds.new("WLD_book-preview")
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.10, 0.13, 0.13, 1.0)
    bg.inputs["Strength"].default_value = 1.0
    scn.world = world
    return cam


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main():
    scn, col = setup_scene("PRP_book")

    m_cover = material("MAT_book_cover", PAL["dark"], roughness=0.62)
    m_pages = material("MAT_book_pages", PAL["bone"], roughness=0.78)
    m_strap = material("MAT_book_strap", PAL["deep"], roughness=0.70)
    m_buckle = material("MAT_book_buckle", PAL["orange"], roughness=0.40, metallic=0.2)

    cover = build_cover(m_cover, col)
    pages = build_pages(m_pages, col)
    strap = build_strap(m_strap, m_buckle, col)

    setup_preview(scn, (0.30, -0.36, 0.24), (0.0, 0.0, 0.014), lens=55.0)

    print("=== RINGKASAN debt-book ===")
    total_v = 0
    for obj in (cover, pages, strap):
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

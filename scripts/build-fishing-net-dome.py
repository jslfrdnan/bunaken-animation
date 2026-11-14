"""
Membangun aset props Scene 2: jaring kubah (dome net) yang mengapung/terbuka.

Hasil: assets/props/fishing-net-dome.blend (koleksi PRP_net-dome)
  CTL_net-dome       -> empty di (0,0,0), induk ketiga objek mesh
  PRP_net-dome_mesh  -> belahan bola (hemisphere) radius 3,0 m, TERBUKA di
                        bawah, jaring belah ketupat mata 10 cm, benang teal
                        dalam #0F5C63, tebal 3 mm. Origin di pusat rim (z 0),
                        kubah mengarah +Z. Bagian atas dikumpulkan ke satu titik
                        (gathered crown) seperti jaring sungguhan.
  PRP_net-dome_float -> 12 pelampung kecil krem #F2E9DC di sepanjang rim
  PRP_net-dome_rope  -> tali ris (rim) + tali mahkota atas + 2 ujung tali putus

Warna: teal dalam #0F5C63 (benang), pasir hangat #E8D5B0 (tali), krem tulang
#F2E9DC (pelampung) — palette PROJECT.md §2. Tanpa tekstur image.

Geometri: cincin lintang dengan jumlah knot per cincin mengikuti keliling
(2*pi*R*sin(phi)), sehingga mata jaring tetap ~10 cm dari ekuator sampai
mahkota. Setiap knot terhubung ke dua knot di cincin bawah -> pola belah
ketupat. Tidak ada penutup di bawah.

Acuan: pengecualian props lead 1 Nov 2026 (AGENTS.md §2.1) — panel storyboard
Scene 2 (jaring dasar / alat tangkap) + ref-perahu-bercadik_v001.jpg (warna
tali & pelampung) + palette. Foto hanya acuan bentuk & warna, bukan tekstur.

Skrip ini TIDAK menyimpan file; penyimpanan dilakukan setelah verifikasi.
"""

import bpy
import math
from mathutils import Vector

# ---------------------------------------------------------------------------
# palette (PROJECT.md §2)
# ---------------------------------------------------------------------------

PAL = {
    "teal": "#1FA3A3",
    "deep": "#0F5C63",
    "reef": "#3E8E6E",
    "orange": "#E4713C",
    "sand": "#E8D5B0",
    "bone": "#F2E9DC",
}

MAT_TWINE, MAT_ROPE, MAT_FLOAT = 0, 1, 2

# ---------------------------------------------------------------------------
# ukuran nyata (m)
# ---------------------------------------------------------------------------

R = 3.00             # radius belahan bola
CELL = 0.10          # mata jaring 10 cm (jarak knot ke knot pada cincin)
THREAD = 0.003       # tebal benang 3 mm
RT = THREAD / 2.0
PHI_TOP = 0.115      # sudut polar awal (mahkota dikumpulkan di sini)
N_FLOATS = 12
ROPE_R = 0.011       # radius tali ris (22 mm)

FL = (0.040, 0.055, 0.045)   # radii pelampung: radial, tangensial, vertikal

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


def material(name, hexcol, roughness=0.8, metallic=0.0, spec=0.3):
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


def add_segment(verts, faces, fmat, fsmooth, p0, p1, radius, sides=3, mat=0, ext=1.8):
    """Satu ruas benang jaring: prisma pendek, sedikit diperpanjang di ujung
    supaya tidak ada celah di titik simpul."""
    d = p1 - p0
    if d.length < 1e-9:
        return
    d = d.normalized()
    hint = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0))
    n = d.cross(hint)
    if n.length < 1e-6:
        n = d.cross(Vector((0, 1, 0)))
    n.normalize()
    b = d.cross(n).normalized()
    a0 = p0 - d * (radius * ext)
    a1 = p1 + d * (radius * ext)
    base = len(verts)
    for p in (a0, a1):
        for j in range(sides):
            ang = 2.0 * math.pi * j / sides
            verts.append(p + n * (math.cos(ang) * radius) + b * (math.sin(ang) * radius))
    for j in range(sides):
        j2 = (j + 1) % sides
        faces.append((base + j, base + j2, base + sides + j2, base + sides + j))
        fmat.append(mat)
        fsmooth.append(True)


# ---------------------------------------------------------------------------
# permukaan kubah
# ---------------------------------------------------------------------------


def wobble(phi, th):
    """Penyimpangan halus dari bola sempurna (jaring tidak kaku), nol di rim."""
    taper = min(1.0, (math.pi / 2.0 - phi) / 0.30)
    amp = 0.016 * taper
    return 1.0 + amp * (0.60 * math.sin(2.3 * th + 1.7 * phi)
                        + 0.40 * math.sin(5.1 * th - 3.3 * phi + 1.1))


def ring_count(phi):
    """Jumlah knot pada satu cincin lintang: keliling / mata jaring."""
    if phi >= math.pi / 2.0 - 1e-9:
        return int(round(2.0 * math.pi * R / CELL))
    return max(8, int(round(2.0 * math.pi * R * math.sin(phi) / CELL)))


def build_rings():
    dphi = CELL / R
    phis = []
    phi = PHI_TOP
    while phi < math.pi / 2.0 - 1e-9:
        phis.append(phi)
        phi += dphi
    # cincin rim harus tepat di z 0
    if math.pi / 2.0 - phis[-1] < dphi * 0.45:
        phis[-1] = math.pi / 2.0
    else:
        phis.append(math.pi / 2.0)

    rings = []
    for phi in phis:
        m = ring_count(phi)
        pts = []
        for j in range(m):
            th = 2.0 * math.pi * j / m
            rad = R * wobble(phi, th)
            pts.append(Vector((rad * math.sin(phi) * math.cos(th),
                               rad * math.sin(phi) * math.sin(th),
                               rad * math.cos(phi))))
        rings.append(pts)
    return rings


# ---------------------------------------------------------------------------
# jaring
# ---------------------------------------------------------------------------


def build_net(m_twine, col):
    V, F, FM, FS = [], [], [], []
    rings = build_rings()

    # pola belah ketupat: tiap knot -> dua knot di cincin bawah
    for k in range(len(rings) - 1):
        A, B = rings[k], rings[k + 1]
        ma, mb = len(A), len(B)
        for j in range(ma):
            t = j * mb / float(ma)
            j0 = int(math.floor(t)) % mb
            j1 = (j0 + 1) % mb
            add_segment(V, F, FM, FS, A[j], B[j0], RT, 3, MAT_TWINE)
            add_segment(V, F, FM, FS, A[j], B[j1], RT, 3, MAT_TWINE)

    # mahkota: benang dikumpulkan ke satu titik di puncak
    apex = Vector((0.0, 0.0, R))
    for p in rings[0]:
        add_segment(V, F, FM, FS, p, apex, RT, 3, MAT_TWINE)

    obj = new_object("PRP_net-dome_mesh", V, F, [m_twine], FM, FS, col)
    return obj, rings


# ---------------------------------------------------------------------------
# tali: ris rim, mahkota, dua ujung putus
# ---------------------------------------------------------------------------


def build_rope(m_rope, col, rings):
    V, F, FM, FS = [], [], [], []
    z_rim = ROPE_R

    # tali ris keliling rim
    pts = []
    n = 150
    for k in range(n):
        a = 2.0 * math.pi * k / n
        pts.append(Vector((R * math.cos(a), R * math.sin(a), z_rim)))
    add_tube(V, F, FM, FS, pts + [pts[0]], [ROPE_R] * (n + 1), 5, mat=MAT_ROPE)

    # tali mahkota atas (mengikat ujung-ujung benang)
    top = rings[0][0]
    zt = top.z
    rt = R * math.sin(math.acos(min(1.0, zt / R)))
    ring2 = []
    for k in range(48):
        a = 2.0 * math.pi * k / 48
        ring2.append(Vector((rt * math.cos(a), rt * math.sin(a), zt + 0.004)))
    add_tube(V, F, FM, FS, ring2 + [ring2[0]], [0.007] * 49, 5, mat=MAT_ROPE)

    # dua ujung tali putus yang menjuntai keluar-bawah
    for a0 in (0.62, 3.55):
        pts2, radii = [], []
        for i in range(11):
            t = i / 10.0
            rad = R + 0.03 + 0.30 * t
            z = z_rim - 0.13 * (t ** 1.5)
            wig = 0.055 * math.sin(2.6 * math.pi * t)
            ang = a0 + wig * 0.55
            pts2.append(Vector((rad * math.cos(ang), rad * math.sin(ang), z)))
            radii.append(ROPE_R * (1.0 - 0.45 * t))
        add_tube(V, F, FM, FS, pts2, radii, 5, mat=MAT_ROPE)

        # serat lepas di ujung putus
        tip = pts2[-1]
        tdir = (pts2[-1] - pts2[-2]).normalized()
        for k in range(3):
            ang = 2.0 * math.pi * k / 3.0 + a0
            side = Vector((math.cos(ang), math.sin(ang), 0.0))
            end = tip + (tdir * 0.6 + side * 0.8).normalized() * 0.075
            add_tube(V, F, FM, FS, [tip, (tip + end) * 0.5, end],
                     [ROPE_R * 0.35, ROPE_R * 0.20, 0.0018], 4, mat=MAT_ROPE)

    obj = new_object("PRP_net-dome_rope", V, F, [m_rope], FM, FS, col)
    return obj


# ---------------------------------------------------------------------------
# pelampung
# ---------------------------------------------------------------------------


def build_floats(m_float, col):
    V, F, FM, FS = [], [], [], []
    seg, rings = 12, 6
    for k in range(N_FLOATS):
        a = 2.0 * math.pi * (k + 0.5) / N_FLOATS
        er = Vector((math.cos(a), math.sin(a), 0.0))
        et = Vector((-math.sin(a), math.cos(a), 0.0))
        up = Vector((0.0, 0.0, 1.0))
        center = er * R + up * (ROPE_R + FL[2] * 0.85)
        base = len(V)
        for ir in range(rings + 1):
            th = math.pi * ir / rings
            for isg in range(seg):
                ph = 2.0 * math.pi * isg / seg
                u = Vector((math.sin(th) * math.cos(ph), math.sin(th) * math.sin(ph),
                            math.cos(th)))
                V.append(center + er * (u.x * FL[0]) + et * (u.y * FL[1]) + up * (u.z * FL[2]))
        for ir in range(rings):
            for isg in range(seg):
                a0 = base + ir * seg + isg
                b0 = base + ir * seg + (isg + 1) % seg
                c0 = base + (ir + 1) * seg + (isg + 1) % seg
                d0 = base + (ir + 1) * seg + isg
                F.append((a0, b0, c0, d0))
                FM.append(MAT_FLOAT)
                FS.append(True)

    return new_object("PRP_net-dome_float", V, F, [m_float], FM, FS, col)


# ---------------------------------------------------------------------------
# scene & pratinjau
# ---------------------------------------------------------------------------


def setup_scene(col_name):
    scn = bpy.context.scene
    scn.name = "fishing-net-dome"
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


def setup_preview(scn, cam_loc, cam_target, lens=28.0):
    """Kamera/lampu netral untuk verifikasi. Bukan look dev final."""
    prev = bpy.data.collections.new("PREVIEW")
    scn.collection.children.link(prev)

    cam_data = bpy.data.cameras.new("CAM_preview")
    cam_data.lens = lens
    cam_data.clip_start = 0.05
    cam_data.clip_end = 200.0
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
    key.data.angle = math.radians(8)
    key.rotation_euler = (math.radians(52), 0.0, math.radians(30))

    fill = bpy.data.objects.new("LGT_preview-fill", bpy.data.lights.new("LGT_preview-fill", "AREA"))
    prev.objects.link(fill)
    fill.data.energy = 900.0
    fill.data.size = 9.0
    fill.location = (-5.0, -7.0, 3.0)
    fill.rotation_euler = (Vector((0, 0, 1.6)) - fill.location).normalized().to_track_quat(
        "-Z", "Y"
    ).to_euler()

    rim = bpy.data.objects.new("LGT_preview-rim", bpy.data.lights.new("LGT_preview-rim", "AREA"))
    prev.objects.link(rim)
    rim.data.energy = 500.0
    rim.data.size = 7.0
    rim.location = (6.0, 5.0, 2.0)
    rim.rotation_euler = (Vector((0, 0, 1.4)) - rim.location).normalized().to_track_quat(
        "-Z", "Y"
    ).to_euler()

    world = bpy.data.worlds.new("WLD_net-dome-preview")
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.32, 0.40, 0.43, 1.0)
    bg.inputs["Strength"].default_value = 1.0
    scn.world = world
    return cam


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main():
    scn, col = setup_scene("PRP_net-dome")

    m_twine = material("MAT_net-dome_twine", PAL["deep"], roughness=0.35, spec=0.45)
    m_rope = material("MAT_net-dome_rope", PAL["sand"], roughness=0.70)
    m_float = material("MAT_net-dome_float", PAL["bone"], roughness=0.55)

    ctl = bpy.data.objects.new("CTL_net-dome", None)
    ctl.empty_display_type = "PLAIN_AXES"
    ctl.empty_display_size = 1.2
    ctl.location = (0.0, 0.0, 0.0)
    col.objects.link(ctl)

    net, rings = build_net(m_twine, col)
    rope = build_rope(m_rope, col, rings)
    floats = build_floats(m_float, col)

    for ob in (net, rope, floats):
        ob.parent = ctl
        ob.matrix_parent_inverse.identity()

    bpy.context.view_layer.update()

    # kamera pratinjau: dari bawah, supaya bentuk kubah terbaca
    setup_preview(scn, (4.60, -5.60, -3.40), (0.0, 0.0, 1.30), lens=26.0)

    print("=== RINGKASAN fishing-net-dome ===")
    total_v = 0
    for obj in (net, rope, floats):
        d = obj.dimensions
        total_v += len(obj.data.vertices)
        print(f"{obj.name}: verts={len(obj.data.vertices)} faces={len(obj.data.polygons)} "
              f"dims=({d.x:.3f}, {d.y:.3f}, {d.z:.3f}) m loc={tuple(round(v,3) for v in obj.location)}")
    print("total verts:", total_v, "(batas 80000)")
    print("cincin lintang:", len(rings), "| knot rim:", len(rings[-1]),
          "| knot mahkota:", len(rings[0]))
    m_eq = 2.0 * math.pi * R / float(len(rings[-1]))
    print(f"mata jaring ekuator/rim: {m_eq*100:.1f} cm | tebal benang {THREAD*1000:.0f} mm")
    zmin = min(v.co.z for v in net.data.vertices)
    zmax = max(v.co.z for v in net.data.vertices)
    print(f"z mesh: {zmin:.3f} .. {zmax:.3f} m (rim harus 0,000)")
    print("materials:", [m.name for m in bpy.data.materials])
    print("collections:", [c.name for c in bpy.data.collections])
    print("engine:", scn.render.engine, "vt:", scn.view_settings.view_transform,
          "res:", scn.render.resolution_x, scn.render.resolution_y,
          "%:", scn.render.resolution_percentage,
          "fps:", scn.render.fps, "frame:", scn.frame_current)
    print("autopack:", bpy.data.use_autopack)


main()

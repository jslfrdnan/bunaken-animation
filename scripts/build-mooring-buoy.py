"""
Membangun aset props Scene 4: mooring buoy oranye (buoy tambat kapal).

Hasil: assets/props/mooring-buoy.blend (koleksi PRP_buoy)
  PRP_buoy_body -> bola pelampung oranye 0,60 m (diameter), center z 2,80
  PRP_buoy_band -> dua pita krem melingkar di badan bola
  PRP_buoy_ring -> dua cincin baja di bawah & atas bola
  PRP_buoy_rope -> tali tambat 2,5 m dari dasar (z 0) ke cincin bawah,
                   dengan mata tali (eye splice) di titik tambat

Origin ketiga objek di (0,0,0) = titik tambat di dasar. Skala nyata.
Warna: oranye karang #E4713C, krem tulang #F2E9DC, teal dalam #0F5C63 (cincin
baja), pasir hangat #E8D5B0 (tali) — palette PROJECT.md §2. Tanpa tekstur image.

Acuan: pengecualian environment/props lead 1 Nov 2026 (AGENTS.md §2.1) —
panel storyboard 4A (cerita: warga menyiapkan mooring buoy di perahu) + palette.
Tidak ada foto yang dipakai sebagai tekstur.

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
}

MAT_BODY, MAT_BAND, MAT_RING, MAT_ROPE = 0, 1, 2, 3

R_BODY = 0.30        # radius bola (diameter 0,60 m)
Z_BODY = 2.80        # pusat bola
Z_ROPE_TOP = 2.44    # tali sampai cincin bawah
ROPE_R = 0.013

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


def add_uvsphere(V, F, FM, FS, center, r, seg=32, rings=18, mat=0, smooth=True):
    top = len(V)
    V.append(Vector((center[0], center[1], center[2] + r)))
    ring_start = []
    for ir in range(1, rings):
        th = math.pi * ir / rings
        start = len(V)
        for isg in range(seg):
            ph = 2.0 * math.pi * isg / seg
            V.append(Vector((
                center[0] + r * math.sin(th) * math.cos(ph),
                center[1] + r * math.sin(th) * math.sin(ph),
                center[2] + r * math.cos(th),
            )))
        ring_start.append(start)
    bot = len(V)
    V.append(Vector((center[0], center[1], center[2] - r)))

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


def add_tube(V, F, FM, FS, points, radii, sides, mat=0, smooth=True):
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


def add_torus(V, F, FM, FS, center, major, minor, seg=24, ring=10, mat=0):
    base = len(V)
    for i in range(seg):
        a = 2.0 * math.pi * i / seg
        for j in range(ring):
            b = 2.0 * math.pi * j / ring
            x = (major + minor * math.cos(b)) * math.cos(a)
            y = (major + minor * math.cos(b)) * math.sin(a)
            z = minor * math.sin(b)
            V.append(Vector((center[0] + x, center[1] + y, center[2] + z)))
    for i in range(seg):
        i2 = (i + 1) % seg
        for j in range(ring):
            j2 = (j + 1) % ring
            F.append((base + i * ring + j, base + i2 * ring + j,
                      base + i2 * ring + j2, base + i * ring + j2))
            FM.append(mat)
            FS.append(True)


def add_band(V, F, FM, FS, z_center, lat0, lat1, seg=40, mat=1, offset=0.004):
    """Pita krem mengikuti permukaan bola; shell tipis 4 mm di atas bola."""
    rows = []
    for lat in (lat0, lat1):
        start = len(V)
        rr = R_BODY + offset
        for isg in range(seg):
            ph = 2.0 * math.pi * isg / seg
            V.append(Vector((
                rr * math.cos(lat) * math.cos(ph),
                rr * math.cos(lat) * math.sin(ph),
                z_center + rr * math.sin(lat),
            )))
        rows.append(start)
    a0, b0 = rows
    for isg in range(seg):
        isg2 = (isg + 1) % seg
        F.append((a0 + isg, a0 + isg2, b0 + isg2, b0 + isg))
        FM.append(mat)
        FS.append(True)


# ---------------------------------------------------------------------------
# bagian-bagian
# ---------------------------------------------------------------------------


def build_body(m_body, collection):
    V, F, FM, FS = [], [], [], []
    add_uvsphere(V, F, FM, FS, (0.0, 0.0, Z_BODY), R_BODY, seg=36, rings=20, mat=MAT_BODY)
    # leher bawah & atas tempat cincin
    for (z0, z1, rr) in ((Z_ROPE_TOP - 0.02, Z_BODY - 0.27, 0.055),
                         (Z_BODY + 0.27, Z_BODY + 0.35, 0.048)):
        pts = [Vector((0, 0, z0)), Vector((0, 0, z1))]
        add_tube(V, F, FM, FS, pts, [rr, rr], 12, mat=MAT_BODY)
    obj = new_object("PRP_buoy_body", V, F, [m_body], FM, FS, collection)
    return obj


def build_bands(m_band, collection):
    V, F, FM, FS = [], [], [], []
    add_band(V, F, FM, FS, Z_BODY, 0.30, 0.50, mat=MAT_BAND)
    add_band(V, F, FM, FS, Z_BODY, -0.50, -0.30, mat=MAT_BAND)
    obj = new_object("PRP_buoy_band", V, F, [m_band], FM, FS, collection)
    return obj


def build_rings(m_ring, collection):
    V, F, FM, FS = [], [], [], []
    add_torus(V, F, FM, FS, (0, 0, Z_ROPE_TOP - 0.03), 0.055, 0.012, mat=MAT_RING)
    add_torus(V, F, FM, FS, (0, 0, Z_BODY + 0.37), 0.048, 0.011, mat=MAT_RING)
    obj = new_object("PRP_buoy_ring", V, F, [m_ring], FM, FS, collection)
    return obj


def build_rope(m_rope, collection):
    V, F, FM, FS = [], [], [], []

    # tali tambat: dari titik tambat (z 0) ke cincin bawah
    pts = []
    n = 26
    for i in range(n + 1):
        t = i / n
        z = 0.03 + (Z_ROPE_TOP - 0.05) * t
        pts.append(Vector((0.020 * math.sin(1.15 * z), 0.014 * math.cos(0.9 * z), z)))
    add_tube(V, F, FM, FS, pts, [ROPE_R] * len(pts), 8, mat=MAT_ROPE)

    # eye splice di titik tambat: mata tali mendatar yang tergeletak di dasar
    loop = []
    seg = 18
    for k in range(seg + 1):
        a = 2.0 * math.pi * k / seg
        loop.append(Vector((0.078 * math.cos(a), 0.055 * math.sin(a), 0.014)))
    add_tube(V, F, FM, FS, loop, [ROPE_R * 0.95] * len(loop), 7, mat=MAT_ROPE)

    # lilitan di cincin bawah (tali dibelit 2 kali)
    for k in range(2):
        z = Z_ROPE_TOP - 0.055 + k * 0.030
        ring = []
        for s in range(15):
            a = 2.0 * math.pi * s / 14
            ring.append(Vector((0.052 * math.cos(a), 0.052 * math.sin(a), z)))
        add_tube(V, F, FM, FS, ring, [ROPE_R * 0.85] * len(ring), 6, mat=MAT_ROPE)

    obj = new_object("PRP_buoy_rope", V, F, [m_rope], FM, FS, collection)
    return obj


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


def setup_preview(scn, cam_loc, cam_target, lens=45.0):
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
    key.data.energy = 3.0
    key.data.angle = math.radians(5)
    key.rotation_euler = (math.radians(52), 0.0, math.radians(30))

    fill = bpy.data.objects.new("LGT_preview-fill", bpy.data.lights.new("LGT_preview-fill", "AREA"))
    prev.objects.link(fill)
    fill.data.energy = 220.0
    fill.data.size = 6.0
    fill.location = (-3.5, -5.0, 3.0)
    fill.rotation_euler = (Vector((0, 0, 1.9)) - fill.location).normalized().to_track_quat(
        "-Z", "Y"
    ).to_euler()

    rim = bpy.data.objects.new("LGT_preview-rim", bpy.data.lights.new("LGT_preview-rim", "AREA"))
    prev.objects.link(rim)
    rim.data.energy = 120.0
    rim.data.size = 5.0
    rim.location = (4.0, 3.5, 4.0)
    rim.rotation_euler = (Vector((0, 0, 2.4)) - rim.location).normalized().to_track_quat(
        "-Z", "Y"
    ).to_euler()

    world = bpy.data.worlds.new("WLD_buoy-preview")
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.075, 0.095, 0.105, 1.0)
    bg.inputs["Strength"].default_value = 1.0
    scn.world = world
    return cam


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main():
    scn, col = setup_scene("PRP_buoy")

    mats = [
        material("MAT_buoy_body", PAL["orange"], roughness=0.42),
        material("MAT_buoy_band", PAL["bone"], roughness=0.50),
        material("MAT_buoy_ring", PAL["deep"], roughness=0.32, metallic=0.75),
        material("MAT_buoy_rope", PAL["sand"], roughness=0.80),
    ]

    body = build_body(mats[MAT_BODY], col)
    band = build_bands(mats[MAT_BAND], col)
    ring = build_rings(mats[MAT_RING], col)
    rope = build_rope(mats[MAT_ROPE], col)

    setup_preview(scn, (3.30, -4.55, 2.55), (0.0, 0.0, 1.55), lens=32.0)

    print("=== RINGKASAN mooring-buoy ===")
    total_v = 0
    for obj in (body, band, ring, rope):
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

"""
Membangun aset props Scene 3: kamera bawah air (underwater camera housing).

Hasil: assets/props/underwater-camera.blend (koleksi PRP_camera)
  PRP_camera_housing -> housing kotak 0,22 x 0,16 x 0,14 m, sudut dibulatkan,
                        dua kancing depan, jendela lensa depan, paking oranye.
  PRP_camera_lens    -> tabung lensa + cincin depan + tutup lensa kaca.
  PRP_camera_handle  -> gagang di atas housing + dua braket.
  PRP_camera_strap   -> tali pergelangan tangan (loop) di sisi kanan.

Origin semua objek di (0,0,0) = dasar housing (sisi bawah), skala nyata.
Sumbu: depan kamera menghadap -Y (konsisten dengan Nara yang menghadap -Y).

Warna: housing abu gelap #2E383A, aksen teal #1FA3A3, cincin oranye karang
#E4713C, tali krem tulang #F2E9DC, kaca teal dalam #0F5C63 — palette
PROJECT.md §2. Tanpa tekstur image.

Acuan: panel storyboard 3A (Nara merekam karang rusak dengan kamera bawah air) +
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

MAT_BODY, MAT_ACCENT, MAT_GLASS, MAT_STRAP = 0, 1, 2, 3

HX, HY, HZ = 0.110, 0.080, 0.070   # setengah dimensi housing (m)

# ---------------------------------------------------------------------------
# utilitas
# ---------------------------------------------------------------------------


def srgb(hexstr):
    h = hexstr.lstrip("#")
    values = [int(h[i : i + 2], 16) / 255.0 for i in (0, 2, 4)]

    def to_linear(u):
        return u / 12.92 if u <= 0.04045 else ((u + 0.055) / 1.055) ** 2.4

    return tuple(to_linear(v) for v in values) + (1.0,)


def material(name, hexcol, roughness=0.6, metallic=0.0, alpha=1.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.use_backface_culling = False
    mat.diffuse_color = srgb(hexcol)
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = srgb(hexcol)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    if alpha < 1.0:
        bsdf.inputs["Alpha"].default_value = alpha
        mat.blend_method = "BLEND"
    spec = bsdf.inputs.get("Specular IOR Level") or bsdf.inputs.get("Specular")
    if spec is not None:
        spec.default_value = 0.45
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


def add_rounded_box(V, F, FM, FS, center, half, bevel, seg=4, mat=0, smooth=True):
    """Kotak dengan sudut dibulatkan sederhana: grid permukaan + offset sudut."""
    cx, cy, cz = center
    hx, hy, hz = half
    b = min(bevel, hx * 0.6, hy * 0.6, hz * 0.6)

    # 6 sisi, tiap sisi grid (seg+1)^2; sudut digeser ke arah luar oleh b
    faces_def = [
        ((0, 0, 1), (1, 0, 0), (0, 1, 0), (cx, cy, cz + hz)),
        ((0, 0, -1), (1, 0, 0), (0, -1, 0), (cx, cy, cz - hz)),
        ((1, 0, 0), (0, 1, 0), (0, 0, 1), (cx + hx, cy, cz)),
        ((-1, 0, 0), (0, -1, 0), (0, 0, 1), (cx - hx, cy, cz)),
        ((0, 1, 0), (-1, 0, 0), (0, 0, 1), (cx, cy + hy, cz)),
        ((0, -1, 0), (1, 0, 0), (0, 0, 1), (cx, cy - hy, cz)),
    ]
    normal_sign = {
        (0, 0, 1): 1, (0, 0, -1): -1, (1, 0, 0): 1,
        (-1, 0, 0): -1, (0, 1, 0): 1, (0, -1, 0): -1,
    }

    for nrm, u_axis, v_axis, origin in faces_def:
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
                # tarik sudut ke dalam (efek chamfer): kurangi komponen normal
                du = max(0.0, abs(fu) - (1.0 - 2.0 * b / max(hu, 1e-6)))
                dv = max(0.0, abs(fv) - (1.0 - 2.0 * b / max(hv, 1e-6)))
                if du > 0 or dv > 0:
                    shrink = min(1.0, (du + dv) * 0.5)
                    p -= nrm * (b * shrink)
                    p -= u_axis * (math.copysign(b * 0.5, fu) * du)
                    p -= v_axis * (math.copysign(b * 0.5, fv) * dv)
                V.append(p)
        for iu in range(seg):
            for iv in range(seg):
                a = base + iu * (seg + 1) + iv
                b2 = base + (iu + 1) * (seg + 1) + iv
                if normal_sign[tuple(int(x) for x in nrm)] > 0:
                    F.append((a, a + 1, b2 + 1, b2))
                else:
                    F.append((a, b2, b2 + 1, a + 1))
                FM.append(mat)
                FS.append(smooth)


# ---------------------------------------------------------------------------
# bagian-bagian
# ---------------------------------------------------------------------------


def build_housing(m_body, m_accent, m_glass, collection):
    V, F, FM, FS = [], [], [], []
    mats = [m_body, m_accent, m_glass]

    add_rounded_box(V, F, FM, FS, (0, 0, HZ), (HX, HY, HZ), bevel=0.018,
                    seg=5, mat=MAT_BODY)

    # jendela lensa depan (cekung): cincin + kaca
    y_front = -HY - 0.001
    add_tube(V, F, FM, FS,
             [(0.0, y_front, HZ), (0.0, y_front - 0.020, HZ)],
             [0.050, 0.046], 24, mat=MAT_BODY)
    add_tube(V, F, FM, FS,
             [(0.0, y_front - 0.021, HZ), (0.0, y_front - 0.026, HZ)],
             [0.044, 0.040], 24, mat=MAT_GLASS)
    # paking oranye di sekeliling jendela
    add_tube(V, F, FM, FS,
             [(0.0, y_front - 0.004, HZ), (0.0, y_front - 0.012, HZ)],
             [0.054, 0.052], 24, mat=MAT_ACCENT)

    # dua kancing depan kiri-kanan bawah
    for sx in (-1, 1):
        x = sx * 0.062
        add_tube(V, F, FM, FS,
                 [(x, y_front - 0.004, 0.030), (x, y_front - 0.018, 0.030)],
                 [0.011, 0.011], 12, mat=MAT_ACCENT)

    # kenop atas (shutter) + kenop samping (mode)
    add_tube(V, F, FM, FS,
             [(0.045, 0.010, HZ * 2 + 0.002), (0.045, 0.010, HZ * 2 + 0.014)],
             [0.014, 0.012], 14, mat=MAT_ACCENT)
    add_tube(V, F, FM, FS,
             [(HX + 0.001, 0.012, HZ + 0.012), (HX + 0.014, 0.012, HZ + 0.012)],
             [0.012, 0.010], 14, mat=MAT_ACCENT)

    # garis teal tipis di sisi (identitas dive shop)
    add_tube(V, F, FM, FS,
             [(-HX - 0.001, -0.02, HZ + 0.030), (-HX - 0.001, 0.05, HZ + 0.030)],
             [0.004, 0.004], 6, mat=MAT_ACCENT, caps=False)

    return new_object("PRP_camera_housing", V, F, mats, FM, FS, collection)


def build_lens(m_body, m_glass, m_accent, collection):
    V, F, FM, FS = [], [], [], []
    mats = [m_body, m_glass, m_accent]
    y0 = -HY - 0.052
    # tabung lensa menjulur
    add_tube(V, F, FM, FS,
             [(0.0, y0 + 0.012, HZ), (0.0, y0 - 0.016, HZ)],
             [0.040, 0.043], 24, mat=0)
    # cincin depan (thread)
    add_tube(V, F, FM, FS,
             [(0.0, y0 - 0.016, HZ), (0.0, y0 - 0.026, HZ)],
             [0.046, 0.046], 24, mat=2)
    # kaca depan
    add_tube(V, F, FM, FS,
             [(0.0, y0 - 0.027, HZ), (0.0, y0 - 0.031, HZ)],
             [0.039, 0.034], 24, mat=1)
    return new_object("PRP_camera_lens", V, F, mats, FM, FS, collection)


def build_handle(m_body, m_strap, collection):
    V, F, FM, FS = [], [], [], []
    mats = [m_body, m_strap]

    z_top = HZ * 2
    # dua braket
    for sx in (-1, 1):
        x = sx * 0.062
        add_tube(V, F, FM, FS,
                 [(x, 0.010, z_top - 0.002), (x, 0.010, z_top + 0.016)],
                 [0.010, 0.009], 10, mat=0)
    # gagang melengkung
    pts = []
    n = 10
    for i in range(n + 1):
        t = i / n
        x = -0.062 + 0.124 * t
        z = z_top + 0.016 + 0.030 * math.sin(math.pi * t)
        pts.append((x, 0.010, z))
    add_tube(V, F, FM, FS, pts, [0.013] * len(pts), 10, mat=0)

    return new_object("PRP_camera_handle", V, F, mats, FM, FS, collection)


def build_strap(m_strap, collection):
    V, F, FM, FS = [], [], [], []
    mats = [m_strap]
    # loop tali pergelangan di sisi +X, menggantung ke bawah
    pts = []
    n = 22
    for i in range(n + 1):
        t = i / n
        a = 2.0 * math.pi * t
        x = HX + 0.026 + 0.030 * math.cos(a)
        y = 0.030 + 0.055 * math.sin(a)
        z = HZ * 0.55 + 0.055 * math.sin(a * 0.5)
        pts.append((x, y, z))
    add_tube(V, F, FM, FS, pts, [0.0065] * len(pts), 6, mat=0, caps=False)

    # penjepit tali di housing
    for y in (-0.02, 0.075):
        add_tube(V, F, FM, FS,
                 [(HX - 0.004, y, HZ * 0.55), (HX + 0.012, y, HZ * 0.55)],
                 [0.008, 0.008], 8, mat=0)
    return new_object("PRP_camera_strap", V, F, mats, FM, FS, collection)


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

    ground_mat = material("MAT_preview-ground", "1E2A2E", roughness=0.95)
    mesh = bpy.data.meshes.new("PREVIEW_ground")
    mesh.from_pydata(
        [(-4, -4, -0.002), (4, -4, -0.002), (4, 4, -0.002), (-4, 4, -0.002)],
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
    key.data.energy = 3.6
    key.data.angle = math.radians(4)
    key.rotation_euler = (math.radians(52), 0.0, math.radians(-34))

    fill = bpy.data.objects.new("LGT_preview-fill", bpy.data.lights.new("LGT_preview-fill", "AREA"))
    prev.objects.link(fill)
    fill.data.energy = 90.0
    fill.data.size = 3.0
    fill.location = (-1.4, -1.6, 1.2)
    fill.rotation_euler = (Vector((0, 0, 0.07)) - fill.location).normalized().to_track_quat(
        "-Z", "Y"
    ).to_euler()

    rim = bpy.data.objects.new("LGT_preview-rim", bpy.data.lights.new("LGT_preview-rim", "AREA"))
    prev.objects.link(rim)
    rim.data.energy = 70.0
    rim.data.size = 2.0
    rim.location = (1.3, 1.4, 1.1)
    rim.rotation_euler = (Vector((0, 0, 0.07)) - rim.location).normalized().to_track_quat(
        "-Z", "Y"
    ).to_euler()

    world = bpy.data.worlds.new("WLD_camera-preview")
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.09, 0.14, 0.16, 1.0)
    bg.inputs["Strength"].default_value = 1.0
    scn.world = world
    return cam


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main():
    scn, col = setup_scene("PRP_camera")

    m_body = material("MAT_camera_housing", PAL["dark"], roughness=0.42)
    m_accent = material("MAT_camera_accent", PAL["teal"], roughness=0.38)
    m_glass = material("MAT_camera_glass", PAL["deep"], roughness=0.08, metallic=0.3)
    m_strap = material("MAT_camera_strap", PAL["bone"], roughness=0.85)

    housing = build_housing(m_body, m_accent, m_glass, col)
    lens = build_lens(m_body, m_glass, m_accent, col)
    handle = build_handle(m_body, m_strap, col)
    strap = build_strap(m_strap, col)

    setup_preview(scn, (0.62, -0.78, 0.42), (0.0, -0.02, 0.085), lens=58.0)

    print("=== RINGKASAN underwater-camera ===")
    total_v = 0
    for obj in (housing, lens, handle, strap):
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

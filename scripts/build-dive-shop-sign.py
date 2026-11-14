"""
Membangun aset props Scene 1 shot 080: papan nama dive shop.

Hasil: assets/props/dive-shop-sign.blend (koleksi PRP_sign)
  PRP_sign_board    -> papan kayu 1,80 x 0,50 x 0,04 m (4 papan + inti gelap +
                       panel teal tenggelam + garis aksen teal)
  PRP_sign_frame    -> bingkai kayu gelap keliling papan
  PRP_sign_post_l   -> tiang kiri 2,20 m (kayu pasir + alas & tutup gelap)
  PRP_sign_post_r   -> tiang kanan 2,20 m
  PRP_sign_text     -> huruf timbul "BUNAKEN / DIVE" (mesh hasil konversi
                       text object, bukan tekstur gambar)

Origin semua objek di (0,0,0) = dasar tiang (z 0). Skala nyata.
Warna: kayu pasir #E8D5B0, kayu gelap #3E2C20 (sama dengan kayu gelap
boats.blend, sudah dipakai sebagai prop dermaga), krem tulang #F2E9DC,
teal aksen #1FA3A3, teal dalam #0F5C63 (panel) - palette PROJECT.md §2.
Tanpa tekstur image, tanpa pack.

Acuan: pengecualian environment/props lead 1 Nov 2026 (AGENTS.md §2.1) -
panel storyboard 1C (dive shop keluarga, Pak Daniel memperbaiki jaring) +
palette. Tidak ada foto yang dipakai sebagai tekstur.

Skrip idempoten: mengosongkan bpy.data manual (TIDAK memakai open_mainfile),
lalu menyimpan hasil ke assets/props/dive-shop-sign.blend.
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
    "wood_dark": "#3E2C20",
}

OUT = r"D:\Tugas Semester 5\Grafika Komputer\Project-Animasi\assets\props\dive-shop-sign.blend"

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
        spec.default_value = 0.30
    return mat


def wipe_data():
    """Kosongkan bpy.data manual. Tidak memakai open_mainfile/read_factory."""
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
                V.append((x, y, z))
    # 0:(x0,y0,z0) 1:(x1,y0,z0) 2:(x0,y1,z0) 3:(x1,y1,z0)
    # 4:(x0,y0,z1) 5:(x1,y0,z1) 6:(x0,y1,z1) 7:(x1,y1,z1)
    faces = [
        (0, 2, 3, 1),  # bawah
        (4, 5, 7, 6),  # atas
        (0, 1, 5, 4),  # depan (-Y)
        (2, 6, 7, 3),  # belakang (+Y)
        (0, 4, 6, 2),  # kiri
        (1, 3, 7, 5),  # kanan
    ]
    for f in faces:
        F.append(tuple(base + i for i in f))
        FM.append(mat)
        FS.append(smooth)


def add_prism(V, F, FM, FS, cx, cy, radius, z0, z1, sides=8, mat=0, smooth=True, angle=0.0):
    ring0 = []
    for k in range(sides):
        a = angle + 2.0 * math.pi * k / sides
        ring0.append(len(V))
        V.append((cx + radius * math.cos(a), cy + radius * math.sin(a), z0))
    ring1 = []
    for k in range(sides):
        a = angle + 2.0 * math.pi * k / sides
        ring1.append(len(V))
        V.append((cx + radius * math.cos(a), cy + radius * math.sin(a), z1))
    for k in range(sides):
        k2 = (k + 1) % sides
        F.append((ring0[k], ring0[k2], ring1[k2], ring1[k]))
        FM.append(mat)
        FS.append(smooth)
    F.append(tuple(reversed(ring0)))
    FM.append(mat)
    FS.append(False)
    F.append(tuple(ring1))
    FM.append(mat)
    FS.append(False)


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
# geometri papan nama
# ---------------------------------------------------------------------------

ZC = 1.86          # pusat papan
BOARD_W = 1.80
BOARD_H = 0.50
BOARD_T = 0.04
POST_X = 0.74
POST_H = 2.20
POST_R = 0.064

# material index papan
M_WOOD, M_DARK, M_PANEL, M_ACCENT = 0, 1, 2, 3


def build_board(collection):
    V, F, FM, FS = [], [], [], []

    gap = 0.006
    plank_h = (BOARD_H - 3 * gap) / 4.0
    for i in range(4):
        z0 = ZC - BOARD_H / 2 + i * (plank_h + gap)
        add_box(V, F, FM, FS, -BOARD_W / 2, BOARD_W / 2, -0.020, 0.012, z0, z0 + plank_h, M_WOOD)

    # inti gelap di belakang celah papan
    add_box(V, F, FM, FS, -0.88, 0.88, 0.012, 0.022, ZC - 0.24, ZC + 0.24, M_DARK)

    # panel teal tenggelam untuk huruf
    add_box(V, F, FM, FS, -0.78, 0.78, -0.026, -0.019, ZC - 0.17, ZC + 0.17, M_PANEL)

    # garis aksen teal tipis di bawah "DIVE"
    add_box(V, F, FM, FS, -0.22, 0.22, -0.029, -0.025, ZC - 0.163, ZC - 0.155, M_ACCENT)

    return new_object("PRP_sign_board", V, F, [], FM, FS, collection)


def build_frame(collection):
    V, F, FM, FS = [], [], [], []
    y0, y1 = -0.050, 0.000
    # rel atas & bawah
    add_box(V, F, FM, FS, -0.95, 0.95, y0, y1, ZC + 0.230, ZC + 0.280, M_DARK)
    add_box(V, F, FM, FS, -0.95, 0.95, y0, y1, ZC - 0.280, ZC - 0.230, M_DARK)
    # stile kiri & kanan
    add_box(V, F, FM, FS, -0.950, -0.900, y0, y1, ZC - 0.280, ZC + 0.280, M_DARK)
    add_box(V, F, FM, FS, 0.900, 0.950, y0, y1, ZC - 0.280, ZC + 0.280, M_DARK)
    return new_object("PRP_sign_frame", V, F, [], FM, FS, collection)


def build_post(name, sx, collection):
    V, F, FM, FS = [], [], [], []
    x = sx * POST_X
    add_prism(V, F, FM, FS, x, 0.060, POST_R, 0.0, POST_H, sides=8, mat=M_WOOD)
    # alas gelap
    add_box(V, F, FM, FS, x - 0.076, x + 0.076, 0.060 - 0.076, 0.060 + 0.076, 0.0, 0.10, M_DARK)
    # tutup atas gelap
    add_box(V, F, FM, FS, x - 0.074, x + 0.074, 0.060 - 0.074, 0.060 + 0.074, POST_H - 0.035, POST_H, M_DARK)
    return new_object(name, V, F, [], FM, FS, collection)


def text_line(body, size, target_h, center_z, max_w=1.28):
    """Konversi satu baris text object jadi (verts, faces) di bidang XZ."""
    cu = bpy.data.curves.new("TMP_sign_line", type="FONT")
    cu.body = body
    cu.align_x = "CENTER"
    cu.align_y = "CENTER"
    cu.size = size
    cu.extrude = 0.010
    cu.offset = 0.004
    cu.resolution_u = 4
    tmp = bpy.data.objects.new("TMP_sign_line", cu)
    bpy.context.scene.collection.objects.link(tmp)
    bpy.context.view_layer.update()

    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(tmp.evaluated_get(dg))

    bpy.data.objects.remove(tmp, do_unlink=True)
    bpy.data.curves.remove(cu)

    # rotasi X +90 deg: huruf berdiri di bidang XZ, ekstrusi ke -Y
    pts = []
    for v in me.vertices:
        x, y, z = v.co
        pts.append([x, -z, y])
    faces = [tuple(p.vertices) for p in me.polygons]
    bpy.data.meshes.remove(me)

    xs = [p[0] for p in pts]
    zs = [p[2] for p in pts]
    w = max(xs) - min(xs)
    h = max(zs) - min(zs)
    scale = target_h / h
    if w * scale > max_w:
        scale = max_w / w
    cx = (max(xs) + min(xs)) / 2.0
    cz = (max(zs) + min(zs)) / 2.0
    for p in pts:
        p[0] = (p[0] - cx) * scale
        p[2] = (p[2] - cz) * scale + center_z
        p[1] = p[1] - 0.036  # punggung huruf menempel panel (-0.026)
    return pts, faces


def build_text(mat_cream, collection):
    V, F, FM, FS = [], [], [], []
    lines = [
        ("BUNAKEN", 0.26, 0.180, ZC + 0.068),
        ("DIVE", 0.17, 0.110, ZC - 0.091),
    ]
    for body, size, target_h, cz in lines:
        pts, faces = text_line(body, size, target_h, cz)
        base = len(V)
        V.extend(pts)
        for f in faces:
            F.append(tuple(base + i for i in f))
            FM.append(0)
            FS.append(False)
    return new_object("PRP_sign_text", V, F, [mat_cream], FM, FS, collection)


# ---------------------------------------------------------------------------
# scene & pratinjau
# ---------------------------------------------------------------------------


def setup_scene():
    scn = bpy.context.scene
    scn.name = "dive-shop-sign"
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
    scn.render.film_transparent = False
    if hasattr(scn, "eevee"):
        scn.eevee.taa_render_samples = 64
    return scn


def setup_preview(scn):
    prev = bpy.data.collections.new("PREVIEW")
    scn.collection.children.link(prev)

    gmat = material("MAT_preview-ground", "#39423F", roughness=0.95)
    mesh = bpy.data.meshes.new("PREVIEW_ground")
    s = 8.0
    mesh.from_pydata(
        [(-s, -s, -0.003), (s, -s, -0.003), (s, s, -0.003), (-s, s, -0.003)],
        [],
        [(0, 1, 2, 3)],
    )
    mesh.materials.append(gmat)
    mesh.update()
    prev.objects.link(bpy.data.objects.new("PREVIEW_ground", mesh))

    cam_data = bpy.data.cameras.new("CAM_preview")
    cam_data.lens = 50.0
    cam = bpy.data.objects.new("CAM_preview", cam_data)
    prev.objects.link(cam)
    cam.location = (2.35, -4.35, 1.62)
    cam.rotation_euler = (
        Vector((0.0, 0.0, 1.48)) - cam.location
    ).normalized().to_track_quat("-Z", "Y").to_euler()
    scn.camera = cam

    key = bpy.data.objects.new("LGT_preview-key", bpy.data.lights.new("LGT_preview-key", "SUN"))
    prev.objects.link(key)
    key.data.energy = 3.2
    key.data.angle = math.radians(6)
    key.rotation_euler = (math.radians(55), 0.0, math.radians(38))

    fill = bpy.data.objects.new("LGT_preview-fill", bpy.data.lights.new("LGT_preview-fill", "AREA"))
    prev.objects.link(fill)
    fill.data.energy = 260.0
    fill.data.size = 4.0
    fill.location = (-3.6, -4.2, 3.2)
    fill.rotation_euler = (
        Vector((0.0, 0.0, 1.5)) - fill.location
    ).normalized().to_track_quat("-Z", "Y").to_euler()

    rim = bpy.data.objects.new("LGT_preview-rim", bpy.data.lights.new("LGT_preview-rim", "AREA"))
    prev.objects.link(rim)
    rim.data.energy = 140.0
    rim.data.size = 3.0
    rim.location = (3.2, 2.4, 3.4)
    rim.rotation_euler = (
        Vector((0.0, 0.0, 1.9)) - rim.location
    ).normalized().to_track_quat("-Z", "Y").to_euler()

    world = bpy.data.worlds.new("WLD_sign-preview")
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.070, 0.088, 0.095, 1.0)
    bg.inputs["Strength"].default_value = 1.0
    scn.world = world
    return cam


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main():
    wipe_data()
    scn = setup_scene()

    col = bpy.data.collections.new("PRP_sign")
    scn.collection.children.link(col)

    m_wood = material("MAT_sign_wood", PAL["sand"], roughness=0.78)
    m_dark = material("MAT_sign_wood-dark", PAL["wood_dark"], roughness=0.62)
    m_panel = material("MAT_sign_panel", PAL["deep"], roughness=0.52)
    m_accent = material("MAT_sign_teal", PAL["teal"], roughness=0.50)
    m_cream = material("MAT_sign_cream", PAL["bone"], roughness=0.48)

    board = build_board(col)
    # slot kosong: cukup append berurutan (clear() akan mereset material_index)
    for m in (m_wood, m_dark, m_panel, m_accent):
        board.data.materials.append(m)

    frame = build_frame(col)
    frame.data.materials.append(m_dark)

    post_l = build_post("PRP_sign_post_l", -1, col)
    post_r = build_post("PRP_sign_post_r", 1, col)
    for p in (post_l, post_r):
        p.data.materials.append(m_wood)
        p.data.materials.append(m_dark)

    text = build_text(m_cream, col)

    setup_preview(scn)

    scn["asset"] = "dive-shop-sign"
    scn["asset_note"] = "Papan nama dive shop Scene 1 shot 080. Origin di dasar tiang z 0."

    # simpan
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=OUT, check_existing=False)

    print("=== RINGKASAN dive-shop-sign ===")
    total_v = 0
    for obj in (board, frame, post_l, post_r, text):
        d = obj.dimensions
        total_v += len(obj.data.vertices)
        print(
            f"{obj.name:20s} verts={len(obj.data.vertices):5d} "
            f"faces={len(obj.data.polygons):5d} "
            f"dims=({d.x:.3f}, {d.y:.3f}, {d.z:.3f}) m"
        )
    print("total verts:", total_v)
    print("materials:", [m.name for m in bpy.data.materials])
    print("collections:", [c.name for c in bpy.data.collections])
    print("engine:", scn.render.engine, "| vt:", scn.view_settings.view_transform,
          "| res:", scn.render.resolution_x, scn.render.resolution_y,
          "| fps:", scn.render.fps, "| frame:", scn.frame_current)
    print("saved:", OUT, "| size:", os.path.getsize(OUT), "bytes")


main()

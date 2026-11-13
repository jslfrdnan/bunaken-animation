"""
Membangun aset props Scene 1 shot 080: jaring nelayan terlipat + alat tangkap.

Hasil: assets/props/fishing-gear.blend (koleksi PRP_gear)
  PRP_gear_fishnet  -> tumpukan jaring terlipat (pola lubang belah ketupat),
                      origin di dasar (z 0), ±1,6 x 1,1 x 0,42 m
  PRP_gear_float    -> pelampung pancing kecil (telur, garis tengah), origin
                      di dasar, ±0,32 m
  PRP_gear_basket   -> keranjang anyaman ±0,4 m, origin di dasar

Semua geometri dibuat prosedural dari nol. Acuan: storyboard panel 1C
(Pak Daniel memperbaiki jaring di teras dive shop) + palette PROJECT.md §2.
Tidak ada foto yang dipakai sebagai tekstur. Dasar: pengecualian acuan
gabungan lead (1 Nov 2026) untuk aset environment prosedural.

Skrip ini TIDAK menyimpan file; penyimpanan dilakukan setelah verifikasi
screenshot di Blender MCP.
"""

import bpy
import math
from mathutils import Vector

# ---------------------------------------------------------------------------
# utilitas (pola sama dengan scripts/build-vegetation.py)
# ---------------------------------------------------------------------------


def srgb(hexstr):
    """Hex sRGB -> linear RGBA, karena Base Color di Blender linear."""
    h = hexstr.lstrip("#")
    values = [int(h[i : i + 2], 16) / 255.0 for i in (0, 2, 4)]

    def to_linear(u):
        return u / 12.92 if u <= 0.04045 else ((u + 0.055) / 1.055) ** 2.4

    return tuple(to_linear(v) for v in values) + (1.0,)


def material(name, hexcol, roughness=0.8, metallic=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.use_backface_culling = False  # geometri tipis harus terlihat dua sisi
    mat.diffuse_color = srgb(hexcol)

    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = srgb(hexcol)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    spec = bsdf.inputs.get("Specular IOR Level") or bsdf.inputs.get("Specular")
    if spec is not None:
        spec.default_value = 0.25
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
    mats,
    smooths,
    points,
    radii,
    sides,
    mat=0,
    cap_start=False,
    cap_end=False,
    mat_per_segment=None,
    smooth=True,
):
    """Tabung mengikuti polyline, memakai parallel-transport frame."""
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
        seg_mat = mat_per_segment(i) if mat_per_segment else mat
        a_ring = base + i * sides
        b_ring = base + (i + 1) * sides
        for j in range(sides):
            j2 = (j + 1) % sides
            faces.append((a_ring + j, a_ring + j2, b_ring + j2, b_ring + j))
            mats.append(seg_mat)
            smooths.append(smooth)


def bezier3(p0, p1, p2, steps):
    p0, p1, p2 = Vector(p0), Vector(p1), Vector(p2)
    out = []
    for i in range(steps):
        t = i / (steps - 1)
        out.append(p0 * ((1 - t) ** 2) + p1 * (2 * (1 - t) * t) + p2 * (t * t))
    return out


def circle_points(center, radius, z, seg):
    pts = []
    for k in range(seg):
        a = 2.0 * math.pi * k / seg
        pts.append(Vector((center[0] + radius * math.cos(a), center[1] + radius * math.sin(a), z)))
    pts.append(pts[0])
    return pts


# ---------------------------------------------------------------------------
# cleanup (agar skrip bisa dijalankan ulang)
# ---------------------------------------------------------------------------


def cleanup():
    for obj in list(bpy.data.objects):
        if obj.name.startswith(("PRP_gear", "LGT_gear")) or obj.name == "Cube":
            bpy.data.objects.remove(obj, do_unlink=True)
    for obj in list(bpy.data.objects):
        if obj.type == "LIGHT" and obj.name == "Light":
            bpy.data.objects.remove(obj, do_unlink=True)
    for mat in list(bpy.data.materials):
        if mat.name.startswith("MAT_gear") or mat.name in ("Material", "Dots Stroke"):
            bpy.data.materials.remove(mat)
    if "PRP_gear" in bpy.data.collections:
        bpy.data.collections.remove(bpy.data.collections["PRP_gear"], do_unlink=True)
    cam = bpy.data.objects.get("Camera")
    if cam:
        cam.name = "CAM_preview"


# ---------------------------------------------------------------------------
# jaring: tumpukan 3 lapis pola belah ketupat, tepi menebal (tali ris)
# ---------------------------------------------------------------------------

S = 0.06          # sisi lubang belah ketupat (mata jaring)
R_TWINE = 0.0035  # jari-jari benang biasa
R_BOUND = 0.006   # jari-jari benang tepi (tali ris)

# per lapis: ukuran, pusat, tinggi dasar, amplitudo gelombang, fase
LAYERS = [
    dict(size=(1.60, 1.10), center=(0.00, 0.00), base=0.00, amp=0.10, ph=(0.0, 0.0)),
    dict(size=(1.30, 0.85), center=(0.06, 0.05), base=0.07, amp=0.08, ph=(1.3, 0.6)),
    dict(size=(0.85, 0.62), center=(-0.10, -0.03), base=0.11, amp=0.09, ph=(2.4, 1.8),
         lift=dict(pos=(0.20, 0.16), r=0.38, h=0.34)),
]


def net_z(x, y, W, D, amp, ph, base, lift=None):
    """Tinggi gelombang lipatan kain jaring; tepi melandai ke lantai."""
    edge = max(abs(x) / (W / 2.0), abs(y) / (D / 2.0))
    env = max(0.0, 1.0 - edge) ** 0.9
    z = base + amp * env * (0.5 + 0.5 * math.sin(2.1 * x - 0.9 * y + ph[0])) * (
        0.5 + 0.5 * math.cos(1.7 * x + 1.3 * y + ph[1])
    )
    if lift:
        d = math.hypot(x - lift["pos"][0], y - lift["pos"][1])
        if d < lift["r"]:
            z += lift["h"] * (1.0 - d / lift["r"]) ** 1.6
    return max(z, 0.004)


def build_fishnet(m_net, collection):
    verts, faces, fmat, fsmooth = [], [], [], []
    e1 = Vector((0.70710678, 0.70710678))
    e2 = Vector((0.70710678, -0.70710678))

    for cfg in LAYERS:
        W, D = cfg["size"]
        cx, cy = cfg["center"]
        Ni = int((W / 2.0 + D / 2.0) / (S * 1.41421356)) + 2
        knots = {}
        for i in range(-Ni, Ni + 1):
            for j in range(-Ni, Ni + 1):
                p = Vector((cx + i * S * e1.x + j * S * e2.x, cy + i * S * e1.y + j * S * e2.y))
                if abs(p.x - cx) <= W / 2.0 + S * 0.7 and abs(p.y - cy) <= D / 2.0 + S * 0.7:
                    z = net_z(p.x - cx, p.y - cy, W, D, cfg["amp"], cfg["ph"], cfg["base"], cfg.get("lift"))
                    knots[(i, j)] = Vector((p.x, p.y, z))

        for (i, j), p in knots.items():
            for di, dj in ((1, 0), (0, 1)):
                q = knots.get((i + di, j + dj))
                if q is None:
                    continue
                if di == 1:
                    nb = [(i, j - 1), (i + 1, j - 1), (i, j + 1), (i + 1, j + 1)]
                else:
                    nb = [(i - 1, j), (i - 1, j + 1), (i + 1, j), (i + 1, j + 1)]
                boundary = any(n not in knots for n in nb)
                r = R_BOUND if boundary else R_TWINE
                add_tube(verts, faces, fmat, fsmooth, [p, q], [r, r], 6, mat=0, smooth=True)

    # tali perbaikan longgar membentang di atas tumpukan
    pts = bezier3((0.35, -0.50, 0.02), (0.05, 0.05, 0.35), (-0.30, 0.45, 0.03), 24)
    add_tube(verts, faces, fmat, fsmooth, pts, [0.0035] * len(pts), 5, mat=0, smooth=True)

    return new_object("PRP_gear_fishnet", verts, faces, [m_net], fmat, fsmooth, collection)


# ---------------------------------------------------------------------------
# pelampung pancing kecil: telur + tali tembus + simpul, garis tengah krem
# ---------------------------------------------------------------------------


def build_float(m_float, m_band, m_rope, collection):
    verts, faces, fmat, fsmooth = [], [], [], []

    # badan telur (sumbu panjang = X, tergeletak)
    seg, rings = 18, 12
    r = 0.07
    base = len(verts)
    for iring in range(rings + 1):
        th = math.pi * iring / rings
        for iseg in range(seg):
            ph = 2.0 * math.pi * iseg / seg
            p = Vector((math.sin(th) * math.cos(ph), math.sin(th) * math.sin(ph), math.cos(th))) * r
            verts.append(Vector((p.x * 1.15, p.y, p.z)))
    for iring in range(rings):
        for iseg in range(seg):
            a = base + iring * seg + iseg
            b = base + iring * seg + (iseg + 1) % seg
            c = base + (iring + 1) * seg + (iseg + 1) % seg
            d = base + (iring + 1) * seg + iseg
            faces.append((a, b, c, d))
            fmat.append(0)
            fsmooth.append(True)

    # tali tembus (melorot ke lantai di kedua ujung) + simpul cincin
    line_pts = [(-0.24, 0.0, -0.045), (-0.10, 0.0, 0.0), (0.10, 0.0, 0.0), (0.24, 0.0, -0.045)]
    add_tube(verts, faces, fmat, fsmooth, line_pts, [0.0035] * 4, 6, mat=2, smooth=True)

    loop_seg = 12
    lr = 0.022
    lbase = len(verts)
    for k in range(loop_seg):
        a = 2.0 * math.pi * k / loop_seg
        verts.append(Vector((0.245, lr * math.cos(a), -0.02 + lr * math.sin(a))))
    lc = len(verts)
    verts.append(Vector((0.245, 0.0, -0.02)))
    for k in range(loop_seg):
        k2 = (k + 1) % loop_seg
        faces.append((lbase + k, lbase + k2, lc))
        fmat.append(2)
        fsmooth.append(True)

    # garis tengah krem: face dengan centroid |x| < 0.035
    for fi, f in enumerate(faces):
        cx = sum(verts[v].x for v in f) / len(f)
        if fmat[fi] == 0 and abs(cx) < 0.035:
            fmat[fi] = 1

    # origin di dasar lantai: geser seluruh mesh +0,07 m ke atas
    for v in verts:
        v.z += 0.07

    obj = new_object("PRP_gear_float", verts, faces, [m_float, m_band, m_rope], fmat, fsmooth, collection)
    obj.location = (1.05, 0.55, 0.0)
    return obj


# ---------------------------------------------------------------------------
# keranjang anyaman: cincin mendatar + bilah vertikal, pita cat teal, tali
# ---------------------------------------------------------------------------


def build_basket(m_woven, m_rim, m_band, m_rope, collection):
    verts, faces, fmat, fsmooth = [], [], [], []
    H, rt, rb, bulge = 0.40, 0.24, 0.17, 0.015
    SEG = 32

    def r_at(z):
        t = z / H
        r = rb + (rt - rb) * t + bulge * math.sin(math.pi * t)
        if z > H - 0.055:
            r += 0.010 * (z - (H - 0.055)) / 0.055
        return r

    # cincin anyaman mendatar (selang-seling menonjol/cekung)
    for k in range(12):
        z0 = 0.012 + k * 0.030
        h = 0.013
        zmid = z0 + h / 2.0
        offset = 0.0035 if k % 2 == 0 else -0.002
        rr = r_at(zmid) + offset
        if 0.285 <= zmid <= 0.322:      # pita cat teal (dua cincin)
            mi, tr = 2, 0.009
        elif k >= 10:                    # cincin atas agak tebal
            mi, tr = 1, 0.008
        else:
            mi, tr = 0, h / 2.0 + 0.001
        pts = circle_points((0, 0), rr, zmid, SEG)
        add_tube(verts, faces, fmat, fsmooth, pts, [tr] * len(pts), 8, mat=mi, smooth=True)

    # bilah vertikal anyaman
    for k in range(24):
        a = 2.0 * math.pi * k / 24
        pts = []
        for z in (0.015, 0.20, 0.372):
            rr = r_at(z) + 0.004
            pts.append(Vector((rr * math.cos(a), rr * math.sin(a), z)))
        add_tube(verts, faces, fmat, fsmooth, pts, [0.005] * 3, 4, mat=0, smooth=True)

    # bibir atas krem
    pts = circle_points((0, 0), r_at(0.375) + 0.012, 0.381, SEG)
    add_tube(verts, faces, fmat, fsmooth, pts, [0.014] * len(pts), 10, mat=1, smooth=True)

    # cincin dasar krem
    pts = circle_points((0, 0), r_at(0.012) - 0.002, 0.012, SEG)
    add_tube(verts, faces, fmat, fsmooth, pts, [0.008] * len(pts), 8, mat=1, smooth=True)

    # dinding dalam (agar tidak tembus pandang)
    base = len(verts)
    for k in range(SEG):
        a = 2.0 * math.pi * k / SEG
        verts.append(Vector((r_at(0.03) * 0.86 * math.cos(a), r_at(0.03) * 0.86 * math.sin(a), 0.03)))
        verts.append(Vector((r_at(0.36) * 0.90 * math.cos(a), r_at(0.36) * 0.90 * math.sin(a), 0.36)))
    for k in range(SEG):
        k2 = (k + 1) % SEG
        b0 = base + 2 * k
        b1 = base + 2 * k + 1
        n0 = base + 2 * k2
        n1 = base + 2 * k2 + 1
        faces.append((b0, b1, n1, n0))  # normal ke dalam
        fmat.append(0)
        fsmooth.append(True)

    # dasar luar + lantai dalam (kipas)
    for (z, rr) in ((0.0, r_at(0.0) + 0.006), (0.035, r_at(0.035) * 0.86)):
        base = len(verts)
        verts.append(Vector((0, 0, z)))
        for k in range(SEG):
            a = 2.0 * math.pi * k / SEG
            verts.append(Vector((rr * math.cos(a), rr * math.sin(a), z)))
        for k in range(SEG):
            k2 = (k + 1) % SEG
            faces.append((base, base + 1 + k, base + 1 + k2))
            fmat.append(0)
            fsmooth.append(False)

    # dua gagang tali teal
    for side in (1, -1):
        cy = side * (r_at(0.35) + 0.02)
        pts = []
        for k in range(13):
            a = math.pi * k / 12.0
            pts.append(Vector((0.028 * math.cos(a), cy, 0.35 + 0.028 * math.sin(a))))
        add_tube(verts, faces, fmat, fsmooth, pts, [0.004] * len(pts), 6, mat=3, smooth=True)

    obj = new_object("PRP_gear_basket", verts, faces, [m_woven, m_rim, m_band, m_rope], fmat, fsmooth, collection)
    obj.location = (-0.90, -0.30, 0.0)
    return obj


# ---------------------------------------------------------------------------
# scene
# ---------------------------------------------------------------------------


def setup_scene():
    scn = bpy.context.scene
    try:
        scn.render.engine = "BLENDER_EEVEE"
    except TypeError:
        pass  # nilai saat ini selalu valid, sudah EEVEE
    scn.render.resolution_x = 1920
    scn.render.resolution_y = 1080
    scn.render.fps = 24
    scn.view_settings.view_transform = "Standard"
    scn.frame_set(1)

    col = bpy.data.collections.get("Collection")
    if col is None:
        col = bpy.data.collections.new("PRP_gear")
        bpy.context.scene.collection.children.link(col)
    col.name = "PRP_gear"
    return col


def setup_world(scn):
    """World netral untuk pratinjau; look dev asli milik scene-1-look.blend."""
    world = scn.world
    if world is None:
        world = bpy.data.worlds.new("WLD_gear-preview")
        scn.world = world
    if world.name in ("World", "WLD_gear-preview"):
        world.name = "WLD_gear-preview"
    world.use_nodes = True
    nt = world.node_tree
    bg = next((n for n in nt.nodes if n.type == "BACKGROUND"), None)
    if bg is None:
        bg = nt.nodes.new("ShaderNodeBackground")
        out = next(n for n in nt.nodes if n.type == "OUTPUT_WORLD")
        nt.links.new(bg.outputs["Background"], out.inputs["Surface"])
    bg.inputs["Color"].default_value = (0.18, 0.19, 0.20, 1.0)
    bg.inputs["Strength"].default_value = 1.0


def setup_camera_lamp(scn, col):
    cam = bpy.data.objects.get("CAM_preview")
    if cam is None:
        cam = bpy.data.objects.new("CAM_preview", bpy.data.cameras.new("CAM_preview"))
    if cam.name not in col.objects:
        col.objects.link(cam)
    if cam.data.name == "Camera":
        cam.data.name = "CAM_preview"
    cam.location = (2.2, -2.4, 1.55)
    cam.rotation_euler = (Vector((0, 0, 0.18)) - cam.location).normalized().to_track_quat("-Z", "Y").to_euler()
    scn.camera = cam

    lgt = bpy.data.objects.get("LGT_gear_preview")
    if lgt is None:
        lgt = bpy.data.objects.new("LGT_gear_preview", bpy.data.lights.new("LGT_gear_preview", "AREA"))
    if lgt.name not in col.objects:
        col.objects.link(lgt)
    lgt.location = (1.5, -2.0, 2.6)
    lgt.rotation_euler = (Vector((0, 0, 0.15)) - lgt.location).normalized().to_track_quat("-Z", "Y").to_euler()
    lgt.data.energy = 60
    lgt.data.size = 2.5


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main():
    cleanup()
    col = setup_scene()

    m_net = material("MAT_gear_net", "0F5C63", roughness=0.55)
    m_float = material("MAT_gear_float", "E4713C", roughness=0.50)
    m_float_band = material("MAT_gear_float-band", "F2E9DC", roughness=0.55)
    m_woven = material("MAT_gear_basket-weave", "E8D5B0", roughness=0.70)
    m_rim = material("MAT_gear_basket-rim", "F2E9DC", roughness=0.60)
    m_band = material("MAT_gear_basket-band", "0F5C63", roughness=0.55)

    net = build_fishnet(m_net, col)
    flt = build_float(m_float, m_float_band, m_net, col)
    bsk = build_basket(m_woven, m_rim, m_band, m_net, col)

    setup_world(bpy.context.scene)
    setup_camera_lamp(bpy.context.scene, col)

    print("=== RINGKASAN ===")
    for obj in (net, flt, bsk):
        d = obj.dimensions
        print(
            f"{obj.name}: verts={len(obj.data.vertices)} "
            f"dims=({d.x:.2f}, {d.y:.2f}, {d.z:.2f}) m "
            f"origin={tuple(round(v, 3) for v in obj.location)}"
        )
    print("materials:", [m.name for m in bpy.data.materials if m.name.startswith("MAT_gear")])
    print("collections:", [c.name for c in bpy.data.collections])
    print("view_transform:", bpy.context.scene.view_settings.view_transform)
    print("frame:", bpy.context.scene.frame_current)


main()

"""
Membangun aset environment Scene 2 & 4: karang pulih muda (3 varian).

Hasil: assets/env/reef-recovering.blend (koleksi ENV_reef-recovering)
  ENV_reef_recovering-branching -> karang bercabang muda, tinggi 0,35 m
  ENV_reef_recovering-massive   -> karang massif, tinggi 0,30 m
  ENV_reef_recovering-table     -> karang meja, tinggi 0,25 m, cakram tipis

Origin setiap objek di dasar (z 0). Skala nyata. Total verts < 20k.
Warna hidup dari palette PROJECT.md §2: hijau terumbu #3E8E6E, teal #1FA3A3,
aksen oranye karang #E4713C (hanya ujung cabang / tepi cakram), pasir hangat
#E8D5B0 untuk alas. Tanpa tekstur image, tanpa pack.

Acuan: pengecualian environment prosedural lead 1 Nov 2026 (AGENTS.md §2.1) -
foto storyboard/refs/ref-reef-underwater_v001.jpg untuk bentuk karang bercabang
& massif, panel storyboard 4A/4B (karang yang mulai pulih) + palette. Tidak ada
foto yang dipakai sebagai tekstur.

Skrip idempoten: mengosongkan bpy.data manual (TIDAK memakai open_mainfile),
lalu menyimpan ke assets/env/reef-recovering.blend.
"""

import bpy
import math
import os
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

OUT = r"D:\Tugas Semester 5\Grafika Komputer\Project-Animasi\assets\env\reef-recovering.blend"

# ---------------------------------------------------------------------------
# utilitas
# ---------------------------------------------------------------------------


def srgb(hexstr):
    h = hexstr.lstrip("#")
    values = [int(h[i : i + 2], 16) / 255.0 for i in (0, 2, 4)]

    def to_linear(u):
        return u / 12.92 if u <= 0.04045 else ((u + 0.055) / 1.055) ** 2.4

    return tuple(to_linear(v) for v in values) + (1.0,)


def material(name, hexcol, roughness=0.7, metallic=0.0):
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
        spec.default_value = 0.28
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


def add_tube(V, F, FM, FS, points, radii, sides, mat=0, smooth=True, cap_end=False):
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
    if cap_end:
        last = base + (len(points) - 1) * sides
        F.append(tuple(last + j for j in range(sides)))
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


def normalize(V, target_h):
    """Skalakan seragam agar tinggi = target_h dan dasar di z 0."""
    zs = [p[2] for p in V]
    lo, hi = min(zs), max(zs)
    s = target_h / (hi - lo)
    for p in V:
        p[0] *= s
        p[1] *= s
        p[2] = (p[2] - lo) * s


# ---------------------------------------------------------------------------
# material index bersama
# ---------------------------------------------------------------------------

M_GREEN, M_TEAL, M_ORANGE, M_BASE = 0, 1, 2, 3


def build_branching(collection):
    V, F, FM, FS = [], [], [], []
    rng = random.Random(20261114)
    twig_total = [0]

    def grow(p, d, length, radius, depth):
        d = d.normalized()
        side = d.cross(Vector((0, 0, 1)))
        if side.length < 1e-6:
            side = Vector((1, 0, 0))
        side.normalize()
        bend = side * rng.uniform(-0.22, 0.22) * length
        bend += Vector((0, 0, 1)) * rng.uniform(0.02, 0.10) * length
        mid = p + d * (length * 0.55) + bend * 0.5
        tip = p + d * length + bend

        if depth >= 3:
            twig_total[0] += 1
            mat = M_ORANGE if rng.random() < 0.26 else M_TEAL
        else:
            mat = M_GREEN

        add_tube(
            V, F, FM, FS,
            [p, mid, tip],
            [radius, radius * 0.74, radius * 0.44],
            7,
            mat=mat,
            cap_end=depth >= 3,
        )
        if depth >= 3:
            return
        for k in range(2):
            axis = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-0.05, 0.55)))
            if axis.length < 1e-6:
                axis = Vector((1, 0, 0))
            axis.normalize()
            nd = (d + axis * rng.uniform(0.55, 0.95)).normalized()
            nd.z = max(nd.z, 0.22)
            nd.normalize()
            grow(tip, nd, length * rng.uniform(0.60, 0.76), radius * 0.64, depth + 1)

    # lima batang utama dari alas
    for k in range(5):
        a = 2.0 * math.pi * k / 5 + rng.uniform(-0.25, 0.25)
        d = Vector((math.cos(a), math.sin(a), rng.uniform(0.75, 1.05))).normalized()
        start = Vector((0.02 * math.cos(a), 0.02 * math.sin(a), 0.015))
        grow(start, d, rng.uniform(0.105, 0.135), 0.028, 0)

    # alas kerak
    seg = 20
    base_idx = len(V)
    z0, z1 = 0.0, 0.022
    for k in range(seg):
        a = 2.0 * math.pi * k / seg
        V.append(Vector((0.105 * math.cos(a), 0.088 * math.sin(a), z0)))
    for k in range(seg):
        a = 2.0 * math.pi * k / seg
        V.append(Vector((0.085 * math.cos(a), 0.070 * math.sin(a), z1)))
    for k in range(seg):
        k2 = (k + 1) % seg
        F.append((base_idx + k, base_idx + k2, base_idx + seg + k2, base_idx + seg + k))
        FM.append(M_BASE)
        FS.append(True)
    F.append(tuple(base_idx + seg + k for k in range(seg)))
    FM.append(M_BASE)
    FS.append(False)

    normalize(V, 0.35)
    obj = new_object("ENV_reef_recovering-branching", V, F, [], FM, FS, collection)
    obj["twigs"] = twig_total[0]
    return obj


def build_massive(collection):
    V, F, FM, FS = [], [], [], []
    H, R = 0.30, 0.230
    rings, seg = 14, 40
    apex = len(V)
    V.append(Vector((0.0, 0.0, H)))

    ring_start = []
    for i in range(1, rings + 1):
        t = i / rings
        th = t * math.pi / 2.0
        z = H * math.cos(th)
        rad = R * math.sin(th)
        start = len(V)
        ring_start.append(start)
        for k in range(seg):
            phi = 2.0 * math.pi * k / seg
            lump = (
                1.0
                + 0.14 * math.sin(3.0 * phi + 0.5)
                + 0.11 * math.sin(5.0 * phi + 1.8 + 1.2 * t)
                + 0.05 * math.sin(9.0 * phi + 2.6)
                + 0.04 * math.sin(2.0 * phi + 0.9 + 3.5 * t)
                + 0.016 * math.sin(17.0 * phi + 6.0 * t)
            )
            r = rad * lump
            V.append(Vector((r * math.cos(phi), r * math.sin(phi), z)))

    first = ring_start[0]
    for k in range(seg):
        k2 = (k + 1) % seg
        F.append((apex, first + k, first + k2))
        FM.append(M_GREEN)
        FS.append(True)

    for i in range(len(ring_start) - 1):
        a0 = ring_start[i]
        b0 = ring_start[i + 1]
        t = (i + 1) / rings
        for k in range(seg):
            k2 = (k + 1) % seg
            phi = 2.0 * math.pi * (k + 0.5) / seg
            lump = (
                1.0
                + 0.14 * math.sin(3.0 * phi + 0.5)
                + 0.11 * math.sin(5.0 * phi + 1.8 + 1.2 * t)
                + 0.05 * math.sin(9.0 * phi + 2.6)
                + 0.04 * math.sin(2.0 * phi + 0.9 + 3.5 * t)
                + 0.016 * math.sin(17.0 * phi + 6.0 * t)
            )
            teal = t > 0.86
            F.append((a0 + k, b0 + k, b0 + k2, a0 + k2))
            FM.append(M_TEAL if teal else M_GREEN)
            FS.append(True)

    # tutup dasar
    base_ring = ring_start[-1]
    center = len(V)
    V.append(Vector((0.0, 0.0, 0.0)))
    for k in range(seg):
        k2 = (k + 1) % seg
        F.append((center, base_ring + k2, base_ring + k))
        FM.append(M_BASE)
        FS.append(False)

    normalize(V, 0.30)
    return new_object("ENV_reef_recovering-massive", V, F, [], FM, FS, collection)


def build_table(collection):
    V, F, FM, FS = [], [], [], []

    # batang
    pts = [Vector((0, 0, 0)), Vector((0.012, 0.004, 0.09)), Vector((0.004, 0, 0.205))]
    add_tube(V, F, FM, FS, pts, [0.058, 0.040, 0.030], 10, mat=M_TEAL)

    # cakram
    r_plate = 0.30
    z_rim_top, z_rim_bot = 0.238, 0.224
    rings, seg = 18, 48

    def edge(phi):
        return r_plate * (1.0 + 0.05 * math.sin(5.0 * phi + 0.6) + 0.025 * math.sin(9.0 * phi + 2.0))

    tops = []
    under = []
    for i in range(1, rings + 1):
        frac = i / rings
        tops.append(len(V))
        for k in range(seg):
            phi = 2.0 * math.pi * k / seg
            er = edge(phi)
            r = er * frac
            z = (
                z_rim_top
                + 0.012 * (1.0 - frac * frac)
                + 0.0028 * math.sin(7.0 * phi + 0.8) * (frac ** 3)
            )
            V.append(Vector((r * math.cos(phi), r * math.sin(phi), z)))
    for i in range(1, rings + 1):
        frac = i / rings
        under.append(len(V))
        for k in range(seg):
            phi = 2.0 * math.pi * k / seg
            er = edge(phi)
            r = er * frac
            z = z_rim_bot + 0.006 * (1.0 - frac * frac)
            V.append(Vector((r * math.cos(phi), r * math.sin(phi), z)))

    ctop = len(V)
    V.append(Vector((0.0, 0.0, z_rim_top + 0.012)))
    cbot = len(V)
    V.append(Vector((0.0, 0.0, z_rim_bot + 0.006)))

    for k in range(seg):
        k2 = (k + 1) % seg
        F.append((ctop, tops[0] + k, tops[0] + k2))
        FM.append(M_GREEN)
        FS.append(True)
        F.append((cbot, under[0] + k2, under[0] + k))
        FM.append(M_TEAL)
        FS.append(True)

    for i in range(len(tops) - 1):
        a0, b0 = tops[i], tops[i + 1]
        a1, b1 = under[i], under[i + 1]
        band_rim = i == len(tops) - 2
        for k in range(seg):
            k2 = (k + 1) % seg
            F.append((a0 + k, b0 + k, b0 + k2, a0 + k2))
            FM.append(M_ORANGE if band_rim else M_GREEN)
            FS.append(True)
            F.append((a1 + k, a1 + k2, b1 + k2, b1 + k))
            FM.append(M_TEAL)
            FS.append(True)

    # pita tepi (rim) atas-bawah
    outer_t, outer_u = tops[-1], under[-1]
    for k in range(seg):
        k2 = (k + 1) % seg
        F.append((outer_t + k, outer_t + k2, outer_u + k2, outer_u + k))
        FM.append(M_TEAL)
        FS.append(True)

    normalize(V, 0.25)
    return new_object("ENV_reef_recovering-table", V, F, [], FM, FS, collection)


# ---------------------------------------------------------------------------
# scene & pratinjau
# ---------------------------------------------------------------------------


def setup_scene():
    scn = bpy.context.scene
    scn.name = "reef-recovering"
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

    gmat = material("MAT_preview-ground", "#4A4F4A", roughness=0.95)
    mesh = bpy.data.meshes.new("PREVIEW_ground")
    s = 6.0
    mesh.from_pydata(
        [(-s, -s, -0.002), (s, -s, -0.002), (s, s, -0.002), (-s, s, -0.002)],
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
    cam.location = (0.0, -1.72, 0.62)
    cam.rotation_euler = (
        Vector((0.0, 0.0, 0.16)) - cam.location
    ).normalized().to_track_quat("-Z", "Y").to_euler()
    scn.camera = cam

    key = bpy.data.objects.new("LGT_preview-key", bpy.data.lights.new("LGT_preview-key", "SUN"))
    prev.objects.link(key)
    key.data.energy = 2.7
    key.data.angle = math.radians(10)
    key.rotation_euler = (math.radians(50), 0.0, math.radians(28))

    fill = bpy.data.objects.new("LGT_preview-fill", bpy.data.lights.new("LGT_preview-fill", "AREA"))
    prev.objects.link(fill)
    fill.data.energy = 90.0
    fill.data.size = 3.0
    fill.location = (-1.7, -1.5, 1.1)
    fill.rotation_euler = (
        Vector((0.0, 0.0, 0.15)) - fill.location
    ).normalized().to_track_quat("-Z", "Y").to_euler()

    rim = bpy.data.objects.new("LGT_preview-rim", bpy.data.lights.new("LGT_preview-rim", "AREA"))
    prev.objects.link(rim)
    rim.data.energy = 60.0
    rim.data.size = 2.5
    rim.location = (1.6, 1.4, 1.4)
    rim.rotation_euler = (
        Vector((0.0, 0.0, 0.2)) - rim.location
    ).normalized().to_track_quat("-Z", "Y").to_euler()

    world = bpy.data.worlds.new("WLD_reef-recovering-preview")
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.050, 0.085, 0.095, 1.0)
    bg.inputs["Strength"].default_value = 1.0
    scn.world = world
    return cam


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main():
    wipe_data()
    scn = setup_scene()

    col = bpy.data.collections.new("ENV_reef-recovering")
    scn.collection.children.link(col)

    m_green = material("MAT_reef_recovering_green", PAL["reef"], roughness=0.72)
    m_teal = material("MAT_reef_recovering_teal", PAL["teal"], roughness=0.62)
    m_orange = material("MAT_reef_recovering_orange", PAL["orange"], roughness=0.60)
    m_base = material("MAT_reef_recovering_base", PAL["sand"], roughness=0.88)
    mats = [m_green, m_teal, m_orange, m_base]

    branching = build_branching(col)
    massive = build_massive(col)
    table = build_table(col)
    for obj in (branching, massive, table):
        for m in mats:
            obj.data.materials.append(m)

    setup_preview(scn)

    scn["asset"] = "reef-recovering"
    scn["asset_note"] = "3 varian karang pulih Scene 2/4. Origin di dasar z 0, skala nyata."

    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=OUT, check_existing=False)

    print("=== RINGKASAN reef-recovering ===")
    total_v = 0
    for obj in (branching, massive, table):
        d = obj.dimensions
        total_v += len(obj.data.vertices)
        print(
            f"{obj.name:34s} verts={len(obj.data.vertices):5d} "
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

"""
Membangun ikan cakalang (skipjack tuna) — blockout bentuk, bukan sculpt final.

Hasil: assets/env/fish-cakalang.blend
  scene "fish-cakalang"
    koleksi ENV_fish
      +-- empty CTL_fish                   pivot induk di origin dunia
      +-- ENV_fish_cakalang                badan + kepala + mata
      +-- ENV_fish_cakalang_dorsal         sirip punggung tinggi + 7 finlet
      +-- ENV_fish_cakalang_tail           ekor bercabang dalam
      +-- ENV_fish_cakalang_pectoral       sirip dada, perut, dan anal
    koleksi PREVIEW                        kamera + lampu + lantai

Acuan bentuk & warna: storyboard/refs/ref-cakalang_v001.jpg (ilustrasi ikan
cakalang: badan torpedo memanjang, punggung biru gelap, perut perak, sirip
kekuningan, ekor bercabang dalam). Foto HANYA acuan proporsi/siluet — tidak
dipakai sebagai tekstur, latar, atau image plane.

Skala nyata & orientasi:
  panjang total (moncong -> ujung ekor) ±0,70 m
  hadap -Y  (moncong di -Y, ekor di +Y)
  origin di tengah badan, z 0 = garis tengah badan
  tinggi badan maks ±0,165 m, lebar maks ±0,115 m

Material (palette PROJECT.md §2, tanpa tekstur):
  MAT_fish_back    #0F5C63  (teal dalam)  punggung
  MAT_fish_belly   #F2E9DC  (krem tulang) perut perak-krem
  MAT_fish_fin     #E4713C  (oranye karang) sirip — hanya aksen
  MAT_fish_eye     #2E383A  (netral gelap) mata

Skrip IDEMPOTEN terhadap datablock miliknya dan MENYIMPAN file di akhir.
Tanpa open_mainfile / read_factory_settings / read_homefile; file aktif
dilepas lewat save_as_mainfile ke renders/tmp/_wipe.blend.
"""

import bpy
import bmesh
import os
import math
import datetime
from math import cos, sin, pi, copysign
from mathutils import Vector

# ---------------------------------------------------------------------------
# konstanta
# ---------------------------------------------------------------------------

HEX_BACK = "#0F5C63"   # teal dalam, palette §2
HEX_BELLY = "#F2E9DC"  # krem tulang, palette §2
HEX_FIN = "#E4713C"    # oranye karang, palette §2 (aksen)
HEX_EYE = "#2E383A"    # netral gelap (14 Nov 2026)
HEX_GROUND = "#2E383A"

SEG_BODY = 28
SEG_EYE = 14

# (y, rx, rz, cz) — moncong di -0,35 sampai batang ekor di +0,272
BODY = [
    (-0.350, 0.007, 0.009, 0.000),
    (-0.335, 0.018, 0.028, 0.000),
    (-0.305, 0.031, 0.047, 0.002),
    (-0.265, 0.042, 0.062, 0.003),
    (-0.215, 0.050, 0.073, 0.003),
    (-0.155, 0.056, 0.080, 0.001),
    (-0.085, 0.058, 0.082, 0.000),
    (0.000, 0.055, 0.077, -0.002),
    (0.070, 0.047, 0.067, -0.002),
    (0.140, 0.037, 0.051, 0.000),
    (0.200, 0.025, 0.033, 0.004),
    (0.245, 0.016, 0.020, 0.006),
    (0.272, 0.011, 0.013, 0.008),
]

# ---------------------------------------------------------------------------
# utilitas mesh
# ---------------------------------------------------------------------------


def srgb(hexstr):
    h = hexstr.lstrip("#")
    values = [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]

    def to_linear(u):
        return u / 12.92 if u <= 0.04045 else ((u + 0.055) / 1.055) ** 2.4

    return tuple(to_linear(v) for v in values) + (1.0,)


def superellipse(rx, ry, t, exp):
    ct, st = cos(t), sin(t)
    x = rx * copysign(abs(ct) ** (2.0 / exp), ct)
    y = ry * copysign(abs(st) ** (2.0 / exp), st)
    return x, y


def new_mesh_object(name, V, F, FM, FS, mats, collection):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(V, [], F)
    for m in mats:
        mesh.materials.append(m)
    for poly, mat_index, smooth in zip(mesh.polygons, FM, FS):
        poly.material_index = mat_index
        poly.use_smooth = smooth
    mesh.validate(verbose=False)
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    return obj


def material(name, hexcol, roughness=0.6, metallic=0.0, spec=0.5):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.use_backface_culling = False
    col = srgb(hexcol)
    mat.diffuse_color = col
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = col
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    spec_in = bsdf.inputs.get("Specular IOR Level") or bsdf.inputs.get("Specular")
    if spec_in is not None:
        spec_in.default_value = spec
    return mat


# ---------------------------------------------------------------------------
# badan
# ---------------------------------------------------------------------------


def body_profile(y):
    """Interpolasi profil badan pada posisi y -> (rx, rz, cz)."""
    pts = BODY
    if y <= pts[0][0]:
        return pts[0][1], pts[0][2], pts[0][3]
    if y >= pts[-1][0]:
        return pts[-1][1], pts[-1][2], pts[-1][3]
    for k in range(len(pts) - 1):
        y0, rx0, rz0, cz0 = pts[k]
        y1, rx1, rz1, cz1 = pts[k + 1]
        if y0 <= y <= y1:
            t = (y - y0) / (y1 - y0)
            return (rx0 + (rx1 - rx0) * t,
                    rz0 + (rz1 - rz0) * t,
                    cz0 + (cz1 - cz0) * t)
    return pts[-1][1], pts[-1][2], pts[-1][3]


def body_top(y):
    rx, rz, cz = body_profile(y)
    return cz + rz


def body_bottom(y):
    rx, rz, cz = body_profile(y)
    return cz - rz


def build_body(mats, col):
    V, F, FM, FS = [], [], [], []
    M_BACK, M_BELLY, M_FIN, M_EYE = 0, 1, 2, 3

    starts = []
    for (y, rx, rz, cz) in BODY:
        starts.append(len(V))
        for i in range(SEG_BODY):
            a, b = superellipse(rx, rz, 2.0 * pi * i / SEG_BODY, 2.15)
            V.append(Vector((a, y, cz + b)))
    for k in range(len(starts) - 1):
        a, b = starts[k], starts[k + 1]
        for i in range(SEG_BODY):
            i2 = (i + 1) % SEG_BODY
            F.append((a + i, a + i2, b + i2, b + i))
            # punggung gelap di atas garis sisi, perut terang di bawahnya
            zc = (V[a + i].z + V[a + i2].z + V[b + i].z + V[b + i2].z) / 4.0
            FM.append(M_BACK if zc > 0.004 else M_BELLY)
            FS.append(True)
    # moncong & batang ekor ditutup
    F.append(tuple(starts[0] + i for i in range(SEG_BODY - 1, -1, -1)))
    FM.append(M_BACK)
    FS.append(False)
    F.append(tuple(starts[-1] + i for i in range(SEG_BODY)))
    FM.append(M_BACK)
    FS.append(False)

    # mata: bola kecil di kedua sisi kepala
    for sx in (-1.0, 1.0):
        cx = sx * 0.033
        cy = -0.288
        cz = 0.016
        top = len(V)
        V.append(Vector((cx, cy, cz + 0.0105)))
        rings = []
        for ir in range(1, 6):
            th = pi * ir / 6
            s, c = sin(th), cos(th)
            st = len(V)
            for i in range(SEG_EYE):
                ph = 2.0 * pi * i / SEG_EYE
                V.append(Vector((cx + 0.0105 * s * cos(ph) * 0.55,
                                 cy + 0.0105 * s * sin(ph),
                                 cz + 0.0105 * c)))
            rings.append(st)
        bot = len(V)
        V.append(Vector((cx, cy, cz - 0.0105)))
        for i in range(SEG_EYE):
            i2 = (i + 1) % SEG_EYE
            F.append((top, rings[0] + i, rings[0] + i2))
            FM.append(M_EYE)
            FS.append(True)
        for k in range(len(rings) - 1):
            a, b = rings[k], rings[k + 1]
            for i in range(SEG_EYE):
                i2 = (i + 1) % SEG_EYE
                F.append((a + i, b + i, b + i2, a + i2))
                FM.append(M_EYE)
                FS.append(True)
        last = rings[-1]
        for i in range(SEG_EYE):
            i2 = (i + 1) % SEG_EYE
            F.append((bot, last + i2, last + i))
            FM.append(M_EYE)
            FS.append(True)

    obj = new_mesh_object("ENV_fish_cakalang", V, F, FM, FS,
                          [mats["back"], mats["belly"], mats["fin"], mats["eye"]],
                          col)
    obj["part"] = "body"
    return obj


# ---------------------------------------------------------------------------
# sirip
# ---------------------------------------------------------------------------


def slab(V, F, FM, FS, outline, normal, thickness, mat, smooth=True):
    """Pelat tipis dari poligon planar (outline 3D) + ketebalan di `normal`."""
    n = normal.normalized() * (thickness * 0.5)
    base = len(V)
    for p in outline:
        V.append(Vector(p) - n)
    for p in outline:
        V.append(Vector(p) + n)
    m = len(outline)
    F.append(tuple(base + i for i in range(m - 1, -1, -1)))
    FM.append(mat)
    FS.append(False)
    F.append(tuple(base + m + i for i in range(m)))
    FM.append(mat)
    FS.append(False)
    for i in range(m):
        i2 = (i + 1) % m
        F.append((base + i, base + i2, base + m + i2, base + m + i))
        FM.append(mat)
        FS.append(smooth)


def build_dorsal(mats, col):
    V, F, FM, FS = [], [], [], []
    M = 0

    # sirip punggung pertama: segitiga tinggi di atas badan
    y0, y1 = -0.150, -0.030
    outline = [
        (0.0, y0, body_top(y0) - 0.012),
        (0.0, y0 + 0.026, 0.152),
        (0.0, y0 + 0.038, 0.147),
        (0.0, y1, body_top(y1) - 0.012),
    ]
    slab(V, F, FM, FS, outline, Vector((1, 0, 0)), 0.008, M)

    # finlet punggung: 7 sirip kecil menuju ekor
    for i in range(7):
        y = 0.012 + i * 0.030
        h = 0.022 - i * 0.0012
        base_z = body_top(y) - 0.006
        tri = [
            (0.0, y, base_z),
            (0.0, y + 0.008, base_z + h),
            (0.0, y + 0.017, base_z),
        ]
        slab(V, F, FM, FS, tri, Vector((1, 0, 0)), 0.005, M)

    obj = new_mesh_object("ENV_fish_cakalang_dorsal", V, F, FM, FS,
                          [mats["fin"]], col)
    obj["part"] = "dorsal+finlet"
    return obj


def build_tail(mats, col):
    V, F, FM, FS = [], [], [], []
    M = 0
    y_base = 0.266

    # ekor bercabang dalam: dua cuping lebar
    upper = [
        (0.0, y_base, 0.010),
        (0.0, 0.300, 0.048),
        (0.0, 0.340, 0.098),
        (0.0, 0.352, 0.090),
        (0.0, 0.316, 0.008),
    ]
    lower = [(x, y, -z) for (x, y, z) in upper]
    slab(V, F, FM, FS, upper, Vector((1, 0, 0)), 0.010, M)
    slab(V, F, FM, FS, lower, Vector((1, 0, 0)), 0.010, M)
    # sambungan cuping ke batang ekor
    tri = [
        (0.0, 0.260, 0.012),
        (0.0, 0.300, 0.010),
        (0.0, 0.260, -0.012),
    ]
    slab(V, F, FM, FS, tri, Vector((1, 0, 0)), 0.012, M)

    obj = new_mesh_object("ENV_fish_cakalang_tail", V, F, FM, FS,
                          [mats["fin"]], col)
    obj["part"] = "caudal"
    return obj


def build_pectoral(mats, col):
    V, F, FM, FS = [], [], [], []
    M = 0

    for sx in (-1.0, 1.0):
        # sirip dada: pelat mendatar, menyapu ke belakang
        pect = [
            (sx * 0.045, -0.190, -0.008),
            (sx * 0.108, -0.150, -0.020),
            (sx * 0.100, -0.112, -0.026),
            (sx * 0.046, -0.132, -0.014),
        ]
        slab(V, F, FM, FS, pect, Vector((0, 0, 1)), 0.006, M)
        # sirip perut: kecil, di bawah badan
        pelv = [
            (sx * 0.012, -0.070, body_bottom(-0.070) + 0.010),
            (sx * 0.030, -0.040, body_bottom(-0.040) + 0.008),
            (sx * 0.026, -0.020, -0.082),
            (sx * 0.012, -0.048, -0.076),
        ]
        slab(V, F, FM, FS, pelv, Vector((0, 0, 1)), 0.005, M)

    # sirip anal: satu pelat kecil di bawah dekat ekor
    anal = [
        (0.0, 0.130, body_bottom(0.130) + 0.008),
        (0.0, 0.155, -0.062),
        (0.0, 0.196, body_bottom(0.196) + 0.006),
    ]
    slab(V, F, FM, FS, anal, Vector((1, 0, 0)), 0.005, M)
    # finlet anal
    for i in range(5):
        y = 0.190 + i * 0.016
        h = 0.016 - i * 0.0012
        base_z = body_bottom(y) + 0.004
        tri = [
            (0.0, y, base_z),
            (0.0, y + 0.006, base_z - h),
            (0.0, y + 0.013, base_z),
        ]
        slab(V, F, FM, FS, tri, Vector((1, 0, 0)), 0.004, M)

    obj = new_mesh_object("ENV_fish_cakalang_pectoral", V, F, FM, FS,
                          [mats["fin"]], col)
    obj["part"] = "pectoral+pelvic+anal"
    return obj


# ---------------------------------------------------------------------------
# scene, preview, simpan
# ---------------------------------------------------------------------------


def set_engine(scn):
    last = None
    for cand in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scn.render.engine = cand
            return cand
        except TypeError as err:
            last = err
    print("PERINGATAN: gagal set EEVEE:", last)
    return scn.render.engine


def setup_scene(scn):
    scn.name = "fish-cakalang"
    scn.render.resolution_x = 1920
    scn.render.resolution_y = 1080
    scn.render.resolution_percentage = 100
    scn.render.fps = 24
    scn.render.fps_base = 1.0
    scn.view_settings.view_transform = "Standard"
    try:
        scn.view_settings.look = "None"
    except TypeError:
        pass
    scn.frame_start = 1
    scn.frame_end = 48
    scn.frame_set(1)
    engine = set_engine(scn)
    try:
        scn.eevee.taa_render_samples = 32
    except AttributeError:
        pass
    scn.render.image_settings.file_format = "PNG"
    scn.render.image_settings.color_mode = "RGBA"
    scn.render.film_transparent = False
    scn["asset"] = "fish-cakalang"
    scn["asset_note"] = ("Ikan cakalang 0,70 m, hadap -Y, origin tengah badan. "
                         "Acuan ref-cakalang_v001.jpg; warna palette §2, tanpa tekstur.")
    return scn, engine


def setup_preview(scn):
    prev = bpy.data.collections.new("PREVIEW")
    scn.collection.children.link(prev)

    ground_mat = material("MAT_preview_fish-ground", HEX_GROUND, roughness=0.95,
                          spec=0.1)
    mesh = bpy.data.meshes.new("PREVIEW_ground")
    mesh.from_pydata(
        [(-6, -6, -0.45), (6, -6, -0.45), (6, 6, -0.45), (-6, 6, -0.45)],
        [], [(0, 1, 2, 3)],
    )
    mesh.materials.append(ground_mat)
    mesh.update()
    prev.objects.link(bpy.data.objects.new("PREVIEW_ground", mesh))

    cam_data = bpy.data.cameras.new("CAM_preview")
    cam_data.lens = 60.0
    cam = bpy.data.objects.new("CAM_preview", cam_data)
    prev.objects.link(cam)
    cam.location = (0.40, -0.95, 0.28)
    cam.rotation_euler = (Vector((0.0, 0.0, 0.01)) - cam.location).normalized(
    ).to_track_quat("-Z", "Y").to_euler()
    scn.camera = cam

    key = bpy.data.objects.new("LGT_preview-key",
                               bpy.data.lights.new("LGT_preview-key", "SUN"))
    prev.objects.link(key)
    key.data.energy = 2.2
    key.data.angle = math.radians(20)
    key.rotation_euler = (math.radians(48), 0.0, math.radians(32))

    fill = bpy.data.objects.new("LGT_preview-fill",
                                bpy.data.lights.new("LGT_preview-fill", "AREA"))
    prev.objects.link(fill)
    fill.data.energy = 45.0
    fill.data.size = 1.6
    fill.location = (-0.9, -0.7, 0.55)
    fill.rotation_euler = (Vector((0, 0, 0.05)) - fill.location).normalized(
    ).to_track_quat("-Z", "Y").to_euler()

    rim = bpy.data.objects.new("LGT_preview-rim",
                               bpy.data.lights.new("LGT_preview-rim", "AREA"))
    prev.objects.link(rim)
    rim.data.energy = 70.0
    rim.data.size = 1.4
    rim.location = (0.9, 0.9, 0.7)
    rim.rotation_euler = (Vector((0, 0, 0.05)) - rim.location).normalized(
    ).to_track_quat("-Z", "Y").to_euler()

    world = bpy.data.worlds.new("WLD_fish-preview")
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.055, 0.068, 0.075, 1.0)
    bg.inputs["Strength"].default_value = 1.0
    scn.world = world
    return cam


def repo_root():
    try:
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    except NameError:
        return os.getcwd()


def log(line):
    path = os.path.join(repo_root(), "renders", "logs", "modeling.log")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    stamp = datetime.datetime.now().strftime("%H:%M")
    with open(path, "a", encoding="utf-8") as fh:
        fh.write("[%s] %s\n" % (stamp, line))


def release_and_wipe():
    tmp = os.path.join(repo_root(), "renders", "tmp", "_wipe.blend")
    os.makedirs(os.path.dirname(tmp), exist_ok=True)
    try:
        bpy.context.preferences.filepaths.save_version = 0
    except Exception:
        pass
    if bpy.data.filepath and os.path.abspath(bpy.data.filepath) != os.path.abspath(tmp):
        bpy.ops.wm.save_as_mainfile(filepath=tmp)

    scn = bpy.context.scene
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for col in list(bpy.data.collections):
        bpy.data.collections.remove(col)
    for s in list(bpy.data.scenes):
        if s is not scn:
            bpy.data.scenes.remove(s)
    for blocks in (bpy.data.meshes, bpy.data.materials, bpy.data.cameras,
                   bpy.data.lights, bpy.data.armatures, bpy.data.actions,
                   bpy.data.curves, bpy.data.node_groups, bpy.data.worlds,
                   bpy.data.images):
        for b in list(blocks):
            try:
                blocks.remove(b)
            except Exception:
                pass
    return scn


def render_previews():
    scn = bpy.context.scene
    cam = scn.camera
    out_dir = os.path.join(repo_root(), "renders", "stills")
    os.makedirs(out_dir, exist_ok=True)
    shots = [
        ("cakalang_preview-01", (0.72, -1.10, 0.34), (0.0, 0.0, 0.01), 45.0),
        ("cakalang_preview-02", (-0.30, -1.05, 0.72), (0.0, 0.02, 0.0), 45.0),
    ]
    scn.render.resolution_percentage = 50
    paths = []
    for name, loc, tgt, lens in shots:
        cam.location = loc
        cam.data.lens = lens
        cam.rotation_euler = (Vector(tgt) - Vector(loc)).normalized().to_track_quat(
            "-Z", "Y").to_euler()
        path = os.path.join(out_dir, name + ".png")
        scn.render.filepath = path
        bpy.ops.render.render(write_still=True)
        paths.append(path)
        print("render ->", path)
    scn.render.resolution_percentage = 100
    return paths


def main():
    scn = release_and_wipe()
    scn, engine = setup_scene(scn)
    log("MCP - Blender siap; scene fish-cakalang diset (EEVEE, 1920x1080, 24 fps, Standard)")

    mats = {
        "back": material("MAT_fish_back", HEX_BACK, roughness=0.46, spec=0.32),
        "belly": material("MAT_fish_belly", HEX_BELLY, roughness=0.40, spec=0.38),
        "fin": material("MAT_fish_fin", HEX_FIN, roughness=0.50, spec=0.30),
        "eye": material("MAT_fish_eye", HEX_EYE, roughness=0.18, spec=0.60),
    }

    root = bpy.data.collections.new("ENV_fish")
    scn.collection.children.link(root)

    ctl = bpy.data.objects.new("CTL_fish", None)
    ctl.empty_display_type = "PLAIN_AXES"
    ctl.empty_display_size = 0.20
    ctl.location = (0.0, 0.0, 0.0)
    ctl["asset"] = "ENV_fish_cakalang"
    ctl["note"] = "pivot induk; origin di tengah badan, z 0 = garis tengah"
    ctl["facing"] = "-Y"
    root.objects.link(ctl)

    body = build_body(mats, root)
    dorsal = build_dorsal(mats, root)
    tail = build_tail(mats, root)
    pectoral = build_pectoral(mats, root)

    for obj in (body, dorsal, tail, pectoral):
        obj.parent = ctl
        obj.matrix_parent_inverse = ctl.matrix_world.inverted()
        obj["facing"] = "-Y"

    setup_preview(scn)

    objs = (body, dorsal, tail, pectoral)
    total = 0
    print("=== RINGKASAN ENV_fish_cakalang ===")
    for obj in objs:
        d = obj.dimensions
        v = len(obj.data.vertices)
        total += v
        print("%-30s verts=%5d faces=%5d dims=(%.3f, %.3f, %.3f) m"
              % (obj.name, v, len(obj.data.polygons), d.x, d.y, d.z))
    # bounding box total
    xs, ys, zs = [], [], []
    for obj in objs:
        for c in obj.bound_box:
            p = obj.matrix_world @ Vector(c)
            xs.append(p.x)
            ys.append(p.y)
            zs.append(p.z)
    print("panjang total (Y): %.3f m | lebar %.3f | tinggi %.3f"
          % (max(ys) - min(ys), max(xs) - min(xs), max(zs) - min(zs)))
    print("total verts:", total)
    print("materials:", [m.name for m in bpy.data.materials])
    print("engine=%s vt=%s res=%dx%d fps=%d frame=%d"
          % (engine, scn.view_settings.view_transform, scn.render.resolution_x,
             scn.render.resolution_y, scn.render.fps, scn.frame_current))

    target = os.path.join(repo_root(), "assets", "env", "fish-cakalang.blend")
    bpy.ops.wm.save_as_mainfile(filepath=target, check_existing=False)
    print("saved:", target, "%.1f KB" % (os.path.getsize(target) / 1024.0))
    log("MODEL - fish-cakalang.blend: badan+dorsal+tail+pectoral, %d vert, panjang %.3f m"
        % (total, max(ys) - min(ys)))

    paths = render_previews()
    log("VERIFY - cakalang_preview-01/02 50%%: %s" % ", ".join(
        os.path.basename(p) for p in paths))


if __name__ == "__main__":
    main()

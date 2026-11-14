"""Build assets/env/reef-dense_v003.blend — titik selam padat untuk Scene 1/4.

v003 (14 Nov 2026) — reef-dense_v002 dipadatkan atas permintaan Director:

  karang      140 buah (84 bercabang / 46 massif / 10 meja) dalam 12 klaster
              di area 20 x 20 m, tinggi 0,30–1,60 m  (v002: 72)
  lamun       600 rumpun, tinggi 0,15–0,45 m, di sela karang (v002: 240)
  dasar       pasir 26 x 26 m, datum z = -5 m
  ikan        3 sekolah, tiap sekolah = sub-koleksi + empty pivot di (0,0,0):
                ENV_school_cakalang    12 cakalang   (mesh fish-cakalang.blend)
                ENV_school_kakatua     20 kakatua    (mesh reef.blend + sirip)
                ENV_school_damselfish  24 damselfish (mesh reef.blend + sirip)

Ikan **tidak dianimasikan**: semuanya di-parent ke empty pivot sekolah, origin
di tengah badan, menghadap -Y. Teknisi yang menggerakkan empty + bob per ikan.

Material karang di-append apa adanya dari reef-dense_v002.blend supaya look
v002 tidak berubah:
  MAT_reef_coral-branching / -massive / -table / -accent  (+ pasir & lamun)
Semua prosedural, tanpa tekstur gambar. Aksen oranye <10% luas permukaan.

Mesh karang diambil dari assets/env/reef.blend, di-append `link=False`, modifier
(skin/subsurf/displace) dievaluasi sekali lalu di-decimate — instance memakai
mesh hasil itu, jadi 140 karang tidak menambah vert unik. Tidak ada file sumber
yang diubah.

Jalankan utuh:

    blender -b --python scripts/build-reef-dense-v003.py

Atau bertahap lewat Blender MCP (namespace baru per tahap, state bpy tetap):

    g = {"__name__": "reefbuild"}; exec(open(SCRIPT).read(), g)
    g["stage_setup_and_corals"]()      # wipe + karang + pasir  -> simpan
    g["stage_seagrass_fish_finish"]()  # lamun + 3 sekolah + kamera -> simpan
    g["render_previews"]()             # 2 render 50%
"""
import bpy
import bmesh
import math
import os
import random

from mathutils import Vector

try:
    from mathutils.noise import noise as mnoise
except Exception:  # pragma: no cover
    def mnoise(v):
        return math.sin(v.x * 1.7) * math.cos(v.y * 1.3) * 0.5

try:
    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
except NameError:
    ROOT = r"D:\Tugas Semester 5\Grafika Komputer\Project-Animasi"

ENV_DIR = os.path.join(ROOT, "assets", "env")
REEF = os.path.join(ENV_DIR, "reef.blend")
FISH = os.path.join(ENV_DIR, "fish-cakalang.blend")
V002 = os.path.join(ENV_DIR, "reef-dense_v002.blend")
OUT = os.path.join(ENV_DIR, "reef-dense_v003.blend")
WIPE = os.path.join(ROOT, "renders", "tmp", "_wipe.blend")
STILLS = os.path.join(ROOT, "renders", "stills")

SEED = 20261114
SEABED_Z = -5.0
SEABED_HALF = 13.0          # 26 x 26 m
AREA_HALF = 10.0            # karang tersebar di 20 x 20 m
CORAL_TOTAL = 140
N_BRANCH = 84
N_BOULDER = 46
N_TABLE = 10
CLUSTER_COUNT = 12
CORAL_H_MIN, CORAL_H_MAX = 0.30, 1.60
SEAGRASS_CLUMPS = 600
SEAGRASS_H_MIN, SEAGRASS_H_MAX = 0.15, 0.45

ROOT_COLL = "ENV_reef-dense"
CTL = "CTL_reef-dense"

CORAL_SRC = ["ENV_reef_branching-coral", "ENV_reef_branching-coral_b",
             "ENV_reef_boulder-coral", "ENV_reef_table-coral",
             "ENV_reef_table-coral_stem"]

MAT_CORAL = ["MAT_reef_coral-branching", "MAT_reef_coral-massive",
             "MAT_reef_coral-table", "MAT_reef_coral-accent"]
MAT_OTHER = ["MAT_dense_sand", "MAT_dense_seagrass", "MAT_dense_seagrass-dark"]

# Sekolah ikan: (nama, jumlah, kolom X, baris Z, jarak min, jarak max,
#                skala min, skala max, pusat, jitter, rot_z dasar)
# rot_z = -pi/2 karena mesh kakatua & damselfish memanjang di +X (hadap +X),
# sedangkan cakalang sudah menghadap -Y sejak dibuat (fish-cakalang.blend).
SCHOOLS = [
    dict(name="cakalang", count=12, cols=4, rows=3, gap=(0.85, 1.35),
         scale=(1.00, 1.30), center=(0.60, 1.40, -2.75), jitter=0.24, depth=1.00,
         rot_z=0.0, src="fish-cakalang"),
    dict(name="kakatua", count=20, cols=5, rows=4, gap=(0.35, 0.60),
         scale=(0.90, 1.10), center=(-3.00, -0.60, -3.00), jitter=0.09, depth=0.60,
         rot_z=-math.pi / 2, src="reef"),
    dict(name="damselfish", count=24, cols=6, rows=4, gap=(0.25, 0.45),
         scale=(0.80, 1.00), center=(3.00, -0.20, -3.05), jitter=0.06, depth=0.65,
         rot_z=-math.pi / 2, src="reef"),
]


# --------------------------------------------------------------------- utils
def srgb(hex_color):
    h = hex_color.lstrip("#")
    out = []
    for i in range(3):
        c = int(h[i * 2:i * 2 + 2], 16) / 255.0
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return (out[0], out[1], out[2], 1.0)


def set_input(node, name, value):
    if name in node.inputs:
        node.inputs[name].default_value = value


def make_mat(name, hex_color, rough=0.85):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    col = srgb(hex_color)
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    set_input(bsdf, "Base Color", col)
    set_input(bsdf, "Roughness", rough)
    mat.diffuse_color = col
    return mat


def make_mottle(name, hex_a, hex_b, scale, rough=0.9, detail=4.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nodes, links = nt.nodes, nt.links
    bsdf = next(n for n in nodes if n.type == "BSDF_PRINCIPLED")
    set_input(bsdf, "Roughness", rough)
    coord = nodes.new("ShaderNodeTexCoord")
    noise = nodes.new("ShaderNodeTexNoise")
    set_input(noise, "Scale", scale)
    set_input(noise, "Detail", detail)
    set_input(noise, "Roughness", 0.6)
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.28
    ramp.color_ramp.elements[0].color = srgb(hex_a)
    ramp.color_ramp.elements[1].position = 0.72
    ramp.color_ramp.elements[1].color = srgb(hex_b)
    links.new(coord.outputs["Object"], noise.inputs["Vector"])
    links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    mat.diffuse_color = srgb(hex_a)
    return mat


def wipe():
    """Wipe manual bpy.data — bukan open_mainfile/read_factory_settings."""
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for coll in list(bpy.data.collections):
        bpy.data.collections.remove(coll)
    for block in (bpy.data.meshes, bpy.data.materials, bpy.data.cameras,
                  bpy.data.lights, bpy.data.worlds, bpy.data.textures,
                  bpy.data.node_groups, bpy.data.images, bpy.data.actions,
                  bpy.data.armatures, bpy.data.curves):
        for item in list(block):
            try:
                block.remove(item)
            except Exception:
                pass
    for sc in list(bpy.data.scenes):
        if sc is not bpy.context.scene:
            bpy.data.scenes.remove(sc)


def append_objects(blend_path, names):
    with bpy.data.libraries.load(blend_path, link=False) as (src, dst):
        dst.objects = [n for n in names if n in src.objects]
        missing = [n for n in names if n not in src.objects]
    if missing:
        print("WARN objek tidak ada di", os.path.basename(blend_path), missing)
    return [o for o in dst.objects if o is not None]


def append_materials(blend_path, names):
    with bpy.data.libraries.load(blend_path, link=False) as (src, dst):
        dst.materials = [n for n in names if n in src.materials]
        missing = [n for n in names if n not in src.materials]
    if missing:
        print("WARN material tidak ada di", os.path.basename(blend_path), missing)
    return {m.name: m for m in dst.materials if m is not None}


def own(ob, coll):
    for c in list(ob.users_collection):
        c.objects.unlink(ob)
    coll.objects.link(ob)
    return ob


def purge_libraries():
    for lib in list(bpy.data.libraries):
        used = (any(o.library == lib for o in bpy.data.objects)
                or any(m.library == lib for m in bpy.data.materials)
                or any(m.library == lib for m in bpy.data.meshes)
                or any(m.library == lib for m in bpy.data.node_groups))
        if used:
            print("PERINGATAN library masih dipakai:", lib.filepath)
            continue
        path = lib.filepath
        try:
            bpy.data.libraries.remove(lib)
            print("lepas library kosong:", os.path.basename(path))
        except Exception as exc:
            print("gagal lepas library", path, exc)


def eval_mesh(src_obj, name, coll, subsurf_cap=1, decimate=0.5):
    """Terapkan semua modifier objek sumber jadi mesh nyata (sekali)."""
    tmp = bpy.data.objects.new(name + "_tmp", src_obj.data)
    coll.objects.link(tmp)
    for mod in src_obj.modifiers:
        new = tmp.modifiers.new(mod.name, mod.type)
        for prop in ("subdivision_type", "levels", "render_levels", "ratio",
                     "strength", "mid_level", "texture", "direction"):
            if hasattr(mod, prop) and hasattr(new, prop):
                try:
                    setattr(new, prop, getattr(mod, prop))
                except Exception:
                    pass
        if mod.type == "SUBSURF":
            new.levels = min(new.levels, subsurf_cap)
            new.render_levels = min(new.render_levels, subsurf_cap)
    if decimate and decimate < 1.0:
        dec = tmp.modifiers.new("dense_dec", "DECIMATE")
        dec.ratio = decimate
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(tmp.evaluated_get(dg))
    me.name = name
    for p in me.polygons:
        p.use_smooth = True
    bpy.data.objects.remove(tmp, do_unlink=True)
    return me


def merge_meshes(name, items):
    """items: list of (mesh, matrix_world) — digabung dengan transformasi dunia."""
    mats = []
    for me, _mw in items:
        for m in me.materials:
            if m is not None and m not in mats:
                mats.append(m)
    bm = bmesh.new()
    for me, mw in items:
        before = len(bm.verts)
        bm.from_mesh(me)
        bm.verts.ensure_lookup_table()
        new_verts = [bm.verts[i] for i in range(before, len(bm.verts))]
        for v in new_verts:
            v.co = mw @ v.co
        remap = {i: mats.index(m) for i, m in enumerate(me.materials) if m in mats}
        for f in {f for v in new_verts for f in v.link_faces}:
            f.material_index = remap.get(f.material_index, 0)
    out = bpy.data.meshes.new(name)
    bm.to_mesh(out)
    bm.free()
    for m in mats:
        out.materials.append(m)
    return out


def bm_face(bm, pts, mat):
    vs = [bm.verts.new(p) for p in pts]
    f = bm.faces.new(vs)
    f.material_index = mat


def seabed_z(x, y):
    n = mnoise(Vector((x * 0.11, y * 0.11, 3.7)))
    return SEABED_Z + 0.22 * n


def mesh_bounds(me):
    xs = [v.co.x for v in me.vertices]
    ys = [v.co.y for v in me.vertices]
    zs = [v.co.z for v in me.vertices]
    return (round(max(xs) - min(xs), 2), round(max(ys) - min(ys), 2),
            round(max(zs) - min(zs), 2))


def coral_accent_faces(me, base_mat, accent_mat, max_frac=0.10, rim=False):
    """Warna dasar `base_mat`, aksen oranye hanya di ujung cabang / tepi meja."""
    me.materials.clear()
    me.materials.append(base_mat)
    for p in me.polygons:
        p.material_index = 0
    me.materials.append(accent_mat)
    total = sum(p.area for p in me.polygons)
    if total <= 0.0 or max_frac <= 0.0:
        return 0.0
    if rim:
        xs = [v.co.x for v in me.vertices]
        ys = [v.co.y for v in me.vertices]
        cx, cy = (min(xs) + max(xs)) * 0.5, (min(ys) + max(ys)) * 0.5

        def key(p):
            return (p.center.x - cx) ** 2 + (p.center.y - cy) ** 2

        # hanya sisi tegak (bibir meja) — bidang atas/bawah tidak ikut jadi oranye
        cand = [p for p in me.polygons if abs(p.normal.z) < 0.55]
    else:
        def key(p):
            return p.center.z
        cand = list(me.polygons)
    acc = 0.0
    for p in sorted(cand, key=key, reverse=True):
        if acc + p.area > total * max_frac:
            break
        p.material_index = 1
        acc += p.area
    return acc / total


def setup_scene():
    scene = bpy.context.scene
    scene.name = "reef-dense"
    os.makedirs(os.path.dirname(WIPE), exist_ok=True)
    os.makedirs(STILLS, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=WIPE)
    print("scratch file:", bpy.data.filepath)
    return scene


def get_root():
    root = bpy.data.collections.get(ROOT_COLL)
    ctl = bpy.data.objects.get(CTL)
    if root is None or ctl is None:
        raise RuntimeError("koleksi/empty kontrol tidak ada — jalankan tahap 1 dulu")
    return root, ctl


# ============================================================ TAHAP 1: karang
def stage_setup_and_corals():
    random.seed(SEED)
    wipe()
    scene = setup_scene()

    root = bpy.data.collections.new(ROOT_COLL)
    scene.collection.children.link(root)

    ctl = bpy.data.objects.new(CTL, None)
    ctl.empty_display_type = "PLAIN_AXES"
    ctl.empty_display_size = 2.0
    root.objects.link(ctl)

    # ---------------------------------------------------------- sumber mesh
    tmp_coll = bpy.data.collections.new("TMP_src")
    scene.collection.children.link(tmp_coll)
    src_objs = append_objects(REEF, CORAL_SRC + ["LGT_sun"])
    by_name = {o.name: o for o in src_objs}
    for n in CORAL_SRC:
        if n not in by_name:
            raise RuntimeError("karang tidak ada: " + n)
    for o in src_objs:
        own(o, tmp_coll)
    sun = by_name["LGT_sun"]
    own(sun, scene.collection)

    MESH_BRANCH = eval_mesh(by_name["ENV_reef_branching-coral"],
                            "ENV_dense_coral_branching", tmp_coll, decimate=0.28)
    MESH_BRANCH_B = eval_mesh(by_name["ENV_reef_branching-coral_b"],
                              "ENV_dense_coral_branching-b", tmp_coll, decimate=0.5)
    MESH_BOULDER = eval_mesh(by_name["ENV_reef_boulder-coral"],
                             "ENV_dense_coral_boulder", tmp_coll, decimate=0.30)
    table_me = eval_mesh(by_name["ENV_reef_table-coral"],
                         "ENV_dense_coral_table", tmp_coll, decimate=None)
    stem_obj = by_name["ENV_reef_table-coral_stem"]
    stem_me = stem_obj.data.copy()
    stem_me.name = "ENV_dense_coral_table-stem"
    MESH_TABLE = merge_meshes("ENV_dense_coral_table-merged",
                              [(table_me, by_name["ENV_reef_table-coral"].matrix_world),
                               (stem_me, stem_obj.matrix_world)])
    if stem_me.users == 0:
        bpy.data.meshes.remove(stem_me)
    if table_me.users == 0:
        bpy.data.meshes.remove(table_me)

    for ob in list(src_objs):
        if ob is sun:
            continue
        bpy.data.objects.remove(ob, do_unlink=True)
    if len(tmp_coll.objects) == 0:
        bpy.data.collections.remove(tmp_coll)

    print("verts karang: branch", len(MESH_BRANCH.vertices), mesh_bounds(MESH_BRANCH),
          "| branch_b", len(MESH_BRANCH_B.vertices), mesh_bounds(MESH_BRANCH_B),
          "| boulder", len(MESH_BOULDER.vertices), mesh_bounds(MESH_BOULDER),
          "| table", len(MESH_TABLE.vertices), mesh_bounds(MESH_TABLE))

    # ------------------------------------------------------------ material
    # Material hidup dari v002 di-append utuh supaya look tidak bergeser.
    mats = append_materials(V002, MAT_CORAL + MAT_OTHER)
    MAT_BRANCH_C = mats.get("MAT_reef_coral-branching") or make_mottle(
        "MAT_reef_coral-branching", "#3E8E6E", "#93C4A8", 4.5, rough=0.55)
    MAT_MASSIVE_C = mats.get("MAT_reef_coral-massive") or make_mottle(
        "MAT_reef_coral-massive", "#0F5C63", "#3E8E6E", 1.6, rough=0.72)
    MAT_TABLE_C = mats.get("MAT_reef_coral-table") or make_mottle(
        "MAT_reef_coral-table", "#8AAE8C", "#A9B98C", 6.0, rough=0.62)
    MAT_ACCENT = mats.get("MAT_reef_coral-accent") or make_mat(
        "MAT_reef_coral-accent", "#E4713C", rough=0.5)
    MAT_ACCENT.use_fake_user = True
    MAT_SAND = mats.get("MAT_dense_sand") or make_mottle(
        "MAT_dense_sand", "#E8D5B0", "#CBB58D", 0.35, rough=0.95)
    MAT_SG = mats.get("MAT_dense_seagrass") or make_mat(
        "MAT_dense_seagrass", "#3E8E6E", rough=0.9)
    MAT_SG_D = mats.get("MAT_dense_seagrass-dark") or make_mat(
        "MAT_dense_seagrass-dark", "#35775C", rough=0.9)

    coral_accent_faces(MESH_BRANCH, MAT_BRANCH_C, MAT_ACCENT, 0.045)
    coral_accent_faces(MESH_BRANCH_B, MAT_BRANCH_C, MAT_ACCENT, 0.045)
    coral_accent_faces(MESH_BOULDER, MAT_MASSIVE_C, MAT_ACCENT, 0.0)
    coral_accent_faces(MESH_TABLE, MAT_TABLE_C, MAT_ACCENT, 0.03, rim=True)
    for me in (MESH_BRANCH, MESH_BRANCH_B, MESH_BOULDER, MESH_TABLE):
        acc = sum(p.area for p in me.polygons
                  if p.material_index == 1 and len(me.materials) > 1)
        tot = sum(p.area for p in me.polygons)
        print("aksen", me.name, "%.1f%%" % (100.0 * acc / max(tot, 1e-9)),
              [m.name for m in me.materials])

    # --------------------------------------------------------------- pasir
    bm = bmesh.new()
    N = 14
    grid = {}
    for iy in range(N + 1):
        for ix in range(N + 1):
            x = -SEABED_HALF + 2 * SEABED_HALF * ix / N
            y = -SEABED_HALF + 2 * SEABED_HALF * iy / N
            grid[(ix, iy)] = bm.verts.new((x, y, seabed_z(x, y)))
    for iy in range(N):
        for ix in range(N):
            bm.faces.new((grid[(ix, iy)], grid[(ix + 1, iy)],
                          grid[(ix + 1, iy + 1)], grid[(ix, iy + 1)]))
    seabed_me = bpy.data.meshes.new("ENV_dense_seabed")
    bm.to_mesh(seabed_me)
    bm.free()
    seabed_me.materials.append(MAT_SAND)
    for p in seabed_me.polygons:
        p.use_smooth = True
    seabed = bpy.data.objects.new("ENV_dense_seabed", seabed_me)
    root.objects.link(seabed)
    seabed.parent = ctl

    # -------------------------------------------------------------- klaster
    rng = random.Random(SEED)
    clusters = []
    guard = 0
    while len(clusters) < CLUSTER_COUNT and guard < 8000:
        guard += 1
        cx = rng.uniform(-8.0, 8.0)
        cy = rng.uniform(-8.0, 8.0)
        if all(math.hypot(cx - ax, cy - ay) > 3.3 for ax, ay in clusters):
            clusters.append((cx, cy))
    print("klaster:", len(clusters),
          [(round(a, 1), round(b, 1)) for a, b in clusters])

    kinds = (["branch"] * N_BRANCH + ["boulder"] * N_BOULDER
             + ["table"] * N_TABLE)
    rng.shuffle(kinds)

    TYPE_INFO = {
        "branch": (MESH_BRANCH, "ENV_dense_coral_branching", 0.36, (1.15, 3.3)),
        "branch_b": (MESH_BRANCH_B, "ENV_dense_coral_branching-b", 0.25, (1.4, 4.4)),
        "boulder": (MESH_BOULDER, "ENV_dense_coral_boulder", 1.20, (0.42, 1.15)),
        "table": (MESH_TABLE, "ENV_dense_coral_table", 0.79, (0.65, 1.6)),
    }

    per_cluster = [CORAL_TOTAL // CLUSTER_COUNT] * CLUSTER_COUNT
    for i in range(CORAL_TOTAL - sum(per_cluster)):
        per_cluster[i] += 1
    print("per klaster:", per_cluster, "total", sum(per_cluster))

    coral_xz = []
    placed = 0
    heights = []
    for ci, (cx, cy) in enumerate(clusters):
        radius = rng.uniform(1.6, 2.8)
        for _k in range(per_cluster[ci]):
            kind = kinds[placed]
            if kind == "branch" and rng.random() < 0.34:
                kind = "branch_b"
            mesh, _mname, base_h, (smin, smax) = TYPE_INFO[kind]
            ang = rng.uniform(0.0, math.tau)
            rad = radius * math.sqrt(rng.random())
            x = cx + math.cos(ang) * rad
            y = cy + math.sin(ang) * rad
            x = max(-AREA_HALF, min(AREA_HALF, x))
            y = max(-AREA_HALF, min(AREA_HALF, y))
            scale = rng.uniform(smin, smax)
            h = base_h * scale
            if h < CORAL_H_MIN:
                scale *= CORAL_H_MIN / max(h, 1e-4)
            elif h > CORAL_H_MAX:
                scale *= CORAL_H_MAX / h
            h = base_h * scale
            ob = bpy.data.objects.new("ENV_dense_coral_%04d" % placed, mesh)
            root.objects.link(ob)
            ob.location = (x, y, seabed_z(x, y) - 0.04)
            ob.rotation_euler = (rng.uniform(-0.05, 0.05),
                                 rng.uniform(-0.05, 0.05),
                                 rng.uniform(0.0, math.tau))
            ob.scale = (scale, scale, scale)
            ob.parent = ctl
            coral_xz.append((x, y, scale))
            heights.append(h)
            placed += 1
    print("karang:", placed, "tinggi", round(min(heights), 2), "-",
          round(max(heights), 2), "m")
    print("komposisi: bercabang", N_BRANCH, "massif", N_BOULDER, "meja", N_TABLE)

    purge_libraries()
    bpy.ops.wm.save_as_mainfile(filepath=OUT)
    print("TAHAP 1 saved", OUT, round(os.path.getsize(OUT) / 1048576.0, 2), "MB",
          "| objek", len(bpy.data.objects),
          "| vert unik", sum(len(m.vertices) for m in bpy.data.meshes))


# ================================================= TAHAP 2: lamun + sekolah
def stage_seagrass_fish_finish():
    scene = bpy.context.scene
    root, ctl = get_root()
    rng = random.Random(SEED + 3)

    MAT_SG = bpy.data.materials.get("MAT_dense_seagrass")
    MAT_SG_D = bpy.data.materials.get("MAT_dense_seagrass-dark")
    if MAT_SG is None:
        MAT_SG = make_mat("MAT_dense_seagrass", "#3E8E6E", rough=0.9)
    if MAT_SG_D is None:
        MAT_SG_D = make_mat("MAT_dense_seagrass-dark", "#35775C", rough=0.9)

    coral_xz = []
    for ob in root.objects:
        if ob.name.startswith("ENV_dense_coral_") and ob.type == "MESH":
            coral_xz.append((ob.location.x, ob.location.y,
                             max(ob.scale) * 0.35))

    # --------------------------------------------------------------- lamun
    bm = bmesh.new()
    clumps = 0
    tries = 0
    while clumps < SEAGRASS_CLUMPS and tries < 40000:
        tries += 1
        x = rng.uniform(-AREA_HALF - 0.5, AREA_HALF + 0.5)
        y = rng.uniform(-AREA_HALF - 0.5, AREA_HALF + 0.5)
        # "di sela karang": jangan menancap di badan karang
        if any(math.hypot(x - cx, y - cy) < 0.30 + cr for cx, cy, cr in coral_xz):
            continue
        blades = rng.randint(10, 14)
        mi = 0 if rng.random() < 0.74 else 1
        base = seabed_z(x, y) - 0.02
        for _b in range(blades):
            bx = x + rng.uniform(-0.20, 0.20)
            by = y + rng.uniform(-0.20, 0.20)
            hgt = rng.uniform(SEAGRASS_H_MIN, SEAGRASS_H_MAX)
            wid = 0.042
            yaw = rng.uniform(0.0, math.tau)
            ux, uy = math.cos(yaw) * wid, math.sin(yaw) * wid
            lean_x = rng.uniform(-0.14, 0.14)
            lean_y = rng.uniform(-0.14, 0.14)
            p0a = (bx - ux, by - uy, base)
            p0b = (bx + ux, by + uy, base)
            p1a = (bx - ux * 0.8 + lean_x * 0.45, by - uy * 0.8 + lean_y * 0.45,
                   base + hgt * 0.55)
            p1b = (bx + ux * 0.8 + lean_x * 0.45, by + uy * 0.8 + lean_y * 0.45,
                   base + hgt * 0.55)
            p2a = (bx - ux * 0.35 + lean_x, by - uy * 0.35 + lean_y, base + hgt)
            p2b = (bx + ux * 0.35 + lean_x, by + uy * 0.35 + lean_y, base + hgt)
            bm_face(bm, [p0a, p0b, p1b, p1a], mi)
            bm_face(bm, [p1a, p1b, p2b, p2a], mi)
        clumps += 1

    sg_me = bpy.data.meshes.new("ENV_dense_seagrass")
    bm.to_mesh(sg_me)
    bm.free()
    sg_me.materials.append(MAT_SG)
    sg_me.materials.append(MAT_SG_D)
    seagrass = bpy.data.objects.new("ENV_dense_seagrass", sg_me)
    root.objects.link(seagrass)
    seagrass.parent = ctl
    print("lamun rumpun", clumps, "verts", len(sg_me.vertices),
          "tinggi", SEAGRASS_H_MIN, "-", SEAGRASS_H_MAX, "m", "percobaan", tries)

    # -------------------------------------------------------------- sekolah
    def fish_mesh(school):
        keep = []
        if school["src"] == "fish-cakalang":
            parts = append_objects(FISH, ["CTL_fish", "ENV_fish_cakalang",
                                          "ENV_fish_cakalang_tail",
                                          "ENV_fish_cakalang_pectoral",
                                          "ENV_fish_cakalang_dorsal"])
            ctl_fish = next((o for o in parts if o.name == "CTL_fish"), None)
            meshes = [o for o in parts if o.type == "MESH"]
            items = [(o.data, o.matrix_world.copy()) for o in meshes]
            me = merge_meshes("ENV_school_mesh_cakalang", items)
            keep = [ctl_fish] if ctl_fish is not None else []
        else:
            kind = "kakatua" if school["name"] == "kakatua" else "damselfish"
            names = ["ENV_reef_fish_" + kind,
                     "ENV_reef_fish_%s_dorsal" % kind,
                     "ENV_reef_fish_%s_tail" % kind]
            meshes = append_objects(REEF, names)
            if len(meshes) != 3:
                raise RuntimeError("mesh %s tidak lengkap: %s"
                                   % (kind, [o.name for o in meshes]))
            items = [(o.data, o.matrix_world.copy()) for o in meshes]
            me = merge_meshes("ENV_school_mesh_" + kind, items)
        for o in meshes:
            bpy.data.objects.remove(o, do_unlink=True)
        for o in keep:
            bpy.data.objects.remove(o, do_unlink=True)
        return me

    for sch in SCHOOLS:
        name = "ENV_school_" + sch["name"]
        coll = bpy.data.collections.new(name)
        root.children.link(coll)
        pivot = bpy.data.objects.new(name + "_pivot", None)
        pivot.empty_display_type = "ARROWS"
        pivot.empty_display_size = 0.6
        coll.objects.link(pivot)
        pivot.parent = ctl
        pivot.location = (0.0, 0.0, 0.0)

        me = fish_mesh(sch)
        me.name = "ENV_school_mesh_" + sch["name"]
        print("mesh", sch["name"], "verts", len(me.vertices),
              mesh_bounds(me), [m.name for m in me.materials])

        cols, rows = sch["cols"], sch["rows"]
        if cols * rows != sch["count"]:
            raise RuntimeError("formasi != jumlah: " + sch["name"])
        gx = rng.uniform(*sch["gap"])
        gz = rng.uniform(*sch["gap"])
        cx, cy, cz = sch["center"]
        jit = sch["jitter"]
        i = 0
        for r in range(rows):
            row_dx = 0.18 * gx if r % 2 else 0.0
            for c in range(cols):
                i += 1
                col_dz = 0.22 * gz if c % 2 else 0.0
                x = (cx + (c - (cols - 1) * 0.5) * gx + row_dx
                     + rng.uniform(-jit, jit) * 1.4)
                z = (cz + (r - (rows - 1) * 0.5) * gz + col_dz
                     + rng.uniform(-jit, jit) * 1.4)
                y = cy + rng.uniform(-sch["depth"], sch["depth"])
                s = rng.uniform(*sch["scale"])
                ob = bpy.data.objects.new("%s_%02d" % (name, i), me)
                coll.objects.link(ob)
                ob.location = (x, y, z)
                ob.rotation_euler = (
                    rng.uniform(-0.08, 0.08),
                    rng.uniform(-0.08, 0.08),
                    sch["rot_z"] + rng.uniform(-0.17, 0.17),
                )
                ob.scale = (s, s, s)
                ob.parent = pivot
                ob.matrix_parent_inverse.identity()
        print("sekolah", name, "ikan", len([o for o in coll.objects
                                            if o.type == "MESH"]),
              "jarak", round(gx, 2), "/", round(gz, 2),
              "skala", sch["scale"], "pusat", sch["center"])

    # ------------------------------------------------------------- world
    world = bpy.data.worlds.new("WLD_reef-dense")
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = srgb("#0F5C63")
    bg.inputs["Strength"].default_value = 0.85
    scene.world = world

    # ------------------------------------------------------------ kamera
    def add_camera(name, loc, target, lens):
        cam_data = bpy.data.cameras.new(name)
        cam_data.lens = lens
        cam_data.clip_start = 0.05
        cam_data.clip_end = 200.0
        cam = bpy.data.objects.new(name, cam_data)
        scene.collection.objects.link(cam)
        cam.location = loc
        cam.rotation_euler = ((Vector(target) - Vector(loc))
                             .to_track_quat("-Z", "Y").to_euler())
        return cam

    cam_a = add_camera("CAM_dense_01", (-7.8, -8.2, -2.2), (1.2, 0.4, -3.1), 24.0)
    cam_b = add_camera("CAM_dense_02", (6.5, -8.5, -2.1), (0.0, 0.8, -3.2), 24.0)
    scene.camera = cam_a

    sun = bpy.data.objects.get("LGT_sun")
    if sun is not None and sun.type == "LIGHT":
        sun.data.energy = 2.4
        sun.data.angle = math.radians(6.0)
        print("sun:", sun.name, round(sun.data.energy, 2))
    fill_data = bpy.data.lights.new("LGT_dense_fill", type="AREA")
    fill_data.energy = 120.0
    fill_data.size = 6.0
    fill = bpy.data.objects.new("LGT_dense_fill", fill_data)
    scene.collection.objects.link(fill)
    fill.location = (2.5, -6.0, 1.5)
    fill.rotation_euler = ((Vector((0.0, 0.0, -3.6)) - fill.location)
                           .to_track_quat("-Z", "Y").to_euler())

    # ------------------------------------------------------------ render
    scene.frame_set(1)
    scene.frame_start = 1
    scene.frame_end = 1
    scene.render.fps = 24
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.resolution_percentage = 100
    scene.view_settings.view_transform = "Standard"
    try:
        scene.view_settings.look = "None"
    except Exception:
        pass
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = "//"
    for engine in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scene.render.engine = engine
            break
        except TypeError:
            continue
    print("engine", scene.render.engine, "| fps", scene.render.fps,
          "| res", scene.render.resolution_x, scene.render.resolution_y,
          "| view", scene.view_settings.view_transform)

    purge_libraries()
    bpy.ops.wm.save_as_mainfile(filepath=OUT)

    print("TAHAP 2 saved", OUT, round(os.path.getsize(OUT) / 1048576.0, 2), "MB")
    print("objek total", len(bpy.data.objects))
    print("vert unik", sum(len(m.vertices) for m in bpy.data.meshes))
    for sch in SCHOOLS:
        coll = bpy.data.collections.get("ENV_school_" + sch["name"])
        print("  ", coll.name, "objek", len(coll.objects),
              "ikan", len([o for o in coll.objects if o.type == "MESH"]))
    print("material", len(bpy.data.materials),
          sorted(m.name for m in bpy.data.materials))
    print("images (harus 0)", [i.name for i in bpy.data.images])
    print("libraries (harus 0)", [l.filepath for l in bpy.data.libraries])
    print("packed files (harus 0)", [i.name for i in bpy.data.images
                                     if i.packed_file])


def render_previews():
    scene = bpy.context.scene
    cam_a = bpy.data.objects.get("CAM_dense_01")
    cam_b = bpy.data.objects.get("CAM_dense_02")
    if cam_a is None or cam_b is None:
        raise RuntimeError("kamera pratinjau tidak ada")
    scene.render.resolution_percentage = 50
    for idx, cam in ((1, cam_a), (2, cam_b)):
        scene.camera = cam
        scene.render.filepath = os.path.join(
            STILLS, "reef-dense-v003_preview-%02d.png" % idx)
        bpy.ops.render.render(write_still=True)
        print("render", scene.render.filepath)
    scene.render.resolution_percentage = 100


def stats():
    print("objek", len(bpy.data.objects),
          "vert unik", sum(len(m.vertices) for m in bpy.data.meshes))
    for coll in bpy.data.collections:
        print(" koleksi", coll.name, len(coll.objects))


def main():
    stage_setup_and_corals()
    stage_seagrass_fish_finish()
    render_previews()
    stats()


if __name__ == "__main__":
    main()

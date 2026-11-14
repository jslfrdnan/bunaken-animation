"""Build assets/env/reef-dense_v002.blend — titik selam padat untuk Scene 1.

v002 (14 Nov 2026) — perbaikan lead: karang terbaca pucat/putih pada render.
Warna lama diwarisi dari reef.blend (material placeholder hampir putih), jadi
v002 memakai material karang baru yang seluruhnya prosedural dan berasal dari
palette PROJECT.md §2 (tanpa tekstur gambar):

  MAT_reef_coral-branching  hijau terumbu #3E8E6E, ujung cabang lebih terang
                            (gradien Generated-Z + ColorRamp), roughness 0,55
  MAT_reef_coral-massive    teal dalam #0F5C63 dengan bercak hijau #3E8E6E
  MAT_reef_coral-table      hijau kekuningan (campuran #3E8E6E + pasir #E8D5B0)
  MAT_reef_coral-accent     oranye karang #E4713C, hanya di ujung cabang dan
                            tepi meja (mask ≤10% permukaan)

Isi koleksi `ENV_reef-dense` (empty kontrol `CTL_reef-dense` di origin):

  ENV_dense_seabed          dasar pasir 26 x 26 m (datum z = -5 m)
  ENV_dense_coral_####      72 karang dalam 7 klaster, 60/30/10 %
  ENV_dense_seagrass        240 rumpun lamun di dasar
  ENV_dense_cakalang_#      8 ikan cakalang, 1–4 m di atas dasar (material asli)

Mesh karang diambil dari assets/env/reef.blend (bercabang, massif, meja) dan
ikan dari assets/env/fish-cakalang.blend, di-append `link=False` lalu modifier
(skin/subsurf/displace) dievaluasi sekali — instance memakai mesh hasil itu.
Tidak ada file sumber yang diubah.

Jalankan dari Blender apa pun (MCP atau `blender -b --python`):

    blender -b --python scripts/build-reef-dense-v002.py
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
OUT = os.path.join(ENV_DIR, "reef-dense_v002.blend")
WIPE = os.path.join(ROOT, "renders", "tmp", "_wipe.blend")
STILLS = os.path.join(ROOT, "renders", "stills")

SEED = 20261114
random.seed(SEED)

SEABED_Z = -5.0
CORAL_TOTAL = 72
CLUSTER_COUNT = 7
FISH_COUNT = 8
SEAGRASS_CLUMPS = 240


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


def make_mat(name, hex_color, rough=0.85, metallic=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    col = srgb(hex_color)
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    set_input(bsdf, "Base Color", col)
    set_input(bsdf, "Roughness", rough)
    set_input(bsdf, "Metallic", metallic)
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
        print("WARN tidak ada di", os.path.basename(blend_path), missing)
    return [o for o in dst.objects if o is not None]


def own(ob, coll):
    for c in list(ob.users_collection):
        c.objects.unlink(ob)
    coll.objects.link(ob)
    return ob


def purge_libraries():
    for lib in list(bpy.data.libraries):
        used = (any(o.library == lib for o in bpy.data.objects)
                or any(m.library == lib for m in bpy.data.materials)
                or any(m.library == lib for m in bpy.data.meshes))
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
    """Terapkan seluruh modifier objek sumber jadi mesh nyata.

    Subsurf dibatasi `subsurf_cap` level dan hasilnya di-decimate sekali supaya
    instance tidak membengkak (target < 120.000 vert)."""
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


def merge_meshes(name, items, coll):
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


# --------------------------------------------------------------------- setup
wipe()
scene = bpy.context.scene
scene.name = "reef-dense"

os.makedirs(os.path.dirname(WIPE), exist_ok=True)
os.makedirs(STILLS, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=WIPE)
print("scratch file:", bpy.data.filepath)

root = bpy.data.collections.new("ENV_reef-dense")
scene.collection.children.link(root)

ctl = bpy.data.objects.new("CTL_reef-dense", None)
ctl.empty_display_type = "PLAIN_AXES"
ctl.empty_display_size = 2.0
root.objects.link(ctl)

# ------------------------------------------------------------ append sumber
coral_names = ["ENV_reef_branching-coral", "ENV_reef_branching-coral_b",
               "ENV_reef_boulder-coral", "ENV_reef_table-coral",
               "ENV_reef_table-coral_stem"]
coral_objs = append_objects(REEF, coral_names + ["LGT_sun"])
by_name = {o.name: o for o in coral_objs}
for n in coral_names:
    if n not in by_name:
        raise RuntimeError("karang tidak ada: " + n)
sun = own(by_name["LGT_sun"], scene.collection)

# mesh hasil evaluasi modifier (skin/subsurf/displace) untuk semua tipe
MESH_BRANCH = eval_mesh(by_name["ENV_reef_branching-coral"],
                        "ENV_dense_coral_branching", root, decimate=0.28)
MESH_BRANCH_B = eval_mesh(by_name["ENV_reef_branching-coral_b"],
                          "ENV_dense_coral_branching-b", root, decimate=0.5)
MESH_BOULDER = eval_mesh(by_name["ENV_reef_boulder-coral"],
                         "ENV_dense_coral_boulder", root, decimate=0.30)
table_me = eval_mesh(by_name["ENV_reef_table-coral"],
                     "ENV_dense_coral_table", root, decimate=None)
stem_obj = by_name["ENV_reef_table-coral_stem"]
stem_me = stem_obj.data.copy()
stem_me.name = "ENV_dense_coral_table-stem"
MESH_TABLE = merge_meshes("ENV_dense_coral_table-merged",
                          [(table_me, by_name["ENV_reef_table-coral"].matrix_world),
                           (stem_me, stem_obj.matrix_world)], root)
if stem_me.users == 0:
    bpy.data.meshes.remove(stem_me)
if table_me.users == 0:
    bpy.data.meshes.remove(table_me)

for ob in coral_objs:
    if ob is sun:
        continue
    bpy.data.objects.remove(ob, do_unlink=True)


def mesh_bounds(me):
    xs = [v.co.x for v in me.vertices]
    ys = [v.co.y for v in me.vertices]
    zs = [v.co.z for v in me.vertices]
    return (round(max(xs) - min(xs), 2), round(max(ys) - min(ys), 2),
            round(max(zs) - min(zs), 2))


print("mesh karang verts: branch", len(MESH_BRANCH.vertices),
      mesh_bounds(MESH_BRANCH),
      "branch_b", len(MESH_BRANCH_B.vertices), mesh_bounds(MESH_BRANCH_B))
print("boulder", len(MESH_BOULDER.vertices), mesh_bounds(MESH_BOULDER),
      "table", len(MESH_TABLE.vertices), mesh_bounds(MESH_TABLE))

# ---------------------------------------------------------------- materials
MAT_SAND = make_mottle("MAT_dense_sand", "#E8D5B0", "#CBB58D", 0.35, rough=0.95)
MAT_SG = make_mat("MAT_dense_seagrass", "#3E8E6E", rough=0.9)
MAT_SG_D = make_mat("MAT_dense_seagrass-dark", "#35775C", rough=0.9)

# --- material karang v002 ---------------------------------------------------
# v001 mewarisi material placeholder hampir putih dari reef.blend, sehingga
# karang terbaca pucat. Semua material di bawah prosedural (tanpa tekstur
# gambar) dan memakai palette PROJECT.md §2.
MAT_ACCENT = make_mat("MAT_reef_coral-accent", "#E4713C", rough=0.50)
MAT_ACCENT.use_fake_user = True          # disimpan walau dipakai per-face


def _srgb_ramp(ramp, stops):
    els = ramp.color_ramp.elements
    while len(els) > 1:
        els.remove(els[-1])
    els[0].position = stops[0][0]
    els[0].color = srgb(stops[0][1])
    for pos, hexc in stops[1:]:
        els.new(pos).color = srgb(hexc)


def _noisy_fac(nodes, links, coord, base_socket, noise_scale, noise_amp):
    """Fac = base + (noise - 0,5) * amp, tanpa node Mix warna."""
    noi = nodes.new("ShaderNodeTexNoise")
    set_input(noi, "Scale", noise_scale)
    set_input(noi, "Detail", 5.0)
    set_input(noi, "Roughness", 0.55)
    links.new(coord.outputs["Object"], noi.inputs["Vector"])
    sub = nodes.new("ShaderNodeMath")
    sub.operation = "SUBTRACT"
    sub.inputs[1].default_value = 0.5
    links.new(noi.outputs["Fac"], sub.inputs[0])
    mul = nodes.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    mul.inputs[1].default_value = noise_amp
    links.new(sub.outputs[0], mul.inputs[0])
    add = nodes.new("ShaderNodeMath")
    add.operation = "ADD"
    links.new(base_socket, add.inputs[0])
    links.new(mul.outputs[0], add.inputs[1])
    return add.outputs[0]


def coral_branching_mat():
    """Hijau terumbu #3E8E6E; dasar lebih gelap, ujung cabang lebih terang."""
    mat = bpy.data.materials.new("MAT_reef_coral-branching")
    mat.use_nodes = True
    nt = mat.node_tree
    nodes, links = nt.nodes, nt.links
    bsdf = next(n for n in nodes if n.type == "BSDF_PRINCIPLED")
    set_input(bsdf, "Roughness", 0.55)
    coord = nodes.new("ShaderNodeTexCoord")
    sep = nodes.new("ShaderNodeSeparateXYZ")
    links.new(coord.outputs["Generated"], sep.inputs["Vector"])
    fac = _noisy_fac(nodes, links, coord, sep.outputs["Z"], 4.5, 0.22)
    ramp = nodes.new("ShaderNodeValToRGB")
    _srgb_ramp(ramp, [(0.0, "#3E8E6E"), (0.55, "#4E9E7A"), (0.95, "#93C4A8")])
    links.new(fac, ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    mat.diffuse_color = srgb("#3E8E6E")
    return mat


def coral_table_mat():
    """Hijau kekuningan: campuran #3E8E6E + pasir #E8D5B0, lebih terang di tepi."""
    mat = bpy.data.materials.new("MAT_reef_coral-table")
    mat.use_nodes = True
    nt = mat.node_tree
    nodes, links = nt.nodes, nt.links
    bsdf = next(n for n in nodes if n.type == "BSDF_PRINCIPLED")
    set_input(bsdf, "Roughness", 0.62)
    coord = nodes.new("ShaderNodeTexCoord")
    sep = nodes.new("ShaderNodeSeparateXYZ")
    links.new(coord.outputs["Generated"], sep.inputs["Vector"])

    def _sub(axis, offset):
        n = nodes.new("ShaderNodeMath")
        n.operation = "SUBTRACT"
        n.inputs[1].default_value = offset
        links.new(sep.outputs[axis], n.inputs[0])
        return n.outputs[0]

    def _mul(a, b):
        n = nodes.new("ShaderNodeMath")
        n.operation = "MULTIPLY"
        links.new(a, n.inputs[0])
        if isinstance(b, float):
            n.inputs[1].default_value = b
        else:
            links.new(b, n.inputs[1])
        return n.outputs[0]

    dx, dy = _sub("X", 0.5), _sub("Y", 0.5)
    d2 = nodes.new("ShaderNodeMath")
    d2.operation = "ADD"
    links.new(_mul(dx, dx), d2.inputs[0])
    links.new(_mul(dy, dy), d2.inputs[1])
    rad = nodes.new("ShaderNodeMath")
    rad.operation = "SQRT"
    links.new(d2.outputs[0], rad.inputs[0])
    norm = _mul(rad.outputs[0], 1.41421356)
    fac = _noisy_fac(nodes, links, coord, norm, 6.0, 0.22)
    ramp = nodes.new("ShaderNodeValToRGB")
    _srgb_ramp(ramp, [(0.0, "#8AAE8C"), (0.55, "#8FBA92"), (1.0, "#A9B98C")])
    links.new(fac, ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    mat.diffuse_color = srgb("#8AAE8C")
    return mat


MAT_BRANCH_C = coral_branching_mat()
MAT_TABLE_C = coral_table_mat()
MAT_MASSIVE_C = make_mottle("MAT_reef_coral-massive", "#0F5C63", "#3E8E6E",
                            1.6, rough=0.72, detail=5.0)


def coral_accent_faces(me, base_mat, max_frac=0.10, rim=False):
    """Warna dasar dari `base_mat`, aksen oranye hanya di ujung/tepi.

    Aksen dipilih per-face: `rim=False` memakai wajah paling atas (ujung
    cabang), `rim=True` memakai wajah paling luar (tepi karang meja). Total
    luas aksen dibatasi `max_frac` dari luas permukaan."""
    me.materials.clear()
    me.materials.append(base_mat)
    for p in me.polygons:
        p.material_index = 0
    me.materials.append(MAT_ACCENT)
    total = sum(p.area for p in me.polygons)
    if total <= 0.0:
        return 0.0
    if rim:
        xs = [v.co.x for v in me.vertices]
        ys = [v.co.y for v in me.vertices]
        cx, cy = (min(xs) + max(xs)) * 0.5, (min(ys) + max(ys)) * 0.5

        def key(p):
            return (p.center.x - cx) ** 2 + (p.center.y - cy) ** 2
    else:
        def key(p):
            return p.center.z
    acc = 0.0
    for p in sorted(me.polygons, key=key, reverse=True):
        if acc + p.area > total * max_frac:
            break
        p.material_index = 1
        acc += p.area
    return acc / total


print("aksen bercabang %.1f%%" % (coral_accent_faces(
    MESH_BRANCH, MAT_BRANCH_C, 0.045) * 100.0),
    "| bercabang-b %.1f%%" % (coral_accent_faces(
        MESH_BRANCH_B, MAT_BRANCH_C, 0.045) * 100.0),
    "| meja %.1f%%" % (coral_accent_faces(
        MESH_TABLE, MAT_TABLE_C, 0.06, rim=True) * 100.0))
# karang massif tanpa aksen: oranye hanya di ujung cabang & tepi meja
coral_accent_faces(MESH_BOULDER, MAT_MASSIVE_C, 0.0)
for _me in (MESH_BRANCH, MESH_BRANCH_B, MESH_BOULDER, MESH_TABLE):
    print("material", _me.name, [m.name for m in _me.materials])

# ------------------------------------------------------------------ seabed
bm = bmesh.new()
N = 12
half = 13.0
grid = {}
for iy in range(N + 1):
    for ix in range(N + 1):
        x = -half + 2 * half * ix / N
        y = -half + 2 * half * iy / N
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

# ------------------------------------------------------------------ karang
clusters = []
guard = 0
while len(clusters) < CLUSTER_COUNT and guard < 4000:
    guard += 1
    cx = random.uniform(-8.4, 8.4)
    cy = random.uniform(-8.4, 8.4)
    if all(math.hypot(cx - ax, cy - ay) > 4.4 for ax, ay in clusters):
        clusters.append((cx, cy))
print("klaster:", [(round(a, 1), round(b, 1)) for a, b in clusters])

n_branch = int(round(CORAL_TOTAL * 0.60))
n_boulder = int(round(CORAL_TOTAL * 0.30))
n_table = CORAL_TOTAL - n_branch - n_boulder
kinds = (["branch"] * n_branch + ["boulder"] * n_boulder + ["table"] * n_table)
random.shuffle(kinds)
print("campuran:", kinds.count("branch"), kinds.count("boulder"), kinds.count("table"))

TYPE_INFO = {
    "branch": (MESH_BRANCH, 0.36, (1.15, 3.3)),
    "branch_b": (MESH_BRANCH_B, 0.25, (1.4, 4.4)),
    "boulder": (MESH_BOULDER, 1.20, (0.42, 1.15)),
    "table": (MESH_TABLE, 0.79, (0.65, 1.6)),
}

placed = 0
per_cluster = [CORAL_TOTAL // CLUSTER_COUNT] * CLUSTER_COUNT
for i in range(CORAL_TOTAL - sum(per_cluster)):
    per_cluster[i] += 1

for ci, (cx, cy) in enumerate(clusters):
    radius = random.uniform(1.7, 3.1)
    for _k in range(per_cluster[ci]):
        kind = kinds[placed]
        mesh, base_h, (smin, smax) = TYPE_INFO[kind]
        ang = random.uniform(0.0, math.tau)
        rad = radius * math.sqrt(random.random())
        x = cx + math.cos(ang) * rad
        y = cy + math.sin(ang) * rad
        if abs(x) > 10.0 or abs(y) > 10.0:
            x = max(-10.0, min(10.0, x))
            y = max(-10.0, min(10.0, y))
        scale = random.uniform(smin, smax)
        if kind in ("branch", "branch_b") and random.random() < 0.32:
            kind_b = "branch_b"
            mesh, base_h, (smin, smax) = TYPE_INFO[kind_b]
            scale = random.uniform(smin, smax)
        height = base_h * scale
        if height < 0.30:
            scale *= 0.32 / max(height, 1e-4)
        elif height > 1.60:
            scale *= 1.55 / height
        ob = bpy.data.objects.new(f"ENV_dense_coral_{placed:04d}", mesh)
        root.objects.link(ob)
        ob.location = (x, y, seabed_z(x, y) - 0.04)
        ob.rotation_euler = (random.uniform(-0.05, 0.05),
                             random.uniform(-0.05, 0.05),
                             random.uniform(0.0, math.tau))
        ob.scale = (scale, scale, scale)
        ob.parent = ctl
        placed += 1
print("karang:", placed)

# ------------------------------------------------------------------ lamun
bm = bmesh.new()
clumps = 0
tries = 0
while clumps < SEAGRASS_CLUMPS and tries < 6000:
    tries += 1
    x = random.uniform(-11.0, 11.0)
    y = random.uniform(-11.0, 11.0)
    blades = random.randint(9, 12)
    mi = 0 if random.random() < 0.74 else 1
    base = seabed_z(x, y) - 0.02
    for _b in range(blades):
        bx = x + random.uniform(-0.19, 0.19)
        by = y + random.uniform(-0.19, 0.19)
        hgt = random.uniform(0.16, 0.36)
        wid = 0.032
        yaw = random.uniform(0.0, math.tau)
        ux, uy = math.cos(yaw) * wid, math.sin(yaw) * wid
        lean_x = random.uniform(-0.12, 0.12)
        lean_y = random.uniform(-0.12, 0.12)
        # strip 3 baris: pangkal, tengah, ujung (melengkung)
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
print("lamun rumpun", clumps, "verts", len(sg_me.vertices))

# -------------------------------------------------------------- ikan cakalang
fish_names = ["ENV_fish_cakalang", "ENV_fish_cakalang_tail",
              "ENV_fish_cakalang_pectoral", "ENV_fish_cakalang_dorsal"]
fish_parts = append_objects(FISH, fish_names)
if len(fish_parts) != 4:
    raise RuntimeError("mesh cakalang tidak lengkap: %s" % [o.name for o in fish_parts])
fish_me = merge_meshes("ENV_dense_cakalang-mesh",
                       [(o.data, o.matrix_world) for o in fish_parts], root)
for o in fish_parts:
    bpy.data.objects.remove(o, do_unlink=True)
print("cakalang mesh verts", len(fish_me.vertices))

fish_xy = []
for i in range(FISH_COUNT):
    ob = bpy.data.objects.new(f"ENV_dense_cakalang_{i + 1:02d}", fish_me)
    root.objects.link(ob)
    for _try in range(200):
        x = random.uniform(-8.0, 8.0)
        y = random.uniform(-8.0, 8.0)
        if math.hypot(x, y) < 2.4:
            continue
        if math.hypot(x - 0.8, y + 8.6) < 3.2:
            continue
        if math.hypot(x + 6.4, y + 5.8) < 3.2:
            continue
        if any(math.hypot(x - fx, y - fy) < 1.6 for fx, fy in fish_xy):
            continue
        break
    fish_xy.append((x, y))
    z = random.uniform(-4.0, -1.0)
    s = random.uniform(1.0, 1.3)
    ob.location = (x, y, z)
    ob.rotation_euler = (random.uniform(-0.08, 0.08),
                         random.uniform(-0.12, 0.12),
                         random.uniform(0.0, math.tau))
    ob.scale = (s, s, s)
    ob.parent = ctl
    print("cakalang", ob.name, "z", round(z, 2), "skala", round(s, 2))

# ------------------------------------------------------------------- world
world = bpy.data.worlds.new("WLD_reef-dense")
world.use_nodes = True
bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
bg.inputs["Color"].default_value = srgb("#0F5C63")
bg.inputs["Strength"].default_value = 0.85
scene.world = world

# ----------------------------------------------------------------- kamera
def add_camera(name, loc, target, lens):
    cam_data = bpy.data.cameras.new(name)
    cam_data.lens = lens
    cam_data.clip_start = 0.05
    cam_data.clip_end = 200.0
    cam = bpy.data.objects.new(name, cam_data)
    scene.collection.objects.link(cam)
    cam.location = loc
    cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return cam


cam_a = add_camera("CAM_dense_01", (0.8, -8.6, -2.7), (0.0, 0.8, -4.35), 24.0)
cam_b = add_camera("CAM_dense_02", (-6.4, -5.8, -3.2), (0.6, 1.2, -4.2), 32.0)
scene.camera = cam_a
print("sun:", sun.name, sun.data.type, round(sun.data.energy, 2),
      tuple(round(v, 2) for v in sun.rotation_euler))
# cahaya pratinjau: v001 menurunkan matahari ke 1,9 karena karang putih
# placeholder hampir clipping. Karang v002 sudah berwarna palette, jadi cahaya
# dinaikkan ke 2,4 supaya warna terbaca (pasir masih jauh dari clipping).
sun.data.energy = 2.4
sun.data.angle = math.radians(6.0)

# ------------------------------------------------------------- render setup
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
print("engine sebelum:", scene.render.engine)
for engine in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
    try:
        scene.render.engine = engine
        break
    except TypeError:
        continue
print("engine sesudah:", scene.render.engine)

# --------------------------------------------------------------------- simpan
purge_libraries()
bpy.ops.wm.save_as_mainfile(filepath=OUT)
print("SAVED", OUT, round(os.path.getsize(OUT) / 1048576.0, 2), "MB")
print("objects", len(bpy.data.objects), "meshes", len(bpy.data.meshes),
      "unique mesh verts", sum(len(m.vertices) for m in bpy.data.meshes))
print("materials", len(bpy.data.materials))
print("images (harus 0)", [i.name for i in bpy.data.images])
print("libraries", [l.name for l in bpy.data.libraries])

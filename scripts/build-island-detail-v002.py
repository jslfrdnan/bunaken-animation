"""Build assets/env/island-detail_v002.blend — detail layer Scene 1 aerial.

v002 (14 Nov 2026) — perbaikan lead: pada shot aerial 120–150 m pohon kelapa
terbaca sebagai garis tipis. Perubahan dari v001:

  + 150 kelapa pesisir (`ENV_detail_palm-coast_###`) dalam klaster rapat
    9–16 pohon, berjarak 10–25 m dari garis pantai (diukur dengan menuruni
    gradien ketinggian sampai permukaan air, bukan tebakan), skala 1,25–1,75.
  + tajuk kelapa pesisir diperbesar 1,2x (verteks material frond diskalakan
    pada sumbu batang) supaya siluet tajuk terbaca pada 120 m.
  + frond kelapa pesisir memakai hijau palette `#3E8E6E` + tint muda `#4E9E7A`
    (material asli vegetation.blend tetap #3A7A56, tidak diubah).
  + kamera pratinjau aerial 24 mm pada ketinggian 120 m.

Tetap: 3.000 rumpun rumput, 12 rumah detail, Manado Tua, bidang air 4 km.

Isi koleksi `ENV_island-detail` (empty kontrol `CTL_island-detail` di origin):

  ENV_detail_island              salinan verbatim ENV_surface_island (dasar)
  ENV_detail_grass               3.000 rumpun rumput di pantai–lereng
  ENV_detail_palm-extra_###      200 pohon kelapa sebaran campuran
  ENV_detail_palm-coast_###      150 pohon kelapa pesisir (klaster, skala besar)
  ENV_detail_manado-tua          Manado Tua + ridge/lembah, puncak tetap 745 m
  ENV_detail_manado-tua_veg      tutupan vegetasi lereng Manado Tua
  ENV_detail_houses_01..12       12 rumah kampung detail
  ENV_detail_sea-surface         bidang air 4 km, shader noise (tanpa tekstur)

Sub-koleksi `ENV_island-detail_context` memuat konteks yang di-append apa adanya
dari surface.blend: dermaga (deck/posts/railing), dive shop, annex atap putih.
Semua aset sumber di-append `link=False` dan tidak diubah di file asalnya.

Jalankan dari Blender apa pun (MCP atau `blender -b --python`), tanpa
membuka file lain: skrip menghapus bpy.data manual, lalu menyimpan ke
renders/tmp/_wipe.blend sebelum meng-append.

    blender -b --python scripts/build-island-detail-v002.py
"""
import bpy
import bmesh
import math
import os
import random

from mathutils import Vector

try:  # mathutils.noise ada di semua build resmi; fallback analitik kalau tidak
    from mathutils.noise import noise as mnoise
except Exception:  # pragma: no cover
    def mnoise(v):
        return math.sin(v.x * 1.7) * math.cos(v.y * 1.3) * 0.5

try:
    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
except NameError:  # dijalankan lewat exec() MCP: __file__ tidak ada
    ROOT = r"D:\Tugas Semester 5\Grafika Komputer\Project-Animasi"

ENV_DIR = os.path.join(ROOT, "assets", "env")
SURFACE = os.path.join(ENV_DIR, "surface.blend")
VEGETATION = os.path.join(ENV_DIR, "vegetation.blend")
OUT = os.path.join(ENV_DIR, "island-detail_v002.blend")
WIPE = os.path.join(ROOT, "renders", "tmp", "_wipe.blend")
STILLS = os.path.join(ROOT, "renders", "stills")

SEED = 20261114
random.seed(SEED)

GRASS_TUFTS = 3000
PALM_COUNT = 200            # sebaran campuran (sama seperti v001)
PALM_COASTAL = 150          # klaster pesisir baru: total kelapa 350
COASTAL_MIN_D = 10.0        # jarak minimum dari garis pantai (m)
COASTAL_MAX_D = 25.0        # jarak maksimum dari garis pantai (m)
FROND_BOOST = 1.2           # tajuk kelapa pesisir diperbesar 1,2x
MANADO_VEG = 1400
HOUSE_SPOTS = [
    (-31.0, 19.5), (-22.5, 19.5), (-14.0, 19.5), (-5.5, 19.5),
    (38.0, 19.5), (46.0, 19.5),
    (-29.0, 32.5), (-20.0, 32.5), (-11.0, 32.5), (-2.0, 32.5),
    (13.0, 32.5), (26.0, 32.5),
]


# --------------------------------------------------------------------- utils
def srgb(hex_color):
    """#RRGGBB sRGB -> linear RGBA (palette PROJECT.md §2)."""
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
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    col = srgb(hex_color)
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    set_input(bsdf, "Base Color", col)
    set_input(bsdf, "Roughness", rough)
    set_input(bsdf, "Metallic", metallic)
    mat.diffuse_color = col
    return mat


def make_mottle(name, hex_a, hex_b, scale, rough=0.92, detail=4.0):
    """Material palette dengan bercak dua oktaf (tanpa tekstur gambar)."""
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
    set_input(noise, "Roughness", 0.62)
    fine = nodes.new("ShaderNodeTexNoise")
    set_input(fine, "Scale", scale * 9.0)
    set_input(fine, "Detail", 6.0)
    set_input(fine, "Roughness", 0.7)
    add = nodes.new("ShaderNodeMath")
    add.operation = "ADD"
    half = nodes.new("ShaderNodeMath")
    half.operation = "MULTIPLY"
    half.inputs[1].default_value = 0.5
    links.new(coord.outputs["Object"], noise.inputs["Vector"])
    links.new(coord.outputs["Object"], fine.inputs["Vector"])
    links.new(noise.outputs["Fac"], add.inputs[0])
    links.new(fine.outputs["Fac"], add.inputs[1])
    links.new(add.outputs[0], half.inputs[0])
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.18
    ramp.color_ramp.elements[0].color = srgb(hex_b)
    ramp.color_ramp.elements[1].position = 0.82
    ramp.color_ramp.elements[1].color = srgb(hex_a)
    mid = ramp.color_ramp.elements.new(0.5)
    mid.color = srgb(hex_a)
    links.new(half.outputs[0], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    mat.diffuse_color = srgb(hex_a)
    return mat


def wipe():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for coll in list(bpy.data.collections):
        bpy.data.collections.remove(coll)
    for lib in list(bpy.data.libraries):
        try:
            bpy.data.libraries.remove(lib)
        except Exception:
            pass
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
    """Lepas entri library kosong supaya file tidak menyimpan dependensi luar."""
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


def merge_objects(name, objs, coll=None):
    """Gabung objek (world transform) jadi satu mesh + material unik."""
    mats = []
    for o in objs:
        for m in o.data.materials:
            if m is not None and m not in mats:
                mats.append(m)
    bm = bmesh.new()
    for o in objs:
        me = o.data
        before = len(bm.verts)
        bm.from_mesh(me)
        bm.verts.ensure_lookup_table()
        mw = o.matrix_world
        new_verts = [bm.verts[i] for i in range(before, len(bm.verts))]
        for v in new_verts:
            v.co = mw @ v.co
        remap = {i: mats.index(m) for i, m in enumerate(me.materials) if m in mats}
        for f in {f for v in new_verts for f in v.link_faces}:
            f.material_index = remap.get(f.material_index, 0)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    ob = bpy.data.objects.new(name, me)
    if coll is not None:
        coll.objects.link(ob)
    return ob


def mesh_with_modifier(src_mesh, name, setup, coll):
    """Evaluasi src_mesh lewat modifier `setup(obj)` -> mesh baru."""
    tmp = bpy.data.objects.new(name + "_tmp", src_mesh)
    coll.objects.link(tmp)
    mods = setup(tmp)
    dg = bpy.context.evaluated_depsgraph_get()
    new_me = bpy.data.meshes.new_from_object(tmp.evaluated_get(dg))
    new_me.name = name
    for mod in mods:
        tmp.modifiers.remove(mod)
    bpy.data.objects.remove(tmp, do_unlink=True)
    return new_me


def bm_box(bm, center, size, mat):
    ret = bmesh.ops.create_cube(bm, size=1.0)
    verts = ret["verts"]
    cx, cy, cz = center
    sx, sy, sz = size
    for v in verts:
        v.co = Vector((cx + v.co.x * sx, cy + v.co.y * sy, cz + v.co.z * sz))
    for f in {f for v in verts for f in v.link_faces}:
        f.material_index = mat


def bm_face(bm, pts, mat):
    vs = [bm.verts.new(p) for p in pts]
    f = bm.faces.new(vs)
    f.material_index = mat
    return f


# --------------------------------------------------------------------- setup
wipe()
scene = bpy.context.scene
scene.name = "island-detail"

os.makedirs(os.path.dirname(WIPE), exist_ok=True)
os.makedirs(STILLS, exist_ok=True)
# lepaskan file aktif (kalau ada) sebelum libraries.load
bpy.ops.wm.save_as_mainfile(filepath=WIPE)
print("scratch file:", bpy.data.filepath)

root = bpy.data.collections.new("ENV_island-detail")
scene.collection.children.link(root)
ctx = bpy.data.collections.new("ENV_island-detail_context")
root.children.link(ctx)

ctl = bpy.data.objects.new("CTL_island-detail", None)
ctl.empty_display_type = "PLAIN_AXES"
ctl.empty_display_size = 40.0
root.objects.link(ctl)

# ------------------------------------------------------------------ materials
MAT_GRASS = make_mat("MAT_detail_grass", "#3E8E6E", rough=0.92)
MAT_GRASS_D = make_mat("MAT_detail_grass-dark", "#2D664F", rough=0.94)
MAT_COVER = make_mat("MAT_detail_veg-cover", "#3E8E6E", rough=0.95)
MAT_COVER_D = make_mat("MAT_detail_veg-cover-dark", "#2D664F", rough=0.95)
MAT_WALL = make_mat("MAT_detail_wall", "#F2E9DC", rough=0.88)
MAT_WOOD = make_mat("MAT_detail_wood", "#E8D5B0", rough=0.82)
MAT_GLASS = make_mat("MAT_detail_window", "#0F5C63", rough=0.18)
MAT_ROOF = make_mat("MAT_detail_roof", "#E4713C", rough=0.62)
# frond kelapa pesisir: hijau palette #3E8E6E + tint muda, supaya tajuk terbaca
MAT_PALM_FROND = make_mat("MAT_detail_palm-frond-aerial", "#3E8E6E", rough=0.60)
MAT_PALM_FROND_Y = make_mat("MAT_detail_palm-frond-aerial-light", "#4E9E7A",
                            rough=0.58)

# tutupan vegetasi pulau/gunung: bercak hijau palette, bukan satu bidang rata
MAT_ISLAND_VEG = make_mottle("MAT_detail_island-vegetation", "#3E8E6E",
                             "#316F58", 0.055)
MAT_MANADO_VEG = make_mottle("MAT_detail_manado-vegetation", "#3E8E6E",
                             "#2C6149", 0.012)

# atap seng: bump gelombang prosedural, tanpa tekstur gambar
_nt = MAT_ROOF.node_tree
_bsdf = next(n for n in _nt.nodes if n.type == "BSDF_PRINCIPLED")
_wave = _nt.nodes.new("ShaderNodeTexWave")
_wave.wave_type = "BANDS"
_wave.bands_direction = "Y"
_wave.inputs["Scale"].default_value = 26.0
_wave.inputs["Distortion"].default_value = 0.0
_bump = _nt.nodes.new("ShaderNodeBump")
_bump.inputs["Strength"].default_value = 0.22
_bump.inputs["Distance"].default_value = 0.05
_coord = _nt.nodes.new("ShaderNodeTexCoord")
_nt.links.new(_coord.outputs["Object"], _wave.inputs["Vector"])
_nt.links.new(_wave.outputs["Fac"], _bump.inputs["Height"])
_nt.links.new(_bump.outputs["Normal"], _bsdf.inputs["Normal"])

# ------------------------------------------------------------ append sumber
surf_names = [
    "ENV_surface_island", "ENV_surface_manado-tua",
    "ENV_surface_pier-deck", "ENV_surface_pier-posts",
    "ENV_surface_pier-railing", "ENV_surface_dive-shop",
    "ENV_surface_white-roof-annex", "LGT_sun",
]
surf_objs = append_objects(SURFACE, surf_names)
by_name = {o.name: o for o in surf_objs}
for key in ("ENV_surface_island", "ENV_surface_manado-tua", "LGT_sun"):
    if key not in by_name:
        raise RuntimeError("objek wajib tidak ada: " + key)

island = own(by_name["ENV_surface_island"], root)
island.name = "ENV_detail_island"
island.data.name = "ENV_detail_island"
# slot 0 = vegetasi pulau: varian bercak (aset sumber tidak diubah)
if island.data.materials and island.data.materials[0] is not None:
    island.data.materials[0] = MAT_ISLAND_VEG
manado_base = by_name["ENV_surface_manado-tua"]
sun = own(by_name["LGT_sun"], scene.collection)
for n in ("ENV_surface_pier-deck", "ENV_surface_pier-posts",
          "ENV_surface_pier-railing", "ENV_surface_dive-shop",
          "ENV_surface_white-roof-annex"):
    if n in by_name:
        own(by_name[n], ctx)

MANADO_LOC = manado_base.location.copy()
print("island verts", len(island.data.vertices),
      "manado verts", len(manado_base.data.vertices),
      "manado loc", tuple(round(v, 1) for v in MANADO_LOC))


# ------------------------------------------------------------------- terrain
def ray_obj(obj, x, y, ztop=2000.0, dist=6000.0):
    lx, ly = x - obj.location.x, y - obj.location.y
    hit, loc, nrm, idx = obj.ray_cast(Vector((lx, ly, ztop)),
                                      Vector((0.0, 0.0, -1.0)), distance=dist)
    if not hit:
        return None
    poly = obj.data.polygons[idx]
    return (Vector((loc.x + obj.location.x, loc.y + obj.location.y,
                    loc.z + obj.location.z)), nrm, poly.material_index)


# cache ketinggian: uji jarak ke pantai butuh banyak probe di titik yang sama
_HCACHE = {}


def ground_at(x, y):
    key = (round(x, 1), round(y, 1))
    if key in _HCACHE:
        return _HCACHE[key]
    val = ray_obj(island, x, y, ztop=800.0, dist=2000.0)
    _HCACHE[key] = val
    return val


def dist_to_water(x, y, step=2.0, max_steps=16):
    """Tidak dipakai lagi di v002.

    Mesh pulau tidak punya geometri bawah air (ray cast berhenti di tepi pantai
    z ~0,25 m) dan lereng pantai hampir datar, sehingga menuruni gradien tidak
    pernah mencapai air. Jarak ke pantai dihitung dengan medan jarak chamfer
    `coast_dist()` di blok kelapa pesisir.
    """
    return None


BLOCKED = [
    (-10.0, -118.0, 10.0, 6.0),   # dermaga + tiang
    (-4.0, -6.0, 26.0, 20.0),     # dive shop
    (20.0, -2.0, 36.0, 14.0),     # annex atap putih
]


def blocked(x, y, margin=0.0):
    for x0, y0, x1, y1 in BLOCKED:
        if x0 - margin <= x <= x1 + margin and y0 - margin <= y <= y1 + margin:
            return True
    return False


# ---------------------------------------------------- Manado Tua detail mesh
base_copy = manado_base.data.copy()
base_copy.name = "ENV_detail_manado-tua_src"


def _subdiv(ob):
    mod = ob.modifiers.new("subd", "SUBSURF")
    mod.subdivision_type = "SIMPLE"
    mod.levels = 1
    mod.render_levels = 1
    return [mod]


sub_me = mesh_with_modifier(base_copy, "ENV_detail_manado-tua", _subdiv, root)

vmax = max(sub_me.vertices, key=lambda v: v.co.z)
peak = Vector((vmax.co.x, vmax.co.y, vmax.co.z))
R = max(math.hypot(v.co.x - peak.x, v.co.y - peak.y) for v in sub_me.vertices)
print("manado detail: verts", len(sub_me.vertices), "peak",
      round(peak.z, 2), "R", round(R, 1))

for v in sub_me.vertices:
    dx, dy = v.co.x - peak.x, v.co.y - peak.y
    r = math.hypot(dx, dy)
    ang = math.atan2(dy, dx)
    rn = min(1.0, r / R)
    h = v.co.z
    # ridge radial (14 punggung + 7 lembah sekunder) seperti peta acuan
    ridge = math.cos(ang * 14.0 + 0.6) * 0.62 + math.cos(ang * 7.0 - 1.1) * 0.38
    env = math.sin(math.pi * rn) ** 0.75
    peak_fade = min(1.0, max(0.0, (r - 70.0) / 180.0))
    coast_fade = min(1.0, max(0.0, (h - 6.0) / 40.0))
    disp = 36.0 * env * ridge * peak_fade * coast_fade
    disp += 9.0 * mnoise(Vector((v.co.x * 0.0045, v.co.y * 0.0045, v.co.z * 0.003)))
    # jaga puncak & garis pantai
    v.co.z += disp * peak_fade * coast_fade

for p in sub_me.polygons:
    p.use_smooth = True
sub_me.name = "ENV_detail_manado-tua_displaced"


def _manado_decimate(ob):
    mod = ob.modifiers.new("dec", "DECIMATE")
    mod.ratio = 0.55
    return [mod]


detail_me = mesh_with_modifier(sub_me, "ENV_detail_manado-tua",
                               _manado_decimate, root)
for p in detail_me.polygons:
    p.use_smooth = True
if detail_me.materials and detail_me.materials[0] is not None:
    detail_me.materials[0] = MAT_MANADO_VEG
print("manado detail decimated verts", len(detail_me.vertices))

manado = bpy.data.objects.new("ENV_detail_manado-tua", detail_me)
manado.location = MANADO_LOC
root.objects.link(manado)
manado.parent = ctl

peak_after = max(v.co.z for v in detail_me.vertices)
print("manado detail: puncak", round(peak_after, 2), "m (target 745)")

if sub_me.users == 0:
    bpy.data.meshes.remove(sub_me)

# buang sumber (base + salinan) supaya file tidak menyimpan dua gunung
base_mesh = manado_base.data
bpy.data.objects.remove(manado_base, do_unlink=True)
if base_mesh.users == 0:
    bpy.data.meshes.remove(base_mesh)
if base_copy.users == 0:
    bpy.data.meshes.remove(base_copy)

# ------------------------------------------- tutupan vegetasi lereng Manado
bm = bmesh.new()
placed = 0
tries = 0
mx0, mx1 = MANADO_LOC.x - 1790.0, MANADO_LOC.x + 1790.0
my0, my1 = MANADO_LOC.y - 1650.0, MANADO_LOC.y + 1660.0
while placed < MANADO_VEG and tries < 40000:
    tries += 1
    x = random.uniform(mx0, mx1)
    y = random.uniform(my0, my1)
    hit = ray_obj(manado, x, y, ztop=2000.0, dist=3000.0)
    if hit is None:
        continue
    p, nrm, _m = hit
    if p.z < 6.0 or p.z > 560.0 or nrm.z < 0.5:
        continue
    h = p.z
    if h > 430.0 and random.random() > 0.45:      # puncak makin jarang
        continue
    if h < 40.0 and random.random() > 0.85:       # garis pantai hampir kosong
        continue
    w = random.uniform(16.0, 30.0)
    hh = random.uniform(12.0, 24.0)
    yaw = random.uniform(0.0, math.tau)
    mi = 0 if random.random() < 0.70 else 1
    n = nrm.normalized()
    up = Vector((0.0, 0.0, 1.0))
    u = n.cross(up)
    if u.length < 1e-5:
        u = Vector((1.0, 0.0, 0.0))
    u.normalize()
    v = u.cross(n).normalized()
    cu, cv = math.cos(yaw), math.sin(yaw)
    ax, ay = u * (w * 0.5), v * (hh * 0.5)
    c0 = p + n * 0.6
    p0 = c0 - ax * cu - ay * cv
    p1 = c0 + ax * cu - ay * cv
    p2 = c0 + ax * cu + ay * cv
    p3 = c0 - ax * cu + ay * cv
    bm_face(bm, [tuple(p0), tuple(p1), tuple(p2), tuple(p3)], mi)
    placed += 1

veg_me = bpy.data.meshes.new("ENV_detail_manado-tua_veg")
bm.to_mesh(veg_me)
bm.free()
veg_me.materials.append(MAT_COVER)
veg_me.materials.append(MAT_COVER_D)
veg_ob = bpy.data.objects.new("ENV_detail_manado-tua_veg", veg_me)
root.objects.link(veg_ob)
veg_ob.parent = ctl
print("manado veg cards", placed, "verts", len(veg_me.vertices))

# --------------------------------------------------------------- rumah detail
def build_house(name, ox, oy, ground_z, yaw, idx):
    w = random.uniform(5.7, 6.9)
    d = random.uniform(4.4, 5.4)
    wall_h = random.uniform(2.55, 2.85)
    floor_z = 0.55 + random.uniform(-0.08, 0.12)
    roof_rise = random.uniform(1.35, 1.75)
    eave_y = d * 0.5 + 0.7
    eave_z = floor_z + wall_h + 0.05
    ridge_z = eave_z + roof_rise
    bmh = bmesh.new()
    m_wall, m_wood, m_roof, m_glass = 0, 1, 2, 3

    # pondasi / tiang
    for px in (-w * 0.5 + 0.35, 0.0, w * 0.5 - 0.35):
        for py in (-d * 0.5 + 0.35, 0.0, d * 0.5 - 0.35):
            bm_box(bmh, (px, py, (floor_z - 0.35) * 0.5),
                   (0.17, 0.17, floor_z + 0.45), m_wood)
    # lantai panggung
    bm_box(bmh, (0.0, 0.0, floor_z), (w, d, 0.12), m_wood)
    # dinding
    bm_box(bmh, (0.0, -d * 0.5 + 0.075, floor_z + wall_h * 0.5),
           (w, 0.15, wall_h), m_wall)
    bm_box(bmh, (0.0, d * 0.5 - 0.075, floor_z + wall_h * 0.5),
           (w, 0.15, wall_h), m_wall)
    bm_box(bmh, (-w * 0.5 + 0.075, 0.0, floor_z + wall_h * 0.5),
           (0.15, d - 0.3, wall_h), m_wall)
    bm_box(bmh, (w * 0.5 - 0.075, 0.0, floor_z + wall_h * 0.5),
           (0.15, d - 0.3, wall_h), m_wall)
    # pintu + kusen (menempel di muka luar dinding depan, -Y)
    dx = -w * 0.22
    yf = -d * 0.5
    yd = yf - 0.04
    bm_box(bmh, (dx, yd, floor_z + 1.05), (0.95, 0.07, 2.10), m_wood)
    bm_box(bmh, (dx - 0.55, yd - 0.03, floor_z + 1.10), (0.12, 0.12, 2.25), m_wood)
    bm_box(bmh, (dx + 0.55, yd - 0.03, floor_z + 1.10), (0.12, 0.12, 2.25), m_wood)
    bm_box(bmh, (dx, yd - 0.03, floor_z + 2.18), (1.24, 0.12, 0.14), m_wood)
    # jendela depan (2) + samping (2)
    for wx in (w * 0.26, w * 0.5 - 0.75):
        bm_box(bmh, (wx, yf - 0.03, floor_z + 1.62), (1.00, 0.06, 1.02), m_glass)
        bm_box(bmh, (wx, yf - 0.05, floor_z + 2.16), (1.14, 0.11, 0.12), m_wood)
        bm_box(bmh, (wx, yf - 0.05, floor_z + 1.08), (1.14, 0.11, 0.12), m_wood)
        bm_box(bmh, (wx - 0.53, yf - 0.05, floor_z + 1.62), (0.10, 0.11, 1.14), m_wood)
        bm_box(bmh, (wx + 0.53, yf - 0.05, floor_z + 1.62), (0.10, 0.11, 1.14), m_wood)
    sx = -w * 0.5
    bm_box(bmh, (sx - 0.03, 0.35, floor_z + 1.62), (0.06, 1.00, 1.00), m_glass)
    bm_box(bmh, (sx - 0.05, 0.35, floor_z + 2.16), (0.11, 1.14, 0.12), m_wood)
    bm_box(bmh, (sx - 0.05, 0.35, floor_z + 1.08), (0.11, 1.14, 0.12), m_wood)
    # teras
    vd = 1.55
    bm_box(bmh, (0.0, -d * 0.5 - vd * 0.5, floor_z - 0.06), (w * 0.94, vd, 0.10), m_wood)
    for px in (-w * 0.42, w * 0.42):
        bm_box(bmh, (px, -d * 0.5 - vd + 0.12, (floor_z + eave_z) * 0.5),
               (0.13, 0.13, eave_z - floor_z), m_wood)
    py = -d * 0.5 - vd + 0.12
    bm_box(bmh, (0.0, py, floor_z + 0.92), (w * 0.9, 0.07, 0.07), m_wood)
    for px in (-w * 0.4, -w * 0.05, w * 0.3):
        bm_box(bmh, (px, py, floor_z + 0.48), (0.07, 0.07, 0.88), m_wood)
    # atap seng dua bidang + ridge
    x0, x1 = -w * 0.5 - 0.35, w * 0.5 + 0.35
    bm_face(bmh, [(x0, -eave_y, eave_z), (x1, -eave_y, eave_z),
                  (x1, 0.0, ridge_z), (x0, 0.0, ridge_z)], m_roof)
    bm_face(bmh, [(x1, eave_y, eave_z), (x0, eave_y, eave_z),
                  (x0, 0.0, ridge_z), (x1, 0.0, ridge_z)], m_roof)
    bm_box(bmh, (0.0, 0.0, ridge_z + 0.04), (2 * x1, 0.26, 0.13), m_roof)
    # gable (segitiga dinding atas) di ujung atap, winding menghadap keluar
    gx = w * 0.5 + 0.33
    bm_face(bmh, [(-gx, -d * 0.5, eave_z - 0.05),
                  (-gx, 0.0, ridge_z),
                  (-gx, d * 0.5, eave_z - 0.05)], m_roof)
    bm_face(bmh, [(gx, -d * 0.5, eave_z - 0.05),
                  (gx, d * 0.5, eave_z - 0.05),
                  (gx, 0.0, ridge_z)], m_roof)
    # cerobong/asap kecil (opsional)
    if idx % 2 == 0:
        bm_box(bmh, (w * 0.28, 0.55, ridge_z + 0.15), (0.17, 0.17, 1.0), m_wall)
    # transform ke dunia
    cosr, sinr = math.cos(yaw), math.sin(yaw)
    for v in bmh.verts:
        lx, ly, lz = v.co
        v.co = Vector((ox + lx * cosr - ly * sinr,
                       oy + lx * sinr + ly * cosr,
                       ground_z + lz))
    me = bpy.data.meshes.new(name)
    bmh.to_mesh(me)
    bmh.free()
    for m in (MAT_WALL, MAT_WOOD, MAT_ROOF, MAT_GLASS):
        me.materials.append(m)
    ob = bpy.data.objects.new(name, me)
    root.objects.link(ob)
    ob.parent = ctl
    return ob


house_objs = []
house_pads = []
for i, (hx, hy) in enumerate(HOUSE_SPOTS, start=1):
    hit = ray_obj(island, hx, hy)
    if hit is None:                     # mundur ke dalam pulau kalau kena laut
        hit = ray_obj(island, hx, hy + 12.0)
    if hit is None:
        print("WARN rumah", i, "tidak dapat permukaan di", hx, hy)
        continue
    p = hit[0]
    yaw = random.uniform(-0.07, 0.07)
    hname = f"ENV_detail_houses_{i:02d}"
    house_objs.append(build_house(hname, hx, hy, p.z, yaw, i))
    house_pads.append((hx - 5.0, hy - 5.0, hx + 5.0, hy + 5.0))
    print(hname, "at", round(hx, 1), round(hy, 1), "z", round(p.z, 2))

# ------------------------------------------------------------------- rumput
bm = bmesh.new()
placed = 0
tries = 0
while placed < GRASS_TUFTS and tries < 90000:
    tries += 1
    if random.random() < 0.72:
        x = random.uniform(-330.0, 430.0)
        y = random.uniform(-230.0, 300.0)
    else:
        x = random.uniform(-1600.0, 3150.0)
        y = random.uniform(-2420.0, 1480.0)
    hit = ray_obj(island, x, y, ztop=800.0, dist=2000.0)
    if hit is None:
        continue
    p, nrm, mat_idx = hit
    if mat_idx != 0 or p.z < 0.28 or p.z > 75.0 or nrm.z < 0.5:
        continue
    if blocked(x, y, margin=1.5):
        continue
    if any(x0 <= x <= x1 and y0 <= y <= y1 for x0, y0, x1, y1 in house_pads):
        continue
    size = random.uniform(0.55, 1.2)
    hgt = size
    wid = size * 0.35
    yaw = random.uniform(0.0, math.tau)
    mi = 0 if random.random() < 0.66 else 1
    for k in range(3):
        a = yaw + k * (math.pi / 3.0)
        dx, dy = math.cos(a) * wid, math.sin(a) * wid
        bm_face(bm, [(x - dx, y - dy, p.z - 0.04),
                     (x + dx, y + dy, p.z - 0.04),
                     (x + dx * 0.3, y + dy * 0.3, p.z + hgt),
                     (x - dx * 0.3, y - dy * 0.3, p.z + hgt)], mi)
    placed += 1

grass_me = bpy.data.meshes.new("ENV_detail_grass")
bm.to_mesh(grass_me)
bm.free()
grass_me.materials.append(MAT_GRASS)
grass_me.materials.append(MAT_GRASS_D)
grass_ob = bpy.data.objects.new("ENV_detail_grass", grass_me)
root.objects.link(grass_ob)
grass_ob.parent = ctl
print("grass tufts", placed, "verts", len(grass_me.vertices), "tries", tries)

# ------------------------------------------------------- pohon kelapa ekstra
palm_parts = append_objects(VEGETATION, ["ENV_veg_palm-trunk",
                                         "ENV_veg_palm-fronds",
                                         "ENV_veg_palm-coconuts"])
if len(palm_parts) != 3:
    raise RuntimeError("mesh kelapa tidak lengkap: %s" % [o.name for o in palm_parts])
palm_template = merge_objects("ENV_veg_palm-merged", palm_parts, None)
for o in palm_parts:
    bpy.data.objects.remove(o, do_unlink=True)

def _palm_lod(ob):
    mod = ob.modifiers.new("lod", "DECIMATE")
    mod.ratio = 0.30
    return [mod]


palm_lod = mesh_with_modifier(palm_template.data, "ENV_veg_palm-merged-lod",
                              _palm_lod, root)
print("palm verts", len(palm_template.data.vertices),
      "lod verts", len(palm_lod.vertices))

placed = 0
tries = 0
spacing = []
while placed < PALM_COUNT and tries < 40000:
    tries += 1
    if random.random() < 0.60:
        x = random.uniform(-420.0, 520.0)
        y = random.uniform(-260.0, 380.0)
    else:
        x = random.uniform(-1610.0, 3160.0)
        y = random.uniform(-2420.0, 1480.0)
    hit = ray_obj(island, x, y, ztop=800.0, dist=2000.0)
    if hit is None:
        continue
    p, nrm, mat_idx = hit
    if mat_idx != 0 or p.z < 1.1 or p.z > 70.0 or nrm.z < 0.62:
        continue
    if blocked(x, y, margin=6.0):
        continue
    if any(x0 <= x <= x1 and y0 <= y <= y1 for x0, y0, x1, y1 in house_pads):
        continue
    if any((x - px) ** 2 + (y - py) ** 2 < 11.0 ** 2 for px, py in spacing):
        continue
    scale = random.uniform(0.8, 1.2)
    # di luar 300 m dari kampung pakai LOD: di layar tidak terbaca bedanya,
    # tapi biaya render turun banyak (200 instance)
    far = math.hypot(x, y) > 300.0 or p.z > 25.0
    src_mesh = palm_lod if far else palm_template.data
    inst = bpy.data.objects.new(f"ENV_detail_palm-extra_{placed:03d}", src_mesh)
    root.objects.link(inst)
    inst.location = (x, y, p.z - 0.05)
    inst.rotation_euler = (random.uniform(-0.04, 0.04),
                           random.uniform(-0.04, 0.04),
                           random.uniform(0.0, math.tau))
    inst.scale = (scale, scale, scale)
    inst.parent = ctl
    spacing.append((x, y))
    placed += 1
print("palms placed", placed, "tries", tries)

# --------------------------------------------- kelapa pesisir (v002, klaster)
# 150 kelapa tambahan: klaster rapat 9–16 pohon, 10–25 m dari garis pantai,
# skala 1,25–1,75 dan tajuk 1,2x supaya siluet tajuk terbaca pada aerial 120 m.
def coastal_palm_mesh():
    me = palm_template.data.copy()
    me.name = "ENV_veg_palm-coastal"
    slots = [i for i, m in enumerate(me.materials)
             if m is not None and "frond" in m.name.lower()]
    if not slots:
        raise RuntimeError("material frond kelapa tidak ada: %s"
                           % [m.name for m in me.materials if m])
    for si in slots:
        young = "young" in me.materials[si].name.lower()
        me.materials[si] = MAT_PALM_FROND_Y if young else MAT_PALM_FROND
    vids = set()
    for poly in me.polygons:
        if poly.material_index in slots:
            vids.update(poly.vertices)
    crown = min(me.vertices[i].co.z for i in vids)
    for i in vids:
        co = me.vertices[i].co
        co.x *= FROND_BOOST
        co.y *= FROND_BOOST
        co.z = crown + (co.z - crown) * 1.05      # mahkota sedikit lebih tebal
    return me, slots, crown


coastal_me, coastal_slots, crown_z = coastal_palm_mesh()
print("coastal palm mesh verts", len(coastal_me.vertices),
      "frond slots", coastal_slots, "crown z", round(crown_z, 2))

# --- medan jarak ke garis pantai -------------------------------------------
# Mesh pulau tidak punya geometri bawah air: ray cast berhenti di tepi pantai
# (z ~0,25 m). Jadi peta darat/laut dibuat sekali di kisi 3 m, lalu jarak ke
# pantai dihitung dengan distance transform chamfer 2 lintasan.
COAST_STEP = 3.0
COAST_X0, COAST_X1 = -340.0, 445.0
COAST_Y0, COAST_Y1 = -70.0, 145.0
COAST_W = int((COAST_X1 - COAST_X0) / COAST_STEP) + 1
COAST_H = int((COAST_Y1 - COAST_Y0) / COAST_STEP) + 1
INF = 1e9
_dm = []
for _i in range(COAST_W):
    _x = COAST_X0 + _i * COAST_STEP
    _col = []
    for _j in range(COAST_H):
        _y = COAST_Y0 + _j * COAST_STEP
        _col.append(INF if ray_obj(island, _x, _y, ztop=800.0, dist=2000.0)
                    else 0.0)
    _dm.append(_col)
for _i in range(COAST_W):                      # lintasan maju
    for _j in range(COAST_H):
        _v = _dm[_i][_j]
        if _v == 0.0:
            continue
        if _i > 0:
            _v = min(_v, _dm[_i - 1][_j] + 1.0)
            if _j > 0:
                _v = min(_v, _dm[_i - 1][_j - 1] + 1.41421356)
            if _j < COAST_H - 1:
                _v = min(_v, _dm[_i - 1][_j + 1] + 1.41421356)
        if _j > 0:
            _v = min(_v, _dm[_i][_j - 1] + 1.0)
        _dm[_i][_j] = _v
for _i in range(COAST_W - 1, -1, -1):          # lintasan balik
    for _j in range(COAST_H - 1, -1, -1):
        _v = _dm[_i][_j]
        if _v == 0.0:
            continue
        if _i < COAST_W - 1:
            _v = min(_v, _dm[_i + 1][_j] + 1.0)
            if _j < COAST_H - 1:
                _v = min(_v, _dm[_i + 1][_j + 1] + 1.41421356)
            if _j > 0:
                _v = min(_v, _dm[_i + 1][_j - 1] + 1.41421356)
        if _j < COAST_H - 1:
            _v = min(_v, _dm[_i][_j + 1] + 1.0)
        _dm[_i][_j] = _v


def coast_dist(x, y):
    """Jarak (m) ke garis pantai dari medan jarak; None di luar peta."""
    i = int(round((x - COAST_X0) / COAST_STEP))
    j = int(round((y - COAST_Y0) / COAST_STEP))
    if not (0 <= i < COAST_W and 0 <= j < COAST_H):
        return None
    v = _dm[i][j]
    if v >= INF:
        return None
    return v * COAST_STEP


_land_cells = sum(1 for _i in range(COAST_W) for _j in range(COAST_H)
                  if _dm[_i][_j] > 0.0)
print("medan jarak pantai: grid", COAST_W, "x", COAST_H,
      "sel darat", _land_cells, "dibuat dari ray cast tepi pantai")

coast_placed = 0
cluster_centres = []
coast_spacing = []
coast_scales = []
coast_dists = []
tries = 0
while coast_placed < PALM_COASTAL and tries < 4000:
    tries += 1
    cx = random.uniform(COAST_X0 + 5.0, COAST_X1 - 5.0)
    cy = random.uniform(COAST_Y0 + 5.0, COAST_Y1 - 5.0)
    if any((cx - a) ** 2 + (cy - b) ** 2 < 20.0 ** 2 for a, b in cluster_centres):
        continue
    cdist = coast_dist(cx, cy)
    if cdist is None or not (COASTAL_MIN_D + 1.5 <= cdist <= COASTAL_MAX_D - 1.5):
        continue
    if blocked(cx, cy, margin=10.0):
        continue
    if any(x0 - 2.0 <= cx <= x1 + 2.0 and y0 - 2.0 <= cy <= y1 + 2.0
           for x0, y0, x1, y1 in house_pads):
        continue
    cluster_centres.append((cx, cy))
    want = random.randint(9, 16)
    added = 0
    for _k in range(want * 12):
        if added >= want or coast_placed >= PALM_COASTAL:
            break
        ang = random.uniform(0.0, math.tau)
        rad = random.uniform(1.6, 8.0) * math.sqrt(random.random() + 1e-6)
        x, y = cx + math.cos(ang) * rad, cy + math.sin(ang) * rad
        hit = ground_at(x, y)
        if hit is None:
            continue
        p, nrm, _mi = hit
        if p.z < 0.12 or p.z > 22.0 or nrm.z < 0.30:
            continue
        if blocked(x, y, margin=5.0):
            continue
        if any(x0 <= x <= x1 and y0 <= y <= y1 for x0, y0, x1, y1 in house_pads):
            continue
        if any((x - px) ** 2 + (y - py) ** 2 < 2.4 ** 2 for px, py in coast_spacing):
            continue
        d2 = coast_dist(x, y)
        if d2 is None or not (COASTAL_MIN_D <= d2 <= COASTAL_MAX_D):
            continue
        scale = random.uniform(1.25, 1.75)
        inst = bpy.data.objects.new(f"ENV_detail_palm-coast_{coast_placed:03d}",
                                    coastal_me)
        root.objects.link(inst)
        inst.location = (x, y, p.z - 0.05)
        inst.rotation_euler = (random.uniform(-0.05, 0.05),
                               random.uniform(-0.05, 0.05),
                               random.uniform(0.0, math.tau))
        inst.scale = (scale, scale, scale)
        inst.parent = ctl
        coast_spacing.append((x, y))
        coast_scales.append(scale)
        coast_dists.append(d2)
        coast_placed += 1
        added += 1
    print("klaster pesisir", len(cluster_centres),
          "di", round(cx, 1), round(cy, 1), "jarak pantai", round(cdist, 1),
          "m ->", added, "pohon (total", coast_placed, ")")

print("coastal palms", coast_placed, "klaster", len(cluster_centres),
      "tries", tries)
if coast_scales:
    print("skala pesisir min/avg/max",
          round(min(coast_scales), 3),
          round(sum(coast_scales) / len(coast_scales), 3),
          round(max(coast_scales), 3),
          "| jarak pantai min/max",
          round(min(coast_dists), 1), round(max(coast_dists), 1))

# ---------------------------------------------------------------- bidang air
def sea_material():
    mat = bpy.data.materials.new("MAT_detail_sea-surface")
    mat.use_nodes = True
    nt = mat.node_tree
    nodes, links = nt.nodes, nt.links
    bsdf = next(n for n in nodes if n.type == "BSDF_PRINCIPLED")
    set_input(bsdf, "Roughness", 0.18)
    set_input(bsdf, "IOR", 1.333)
    set_input(bsdf, "Metallic", 0.0)
    coord = nodes.new("ShaderNodeTexCoord")

    big = nodes.new("ShaderNodeTexNoise")
    set_input(big, "Scale", 0.012)
    set_input(big, "Detail", 2.5)
    set_input(big, "Roughness", 0.55)
    links.new(coord.outputs["Object"], big.inputs["Vector"])

    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.30
    ramp.color_ramp.elements[0].color = srgb("#1FA3A3")
    ramp.color_ramp.elements[1].position = 0.70
    ramp.color_ramp.elements[1].color = srgb("#178A8C")
    links.new(big.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])

    fine = nodes.new("ShaderNodeTexNoise")
    set_input(fine, "Scale", 0.30)
    set_input(fine, "Detail", 6.0)
    set_input(fine, "Roughness", 0.62)
    links.new(coord.outputs["Object"], fine.inputs["Vector"])
    bump = nodes.new("ShaderNodeBump")
    set_input(bump, "Strength", 0.10)
    set_input(bump, "Distance", 0.25)
    links.new(fine.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    mat.diffuse_color = srgb("#1FA3A3")
    return mat


def plane_mesh(name, size, z):
    me = bpy.data.meshes.new(name)
    s = size * 0.5
    me.from_pydata([(-s, -s, z), (s, -s, z), (s, s, z), (-s, s, z)], [], [(0, 1, 2, 3)])
    me.update()
    for p in me.polygons:
        p.use_smooth = True
    return me


sea_me = plane_mesh("ENV_detail_sea-surface", 4000.0, 0.0)
sea_me.materials.append(sea_material())
sea = bpy.data.objects.new("ENV_detail_sea-surface", sea_me)
sea.location = (0.0, -450.0, 0.0)
root.objects.link(sea)
sea.parent = ctl

# ------------------------------------------------------------------- world
# Langit berkabut + haze laut di horizon: tanpa tekstur, hanya gradien.
world = bpy.data.worlds.new("WLD_island-detail")
world.use_nodes = True
_wt = world.node_tree
_bg = next(n for n in _wt.nodes if n.type == "BACKGROUND")
_tc = _wt.nodes.new("ShaderNodeTexCoord")
_sep = _wt.nodes.new("ShaderNodeSeparateXYZ")
_map = _wt.nodes.new("ShaderNodeMapRange")
_map.inputs["From Min"].default_value = -0.02
_map.inputs["From Max"].default_value = 0.34
_ramp = _wt.nodes.new("ShaderNodeValToRGB")
_ramp.color_ramp.elements[0].position = 0.0
_ramp.color_ramp.elements[0].color = srgb("#1FA3A3")
_ramp.color_ramp.elements[1].position = 1.0
_ramp.color_ramp.elements[1].color = srgb("#F2E9DC")
_wt.links.new(_tc.outputs["Generated"], _sep.inputs["Vector"])
_wt.links.new(_sep.outputs["Z"], _map.inputs["Value"])
_wt.links.new(_map.outputs["Result"], _ramp.inputs["Fac"])
_wt.links.new(_ramp.outputs["Color"], _bg.inputs["Color"])
_bg.inputs["Strength"].default_value = 0.9
scene.world = world

# ----------------------------------------------------------------- kamera
def add_camera(name, loc, target, lens):
    cam_data = bpy.data.cameras.new(name)
    cam_data.lens = lens
    cam_data.clip_start = 0.5
    cam_data.clip_end = 30000.0
    cam = bpy.data.objects.new(name, cam_data)
    scene.collection.objects.link(cam)
    cam.location = loc
    cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return cam


cam_a = add_camera("CAM_detail_aerial", (170.0, -230.0, 120.0),
                   (-180.0, 130.0, 25.0), 24.0)
cam_b = add_camera("CAM_detail_village", (95.0, -150.0, 68.0),
                   (-4.0, 26.0, 4.0), 45.0)
scene.camera = cam_a

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

uniq = sum(len(m.vertices) for m in bpy.data.meshes)
print("objects", len(bpy.data.objects), "meshes", len(bpy.data.meshes),
      "unique mesh verts", uniq)
print("materials", len(bpy.data.materials))
print("collections", [c.name for c in bpy.data.collections])
print("images (harus 0)", [i.name for i in bpy.data.images])

"""Build assets/env/island-detail_v003.blend - fasad dive shop.

v003 (14 Nov 2026) - perbaikan fasad dive shop. Isi v002 disalin verbatim
(350 kelapa, 3.000 rumpun rumput, 12 rumah kampung, Manado Tua, bidang air
4 km, dermaga, annex atap putih) lewat append `link=False` dari
`island-detail_v002.blend`. **Tidak ada aset lain yang diubah atau dihapus.**

Satu-satunya objek lama yang disentuh: `ENV_surface_dive-shop`. Dinding polos
dibiarkan, tetapi kanopi datar lama yang melayang 4,4 m dari dinding (12 muka
+ 2 tiang tipis di ujung bangunan, sisa blockout) dibuang supaya teras baru
tidak tertutup; normal bangunan juga dihitung ulang keluar (sebelumnya semua
muka menghadap ke dalam sehingga bangunan tidak menerima cahaya matahari).
Bentuk, ukuran, dan material bangunan tidak berubah.

Fasad baru di dinding depan (bidang y = 2,00 m, hadap -Y ke arah laut), di
koleksi `ENV_island-detail_context`:

  ENV_shop_door              pintu ganda kayu 2,10 m (2 daun, 2 panel/daun), kusen krem
  ENV_shop_window_01..04     4 jendela berbingkai krem + kaca teal #0F5C63
                             (2 di kiri pintu, 2 di kanan), ambang + lintel kayu
  ENV_shop_porch-deck        teras kayu 10,0 x 2,5 m, 8 papan + balok bawah
  ENV_shop_porch-post_01..03 3 tiang kayu 0,18 m, 2,38 m di atas lantai + tiang pancang
  ENV_shop_porch-roof        atap teras menonjol 2,5 m dari dinding + lis kayu
  ENV_shop_sign-board        papan nama kayu 8,0 x 1,0 m + 2 braket
  ENV_shop_sign-text         huruf "BUNAKEN DIVE" sebagai MESH (bukan tekstur)
  ENV_shop_stairs            tangga 3 anak tangga ke teras
  ENV_shop_trim              balok tepi teras + lis dinding bawah atap

Warna memakai palette PROJECT.md §2 (tanpa material baru kecuali
`MAT_shop_sign-text`): kayu #E8D5B0, krem #F2E9DC, atap #E4713C, kaca #0F5C63.

Skala 1 unit = 1 m. Pivot semua objek baru di origin dunia (0,0,0) karena
geometri dibangun pada koordinat absolut bangunan di pulau.

Setelan file: EEVEE, 1920x1080, 24 fps, view transform Standard, frame 1,
tanpa pack tekstur, tanpa library. Skrip idempoten (selalu mulai dari wipe).
Lampu pratinjau hanya dipasang saat render lalu dihapus sebelum simpan.

Jalankan dari Blender apa pun (MCP atau `blender -b --python`):

    blender -b --python scripts/build-island-detail-v003.py
"""
import bpy
import bmesh
import math
import os
import time

from mathutils import Vector

try:
    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
except NameError:  # dijalankan lewat exec() MCP: __file__ tidak ada
    ROOT = r"D:\Tugas Semester 5\Grafika Komputer\Project-Animasi"

ENV_DIR = os.path.join(ROOT, "assets", "env")
SRC = os.path.join(ENV_DIR, "island-detail_v002.blend")
OUT = os.path.join(ENV_DIR, "island-detail_v003.blend")
WIPE = os.path.join(ROOT, "renders", "tmp", "_wipe.blend")
STILLS = os.path.join(ROOT, "renders", "stills")
LOG = os.path.join(ROOT, "renders", "logs", "modeling.log")

# geometri dive shop (diukur dari ENV_surface_dive-shop, satuan meter)
WALL_Y = 2.00       # bidang dinding depan (menghadap -Y)
FRONT_Y = 1.90      # muka kusen menonjol 10 cm dari dinding
FLOOR_Z = 0.62      # puncak lantai teras = puncak plinth 0,50 + papan 0,12


def log(line):
    stamp = time.strftime("%H:%M")
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as fh:
            fh.write("[%s] %s\n" % (stamp, line))
    except Exception as err:  # pragma: no cover
        print("peringatan log:", err)
    print("[%s] %s" % (stamp, line))


# --------------------------------------------------------------------- utils
def srgb(hex_color):
    h = hex_color.lstrip("#")
    out = []
    for i in (0, 2, 4):
        u = int(h[i:i + 2], 16) / 255.0
        out.append(u / 12.92 if u <= 0.04045 else ((u + 0.055) / 1.055) ** 2.4)
    return out


def set_input(node, name, value):
    if name in node.inputs:
        node.inputs[name].default_value = value


def make_mat(name, hex_color, rough=0.85, metallic=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    col = srgb(hex_color)
    set_input(bsdf, "Base Color", (col[0], col[1], col[2], 1.0))
    set_input(bsdf, "Roughness", rough)
    set_input(bsdf, "Metallic", metallic)
    mat.diffuse_color = (col[0], col[1], col[2], 1.0)
    return mat


def get_or_make(name, hex_color, rough=0.85, metallic=0.0):
    mat = bpy.data.materials.get(name)
    if mat is not None:
        return mat
    return make_mat(name, hex_color, rough, metallic)


def wipe():
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
                   bpy.data.images, bpy.data.fonts):
        for b in list(blocks):
            try:
                blocks.remove(b)
            except Exception:
                pass
    return scn


def purge_libraries():
    for lib in list(bpy.data.libraries):
        try:
            bpy.data.libraries.remove(lib)
        except Exception as err:
            print("PERINGATAN library masih dipakai:", lib.filepath, err)


def drop_render_result():
    """Render Result bukan tekstur, tapi dibuang supaya file bersih."""
    for img in list(bpy.data.images):
        if img.type == "RENDER_RESULT":
            try:
                bpy.data.images.remove(img)
            except Exception as err:
                print("peringatan render result:", err)


# ------------------------------------------------------------------ builder
class Part:
    """Kumpulan kotak dalam satu objek mesh dengan beberapa slot material."""

    def __init__(self, name, coll, mats):
        self.name = name
        self.coll = coll
        self.mats = mats
        self.bm = bmesh.new()

    def box(self, x0, x1, y0, y1, z0, z1, mi=0, drop=0.0):
        """Kotak sumbu-sejajar; `drop` menurunkan sudut atas di sisi -Y."""
        zf = z1 - drop
        v = [self.bm.verts.new((x0, y0, z0)), self.bm.verts.new((x1, y0, z0)),
             self.bm.verts.new((x1, y1, z0)), self.bm.verts.new((x0, y1, z0)),
             self.bm.verts.new((x0, y0, zf)), self.bm.verts.new((x1, y0, zf)),
             self.bm.verts.new((x1, y1, z1)), self.bm.verts.new((x0, y1, z1))]
        quads = ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
                 (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7))
        for q in quads:
            try:
                f = self.bm.faces.new([v[i] for i in q])
                f.material_index = mi
            except ValueError:
                pass
        return self

    def boxc(self, cx, cy, cz, sx, sy, sz, mi=0, drop=0.0):
        return self.box(cx - sx * 0.5, cx + sx * 0.5, cy - sy * 0.5, cy + sy * 0.5,
                        cz - sz * 0.5, cz + sz * 0.5, mi, drop)

    def finish(self, bevel=0.0):
        bm = self.bm
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        if bevel > 0.0:
            try:
                bmesh.ops.bevel(bm, geom=list(bm.verts) + list(bm.edges),
                                offset=bevel, segments=1, affect="EDGES",
                                profile=0.5, clamp_overlap=True)
                bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
            except Exception as err:
                print("peringatan bevel", self.name, err)
        me = bpy.data.meshes.new(self.name)
        bm.to_mesh(me)
        bm.free()
        for m in self.mats:
            me.materials.append(m)
        for p in me.polygons:
            p.use_smooth = False
        ob = bpy.data.objects.new(self.name, me)
        self.coll.objects.link(ob)
        ob["part"] = "fasad dive shop v003"
        return ob


def add_camera(name, loc, target, lens):
    cam_data = bpy.data.cameras.new(name)
    cam_data.lens = lens
    cam_data.clip_start = 0.1
    cam_data.clip_end = 30000.0
    cam = bpy.data.objects.new(name, cam_data)
    bpy.context.scene.collection.objects.link(cam)
    cam.location = loc
    cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return cam


def add_sun(name, direction, energy, angle=0.06):
    data = bpy.data.lights.new(name, "SUN")
    data.energy = energy
    data.angle = angle
    ob = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(ob)
    ob.rotation_euler = Vector(direction).to_track_quat("-Z", "Y").to_euler()
    return ob


# --------------------------------------------------------------------- setup
os.makedirs(os.path.dirname(WIPE), exist_ok=True)
os.makedirs(STILLS, exist_ok=True)
try:
    bpy.context.preferences.filepaths.save_version = 0
except Exception:
    pass

scn = wipe()
if bpy.data.filepath and os.path.abspath(bpy.data.filepath) != os.path.abspath(WIPE):
    bpy.ops.wm.save_as_mainfile(filepath=WIPE)
    print("scratch:", bpy.data.filepath)
scn.name = "island-detail"

# --------------------------------------------------- append v002 (link=False)
with bpy.data.libraries.load(SRC, link=False) as (df, dt):
    src_cols = list(df.collections)
    src_objs = list(df.objects)
    src_worlds = list(df.worlds)
    dt.collections = src_cols
    dt.objects = src_objs
    dt.worlds = src_worlds

root = bpy.data.collections.get("ENV_island-detail")
ctx = bpy.data.collections.get("ENV_island-detail_context")
if root is None or ctx is None:
    raise RuntimeError("koleksi v002 tidak terbawa append")
if root.name not in [c.name for c in scn.collection.children]:
    scn.collection.children.link(root)
for w in bpy.data.worlds:
    scn.world = w
    break
print("objects sesudah append:", len(bpy.data.objects))

shop = bpy.data.objects.get("ENV_surface_dive-shop")
if shop is None:
    raise RuntimeError("ENV_surface_dive-shop tidak ada di v002")

# --------------------------------------------------------------- material
MAT_WOOD = get_or_make("MAT_detail_wood", "#E8D5B0", rough=0.82)
MAT_KREM = get_or_make("MAT_detail_wall", "#F2E9DC", rough=0.88)
MAT_ROOF = get_or_make("MAT_detail_roof", "#E4713C", rough=0.62)
MAT_GLASS = get_or_make("MAT_detail_window", "#0F5C63", rough=0.18)
MAT_SIGNTXT = get_or_make("MAT_shop_sign-text", "#0F5C63", rough=0.55)

# ------------------------------------- bersihkan kanopi datar lama (blockout)
shop_verts_before = len(shop.data.vertices)
bm = bmesh.new()
bm.from_mesh(shop.data)
bm.verts.ensure_lookup_table()
bm.faces.ensure_lookup_table()
doomed = [f for f in bm.faces if f.calc_center_median().y < 0.9]   # kanopi y <= 0
n_old = len(doomed)
if doomed:
    bmesh.ops.delete(bm, geom=doomed, context="FACES")
loose = [v for v in bm.verts if not v.link_faces]
if loose:
    bmesh.ops.delete(bm, geom=loose, context="VERTS")
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)      # normal menghadap keluar
bm.to_mesh(shop.data)
bm.free()
shop.data.update()
log("MODEL - dive shop: %d muka kanopi datar lama dibuang, %d -> %d vert, normal "
    "dihitung ulang keluar (bentuk/ukuran/material tidak berubah)"
    % (n_old, shop_verts_before, len(shop.data.vertices)))

# ------------------------------------------------------------- 1. pintu ganda
door = Part("ENV_shop_door", ctx, [MAT_WOOD, MAT_KREM])
DOOR_X0, DOOR_X1 = 10.41, 11.59          # 2 daun x 0,585 m
DOOR_Z0, DOOR_Z1 = FLOOR_Z, 2.72         # tinggi 2,10 m
LEAF = (DOOR_X1 - DOOR_X0) * 0.5 - 0.005
for x0 in (DOOR_X0, DOOR_X0 + LEAF + 0.010):
    x1 = x0 + LEAF
    door.box(x0, x1, 1.935, 1.985, DOOR_Z0, DOOR_Z1, mi=0)
    for z0, z1 in ((0.74, 1.58), (1.70, 2.56)):     # 2 panel per daun
        door.box(x0 + 0.085, x1 - 0.085, 1.900, 1.938, z0, z1, mi=0)
# kusen pintu (krem) menonjol 10 cm
door.box(10.31, 10.41, FRONT_Y, 2.02, FLOOR_Z, 2.82, mi=1)
door.box(11.59, 11.69, FRONT_Y, 2.02, FLOOR_Z, 2.82, mi=1)
door.box(10.31, 11.69, FRONT_Y, 2.02, 2.72, 2.82, mi=1)
door.box(10.31, 11.69, 1.89, 2.02, 0.56, FLOOR_Z, mi=1)      # ambang
# gagang pintu (krem)
door.boxc(10.905, 1.885, 1.46, 0.045, 0.06, 0.22, mi=1)
door.boxc(11.095, 1.885, 1.46, 0.045, 0.06, 0.22, mi=1)
door_ob = door.finish(bevel=0.006)

# ---------------------------------------------------------------- 2. jendela
WIN_CX = (7.00, 8.60, 13.40, 15.00)      # 2 kiri + 2 kanan pintu
WIN_W, WIN_Z0, WIN_Z1 = 1.10, 1.40, 2.60  # ambang 0,78 m di atas lantai teras
win_obs = []
for i, cx in enumerate(WIN_CX, start=1):
    x0, x1 = cx - WIN_W * 0.5, cx + WIN_W * 0.5
    p = Part("ENV_shop_window_%02d" % i, ctx, [MAT_KREM, MAT_GLASS, MAT_WOOD])
    f = 0.08                                  # lebar batang kusen
    p.box(x0, x0 + f, FRONT_Y, 2.00, WIN_Z0, WIN_Z1, mi=0)          # tiang kiri
    p.box(x1 - f, x1, FRONT_Y, 2.00, WIN_Z0, WIN_Z1, mi=0)          # tiang kanan
    p.box(x0, x1, FRONT_Y, 2.00, WIN_Z1 - f, WIN_Z1, mi=0)          # ambang atas
    p.box(x0, x1, FRONT_Y, 2.00, WIN_Z0, WIN_Z0 + f, mi=0)          # ambang bawah
    p.box(cx - 0.03, cx + 0.03, FRONT_Y, 2.00, WIN_Z0, WIN_Z1, mi=0)  # mullion
    p.box(x0, x1, FRONT_Y, 2.00, 1.965, 2.025, mi=0)                # rel tengah
    p.box(x0 + f, x1 - f, 1.945, 1.975, WIN_Z0 + f, WIN_Z1 - f, mi=1)  # kaca
    p.box(x0 - 0.07, x1 + 0.07, 1.830, 2.02, WIN_Z0 - 0.09, WIN_Z0, mi=2)  # ambang kayu
    p.box(x0 - 0.05, x1 + 0.05, 1.855, 2.02, WIN_Z1, WIN_Z1 + 0.10, mi=2)  # lintel kayu
    win_obs.append(p.finish(bevel=0.005))

# ------------------------------------------------------------- 3. teras kayu
# teras 10,0 m; digeser 1 m ke kiri dari sumbu bangunan supaya tiang tengah
# tidak menghalangi pintu (pintu tetap di sumbu fasad x = 11,00)
PORCH_X0, PORCH_X1 = 5.00, 15.00         # 10,0 m
PORCH_Y0, PORCH_Y1 = -0.50, WALL_Y       # 2,5 m menjorok dari dinding
deck = Part("ENV_shop_porch-deck", ctx, [MAT_WOOD])
n_boards, gap = 8, 0.02
bw = ((PORCH_Y1 - PORCH_Y0) - (n_boards - 1) * gap) / n_boards
for i in range(n_boards):
    y0 = PORCH_Y0 + i * (bw + gap)
    deck.box(PORCH_X0, PORCH_X1, y0, y0 + bw, FLOOR_Z - 0.07, FLOOR_Z, mi=0)
for bx in (5.25, 9.90, 14.55):           # balok bawah papan
    deck.box(bx, bx + 0.20, PORCH_Y0 + 0.05, PORCH_Y1, FLOOR_Z - 0.20,
             FLOOR_Z - 0.07, mi=0)
deck_ob = deck.finish(bevel=0.004)

# ------------------------------------------------- 4. tiang + tiang pancang
ROOF_Z0, ROOF_Z1 = 3.00, 3.20
POSTS_X = (5.35, 10.00, 14.65)           # tiang tengah di x 10,00: di kiri pintu
posts = []
for i, cx in enumerate(POSTS_X, start=1):
    p = Part("ENV_shop_porch-post_%02d" % i, ctx, [MAT_WOOD])
    p.boxc(cx, -0.30, (FLOOR_Z + ROOF_Z0) * 0.5, 0.18, 0.18, ROOF_Z0 - FLOOR_Z, mi=0)
    p.boxc(cx, -0.30, FLOOR_Z + 0.05, 0.28, 0.28, 0.10, mi=0)      # alas tiang
    p.boxc(cx, -0.30, ROOF_Z0 - 0.05, 0.26, 0.26, 0.10, mi=0)      # kepala tiang
    p.boxc(cx, -0.30, 0.14, 0.18, 0.18, 1.06, mi=0)                # pancang ke air
    posts.append(p.finish(bevel=0.005))

# --------------------------------------------------------------- 5. atap teras
roof = Part("ENV_shop_porch-roof", ctx, [MAT_ROOF, MAT_WOOD])
roof.box(PORCH_X0 - 0.12, PORCH_X1 + 0.12, PORCH_Y0 - 0.32, 2.05,
         ROOF_Z0, ROOF_Z1, mi=0, drop=0.12)                        # bidang atap
roof.box(PORCH_X0 - 0.18, PORCH_X1 + 0.18, PORCH_Y0 - 0.38, PORCH_Y0 - 0.24,
         ROOF_Z0 - 0.12, ROOF_Z1, mi=1)                            # lis depan kayu
for cx in POSTS_X:                                                  # balok
    roof.box(cx - 0.08, cx + 0.08, PORCH_Y0 - 0.24, WALL_Y,
             ROOF_Z0 - 0.12, ROOF_Z0, mi=1)
roof_ob = roof.finish(bevel=0.004)

# ------------------------------------------------------------ 6. papan nama
SIGN_X0, SIGN_X1 = 7.00, 15.00           # 8,0 m
SIGN_Z0, SIGN_Z1 = 3.42, 4.42            # 1,0 m, di atas atap teras
sign = Part("ENV_shop_sign-board", ctx, [MAT_WOOD])
sign.box(SIGN_X0, SIGN_X1, 1.94, 2.00, SIGN_Z0, SIGN_Z1, mi=0)
sign.box(SIGN_X0 + 0.18, SIGN_X0 + 0.42, 1.90, 2.00, SIGN_Z0 - 0.16, SIGN_Z0 + 0.04, mi=0)
sign.box(SIGN_X1 - 0.42, SIGN_X1 - 0.18, 1.90, 2.00, SIGN_Z0 - 0.16, SIGN_Z0 + 0.04, mi=0)
sign.box(SIGN_X0, SIGN_X1, 1.925, 1.985, SIGN_Z1, SIGN_Z1 + 0.07, mi=0)   # lis atas
sign_ob = sign.finish(bevel=0.005)

# huruf mesh: FONT -> MESH, bukan tekstur
cu = bpy.data.curves.new("ENV_shop_sign-text", type="FONT")
cu.body = "BUNAKEN DIVE"
cu.size = 1.0
cu.extrude = 0.025
cu.align_x = "CENTER"
cu.align_y = "CENTER"
cu.resolution_u = 3
cu.offset = 0.004
txt = bpy.data.objects.new("ENV_shop_sign-text", cu)
ctx.objects.link(txt)
txt.rotation_euler = (math.pi * 0.5, 0.0, 0.0)   # bidang teks menghadap -Y
txt.location = (11.0, 1.915, (SIGN_Z0 + SIGN_Z1) * 0.5)
bpy.ops.object.select_all(action="DESELECT")
txt.select_set(True)
bpy.context.view_layer.objects.active = txt
bpy.ops.object.convert(target="MESH")
txt = bpy.context.view_layer.objects.active
scale = 7.40 / txt.dimensions.x
txt.scale = (scale, scale, scale)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
txt.data.materials.append(MAT_SIGNTXT)
for p in txt.data.polygons:
    p.use_smooth = False
txt["part"] = "fasad dive shop v003"
txt_verts = len(txt.data.vertices)
txt_dims = tuple(round(v, 3) for v in txt.dimensions)

# ------------------------------------------------------------------ 7. tangga
stairs = Part("ENV_shop_stairs", ctx, [MAT_WOOD])
STEP_W = 1.70
STEP_TREAD = 0.10
for ztop, y0, y1 in ((0.45, -0.50, -0.84), (0.28, -0.84, -1.18),
                     (0.11, -1.18, -1.52)):
    stairs.box(11.0 - STEP_W * 0.5, 11.0 + STEP_W * 0.5, y0, y1,
               ztop - STEP_TREAD, ztop, mi=0)                     # papan pijak
    stairs.box(11.0 - STEP_W * 0.5, 11.0 + STEP_W * 0.5, y1 - 0.05, y1,
               ztop - 0.17, ztop - STEP_TREAD, mi=0)              # papan tegak
for sx in (11.0 - STEP_W * 0.5 - 0.06, 11.0 + STEP_W * 0.5):
    stairs.box(sx, sx + 0.06, -0.50, -1.52, 0.02, 0.52, mi=0)     # rusuk samping
stairs_ob = stairs.finish(bevel=0.004)

# -------------------------------------------------------------------- 8. trim
trim = Part("ENV_shop_trim", ctx, [MAT_WOOD])
trim.box(PORCH_X0, PORCH_X1, PORCH_Y0 - 0.06, PORCH_Y0, FLOOR_Z - 0.20, FLOOR_Z, mi=0)
trim.box(WALL_Y - 0.05, WALL_Y, PORCH_X0, PORCH_X1, ROOF_Z0 - 0.16, ROOF_Z0 - 0.08, mi=0)
trim_ob = trim.finish(bevel=0.003)

new_obs = [door_ob, *win_obs, deck_ob, *posts, roof_ob, sign_ob, txt, stairs_ob, trim_ob]
names = [o.name for o in new_obs]
verts = sum(len(o.data.vertices) for o in new_obs)
log("MODEL - fasad dive shop v003: %d objek baru (%d vert), dinding y=2,00 m hadap -Y, "
    "pintu 2,10 m + 4 jendela + teras 2,5 m + 3 tiang + papan nama mesh + 3 anak tangga"
    % (len(new_obs), verts))
print("objek fasad:", names)

# ------------------------------------------------------------- render setup
scn.frame_set(1)
scn.frame_start = 1
scn.frame_end = 1
scn.render.fps = 24
scn.render.resolution_x = 1920
scn.render.resolution_y = 1080
scn.render.resolution_percentage = 100
scn.view_settings.view_transform = "Standard"
try:
    scn.view_settings.look = "None"
except Exception:
    pass
scn.render.image_settings.file_format = "PNG"
scn.render.film_transparent = False
for engine in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
    try:
        scn.render.engine = engine
        break
    except TypeError:
        continue
try:
    scn.eevee.taa_render_samples = 32
except Exception:
    pass
print("engine:", scn.render.engine, "world:", scn.world.name if scn.world else None)

# kamera pratinjau fasad (tambahan, kamera lama tidak diubah)
cam1 = add_camera("CAM_shop-facade-01", (11.0, -10.5, 2.55), (11.0, 1.70, 2.15), 32.0)
cam2 = add_camera("CAM_shop-facade-02", (20.4, -8.8, 4.10), (9.6, 1.70, 2.30), 34.0)
cam_aerial = bpy.data.objects.get("CAM_detail_aerial")
scn.camera = cam_aerial or cam1

# ------------------------------------------------------------ render 2 sudut
temp_lights = [add_sun("LGT_tmp-key", (-0.28, 0.86, -0.42), 3.4, 0.05),
               add_sun("LGT_tmp-fill", (0.55, 0.60, -0.28), 1.2, 0.4)]


def render(path, cam, pct=50):
    scn.camera = cam
    scn.render.resolution_percentage = pct
    scn.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("RENDER", path, os.path.exists(path))


p1 = os.path.join(STILLS, "island-detail-v003_preview-01.png")
p2 = os.path.join(STILLS, "island-detail-v003_preview-02.png")
render(p1, cam1)
render(p2, cam2)
for lt in temp_lights:
    bpy.data.objects.remove(lt, do_unlink=True)
log("VERIFY - render fasad (skala 50%%): %s, %s (kamera depan teras + 3/4)"
    % (os.path.basename(p1), os.path.basename(p2)))

# ----------------------------------------------------------------- simpan
scn.camera = cam_aerial or cam1
scn.render.resolution_percentage = 100
scn.render.filepath = "//"
purge_libraries()
drop_render_result()
bpy.ops.wm.save_as_mainfile(filepath=OUT)
size_mb = round(os.path.getsize(OUT) / 1048576.0, 2)
log("MODEL - island-detail_v003.blend disimpan (%s MB, %d objek, %d vert objek baru)"
    % (size_mb, len(bpy.data.objects), verts))
print("images (harus 0):", [i.name for i in bpy.data.images])
print("libraries (harus 0):", [l.filepath for l in bpy.data.libraries])
print("lights (harus LGT_sun saja):", [o.name for o in bpy.data.objects if o.type == "LIGHT"])
print("dims teks:", txt_dims, "verts teks:", txt_verts)
print("collection fasad:", len(ctx.objects), "objek di", ctx.name)
print("MAT fasad:", {o.name: [m.name for m in o.data.materials] for o in new_obs[:3]})

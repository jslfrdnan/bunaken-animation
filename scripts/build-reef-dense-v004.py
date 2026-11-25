"""Build assets/env/reef-dense_v004.blend — titik selam padat Scene 1/4.

v004 (25 Nov 2026) — permintaan Director:
  * **3 varian karang baru** yang bentuknya berbeda dari 4 mesh lama
    (bercabang, bercabang-b, massif, meja): **karang otak**, **karang pipa**,
    **karang jamur** -> total **7 tipe**.
  * 140 karang tetap, komposisi **55 % bercabang (77) / 30 % massif (42) /
    10 % meja (14) / 5 % varian baru (7) = 140**.
  * Warna tetap palette PROJECT.md §2 (material MAT_reef_coral-* v002
    di-append apa adanya); **aksen oranye < 7 %** dari luas permukaan karang.
  * Isi lain v003 dipertahankan: lamun 600 rumpun, pasir 26 x 26 m, 3 sekolah
    ikan (12 cakalang / 20 kakatua / 24 damselfish), 12 klaster.

Tahap karang + pasir ditulis ulang di sini; tahap lamun, sekolah ikan, world,
kamera, dan setelan render dipanggil dari `scripts/build-reef-dense-v003.py`
(modul diimpor, bukan dijalankan sebagai __main__) supaya look v003 tidak
bergeser. Skrip idempoten.

    blender -b --python scripts/build-reef-dense-v004.py
"""
import bpy
import bmesh
import importlib.util
import math
import os
import random
import time

from mathutils import Vector

try:
    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
except NameError:
    ROOT = r"D:\Tugas Semester 5\Grafika Komputer\Project-Animasi"

ENV_DIR = os.path.join(ROOT, "assets", "env")
REEF = os.path.join(ENV_DIR, "reef.blend")
V002 = os.path.join(ENV_DIR, "reef-dense_v002.blend")
OUT = os.path.join(ENV_DIR, "reef-dense_v004.blend")
STILLS = os.path.join(ROOT, "renders", "stills")
LOG = os.path.join(ROOT, "renders", "logs", "modeling.log")
V003_SCRIPT = os.path.join(ROOT, "scripts", "build-reef-dense-v003.py")

SEED = 20261125
CORAL_TOTAL = 140
N_BRANCH = 77          # 55 %  (branch + branch_b)
N_BOULDER = 42         # 30 %
N_TABLE = 14           # 10 %
N_NEW = 7              # 5 %   (otak 3, pipa 2, jamur 2)
N_BRANCH_A = N_BRANCH - 27
N_BRANCH_B = 27
CLUSTER_COUNT = 12

CORAL_SRC = ["ENV_reef_branching-coral", "ENV_reef_branching-coral_b",
             "ENV_reef_boulder-coral", "ENV_reef_table-coral",
             "ENV_reef_table-coral_stem"]
MAT_CORAL = ["MAT_reef_coral-branching", "MAT_reef_coral-massive",
             "MAT_reef_coral-table", "MAT_reef_coral-accent"]
MAT_OTHER = ["MAT_dense_sand", "MAT_dense_seagrass", "MAT_dense_seagrass-dark"]
ROOT_COLL = "ENV_reef-dense"
CTL = "CTL_reef-dense"


def log(line):
    stamp = time.strftime("%H:%M")
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as fh:
            fh.write("[%s] %s\n" % (stamp, line))
    except Exception as err:  # pragma: no cover
        print("peringatan log:", err)
    print("[%s] %s" % (stamp, line))


def load_v003():
    spec = importlib.util.spec_from_file_location("reef_dense_v003", V003_SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)          # hanya definisi fungsi/konstanta
    mod.OUT = OUT
    return mod


# ============================================================ mesh karang baru
def build_brain_coral(name, coll):
    """Karang otak: kubah rendah dengan alur radial berkelok (alur dalam)."""
    SEG, RINGS = 48, 15
    R, H = 0.44, 0.46
    bm = bmesh.new()
    rings = []
    for k in range(RINGS + 1):
        t = k / RINGS
        rr = R * max(0.09, (1.0 - t ** 1.9) ** 0.5)
        z = H * t ** 0.92
        ring = []
        for i in range(SEG):
            a = math.tau * i / SEG
            wob = (0.105 * math.sin(12.0 * a + 1.8 * math.sin(t * 6.5))
                   + 0.045 * math.sin(26.0 * a + 0.7))
            r = rr * (1.0 + wob * (0.40 + 0.60 * math.sin(t * math.pi)))
            zz = z + 0.030 * math.sin(12.0 * a + t * 5.0) * math.sin(t * math.pi)
            ring.append(bm.verts.new((math.cos(a) * r, math.sin(a) * r,
                                      max(0.0, zz))))
        rings.append(ring)
    for k in range(RINGS):
        a_ring, b_ring = rings[k], rings[k + 1]
        for i in range(SEG):
            i2 = (i + 1) % SEG
            try:
                bm.faces.new((a_ring[i], a_ring[i2], b_ring[i2], b_ring[i]))
            except ValueError:
                pass
    try:
        bm.faces.new(rings[-1])
    except ValueError:
        pass
    try:
        bm.faces.new(list(reversed(rings[0])))
    except ValueError:
        pass
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    return me


def build_tube_coral(name, coll):
    """Karang pipa: 11 tabung tegak berongga, tinggi 0,38–0,92 m."""
    rng = random.Random(SEED + 11)
    SEG = 10
    bm = bmesh.new()
    for _t in range(11):
        ang = rng.uniform(0.0, math.tau)
        rad = rng.uniform(0.0, 0.28) * math.sqrt(rng.random())
        cx, cy = math.cos(ang) * rad, math.sin(ang) * rad
        r_out = rng.uniform(0.045, 0.085)
        r_in = r_out * 0.62
        h = rng.uniform(0.38, 0.92) * (1.0 - rad * 0.9)
        tx, ty = rng.uniform(-0.14, 0.14), rng.uniform(-0.14, 0.14)

        def pt(rr, a, zz, cx=cx, cy=cy, tx=tx, ty=ty):
            return (cx + math.cos(a) * rr + tx * zz,
                    cy + math.sin(a) * rr + ty * zz, zz)

        outer_b = [bm.verts.new(pt(r_out, math.tau * i / SEG, 0.0)) for i in range(SEG)]
        outer_t = [bm.verts.new(pt(r_out, math.tau * i / SEG, h)) for i in range(SEG)]
        inner_t = [bm.verts.new(pt(r_in, math.tau * i / SEG, h)) for i in range(SEG)]
        inner_b = [bm.verts.new(pt(r_in, math.tau * i / SEG, h * 0.5)) for i in range(SEG)]
        for i in range(SEG):
            i2 = (i + 1) % SEG
            for quad in ((outer_b[i], outer_b[i2], outer_t[i2], outer_t[i]),
                         (outer_t[i], outer_t[i2], inner_t[i2], inner_t[i]),
                         (inner_t[i], inner_t[i2], inner_b[i2], inner_b[i])):
                try:
                    bm.faces.new(quad)
                except ValueError:
                    pass
        try:
            bm.faces.new(list(reversed(outer_b)))
        except ValueError:
            pass
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    return me


def build_mushroom_coral(name, coll):
    """Karang jamur: tangkai pendek + cakram bertepi berombak Ø0,68 m."""
    SEG = 36
    R, STALK_R, STALK_H = 0.34, 0.075, 0.16
    bm = bmesh.new()
    stalk_b = [bm.verts.new((math.cos(math.tau * i / SEG) * STALK_R,
                             math.sin(math.tau * i / SEG) * STALK_R, 0.0))
               for i in range(SEG)]
    stalk_t = [bm.verts.new((math.cos(math.tau * i / SEG) * STALK_R,
                             math.sin(math.tau * i / SEG) * STALK_R, STALK_H))
               for i in range(SEG)]
    for i in range(SEG):
        i2 = (i + 1) % SEG
        bm.faces.new((stalk_b[i], stalk_b[i2], stalk_t[i2], stalk_t[i]))
    bm.faces.new(list(reversed(stalk_b)))
    DOME = 0.115
    top_c = bm.verts.new((0.0, 0.0, STALK_H + DOME))
    bot_c = bm.verts.new((0.0, 0.0, STALK_H + DOME - 0.085))
    fracs = (0.30, 0.60, 0.85, 1.00)
    top_rings, bot_rings = [], []
    for t in fracs:
        tr, br = [], []
        for i in range(SEG):
            a = math.tau * i / SEG
            rr = R * t * (1.0 + 0.075 * math.sin(9.0 * a)
                          + 0.030 * math.sin(13.0 * a + 0.9))
            zt = STALK_H + DOME * (1.0 - t ** 2.1) - 0.030 * t ** 6
            tr.append(bm.verts.new((math.cos(a) * rr, math.sin(a) * rr, zt)))
            br.append(bm.verts.new((math.cos(a) * rr * 0.985,
                                    math.sin(a) * rr * 0.985,
                                    zt - 0.050 * (1.0 - 0.45 * t))))
        top_rings.append(tr)
        bot_rings.append(br)
    for i in range(SEG):                       # fan tengah atas
        i2 = (i + 1) % SEG
        bm.faces.new((top_c, top_rings[0][i], top_rings[0][i2]))
        bm.faces.new((bot_c, bot_rings[0][i2], bot_rings[0][i]))
    for k in range(len(fracs) - 1):
        for i in range(SEG):
            i2 = (i + 1) % SEG
            bm.faces.new((top_rings[k][i], top_rings[k][i2],
                          top_rings[k + 1][i2], top_rings[k + 1][i]))
            bm.faces.new((bot_rings[k][i], bot_rings[k + 1][i],
                          bot_rings[k + 1][i2], bot_rings[k][i2]))
    for i in range(SEG):                       # bibir
        i2 = (i + 1) % SEG
        bm.faces.new((top_rings[-1][i], bot_rings[-1][i],
                      bot_rings[-1][i2], top_rings[-1][i2]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    return me


def mesh_area_parts(me):
    tot = sum(p.area for p in me.polygons)
    acc = sum(p.area for p in me.polygons if p.material_index == 1)
    return tot, acc


# ================================================================== tahap karang
def stage_corals(mod):
    random.seed(SEED)
    mod.wipe()
    scene = mod.setup_scene()

    root = bpy.data.collections.new(ROOT_COLL)
    scene.collection.children.link(root)
    ctl = bpy.data.objects.new(CTL, None)
    ctl.empty_display_type = "PLAIN_AXES"
    ctl.empty_display_size = 2.0
    root.objects.link(ctl)

    tmp_coll = bpy.data.collections.new("TMP_src")
    scene.collection.children.link(tmp_coll)
    src_objs = mod.append_objects(REEF, CORAL_SRC + ["LGT_sun"])
    by_name = {o.name: o for o in src_objs}
    for n in CORAL_SRC:
        if n not in by_name:
            raise RuntimeError("karang tidak ada: " + n)
    for o in src_objs:
        mod.own(o, tmp_coll)
    sun = by_name["LGT_sun"]
    mod.own(sun, scene.collection)

    MESH_BRANCH = mod.eval_mesh(by_name["ENV_reef_branching-coral"],
                                "ENV_dense_coral_branching", tmp_coll, decimate=0.28)
    MESH_BRANCH_B = mod.eval_mesh(by_name["ENV_reef_branching-coral_b"],
                                  "ENV_dense_coral_branching-b", tmp_coll, decimate=0.5)
    MESH_BOULDER = mod.eval_mesh(by_name["ENV_reef_boulder-coral"],
                                 "ENV_dense_coral_boulder", tmp_coll, decimate=0.30)
    table_me = mod.eval_mesh(by_name["ENV_reef_table-coral"],
                             "ENV_dense_coral_table", tmp_coll, decimate=None)
    stem_obj = by_name["ENV_reef_table-coral_stem"]
    stem_me = stem_obj.data.copy()
    stem_me.name = "ENV_dense_coral_table-stem"
    MESH_TABLE = mod.merge_meshes("ENV_dense_coral_table-merged",
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

    # --------------------------------------------------------------- material
    mats = mod.append_materials(V002, MAT_CORAL + MAT_OTHER)
    MAT_BRANCH_C = mats.get("MAT_reef_coral-branching") or mod.make_mottle(
        "MAT_reef_coral-branching", "#3E8E6E", "#93C4A8", 4.5, rough=0.55)
    MAT_MASSIVE_C = mats.get("MAT_reef_coral-massive") or mod.make_mottle(
        "MAT_reef_coral-massive", "#0F5C63", "#3E8E6E", 1.6, rough=0.72)
    MAT_TABLE_C = mats.get("MAT_reef_coral-table") or mod.make_mottle(
        "MAT_reef_coral-table", "#8AAE8C", "#A9B98C", 6.0, rough=0.62)
    MAT_ACCENT = mats.get("MAT_reef_coral-accent") or mod.make_mat(
        "MAT_reef_coral-accent", "#E4713C", rough=0.5)
    MAT_ACCENT.use_fake_user = True
    # karang otak: mottle rapat dari dua warna palette (alur otak terbaca)
    MAT_BRAIN_C = mod.make_mottle("MAT_reef_coral-brain", "#0F5C63", "#3E8E6E",
                                  9.0, rough=0.68, detail=6.0)
    MAT_SAND = mats.get("MAT_dense_sand") or mod.make_mottle(
        "MAT_dense_sand", "#E8D5B0", "#CBB58D", 0.35, rough=0.95)

    mod.coral_accent_faces(MESH_BRANCH, MAT_BRANCH_C, MAT_ACCENT, 0.045)
    mod.coral_accent_faces(MESH_BRANCH_B, MAT_BRANCH_C, MAT_ACCENT, 0.045)
    mod.coral_accent_faces(MESH_BOULDER, MAT_MASSIVE_C, MAT_ACCENT, 0.0)
    mod.coral_accent_faces(MESH_TABLE, MAT_TABLE_C, MAT_ACCENT, 0.03, rim=True)

    # ------------------------------------------------ 3 varian karang baru
    MESH_BRAIN = build_brain_coral("ENV_dense_coral_brain", root)
    mod.coral_accent_faces(MESH_BRAIN, MAT_BRAIN_C, MAT_ACCENT, 0.0)

    MESH_TUBE = build_tube_coral("ENV_dense_coral_tube", root)
    mod.coral_accent_faces(MESH_TUBE, MAT_BRANCH_C, MAT_ACCENT, 0.05)

    MESH_MUSH = build_mushroom_coral("ENV_dense_coral_mushroom", root)
    mod.coral_accent_faces(MESH_MUSH, MAT_TABLE_C, MAT_ACCENT, 0.03, rim=True)

    with open(LOG, "a", encoding="utf-8") as _f:
        _f.write("")
    for me in (MESH_BRANCH, MESH_BRANCH_B, MESH_BOULDER, MESH_TABLE,
               MESH_BRAIN, MESH_TUBE, MESH_MUSH):
        tot, acc = mesh_area_parts(me)
        print("mesh %-30s vert %5d  dim %s  aksen %4.1f%%  %s"
              % (me.name, len(me.vertices), mod.mesh_bounds(me),
                 100.0 * acc / max(tot, 1e-9), [m.name for m in me.materials]))

    # ----------------------------------------------------------------- pasir
    bm = bmesh.new()
    N = 14
    grid = {}
    for iy in range(N + 1):
        for ix in range(N + 1):
            x = -mod.SEABED_HALF + 2 * mod.SEABED_HALF * ix / N
            y = -mod.SEABED_HALF + 2 * mod.SEABED_HALF * iy / N
            grid[(ix, iy)] = bm.verts.new((x, y, mod.seabed_z(x, y)))
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

    kinds = (["branch"] * N_BRANCH_A + ["branch_b"] * N_BRANCH_B
             + ["boulder"] * N_BOULDER + ["table"] * N_TABLE
             + ["brain"] * 3 + ["tube"] * 2 + ["mushroom"] * 2)
    if len(kinds) != CORAL_TOTAL:
        raise RuntimeError("komposisi %d != %d" % (len(kinds), CORAL_TOTAL))
    rng.shuffle(kinds)

    TYPE_INFO = {
        "branch": (MESH_BRANCH, 0.36, (1.15, 3.3)),
        "branch_b": (MESH_BRANCH_B, 0.25, (1.4, 4.4)),
        "boulder": (MESH_BOULDER, 1.20, (0.42, 1.15)),
        "table": (MESH_TABLE, 0.79, (0.65, 1.6)),
        "brain": (MESH_BRAIN, 0.46, (0.70, 1.60)),
        "tube": (MESH_TUBE, 0.92, (0.58, 1.30)),
        "mushroom": (MESH_MUSH, 0.29, (0.85, 1.90)),
    }

    per_cluster = [CORAL_TOTAL // CLUSTER_COUNT] * CLUSTER_COUNT
    for i in range(CORAL_TOTAL - sum(per_cluster)):
        per_cluster[i] += 1

    placed = 0
    heights = []
    for ci, (cx, cy) in enumerate(clusters):
        radius = rng.uniform(1.6, 2.8)
        for _k in range(per_cluster[ci]):
            kind = kinds[placed]
            mesh, base_h, (smin, smax) = TYPE_INFO[kind]
            ang = rng.uniform(0.0, math.tau)
            rad = radius * math.sqrt(rng.random())
            x = cx + math.cos(ang) * rad
            y = cy + math.sin(ang) * rad
            x = max(-mod.AREA_HALF, min(mod.AREA_HALF, x))
            y = max(-mod.AREA_HALF, min(mod.AREA_HALF, y))
            scale = rng.uniform(smin, smax)
            h = base_h * scale
            if h < mod.CORAL_H_MIN:
                scale *= mod.CORAL_H_MIN / max(h, 1e-4)
            elif h > mod.CORAL_H_MAX:
                scale *= mod.CORAL_H_MAX / h
            h = base_h * scale
            ob = bpy.data.objects.new("ENV_dense_coral_%04d" % placed, mesh)
            root.objects.link(ob)
            ob.location = (x, y, mod.seabed_z(x, y) - 0.04)
            ob.rotation_euler = (rng.uniform(-0.05, 0.05),
                                 rng.uniform(-0.05, 0.05),
                                 rng.uniform(0.0, math.tau))
            ob.scale = (scale, scale, scale)
            ob.parent = ctl
            ob["coral_type"] = kind
            heights.append(h)
            placed += 1

    # ------------------------------------------------- rekap aksen & komposisi
    type_count = {}
    area_accent = 0.0
    area_total = 0.0
    for ob in root.objects:
        if ob.type != "MESH" or not ob.name.startswith("ENV_dense_coral_"):
            continue
        me = ob.data
        sc = max(ob.scale) ** 2
        tot, acc = mesh_area_parts(me)
        area_total += tot * sc
        area_accent += acc * sc
        t = ob.get("coral_type", "?")
        type_count[t] = type_count.get(t, 0) + 1
    accent_pct = 100.0 * area_accent / max(area_total, 1e-9)
    types = [k for k in ("branch", "branch_b", "boulder", "table",
                         "brain", "tube", "mushroom")]
    print("komposisi:", type_count, "total", sum(type_count.values()))
    print("tipe mesh unik:", len({ob.data.name for ob in root.objects
                                  if ob.type == "MESH"
                                  and ob.name.startswith("ENV_dense_coral_")}))
    print("aksen oranye: %.2f%% dari luas permukaan karang" % accent_pct)
    log("MODEL - reef-dense_v004: %d karang, 7 tipe (%s), komposisi 55/30/10/5 "
        "(bercabang %d, massif %d, meja %d, baru %d), aksen oranye %.2f%%"
        % (placed, ", ".join(types),
           type_count.get("branch", 0) + type_count.get("branch_b", 0),
           type_count.get("boulder", 0), type_count.get("table", 0),
           type_count.get("brain", 0) + type_count.get("tube", 0)
           + type_count.get("mushroom", 0), accent_pct))

    mod.purge_libraries()
    bpy.ops.wm.save_as_mainfile(filepath=OUT)
    print("TAHAP 1 saved", OUT, round(os.path.getsize(OUT) / 1048576.0, 2), "MB")
    return accent_pct


def render_previews(scn, prefix):
    cam_a = bpy.data.objects.get("CAM_dense_01")
    cam_b = bpy.data.objects.get("CAM_dense_02")
    if cam_a is None or cam_b is None:
        raise RuntimeError("kamera pratinjau tidak ada")
    for idx, cam in ((1, cam_a), (2, cam_b)):
        scn.camera = cam
        scn.render.resolution_percentage = 50
        scn.render.filepath = os.path.join(STILLS, "%s_preview-%02d.png" % (prefix, idx))
        bpy.ops.render.render(write_still=True)
        print("RENDER", scn.render.filepath, os.path.exists(scn.render.filepath))
    scn.camera = cam_a
    scn.render.resolution_percentage = 100


def drop_render_result():
    for img in list(bpy.data.images):
        if img.type == "RENDER_RESULT":
            try:
                bpy.data.images.remove(img)
            except Exception as err:
                print("peringatan render result:", err)


def render_new_corals(scn):
    """Render dekat satu contoh tiap varian baru (bukti bentuk berbeda)."""
    from mathutils import Vector as V
    cam = bpy.data.objects.get("CAM_dense_01")
    home = (cam.location.copy(), cam.rotation_euler.copy(), cam.data.lens)
    picks = {}
    for ob in bpy.data.objects:
        kind = ob.get("coral_type")
        if kind in ("brain", "tube", "mushroom") and kind not in picks:
            picks[kind] = ob
    for kind, ob in picks.items():
        cos = [ob.matrix_world @ V(c) for c in ob.bound_box]
        cen = sum(cos, V((0, 0, 0))) / 8.0
        size = max(ob.dimensions)
        d = max(0.35, size)
        # sembunyikan karang/lamun/ikan lain supaya bentuk varian terbaca
        hidden = []
        for other in bpy.data.objects:
            if other.type != "MESH" or other is ob:
                continue
            if other.name == "ENV_dense_seabed" or other.hide_render:
                continue
            other.hide_render = True
            hidden.append(other)
        cam.location = cen + V((d * 1.15, -d * 1.95, d * 1.05))
        cam.data.lens = 50.0
        cam.rotation_euler = (cen - cam.location).to_track_quat("-Z", "Y").to_euler()
        scn.camera = cam
        scn.render.resolution_percentage = 50
        scn.render.filepath = os.path.join(
            STILLS, "reef-dense-v004_coral-%s.png" % kind)
        bpy.ops.render.render(write_still=True)
        for other in hidden:
            other.hide_render = False
        print("RENDER varian", kind, ob.name, "dim",
              tuple(round(v, 2) for v in ob.dimensions),
              os.path.exists(scn.render.filepath))
    cam.location, cam.rotation_euler, cam.data.lens = home
    scn.render.resolution_percentage = 100


def main():
    mod = load_v003()
    accent_pct = stage_corals(mod)
    mod.stage_seagrass_fish_finish()      # lamun, 3 sekolah, world, kamera, simpan
    scn = bpy.context.scene
    render_previews(scn, "reef-dense-v004")
    render_new_corals(scn)
    scn.render.resolution_percentage = 100
    scn.render.filepath = "//"
    mod.purge_libraries()
    drop_render_result()
    bpy.ops.wm.save_as_mainfile(filepath=OUT)
    size_mb = round(os.path.getsize(OUT) / 1048576.0, 2)

    corals = [o for o in bpy.data.objects
              if o.name.startswith("ENV_dense_coral_")]
    types = sorted({o.get("coral_type", "?") for o in corals})
    print("=== RINGKASAN ===")
    print("karang", len(corals), "| tipe", len(types), types)
    for name in ("cakalang", "kakatua", "damselfish"):
        coll = bpy.data.collections.get("ENV_school_" + name)
        if coll:
            print("  sekolah", name,
                  len([o for o in coll.objects if o.type == "MESH"]), "ikan")
    print("aksen oranye %.2f%%" % accent_pct)
    print("objek", len(bpy.data.objects),
          "| vert unik", sum(len(m.vertices) for m in bpy.data.meshes))
    print("images", [i.name for i in bpy.data.images])
    print("libraries", [l.filepath for l in bpy.data.libraries])
    print("engine", scn.render.engine, "vt", scn.view_settings.view_transform,
          "res", scn.render.resolution_x, scn.render.resolution_y,
          "fps", scn.render.fps)
    log("MODEL - reef-dense_v004.blend disimpan (%.2f MB, %d karang, %d tipe, "
        "aksen %.2f%%)" % (size_mb, len(corals), len(types), accent_pct))
    print("SELESAI", OUT, size_mb, "MB")


if __name__ == "__main__":
    main()

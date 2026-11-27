"""Build assets/env/reef-dense_v005.blend — titik selam padat Scene 1/4.

v005 (27 Nov 2026) — tiga keluhan Director diperbaiki:

  1. **Aksen oranye jadi bintik.** v004 mewarnai muka secara acak/dipilih per
     face, jadi tiap ujung cabang tampak seperti polka dot. v005 menggantinya
     dengan **gradien jarak geodesik dari pangkal ke ujung cabang**:
     bobot 0,0 di pangkal, 1,0 di ujung, disimpan sebagai vertex group
     `GRP_coral-tip` **dan** point attribute `tip_weight` (shader Blender tidak
     bisa membaca deform layer, jadi attribute memakai bobot yang sama persis)
     lalu ColorRamp → Mix dengan oranye palette #E4713C. Tidak ada lagi
     material slot kedua per face. Target luas oranye **3–5 %**.
  2. **Lamun kaku.** Bilah lurus 2 segmen diganti **pita melengkung** 4 segmen
     (5 ring), lebar pangkal 2–4 cm menyempit ke ujung, tinggi 0,15–0,45 m,
     ujung melengkung 15–30°, warna hijau bervariasi 4 tone (turunan hijau
     terumbu palette).
  3. **Karang meja kebesaran.** Diameter meja dibatasi **1,2 m** (v004 sampai
     3,07 m — lebih lebar dari tubuh Nara); karang lain maks **1,6 m**.

Tetap: 140 karang 7 tipe, 600 rumpun lamun, 3 sekolah ikan (mesh v004),
pasir 26 x 26 m, 12 klaster, world/kamera/setelan v004.

Skrip membuka `reef-dense_v004.blend` (file proyek sendiri, bukan
open_mainfile sembarang), mengubah yang perlu, lalu menyimpan versi baru —
v004 tidak ditimpa. Jalankan headless:

    blender -b --python scripts/build-reef-dense-v005.py
"""
import bpy
import bmesh
import heapq
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
V004 = os.path.join(ENV_DIR, "reef-dense_v004.blend")
OUT = os.path.join(ENV_DIR, "reef-dense_v005.blend")
STILLS = os.path.join(ROOT, "renders", "stills")
LOG = os.path.join(ROOT, "renders", "logs", "modeling.log")
V004_SCRIPT = os.path.join(ROOT, "scripts", "build-reef-dense-v004.py")

SEED = 20261127
SEAGRASS_CLUMPS = 600
SEAGRASS_H_MIN, SEAGRASS_H_MAX = 0.15, 0.45
TABLE_MAX_DIA = 1.20             # m
CORAL_MAX_DIA = 1.60             # m

TIP_GROUP = "GRP_coral-tip"
TIP_ATTR = "tip_weight"

# mesh karang -> (cara bobot, target fraksi luas oranye per mesh)
ACCENT_PLAN = {
    "ENV_dense_coral_branching-hi": ("branch", 0.070),
    "ENV_dense_coral_branching-b_hi": ("branch", 0.060),
    "ENV_dense_coral_boulder": ("none", 0.0),
    "ENV_dense_coral_table-merged": ("radial", 0.080),
    "ENV_dense_coral_brain": ("none", 0.0),
    "ENV_dense_coral_tube": ("branch", 0.100),
    "ENV_dense_coral_mushroom": ("radial", 0.100),
}

SG_TONES = ("MAT_dense_seagrass", "MAT_dense_seagrass-dark",
            "MAT_dense_seagrass-light", "MAT_dense_seagrass-deep")


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
    """Helper v003: srgb, make_mat/make_mottle, mesh_bounds, seabed_z, purge."""
    spec = importlib.util.spec_from_file_location("reef_dense_v003", os.path.join(
        ROOT, "scripts", "build-reef-dense-v003.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ------------------------------------------------------------------ bobot ujung
def mesh_components(me):
    adj = [[] for _ in me.vertices]
    for e in me.edges:
        a, b = e.vertices
        adj[a].append(b)
        adj[b].append(a)
    seen = [False] * len(me.vertices)
    comps = []
    for i in range(len(me.vertices)):
        if seen[i]:
            continue
        seen[i] = True
        stack = [i]
        comp = []
        while stack:
            v = stack.pop()
            comp.append(v)
            for n in adj[v]:
                if not seen[n]:
                    seen[n] = True
                    stack.append(n)
        comps.append(comp)
    return comps, adj


def geodesic(adj, roots):
    dist = [float("inf")] * len(adj)
    heap = []
    for r in roots:
        dist[r] = 0.0
        heap.append((0.0, r))
    heapq.heapify(heap)
    while heap:
        d, v = heapq.heappop(heap)
        if d > dist[v] + 1e-12:
            continue
        for n in adj[v]:
            # bobot edge: pakai jarak 3D supaya cabang panjang = bobot turun lambat
            nd = d + 1.0
            if nd < dist[n]:
                dist[n] = nd
                heapq.heappush(heap, (nd, n))
    return dist


def weights_branch(me):
    """0 di pangkal tiap cabang, 1 di ujungnya — per komponen (cabang)."""
    comps, adj = mesh_components(me)
    w = [0.0] * len(me.vertices)
    for comp in comps:
        zmin = min(me.vertices[i].co.z for i in comp)
        zmax = max(me.vertices[i].co.z for i in comp)
        span = max(zmax - zmin, 1e-6)
        roots = [i for i in comp if me.vertices[i].co.z <= zmin + 0.18 * span]
        if not roots:
            roots = [min(comp, key=lambda i: me.vertices[i].co.z)]
        d = geodesic(adj, roots)
        dmax = max((d[i] for i in comp if d[i] < float("inf")), default=0.0)
        if dmax <= 1e-9:
            continue
        for i in comp:
            if d[i] < float("inf"):
                w[i] = min(1.0, d[i] / dmax)
    return w


def weights_radial(me):
    """0 di sumbu tengah (pangkal), 1 di tepi cakram/meja."""
    xs = [v.co.x for v in me.vertices]
    ys = [v.co.y for v in me.vertices]
    cx, cy = (min(xs) + max(xs)) * 0.5, (min(ys) + max(ys)) * 0.5
    rmax = max(math.hypot(v.co.x - cx, v.co.y - cy) for v in me.vertices)
    if rmax <= 1e-9:
        return [0.0] * len(me.vertices)
    return [min(1.0, math.hypot(v.co.x - cx, v.co.y - cy) / rmax)
            for v in me.vertices]


def store_tip_weights(me, weights):
    if TIP_ATTR in me.attributes:
        me.attributes.remove(me.attributes[TIP_ATTR])
    attr = me.attributes.new(TIP_ATTR, "FLOAT", "POINT")
    attr.data.foreach_set("value", weights)
    me.update()


def face_weights(me, weights):
    return [sum(weights[v] for v in p.vertices) / len(p.vertices)
            for p in me.polygons]


def threshold_for_fraction(fw, areas, target):
    """Ambang bobot m sehingga luas muka dengan w >= m == target * total."""
    total = sum(areas)
    if total <= 0.0 or target <= 0.0:
        return 1.0
    target = min(target, 0.999)
    pairs = sorted(zip(fw, areas), key=lambda t: t[0])
    acc = 0.0
    cut = total * target
    for w, a in reversed(pairs):
        acc += a
        if acc >= cut:
            return w
    return 0.0


# ------------------------------------------------------------------- material
def socket(node, name, stype):
    for s in node.inputs:
        if s.name == name and s.type == stype:
            return s
    raise RuntimeError("socket %s/%s tidak ada di %s" % (name, stype, node.bl_idname))


def gradient_material(base_mat, orange_rgba, ramp_start, name):
    """Salin material dasar, sisipkan Attribute(tip_weight) -> ColorRamp -> Mix."""
    mat = base_mat.copy()
    mat.name = name
    nt = mat.node_tree
    nodes, links = nt.nodes, nt.links
    bsdf = next(n for n in nodes if n.type == "BSDF_PRINCIPLED")
    base_in = bsdf.inputs["Base Color"]
    src = base_in.links[0].from_socket if base_in.is_linked else None

    attr = nodes.new("ShaderNodeAttribute")
    attr.attribute_type = "GEOMETRY"
    attr.attribute_name = TIP_ATTR
    attr.location = (-900, -260)

    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.location = (-680, -260)
    ramp.color_ramp.interpolation = "EASE"
    ramp.color_ramp.elements[0].position = max(0.0, min(0.97, ramp_start))
    ramp.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)
    ramp.color_ramp.elements[1].position = 1.0
    ramp.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1.0)

    mix = nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.blend_type = "MIX"
    mix.location = (-420, 40)
    socket(mix, "B", "RGBA").default_value = orange_rgba

    links.new(attr.outputs["Fac"], ramp.inputs["Fac"])
    out_rgba = next(o for o in mix.outputs if o.type == "RGBA")
    links.new(ramp.outputs["Color"], mix.inputs["Factor"])
    if src is not None:
        links.new(src, socket(mix, "A", "RGBA"))
    else:
        socket(mix, "A", "RGBA").default_value = base_in.default_value
    links.new(out_rgba, base_in)
    mat["accent_ramp_start"] = ramp.color_ramp.elements[0].position
    return mat


def orange_rgba(v3):
    return v3.srgb("#E4713C")


# ------------------------------------------------------------------- lamun baru
def build_seagrass_mesh(v3, rng, coral_positions):
    """600 rumpun, bilah pita melengkung 4 segmen, ujung melengkung."""
    bm = bmesh.new()
    mats = []
    for nm in SG_TONES:
        m = bpy.data.materials.get(nm)
        if m is None:
            if nm.endswith("-light"):
                m = v3.make_mat(nm, "#4E9E7A", rough=0.9)
            elif nm.endswith("-deep"):
                m = v3.make_mat(nm, "#2C6455", rough=0.9)
            elif nm.endswith("-dark"):
                m = v3.make_mat(nm, "#35775C", rough=0.9)
            else:
                m = v3.make_mat(nm, "#3E8E6E", rough=0.9)
        mats.append(m)
    tone_weights = (0.40, 0.16, 0.34, 0.10)   # base, gelap, terang, paling gelap

    def pick_tone():
        r = rng.random()
        acc = 0.0
        for i, w in enumerate(tone_weights):
            acc += w
            if r <= acc:
                return i
        return 0

    base = v3.seabed_z
    clumps = 0
    tries = 0
    blades = 0
    heights = []
    while clumps < SEAGRASS_CLUMPS and tries < 60000:
        tries += 1
        x = rng.uniform(-v3.AREA_HALF - 0.5, v3.AREA_HALF + 0.5)
        y = rng.uniform(-v3.AREA_HALF - 0.5, v3.AREA_HALF + 0.5)
        if any(math.hypot(x - cx, y - cy) < 0.30 + cr
               for cx, cy, cr in coral_positions):
            continue
        z0 = base(x, y) - 0.02
        n_blades = rng.randint(10, 14)
        for _b in range(n_blades):
            bx = x + rng.uniform(-0.20, 0.20)
            by = y + rng.uniform(-0.20, 0.20)
            bz = base(bx, by) - 0.02
            hgt = rng.uniform(SEAGRASS_H_MIN, SEAGRASS_H_MAX)
            half_w = rng.uniform(0.010, 0.020)       # lebar total 2-4 cm
            az = rng.uniform(0.0, math.tau)
            bend = math.radians(rng.uniform(6.0, 26.0))
            curl = math.radians(rng.uniform(15.0, 30.0))
            mi = pick_tone()
            STEPS = 4
            seg = hgt / STEPS
            pts = [Vector((bx, by, bz))]
            p = pts[0].copy()
            for i in range(1, STEPS + 1):
                t = i / STEPS
                ang = bend * (t ** 1.55) + curl * max(0.0, (t - 0.70) / 0.30) ** 1.5
                step = Vector((math.cos(az) * math.sin(ang),
                               math.sin(az) * math.sin(ang),
                               math.cos(ang))) * seg
                p = p + step
                pts.append(p.copy())
            axis = Vector((-math.sin(az), math.cos(az), 0.0))
            prev = None
            for i in range(STEPS + 1):
                t = i / STEPS
                w = half_w * (1.0 - 0.25 * t)
                a = bm.verts.new(pts[i] - axis * w)
                b = bm.verts.new(pts[i] + axis * w)
                cur = (a, b)
                if prev is not None:
                    try:
                        f = bm.faces.new((prev[0], prev[1], cur[1], cur[0]))
                        f.material_index = mi
                    except ValueError:
                        pass
                prev = cur
            blades += 1
            heights.append(hgt)
        clumps += 1

    me = bpy.data.meshes.new("ENV_dense_seagrass")
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    for p in me.polygons:
        p.use_smooth = True
    print("lamun baru: %d rumpun, %d bilah, %d vert, tinggi %.2f-%.2f m, lebar 2-4 cm"
          % (clumps, blades, len(me.vertices), min(heights), max(heights)))
    return me, clumps, blades, (min(heights), max(heights))


# ----------------------------------------------------------------------- kamar
def add_camera(scene, name, loc, target, lens, clip_start=0.05):
    data = bpy.data.cameras.new(name)
    data.lens = lens
    data.clip_start = clip_start
    data.clip_end = 300.0
    cam = bpy.data.objects.new(name, data)
    scene.collection.objects.link(cam)
    cam.location = loc
    cam.rotation_euler = ((Vector(target) - Vector(loc))
                          .to_track_quat("-Z", "Y").to_euler())
    return cam


def coral_weights(me, mode):
    if mode == "branch":
        return weights_branch(me)
    if mode == "radial":
        return weights_radial(me)
    return [0.0] * len(me.vertices)


def subdivide_mesh(me, cuts=2):
    """Tambah kerapatan ring supaya gradien tepi meja bisa tipis & halus."""
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.subdivide_edges(bm, edges=list(bm.edges), cuts=cuts,
                              use_grid_fill=True)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    me.update()


def compute_weight_data(base_mats):
    data = {}
    for name, (mode, frac) in ACCENT_PLAN.items():
        me = bpy.data.meshes.get(name)
        if me is None:
            continue
        weights = coral_weights(me, mode)
        store_tip_weights(me, weights)
        data[name] = dict(
            me=me, weights=weights, frac=frac, base=base_mats.get(name),
            fw=face_weights(me, weights),
            areas=[p.area for p in me.polygons],
            total=sum(p.area for p in me.polygons))
    return data


def apply_k(root, data, k):
    """Pilih ambang ColorRamp per mesh untuk target frac * k, ukur luas nyata."""
    for d in data.values():
        target = d["frac"] * k
        if target > 0.0 and d["total"] > 0.0:
            m = threshold_for_fraction(d["fw"], d["areas"], target)
            ramp_start = max(0.0, min(0.97, 2.0 * m - 1.0))
        else:
            ramp_start = 1.0
        cut = (ramp_start + 1.0) * 0.5
        d["ramp_start"] = ramp_start
        d["actual"] = sum(a for a, w in zip(d["areas"], d["fw"]) if w >= cut) \
            / max(d["total"], 1e-9)
    return measure_accent(root, data)


def measure_accent(root, data):
    total_i = 0.0
    acc_i = 0.0
    for ob in root.objects:
        if ob.type != "MESH":
            continue
        d = data.get(ob.data.name)
        if d is None:
            continue
        sc = max(ob.scale) ** 2
        total_i += d["total"] * sc
        acc_i += d.get("actual", 0.0) * d["total"] * sc
    return 100.0 * acc_i / max(total_i, 1e-9)


def apply_accent_materials(data, v3):
    for name, d in data.items():
        me = bpy.data.meshes[name]
        base = d["base"]
        if base is None:
            continue
        gname = "MAT_grad_" + name.replace("ENV_dense_coral_", "coral-") + "_v005"
        mat = bpy.data.materials.get(gname)
        if mat is None:
            mat = gradient_material(base, orange_rgba(v3), d["ramp_start"], gname)
        else:
            ramp = next(n for n in mat.node_tree.nodes if n.type == "VALTORGB")
            ramp.color_ramp.elements[0].position = d["ramp_start"]
            mat["accent_ramp_start"] = d["ramp_start"]
        me.materials.clear()
        me.materials.append(mat)
        for p in me.polygons:
            p.material_index = 0


def assign_tip_groups(root):
    n = 0
    for ob in root.objects:
        if ob.type != "MESH" or not ob.name.startswith("ENV_dense_coral_"):
            continue
        me = ob.data
        if TIP_ATTR not in me.attributes:
            continue
        vals = [0.0] * len(me.vertices)
        me.attributes[TIP_ATTR].data.foreach_get("value", vals)
        vg = ob.vertex_groups.get(TIP_GROUP)
        if vg is None:
            vg = ob.vertex_groups.new(name=TIP_GROUP)
        buckets = {}
        for i, w in enumerate(vals):
            buckets.setdefault(round(w, 2), []).append(i)
        for w, idx in buckets.items():
            vg.add(idx, w, "REPLACE")
        n += 1
    return n


def cap_coral_scales():
    tables, others = [], []
    for ob in bpy.data.objects:
        kind = ob.get("coral_type")
        if not kind or ob.type != "MESH":
            continue
        dia = max(ob.dimensions.x, ob.dimensions.y)
        (tables if kind == "table" else others).append((ob, dia))
    for ob, dia in tables:
        s_old = max(ob.scale)
        base_dia = max(dia / max(s_old, 1e-6), 1e-6)
        t = max(0.0, min(1.0, (s_old - 0.65) / (1.60 - 0.65)))
        s_new = 0.40 + t * (TABLE_MAX_DIA / base_dia - 0.40)
        s_new = min(s_new, TABLE_MAX_DIA / base_dia)
        ob.scale = (s_new, s_new, s_new)
    capped = 0
    for ob, dia in others:
        if dia > CORAL_MAX_DIA:
            f = CORAL_MAX_DIA / dia
            ob.scale = tuple(s * f for s in ob.scale)
            capped += 1
    bpy.context.view_layer.update()
    t_dias = sorted(round(max(o.dimensions.x, o.dimensions.y), 2) for o, _ in tables)
    all_dias = sorted(round(max(o.dimensions.x, o.dimensions.y), 2)
                      for o, _ in tables + others)
    return len(tables), t_dias, all_dias, capped


def rebuild_branch_mesh(v3, scene, src_name, new_name, decimate, base_mat):
    """Evaluasi ulang mesh cabang dari reef.blend dengan decimate lebih ringan."""
    tmp = bpy.data.collections.new("TMP_rebuild")
    scene.collection.children.link(tmp)
    objs = v3.append_objects(v3.REEF, [src_name])
    if not objs:
        bpy.data.collections.remove(tmp)
        raise RuntimeError("sumber tidak ada di reef.blend: " + src_name)
    for o in objs:
        v3.own(o, tmp)
    me = v3.eval_mesh(objs[0], new_name, tmp, decimate=decimate)
    for o in list(tmp.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.data.collections.remove(tmp)
    me.materials.clear()
    if base_mat is not None:
        me.materials.append(base_mat)
    return me


def main():
    v3 = load_v003()
    rng = random.Random(SEED)

    print("buka", V004)
    bpy.ops.wm.open_mainfile(filepath=V004)
    scn = bpy.context.scene
    root = bpy.data.collections.get("ENV_reef-dense")
    ctl = bpy.data.objects.get("CTL_reef-dense")
    if root is None or ctl is None:
        raise RuntimeError("koleksi reef-dense tidak ada di v004")
    log("PLAN - reef-dense_v005: aksen gradien ujung cabang, lamun pita melengkung, "
        "meja maks 1,2 m (v004: bintik per-face, lamun kaku, meja 3,07 m)")

    # ---------------------------- 0. mesh cabang lebih halus (gradien ujung)
    old_branch = bpy.data.meshes.get("ENV_dense_coral_branching")
    old_branch_b = bpy.data.meshes.get("ENV_dense_coral_branching-b")
    base_branch = (old_branch.materials[0]
                   if old_branch is not None and old_branch.materials else None)
    new_branch = rebuild_branch_mesh(v3, scn, "ENV_reef_branching-coral",
                                     "ENV_dense_coral_branching-hi", 0.85, base_branch)
    new_branch_b = rebuild_branch_mesh(v3, scn, "ENV_reef_branching-coral_b",
                                       "ENV_dense_coral_branching-b_hi", 0.80, base_branch)
    swapped = 0
    for ob in root.objects:
        if ob.type != "MESH":
            continue
        kind = ob.get("coral_type")
        if kind == "branch":
            ob.data = new_branch
            swapped += 1
        elif kind == "branch_b":
            ob.data = new_branch_b
            swapped += 1
    for me in (old_branch, old_branch_b):
        if me is not None and me.users == 0:
            bpy.data.meshes.remove(me)
    print("mesh cabang dirapikan: %d vert / %d vert, %d instans dipasang ulang"
          % (len(new_branch.vertices), len(new_branch_b.vertices), swapped))
    log("MODEL - mesh cabang dinaikkan resolusinya (decimate 0,28->0,85 dan 0,5->0,8) "
        "supaya gradien ujung tidak pecah jadi facet")

    base_mats = {}
    for name in ACCENT_PLAN:
        me = bpy.data.meshes.get(name)
        if me is not None and me.materials:
            base_mats[name] = me.materials[0]

    # ------------------------------------------------- 1. ukuran karang dibatasi
    n_tab, t_dias, all_dias, capped = cap_coral_scales()
    print("meja %d: diameter %.2f-%.2f m (target <= %.2f) | semua karang maks %.2f m "
          "(target <= %.2f), %d objek lain diturunkan"
          % (n_tab, t_dias[0], t_dias[-1], TABLE_MAX_DIA, all_dias[-1],
             CORAL_MAX_DIA, capped))
    log("MODEL - karang meja: diameter dibatasi %.2f m (v004 maks 3,07 m); "
        "semua karang maks %.2f m" % (t_dias[-1], all_dias[-1]))

    # --------------------------------------------- 2. aksen gradien ujung cabang
    for nm in ("ENV_dense_coral_table-merged", "ENV_dense_coral_mushroom"):
        me = bpy.data.meshes.get(nm)
        if me is None:
            continue
        before = len(me.vertices)
        subdivide_mesh(me, 2)
        print("subdivide %-28s %d -> %d vert (gradien tepi meja lebih halus)"
              % (nm, before, len(me.vertices)))

    data = compute_weight_data(base_mats)
    best = None
    for k in (1.0, 0.85, 0.7, 0.55, 0.45, 0.35, 0.25, 1.2, 1.4):
        pct = apply_k(root, data, k)
        print("  uji k %.2f -> aksen nyata %.2f%%" % (k, pct))
        if best is None or abs(pct - 4.0) < abs(best[1] - 4.0):
            best = (k, pct)
    accent_pct = apply_k(root, data, best[0])
    print("kalibrasi aksen: k=%.2f -> %.2f%% (target 3-5%%)" % (best[0], accent_pct))
    apply_accent_materials(data, v3)
    n_vg = assign_tip_groups(root)
    print("vertex group %s di %d objek karang (bobot = attribute %s)"
          % (TIP_GROUP, n_vg, TIP_ATTR))

    for name, d in data.items():
        me = bpy.data.meshes[name]
        print("mesh %-32s v %5d  aksen nyata %5.1f%%  ramp %.2f  %s"
              % (name, len(me.vertices), 100.0 * d["actual"],
                 d["ramp_start"], [m.name for m in me.materials]))

    # -------------------------------------------------------- 3. lamun baru
    old = bpy.data.objects.get("ENV_dense_seagrass")
    old_me = old.data if old is not None else None
    if old is not None:
        bpy.data.objects.remove(old, do_unlink=True)
    if old_me is not None and old_me.users == 0:
        bpy.data.meshes.remove(old_me)

    coral_pos = [(ob.location.x, ob.location.y, max(ob.scale) * 0.35)
                 for ob in root.objects
                 if ob.type == "MESH" and ob.name.startswith("ENV_dense_coral_")]
    sg_me, clumps, blades, (hmin, hmax) = build_seagrass_mesh(v3, rng, coral_pos)
    sg = bpy.data.objects.new("ENV_dense_seagrass", sg_me)
    root.objects.link(sg)
    sg.parent = ctl
    log("MODEL - lamun: %d rumpun, %d bilah pita melengkung 4 segmen, lebar pangkal 2-4 cm, "
        "tinggi %.2f-%.2f m, ujung melengkung 15-30 derajat, 4 tone hijau"
        % (clumps, blades, hmin, hmax))

    # ---------------------------------------------------------------- kamera
    cam_tip = bpy.data.objects.get("CAM_dense_tip")
    target_ob = None
    for ob in bpy.data.objects:
        if ob.get("coral_type") == "branch":
            target_ob = ob
            break
    if target_ob is not None:
        cos = [target_ob.matrix_world @ Vector(c) for c in target_ob.bound_box]
        cen = sum(cos, Vector((0, 0, 0))) / 8.0
        d = max(target_ob.dimensions)
        aim = cen + Vector((0.0, 0.0, 0.30 * d))
        loc = cen + Vector((0.92 * d, -1.38 * d, 0.16 * d))
        if cam_tip is None:
            cam_tip = add_camera(scn, "CAM_dense_tip", loc, aim, 50.0)
        else:
            cam_tip.location = loc
            cam_tip.data.lens = 50.0
            cam_tip.rotation_euler = (aim - loc).to_track_quat("-Z", "Y").to_euler()

    # ---------------------------------------------------------------- render
    bpy.context.view_layer.update()
    cam_a = bpy.data.objects.get("CAM_dense_01")
    cam_b = bpy.data.objects.get("CAM_dense_02")
    if cam_a is None or cam_b is None:
        raise RuntimeError("kamera CAM_dense_01/02 tidak ada")
    os.makedirs(STILLS, exist_ok=True)
    scn.render.resolution_percentage = 50

    def shot(cam, path):
        scn.camera = cam
        scn.render.filepath = path
        bpy.ops.render.render(write_still=True)
        print("RENDER", path, os.path.exists(path))

    shot(cam_a, os.path.join(STILLS, "reef-dense-v005_preview-01.png"))
    shot(cam_b, os.path.join(STILLS, "reef-dense-v005_preview-02.png"))

    if cam_tip is not None and target_ob is not None:
        hidden = []
        for other in bpy.data.objects:
            if other.type != "MESH" or other is target_ob:
                continue
            if other.name == "ENV_dense_seabed":
                continue
            other.hide_render = True
            hidden.append(other)
        shot(cam_tip, os.path.join(STILLS, "reef-dense-v005_ujung-cabang.png"))
        for other in hidden:
            other.hide_render = False
        print("close-up ujung cabang:", target_ob.name,
              tuple(round(v, 2) for v in target_ob.dimensions))

    # bukti tambahan: bentuk pita lamun (bukan bilah lurus)
    cam_sg = bpy.data.objects.get("CAM_dense_lamun")
    z0 = v3.seabed_z(0.0, 0.4)
    loc = Vector((-1.55, -0.95, z0 + 0.52))
    aim = Vector((0.25, 0.55, z0 + 0.16))
    if cam_sg is None:
        cam_sg = add_camera(scn, "CAM_dense_lamun", loc, aim, 55.0)
    else:
        cam_sg.location = loc
        cam_sg.rotation_euler = (aim - loc).to_track_quat("-Z", "Y").to_euler()
    hidden = []
    for other in bpy.data.objects:
        if other.type != "MESH" or other.name in ("ENV_dense_seagrass",
                                                  "ENV_dense_seabed"):
            continue
        other.hide_render = True
        hidden.append(other)
    shot(cam_sg, os.path.join(STILLS, "reef-dense-v005_lamun.png"))
    for other in hidden:
        other.hide_render = False
    log("VERIFY - reef-dense_v005: render 50% 2 sudut bawah laut + close-up ujung cabang")

    # ----------------------------------------------------------------- simpan
    scn.camera = cam_a
    scn.render.resolution_percentage = 100
    scn.render.filepath = "//"
    for img in list(bpy.data.images):
        if img.type == "RENDER_RESULT":
            try:
                bpy.data.images.remove(img)
            except Exception:
                pass
    v3.purge_libraries()
    bpy.ops.wm.save_as_mainfile(filepath=OUT)
    size_mb = round(os.path.getsize(OUT) / 1048576.0, 2)

    corals = [o for o in bpy.data.objects if o.name.startswith("ENV_dense_coral_")]
    types = sorted({o.get("coral_type", "?") for o in corals})
    print("=== RINGKASAN reef-dense_v005 ===")
    print("karang", len(corals), "| tipe", len(types), types)
    print("lamun bilah", blades, "| tinggi", round(hmin, 2), "-", round(hmax, 2))
    print("aksen oranye %.2f%% (target 3-5%%)" % accent_pct)
    print("objek", len(bpy.data.objects), "| vert unik",
          sum(len(m.vertices) for m in bpy.data.meshes))
    print("images", [i.name for i in bpy.data.images],
          "| libraries", [l.filepath for l in bpy.data.libraries])
    print("engine", scn.render.engine, "vt", scn.view_settings.view_transform,
          "res", scn.render.resolution_x, scn.render.resolution_y,
          "fps", scn.render.fps, "frame", scn.frame_current)
    log("MODEL - reef-dense_v005.blend disimpan (%.2f MB, %d karang, %d tipe, "
        "aksen gradien %.2f%%, lamun %d bilah melengkung, meja <= %.2f m)"
        % (size_mb, len(corals), len(types), accent_pct, blades, t_dias[-1]))
    print("SELESAI", OUT, size_mb, "MB")


if __name__ == "__main__":
    main()

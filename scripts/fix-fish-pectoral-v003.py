"""Perbaiki bobot sirip dada ikan — versi `_v003` (tiga file).

Masalah v002: gradient bobot hanya diberikan ke verteks sirip yang **saat itu**
punya bobot pectoral > 0,5. Akibatnya sebagian verteks sirip (pangkal, bibir
piring) tetap kaku/ikut badan saja — sirip tidak terdeformasi sebagai satu
kesatuan.

v003 (25 Nov 2026):
  1. **Semua** verteks sirip dada didaftar lebih dulu, bukan hanya yang
     berbobot > 0,5:
       - kakatua & damselfish: blok verteks `pect_L` / `pect_R` dihitung ulang
         dengan memutar ulang fungsi pembangun mesh (deterministik, sama
         persis dengan `scripts/build-fish-kakatua.py` / `-damselfish.py`),
         lalu diverifikasi jumlah verteks mesh == hasil hitung ulang.
       - cakalang: objek `ENV_fish_cakalang_pectoral` berisi sirip dada +
         perut + anal; sirip dada dipilih dari benih |x| > 0,04 lalu
         di-flood-fill sepanjang edge supaya akar piring ikut (sirip perut &
         anal tetap utuh, bukan pulau mesh yang sama).
  2. Setiap verteks sirip diberi **campuran** `pectoral_L/R` + `spine_02`
     dengan gradien pangkal 0,20 -> ujung 0,90 (parameter: jarak radial dari
     kepala bone pectoral), dihaluskan 2 iterasi, dijepit 0,20–0,90, lalu
     dinormalkan. Tidak ada verteks sirip yang 100 % satu bone.
  3. Grup lain di verteks sirip dibuang; verteks di luar sirip tidak disentuh.
     Action renang tidak diubah.

Verifikasi (headless): jumlah verteks sirip yang dibobot ulang, persentase yang
memakai dua grup, panjang tepi berubah (tanda berdeformasi, bukan piringan
kaku), dan **perpindahan ujung sirip antara frame 6 dan 18** (target > 5 mm).

Keluaran:
    assets/env/fish-kakatua_v003.blend
    assets/env/fish-damselfish_v003.blend
    assets/env/fish-cakalang-rig_v003.blend
    renders/stills/<aset>-v003_preview-01.png   (frame 6)
    renders/stills/<aset>-v003_preview-02.png   (frame 18)

Setelan: EEVEE, 1920x1080, 24 fps, Standard, frame 1, tanpa pack, idempoten.

    blender -b -P scripts/fix-fish-pectoral-v003.py
"""
import bpy
import importlib.util
import os
import time

from mathutils import Vector

try:
    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
except NameError:
    ROOT = r"D:\Tugas Semester 5\Grafika Komputer\Project-Animasi"

ENV_DIR = os.path.join(ROOT, "assets", "env")
SCRIPTS = os.path.join(ROOT, "scripts")
WIPE = os.path.join(ROOT, "renders", "tmp", "_wipe.blend")
STILLS = os.path.join(ROOT, "renders", "stills")
LOG = os.path.join(ROOT, "renders", "logs", "modeling.log")

F_A, F_B = 6, 18
W_MIN, W_MAX = 0.20, 0.90      # pangkal -> ujung (campuran pectoral + spine_02)
TIP_MIN_MM = 5.0

# (sumber v002, keluaran v003, nama armature, modul pembangun mesh)
FILES = [
    ("fish-kakatua_v002.blend", "fish-kakatua_v003.blend",
     "CHR_fish_kakatua_rig", "build-fish-kakatua.py", "ENV_fish_kakatua"),
    ("fish-damselfish_v002.blend", "fish-damselfish_v003.blend",
     "CHR_fish_damselfish_rig", "build-fish-damselfish.py", "ENV_fish_damselfish"),
    ("fish-cakalang-rig_v002.blend", "fish-cakalang-rig_v003.blend",
     "CHR_cakalang_rig", None, "ENV_fish_cakalang_pectoral"),
]

BUILD_ORDER = ("body", "eyes", "dorsal", "anal", "pelvic", "pect_L", "pect_R",
               "caudal")


def log(line):
    stamp = time.strftime("%H:%M")
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as fh:
            fh.write("[%s] %s\n" % (stamp, line))
    except Exception as err:  # pragma: no cover
        print("peringatan log:", err)
    print("[%s] %s" % (stamp, line))


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
    for img in list(bpy.data.images):
        if img.type == "RENDER_RESULT":
            try:
                bpy.data.images.remove(img)
            except Exception as err:
                print("peringatan render result:", err)


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def replay_ranges(script_name):
    """Hitung ulang rentang verteks tiap bagian mesh (deterministik)."""
    mod = load_module(os.path.join(SCRIPTS, script_name),
                      "replay_" + script_name.replace("-", "_")[:-3])
    V, F, FM, FS = [], [], [], []
    ranges = {}
    for key in BUILD_ORDER:
        v0 = len(V)
        if key == "pect_L":
            mod.build_pectoral(1.0, V, F, FM, FS)
        elif key == "pect_R":
            mod.build_pectoral(-1.0, V, F, FM, FS)
        else:
            getattr(mod, "build_" + key)(V, F, FM, FS)
        ranges[key] = (v0, len(V))
    return ranges, len(V)


def flood_fill(mesh, seeds):
    """Tambah verteks yang terhubung lewat edge ke benih (satu pulau mesh)."""
    adj = {}
    for e in mesh.edges:
        a, b = e.vertices
        adj.setdefault(a, []).append(b)
        adj.setdefault(b, []).append(a)
    out = set(seeds)
    stack = list(seeds)
    while stack:
        i = stack.pop()
        for j in adj.get(i, ()):
            if j not in out:
                out.add(j)
                stack.append(j)
    return out


def fin_sets(mesh_obj, own_mesh, ranges):
    """Kembalikan {side: set(indeks verteks sirip dada)}."""
    mesh = mesh_obj.data
    if ranges is not None:                       # kakatua & damselfish
        return {
            "L": set(range(*ranges["pect_L"])),
            "R": set(range(*ranges["pect_R"])),
        }
    seeds = {"L": set(), "R": set()}
    for v in mesh.vertices:
        if v.co.x > 0.040:
            seeds["L"].add(v.index)
        elif v.co.x < -0.040:
            seeds["R"].add(v.index)
    out = {}
    for side in ("L", "R"):
        out[side] = flood_fill(mesh, seeds[side]) if seeds[side] else set()
    return out


def bone_frame(arm, bone_name):
    bone = arm.data.bones[bone_name]
    head = bone.head_local.copy()
    return head


def reweight(mesh_obj, arm, side, idx):
    """Campuran pectoral_<side> + spine_02 untuk SEMUA verteks sirip."""
    bone = "pectoral_%s" % side
    head = bone_frame(arm, bone)
    mw = mesh_obj.matrix_world
    aw = arm.matrix_world.inverted()
    dist = {}
    for i in idx:
        co = aw @ (mw @ mesh_obj.data.vertices[i].co)
        dist[i] = (co - head).length
    dmax, dmin = max(dist.values()), min(dist.values())
    span = max(dmax - dmin, 1e-6)
    t = {i: (dist[i] - dmin) / span for i in idx}
    w = {i: W_MIN + (W_MAX - W_MIN) * (t[i] ** 0.85) for i in idx}
    # 2 iterasi penghalusan di dalam sirip
    adj = {i: set() for i in idx}
    for e in mesh_obj.data.edges:
        a, b = e.vertices
        if a in idx and b in idx:
            adj[a].add(b)
            adj[b].add(a)
    for _ in range(2):
        nw = {}
        for i in idx:
            nb = adj[i]
            avg = sum(w[j] for j in nb) / len(nb) if nb else w[i]
            nw[i] = 0.6 * w[i] + 0.4 * avg
        w = nw
    for i in idx:
        w[i] = min(W_MAX, max(W_MIN, w[i]))
    vg_p = mesh_obj.vertex_groups.get(bone) or mesh_obj.vertex_groups.new(name=bone)
    vg_s = (mesh_obj.vertex_groups.get("spine_02")
            or mesh_obj.vertex_groups.new(name="spine_02"))
    others = [g for g in mesh_obj.vertex_groups if g.name not in (bone, "spine_02")]
    idx_list = sorted(idx)
    for g in others:
        g.remove(idx_list)
    for i in idx_list:
        vg_p.add([i], w[i], "REPLACE")
        vg_s.add([i], 1.0 - w[i], "REPLACE")
    ordered = sorted(idx, key=lambda i: t[i])
    return {"n": len(idx), "w": w, "t": t,
            "base": ordered[0], "tip": ordered[-1],
            "wmin": min(w.values()), "wmax": max(w.values())}


def eval_coords(arm, mesh_obj, idx, frame):
    scn = bpy.context.scene
    scn.frame_set(frame)
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    ev = mesh_obj.evaluated_get(dg)
    me = ev.to_mesh()
    mw = ev.matrix_world
    co = {i: mw @ me.vertices[i].co.copy() for i in idx}
    ev.to_mesh_clear()
    pb = arm.pose.bones["spine_02"]
    m_rel = pb.matrix.inverted() @ arm.matrix_world.inverted()
    rel = {i: m_rel @ co[i] for i in idx}
    return co, rel


def measure(arm, mesh_obj, info, idx):
    idx = set(idx)
    edges = [(e.vertices[0], e.vertices[1]) for e in mesh_obj.data.edges
             if e.vertices[0] in idx and e.vertices[1] in idx]
    co_a, rel_a = eval_coords(arm, mesh_obj, idx, F_A)
    co_b, rel_b = eval_coords(arm, mesh_obj, idx, F_B)
    lens = []
    for a, b in edges:
        la = (co_a[a] - co_a[b]).length
        lb = (co_b[a] - co_b[b]).length
        if la > 1e-9:
            lens.append(abs(lb - la) / la)
    tip = info["tip"]
    return {
        "tip_world_mm": (co_b[tip] - co_a[tip]).length * 1000.0,
        "tip_rel_mm": (rel_b[tip] - rel_a[tip]).length * 1000.0,
        "edge_pct": 100.0 * sum(lens) / len(lens) if lens else 0.0,
    }


# ------------------------------------------------------------------- per file
def do_file(src_name, out_name, arm_name, build_script, mesh_name):
    SRC = os.path.join(ENV_DIR, src_name)
    OUT = os.path.join(ENV_DIR, out_name)
    scn = wipe()
    os.makedirs(os.path.dirname(WIPE), exist_ok=True)
    os.makedirs(STILLS, exist_ok=True)
    try:
        bpy.context.preferences.filepaths.save_version = 0
    except Exception:
        pass
    if bpy.data.filepath and os.path.abspath(bpy.data.filepath) != os.path.abspath(WIPE):
        bpy.ops.wm.save_as_mainfile(filepath=WIPE)
    scn.name = out_name.replace(".blend", "")

    with bpy.data.libraries.load(SRC, link=False) as (df, dt):
        src_cols = list(df.collections)
        src_objs = list(df.objects)
        dt.collections = src_cols
        dt.objects = src_objs
    for c in bpy.data.collections:
        if c.name not in [x.name for x in scn.collection.children]:
            scn.collection.children.link(c)

    arm = bpy.data.objects.get(arm_name)
    if arm is None:
        raise RuntimeError("%s: armature %s tidak ada" % (src_name, arm_name))
    act = arm.animation_data.action if arm.animation_data else None
    act_keys = 0
    if act is not None:
        try:
            for layer in act.layers:
                for strip in layer.strips:
                    for bag in getattr(strip, "channelbags", []):
                        act_keys += len(bag.fcurves)
        except AttributeError:
            act_keys = -1
    meshes = [o for o in bpy.data.objects if o.type == "MESH"
              and any(m.type == "ARMATURE" and m.object is arm for m in o.modifiers)]
    mesh_obj = bpy.data.objects.get(mesh_name)
    if mesh_obj is None:
        raise RuntimeError("%s: mesh %s tidak ada" % (src_name, mesh_name))
    print("==", src_name, "| arm", arm.name, "| bone", len(arm.data.bones),
          "| action", act.name if act else None, "| fcurve", act_keys,
          "| mesh", [m.name for m in meshes])

    ranges = None
    if build_script:
        ranges, replay_n = replay_ranges(build_script)
        if replay_n != len(mesh_obj.data.vertices):
            raise RuntimeError("%s: hitung ulang %d != mesh %d"
                               % (src_name, replay_n, len(mesh_obj.data.vertices)))
        print("rentang verteks dihitung ulang:", ranges)

    fins = fin_sets(mesh_obj, True, ranges)
    before = {}
    for side in ("L", "R"):
        idx = fins[side]
        if not idx:
            continue
        vg = mesh_obj.vertex_groups.get("pectoral_%s" % side)
        seed_half = 0
        if vg is not None:
            for i in idx:
                for g in mesh_obj.data.vertices[i].groups:
                    if g.group == vg.index and g.weight > 0.5:
                        seed_half += 1
                        break
        before[side] = (len(idx), seed_half)
        print("  sirip %s: %d verteks (v002 hanya %d yang bobot >0,5)"
              % (side, len(idx), seed_half))

    results = {}
    for side in ("L", "R"):
        idx = fins[side]
        if not idx:
            continue
        info = reweight(mesh_obj, arm, side, idx)
        met = measure(arm, mesh_obj, info, idx)
        results[side] = (info, met, before[side])
        print("%-24s %s n=%3d | bobot pectoral %.2f-%.2f | panjang tepi berubah "
              "%4.1f%% | ujung bergerak %.1f mm (relatif badan %.1f mm)"
              % (mesh_name, "pectoral_" + side, info["n"], info["wmin"],
                 info["wmax"], met["edge_pct"], met["tip_world_mm"],
                 met["tip_rel_mm"]))

    # cek cakupan: berapa verteks sirip yang memakai dua grup
    dual = 0
    total = 0
    for side in ("L", "R"):
        idx = fins[side]
        vg = mesh_obj.vertex_groups.get("pectoral_%s" % side)
        vg_s = mesh_obj.vertex_groups.get("spine_02")
        for i in idx:
            total += 1
            wp = ws = 0.0
            for g in mesh_obj.data.vertices[i].groups:
                if g.group == vg.index:
                    wp = g.weight
                elif g.group == vg_s.index:
                    ws = g.weight
            if wp > 0.0 and ws > 0.0 and abs(wp + ws - 1.0) < 1e-3:
                dual += 1
    unweighted = sum(1 for v in mesh_obj.data.vertices
                     if sum(g.weight for g in v.groups) < 1e-4)

    # ---------------------------------------------------------- render setup
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
    for engine in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scn.render.engine = engine
            break
        except TypeError:
            continue
    try:
        scn.eevee.taa_render_samples = 24
    except Exception:
        pass

    cam = bpy.data.objects.get("CAM_preview")
    if cam is None:
        raise RuntimeError("%s: CAM_preview tidak ada" % src_name)
    scn.camera = cam
    body = max(meshes, key=lambda o: len(o.data.vertices))
    L = max(body.dimensions.x, body.dimensions.y, body.dimensions.z)
    k = max(L, 0.05) / 0.45
    tgt = Vector((0.0, -0.05 * k, 0.0))
    loc = Vector((0.95 * k, -0.55 * k, 0.38 * k))
    cam.location = loc
    cam.data.lens = 55.0
    cam.rotation_euler = (tgt - loc).to_track_quat("-Z", "Y").to_euler()

    prefix = out_name.replace(".blend", "").replace("_", "-")
    for idx, frame in ((1, F_A), (2, F_B)):
        scn.frame_set(frame)
        scn.render.resolution_percentage = 50
        path = os.path.join(STILLS, "%s_preview-%02d.png" % (prefix, idx))
        scn.render.filepath = path
        bpy.ops.render.render(write_still=True)
        print("RENDER", path, os.path.exists(path))

    # -------------------------------------------------------------- simpan
    scn.frame_set(1)
    scn.render.resolution_percentage = 100
    scn.render.filepath = "//"
    purge_libraries()
    drop_render_result()
    bpy.ops.wm.save_as_mainfile(filepath=OUT)
    size_kb = round(os.path.getsize(OUT) / 1024.0)

    worst_tip = min((r[1]["tip_world_mm"] for r in results.values()), default=0.0)
    log("RIG - %s: %d verteks sirip dada dibobot ulang (semua, campuran "
        "pectoral+spine_02 %.2f-%.2f), ujung sirip bergerak %.1f-%.1f mm "
        "(frame 6->18), action %s tetap, %d KB"
        % (out_name, total, W_MIN, W_MAX,
           min(r[1]["tip_world_mm"] for r in results.values()),
           max(r[1]["tip_world_mm"] for r in results.values()),
           act.name if act else "tanpa action", size_kb))
    if worst_tip < TIP_MIN_MM:
        log("BLOCKED - %s: ujung sirip hanya bergerak %.2f mm (< %.1f mm)"
            % (out_name, worst_tip, TIP_MIN_MM))
    if dual != total:
        log("BLOCKED - %s: %d/%d verteks sirip memakai dua grup" % (out_name, dual, total))

    print("SIMPAN", OUT, size_kb, "KB | sirip", total, "verteks | dua grup",
          "%d/%d" % (dual, total), "| tanpa bobot", unweighted,
          "| action", act.name if act else None, "keys", act_keys)
    print("images", [i.name for i in bpy.data.images],
          "| libraries", [l.filepath for l in bpy.data.libraries])
    return {"file": out_name, "fins": total, "dual": dual,
            "tip_mm": {s: round(r[1]["tip_world_mm"], 1) for s, r in results.items()},
            "edge_pct": {s: round(r[1]["edge_pct"], 1) for s, r in results.items()},
            "act": act.name if act else None, "kb": size_kb}


summary = []
for src_name, out_name, arm_name, build_script, mesh_name in FILES:
    summary.append(do_file(src_name, out_name, arm_name, build_script, mesh_name))

print("=== RINGKASAN ===")
for s in summary:
    print(s)
log("VERIFY - 3 file ikan _v003: pergerakan ujung sirip %s"
    % ", ".join("%s %s mm" % (s["file"], s["tip_mm"]) for s in summary))

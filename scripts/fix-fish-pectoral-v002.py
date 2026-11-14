"""Perbaiki bobot sirip dada ikan - tiga file `_v002`.

Masalah: di v001, verteks sirip dada diberi bobot **kaku** 100 % ke bone
`pectoral_L` / `pectoral_R` (assign_rigid di build-fish-*.py), sehingga sirip
berputar sebagai piringan keras dan tidak ikut deformasi halus badan.

Perbaikan (14 Nov 2026):
  1. setiap verteks sirip dada diberi bobot campuran `pectoral_L/R` +
     `spine_02`, gradien dari pangkal (0,25 / 0,75) ke ujung (1,00 / 0,00).
     Parameter gradien = proyeksi verteks pada sumbu bone pectoral.
  2. bobot dihaluskan 2 iterasi rata-rata tetangga topologi (0,6 bobot sendiri
     + 0,4 rata-rata tetangga), lalu dijepit 0,12-1,0 dan dinormalkan.
  3. verteks di luar sirip dada tidak disentuh; action renang dipertahankan
     apa adanya (tidak ada perubahan animasi).

File hasil (sumber tidak diubah):
    assets/env/fish-kakatua_v002.blend
    assets/env/fish-damselfish_v002.blend
    assets/env/fish-cakalang-rig_v002.blend

Verifikasi numerik per file: sebelum vs sesudah perbaikan, pada frame 6 dan 18
diukur (a) perubahan panjang tepi di dalam sirip (0 % = kaku, >0 = berdeformasi)
dan (b) perpindahan ujung sirip relatif terhadap bone `spine_02`.

Setelan file: EEVEE, 1920x1080, 24 fps, view transform Standard, frame 1,
tanpa texture/pack gambar. Skrip idempoten, tanpa open_mainfile.

    blender -b --python scripts/fix-fish-pectoral-v002.py
"""
import bpy
import os
import time
from mathutils import Vector

try:
    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
except NameError:  # dijalankan lewat exec() MCP: __file__ tidak ada
    ROOT = r"D:\Tugas Semester 5\Grafika Komputer\Project-Animasi"

ENV_DIR = os.path.join(ROOT, "assets", "env")
WIPE = os.path.join(ROOT, "renders", "tmp", "_wipe.blend")
STILLS = os.path.join(ROOT, "renders", "stills")
LOG = os.path.join(ROOT, "renders", "logs", "modeling.log")

FILES = [
    ("fish-kakatua.blend", "fish-kakatua_v002.blend", "CHR_fish_kakatua_rig"),
    ("fish-damselfish.blend", "fish-damselfish_v002.blend", "CHR_fish_damselfish_rig"),
    ("fish-cakalang-rig.blend", "fish-cakalang-rig_v002.blend", "CHR_cakalang_rig"),
]
F_A, F_B = 6, 18          # dua fase action renang untuk uji deformasi


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


# ---------------------------------------------------------------- bobot sirip
def fin_verts(mesh_obj, bone_name):
    """Indeks verteks yang saat ini kaku (>0,5) ke bone pectoral."""
    vg = mesh_obj.vertex_groups.get(bone_name)
    if vg is None:
        return []
    out = []
    for v in mesh_obj.data.vertices:
        for g in v.groups:
            if g.group == vg.index and g.weight > 0.5:
                out.append(v.index)
                break
    return out


def bone_axis(arm, bone_name):
    bone = arm.data.bones[bone_name]
    head = bone.head_local.copy()
    tail = bone.tail_local.copy()
    d = tail - head
    length = d.length
    return head, d.normalized(), max(length, 1e-6)


def gradient_weights(mesh_obj, arm, side):
    """Bobot campuran pectoral + spine_02, gradien pangkal -> ujung."""
    bone = "pectoral_%s" % side
    idx = fin_verts(mesh_obj, bone)
    if not idx:
        return None
    head, axis, length = bone_axis(arm, bone)
    mw = mesh_obj.matrix_world
    aw = arm.matrix_world.inverted()
    # parameter pangkal -> ujung: jarak radial dari pangkal bone (lebih tahan
    # untuk sirip berbentuk kipas yang tidak sejajar sumbu bone)
    dist = {}
    for i in idx:
        co = aw @ (mw @ mesh_obj.data.vertices[i].co)
        dist[i] = (co - head).length
    dmax = max(dist.values()) or 1e-6
    dmin = min(dist.values())
    span = max(dmax - dmin, 1e-6)
    t = {i: (dist[i] - dmin) / span for i in idx}
    w = {i: 0.25 + 0.75 * t[i] for i in idx}         # pangkal 0,25 -> ujung 1,0
    # 2 iterasi penghalusan di dalam sirip
    adj = {i: set() for i in idx}
    idx_set = set(idx)
    for e in mesh_obj.data.edges:
        a, b = e.vertices
        if a in idx_set and b in idx_set:
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
        w[i] = min(1.0, max(0.12, w[i]))
    # tulis bobot: pectoral = w, spine_02 = 1-w, grup lain dibuang dari sirip
    vg_p = mesh_obj.vertex_groups.get(bone) or mesh_obj.vertex_groups.new(name=bone)
    vg_s = (mesh_obj.vertex_groups.get("spine_02")
            or mesh_obj.vertex_groups.new(name="spine_02"))
    others = [g for g in mesh_obj.vertex_groups if g.name not in (bone, "spine_02")]
    for i in idx:
        for g in others:
            g.remove([i])
        vg_p.add([i], w[i], "REPLACE")
        vg_s.add([i], 1.0 - w[i], "REPLACE")
    ordered = sorted(idx, key=lambda i: t[i])
    return {
        "n": len(idx),
        "t": t,
        "w": w,
        "base": ordered[0],
        "mid": ordered[len(ordered) // 2],
        "tip": ordered[-1],
    }


def deform_metrics(arm, mesh_obj, bone_name, idxs):
    """Panjang tepi + posisi relatif ke spine_02 pada frame 6 dan 18."""
    scn = bpy.context.scene
    idx_set = set(idxs)
    edges = [(e.vertices[0], e.vertices[1]) for e in mesh_obj.data.edges
             if e.vertices[0] in idx_set and e.vertices[1] in idx_set]
    data = {}
    for f in (F_A, F_B):
        scn.frame_set(f)
        bpy.context.view_layer.update()
        dg = bpy.context.evaluated_depsgraph_get()
        ev = mesh_obj.evaluated_get(dg)
        me = ev.to_mesh()
        mw = ev.matrix_world
        co = {i: mw @ me.vertices[i].co.copy() for i in idxs}
        ev.to_mesh_clear()
        pb = arm.pose.bones["spine_02"]
        m_rel = pb.matrix.inverted() @ arm.matrix_world.inverted()
        rel = {i: m_rel @ co[i] for i in idxs}
        elen = [(co[a] - co[b]).length for a, b in edges]
        data[f] = {"co": co, "rel": rel, "edge": elen}
    scn.frame_set(1)
    bpy.context.view_layer.update()
    rigid = 0.0
    if data[F_A]["edge"]:
        diffs = [abs(b - a) / a for a, b in zip(data[F_A]["edge"], data[F_B]["edge"]) if a > 1e-9]
        rigid = 100.0 * sum(diffs) / len(diffs)
    return data, rigid


def measure(arm, mesh_obj, bone_name, idxs):
    info = gradient_info.get((mesh_obj.name, bone_name))
    data, rigid = deform_metrics(arm, mesh_obj, bone_name, idxs)
    out = {"rigid_pct": rigid, "move": {}}
    for tag in ("base", "mid", "tip"):
        if not info:
            break
        i = info[tag]
        out["move"][tag] = (data[F_B]["rel"][i] - data[F_A]["rel"][i]).length
    # ukuran mutlak ujung sirip
    tip_co_a = data[F_A]["co"][idxs[-1]]
    tip_co_b = data[F_B]["co"][idxs[-1]]
    out["tip_world_move_mm"] = (tip_co_b - tip_co_a).length * 1000.0
    return out


gradient_info = {}


# ------------------------------------------------------------------- per file
for src_name, out_name, arm_name in FILES:
    SRC = os.path.join(ENV_DIR, src_name)
    OUT = os.path.join(ENV_DIR, out_name)
    os.makedirs(os.path.dirname(WIPE), exist_ok=True)
    os.makedirs(STILLS, exist_ok=True)
    try:
        bpy.context.preferences.filepaths.save_version = 0
    except Exception:
        pass
    scn = wipe()
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
    meshes = [o for o in bpy.data.objects if o.type == "MESH"
              and any(m.type == "ARMATURE" and m.object is arm for m in o.modifiers)]
    print("==", src_name, "| arm", arm.name, "| bone", len(arm.data.bones),
          "| action", act.name if act else None, "| mesh", [m.name for m in meshes])

    # ---------- ukur kondisi lama (kaku) ----------
    before = {}
    for mesh in meshes:
        for side in ("L", "R"):
            idx = fin_verts(mesh, "pectoral_%s" % side)
            if not idx:
                continue
            data, rigid = deform_metrics(arm, mesh, "pectoral_%s" % side, idx)
            before[(mesh.name, side)] = rigid

    # ---------- perbaiki bobot ----------
    summary = []
    for mesh in meshes:
        for side in ("L", "R"):
            info = gradient_weights(mesh, arm, side)
            if info is None:
                continue
            gradient_info[(mesh.name, "pectoral_%s" % side)] = info
            bad = sum(1 for v in mesh.data.vertices if sum(g.weight for g in v.groups) < 1e-4)
            summary.append((mesh.name, side, info, bad))

    # ---------- ukur sesudah ----------
    results = []
    for mesh_name, side, info, unweighted in summary:
        mesh = bpy.data.objects[mesh_name]
        bone = "pectoral_%s" % side
        after = measure(arm, mesh, bone, list(info["t"].keys()))
        rigid_before = before.get((mesh_name, side), 0.0)
        results.append((mesh_name, side, info, rigid_before, after, unweighted))
        print("%-28s %s n=%3d | panjang tepi berubah %4.1f%% -> %4.1f%% | "
              "bobot pangkal %.2f tengah %.2f ujung %.2f | gerak relatif badan "
              "pangkal %.2f mm, ujung %.2f mm | tanpa bobot %d"
              % (mesh_name, bone, info["n"], rigid_before, after["rigid_pct"],
                 info["w"][info["base"]], info["w"][info["mid"]],
                 info["w"][info["tip"]],
                 after["move"].get("base", 0) * 1000.0,
                 after["move"].get("tip", 0) * 1000.0, unweighted))

    # ---------- setelan render ----------
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

    # ---------- render 2 fase (dekat sirip dada) ----------
    cam = bpy.data.objects.get("CAM_preview")
    body = max(meshes, key=lambda o: len(o.data.vertices))
    length = max(body.dimensions.x, body.dimensions.y, body.dimensions.z)
    L = max(length, 0.05)
    k = L / 0.45
    shots = [
        ("%s_preview-01" % out_name.replace(".blend", ""), F_A,
         (0.20 * k, -0.34 * k, -0.26 * k), (0.03 * k, -0.12 * k, -0.02 * k), 55.0),
        ("%s_preview-02" % out_name.replace(".blend", ""), F_B,
         (0.20 * k, -0.34 * k, -0.26 * k), (0.03 * k, -0.12 * k, -0.02 * k), 55.0),
    ]
    scn.camera = cam
    for name, frame, loc, tgt, lens in shots:
        scn.frame_set(frame)
        cam.location = loc
        cam.data.lens = lens
        cam.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        scn.render.resolution_percentage = 50
        path = os.path.join(STILLS, name + ".png")
        scn.render.filepath = path
        bpy.ops.render.render(write_still=True)
        print("RENDER", path, os.path.exists(path))

    # ---------- simpan ----------
    scn.frame_set(1)
    cam.location = (0.30 * k, -0.62 * k, -0.34 * k)
    cam.data.lens = 50.0
    cam.rotation_euler = ((Vector((0.0, -0.06 * k, 0.0)) - Vector(cam.location))
                          .to_track_quat("-Z", "Y").to_euler())
    scn.render.resolution_percentage = 100
    scn.render.filepath = "//"
    purge_libraries()
    drop_render_result()
    bpy.ops.wm.save_as_mainfile(filepath=OUT)
    size_kb = round(os.path.getsize(OUT) / 1024.0)

    worst = max(r[5] for r in results) if results else 0
    log("RIG - %s: %d kelompok sirip dada dibobot ulang (campuran pectoral+spine_02, "
        "2 iterasi halus); panjang tepi berubah %.1f-%.1f%% (kaku 0%%), action %s tetap, "
        "%d KB"
        % (out_name, len(results),
           min(r[4]["rigid_pct"] for r in results) if results else 0,
           max(r[4]["rigid_pct"] for r in results) if results else 0,
           act.name if act else "tanpa action", size_kb))
    if worst:
        log("BLOCKED - %s: %d verteks tanpa bobot" % (out_name, worst))
    print("SIMPAN", OUT, size_kb, "KB | images", [i.name for i in bpy.data.images],
          "| libraries", [l.filepath for l in bpy.data.libraries])

print("SELESAI 3 file")

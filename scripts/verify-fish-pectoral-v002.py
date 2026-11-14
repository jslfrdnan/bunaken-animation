"""Verifikasi ulang + render pratinjau tiga file ikan `_v002`.

Dipakai setelah `scripts/fix-fish-pectoral-v002.py`:

  1. append file dari disk (`link=False`) - jadi membaca isi file, bukan state
     sesi;
  2. cek armature, jumlah bone, bobot sirip dada (gradien pangkal/tengah/ujung,
     verteks tanpa bobot), dan action renang yang dipertahankan;
  3. ukur deformasi: panjang tepi di dalam sirip + perpindahan ujung sirip
     relatif terhadap bone `spine_02` pada frame 6 vs 18;
  4. render dua fase (frame 6 dan 18) ke renders/stills/*_preview-01/02.png
     pada skala 50 % dengan bingkai seluruh ikan;
  5. simpan lagi hanya untuk menaruh bingkai kamera pratinjau yang benar.

    blender -b --python scripts/verify-fish-pectoral-v002.py
"""
import bpy
import os
import time
from mathutils import Vector

try:
    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
except NameError:
    ROOT = r"D:\Tugas Semester 5\Grafika Komputer\Project-Animasi"

ENV_DIR = os.path.join(ROOT, "assets", "env")
WIPE = os.path.join(ROOT, "renders", "tmp", "_wipe.blend")
STILLS = os.path.join(ROOT, "renders", "stills")
LOG = os.path.join(ROOT, "renders", "logs", "modeling.log")

FILES = [
    ("fish-kakatua_v002.blend", "CHR_fish_kakatua_rig"),
    ("fish-damselfish_v002.blend", "CHR_fish_damselfish_rig"),
    ("fish-cakalang-rig_v002.blend", "CHR_cakalang_rig"),
]
F_A, F_B = 6, 18


def log(line):
    stamp = time.strftime("%H:%M")
    try:
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


def drop_render_result():
    for img in list(bpy.data.images):
        if img.type == "RENDER_RESULT":
            try:
                bpy.data.images.remove(img)
            except Exception:
                pass


def fin_indices(mesh, bone):
    vg = mesh.vertex_groups.get(bone)
    if vg is None:
        return []
    out = []
    for v in mesh.data.vertices:
        for g in v.groups:
            if g.group == vg.index and g.weight > 0.4:
                out.append(v.index)
                break
    return out


for fname, arm_name in FILES:
    SRC = os.path.join(ENV_DIR, fname)
    os.makedirs(os.path.dirname(WIPE), exist_ok=True)
    try:
        bpy.context.preferences.filepaths.save_version = 0
    except Exception:
        pass
    scn = wipe()
    if bpy.data.filepath and os.path.abspath(bpy.data.filepath) != os.path.abspath(WIPE):
        bpy.ops.wm.save_as_mainfile(filepath=WIPE)
    scn.name = fname.replace(".blend", "")

    with bpy.data.libraries.load(SRC, link=False) as (df, dt):
        dt.collections = list(df.collections)
        dt.objects = list(df.objects)
    for c in bpy.data.collections:
        if c.name not in [x.name for x in scn.collection.children]:
            scn.collection.children.link(c)

    arm = bpy.data.objects[arm_name]
    act = arm.animation_data.action if arm.animation_data else None
    meshes = [o for o in bpy.data.objects if o.type == "MESH"
              and any(m.type == "ARMATURE" and m.object is arm for m in o.modifiers)]
    unweighted = sum(1 for m in meshes for v in m.data.vertices
                     if sum(g.weight for g in v.groups) < 1e-4)
    rng = []
    if act:
        try:
            rng = [int(act.frame_range[0]), int(act.frame_range[1])]
        except Exception:
            rng = []

    report = []
    for mesh in meshes:
        for side in ("L", "R"):
            bone = "pectoral_%s" % side
            idx = fin_indices(mesh, bone)
            if not idx:
                continue
            vg_p = mesh.vertex_groups[bone]
            vg_s = mesh.vertex_groups.get("spine_02")
            ws = []
            for i in idx:
                w = 0.0
                for g in mesh.data.vertices[i].groups:
                    if g.group == vg_p.index:
                        w = g.weight
                ws.append((w, i))
            ws.sort()
            edges = [(e.vertices[0], e.vertices[1]) for e in mesh.data.edges
                     if e.vertices[0] in idx and e.vertices[1] in idx]
            data = {}
            for f in (F_A, F_B):
                scn.frame_set(f)
                bpy.context.view_layer.update()
                dg = bpy.context.evaluated_depsgraph_get()
                ev = mesh.evaluated_get(dg)
                me = ev.to_mesh()
                mw = ev.matrix_world
                co = {i: mw @ me.vertices[i].co.copy() for i in idx}
                ev.to_mesh_clear()
                m_rel = arm.pose.bones["spine_02"].matrix.inverted() @ arm.matrix_world.inverted()
                data[f] = {"co": co, "rel": {i: m_rel @ co[i] for i in idx},
                           "edge": [(co[a] - co[b]).length for a, b in edges]}
            diffs = [abs(b - a) / a for a, b in zip(data[F_A]["edge"], data[F_B]["edge"]) if a > 1e-9]
            rigid = 100.0 * sum(diffs) / len(diffs) if diffs else 0.0
            base_i, tip_i = ws[0][1], ws[-1][1]
            move = (lambda i: (data[F_B]["rel"][i] - data[F_A]["rel"][i]).length * 1000.0)
            report.append((mesh.name, bone, len(idx), ws[0][0], ws[-1][0], rigid,
                           move(base_i), move(tip_i)))
            print("  %-26s %s n=%3d w %.2f-%.2f | tepi %4.1f%% | gerak relatif "
                  "pangkal %.2f mm ujung %.2f mm"
                  % (mesh.name, bone, len(idx), ws[0][0], ws[-1][0], rigid,
                     move(base_i), move(tip_i)))
    print("%-26s bone %d | action %s %s | tanpa bobot %d"
          % (fname, len(arm.data.bones), act.name if act else None, rng, unweighted))

    # ---------------- render dua fase, bingkai seluruh ikan ----------------
    scn.frame_start = 1
    scn.frame_end = 1
    scn.render.fps = 24
    scn.render.resolution_x = 1920
    scn.render.resolution_y = 1080
    scn.view_settings.view_transform = "Standard"
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
    cam = bpy.data.objects["CAM_preview"]
    scn.camera = cam
    body = max(meshes, key=lambda o: len(o.data.vertices))
    L = max(body.dimensions.x, body.dimensions.y, body.dimensions.z)
    centre = Vector((0.0, -0.05 * L, 0.02 * L))
    loc = Vector((1.25 * L, -2.10 * L, 0.75 * L))
    cam.location = loc
    cam.data.lens = 50.0
    cam.rotation_euler = (centre - loc).to_track_quat("-Z", "Y").to_euler()
    prefix = fname.replace(".blend", "")
    for frame, tag in ((F_A, "01"), (F_B, "02")):
        scn.frame_set(frame)
        scn.render.resolution_percentage = 50
        path = os.path.join(STILLS, "%s_preview-%s.png" % (prefix, tag))
        scn.render.filepath = path
        bpy.ops.render.render(write_still=True)
        print("  RENDER", os.path.basename(path), os.path.exists(path))

    scn.frame_set(1)
    scn.render.resolution_percentage = 100
    scn.render.filepath = "//"
    for lib in list(bpy.data.libraries):
        try:
            bpy.data.libraries.remove(lib)
        except Exception:
            pass
    drop_render_result()
    bpy.ops.wm.save_as_mainfile(filepath=SRC)
    lo = min(r[5] for r in report) if report else 0
    hi = max(r[5] for r in report) if report else 0
    mt = min(r[7] for r in report) if report else 0
    log("VERIFY - %s dibuka ulang: bone %d, %d kelompok sirip dada (w %.2f tas pangkal "
        "-> %.2f ujung), tepi berubah %.1f-%.1f%%, ujung sirip bergerak %.1f-%.1f mm "
        "relatif badan (frame %d vs %d), action %s tetap, %d vert tanpa bobot, %.0f KB"
        % (fname, len(arm.data.bones), len(report),
           min(r[3] for r in report) if report else 0,
           max(r[4] for r in report) if report else 0, lo, hi,
           min(r[6] for r in report) if report else 0,
           max(r[7] for r in report) if report else 0, F_A, F_B,
           act.name if act else "-", unweighted,
           os.path.getsize(SRC) / 1024.0))

print("VERIFIKASI 3 FILE SELESAI")

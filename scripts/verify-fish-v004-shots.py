"""verify-fish-v004-shots.py — tes penerimaan ikan v004 di shot Scene 1.

JALUR HEADLESS:

    & "D:\\Blender Foundation\\Blender 5.2\\blender.exe" -b ^
        -P scripts/verify-fish-v004-shots.py -- 030 040 050

Yang dihitung (bukan diklaim):
  1. 20 frame tersebar per sekolah; `forward_world . tangent_normalized` untuk
     SETIAP ikan di frame itu — laporkan min & rata-rata.
  2. Vektor up dunia tiap sampel — laporkan min z.
  3. Amplitudo sudut `tail_02` vs `spine_03` per action — rasio.
  4. Jumlah action berbeda per sekolah.
  5. Tidak ada dot < 0 (mundur).
  6. Bukti lengkung jalur (sebaran arah tangent) & animasi tetap jalan lewat
     frame 32 (CYCLES).
  7. Kamera, karang, lamun, lampu tidak berubah dibanding backup v003.
"""

import bpy
import datetime
import math
import os
import sys
from mathutils import Vector

ROOT = r"D:/Tugas Semester 5/Grafika Komputer/Project-Animasi"
SCENES = ROOT + "/scenes"
TMP = ROOT + "/renders/tmp"
LOGPATH = ROOT + "/renders/logs/technical.log"

SHOTS = {
    "030": "scene-1_shot-030_terumbu_v001.blend",
    "040": "scene-1_shot-040_penyu_v001.blend",
    "050": "scene-1_shot-050_nara-dive_v001.blend",
}
BACKUP = {
    "030": "backup-scene-1_shot-030_terumbu__v000.blend",
    "040": "backup-scene-1_shot-040_penyu__v000.blend",
    "050": "backup-scene-1_shot-050_nara-dive__v000.blend",
}
SCHOOLS = ("cakalang", "kakatua", "damselfish")
EXPECT = {"cakalang": 12, "kakatua": 20, "damselfish": 24}
BONES = ("tail_02", "spine_03")


def log(phase, line):
    os.makedirs(os.path.dirname(LOGPATH), exist_ok=True)
    stamp = datetime.datetime.now().strftime("%H:%M")
    with open(LOGPATH, "a", encoding="utf-8") as fh:
        fh.write("[%s] %s - %s\n" % (stamp, phase, line))
    print("[log]", phase, line)


def ang_deg(q):
    v = Vector((q[1], q[2], q[3])).length
    return math.degrees(2.0 * math.atan2(v, abs(q[0])))


def sample_frames(f0, f1, n=20):
    if n == 1:
        return [f0]
    return sorted({int(round(f0 + (f1 - f0) * i / float(n - 1))) for i in range(n)})


def fingerprint_environment():
    """Sidik jari kamera/karang/lamun/lampu (untuk dibandingkan dgn backup)."""
    scn = bpy.context.scene
    out = {}
    cam = scn.camera
    if cam is not None:
        rows = []
        for f in (scn.frame_start, (scn.frame_start + scn.frame_end) // 2, scn.frame_end):
            scn.frame_set(f)
            bpy.context.view_layer.update()
            m = cam.matrix_world
            rows.append((round(m.translation.x, 5), round(m.translation.y, 5),
                         round(m.translation.z, 5),
                         round(cam.data.lens, 5)))
        out["camera"] = (cam.name, rows)
    coral = []
    for o in bpy.data.objects:
        if o.name.startswith(("ENV_dense_", "ENV_reef-dense")):
            m = o.matrix_world
            coral.append((o.name, round(m.translation.x, 4), round(m.translation.y, 4),
                          round(m.translation.z, 4), round(o.scale.x, 4)))
    out["env_objects"] = sorted(coral)
    sg = bpy.data.objects.get("ENV_dense_seagrass")
    out["seagrass"] = (len(sg.data.vertices), len(sg.data.polygons)) if sg else None
    out["lights"] = sorted((o.name, round(o.data.energy, 3))
                           for o in bpy.data.objects if o.type == "LIGHT")
    scn.frame_set(scn.frame_start)
    return out


def check_shot(key):
    path = os.path.join(SCENES, SHOTS[key])
    bak = os.path.join(TMP, BACKUP[key])
    if not os.path.exists(path):
        raise SystemExit("shot tidak ada: " + path)

    env_old = None
    if os.path.exists(bak):
        bpy.ops.wm.open_mainfile(filepath=bak)
        env_old = fingerprint_environment()

    bpy.ops.wm.open_mainfile(filepath=path)
    scn = bpy.context.scene
    f0, f1 = scn.frame_start, scn.frame_end
    print("=== VERIFY s1-%s (%s) %d-%d ===" % (key, scn.name, f0, f1))

    samples = sample_frames(f0, f1, 20)
    report = {}
    all_dots = []
    all_upz = []
    for kind in SCHOOLS:
        coll = bpy.data.collections.get("ENV_school_" + kind)
        arms = [o for o in coll.objects if o.type == "ARMATURE"] if coll else []
        pivot = bpy.data.objects.get("ENV_school_%s_pivot" % kind)
        dots, ups, headings = [], [], []
        tangents = []
        for f in samples:
            scn.frame_set(f)
            bpy.context.view_layer.update()
            scn.frame_set(max(f0, f - 1))
            bpy.context.view_layer.update()
            pm = pivot.matrix_world.translation.copy()
            scn.frame_set(min(f1, f + 1))
            bpy.context.view_layer.update()
            pp = pivot.matrix_world.translation.copy()
            tan = pp - pm
            if tan.length < 1e-9:
                print("  PERINGATAN tangent nol di f%d %s" % (f, kind))
                continue
            tan.normalize()
            tangents.append(tan.copy())
            scn.frame_set(f)
            bpy.context.view_layer.update()
            for a in arms:
                m3 = a.matrix_world.to_3x3()
                fwd = (m3 @ Vector((0.0, -1.0, 0.0))).normalized()
                up = (m3 @ Vector((0.0, 0.0, 1.0))).normalized()
                dots.append(fwd.dot(tan))
                ups.append(up.z)
        acts_all = [a.animation_data.action.name for a in arms
                    if a.animation_data and a.animation_data.action]
        acts = sorted(set(acts_all))
        dist = {n: acts_all.count(n) for n in acts}
        swing = 0.0
        for i in range(len(tangents)):
            for j in range(i + 1, len(tangents)):
                swing = max(swing, math.degrees(
                    math.acos(max(-1.0, min(1.0, tangents[i].dot(tangents[j]))))))
        v003 = [o.name for o in (coll.objects if coll else [])
                if o.type == "MESH" and o.name.startswith("ENV_school_%s_" % kind)]
        report[kind] = dict(n=len(arms), dots=dots, ups=ups, acts=acts, dist=dist,
                            v003=v003, swing=swing)
        all_dots.extend(dots)
        all_upz.extend(ups)

    # --- amplitudo action (tail_02 vs spine_03) ---------------------------
    amp_rows = []
    for kind in SCHOOLS:
        coll = bpy.data.collections["ENV_school_" + kind]
        arm = next(o for o in coll.objects if o.type == "ARMATURE")
        for act in sorted({a.animation_data.action for a in coll.objects
                           if a.type == "ARMATURE" and a.animation_data
                           and a.animation_data.action}, key=lambda x: x.name):
            ad = arm.animation_data
            ad.action = act
            try:
                if len(act.slots):
                    ad.action_slot = act.slots[0]
            except Exception:
                pass
            amp = {}
            for bname in BONES:
                mx = 0.0
                for f in range(1, 34):
                    scn.frame_set(f)
                    bpy.context.view_layer.update()
                    pb = arm.pose.bones.get(bname)
                    if pb is None:
                        continue
                    mx = max(mx, ang_deg(pb.rotation_quaternion))
                amp[bname] = mx
            ratio = amp["tail_02"] / amp["spine_03"] if amp["spine_03"] > 1e-6 else 0.0
            amp_rows.append((kind, act.name, amp["tail_02"], amp["spine_03"], ratio))

    # --- animasi tetap jalan lewat frame 32 (CYCLES) ----------------------
    loop_rows = []
    for kind in SCHOOLS:
        coll = bpy.data.collections["ENV_school_" + kind]
        arm = next(o for o in coll.objects if o.type == "ARMATURE")
        qs = {}
        for f in (1, 9, 33, 41, 49, 57, 89):
            scn.frame_set(f)
            bpy.context.view_layer.update()
            qs[f] = arm.pose.bones["tail_02"].rotation_quaternion.copy()
        span = max(ang_deg(qs[a].rotation_difference(qs[b]))
                   for a in (41, 49, 57, 89) for b in (41, 49, 57, 89))
        seam = ang_deg(qs[1].rotation_difference(qs[33]))
        loop_rows.append((kind, span, seam))

    # --- lingkungan tidak berubah ---------------------------------------
    env_new = fingerprint_environment()
    env_same = None
    if env_old is not None:
        diffs = []
        if env_old.get("camera") != env_new.get("camera"):
            diffs.append("kamera")
        if env_old.get("env_objects") != env_new.get("env_objects"):
            diffs.append("karang/objek env")
        if env_old.get("seagrass") != env_new.get("seagrass"):
            diffs.append("lamun")
        if env_old.get("lights") != env_new.get("lights"):
            diffs.append("lampu")
        env_same = (not diffs, diffs)

    # --- spesifikasi file -------------------------------------------------
    path_size = os.path.getsize(path)
    packed = [i.name for i in bpy.data.images if i.packed_file is not None]
    libs = [l.filepath for l in bpy.data.libraries]
    scn.frame_set(1)

    # --- ringkasan --------------------------------------------------------
    dot_min = min(all_dots) if all_dots else float("nan")
    dot_mean = sum(all_dots) / len(all_dots) if all_dots else float("nan")
    up_min = min(all_upz) if all_upz else float("nan")
    print("  dot: min %.4f rata %.4f | %d sampel | up z min %.4f | dot<0: %d"
          % (dot_min, dot_mean, len(all_dots), up_min,
             len([d for d in all_dots if d < 0])))
    for kind in SCHOOLS:
        r = report[kind]
        print("  %-11s n=%2d (harus %2d) | dot min %.4f rata %.4f | up z min %.4f | "
              "action %d %s | sisa mesh v003 %d | belok maks %.0f deg"
              % (kind, r["n"], EXPECT[kind], min(r["dots"]), sum(r["dots"]) / len(r["dots"]),
                 min(r["ups"]), len(r["acts"]),
                 {a.split("_", 2)[-1]: c for a, c in r["dist"].items()},
                 len(r["v003"]), r["swing"]))
    for kind, name, t_amp, s_amp, ratio in amp_rows:
        print("  amp %-11s %-34s tail %.1f spine_03 %.1f ratio %.2f %s"
              % (kind, name.split("_", 2)[-1], t_amp, s_amp, ratio,
                 "OK" if ratio >= 2.0 else "KURANG"))
    for kind, span, seam in loop_rows:
        print("  loop %-11s gerak f41-89 %.2f deg, sambungan f1-f33 %.2f deg"
              % (kind, span, seam))
    print("  file %d bytes | %dx%d %d fps | range %d-%d | vt %s | frame %d | "
          "packed %s | libraries %s"
          % (path_size, scn.render.resolution_x, scn.render.resolution_y,
             scn.render.fps, f0, f1, scn.view_settings.view_transform,
             scn.frame_current, packed or "-", libs or "-"))
    if env_same is not None:
        print("  lingkungan vs backup v003: %s"
              % ("TIDAK BERUBAH" if env_same[0] else "BERUBAH: " + ", ".join(env_same[1])))

    ok = (dot_min > 0.95 and up_min > 0.0 and not [d for d in all_dots if d < 0]
          and all(r["n"] == EXPECT[k] for k, r in report.items())
          and all(len(r["acts"]) >= 3 for r in report.values())
          and all(ratio >= 2.0 for _, _, _, _, ratio in amp_rows)
          and all(len(r["v003"]) == 0 for r in report.values()))
    print("  VERDICT s1-%s: %s" % (key, "LULUS" if ok else "TIDAK LULUS"))
    return dict(key=key, dot_min=dot_min, dot_mean=dot_mean, up_min=up_min,
                dots=len(all_dots), report=report, amp=amp_rows,
                loop=loop_rows, ok=ok, size=path_size, env=env_same,
                act_count={k: len(r["acts"]) for k, r in report.items()})


def main(argv):
    args = argv[argv.index("--") + 1:] if "--" in argv else []
    keys = [a for a in args if a in SHOTS] or list(SHOTS.keys())
    log("VERIFY", "tes penerimaan ikan v004 shot %s dimulai" % ",".join(keys))
    results = []
    for key in keys:
        results.append(check_shot(key))
    print("=== RINGKASAN ===")
    for r in results:
        print("s1-%s: dot min %.4f rata %.4f | up z min %.4f | %d action/sekolah | %s"
              % (r["key"], r["dot_min"], r["dot_mean"], r["up_min"],
                 min(r["act_count"].values()), "LULUS" if r["ok"] else "TIDAK LULUS"))
    allok = all(r["ok"] for r in results)
    worst = min(r["dot_min"] for r in results)
    log("VERIFY", "ikan v004 shot %s: dot min %.4f, up z min %.4f, verdict %s"
        % (",".join(keys), worst, min(r["up_min"] for r in results),
           "LULUS" if allok else "TIDAK LULUS"))
    print("SELESAI verifikasi", "LULUS" if allok else "TIDAK LULUS")


if __name__ == "__main__":
    main(sys.argv)

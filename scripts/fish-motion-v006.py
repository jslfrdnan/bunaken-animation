"""Gerak ikan Scene 1 v006 — dijalankan lewat Blender MCP.

Perubahan dari v005:
- Pivot sekolah bergerak dengan kecepatan konstan (arc-length resample).
- Formasi ikan direnggangkan 3D sampai jarak minimum 1,0 m.
- Action renang baru: gelombang menjalar spine_01 -> tail_02, ujung ekor ~0,35 m.
- NLA per ikan tetap memberi fase dan kecepatan berbeda.
"""

import math
import os

import bpy
from mathutils import Vector

ROOT = r"D:/Tugas Semester 5/Grafika Komputer/Project-Animasi"
SCHOOLS = ("cakalang", "kakatua", "damselfish")
PARAMS = {
    "cakalang": dict(speed=1.5, roll=0.030, yaw=0.012, sway=0.020, bob=0.015),
    "kakatua": dict(speed=1.1, roll=0.025, yaw=0.010, sway=0.015, bob=0.012),
    "damselfish": dict(speed=0.9, roll=0.020, yaw=0.008, sway=0.012, bob=0.010),
}
AMPS = {  # derajat
    "spine_01": (3.0, 0.00),
    "spine_02": (7.0, -0.55),
    "spine_03": (11.0, -1.10),
    "tail_01": (16.0, -1.65),
    "tail_02": (26.0, -2.20),
    "dorsal": (4.0, -0.80),
    "pelvic_L": (5.0, -0.40),
    "pelvic_R": (5.0, -0.40),
    "jaw": (1.0, 0.00),
}
MIN_DIST = 1.0


def _wipe():
    for db in (bpy.data.objects, bpy.data.collections, bpy.data.meshes,
               bpy.data.materials, bpy.data.cameras, bpy.data.lights,
               bpy.data.worlds, bpy.data.actions, bpy.data.armatures,
               bpy.data.curves):
        for block in list(db):
            try:
                db.remove(block)
            except Exception:
                pass


def isolate(path):
    dummy = bpy.data.scenes.new("TMP_fish6")
    bpy.context.window.scene = dummy
    _wipe()
    for scn in list(bpy.data.scenes):
        if scn != dummy:
            bpy.data.scenes.remove(scn)
    with bpy.data.libraries.load(path, link=False) as (src, dst):
        dst.scenes = list(src.scenes)
    scn = dst.scenes[0]
    for lib in list(bpy.data.libraries):
        bpy.data.libraries.remove(lib)
    bpy.context.window.scene = scn
    bpy.data.scenes.remove(dummy)
    return scn


def constant_pivot(scn, kind):
    piv = bpy.data.objects["ENV_school_%s_pivot" % kind]
    parent = piv.parent
    to_local = parent.matrix_world.inverted() if parent else None
    f0, f1 = scn.frame_start, scn.frame_end
    world = []
    old_rot = []
    for f in range(f0, f1 + 1):
        scn.frame_set(f)
        bpy.context.view_layer.update()
        world.append(piv.matrix_world.translation.copy())
        old_rot.append(piv.rotation_quaternion.copy())
    seg = [(world[i] - world[i - 1]).length for i in range(1, len(world))]
    total = sum(seg)
    # interpolasi posisi sepanjang polyline dengan panjang busur konstan
    cum = [0.0]
    for d in seg:
        cum.append(cum[-1] + d)
    out = []
    for i in range(len(world)):
        s = total * i / float(len(world) - 1)
        j = 1
        while j < len(cum) - 1 and cum[j] < s:
            j += 1
        d0, d1 = cum[j - 1], cum[j]
        t = 0.0 if d1 - d0 < 1e-9 else (s - d0) / (d1 - d0)
        out.append(world[j - 1].lerp(world[j], t))
    # rotasi: pertahankan pitch/roll, hitung yaw dari tangent
    act = bpy.data.actions.new("ENV_%s_pivot_const_v006" % kind)
    piv.animation_data_create()
    piv.animation_data.action = act
    piv.rotation_mode = "XYZ"
    for i in range(len(out)):
        p = out[i]
        lp = to_local @ p if to_local else p
        piv.location = lp
        a = out[max(0, i - 1)]
        b = out[min(len(out) - 1, i + 1)]
        tan = b - a
        if tan.length > 1e-9:
            horiz = math.hypot(tan.x, tan.y)
            yaw = math.atan2(tan.x, -tan.y)
            pitch = -math.atan2(tan.z, horiz) if horiz > 1e-9 else 0.0
        else:
            e = old_rot[i].to_euler()
            yaw, pitch = e.z, e.x
        piv.rotation_euler = (pitch, 0.0, yaw)
        piv.keyframe_insert("location", frame=f0 + i)
        piv.keyframe_insert("rotation_euler", frame=f0 + i)
    scn.frame_set(f0)
    return total


def respace(scn, kind, min_dist=MIN_DIST):
    coll = bpy.data.collections["ENV_school_" + kind]
    arms = sorted((o for o in coll.objects if o.type == "ARMATURE"),
                  key=lambda o: o.name)
    pts = [a.location.copy() for a in arms]
    n = len(pts)
    for it in range(300):
        moved = False
        for i in range(n):
            for j in range(i + 1, n):
                d = pts[i] - pts[j]
                if d.length < min_dist:
                    if d.length < 1e-6:
                        d = Vector((0.01 * (i + 1), 0.01 * (j + 1), 0.02))
                    push = d.normalized() * ((min_dist - d.length) * 0.5 + 0.001)
                    pts[i] += push
                    pts[j] -= push
                    moved = True
        if not moved:
            break
    for a, p in zip(arms, pts):
        a.location = p
    bpy.context.view_layer.update()
    return min((pts[i] - pts[j]).length for i in range(n) for j in range(i + 1, n))


def build_action(kind, scn):
    coll = bpy.data.collections["ENV_school_" + kind]
    arm = sorted((o for o in coll.objects if o.type == "ARMATURE"),
                 key=lambda o: o.name)[0]
    ad = arm.animation_data
    if ad is None:
        ad = arm.animation_data_create()
    for track in list(ad.nla_tracks):
        if track.name.startswith("SWIM"):
            ad.nla_tracks.remove(track)
    act = bpy.data.actions.get("ENV_%s_swim_v006" % kind)
    if act:
        bpy.data.actions.remove(act)
    act = bpy.data.actions.new("ENV_%s_swim_v006" % kind)
    ad.action = act
    for pb in arm.pose.bones:
        pb.rotation_mode = "QUATERNION"
    for f in range(1, 26):
        phase = (f - 1) / 24.0 * 2.0 * math.pi
        for bname, (amp, lag) in AMPS.items():
            pb = arm.pose.bones.get(bname)
            if pb is None:
                continue
            angle = math.radians(amp) * math.sin(phase + lag)
            pb.rotation_quaternion = (math.cos(angle / 2.0), 0.0, 0.0,
                                      math.sin(angle / 2.0))
            pb.keyframe_insert("rotation_quaternion", frame=f)
    ad.action = None
    return act, arm


def apply_motion(scn):
    for kind in SCHOOLS:
        p = PARAMS[kind]
        coll = bpy.data.collections.get("ENV_school_" + kind)
        if coll is None:
            continue
        arms = sorted((o for o in coll.objects if o.type == "ARMATURE"),
                      key=lambda o: o.name)
        for arm in arms:
            ad = arm.animation_data
            if ad:
                for track in list(ad.nla_tracks):
                    if track.name.startswith("SWIM"):
                        ad.nla_tracks.remove(track)
                for fc in list(ad.drivers):
                    if (fc.data_path, fc.array_index) in (
                            ("rotation_euler", 0), ("rotation_euler", 1),
                            ("rotation_euler", 2), ("location", 0), ("location", 2),
                            ("delta_location", 0), ("delta_location", 2)):
                        ad.drivers.remove(fc)
                ad.action = None
            arm.rotation_euler = (0.0, 0.0, 0.0)
            arm.delta_location = (0.0, 0.0, 0.0)
        total = constant_pivot(scn, kind)
        mind = respace(scn, kind)
        act, template = build_action(kind, scn)
        for i, arm in enumerate(arms):
            ad = arm.animation_data_create()
            track = ad.nla_tracks.new()
            track.name = "SWIM_V006"
            strip = track.strips.new("swim", int(-i * 2.0), act)
            strip.scale = p["speed"] * (1.0 + 0.04 * ((i % 3) - 1))
            strip.repeat = 8.0
            if hasattr(strip, "action_slot") and len(act.slots):
                strip.action_slot = act.slots[0]
            ad.action = None
            arm.rotation_mode = "XYZ"
            ph = i * 0.7
            for path, idx, amp, freq, off in (
                ("rotation_euler", 1, p["roll"], 0.20, ph),
                ("rotation_euler", 2, p["yaw"], 0.16, ph + 0.9),
                ("delta_location", 0, p["sway"], 0.18, ph + 0.7),
                ("delta_location", 2, p["bob"], 0.15, ph + 1.9),
            ):
                fc = arm.driver_add(path, idx)
                fc.driver.type = "SCRIPTED"
                fc.driver.expression = "%.4f*sin(frame*%.2f + %.3f)" % (amp, freq, off)
        print("KIND", kind, "path_m", round(total, 2), "min_dist", round(mind, 3),
              "action", act.name, "fish", len(arms))
    scn.frame_set(scn.frame_start)


def metrics(scn, samples=20):
    f0, f1 = scn.frame_start, scn.frame_end
    frames = sorted({int(round(f0 + (f1 - f0) * i / (samples - 1.0)))
                     for i in range(samples)})
    dots, ups = [], []
    speeds = []
    for kind in SCHOOLS:
        coll = bpy.data.collections.get("ENV_school_" + kind)
        if coll is None:
            continue
        arms = [o for o in coll.objects if o.type == "ARMATURE"]
        piv = bpy.data.objects["ENV_school_%s_pivot" % kind]
        pos = []
        for f in range(f0, f1 + 1):
            scn.frame_set(f)
            bpy.context.view_layer.update()
            pos.append(piv.matrix_world.translation.copy())
        sp = [(pos[i] - pos[i - 1]).length for i in range(1, len(pos))]
        speeds.append((min(sp), max(sp)))
        for f in frames:
            scn.frame_set(max(f0, f - 1))
            bpy.context.view_layer.update()
            pm = piv.matrix_world.translation.copy()
            scn.frame_set(min(f1, f + 1))
            bpy.context.view_layer.update()
            pp = piv.matrix_world.translation.copy()
            tan = pp - pm
            if tan.length < 1e-9:
                continue
            tan.normalize()
            scn.frame_set(f)
            bpy.context.view_layer.update()
            for a in arms:
                m3 = a.matrix_world.to_3x3()
                fwd = (m3 @ Vector((0.0, -1.0, 0.0))).normalized()
                up = (m3 @ Vector((0.0, 0.0, 1.0))).normalized()
                dots.append(fwd.dot(tan))
                ups.append(up.z)
    # jarak minimum sekarang
    mins = []
    for kind in SCHOOLS:
        arms = [o for o in bpy.data.collections["ENV_school_" + kind].objects
                if o.type == "ARMATURE"]
        pts = [a.location for a in arms]
        mins.append(min((pts[i] - pts[j]).length
                        for i in range(len(pts)) for j in range(i + 1, len(pts))))
    # ayunan ujung ekor
    arm = next(o for o in bpy.data.collections["ENV_school_cakalang"].objects
               if o.type == "ARMATURE")
    tips = []
    for f in range(1, 25):
        scn.frame_set(f)
        bpy.context.view_layer.update()
        tips.append(arm.pose.bones["tail_02"].tail.copy())
    sweep = max((tips[i] - tips[j]).length
                for i in range(len(tips)) for j in range(i + 1, len(tips)))
    ratios = [max(s) / max(min(s), 1e-9) for s in speeds]
    return {
        "dot_min": round(min(dots), 4) if dots else None,
        "up_min": round(min(ups), 3) if ups else None,
        "backwards": len([d for d in dots if d < 0]),
        "pivot_speed_ratio": round(max(ratios), 2),
        "min_pair_m": round(min(mins), 3),
        "tail_sweep_m": round(sweep, 3),
    }


def main():
    for shot in ("scene-1_shot-030_terumbu_v001",
                 "scene-1_shot-040_penyu_v001",
                 "scene-1_shot-050_nara-dive_v001"):
        path = os.path.join(ROOT, "scenes", shot + ".blend")
        scn = isolate(path)
        apply_motion(scn)
        result = metrics(scn)
        print("FISH6", shot, result)
        bpy.ops.wm.save_as_mainfile(filepath=path, check_existing=False)
    print("FISH6_DONE")


if __name__ == "__main__":
    main()

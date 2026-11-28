"""Retune gerak ikan Scene 1 (v005) — dijalankan lewat Blender MCP.

Perubahan:
- NLA strip per ikan: fase dan kecepatan kepakan berbeda (tidak serempak).
- Driver roll (banking), yaw kecil, weave lateral, dan bob vertikal.
- Tidak mengubah rig, action sumber, kamera, karang, atau lamun.

Pemakaian lewat MCP:
    exec(open("scripts/fish-motion-v005.py").read(), {"__name__": "__main__"})
"""

import math
import os

import bpy
from mathutils import Vector

ROOT = r"D:/Tugas Semester 5/Grafika Komputer/Project-Animasi"
SHOTS = [
    "scene-1_shot-030_terumbu_v001",
    "scene-1_shot-040_penyu_v001",
    "scene-1_shot-050_nara-dive_v001",
]
SCHOOLS = ("cakalang", "kakatua", "damselfish")
PARAMS = {
    "cakalang": dict(scale=1.8, step=2.3, roll=0.050, sway=0.040, bob=0.030, yaw=0.020),
    "kakatua": dict(scale=1.4, step=2.0, roll=0.040, sway=0.030, bob=0.025, yaw=0.015),
    "damselfish": dict(scale=1.2, step=1.8, roll=0.035, sway=0.025, bob=0.020, yaw=0.012),
}
DRIVER_PROPS = (("rotation_euler", 1), ("rotation_euler", 2),
                ("location", 0), ("location", 2))


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
    """Muat satu scene shot tanpa open_mainfile (aman untuk MCP)."""
    dummy = bpy.data.scenes.new("TMP_fish")
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


def _clear_motion(arm):
    ad = arm.animation_data
    if ad is None:
        return None
    act = ad.action
    for track in list(ad.nla_tracks):
        if track.name.startswith("SWIM"):
            if act is None and track.strips:
                act = track.strips[0].action
            ad.nla_tracks.remove(track)
    for fc in list(ad.drivers):
        if (fc.data_path, fc.array_index) in DRIVER_PROPS:
            ad.drivers.remove(fc)
    if act is not None:
        ad.action = act
    return act


def apply_motion(scn):
    applied = {}
    for kind in SCHOOLS:
        p = PARAMS[kind]
        coll = bpy.data.collections.get("ENV_school_" + kind)
        if coll is None:
            continue
        arms = sorted((o for o in coll.objects if o.type == "ARMATURE"),
                      key=lambda o: o.name)
        for i, arm in enumerate(arms):
            act = _clear_motion(arm)
            ad = arm.animation_data
            if act is not None:
                track = ad.nla_tracks.new()
                track.name = "SWIM"
                strip = track.strips.new("swim", int(-i * p["step"]), act)
                strip.scale = p["scale"] * (1.0 + 0.03 * ((i % 3) - 1))
                strip.repeat = 10.0
                if hasattr(strip, "action_slot") and len(act.slots):
                    strip.action_slot = act.slots[0]
                ad.action = None
            arm.rotation_mode = "XYZ"
            phase = i * 0.7
            exprs = (
                ("rotation_euler", 1, p["roll"], phase),
                ("rotation_euler", 2, p["yaw"], phase + 0.9),
                ("location", 0, p["sway"], phase + 0.7),
                ("location", 2, p["bob"], phase + 1.9),
            )
            for path, idx, amp, ph in exprs:
                fc = arm.driver_add(path, idx)
                fc.driver.type = "SCRIPTED"
                fc.driver.expression = "%.4f*sin(frame*%s + %.3f)" % (
                    amp, "0.22" if path == "rotation_euler" and idx == 1
                    else ("0.17" if path == "rotation_euler" else
                          ("0.18" if idx == 0 else "0.15")), ph)
        applied[kind] = len(arms)
    return applied


def metrics(scn, samples=20):
    f0, f1 = scn.frame_start, scn.frame_end
    frames = sorted({int(round(f0 + (f1 - f0) * i / (samples - 1.0)))
                     for i in range(samples)})
    dots, ups, tails = [], [], []
    for kind in SCHOOLS:
        coll = bpy.data.collections.get("ENV_school_" + kind)
        if coll is None:
            continue
        arms = [o for o in coll.objects if o.type == "ARMATURE"]
        pivot = bpy.data.objects.get("ENV_school_%s_pivot" % kind)
        for f in frames:
            scn.frame_set(max(f0, f - 1))
            bpy.context.view_layer.update()
            pm = pivot.matrix_world.translation.copy()
            scn.frame_set(min(f1, f + 1))
            bpy.context.view_layer.update()
            pp = pivot.matrix_world.translation.copy()
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
    scn.frame_set(48)
    bpy.context.view_layer.update()
    for kind in SCHOOLS:
        coll = bpy.data.collections.get("ENV_school_" + kind)
        if coll is None:
            continue
        for a in [o for o in coll.objects if o.type == "ARMATURE"][:8]:
            q = a.pose.bones["tail_02"].rotation_quaternion
            tails.append(round(math.degrees(
                2.0 * math.atan2((q[1] ** 2 + q[2] ** 2 + q[3] ** 2) ** 0.5,
                                 abs(q[0]))), 1))
    return {
        "dots": len(dots),
        "dot_min": round(min(dots), 4) if dots else None,
        "dot_mean": round(sum(dots) / len(dots), 4) if dots else None,
        "up_min": round(min(ups), 3) if ups else None,
        "backwards": len([d for d in dots if d < 0]),
        "tail48": tails,
    }


def main():
    for shot in SHOTS:
        path = os.path.join(ROOT, "scenes", shot + ".blend")
        scn = isolate(path)
        applied = apply_motion(scn)
        result = metrics(scn)
        assert len(bpy.data.scenes) == 1, len(bpy.data.scenes)
        bpy.ops.wm.save_as_mainfile(filepath=path, check_existing=False)
        print("FISH", shot, "objects", len(scn.objects), "applied", applied,
              result, "size", os.path.getsize(path))
    print("FISH_DONE")


if __name__ == "__main__":
    main()

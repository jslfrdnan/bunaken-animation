"""Kamera 3-shot (menyelam turun) + animasi gelembung untuk Scene 2 (768 frame @24fps).

Shot 1 (f1-240)   menembus permukaan, god rays, mulai turun
Shot 2 (f241-480) turun mid-water
Shot 3 (f481-768) menyusuri dinding drop-off ke bawah -> transisi Scene 3
Dinding di y=0 (permukaan menonjol ke -Y), kamera di sisi +Y melihat ke -Y/bawah.
"""
import random

import bpy
from mathutils import Vector


def _iter_fcurves(action):
    fcs = list(getattr(action, "fcurves", []) or [])
    if fcs:
        return fcs
    for layer in getattr(action, "layers", []):
        for strip in layer.strips:
            for cbag in getattr(strip, "channelbags", []):
                fcs.extend(cbag.fcurves)
    return fcs


def _ease(obj):
    try:
        for fc in _iter_fcurves(obj.animation_data.action):
            for kp in fc.keyframe_points:
                kp.interpolation = "BEZIER"; kp.handle_left_type = kp.handle_right_type = "AUTO_CLAMPED"
    except Exception as e:
        print("  (lewati easing:", e, ")")


def _look_euler(pos, target):
    return (Vector(target) - Vector(pos)).to_track_quat("-Z", "Y").to_euler()


def _key_cam(cam, frame, pos, target):
    cam.location = Vector(pos)
    cam.rotation_euler = _look_euler(pos, target)
    cam.keyframe_insert("location", frame=frame)
    cam.keyframe_insert("rotation_euler", frame=frame)


def _new_cam(name, lens):
    d = bpy.data.cameras.new(name); d.lens = lens; d.clip_end = 2000.0
    o = bpy.data.objects.new(name, d); bpy.context.scene.collection.objects.link(o)
    return o


def setup():
    sc = bpy.context.scene

    # ---------- gelembung naik ----------
    rng = random.Random(9)
    for o in bpy.data.objects:
        if not o.name.startswith("Gelembung_"):
            continue
        z0 = o.location.z
        rise = rng.uniform(35, 58)
        x0 = o.location.x
        o.location.z = z0
        o.keyframe_insert("location", frame=1)
        o.location.x = x0 + rng.uniform(-1.5, 1.5)
        o.location.z = z0 + rise
        o.keyframe_insert("location", frame=768)
        # gerak lurus naik (linear)
        try:
            for fc in _iter_fcurves(o.animation_data.action):
                for kp in fc.keyframe_points:
                    kp.interpolation = "LINEAR"
        except Exception:
            pass

    # ---------- 3 kamera turun ----------
    cam1 = _new_cam("Cam2_Shot1_Permukaan", 24)
    _key_cam(cam1, 1,   (0, 36, -1.5), (0, 12, -14))
    _key_cam(cam1, 240, (2, 30, -8),   (0, 8, -20))

    cam2 = _new_cam("Cam2_Shot2_Turun", 30)
    _key_cam(cam2, 241, (6, 28, -11), (-2, 4, -22))
    _key_cam(cam2, 480, (3, 22, -20), (-2, 2, -30))

    cam3 = _new_cam("Cam2_Shot3_Dinding", 34)
    _key_cam(cam3, 481, (4, 18, -18), (0, -3, -22))
    _key_cam(cam3, 640, (3, 16, -25), (0, -4, -28))
    _key_cam(cam3, 768, (2, 15, -31), (0, -4, -33))

    for c in (cam1, cam2, cam3):
        _ease(c)

    mk = sc.timeline_markers
    for m in list(mk):
        mk.remove(m)
    for frame, cam in [(1, cam1), (241, cam2), (481, cam3)]:
        mk.new(cam.name, frame=frame).camera = cam
    sc.camera = cam1
    print("Kamera & gelembung Scene 2 siap:", [c.name for c in (cam1, cam2, cam3)])


if __name__ == "__main__":
    setup()

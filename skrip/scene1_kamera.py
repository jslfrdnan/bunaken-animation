"""Kamera 4-shot + animasi perahu untuk Scene 1 (960 frame @ 24 fps).

Shot 1 (f1-240)    establishing: aerial lebar Teluk Manado (Manado Tua + Bunaken + pesisir)
Shot 2 (f241-528)  flyover pesisir desa (rendah, menyusuri pantai)
Shot 3 (f529-768)  mengikuti perahu katinting yang berangkat
Shot 4 (f769-960)  menukik ke permukaan laut di tepi drop-off (match-cut ke Scene 2)

Potongan antar-shot pakai 4 kamera + marker timeline (hard cut), jadi tidak ada
interpolasi silang antar vantage point.
"""
import math

import bpy
from mathutils import Vector

BOB = 0.12  # amplitudo ayunan vertikal perahu


def _iter_fcurves(action):
    """Ambil fcurves lintas versi API (Blender <4.4 vs layered action 4.4+)."""
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
        act = obj.animation_data.action
        for fc in _iter_fcurves(act):
            for kp in fc.keyframe_points:
                kp.interpolation = "BEZIER"
                kp.handle_left_type = kp.handle_right_type = "AUTO_CLAMPED"
    except Exception as e:
        print("  (lewati easing:", e, ")")


def _look_euler(pos, target):
    d = Vector(target) - Vector(pos)
    return d.to_track_quat("-Z", "Y").to_euler()


def _key_cam(cam, frame, pos, target):
    cam.location = Vector(pos)
    cam.rotation_euler = _look_euler(pos, target)
    cam.keyframe_insert("location", frame=frame)
    cam.keyframe_insert("rotation_euler", frame=frame)


def _new_cam(name, lens):
    data = bpy.data.cameras.new(name)
    data.lens = lens
    data.clip_end = 4000.0
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    return obj


# --- jalur perahu (XY) sepanjang waktu ---
BOAT_KEYS = [
    (1, (16, 50)), (240, (17.5, 56)), (420, (20, 69)),
    (600, (24, 84)), (768, (28, 100)), (960, (34, 122)),
]


def _boat_pos(frame):
    ks = BOAT_KEYS
    if frame <= ks[0][0]:
        return Vector((*ks[0][1], 0))
    for i in range(len(ks) - 1):
        f0, p0 = ks[i]; f1, p1 = ks[i + 1]
        if frame <= f1:
            t = (frame - f0) / (f1 - f0)
            x = p0[0] + (p1[0] - p0[0]) * t
            y = p0[1] + (p1[1] - p0[1]) * t
            return Vector((x, y, 0))
    return Vector((*ks[-1][1], 0))


def setup():
    sc = bpy.context.scene

    # ---------- animasi perahu berangkat + nelayan ikut ----------
    boat = bpy.data.objects.get("Perahu_jalan")
    nelayan = bpy.data.objects.get("Nelayan")
    if boat:
        if nelayan and nelayan.parent:
            nelayan.parent = None   # batalkan parenting lama yang bermasalah
        for f, (x, y) in BOAT_KEYS:
            nxt = _boat_pos(f + 1)
            head = math.atan2(nxt.y - y, nxt.x - x)
            z = -0.15 + BOB * math.sin(f * 0.12)
            boat.location = Vector((x, y, z))
            boat.rotation_euler = (0, 0, head + math.radians(-90))  # perahu menghadap arah laju
            boat.keyframe_insert("location", frame=f)
            boat.keyframe_insert("rotation_euler", frame=f)
            if nelayan:
                nelayan.location = Vector((x, y, z + 0.35))   # berdiri di dek
                nelayan.rotation_euler = (0, 0, head + math.radians(-90))
                nelayan.keyframe_insert("location", frame=f)
                nelayan.keyframe_insert("rotation_euler", frame=f)
        _ease(boat)
        if nelayan:
            _ease(nelayan)

    # ---------- 4 kamera ----------
    cam1 = _new_cam("Cam_Shot1_Establishing", 30)
    _key_cam(cam1, 1,   (35, -185, 72), (-70, 70, 22))
    _key_cam(cam1, 240, (28, -150, 60), (-66, 78, 20))

    cam2 = _new_cam("Cam_Shot2_Flyover", 30)
    _key_cam(cam2, 241, (-58, 16, 15), (4, 44, 3))
    _key_cam(cam2, 528, (54, 30, 13),  (12, 48, 3))

    cam3 = _new_cam("Cam_Shot3_FollowBoat", 42)
    for f in (529, 648, 768):
        bp = _boat_pos(f)
        _key_cam(cam3, f, (bp.x - 11, bp.y - 15, 9.5), (bp.x, bp.y, 1.2))

    cam4 = _new_cam("Cam_Shot4_Dive", 26)
    _key_cam(cam4, 769, (18, 68, 19),  (23, 92, -2))
    _key_cam(cam4, 900, (21, 80, 6),   (25, 98, -6))
    _key_cam(cam4, 960, (23, 87, 0.7), (25, 100, -5))

    for cam in (cam1, cam2, cam3, cam4):
        _ease(cam)

    # ---------- marker timeline: potong antar-shot ----------
    mk = sc.timeline_markers
    for m in list(mk):
        mk.remove(m)
    for frame, cam in [(1, cam1), (241, cam2), (529, cam3), (769, cam4)]:
        marker = mk.new(cam.name, frame=frame)
        marker.camera = cam
    sc.camera = cam1
    print("Kamera & animasi perahu siap. Kamera:", [c.name for c in (cam1, cam2, cam3, cam4)])


if __name__ == "__main__":
    setup()

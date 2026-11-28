"""Boids ikan Scene 1 v007 — dijalankan lewat Blender MCP.

- Obstacle: AABB mesh karang, diperluas setengah panjang ikan + clearance 0,20 m.
- Boids: separation, alignment, cohesion, waypoint sekolah, obstacle avoidance.
- Cruise speed terkunci; kamera tidak digeser.
- Hasil di-bake ke transform objek per frame; NLA ekor v006 tetap dipakai.
"""

import math
import os

import bpy
from mathutils import Quaternion, Vector
from bpy_extras.object_utils import world_to_camera_view

ROOT = r"D:/Tugas Semester 5/Grafika Komputer/Project-Animasi"
SCHOOLS = ("cakalang", "kakatua", "damselfish")
FISH_HALF = {"cakalang": 0.39, "kakatua": 0.28, "damselfish": 0.20}
CLEARANCE = 0.20          # clearance mesh karang
PARAMS = {
    "cakalang": dict(sep=1.35, ali=3.5, coh=5.0, wsep=1.2, wali=0.25, wcoh=0.10, wgoal=4.0, wobs=2.0),
    "kakatua": dict(sep=1.25, ali=3.0, coh=4.2, wsep=1.2, wali=0.25, wcoh=0.10, wgoal=4.0, wobs=2.0),
    "damselfish": dict(sep=1.15, ali=2.5, coh=3.6, wsep=1.2, wali=0.20, wcoh=0.10, wgoal=4.0, wobs=2.2),
}
MAX_DEV = 0.8


def _respace_xy(points, min_dist=1.3):
    pts = [Vector((p.x, p.y, 0.0)) for p in points]
    n = len(pts)
    for _ in range(300):
        moved = False
        for i in range(n):
            for j in range(i + 1, n):
                d = pts[i] - pts[j]
                dist = d.length
                if dist < min_dist:
                    if dist < 1e-6:
                        d = Vector((0.01 * (i + 1), 0.01 * (j + 1), 0.0))
                        dist = d.length
                    push = d.normalized() * ((min_dist - dist) * 0.5 + 0.001)
                    pts[i] += push
                    pts[j] -= push
                    moved = True
        if not moved:
            break
    return [Vector((pts[i].x, pts[i].y, points[i].z)) for i in range(n)]


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
    dummy = bpy.data.scenes.new("TMP_boids")
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


def obstacle_boxes(scn, margin=0.0):
    """Silinder karang: (cx, cy, radius, zmin, zmax) dalam world."""
    boxes = []
    for ob in scn.objects:
        if ob.type != "MESH" or not ob.get("coral_type"):
            continue
        pts = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
        dx = max(p.x for p in pts) - min(p.x for p in pts)
        dy = max(p.y for p in pts) - min(p.y for p in pts)
        cx = (max(p.x for p in pts) + min(p.x for p in pts)) * 0.5
        cy = (max(p.y for p in pts) + min(p.y for p in pts)) * 0.5
        boxes.append((cx, cy, 0.5 * max(dx, dy) + margin,
                      min(p.z for p in pts) - margin,
                      max(p.z for p in pts) + margin))
    return boxes


def _box_dist(p, o):
    cx, cy, r, z0, z1 = o
    h = math.hypot(p.x - cx, p.y - cy) - r
    if p.z < z0:
        dz = z0 - p.z
    elif p.z > z1:
        dz = p.z - z1
    else:
        dz = 0.0
    if h <= 0.0 and dz <= 0.0:
        return 0.0
    return math.hypot(max(h, 0.0), dz)


def _inside(p, o):
    cx, cy, r, z0, z1 = o
    return math.hypot(p.x - cx, p.y - cy) < r and z0 < p.z < z1


def _slide_escape(p, v, boxes, cruise, seed=0):
    """Dorong ke tepi silinder sambil mempertahankan gerak tangensial."""
    for o in boxes:
        cx, cy, r, z0, z1 = o
        if not (z0 < p.z < z1):
            continue
        dx, dy = p.x - cx, p.y - cy
        h = math.hypot(dx, dy)
        if h >= r:
            continue
        if h < 1e-6:
            dx, dy, h = 1.0, 0.0, 1.0
        nx, ny = dx / h, dy / h
        rr = r + 0.02 + 0.10 * (seed % 3)
        p.x = cx + nx * rr
        p.y = cy + ny * rr
        inward = v.x * nx + v.y * ny
        if inward < 0.0:
            v.x -= nx * inward
            v.y -= ny * inward
        if v.length < 0.35 * cruise:
            v.x += -ny * 0.6 * cruise
            v.y += nx * 0.6 * cruise
        if v.length > 1e-6:
            v = v.normalized() * cruise
    return p, v


def build_guide(scn, kind):
    arms = sorted((o for o in bpy.data.collections["ENV_school_" + kind].objects
                   if o.type == "ARMATURE"), key=lambda o: o.name)
    f0, f1 = scn.frame_start, scn.frame_end
    targets = []
    for f in range(f0, f1 + 1):
        scn.frame_set(f)
        bpy.context.view_layer.update()
        targets.append([a.matrix_world.translation.copy() for a in arms])
    return targets, arms


def simulate(scn, kind, boxes, substeps=4):
    p = PARAMS[kind]
    targets, arms = build_guide(scn, kind)
    n = len(arms)
    frames = len(targets)
    centers = [sum(t, Vector()) / n for t in targets]
    seg = [(centers[i] - centers[i - 1]).length for i in range(1, len(centers))]
    cruise = sum(seg) / max(1, frames - 1) * 24.0
    # satu ketinggian aman global di atas seluruh karang
    global_safe = max(o[4] for o in boxes) + 0.20
    for fi in range(frames):
        for i in range(n):
            targets[fi][i].z = max(targets[fi][i].z, global_safe)

    pos = [targets[0][i].copy() for i in range(n)]
    vel = []
    for i in range(n):
        d = centers[1] - centers[0] if len(centers) > 1 else Vector((0, 1, 0))
        if d.length < 1e-6:
            d = Vector((0, 1, 0))
        vel.append(d.normalized() * cruise)

    out_pos = []
    out_vel = []
    dt = 1.0 / 24.0 / substeps
    for fi in range(frames):
        target = targets[fi]
        for _ in range(substeps):
            for i in range(n):
                sep = Vector()
                ali = Vector()
                coh = Vector()
                cnt_s = cnt_a = cnt_c = 0
                for j in range(n):
                    if i == j:
                        continue
                    d = pos[i] - pos[j]
                    dist = d.length
                    if dist < 1e-6:
                        d = Vector((0.01, 0.01, 0.01))
                        dist = d.length
                    if dist < p["sep"]:
                        sep += d.normalized() * (1.0 - dist / p["sep"])
                        cnt_s += 1
                    if dist < p["ali"]:
                        ali += vel[j]
                        cnt_a += 1
                    if dist < p["coh"]:
                        coh += pos[j]
                        cnt_c += 1
                force = Vector()
                if cnt_s:
                    force += sep.normalized() * p["wsep"]
                if cnt_a:
                    force += (ali / cnt_a).normalized() * p["wali"]
                if cnt_c:
                    force += ((coh / cnt_c) - pos[i]).normalized() * p["wcoh"]
                goal = target[i] - pos[i]
                dist_goal = goal.length
                if dist_goal > 1e-6:
                    force += goal.normalized() * p["wgoal"] * min(2.0, dist_goal / 2.0)
                # obstacle avoidance
                danger = None
                dmin = 1e9
                for box in boxes:
                    d = _box_dist(pos[i], box)
                    if d < dmin:
                        dmin = d
                        danger = box
                if danger is not None and dmin < 1.5 and pos[i].z < danger[4]:
                    cx, cy, r, z0, z1 = danger
                    rad = Vector((pos[i].x - cx, pos[i].y - cy, 0.0))
                    if rad.length < 1e-6:
                        rad = Vector((1.0, 0.0, 0.0))
                    rad.normalize()
                    force += rad * p["wobs"] * (1.5 - dmin)
                    # komponen tangensial agar ikan memutar, bukan berhenti
                    force += Vector((-rad.y, rad.x, 0.0)) * p["wobs"] * 0.25 * (1.5 - dmin)
                # boundary
                away_goal = pos[i] - target[i]
                if away_goal.length > 2.5:
                    force -= away_goal.normalized() * 2.5
                # integrate
                vel[i] = vel[i] + force * dt
                sp = vel[i].length
                if sp < 1e-6:
                    vel[i] = Vector((0, 1, 0)) * cruise
                else:
                    vel[i] = vel[i].lerp(vel[i].normalized() * cruise, 0.35)
                pos[i] = pos[i] + vel[i] * dt
                pos[i].z = min(target[i].z + 0.05, max(target[i].z - 0.05, pos[i].z))
            # kunci ke slot formasi
            for i in range(n):
                dev = pos[i] - target[i]
                if dev.length > MAX_DEV:
                    pos[i] = target[i] + dev.normalized() * MAX_DEV
                pos[i].z = min(target[i].z + 0.05, max(target[i].z - 0.05, pos[i].z))
            # pass separasi terakhir agar tidak saling tembus
            for _ in range(10):
                moved = False
                for i in range(n):
                    for j in range(i + 1, n):
                        d = pos[i] - pos[j]
                        dist = d.length
                        if dist < 1.05:
                            if dist < 1e-6:
                                d = Vector((0.01, 0.01, 0.0))
                                dist = d.length
                            push = d.normalized() * ((1.05 - dist) * 0.5)
                            pos[i] += push
                            pos[j] -= push
                            moved = True
                if not moved:
                    break
        out_pos.append([v.copy() for v in pos])
        out_vel.append([v.copy() for v in vel])
    return out_pos, out_vel, arms, cruise


def bake(scn, kind, positions, velocities, arms):
    for fish_idx, arm in enumerate(arms):
        world = arm.matrix_world.copy()
        arm.parent = None
        arm.matrix_world = world
        ad = arm.animation_data
        if ad:
            for fc in list(ad.drivers):
                ad.drivers.remove(fc)
            ad.action = None
        arm.rotation_mode = "QUATERNION"
        act = bpy.data.actions.new("ENV_%s_boids_v007" % arm.name)
        ad = arm.animation_data_create()
        ad.action = act
        prev_yaw = None
        for fi in range(len(positions)):
            f = scn.frame_start + fi
            p = positions[fi][fish_idx]
            v = velocities[fi][fish_idx]
            arm.location = p
            prev = positions[max(0, fi - 1)][fish_idx]
            motion = p - prev
            vel_dir = v.normalized() if v.length > 1e-6 else Vector((0, 1, 0))
            fwd = motion.normalized() if motion.length > 0.01 else vel_dir
            q = fwd.to_track_quat("-Y", "Z")
            yaw = math.atan2(fwd.x, -fwd.y)
            if prev_yaw is not None:
                dy = (yaw - prev_yaw + math.pi) % (2 * math.pi) - math.pi
                roll = max(-0.30, min(0.30, -dy * 1.8))
            else:
                roll = 0.0
            prev_yaw = yaw
            arm.rotation_quaternion = q @ Quaternion((0.0, 1.0, 0.0), roll)
            arm.keyframe_insert("location", frame=f)
            arm.keyframe_insert("rotation_quaternion", frame=f)


def visible_fraction(scn, kind):
    arms = [o for o in bpy.data.collections["ENV_school_" + kind].objects
            if o.type == "ARMATURE"]
    if not arms or scn.camera is None:
        return 1.0
    seen = total = 0
    for f in (scn.frame_start, (scn.frame_start + scn.frame_end) // 2, scn.frame_end):
        scn.frame_set(f)
        bpy.context.view_layer.update()
        for a in arms:
            total += 1
            n = world_to_camera_view(scn, scn.camera, a.matrix_world.translation)
            if 0.0 <= n.x <= 1.0 and 0.0 <= n.y <= 1.0:
                seen += 1
    return seen / max(1, total)


def metrics(scn):
    base = obstacle_boxes(scn, 0.0)
    f0, f1 = scn.frame_start, scn.frame_end
    min_clear = 1e9
    min_pair = 1e9
    dots = []
    outside = 0
    total = 0
    cam = scn.camera
    for kind in SCHOOLS:
        half = FISH_HALF[kind]
        coll = bpy.data.collections["ENV_school_" + kind]
        if coll.hide_render:
            continue
        arms = sorted((o for o in coll.objects
                       if o.type == "ARMATURE"), key=lambda o: o.name)
        prev = None
        for f in range(f0, f1 + 1):
            scn.frame_set(f)
            bpy.context.view_layer.update()
            pts = [a.matrix_world.translation.copy() for a in arms]
            for i in range(len(pts)):
                for j in range(i + 1, len(pts)):
                    min_pair = min(min_pair, (pts[i] - pts[j]).length)
                for o in base:
                    if _inside(pts[i], o):
                        clr = -half
                    else:
                        clr = _box_dist(pts[i], o) - half
                    min_clear = min(min_clear, clr)
                fwd = (arms[i].matrix_world.to_3x3() @ Vector((0, -1, 0))).normalized()
                if prev is not None:
                    delta = pts[i] - prev[i]
                    if delta.length > 0.01:
                        dots.append(fwd.dot(delta.normalized()))
                if cam is not None:
                    total += 1
                    ndc = world_to_camera_view(scn, cam, pts[i])
                    if not (0.0 <= ndc.x <= 1.0 and 0.0 <= ndc.y <= 1.0):
                        outside += 1
            prev = pts
    return {
        "min_clearance_m": round(min_clear, 3),
        "min_pair_m": round(min_pair, 3),
        "dot_min": round(min(dots), 4) if dots else None,
        "outside_pct": round(100.0 * outside / max(1, total), 1),
    }


def main():
    for shot in ("scene-1_shot-030_terumbu_v001",
                 "scene-1_shot-040_penyu_v001",
                 "scene-1_shot-050_nara-dive_v001"):
        path = os.path.join(ROOT, "scenes", shot + ".blend")
        scn = isolate(path)
        print("SHOT", shot, "obstacles", len(obstacle_boxes(scn, 0.0)))
        for kind in SCHOOLS:
            coll = bpy.data.collections["ENV_school_" + kind]
            vis = visible_fraction(scn, kind)
            if vis < 0.15:
                coll.hide_render = True
                coll.hide_viewport = True
                print("  ", kind, "DISEMBUNYIKAN, visibilitas", round(vis, 2))
                continue
            boxes = obstacle_boxes(scn, FISH_HALF[kind] + CLEARANCE)
            pos, vel, arms, cruise = simulate(scn, kind, boxes)
            bake(scn, kind, pos, vel, arms)
            print("  ", kind, "fish", len(arms), "cruise", round(cruise, 2),
                  "vis", round(vis, 2))
        print("  METRICS", metrics(scn))
        bpy.ops.wm.save_as_mainfile(filepath=path, check_existing=False)
    print("BOIDS_DONE")


if __name__ == "__main__":
    main()

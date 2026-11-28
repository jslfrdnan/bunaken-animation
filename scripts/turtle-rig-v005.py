"""Rig flipper penyu v005 (2 bone per flipper) — dijalankan lewat Blender MCP.

- Satu armature `ENV_turtle_rig` di bawah CTL_turtle.
- 8 bone: fl/fr/rl/rr _01 _02, dihitung dari bbox tiap flipper.
- Weight halus sepanjang flipper; action renang 72 frame.
"""

import math

import bpy
from mathutils import Vector, Quaternion

PAIRS = {
    "fl": "Turtle_Flap_Front_L",
    "fr": "Turtle_Flap_Front_R",
    "rl": "Turtle_Flap_Rear_L",
    "rr": "Turtle_Flap_Rear_R",
}
FRONT = ("fl", "fr")
REAR = ("rl", "rr")


def _smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def _clear_previous(ctl):
    old = bpy.data.objects.get("ENV_turtle_rig")
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    for name in PAIRS.values():
        ob = bpy.data.objects.get(name)
        if ob is None:
            continue
        ob.animation_data_clear()
        for mod in list(ob.modifiers):
            if mod.type == "ARMATURE":
                ob.modifiers.remove(mod)
        for vg in list(ob.vertex_groups):
            if vg.name.split("_")[0] in PAIRS:
                ob.vertex_groups.remove(vg)


def apply(scn):
    ctl = bpy.data.objects["CTL_turtle"]
    carapace = bpy.data.objects["Turtle_Carapace"]
    cw = ctl.matrix_world
    carapace_pts = [cw.inverted() @ (carapace.matrix_world @ Vector(c)) for c in carapace.bound_box]
    body_center = sum(carapace_pts, Vector()) / len(carapace_pts)

    _clear_previous(ctl)

    arm_data = bpy.data.armatures.new("ENV_turtle_rig")
    arm_obj = bpy.data.objects.new("ENV_turtle_rig", arm_data)
    scn.collection.objects.link(arm_obj)
    arm_obj.parent = ctl
    arm_obj.matrix_parent_inverse = cw.inverted()
    arm_obj.matrix_world = cw.copy()
    arm_obj.show_in_front = True

    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode="EDIT")
    specs = {}
    for key, name in PAIRS.items():
        ob = bpy.data.objects[name]
        pts = [cw.inverted() @ (ob.matrix_world @ v.co) for v in ob.data.vertices]
        centroid = sum(pts, Vector()) / len(pts)
        far = max(pts, key=lambda p: (p - centroid).length)
        direction = (far - centroid)
        if direction.length < 1e-6:
            direction = Vector((0, 1, 0))
        direction.normalize()
        proj = [(p - centroid).dot(direction) for p in pts]
        root = centroid + direction * min(proj)
        tip = centroid + direction * max(proj)
        mid = (root + tip) * 0.5
        b1 = arm_data.edit_bones.new(key + "_01")
        b1.head = root
        b1.tail = mid
        b2 = arm_data.edit_bones.new(key + "_02")
        b2.head = mid
        b2.tail = tip
        b2.parent = b1
        b2.use_connect = True
        specs[key] = (root, tip, direction, ob, pts)
    bpy.ops.object.mode_set(mode="OBJECT")

    # weight + modifier
    for key, (root, tip, direction, ob, pts) in specs.items():
        length = max((tip - root).length, 1e-6)
        g1 = ob.vertex_groups.new(name=key + "_01")
        g2 = ob.vertex_groups.new(name=key + "_02")
        for v, p in zip(ob.data.vertices, pts):
            t = (p - root).dot(direction) / length
            w2 = _smooth((t - 0.12) / 0.76)
            g1.add([v.index], 1.0 - w2, "REPLACE")
            g2.add([v.index], w2, "REPLACE")
        mod = ob.modifiers.new("Armature", "ARMATURE")
        mod.object = arm_obj
        mod.use_vertex_groups = True

    # action renang 72 frame
    act = bpy.data.actions.new("ENV_act_turtle_swim_v005")
    arm_obj.animation_data_create()
    arm_obj.animation_data.action = act
    for pb in arm_obj.pose.bones:
        pb.rotation_mode = "QUATERNION"
    axes = {}
    for pb in arm_obj.pose.bones:
        inv = pb.bone.matrix_local.to_3x3().inverted()
        axes[pb.name] = ((inv @ Vector((1.0, 0.0, 0.0))).normalized(),
                         (inv @ Vector((0.0, 0.0, 1.0))).normalized())

    for f in range(1, scn.frame_end + 1):
        phase = (f - 1) / 48.0 * 2.0 * math.pi
        for key in PAIRS:
            front = key in FRONT
            amp_pitch = math.radians(25.0 if front else 10.0)
            amp_sweep = math.radians(14.0 if front else 6.0)
            phase_off = 0.0 if front else math.pi
            pitch = amp_pitch * math.sin(phase + phase_off)
            sweep = amp_sweep * math.cos(phase + phase_off)
            flex = pitch * 0.35 * math.sin(phase + phase_off - 0.7)
            for suffix, angle_pitch, angle_sweep in (("_01", pitch, sweep),
                                                     ("_02", flex, 0.0)):
                pb = arm_obj.pose.bones[key + suffix]
                ax_pitch, ax_sweep = axes[pb.name]
                pb.rotation_quaternion = (
                    Quaternion(ax_pitch, angle_pitch)
                    @ Quaternion(ax_sweep, angle_sweep))
                pb.keyframe_insert("rotation_quaternion", frame=f)

    scn.frame_set(1)
    bpy.context.view_layer.update()

    # diagnostik: gerak ujung flipper
    dg = bpy.context.evaluated_depsgraph_get()
    report = {}
    for key, name in PAIRS.items():
        ob = bpy.data.objects[name]
        idx = max(range(len(ob.data.vertices)),
                  key=lambda i: (cw.inverted() @ (ob.matrix_world @ ob.data.vertices[i].co) - body_center).length)
        zs = []
        for f in (1, 13, 25, 37, 49, 61, 72):
            scn.frame_set(f)
            bpy.context.view_layer.update()
            ev = ob.evaluated_get(bpy.context.evaluated_depsgraph_get())
            zs.append(round((cw.inverted() @ (ev.matrix_world @ ev.data.vertices[idx].co)).z, 4))
        report[key] = (round(max(zs) - min(zs), 4), idx)
    scn.frame_set(1)
    return arm_obj, act, report


if __name__ == "__main__":
    scn = bpy.context.scene
    arm, act, report = apply(scn)
    print("TURTLE_RIG", arm.name, "bones", len(arm.data.bones), "action", act.name)
    print("TURTLE_TIP_RANGE", report)

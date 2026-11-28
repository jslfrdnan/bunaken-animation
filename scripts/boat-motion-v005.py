"""Gerak kapal Scene 1 (v005) — dijalankan lewat Blender MCP.

020: kapal lewat sudah punya lintasan; tambah bob/roll/pitch halus.
070: kapal dive diam; tambah drift 0,45 m menjauhi Nara + bob/roll + wake.
"""

import math
import os

import bpy


def _mat_wake():
    mat = bpy.data.materials.get("MAT_wake_foam_v005")
    if mat:
        return mat
    mat = bpy.data.materials.new("MAT_wake_foam_v005")
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (0.88, 0.96, 0.95, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.8
    bsdf.inputs["Alpha"].default_value = 0.42
    try:
        bsdf.inputs["Emission Color"].default_value = (0.75, 0.9, 0.9, 1.0)
        bsdf.inputs["Emission Strength"].default_value = 0.15
    except Exception:
        pass
    try:
        mat.surface_render_method = "BLENDED"
    except Exception:
        try:
            mat.blend_method = "BLEND"
        except Exception:
            pass
    mat.use_backface_culling = False
    return mat


def _wake_mesh(ctl, length=6.0, width=1.1, z_local=0.34):
    steps = 6
    verts, faces = [], []
    for side in (1.0, -1.0):
        start = len(verts)
        for i in range(steps + 1):
            t = i / float(steps)
            x = -3.2 - length * t
            y = side * (0.22 + (width - 0.22) * t)
            z = z_local + 0.01
            verts.append((x, y, z))
            verts.append((x, y, z + 0.09 * (1.0 - 0.4 * t)))
        for i in range(steps):
            a = start + i * 2
            faces.append((a, a + 2, a + 3, a + 1))
    # churn patch di buritan
    base = len(verts)
    verts += [(-3.2, 0.28, z_local + 0.01), (-6.0, 1.0, z_local + 0.01),
              (-6.0, -1.0, z_local + 0.01), (-3.2, -0.28, z_local + 0.01)]
    faces.append((base, base + 1, base + 2, base + 3))
    me = bpy.data.meshes.new("FX_wake_v005")
    me.from_pydata(verts, [], faces)
    me.materials.append(_mat_wake())
    ob = bpy.data.objects.new("FX_wake_v005", me)
    bpy.context.scene.collection.objects.link(ob)
    ob.parent = ctl
    ob.matrix_parent_inverse = ctl.matrix_world.inverted()
    ob.location = (0, 0, 0)
    ob.visible_shadow = False
    return ob


def _drivers(ctl, roll, pitch, bob):
    paths = (
        ("rotation_euler", 0, "%.3f*sin(frame*0.20 + 0.4)" % roll),
        ("rotation_euler", 1, "%.3f*sin(frame*0.16 + 1.7)" % pitch),
        ("location", 2, "%.3f*sin(frame*0.22 + 2.4)" % bob),
    )
    for path, idx, expr in paths:
        for fc in list(ctl.animation_data.drivers if ctl.animation_data else []):
            if (fc.data_path, fc.array_index) == (path, idx):
                ctl.animation_data.drivers.remove(fc)
        fc = ctl.driver_add(path, idx)
        fc.driver.type = "SCRIPTED"
        fc.driver.expression = expr


def apply_070(scn):
    ctl = bpy.data.objects["CTL_boat-dive"]
    ctl.rotation_mode = "XYZ"
    base = ctl.location.copy()
    act = bpy.data.actions.get("CTL_boat-diveAction_v005")
    if act is None:
        act = bpy.data.actions.new("CTL_boat-diveAction_v005")
    ctl.animation_data_create()
    ctl.animation_data.action = act
    for f, dist in ((1, 0.0), (24, 0.10), (48, 0.25), (72, 0.38), (96, 0.45)):
        ctl.location = (base.x + dist, base.y - dist * 0.18, base.z)
        ctl.keyframe_insert("location", frame=f)
    ctl.location = base
    _drivers(ctl, roll=0.022, pitch=0.010, bob=0.030)
    old = bpy.data.objects.get("FX_wake_v005")
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    _wake_mesh(ctl)
    scn.frame_set(1)
    return ctl


def apply_020(scn):
    ctl = bpy.data.objects["CTL_boat-pass"]
    ctl.rotation_mode = "XYZ"
    _drivers(ctl, roll=0.030, pitch=0.012, bob=0.040)
    scn.frame_set(1)
    return ctl


if __name__ == "__main__":
    scn = bpy.context.scene
    if scn.name.startswith("scene-1_shot-070"):
        ctl = apply_070(scn)
    else:
        ctl = apply_020(scn)
    print("BOAT", scn.name, ctl.name, "wake", bool(bpy.data.objects.get("FX_wake_v005")))

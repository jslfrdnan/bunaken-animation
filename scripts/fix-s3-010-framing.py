"""
Perbaikan Scene 3 shot 010: baringkan Nara dengan parent empty, lalu arahkan
kamera statis ke pusat tubuh. Properti kamera ikut diputar.

Headless:
    "D:\\Blender Foundation\\Blender 5.2\\blender.exe" -b -P scripts/fix-s3-010-framing.py
"""

import math
import os

import bpy
from mathutils import Vector

ROOT = r"D:/Tugas Semester 5/Grafika Komputer/Project-Animasi"
FILE = ROOT + "/scenes/scene-3_shot-010_nara-rekam_v001.blend"

bpy.ops.wm.open_mainfile(filepath=FILE)
scn = bpy.context.scene
scn.frame_set(48)
bpy.context.view_layer.update()

nara = [o for o in bpy.data.objects if o.type == "MESH" and o.name.startswith("CHR_nara")]
prop = [o for o in bpy.data.objects if o.type == "MESH" and o.name.startswith("PRP_camera")]
if not nara:
    raise RuntimeError("mesh Nara tidak ditemukan")

hips = bpy.data.objects.get("CHR_nara_hips")
anchor = hips.matrix_world.translation.copy() if hips else Vector((0, 0, 0.9))
print("anchor:", tuple(round(v, 2) for v in anchor))

pivot = bpy.data.objects.new("CTL_nara_prone", None)
scn.collection.objects.link(pivot)
pivot.location = anchor

for ob in nara + prop:
    mw = ob.matrix_world.copy()
    ob.parent = pivot
    ob.matrix_parent_inverse = pivot.matrix_world.inverted()
    ob.matrix_world = mw

pivot.rotation_euler = (math.radians(90), 0.0, 0.0)
pivot.location.z += 0.45
bpy.context.view_layer.update()

pts = []
for ob in nara + prop:
    for corner in ob.bound_box:
        pts.append(ob.matrix_world @ Vector(corner))
lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
center = (lo + hi) * 0.5
size = hi - lo
print("bbox:", tuple(round(v, 2) for v in lo), tuple(round(v, 2) for v in hi),
      "size", tuple(round(v, 2) for v in size))

cam = scn.camera
cam.animation_data_clear()
cam.data.lens = 32.0
dist = max(size.x, size.y, size.z) * 2.1
cam.location = center + Vector((dist * 0.80, -dist * 0.62, dist * 0.30))
cam.rotation_euler = (center - cam.location).to_track_quat("-Z", "Y").to_euler()
print("kamera:", tuple(round(v, 2) for v in cam.location),
      "jarak", round((center - cam.location).length, 2))

scn.render.resolution_percentage = 50
scn.render.image_settings.file_format = "PNG"
out = ROOT + "/renders/stills/anim-s3-010_v001.png"
scn.render.filepath = out[:-4]
bpy.ops.render.render(write_still=True)
print("RENDER", out, os.path.getsize(out))

bpy.ops.wm.save_as_mainfile(filepath=FILE)
print("SAVED", FILE, os.path.getsize(FILE), "bytes")

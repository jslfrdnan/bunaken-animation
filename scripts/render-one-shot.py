"""
Render satu shot dengan look, untuk perbaikan cepat.

    "D:\\Blender Foundation\\Blender 5.2\\blender.exe" -b -P scripts/render-one-shot.py -- <shot> <scene_id>

Contoh:
    ... -P scripts/render-one-shot.py -- scene-4_shot-080_nara-dermaga_v001 4
"""

import os
import sys

import bpy

ROOT = r"D:/Tugas Semester 5/Grafika Komputer/Project-Animasi"
sys.path.insert(0, ROOT + "/scripts")
import look  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
if len(argv) < 2:
    raise SystemExit("butuh <shot> <scene_id>")
shot, scene_id = argv[0], argv[1]

path = os.path.join(ROOT, "scenes", shot + ".blend")
bpy.ops.wm.open_mainfile(filepath=path)
scn = bpy.context.scene
scn.render.resolution_x = 1920
scn.render.resolution_y = 1080
scn.render.resolution_percentage = 100
scn.render.fps = 24
scn.view_settings.view_transform = "Standard"
try:
    scn.eevee.taa_render_samples = 16
except Exception:
    pass
look.apply_look(scn, scene_id)
print("LOOK applied", scene_id)

short = shot.split("_shot-")[1].split("_")[0]
out = os.path.join(ROOT, "renders", "film", "frames", f"S{scene_id}_{short}")
os.makedirs(out, exist_ok=True)
scn.render.image_settings.file_format = "PNG"
scn.render.image_settings.color_mode = "RGBA"
scn.render.filepath = out + "/"
bpy.ops.render.render(animation=True)
print("RENDERED", out, scn.frame_end)

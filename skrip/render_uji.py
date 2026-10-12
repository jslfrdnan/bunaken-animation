"""Render uji Scene 1 — dijalankan via Blender background:

    blender -b scene1.blend -P render_uji.py -- <frame_awal> <frame_akhir> <persen> <nama>

Default: shot 3 (perahu, f529-768) @ 50%, output MP4 ke render/scene1/.
Dipakai untuk mengecek gerakan sebelum render penuh.
"""
import sys

import bpy

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
f0 = int(argv[0]) if len(argv) > 0 else 529
f1 = int(argv[1]) if len(argv) > 1 else 768
persen = int(argv[2]) if len(argv) > 2 else 50
nama = argv[3] if len(argv) > 3 else "uji_shot3"

sc = bpy.context.scene
sc.render.resolution_percentage = persen
try:
    sc.eevee.taa_render_samples = 12
except Exception as e:
    print("samples:", e)

# Build Blender ini tanpa FFmpeg, jadi render ke PNG sequence; digabung jadi MP4 di luar.
sc.render.image_settings.file_format = "PNG"
sc.render.image_settings.color_mode = "RGB"

import os
folder = os.path.join(r"D:\Tugas Semester 5\Grafika Komputer\Project\render\scene1", nama)
os.makedirs(folder, exist_ok=True)

sc.frame_start = f0
sc.frame_end = f1
sc.render.filepath = os.path.join(folder, nama + "_")

print(f"[render_uji] {nama}: frame {f0}-{f1} @ {persen}% ({f1 - f0 + 1} frame)")
bpy.ops.render.render(animation=True)
print("[render_uji] SELESAI")

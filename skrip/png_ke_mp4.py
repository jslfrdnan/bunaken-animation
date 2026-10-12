"""Gabung PNG sequence hasil render Blender jadi MP4 pakai OpenCV.

    python png_ke_mp4.py <folder_png> <keluaran.mp4> [fps]

Dipakai karena build Blender di sini tanpa FFmpeg.
"""
import glob
import os
import sys

import cv2

folder = sys.argv[1]
keluar = sys.argv[2]
fps = float(sys.argv[3]) if len(sys.argv) > 3 else 24.0

files = sorted(glob.glob(os.path.join(folder, "*.png")))
if not files:
    raise SystemExit("Tidak ada PNG di " + folder)

first = cv2.imread(files[0])
h, w = first.shape[:2]
vw = cv2.VideoWriter(keluar, cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
for i, f in enumerate(files):
    vw.write(cv2.imread(f))
vw.release()
print(f"OK {len(files)} frame -> {keluar} ({w}x{h} @ {fps}fps)")

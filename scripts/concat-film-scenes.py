"""
Gabungkan frame film final menjadi MP4 per scene (versi v002).

Input : renders/film/frames/S<scene>_<shot>/*.png
Output: renders/scene-<n>/scene-<n>_v002.mp4

Jalankan: python scripts/concat-film-scenes.py
"""

import json
import os
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRAMES = os.path.join(ROOT, "renders", "film", "frames")
FFMPEG = os.path.join(
    ROOT, "motion", "node_modules", "@remotion", "compositor-win32-x64-msvc", "ffmpeg.exe"
)
FFPROBE = FFMPEG.replace("ffmpeg.exe", "ffprobe.exe")

ORDER = {
    "1": ["010", "020", "030", "040", "050", "060", "070", "080", "090", "100"],
    "2": ["010", "020", "030", "040", "050", "060", "070", "080", "090"],
    "3": ["010", "020", "030", "040", "050", "060", "070", "080", "090", "100"],
    "4": ["010", "020", "030", "040", "050", "060", "070", "080", "090"],
}


def scene_frames(scene, shots):
    files = []
    for shot in shots:
        d = os.path.join(FRAMES, f"S{scene}_{shot}")
        if not os.path.isdir(d):
            raise SystemExit(f"frame hilang: {d}")
        files.extend(os.path.join(d, f) for f in sorted(os.listdir(d)) if f.endswith(".png"))
    return files


def main():
    for scene, shots in ORDER.items():
        files = scene_frames(scene, shots)
        outdir = os.path.join(ROOT, "renders", f"scene-{scene}")
        os.makedirs(outdir, exist_ok=True)
        listing = os.path.join(outdir, "concat-v004.txt")
        with open(listing, "w", encoding="utf-8") as fh:
            for path in files:
                fh.write("file '" + path.replace("\\", "/") + "'\n")

        out = os.path.join(outdir, f"scene-{scene}_v004.mp4")
        subprocess.run(
            [FFMPEG, "-y", "-f", "concat", "-safe", "0", "-r", "24", "-i", listing,
             "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
             "-r", "24", "-fps_mode", "cfr", out],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        probe = subprocess.run(
            [FFPROBE, "-v", "error",
             "-show_entries", "format=duration,size",
             "-show_entries", "stream=width,height,nb_frames",
             "-of", "json", out],
            check=True, capture_output=True, text=True,
        )
        info = json.loads(probe.stdout)
        st = info["streams"][0]
        print(f"scene-{scene}: {len(files)} frame -> {os.path.basename(out)} "
              f"{st['width']}x{st['height']} {st.get('nb_frames')}f "
              f"{float(info['format']['duration']):.1f}s "
              f"{int(info['format']['size'])/1e6:.1f} MB")


if __name__ == "__main__":
    main()



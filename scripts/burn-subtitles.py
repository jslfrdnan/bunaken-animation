"""
Bakar subtitle ke frame film lalu gabungkan dengan audio sementara.

Dijalankan setelah `scripts/render-film.py` selesai.

    python scripts/burn-subtitles.py

Input : renders/film/frames/S<scene>_<shot>/*.png
        assets/subtitles/warisan-bunaken_v001.srt
        renders/audio/warisan-bunaken_ambience_v001.wav
Output: renders/film/warisan-bunaken_film_v004.mp4 (2:25, subtitle bakar, audio sementara)

Catatan: ffmpeg di repo ini tidak punya filter `subtitles` (libass), jadi teks
digambar per frame memakai PIL. Cue tagline (2:20) dilewati karena sudah tampil
sebagai kartu teks di shot 090 Scene 4.
"""

import os
import re
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRAMES = os.path.join(ROOT, "renders", "film", "frames")
SUBTITLED = os.path.join(ROOT, "renders", "film", "subtitled")
SRT = os.path.join(ROOT, "assets", "subtitles", "warisan-bunaken_v001.srt")
AUDIO = os.path.join(ROOT, "renders", "audio", "warisan-bunaken_ambience_v001.wav")
OUT = os.path.join(ROOT, "renders", "film", "warisan-bunaken_film_v004.mp4")
FFMPEG = os.path.join(
    ROOT, "motion", "node_modules", "@remotion", "compositor-win32-x64-msvc", "ffmpeg.exe"
)

FPS = 24
SKIP_CUE_AFTER = 139.0  # tagline sudah ada di kartu shot 090

ORDER = [
    ("1", "010"), ("1", "020"), ("1", "030"), ("1", "040"), ("1", "050"),
    ("1", "060"), ("1", "070"), ("1", "080"), ("1", "090"), ("1", "100"),
    ("2", "010"), ("2", "020"), ("2", "030"), ("2", "040"), ("2", "050"),
    ("2", "060"), ("2", "070"), ("2", "080"), ("2", "090"),
    ("3", "010"), ("3", "020"), ("3", "030"), ("3", "040"), ("3", "050"),
    ("3", "060"), ("3", "070"), ("3", "080"), ("3", "090"), ("3", "100"),
    ("4", "010"), ("4", "020"), ("4", "030"), ("4", "040"), ("4", "050"),
    ("4", "060"), ("4", "070"), ("4", "080"), ("4", "090"),
]


def parse_srt(path):
    text = open(path, encoding="utf-8-sig").read().replace("\r\n", "\n")
    cues = []
    for block in text.strip().split("\n\n"):
        lines = [l for l in block.split("\n") if l.strip()]
        if len(lines) < 3:
            continue
        m = re.match(r"(\d+):(\d+):(\d+),(\d+) --> (\d+):(\d+):(\d+),(\d+)", lines[1])
        if not m:
            continue
        h1, m1, s1, ms1, h2, m2, s2, ms2 = (int(v) for v in m.groups())
        start = h1 * 3600 + m1 * 60 + s1 + ms1 / 1000
        end = h2 * 3600 + m2 * 60 + s2 + ms2 / 1000
        cues.append((start, end, lines[2:]))
    return cues


def main():
    cues = [c for c in parse_srt(SRT) if c[0] < SKIP_CUE_AFTER]
    print(f"{len(cues)} cue subtitle dibakar")

    try:
        font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 40)
    except OSError:
        font = ImageFont.load_default()

    shots = []
    for scene, shot in ORDER:
        d = os.path.join(FRAMES, f"S{scene}_{shot}")
        files = sorted(f for f in os.listdir(d) if f.endswith(".png")) if os.path.isdir(d) else []
        if not files:
            sys.exit(f"frame hilang untuk S{scene}_{shot}: {d}")
        shots.append((d, files))

    os.makedirs(SUBTITLED, exist_ok=True)
    index = 0
    for d, files in shots:
        for name in files:
            t = index / FPS
            img = Image.open(os.path.join(d, name)).convert("RGB")
            cue = next((c for c in cues if c[0] <= t < c[1]), None)
            if cue:
                draw = ImageDraw.Draw(img)
                lines = cue[2]
                w, h = img.size
                y = h - 110 - (len(lines) - 1) * 46
                for line in lines:
                    tw = draw.textlength(line, font=font)
                    draw.text(((w - tw) / 2, y), line, font=font, fill=(242, 233, 220),
                              stroke_width=4, stroke_fill=(0, 0, 0))
                    y += 46
            img.save(os.path.join(SUBTITLED, f"{index:06d}.png"))
            index += 1

    print(f"{index} frame ditulis ke {SUBTITLED}")

    cmd = [
        FFMPEG, "-y",
        "-framerate", "24", "-i", os.path.join(SUBTITLED, "%06d.png"),
        "-i", AUDIO,
        "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest", OUT,
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("MP4:", OUT, round(os.path.getsize(OUT) / 1e6, 1), "MB")


if __name__ == "__main__":
    main()




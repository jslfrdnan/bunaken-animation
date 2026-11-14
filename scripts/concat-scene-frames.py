"""
Gabungkan PNG per scene menjadi MP4, lalu verifikasi dengan ffprobe.

Dipakai setelah `scripts/render-scene-shots.py` selesai.

    python scripts/concat-scene-frames.py

Output:
    renders/scene-<n>/scene-<n>_v001.mp4

Tidak menyentuh git. Render tetap di luar repo.
"""

import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RENDERS = os.path.join(ROOT, "renders")
FFMPEG = os.path.join(
    ROOT, "motion", "node_modules", "@remotion", "compositor-win32-x64-msvc", "ffmpeg.exe"
)
FFPROBE = FFMPEG.replace("ffmpeg.exe", "ffprobe.exe")

MANIFEST = {
    "2": [
        "scene-2_shot-010_haris-subuh_v001",
        "scene-2_shot-020_bom_v001",
        "scene-2_shot-030_jaring-dasar_v001",
        "scene-2_shot-040_karang-hancur_v001",
        "scene-2_shot-050_ikan-mati_v001",
    ],
    "3": [
        "scene-3_shot-010_nara-rekam_v001",
        "scene-3_shot-020_rekaman-bukti_v001",
        "scene-3_shot-050_buku-utang_v001",
        "scene-3_shot-100_kalimat-kunci_v001",
    ],
    "4": [
        "scene-4_shot-020_buoy-dipasang_v001",
        "scene-4_shot-030_kerangka-karang_v001",
        "scene-4_shot-070_penyu-kembali_v001",
        "scene-4_shot-080_nara-dermaga_v001", "scene-4_shot-090_tagline_v001",
    ],
}


def frames_for(shot_dir):
    files = [f for f in os.listdir(shot_dir) if f.lower().endswith(".png")]
    return [os.path.join(shot_dir, f) for f in sorted(files)]


def concat_scene(scene_id, shots):
    frame_dir = os.path.join(RENDERS, f"scene-{scene_id}", "frames")
    files = []
    missing = []
    for shot in shots:
        d = os.path.join(frame_dir, shot)
        if not os.path.isdir(d):
            missing.append(shot)
            continue
        got = frames_for(d)
        if not got:
            missing.append(shot)
        files.extend(got)

    if not files:
        print(f"scene-{scene_id}: tidak ada frame, dilewati")
        return None

    listing = os.path.join(RENDERS, f"scene-{scene_id}", "concat.txt")
    os.makedirs(os.path.dirname(listing), exist_ok=True)
    with open(listing, "w", encoding="utf-8") as fh:
        for path in files:
            fh.write("file '" + path.replace("\\", "/") + "'\n")

    out = os.path.join(RENDERS, f"scene-{scene_id}", f"scene-{scene_id}_v001.mp4")
    cmd = [
        FFMPEG, "-y",
        "-f", "concat", "-safe", "0", "-r", "24", "-i", listing,
        "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
        "-r", "24", "-fps_mode", "cfr", out,
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    probe = subprocess.run(
        [FFPROBE, "-v", "error",
         "-show_entries", "format=duration,size",
         "-show_entries", "stream=width,height,r_frame_rate,nb_frames",
         "-of", "json", out],
        check=True, capture_output=True, text=True,
    )
    info = json.loads(probe.stdout)
    stream = info["streams"][0]
    print(f"scene-{scene_id}: {len(files)} frame -> {out}")
    print(f"  {stream['width']}x{stream['height']} {stream['r_frame_rate']} "
          f"{stream.get('nb_frames', '?')} frame "
          f"{float(info['format']['duration']):.3f} s "
          f"{int(info['format']['size'])/1e6:.1f} MB")
    if missing:
        print(f"  shot belum lengkap: {', '.join(missing)}")
    return out


def main():
    if not os.path.exists(FFMPEG):
        sys.exit(f"ffmpeg tidak ditemukan: {FFMPEG}")
    for scene_id, shots in MANIFEST.items():
        concat_scene(scene_id, shots)


if __name__ == "__main__":
    main()


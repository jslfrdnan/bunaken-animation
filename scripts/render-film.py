"""
Render seluruh 38 shot menjadi PNG sequence untuk film 2:25.

Headless:
    "D:\\Blender Foundation\\Blender 5.2\\blender.exe" -b -P scripts/render-film.py

Output: renders/film/frames/S<scene>_<shot>/####.png
"""

import os
import sys
import time

import bpy

ROOT = r"D:/Tugas Semester 5/Grafika Komputer/Project-Animasi"
SCENES = ROOT + "/scenes"
OUT = ROOT + "/renders/film/frames"
LOG = ROOT + "/renders/logs/pipeline.log"

sys.path.insert(0, ROOT + "/scripts")
import look  # noqa: E402

# (scene, shot filename, frame_end override atau None)
SHOTS = [
    ("1", "scene-1_shot-010_bunaken-aerial_v001", None),
    ("1", "scene-1_shot-020_turun-permukaan_v001", None),
    ("1", "scene-1_shot-030_terumbu_v001", None),
    ("1", "scene-1_shot-040_penyu_v001", None),
    ("1", "scene-1_shot-050_nara-dive_v001", None),
    ("1", "scene-1_shot-060_nara-ok_v001", None),
    ("1", "scene-1_shot-070_nara-naik_v001", None),
    ("1", "scene-1_shot-080_daniel-jaring_v001", None),
    ("1", "scene-1_shot-090_anak-dermaga_v001", None),
    ("1", "scene-1_shot-100_nara-ujung-dermaga_v001", None),
    ("2", "scene-2_shot-010_haris-subuh_v001", None),
    ("2", "scene-2_shot-020_bom_v001", None),
    ("2", "scene-2_shot-030_jaring-dasar_v001", None),
    ("2", "scene-2_shot-040_karang-hancur_v001", None),
    ("2", "scene-2_shot-050_ikan-mati_v001", None),
    ("2", "scene-2_shot-060_nara-protes_v001", None),
    ("2", "scene-2_shot-070_warga-membela_v001", 72),
    ("2", "scene-2_shot-080_haris-menjawab_v001", None),
    ("2", "scene-2_shot-090_daniel-naik_v001", None),
    ("3", "scene-3_shot-010_nara-rekam_v001", None),
    ("3", "scene-3_shot-020_rekaman-bukti_v001", None),
    ("3", "scene-3_shot-030_nara-kumpulkan_v001", None),
    ("3", "scene-3_shot-040_konfrontasi_v001", None),
    ("3", "scene-3_shot-050_buku-utang_v001", None),
    ("3", "scene-3_shot-060_haris-diam_v001", None),
    ("3", "scene-3_shot-070_daniel-malu_v001", None),
    ("3", "scene-3_shot-080_nara-rencana_v001", None),
    ("3", "scene-3_shot-090_warga-temui_v001", None),
    ("3", "scene-3_shot-100_kalimat-kunci_v001", None),
    ("4", "scene-4_shot-010_warga-siapkan-buoy_v001", None),
    ("4", "scene-4_shot-020_buoy-dipasang_v001", None),
    ("4", "scene-4_shot-030_kerangka-karang_v001", None),
    ("4", "scene-4_shot-040_haris-keramba_v001", None),
    ("4", "scene-4_shot-050_haris-pemandu_v001", None),
    ("4", "scene-4_shot-060_daniel-ajari_v001", None),
    ("4", "scene-4_shot-070_penyu-kembali_v001", None),
    ("4", "scene-4_shot-080_nara-dermaga_v001", None),
    ("4", "scene-4_shot-090_tagline_v001", None),
]


def log(line):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(f"[{time.strftime('%H:%M')}] {line}\n")
    print(line, flush=True)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    only = argv[0] if argv else None
    if only:
        print("filter scene:", only, flush=True)
    total = 0
    for scene_id, shot, override in SHOTS:
        if only and scene_id != only:
            continue
        path = os.path.join(SCENES, shot + ".blend")
        if not os.path.exists(path):
            log(f"SKIP - {shot}")
            continue
        bpy.ops.wm.open_mainfile(filepath=path)
        scn = bpy.context.scene
        if override is not None:
            scn.frame_end = override
        scn.render.resolution_x = 1920
        scn.render.resolution_y = 1080
        scn.render.resolution_percentage = 100
        scn.render.fps = 24
        scn.render.fps_base = 1.0
        scn.view_settings.view_transform = "Standard"
        try:
            scn.eevee.taa_render_samples = 16
        except Exception:
            pass
        try:
            if "tagline" in shot:
                log(f"LOOK-SKIP - {shot} kartu teks hitam")
            else:
                look.apply_look(scn, scene_id)
                log(f"LOOK - {shot} memakai look scene-{scene_id}")
        except Exception as exc:
            log(f"LOOK-WARN - {shot}: {exc}")
        scn.render.image_settings.file_format = "PNG"
        scn.render.image_settings.color_mode = "RGBA"
        out = os.path.join(OUT, f"S{scene_id}_{shot.split('_shot-')[1].split('_')[0]}")
        os.makedirs(out, exist_ok=True)
        scn.render.filepath = out + "/"

        t0 = time.time()
        bpy.ops.render.render(animation=True)
        frames = scn.frame_end - scn.frame_start + 1
        total += frames
        log(f"RENDER - {shot} {frames}f {time.time() - t0:.0f}s (total {total})")

    log(f"ALL-DONE total {total} frame")


main()

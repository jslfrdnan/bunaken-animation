"""
Render PNG sequence untuk shot-shot yang sudah ada, per scene.

Dipakai lewat Blender headless (bukan MCP):

    "D:\\Blender Foundation\\Blender 5.2\\blender.exe" -b -P scripts/render-scene-shots.py

Aman memakai open_mainfile di sini karena prosesnya terpisah dari sesi MCP.

Output:
  renders/scene-<n>/frames/<nama-shot>/####.png
  renders/scene-<n>/render-report.txt
"""

import json
import os
import time

import bpy

ROOT = r"D:/Tugas Semester 5/Grafika Komputer/Project-Animasi"
SCENES = ROOT + "/scenes"
RENDERS = ROOT + "/renders"

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
        "scene-4_shot-080_nara-dermaga_v001",
    ],
}


def log(line):
    path = os.path.join(RENDERS, "logs", "pipeline.log")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    stamp = time.strftime("%H:%M")
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(f"[{stamp}] {line}\n")
    print(line, flush=True)


def render_shot(scene_id, shot):
    path = os.path.join(SCENES, shot + ".blend")
    if not os.path.exists(path):
        log(f"SKIP - {shot} tidak ada")
        return None

    bpy.ops.wm.open_mainfile(filepath=path)
    scn = bpy.context.scene
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
    scn.render.image_settings.file_format = "PNG"
    scn.render.image_settings.color_mode = "RGBA"
    out = os.path.join(RENDERS, f"scene-{scene_id}", "frames", shot)
    os.makedirs(out, exist_ok=True)
    scn.render.filepath = out + "/"

    start = time.time()
    bpy.ops.render.render(animation=True)
    dur = time.time() - start
    frames = scn.frame_end - scn.frame_start + 1
    log(f"RENDER - {shot} {frames} frame {dur:.0f}s")
    return {"shot": shot, "frames": frames, "seconds": round(dur)}


def main():
    report = {}
    for scene_id, shots in MANIFEST.items():
        log(f"PLAN - scene-{scene_id} {len(shots)} shot")
        rows = []
        for shot in shots:
            info = render_shot(scene_id, shot)
            if info:
                rows.append(info)
        report[scene_id] = rows
        total = sum(r["frames"] for r in rows)
        log(f"DONE - scene-{scene_id} {len(rows)} shot {total} frame")

        outdir = os.path.join(RENDERS, f"scene-{scene_id}")
        os.makedirs(outdir, exist_ok=True)
        with open(os.path.join(outdir, "render-report.txt"), "w", encoding="utf-8") as fh:
            fh.write(json.dumps(rows, indent=2))

    log("ALL-DONE")


main()

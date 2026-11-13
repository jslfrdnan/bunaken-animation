"""
Merakit master per scene dari file shot (satu scene per shot).

    "D:\\Blender Foundation\\Blender 5.2\\blender.exe" -b -P scripts/build-scene-masters.py

Hasil:
    scenes/scene-2_master_v001.blend
    scenes/scene-3_master_v001.blend
    scenes/scene-4_master_v001.blend

Master hanya berisi scene hasil append; file shot tidak diubah. Kalau sebuah
shot memakai koleksi ter-link dari file aset, dependensi itu tetap tercatat di
master (buka dengan aset di tempat yang sama).
"""

import os

import bpy

ROOT = r"D:/Tugas Semester 5/Grafika Komputer/Project-Animasi"
SCENES = ROOT + "/scenes"

SHOTS = {
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
        "scene-4_shot-090_tagline_v001",
    ],
}


def wipe():
    for db in (
        bpy.data.objects, bpy.data.collections, bpy.data.meshes, bpy.data.materials,
        bpy.data.cameras, bpy.data.lights, bpy.data.worlds, bpy.data.actions,
        bpy.data.armatures, bpy.data.curves, bpy.data.scenes,
    ):
        for block in list(db):
            try:
                db.remove(block)
            except Exception:
                pass


def build(scene_id, shots):
    wipe()
    made = []
    for shot in shots:
        path = os.path.join(SCENES, shot + ".blend")
        if not os.path.exists(path):
            print("SKIP", shot, "tidak ada")
            continue
        with bpy.data.libraries.load(path, link=False) as (src, dst):
            names = list(src.scenes)
            if not names:
                print("SKIP", shot, "tanpa scene")
                continue
            dst.scenes = [names[0]]
        scn = dst.scenes[0]
        if scn is None:
            print("SKIP", shot, "gagal append")
            continue
        short = shot.split("_shot-")[1].split("_")[0]
        scn.name = f"S{scene_id}_{short}"
        made.append((scn.name, len(scn.objects), scn.frame_start, scn.frame_end))
        print("APPEND", shot, "->", scn.name, len(scn.objects), "objek")

    if not made:
        print("GAGAL: tidak ada scene untuk", scene_id)
        return

    out = os.path.join(SCENES, f"scene-{scene_id}_master_v001.blend")
    bpy.ops.wm.save_as_mainfile(filepath=out)
    size = os.path.getsize(out)
    total = sum(row[3] - row[2] + 1 for row in made)
    print(f"SAVED {out} {size} bytes; {len(made)} scene; {total} frame")


def main():
    for scene_id, shots in SHOTS.items():
        build(scene_id, shots)


main()

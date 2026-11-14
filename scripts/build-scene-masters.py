"""
Merakit master per scene dari seluruh file shot (satu scene per shot).

    "D:\\Blender Foundation\\Blender 5.2\\blender.exe" -b -P scripts/build-scene-masters.py

Hasil:
    scenes/scene-1_master_v002.blend
    scenes/scene-2_master_v002.blend
    scenes/scene-3_master_v002.blend
    scenes/scene-4_master_v002.blend

Catatan: scene-1_master_v001 dibuat pada 14 Nov lebih awal (10 shot) dan
dipertahankan sebagai riwayat; v002 memakai penamaan seragam.
"""

import os

import bpy

ROOT = r"D:/Tugas Semester 5/Grafika Komputer/Project-Animasi"
SCENES = ROOT + "/scenes"

SHOTS = {
    "1": [
        "scene-1_shot-010_bunaken-aerial_v001",
        "scene-1_shot-020_turun-permukaan_v001",
        "scene-1_shot-030_terumbu_v001",
        "scene-1_shot-040_penyu_v001",
        "scene-1_shot-050_nara-dive_v001",
        "scene-1_shot-060_nara-ok_v001",
        "scene-1_shot-070_nara-naik_v001",
        "scene-1_shot-080_daniel-jaring_v001",
        "scene-1_shot-090_anak-dermaga_v001",
        "scene-1_shot-100_nara-ujung-dermaga_v001",
    ],
    "2": [
        "scene-2_shot-010_haris-subuh_v001",
        "scene-2_shot-020_bom_v001",
        "scene-2_shot-030_jaring-dasar_v001",
        "scene-2_shot-040_karang-hancur_v001",
        "scene-2_shot-050_ikan-mati_v001",
        "scene-2_shot-060_nara-protes_v001",
        "scene-2_shot-070_warga-membela_v001",
        "scene-2_shot-080_haris-menjawab_v001",
        "scene-2_shot-090_daniel-naik_v001",
    ],
    "3": [
        "scene-3_shot-010_nara-rekam_v001",
        "scene-3_shot-020_rekaman-bukti_v001",
        "scene-3_shot-030_nara-kumpulkan_v001",
        "scene-3_shot-040_konfrontasi_v001",
        "scene-3_shot-050_buku-utang_v001",
        "scene-3_shot-060_haris-diam_v001",
        "scene-3_shot-070_daniel-malu_v001",
        "scene-3_shot-080_nara-rencana_v001",
        "scene-3_shot-090_warga-temui_v001",
        "scene-3_shot-100_kalimat-kunci_v001",
    ],
    "4": [
        "scene-4_shot-010_warga-siapkan-buoy_v001",
        "scene-4_shot-020_buoy-dipasang_v001",
        "scene-4_shot-030_kerangka-karang_v001",
        "scene-4_shot-040_haris-keramba_v001",
        "scene-4_shot-050_haris-pemandu_v001",
        "scene-4_shot-060_daniel-ajari_v001",
        "scene-4_shot-070_penyu-kembali_v001",
        "scene-4_shot-080_nara-dermaga_v001",
        "scene-4_shot-090_tagline_v001",
    ],
}

# durasi khusus (frame_end) — Scene 2 shot 070 adalah 3 detik
OVERRIDE = {("2", "070"): 72}


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
            print("SKIP", shot)
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
        if (scene_id, short) in OVERRIDE:
            scn.frame_end = OVERRIDE[(scene_id, short)]
        made.append((scn.name, len(scn.objects), scn.frame_start, scn.frame_end))
        print("APPEND", shot, "->", scn.name, len(scn.objects), "objek")

    if not made:
        print("GAGAL", scene_id)
        return

    out = os.path.join(SCENES, f"scene-{scene_id}_master_v002.blend")
    bpy.ops.wm.save_as_mainfile(filepath=out)
    total = sum(row[3] - row[2] + 1 for row in made)
    print(f"SAVED {out} {os.path.getsize(out)} bytes; {len(made)} scene; {total} frame")


def main():
    for scene_id, shots in SHOTS.items():
        build(scene_id, shots)


main()

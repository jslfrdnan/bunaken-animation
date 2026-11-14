"""
Membangun shot Scene 3 yang tidak membutuhkan model karakter.

Saat ini: shot 020 — POV kamera bawah air: jaring dasar, karang patah, puing.
(Skenario penuh: Nara merekam bukti; shot 010 & 100 butuh rig, menyusul.)

Hasil: scenes/scene-3_shot-020_rekaman-bukti_v001.blend

Helper diimpor dari `scripts/build-scene-4-shots.py` supaya tidak duplikat:
wipe, setup_scene, append_collection, material, kamera, dan penyimpanan.

Cara pakai di Blender MCP:
    path = r".../scripts/build-scene-3-shots.py"
    exec(compile(open(path).read(), path, "exec"), {"__name__": "__main__"})
"""

import importlib.util
import math
import os

import bpy
from mathutils import Vector

ROOT = r"D:/Tugas Semester 5/Grafika Komputer/Project-Animasi"
ASSETS = ROOT + "/assets"

_spec = importlib.util.spec_from_file_location(
    "shot_lib", ROOT + "/scripts/build-scene-4-shots.py"
)
lib = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(lib)

PAL = lib.PAL


def build_020():
    lib.wipe()
    scn = lib.setup_scene("scene-3_shot-020_rekaman-bukti")

    sand = lib.material("MAT_seabed_sand", PAL["sand"], roughness=0.94)
    lib.make_plane("ENV_seabed", 40.0, 0.0, sand)

    # Puing karang tersebar di jalur kamera.
    rubble = lib.append_collection(ASSETS + "/env/reef-damaged.blend", "ENV_reef-damaged")
    lib.purge_lights_cameras(rubble)
    layout = {
        "ENV_reef_damaged-rubble_a": ((1.6, -2.2, 0.0), 18),
        "ENV_reef_damaged-rubble_b": ((-1.9, -0.8, 0.0), -35),
        "ENV_reef_damaged-rubble_c": ((0.6, 1.2, 0.0), 62),
        "ENV_reef_damaged-bomb": ((-4.2, 1.6, 0.0), 8),
        "ENV_reef_damaged-net": ((3.4, 0.4, 0.0), -22),
    }
    for name, (loc, rz) in layout.items():
        obj = bpy.data.objects.get(name)
        if obj:
            obj.location = loc
            obj.rotation_euler = (0.0, 0.0, math.radians(rz))

    # Jaring terbentang menutupi puing di depan kamera.
    net = lib.append_collection(ASSETS + "/props/fishing-net-spread.blend", "PRP_gear")
    lib.purge_lights_cameras(net)
    net = lib.live_objects(net)
    for obj in net:
        obj.location = (0.2, -1.1, 0.28)
        obj.rotation_euler = (math.radians(7), math.radians(-4), math.radians(14))
        obj.scale = (1.25, 1.25, 1.0)

    # Karang hidup di latar, penyu placeholder dibuang.
    reef = lib.append_collection(ASSETS + "/env/reef.blend", "ENV_reef")
    lib.purge_lights_cameras(reef)
    for name in list(bpy.data.objects.keys()):
        if name.startswith("ENV_reef_turtle"):
            bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)
    reef = lib.live_objects(reef)
    for obj in reef:
        if obj.name.startswith(("ENV_reef_branching", "ENV_reef_boulder", "ENV_reef_table")):
            obj.location = (obj.location.x + 5.5, obj.location.y + 6.0, obj.location.z)
            obj.scale = (2.0, 2.0, 2.0)
        elif obj.name.startswith("ENV_reef_fish"):
            obj.location = (obj.location.x - 2.0, obj.location.y + 4.0, obj.location.z + 1.2)

    lib.add_world("WLD_s3-020", "#0F5C63", strength=1.7)
    lib.add_sun(energy=4.4, angle_deg=9.0, rot=(22, 0, 12))
    lib.add_fill(energy=120.0, size=7.0, loc=(-3, -5, 4.5), target=(0, 0, 0.5))

    # POV: kamera rendah, lensa lebar, menyusur pelan ke depan.
    cam = lib.make_camera("CAM_shot-020", (0.0, -5.8, 1.05), (0.0, -1.0, 0.45), lens=24.0)
    lib.key_camera(
        cam, 1, 96,
        (0.05, -5.9, 1.10), (-0.05, -0.4, 0.95),
        (0.0, -1.2, 0.40), (0.0, 3.4, 0.50),
    )

    lib.report("s3-020", [o for o in bpy.data.objects if o.type == "MESH"], scn)
    lib.save_and_preview(
        "s3-020", "scene-3_shot-020_rekaman-bukti_v001.blend", preview_frame=48
    )


def main():
    build_020()


if __name__ == "__main__":
    main()

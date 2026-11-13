"""
Membangun shot 090 Scene 4: kartu tagline di atas hitam (4 detik).

Hasil: scenes/scene-4_shot-090_tagline_v001.blend

Teks: "Laut yang dijaga adalah warisan, bukan tambang."
Aturan PROJECT.md Â§1.6: tagline hanya sekali, di akhir Scene 4.

Jalankan headless:
    "D:\\Blender Foundation\\Blender 5.2\\blender.exe" -b -P scripts/build-tagline-card.py

Atau lewat Blender MCP dengan exec(compile(...)).
"""

import os

import bpy

ROOT = r"D:/Tugas Semester 5/Grafika Komputer/Project-Animasi"
SCENES = ROOT + "/scenes"
STILLS = ROOT + "/renders/stills"

LINE_1 = "Laut yang dijaga adalah warisan,"
LINE_2 = "bukan tambang."


def wipe():
    for db in (
        bpy.data.objects, bpy.data.collections, bpy.data.meshes, bpy.data.materials,
        bpy.data.cameras, bpy.data.lights, bpy.data.worlds, bpy.data.actions,
        bpy.data.curves, bpy.data.images,
    ):
        for block in list(db):
            try:
                db.remove(block)
            except Exception:
                pass


def srgb(hexstr):
    h = hexstr.lstrip("#")
    vals = [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]

    def lin(u):
        return u / 12.92 if u <= 0.04045 else ((u + 0.055) / 1.055) ** 2.4

    return tuple(lin(v) for v in vals) + (1.0,)


def main():
    wipe()
    scn = bpy.context.scene
    scn.name = "scene-4_shot-090_tagline"
    scn.render.resolution_x = 1920
    scn.render.resolution_y = 1080
    scn.render.resolution_percentage = 100
    scn.render.fps = 24
    scn.render.fps_base = 1.0
    scn.view_settings.view_transform = "Standard"
    scn.frame_start = 1
    scn.frame_end = 96
    scn.frame_set(1)
    try:
        scn.eevee.taa_render_samples = 16
    except Exception:
        pass

    world = bpy.data.worlds.new("WLD_tagline")
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.0, 0.0, 0.0, 1.0)
    bg.inputs["Strength"].default_value = 0.0
    scn.world = world

    mat = bpy.data.materials.new("MAT_tagline")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    emis = nt.nodes.new("ShaderNodeEmission")
    emis.inputs["Color"].default_value = srgb("#F2E9DC")
    emis.inputs["Strength"].default_value = 1.0
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(emis.outputs["Emission"], out.inputs["Surface"])

    curve = bpy.data.curves.new("TXT_tagline", type="FONT")
    curve.body = LINE_1 + "\n" + LINE_2
    curve.align_x = "CENTER"
    curve.align_y = "CENTER"
    curve.size = 0.62
    curve.space_line = 0.95
    txt = bpy.data.objects.new("TXT_tagline", curve)
    txt.data.materials.append(mat)
    scn.collection.objects.link(txt)
    txt.location = (0.0, 0.06, 0.0)

    # garis aksen tipis di bawah teks
    line_mesh = bpy.data.meshes.new("TXT_rule")
    line_mesh.from_pydata([(-3.2, 0, 0), (3.2, 0, 0), (3.2, 0.04, 0), (-3.2, 0.04, 0)],
                          [], [(0, 1, 2, 3)])
    line_mesh.materials.append(mat)
    line_mesh.update()
    rule = bpy.data.objects.new("TXT_rule", line_mesh)
    rule.location = (0.0, -1.35, 0.0)
    scn.collection.objects.link(rule)

    cam_data = bpy.data.cameras.new("CAM_shot-090")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = 16.0
    cam = bpy.data.objects.new("CAM_shot-090", cam_data)
    cam.location = (0.0, 0.0, 12.0)
    cam.rotation_euler = (0.0, 0.0, 0.0)
    scn.collection.objects.link(cam)
    scn.camera = cam

    os.makedirs(STILLS, exist_ok=True)
    path = os.path.join(SCENES, "scene-4_shot-090_tagline_v001.blend")
    bpy.ops.wm.save_as_mainfile(filepath=path)
    print("SAVED:", path, os.path.getsize(path), "bytes")

    scn.render.resolution_percentage = 50
    scn.render.image_settings.file_format = "PNG"
    out_path = os.path.join(STILLS, "anim-s4-090_v001.png")
    scn.render.filepath = out_path[:-4]
    bpy.ops.render.render(write_still=True)
    print("RENDER:", out_path, os.path.getsize(out_path) if os.path.exists(out_path) else "MISSING")


main()


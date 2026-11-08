"""
Render pratinjau aset vegetation.blend.

Jalankan dari root repo:
    "D:\\Blender Foundation\\Blender 5.2\\blender.exe" -b assets\\env\\vegetation.blend ^
        --python scripts\\render-vegetation-preview.py

Hasil (tidak masuk git):
    renders/stills/vegetation-palm.png
    renders/stills/vegetation-mangrove.png
    renders/stills/vegetation-both.png
"""

import bpy
import math
import os
from mathutils import Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "renders", "stills")
os.makedirs(OUT_DIR, exist_ok=True)

scene = bpy.context.scene

# engine: nama identifier berubah antar versi, coba yang tersedia
for candidate in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
    try:
        scene.render.engine = candidate
        break
    except TypeError:
        continue
print("ENGINE", scene.render.engine)

scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"
scene.render.film_transparent = False
scene.render.resolution_percentage = 100
try:
    scene.eevee.taa_render_samples = 48
except AttributeError:
    pass


def simple_material(name, hexcol, roughness, metallic=0.0):
    def srgb(h):
        h = h.lstrip("#")
        values = [int(h[i : i + 2], 16) / 255.0 for i in (0, 2, 4)]

        def lin(u):
            return u / 12.92 if u <= 0.04045 else ((u + 0.055) / 1.055) ** 2.4

        return tuple(lin(v) for v in values) + (1.0,)

    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = srgb(hexcol)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    mat.diffuse_color = srgb(hexcol)
    return mat


def add_plane(name, center, size, mat):
    cx, cy, cz = center
    sx, sy = size
    verts = [
        (cx - sx / 2, cy - sy / 2, cz),
        (cx + sx / 2, cy - sy / 2, cz),
        (cx + sx / 2, cy + sy / 2, cz),
        (cx - sx / 2, cy + sy / 2, cz),
    ]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], [(0, 1, 2, 3)])
    mesh.update()
    mesh.materials.append(mat)
    obj = bpy.data.objects.new(name, mesh)
    scene.collection.objects.link(obj)
    return obj


add_plane(
    "PREVIEW_sand",
    (0.0, 0.0, -0.02),
    (12.0, 26.0),
    simple_material("MAT_preview_sand", "#E8D5B0", 0.95),
)
add_plane(
    "PREVIEW_water",
    (14.0, 0.0, -0.06),
    (18.0, 26.0),
    simple_material("MAT_preview_water", "#1FA3A3", 0.28),
)

# cahaya isi supaya sisi teduh tidak hitam
fill_data = bpy.data.lights.new("PREVIEW_fill", type="AREA")
fill_data.energy = 900.0
fill_data.size = 14.0
fill_data.color = (0.85, 0.93, 1.0)
fill = bpy.data.objects.new("PREVIEW_fill", fill_data)
scene.collection.objects.link(fill)
fill.location = (-8.0, -10.0, 7.0)
direction = Vector((6.0, 0.0, 3.0)) - fill.location
fill.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()

cam = bpy.data.objects["CAM_preview"]
scene.camera = cam


def shoot(path, location, target, lens, width, height):
    cam.location = location
    cam.data.lens = lens
    direction = Vector(target) - Vector(location)
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("WROTE", path)


shoot(
    os.path.join(OUT_DIR, "vegetation-palm.png"),
    (10.5, -15.5, 8.0),
    (0.0, 0.0, 5.0),
    38.0,
    1400,
    1000,
)
shoot(
    os.path.join(OUT_DIR, "vegetation-mangrove.png"),
    (23.5, -10.5, 4.8),
    (14.0, 0.0, 2.5),
    55.0,
    1400,
    1000,
)
shoot(
    os.path.join(OUT_DIR, "vegetation-both.png"),
    (7.0, -24.0, 9.5),
    (7.0, 0.0, 4.2),
    36.0,
    1700,
    1000,
)
shoot(
    os.path.join(OUT_DIR, "vegetation-palm-crown.png"),
    (4.5, -8.5, 10.2),
    (0.6, 0.0, 8.1),
    50.0,
    1400,
    1000,
)

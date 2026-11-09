"""Build assets/env/surface-vegetation.blend from the current surface.blend.

The surface file already contains the palm + mangrove meshes (ENV_surface_palm_*
and ENV_surface_mangrove_*). This script reuses those meshes: palms along the
coast, mangroves at the shoreline, and a denser background mangrove layer using
a decimated LOD of the existing mangrove mesh.

Run from the repo root:
    blender -b assets/env/surface.blend --python scripts/build-surface-vegetation.py

The saved file keeps no world: the final surface world comes from
assets/look/scene-1-look.blend.
"""
import bpy
import math
import os
import random
from mathutils import Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SURFACE = os.path.join(ROOT, "assets", "env", "surface.blend")
OUT = os.path.join(ROOT, "assets", "env", "surface-vegetation.blend")
QA_RENDER = r"C:\Users\Lenovo\AppData\Local\Temp\opencode\qa_surface-vegetation.png"

SEED = 20261108
random.seed(SEED)

# ------------------------------------------------------------------ open surface
bpy.ops.wm.open_mainfile(filepath=SURFACE)
scene = bpy.context.scene
island = bpy.data.objects["ENV_surface_island"]
manado = bpy.data.objects["ENV_surface_manado-tua"]

# the current surface already has palms + mangroves from the vegetation pass
palm_src = next(o for o in bpy.data.objects if o.name.startswith("ENV_surface_palm_"))
mangrove_src = next(o for o in bpy.data.objects if o.name.startswith("ENV_surface_mangrove_"))
print("source palm", palm_src.name, "mesh", palm_src.data.name)
print("source mangrove", mangrove_src.name, "mesh", mangrove_src.data.name)

# ------------------------------------------------------------------ new file
bpy.ops.wm.save_as_mainfile(filepath=OUT)
scene.name = "surface-vegetation"
print("created", OUT)

# ------------------------------------------------------------------ collections
for name in ("ENV_veg_assets", "ENV_veg_canopy", "ENV_veg_mangrove-bg",
             "ENV_veg_palms", "ENV_veg_mangroves"):
    if name in bpy.data.collections:
        bpy.data.collections.remove(bpy.data.collections[name])
assets = bpy.data.collections.new("ENV_veg_assets")
bg_coll = bpy.data.collections.new("ENV_veg_mangrove-bg")
palm_coll = bpy.data.collections.new("ENV_veg_palms")
mangrove_coll = bpy.data.collections.new("ENV_veg_mangroves")
for c in (assets, bg_coll, palm_coll, mangrove_coll):
    scene.collection.children.link(c)


# ------------------------------------------------------------------ templates
# palm / mangrove: reuse the meshes already in surface.blend
palm_template = bpy.data.objects.new("ENV_veg_palm-template", palm_src.data)
palm_template.location = (0, 0, 0)
assets.objects.link(palm_template)

mangrove_template = bpy.data.objects.new("ENV_veg_mangrove-template", mangrove_src.data)
mangrove_template.location = (0, 0, 0)
assets.objects.link(mangrove_template)

# background mangrove: use the existing mangrove mesh at a decimated LOD so
# 1.000+ background trees stay light. The silhouette is still the mangrove.
bg_me = mangrove_src.data.copy()
bg_me.name = "ENV_veg_mangrove-bg"
bg_template = bpy.data.objects.new("ENV_veg_mangrove-bg-template", bg_me)
assets.objects.link(bg_template)

mod = bg_template.modifiers.new("decimate", "DECIMATE")
mod.ratio = 0.25
depsgraph = bpy.context.evaluated_depsgraph_get()
dec_me = bpy.data.meshes.new_from_object(bg_template.evaluated_get(depsgraph))
bg_template.modifiers.remove(mod)
bg_template.data = dec_me
dec_me.name = "ENV_veg_mangrove-bg"
if bg_me.users == 0:
    bpy.data.meshes.remove(bg_me)
print("background mangrove template verts", len(dec_me.vertices),
      "faces", len(dec_me.polygons),
      "mats", [m.name for m in dec_me.materials])

# ------------------------------------------------------------------ placement
grid_bg, grid_palm, grid_mangrove = {}, {}, {}


def too_close(grid, x, y, dist):
    cell = 12.0
    cx, cy = int(x // cell), int(y // cell)
    d2 = dist * dist
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for px, py in grid.get((cx + dx, cy + dy), ()):
                if (x - px) ** 2 + (y - py) ** 2 < d2:
                    return True
    return False


def add_grid(grid, x, y):
    cell = 12.0
    grid.setdefault((int(x // cell), int(y // cell)), []).append((x, y))


# the existing surface palms/mangroves must not get a duplicate on top of them
for o in bpy.data.objects:
    if o.name.startswith("ENV_surface_palm_"):
        add_grid(grid_palm, o.location.x, o.location.y)
    elif o.name.startswith("ENV_surface_mangrove_"):
        add_grid(grid_mangrove, o.location.x, o.location.y)


def blocked_village(x, y):
    if -8 <= x <= 8 and -112 <= y <= 10:        # pier
        return True
    if -8 <= x <= 38 and -8 <= y <= 24:         # dive shop + annex
        return True
    if -42 <= x <= 60 and 4 <= y <= 44:         # village houses
        return True
    return False


def surface(obj, x, y):
    lx, ly = x - obj.location.x, y - obj.location.y
    hit, loc, normal, idx = obj.ray_cast(
        Vector((lx, ly, 1500.0)), Vector((0, 0, -1)), distance=5000)
    if not hit:
        return None
    poly = obj.data.polygons[idx]
    return (loc.x + obj.location.x, loc.y + obj.location.y, loc.z + obj.location.z,
            normal.z, poly.material_index)


def scatter(obj, bbox, target, kind, max_tries):
    count = 0
    tries = 0
    while count < target and tries < max_tries:
        tries += 1
        x = random.uniform(bbox[0], bbox[2])
        y = random.uniform(bbox[1], bbox[3])
        hit = surface(obj, x, y)
        if hit is None:
            continue
        wx, wy, wz, nz, mat = hit

        if kind == "mangrove_bg":
            if mat != 0 or nz < 0.55 or wz < 0.35:
                continue
            if obj is island and blocked_village(wx, wy):
                continue
            if too_close(grid_palm, wx, wy, 6.0):
                continue
            if too_close(grid_mangrove, wx, wy, 6.0):
                continue
            if too_close(grid_bg, wx, wy, 10.0):
                continue
            p = 0.85 if wz < 15 else (0.50 if wz < 50 else 0.25)
            if obj is island and (wx * wx + wy * wy) < 800 ** 2:
                p = min(0.95, p + 0.10)
            if random.random() > p:
                continue
            s = random.uniform(1.80, 2.80)
            inst = bg_template.copy()
            inst.name = f"ENV_veg_mangrove-bg_{count:04d}"
            bg_coll.objects.link(inst)
            inst.location = (wx, wy, wz - 0.05)
            inst.rotation_euler = (random.uniform(-0.03, 0.03),
                                   random.uniform(-0.03, 0.03),
                                   random.uniform(0, math.tau))
            inst.scale = (s, s, s)
            add_grid(grid_bg, wx, wy)
            count += 1

        elif kind == "palm":
            if mat != 0 or nz < (0.75 if obj is island else 0.55) or wz < 0.35:
                continue
            if obj is island and blocked_village(wx, wy):
                continue
            if too_close(grid_palm, wx, wy, 9.5):
                continue
            if too_close(grid_bg, wx, wy, 7.0):
                continue
            p = 0.75 if wz < 20 else (0.35 if wz < 60 else 0.12)
            if obj is island and (wx * wx + wy * wy) < 900 ** 2:
                p = min(0.9, p + 0.10)
            if random.random() > p:
                continue
            s = random.uniform(1.45, 1.75)
            inst = palm_template.copy()
            inst.name = f"ENV_veg_palm_{count:04d}"
            palm_coll.objects.link(inst)
            inst.location = (wx, wy, wz - 0.03)
            inst.rotation_euler = (random.uniform(-0.05, 0.05),
                                   random.uniform(-0.05, 0.05),
                                   random.uniform(0, math.tau))
            inst.scale = (s, s, s)
            add_grid(grid_palm, wx, wy)
            count += 1

        elif kind == "mangrove":
            if mat != 1 or nz < 0.90 or wz > 0.45:
                continue
            if abs(wx) < 150 and wy > -80:
                continue
            if too_close(grid_mangrove, wx, wy, 5.0):
                continue
            s = random.uniform(0.80, 1.15)
            inst = mangrove_template.copy()
            inst.name = f"ENV_veg_mangrove_{count:04d}"
            mangrove_coll.objects.link(inst)
            inst.location = (wx, wy, wz - 0.05)
            inst.rotation_euler = (random.uniform(-0.03, 0.03),
                                   random.uniform(-0.03, 0.03),
                                   random.uniform(0, math.tau))
            inst.scale = (s, s, s)
            add_grid(grid_mangrove, wx, wy)
            count += 1
    print(f"{kind}: {count} placed ({tries} tries)")
    return count


bunaken_bbox = (-1624, -2439, 3175, 1494)
manado_bbox = (-7154, -238, -3584, 3062)
scatter(island, bunaken_bbox, 300, "palm", 60000)
scatter(island, bunaken_bbox, 40, "mangrove", 60000)
scatter(island, bunaken_bbox, 1200, "mangrove_bg", 120000)
scatter(manado, manado_bbox, 60, "palm", 30000)
scatter(manado, manado_bbox, 250, "mangrove_bg", 60000)

# hide templates only after the instances have been created
for tmpl in (palm_template, mangrove_template, bg_template):
    tmpl.hide_render = True
    tmpl.hide_viewport = True
    try:
        tmpl.hide_set(True)
    except Exception:
        pass

# ------------------------------------------------------------------ preview camera
cam_data = bpy.data.cameras.new("CAM_env-preview")
cam = bpy.data.objects.new("CAM_env-preview", cam_data)
scene.collection.objects.link(cam)
cam.location = (120, -220, 50)
target = Vector((0, 55, 8))
cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
cam_data.lens = 45
cam_data.clip_start = 0.5
cam_data.clip_end = 30000
scene.camera = cam

# ------------------------------------------------------------------ save
# Save the assembled environment. The QA render is a separate step so a render
# crash can never cost the scatter pass.
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 1920
scene.render.resolution_y = 1080
scene.render.resolution_percentage = 100
scene.view_settings.view_transform = "Standard"
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = "//"
bpy.ops.wm.save_as_mainfile(filepath=OUT)
print("SAVED", OUT)
print("objects", len(bpy.data.objects), "materials", len(bpy.data.materials))
print("collections", [c.name for c in bpy.data.collections])

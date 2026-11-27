"""build-look-v004.py — Scene 1 look dev v004 (air anti-moiré + atmosfer bawah laut).

Dijalankan HEADLESS:

    blender -b -P scripts/build-look-v004.py

Masukan  : assets/look/scene-1-look_v003.blend  (dibuka, TIDAK ditimpa)
Keluaran : assets/look/scene-1-look_v004.blend

Isi v004:
1. `SHD_water-surface_v002` (dan kembarannya `SHD_water-surface`) diperbaiki:
   - Mapping 1/160 -> 1/220  (panjang gelombang ripple 4 m -> 5,5 m)
   - Bump_ripple strength 0,15 -> 0,07 (Filter Width 0,5)
   - Principled roughness 0,12 -> 0,16
   - filter normal 0,5 px lewat input "Filter Width" node Bump (di Blender 5.2
     tidak ada node Blur di node tree shader; hanya compositor)
   - Base color tetap #1FA3A3
2. `SHD_seabed_caustics` — pasir + pola caustic prosedural (Voronoi + Wave,
   mix additive 0,18, plus peredam 0,45 di lembah pola supaya tetap terbaca di
   bawah sinar kuat). Tanpa tekstur gambar.
3. Koleksi `FX_atmosphere` (induk `FX_atmosphere_root`):
   - 3 `FX_godray_card_01..03` — cone emissive tipis 12 m, lebar 2–3,2 m,
     warna krem #F2E9DC, emission 0,6, alpha memudar di ujung.
   - `FX_particles` — satu mesh 200 bola r 1–2 cm di volume 20 x 20 x 8 m.
   - 2 `FX_fog_card_01/02` — bidang semi-transparan alpha 0,08 (kedalaman).

Tanpa tekstur gambar, tanpa World Volume (EEVEE 5.2 -> frame hitam).
"""

from __future__ import annotations

import math
import os
import random

import bmesh
import bpy
from mathutils import Matrix, Vector

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(REPO_ROOT, "assets", "look", "scene-1-look_v003.blend")
DST = os.path.join(REPO_ROOT, "assets", "look", "scene-1-look_v004.blend")

FX_COLLECTION = "FX_atmosphere"

# --- palette PROJECT.md §2 (sRGB -> linear) ---
C_TEAL = (0.0137, 0.3663, 0.3663)        # #1FA3A3
C_TEAL_DEEP = (0.0048, 0.1070, 0.1248)   # #0F5C63
C_SAND = (0.8070, 0.6654, 0.4342)        # #E8D5B0
C_CREAM = (0.8880, 0.8150, 0.7160)       # #F2E9DC

WATER_MATS = ("SHD_water-surface_v002", "SHD_water-surface")
MAPPING_SCALE = 1.0 / 220.0
BUMP_RIPPLE_STRENGTH = 0.07
FILTER_WIDTH_PX = 0.5      # lebar filter normal di node Bump (piksel)


# ------------------------------------------------------------------ helper ---

def node_by_name(tree, name):
    return next((n for n in tree.nodes if n.name == name), None)


def principled(tree):
    return next((n for n in tree.nodes if n.type == "BSDF_PRINCIPLED"), None)


def clear_nodes(mat):
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    return nt


def set_blended(mat):
    """Transparansi EEVEE Next (5.2): surface_render_method BLENDED."""
    if hasattr(mat, "surface_render_method"):
        mat.surface_render_method = "BLENDED"
    if hasattr(mat, "blend_method"):
        try:
            mat.blend_method = "BLEND"
        except TypeError:
            pass
    if hasattr(mat, "use_transparent_shadow"):
        mat.use_transparent_shadow = False
    mat.use_backface_culling = False
    mat.use_fake_user = True


def new_material(name):
    mat = bpy.data.materials.get(name)
    if mat is not None:
        bpy.data.materials.remove(mat)
    mat = bpy.data.materials.new(name)
    mat.use_fake_user = True
    return mat


# ------------------------------------------------------- 1. perbaikan air ---

def patch_water(mat_name):
    mat = bpy.data.materials.get(mat_name)
    if mat is None or not mat.use_nodes:
        print("SKIP air:", mat_name)
        return None
    nt = mat.node_tree
    mapping = node_by_name(nt, "Mapping_wave-scale")
    bump_ripple = node_by_name(nt, "Bump_ripple")
    bsdf = principled(nt)
    if mapping is None or bump_ripple is None or bsdf is None:
        print("WARN node tidak lengkap:", mat_name)
        return None

    mapping.inputs["Scale"].default_value = (MAPPING_SCALE,) * 3
    bump_ripple.inputs["Strength"].default_value = BUMP_RIPPLE_STRENGTH
    bump_ripple.inputs["Distance"].default_value = 6.0
    # Filter normal: di Blender 5.2 tidak ada node "Blur" di node tree shader
    # (hanya ada di compositor), jadi filter 0,35 px diterapkan lewat input
    # "Filter Width" milik node Bump — input itu memang lebar filter dalam piksel
    # untuk turunan height, jadi efeknya sama: normal dihaluskan per piksel.
    if "Filter Width" in bump_ripple.inputs:
        bump_ripple.inputs["Filter Width"].default_value = FILTER_WIDTH_PX
    bump_swell = node_by_name(nt, "Bump_swell")
    if bump_swell is not None and "Filter Width" in bump_swell.inputs:
        bump_swell.inputs["Filter Width"].default_value = 0.6
    bsdf.inputs["Roughness"].default_value = 0.16

    # base color tetap #1FA3A3 (input A dari Mix_trough, kalau ada)
    mix = node_by_name(nt, "Mix_trough")
    if mix is not None:
        for sock in mix.inputs:
            if sock.type == "RGBA" and sock.identifier == "A_Color":
                sock.default_value = (*C_TEAL, 1.0)

    # Norma dari Bump_ripple -> Principled.Normal (tanpa node tambahan; filter
    # ditangani Filter Width di atas). Rantai lama dibersihkan supaya idempoten.
    for link in list(nt.links):
        if link.to_node == bsdf and link.to_socket.name == "Normal":
            nt.links.remove(link)
    nt.links.new(bump_ripple.outputs["Normal"], bsdf.inputs["Normal"])

    print("AIR", mat_name, "mapping", round(MAPPING_SCALE, 6),
          "bump_ripple", BUMP_RIPPLE_STRENGTH, "rough", 0.16,
          "filter_width", FILTER_WIDTH_PX)
    return mat


# ------------------------------------------------- 2. material caustic pasir ---

def build_caustics_material():
    mat = new_material("SHD_seabed_caustics")
    nt = clear_nodes(mat)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.location = (700, 0)
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (420, 0)
    bsdf.inputs["Roughness"].default_value = 0.85
    bsdf.inputs["Specular IOR Level"].default_value = 0.25
    bsdf.inputs["Metallic"].default_value = 0.0

    coord = nt.nodes.new("ShaderNodeTexCoord")
    coord.location = (-1100, 0)
    mapping = nt.nodes.new("ShaderNodeMapping")
    mapping.name = "Mapping_caustic"
    mapping.location = (-920, 0)
    mapping.inputs["Scale"].default_value = (0.16, 0.16, 0.16)   # 1/6,25 m

    # --- pola 1: Voronoi (garis sel = jaring caustic) ---
    vor = nt.nodes.new("ShaderNodeTexVoronoi")
    vor.name = "Voronoi_caustic"
    vor.location = (-720, 160)
    vor.voronoi_dimensions = "3D"
    vor.feature = "DISTANCE_TO_EDGE"
    vor.inputs["Scale"].default_value = 6.0
    if "Randomness" in vor.inputs:
        vor.inputs["Randomness"].default_value = 1.0

    vor_ramp = nt.nodes.new("ShaderNodeValToRGB")
    vor_ramp.name = "Ramp_voronoi"
    vor_ramp.location = (-520, 200)
    vor_ramp.color_ramp.elements[0].position = 0.0
    vor_ramp.color_ramp.elements[0].color = (1, 1, 1, 1)
    vor_ramp.color_ramp.elements[1].position = 0.09
    vor_ramp.color_ramp.elements[1].color = (0, 0, 0, 1)

    # --- pola 2: Wave (riak air) ---
    wave = nt.nodes.new("ShaderNodeTexWave")
    wave.name = "Wave_caustic"
    wave.location = (-720, -180)
    wave.wave_type = "BANDS"
    wave.bands_direction = "DIAGONAL"
    wave.inputs["Scale"].default_value = 7.0
    wave.inputs["Distortion"].default_value = 12.0
    wave.inputs["Detail"].default_value = 2.0
    wave.inputs["Detail Scale"].default_value = 1.6

    wave_ramp = nt.nodes.new("ShaderNodeValToRGB")
    wave_ramp.name = "Ramp_wave"
    wave_ramp.location = (-520, -180)
    wave_ramp.color_ramp.elements[0].position = 0.42
    wave_ramp.color_ramp.elements[0].color = (0, 0, 0, 1)
    wave_ramp.color_ramp.elements[1].position = 0.62
    wave_ramp.color_ramp.elements[1].color = (1, 1, 1, 1)

    # --- campur additive lembut kedua pola ---
    mix_pattern = nt.nodes.new("ShaderNodeMix")
    mix_pattern.name = "Mix_caustic-pattern"
    mix_pattern.data_type = "RGBA"
    mix_pattern.blend_type = "ADD"
    mix_pattern.location = (-260, 0)
    mix_pattern.inputs["Factor"].default_value = 0.55

    # --- additive ke warna pasir, kekuatan 0,18 ---
    mix_add = nt.nodes.new("ShaderNodeMix")
    mix_add.name = "Mix_caustic-add"
    mix_add.data_type = "RGBA"
    mix_add.blend_type = "ADD"
    mix_add.location = (240, 60)
    mix_add.inputs["Factor"].default_value = 0.18
    for sock in mix_add.inputs:
        if sock.identifier == "B_Color":
            sock.default_value = (*C_CREAM, 1.0)

    # --- peredam di lembah pola: pasir dikali 0,55..1,00 supaya jaring caustic
    # tetap terbaca walau pasir sudah mendekati putih karena sinar kuat ---
    ramp_mul = nt.nodes.new("ShaderNodeValToRGB")
    ramp_mul.name = "Ramp_caustic-multiply"
    ramp_mul.location = (-60, -60)
    ramp_mul.color_ramp.elements[0].position = 0.0
    ramp_mul.color_ramp.elements[0].color = (0.45, 0.45, 0.45, 1)
    ramp_mul.color_ramp.elements[1].position = 1.0
    ramp_mul.color_ramp.elements[1].color = (1, 1, 1, 1)

    mix_mul = nt.nodes.new("ShaderNodeMix")
    mix_mul.name = "Mix_caustic-multiply"
    mix_mul.data_type = "RGBA"
    mix_mul.blend_type = "MULTIPLY"
    mix_mul.location = (20, 60)
    mix_mul.inputs["Factor"].default_value = 1.0
    for sock in mix_mul.inputs:
        if sock.identifier == "A_Color":
            sock.default_value = (*C_SAND, 1.0)

    # --- bump pasir (sama seperti SHD_sand) ---
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.name = "Noise_sand"
    noise.location = (-260, -320)
    noise.inputs["Scale"].default_value = 60.0
    noise.inputs["Detail"].default_value = 6.0
    noise.inputs["Roughness"].default_value = 0.55

    bump = nt.nodes.new("ShaderNodeBump")
    bump.name = "Bump_sand"
    bump.location = (140, -280)
    bump.inputs["Strength"].default_value = 0.18
    bump.inputs["Distance"].default_value = 0.08

    L = nt.links
    L.new(coord.outputs["Object"], mapping.inputs["Vector"])
    L.new(mapping.outputs["Vector"], vor.inputs["Vector"])
    L.new(mapping.outputs["Vector"], wave.inputs["Vector"])
    L.new(vor.outputs["Distance"], vor_ramp.inputs["Factor"])
    L.new(wave.outputs["Color"], wave_ramp.inputs["Factor"])
    L.new(vor_ramp.outputs["Color"], mix_pattern.inputs[6])   # A_Color
    L.new(wave_ramp.outputs["Color"], mix_pattern.inputs[7])  # B_Color
    # pola -> peredam -> pasir*ramp -> + cream 0,18 -> base color
    L.new(mix_pattern.outputs[2], ramp_mul.inputs["Factor"])
    L.new(ramp_mul.outputs["Color"], mix_mul.inputs[7])        # B_Color
    L.new(mix_mul.outputs[2], mix_add.inputs[6])               # A_Color
    L.new(mix_add.outputs[2], bsdf.inputs["Base Color"])
    L.new(mapping.outputs["Vector"], noise.inputs["Vector"])
    L.new(noise.outputs["Factor"], bump.inputs["Height"])
    L.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    L.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    print("CAUSTIC SHD_seabed_caustics: Voronoi 6 + Wave 7/dist 12, mix ADD 0,55; "
          "pasir x0,45-1,00; additive cream 0,18")
    return mat


def build_fx_materials():
    # god ray card — emission lembut, tepi siluet dibuat hilang (Layer Weight
    # Facing) supaya cone tidak terbaca sebagai bidang bersisi keras.
    mat = new_material("SHD_godray_card")
    nt = clear_nodes(mat)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.location = (720, 0)
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (440, 0)
    bsdf.inputs["Base Color"].default_value = (0, 0, 0, 1)
    bsdf.inputs["Roughness"].default_value = 1.0
    bsdf.inputs["Specular IOR Level"].default_value = 0.0
    bsdf.inputs["Emission Color"].default_value = (*C_CREAM, 1.0)
    bsdf.inputs["Emission Strength"].default_value = 0.6

    coord = nt.nodes.new("ShaderNodeTexCoord")
    coord.location = (-820, -140)
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    sep.location = (-640, -140)
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.name = "Ramp_fade"
    ramp.location = (-440, -140)
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = (0, 0, 0, 1)
    ramp.color_ramp.elements[1].position = 0.22
    ramp.color_ramp.elements[1].color = (1, 1, 1, 1)
    e = ramp.color_ramp.elements.new(0.80)
    e.color = (1, 1, 1, 1)
    ramp.color_ramp.elements[-1].position = 1.0
    ramp.color_ramp.elements[-1].color = (0, 0, 0, 1)

    # tepi: facing 1 di siluet -> kuasakan (1 - facing)^1,5
    lw = nt.nodes.new("ShaderNodeLayerWeight")
    lw.location = (-820, -360)
    lw.inputs["Blend"].default_value = 0.5
    inv = nt.nodes.new("ShaderNodeMath")
    inv.name = "Edge_invert"
    inv.operation = "SUBTRACT"
    inv.location = (-640, -360)
    inv.inputs[0].default_value = 1.0
    power = nt.nodes.new("ShaderNodeMath")
    power.name = "Edge_power"
    power.operation = "POWER"
    power.location = (-440, -360)
    power.inputs[1].default_value = 1.5

    mul = nt.nodes.new("ShaderNodeMath")
    mul.name = "Alpha_scale"
    mul.operation = "MULTIPLY"
    mul.location = (-100, -220)
    mul.inputs[1].default_value = 0.55          # alpha puncak
    mul2 = nt.nodes.new("ShaderNodeMath")
    mul2.name = "Alpha_edge"
    mul2.operation = "MULTIPLY"
    mul2.location = (140, -220)

    nt.links.new(coord.outputs["Generated"], sep.inputs["Vector"])
    nt.links.new(sep.outputs["Z"], ramp.inputs["Factor"])
    nt.links.new(lw.outputs["Facing"], inv.inputs[1])
    nt.links.new(inv.outputs["Value"], power.inputs[0])
    nt.links.new(ramp.outputs["Color"], mul.inputs[0])
    nt.links.new(mul.outputs["Value"], mul2.inputs[0])
    nt.links.new(power.outputs["Value"], mul2.inputs[1])
    nt.links.new(mul2.outputs["Value"], bsdf.inputs["Alpha"])
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    set_blended(mat)

    # fog card — tint murni (emission), TIDAK ikut terang sinar: kalau memakai
    # Principled diffuse, alpha 0,08 x sinar 3,8 justru menambah terang.
    fog = new_material("SHD_fog_card")
    ntf = clear_nodes(fog)
    out = ntf.nodes.new("ShaderNodeOutputMaterial")
    out.location = (320, 0)
    b = ntf.nodes.new("ShaderNodeBsdfPrincipled")
    b.inputs["Base Color"].default_value = (0, 0, 0, 1)
    b.inputs["Roughness"].default_value = 1.0
    b.inputs["Specular IOR Level"].default_value = 0.0
    b.inputs["Emission Color"].default_value = (*C_TEAL_DEEP, 1.0)
    b.inputs["Emission Strength"].default_value = 1.0
    b.inputs["Alpha"].default_value = 0.08
    ntf.links.new(b.outputs["BSDF"], out.inputs["Surface"])
    set_blended(fog)

    # particle
    part = new_material("SHD_fx_particle")
    ntp = clear_nodes(part)
    out = ntp.nodes.new("ShaderNodeOutputMaterial")
    out.location = (320, 0)
    p = ntp.nodes.new("ShaderNodeBsdfPrincipled")
    p.inputs["Base Color"].default_value = (*C_CREAM, 1.0)
    p.inputs["Roughness"].default_value = 0.6
    p.inputs["Emission Color"].default_value = (*C_CREAM, 1.0)
    p.inputs["Emission Strength"].default_value = 0.35
    ntp.links.new(p.outputs["BSDF"], out.inputs["Surface"])
    part.use_fake_user = True
    print("FX material: SHD_godray_card (emission 0,6 #F2E9DC, alpha 0,55 x tepi), "
          "SHD_fog_card (emission tint alpha 0,08 #0F5C63), SHD_fx_particle")
    return mat, fog, part


# ------------------------------------------------------------- 3. geometri ---

def mesh_from_bmesh(name, bm):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    return me


def make_cone_mesh(name, r_bottom, r_top, height, segments=32):
    """Cone dengan alas di z = 0, puncak di z = height."""
    bm = bmesh.new()
    try:
        bmesh.ops.create_cone(
            bm, cap_ends=True, cap_tris=False, segments=segments,
            radius1=r_bottom, radius2=r_top, depth=height,
            matrix=Matrix.Translation((0, 0, height / 2.0)),
        )
    except TypeError:  # Blender lama memakai diameter1/diameter2
        bmesh.ops.create_cone(
            bm, cap_ends=True, cap_tris=False, segments=segments,
            diameter1=r_bottom * 2, diameter2=r_top * 2, depth=height,
            matrix=Matrix.Translation((0, 0, height / 2.0)),
        )
    return mesh_from_bmesh(name, bm)


def make_particles_mesh(name, count=200, seed=7):
    """Satu mesh: `count` bola kecil r 1–2 cm di volume 20 x 20 x 8 m."""
    rng = random.Random(seed)
    bm = bmesh.new()
    for _ in range(count):
        radius = rng.uniform(0.01, 0.02)
        loc = (rng.uniform(-10, 10), rng.uniform(-10, 10), rng.uniform(0.2, 8.0))
        mat = Matrix.Translation(loc) @ Matrix.Scale(radius, 4)
        try:
            bmesh.ops.create_icosphere(bm, subdivisions=1, radius=1.0, matrix=mat)
        except TypeError:
            bmesh.ops.create_icosphere(bm, subdivisions=1, diameter=2.0, matrix=mat)
    return mesh_from_bmesh(name, bm)


def make_card_mesh(name, width, height):
    """Bidang vertikal di bidang XZ (normal +Y), alas di z = 0."""
    bm = bmesh.new()
    verts = [
        bm.verts.new((-width / 2, 0, 0)),
        bm.verts.new((width / 2, 0, 0)),
        bm.verts.new((width / 2, 0, height)),
        bm.verts.new((-width / 2, 0, height)),
    ]
    bm.faces.new(verts)
    bm.normal_update()
    return mesh_from_bmesh(name, bm)


def new_object(name, data, collection, parent=None, location=(0, 0, 0)):
    ob = bpy.data.objects.new(name, data)
    collection.objects.link(ob)
    if parent is not None:
        ob.parent = parent
        ob.matrix_parent_inverse = Matrix.Identity(4)
    ob.location = location
    ob.visible_shadow = False
    return ob


def build_fx_collection():
    old = bpy.data.collections.get(FX_COLLECTION)
    if old is not None:
        for ob in list(old.objects):
            data = ob.data
            bpy.data.objects.remove(ob, do_unlink=True)
        bpy.data.collections.remove(old)
        print("FX lama dibersihkan")

    coll = bpy.data.collections.new(FX_COLLECTION)
    bpy.context.scene.collection.children.link(coll)
    coll.use_fake_user = True

    root = bpy.data.objects.new("FX_atmosphere_root", None)
    root.empty_display_type = "PLAIN_AXES"
    root.empty_display_size = 1.0
    coll.objects.link(root)

    mat_ray, mat_fog, mat_part = build_fx_materials()

    # 3 god ray card: 12 m tinggi, lebar 2–3,2 m
    rays = [
        ("FX_godray_card_01", 1.60, 0.45, (-4.2, 0.0, 0.0)),
        ("FX_godray_card_02", 1.10, 0.35, (0.4, 1.3, 0.4)),
        ("FX_godray_card_03", 1.00, 0.30, (4.4, -0.7, 0.0)),
    ]
    for name, rb, rt, loc in rays:
        me = make_cone_mesh(name, rb, rt, 12.0)
        me.materials.append(mat_ray)
        ob = new_object(name, me, coll, parent=root, location=loc)
        ob.rotation_euler = (math.radians(3), math.radians(-2), 0.0)

    # partikel: satu mesh 200 bola
    me = make_particles_mesh("FX_particles")
    me.materials.append(mat_part)
    new_object("FX_particles", me, coll, parent=root)

    # 2 fog card besar semi-transparan
    for name, w, h, loc in (
        ("FX_fog_card_01", 34.0, 16.0, (0.0, -7.0, -1.0)),
        ("FX_fog_card_02", 44.0, 22.0, (0.0, -15.0, -2.0)),
    ):
        me = make_card_mesh(name, w, h)
        me.materials.append(mat_fog)
        ob = new_object(name, me, coll, parent=root, location=loc)
        ob.visible_shadow = False

    print("FX:", [o.name for o in coll.objects])
    return coll


# -------------------------------------------------------------------- main ---

def _load_into_empty(path):
    """Muat file sumber tanpa open_mainfile (aman untuk sesi MCP)."""
    scn = bpy.context.scene
    for db in (bpy.data.objects, bpy.data.collections, bpy.data.meshes,
               bpy.data.materials, bpy.data.cameras, bpy.data.lights,
               bpy.data.worlds, bpy.data.actions, bpy.data.curves,
               bpy.data.armatures):
        for block in list(db):
            try:
                db.remove(block)
            except Exception:
                pass
    with bpy.data.libraries.load(path, link=False) as (src, dst):
        all_names = list(src.objects)
        dst.collections = list(src.collections)
    missing = [n for n in all_names if n not in bpy.data.objects]
    if missing:
        with bpy.data.libraries.load(path, link=False) as (src, dst):
            dst.objects = [n for n in src.objects if n in missing]
    children = {c.name for coll in dst.collections if coll for c in coll.children}
    for coll in dst.collections:
        if coll is not None and coll.name not in children:
            scn.collection.children.link(coll)
    for ob in bpy.data.objects:
        if not ob.users_collection:
            scn.collection.objects.link(ob)
    return scn


def main():
    scn = _load_into_empty(SRC)

    for name in WATER_MATS:
        patch_water(name)

    build_caustics_material()
    build_fx_collection()

    # standar render (PROJECT.md §3)
    scn.render.engine = "BLENDER_EEVEE"
    scn.render.resolution_x = 1920
    scn.render.resolution_y = 1080
    scn.render.resolution_percentage = 100
    scn.render.fps = 24
    scn.view_settings.view_transform = "Standard"
    scn.frame_set(1)

    scn.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=DST)
    size = os.path.getsize(DST) / 1048576
    print("SAVED", DST, round(size, 2), "MB")
    print("MATERIALS", [m.name for m in bpy.data.materials])
    print("COLLECTIONS", [(c.name, len(c.objects)) for c in bpy.data.collections])


if __name__ == "__main__":
    main()

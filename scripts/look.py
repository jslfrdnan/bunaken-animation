"""look.py — terapkan look dev per scene ke file shot.

Dipakai oleh renderer: `from look import apply_look` lalu `apply_look(scn, 1)`.
Fungsi ini menyentuh tujuh hal:

1. `scn.world`  — world look scene terkait (append `link=False` dari `assets/look/`).
2. material objek air (nama mengandung `water` / `sea`) — `SHD_water-surface_v002`.
3. modifier `Displace` gelombang pada objek air ber-vert < 10.000 (lihat
   `add_wave_displace`): tekstur Clouds size 25, strength 0,12 m. Objek air yang
   lebih besar (mis. bidang laut 200 km) dilewati dan dicatat di
   `renders/logs/production.log`.
4. `scn.view_settings.view_transform` — dipaksa `"Standard"` (bukan AgX).
5. objek dasar laut (`seabed` / `sand`) — material `SHD_seabed_caustics`
   (pasir + pola caustic Voronoi + Wave, additive 0,18).
6. koleksi `FX_atmosphere` di-append sekali per scene: 3 kartu god ray, satu mesh
   200 partikel, 2 kartu kabut. Posisinya dihitung dari kamera (di belakang
   subjek), jadi file FX bisa dipakai semua shot bawah laut. Idempoten: kalau
   koleksinya sudah ada di file shot, tidak di-append ulang.
7. kabut kedalaman: `scn.world.mist_settings` + render pass Mist + compositor
   `Mist -> Mix` ke teal dalam `#0F5C63` (faktor 0,42 bawah laut / 0,25 di atas
   air untuk Scene 1). Tanpa World Volume — di EEVEE 5.2 world volume membuat
   frame hitam (lihat `assets/look/README.md`).

File shot TIDAK disimpan dan data lain (geometri, animasi, kamera, lampu,
material non-air) tidak diubah. Tidak ada tekstur gambar, jadi tidak ada path
gambar yang bisa putus. Lihat `PROJECT.md` §2 (palette) dan §3 ( teknis).

Pemakaian di dalam sesi Blender MCP (tanpa membuka file):

    import sys, bpy
    sys.path.append(<repo>/scripts)
    from look import apply_look
    report = apply_look(bpy.context.scene, 1)

Pemakaian CLI (proses Blender terpisah, boleh membuka file shot):

    blender -b scenes/scene-1_shot-030_terumbu_v001.blend -P scripts/look.py \
        -- --scene 1 --out renders/stills/look-test-s1.png

Catatan: `main()` memakai `bpy.ops.wm.open_mainfile` hanya kalau dijalankan
sebagai proses terpisah. Jangan panggil `main()` di sesi MCP yang hidup —
aturan proyek melarang `open_mainfile` di sesi hidup.
"""

from __future__ import annotations

import math
import os
import re
import sys

import bpy
from mathutils import Vector

# ---------------------------------------------------------------- konstanta ---

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOOK_DIR = os.path.join(REPO_ROOT, "assets", "look")
STILLS_DIR = os.path.join(REPO_ROOT, "renders", "stills")

LOOK_FILES = {
    1: "scene-1-look_v004.blend",
    2: "scene-2-look.blend",
    3: "scene-3-look.blend",
    4: "scene-4-look.blend",
}

# world utama per scene + world tambahan (scene 1 punya versi permukaan)
WORLDS = {
    1: {"underwater": "WLD_scene-1", "surface": "WLD_scene-1_surface"},
    2: {"underwater": "WLD_scene-2", "surface": "WLD_scene-2"},
    3: {"underwater": "WLD_scene-3", "surface": "WLD_scene-3"},
    4: {"underwater": "WLD_scene-4", "surface": "WLD_scene-4"},
}

# Shader air v003. `SHD_water-surface_v002` adalah material baru (dua skala noise
# 4D yang dianimasikan); `SHD_water-surface` di file look adalah kembarannya
# supaya file shot lama yang sudah memakai nama itu tidak kehilangan shader.
WATER_MATERIAL = "SHD_water-surface_v002"
WATER_MATERIAL_LEGACY = "SHD_water-surface"
# nama paling lama (garis bawah) hanya masih ada di scene-1-look.blend (v001)
WATER_MATERIAL_LEGACY_2 = "SHD_water_surface"

# --------------------------------------------------------------- atmosfer ---

# Koleksi FX + material yang ikut di-append (link=False) dari file look.
FX_COLLECTION = "FX_atmosphere"
FX_ROOT = "FX_atmosphere_root"
SEABED_MATERIAL = "SHD_seabed_caustics"
SEABED_HINTS = ("seabed", "sand")
# jarak kartu atmosfer dari kamera (meter) dan tinggi alas god ray relatif
FX_DISTANCE_UNDERWATER = 17.0
FX_ROOT_DROP = 2.2        # root = z kamera - 2,2 m (kira-kira setinggi dasar)
FX_ROOT_ABOVE_WATER = -12.5   # seluruh cone 12 m tetap di bawah permukaan

# Kabut compositor: Mix ke teal dalam #0F5C63 (PROJECT.md §2)
FOG_COLOR = (0.0048, 0.1070, 0.1248)
FOG_FACTOR = {1: 0.42, 2: 0.30, 3: 0.28, 4: 0.25}
FOG_FACTOR_ABOVE_WATER = 0.25
WORLD_MIST_START = 2.0
WORLD_MIST_DEPTH = 45.0
WORLD_MIST_INTENSITY = 1.0

# --------------------------------------------------------- gelombang profil ---

DISPLACE_NAME = "FX_water_wave-displace"
DISPLACE_TEXTURE = "FX_water_wave-clouds"
DISPLACE_MAX_VERTS = 10_000   # objek air lebih besar dari ini dilewati
DISPLACE_SIZE = 25.0          # Clouds size (m)
DISPLACE_STRENGTH = 0.12      # meter, amplitudo ombak

# Objek yang dianggap "permukaan air": token nama memuat "water" / "sea" ...
WATER_HINTS = ("water", "sea")
# ... tetapi BUKAN ini. `FX_water_volume` adalah kubus kabut bawah laut; kalau
# diberi shader permukaan ia jadi bidang gelap yang menutupi kamera.
WATER_EXCLUDE_HINTS = ("volume", "fog", "mist", "kabut")

_LOOK_CACHE = {}  # scene_id -> {"world": w, "world_surface": w, "material": m}


# ------------------------------------------------------------------ helper ---

def look_path(scene_id: int) -> str:
    """Path absolut file look untuk scene_id (1..4)."""
    try:
        name = LOOK_FILES[int(scene_id)]
    except KeyError:
        raise ValueError("scene_id harus 1..4, bukan %r" % (scene_id,))
    path = os.path.join(LOOK_DIR, name)
    if not os.path.exists(path):
        raise FileNotFoundError("file look tidak ada: %s" % path)
    return path


def load_look(scene_id: int) -> dict:
    """Append (link=False) world + material air dari file look.

    Idempoten: kalau world/material dengan nama itu sudah ada di file aktif,
    data yang ada dipakai ulang supaya tidak lahir `WLD_scene-1.001`.
    TIDAK memakai cache lintas file: setiap shot dibuka sebagai file baru,
    sehingga referensi World lama akan mati (StructRNA removed).
    """
    scene_id = int(scene_id)

    path = look_path(scene_id)
    names = WORLDS[scene_id]
    names_list = list(dict.fromkeys([names["underwater"], names["surface"]]))
    wanted_worlds = [n for n in names_list if n not in bpy.data.worlds]
    wanted_mats = [n for n in (WATER_MATERIAL, SEABED_MATERIAL) if n not in bpy.data.materials]

    if wanted_worlds or wanted_mats:
        with bpy.data.libraries.load(path, link=False) as (src, dst):
            dst.worlds = [n for n in src.worlds if n in wanted_worlds] if wanted_worlds else []
            dst.materials = [n for n in src.materials if n in wanted_mats] if wanted_mats else []

    # Scene 2–4 hanya menyimpan world; shader air tinggal di file look Scene 1.
    material = (
        bpy.data.materials.get(WATER_MATERIAL)
        or bpy.data.materials.get(WATER_MATERIAL_LEGACY)
        or bpy.data.materials.get(WATER_MATERIAL_LEGACY_2)
    )
    if material is None and scene_id != 1:
        with bpy.data.libraries.load(look_path(1), link=False) as (src, dst):
            dst.materials = [n for n in src.materials if n in (WATER_MATERIAL, SEABED_MATERIAL)]
        material = bpy.data.materials.get(WATER_MATERIAL)

    caustics = bpy.data.materials.get(SEABED_MATERIAL)
    if caustics is None:  # scene 2–4 belum punya material caustic
        try:
            with bpy.data.libraries.load(look_path(1), link=False) as (src, dst):
                dst.materials = [n for n in src.materials if n == SEABED_MATERIAL]
            caustics = bpy.data.materials.get(SEABED_MATERIAL)
        except Exception:
            caustics = None

    world = bpy.data.worlds.get(names["underwater"])
    if world is None:  # fallback: world pertama di file look
        world = next((w for w in bpy.data.worlds if w.name.startswith("WLD_scene-%d" % scene_id)), None)
    if world is None or material is None:
        raise RuntimeError("look scene %d tidak lengkap (world=%r, material=%r)" % (scene_id, world, material))

    for w in (world, bpy.data.worlds.get(names["surface"])):
        if w is not None:
            w.use_fake_user = True
    material.use_fake_user = True
    if caustics is not None:
        caustics.use_fake_user = True

    return {
        "world": world,
        "world_surface": bpy.data.worlds.get(names["surface"]) or world,
        "material": material,
        "caustics": caustics,
    }


def water_objects(scn) -> list:
    """Objek permukaan air di scn: token nama `water`/`sea`, tanpa `volume`/`fog`.

    Pencocokan memakai token (pecah pada `-`, `_`, spasi, titik), bukan substring
    mentah: `PRP_boat_cadik_seam-4` memuat "sea" sebagai huruf tetapi BUKAN air,
    jadi ia tidak boleh ikut diganti (`seam` != token `sea`).

    `FX_water_volume` juga sengaja dilewati: itu kubus kabut (`SHD_water_volume`),
    bukan permukaan. Menggantinya dengan shader permukaan membuat seluruh frame
    gelap karena kamera berada di dalam kubus.
    """
    found = []
    for ob in scn.objects:
        if ob.type not in {"MESH", "CURVE", "SURFACE", "FONT", "META"}:
            continue
        tokens = [t for t in re.split(r"[^a-z0-9]+", ob.name.lower()) if t]
        is_water = any(t == "water" or t.startswith("water") or t == "sea" or t.startswith("seawater")
                       for t in tokens)
        if not is_water:
            continue
        if any(h in t for t in tokens for h in WATER_EXCLUDE_HINTS):
            continue
        found.append(ob)
    return found


def _camera_height(scn) -> float:
    cam = scn.camera
    if cam is None or cam.type != "CAMERA":
        return None
    return (cam.matrix_world.translation.z)


def _log(message: str) -> None:
    """Tulis satu baris ke renders/logs/production.log (kalau foldernya ada)."""
    try:
        import datetime

        path = os.path.join(REPO_ROOT, "renders", "logs", "production.log")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8") as handle:
            handle.write("[%s] LOOK - %s\n" % (datetime.datetime.now().strftime("%H:%M"), message))
    except Exception:  # logging tidak boleh menggagalkan render
        pass


def wave_texture():
    """Tekstur Clouds untuk Displace gelombang (idempoten)."""
    tex = bpy.data.textures.get(DISPLACE_TEXTURE)
    if tex is None:
        tex = bpy.data.textures.new(DISPLACE_TEXTURE, type="CLOUDS")
    tex.noise_scale = DISPLACE_SIZE
    tex.noise_depth = 2
    tex.use_fake_user = True
    return tex


def add_wave_displace(ob) -> str:
    """Tambah modifier Displace gelombang ke objek air. Kembalikan status singkat.

    Hanya untuk objek air dengan < `DISPLACE_MAX_VERTS` vert. Objek yang lebih
    besar (mis. bidang laut 200 km di `surface.blend`) dilewati supaya modifier
    tidak membebani mesh dekat nol-vert yang tidak akan menampilkan profil apa
    pun; statusnya dicatat ke log.
    """
    if ob.type != "MESH":
        return "dilewati: %s bukan mesh" % ob.type
    verts = len(ob.data.vertices)
    if verts >= DISPLACE_MAX_VERTS:
        _log("displace dilewati: %s (%d vert >= %d)" % (ob.name, verts, DISPLACE_MAX_VERTS))
        return "dilewati: %d vert >= %d" % (verts, DISPLACE_MAX_VERTS)

    mod = ob.modifiers.get(DISPLACE_NAME)
    if mod is None:
        mod = ob.modifiers.new(DISPLACE_NAME, "DISPLACE")
    mod.texture = wave_texture()
    mod.texture_coords = "LOCAL"
    mod.direction = "NORMAL"
    mod.mid_level = 0.5
    mod.strength = DISPLACE_STRENGTH
    return "displace %.2f m pada %d vert" % (DISPLACE_STRENGTH, verts)


# ------------------------------------------------------ dasar laut + caustic ---

def seabed_objects(scn) -> list:
    """Objek dasar laut: token nama `seabed`, atau `sand` selama di bawah air.

    `sand` di atas permukaan (pantai, gundukan pasir shot 020) TIDAK diganti:
    pola caustic hanya masuk akal di bawah air.
    """
    found = []
    for ob in scn.objects:
        if ob.type != "MESH":
            continue
        tokens = [t for t in re.split(r"[^a-z0-9]+", ob.name.lower()) if t]
        if any(h in t for t in tokens for h in WATER_EXCLUDE_HINTS):
            continue
        is_seabed = any(t.startswith("seabed") for t in tokens)
        is_sand = any(t == "sand" or t.startswith("sand") for t in tokens)
        if not (is_seabed or is_sand):
            continue
        if not is_seabed and ob.matrix_world.translation.z > 0.5:
            continue  # pasir di atas air: biarkan material aslinya
        found.append(ob)
    return found


def assign_seabed_material(scn, mat) -> list:
    """Ganti material objek dasar laut ke `SHD_seabed_caustics`. Idempoten."""
    if mat is None:
        return []
    touched = []
    for ob in seabed_objects(scn):
        data = getattr(ob, "data", None)
        if data is None or not hasattr(data, "materials"):
            continue
        if len(data.materials) == 0:
            data.materials.append(mat)
        else:
            for i in range(len(data.materials)):
                data.materials[i] = mat
        touched.append(ob.name)
    return touched


# --------------------------------------------------------------- FX atmosfer ---

def _collection_linked(scn, coll) -> bool:
    """True kalau `coll` sudah ter-link ke scn (langsung atau lewat anak)."""
    stack = [scn.collection]
    seen = set()
    while stack:
        c = stack.pop()
        if c.name in seen:
            continue
        seen.add(c.name)
        if c == coll:
            return True
        stack.extend(c.children)
    return False


def _append_fx_collection(scene_id: int):
    """Append koleksi FX_atmosphere dari file look (link=False). Idempoten."""
    coll = bpy.data.collections.get(FX_COLLECTION)
    if coll is not None:
        return coll
    path = look_path(scene_id)
    try:
        with bpy.data.libraries.load(path, link=False) as (src, dst):
            if FX_COLLECTION in src.collections:
                dst.collections = [FX_COLLECTION]
    except Exception as exc:  # file look scene 2–4 tidak punya FX
        _log("FX_atmosphere tidak bisa di-append dari %s: %s" % (os.path.basename(path), exc))
        return None
    return bpy.data.collections.get(FX_COLLECTION)


def place_atmosphere(scn, coll, above_water: bool) -> dict:
    """Tempatkan FX_atmosphere di depan kamera, di belakang subjek.

    Root diputar mengikuti yaw kamera, jadi kartu kabut selalu menghadap kamera
    dan god ray tetap vertikal. Jarak 17 m (bawah laut) supaya berkas cahaya
    berada di kedalaman frame, bukan menempel di lensa. Untuk kamera di atas air
    seluruh grup diturunkan ke z -12,5 m agar tertutup bidang air.
    """
    cam = scn.camera
    root = coll.objects.get(FX_ROOT) if coll else None
    if cam is None or root is None:
        return {}
    direction = cam.matrix_world.to_quaternion() @ Vector((0.0, 0.0, -1.0))
    pos = cam.matrix_world.translation

    if above_water:
        dist = FX_DISTANCE_UNDERWATER * 1.5
        if direction.z < -0.02:  # kamera menunduk: taruh FX di bawah permukaan
            dist = max(8.0, min(90.0, (FX_ROOT_ABOVE_WATER - pos.z) / direction.z))
        root_z = FX_ROOT_ABOVE_WATER
    else:
        dist = FX_DISTANCE_UNDERWATER
        root_z = pos.z - FX_ROOT_DROP

    root.location = (pos.x + direction.x * dist, pos.y + direction.y * dist, root_z)
    root.rotation_euler = (0.0, 0.0, math.atan2(direction.x, -direction.y))
    return {
        "root": root.name,
        "location": tuple(round(v, 2) for v in root.location),
        "distance": round(dist, 2),
    }


def ensure_atmosphere(scn, scene_id: int, above_water: bool, enabled: bool = True):
    """Append + tempatkan FX_atmosphere sekali per scene. Idempoten."""
    if not enabled:
        return None
    coll = _append_fx_collection(scene_id)
    if coll is None:
        return None
    if not _collection_linked(scn, coll):
        scn.collection.children.link(coll)
    place_atmosphere(scn, coll, above_water)
    return coll


# ------------------------------------------------------------ kabut compositor ---

def _compositor_tree(scn):
    """Compositor tree 5.x (`scn.compositing_node_group`), dibuat bila kosong."""
    tree = getattr(scn, "compositing_node_group", None)
    if tree is None:
        try:
            scn.use_nodes = True
        except Exception:
            pass
        tree = getattr(scn, "compositing_node_group", None)
    if tree is None:
        try:
            tree = bpy.data.node_groups.new("COMP_scene-look", "CompositorNodeTree")
        except Exception as exc:
            _log("compositor tidak tersedia: %s" % exc)
            return None
        scn.compositing_node_group = tree
    outputs = [s for s in tree.interface.items_tree if getattr(s, "in_out", "") == "OUTPUT"]
    if not outputs:
        try:
            tree.interface.new_socket(name="Image", in_out="OUTPUT", socket_type="NodeSocketColor")
        except Exception:
            pass
    return tree


def apply_fog(scn, scene_id: int, above_water: bool, enabled: bool = True) -> dict:
    """Kabut kedalaman: mist_settings + pass Mist + compositor Mix ke #0F5C63.

    Idempoten: node dikenali dari namanya (`FOG_*`), nilainya diperbarui tanpa
    menambah node baru. Tidak memakai World Volume (EEVEE 5.2 -> frame hitam).
    """
    if not enabled:
        return {}
    factor = FOG_FACTOR_ABOVE_WATER if above_water else FOG_FACTOR.get(int(scene_id), 0.30)

    mist = getattr(getattr(scn, "world", None), "mist_settings", None)
    if mist is not None:
        mist.start = WORLD_MIST_START
        mist.depth = WORLD_MIST_DEPTH
        mist.falloff = "QUADRATIC"
        mist.intensity = WORLD_MIST_INTENSITY
    if hasattr(scn.render, "use_mist"):
        scn.render.use_mist = True

    for vl in scn.view_layers:
        if hasattr(vl, "use_pass_mist"):
            vl.use_pass_mist = True
        if hasattr(vl, "use_pass_z"):
            vl.use_pass_z = True

    tree = _compositor_tree(scn)
    if tree is None:
        return {"fog": "compositor tidak tersedia"}

    # Render Layers: socket Mist hanya ada kalau pass-nya sudah aktif saat node
    # dibuat. Kalau node lama belum punya Mist, buat ulang.
    rl = next((n for n in tree.nodes if n.bl_idname == "CompositorNodeRLayers"), None)
    if rl is not None and "Mist" not in [s.name for s in rl.outputs]:
        tree.nodes.remove(rl)
        rl = None
    if rl is None:
        rl = tree.nodes.new("CompositorNodeRLayers")
        rl.name = "FOG_render-layers"
        rl.location = (-620, 0)

    out = next((n for n in tree.nodes if n.bl_idname == "NodeGroupOutput"), None)
    if out is None:
        out = tree.nodes.new("NodeGroupOutput")
        out.location = (420, 0)

    mix = tree.nodes.get("FOG_mix")
    if mix is None:
        mix = tree.nodes.new("ShaderNodeMix")
        mix.name = "FOG_mix"
        mix.label = "Kabut kedalaman #0F5C63"
        mix.data_type = "RGBA"
        mix.blend_type = "MIX"
        mix.location = (160, 0)
        try:
            mix.clamp_factor = True
        except Exception:
            pass

    def socket(node, identifier):
        return next((s for s in node.inputs if s.identifier == identifier), None)

    def out_socket(node, identifier):
        return next((s for s in node.outputs if s.identifier == identifier), None)

    b_color = socket(mix, "B_Color")
    if b_color is not None:
        b_color.default_value = (*FOG_COLOR, 1.0)
    a_color = socket(mix, "A_Color")
    factor_in = socket(mix, "Factor_Float") or socket(mix, "Factor")
    result_out = out_socket(mix, "Result_Color") or out_socket(mix, "Result")

    scale = tree.nodes.get("FOG_factor")
    if scale is None:
        scale = tree.nodes.new("ShaderNodeMath")
        scale.name = "FOG_factor"
        scale.operation = "MULTIPLY"
        scale.location = (-220, -160)
        scale.inputs[1].default_value = factor
    else:
        scale.inputs[1].default_value = factor

    links = tree.links

    def _prune(predicate):
        # Jangan menyimpan referensi NodeLink lalu menghapus link lain:
        # StructRNA-nya jadi tidak valid. Ambil ulang per indeks.
        i = 0
        while i < len(links):
            if predicate(links[i]):
                links.remove(links[i])
            else:
                i += 1

    _prune(lambda l: l.to_node == out)
    _prune(lambda l: l.to_node == mix and (l.from_node == rl or l.from_node == scale or l.from_node == out))
    _prune(lambda l: l.to_node == scale and l.from_node == rl)

    if "Mist" in [s.name for s in rl.outputs]:
        links.new(rl.outputs["Mist"], scale.inputs[0])
    else:  # jaring pengaman: pakai Depth kalau Mist tidak tersedia
        depth = tree.nodes.get("FOG_depth-map")
        if depth is None:
            depth = tree.nodes.new("ShaderNodeMapRange")
            depth.name = "FOG_depth-map"
            depth.location = (-420, -160)
            try:
                depth.clamp = True
            except Exception:
                pass
            depth.inputs["From Min"].default_value = WORLD_MIST_START
            depth.inputs["From Max"].default_value = WORLD_MIST_DEPTH
        links.new(rl.outputs["Depth"], depth.inputs["Value"])
        links.new(depth.outputs["Result"], scale.inputs[0])

    links.new(scale.outputs[0], factor_in)
    links.new(rl.outputs["Image"], a_color)
    links.new(result_out, out.inputs["Image"])
    scn.render.use_compositing = True

    return {
        "fog": "Mist -> Mix #0F5C63",
        "factor": round(factor, 2),
        "mist": (WORLD_MIST_START, WORLD_MIST_DEPTH, "QUADRATIC"),
    }


def apply_look(scn, scene_id: int, above_water=None, assign_water=True, displace=True,
               fx=True, fog=True, caustics=True) -> dict:
    """Terapkan look scene_id ke scene `scn`. Tidak menyimpan file.

    scn          : bpy.types.Scene sasaran (scene dari file shot).
    scene_id     : 1..4.
    above_water  : True/False paksa world permukaan (scene 1 punya dua world);
                   None = deteksi otomatis dari tinggi kamera (> 0,5 m = di atas
                   permukaan). Scene 2–4 memakai satu world untuk dua-duanya.
    assign_water : False kalau renderer hanya ingin world + view transform.
    displace     : False kalau renderer tidak ingin modifier Displace gelombang.
    fx           : False kalau renderer tidak ingin koleksi FX_atmosphere.
    fog          : False kalau renderer tidak ingin kabut compositor.
    caustics     : False kalau material dasar laut tidak boleh diganti.

    Mengembalikan dict laporan: world, material, objek, modifier, FX, kabut,
    view transform.
    """
    scene_id = int(scene_id)
    look = load_look(scene_id)

    if above_water is None:
        z = _camera_height(scn)
        above_water = (z is not None and z > 0.5)

    world = look["world_surface"] if above_water else look["world"]
    if world is None:
        world = look["world"]
    scn.world = world

    touched = []
    displaced = {}
    if assign_water:
        mat = look["material"]
        for ob in water_objects(scn):
            data = getattr(ob, "data", None)
            if data is None or not hasattr(data, "materials"):
                continue
            if len(data.materials) == 0:
                data.materials.append(mat)
            else:
                for i in range(len(data.materials)):
                    data.materials[i] = mat
            touched.append(ob.name)
            if displace:
                displaced[ob.name] = add_wave_displace(ob)

    seabed = assign_seabed_material(scn, look["caustics"]) if caustics else []
    coll = ensure_atmosphere(scn, scene_id, above_water, enabled=fx)
    fog_report = apply_fog(scn, scene_id, above_water, enabled=fog)

    scn.view_settings.view_transform = "Standard"

    return {
        "scene_id": scene_id,
        "world": world.name,
        "above_water": bool(above_water),
        "water_material": look["material"].name if assign_water else None,
        "water_objects": touched,
        "water_displace": displaced,
        "seabed_objects": seabed,
        "fx_collection": coll.name if coll is not None else None,
        "fog": fog_report,
        "view_transform": scn.view_settings.view_transform,
    }


def render_still(scn, filepath: str, percent: int = 50, samples: int = 16) -> str:
    """Render still scn ke filepath (PNG). Scene harus sudah punya kamera."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    scn.render.engine = "BLENDER_EEVEE"
    scn.render.resolution_x = 1920
    scn.render.resolution_y = 1080
    scn.render.resolution_percentage = int(percent)
    scn.render.image_settings.file_format = "PNG"
    scn.render.image_settings.color_mode = "RGBA"
    if hasattr(scn, "eevee") and hasattr(scn.eevee, "taa_render_samples"):
        scn.eevee.taa_render_samples = int(samples)
    scn.render.filepath = filepath
    scn.render.use_file_extension = True
    win = getattr(bpy.context, "window", None)
    if win is not None and win.scene is not scn:
        win.scene = scn
    bpy.ops.render.render(write_still=True)
    return scn.render.filepath


# -------------------------------------------------------------------- main ---

def main(argv=None) -> int:
    """Uji opsional: buka satu file shot, apply_look, render masih.

    HANYA untuk proses Blender terpisah. Di sesi MCP hidup jangan dipanggil.
    """
    argv = list(sys.argv if argv is None else argv)
    argv = argv[argv.index("--") + 1:] if "--" in argv else argv

    def arg(flag, default=None):
        if flag in argv:
            i = argv.index(flag)
            if i + 1 < len(argv):
                return argv[i + 1]
        return default

    shot = arg("--shot")
    scene_id = int(arg("--scene", "1"))
    out = arg("--out", os.path.join(STILLS_DIR, "look-test-s%d.png" % scene_id))
    percent = int(arg("--percent", "50"))

    if shot and os.path.abspath(shot) != os.path.abspath(bpy.data.filepath):
        bpy.ops.wm.open_mainfile(filepath=os.path.abspath(shot))

    report = apply_look(bpy.context.scene, scene_id)
    render_still(bpy.context.scene, out, percent=percent)
    print("[look]", report, "->", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())

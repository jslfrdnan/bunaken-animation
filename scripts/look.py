"""look.py — terapkan look dev per scene ke file shot.

Dipakai oleh renderer: `from look import apply_look` lalu `apply_look(scn, 1)`.
Fungsi ini HANYA menyentuh empat hal:

1. `scn.world`  — world look scene terkait (append `link=False` dari `assets/look/`).
2. material objek air (nama mengandung `water` / `sea`) — `SHD_water-surface_v002`.
3. modifier `Displace` gelombang pada objek air ber-vert < 10.000 (lihat
   `add_wave_displace`): tekstur Clouds size 25, strength 0,12 m. Objek air yang
   lebih besar (mis. bidang laut 200 km) dilewati dan dicatat di
   `renders/logs/production.log`.
4. `scn.view_settings.view_transform` — dipaksa `"Standard"` (bukan AgX).

Tidak ada lampu yang ditambahkan dan tidak ada objek baru selain modifier itu.

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

import os
import re
import sys

import bpy

# ---------------------------------------------------------------- konstanta ---

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOOK_DIR = os.path.join(REPO_ROOT, "assets", "look")
STILLS_DIR = os.path.join(REPO_ROOT, "renders", "stills")

LOOK_FILES = {
    1: "scene-1-look_v003.blend",
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
    wanted_worlds = [n for n in (names["underwater"], names["surface"]) if n not in bpy.data.worlds]
    wanted_mats = [WATER_MATERIAL] if WATER_MATERIAL not in bpy.data.materials else []

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
            dst.materials = [n for n in src.materials if n == WATER_MATERIAL]
        material = bpy.data.materials.get(WATER_MATERIAL)

    world = bpy.data.worlds.get(names["underwater"])
    if world is None:  # fallback: world pertama di file look
        world = next((w for w in bpy.data.worlds if w.name.startswith("WLD_scene-%d" % scene_id)), None)
    if world is None or material is None:
        raise RuntimeError("look scene %d tidak lengkap (world=%r, material=%r)" % (scene_id, world, material))

    for w in (world, bpy.data.worlds.get(names["surface"])):
        if w is not None:
            w.use_fake_user = True
    material.use_fake_user = True

    return {
        "world": world,
        "world_surface": bpy.data.worlds.get(names["surface"]) or world,
        "material": material,
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


def apply_look(scn, scene_id: int, above_water=None, assign_water=True, displace=True) -> dict:
    """Terapkan look scene_id ke scene `scn`. Tidak menyimpan file.

    scn          : bpy.types.Scene sasaran (scene dari file shot).
    scene_id     : 1..4.
    above_water  : True/False paksa world permukaan (scene 1 punya dua world);
                   None = deteksi otomatis dari tinggi kamera (> 0,5 m = di atas
                   permukaan). Scene 2–4 memakai satu world untuk dua-duanya.
    assign_water : False kalau renderer hanya ingin world + view transform.
    displace     : False kalau renderer tidak ingin modifier Displace gelombang.

    Mengembalikan dict laporan: world, material, objek, modifier, view transform.
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

    scn.view_settings.view_transform = "Standard"

    return {
        "scene_id": scene_id,
        "world": world.name,
        "above_water": bool(above_water),
        "water_material": look["material"].name if assign_water else None,
        "water_objects": touched,
        "water_displace": displaced,
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

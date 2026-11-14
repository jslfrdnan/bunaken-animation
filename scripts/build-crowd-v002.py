"""
Crowd dermaga v002 — 12 figur dari crowd.blend + WAJAH SEDERHANA.

Hasil: assets/char/crowd_v002.blend
  scene "crowd-v002"
    koleksi CHR_crowd                    (hasil append dari crowd.blend)
      +-- empty CTL_crowd                pivot induk di origin
      +-- CRW_01 … CRW_12                mesh figur (tidak diubah)
      +-- CHR_crowd_face-crw-01 … -12    wajah: 2 mata + kelopak + hidung + mulut
    koleksi PREVIEW                      kamera + lampu + lantai

Sumber figur: assets/char/crowd.blend (dibangun build-crowd.py), di-append
`link=False`. Tinggi, pose, origin, nama, dan material figur TIDAK diubah —
wajah hanya ditambahkan sebagai objek anak per figur, sehingga menggeser figur
selalu menggeser wajahnya.

Wajah (sederhana, bukan facial rig):
  2 bola mata kecil + kelopak atas (kulit), hidung kecil (kulit), mulut pipih.
  Warna: mata #2E383A (netral gelap), mulut #C7A985 (bibir), kulit memakai
  material kulit figur itu sendiri (MAT_crowd_skin / MAT_crowd_skin-alt).
  Semua proporsi dihitung dari pusat & radius kepala figur (lihat SPECS di
  bawah, disalin dari build-crowd.py) supaya pas untuk dewasa maupun anak.

Tanpa tekstur, tanpa pack gambar. Skrip IDEMPOTEN dan MENYIMPAN file di akhir.
Tanpa open_mainfile / read_factory_settings / read_homefile; file aktif
dilepas lewat save_as_mainfile ke renders/tmp/_wipe.blend.
"""

import bpy
import bmesh
import os
import math
import datetime
from math import cos, sin, pi
from mathutils import Vector

HEX_GROUND = "#2E383A"
HEX_EYE = "#2E383A"      # netral gelap (14 Nov 2026)
HEX_CREAM = "#F2E9DC"    # krem tulang (sklera mata)
HEX_MOUTH = "#C7A985"    # bibir (kulit digelapkan)

SEG_EYE = 12

# disalin dari scripts/build-crowd.py (dipakai hanya untuk menghitung kepala)
SPECS = {
    "male": {"height": 1.72, "head": ((0.0, 0.0, 1.6055), (0.077, 0.093, 0.1145))},
    "female": {"height": 1.62, "head": ((0.0, 0.0, 1.512), (0.072, 0.089, 0.108))},
    "child": {"height": 1.25, "head": ((0.0, 0.0, 1.1425), (0.078, 0.091, 0.1075))},
}
CATEGORY_BASE = {"dewasa-pria": "male", "dewasa-wanita": "female", "anak": "child"}
HAIR_TOP = 1.06  # pusat rambut +0,06 rz, radius rz -> ubun-ubun 1,06 rz


# ---------------------------------------------------------------------------
# utilitas
# ---------------------------------------------------------------------------


def srgb(hexstr):
    h = hexstr.lstrip("#")
    values = [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]

    def to_linear(u):
        return u / 12.92 if u <= 0.04045 else ((u + 0.055) / 1.055) ** 2.4

    return tuple(to_linear(v) for v in values) + (1.0,)


def material(name, hexcol, roughness=0.6, spec=0.3):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.use_backface_culling = False
    col = srgb(hexcol)
    mat.diffuse_color = col
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = col
    bsdf.inputs["Roughness"].default_value = roughness
    spec_in = bsdf.inputs.get("Specular IOR Level") or bsdf.inputs.get("Specular")
    if spec_in is not None:
        spec_in.default_value = spec
    mat["source_hex"] = hexcol
    return mat


def ellipsoid(V, F, FM, FS, center, radii, mat, seg=SEG_EYE, rings_n=6):
    cx, cy, cz = center
    rx, ry, rz = radii
    top = len(V)
    V.append(Vector((cx, cy, cz + rz)))
    ring_starts = []
    for ir in range(1, rings_n):
        th = pi * ir / rings_n
        s, c = sin(th), cos(th)
        st = len(V)
        for i in range(seg):
            ph = 2.0 * pi * i / seg
            V.append(Vector((cx + rx * s * cos(ph), cy + ry * s * sin(ph),
                             cz + rz * c)))
        ring_starts.append(st)
    bot = len(V)
    V.append(Vector((cx, cy, cz - rz)))
    first = ring_starts[0]
    for i in range(seg):
        i2 = (i + 1) % seg
        F.append((top, first + i, first + i2))
        FM.append(mat)
        FS.append(True)
    for k in range(len(ring_starts) - 1):
        a, b = ring_starts[k], ring_starts[k + 1]
        for i in range(seg):
            i2 = (i + 1) % seg
            F.append((a + i, b + i, b + i2, a + i2))
            FM.append(mat)
            FS.append(True)
    last = ring_starts[-1]
    for i in range(seg):
        i2 = (i + 1) % seg
        F.append((bot, last + i2, last + i))
        FM.append(mat)
        FS.append(True)


def new_mesh_object(name, V, F, FM, FS, mats, collection):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(V, [], F)
    for m in mats:
        mesh.materials.append(m)
    for poly, mat_index, smooth in zip(mesh.polygons, FM, FS):
        poly.material_index = mat_index
        poly.use_smooth = smooth
    mesh.validate(verbose=False)
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    return obj


def set_engine(scn):
    last = None
    for cand in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scn.render.engine = cand
            return cand
        except TypeError as err:
            last = err
    print("PERINGATAN: gagal set EEVEE:", last)
    return scn.render.engine


def repo_root():
    try:
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    except NameError:
        return os.getcwd()


def log(line):
    path = os.path.join(repo_root(), "renders", "logs", "modeling.log")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    stamp = datetime.datetime.now().strftime("%H:%M")
    with open(path, "a", encoding="utf-8") as fh:
        fh.write("[%s] %s\n" % (stamp, line))


def release_and_wipe():
    tmp = os.path.join(repo_root(), "renders", "tmp", "_wipe.blend")
    os.makedirs(os.path.dirname(tmp), exist_ok=True)
    try:
        bpy.context.preferences.filepaths.save_version = 0
    except Exception:
        pass
    if bpy.data.filepath and os.path.abspath(bpy.data.filepath) != os.path.abspath(tmp):
        bpy.ops.wm.save_as_mainfile(filepath=tmp)

    scn = bpy.context.scene
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for col in list(bpy.data.collections):
        bpy.data.collections.remove(col)
    for s in list(bpy.data.scenes):
        if s is not scn:
            bpy.data.scenes.remove(s)
    for blocks in (bpy.data.meshes, bpy.data.materials, bpy.data.cameras,
                   bpy.data.lights, bpy.data.armatures, bpy.data.actions,
                   bpy.data.curves, bpy.data.node_groups, bpy.data.worlds,
                   bpy.data.images):
        for b in list(blocks):
            try:
                blocks.remove(b)
            except Exception:
                pass
    return scn


def setup_scene(scn):
    scn.name = "crowd-v002"
    scn.render.resolution_x = 1920
    scn.render.resolution_y = 1080
    scn.render.resolution_percentage = 100
    scn.render.fps = 24
    scn.render.fps_base = 1.0
    scn.view_settings.view_transform = "Standard"
    try:
        scn.view_settings.look = "None"
    except TypeError:
        pass
    scn.frame_start = 1
    scn.frame_end = 48
    scn.frame_set(1)
    engine = set_engine(scn)
    try:
        scn.eevee.taa_render_samples = 24
    except AttributeError:
        pass
    scn.render.image_settings.file_format = "PNG"
    scn.render.image_settings.color_mode = "RGBA"
    scn.render.film_transparent = False
    scn["asset"] = "crowd-v002"
    scn["asset_note"] = ("12 figur warga dermaga (dari crowd.blend) + wajah sederhana: "
                         "2 mata + kelopak, hidung, mulut. Tanpa tekstur.")
    return scn, engine


def append_collection(path, name):
    with bpy.data.libraries.load(path, link=False) as (df, dt):
        if name not in df.collections:
            raise RuntimeError("%s tidak punya koleksi %s" % (path, name))
        dt.collections = [name]
    return bpy.data.collections.get(name)


# ---------------------------------------------------------------------------
# kepala: pusat & radius di ruang lokal figur
# ---------------------------------------------------------------------------


def head_metrics(obj):
    """Kembalikan (hz, hrx, hry, hrz) di ruang lokal figur.

    Figur di build-crowd.py diskalakan k lalu dinormalisasi z supaya ubun-ubun
    tepat di tinggi target; karena itu rasio z dipakai ulang di sini.
    """
    target_h = float(obj["height_target_m"])
    base = CATEGORY_BASE.get(obj.get("category", "dewasa-pria"), "male")
    spec = SPECS[base]
    k = target_h / spec["height"]
    hc_z, (hrx_s, hry_s, hrz_s) = spec["head"][0][2], spec["head"][1]
    zden = hc_z + HAIR_TOP * hrz_s
    hz = hc_z * target_h / zden
    hrz = hrz_s * target_h / zden
    hrx = hrx_s * k
    hry = hry_s * k
    return hz, hrx, hry, hrz


def face_surface_y(hrx, hry, hrz, x, dz):
    """y permukaan ellipsoid kepala di depan (-Y) untuk x & dz tertentu."""
    q = 1.0 - (x / hrx) ** 2 - (dz / hrz) ** 2
    if q <= 0.0:
        return -hry
    return -hry * math.sqrt(q)


def skin_material(obj, hz, hrx, hry, hrz):
    """Material kulit (slot 0/1) yang dipakai di kepala figur.

    Slot 0 = MAT_crowd_skin, slot 1 = MAT_crowd_skin-alt; rambut (slot 2) dan
    baju tidak boleh terpilih, jadi pemilihan dibatasi ke dua slot kulit dan
    dihitung dari jumlah muka di daerah kepala.
    """
    counts = {}
    c = Vector((0.0, 0.0, hz))
    limit = 1.3 * max(hrx, hry, hrz)
    for p in obj.data.polygons:
        if p.material_index not in (0, 1):
            continue
        if (p.center - c).length > limit:
            continue
        counts[p.material_index] = counts.get(p.material_index, 0) + 1
    if not counts:
        return None
    idx = max(counts, key=counts.get)
    if 0 <= idx < len(obj.data.materials) and obj.data.materials[idx]:
        return obj.data.materials[idx]
    return None


def build_face(fig, m_eye, m_mouth, m_sclera, collection):
    hz, hrx, hry, hrz = head_metrics(fig)
    skin = skin_material(fig, hz, hrx, hry, hrz)
    if skin is None:
        skin = m_mouth

    V, F, FM, FS = [], [], [], []
    M_SKIN, M_EYE, M_MOUTH, M_SCLERA = 0, 1, 2, 3

    re = 0.155 * hrx                      # radius bola mata (±13 mm dewasa)
    ex = 0.400 * hrx                      # jarak mata dari garis tengah
    dz_eye = 0.080 * hrz
    ey = face_surface_y(hrx, hry, hrz, ex, dz_eye) + 0.010 * hry
    ez = hz + dz_eye

    for sx in (-1.0, 1.0):
        # bola mata: sklera krem + iris gelap di depan
        ellipsoid(V, F, FM, FS, (sx * ex, ey, ez),
                  (re * 0.85, re, re), M_SCLERA, seg=SEG_EYE, rings_n=6)
        ellipsoid(V, F, FM, FS, (sx * ex, ey - 0.60 * re, ez),
                  (re * 0.46, re * 0.62, re * 0.56), M_EYE,
                  seg=SEG_EYE, rings_n=5)
        # kelopak atas: cangkang pipih menutup bagian atas bola mata
        ellipsoid(V, F, FM, FS, (sx * ex, ey + 0.10 * re, ez + 0.40 * re),
                  (re * 1.16, re * 1.02, re * 0.60), M_SKIN,
                  seg=SEG_EYE, rings_n=5)

    # hidung kecil
    nz = hz - 0.045 * hrz
    ny = face_surface_y(hrx, hry, hrz, 0.0, -0.045 * hrz)
    ellipsoid(V, F, FM, FS, (0.0, ny + 0.030 * hry, nz),
              (0.110 * hrx, 0.115 * hry, 0.115 * hrz), M_SKIN,
              seg=SEG_EYE, rings_n=5)

    # mulut pipih
    mz = hz - 0.360 * hrz
    my = face_surface_y(hrx, hry, hrz, 0.0, -0.360 * hrz)
    ellipsoid(V, F, FM, FS, (0.0, my + 0.015 * hry, mz),
              (0.340 * hrx, 0.070 * hry, 0.048 * hrz), M_MOUTH,
              seg=SEG_EYE, rings_n=4)

    name = "CHR_crowd_face-crw-%s" % fig.name.split("_")[-1].lower()
    obj = new_mesh_object(name, V, F, FM, FS,
                          [skin, m_eye, m_mouth, m_sclera], collection)
    obj.parent = fig
    obj.matrix_parent_inverse = fig.matrix_world.inverted()
    obj["asset"] = "CHR_crowd"
    obj["part"] = "wajah"
    obj["note"] = "2 mata + kelopak + hidung + mulut; menempel di figur induk"
    return obj, (hz, hrx, hry, hrz)


# ---------------------------------------------------------------------------
# preview
# ---------------------------------------------------------------------------


def setup_preview(scn):
    prev = bpy.data.collections.new("PREVIEW")
    scn.collection.children.link(prev)

    ground_mat = material("MAT_preview_crowd-ground", HEX_GROUND, roughness=0.95,
                          spec=0.08)
    mesh = bpy.data.meshes.new("PREVIEW_ground")
    mesh.from_pydata(
        [(-14, -14, -0.002), (14, -14, -0.002), (14, 14, -0.002),
         (-14, 14, -0.002)], [], [(0, 1, 2, 3)],
    )
    mesh.materials.append(ground_mat)
    mesh.update()
    prev.objects.link(bpy.data.objects.new("PREVIEW_ground", mesh))

    cam_data = bpy.data.cameras.new("CAM_preview")
    cam_data.lens = 40.0
    cam_data.clip_start = 0.05
    cam = bpy.data.objects.new("CAM_preview", cam_data)
    prev.objects.link(cam)
    cam.location = (0.15, -7.20, 2.55)
    cam.rotation_euler = (Vector((0.0, 0.25, 1.05)) - cam.location).normalized(
    ).to_track_quat("-Z", "Y").to_euler()
    scn.camera = cam

    key = bpy.data.objects.new("LGT_preview-key",
                               bpy.data.lights.new("LGT_preview-key", "SUN"))
    prev.objects.link(key)
    key.data.energy = 2.1
    key.data.angle = math.radians(16)
    key.rotation_euler = (math.radians(50), 0.0, math.radians(28))

    fill = bpy.data.objects.new("LGT_preview-fill",
                                bpy.data.lights.new("LGT_preview-fill", "AREA"))
    prev.objects.link(fill)
    fill.data.energy = 420.0
    fill.data.size = 7.0
    fill.location = (-4.2, -6.0, 3.6)
    fill.rotation_euler = (Vector((0, 0.2, 1.0)) - fill.location).normalized(
    ).to_track_quat("-Z", "Y").to_euler()

    rim = bpy.data.objects.new("LGT_preview-rim",
                               bpy.data.lights.new("LGT_preview-rim", "AREA"))
    prev.objects.link(rim)
    rim.data.energy = 380.0
    rim.data.size = 6.0
    rim.location = (4.5, 5.0, 4.2)
    rim.rotation_euler = (Vector((0, 0, 1.2)) - rim.location).normalized(
    ).to_track_quat("-Z", "Y").to_euler()

    world = bpy.data.worlds.new("WLD_crowd-preview")
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.060, 0.074, 0.080, 1.0)
    bg.inputs["Strength"].default_value = 1.0
    scn.world = world
    return cam


def render_previews(shots):
    scn = bpy.context.scene
    cam = scn.camera
    out_dir = os.path.join(repo_root(), "renders", "stills")
    os.makedirs(out_dir, exist_ok=True)
    scn.render.resolution_percentage = 50
    paths = []
    for name, loc, tgt, lens in shots:
        cam.location = loc
        cam.data.lens = lens
        cam.rotation_euler = (Vector(tgt) - Vector(loc)).normalized().to_track_quat(
            "-Z", "Y").to_euler()
        path = os.path.join(out_dir, name + ".png")
        scn.render.filepath = path
        bpy.ops.render.render(write_still=True)
        paths.append(path)
        print("render ->", path)
    scn.render.resolution_percentage = 100
    return paths


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main():
    src = os.path.join(repo_root(), "assets", "char", "crowd.blend")
    if not os.path.exists(src):
        raise RuntimeError("file asal tidak ada: %s" % src)

    scn = release_and_wipe()
    scn, engine = setup_scene(scn)
    log("MCP - Blender siap; scene crowd-v002 diset (EEVEE, 1920x1080, 24 fps, Standard)")

    col = append_collection(src, "CHR_crowd")
    if col is None:
        raise RuntimeError("append koleksi CHR_crowd gagal")
    scn.collection.children.link(col)

    figs = sorted([o for o in col.objects if o.type == "MESH"
                   and o.name.startswith("CRW_")], key=lambda o: o.name)
    if len(figs) != 12:
        raise RuntimeError("jumlah figur bukan 12: %d" % len(figs))
    log("MODEL - append CHR_crowd dari crowd.blend: %d figur (%s)"
        % (len(figs), ", ".join(f.name for f in figs)))

    before = {f.name: (f.location.copy(), f.dimensions.z, len(f.data.vertices))
              for f in figs}

    m_eye = material("MAT_crowd_eye", HEX_EYE, roughness=0.18, spec=0.60)
    m_sclera = material("MAT_crowd_eye-white", HEX_CREAM, roughness=0.22, spec=0.55)
    m_mouth = material("MAT_crowd_mouth", HEX_MOUTH, roughness=0.55, spec=0.25)

    faces = []
    metrics = {}
    for fig in figs:
        face, met = build_face(fig, m_eye, m_mouth, m_sclera, col)
        faces.append(face)
        metrics[fig.name] = met

    log("MODEL - %d objek wajah (2 mata + sklera + 2 kelopak + hidung + mulut per "
        "figur), %d vert total"
        % (len(faces), sum(len(f.data.vertices) for f in faces)))

    setup_preview(scn)
    bpy.context.view_layer.update()

    # ---- verifikasi: tinggi/pose/origin figur tidak berubah ----
    changed = []
    for f in figs:
        loc, dz, nv = before[f.name]
        if (f.location - loc).length > 1e-6 or abs(f.dimensions.z - dz) > 1e-6 \
                or len(f.data.vertices) != nv:
            changed.append(f.name)

    print("=== RINGKASAN CHR_crowd v002 ===")
    for fig in figs:
        hz, hrx, hry, hrz = metrics[fig.name]
        face = next(f for f in faces if f.parent is fig)
        print("%-8s tinggi=%.3f  lokasi=(%.2f, %.2f)  kepala z=%.3f r=(%.3f,%.3f,%.3f)"
              "  wajah %s verts=%d"
              % (fig.name, fig.dimensions.z, fig.location.x, fig.location.y,
                 hz, hrx, hry, hrz, face.name, len(face.data.vertices)))
    print("figur berubah (harus kosong):", changed)
    print("total objek di koleksi:", len(col.objects))
    print("material:", [m.name for m in bpy.data.materials])
    print("engine=%s vt=%s res=%dx%d fps=%d frame=%d"
          % (engine, scn.view_settings.view_transform, scn.render.resolution_x,
             scn.render.resolution_y, scn.render.fps, scn.frame_current))

    target = os.path.join(repo_root(), "assets", "char", "crowd_v002.blend")
    bpy.ops.wm.save_as_mainfile(filepath=target, check_existing=False)
    print("saved:", target, "%.1f KB" % (os.path.getsize(target) / 1024.0))
    log("MODEL - crowd_v002.blend: 12 figur + 12 wajah, tinggi/pose/origin tidak "
        "berubah (%s), %.0f KB" % ("ok" if not changed else changed,
                                   os.path.getsize(target) / 1024.0))

    shots = [
        ("crowd-v002_preview-01", (0.15, -7.20, 2.55), (0.0, 0.25, 1.05), 40.0),
        ("crowd-v002_preview-02", (0.20, -4.60, 1.80), (0.00, -0.60, 1.35), 45.0),
    ]
    paths = render_previews(shots)
    log("VERIFY - crowd-v002_preview-01/02 50%%: %s"
        % ", ".join(os.path.basename(p) for p in paths))


if __name__ == "__main__":
    main()

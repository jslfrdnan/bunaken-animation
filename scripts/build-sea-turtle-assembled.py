"""
Menyusun ulang penyu hijau dari `assets/env/sea_turtle.blend` (milik Gian
Keintjem) menjadi satu penyu utuh ±1,1 m di koleksi `ENV_turtle`.

Latar masalah: di file asal, seluruh mesh bagian (karapas, plastron, badan,
kepala, sirip, scute) punya titik pusat yang sama (0,0,0). Hasil render hanya
terbaca sebagai kubah karapas karena semua bagian saling menumpuk di satu
titik. Mesh tiap bagian sendiri sudah berproporsi wajar terhadap karapas —
yang hilang hanya penempatan (transform) tiap bagian.

Skrip ini TIDAK menyimpan file, TIDAK merender, TIDAK mengubah file aset asal.
Ia hanya membangun penyu di memori; penyimpanan dilakukan terpisah oleh
pemanggil (lihat `assets/env/sea_turtle-assembled.blend`).

Cara pakai di Blender MCP (satu eksekusi):
    p = r"D:/Tugas Semester 5/Grafika Komputer/Project-Animasi/scripts/build-sea-turtle-assembled.py"
    exec(compile(open(p).read(), p, "exec"), {"__name__": "__main__"})

Aturan yang dipatuhi:
- Tidak memanggil open_mainfile / read_factory_settings / read_homefile
  (mematikan socket add-on). Data Blender di-wipe manual.
- Aset di-APPEND (bukan link); file asal tidak pernah ditulis.
- Material memakai material asli file asal (Skin, Shell, Plastron, Scute,
  Scute2, Eye, Mouth). Tanpa tekstur image, tanpa pack.
- EEVEE, 1920x1080, 24 fps, view transform Standard, frame 1.
- Idempoten: aman dijalankan berulang; hasil selalu sama.

Orientasi & skala (meter):
- Menghadap -Y, punggung +Z. Karapas 0,95 (Y) x 0,82 (X) x 0,34 (Z).
- Panjang total (moncong ke ujung karapas) +-1,12 m.
- Empty `CTL_turtle` di (0,0,0); z 0 = titik terendah tubuh (plastron).
"""

import math

import bpy
from mathutils import Vector, Matrix

ROOT = r"D:/Tugas Semester 5/Grafika Komputer/Project-Animasi"
SRC = ROOT + "/assets/env/sea_turtle.blend"

COLL_NAME = "ENV_turtle"
PIVOT_NAME = "CTL_turtle"
SHOW_SCUTES = True

# Semi-sumbu karapas (X = lebar, Y = panjang, Z = tinggi). Pusat karapas = 0,0,0.
CAR_AX = 0.41
CAR_AY = 0.475
CAR_AZ = 0.17

# Bagian tubuh: dims = ukuran akhir pada sumbu mesh lokal (x, y, z) dalam meter.
# Bagian yang panjangnya di mesh lokal mengikuti sumbu X diberi rot -90 supaya
# sumbu panjang itu menunjuk -Y (arah hadap penyu). Jadi untuk bagian tubuh,
# dims = (panjang, lebar, tinggi); loc tetap di koordinat dunia (X, Y, Z).
BODY_ROT = -90.0
PARTS = {
    # nama: (dims lokal x,y,z), (loc dunia x,y,z), rot_z_deg [, rot_y_deg]
    "Turtle_Carapace": ((0.95, 0.82, 0.34), (0.00, 0.00, 0.000), BODY_ROT),
    "Turtle_Plastron": ((0.84, 0.62, 0.10), (0.00, 0.01, -0.175), BODY_ROT),
    "Turtle_Body":     ((0.76, 0.60, 0.22), (0.00, 0.00, -0.075), BODY_ROT),
    "Turtle_Neck":     ((0.26, 0.155, 0.155), (0.00, -0.415, 0.005), BODY_ROT),
    "Turtle_Head":     ((0.21, 0.170, 0.155), (0.00, -0.505, 0.015), BODY_ROT),
    "Turtle_Snout":    ((0.095, 0.115, 0.095), (0.00, -0.5925, -0.012), BODY_ROT),
    "Turtle_Mouth":    ((0.040, 0.055, 0.028), (0.00, -0.618, -0.048), BODY_ROT),
    "Turtle_Eye_L":    ((0.034, 0.034, 0.034), (0.072, -0.548, 0.050), BODY_ROT),
    "Turtle_Eye_R":    ((0.034, 0.034, 0.034), (-0.072, -0.548, 0.050), BODY_ROT),
    # Sirip: sumbu panjang mesh lokal = X, jadi menunjuk ke luar (kiri/kanan).
    # Depan menyudut 28 derajat ke belakang (rot Z) dengan ujung turun 8 derajat
    # (rot Y); belakang menyudut 18 derajat dari arah ekor (rot Z 90-18 = 72).
    "Turtle_Flap_Front_L": ((0.55, 0.19, 0.050), (0.500, -0.110, -0.075), 28.0, 8.0),
    "Turtle_Flap_Front_R": ((0.55, 0.19, 0.050), (-0.500, -0.110, -0.075), -28.0, -8.0),
    "Turtle_Flap_Rear_L":  ((0.34, 0.15, 0.045), (0.320, 0.300, -0.060), 72.0),
    "Turtle_Flap_Rear_R":  ((0.34, 0.15, 0.045), (-0.320, 0.300, -0.060), -72.0),
}

# Scute: (dims lokal x=sepanjang tubuh, y=melintang, z=tebal) per jenis.
SCUTE_VERT = (0.240, 0.190, 0.026)
SCUTE_COSTAL = (0.330, 0.160, 0.026)
SCUTE_MARG = (0.115, 0.070, 0.020)
SCUTE_SINK = 0.012  # ditanam sedikit ke permukaan karapas
# Keping marginal (16 buah) di tepi karapas: hasil render terbaca seperti
# teritip menempel, bukan keping karapas, jadi disembunyikan.
SHOW_MARGINALS = False


# ---------------------------------------------------------------------------
# utilitas
# ---------------------------------------------------------------------------

def wipe():
    """Kosongkan bpy.data. Bukan open_mainfile: socket add-on tetap hidup."""
    for db in (
        bpy.data.objects, bpy.data.collections, bpy.data.meshes, bpy.data.materials,
        bpy.data.cameras, bpy.data.lights, bpy.data.worlds, bpy.data.actions,
        bpy.data.armatures, bpy.data.curves, bpy.data.images, bpy.data.node_groups,
    ):
        for block in list(db):
            try:
                db.remove(block)
            except Exception:
                pass


def mesh_extent(obj):
    """Bbox mesh lokal: (extent Vector, center Vector)."""
    xs = [v.co for v in obj.data.vertices]
    mn = Vector((min(v.x for v in xs), min(v.y for v in xs), min(v.z for v in xs)))
    mx = Vector((max(v.x for v in xs), max(v.y for v in xs), max(v.z for v in xs)))
    return mx - mn, (mn + mx) * 0.5


def append_objects(blend_path, names):
    """Append (copy) objek dari file aset. File asal tidak disentuh."""
    with bpy.data.libraries.load(blend_path, link=False) as (src, dst):
        missing = [n for n in names if n not in src.objects]
        if missing:
            raise RuntimeError("objek tidak ada di %s: %s" % (blend_path, missing))
        dst.objects = list(names)
    return [o for o in dst.objects if o is not None]


def place(obj, dims, loc, rot_z_deg, rot_y_deg=0.0):
    """Skala mesh ke `dims` (sumbu lokal, meter), putar, taruh pusat bbox di loc."""
    ext, center = mesh_extent(obj)
    obj.rotation_mode = "XYZ"
    obj.rotation_euler = (0.0, math.radians(rot_y_deg), math.radians(rot_z_deg))
    obj.scale = Vector((dims[0] / ext.x, dims[1] / ext.y, dims[2] / ext.z))
    scaled_center = Vector((center.x * obj.scale.x,
                            center.y * obj.scale.y,
                            center.z * obj.scale.z))
    obj.location = Vector(loc) - obj.rotation_euler.to_matrix() @ scaled_center


def world_bbox(objs):
    """Bbox dunia objek yang terlihat. Objek disembunyikan dilewati: Blender
    tidak mengevaluasi matrix_world mereka, jadi nilainya bisa basi."""
    lo = Vector((1e9, 1e9, 1e9))
    hi = Vector((-1e9, -1e9, -1e9))
    for obj in objs:
        if obj.hide_viewport or obj.hide_render:
            continue
        mw = obj.matrix_world
        for v in obj.data.vertices:
            w = mw @ v.co
            lo.x, lo.y, lo.z = min(lo.x, w.x), min(lo.y, w.y), min(lo.z, w.z)
            hi.x, hi.y, hi.z = max(hi.x, w.x), max(hi.y, w.y), max(hi.z, w.z)
    return lo, hi


# ---------------------------------------------------------------------------
# scute (keping karapas) — ditempel ke permukaan elipsoid karapas
# ---------------------------------------------------------------------------

def surface_frame(point, fwd=Vector((0.0, -1.0, 0.0))):
    """Kerangka tangen elipsoid karapas: X sepanjang tubuh, Y melintang, Z normal."""
    n = Vector((point.x / CAR_AX ** 2,
                point.y / CAR_AY ** 2,
                point.z / CAR_AZ ** 2)).normalized()
    along = fwd - n * fwd.dot(n)
    if along.length < 1e-5:  # di kutub depan/belakang
        along = Vector((1.0, 0.0, 0.0)) - n * n.x
    x_axis = along.normalized()
    y_axis = n.cross(x_axis).normalized()
    rot = Matrix((x_axis, y_axis, n)).transposed().to_4x4()
    return rot, n


def stick_to_shell(obj, point, dims, sink=SCUTE_SINK):
    rot, n = surface_frame(point)
    ext, _center = mesh_extent(obj)
    scale = Vector((dims[0] / ext.x, dims[1] / ext.y, dims[2] / ext.z))
    obj.matrix_world = (Matrix.Translation(point - n * sink)
                        @ rot
                        @ Matrix.Diagonal(scale.to_4d()))


def shell_point(phi_deg, z=0.0):
    """Titik di permukaan karapas pada sudut phi (0 = sisi kanan, 90 = ekor)."""
    phi = math.radians(phi_deg)
    k = math.sqrt(max(0.0, 1.0 - (z / CAR_AZ) ** 2))
    return Vector((CAR_AX * k * math.cos(phi), CAR_AY * k * math.sin(phi), z))


def place_scutes(scutes):
    """3 vertebral di punggung, 2 costal di samping, 16 marginal di tepi."""
    by_name = {s.name: s for s in scutes}

    # Vertebral: deretan tengah punggung.
    for i, y in enumerate((-0.22, 0.02, 0.26)):
        obj = by_name.get("Scute_Vert_%d" % i)
        if obj is None:
            continue
        z = CAR_AZ * math.sqrt(max(0.0, 1.0 - (y / CAR_AY) ** 2))
        stick_to_shell(obj, Vector((0.0, y, z)), SCUTE_VERT)

    # Costal: satu kiri satu kanan, agak ke depan.
    costals = [by_name.get("Scute_Costal_%d" % i) for i in (0, 1)]
    for side, obj in zip((1.0, -1.0), costals):
        if obj is None:
            continue
        x = 0.20 * side
        y = 0.02
        k = 1.0 - (x / CAR_AX) ** 2 - (y / CAR_AY) ** 2
        z = CAR_AZ * math.sqrt(max(0.0, k))
        stick_to_shell(obj, Vector((x, y, z)), SCUTE_COSTAL)

    # Marginal: 16 keping mengelilingi tepi, melewati bagian depan (leher).
    # Tetap ditempatkan di permukaan (supaya bbox bersih dan mudah diaktifkan
    # lagi), tapi disembunyikan kalau SHOW_MARGINALS False.
    margs = [by_name.get("Scute_Marg_%d" % i) for i in range(16)]
    margs = [m for m in margs if m is not None]
    start, end = -55.0, 235.0
    step = (end - start) / max(1, len(margs) - 1)
    for i, obj in enumerate(margs):
        stick_to_shell(obj, shell_point(start + i * step, z=-0.030), SCUTE_MARG)
        if not SHOW_MARGINALS:
            obj.hide_render = True
            obj.hide_viewport = True


# ---------------------------------------------------------------------------
# scene
# ---------------------------------------------------------------------------

def setup_scene():
    scn = bpy.context.scene
    scn.name = "sea_turtle-assembled"
    scn.render.resolution_x = 1920
    scn.render.resolution_y = 1080
    scn.render.resolution_percentage = 100
    scn.render.fps = 24
    scn.render.fps_base = 1.0
    scn.view_settings.view_transform = "Standard"
    scn.frame_start = 1
    scn.frame_end = 1
    scn.frame_set(1)
    # Blender 5.2 menamai EEVEE Next cukup "BLENDER_EEVEE".
    try:
        scn.render.engine = "BLENDER_EEVEE"
    except TypeError:
        pass
    return scn


def main():
    if bpy.data.is_dirty:
        print("PERINGATAN: file terbuka punya perubahan belum disimpan; "
              "data di memori akan dikosongkan oleh wipe().")

    names = list(PARTS.keys()) + ["Scute_Vert_%d" % i for i in range(3)] \
        + ["Scute_Costal_%d" % i for i in range(2)] \
        + ["Scute_Marg_%d" % i for i in range(16)]

    wipe()
    objs = append_objects(SRC, names)
    found = {o.name for o in objs}
    missing = [n for n in names if n not in found]
    if missing:
        raise RuntimeError("bagian penyu hilang setelah append: %s" % missing)

    scn = setup_scene()
    coll = bpy.data.collections.new(COLL_NAME)
    scn.collection.children.link(coll)

    pivot = bpy.data.objects.new(PIVOT_NAME, None)
    pivot.empty_display_type = "PLAIN_AXES"
    pivot.empty_display_size = 0.30
    coll.objects.link(pivot)

    # Objek hasil append mendarat di koleksi scene; pindahkan ke ENV_turtle.
    for obj in objs:
        for c in list(obj.users_collection):
            c.objects.unlink(obj)
        coll.objects.link(obj)

    parts = [o for o in objs if not o.name.startswith("Scute_")]
    scutes = [o for o in objs if o.name.startswith("Scute_")]

    for name, spec in PARTS.items():
        dims, loc, rot_z = spec[0], spec[1], spec[2]
        rot_y = spec[3] if len(spec) > 3 else 0.0
        place(bpy.data.objects[name], dims, loc, rot_z, rot_y)

    if SHOW_SCUTES:
        place_scutes(scutes)
    else:
        for s in scutes:
            s.hide_render = True
            s.hide_viewport = True

    # Parent ke satu empty supaya mudah dianimasikan.
    for obj in objs:
        obj.parent = pivot
        obj.matrix_parent_inverse = Matrix.Identity(4)

    bpy.context.view_layer.update()

    # z 0 = bagian terendah.
    lo, hi = world_bbox(objs)
    dz = -lo.z
    if abs(dz) > 1e-6:
        for obj in objs:
            obj.location.z += dz
        bpy.context.view_layer.update()
        lo, hi = world_bbox(objs)

    print("=== penyu tersusun ===")
    print("objek: %d (bagian %d + scute %d)"
          % (len(objs), len(parts), len(scutes)))
    for name in PARTS:
        obj = bpy.data.objects[name]
        lo_p, hi_p = world_bbox([obj])
        d = hi_p - lo_p
        print("  %-22s dim %.3f x %.3f x %.3f  pusat (%.3f, %.3f, %.3f)"
              % (name, d.x, d.y, d.z,
                 (lo_p.x + hi_p.x) / 2, (lo_p.y + hi_p.y) / 2, (lo_p.z + hi_p.z) / 2))
    print("  total bbox: %.3f x %.3f x %.3f m"
          % (hi.x - lo.x, hi.y - lo.y, hi.z - lo.z))
    print("  min z = %.4f  max z = %.4f" % (lo.z, hi.z))
    print("  material: %s" % sorted({m.name for o in objs for m in o.data.materials if m}))
    print("======================")


if __name__ == "__main__":
    main()

"""Bangun lingkungan dasar Scene 1 (Pulau Bunaken dari udara) — buatan sendiri.

Membuat terrain pulau Bunaken (stilisasi low-poly), laut dengan reef-flat → garis
drop-off → laut dalam, kerucut Gunung Manado Tua, siluet pesisir Manado di kejauhan,
langit gradasi pagi, dan matahari rendah. Semua geometri di-generate prosedural lalu
flat-shaded dan diwarnai per-ketinggian (vertex color) dengan palet Bunaken.

Skala dipadatkan (1 unit = 1 m, pulau ±¼ ukuran asli). Jalankan di Blender via MCP
atau: exec(open(path).read()).
"""
import bpy
import bmesh
from mathutils import Vector, noise

# ---------- Palet (linear-ish sRGB, dipakai sebagai base color) ----------
PALET = {
    "laut_dalam": (0.02, 0.06, 0.20),
    "laut_sedang": (0.03, 0.18, 0.38),
    "reef": (0.10, 0.52, 0.52),
    "pasir": (0.86, 0.80, 0.62),
    "hijau": (0.18, 0.42, 0.18),
    "hijau_tua": (0.10, 0.26, 0.14),
    "gunung": (0.16, 0.22, 0.18),
    "gunung_atas": (0.30, 0.34, 0.30),
}

# ---------- Geometri pulau ----------
ICX, ICY = 0.0, -10.0      # pusat pulau
IA, IB = 90.0, 55.0        # semi-sumbu elips pulau (x, y)
PUNCAK = 15.0              # tinggi maksimum daratan
REEF_W, DROP_W = 26.0, 22.0
LAUT_DALAM_Z = -32.0


def _warna_dari_z(z):
    if z < -22:
        return PALET["laut_dalam"]
    if z < -4:
        t = (z + 22) / 18.0
        return _lerp(PALET["laut_dalam"], PALET["laut_sedang"], t)
    if z < 0.0:
        return PALET["reef"]
    if z < 1.6:
        return PALET["pasir"]
    if z < 6.0:
        return PALET["hijau"]
    return PALET["hijau_tua"]


def _lerp(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def height(x, y):
    nx, ny = x * 0.014, y * 0.014
    n = noise.noise(Vector((nx, ny, 0.0)))
    n2 = noise.noise(Vector((nx * 3.1, ny * 3.1, 5.3)))
    e = (((x - ICX) / IA) ** 2 + ((y - ICY) / IB) ** 2) ** 0.5
    e *= 1.0 + 0.12 * n              # pantai tidak bulat sempurna
    if e < 1.0:
        land = 1.0 - e
        h = land * PUNCAK + n * 3.0 + n2 * 1.2
        return max(h, 0.35 * (1.0 - e) + 0.2)   # tetap di atas air di dalam pulau
    dm = (e - 1.0) * ((IA + IB) / 2.0)           # jarak di luar pulau (meter)
    if dm < REEF_W:
        return -1.4 + n2 * 0.5
    if dm < REEF_W + DROP_W:
        t = (dm - REEF_W) / DROP_W
        return -1.4 + t * (LAUT_DALAM_Z - -1.4) + n2 * 1.2
    return LAUT_DALAM_Z + n * 2.2


def _mat_vertex_color(nama):
    mat = bpy.data.materials.get(nama)
    if mat:
        return mat
    mat = bpy.data.materials.new(nama)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    if "Roughness" in bsdf.inputs:
        bsdf.inputs["Roughness"].default_value = 1.0
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 0.1
    attr = nt.nodes.new("ShaderNodeVertexColor")
    attr.layer_name = "Col"
    nt.links.new(attr.outputs["Color"], bsdf.inputs["Base Color"])
    return mat


def _grid_mesh(nama, x0, x1, y0, y1, cell, hfn, color_fn, warp=0.0):
    nx = int((x1 - x0) / cell) + 1
    ny = int((y1 - y0) / cell) + 1
    bm = bmesh.new()
    verts = [[None] * ny for _ in range(nx)]
    for i in range(nx):
        for j in range(ny):
            x = x0 + i * cell
            y = y0 + j * cell
            if warp:
                x += noise.noise(Vector((x * 0.03, y * 0.03, 1.0))) * warp
                y += noise.noise(Vector((x * 0.03, y * 0.03, 2.0))) * warp
            verts[i][j] = bm.verts.new((x, y, hfn(x, y)))
    for i in range(nx - 1):
        for j in range(ny - 1):
            bm.faces.new((verts[i][j], verts[i + 1][j], verts[i + 1][j + 1], verts[i][j + 1]))
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    col = bm.loops.layers.color.new("Col")
    for f in bm.faces:
        for loop in f.loops:
            c = color_fn(loop.vert.co.z)
            loop[col] = (c[0], c[1], c[2], 1.0)
    me = bpy.data.meshes.new(nama)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(nama, me)
    obj.data.materials.append(_mat_vertex_color("M_Terrain"))
    for p in obj.data.polygons:
        p.use_smooth = False
    return obj


def build_terrain(coll):
    obj = _grid_mesh("Terrain_Bunaken", -200, 200, -200, 170, 5.0, height, _warna_dari_z, warp=1.5)
    coll.objects.link(obj)
    return obj


def build_manado_tua(coll):
    # kerucut low-poly dengan puncak ber-noise, berdiri dari dasar laut
    cx, cy = -155.0, 135.0
    base_r, tinggi = 72.0, 96.0
    seg = 13
    bm = bmesh.new()
    import math
    ring = []
    for k in range(seg):
        a = 2 * math.pi * k / seg
        rr = base_r * (1.0 + 0.08 * noise.noise(Vector((a, 0, 7))))
        ring.append(bm.verts.new((cx + math.cos(a) * rr, cy + math.sin(a) * rr, LAUT_DALAM_Z)))
    puncak = bm.verts.new((cx + 4, cy + 2, LAUT_DALAM_Z + tinggi))
    col = bm.loops.layers.color.new("Col")
    faces = []
    for k in range(seg):
        faces.append(bm.faces.new((ring[k], ring[(k + 1) % seg], puncak)))
    # tutup alas
    bm.faces.new(ring)
    for f in bm.faces:
        for loop in f.loops:
            z = loop.vert.co.z
            c = PALET["gunung_atas"] if z > LAUT_DALAM_Z + tinggi * 0.7 else PALET["gunung"]
            loop[col] = (c[0], c[1], c[2], 1.0)
    me = bpy.data.meshes.new("ManadoTua")
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new("ManadoTua", me)
    o.data.materials.append(_mat_vertex_color("M_Terrain"))
    for p in o.data.polygons:
        p.use_smooth = False
    coll.objects.link(o)
    return o


def build_pesisir_jauh(coll):
    # daratan Manado di kaki langit: ridge panjang yang muncul dari air,
    # alas depan ~z0 (garis pantai), naik ke ±28 m, lalu turun di belakang.
    Y0 = 330.0
    def h(x, y):
        d = y - Y0                                   # jarak dari garis pantai depan
        if d < 0:
            return -2.0                              # masih laut dangkal di depan pantai
        prof = max(0.0, 1.0 - abs(d - 55.0) / 70.0)  # puncak ridge ~55 m di belakang pantai
        base = 24.0 + 12.0 * noise.noise(Vector((x * 0.008, 0, 3)))
        return -1.0 + base * prof + noise.noise(Vector((x * 0.03, y * 0.03, 8))) * 2.0
    def col(z):
        if z < 0.2:
            return PALET["reef"]
        if z < 2.0:
            return PALET["pasir"]
        return PALET["hijau_tua"]
    obj = _grid_mesh("PesisirManado", -700, 700, 300, 470, 12.0, h, col)
    coll.objects.link(obj)
    return obj


def build_water(coll):
    bm = bmesh.new()
    import math
    x0, x1, y0, y1, cell = -1400, 1400, -1400, 1400, 28.0
    nx = int((x1 - x0) / cell) + 1
    ny = int((y1 - y0) / cell) + 1
    verts = [[None] * ny for _ in range(nx)]
    for i in range(nx):
        for j in range(ny):
            x, y = x0 + i * cell, y0 + j * cell
            w = 0.18 * math.sin(x * 0.12 + y * 0.09) + 0.12 * noise.noise(Vector((x * 0.05, y * 0.05, 9)))
            verts[i][j] = bm.verts.new((x, y, w))
    for i in range(nx - 1):
        for j in range(ny - 1):
            bm.faces.new((verts[i][j], verts[i + 1][j], verts[i + 1][j + 1], verts[i][j + 1]))
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new("Laut")
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new("Laut", me)
    for p in o.data.polygons:
        p.use_smooth = False
    o.data.materials.append(_mat_air())
    coll.objects.link(o)
    return o


def _mat_air():
    mat = bpy.data.materials.get("M_Air")
    if mat:
        return mat
    mat = bpy.data.materials.new("M_Air")
    mat.use_nodes = True
    mat.blend_method = "BLEND" if hasattr(mat, "blend_method") else mat.blend_method
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (0.05, 0.35, 0.55, 1.0)
    if "Roughness" in bsdf.inputs:
        bsdf.inputs["Roughness"].default_value = 0.08
    if "Alpha" in bsdf.inputs:
        bsdf.inputs["Alpha"].default_value = 0.72
    if "Transmission Weight" in bsdf.inputs:
        bsdf.inputs["Transmission Weight"].default_value = 0.35
    try:
        mat.blend_method = "BLEND"
    except Exception:
        pass
    return mat


def setup_world_sky():
    world = bpy.context.scene.world or bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    mapr = nt.nodes.new("ShaderNodeMapRange")   # petakan Incoming.z (-1..1) -> 0..1
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    mapr.inputs["From Min"].default_value = -0.15
    mapr.inputs["From Max"].default_value = 0.65
    # gradasi langit pagi: horizon hangat -> kabut -> biru di atas
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = (0.97, 0.80, 0.58, 1.0)   # horizon jingga lembut
    el = ramp.color_ramp.elements.new(0.12)
    el.color = (0.82, 0.84, 0.84, 1.0)                            # kabut tipis dekat horizon
    ramp.color_ramp.elements[-1].position = 0.75
    ramp.color_ramp.elements[-1].color = (0.30, 0.53, 0.82, 1.0)  # biru langit
    nt.links.new(geo.outputs["Incoming"], sep.inputs["Vector"])
    nt.links.new(sep.outputs["Z"], mapr.inputs["Value"])
    nt.links.new(mapr.outputs["Result"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 0.65   # redup agar matahari dominan, tak flat
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])


def setup_sun():
    import math
    data = bpy.data.lights.new("MatahariPagi", type="SUN")
    data.energy = 4.6
    data.angle = math.radians(1.5)
    data.color = (1.0, 0.86, 0.68)   # hangat pagi
    sun = bpy.data.objects.new("MatahariPagi", data)
    sun.rotation_euler = (math.radians(64), 0.0, math.radians(40))  # matahari ~26° di atas horizon
    bpy.context.scene.collection.objects.link(sun)
    return sun


def build():
    sc = bpy.context.scene
    # collection lingkungan
    env = bpy.data.collections.get("Lingkungan")
    if env is None:
        env = bpy.data.collections.new("Lingkungan")
        sc.collection.children.link(env)
    build_terrain(env)
    build_manado_tua(env)
    build_pesisir_jauh(env)
    build_water(env)
    setup_world_sky()
    setup_sun()
    # kabut jarak jauh (EEVEE mist via volume ringan dilewati; andalkan gradasi langit)
    print("Lingkungan selesai:", [o.name for o in env.objects])


if __name__ == "__main__":
    build()

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
    "laut_dalam": (0.02, 0.14, 0.34),     # biru laut dalam
    "pasir_dasar": (0.62, 0.74, 0.64),    # dasar laut berpasir (terbaca turquoise lewat air jernih)
    "pasir_dangkal": (0.88, 0.87, 0.72),  # pasir dangkal dekat pantai (terang)
    "pasir": (0.90, 0.85, 0.68),          # pasir pantai kering
    "buih": (0.95, 0.97, 0.95),           # buih tepi pantai
    "reef": (0.22, 0.62, 0.58),           # karang dangkal
    "hijau": (0.34, 0.56, 0.26),          # rumput
    "hijau_terang": (0.50, 0.68, 0.34),   # bercak rumput terang
    "hijau_tua": (0.18, 0.40, 0.20),      # rumput/semak gelap
    "gunung": (0.16, 0.24, 0.20),
    "gunung_atas": (0.34, 0.40, 0.36),
}

# ---------- Geometri pulau ----------
ICX, ICY = 0.0, -10.0      # pusat pulau
IA, IB = 90.0, 55.0        # semi-sumbu elips pulau (x, y)
PUNCAK = 15.0              # tinggi maksimum daratan
REEF_W, DROP_W = 26.0, 22.0
LAUT_DALAM_Z = -32.0


def _warna_dari_z(z):
    # dasar laut: dalam (biru) -> dangkal (pasir terang), supaya air jernih tampak turquoise
    if z < -24:
        return PALET["laut_dalam"]
    if z < -8:
        return _lerp(PALET["laut_dalam"], PALET["pasir_dasar"], (z + 24) / 16.0)
    if z < -1.0:
        return _lerp(PALET["pasir_dasar"], PALET["pasir_dangkal"], (z + 8) / 7.0)
    if z < 0.25:
        return PALET["pasir_dangkal"]          # pasir basah tepat di garis air
    if z < 0.7:
        return PALET["buih"]                   # buih/pasir basah
    if z < 2.2:
        return PALET["pasir"]                  # pantai kering
    if z < 7.0:
        return PALET["hijau"]                  # rumput (variasi ditambah di _grid_mesh)
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
            v = loop.vert.co
            c = color_fn(v.z)
            if v.z > 2.2:   # variasi rumput: bercak terang & gelap
                t = noise.noise(Vector((v.x * 0.09, v.y * 0.09, 20.0)))
                if t > 0.08:
                    c = _lerp(c, PALET["hijau_terang"], min((t - 0.08) * 1.6, 0.7))
                elif t < -0.15:
                    c = _lerp(c, PALET["hijau_tua"], min((-0.15 - t) * 1.3, 0.55))
            elif -16.0 < v.z < -0.5:   # dasar laut: bercak pasir terang/gelap (tekstur dasar)
                t = noise.noise(Vector((v.x * 0.13, v.y * 0.13, 30.0)))
                t2 = noise.noise(Vector((v.x * 0.4, v.y * 0.4, 33.0)))
                if t > 0.0:
                    c = _lerp(c, PALET["pasir_dangkal"], min(t * 1.8, 0.75))
                else:
                    c = _lerp(c, PALET["reef"], min(-t * 1.5, 0.55))
                c = _lerp(c, PALET["laut_dalam"], max(0.0, t2 * 0.2))   # bintik gelap (karang/rumput laut)
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


def build_rocks(coll):
    """Batu/boulder low-poly abu tersebar di pulau (seperti referensi)."""
    import math
    import random
    rng = random.Random(33)
    mat = bpy.data.materials.get("M_Batu")
    if mat is None:
        mat = bpy.data.materials.new("M_Batu"); mat.use_nodes = True
        b = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        b.inputs["Base Color"].default_value = (0.56, 0.57, 0.54, 1.0)
        if "Roughness" in b.inputs: b.inputs["Roughness"].default_value = 1.0
    grp = bpy.data.collections.new("Batu"); coll.children.link(grp)
    n = 0
    tries = 0
    while n < 22 and tries < 500:
        tries += 1
        a = rng.uniform(0, 2 * math.pi)
        r = rng.uniform(0.15, 0.95)
        x = ICX + math.cos(a) * IA * r
        y = ICY + math.sin(a) * IB * r
        z = height(x, y)
        if not (1.0 < z < 13.0):
            continue
        s = rng.uniform(1.2, 4.5)
        bm = bmesh.new()
        bmesh.ops.create_icosphere(bm, subdivisions=1, radius=1.0)
        for v in bm.verts:            # gepengkan + benjol acak
            v.co.x *= rng.uniform(0.8, 1.4)
            v.co.y *= rng.uniform(0.8, 1.4)
            v.co.z *= rng.uniform(0.5, 0.8)
            v.co += Vector((rng.uniform(-0.12, 0.12), rng.uniform(-0.12, 0.12), rng.uniform(-0.1, 0.1)))
        me = bpy.data.meshes.new(f"Batu_{n}")
        bm.to_mesh(me); bm.free()
        o = bpy.data.objects.new(f"Batu_{n}", me)
        o.scale = (s, s, s)
        o.location = (x, y, z - s * 0.25)   # agak terbenam
        o.rotation_euler = (0, 0, rng.uniform(0, 6.28))
        o.data.materials.append(mat)
        for p in o.data.polygons: p.use_smooth = False
        grp.objects.link(o)
        n += 1
    print("Batu:", n)
    return grp


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
            w = (0.45 * math.sin(x * 0.07 + y * 0.05)
                 + 0.22 * math.sin(x * 0.19 + y * 0.14)
                 + 0.14 * noise.noise(Vector((x * 0.06, y * 0.06, 9))))
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
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (0.06, 0.52, 0.58, 1.0)   # turquoise
    if "Roughness" in bsdf.inputs:
        bsdf.inputs["Roughness"].default_value = 0.02                   # mengkilap -> kilau matahari
    if "Alpha" in bsdf.inputs:
        bsdf.inputs["Alpha"].default_value = 0.40                       # lebih jernih: dasar pasir tembus
    if "Transmission Weight" in bsdf.inputs:
        bsdf.inputs["Transmission Weight"].default_value = 0.0
    if "IOR" in bsdf.inputs:
        bsdf.inputs["IOR"].default_value = 1.33

    # --- riak permukaan: dua noise skala beda -> bump normal (gerak & dimensi air) ---
    texc = nt.nodes.new("ShaderNodeTexCoord")
    mapp = nt.nodes.new("ShaderNodeMapping"); mapp.name = "RippleMap"
    n1 = nt.nodes.new("ShaderNodeTexNoise"); n1.inputs["Scale"].default_value = 0.18; n1.inputs["Detail"].default_value = 3.0
    n2 = nt.nodes.new("ShaderNodeTexNoise"); n2.inputs["Scale"].default_value = 0.6; n2.inputs["Detail"].default_value = 2.0
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "FLOAT"; mix.inputs["Factor"].default_value = 0.4
    bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.35; bump.inputs["Distance"].default_value = 0.6
    nt.links.new(texc.outputs["Object"], mapp.inputs["Vector"])
    nt.links.new(mapp.outputs["Vector"], n1.inputs["Vector"])
    nt.links.new(mapp.outputs["Vector"], n2.inputs["Vector"])
    nt.links.new(n1.outputs["Fac"], mix.inputs["A"])
    nt.links.new(n2.outputs["Fac"], mix.inputs["B"])
    nt.links.new(mix.outputs["Result"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

    # --- guratan buih/busa di permukaan: warna air bervariasi (turquoise -> toska terang) ---
    nstreak = nt.nodes.new("ShaderNodeTexNoise")
    nstreak.inputs["Scale"].default_value = 0.35
    nstreak.inputs["Detail"].default_value = 4.0
    smap = nt.nodes.new("ShaderNodeMapping"); smap.inputs["Scale"].default_value = (0.3, 1.0, 1.0)  # diregangkan -> guratan
    cramp = nt.nodes.new("ShaderNodeValToRGB")
    cramp.color_ramp.elements[0].position = 0.42
    cramp.color_ramp.elements[0].color = (0.06, 0.52, 0.58, 1.0)   # turquoise
    cramp.color_ramp.elements[1].position = 0.72
    cramp.color_ramp.elements[1].color = (0.42, 0.78, 0.80, 1.0)   # toska terang (busa)
    nt.links.new(texc.outputs["Object"], smap.inputs["Vector"])
    nt.links.new(smap.outputs["Vector"], nstreak.inputs["Vector"])
    nt.links.new(nstreak.outputs["Fac"], cramp.inputs["Fac"])
    nt.links.new(cramp.outputs["Color"], bsdf.inputs["Base Color"])
    smap.name = "StreakMap"
    # animasi riak: geser mapping mengikuti frame
    drv = mapp.inputs["Location"].driver_add("default_value", 0).driver
    drv.expression = "frame * 0.02"
    drv2 = mapp.inputs["Location"].driver_add("default_value", 1).driver
    drv2.expression = "frame * 0.014"

    try:
        mat.blend_method = "BLEND"
    except Exception:
        pass
    if hasattr(mat, "show_transparent_back"):
        mat.show_transparent_back = False
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
    mapr.inputs["From Max"].default_value = 0.7
    # langit tropis cerah: horizon putih-cyan -> cyan -> biru cerah di atas
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = (0.80, 0.93, 0.97, 1.0)   # horizon putih-cyan
    el = ramp.color_ramp.elements.new(0.3)
    el.color = (0.52, 0.82, 0.93, 1.0)                            # cyan cerah
    ramp.color_ramp.elements[-1].position = 0.9
    ramp.color_ramp.elements[-1].color = (0.22, 0.60, 0.90, 1.0)  # biru langit cerah
    nt.links.new(geo.outputs["Incoming"], sep.inputs["Vector"])
    nt.links.new(sep.outputs["Z"], mapr.inputs["Value"])
    nt.links.new(mapr.outputs["Result"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 1.1    # terang (siang tropis)
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])


def setup_sun():
    import math
    data = bpy.data.lights.new("MatahariPagi", type="SUN")
    data.energy = 5.2
    data.angle = math.radians(1.5)
    data.color = (1.0, 0.96, 0.88)   # siang tropis, sedikit hangat
    sun = bpy.data.objects.new("MatahariPagi", data)
    sun.rotation_euler = (math.radians(52), 0.0, math.radians(35))  # matahari ~38° (lebih tinggi)
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
    build_rocks(env)
    build_manado_tua(env)
    build_pesisir_jauh(env)
    build_water(env)
    setup_world_sky()
    setup_sun()
    # kabut jarak jauh (EEVEE mist via volume ringan dilewati; andalkan gradasi langit)
    print("Lingkungan selesai:", [o.name for o in env.objects])


if __name__ == "__main__":
    build()

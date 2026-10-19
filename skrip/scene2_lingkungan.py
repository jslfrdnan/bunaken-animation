"""Bangun lingkungan bawah air Scene 2 (Menyelam) — buatan sendiri.

Geografi Bunaken: **reef flat dangkal berkarang** (lantai datar) → **tepi drop-off**
(dinding tegak) → **laut dalam**. Karang tumbuh rata di lantai reef (bukan di dinding).
Permukaan laut dari bawah, gradasi kedalaman, matahari + gelembung. Flat-shaded,
diwarnai per-vertex. Skala: permukaan z=0, reef flat z≈-9, dasar dalam z=-44.
"""
import bpy
import bmesh
from mathutils import Vector, noise

REEF_Z = -9.0          # kedalaman lantai reef flat
EDGE_Y = -8.0          # garis tepi drop-off (reef di y>EDGE_Y, jurang di y<EDGE_Y)
DEEP_Z = -44.0

PALET = {
    "pasir": (0.50, 0.52, 0.44),       # pasir reef
    "karang_batu": (0.34, 0.44, 0.36), # batu berkarang (kehijauan)
    "dinding": (0.20, 0.26, 0.28),     # muka drop-off
    "dinding_bawah": (0.08, 0.14, 0.18),
    "pasir_dalam": (0.14, 0.22, 0.28),
}


def _mat_vcol(nama):
    mat = bpy.data.materials.get(nama)
    if mat:
        return mat
    mat = bpy.data.materials.new(nama); mat.use_nodes = True
    nt = mat.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    if "Roughness" in b.inputs: b.inputs["Roughness"].default_value = 1.0
    if "Specular IOR Level" in b.inputs: b.inputs["Specular IOR Level"].default_value = 0.1
    vc = nt.nodes.new("ShaderNodeVertexColor"); vc.layer_name = "Col"
    nt.links.new(vc.outputs["Color"], b.inputs["Base Color"])
    return mat


def _flat(o):
    for p in o.data.polygons: p.use_smooth = False


def build_reef_floor(coll):
    """Lantai reef flat datar + bergelombang halus, di y > EDGE_Y."""
    x0, x1, y0, y1, cell = -55, 55, EDGE_Y, 44, 3.0
    nx = int((x1 - x0) / cell) + 1
    ny = int((y1 - y0) / cell) + 1
    bm = bmesh.new()
    V = [[None] * ny for _ in range(nx)]
    for i in range(nx):
        for j in range(ny):
            x = x0 + i * cell
            y = y0 + j * cell
            z = REEF_Z + noise.noise(Vector((x * 0.07, y * 0.07, 1))) * 1.3 \
                + noise.noise(Vector((x * 0.2, y * 0.2, 4))) * 0.4
            V[i][j] = bm.verts.new((x, y, z))
    for i in range(nx - 1):
        for j in range(ny - 1):
            bm.faces.new((V[i][j], V[i + 1][j], V[i + 1][j + 1], V[i][j + 1]))
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    col = bm.loops.layers.color.new("Col")
    for f in bm.faces:
        for lo in f.loops:
            v = lo.vert.co
            t = noise.noise(Vector((v.x * 0.15, v.y * 0.15, 9)))
            c = PALET["karang_batu"] if t > 0.15 else PALET["pasir"]
            lo[col] = (*c, 1.0)
    me = bpy.data.meshes.new("ReefFlat"); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new("ReefFlat", me)
    o.data.materials.append(_mat_vcol("M_Reef")); _flat(o)
    coll.objects.link(o)
    return o


def build_dropoff(coll):
    """Dinding tepi drop-off di y=EDGE_Y, dari reef (z=REEF_Z) turun ke z=DEEP_Z. Latar."""
    x0, x1, z0, z1, cell = -55, 55, DEEP_Z, REEF_Z, 3.0
    nx = int((x1 - x0) / cell) + 1
    nz = int((z1 - z0) / cell) + 1
    bm = bmesh.new()
    V = [[None] * nz for _ in range(nx)]
    for i in range(nx):
        for k in range(nz):
            x = x0 + i * cell
            z = z0 + k * cell
            n = noise.noise(Vector((x * 0.04, z * 0.05, 0)))
            y = EDGE_Y - (2.0 + n * 3.0)       # menjorok ke -Y (ke jurang)
            if k == nz - 1:
                y = EDGE_Y                      # bibir menyambung lantai reef
            V[i][k] = bm.verts.new((x, y, z))
    for i in range(nx - 1):
        for k in range(nz - 1):
            bm.faces.new((V[i][k], V[i + 1][k], V[i + 1][k + 1], V[i][k + 1]))
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    for f in bm.faces:
        if f.normal.y < 0:
            f.normal_flip()
    col = bm.loops.layers.color.new("Col")
    for f in bm.faces:
        for lo in f.loops:
            z = lo.vert.co.z
            c = PALET["dinding"] if z > -26 else PALET["dinding_bawah"]
            lo[col] = (*c, 1.0)
    me = bpy.data.meshes.new("Dropoff"); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new("Dropoff", me)
    o.data.materials.append(_mat_vcol("M_Dinding")); _flat(o)
    coll.objects.link(o)
    return o


def build_dasar(coll):
    x0, x1, y0, y1, cell = -70, 70, -70, EDGE_Y, 6.0
    nx = int((x1 - x0) / cell) + 1; ny = int((y1 - y0) / cell) + 1
    bm = bmesh.new(); V = [[None] * ny for _ in range(nx)]
    for i in range(nx):
        for j in range(ny):
            x = x0 + i * cell; y = y0 + j * cell
            z = DEEP_Z + noise.noise(Vector((x * 0.05, y * 0.05, 7))) * 2.0
            V[i][j] = bm.verts.new((x, y, z))
    for i in range(nx - 1):
        for j in range(ny - 1):
            bm.faces.new((V[i][j], V[i + 1][j], V[i + 1][j + 1], V[i][j + 1]))
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    col = bm.loops.layers.color.new("Col")
    for f in bm.faces:
        for lo in f.loops: lo[col] = (*PALET["pasir_dalam"], 1.0)
    me = bpy.data.meshes.new("DasarLaut"); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new("DasarLaut", me)
    o.data.materials.append(_mat_vcol("M_Dasar")); _flat(o)
    coll.objects.link(o)
    return o


def build_permukaan(coll):
    import math
    x0, x1, y0, y1, cell = -120, 120, -80, 80, 6.0
    nx = int((x1 - x0) / cell) + 1; ny = int((y1 - y0) / cell) + 1
    bm = bmesh.new(); V = [[None] * ny for _ in range(nx)]
    for i in range(nx):
        for j in range(ny):
            x = x0 + i * cell; y = y0 + j * cell
            z = 0.0 + 0.3 * math.sin(x * 0.15 + y * 0.1) + 0.2 * noise.noise(Vector((x * 0.08, y * 0.08, 2)))
            V[i][j] = bm.verts.new((x, y, z))
    for i in range(nx - 1):
        for j in range(ny - 1):
            bm.faces.new((V[i][j], V[i + 1][j], V[i + 1][j + 1], V[i][j + 1]))
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new("Permukaan"); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new("Permukaan", me)
    o.data.materials.append(_mat_permukaan()); _flat(o)
    coll.objects.link(o)
    return o


def _mat_permukaan():
    mat = bpy.data.materials.get("M_Permukaan")
    if mat: return mat
    mat = bpy.data.materials.new("M_Permukaan"); mat.use_nodes = True
    b = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (0.30, 0.55, 0.70, 1.0)
    if "Emission Color" in b.inputs:
        b.inputs["Emission Color"].default_value = (0.55, 0.75, 0.85, 1.0)
        b.inputs["Emission Strength"].default_value = 0.5
    return mat


def setup_world_underwater():
    w = bpy.context.scene.world or bpy.data.worlds.new("World")
    bpy.context.scene.world = w; w.use_nodes = True
    nt = w.node_tree
    for n in list(nt.nodes): nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    mapr = nt.nodes.new("ShaderNodeMapRange")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    mapr.inputs["From Min"].default_value = -0.6
    mapr.inputs["From Max"].default_value = 0.5
    ramp.color_ramp.elements[0].color = (0.01, 0.05, 0.11, 1.0)
    ramp.color_ramp.elements[1].color = (0.18, 0.52, 0.64, 1.0)
    nt.links.new(geo.outputs["Incoming"], sep.inputs["Vector"])
    nt.links.new(sep.outputs["Z"], mapr.inputs["Value"])
    nt.links.new(mapr.outputs["Result"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 1.0
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])


def setup_sun():
    import math
    d = bpy.data.lights.new("MatahariAtas", type="SUN")
    d.energy = 12.0; d.angle = math.radians(2); d.color = (0.95, 0.97, 1.0)
    if hasattr(d, "use_shadow"): d.use_shadow = True
    s = bpy.data.objects.new("MatahariAtas", d)
    arah = Vector((0.1, -0.4, -1.0))    # dari atas, sedikit dari depan
    s.rotation_euler = arah.to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.collection.objects.link(s)
    return s


def build_gelembung(coll):
    import random
    rng = random.Random(5)
    mat = bpy.data.materials.get("M_Gelembung") or bpy.data.materials.new("M_Gelembung")
    mat.use_nodes = True
    b = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (0.7, 0.85, 0.95, 1.0)
    if "Alpha" in b.inputs: b.inputs["Alpha"].default_value = 0.5
    try: mat.blend_method = "BLEND"
    except Exception: pass
    grp = bpy.data.collections.new("Gelembung"); coll.children.link(grp)
    for i in range(40):
        me = bpy.data.meshes.new(f"Gelembung_{i}")
        bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=1, radius=rng.uniform(0.05, 0.16))
        bm.to_mesh(me); bm.free()
        o = bpy.data.objects.new(f"Gelembung_{i}", me)
        o.location = (rng.uniform(-30, 30), rng.uniform(-6, 36), rng.uniform(REEF_Z, -1))
        o.data.materials.append(mat); _flat(o)
        grp.objects.link(o)
    return grp


def setup_eevee_volumetric():
    ee = bpy.context.scene.eevee
    for attr, val in [("use_volumetric_shadows", True), ("use_volumetric_lights", True)]:
        if hasattr(ee, attr):
            try: setattr(ee, attr, val)
            except Exception: pass


def build():
    sc = bpy.context.scene
    env = bpy.data.collections.get("Lingkungan2")
    if env is None:
        env = bpy.data.collections.new("Lingkungan2"); sc.collection.children.link(env)
    build_reef_floor(env); build_dropoff(env); build_dasar(env); build_permukaan(env)
    setup_world_underwater(); setup_sun()
    build_gelembung(env)
    setup_eevee_volumetric()
    print("Lingkungan reef flat selesai:", [o.name for o in env.objects])


if __name__ == "__main__":
    build()

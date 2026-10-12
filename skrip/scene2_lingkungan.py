"""Bangun lingkungan bawah air Scene 2 (Menyelam) — buatan sendiri.

Dinding drop-off vertikal khas Bunaken + teras dasar, permukaan laut dari bawah,
dasar laut dalam, kabut biru (volume scatter) + god rays (matahari dari atas),
caustics (noise emisi), dan gelembung naik. Semua prosedural, flat-shaded,
diwarnai per-kedalaman. Skala: permukaan z=0, dalam z=-45.
"""
import bpy
import bmesh
from mathutils import Vector, noise

# dinding drop-off di y=0, kamera di sisi +Y melihat ke -Y
WALL_Y = 0.0
TOP_Z, DEEP_Z = -1.5, -45.0

PALET = {
    "batu": (0.26, 0.30, 0.30),       # batu karang gelap (dalam)
    "batu_atas": (0.40, 0.46, 0.38),  # karang tumbuh (atas, kehijauan)
    "pasir_dalam": (0.34, 0.44, 0.48),
    "deep": (0.04, 0.10, 0.16),
}


def _mat_vcol(nama, caustic=False):
    mat = bpy.data.materials.get(nama)
    if mat:
        return mat
    mat = bpy.data.materials.new(nama)
    mat.use_nodes = True
    nt = mat.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    if "Roughness" in b.inputs: b.inputs["Roughness"].default_value = 1.0
    if "Specular IOR Level" in b.inputs: b.inputs["Specular IOR Level"].default_value = 0.1
    vc = nt.nodes.new("ShaderNodeVertexColor"); vc.layer_name = "Col"
    nt.links.new(vc.outputs["Color"], b.inputs["Base Color"])
    return mat


def _warna_dinding(z):
    if z > -6:
        return PALET["batu_atas"]
    if z > -30:
        t = (z + 30) / 24.0
        a, b = PALET["batu"], PALET["batu_atas"]
        return tuple(a[i] + (b[i]-a[i])*t for i in range(3))
    return PALET["batu"]


def build_wall(coll):
    # grid vertikal di bidang XZ (dinding), displaced ke -Y (ke dalam) + teras
    x0, x1, z0, z1, cell = -75, 75, DEEP_Z, TOP_Z, 3.0
    nx = int((x1-x0)/cell)+1
    nz = int((z1-z0)/cell)+1
    bm = bmesh.new()
    V = [[None]*nz for _ in range(nx)]
    for i in range(nx):
        for k in range(nz):
            x = x0 + i*cell
            z = z0 + k*cell
            n = noise.noise(Vector((x*0.03, z*0.05, 0)))
            n2 = noise.noise(Vector((x*0.09, z*0.12, 3)))
            y = WALL_Y - (6.0 + n*3.0 + n2*1.5)          # dinding selalu di -Y (depan kamera)
            # teras/ledge: sedikit MENJOROK ke dalam (lebih negatif), bukan ke kamera
            if -12 < z < -9 or -26 < z < -23:
                y -= 2.5
            y = min(y, -1.5)                              # jangan pernah menonjol ke +Y
            V[i][k] = bm.verts.new((x, y, z))
    for i in range(nx-1):
        for k in range(nz-1):
            bm.faces.new((V[i][k], V[i+1][k], V[i+1][k+1], V[i][k+1]))
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    # pastikan normal menghadap +Y (ke kamera)
    for f in bm.faces:
        if f.normal.y < 0:
            f.normal_flip()
    col = bm.loops.layers.color.new("Col")
    coral = (0.55, 0.42, 0.40)   # bercak karang/ warm
    for f in bm.faces:
        for lo in f.loops:
            v = lo.vert.co
            c = _warna_dinding(v.z)
            t = noise.noise(Vector((v.x*0.12, v.z*0.12, 11)))
            if t > 0.35:                                   # bercak karang hangat sesekali
                m = min((t-0.35)/0.4, 1.0) * 0.6
                c = tuple(c[i] + (coral[i]-c[i])*m for i in range(3))
            lo[col] = (*c, 1.0)
    me = bpy.data.meshes.new("DindingDropoff")
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new("DindingDropoff", me)
    o.data.materials.append(_mat_vcol("M_Reef"))
    for p in o.data.polygons: p.use_smooth = False
    coll.objects.link(o)
    return o


def build_dasar(coll):
    # dasar laut dalam di kaki dinding
    x0, x1, y0, y1, cell = -90, 90, -60, 10, 6.0
    nx=int((x1-x0)/cell)+1; ny=int((y1-y0)/cell)+1
    bm=bmesh.new(); V=[[None]*ny for _ in range(nx)]
    for i in range(nx):
        for j in range(ny):
            x=x0+i*cell; y=y0+j*cell
            z=DEEP_Z + noise.noise(Vector((x*0.05,y*0.05,7)))*2.0
            V[i][j]=bm.verts.new((x,y,z))
    for i in range(nx-1):
        for j in range(ny-1):
            bm.faces.new((V[i][j],V[i+1][j],V[i+1][j+1],V[i][j+1]))
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    col=bm.loops.layers.color.new("Col")
    for f in bm.faces:
        for lo in f.loops: lo[col]=(*PALET["pasir_dalam"],1.0)
    me=bpy.data.meshes.new("DasarLaut"); bm.to_mesh(me); bm.free()
    o=bpy.data.objects.new("DasarLaut",me)
    o.data.materials.append(_mat_vcol("M_Dasar"))
    for p in o.data.polygons: p.use_smooth=False
    coll.objects.link(o)
    return o


def build_permukaan(coll):
    # permukaan laut dilihat dari bawah: terang, beriak
    import math
    x0,x1,y0,y1,cell=-120,120,-80,80,6.0
    nx=int((x1-x0)/cell)+1; ny=int((y1-y0)/cell)+1
    bm=bmesh.new(); V=[[None]*ny for _ in range(nx)]
    for i in range(nx):
        for j in range(ny):
            x=x0+i*cell; y=y0+j*cell
            z=0.0 + 0.3*math.sin(x*0.15+y*0.1)+0.2*noise.noise(Vector((x*0.08,y*0.08,2)))
            V[i][j]=bm.verts.new((x,y,z))
    for i in range(nx-1):
        for j in range(ny-1):
            bm.faces.new((V[i][j],V[i+1][j],V[i+1][j+1],V[i][j+1]))
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    me=bpy.data.meshes.new("Permukaan"); bm.to_mesh(me); bm.free()
    o=bpy.data.objects.new("Permukaan",me)
    o.data.materials.append(_mat_permukaan())
    for p in o.data.polygons: p.use_smooth=False
    coll.objects.link(o)
    return o


def _mat_permukaan():
    mat=bpy.data.materials.get("M_Permukaan")
    if mat: return mat
    mat=bpy.data.materials.new("M_Permukaan"); mat.use_nodes=True
    nt=mat.node_tree; b=next(n for n in nt.nodes if n.type=="BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value=(0.30,0.55,0.70,1.0)
    if "Emission Color" in b.inputs:
        b.inputs["Emission Color"].default_value=(0.55,0.75,0.85,1.0)
        b.inputs["Emission Strength"].default_value=0.6
    return mat


def setup_world_underwater():
    w=bpy.context.scene.world or bpy.data.worlds.new("World")
    bpy.context.scene.world=w; w.use_nodes=True
    nt=w.node_tree
    for n in list(nt.nodes): nt.nodes.remove(n)
    out=nt.nodes.new("ShaderNodeOutputWorld")
    bg=nt.nodes.new("ShaderNodeBackground")
    # gradasi kedalaman: aqua terang ke arah permukaan (atas) -> biru gelap ke dalam (bawah)
    geo=nt.nodes.new("ShaderNodeNewGeometry")
    sep=nt.nodes.new("ShaderNodeSeparateXYZ")
    mapr=nt.nodes.new("ShaderNodeMapRange")
    ramp=nt.nodes.new("ShaderNodeValToRGB")
    mapr.inputs["From Min"].default_value=-0.6
    mapr.inputs["From Max"].default_value=0.5
    ramp.color_ramp.elements[0].position=0.0
    ramp.color_ramp.elements[0].color=(0.01,0.05,0.11,1.0)   # dalam, gelap
    ramp.color_ramp.elements[1].position=1.0
    ramp.color_ramp.elements[1].color=(0.18,0.52,0.64,1.0)   # dekat permukaan, aqua terang
    nt.links.new(geo.outputs["Incoming"], sep.inputs["Vector"])
    nt.links.new(sep.outputs["Z"], mapr.inputs["Value"])
    nt.links.new(mapr.outputs["Result"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value=1.0
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])
    # catatan: volume scatter dilepas (bikin gelap & sulit disetel); kontras dari sun + gradasi.


def setup_sun():
    import math
    d=bpy.data.lights.new("MatahariAtas",type="SUN")
    d.energy=12.0; d.angle=math.radians(2); d.color=(0.95,0.97,1.0)
    if hasattr(d, "use_shadow"): d.use_shadow = True
    s=bpy.data.objects.new("MatahariAtas",d)
    # cahaya datang dari atas-depan (+Y,+Z), menyinari muka dinding (+Y) & permukaan atas
    arah = Vector((0.1, -1.0, -0.8))   # arah rambat cahaya
    s.rotation_euler = arah.to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.collection.objects.link(s)
    return s


def build_gelembung(coll):
    # beberapa untai gelembung (ico-sphere kecil) yang akan dianimasikan naik di scene2_kamera
    import random
    rng=random.Random(5)
    mat=bpy.data.materials.get("M_Gelembung") or bpy.data.materials.new("M_Gelembung")
    mat.use_nodes=True
    b=next(n for n in mat.node_tree.nodes if n.type=="BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value=(0.7,0.85,0.95,1.0)
    if "Alpha" in b.inputs: b.inputs["Alpha"].default_value=0.5
    try: mat.blend_method="BLEND"
    except Exception: pass
    grp=bpy.data.collections.new("Gelembung"); coll.children.link(grp)
    for i in range(40):
        me=bpy.data.meshes.new(f"Gelembung_{i}")
        bm=bmesh.new()
        bmesh.ops.create_icosphere(bm, subdivisions=1, radius=rng.uniform(0.05,0.18))
        bm.to_mesh(me); bm.free()
        o=bpy.data.objects.new(f"Gelembung_{i}", me)
        o.location=(rng.uniform(-30,30), rng.uniform(-8,8), rng.uniform(TOP_Z, DEEP_Z))
        o.data.materials.append(mat)
        for p in o.data.polygons: p.use_smooth=False
        grp.objects.link(o)
    return grp


def setup_eevee_volumetric():
    ee = bpy.context.scene.eevee
    for attr, val in [("volumetric_start", 0.1), ("volumetric_end", 220.0),
                      ("volumetric_samples", 64), ("volumetric_tile_size", "4"),
                      ("use_volumetric_shadows", True), ("use_volumetric_lights", True)]:
        if hasattr(ee, attr):
            try:
                setattr(ee, attr, val)
            except Exception as e:
                print("  eevee", attr, e)


def build():
    sc=bpy.context.scene
    env=bpy.data.collections.get("Lingkungan2")
    if env is None:
        env=bpy.data.collections.new("Lingkungan2"); sc.collection.children.link(env)
    build_wall(env); build_dasar(env); build_permukaan(env)
    setup_world_underwater(); setup_sun()
    build_gelembung(env)
    setup_eevee_volumetric()
    print("Lingkungan bawah air selesai:", [o.name for o in env.objects])


if __name__ == "__main__":
    build()

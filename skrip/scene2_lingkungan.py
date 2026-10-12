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
    "batu": (0.10, 0.16, 0.18),
    "batu_atas": (0.16, 0.28, 0.26),
    "pasir_dalam": (0.20, 0.30, 0.38),
    "deep": (0.01, 0.03, 0.08),
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
    if caustic:
        # caustics: noise -> emisi biru-hijau lembut, pola bergerak (animasi via mapping offset)
        tex = nt.nodes.new("ShaderNodeTexNoise")
        tex.inputs["Scale"].default_value = 6.0
        tex.inputs["Detail"].default_value = 2.0
        mapp = nt.nodes.new("ShaderNodeMapping")
        texc = nt.nodes.new("ShaderNodeTexCoord")
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].position = 0.55
        ramp.color_ramp.elements[0].color = (0, 0, 0, 1)
        ramp.color_ramp.elements[1].position = 0.75
        ramp.color_ramp.elements[1].color = (0.25, 0.55, 0.6, 1)
        nt.links.new(texc.outputs["Object"], mapp.inputs["Vector"])
        nt.links.new(mapp.outputs["Vector"], tex.inputs["Vector"])
        nt.links.new(tex.outputs["Fac"], ramp.inputs["Fac"])
        if "Emission Color" in b.inputs:
            nt.links.new(ramp.outputs["Color"], b.inputs["Emission Color"])
            b.inputs["Emission Strength"].default_value = 1.2
        mapp.name = "CausticMapping"
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
            y = WALL_Y - (3.5 + n*4.0 + n2*1.5)          # tonjolan dinding ke -Y
            # teras/ledge di beberapa kedalaman
            if -12 < z < -9 or -26 < z < -23:
                y += 4.0
            V[i][k] = bm.verts.new((x, y, z))
    for i in range(nx-1):
        for k in range(nz-1):
            bm.faces.new((V[i][k], V[i+1][k], V[i+1][k+1], V[i][k+1]))
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    col = bm.loops.layers.color.new("Col")
    for f in bm.faces:
        for lo in f.loops:
            c = _warna_dinding(lo.vert.co.z)
            lo[col] = (*c, 1.0)
    me = bpy.data.meshes.new("DindingDropoff")
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new("DindingDropoff", me)
    o.data.materials.append(_mat_vcol("M_Reef", caustic=True))
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
    o.data.materials.append(_mat_vcol("M_Dasar", caustic=True))
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
    bg.inputs["Color"].default_value=(0.02,0.10,0.20,1.0)
    bg.inputs["Strength"].default_value=0.5
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])
    # kabut biru: volume scatter di world
    vol=nt.nodes.new("ShaderNodeVolumeScatter")
    vol.inputs["Color"].default_value=(0.06,0.22,0.34,1.0)
    vol.inputs["Density"].default_value=0.018
    vol.inputs["Anisotropy"].default_value=0.4
    nt.links.new(vol.outputs["Volume"], out.inputs["Volume"])


def setup_sun():
    import math
    d=bpy.data.lights.new("MatahariAtas",type="SUN")
    d.energy=6.0; d.angle=math.radians(3); d.color=(0.7,0.85,1.0)
    s=bpy.data.objects.new("MatahariAtas",d)
    s.rotation_euler=(math.radians(18),0,math.radians(15))  # hampir dari atas (god rays tegak)
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


def build():
    sc=bpy.context.scene
    env=bpy.data.collections.get("Lingkungan2")
    if env is None:
        env=bpy.data.collections.new("Lingkungan2"); sc.collection.children.link(env)
    build_wall(env); build_dasar(env); build_permukaan(env)
    setup_world_underwater(); setup_sun()
    build_gelembung(env)
    print("Lingkungan bawah air selesai:", [o.name for o in env.objects])


if __name__ == "__main__":
    build()

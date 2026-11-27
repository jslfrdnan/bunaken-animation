"""swap-fish-v004-shots.py — ganti sekolah ikan v003 -> v004 di shot Scene 1.

JALUR HEADLESS (tanpa Blender MCP, bukan milik sesi ini):

    & "D:\\Blender Foundation\\Blender 5.2\\blender.exe" -b ^
        -P scripts/swap-fish-v004-shots.py -- 030 [--no-still]

Satu proses = satu shot (030 / 040 / 050). Skrip membuka file shot yang sudah ada
(hasil build-scene-1-v004-shots.py), lalu:

  1. Mengukur posisi dunia tiap ikan v003 + jalur centroid sekolah (per frame),
     sebelum apa pun dihapus. Jalur dasar ini disimpan sebagai properti pivot
     (`fish_base_path`) supaya skrip idempoten: dijalankan dua kali tidak
     menumpuk offset.
  2. Menghapus mesh + armature v003 dan action renang v003.
  3. Append aset v004 (link=False) + lima action `ENV_act_<sp>_swim[_p1.._p4]`.
     Mesh v004 menghadap -Y, up +Z, jadi rotasi lokal ikan cukup jitter kecil —
     tidak ada lagi Euler manual +-90 seperti v003.
  4. Pivot dipindah ke centroid sekolah; anak-anaknya memakai offset relatif
     centroid (sehingga rotasi pivot memutar formasi di tempat, bukan
     mengayunkan sekolah sejauh 5 m seperti file v003).
  5. Orientasi: setiap keyframe (tiap frame) rotasi pivot =
     `tangent.to_track_quat('-Y', 'Z')`. Tangent = beda hingga jalur (dasar +
     orbit), bukan Euler karangan.
  6. Fase: action bergiliran `_swim`, `_p1`..`_p4` per ikan + jitter kecil.
  7. Simpan di frame 1 (EEVEE, 1920x1080, 24 fps, Standard, tanpa pack) lalu
     render still 50% frame 48 sesudah look dipasang (look TIDAK disimpan).

Kamera, karang, lamun, dan look tidak disentuh.
"""

import bpy
import datetime
import importlib.util
import math
import os
import random
import shutil
import sys
from mathutils import Matrix, Quaternion, Vector

ROOT = r"D:/Tugas Semester 5/Grafika Komputer/Project-Animasi"
ENV = ROOT + "/assets/env"
SCENES = ROOT + "/scenes"
STILLS = ROOT + "/renders/stills"
TMP = ROOT + "/renders/tmp"
LOGPATH = ROOT + "/renders/logs/technical.log"

P_FISH = {
    "cakalang": ENV + "/fish-cakalang-rig_v004.blend",
    "kakatua": ENV + "/fish-kakatua_v004.blend",
    "damselfish": ENV + "/fish-damselfish_v004.blend",
}
ASSET_ARM = {
    "cakalang": "CHR_cakalang_rig",
    "kakatua": "CHR_fish_kakatua_rig",
    "damselfish": "CHR_fish_damselfish_rig",
}
# (jumlah wajib,radius orbit horizontal m, putaran, bentuk, radius vertikal m)
SCHOOLS = {
    "cakalang": dict(count=12, amp=0.62, revs=1.00, shape="circle", bob=0.24),
    "kakatua": dict(count=20, amp=0.38, revs=1.25, shape="circle", bob=0.15),
    "damselfish": dict(count=24, amp=0.33, revs=1.50, shape="eight", bob=0.12),
}
SHOTS = {
    "030": "scene-1_shot-030_terumbu_v001.blend",
    "040": "scene-1_shot-040_penyu_v001.blend",
    "050": "scene-1_shot-050_nara-dive_v001.blend",
}
PHASE_ORDER = ["swim", "p1", "p2", "p3", "p4"]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def log(phase, line):
    os.makedirs(os.path.dirname(LOGPATH), exist_ok=True)
    stamp = datetime.datetime.now().strftime("%H:%M")
    with open(LOGPATH, "a", encoding="utf-8") as fh:
        fh.write("[%s] %s - %s\n" % (stamp, phase, line))
    print("[log]", phase, line)


# --------------------------------------------------------------------- util ---


def action_fcurves(act):
    """Blender 5.x: action.fcurves tidak ada; fcurve hidup di channelbag."""
    out = []
    try:
        for layer in act.layers:
            for strip in layer.strips:
                for bag in getattr(strip, "channelbags", []):
                    out.extend(bag.fcurves)
    except AttributeError:
        pass
    if not out:
        try:
            out = list(act.fcurves)
        except AttributeError:
            pass
    return out


def purge_orphans(passes=3):
    for _ in range(passes):
        for db in (bpy.data.meshes, bpy.data.materials, bpy.data.armatures,
                   bpy.data.actions, bpy.data.collections):
            for block in list(db):
                try:
                    if block.users == 0 and not block.use_fake_user:
                        db.remove(block)
                except Exception:
                    pass


def world_rot(ob):
    """Rotasi dunia ternormalisasi (buang skala)."""
    m = ob.matrix_world.to_3x3()
    return m.to_quaternion()


# ------------------------------------------------------- jalur & orientasi ---


class SchoolPath:
    """Jalur pivot: drift dasar (hasil sampling v003) + orbit kecil di bidang
    tegak lurus arah jalan.

    Catatan penting: jalur v003 di file shot ternyata LINEAR ber-ease, bukan
    lingkar/angka-delapan. Drift dasarnya dipertahankan (cepat f1-40, melambat
    f40-72, pergi f72-96) lewat lengkung kuadratik + parameter ulang panjang
    busur; orbit ditambahkan supaya tangent benar-benar melengkung. Orbit sengaja
    TANPA komponen searah jalan — kalau ada, orbit bisa membalik arah saat fase
    melambat. Kecepatan orbit ikut kecepatan drift supaya fase cepat-melambat-
    pergi tetap terasa.
    """

    def __init__(self, base, f0, f1, amp, revs, shape, bob):
        self.base = base          # {frame: Vector} jalur dasar mentah
        self.f0 = f0
        self.f1 = f1
        self.amp = amp
        self.revs = revs
        self.shape = shape
        self.bob = bob
        self.up = Vector((0.0, 0.0, 1.0))
        self._build_curve()
        self.base_s = self._retime()
        self.phase = self._build_phase()
        self.pos = {}
        self._build_positions()

    # --- jalur dasar -------------------------------------------------------
    def raw_at(self, f):
        f = max(self.f0, min(self.f1, f))
        lo = int(math.floor(f))
        hi = min(self.f1, lo + 1)
        t = f - lo
        a = self.raw_map.get(lo, self.raw_map.get(hi))
        b = self.raw_map.get(hi, a)
        return a.lerp(b, t)

    @property
    def raw_map(self):
        if not hasattr(self, "_raw_map"):
            self._raw_map = {f: self.base[f] for f in range(self.f0, self.f1 + 1)}
        return self._raw_map

    def _build_curve(self):
        """Lengkung kuadratik lewat tiga titik: awal, tengah, akhir jalur v003.

        Dipakai pengganti spline melalui banyak knot: knot dari jalur v003 yang
        nyaris berhenti membuat spline bisa berbalik arah. Lengkung kuadratik
        tidak pernah berbalik (titik kontrolnya terurut), jadi arah jalan selalu
        terdefinisi. Bentuk lengkung tetap mengikuti jalur asli (naik 0,5 m).
        """
        raw = self.raw_map
        p0 = raw[self.f0].copy()
        p2 = raw[self.f1].copy()
        fm = (self.f0 + self.f1) // 2
        acc = Vector()
        for k in range(-3, 4):
            acc += raw[min(self.f1, max(self.f0, fm + k))]
        m = acc / 7.0
        p1 = m * 2.0 - (p0 + p2) * 0.5
        self.bz = (p0, p1, p2)

    def curve_at(self, t):
        u = 1.0 - t
        return (self.bz[0] * (u * u) + self.bz[1] * (2.0 * u * t)
                + self.bz[2] * (t * t))

    def _retime(self):
        """Parameter ulang per panjang busur dengan kecepatan minimum.

        Jalur v003 nyaris berhenti di tengah (1,6 mm/frame) sementara z masih
        naik: tangent mentahnya nyaris vertikal dan arahnya berbalik. Kecepatan
        dasar diberi lantai 6% kecepatan puncak — fase melambat tetap lambat,
        tetapi arah jalan tetap terdefinisi dan tidak ada ikan yang berputar
        180 derajat dalam satu frame.
        """
        speeds = {}
        for f in range(self.f0, self.f1 + 1):
            speeds[f] = (self.raw_at(f + 0.5) - self.raw_at(f - 0.5)).length
        smax = max(speeds.values()) or 1.0
        vmin = 0.06 * smax
        dist = {self.f0: 0.0}
        for f in range(self.f0 + 1, self.f1 + 1):
            dist[f] = dist[f - 1] + max(speeds[f], vmin)

        n = 2000
        arc = [(0.0, self.curve_at(0.0))]
        acc = 0.0
        for k in range(1, n + 1):
            p = self.curve_at(k / float(n))
            acc += (p - arc[-1][1]).length
            arc.append((acc, p))
        arc_total = acc or 1.0
        scale = arc_total / (dist[self.f1] or 1.0)

        def at_arc(d):
            d = max(0.0, min(arc_total, d))
            lo, hi = 0, len(arc) - 1
            while lo < hi - 1:
                mid = (lo + hi) // 2
                if arc[mid][0] <= d:
                    lo = mid
                else:
                    hi = mid
            d0, p0 = arc[lo]
            d1, p1 = arc[hi]
            t = 0.0 if d1 - d0 < 1e-9 else (d - d0) / (d1 - d0)
            return p0.lerp(p1, t)

        return {f: at_arc(dist[f] * scale) for f in range(self.f0, self.f1 + 1)}

    def base_at(self, f):
        f = max(self.f0, min(self.f1, f))
        lo = int(math.floor(f))
        hi = min(self.f1, lo + 1)
        t = f - lo
        a = self.base_s[lo]
        b = self.base_s[hi]
        return a.lerp(b, t)

    def speed_base(self, f):
        return (self.base_at(f + 0.5) - self.base_at(f - 0.5)).length

    def _build_phase(self):
        """Fase orbit terakumulasi; laju orbit dibatasi oleh kecepatan drift.

        Batas 0,35 x kecepatan drift: sudut belok sekolah maksimal ~19 derajat,
        jadi formasi tidak berputar jauh dan tangent tetap dekat arah jalan.
        Di fase melambat orbit ikut melambat (bukan berputar di tempat).
        """
        speeds = {f: self.speed_base(f) for f in range(self.f0, self.f1 + 1)}
        step_nom = 2.0 * math.pi * self.revs / float(self.f1 - self.f0)
        amp = max(1e-4, self.amp)
        acc = 0.0
        out = {self.f0: 0.0}
        for f in range(self.f0 + 1, self.f1 + 1):
            step = min(step_nom, 0.35 * speeds[f] / amp)
            acc += step
            out[f] = acc
        return out

    # --- posisi & tangent --------------------------------------------------
    def _build_positions(self):
        prev_h = None
        for f in range(self.f0, self.f1 + 1):
            t = self.base_at(f + 1) - self.base_at(f - 1)
            h = Vector((t.x, t.y, 0.0))
            if h.length < 1e-6:
                h = prev_h.copy() if prev_h is not None else Vector((1.0, 0.0, 0.0))
            h.normalize()
            prev_h = h
            side = h.cross(self.up)
            if side.length < 1e-6:
                side = Vector((0.0, -1.0, 0.0))
            side.normalize()
            th = self.phase[f]
            if self.shape == "circle":
                # lingkar (elips) di bidang tegak lurus arah jalan
                off = side * (self.amp * math.sin(th)) + self.up * (self.bob * math.cos(th))
            else:
                # angka-delapan (Gerono) di bidang tegak lurus arah jalan
                off = (side * (self.amp * math.sin(th))
                       + self.up * (self.bob * math.sin(2.0 * th)))
            self.pos[f] = self.base_at(f) + off

    def at(self, f):
        f = max(self.f0, min(self.f1, f))
        lo = int(math.floor(f))
        hi = min(self.f1, lo + 1)
        t = f - lo
        return self.pos[lo].lerp(self.pos[hi], t)

    def tangent(self, f):
        t = self.at(f + 0.5) - self.at(f - 0.5)
        if t.length < 1e-8:
            t = self.pos[min(self.f1, int(f) + 1)] - self.pos[max(self.f0, int(f) - 1)]
        if t.length < 1e-8:
            return Vector((1.0, 0.0, 0.0))
        return t.normalized()


# ------------------------------------------------------------------- swap ---


def sample_school(arms):
    """Posisi & skala dunia tiap ikan + jalur centroid, per frame (v003 lama)."""
    scn = bpy.context.scene
    f0, f1 = scn.frame_start, scn.frame_end
    path = {}
    first = {}
    for f in range(f0, f1 + 1):
        scn.frame_set(f)
        bpy.context.view_layer.update()
        pts = [a.matrix_world.translation.copy() for a in arms]
        path[f] = sum(pts, Vector()) / float(len(pts))
        if f == f0:
            first = {a.name: (a.matrix_world.translation.copy(), a.scale.copy())
                     for a in arms}
    scn.frame_set(f0)
    bpy.context.view_layer.update()
    return path, first


def append_fish_asset(kind):
    """Append koleksi ENV_fish + lima action renang v004 (link=False)."""
    path = P_FISH[kind]
    arm_name = ASSET_ARM[kind]
    act_prefix = "ENV_act_%s_swim" % kind
    before_objs = set(bpy.data.objects.keys())
    before_acts = set(bpy.data.actions.keys())
    before_colls = set(bpy.data.collections.keys())
    with bpy.data.libraries.load(path, link=False) as (src, dst):
        if "ENV_fish" not in src.collections:
            raise RuntimeError("koleksi ENV_fish tidak ada di " + path)
        dst.collections = ["ENV_fish"]
        dst.actions = [n for n in src.actions if n.startswith(act_prefix)]
    new_colls = [bpy.data.collections[n] for n in bpy.data.collections.keys()
                 if n not in before_colls]
    new_coll = new_colls[0] if new_colls else None
    objs = [bpy.data.objects[n] for n in bpy.data.objects.keys() if n not in before_objs]
    acts = [bpy.data.actions[n] for n in bpy.data.actions.keys() if n not in before_acts]
    src_arm = next((o for o in objs if o.type == "ARMATURE" and o.name == arm_name), None)
    if src_arm is None:
        src_arm = next((o for o in objs if o.type == "ARMATURE"), None)
    if src_arm is None:
        raise RuntimeError("armature %s tidak ditemukan di %s" % (arm_name, path))
    src_meshes = [o for o in objs if o.type == "MESH"]
    print("  append %s: %d objek, %d action %s"
          % (os.path.basename(path), len(objs), len(acts), [a.name for a in acts]))
    return src_arm, src_meshes, acts, objs, new_coll


def build_school(kind, cfg, pivot, src_arm, src_meshes, acts, first, base_path):
    scn = bpy.context.scene
    coll = bpy.data.collections["ENV_school_" + kind]
    f0, f1 = scn.frame_start, scn.frame_end
    path = SchoolPath(base_path, f0, f1, cfg["amp"], cfg["revs"], cfg["shape"], cfg["bob"])

    p0 = pivot.parent.matrix_world if pivot.parent else Matrix.Identity(4)
    p0_inv = p0.inverted()
    q_ref = path.tangent(f0).to_track_quat("-Y", "Z")
    q_ref_local = (p0.to_quaternion().inverted() @ q_ref)
    centroid0 = path.at(f0)

    rng = random.Random(4104 + cfg["count"])
    old = dict(first)
    names = sorted(old.keys())

    pivot.animation_data_clear()
    pivot.rotation_mode = "QUATERNION"

    made = []
    for i in range(1, cfg["count"] + 1):
        if i - 1 < len(names):
            world0, scale0 = old[names[i - 1]]
        else:
            world0 = centroid0 + Vector((rng.uniform(-0.4, 0.4),
                                         rng.uniform(-0.4, 0.4),
                                         rng.uniform(-0.15, 0.15)))
            scale0 = Vector((1.0, 1.0, 1.0))
        local = q_ref.inverted() @ (world0 - centroid0)
        a = src_arm.copy()
        a.data = src_arm.data
        a.name = "ENV_fish_%s_%02d_rig" % (kind, i)
        coll.objects.link(a)
        a.parent = pivot
        a.matrix_parent_inverse = Matrix.Identity(4)
        a.location = local
        a.rotation_mode = "XYZ"
        a.rotation_euler = (math.radians(rng.uniform(-2.0, 2.0)),
                            math.radians(rng.uniform(-1.5, 1.5)),
                            math.radians(rng.uniform(-3.5, 3.5)))
        a.scale = scale0
        role = PHASE_ORDER[(i - 1) % len(PHASE_ORDER)]
        act = next((x for x in acts
                    if x.name == "ENV_act_%s_%s" % (kind, role)), None)
        if act is None:
            act = acts[(i - 1) % len(acts)]
        ad = a.animation_data or a.animation_data_create()
        ad.action = act
        try:
            if len(act.slots):
                ad.action_slot = act.slots[0]
        except Exception as exc:
            print("  PERINGATAN action_slot %s: %s" % (a.name, exc))
        for sm in src_meshes:
            m = sm.copy()
            m.data = sm.data
            suffix = sm.name[len("ENV_fish_" + kind):]
            m.name = "ENV_fish_%s_%02d%s" % (kind, i, suffix)
            coll.objects.link(m)
            m.parent = a
            m.matrix_parent_inverse = Matrix.Identity(4)
            m.matrix_basis = Matrix.Identity(4)
            for mod in m.modifiers:
                if mod.type == "ARMATURE":
                    mod.object = a
        made.append(a)

    # kunci jalur + orientasi tiap frame
    for f in range(f0, f1 + 1):
        world_p = path.at(f)
        local_p = p0_inv @ world_p
        q = path.tangent(f).to_track_quat("-Y", "Z")
        q_local = p0.to_quaternion().inverted() @ q
        pivot.location = local_p
        pivot.rotation_quaternion = q_local
        pivot.keyframe_insert("location", frame=f)
        pivot.keyframe_insert("rotation_quaternion", frame=f)
    ad = pivot.animation_data
    if ad and ad.action:
        for fc in action_fcurves(ad.action):
            for kp in fc.keyframe_points:
                kp.interpolation = "LINEAR"
    pivot["fish_asset"] = "v004"
    pivot["fish_phase"] = ",".join(PHASE_ORDER)
    pivot["fish_path_shape"] = cfg["shape"]
    pivot["fish_path_amp"] = cfg["amp"]
    pivot["fish_path_revs"] = cfg["revs"]
    pivot["fish_base_frame0"] = f0
    flat = []
    for f in range(f0, f1 + 1):
        v = base_path[f]
        flat.extend([v.x, v.y, v.z])
    pivot["fish_base_path"] = flat

    act_set = sorted({(a.animation_data.action.name if a.animation_data and a.animation_data.action else "-")
                      for a in made})
    print("  %-11s %2d ikan | action %s | orbit %s A=%.2f n=%.2f"
          % (kind, len(made), act_set, cfg["shape"], cfg["amp"], cfg["revs"]))
    return made


def store_base_path(pivot, base_path, f0, f1):
    flat = []
    for f in range(f0, f1 + 1):
        v = base_path[f]
        flat.extend([v.x, v.y, v.z])
    pivot["fish_base_path"] = flat
    pivot["fish_base_frame0"] = f0


def read_base_path(pivot, f0, f1):
    flat = list(pivot.get("fish_base_path", []))
    if len(flat) != 3 * (f1 - f0 + 1):
        return None
    out = {}
    for k, f in enumerate(range(f0, f1 + 1)):
        out[f] = Vector((flat[3 * k], flat[3 * k + 1], flat[3 * k + 2]))
    return out


def swap_shot(key):
    path = os.path.join(SCENES, SHOTS[key])
    if not os.path.exists(path):
        raise SystemExit("shot tidak ada: " + path)
    bak = os.path.join(TMP, "backup-%s_v000.blend" % SHOTS[key][:-10])
    os.makedirs(TMP, exist_ok=True)
    if not os.path.exists(bak):
        shutil.copy2(path, bak)
        print("BACKUP:", os.path.basename(bak))

    bpy.ops.wm.open_mainfile(filepath=path)
    scn = bpy.context.scene
    f0, f1 = scn.frame_start, scn.frame_end
    print("=== SWAP s1-%s (%s) frame %d-%d ===" % (key, scn.name, f0, f1))

    for kind, cfg in SCHOOLS.items():
        coll = bpy.data.collections.get("ENV_school_" + kind)
        if coll is None:
            raise SystemExit("koleksi ENV_school_%s tidak ada" % kind)
        pivot = bpy.data.objects.get("ENV_school_%s_pivot" % kind)
        if pivot is None:
            raise SystemExit("pivot %s tidak ada" % kind)
        arms = [o for o in coll.objects if o.type == "ARMATURE"]
        meshes = [o for o in coll.objects if o.type == "MESH"]
        if len(arms) != cfg["count"]:
            raise SystemExit("%s: armature %d, harus %d" % (kind, len(arms), cfg["count"]))

        base = read_base_path(pivot, f0, f1)
        if base is None:
            base, first = sample_school(arms)
        else:
            print("  %-11s jalur dasar dibaca dari properti pivot (tidak menumpuk orbit)" % kind)
            scn.frame_set(f0)
            bpy.context.view_layer.update()
            first = {a.name: (a.matrix_world.translation.copy(), a.scale.copy())
                     for a in arms}

        # buang v003
        for ob in meshes + arms:
            if ob.name in bpy.data.objects:
                bpy.data.objects.remove(ob, do_unlink=True)
        for act in list(bpy.data.actions):
            if act.name.startswith("ENV_act_%s_swim" % kind):
                bpy.data.actions.remove(act)
        old_piv = "ENV_school_%s_pivotAction" % kind
        if old_piv in bpy.data.actions:
            bpy.data.actions.remove(bpy.data.actions[old_piv])
        purge_orphans()

        src_arm, src_meshes, acts, objs, new_coll = append_fish_asset(kind)
        # action loop: file shot 96 frame, action hanya 32 frame
        for act in acts:
            for fc in action_fcurves(act):
                if not any(m.type == "CYCLES" for m in fc.modifiers):
                    mod = fc.modifiers.new("CYCLES")
                    mod.mode_before = "REPEAT"
                    mod.mode_after = "REPEAT"
            act.use_fake_user = True
        build_school(kind, cfg, pivot, src_arm, src_meshes, acts, first, base)

        for ob in objs:
            if ob.name in bpy.data.objects:
                bpy.data.objects.remove(ob, do_unlink=True)
        if new_coll is not None and new_coll.name in bpy.data.collections:
            try:
                bpy.data.collections.remove(new_coll)
            except Exception as exc:
                print("  koleksi aset tidak bisa dilepas:", exc)
        purge_orphans()

    # buang sisa koleksi ENV_fish kosong
    for c in list(bpy.data.collections):
        if c.name.startswith("ENV_fish") and len(c.objects) == 0:
            bpy.data.collections.remove(c)

    for lby in list(bpy.data.libraries):
        try:
            bpy.data.libraries.remove(lby)
        except Exception as exc:
            print("library tidak bisa dilepas:", lby.filepath, exc)

    scn.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=path)
    size = os.path.getsize(path)
    objs_total = len([o for o in bpy.data.objects])
    arms_total = len([o for o in bpy.data.objects if o.type == "ARMATURE"])
    print("SAVED %s (%d bytes, %d objek, %d armature)"
          % (os.path.basename(path), size, objs_total, arms_total))
    return path, size


def self_test(key):
    """Cek cepat di file yang baru disimpan: dot maju vs tangent, up z, sirip."""
    scn = bpy.context.scene
    f0, f1 = scn.frame_start, scn.frame_end
    samples = [int(round(f0 + (f1 - f0) * i / 19.0)) for i in range(20)]
    rows = []
    for kind in SCHOOLS:
        coll = bpy.data.collections["ENV_school_" + kind]
        arms = [o for o in coll.objects if o.type == "ARMATURE"]
        pivot = bpy.data.objects["ENV_school_%s_pivot" % kind]
        dots = []
        ups = []
        for f in samples:
            scn.frame_set(f)
            bpy.context.view_layer.update()
            p0 = pivot.matrix_world.translation.copy()
            scn.frame_set(max(f0, f - 1))
            bpy.context.view_layer.update()
            pm = pivot.matrix_world.translation.copy()
            scn.frame_set(min(f1, f + 1))
            bpy.context.view_layer.update()
            pp = pivot.matrix_world.translation.copy()
            tan = (pp - pm)
            if tan.length < 1e-8:
                continue
            tan.normalize()
            scn.frame_set(f)
            bpy.context.view_layer.update()
            for a in arms:
                fwd = (a.matrix_world.to_3x3() @ Vector((0.0, -1.0, 0.0))).normalized()
                up = (a.matrix_world.to_3x3() @ Vector((0.0, 0.0, 1.0))).normalized()
                dots.append(fwd.dot(tan))
                ups.append(up.z)
        rows.append((kind, min(dots), sum(dots) / len(dots), min(ups), len(dots)))
        print("  cek %-11s dot min %.4f rata %.4f | up z min %.4f | %d sampel"
              % rows[-1])

        # ekor bergerak & loop melewati frame 32?
        probe = arms[0]
        pos = {}
        for f in (1, 9, 41, 49):
            scn.frame_set(f)
            bpy.context.view_layer.update()
            pb = probe.pose.bones.get("tail_02") or probe.pose.bones.get("tail_01")
            pos[f] = probe.matrix_world @ pb.tail
        print("     probe %s: |f1-f9|=%.4f m |f9-f41|=%.4f |f1-f49|=%.4f"
              % (probe.name, (pos[1] - pos[9]).length, (pos[9] - pos[41]).length,
                 (pos[1] - pos[49]).length))
    scn.frame_set(1)
    return rows


def still(key, frame=48, percent=50):
    look = _load("looklib_swap", ROOT + "/scripts/look.py")
    scn = bpy.context.scene
    out = os.path.join(STILLS, "anim-s1-%s_v001.png" % key)
    os.makedirs(STILLS, exist_ok=True)
    try:
        rep = look.apply_look(scn, 1, above_water=None)
        scn.frame_set(int(frame))
        look.render_still(scn, out, percent=percent, samples=24)
        scn.frame_set(1)
        print("STILL:", out, os.path.exists(out), "| world", rep["world"],
              "| water", rep["water_objects"])
    except Exception as exc:
        print("STILL GAGAL:", repr(exc))


def main(argv):
    args = argv[argv.index("--") + 1:] if "--" in argv else []
    if not args:
        print("pakai: -- <030|040|050> [--no-still]")
        return
    key = args[0]
    if key not in SHOTS:
        raise SystemExit("shot tidak dikenal: " + key)
    log("ANIM", "swap ikan v004 s1-%s dimulai (12 cakalang / 20 kakatua / 24 damselfish)" % key)
    path, size = swap_shot(key)
    rows = self_test(key)
    txt = "; ".join("%s dot min %.4f rata %.4f up z min %.4f"
                    % (k, mn, mean, uz) for k, mn, mean, uz, _ in rows)
    log("VERIFY", "s1-%s ikan v004: %s (%d bytes)" % (key, txt, size))
    if "--no-still" not in args:
        still(key, 48, 50)
    log("DONE", "s1-%s ikan v004 terpasang, orientasi ikut tangent" % key)
    print("SELESAI", path)


if __name__ == "__main__":
    main(sys.argv)

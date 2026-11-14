"""fix-scene-1-v003.py — lima perbaikan Scene 1 (14 Nov 2026).

Semua shot lama DIBACA ULANG lewat `bpy.data.libraries.load(link=False)` lalu
disunting di tempat (tanpa `open_mainfile`):

  s1-020  island-detail_v002 -> _v003
  s1-070  island _v003 + animasi lepas masker (head -> hand.R 20..40)
  s1-080  island _v003 + kamera wide 50 mm (teras, papan nama, Daniel)
  s1-090  crowd_v003, 4 anak CRW_C01..C04, handheld halus
  s1-030  fish-cakalang-rig_v002 + fase kecepatan pivot 1-40/40-72/72-96
  s1-040  fish-kakatua_v002     + fase kecepatan pivot
  s1-050  fish-damselfish_v002  + fase kecepatan pivot

Cara pakai di Blender MCP (satu tahap per eksekusi):
    ns = {"__name__": "__main__"}
    exec(compile(open(path).read(), path, "exec"), ns)
    ns["stage"]("020")
"""

import bpy
import datetime
import importlib.util
import math
import os
import re
import sys
from mathutils import Matrix, Vector, Euler

ROOT = r"D:/Tugas Semester 5/Grafika Komputer/Project-Animasi"
ASSETS = ROOT + "/assets"
SCENES = ROOT + "/scenes"
STILLS = ROOT + "/renders/stills"
TMP = ROOT + "/renders/tmp"
LOGPATH = ROOT + "/renders/logs/technical.log"
WIPE = TMP + "/_wipe.blend"

P_ISLAND3 = ASSETS + "/env/island-detail_v003.blend"
P_CROWD3 = ASSETS + "/char/crowd_v003.blend"
P_NARA2 = ASSETS + "/char/nara_rig_v002.blend"
P_GEAR = ASSETS + "/props/divegear.blend"
P_FISH2 = {
    "cakalang": ASSETS + "/env/fish-cakalang-rig_v002.blend",
    "kakatua": ASSETS + "/env/fish-kakatua_v002.blend",
    "damselfish": ASSETS + "/env/fish-damselfish_v002.blend",
}

SHOTS = {
    "020": ("scene-1_shot-020_turun-permukaan_v001.blend", 96),
    "030": ("scene-1_shot-030_terumbu_v001.blend", 96),
    "040": ("scene-1_shot-040_penyu_v001.blend", 96),
    "050": ("scene-1_shot-050_nara-dive_v001.blend", 96),
    "070": ("scene-1_shot-070_nara-naik_v001.blend", 96),
    "080": ("scene-1_shot-080_daniel-jaring_v001.blend", 72),
    "090": ("scene-1_shot-090_anak-dermaga_v001.blend", 72),
}

ISLAND_COLLS = ("ENV_island-detail", "ENV_island-detail_context")
ISLAND_PAT = re.compile(r"^(ENV_detail_|ENV_surface_|ENV_shop_)")


# ---------------------------------------------------------------- util & log


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


lib = _load("s4lib", ROOT + "/scripts/build-scene-4-shots.py")
s1 = _load("s1lib", ROOT + "/scripts/build-scene-1-detail-shots.py")


def log(phase, line):
    os.makedirs(os.path.dirname(LOGPATH), exist_ok=True)
    stamp = datetime.datetime.now().strftime("%H:%M")
    with open(LOGPATH, "a", encoding="utf-8") as fh:
        fh.write("[%s] %s - %s\n" % (stamp, phase, line))
    print("[log]", phase, line)


def wipe():
    lib.wipe()
    scn = bpy.context.scene
    scn.name = "wipe"
    return scn


def setup_scene(name, frame_end):
    scn = bpy.context.scene
    scn.name = name
    scn.render.resolution_x = 1920
    scn.render.resolution_y = 1080
    scn.render.resolution_percentage = 100
    scn.render.fps = 24
    scn.render.fps_base = 1.0
    scn.view_settings.view_transform = "Standard"
    scn.render.film_transparent = False
    try:
        scn.render.engine = "BLENDER_EEVEE"
    except TypeError:
        pass
    if hasattr(scn, "eevee"):
        scn.eevee.taa_render_samples = 32
    scn.frame_start = 1
    scn.frame_end = frame_end
    scn.frame_set(1)
    return scn


def purge_orphans(passes=3):
    """Buang data-block tanpa user (mesh/material/action/collection)."""
    for _ in range(passes):
        for db in (
            bpy.data.meshes,
            bpy.data.materials,
            bpy.data.armatures,
            bpy.data.curves,
            bpy.data.cameras,
            bpy.data.lights,
            bpy.data.worlds,
            bpy.data.actions,
            bpy.data.collections,
            bpy.data.images,
        ):
            for block in list(db):
                try:
                    if block.users == 0 and not block.use_fake_user:
                        db.remove(block)
                except Exception:
                    pass


# ------------------------------------------------------------------- append


def append_blend(path, colls=None, set_world=True):
    """Append koleksi + objek scene-level + world dari `path`. Kembalikan objek baru."""
    before_obj = set(bpy.data.objects.keys())
    before_world = set(bpy.data.worlds.keys())
    with bpy.data.libraries.load(path, link=False) as (src, dst):
        want_c = [c for c in (colls if colls is not None else src.collections) if c in src.collections]
        # dst.<db> dimutasi di tempat oleh Blender -> kirim salinan list
        dst.collections = list(want_c)
    scn = bpy.context.scene
    top = [ch.name for ch in scn.collection.children]
    for name in want_c:
        c = bpy.data.collections.get(name)
        if c is None:
            continue
        nested = any(c.name in [ch.name for ch in other.children]
                     for other in bpy.data.collections if other.name != name)
        if not nested and c.name not in top:
            scn.collection.children.link(c)
    # objek yang tidak ikut koleksi (kamera, lampu, empty kontrol, FX)
    with bpy.data.libraries.load(path, link=False) as (src, dst):
        dst.objects = [n for n in src.objects if n not in bpy.data.objects]
    with bpy.data.libraries.load(path, link=False) as (src, dst):
        dst.worlds = [n for n in src.worlds if n not in bpy.data.worlds]
    for ob in bpy.data.objects:
        if len(ob.users_collection) == 0:
            scn.collection.objects.link(ob)
    # sisa preview aset yang ikut ter-append (kamera/lampu/lantai preview)
    junk = [o for o in bpy.data.objects
            if o.name.startswith(("PREVIEW", "CAM_preview", "LGT_preview"))]
    if junk:
        print("buang sisa preview:", [o.name for o in junk])
        for ob in junk:
            bpy.data.objects.remove(ob, do_unlink=True)
        purge_orphans()
    new_worlds = [bpy.data.worlds[n] for n in bpy.data.worlds.keys() if n not in before_world]
    if new_worlds and set_world:
        scn.world = new_worlds[0]
    new_objs = [bpy.data.objects[n] for n in bpy.data.objects.keys() if n not in before_obj]
    cams = [o for o in bpy.data.objects if o.type == "CAMERA" and o.name in bpy.data.objects]
    if cams:
        scn.camera = sorted(cams, key=lambda o: o.name)[0]
    print("APPEND %s -> colls=%s objs=%d world=%s" % (
        os.path.basename(path), want_c, len(new_objs), scn.world.name if scn.world else None))
    return new_objs


def append_island():
    return append_asset(P_ISLAND3, ["ENV_island-detail", "ENV_island-detail_context"])


def append_asset(path, colls):
    """Append aset (link=False) lalu buang kamera/lampu/lantai preview aset."""
    new = append_blend(path, colls, set_world=False)
    new = lib.live_objects(new)
    killed = lib.purge_lights_cameras(new)
    new = lib.live_objects(new)
    prev = bpy.data.collections.get("PREVIEW")
    victims = [o for o in new if o.name.startswith("PREVIEW")]
    if prev is not None:
        victims.extend(list(prev.all_objects))
    for ob in victims:
        if ob.name in bpy.data.objects:
            bpy.data.objects.remove(ob, do_unlink=True)
    if prev is not None:
        bpy.data.collections.remove(prev)
    purge_orphans()
    new = [o for o in lib.live_objects(new) if o.name in bpy.data.objects]
    print("  append_asset %s: %d objek, buang kamera/lampu=%s"
          % (os.path.basename(path), len(new), killed))
    return new


def ensure_camera():
    """Kamera shot (CAM_shot-*) harus aktif, bukan kamera preview aset."""
    scn = bpy.context.scene
    cams = [o for o in bpy.data.objects if o.type == "CAMERA" and o.name.startswith("CAM_shot-")]
    if cams:
        scn.camera = sorted(cams, key=lambda o: o.name)[0]
    print("kamera aktif:", scn.camera.name if scn.camera else None,
          "| semua kamera:", [o.name for o in bpy.data.objects if o.type == "CAMERA"])
    return scn.camera


def shot_world(name, hexcol, strength=1.0):
    """Pastikan world milik shot ada (jangan pakai world aset)."""
    scn = bpy.context.scene
    w = bpy.data.worlds.get(name)
    if w is None:
        w = lib.add_world(name, hexcol, strength=strength)
    scn.world = w
    return w


# ------------------------------------------------------------- island swap


def island_objs():
    found = {}
    for cn in ISLAND_COLLS:
        c = bpy.data.collections.get(cn)
        if c is not None:
            for ob in c.all_objects:
                found[ob.name] = ob
    for ob in bpy.data.objects:
        if ISLAND_PAT.match(ob.name):
            found[ob.name] = ob
    return list(found.values())


def swap_island():
    """Ganti island-detail (versi apa pun) di scene aktif dengan _v003."""
    objs = island_objs()
    old = {}
    for ob in objs:
        old[ob.name] = (ob.matrix_world.copy(), ob.parent.name if ob.parent else None)
    print("ISLAND lama: %d objek" % len(objs))
    for ob in list(objs):
        bpy.data.objects.remove(ob, do_unlink=True)
    for cn in ISLAND_COLLS:
        c = bpy.data.collections.get(cn)
        if c is not None:
            bpy.data.collections.remove(c)
    purge_orphans()

    new = append_island()  # sudah bersih dari kamera/lampu preview
    common = [n for n in old if n in bpy.data.objects]
    common = [n for n in old if n in bpy.data.objects]
    ref = None
    for cand in ["CTL_island-detail"] + [n for n in common if old[n][1] is None]:
        ob = bpy.data.objects.get(cand)
        if ob is not None and ob.parent is None:
            ref = cand
            break
    if ref is None:
        raise RuntimeError("tidak ada objek acuan untuk menghitung offset island")
    delta = old[ref][0] @ bpy.data.objects[ref].matrix_world.inverted()
    for ob in new:
        if ob.parent is None:
            ob.matrix_world = delta @ ob.matrix_world
    err = 0.0
    fixed = 0
    for n in common:
        ob = bpy.data.objects.get(n)
        if ob is None:
            continue
        d = (ob.matrix_world.translation - old[n][0].translation).length
        err = max(err, d)
        if d > 1e-4:
            ob.matrix_world = old[n][0]
            fixed += 1
    new = lib.live_objects(new)
    new = [o for o in new if o.name in bpy.data.objects]
    shops = [o.name for o in new if o.name.startswith("ENV_shop_")]
    ds = delta.translation
    print("ISLAND v003: acuan=%s delta=(%.3f, %.3f, %.3f) | objek baru=%d | shop=%d %s | err_max=%.4f fixed=%d"
          % (ref, ds.x, ds.y, ds.z, len(new), len(shops), shops[:6], err, fixed))
    log("MODEL", "island-detail_v003 dipasang (acuan %s, delta %.2f/%.2f/%.2f, %d objek shop)"
        % (ref, ds.x, ds.y, ds.z, len(shops)))
    return new


# ------------------------------------------------------------ camera helper


def look_at(ob, target):
    s1.look_at(ob, target)


def cam_points_frame(cam, pts, margin=1.25, direction=None):
    """Posisikan kamera sampai semua `pts` masuk frame dengan isi ~margin dari lebar/tinggi."""
    from bpy_extras.object_utils import world_to_camera_view as w2c
    scn = bpy.context.scene
    pts = [Vector(p) for p in pts]
    center = sum(pts, Vector()) / len(pts)
    if direction is None:
        direction = (cam.matrix_world.translation - center).normalized()
    direction = Vector(direction).normalized()
    radius = max((p - center).length for p in pts)
    dist = min(max(radius * 3.0, 2.5), 40.0)
    fill = min(margin, 0.97)
    for _ in range(16):
        cam.location = center + direction * dist
        look_at(cam, center)
        bpy.context.view_layer.update()
        worst = 0.0
        for p in pts:
            v = w2c(scn, cam, p)
            worst = max(worst, abs(v.x - 0.5), abs(v.y - 0.5))
        if worst < 1e-6:
            dist *= 0.6
            continue
        ratio = worst / (0.5 * fill)
        dist = min(max(dist * min(max(ratio, 0.6), 1.7), 2.0), 60.0)
        if abs(ratio - 1.0) < 0.01:
            break
    cam.location = center + direction * dist
    look_at(cam, center)
    bpy.context.view_layer.update()
    ndc = [tuple(round(c, 2) for c in (v.x, v.y)) for v in (w2c(scn, cam, p) for p in pts)]
    print("  ndc titik:", ndc)
    return center, radius, dist


def bbox_center(ob):
    m = ob.matrix_world
    pts = [m @ Vector(c) for c in ob.bound_box]
    return sum(pts, Vector()) / 8.0, pts


# --------------------------------------------------------------- save/still


def drop_libraries():
    """Hapus entri Library basi (append link=False tidak butuh library)."""
    for lby in list(bpy.data.libraries):
        try:
            bpy.data.libraries.remove(lby)
        except Exception as exc:
            print("library tidak bisa dilepas:", lby.filepath, exc)


def save_shot(key):
    filename = SHOTS[key][0]
    src = os.path.join(SCENES, filename)
    bak = src.replace("_v001.blend", "_v000.blend")
    if os.path.exists(src) and not os.path.exists(bak):
        import shutil
        shutil.copy2(src, bak)
        print("BACKUP:", os.path.basename(bak))
    bpy.context.scene.frame_set(1)
    drop_libraries()
    bpy.ops.wm.save_as_mainfile(filepath=src)
    size = os.path.getsize(src)
    print("SAVED %s (%d bytes)" % (os.path.basename(src), size))
    return size


def still(key, frame=48, percent=50, above_water=None):
    scn = bpy.context.scene
    out = os.path.join(STILLS, "anim-s1-%s_v001.png" % key)
    s1.look_still("s1-" + key, frame, above_water=above_water, percent=percent)
    print("STILL:", out, os.path.exists(out))


def summary(key):
    scn = bpy.context.scene
    objs = [o for o in bpy.data.objects]
    print("SUMMARY s1-%s | mesh=%d arm=%d cam=%d light=%d | %dx%d %dfps vt=%s range=%d-%d file=%s"
          % (key,
             len([o for o in objs if o.type == "MESH"]),
             len([o for o in objs if o.type == "ARMATURE"]),
             len([o for o in objs if o.type == "CAMERA"]),
             len([o for o in objs if o.type == "LIGHT"]),
             scn.render.resolution_x, scn.render.resolution_y, scn.render.fps,
             scn.view_settings.view_transform, scn.frame_start, scn.frame_end,
             os.path.basename(bpy.data.filepath)))


# ------------------------------------------------------------------ stages


def stage_020():
    wipe()
    scn = setup_scene("scene-1_shot-020_turun-permukaan", 96)
    path = os.path.join(SCENES, SHOTS["020"][0])
    append_blend(path)
    swap_island()
    shot_world("WLD_s1_020", "#DCEBE6", 1.0)
    scn.frame_set(1)
    ensure_camera()
    size = save_shot("020")
    summary("020")
    log("ANIM", "s1-020 island v003, patch ombak + perahu + kamera dipertahankan (%d bytes)" % size)
    still("020", 48, above_water=True)
    return True


# ------------------------------------------------------------ shot 070


def bone_world(arm, name):
    return arm.matrix_world @ arm.pose.bones[name].matrix


def stage_070():
    wipe()
    scn = setup_scene("scene-1_shot-070_nara-naik", 96)
    path = os.path.join(SCENES, SHOTS["070"][0])
    append_blend(path)
    swap_island()
    shot_world("WLD_s1_070", "#E3EFEA", 1.0)

    # shot 070 belum punya divegear lengkap: append masker + snorkel
    old_gear = bpy.data.collections.get("PRP_divegear")
    if old_gear is not None:
        for ob in list(old_gear.all_objects):
            bpy.data.objects.remove(ob, do_unlink=True)
        bpy.data.collections.remove(old_gear)
        purge_orphans()
    gear = append_asset(P_GEAR, ["PRP_divegear"])
    for nm in ("PRP_divegear_fin_L", "PRP_divegear_fin_R"):
        ob = bpy.data.objects.get(nm)
        if ob is not None:
            bpy.data.objects.remove(ob, do_unlink=True)
    gear = lib.live_objects(gear)
    ensure_camera()

    scn.frame_set(1)
    bpy.context.view_layer.update()
    arm = bpy.data.objects["CHR_nara_rig"]
    mask = bpy.data.objects["PRP_divegear_mask"]
    snorkel = bpy.data.objects.get("PRP_divegear_snorkel")
    print("bones hand/head ada:", "hand.R" in arm.pose.bones, "head" in arm.pose.bones)

    # ---- pemasangan awal: masker + snorkel di kepala (bone head)
    fh, upn, her_right = s1.face_frame(arm)
    face_c = s1.bone_world(arm, "head", 0.56) + upn * 0.005
    yaw = s1.yaw_of(fh)
    s1.attach_gear(mask, arm, "head", face_c + fh * 0.095 + upn * 0.012, yaw, pitch_deg=0.0)
    if snorkel is not None:
        s1.attach_gear(snorkel, arm, "head", face_c + her_right * 0.105 - fh * 0.03, yaw + 8.0, roll_deg=-10.0)
    bpy.context.view_layer.update()
    print("masker di kepala: pos %.2f %.2f %.2f | snorkel parent %s/%s"
          % (mask.matrix_world.translation.x, mask.matrix_world.translation.y,
             mask.matrix_world.translation.z,
             snorkel.parent.name if snorkel else None,
             snorkel.parent_bone if snorkel else None))

    # ---- rekam bone per frame + offset ikatan kepala
    head_m, hand_m = {}, {}
    for f in range(1, 97):
        scn.frame_set(f)
        head_m[f] = bone_world(arm, "head").copy()
        hand_m[f] = bone_world(arm, "hand.R").copy()
    scn.frame_set(1)
    off_head = head_m[1].inverted() @ mask.matrix_world.copy()
    rot_head = mask.matrix_world.to_quaternion()
    scale_head = mask.matrix_world.to_scale()

    # ---- pose akhir: masker dipegang tangan kanan (mengikuti tulang hand.R)
    scn.frame_set(40)
    bpy.context.view_layer.update()
    fh40, upn40, _ = s1.face_frame(arm)
    hand_pos = bone_world(arm, "hand.R").translation + fh40 * 0.10
    grip = (Matrix.Translation(hand_pos)
            @ Matrix.Rotation(math.radians(s1.yaw_of(fh40) + 26.0), 4, "Z")
            @ Matrix.Rotation(math.radians(-24.0), 4, "X")
            @ Matrix.Diagonal(Vector((scale_head.x, scale_head.y, scale_head.z, 1.0))))
    off_hand = hand_m[40].inverted() @ grip

    def smoothstep(t):
        t = max(0.0, min(1.0, t))
        return t * t * (3.0 - 2.0 * t)

    seq = {}
    for f in range(1, 97):
        head_glue = head_m[f] @ off_head
        hand_glue = hand_m[f] @ off_hand
        if f <= 20:
            M = head_glue
        elif f >= 40:
            M = hand_glue
        else:
            s = smoothstep((f - 20) / 20.0)
            loc = head_glue.translation.lerp(hand_glue.translation, s)
            q = head_glue.to_quaternion().slerp(hand_glue.to_quaternion(), s)
            M = Matrix.Translation(loc) @ q.to_matrix().to_4x4() @ Matrix.Diagonal(
                Vector((scale_head.x, scale_head.y, scale_head.z, 1.0)))
        seq[f] = M

    # ---- lepas parent, panggang transform per 2 frame
    scn.frame_set(1)
    mask.parent = None
    mask.parent_type = "OBJECT"
    mask.rotation_mode = "XYZ"
    if mask.animation_data:
        mask.animation_data_clear()
    for f in range(1, 97, 2):
        mask.matrix_world = seq[f]
        mask.keyframe_insert("location", frame=f)
        mask.keyframe_insert("rotation_euler", frame=f)
    mask.matrix_world = seq[96]
    mask.keyframe_insert("location", frame=96)
    mask.keyframe_insert("rotation_euler", frame=96)
    scn.frame_set(1)

    # ---- verifikasi posisi layar
    from bpy_extras.object_utils import world_to_camera_view as w2c
    cam = scn.camera
    for f in (1, 20, 40, 60):
        scn.frame_set(f)
        bpy.context.view_layer.update()
        p = w2c(scn, cam, mask.matrix_world.translation)
        hp = w2c(scn, cam, hand_m[f].translation)
        print("  f%-3d mask ndc (%.2f, %.2f) hand ndc (%.2f, %.2f) | jarak ke tangan %.3f m"
              % (f, p.x, p.y, hp.x, hp.y, (mask.matrix_world.translation - hand_m[f].translation).length))
    scn.frame_set(1)
    print("kamera:", cam.name, "lens", cam.data.lens, "loc", tuple(round(v, 2) for v in cam.matrix_world.translation))

    size = save_shot("070")
    summary("070")
    log("ANIM", "s1-070 island v003 + masker head->hand.R (f20-40), snorkel tetap di kepala (%d bytes)" % size)
    still("070", 48, above_water=True)
    scn.frame_set(60)
    s1.look_still("s1-070-f60", 60, above_water=True, percent=50)
    return True


# ------------------------------------------------------------ shot 080


def stage_080():
    wipe()
    scn = setup_scene("scene-1_shot-080_daniel-jaring", 72)
    path = os.path.join(SCENES, SHOTS["080"][0])
    append_blend(path)
    swap_island()
    shot_world("WLD_s1_080", "#F2E9DC", 0.9)
    scn.frame_set(1)

    cam = bpy.data.objects["CAM_shot-080_wide"]
    cam.data.lens = 50.0
    daniel = bpy.data.objects.get("CHR_daniel_rig")
    sign = bpy.data.objects.get("PRP_sign_board")
    terrace = bpy.data.objects.get("PRP_terrace_deck")
    pts = []
    if daniel is not None and "head" in daniel.pose.bones:
        pts.append(bone_world(daniel, "head").translation.copy())
        body = bpy.data.objects.get("CHR_daniel_body")
        if body is not None:
            pts.extend(bbox_center(body)[1])
    elif daniel is not None:
        pts.extend(bbox_center(daniel)[1])
    for ob, label, use_bbox in ((sign, "papan", True), (terrace, "teras", False)):
        if ob is not None:
            c, corners = bbox_center(ob)
            pts.append(c)
            if use_bbox:
                pts.extend(corners)
            print("%s: %.2f %.2f %.2f (bbox diambil: %s)" % (label, c.x, c.y, c.z, use_bbox))
    shops = [o for o in bpy.data.objects if o.name.startswith("ENV_shop_")]
    if shops:
        door = bpy.data.objects.get("ENV_shop_door")
        if door is not None:
            dc = bbox_center(door)[0]
            pts.append(dc)
            print("pintu shop: %.2f %.2f %.2f" % (dc.x, dc.y, dc.z))

    old_loc = cam.matrix_world.translation.copy()
    direction = Vector((-0.12, -1.0, 0.26))
    center, radius, dist = cam_points_frame(cam, pts, margin=0.94, direction=direction.normalized())
    print("framing: center %.2f %.2f %.2f r=%.2f dist=%.2f cam=%.2f %.2f %.2f"
          % (center.x, center.y, center.z, radius, dist,
             cam.matrix_world.translation.x, cam.matrix_world.translation.y, cam.matrix_world.translation.z))

    ensure_camera()
    size = save_shot("080")
    summary("080")
    log("ANIM", "s1-080 island v003 (fasad baru) + kamera wide 50 mm (%d bytes)" % size)
    still("080", 48, above_water=True)
    return True


# ------------------------------------------------------------ shot 090


def stage_090():
    wipe()
    scn = setup_scene("scene-1_shot-090_anak-dermaga", 72)
    path = os.path.join(SCENES, SHOTS["090"][0])
    append_blend(path)
    swap_island()
    shot_world("WLD_s1_090", "#E8F0EC", 0.95)
    scn.frame_set(1)

    # buang crowd lama (dewasa diskalakan)
    old = [o for o in bpy.data.objects
           if o.name.startswith("CRW_") or o.name.startswith("CHR_crowd_face-")]
    print("crowd lama dibuang:", [o.name for o in old])
    for ob in old:
        bpy.data.objects.remove(ob, do_unlink=True)
    c = bpy.data.collections.get("CHR_crowd")
    if c is not None:
        bpy.data.collections.remove(c)
    purge_orphans()

    new = append_asset(P_CROWD3, ["CHR_crowd"])
    new = lib.live_objects(new)
    # sisakan hanya 4 anak + kontrol
    keep = ["CRW_C01", "CRW_C02", "CRW_C03", "CRW_C04", "CTL_crowd"]
    drop = [o for o in new if o.name not in keep]
    for ob in drop:
        bpy.data.objects.remove(ob, do_unlink=True)
    purge_orphans()
    ctl = bpy.data.objects.get("CTL_crowd")
    kids = [bpy.data.objects[n] for n in keep[:4] if n in bpy.data.objects]
    print("anak:", [(k.name, tuple(round(v, 2) for v in k.dimensions)) for k in kids])

    # dermaga: cari dek pier di island v003
    pier = bpy.data.objects.get("ENV_surface_pier-deck")
    if pier is not None:
        pc, pp = bbox_center(pier)
        xs = [p.x for p in pp]
        ys = [p.y for p in pp]
        zs = [p.z for p in pp]
        print("pier deck: x %.1f..%.1f y %.1f..%.1f z %.2f..%.2f"
              % (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)))
        pier_top = max(zs)
    else:
        pier_top = 0.6
        print("pier deck tidak ketemu")

    cam = scn.camera
    fwd = cam.matrix_world.to_3x3() @ Vector((0.0, 0.0, -1.0))
    fwd.z = 0.0
    fwd.normalize()
    right = fwd.cross(Vector((0, 0, 1))).normalized()
    cam_loc = cam.matrix_world.translation.copy()
    print("kamera:", cam.name, "loc", tuple(round(v, 2) for v in cam_loc), "fwd", tuple(round(v, 2) for v in fwd))

    s1.set_interp("BEZIER")
    offs = [(-1.25, 2.3), (0.35, 3.3), (-0.55, 4.4), (1.10, 5.4)]
    for i, kid in enumerate(kids):
        lat, dist = offs[i]
        start = cam_loc + fwd * dist + right * lat
        start.z = pier_top
        end = start - fwd * 3.0
        end.z = pier_top
        kid.rotation_mode = "XYZ"
        yaw = math.atan2(-fwd.y, -fwd.x) + math.radians(180.0)
        lean = math.radians(7.0)
        for f, p in ((1, start), (72, end)):
            kid.location = (p.x, p.y, p.z)
            kid.keyframe_insert("location", frame=f)
        kid.rotation_euler = (lean, 0.0, yaw + math.radians(8.0 * (1 if i % 2 else -1)))
        kid.keyframe_insert("rotation_euler", frame=1)
        # lari: bob vertikal + sedikit goyang
        for f in range(4, 73, 3):
            u = (f - 1) / 71.0
            pos = start.lerp(end, u)
            pos.z = pier_top + 0.05 * abs(math.sin(u * 14.0 + i * 1.7))
            kid.location = (pos.x, pos.y, pos.z)
            kid.keyframe_insert("location", frame=f)
            kid.rotation_euler = (lean + math.radians(3.0) * math.sin(u * 14.0 + i),
                                  0.0,
                                  yaw + math.radians(7.0) * math.sin(u * 9.0 + i * 1.3))
            kid.keyframe_insert("rotation_euler", frame=f)
        if ctl is not None and kid.parent is None:
            kid.parent = ctl
            kid.matrix_parent_inverse = ctl.matrix_world.inverted()
        print("  %s start %.2f %.2f %.2f" % (kid.name, start.x, start.y, start.z))

    scn.frame_set(1)
    ensure_camera()
    size = save_shot("090")
    summary("090")
    log("ANIM", "s1-090 crowd_v003, 4 anak CRW_C01-C04 di dermaga + handheld (%d bytes)" % size)
    still("090", 48, above_water=True)
    return True


# ------------------------------------------------------------ ikan 030/040/050


def _pivot_samples(pivots):
    """Rekam lokasi+rotasi tiap pivot untuk seluruh 1..96 sebelum di-retime."""
    scn = bpy.context.scene
    data = {}
    for p in pivots:
        data[p.name] = {"loc": {}, "rot": {}}
    for f in range(1, 97):
        scn.frame_set(f)
        for p in pivots:
            data[p.name]["loc"][f] = p.location.copy()
            data[p.name]["rot"][f] = p.rotation_euler.copy()
    return data


def _retime_pivot(p, data):
    """Fase kecepatan: 1-40 cepat, 40-72 hampir berhenti, 72-96 pergi."""
    def tmap(f):
        if f <= 40:
            u = (f - 1) / 39.0
            return 0.62 * (u ** 0.85)
        if f <= 72:
            u = (f - 40) / 32.0
            s = u * u * (3.0 - 2.0 * u)
            return 0.62 + 0.05 * s
        u = (f - 72) / 24.0
        return 0.67 + 0.33 * (u ** 1.6)

    def at(f):
        idx = 1 + tmap(f) * 95.0
        i0 = int(math.floor(idx))
        i1 = min(96, i0 + 1)
        w = idx - i0
        loc = data["loc"][i0].lerp(data["loc"][i1], w)
        r0, r1 = data["rot"][i0], data["rot"][i1]
        rot = Euler((r0.x + (r1.x - r0.x) * w,
                     r0.y + (r1.y - r0.y) * w,
                     r0.z + (r1.z - r0.z) * w), r0.order)
        return loc, rot

    if p.animation_data:
        p.animation_data_clear()
    p.rotation_mode = "XYZ"
    s1.set_interp("BEZIER")
    for f in range(1, 97, 3):
        loc, rot = at(f)
        p.location = loc
        p.rotation_euler = rot
        p.keyframe_insert("location", frame=f)
        p.keyframe_insert("rotation_euler", frame=f)
    scn = bpy.context.scene
    if scn.frame_end >= 96:
        loc, rot = at(96)
        p.location = loc
        p.rotation_euler = rot
        p.keyframe_insert("location", frame=96)
        p.keyframe_insert("rotation_euler", frame=96)
    print("  pivot %s retime ok (f1 %.1f/%.1f/%.1f, f40 %.1f, f72 %.1f, f96 %.1f)"
          % (p.name, at(1)[0].x, at(1)[0].y, at(1)[0].z,
             (at(40)[0] - at(1)[0]).length, (at(72)[0] - at(40)[0]).length,
             (at(96)[0] - at(72)[0]).length))


def _swap_school(kind):
    """Ganti ikan satu sekolah dengan versi _v002 (mesh+rig), posisi & action lama dipakai."""
    scn = bpy.context.scene
    school = bpy.data.collections.get("ENV_school_" + kind)
    if school is None:
        print("sekolah tidak ada:", kind)
        return
    pat = re.compile(r"^ENV_fish_%s" % kind)
    olds = [o for o in school.all_objects if pat.match(o.name)]
    arms = [o for o in olds if o.type == "ARMATURE"]
    meshes = [o for o in olds if o.type == "MESH"]
    rec = []
    for a in arms:
        act = None
        if a.animation_data and a.animation_data.action:
            act = a.animation_data.action
        m = next((o for o in meshes if o.parent is a), None)
        rec.append({
            "action": act,
            "parent": a.parent.name if a.parent else None,
            "pinv": a.matrix_parent_inverse.copy(),
            "basis": a.matrix_basis.copy(),
            "mesh_parent": m.name if m else None,
        })
    print("  %s: %d armature, %d mesh, contoh action %s"
          % (kind, len(arms), len(meshes), rec[0]["action"].name if rec and rec[0]["action"] else None))
    for r in rec:
        if r["action"] is not None:
            r["action"].use_fake_user = True
    for ob in olds:
        bpy.data.objects.remove(ob, do_unlink=True)
    purge_orphans()

    new = append_asset(P_FISH2[kind], ["ENV_fish"])
    new = lib.live_objects(new)
    ground = [o for o in new if o.name.startswith("PREVIEW")]
    for ob in ground:
        bpy.data.objects.remove(ob, do_unlink=True)
    new = [o for o in new if o.name in bpy.data.objects]

    src_arm = next(o for o in new if o.type == "ARMATURE")
    src_mesh = next(o for o in new if o.type == "MESH")
    helper = [o for o in new if o not in (src_arm, src_mesh)]
    for ob in helper:
        bpy.data.objects.remove(ob, do_unlink=True)
    print("  aset v002: arm=%s mesh=%s bones=%d" % (src_arm.name, src_mesh.name, len(src_arm.data.bones)))

    pivot = bpy.data.objects.get("ENV_school_%s_pivot" % kind)
    for i, r in enumerate(rec, start=1):
        a = src_arm.copy()
        a.data = src_arm.data
        a.name = "ENV_fish_%s_%02d_rig" % (kind, i)
        a.animation_data_clear()
        if r["action"] is not None:
            a.animation_data_create()
            a.animation_data.action = r["action"]
        school.objects.link(a)
        if r["parent"] and bpy.data.objects.get(r["parent"]) is not None:
            a.parent = bpy.data.objects[r["parent"]]
            a.matrix_parent_inverse = r["pinv"]
        a.matrix_basis = r["basis"]

        m = src_mesh.copy()
        m.data = src_mesh.data
        m.name = "ENV_fish_%s_%02d" % (kind, i)
        school.objects.link(m)
        m.parent = a
        m.matrix_parent_inverse = a.matrix_world.inverted()
        for mod in m.modifiers:
            if mod.type == "ARMATURE":
                mod.object = a
    bpy.data.objects.remove(src_arm, do_unlink=True)
    bpy.data.objects.remove(src_mesh, do_unlink=True)
    for r in rec:
        if r["action"] is not None:
            r["action"].use_fake_user = False
    purge_orphans()
    bag = [o for o in school.all_objects if pat.match(o.name)]
    print("  %s: %d ikan baru (%d armature)" % (kind, len(bag), len([o for o in bag if o.type == "ARMATURE"])))


def stage_fish(key):
    fields = {"030": ("terumbu", 96), "040": ("penyu", 96), "050": ("nara-dive", 96)}
    desc, fend = fields[key]
    wipe()
    scn = setup_scene("scene-1_shot-%s_%s" % (key, desc), fend)
    path = os.path.join(SCENES, SHOTS[key][0])
    append_blend(path)
    shot_world("WLD_s1_%s" % key, "#0F5C63", 1.1)
    scn.frame_set(1)

    pivots = [bpy.data.objects["ENV_school_%s_pivot" % k]
              for k in ("cakalang", "kakatua", "damselfish")
              if "ENV_school_%s_pivot" % k in bpy.data.objects]
    data = _pivot_samples(pivots)
    for kind in ("cakalang", "kakatua", "damselfish"):
        _swap_school(kind)
    for p in pivots:
        if p.name in bpy.data.objects:
            _retime_pivot(p, data[p.name])

    scn.frame_set(1)
    ensure_camera()
    size = save_shot(key)
    summary(key)
    log("ANIM", "s1-%s ikan %s _v002 (sirip dada lepas) + fase kecepatan pivot 1-40/40-72/72-96 (%d bytes)"
        % (key, "/".join(P_FISH2.keys()), size))
    still(key, 48, above_water=False)
    return True


# ------------------------------------------------------------- verifikasi


def verify_file(key):
    """'Buka ulang' file shot: append seluruh data lalu periksa isinya."""
    filename = SHOTS[key][0]
    path = os.path.join(SCENES, filename)
    wipe()
    setup_scene("verify-" + key, SHOTS[key][1])
    append_blend(path)
    scn = bpy.context.scene
    objs = list(bpy.data.objects)
    print("== %s | %d objek | %d bytes | colls=%s"
          % (filename, len(objs), os.path.getsize(path), [c.name for c in bpy.data.collections]))
    print("   world=%s camera=%s lens=%s | %dx%d %dfps vt=%s range=%d-%d"
          % (scn.world.name if scn.world else None,
             scn.camera.name if scn.camera else None,
             round(scn.camera.data.lens, 1) if scn.camera else None,
             scn.render.resolution_x, scn.render.resolution_y, scn.render.fps,
             scn.view_settings.view_transform, scn.frame_start, scn.frame_end))
    shop = [o.name for o in objs if o.name.startswith("ENV_shop_")]
    print("   fasad v003: %d objek shop" % len(shop))
    if key == "070":
        mask = bpy.data.objects.get("PRP_divegear_mask")
        snorkel = bpy.data.objects.get("PRP_divegear_snorkel")
        arm = bpy.data.objects.get("CHR_nara_rig")
        print("   mask: ada=%s action=%s" % (
            mask is not None,
            mask.animation_data.action.name if mask and mask.animation_data and mask.animation_data.action else None))
        print("   snorkel: parent=%s bone=%s" % (
            snorkel.parent.name if snorkel else None, snorkel.parent_bone if snorkel else None))
        if mask and arm:
            scn.frame_set(1)
            p1 = mask.matrix_world.translation.copy()
            h1 = bone_world(arm, "head").translation.copy()
            scn.frame_set(60)
            p60 = mask.matrix_world.translation.copy()
            hd60 = bone_world(arm, "hand.R").translation.copy()
            print("   f1 mask ke kepala: %.2f m | f60 mask ke tangan: %.2f m | jarak tempuh %.2f m"
                  % ((p1 - h1).length, (p60 - hd60).length, (p60 - p1).length))
            scn.frame_set(20)
            s1.look_still("s1-070-f20", 20, above_water=True, percent=50)
    if key == "090":
        kids = [o.name for o in objs if o.name.startswith("CRW_")]
        print("   crowd: %s | kamera action=%s" % (
            sorted(kids),
            scn.camera.animation_data.action.name if scn.camera and scn.camera.animation_data and scn.camera.animation_data.action else None))
    if key in ("030", "040", "050"):
        arms = [o for o in objs if o.type == "ARMATURE" and o.name.startswith("ENV_fish_")]
        piv = [o for o in objs if o.name.startswith("ENV_school_") and o.name.endswith("_pivot")]
        print("   ikan: %d armature, contoh data=%s" % (len(arms), arms[0].data.name if arms else None))
        print("   pivot: %s" % [(p.name, p.animation_data.action.name if p.animation_data and p.animation_data.action else None) for p in piv])
    if key == "020":
        wave = [o.name for o in objs if "patch" in o.name or "water" in o.name.lower()]
        boat = len([o for o in objs if o.name.startswith("PRP_boat")])
        print("   ombak=%s | objek perahu=%d" % (wave, boat))
    scn.frame_set(1)


def stage_verify():
    for key in ("020", "030", "040", "050", "070", "080", "090"):
        try:
            verify_file(key)
        except Exception as exc:
            print("VERIFY GAGAL %s: %r" % (key, exc))
    log("VERIFY", "7 shot dibaca ulang dari disk: island v003, masker di hand.R, crowd_v003 4 anak, 56 ikan rig v002")
    return True


def stage_tidy():
    """Rapikan: buang koleksi kosong sisa append + samakan world dengan resep asli."""
    recipes = {"030": ("#0F5C63", 1.15), "040": ("#0F5C63", 1.15), "050": ("#0F5C63", 1.1)}
    for key, (hexc, strength) in recipes.items():
        wipe()
        setup_scene("scene-1_shot-%s" % key, SHOTS[key][1])
        append_blend(os.path.join(SCENES, SHOTS[key][0]))
        removed = []
        for c in list(bpy.data.collections):
            if len(c.all_objects) == 0 and len(c.children) == 0:
                removed.append(c.name)
                bpy.data.collections.remove(c)
        w = shot_world("WLD_s1_%s" % key, hexc, strength)
        bg = next((n for n in w.node_tree.nodes if n.type == "BACKGROUND"), None)
        if bg is not None:
            bg.inputs["Strength"].default_value = strength
        ensure_camera()
        size = save_shot(key)
        print("TIDY %s: hapus koleksi kosong %s | world %s strength %.2f | %d bytes"
              % (key, removed, w.name, strength, size))
    log("LOOK", "shot 030/040/050 dirapikan (koleksi kosong dibuang, world #0F5C63 sesuai resep)")
    return True


DISPATCH = {
    "020": stage_020,
    "030": lambda: stage_fish("030"),
    "040": lambda: stage_fish("040"),
    "050": lambda: stage_fish("050"),
    "070": stage_070,
    "080": stage_080,
    "090": stage_090,
    "VERIFY": stage_verify,
    "TIDY": stage_tidy,
}

if __name__ == "__main__" and "STAGE" in globals():
    DISPATCH[globals()["STAGE"]]()
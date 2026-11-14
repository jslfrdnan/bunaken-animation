# assets/look — Look Dev & Shading

Pemilik: **Vaughn Toy** (Anggota 7 — Lighting & Shading)

## Isi

| File | Isi |
|---|---|
| `scene-1-look.blend` | World, shader air/pasir/karang/batu, panggung uji, dan plate shot 030 di atas terumbu asli (v002, 2 Nov 2026) |
| `scene-1-look_v002.blend` | **Look produksi Scene 1 (sebelumnya)** — `WLD_scene-1` (bawah laut, golden hour) + `WLD_scene-1_surface` (permukaan) + `SHD_water-surface` (14 Nov 2026) |
| `scene-1-look_v003.blend` | **Look produksi Scene 1 (aktif)** — world sama dengan v002 + `SHD_water-surface_v002` (air bergelombang, dua skala noise 4D, 14 Nov 2026 malam) dan panggung uji air 200 × 200 m |
| `scene-2-look.blend` | **Look Scene 2** — `WLD_scene-2` subuh biru (14 Nov 2026) |
| `scene-3-look.blend` | **Look Scene 3** — `WLD_scene-3` sore hangat + sun rig `LGT_look_scene-3_sun` (14 Nov 2026) |
| `scene-4-look.blend` | **Look Scene 4** — `WLD_scene-4` pagi cerah (14 Nov 2026) |

## Look dev per scene (14 Nov 2026)

Empat file look di atas adalah **sumber world + shader air per scene**. Renderer
memakainya lewat `scripts/look.py`:

```python
import sys; sys.path.append("<repo>/scripts")
from look import apply_look
apply_look(scn, 1)      # scn = scene dari file shot
```

`apply_look` hanya menyentuh empat hal: `scn.world`, material objek air
(`SHD_water-surface_v002`), modifier `Displace` gelombang (objek air < 10.000
vert; lihat bagian Displace di bawah), dan
`scn.view_settings.view_transform = "Standard"`. File shot tidak disimpan dan
tidak ada lampu yang ditambahkan.

| Scene | World | Strength | Catatan |
|---|---|---|---|
| 1 | `WLD_scene-1` | 0,55 | bawah laut, teal dalam → teal laut + jendela hangat di atas |
| 1 | `WLD_scene-1_surface` | 1,00 | di atas air (kamera z > 0,5 m): langit golden hour krem–pasir |
| 2 | `WLD_scene-2` | 0,70 | subuh biru `#0F5C63`, glow tipis di horizon = kabut |
| 3 | `WLD_scene-3` | 0,35 | sore hangat, oranye hanya pita horizon; sun 4,0 / 78° tersimpan di `LGT_look_scene-3_sun` |
| 4 | `WLD_scene-4` | 1,30 | pagi cerah, ambient tinggi |

### World: kenapa gradient, bukan volume

Tambahan `Volume` di world **tidak dipakai**: di EEVEE 5.2 world volume membuat
frame hitam total (diuji pada shot 030). God rays tetap datang dari kartu
`FX_godray_*` milik shot. Gradient dibuat dengan:

```
Geometry → Incoming → Separate XYZ (Z) → Map Range (-1..1 → 0..1) → Color Ramp → Background
```

Posisi **0,5 di ramp = horizon**, jadi warna langit/permukaan diatur di sekitar
angka itu. Ini juga perbaikan bug lama: `WLD_scene-1_underwater` di
`scene-1-look.blend` memakai `Texture Coordinate → Generated` yang konstan di
world space → air terlihat datar.

### `SHD_water-surface` (v002, lama)

Principled: base `#1FA3A3` (linear 0,0137/0,3663/0,3663), metallic 0,
**roughness 0,18**, IOR 1,333. Normal dari dua Bump berantai: Wave (bands,
scale 22, distortion 6) → Bump 0,18, lalu Noise (scale 16, detail 5) → Bump
**0,25**. Koordinat `Object`, tanpa tekstur gambar. Nama lama
`SHD_water_surface` (garis bawah) tetap ada supaya file shot lama tidak putus.

### `SHD_water-surface_v002` (v003, aktif)

`scene-1-look_v003.blend`. `SHD_water-surface` dibangun ulang dengan isi sama
(kembaran/alias) supaya file shot lama tidak kehilangan shader.

| Node | Nilai |
|---|---|
| Principled Base Color | `#1FA3A3` (linear 0,0137 / 0,3663 / 0,3663) |
| Metallic / Roughness / IOR | 0 / **0,12** / 1,333 |
| Specular IOR Level | 0,65 ("sedikit tinggi") |
| Texture Coordinate | `Object` → **Mapping 1/160** (0,00625) |
| `Noise_swell` | 4D, scale **6**, detail **6**, roughness 0,55, distortion 0,3 |
| `Bump_swell` | strength **0,35**, distance **70** → normal |
| `Noise_ripple` | 4D, scale **40**, detail **4**, roughness 0,5, distortion 0 |
| `Bump_ripple` | strength **0,15**, distance **6**, Normal ← `Bump_swell` (dijumlahkan) |
| `Map_trough` + `Mix_trough` | swell 0,62…0,40 → 0…0,5, mix base → teal dalam `#0F5C63` |
| Animasi | `W` kedua Noise 4D: keyframe **frame 1 = 0,0**, **frame 840 = 1,0**, interpolasi linear |

**Kenapa ada Mapping 1/160.** Koordinat `Object` satuannya meter. Bidang air
Scene 1 berukuran sampai 200 km, jadi noise scale 6/40 pada koordinat mentah
jatuh di frekuensi sub-milimeter → normal saling meniadakan dan air terbaca
sebagai bidang warna rata (masalah v002). Dengan Mapping 1/160, noise scale 6 =
**swell ±27 m** dan scale 40 = **ripple ±4 m**, dua-duanya terbaca: dari kamera
120 m pola gelombang tampak, dari kamera 2 m profil riak tampak. `Distance`
Bump adalah skala turunan tinggi (meter) — itulah tombol untuk mengatur
ketebalan relief tanpa mengubah strength yang disepakati.

**Panggung uji.** `ENV_wtest_water-200m` (grid 64×64, 4225 vert, 200 × 200 m),
`CAM_wtest_aerial-120m`, `CAM_wtest_close-2m`, `LGT_wtest_sun`. Ini panggung uji,
bukan aset: **jangan di-link ke `scenes/`**. Hasil uji:
`renders/stills/water-v003-aerial.png`, `water-v003-close.png`, dan
`water-v003-aerial-f420.png` (bukti animasi: pola di frame 420 berbeda).

### Displace gelombang di `scripts/look.py`

`apply_look` menambahkan modifier `Displace` (nama `FX_water_wave-displace`,
tekstur Clouds `FX_water_wave-clouds`, size **25**, strength **0,12 m**) ke objek
air dengan **< 10.000 vert**. Objek lebih besar dilewati dan dicatat ke
`renders/logs/production.log`. Catatan penting: bidang laut di file shot saat ini
(`ENV_detail_sea-surface`, `ENV_surface_water-placeholder`) hanya **4 vert**, jadi
modifier itu belum menghasilkan profil apa pun — gelombang di shot datang dari
normal shader. Profil geometri baru terlihat kalau mesh airnya dibagi (subdivide)
oleh pemilik shot.

### Jebakan yang sudah menimpa sesi ini

1. **`FX_water_volume` bukan permukaan air.** Nama memuat "water", tetapi itu
   kubus kabut `SHD_water_volume`. Kalau diganti `SHD_water-surface`, kamera
   berada di dalam kubus opak → seluruh frame hitam. `look.py` melewati objek
   dengan token `volume`/`fog`.
2. **`PRP_boat_cadik_seam-4` memuat huruf "sea".** Pencocokan harus per token
   (`seam` ≠ `sea`), bukan substring; kalau tidak, garis papan perahu ikut
   berubah jadi air.
3. **Jangan `save_as_mainfile` menimpa file look yang sedang di-append.**
   Blender menolak ("Cannot overwrite used library"). Simpan ke
   `renders/tmp/`, lalu pindahkan.

## Kenapa file ini penting untuk semua orang

`scene-1-look.blend` adalah **sumber setting render**. Sebelum mulai kerja,
salin dari file ini:

```
Engine            EEVEE Next
Resolusi          1920 x 1080, 24 fps
Color Management  view transform Standard (BUKAN AgX)
                  look None, exposure 0, gamma 1
```

Kalau setting ini beda, warna antar-artist akan beda dan palette di
`PROJECT.md` §2 tidak lagi berlaku.

## Cara memakai material

Material di file ini ber-fake-user, jadi aman di-*append* ke file departemen:

1. Buka file departemenmu (mis. `assets/env/reef.blend`).
2. `File → Append…` → `assets/look/scene-1-look.blend` → **Material**.
3. Pilih `SHD_coral_live`, `SHD_sand`, dst.

| Material | Untuk |
|---|---|
| `SHD_water_surface` | permukaan air, hanya shot di atas/permukaan (020, 070) |
| `SHD_water_volume` | kabut air bawah laut (dipakai kubus `FX_water_volume`) |
| `SHD_sand` | pasir dasar |
| `SHD_coral_live` | karang hidup (hijau terumbu) |
| `SHD_coral_accent` | karang oranye — **aksen saja**, sedikit per frame |
| `SHD_rock` | batu |
| `FX_godray_shaft` | kartu berkas cahaya (lihat catatan di bawah) |

World: `WLD_scene-1_underwater` (shot 030–060) dan `WLD_scene-1_surface`
(shot 010, 020, 070–100).

## Rujukan

Semua acuan kerja tim sekarang ada di `PROJECT.md`, bukan lagi di vault Obsidian
(vault sudah dikeluarkan dari repo):

| Butuh | Lihat |
|---|---|
| Palette, aturan cahaya per scene, larangan gaya | `PROJECT.md` §2 |
| Resolusi, fps, engine, Color Management | `PROJECT.md` §3 |
| Daftar aset look & pemiliknya | `PROJECT.md` §5 |
| Aturan link/append, pack tekstur | `PROJECT.md` §8 |
| Peran 7 & jalur kritis | `PROJECT.md` §9 |

## Yang perlu diketahui sebelum mengutak-atik

1. **Panggung uji bukan aset.** Objek `ENV_*`, `FX_*`, `LGT_*`, `CAM_*` di file
   ini hanya untuk menilai warna dan cahaya. Jangan di-*link* ke
   `scenes/scene-1.blend`.
2. **God rays dibuat dua lapis**: pelat gobo (`FX_sun_shaft_gobo`) untuk pola
   cahaya di pasir, plus kartu cahaya (`FX_godray_00…05`) untuk berkasnya.
   EEVEE 5.2 belum bisa menghasilkan berkas volumetric tajam dari gobo, jadi
   kartu ini disengaja. Kuat-lemahnya diatur di `FX_godray_shaft` →
   Emission Strength. Kalau dirasa murahan di animatic, sembunyikan saja
   objek `FX_godray_*` — pola di pasir tetap ada.
3. **`FX_sun_shaft_gobo` wajib `visible_camera = False`.** Pelat itu tidak punya
   material, jadi kalau terlihat kamera ia ikut ter-render sebagai bidang
   abu-abu raksasa dan merusak frame. Bayangannya tetap bekerja selama
   `visible_shadow = True`.
4. **Skala kartu cahaya jangan lebih dari ~0,6 di sumbu X.** Geometrinya 2–5 m
   lebar; skala 2,0 membuat "berkas" jadi dinding cahaya 10 m. Pakai
   (0,45–0,55 / 1,0 / 1,7) dan `z = -1,7` supaya ujung bawahnya tertutup pasir.
5. **Jangan naikkan angka ini tanpa render uji**: sun **3,8**, fill 110 W,
   volume 0,035. Di terumbu asli, sun 4,6 sudah membuat pasir terbakar putih di
   area berkas (4,6 masih pas untuk panggung primitif v001). Sun di atas ~5 dan
   volume di atas ~0,06 merusak frame.
6. **`Sky Texture` tidak dipakai** untuk world permukaan: dengan view transform
   Standard hasilnya clipping total (putih). Diganti gradient manual agar warna
   tetap sesuai palette. Catat kalau lead mau HDRI sungguhan — perlu file HDRI
   di `assets/textures/` dan pengujian ulang.
7. **Karang duplikat berbagi mesh data.** Mengganti material lewat
   `ob.data.materials` mengubah *semua* duplikat sekaligus (pernah terjadi dan
   membuat 28 karang jadi oranye). Untuk variasi per objek pakai
   `ob.material_slots[0].link = 'OBJECT'`.
8. **Jangan timpa `ob.scale` objek hasil append.** Simpan skala aslinya; objek
   blockout punya skala non-seragam (penyu = 0,48 / 0,40 / 0,15). Menggantinya
   dengan 1,1 membuat penyu jadi bola 2,2 m.
9. **Memindahkan objek yang punya anak akan menggeser anaknya dua kali.**
   `matrix_parent_inverse` menyimpan posisi induk saat di-parent. Kalau induk
   digeser 5,54 m lalu anaknya juga ikut digeser manual, sirip ekor ikan turun
   11 m dan hilang dari frame (pernah terjadi: semua ikan tampak tanpa ekor).
   Setelah memindahkan induk, cukup `anak.matrix_parent_inverse.identity()`
   dan `anak.location = (0,0,0)` — jangan ikut menggeser anak.

## Plate shot 030 (v002)

Plate ini memakai **terumbu asli** dari `assets/env/reef.blend`, bukan panggung
primitif.

```
Append       assets/env/reef.blend → Collection ENV_reef
Turunkan     semua objek root z -= 5.54 (dasar terumbu duduk di pasir z = -6)
Kamera       CAM_lookdev_reef, 26 mm, (-2.0, -6.4, -4.20)
             target (-0.25, 0.80, -5.55)
Material     karang bercabang & meja → SHD_coral_live
             batu                     → SHD_rock
             ikan & penyu             → material asli pemiliknya (tidak diubah)
Pengisi      26 karang bercabang disusun jadi 3 gugusan (pengisi frame,
             bukan aset produksi)
Penyu        hide_render = True (subjeknya shot 040, bukan 030)
```

Render: EEVEE Next, 1920×1080, 64 sampel, ±7 detik. Hasil di
`renders/stills/scene-1-shot-030_lookdev.png` (tidak masuk git).

Catatan untuk Anggota 3 (`reef.blend`): warna material ikan sudah saya ukur —
`MAT_fish_kakatua` `#3E8E6E` (persis hijau terumbu, aman), `MAT_fish_cakalang`
`#4A6E96`, `MAT_fish_hiu` `#6E7B80`, tetapi `MAT_fish_goropa-merah` `#C0392B`
merah menyala, bukan oranye karang `#E4713C`. Merah jenuh juga yang pertama
hilang di bawah air, jadi secara fisik kurang masuk akal.

Model ikannya sendiri **lengkap** — badan, ekor, dan sirip punggung sebagai
objek terpisah yang di-parent ke badan. Sempat terlihat "tanpa ekor" di plate
karena kesalahan saya, bukan karena modelnya (lihat poin 9 di atas).

## Pratinjau

- `renders/stills/scene-1-shot-030_lookdev.png` — plate shot 030 di atas terumbu
  asli (1920×1080). Tidak masuk git.

## Belum selesai

- [x] Karang di file ini sudah diganti blockout asli `assets/env/reef.blend`
      dan diuji di shot 030 (v002).
- [ ] Uji 2 shot bawah laut lainnya: 050 (Nara muncul dari balik karang) dan
      040 (penyu). Butuh rig Nara dari peran 6.
- [ ] `ENV_surface_water-placeholder` di `assets/env/surface.blend` masih bidang
      air datar. Shader air aslinya `SHD_water_surface` dari file ini; perlu
      koordinasi dengan pemilik `surface.blend` (Jasiel) sebelum diganti.
- [ ] Shader permukaan air dilihat dari bawah (shot 020 turun ke air) belum final.
- [ ] Partikel/debris kecil di air (diminta shot 030–060) belum dibuat.
- [ ] Look dev permukaan (shot 010, 080, 090) di atas `surface.blend` +
      `boats.blend` dengan `WLD_scene-1_surface` belum dikerjakan.

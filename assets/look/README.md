# assets/look â€” Look Dev & Shading

Pemilik: **Vaughn Toy** (Anggota 7 â€” Lighting & Shading)

## Isi

| File | Isi |
|---|---|
| `scene-1-look.blend` | World, shader air/pasir/karang/batu, panggung uji, plate shot 030 di atas terumbu asli (v002), dan dunia permukaan: pulau + kampung + dermaga + perahu dengan terumbu di ujung dermaga (v003, 3 Nov 2026) |
| `scene-1-look_v002.blend` | **Look produksi Scene 1 (sebelumnya)** â€” `WLD_scene-1` (bawah laut, golden hour) + `WLD_scene-1_surface` (permukaan) + `SHD_water-surface` (14 Nov 2026) |
| `scene-1-look_v003.blend` | **Look produksi Scene 1 (sebelumnya)** â€” world sama dengan v002 + `SHD_water-surface_v002` (air bergelombang, dua skala noise 4D, 14 Nov 2026 malam) dan panggung uji air 200 Ã— 200 m |
| `scene-1-look_v004.blend` | **Look produksi Scene 1 (aktif, 27 Nov 2026)** â€” air anti-moirÃ© (`SHD_water-surface_v002`: bump ripple 0,07, mapping 1/220, roughness 0,16), material dasar laut `SHD_seabed_caustics`, koleksi `FX_atmosphere` (3 god ray card, 200 partikel, 2 fog card), dan kabut kedalaman compositor |
| `scene-2-look.blend` | **Look Scene 2** â€” `WLD_scene-2` subuh biru (14 Nov 2026) |
| `scene-3-look.blend` | **Look Scene 3** â€” `WLD_scene-3` sore hangat + sun rig `LGT_look_scene-3_sun` (14 Nov 2026) |
| `scene-4-look.blend` | **Look Scene 4** â€” `WLD_scene-4` pagi cerah (14 Nov 2026) |

## Look dev per scene (14 Nov 2026)

Empat file look di atas adalah **sumber world + shader air per scene**. Renderer
memakainya lewat `scripts/look.py`:

```python
import sys; sys.path.append("<repo>/scripts")
from look import apply_look
apply_look(scn, 1)      # scn = scene dari file shot
```

`apply_look` menyentuh tujuh hal: `scn.world`, material objek air
(`SHD_water-surface_v002`), modifier `Displace` gelombang (objek air < 10.000
vert; lihat bagian Displace di bawah), `view_transform = "Standard"`, material
dasar laut (`SHD_seabed_caustics` pada objek `seabed`/`sand` di bawah air),
koleksi `FX_atmosphere` (di-append sekali, idempoten), dan kabut compositor
(mist pass â†’ Mix `#0F5C63`). File shot tidak disimpan dan tidak ada lampu yang
ditambahkan. Scene 2â€“4 belum punya koleksi FX, jadi `fx_collection` bernilai
`None` di sana (hanya kabut yang aktif).

| Scene | World | Strength | Catatan |
|---|---|---|---|
| 1 | `WLD_scene-1` | 0,55 | bawah laut, teal dalam â†’ teal laut + jendela hangat di atas |
| 1 | `WLD_scene-1_surface` | 1,00 | di atas air (kamera z > 0,5 m): langit golden hour kremâ€“pasir |
| 2 | `WLD_scene-2` | 0,70 | subuh biru `#0F5C63`, glow tipis di horizon = kabut |
| 3 | `WLD_scene-3` | 0,35 | sore hangat, oranye hanya pita horizon; sun 4,0 / 78Â° tersimpan di `LGT_look_scene-3_sun` |
| 4 | `WLD_scene-4` | 1,30 | pagi cerah, ambient tinggi |

### World: kenapa gradient, bukan volume

Tambahan `Volume` di world **tidak dipakai**: di EEVEE 5.2 world volume membuat
frame hitam total (diuji pada shot 030). God rays tetap datang dari kartu
`FX_godray_*` milik shot. Gradient dibuat dengan:

```
Geometry â†’ Incoming â†’ Separate XYZ (Z) â†’ Map Range (-1..1 â†’ 0..1) â†’ Color Ramp â†’ Background
```

Posisi **0,5 di ramp = horizon**, jadi warna langit/permukaan diatur di sekitar
angka itu. Ini juga perbaikan bug lama: `WLD_scene-1_underwater` di
`scene-1-look.blend` memakai `Texture Coordinate â†’ Generated` yang konstan di
world space â†’ air terlihat datar.

### `SHD_water-surface` (v002, lama)

Principled: base `#1FA3A3` (linear 0,0137/0,3663/0,3663), metallic 0,
**roughness 0,18**, IOR 1,333. Normal dari dua Bump berantai: Wave (bands,
scale 22, distortion 6) â†’ Bump 0,18, lalu Noise (scale 16, detail 5) â†’ Bump
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
| Texture Coordinate | `Object` â†’ **Mapping 1/160** (0,00625) |
| `Noise_swell` | 4D, scale **6**, detail **6**, roughness 0,55, distortion 0,3 |
| `Bump_swell` | strength **0,35**, distance **70** â†’ normal |
| `Noise_ripple` | 4D, scale **40**, detail **4**, roughness 0,5, distortion 0 |
| `Bump_ripple` | strength **0,15**, distance **6**, Normal â† `Bump_swell` (dijumlahkan) |
| `Map_trough` + `Mix_trough` | swell 0,62â€¦0,40 â†’ 0â€¦0,5, mix base â†’ teal dalam `#0F5C63` |
| Animasi | `W` kedua Noise 4D: keyframe **frame 1 = 0,0**, **frame 840 = 1,0**, interpolasi linear |

**Kenapa ada Mapping 1/160.** Koordinat `Object` satuannya meter. Bidang air
Scene 1 berukuran sampai 200 km, jadi noise scale 6/40 pada koordinat mentah
jatuh di frekuensi sub-milimeter â†’ normal saling meniadakan dan air terbaca
sebagai bidang warna rata (masalah v002). Dengan Mapping 1/160, noise scale 6 =
**swell Â±27 m** dan scale 40 = **ripple Â±4 m**, dua-duanya terbaca: dari kamera
120 m pola gelombang tampak, dari kamera 2 m profil riak tampak. `Distance`
Bump adalah skala turunan tinggi (meter) â€” itulah tombol untuk mengatur
ketebalan relief tanpa mengubah strength yang disepakati.

**Panggung uji.** `ENV_wtest_water-200m` (grid 64Ã—64, 4225 vert, 200 Ã— 200 m),
`CAM_wtest_aerial-120m`, `CAM_wtest_close-2m`, `LGT_wtest_sun`. Ini panggung uji,
bukan aset: **jangan di-link ke `scenes/`**. Hasil uji:
`renders/stills/water-v003-aerial.png`, `water-v003-close.png`, dan
`water-v003-aerial-f420.png` (bukti animasi: pola di frame 420 berbeda).

### `scene-1-look_v004.blend` (27 Nov 2026) — anti-moirÃ© + atmosfer

Perbaikan **air dekat kamera bergaris/moirÃ©** (shot 020 & 070) dan penambahan
atmosfer bawah laut untuk shot 030â€“060. Semua nilai ada di file v004; v003
tidak diubah.

| Bagian | Nilai |
|---|---|
| `SHD_water-surface_v002` + `SHD_water-surface` | Mapping **1/220** (0,004545), `Bump_ripple` strength **0,07** (Distance 6, Filter Width **0,5** px), Roughness **0,16**, `Bump_swell` tetap 0,35 / Filter Width 0,6 |
| Base color air | tetap `#1FA3A3` (0,0137 / 0,3663 / 0,3663) lewat `Mix_trough` |
| `SHD_seabed_caustics` | pasir `#E8D5B0` + pola caustic: Voronoi (Distance to Edge, scale 6) + Wave (bands diagonal, scale 7, distortion 12), mix **ADD 0,55**, additive cream `#F2E9DC` **0,18**; lembah pola dikali 0,45 supaya tetap terbaca di bawah sinar kuat. Bump pasir sama dengan `SHD_sand` |
| `FX_godray_card_01..03` | cone emissive 12 m, lebar 3,2 / 2,2 / 2,0 m, warna `#F2E9DC`, emission **0,6**, alpha 0,55 dengan tepi siluet dihaluskan (`Layer Weight > Facing`) dan ujung memudar (`Ramp_fade`) |
| `FX_particles` | satu mesh, **200 bola** r 1â€“2 cm di volume 20 Ã— 20 Ã— 8 m, emission 0,35 |
| `FX_fog_card_01/02` | bidang 34 Ã— 16 m dan 44 Ã— 22 m, alpha **0,08**, warna `#0F5C63`, memakai emission (tint murni) supaya tidak ikut menjadi terang oleh sun |
| Induk | `FX_atmosphere_root` (Empty); `apply_look` memindahkannya ke depan kamera: 17 m (bawah laut) atau di bawah permukaan (kamera di atas air) |

Di dalam file look, `FX_atmosphere_root` duduk di origin (0, 0, 0) â€” itu posisi
default, bukan posisi final. Posisi per shot dihitung `apply_look`, jadi jangan
menilai atmosfer dengan merender file look apa adanya. Shot di atas air (020,
070) menaruh seluruh grup di bawah permukaan (root z = -12,5 m) sehingga
tertutup bidang air dan tidak mengganggu bingkai.

**Kenapa tidak ada node Blur normal.** Blender 5.2 tidak punya node `Blur` di
node tree shader (hanya di compositor), jadi filter normal 0,35â€“0,5 px diterapkan
lewat input **Filter Width** milik node `Bump` â€” input itu memang lebar filter
(dalam piksel) untuk turunan height. Hasilnya: tidak ada lagi garis periodik di
air dekat kamera (uji crop 100% shot 020).

**Kabut** tidak memakai World Volume (masih menghasilkan frame hitam di EEVEE
5.2). `apply_look` menyalakan `mist_settings` (start 2, depth 45, QUADRATIC) +
pass **Mist** (EEVEE 5.2 ternyata mengisi pass ini) lalu compositor
`Mist â†’ Multiply 0,42 â†’ Mix ke #0F5C63`. Faktor 0,42 bawah laut, 0,25 di atas air.
Compositor 5.2 memakai `scene.compositing_node_group` (tipe `CompositorNodeTree`,
output `NodeGroupOutput`) â€” bukan lagi `CompositorNodeComposite`.

### Displace gelombang di `scripts/look.py`

`apply_look` menambahkan modifier `Displace` (nama `FX_water_wave-displace`,
tekstur Clouds `FX_water_wave-clouds`, size **25**, strength **0,12 m**) ke objek
air dengan **< 10.000 vert**. Objek lebih besar dilewati dan dicatat ke
`renders/logs/production.log`. Catatan penting: bidang laut di file shot saat ini
(`ENV_detail_sea-surface`, `ENV_surface_water-placeholder`) hanya **4 vert**, jadi
modifier itu belum menghasilkan profil apa pun â€” gelombang di shot datang dari
normal shader. Profil geometri baru terlihat kalau mesh airnya dibagi (subdivide)
oleh pemilik shot.

### Jebakan yang sudah menimpa sesi ini

1. **`FX_water_volume` bukan permukaan air.** Nama memuat "water", tetapi itu
   kubus kabut `SHD_water_volume`. Kalau diganti `SHD_water-surface`, kamera
   berada di dalam kubus opak â†’ seluruh frame hitam. `look.py` melewati objek
   dengan token `volume`/`fog`.
2. **`PRP_boat_cadik_seam-4` memuat huruf "sea".** Pencocokan harus per token
   (`seam` â‰  `sea`), bukan substring; kalau tidak, garis papan perahu ikut
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
`PROJECT.md` Â§2 tidak lagi berlaku.

## Cara memakai material

Material di file ini ber-fake-user, jadi aman di-*append* ke file departemen:

1. Buka file departemenmu (mis. `assets/env/reef.blend`).
2. `File â†’ Appendâ€¦` â†’ `assets/look/scene-1-look.blend` â†’ **Material**.
3. Pilih `SHD_coral_live`, `SHD_sand`, dst.

| Material | Untuk |
|---|---|
| `SHD_water_surface` | permukaan air, hanya shot di atas/permukaan (020, 070) |
| `SHD_water_volume` | kabut air bawah laut (dipakai kubus `FX_water_volume`) |
| `SHD_sand` | pasir dasar |
| `SHD_coral_live` | karang hidup (hijau terumbu) |
| `SHD_coral_accent` | karang oranye â€” **aksen saja**, sedikit per frame |
| `SHD_rock` | batu |
| `FX_godray_shaft` | kartu berkas cahaya (lihat catatan di bawah) |

World: `WLD_scene-1_underwater` (shot 030â€“060) dan `WLD_scene-1_surface`
(shot 010, 020, 070â€“100).

## Rujukan

Semua acuan kerja tim sekarang ada di `PROJECT.md`, bukan lagi di vault Obsidian
(vault sudah dikeluarkan dari repo):

| Butuh | Lihat |
|---|---|
| Palette, aturan cahaya per scene, larangan gaya | `PROJECT.md` Â§2 |
| Resolusi, fps, engine, Color Management | `PROJECT.md` Â§3 |
| Daftar aset look & pemiliknya | `PROJECT.md` Â§5 |
| Aturan link/append, pack tekstur | `PROJECT.md` Â§8 |
| Peran 7 & jalur kritis | `PROJECT.md` Â§9 |

## Yang perlu diketahui sebelum mengutak-atik

1. **Panggung uji bukan aset.** Objek `ENV_*`, `FX_*`, `LGT_*`, `CAM_*` di file
   ini hanya untuk menilai warna dan cahaya. Jangan di-*link* ke
   `scenes/scene-1.blend`.
2. **God rays dibuat dua lapis**: pelat gobo (`FX_sun_shaft_gobo`) untuk pola
   cahaya di pasir, plus kartu cahaya (`FX_godray_00â€¦05`) untuk berkasnya.
   EEVEE 5.2 belum bisa menghasilkan berkas volumetric tajam dari gobo, jadi
   kartu ini disengaja. Kuat-lemahnya diatur di `FX_godray_shaft` â†’
   Emission Strength. Kalau dirasa murahan di animatic, sembunyikan saja
   objek `FX_godray_*` â€” pola di pasir tetap ada.
3. **`FX_sun_shaft_gobo` wajib `visible_camera = False`.** Pelat itu tidak punya
   material, jadi kalau terlihat kamera ia ikut ter-render sebagai bidang
   abu-abu raksasa dan merusak frame. Bayangannya tetap bekerja selama
   `visible_shadow = True`.
4. **Skala kartu cahaya jangan lebih dari ~0,6 di sumbu X.** Geometrinya 2â€“5 m
   lebar; skala 2,0 membuat "berkas" jadi dinding cahaya 10 m. Pakai
   (0,45â€“0,55 / 1,0 / 1,7) dan `z = -1,7` supaya ujung bawahnya tertutup pasir.
5. **Jangan naikkan angka ini tanpa render uji**: sun **3,8**, fill 110 W,
   volume 0,035. Di terumbu asli, sun 4,6 sudah membuat pasir terbakar putih di
   area berkas (4,6 masih pas untuk panggung primitif v001). Sun di atas ~5 dan
   volume di atas ~0,06 merusak frame.
6. **`Sky Texture` tidak dipakai** untuk world permukaan: dengan view transform
   Standard hasilnya clipping total (putih). Diganti gradient manual agar warna
   tetap sesuai palette. Catat kalau lead mau HDRI sungguhan â€” perlu file HDRI
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
   dan `anak.location = (0,0,0)` â€” jangan ikut menggeser anak.

## Plate shot 030 (v002)

Plate ini memakai **terumbu asli** dari `assets/env/reef.blend`, bukan panggung
primitif.

```
Append       assets/env/reef.blend â†’ Collection ENV_reef
Turunkan     semua objek root z -= 5.54 (dasar terumbu duduk di pasir z = -6)
Kamera       CAM_lookdev_reef, 26 mm, (-2.0, -6.4, -4.20)
             target (-0.25, 0.80, -5.55)
Material     karang bercabang & meja â†’ SHD_coral_live
             batu                     â†’ SHD_rock
             ikan & penyu             â†’ material asli pemiliknya (tidak diubah)
Pengisi      26 karang bercabang disusun jadi 3 gugusan (pengisi frame,
             bukan aset produksi)
Penyu        hide_render = True (subjeknya shot 040, bukan 030)
```

Render: EEVEE Next, 1920Ã—1080, 64 sampel, Â±7 detik. Hasil di
`renders/stills/scene-1-shot-030_lookdev.png` (tidak masuk git).

Catatan untuk Anggota 3 (`reef.blend`): warna material ikan sudah saya ukur â€”
`MAT_fish_kakatua` `#3E8E6E` (persis hijau terumbu, aman), `MAT_fish_cakalang`
`#4A6E96`, `MAT_fish_hiu` `#6E7B80`, tetapi `MAT_fish_goropa-merah` `#C0392B`
merah menyala, bukan oranye karang `#E4713C`. Merah jenuh juga yang pertama
hilang di bawah air, jadi secara fisik kurang masuk akal.

Model ikannya sendiri **lengkap** â€” badan, ekor, dan sirip punggung sebagai
objek terpisah yang di-parent ke badan. Sempat terlihat "tanpa ekor" di plate
karena kesalahan saya, bukan karena modelnya (lihat poin 9 di atas).

## Dunia permukaan (v003)

Pulau, kampung, dermaga, dan terumbu ada di **satu sistem koordinat**: pulau
berpusat di origin, jadi terumbu bawah laut duduk di bawah air tepat di ujung
dermaga, bukan di panggung terpisah. Semua transform sudah di-*apply*; data
verteks = koordinat dunia.

```
Collection            Isi
LIB_surface_island    ENV_surface_island â€” 420 x 280 m, siluet 36 titik
LIB_surface_sea       ENV_surface_sea â€” satu bidang bergradasi +-7000 m;
                      warna air di-bake per-verteks ke atribut sea_col
ENV_surface_veg       639 pohon (palem & berdaun lebar), linked duplicate
ENV_surface_village   ENV_surface_pier, _pier_apron, _diveshop,
                      _house_00 â€¦ _house_11
ENV_surface_boats     3 perahu bercadik (lihat tabel di bawah)
ENV_reef              224 objek: karang, ikan, penyu, pasir dasar
TMP_build             prototipe, hide_render = True
```

Air laut bukan satu bidang datar per shot, melainkan satu mesh besar dengan
warna kedalaman yang di-bake, supaya tidak ada sambungan antar-shot.

### Perahu

Sumber: `assets/props/boats.blend` **v004** (3 Nov 2026, 85 objek, satu perahu
bercadik). Ke-85 bagian digabung jadi satu mesh `LIB_boat_cadik`
(24.731 verts / 23.392 face / 15 material) lalu dipakai bersama oleh tiga
*linked duplicate* â€” jadi tiga perahu tidak menambah ukuran file.

| Objek | Posisi (x, y, z) | Rotasi Z | Keterangan |
|---|---|---|---|
| `PRP_boat_cadik_00` | 50 ; -104 ; 0 | 38Â° | berlabuh di teluk |
| `PRP_boat_cadik_01` | 65,9 ; -88 ; 0 | 90Â° | sisi barat dermaga |
| `PRP_boat_cadik_02` | 74,15 ; -120 ; 0 | -90Â° | sisi timur dermaga |

- `z = 0` adalah garis air: lambung bawah ada di -0,265 m, jadi perahu
  mengapung tanpa perlu digeser. Jangan menaikkannya â€” garis cat di lambung
  sudah dibuat untuk z = 0.
- Tepi dermaga di x 68,3 dan 71,7; perahu diberi celah Â±1,0 m dari tepi supaya
  balok cadik tidak menyentuh tiang.
- Perahu **tidak** boleh digeser mendekati tepi lagi: dek dermaga setinggi
  1,60 m, lambung perahu hanya 0,30 m, jadi kalau terlalu rapat keduanya
  saling menutup di kamera setinggi dek.

### Penyu

Penyu (`ENV_reef_turtle` + `x00`â€¦`x05`) di-*append* ulang dari
`assets/env/reef.blend` supaya material dobelnya hilang: dulu file ini punya
`MAT_turtle_shell` **dan** `MAT_turtle_shell.001`. Skala aslinya non-seragam
(0,48 / 0,40 / 0,15) â€” lihat poin 8 di atas.

## Pratinjau

- `renders/stills/scene-1-shot-030_lookdev.png` â€” plate shot 030 di atas terumbu
  asli (1920Ã—1080). Tidak masuk git.

## Belum selesai

- [x] Karang di file ini sudah diganti blockout asli `assets/env/reef.blend`
      dan diuji di shot 030 (v002).
- [ ] Uji 2 shot bawah laut lainnya: 050 (Nara muncul dari balik karang) dan
      040 (penyu). Butuh rig Nara dari peran 6.
- [ ] `ENV_surface_water-placeholder` di `assets/env/surface.blend` masih bidang
      air datar. Shader air aslinya `SHD_water_surface` dari file ini; perlu
      koordinasi dengan pemilik `surface.blend` (Jasiel) sebelum diganti.
- [ ] Shader permukaan air dilihat dari bawah (shot 020 turun ke air) belum final.
- [x] Partikel/debris kecil di air (diminta shot 030â€“060) belum dibuat.
      **Sudah:** `FX_particles` (200 bola r 1â€“2 cm) + 3 god ray card + 2 fog
      card di koleksi `FX_atmosphere` (v004, 27 Nov 2026).
- [x] Look dev permukaan (shot 010, 080, 090): pulau, kampung, dermaga, perahu,
      dan lautan dengan `WLD_scene-1_surface` (v003, 3 Nov 2026).
- [ ] Perahu di sisi dermaga masih terbaca "di bawah kolong" kalau kamera
      setinggi dek (shot 090), karena dek 1,60 m sementara lambung perahu
      0,30 m. Kalau mengganggu, turunkan dek dermaga ke Â±1,1 m â€” bukan
      menggeser perahu.
- [ ] Laut dalam keadaan ombak tenang; belum ada gerak permukaan untuk shot
      020/070.

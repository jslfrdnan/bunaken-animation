# assets/look — Look Dev & Shading

Pemilik: **Vaughn Toy** (Anggota 7 — Lighting & Shading)

## Isi

| File | Isi |
|---|---|
| `scene-1-look.blend` | World, shader air/pasir/karang/batu, panggung uji, plate shot 030 di atas terumbu asli (v002), dan dunia permukaan: pulau + kampung + dermaga + perahu dengan terumbu di ujung dermaga (v003, 3 Nov 2026) |

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

## Dunia permukaan (v003)

Pulau, kampung, dermaga, dan terumbu ada di **satu sistem koordinat**: pulau
berpusat di origin, jadi terumbu bawah laut duduk di bawah air tepat di ujung
dermaga, bukan di panggung terpisah. Semua transform sudah di-*apply*; data
verteks = koordinat dunia.

```
Collection            Isi
LIB_surface_island    ENV_surface_island — 420 x 280 m, siluet 36 titik
LIB_surface_sea       ENV_surface_sea — satu bidang bergradasi +-7000 m;
                      warna air di-bake per-verteks ke atribut sea_col
ENV_surface_veg       639 pohon (palem & berdaun lebar), linked duplicate
ENV_surface_village   ENV_surface_pier, _pier_apron, _diveshop,
                      _house_00 … _house_11
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
*linked duplicate* — jadi tiga perahu tidak menambah ukuran file.

| Objek | Posisi (x, y, z) | Rotasi Z | Keterangan |
|---|---|---|---|
| `PRP_boat_cadik_00` | 50 ; -104 ; 0 | 38° | berlabuh di teluk |
| `PRP_boat_cadik_01` | 65,9 ; -88 ; 0 | 90° | sisi barat dermaga |
| `PRP_boat_cadik_02` | 74,15 ; -120 ; 0 | -90° | sisi timur dermaga |

- `z = 0` adalah garis air: lambung bawah ada di -0,265 m, jadi perahu
  mengapung tanpa perlu digeser. Jangan menaikkannya — garis cat di lambung
  sudah dibuat untuk z = 0.
- Tepi dermaga di x 68,3 dan 71,7; perahu diberi celah ±1,0 m dari tepi supaya
  balok cadik tidak menyentuh tiang.
- Perahu **tidak** boleh digeser mendekati tepi lagi: dek dermaga setinggi
  1,60 m, lambung perahu hanya 0,30 m, jadi kalau terlalu rapat keduanya
  saling menutup di kamera setinggi dek.

### Penyu

Penyu (`ENV_reef_turtle` + `x00`…`x05`) di-*append* ulang dari
`assets/env/reef.blend` supaya material dobelnya hilang: dulu file ini punya
`MAT_turtle_shell` **dan** `MAT_turtle_shell.001`. Skala aslinya non-seragam
(0,48 / 0,40 / 0,15) — lihat poin 8 di atas.

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
- [x] Look dev permukaan (shot 010, 080, 090): pulau, kampung, dermaga, perahu,
      dan lautan dengan `WLD_scene-1_surface` (v003, 3 Nov 2026).
- [ ] Perahu di sisi dermaga masih terbaca "di bawah kolong" kalau kamera
      setinggi dek (shot 090), karena dek 1,60 m sementara lambung perahu
      0,30 m. Kalau mengganggu, turunkan dek dermaga ke ±1,1 m — bukan
      menggeser perahu.
- [ ] Laut dalam keadaan ombak tenang; belum ada gerak permukaan untuk shot
      020/070.

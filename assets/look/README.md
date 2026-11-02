# assets/look — Look Dev & Shading

Pemilik: **Vaughn Toy** (Anggota 7 — Lighting & Shading)

## Isi

| File | Isi |
|---|---|
| `scene-1-look.blend` | World, shader air/pasir/karang/batu, panggung uji, dan plate shot 030 di atas terumbu asli (v002, 2 Nov 2026) |

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
hilang di bawah air, jadi secara fisik kurang masuk akal. Selain itu geometri
ikan masih kotak gepeng sehingga terbaca seperti balon dari samping. Keduanya
bukan wewenang saya untuk ubah di file itu.

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

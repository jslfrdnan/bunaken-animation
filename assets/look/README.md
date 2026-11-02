# assets/look — Look Dev & Shading

Pemilik: **Vaughn Toy** (Anggota 7 — Lighting & Shading)

## Isi

| File | Isi |
|---|---|
| `scene-1-look.blend` | World, shader air/pasir/karang/batu, dan panggung uji Scene 1 (v001, 1 Nov 2026) |

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
3. **Jangan naikkan angka ini tanpa render uji**: sun 4.6, fill 110 W, volume
   0.035. Dengan view transform Standard, sun di atas ~6 membuat pasir putih
   terbakar, dan volume di atas ~0.06 membuat seluruh frame jadi kabut rata.
4. **`Sky Texture` tidak dipakai** untuk world permukaan: dengan view transform
   Standard hasilnya clipping total (putih). Diganti gradient manual agar warna
   tetap sesuai palette. Catat kalau lead mau HDRI sungguhan — perlu file HDRI
   di `assets/textures/` dan pengujian ulang.

## Pratinjau

`renders/stills/scene-1-look_v001.png` (tidak masuk git).

## Belum selesai

- [ ] Karang di file ini masih primitif. Blockout asli sudah ada di
      `assets/env/reef.blend` (`ENV_reef_branching-coral`, `_boulder-coral`,
      `_table-coral`) — langkah berikutnya mengganti panggung uji dengan
      blockout itu lewat *link*, lalu uji 3 shot (030, 050, 080).
- [ ] `ENV_surface_water-placeholder` di `assets/env/surface.blend` masih bidang
      air datar. Shader air aslinya `SHD_water_surface` dari file ini; perlu
      koordinasi dengan pemilik `surface.blend` (Jasiel) sebelum diganti.
- [ ] Shader permukaan air dilihat dari bawah (shot 020 turun ke air) belum final.
- [ ] Partikel/debris kecil di air (diminta shot 030–060) belum dibuat.

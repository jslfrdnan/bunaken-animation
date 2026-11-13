# motion/ — Animatic Scene 1 (Remotion)

Animatic **Scene 1** dibuat di Remotion dari aset yang **sudah ada di repo**, bukan
render Blender. Tujuannya mengunci timing 35 detik dan komposisi tiap shot
sebelum pekerjaan 3D/rig jalan.

| | |
|---|---|
| Komposisi | `Scene1Animatic` |
| Durasi | 840 frame = **35 detik** @ 24 fps |
| Resolusi | 1920 × 1080 |
| Jumlah shot | 10 (010–100), sesuai `PROJECT.md` §4 |

## Aset yang dipakai

| Sumber | Dipakai di | Catatan |
|---|---|---|
| `public/board/panel-1a.jpg` | 010, 020 | potongan papan cerita v002 |
| `public/board/panel-1b.jpg` | 040, 050, 060 | idem |
| `public/board/panel-1c.jpg` | 080, 090 | idem |
| `public/board/panel-4b.jpg` | 100 | **pinjam panel Scene 4** — belum ada panel Scene 1 untuk shot ini |
| `public/ref/ref-reef.jpg` | 030 | foto acuan, bukan bagian film |
| `public/ref/ref-perahu.jpg` | 070 | foto acuan perahu bercadik |

Papan cerita asli: `storyboard/frames/storyboard-2shot-per-scene_v002.jpg`
(2752 × 1536). Potongan panel dibuat dengan System.Drawing, margin 2 px.

## Aset 3D (GLB)

Model Blender diekspor ke `public/models/` untuk komposisi `Scene1ThreeD`:

| File | Isi | Status |
|---|---|---|
| `env-surface.glb` | pulau, dermaga, dive shop, 360 kelapa + 40 mangrove | dipakai |
| `env-reef.glb` | karang, 6 jenis ikan, penyu placeholder | dipakai |
| `sea-turtle.glb` | penyu hijau dari `sea_turtle.blend` | dipakai |
| `boat.glb` | perahu bercadik | dipakai |
| `char-nara.glb`, `char-daniel.glb` | blockout karakter | dipakai |
| `env-palm.glb` | pohon kelapa, origin di pangkal batang | **baru, siap dipakai** |
| `env-mangrove.glb` | mangrove, origin di garis air | **baru, siap dipakai** |

Sumber dua aset terakhir: `assets/env/vegetation.blend`, diekspor dengan
`scripts/export-vegetation-glb.py`. Skala nyata, 1 unit = 1 m; konversi
Blender→three tetap `B(x, y, z) = [x, z, -y]`.

**Foto acuan hanya untuk animatic internal.** Jangan pernah memakai foto acuan
sebagai tekstur, latar, atau bagian film final (`PROJECT.md` §1.4).

## Yang membuat gambar diam terasa bergerak

- `shots.ts` menyimpan `from`/`to` per shot: skala 1,02 → 1,14 dan titik fokus
  bergeser, jadi setiap shot punya push-in / tilt / pan sendiri.
- Cross-dissolve 6 frame antar shot, bukan cut keras, supaya mata tidak kaget.
- Shot 090 diberi goyangan halus (handheld).
- Shot 100 memudar ke hitam di 18 frame terakhir.
- Judul film muncul 3 detik pertama shot 010 sebagai overlay
  (`PROJECT.md` §1.6), lalu hilang.

## Warna

Semua warna dari palette `PROJECT.md` §2. Papan cerita abu-abu diberi tint
lewat lapisan `mix-blend-mode: color`:

| Grade | Shot | Tint |
|---|---|---|
| `golden` | 010, 100 | pasir hangat `#E8D5B0` |
| `shallow` | 020 | teal `#1FA3A3` |
| `reef` | 030, 040, 050 | teal dalam `#0F5C63` + kartu cahaya |
| `deep` | 060 | teal dalam lebih pekat |
| `deck` / `warm` | 080, 090, 070 | pasir hangat tipis |

## Perintah

```bash
cd motion
npm i
npm run dev            # Remotion Studio → http://localhost:3000
npx remotion render Scene1Animatic ../renders/animatic/scene-1_animatic_v001.mp4
```

Hasil render **tidak masuk git** (`renders/` diabaikan). Catat tautannya di
`docs/renders.md`.

## Slate

Slate kanan-bawah dan label shot kiri-bawah berguna untuk review. Matikan
dengan mengubah `defaultProps.slate` menjadi `false` di `src/Root.tsx` sebelum
render bersih.

## Belum ada (menunggu aset lain)

- Audio: narasi, musik kolintang, ambient — `assets/audio/scene-1/` masih kosong.
- Render 3D: belum ada plate dari `scenes/scene-1.blend`.
- Rig Nara: shot 050/060/070/100 masih papan cerita.
- Panel Scene 1 untuk shot 100 (sekarang meminjam panel 4B).
- Shot 020 dan 040 belum punya panel khusus (masih memakai crop panel 1A/1B).

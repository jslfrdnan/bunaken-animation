# motion/ — Acuan timing (BUKAN animasi)

> **Keputusan lead 14 Nov 2026:** animasi dibuat **hanya di Blender**. Folder
> ini bukan sumber animasi dan tidak boleh dipakai untuk menghasilkan
> animasi/gambar bergerak. Gunakan `motion/` hanya sebagai acuan timing dan
> pembanding komposisi. Deliverable animasi = `scenes/scene-X_shot-*.blend` +
> render Blender.

Repo ini punya **dua** komposisi animatic:

| Komposisi | Cakupan | Durasi |
|---|---|---|
| `FilmAnimatic` | **4 scene penuh** (2:25) — plate papan cerita + subtitle bakar | 3480 frame = **2 menit 25 detik** |
| `Scene1Animatic` | Scene 1 saja, timing 35 detik | 840 frame = **35 detik** |

Animatic dibuat dari aset yang **sudah ada di repo**, bukan render Blender.
Tujuannya mengunci timing dan komposisi tiap shot sebelum pekerjaan 3D/rig
jalan.

| | `FilmAnimatic` |
|---|---|
| Resolusi | 1920 × 1080 |
| Frame rate | 24 fps |
| Jumlah shot | 38 (10 + 9 + 10 + 9) |
| Sumber data | `src/film.ts` (scene 2–4) + `src/shots.ts` (scene 1) |
| Subtitle | `src/subtitles.ts`, dari `docs/narasi.md` |

Script pemotong panel: `scripts/slice-storyboard.py` (deteksi garis panel dari
profil piksel, bukan tebak koordinat).

## Aset yang dipakai `FilmAnimatic`

| Panel | Dipakai di | Catatan |
|---|---|---|
| `panel-1a.jpg` | S1 010/020, S2 090 | aerial, perahu |
| `panel-1b.jpg` | S1 040–060, S2 020/030, S3 020 | terumbu & penyu |
| `panel-1c.jpg` | S1 080/090, S3 070, S4 060 | dive shop & anak-anak |
| `panel-2a.jpg` | S2 010/090 | perahu subuh |
| `panel-2b.jpg` | S2 060, S3 030/040/080 | dermaga & konfrontasi |
| `panel-3a.jpg` | S2 040/050, S3 010/100, S4 030 | kamera bawah air & karang rusak |
| `panel-3b.jpg` | S2 080, S3 050/060 | buku utang & Haris |
| `panel-4a.jpg` | S2 070, S3 090, S4 010/020/040/050 | mooring buoy & kerja bersama |
| `panel-4b.jpg` | S4 070/080, S1 100 | penyu & Nara di dermaga |

Papan cerita asli: `storyboard/frames/storyboard-2shot-per-scene_v002.jpg`
(2752 × 1536), grid 3 × 3. Panel dipotong 3 px di dalam garis tepi.

## Subtitle

`src/subtitles.ts` memuat 14 cue dari `docs/narasi.md`; cue tagline (2:20)
**tidak** didaftarkan karena sudah tampil sebagai kartu teks di shot 090 Scene 4.
Gaya: putih, outline hitam, maksimal 2 baris, di bawah area aman.

## Animatic Scene 1 (lama)

| | |
|---|---|
| Komposisi | `Scene1Animatic` |
| Durasi | 840 frame = **35 detik** @ 24 fps |
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

# animatic film penuh (2:25, subtitle bakar)
npx remotion render FilmAnimatic ../renders/animatic/warisan-bunaken_animatic_v001.mp4 \
  --codec=h264 --crf=20

# animatic Scene 1 saja
npx remotion render Scene1Animatic ../renders/animatic/scene-1_animatic_v001.mp4
```

Hasil render **tidak masuk git** (`renders/` diabaikan). Catat tautannya di
`docs/renders.md`.

## Slate

Slate kanan-bawah dan label shot kiri-bawah berguna untuk review. Matikan
dengan mengubah `defaultProps.slate` menjadi `false` di `src/Root.tsx` sebelum
render bersih.

## Belum ada (menunggu aset lain)

- Audio: narasi, musik kolintang, ambient — `assets/audio/` masih kosong.
- Render 3D: baru Scene 1 shot 010–100 dan Scene 2 shot 010–050 yang punya
  file animasi; scene 3–4 belum. Plate animatic masih papan cerita.
- Rig Nara halus: shot 050/060/070/100 masih papan cerita di `FilmAnimatic`.
- Model Haris & crowd: shot Scene 2 060–090, Scene 3 030–090, dan Scene 4
  010/040/050/060 masih memakai panel pinjaman.
- Panel khusus shot 020 dan 040 Scene 1 (masih crop panel 1A/1B).

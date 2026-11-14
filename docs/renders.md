# Catatan Render & Animatic

Render **tidak pernah** di-commit ke git (tanpa LFS, dan repo harus tetap ringan).
Simpan file di tempat berikut, lalu catat tautannya di tabel ini.

| Jenis | Tempat |
|---|---|
| File kerja harian, preview kasar | Google Drive tim |
| Animatic & render final per versi | GitHub Releases |
| Video promosi/akhir | YouTube unlisted |

## Cara membuat Release

1. Buka repo → **Releases** → **Draft a new release**
2. Tag: `animatic-scene-1-v001`
3. Upload file `.mp4`
4. Catat tautannya di tabel bawah

## Daftar render

| Tanggal | Item | Versi | Tautan | Catatan |
|---|---|---|---|---|
| 2 Nov 2026 | Render cek look dev shot 030 (stills) | v002 | tidak di-commit | hasil Vaughn Toy, plate di `assets/look/scene-1-look.blend` |
| 2 Nov 2026 | Render cek aset environment (terumbu, pulau, perahu) | v001 | tidak di-commit | QA internal lead — bukan untuk ditayangkan |
| 8 Nov 2026 | Render cek aset vegetasi (kelapa & mangrove) | v001 | tidak di-commit | preview di `renders/stills/vegetation-*.png` |
| 10 Nov 2026 | Render cek vegetasi pulau + populasi terumbu | v002 | tidak di-commit | still di `renders/stills/3d-f*-lush.png` dan `3d-f*-reef*.png` |
| 13 Nov 2026 | Animatic Scene 1 (2D, tanpa audio) | v001 | tidak di-commit — `renders/animatic/scene-1_animatic_v001.mp4` | 840 frame = 35 s, 10 shot; slate masih aktif; MP4 ±30 MB |
| — | Animatic Scene 1 (audio penuh) | v002 | _belum ada_ | menunggu audio peran 8 |
| 13 Nov 2026 | Render cek rig dasar Nara (3 still) | v001 | tidak di-commit | preview `renders/stills/nara-rig-pose-0{1,2,3}.png` |
| 13 Nov 2026 | Render cek aset baru Scene 2 & 4: terumbu rusak, jaring terbentang, mooring buoy | v001 | tidak di-commit | preview 50% di `renders/stills/reef-damaged_preview-0{1,2}.png`, `fishing-net-spread_preview-0{1,2}.png`, `mooring-buoy_preview-0{1,2,3}.png`; menunggu review lead |
| 13 Nov 2026 | Render cek animasi Scene 2 shot 010–050 (5 still) | v001 | tidak di-commit | preview `renders/stills/anim-s2-0{10,20,30,40,50}_v001.png`; laporan audit hilang saat server restart |
| 14 Nov 2026 | Render cek aset Scene 3 & 4: kerangka karang, keramba rumput laut, kamera bawah air, buku utang | v001 | tidak di-commit | preview 50% 2 sudut per aset di `renders/stills/{coral-frame,seaweed-farm,underwater-camera,debt-book}_preview-0{1,2}.png`; menunggu review lead |
| 14 Nov 2026 | **Animatic film penuh 4 scene (2:25) + subtitle bakar** | v001 | tidak di-commit — `renders/animatic/warisan-bunaken_animatic_v001.mp4` | 3480 frame = 145,0 s, 1920×1080, 24 fps, H.264, 72,3 MB; plate papan cerita v002 (belum render 3D); 16 cue subtitle dari `docs/narasi.md`; tanpa audio |
| 14 Nov 2026 | Animatic film penuh + **audio sementara** | v002 | tidak di-commit — `renders/animatic/warisan-bunaken_animatic_v002_audio.mp4` | video v001 + bed ambience sintetis 145 s (`renders/audio/warisan-bunaken_ambience_v001.wav`, 48 kHz stereo); **bukan audio final** — narasi & musik masih menunggu peran 8 |
| 14 Nov 2026 | **Animatic Scene 1 (render ulang bersih)** | v001 | tidak di-commit — `renders/animatic/scene-1_animatic_v001.mp4` | 840 frame = 35,0 s, 1920×1080, 24 fps, 20,5 MB; slate dimatikan; tanpa audio |
| 14 Nov 2026 | Render cek aset @modelling: papan nama dive shop, karang pulih, perahu Haris | v001 | tidak di-commit | preview 50% `renders/stills/{dive-shop-sign,reef-recovering,haris-boat}_preview-0{1,2}.png`; menunggu review lead |
| 14 Nov 2026 | **Render 3D Scene 1 dari master** (`scenes/scene-1_master_v001.blend`, 10 scene = 10 shot) | v001 | tidak di-commit — `renders/scene-1/scene-1_v001.mp4` | 840 frame = 35,0 s, 1920×1080, 24 fps, EEVEE Next taa 16, H.264 CRF 18, 9,4 MB; PNG arsip di `renders/scene-1/frames/S1_0{10..100}/`; master 8,8 MB, tanpa library eksternal |
| 14 Nov 2026 | **Render 3D Scene 2 (shot yang ada: 010–050)** | v001 | tidak di-commit — `renders/scene-2/scene-2_v001.mp4` | 480 frame = 20,0 s (**dari 35 s**; 060–090 belum ada), 1920×1080, 24 fps, 6,6 MB; master `scene-2_master_v001.blend` 5 scene |
| 14 Nov 2026 | **Render 3D Scene 3 (010, 020, 050, 100)** | v001 | tidak di-commit — `renders/scene-3/scene-3_v001.mp4` | 384 frame = 16,0 s (**dari 40 s**), 1920×1080, 24 fps, 7,6 MB; master 4 scene. Shot 010 dirender ulang setelah Nara dibaringkan (empty `CTL_nara_prone`) dan resolusi dikembalikan 100% |
| 14 Nov 2026 | **Render 3D Scene 4 (020, 030, 070, 080, 090)** | v001 | tidak di-commit — `renders/scene-4/scene-4_v001.mp4` | 456 frame = 19,0 s (**dari 35 s**), 1920×1080, 24 fps, 3,5 MB; termasuk kartu tagline Blender; master 5 scene |
| 14 Nov 2026 | **FILM 2:25 dari render Blender** (38 shot, subtitle bakar, audio sementara) | v001 | tidak di-commit — `renders/film/warisan-bunaken_film_v001.mp4` | **3480 frame = 145,0 s**, 1920×1080, 24 fps, H.264 CRF 18, **39,0 MB**; audio AAC 48 kHz stereo = bed ambience sintetis (bukan audio final); 15 cue subtitle digambar per frame (ffmpeg tanpa libass); master `scenes/scene-<n>_master_v002.blend` (10/9/10/9 scene = 3480 frame) |
| 14 Nov 2026 | **Render per scene v002** (semua 38 shot) | v002 | tidak di-commit — `renders/scene-<n>/scene-<n>_v002.mp4` | Scene 1 840f/35,0 s/10,0 MB · Scene 2 840f/35,0 s/9,3 MB · Scene 3 960f/40,0 s/11,5 MB · Scene 4 840f/35,0 s/6,4 MB; total 3480 frame, 1920×1080, 24 fps, tanpa audio |

## Aturan penamaan file render

```
scene-1_animatic_v001.mp4
scene-1_shot-010_v003.png
warisan-bunaken_final_1080p_v001.mp4
```

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

## Aturan penamaan file render

```
scene-1_animatic_v001.mp4
scene-1_shot-010_v003.png
warisan-bunaken_final_1080p_v001.mp4
```

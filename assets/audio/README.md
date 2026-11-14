# Audio — Narasi, Musik, SFX

Folder ini **kosong dari audio final**. Narasi harus direkam manusia (satu
pengisi suara, hangat, tidak teatrikal); musik dan SFX harus dilisensikan atau
direkam sendiri. AI tidak boleh mengarang rekaman narasi.

## Yang dibutuhkan per scene

| Scene | Durasi | Isi |
|---|---|---|
| 1 Permata | 35 s | ambient laut + burung, gelembung, percikan, kolintang + strings |
| 2 Retak | 35 s | subuh, ledakan tertahan, gesekan jaring, murmur warga, strings tanpa melodi |
| 3 Titik Balik | 40 s | klik kamera, murmur, kertas, hening, strings rendah |
| 4 Warisan | 35 s | pagi, klakson perahu, gelembung, tali, tawa anak, kolintang + strings |

Cue waktu lengkap ada di [`docs/narasi.md`](../../docs/narasi.md); subtitle final
di [`assets/subtitles/warisan-bunaken_v001.srt`](../subtitles/warisan-bunaken_v001.srt).

## Konvensi file

```
assets/audio/scene-1/narasi_scene-1_v001.wav
assets/audio/scene-1/musik_scene-1_v001.wav
assets/audio/scene-1/sfx_scene-1_v001.wav
assets/audio/mix/warisan-bunaken_mix_v001.wav
```

- WAV **48 kHz, 24-bit**, stereo.
- Narasi selalu dominan; musik turun **−6 dB** saat narasi.
- Hening **1 detik** sebelum tagline (2:19).
- Ledakan Scene 2 diredam — bukan SFX film perang.
- Jangan commit file >50 MB dan jangan pakai Git LFS.

## Status 14 Nov 2026

| Item | Status |
|---|---|
| Naskah + cue | ✅ `docs/narasi.md` |
| Subtitle `.srt` | ✅ 16 cue |
| Bed ambience sementara (animatic) | ✅ `scripts/make-ambience.py` → `renders/audio/warisan-bunaken_ambience_v001.wav` (tidak di-commit) |
| Narasi direkam | ⬜ butuh manusia |
| Musik kolintang + strings | ⬜ butuh lisensi/rekaman |
| SFX per scene | ⬜ |

Bed ambience sintetis **hanya** untuk review animatic. Jangan pernah
menganggapnya audio final.

# Warisan Bunaken

Animasi 3D pendek tentang seorang pemudi Bunaken yang berhadapan dengan nelayan
yang memakai bom dan jaring dasar — dan menemukan bahwa orang yang merusak laut
sering kali juga korbannya.

**Tagline:** *Laut yang dijaga adalah warisan, bukan tambang.*

| | |
|---|---|
| Format | Animasi 3D, 4 scene |
| Durasi | 2 menit 25 detik (minimum 4 × 30 detik terpenuhi) |
| Resolusi | 1920×1080, 24 fps |
| Render | EEVEE Next (Blender 5.2 LTS) |
| Narasi | Bahasa Indonesia, direkam tim sendiri |
| Subtitle | Bahasa Indonesia |
| Lokasi cerita | Kampung Bunaken, Taman Nasional Laut Bunaken, Manado |

## Struktur repository

```
README.md                 kamu di sini
PROJECT.md                panduan proyek lengkap — BACA INI DULU
AGENTS.md                 aturan kerja AI (dibaca otomatis setiap sesi)
CONTRIBUTING.md           aturan kerja tim (WAJIB dibaca sebelum commit)
docs/                     dokumen teknis lintas tim
  renders.md              catatan link render & animatic
  credits.md              kredit, lisensi, dan sumber data
  prompts-imagegen.md     16 prompt Gemini (00 lembar + 01–15) untuk storyboard
scripts/                  skrip bantu (baca-catatan.ps1)
assets/                   aset sumber per departemen
  env/ char/ props/ textures/ audio/ look/
scenes/                   file .blend master per scene
renders/                  hasil render (TIDAK di-commit, lihat docs/renders.md)
storyboard/               gambar frame storyboard
```

## Mulai dalam 3 langkah

1. `git clone https://github.com/jslfrdnan/bunaken-animation.git`
2. Baca `PROJECT.md` — cerita, gaya visual, spesifikasi teknis, aset, peran,
   jadwal, dan aturan git semuanya ada di sana.
3. Baca `CONTRIBUTING.md`, lalu ambil bagianmu di tabel peran `PROJECT.md` §9.

## Aturan yang tidak boleh dilanggar

- Kerja lewat **Pull Request**. Jangan push langsung ke `main`. **`git pull` sebelum mulai kerja.**
- **Satu file `.blend` = satu pemilik.** Jangan buka `.blend` milik orang lain untuk diedit.
- Render, video, dan file >50 MB **tidak masuk git**.
- Setiap aset yang bukan buatan sendiri dicatat di `docs/credits.md`.

## Status

Scene 1 — animatic kasar (target 2 November 2026). Rincian tugas dan tenggat
ada di `PROJECT.md` §9–§10.

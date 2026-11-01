# Warisan Bunaken

Animasi 3D pendek tentang seorang pemuda Bunaken yang berhadapan dengan nelayan
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
AGENTS.md                 aturan kerja AI (dibaca otomatis setiap sesi)
CONTRIBUTING.md           aturan kerja tim (WAJIB dibaca sebelum commit)
docs/                     dokumen teknis lintas tim
  renders.md              catatan link render & animatic
  prompts-imagegen.md     16 prompt Gemini (00 lembar + 01–15) untuk storyboard
scripts/                  skrip bantu (baca-vault.ps1)
assets/                   aset sumber per departemen
  env/ char/ audio/ props/ textures/
scenes/                   file .blend master per scene
renders/                  hasil render (TIDAK di-commit, lihat docs/renders.md)
storyboard/               gambar frame storyboard
Obsidian-Project-Animasi/ catatan proyek (buka sebagai vault Obsidian)
```

## Mulai dalam 3 langkah

1. `git clone https://github.com/jslfrdnan/bunaken-animation.git`
2. Baca `CONTRIBUTING.md`, lalu `Obsidian-Project-Animasi/40-Panduan/01-alur-git.md`
3. Buka `Obsidian-Project-Animasi/` sebagai vault di Obsidian → mulai dari `00-Proyek/01-ringkasan.md`

## Aturan yang tidak boleh dilanggar

- Kerja langsung di `main`. **`git pull` sebelum mulai kerja.**
- **Satu file `.blend` = satu pemilik.** Jangan buka `.blend` milik orang lain untuk diedit.
- Render, video, dan file >50 MB **tidak masuk git**.
- Setiap aset yang bukan buatan sendiri dicatat di `30-Aset/02-kredit.md`.

## Status

Scene 1 — animatic. Lihat `40-Panduan/04-tugas-scene-1.md`.

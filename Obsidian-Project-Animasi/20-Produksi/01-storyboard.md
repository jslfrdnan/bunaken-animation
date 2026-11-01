---
tags: [produksi, storyboard]
---

# Storyboard — Gambaran Umum

Rincian per shot ada di file terpisah per scene. Scene 1 sudah lengkap:
[[02-shotlist-scene-1]].

| Scene | Durasi | Shot | Status shot list | File |
|---|---|---|---|---|
| 1. Permata | 35 s | 10 | ✅ lengkap | [[02-shotlist-scene-1]] |
| 2. Retak | 35 s | ~9 | ⬜ belum | — |
| 3. Titik Balik | 40 s | ~10 | ⬜ belum | — |
| 4. Warisan | 35 s | ~9 | ⬜ belum | — |
| **Total** | **2:25** | **~38** | | |

Lembar ringkas 2 shot per scene (8 panel, satu gambar) untuk membaca alur:
[[05-storyboard-2shot-per-scene]].

## Cara membaca shot list

- **Shot** — nomor kelipatan 10 (`010`, `020`, …) agar bisa disisipkan shot baru
  tanpa menomori ulang.
- **Durasi** — detik. Total per scene harus tepat sesuai target.
- **Kamera** — jenis shot + gerakan. Tulis spesifik: "medium, tracking kanan",
  bukan "bagus".
- **Audio** — narasi/SFX/musik yang aktif di shot itu.
- **Frame** — nama file gambar di `storyboard/frames/scene-1/`.

## Aturan storyboard

1. **Satu shot = satu ide.** Kalau butuh dua kalimat untuk menjelaskan, pecah.
2. Durasi minimum shot 2 detik — di bawah itu penonton tidak sempat membaca.
3. Scene 1 **tidak boleh** punya shot lebih cepat dari 3 detik: tujuannya
   membangun ketenangan sebelum Scene 2 merusaknya.
4. Setiap scene wajib punya satu **shot establishing** yang memperlihatkan
   Bunaken secara jelas.

## Alur produksi gambar

1. Buat sketsa/blockout shot list (peran 2).
2. Generate frame dengan Gemini memakai [[03-prompt-imagegen]] di `docs/`.
3. Review bareng lead — tandai shot yang komposisinya tidak jalan.
4. Simpan versi final ke `storyboard/frames/scene-1/` dengan nama
   `scene-1_shot-010_v001.png`.

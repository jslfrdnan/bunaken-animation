---
status: In Progress
scene: 2
durasi: 32
pj: C, D
updated: 2026-10-12
tags:
  - project-animasi
  - scene
---

# Scene 2 — Menyelam

Bagian dari [[Tugas Project Animasi]] · Narasi: [[Narasi & Storyboard#Scene 2]] · Aset: [[Aset & Teknik#Scene 2]]

> [!abstract] Konsep
> *Match-cut* dari [[Scene 1 - Pulau Bunaken dari Udara]] (kamera menyentuh permukaan). Kini di bawah air: gelembung & caustics di permukaan, turun melewati god rays, lalu **dinding drop-off** khas Bunaken (*wall dive*) terungkap → menuju [[Scene 3 - Kehidupan Terumbu]].

## Spesifikasi
- Durasi **32 s** = 768 frame @ 24 fps, 1920×1080, EEVEE
- Berkas: `Project/blender/scene2.blend` (aset di-link dari `aset.blend`)
- Gaya low-poly; warna memudar sesuai kedalaman (merah hilang dulu — nyambung Bab 6 e-book)

## Shot list

| Shot | Frame | Durasi | Isi | Kamera |
|---|---|---|---|---|
| 1 | 1–240 | 10 s | Menembus permukaan dari posisi akhir Scene 1; gelembung + kilau caustics di permukaan dari bawah | Dekat permukaan, menunduk |
| 2 | 241–480 | 10 s | Turun melewati god rays; partikel plankton melayang | Turun perlahan |
| 3 | 481–768 | 12 s | Dinding drop-off berkarang terungkap; kamera menyusuri ke bawah | Menyusuri dinding |

## Elemen

### Buatan sendiri
- [ ] Dinding drop-off vertikal (low-poly, berkarang) + teras karang di dasar (transisi Scene 3)
- [ ] Permukaan laut dari bawah (terang, beriak) + dasar laut dalam
- [ ] Kabut biru (volume scatter) + god rays (matahari dari atas)
- [ ] Caustics di dinding & dasar (tekstur noise emisi)
- [ ] Gelembung naik
- [ ] Gradasi warna per kedalaman
- [ ] Kamera 3 shot (turun) + transisi ke Scene 3

### Aset publik (perlu galeri verifikasi — belum ada)
- [ ] Karang: meja, otak, kipas (gorgonian), anemon, spons tabung
- [ ] Ikan karang: badut, ekor kuning/lalosi (aksen; kawanan besar di Scene 3/4)

## Catatan
- God rays & caustics pakai teknik ringan agar render cepat.
- Posisi awal kamera menyambung posisi akhir kamera Scene 1 (match-cut).

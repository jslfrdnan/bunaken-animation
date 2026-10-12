---
status: In Progress
progress: 5
category: Tugas Akhir
mata-kuliah: "[[Grafika Komputer]]"
deadline: 2026-11-29
created: 2026-10-04
updated: 2026-10-04
tags:
  - tugas-akhir
  - animasi
  - blender
  - grafika-komputer
aliases:
  - Project Animasi
---

# Tugas Akhir: Project Animasi Blender bertema Perikanan Bunaken

Mata kuliah: [[Grafika Komputer]]

> [!abstract] Ringkasan
> Video animasi **Blender** berisi **4 scene** (masing-masing ≥ 30 detik) bertema **perikanan dan ekosistem laut Pulau Bunaken**. Scene penutup mereplikasi demo akhir video *Coding Adventure: Boids* (Sebastian Lague, menit 7:47–akhir): kapal selam menjelajah lingkungan rintangan dengan kawanan ikan.
> Referensi video: https://youtu.be/bqtqltqcQhw (file lokal `D:\Tugas Semester 5\Grafika Komputer\Coding Adventure Boids - Sebastian Lague (1080p).mp4`)
> Folder kerja: `D:\Tugas Semester 5\Grafika Komputer\Project`
> Tugas sebelumnya: [[Tugas Kelompok E-book Perikanan]] (algoritma boids dibahas di Bab 8 e-book).

> [!important] Deadline
> ==Minggu, 29 November 2026== (8 minggu dari 4 Oktober 2026).

## Ketentuan dosen
- Video animasi dibuat dengan **Blender**
- **4 scene**, tiap scene minimal **30 detik**

## Berkas & catatan terkait
- Naskah narasi & storyboard: [[Narasi & Storyboard]]
- Catatan per scene:
  - [[Scene 1 - Pulau Bunaken dari Udara]] ← **tahap 1 (dikerjakan pertama)**
  - [[Scene 2 - Menyelam]]
  - [[Scene 3 - Kehidupan Terumbu]]
  - [[Scene 4 - Ekspedisi Kapal Selam]]
- Aset publik, lisensi, kredit & teknik: [[Aset & Teknik]]

## Struktur folder `Project`

Folder kerja `D:\Tugas Semester 5\Grafika Komputer\Project` (repo git; `.blend`, render, audio, dan aset unduhan **tidak** masuk git — disimpan di OneDrive):

```
Project/
├── README.md                 # ringkasan proyek & peta folder
├── .gitignore                # kecualikan .blend, render/, audio/, edit/, aset/unduhan/
├── blender/
│   ├── aset.blend            # library aset bersama (di-link ke tiap scene)
│   └── scene1.blend …        # satu berkas per scene (belum dibuat)
├── skrip/
│   ├── cari_aset_sketchfab.py  # cari kandidat aset CC0/CC-BY di Sketchfab
│   ├── galeri_aset.py          # bangun galeri HTML verifikasi aset
│   └── awan_lowpoly.py         # generator awan low-poly buatan sendiri
├── aset/unduhan/             # aset Poly Pizza yang diunduh manual (CC0/CC-BY)
├── referensi/                # frame referensi video Boids
├── render/sceneN/            # hasil render per scene
├── audio/                    # narasi, musik, SFX
└── edit/                     # proyek editing video
```

> [!note] Yang masuk GitHub vs OneDrive
> GitHub menyimpan **skrip + README + .gitignore** (berversi). `.blend`, render, audio, dan aset unduhan ada di OneDrive agar repo ringan (keputusan Q19).

## Keputusan yang sudah disepakati

| # | Keputusan | Pilihan |
|---|---|---|
| Q1 | Tim & deadline | Kelompok 8 orang (sama seperti e-book); deadline 29 Nov 2026 |
| Q2 | Gaya visual | **Low-poly flat-shaded** seperti video, palet disesuaikan Bunaken (pasir krem, karang toska/ungu/jingga) |
| Q3 | Narasi 4 scene | 1 Pulau Bunaken dari udara → 2 Menyelam → 3 Kehidupan terumbu (+ pesan ancaman ekosistem) → 4 Ekspedisi kapal selam (replika video) |
| Q4 | Lingkup scene 4 | Lingkungan + karang + kapal selam + boids, utuh siap render |
| Q5 | Terumbu karang | Karang low-poly khas Bunaken disebar dengan **Geometry Nodes scatter** (kemiringan/ketinggian) |
| Q6 | Gerak ikan | **Skrip Python bake keyframe**: separation, alignment, cohesion + penghindaran rintangan sinar *golden spiral* (BVHTree) |
| Q7 | Model | Ikan: kawanan lalosi/ekor kuning + aksen ikan karang. Kapal selam: ~~buat sendiri~~ → aset publik (lihat Q31) |
| Q8 | Render | **EEVEE**, 1920×1080, 24 fps (Blender 5.2.2 LTS) |
| Q9 | Obsidian | Folder ini: catatan utama + Narasi & Storyboard + Scene 1–4 + Aset & Teknik |
| Q10 | Folder Project | `blender/` (scene + `aset.blend` di-link), `skrip/`, `render/`, `referensi/`, `audio/`, `edit/`; repo git sendiri |
| Q11 | Batu melayang (video) | Diganti **pinnacle/bommie** karang + satu **lengkungan swim-through** |
| Q12 | Terrain scene 4 | Procedural Python (noise → low-poly → warna vertex per ketinggian), dirapikan sculpt di jalur kamera |
| Q13 | Shot scene 4 | 40 s: establishing (8) → follow-cam (14) → lengkungan (10) → lampu & turun ke jurang (8) |
| Q14 | Boids vs kapal selam | Kapal selam = **rintangan bergerak** (ikan terbelah lalu berkumpul); **150 ikan** |
| Q15 | Kapal selam | Kapal selam riset **kuning** low-poly, lampu sorot, baling-baling, nama fiktif "KS Bunaken-01" |
| Q16 | Audio | **Narasi voice-over bahasa Indonesia** + musik royalty-free + SFX |
| Q17 | Tim | 2 orang per scene + peran lintas scene (lihat di bawah) |
| Q18 | Milestone | Lihat timeline |
| Q19 | Penyimpanan | Skrip & catatan → GitHub; `.blend` & render → OneDrive |
| Q20 | Tahap pertama | **Scene 1** (Pulau Bunaken dari udara); urutan cerita tetap |
| Q21 | Shot scene 1 | 40 s, 4 shot (lihat [[Scene 1 - Pulau Bunaken dari Udara]]) |
| Q22 | Waktu scene 1 | Pagi / golden hour, matahari ±25–30° |
| Q23 | Geografi | Stilisasi dari peta (siluet Bunaken, kerucut Manado Tua) |
| Q24 | Elemen darat | Pantai + kelapa, bakau, desa rumah panggung, dermaga, papan TN Bunaken, perahu tertambat; detail hanya di jalur kamera |
| Q25 | Air laut | Shader air low-poly bergelombang, gradasi kedalaman, *reef flat* toska → garis **drop-off** biru tua |
| Q26 | Perahu & nelayan | Perahu katinting bercadik + nelayan low-poly ber-rig sederhana |
| Q27 | Langit | Gradasi langit stilasi + awan low-poly + kabut tipis + burung |
| Q28 | Transisi 1→2 | *Match cut* di permukaan air; kamera bersama di `aset.blend` |
| Q29 | Narasi scene 1 | Lokasi, Taman Nasional, Segitiga Terumbu Karang, nelayan; ±70–90 kata; fakta diverifikasi dari sumber |
| Q30 | Skala | Dipadatkan (pulau ±¼ ukuran asli, Manado Tua didekatkan) |
| Q31 | Aset publik vs sendiri | **Publik**: props (kelapa, rumah, perahu, nelayan, burung, karang, ikan, kapal selam). **Sendiri**: terrain, shader laut/langit, animasi, kamera, boids, komposisi |
| Q32 | Sumber & lisensi | Hanya **CC0 / CC-BY**; kredit di [[Aset & Teknik]] + *end credits* |
| Q33 | Verifikasi aset | **Galeri HTML** 2–3 kandidat per aset → dipilih pengguna → impor → screenshot konfirmasi |
| Q34 | Penyeragaman | Material ulang ke palet flat bersama, flat shading, decimate bila perlu |
| Q35 | Aset tak tersedia | Ambil aset terdekat lalu **dimodifikasi sendiri** (cadik, atap seng) |
| Q36 | Nelayan | Karakter low-poly yang **sudah ber-rig** (mis. Quaternius CC0), diwarnai ulang, dianimasikan sendiri |
| Q37 | Pengambilan aset | Integrasi **Sketchfab** di add-on MCP aktif; Poly Pizza tidak aktif → dicari lewat browser, diunduh manual ke `aset/unduhan/` |

## Pembagian tugas (8 orang, posisi diundi)

| Posisi | Nama | Scene | Peran lintas scene |
|---|---|---|---|
| A | _(diundi)_ | Scene 1 | **Aset bersama** (`aset.blend`, palet, kredit) |
| B | _(diundi)_ | Scene 1 | – |
| C | _(diundi)_ | Scene 2 | **Naskah & narasi** (rekaman voice-over) |
| D | _(diundi)_ | Scene 2 | – |
| E | _(diundi)_ | Scene 3 | **Editing & audio** (musik, SFX, mixing) |
| F | _(diundi)_ | Scene 3 | – |
| G | _(diundi)_ | Scene 4 | **Skrip boids & generator terrain** |
| H | _(diundi)_ | Scene 4 | – |

## Timeline (4 Okt – 29 Nov 2026)

| Minggu | Tanggal | Target |
|---|---|---|
| 1 | 4 – 10 Okt | Naskah, storyboard, style frame; aset scene 1 diverifikasi |
| 2–3 | 11 – 24 Okt | Aset bersama (ikan, karang, kapal selam), terrain |
| 4–5 | 25 Okt – 7 Nov | Blocking & animasi 4 scene (*animatic*) |
| 6 | 8 – 14 Nov | Boids, lighting final |
| 7 | 15 – 21 Nov | Render (cadangan waktu render) + rekam narasi |
| 8 | 22 – 29 Nov | Editing, audio, revisi, **kumpul 29 Nov** |

## Checklist
- [ ] Undi posisi A–H & isi kolom nama
- [x] Struktur folder `Project` + repo git ✅ 2026-10-04
- [ ] Galeri kandidat aset scene 1 → diverifikasi
- [x] Scene 1: pulau & Manado Tua, laut, langit, props, perahu + nelayan, kamera 4 shot ✅ 2026-10-12 (`blender/scene1.blend`); render penuh & polish aset menyusul
- [ ] Naskah narasi lengkap 4 scene (fakta terverifikasi)
- [ ] Scene 2, 3, 4
- [ ] Render, narasi, musik, editing, ekspor video final

## Pertanyaan terbuka

> [!question] Belum diputuskan
> - Format pengumpulan (MP4? unggah YouTube?) dan apakah ada presentasi di kelas.
> - Detail scene 2 & 3 (di-grill terpisah setelah scene 1).

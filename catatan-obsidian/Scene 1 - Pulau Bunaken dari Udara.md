---
status: In Progress
scene: 1
durasi: 40
pj: A, B
updated: 2026-10-04
tags:
  - project-animasi
  - scene
---

# Scene 1 — Pulau Bunaken dari Udara

Bagian dari [[Tugas Project Animasi]] · Narasi: [[Narasi & Storyboard#Scene 1]] · Aset: [[Aset & Teknik#Scene 1]]

> [!abstract] Konsep
> Pagi hari di Teluk Manado. Kamera terbang dari pandangan lebar Manado Tua & Bunaken, menyusuri pesisir desa, mengikuti perahu katinting nelayan yang berangkat, lalu menukik melewati garis *drop-off* hingga menyentuh permukaan air (→ *match cut* ke [[Scene 2 - Menyelam]]).

## Spesifikasi
- Durasi **40 s** = 960 frame @ 24 fps, 1920×1080, EEVEE
- Berkas: `Project/blender/scene1.blend` (aset di-link dari `aset.blend`)
- Gaya: low-poly flat-shaded, palet Bunaken
- Waktu: pagi / golden hour, matahari ±25–30°, cahaya hangat
- Skala dipadatkan (1 unit = 1 m; pulau ±¼ ukuran asli, Manado Tua didekatkan)

## Shot list

| Shot | Frame | Durasi | Isi | Kamera |
|---|---|---|---|---|
| 1 | 1–240 | 10 s | *Establishing*: Teluk Manado, kerucut Manado Tua menjulang, Bunaken di depannya, garis pantai Manado samar di kejauhan | Lebar, tinggi, *dolly* maju pelan |
| 2 | 241–528 | 12 s | *Flyover* pesisir: pantai pasir putih, kelapa, bakau, desa rumah panggung, dermaga, papan TN Bunaken | Terbang rendah menyusuri pantai |
| 3 | 529–768 | 10 s | Perahu katinting bercadik + nelayan meninggalkan dermaga (tarik tali mesin → duduk mengemudi) | *Follow* dari samping-belakang |
| 4 | 769–960 | 8 s | Kamera menukik melewati tepi *drop-off*: toska → biru tua; berhenti tepat di permukaan air | Menukik, akhir sejajar permukaan |

## Elemen

### Buatan sendiri
- [x] Pulau Bunaken (prosedural low-poly) + Manado Tua (kerucut) + siluet pesisir Manado ✅ (`skrip/scene1_lingkungan.py`)
- [x] Shader air low-poly bergelombang, transparan; *reef flat* toska + garis drop-off ✅
- [x] Terrain diwarnai per-ketinggian (vertex color): laut dalam → reef → pasir → hijau ✅
- [x] Langit gradasi pagi (Incoming.z) + matahari hangat ~26° ✅
- [x] Animasi perahu berangkat + nelayan berdiri di perahu + burung + awan + kamera 4 shot ✅ (`skrip/scene1_kamera.py`)
- [ ] Kamera akhir shot 4 disimpan ke `aset.blend` untuk awal scene 2 (match-cut)

> [!done] Status build Scene 1 (12 Okt)
> `blender/scene1.blend` jadi: lingkungan + 56 aset (link dari `aset.blend`) + 4 kamera beranimasi (960 frame @24fps, EEVEE 1080p). Render uji tiap shot di `render/scene1/test2_*.png`.
>
> **Belum / polish:** render animasi penuh belum dijalankan; modifikasi aset (cadik perahu, atap seng & tiang rumah, teks papan "TN Bunaken") dan penyeragaman palet belum; shot 4 bisa ditambah karang terlihat di bawah air.

### Aset publik (diverifikasi via galeri → lihat [[Aset & Teknik#Scene 1]])
- [x] Pohon kelapa — *Coconut Tree* (sujirour) ✅ diimpor
- [x] Bakau — *Mangrove Tree 2* (nigromancer) ✅ diimpor
- [x] Rumah panggung — *Fisherman's Hut* (mitia) ✅ diimpor; perlu tiang + atap seng
- [x] Papan / gapura — *Stylized wood signs* (Pasindu.Anjana) ✅ diimpor; perlu teks TN Bunaken
- [x] Perahu — *Canoe* (SkyeSladeUT) ✅ diimpor; perlu cadik + mesin katinting
- [x] Burung — *Seagull Animated* (Jamie McFarlane) ✅ diimpor, ber-rig
- [x] Dermaga — *Boardwalk* (Jacob Cherchio) ✅ diimpor (jetty bertiang + pagar)
- [x] Nelayan — *Farmer* (Quaternius) ✅ diimpor, ber-rig + bertopi, 24 animasi
- [x] Awan — **buatan sendiri** ✅ 3 variasi (`Aset_Awan`)

## Catatan teknis
- Detail tinggi hanya di jalur kamera shot 2–3; area jauh cukup siluet hijau.
- Semua aset publik: material ulang ke palet bersama + flat shading.

# Permintaan Visual — 14 Nov 2026

Daftar ini berasal dari brief lead setelah foto acuan dikirim. Urutan = prioritas
kerja. Semua dikerjakan lewat agent kategori; Director memilih skill per tugas.

| # | Permintaan | Acuan | Aset/File | Status |
|---|---|---|---|---|
| 1 | Desain ulang Nara | `storyboard/refs/ref-nara_v001.jpg` | `assets/char/nara_v002.blend` | ✅ 14 Nov (1,68 m, 27 mesh) |
| 2 | Model Pak Haris | `storyboard/refs/ref-haris_v001.png` | `assets/char/haris_v001.blend` | ✅ 14 Nov (1,70 m, 28 mesh) |
| 3 | Rig Nara lebih manusiawi (bukan tabung) | — | `assets/char/nara_rig_v002.blend` + `haris_rig_v001.blend` | 🔄 @technical (join mesh lalu automatic weights) |
| 4 | Crowd dermaga low-detail | `ref-crowd-dermaga_v001.jpg` + `mannequin.blend` | `assets/char/crowd.blend` | ⬜ |
| 5 | Peralatan snorkel (masker, snorkel, fin) | **foto belum diterima** | `assets/props/divegear.blend` | 🚫 blocked |
| 6 | Ikan cakalang didesain ulang | `ref-cakalang_v001.jpg` | `assets/env/reef.blend` (varian cakalang) | ⬜ |
| 7 | Scene 1 aerial: perbanyak pohon | `ref-bunaken-aerial_v001.jpg` | `surface-vegetation.blend` | ⬜ |
| 8 | Manado Tua lebih detail | `ref-bunaken-manado-tua_v001.png` | `assets/env/surface.blend` | ⬜ |
| 9 | Efek permukaan laut (bukan bidang datar) | — | `assets/look/scene-1-look.blend` | ⬜ @technical |
| 10 | Scene 1 bawah laut: perbanyak karang | `ref-reef-underwater_v001.jpg` | `assets/env/reef.blend` | ⬜ |
| 11 | Pulau: rumput + pohon lebih rapat | `ref-bunaken-aerial_v001.jpg` | `vegetation.blend` + `surface.blend` | ⬜ |
| 12 | Rumah kampung lebih detail | `ref-bunaken-aerial_v001.jpg` | `assets/env/surface.blend` | ⬜ |

## Catatan lisensi

- Foto crowd adalah stok iStock *editorial use only* → **tidak boleh** masuk film;
  hanya acuan komposisi. Alternatif: foto tim sendiri atau panel storyboard 1C.
- Foto cakalang belum jelas sumbernya; perlu klarifikasi sebelum publikasi.
- Foto Nara & Haris adalah foto pribadi yang diserahkan tim; dipakai sebagai
  acuan bentuk/warna saja, bukan tekstur.

## Dampak ke shot

- #1–#3 → render ulang shot Nara: S1 050/060/070/100, S2 050, S3 010/050/100,
  S4 080.
- #4 → membuka S1 090, S2 060/070/090, S3 030/040/070/080/090, S4 010/060.
- #5 → melengkapi S1 060/070 dan S3 010.
- #6–#12 → render ulang Scene 1 (dan sebagian Scene 4).

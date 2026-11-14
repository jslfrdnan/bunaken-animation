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
| 6 | Ikan cakalang didesain ulang | `ref-cakalang_v001.jpg` | `assets/env/fish-cakalang.blend` + `reef-dense_v003` (12 ekor berkelompok) | ✅ |
| 7 | Scene 1 aerial: perbanyak pohon | `ref-bunaken-aerial_v001.jpg` | `island-detail_v002` (350 kelapa, 150 pesisir skala besar) | ✅ |
| 8 | Manado Tua lebih detail | `ref-bunaken-manado-tua_v001.png` | `island-detail_v002` (ridge + 1.400 kartu vegetasi, 745 m) | ✅ |
| 9 | Efek permukaan laut (bukan bidang datar) | — | shader `SHD_water-surface_v002` + patch 200 m di shot 020/070 | ✅ |
| 10 | Scene 1 bawah laut: perbanyak karang | `ref-reef-underwater_v001.jpg` | `reef-dense_v003` (140 karang, 3 sekolah ikan, 600 lamun) | ✅ |
| 11 | Pulau: rumput + pohon lebih rapat | `ref-bunaken-aerial_v001.jpg` | `island-detail_v002` (3.000 rumput + 350 kelapa) | ✅ |
| 12 | Rumah kampung lebih detail | `ref-bunaken-aerial_v001.jpg` | `island-detail_v002` (12 rumah: tiang, jendela, teras, atap ridge) | ✅ |

Catatan: semua di atas sudah dipakai di **Scene 1** dan **Scene 2–4** (shot yang
menampilkan pulau, dermaga, kerumunan, atau ikan). Khusus Scene 2:

- **020** — ledakan **bawah laut**: kamera 6 m di bawah permukaan menunduk 12°
  (permukaan tidak terlihat), cincin tekanan, kilatan, 48 gelembung, puing,
  32 ikan ber-rig kabur, hamparan karang hancur.
- **030** — **jaring kubah** Ø6 m menyapu; 6 ikan tersangkut dan ikut jaring,
  10 menghindar; 4 karang berubah menjadi puing saat dilewati.
- **040/050** — `reef-wrecked` (15 klaster puing + 4 kerangka pucat).

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

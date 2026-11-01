---
tags: [produksi, storyboard, lembar, 2shot]
status: perlu-revisi
tanggal: 2026-11-02
prompt: docs/prompts-imagegen.md (prompt 00)
---

# Storyboard — Lembar 2 Shot per Scene (v001)

Lembar ringkas **8 panel** (4 scene × 2 shot) untuk membaca alur film dalam
satu gambar. Dipakai untuk rapat dan pengecekan alur, **bukan** acuan produksi
per shot — untuk Scene 1 yang detail tetap pakai
[[02-shotlist-scene-1]] dan frame per shot di `storyboard/frames/scene-1/`.

## File gambar

| Item | Nilai |
|---|---|
| Path | `storyboard/frames/storyboard-2shot-per-scene_v001.jpg` |
| Resolusi | 1792 × 2400 px (3:4), JPEG ±3 MB |
| Prompt | `docs/prompts-imagegen.md` — bagian **00** |
| Seed | `20261102` |
| Referensi | foto aerial Bunaken |
| Gaya | sketsa pensil hitam-putih (bukan look film) |
| Tanggal jadi | 2 Nov 2026 |

## Isi panel

| Panel | Scene | Isi gambar | Status |
|---|---|---|---|
| **1A** | 1 Permata | Aerial pulau, dermaga panjang, perahu, gunung di kiri | 🟨 gunung kurang menjulang |
| **1B** | 1 Permata | Penyelam di terumbu, penyu di kanan, god rays | ✅ sesuai setelah Nara ditetapkan perempuan |
| **2A** | 2 Retak | Perahu nelayan di air tenang, matahari terbit | 🟥 tidak ada percikan/gelembung bom |
| **2B** | 2 Retak | Nara di dermaga melihat lelaki bertopi naik perahu | 🟨 Haris tidak terbedakan |
| **3A** | 3 Titik Balik | Penyelam memotret karang rusak di bawah air | 🟨 jaring tidak terbaca |
| **3B** | 3 Titik Balik | Nara menunjukkan kertas ke lelaki berbaju putih | 🟨 Daniel & warga tidak ada |
| **4A** | 4 Warisan | Warga menurunkan pelampung tambat dari perahu | 🟨 kerangka karang tidak ada |
| **4B** | 4 Warisan | Nara di ujung dermaga membelakangi kamera, penyu di air | ✅ sesuai |

Urutan baca: kiri–kanan, baris atas (Scene 1) sampai baris bawah (Scene 4).

## Yang sudah bagus

- Grid 2×4 dan label `1A`–`4B` rapi dan terbaca.
- Gaya sketsa konsisten di 8 panel, tidak ada warna nyasar.
- Alur "indah → rusak → bukti → pulih" terbaca tanpa narasi.
- Panel 4B menutup dengan tepat: Nara membelakangi kamera, penyu kembali.

## Yang menyimpang dari sinopsis / tokoh

### 1. Nara perempuan — **sudah diputuskan (opsi B)**

Lead memutuskan **Nara adalah perempuan** pada 1 November 2026. Lembar ini
menggambar Nara sebagai perempuan bersanggul, dan itu sekarang **sesuai** dengan
[[03-tokoh]]. Tidak perlu generate ulang karena gender.

Konsekuensi yang sudah dijalankan:
- [[01-premis]], [[01-ringkasan]], [[02-sinopsis]], [[03-tokoh]] memakai "pemudi".
- [[02-kredit]] dan pengumuman WA ikut disesuaikan.
- Prompt 02 di `docs/prompts-imagegen.md` sekarang meminta *young woman* secara
  eksplisit, supaya frame berikutnya konsisten.

**Yang masih perlu dirapikan:** gaya rambut. Di lembar ini Nara bersanggul,
sedangkan [[03-tokoh]] menulis "rambut pendek hitam". Pilih salah satu —
ubah catatan tokoh jadi "rambut pendek atau diikat", atau minta frame baru
dengan rambut pendek. Tidak mendesak, tapi harus konsisten sebelum Scene 2.

### 2. Scene 2 kehilangan bukti bom

Panel 2A hanya perahu di matahari terbit. Tidak ada percikan dan gelembung
setelah ledakan, padahal itu satu-satunya petunjuk visual "bom ikan" sebelum
Nara menemukan karang hancur. Perahu juga digambar menghadap kamera dengan
banyak penumpang, padahal brief minta satu figur membelakangi kamera.

### 3. Haris tidak bisa dikenali

Di 2B dan 3B, penantang Nara digambar sebagai lelaki biasa tanpa ciri
[[03-tokoh]]: topi lusuh, kumis tipis, bekas luka di lengan kanan. Penonton
tidak akan mengingatnya sebagai orang yang sama di Scene 3–4.

### 4. Detail kecil

- 3B: "buku utang" terbaca sebagai lembar kertas; Pak Daniel dan warga yang
  menonton tidak ada, jadi tekanan sosialnya hilang.
- 4A: kerangka transplantasi karang tidak muncul; buoy terbaca seperti bola
  tambang, bukan pelampung tambat oranye.
- 2B: Nara membawa tas punggung — tidak ada di shot list, tapi masih masuk
  akal (niat pergi ke Manado). Boleh dipertahankan kalau disengaja.

## Keputusan yang menunggu

- [x] Nara: **opsi B — tokoh perempuan** (diputuskan 1 Nov 2026)
- [ ] Rambut Nara: sanggul (sesuai frame) atau pendek (sesuai `03-tokoh`)
- [ ] 2A: tambahkan percikan + gelembung bom, perahu jauh & membelakangi
- [ ] 2B/3B: beri ciri Haris yang khas agar konsisten antar scene
- [ ] 4A: tambahkan kerangka transplantasi karang
- [ ] Simpan PNG final ke path di atas, lalu update status di tabel panel

## Hubungan dengan dokumen lain

- Alur cerita: [[02-sinopsis]]
- Aturan shot & durasi: [[02-shotlist-scene-1]] · [[01-storyboard]]
- Gaya: [[03-gaya-visual]] (lembar ini sketsa, **bukan** look film)
- Prompt: [`docs/prompts-imagegen.md`](../../docs/prompts-imagegen.md) bagian 00

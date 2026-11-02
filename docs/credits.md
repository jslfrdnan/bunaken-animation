# Kredit, Lisensi & Sumber

Dokumen ini wajib diperbarui **setiap kali** ada aset dari luar yang dipakai,
atau klaim faktual baru yang masuk ke narasi.

## 1. Tingkat kredit

Dibagi **di awal**, bukan di akhir, supaya semua orang tahu apa yang harus
mereka selesaikan.

| Tingkat | Syarat | Ditulis sebagai |
|---|---|---|
| **Core** | Minimal 1 scene penuh atau peran kunci sampai selesai | Nama besar di credit, urutan utama |
| **Contributor** | Sebagian tugas, tenggat terpenuhi | Nama di credit, ukuran sedang |
| **Support** | Kontribusi kecil / membantu sesekali / tugas tidak selesai | Nama di credit penutup, ukuran kecil |

Aturan:

- Menyelesaikan tugas **setelah** dipindah ke orang lain → tetap **Support**.
- Anggota yang tidak pernah muncul dan tidak pernah kabar → **tidak masuk credit**.
- Keputusan akhir tingkat kredit oleh lead, diumumkan sebelum render final.

## 2. Format credit film

```
WARISAN BUNAKEN

Sebuah animasi oleh [Nama Kelompok]
[Program Studi / Mata Kuliah] — [Universitas] — 2026

SUTRADARA            Jasiel Wowiling
STORYBOARD           Excel Katuuk
ENVIRONMENT          Jasiel Wowiling
KARAKTER             Yehezkiel Montolalu
RIGGING & ANIMASI    [nama]
LIGHTING & SHADING   Vaughn Toy
AUDIO, EDIT & DOKUM. [nama], Jasiel Wowiling

NARASI               [nama pengisi suara]

ASET PIHAK KETIGA
[daftar]

Cerita ini fiksi. Tokoh dan peristiwa tidak merujuk pada
individu atau kelompok nyata.

Terima kasih kepada Balai Taman Nasional Bunaken
dan warga Bunaken.
```

Nama yang masih `[nama]` diisi lead sebelum render final.

## 3. Aset pihak ketiga — WAJIB diisi

Setiap file dari luar (model, tekstur, HDRI, musik, SFX) masuk tabel ini
**sebelum** dipakai di scene.

| Aset | Pembuat | Lisensi | Tautan | Dipakai di |
|---|---|---|---|---|
| _contoh: HDRI tropis_ | _Poly Haven_ | _CC0_ | _url_ | _Scene 1_ |

### Foto acuan (referensi internal, bukan aset film)

| File | Sumber | Lisensi | Status |
|---|---|---|---|
| `storyboard/refs/ref-bunaken-aerial_v001.jpg` | internet, sumber tidak tercatat | **tidak diketahui** | acuan bentuk saja — **tidak masuk film** |
| `storyboard/refs/ref-reef-underwater_v001.jpg` | internet, sumber tidak tercatat | **tidak diketahui** | acuan bentuk & warna — **tidak masuk film** |

> ⚠️ Kedua foto ini **melanggar aturan lisensi di tabel bawah** (tidak ada
> lisensi jelas). Lead memutuskan tetap menyimpannya karena dibutuhkan seluruh
> tim sebagai acuan bentuk dan warna. Batasnya: **hanya untuk melihat, tidak
> pernah dipakai sebagai tekstur, latar, atau bagian dari film**, dan tidak
> dipublikasikan di luar repo. Kalau nanti perlu dipamerkan ke publik, ganti
> dengan foto milik sendiri atau berlisensi CC0.

### Aset 3D yang dibuat sendiri

Semua model di `assets/env/reef.blend`, `assets/env/surface.blend`, dan
`assets/props/boats.blend` adalah **geometri prosedural yang dibuat di Blender
untuk proyek ini**, atas arahan Jasiel Wowiling. Tidak ada model pihak ketiga di
dalamnya. Tidak perlu kredit eksternal.

### Aturan lisensi

| Lisensi | Boleh dipakai? | Kewajiban |
|---|---|---|
| **CC0** | Ya | Kredit opsional, tetap dicatat di sini |
| **CC-BY** | Ya | **Wajib** sebut nama pembuat di credit film |
| **CC-BY-SA** | Sebaiknya tidak | Kredit + seluruh film harus lisensi sama |
| **Non-commercial** | Hati-hati | Jangan dipakai kalau film bisa masuk lomba berbayar |
| **Tanpa lisensi jelas** | **Tidak** | Jangan dipakai sama sekali |

Kandidat sumber: **Poly Haven** (HDRI, tekstur — CC0), **Poly Pizza** (low-poly
— CC-BY), **Sketchfab** (cek lisensi per model), **Freesound** (cek lisensi per
file). Musik cari CC0/CC-BY.

## 4. Referensi yang tidak masuk film

Foto aerial Bunaken yang dipakai sebagai acuan prompt Gemini **tidak** masuk ke
film selama bukan milik sendiri. Kalau itu foto milik sendiri, catat di tabel §3
sebagai referensi internal.

## 5. Data & fakta — sumber

Setiap angka atau klaim faktual di narasi harus punya baris di sini.

| Klaim | Sumber | Tanggal cek |
|---|---|---|
| Ditetapkan 1991, SK Menhut No. 730/Kpts-II/91 | Arsip Dephut, "Bunaken National Park" (Wayback Machine, capture 10 Feb 2010) | 1 Nov 2026 |
| Luas 89.065 ha (97% laut, 3% darat) | Arsip Dephut, halaman yang sama | 1 Nov 2026 |
| Lima pulau: Bunaken, Manado Tua, Mantehage, Nain, Siladen | Arsip Dephut + UNESCO Tentative List No. 2002 | 1 Nov 2026 |
| 390 spesies karang | E. Turak & L. DeVantier, *Reef-building corals of Bunaken National Park* | 1 Nov 2026 |
| 91 spesies ikan | Arsip Dephut, halaman yang sama | 1 Nov 2026 |
| Kedalaman laut 200–1.840 m; Manado Tua >600 m | UNESCO Tentative List No. 2002 | 1 Nov 2026 |
| ±35.000 penduduk di 22 desa | Arsip Dephut + WWF Bunaken fact sheet | 1 Nov 2026 |
| Daftar tentatif UNESCO sejak 2005, belum terdaftar | UNESCO Tentative List No. 2002 | 1 Nov 2026 |

Tautan:

- Arsip Dephut — <https://web.archive.org/web/20100210172459/http://www.dephut.go.id/INFORMASI/TN%20INDO-ENGLISH/bunaken_NP.htm>
- UNESCO — <https://whc.unesco.org/en/tentativelists/2002/>
- Laporan karang Turak & DeVantier — <http://www.bunaken.org/download/Turak%20DeVantier%20IOI%20Bunaken%20Coral%20Report.pdf>

> **Catatan produksi:** film hanya memodelkan **3 jenis karang** (meja,
> bercabang, massif) dan **4 jenis ikan** (cakalang, hiu, goropa merah, kakatua),
> bukan 390 dan 91. Itu penyederhanaan produksi, bukan klaim bahwa Bunaken hanya
> punya 3 jenis karang. Jangan pernah menarasikan angka 3 atau 4.

## 6. Yang masih kosong

- [ ] Nama kelompok
- [ ] Program studi / universitas
- [ ] Nama peran 6, 8
- [ ] Nama pengisi suara narasi
- [ ] Daftar aset pihak ketiga (§3) — diisi saat aset mulai diambil

# AGENTS.md — Aturan Kerja AI untuk Proyek Warisan Bunaken

Dokumen ini mengikat **setiap sesi AI** (OpenCode, Claude, atau agent lain) yang
 bekerja pada repository ini. Baca ini **sebelum** melakukan apa pun.

---

## 1. Langkah pertama setiap sesi: baca dokumen proyek

**Wajib, tanpa pengecualian.** Sebelum menjawab, sebelum menulis kode, sebelum
membuka Blender:

1. Baca `PROJECT.md` sampai habis — itu satu-satunya sumber kebenaran proyek:
   cerita, tokoh, palette, spesifikasi teknis, shot list, daftar aset, peran,
   tenggat, kredit, dan alur git semuanya ada di sana.
2. Baca `CONTRIBUTING.md` dan `docs/renders.md`.
3. Baru setelah itu kerjakan permintaan pengguna.

Alasan: keputusan cerita, palette, nama tokoh, jadwal, dan aturan file sudah
dikunci di `PROJECT.md`. Bekerja tanpa membacanya berisiko menghasilkan aset yang
bertentangan dengan yang sudah disepakati tim.

`PROJECT.md` cukup panjang. Kalau perlu, gunakan `grep`/pencarian, tapi **jangan
lewati** §1 (Cerita), §2 (Gaya visual), §3 (Spesifikasi teknis), dan §8
(Pipeline Blender).

Catatan: lead masih menyimpan vault Obsidian pribadi di `Obsidian-Project-Animasi/`
di laptopnya. Folder itu **tidak ada di repo** dan bukan acuan kerja tim. Kalau
folder itu kebetulan ada di mesinmu, jangan jadikan sumber keputusan — pakai
`PROJECT.md`.

Jika ada pertentangan antara `PROJECT.md` dan permintaan terbaru pengguna:
**permintaan pengguna menang**, tapi AI wajib (a) menyebut pertentangannya,
(b) memperbarui `PROJECT.md` yang terkait setelah disetujui.

---

## 2. Protokol pembuatan aset model dengan AI

Berlaku untuk **semua** permintaan membuat aset 3D (karakter, environment, props),
baik lewat Blender MCP maupun saran modeling manual.

### 2.1 Wajib minta gambar referensi lebih dulu

AI **tidak boleh** langsung memodelkan dari deskripsi teks. Langkah wajib:

1. Minta **gambar referensi** dari pengguna.
2. Gambar itu dipakai untuk **dua hal sekaligus**:
   - **acuan bentuk** (proporsi, siluet, detail struktural) → modeling
   - **acuan warna & material** (shading, tekstur, roughness) → shading
3. Jika pengguna mengirim lebih dari satu gambar, tanyakan mana acuan **bentuk**
   dan mana acuan **warna/material**.
4. Sebutkan sumber & lisensi gambar di `docs/credits.md` sebelum aset dipakai
   di film.

### 2.2 Kalau gambar tidak jelas atau kurang bagus

AI **wajib memberi keterangan** apa yang kurang, lalu meminta gambar ulang.
Jangan memaksakan modeling dari gambar yang buruk — hasilnya akan dibuang.

Periksa minimal enam hal ini:

| Aspek | Gambar yang baik | Masalah yang harus disebutkan |
|---|---|---|
| **Sudut** | Tampak depan, samping, dan atas (atau 3/4 yang jelas) | Hanya ada satu sudut miring, detail belakang tidak terlihat |
| **Pencahayaan** | Merata, tanpa bayangan keras | Backlight, gelap, wajah/objek setengah tersembunyi |
| **Ketajaman** | Fokus tajam, resolusi cukup (≥1000 px sisi terpanjang) | Blur, noise, jpeg artifact, hasil screenshot kecil |
| **Latar** | Polos/kontras dengan objek | Latar ramai sehingga siluet objek tidak terbaca |
| **Oklusi** | Objek tidak tertutup apa pun | Tertutup tangan, tanaman, air, atau objek lain |
| **Skala & proporsi** | Ada acuan ukuran atau proporsi jelas | Tidak jelas besar kecilnya, perspektif ekstrem |

Format umpan balik yang harus dipakai AI:

```
Gambar ini belum cukup untuk modeling karena:
- <alasan 1>
- <alasan 2>

Mohon kirim ulang dengan:
1. <instruksi konkret>
2. <instruksi konkret>

Contoh gambar yang ideal: <deskripsi singkat / daftar shot>
```

### 2.3 Daftar gambar ideal per jenis aset

| Aset | Gambar minimum |
|---|---|
| Karakter | Character sheet: depan, 3/4, samping, ditambah close-up wajah |
| Props kecil | 1 foto dari sudut jelas + 1 tampak atas |
| Environment/bangunan | 3 sudut berbeda + satu wide shot keseluruhan |
| Tekstur | Foto close-up tegak lurus permukaan, pencahayaan merata, tanpa bayangan |

### 2.4 Setelah aset jadi

- Simpan di folder departemen yang benar (`assets/env/`, `assets/char/`, …).
- Ikuti konvensi nama di `PROJECT.md` §6.
- Jangan pack tekstur ke `.blend`.
- Render preview dan laporkan hasilnya ke pengguna.

---

## 3. Konvensi pesan commit

Gunakan **Conventional Commits** yang ringkas dan jelas. Format:

```
<type>(<scope>): <subject>

<body — jelaskan MENGAPA, bukan sekadar apa>

Refs: <opsional>
```

### Type yang dipakai

| Type | Untuk |
|---|---|
| `feat` | Fitur/aset baru yang bisa dipakai |
| `fix` | Perbaikan kesalahan |
| `docs` | Perubahan dokumentasi/vault |
| `asset` | Penambahan atau penggantian aset biner (model, tekstur, audio) |
| `scene` | Perubahan pada file scene (`scenes/*.blend`) |
| `refactor` | Rapi-rapi tanpa mengubah hasil |
| `chore` | Konfigurasi, `.gitignore`, tooling |
| `build` | Setup build/render |

### Scope yang dipakai

`scene-1` … `scene-4`, `char`, `env`, `props`, `audio`, `docs`, `repo`, `storyboard`

### Aturan penulisan

1. **Subject**: huruf kecil, kata kerja imperatif, tanpa titik di akhir, ≤72 karakter.
2. **Body**: jelaskan alasan perubahan, bungkus di 72 kolom.
3. Satu commit = satu perubahan logis.
4. Bahasa Indonesia boleh, konsisten dalam satu commit.

### Contoh benar

```
feat(char): tambah model nara v001 dari character sheet

Model dibuat dari referensi character sheet yang disetujui di vault.
Proporsi mengikuti gambar depan dan samping; warna rash guard memakai
palette teal #1FA3A3 agar konsisten dengan look dev Scene 1.
```

```
docs(vault): kunci jadwal animatic kasar ke 2 november

Target 6 november dinilai terlalu agresif, jadi ditambahkan tanggal
fallback 13 november tanpa perlu rapat darurat.
```

```
asset(env): tambah tekstur pasir 2k dari poly haven

Lisensi CC0, dicatat di docs/credits.md.
```

### Contoh salah (jangan)

```
update
fix
asdf
final beneran
update file
banyak perubahan
```

Sebelum commit, AI **wajib**:
- menjalankan `git status` dan memastikan tidak ada file yang tidak seharusnya masuk
- memastikan tidak ada `renders/`, `*.blend1`, atau file >50 MB
- melaporkan isi commit ke pengguna

---

## 4. Aturan teknis proyek (ringkas)

- Blender **5.2 LTS**, **EEVEE Next**, 1920×1080, **24 fps**.
- Git: kerja lewat **Pull Request** ke `main`, **tanpa Git LFS**.
- **Satu file `.blend` = satu pemilik**; master hanya *link/append*.
- **Jangan pack tekstur**; tekstur di `assets/textures/` dengan path relatif.
- **Render/video tidak masuk git** → `docs/renders.md`.
- Palette & aturan warna: `PROJECT.md` §2.
- Nama file: `scene-1_shot-010_nara-dive_v001.blend`.

## 5. Batas kemampuan AI

AI bisa: aset prosedural (terumbu, karang, batu, pulau, perahu, jaring, ikan
sederhana), shader air/pasir, lighting, kamera, render previz, blockout karakter,
dokumentasi, dan review.

AI **tidak** bisa: sculpt detail, rigging halus, tekstur hand-painted produksi.
Untuk hal-hal itu, AI menulis panduan langkah-demi-langkah untuk tim.

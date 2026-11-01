# Aturan Kontribusi

Dokumen ini mengikat. Kalau ragu, tanya lead sebelum commit.

## 1. Alur git: kerja lewat Pull Request

Tim **tidak push langsung ke `main`**. `main` dilindungi: setiap perubahan masuk
lewat **Pull Request (PR)** dan di-merge oleh lead.

```bash
git switch main
git pull                        # WAJIB sebelum mulai kerja
git switch -c kerjaku           # branch baru per perubahan
# ...kerja...
git add .
git commit -m "feat(scene-1): blockout terumbu"
git push -u origin kerjaku      # push branch, bukan main
```

Lalu buka PR di GitHub → `base: main`, `compare: kerjaku` → tunggu review lead.
Setelah di-merge, hapus branch dan kembali ke `main`.

Aturan pendukung:

- **Satu PR = satu perubahan yang bisa dijelaskan.** Jangan gabung 5 topik.
- Branch hanya hidup selama PR-nya belum di-merge. Setelah merge, hapus.
- Jangan pernah `git push --force` ke branch yang sudah ada PR-nya.
- Jangan commit file kerja sementara (`.blend1`, cache, `__pycache__`).

## 2. Satu file `.blend` = satu pemilik

File biner tidak bisa di-merge. Dua orang menyimpan file `.blend` yang sama berarti
pekerjaan salah satu orang **hilang**. Karena itu:

- Setiap file `.blend` punya **satu pemilik** yang tercatat di tabel peran &
  aset `PROJECT.md` §5 dan §9.
- `scenes/scene-1.blend` adalah **master** milik lead. Isinya hanya *link/append*
  dari file departemen, bukan aset yang digambar langsung di sana.
- File departemen: `assets/env/reef.blend`, `assets/env/surface.blend`,
  `assets/char/nara.blend`, dst.

## 3. Ukuran dan isi file

Tanpa Git LFS, batas keras GitHub adalah **file >100 MB ditolak**. Maka:

- `.blend` **tidak boleh** menyimpan tekstur (*File → External Data → tidak dipack*).
  Tekstur disimpan di `assets/textures/` dan direferensikan dengan **path relatif**.
- `.blend` dijaga **di bawah ±50 MB**.
- **Render, video, dan animatic tidak masuk git.** Lihat `docs/renders.md`.
- `.blend1` (backup otomatis Blender) diabaikan `.gitignore`.

## 4. Konvensi penamaan

Lihat `PROJECT.md` §6 (Struktur repo & penamaan).

Ringkas: `scene-1_shot-010_nara-dive_v001.blend`

## 5. Pesan commit

Format **Conventional Commits** (lengkap di `AGENTS.md` bagian 3):

```
<type>(<scope>): <subject>

<body — jelaskan MENGAPA, bukan sekadar apa>
```

```
feat(char): tambah model nara v001 dari character sheet
asset(env): tambah tekstur pasir 2k dari poly haven
docs(vault): kunci jadwal animatic kasar ke 2 november
```

Type: `feat`, `fix`, `docs`, `asset`, `scene`, `refactor`, `chore`, `build`.
Scope: `scene-1`…`scene-4`, `char`, `env`, `props`, `audio`, `docs`, `repo`,
`storyboard`.

## 6. Tenggat dan kredit

- Setiap tugas di board punya **pemilik + tenggat**.
- **Lewat 2 tenggat tanpa kabar** → tugas otomatis dipindah ke lead.
- Kredit tiga tingkat: **Core**, **Contributor**, **Support**. Rincian di
  `docs/credits.md`.

## 7. Aset pihak ketiga

Semua aset eksternal (Poly Haven, Sketchfab, Poly Pizza, tekstur, musik) wajib
dicatat di `docs/credits.md`: sumber, lisensi, tautan, dan nama pembuat.
Aset CC-BY wajib dikreditkan di credit film.

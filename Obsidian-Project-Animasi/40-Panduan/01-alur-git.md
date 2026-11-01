---
tags: [panduan, git]
---

# Alur Git (Pull Request, tanpa LFS)

`main` adalah cabang produksi. **Tidak ada yang push langsung ke `main`.**
Setiap perubahan masuk lewat **Pull Request** dan di-merge oleh lead.

## Untuk yang baru pertama kali memakai git

### Sekali saja (setup)

```bash
git clone https://github.com/jslfrdnan/bunaken-animation.git
cd bunaken-animation
git config user.name "Nama Kamu"
git config user.email "email-kamu@contoh.com"
```

> Email **harus** email akun GitHub-mu, supaya commit dihitung sebagai
> kontribusimu.

### Setiap kali mau kerja

```bash
git switch main
git pull
git switch -c kerjaku
```

Branch bisa dinamai bebas: `blockout-terumbu`, `model-nara`, `narasi-scene-1`.
Satu branch = satu pekerjaan.

### Setelah selesai kerja

```bash
git add .
git commit -m "feat(scene-1): blockout terumbu"
git push -u origin kerjaku
```

Lalu di GitHub:

1. Buka repo → akan muncul tombol **Compare & pull request**.
2. Pastikan `base: main` ← `compare: kerjaku`.
3. Tulis judul singkat + apa yang berubah.
4. **Create pull request** → tunggu lead review.
5. Setelah di-merge, klik **Delete branch**, lalu:

```bash
git switch main
git pull
git branch -d kerjaku
```

## Kalau PR-mu ketinggalan dari `main`

GitHub akan bilang "This branch is out-of-date". Perbaiki dengan:

```bash
git switch main
git pull
git switch kerjaku
git merge main
# selesaikan konflik kalau ada
git push
```

PR otomatis ter-update. Jangan push ulang ke `main`.

## Tiga aturan yang mencegah bencana

1. **Satu file `.blend` = satu pemilik.** Daftar pemilik ada di [[04-tugas-scene-1]].
   Jangan buka file `.blend` orang lain untuk diedit. Kalau perlu asetnya, minta
   pemiliknya mengekspor atau gunakan *link/append*.
2. **`git pull` sebelum kerja.** 90% konflik di project kelompok terjadi karena
   orang lupa pull.
3. **Jangan commit render.** `.gitignore` sudah menolak `renders/`, `*.mp4`,
   `*.exr`. Simpan di Google Drive atau GitHub Releases, catat di
   `docs/renders.md`.

## Tanpa Git LFS — konsekuensinya

- File **>100 MB ditolak** GitHub.
- Repo di atas ±1 GB mulai bermasalah (clone lambat).
- Karena itu: **jangan pack tekstur** di `.blend` (*File → External Data →
  jangan centang Automatically Pack Resources*). Simpan tekstur di
  `assets/textures/` dengan path relatif.
- Jaga `.blend` di bawah ±50 MB.

## Kalau tidak sengaja rusak

```bash
git status              # lihat apa yang berubah
git restore nama-file   # batalkan perubahan satu file
git log --oneline -5    # lihat commit terakhir
```

Jangan pernah `git reset --hard` atau `git push --force` tanpa bertanya ke lead.
Kalau branch-mu kacau, lebih aman buat branch baru daripada memperbaiki history.

## Branch

Branch **wajib** untuk setiap pekerjaan yang akan di-PR. Branch eksperimen yang
tidak jadi dipakai cukup dihapus, tidak perlu di-merge.

```bash
git switch -c eksperimen-air
# kerja...
# kalau gagal:
git switch main
git branch -D eksperimen-air
```

## Commit message

Pakai **Conventional Commits** (`AGENTS.md` bagian 3):

```
<type>(<scope>): <subject>

feat(char): tambah model nara v001 dari character sheet
scene(scene-1): blockout terumbu dan karang
docs(vault): jadwal minggu 1
asset(audio): narasi sementara 35 detik
fix(env): perbaiki path tekstur
```

Type: `feat`, `fix`, `docs`, `asset`, `scene`, `refactor`, `chore`, `build`.
Scope: `scene-1`…`scene-4`, `char`, `env`, `props`, `audio`, `docs`, `repo`,
`storyboard`. Subject huruf kecil, imperatif, tanpa titik di akhir.

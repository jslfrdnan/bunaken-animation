---
tags: [panduan, git]
---

# Alur Git (main-only, tanpa LFS)

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
git pull
```

Ini mengambil perubahan terbaru. **Jangan pernah mulai kerja tanpa ini.**

### Setelah selesai kerja

```bash
git add .
git commit -m "feat(scene-1): blockout terumbu"
git pull --rebase
git push
```

Kalau `git pull --rebase` memunculkan konflik:
1. Buka file yang konflik, cari tanda `<<<<<<<`.
2. Pilih versi yang benar, hapus tanda-tandanya.
3. `git add .` lalu `git rebase --continue`.

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

Jangan pernah `git reset --hard` tanpa bertanya ke lead.

## Branch (hanya kalau perlu)

```bash
git switch -c eksperimen-air
# kerja...
git switch main
```

Branch untuk hal yang **boleh gagal**. Pekerjaan utama tetap di `main`.

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

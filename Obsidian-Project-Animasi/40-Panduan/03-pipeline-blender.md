---
tags: [panduan, blender, pipeline]
---

# Pipeline Blender

## Struktur file

```
scenes/scene-1.blend          <- MASTER, hanya link/append, milik lead
assets/env/reef.blend         <- milik Env Artist Underwater
assets/env/surface.blend      <- milik Env Artist Surface
assets/char/nara.blend        <- milik Character Artist
assets/char/daniel.blend      <- milik Character Artist (Scene 1, shot 080)
assets/char/nara_rig.blend    <- milik Rigger
assets/look/scene-1-look.blend <- milik Lighting
```

**Aturan emas:** aset selalu dibuat di file departemennya, lalu **di-link** ke
master. Jangan pernah menggambar aset langsung di `scene-1.blend` — file itu akan
bentrok dengan semua orang.

## Cara link aset ke master

1. Buka `scenes/scene-1.blend`.
2. `File → Link…` (bukan Append, kalau masih akan diedit pemiliknya).
3. Pilih file aset → Collection → `Link`.
4. Aset muncul sebagai *library*; perubahan di file aset otomatis terlihat.

Untuk aset yang sudah final dan tidak akan diubah: `Append`.

## Setup dasar proyek

```
Render Engine : EEVEE Next
Resolution    : 1920 x 1080
Frame Rate    : 24 fps
Color Mgmt    : Standard (bukan AgX) untuk konsistensi warna palette
Output        : PNG RGBA untuk still, FFmpeg MP4 untuk animasi
```

Semua pengaturan ini **wajib** sama di setiap file. Salin dari
`assets/look/scene-1-look.blend`.

## Jangan pack tekstur

*File → External Data → Automatically Pack Resources* → **matikan**.

Tekstur disimpan di `assets/textures/`, direferensikan dengan path **relatif**.
Alasannya: tanpa Git LFS, `.blend` yang dipack akan jadi puluhan MB dan repo
membengkak.

## Sebelum commit file `.blend`

- [ ] Tekstur tidak dipack
- [ ] Ukuran file <50 MB
- [ ] Hapus objek percobaan
- [ ] Nama objek mengikuti konvensi `ENV_` / `CHR_` / `PRP_`
- [ ] Simpan di frame 1
- [ ] File bisa dibuka tanpa error di komputer lain (uji kalau ragu)

## Alur per shot (Scene 1)

1. **Shot list** disetujui (lead).
2. **Blockout** — primitif, tanpa tekstur, kamera sudah benar. Ini yang dipakai
   untuk animatic 2 November.
3. **Modeling** — aset departemen diganti model sebenarnya.
4. **Rigging** — Nara di-rig, uji 2 pose.
5. **Animasi** — per shot, 24 fps.
6. **Lighting & shading** — look dev final.
7. **Render** — MP4, upload ke Releases.

## Bantuan AI (Blender MCP)

Aset prosedural yang bisa dibantu: terumbu, karang, batu, pulau, perahu, jaring,
ikan sederhana, shader air/pasir/karang, lighting, kamera, render previz, dan
blockout karakter.

Yang **tidak** bisa: sculpt detail, rigging halus, tekstur hand-painted.

## Masalah umum

| Masalah | Solusi |
|---|---|
| Tekstur hilang di komputer lain | path relatif, jangan pack, simpan tekstur di `assets/textures/` |
| File `.blend` 200 MB | matikan pack, hapus objek tak terpakai (`File → Clean Up → Unused Data`) |
| Render terlalu lama | turunkan sample EEVEE, kurangi volumetrik, cek jumlah partikel |
| Warna beda antar orang | pakai Color Management yang sama, jangan ubah view transform |

---
tags: [aset, daftar]
---

# Daftar Aset

Status: ⬜ belum · 🟨 proses · ✅ selesai · 🚫 dibatalkan

## Environment

| Aset | File | Pemilik | Scene | Status |
|---|---|---|---|---|
| Terumbu karang + karang rusak | `assets/env/reef.blend` | Anggota 3 | 1, 2, 4 | ⬜ |
| Permukaan: pulau, dermaga, kampung | `assets/env/surface.blend` | Anggota 4 | 1, 4 | ⬜ |
| Dive shop | `assets/env/surface.blend` | Anggota 4 | 1 | ⬜ |
| Perahu kecil + speedboat | `assets/props/boats.blend` | Anggota 4 | 1, 2 | ⬜ |
| Mooring buoy | `assets/props/` | Anggota 4 | 4 | ⬜ |
| Kerangka transplantasi karang | `assets/props/` | Anggota 3 | 4 | ⬜ |
| Ikan (3 jenis) + penyu | `assets/env/reef.blend` | Anggota 3 | 1, 4 | ⬜ |
| Jaring & alat tangkap | `assets/props/` | Anggota 4 | 1, 2 | ⬜ |

## Karakter

| Aset | File | Pemilik | Scene | Status |
|---|---|---|---|---|
| Nara (model) | `assets/char/nara.blend` | Yehezkiel Montolalu | **1**, 2, 3, 4 | 🟨 |
| Nara (rig) | `assets/char/nara_rig.blend` | Anggota 6 | **1**, 2, 3, 4 | ⬜ |
| Pak Daniel | `assets/char/daniel.blend` | Yehezkiel Montolalu | **1**, 2, 3, 4 | 🟨 |
| Pak Haris | `assets/char/haris.blend` | Yehezkiel Montolalu | 2, 3, 4 | ⬜ |
| Warga & anak-anak (low detail) | `assets/char/crowd.blend` | Yehezkiel Montolalu | 2, 3, 4 | ⬜ |
| Peralatan selam (masker, tabung, fin) | `assets/props/divegear.blend` | Yehezkiel Montolalu | **1**, 3 | ⬜ |

> **Scene 1 hanya butuh aset bertanda tebal:** `nara.blend`, `nara_rig.blend`,
> `daniel.blend`, dan `divegear.blend`. Pak Daniel wajib muncul di shot 080.
> Sisa aset karakter baru dipakai Scene 2–4 — jangan dikerjakan lebih dulu.
>
> `nara.blend` dan `daniel.blend` sudah masuk repo (commit `2b7f4a5` dan
> `07cd7ce`, 1 Nov). Statusnya 🟨 karena belum direview lead, bukan karena
> belum dibuat.

## Look & lighting

| Aset | File | Pemilik | Status |
|---|---|---|---|
| World HDRI + warna air | `assets/look/scene-1-look.blend` | Anggota 7 | ⬜ |
| Shader karang, pasir, air | `assets/look/` | Anggota 7 | ⬜ |

## Audio

| Aset | File | Pemilik | Status |
|---|---|---|---|
| Narasi 35 detik (sementara) | `assets/audio/scene-1/narasi-temp.wav` | Anggota 8 | ⬜ |
| Narasi final | `assets/audio/scene-1/narasi_v001.wav` | Anggota 8 | ⬜ |
| Ambient bawah laut | `assets/audio/scene-1/ambience.wav` | Anggota 8 | ⬜ |
| Musik tema | `assets/audio/scene-1/music.wav` | Anggota 8 | ⬜ |
| SFX bom (diredam) | `assets/audio/scene-1/sfx-bomb.wav` | Anggota 8 | ⬜ |

## Aset pihak ketiga

Kandidat sumber (semua **wajib** dicatat di [[02-kredit]] sebelum dipakai):

- **Poly Haven** — HDRI langit tropis, tekstur pasir/kayu/batu (CC0)
- **Poly Pizza** — model low-poly perahu, ikan (CC-BY, kredit wajib)
- **Sketchfab** — model terumbu/perahu realistis (cek lisensi per model)
- **Freesound** — ambient & SFX (cek lisensi per file)
- **Musik** — cari CC-BY/CC0, hindari lagu berhak cipta

## Yang saya (AI) bisa bantu buat

Lewat Blender MCP: terumbu prosedural, karang, batu, pulau, perahu, jaring,
ikan sederhana, shader air, lighting, kamera, render previz, blockout karakter.
**Tidak bisa:** sculpt detail, rigging halus, tekstur hand-painted.

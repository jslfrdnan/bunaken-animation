---
status: Draft
pj: A
updated: 2026-10-04
tags:
  - project-animasi
  - aset
---

# Aset & Teknik

Bagian dari [[Tugas Project Animasi]]

## Aturan aset
- **Aset publik** hanya untuk props; lisensi **CC0** atau **CC-BY** (kredit wajib untuk CC-BY).
- Sumber: **Sketchfab** (integrasi add-on MCP aktif); **Poly Pizza** dicari via browser lalu diunduh manual ke `Project/aset/unduhan/`. Poly Haven untuk HDRI/tekstur bila perlu.
- Alur: galeri kandidat (2–3 per aset) → pengguna memilih → impor ke `Project/blender/aset.blend` → screenshot konfirmasi.
- Penyeragaman: material ulang ke **palet bersama**, flat shading, decimate bila terlalu detail.
- Aset yang tidak tersedia (katinting bercadik, rumah panggung beratap seng): ambil yang terdekat, lalu **dimodifikasi sendiri**.

## Palet bersama (draf)

| Nama | Hex | Dipakai untuk |
|---|---|---|
| Pasir | `#E8D9B0` | Pantai, dasar dangkal |
| Hijau daun | `#4E8A3E` | Kelapa, hutan |
| Hijau tua | `#2F5D34` | Bakau, siluet jauh |
| Toska dangkal | `#3FC1C0` | Reef flat |
| Biru dalam | `#123C78` | Drop-off, laut dalam |
| Kayu | `#8A5A36` | Rumah, dermaga, perahu |
| Seng | `#9AA3A8` | Atap |
| Jingga cakalang | `#E8792B` | Aksen (sama dengan e-book) |
| Langit pagi atas → horizon | `#6FA8DC` → `#F6C98B` | Gradasi langit |

## Scene 1

Galeri verifikasi: https://claude.ai/artifact/82PCzwW8eoJLWehNcxnB46 (dibuat dengan `skrip/cari_aset_sketchfab.py` + `skrip/galeri_aset.py`)

| Aset | Sumber | Pembuat | Lisensi | Status |
|---|---|---|---|---|
| Pohon kelapa | [Coconut Tree](https://sketchfab.com/3d-models/d141941578044b0f861ca83b36d4c411) (Sketchfab) | sujirour | CC-BY | ✅ diimpor (`Aset_Kelapa`) |
| Bakau | [Mangrove Tree 2](https://sketchfab.com/3d-models/4ff47dd59bd7404888545e6780cdce46) (Sketchfab) | nigromancer | CC-BY | ✅ diimpor (`Aset_Bakau`) |
| Rumah panggung | [Low Poly Fisherman's Hut](https://sketchfab.com/3d-models/0bdd5a0dc02c429b9308d9fe06bca56a) (Sketchfab) | mitia | CC-BY | ✅ diimpor + **dipoles**: diangkat 1,6 m + 5 tiang kayu, atap seng, dinding kayu (`skrip/poles_aset.py`) |
| Dermaga kayu | [Boardwalk](https://poly.pizza/m/8gIutJpPSaS) (Poly Pizza) | Jacob Cherchio | CC-BY | ✅ diimpor (`Aset_Dermaga`, di-join 1 mesh, 8 m); jetty bertiang + pagar + tiang lampu; perlu warnai ulang ke palet |
| Papan / gapura | [Stylized wood signs](https://sketchfab.com/3d-models/d529ec8478304d45a5048e15cf9cc9db) (Sketchfab) | Pasindu.Anjana | CC-BY | ✅ diimpor + **dipoles**: teks "TAMAN NASIONAL BUNAKEN" |
| Perahu (→ katinting) | [Canoe](https://sketchfab.com/3d-models/6486623945f44789ae1949e9add15268) (Sketchfab) | SkyeSladeUT | CC-BY | ✅ diimpor + **dipoles** jadi katinting: 2 boom + pelampung cadik, mesin + baling-baling panjang |
| Nelayan ber-rig | [Farmer](https://poly.pizza/m/7pn3R6hPvE) (Poly Pizza) | Quaternius | CC0 | ✅ diimpor (`Aset_Nelayan`, 1,7 m, bertopi, pose Idle); 24 animasi (Idle/Walk/Run/Wave/Interact dll); pakaian siap diwarnai ulang |
| Burung | [Low-Poly Seagull Animated](https://sketchfab.com/3d-models/bff3cd3d48e249e8b5afa7416c6c39f8) (Sketchfab) | Jamie McFarlane | CC-BY | ✅ diimpor, ber-rig + animasi `Take 001` |
| Awan | **Buatan sendiri** (`skrip/awan_lowpoly.py`) | – | – | ✅ dibuat (`Aset_Awan`: Awan_A/B/C, 80–120 face, flat-shaded) |

## Scene 2 — Karang & Ikan

Galeri verifikasi: https://claude.ai/artifact/5ScsWSvS7cghXKAbWJgc2x (dibuat dengan `skrip/cari_aset_scene2.py`)

| Aset | Status |
|---|---|
| Karang meja | ⏳ pilih di galeri (kandidat: Coral Reef Set, Coral) |
| Karang otak | ⏳ pilih (Brain Coral — jazz-the-giraffe) |
| Karang kipas (gorgonian) | ⚠️ kandidat lemah (fan-art nyampur) — mungkin tolak & cari ulang |
| Anemon laut | ⏳ pilih (Low-Poly Anemone dll) |
| Spons tabung | ⏳ pilih (Sponge — Poly by Google) |
| Ikan badut | ⏳ pilih (Clown fish beranimasi) |
| Ikan ekor kuning/lalosi | ⏳ pilih (Quaternius: Butterfly/Lionfish/Fish, CC0 animasi) |

## Kredit (untuk end credits)
- "Coconut Tree" oleh sujirour, CC BY 4.0, via Sketchfab
- "Mangrove Tree 2" oleh nigromancer, CC BY 4.0, via Sketchfab
- "Low Poly Fisherman's Hut" oleh mitia, CC BY 4.0, via Sketchfab
- "Stylized wood signs" oleh Pasindu.Anjana, CC BY 4.0, via Sketchfab
- "Canoe" oleh SkyeSladeUT, CC BY 4.0, via Sketchfab
- "Low-Poly Seagull Animated" oleh Jamie McFarlane, CC BY 4.0, via Sketchfab
- "Boardwalk" oleh Jacob Cherchio, CC BY 3.0, via Poly Pizza
- "Farmer" oleh Quaternius, CC0 1.0, via Poly Pizza (tanpa kewajiban kredit, tetap dicantumkan)
- Awan: model buatan sendiri (bukan aset pihak ketiga)

## Poles aset (12 Okt) — `skrip/poles_aset.py`
Dijalankan di `aset.blend`, otomatis ikut ke `scene1.blend` lewat link:
- **Perahu → katinting**: 2 boom bambu + 2 pelampung (cadik), blok mesin + baling-baling panjang (long-tail).
- **Rumah → panggung**: diangkat 1,6 m, 5 tiang kayu, atap **seng** (abu), dinding kayu.
- **Papan**: teks "TAMAN NASIONAL BUNAKEN".
- **Dermaga**: railing biru-abu di-tint ke kayu.
- **Flat shading** semua aset.
> Catatan: banyak aset pakai **tekstur gambar** (base color abu 0.8), jadi penyeragaman warna penuh via base color tidak bisa; nada natural kayu/hijau yang ada sudah menyatu.

## Teknik buatan sendiri
- Terrain pulau & Manado Tua (low-poly dari siluet peta)
- Shader air (displace + flat shading + gradasi kedalaman), shader langit gradasi
- Animasi kamera, perahu, nelayan, burung
- Scene 4: generator terrain procedural, skrip boids (`skrip/boids.py`), scatter karang Geometry Nodes

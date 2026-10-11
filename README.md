# Project Animasi Grafika Komputer — Bunaken

Video animasi Blender (4 scene, ≥ 30 s/scene) bertema perikanan Pulau Bunaken.
Tugas akhir mata kuliah Grafika Komputer (TIK4041). Deadline 29 November 2026.

Repo ini menyimpan **konteks lengkap untuk kolaborasi tim** — catatan, berkas
Blender, aset, dan skrip semuanya ikut agar anggota tim bisa langsung clone & impor.

| Folder | Isi | Di git? |
|---|---|---|
| `catatan-obsidian/` | Catatan Obsidian (brief, keputusan, storyboard, per-scene, aset & teknik) | Ya |
| `blender/` | `aset.blend` (library aset bersama, di-link ke tiap scene) + `scene1.blend` … `scene4.blend` | Ya |
| `skrip/` | Skrip Python Blender (cari aset, galeri verifikasi, generator awan, terrain, boids) | Ya |
| `aset/unduhan/` | Aset publik yang diunduh (Poly Pizza dll., CC0/CC-BY) | Ya |
| `render/sceneN/` | Hasil render per scene | Ya |
| `referensi/` | Frame referensi video *Coding Adventure: Boids* | Ya (video besar dikecualikan) |
| `audio/` | Narasi, musik, SFX | Ya |
| `edit/` | Proyek editing video | Ya |

Yang **tidak** masuk git: backup otomatis Blender (`.blend1`/`.blend2`), cache Python,
dan video referensi besar (`referensi/*.mp4`).

## Cara mulai (anggota tim)
1. `git clone https://github.com/jslfrdnan/bunaken-animation.git`
2. Buka `blender/aset.blend` (Blender 5.2.2 LTS) untuk library aset bersama.
3. Impor catatan di `catatan-obsidian/` ke vault Obsidian masing-masing (atau baca langsung sebagai Markdown).

Spesifikasi render: Blender 5.2.2 LTS, EEVEE, 1920×1080, 24 fps.
Kredit aset publik (CC-BY) dicatat di `catatan-obsidian/Aset & Teknik.md` dan ditampilkan di *end credits* video.

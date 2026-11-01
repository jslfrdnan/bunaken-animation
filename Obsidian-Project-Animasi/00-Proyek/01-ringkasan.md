---
tags: [proyek, ringkasan]
status: produksi
scene-fokus: 1
---

# Warisan Bunaken — Ringkasan Proyek

## Satu paragraf

Seorang pemudi Bunaken bernama **Nara** bekerja sebagai dive guide magang di
dive shop keluarganya. Ketika nelayan pendatang, **Pak Haris**, mulai memakai bom
dan jaring dasar untuk menutupi hasil tangkapan yang menurun, terumbu karang
tempat Nara bekerja rusak. Konfliknya bertambah rumit karena ayahnya sendiri,
**Pak Daniel**, mulai tergoda ikut cara Haris. Nara harus membuktikan bahwa
menjaga laut bisa menghidupi kampung — tanpa menghukum orang yang sebenarnya
juga korban.

**Tagline:** *Laut yang dijaga adalah warisan, bukan tambang.*

## Ketentuan tugas (dari brief)

| Ketentuan | Status |
|---|---|
| 4 scene | ✅ 4 scene |
| Minimal 30 detik per scene | ✅ 35 / 35 / 40 / 35 detik = 2:25 |
| Tema perikanan | ✅ bom ikan & jaring dasar |
| Memamerkan Bunaken | ✅ 5 shot establishing + environment detail |
| Ada konflik | ✅ eksternal (Haris) + internal (Pak Daniel) |
| Ada pesan moral | ✅ dua lapis, lihat [[05-pesan-moral]] |
| Storyboard | ✅ [[01-storyboard]] + [[02-shotlist-scene-1]] |

## Spesifikasi teknis

- 1920×1080, 24 fps, EEVEE Next, Blender 5.2 LTS
- Narasi Bahasa Indonesia, direkam tim sendiri
- Subtitle Bahasa Indonesia (satu file `.srt`)
- Audio: narasi + musik latar + SFX bawah laut
- Render per scene, digabung di tahap akhir

## Disclaimer

> **Cerita ini fiksi.** Tokoh, nama, dan peristiwa tidak merujuk pada individu
> atau kelompok nyata. "Kampung Bunaken" adalah latar fiktif yang meminjam
> nama dan lanskap Taman Nasional Laut Bunaken. Praktik destruktif yang
> digambarkan (bom ikan, jaring dasar) adalah praktik nyata yang dilarang
> hukum, namun tidak dikaitkan dengan pelaku tertentu.

Kalimat ini **wajib** muncul di credit film.

## Tautan cepat

- Cerita → [[01-premis]] · [[02-sinopsis]] · [[03-tokoh]] · [[04-dunia-bunaken]]
- Produksi → [[03-gaya-visual]] · [[04-spesifikasi-teknis]]
- Kerja tim → [[03-tim]] · [[04-jadwal]] · [[04-tugas-scene-1]] · [[06-urutan-kerja]]
- Git → [[01-alur-git]]

## Risiko yang sudah diketahui

| Risiko | Mitigasi |
|---|---|
| File `.blend` bentrok antaranggota | satu file = satu pemilik, master hanya link/append |
| Tanpa Git LFS, repo membengkak | render tidak di-commit, `.blend` tanpa packed texture |
| Anggota pasif | 2 tenggat terlewat → tugas pindah ke lead |
| Animatic penuh 6 Nov terlalu cepat | fallback ke 13 Nov, yang penting versi kasar Senin sudah jalan |

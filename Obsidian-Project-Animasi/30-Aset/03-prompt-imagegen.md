---
tags: [aset, prompt, imagegen]
---

# Prompt Image-Generation

Prompt lengkap (**1 lembar gabungan + 15 prompt Gemini 2.5 Flash Image**) ada
di file repo:

→ [`docs/prompts-imagegen.md`](../../docs/prompts-imagegen.md)

> **Prompt 00 — lembar 8 panel.** Satu prompt yang menghasilkan **2 shot per
> scene** (4 scene × 2) dalam satu gambar, untuk menyusun alur storyboard dari
> [[02-sinopsis]] sekali jadi. Sifatnya ringkasan untuk rapat, bukan acuan
> produksi per shot.

> **Dua gaya.** Prompt **01–09** (key art, character sheet, environment)
> tetap **berwarna** — itu acuan konsep akhir untuk Anggota 5 & 7. Prompt
> **00 dan 10–15** (frame storyboard) memakai **sketsa hitam-putih** karena
> sketsa hanya bahasa penyajian storyboard, bukan look film. Look film tetap
> sesuai [[03-gaya-visual]].

## Ringkasan cara pakai

1. Model: **Gemini 2.5 Flash Image**
2. Prompt dalam **Bahasa Inggris**
3. Maksimal **3 gambar referensi** per prompt:
   - `ref-environment-bunaken.jpg` — foto aerial Bunaken
   - `ref-char-nara-sheet.png` — character sheet Nara
   - `ref-char-haris-sheet.png` — character sheet Pak Haris
4. Seed tetap per scene: `20261102` (Scene 1), `20261103` (Scene 2), dst.
5. Tempel blok gaya yang sesuai: **STYLE BLOCK** (warna) untuk 01–09,
   **SKETCH STYLE BLOCK** (hitam-putih) untuk 00 dan 10–15.

## Urutan pengerjaan

1. Prompt **00** (lembar 2 shot per scene) — cek alur 4 scene dulu, sekali jadi.
2. Prompt **02** (character sheet Nara) — hasilnya dipakai sebagai referensi
   untuk semua prompt berikutnya.
3. Prompt **04** dan **05** (Pak Daniel, Pak Haris).
4. Prompt **06–09** (environment Bunaken).
5. Prompt **10–12** (frame Scene 1).
6. Prompt **13–15** (Scene 2 dan 4) menyusul setelah shot list scene tersebut
   selesai.

## Penyimpanan hasil

```
storyboard/frames/scene-1/scene-1_shot-010_v001.png
assets/char/ref-char-nara-sheet.png
assets/env/ref-env-aerial.png
```

## Kalau hasil melenceng

Prompt berwarna (01–09):
- Wajah beda → ulangi dengan hanya 1 character sheet + "match the attached
  character sheet exactly".
- Air neon → tambahkan "muted turquoise, natural water color".
- Terlalu fotorealistis → tambahkan "clearly stylized, simplified forms,
  animation look".

Prompt sketsa (10–15):
- Masih ada warna → tambahkan "pure black-and-white graphite sketch, no color
  at all, white paper".
- Terlihat seperti render 3D / foto → tambahkan "hand-drawn pencil sketch,
  visible construction lines, clearly drawn by hand, not a render".
- Terlalu gelap → tambahkan "light grey shading, open linework, keep most of
  the paper white".

Detail lengkap ada di `docs/prompts-imagegen.md`.

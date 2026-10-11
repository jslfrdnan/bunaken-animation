---
status: Not Started
scene: 4
durasi: 40
pj: G, H
updated: 2026-10-04
tags:
  - project-animasi
  - scene
---

# Scene 4 — Ekspedisi Kapal Selam

Bagian dari [[Tugas Project Animasi]] · Narasi: [[Narasi & Storyboard#Scene 4]]

> [!abstract] Konsep
> Replika demo akhir *Coding Adventure: Boids* (Sebastian Lague, 7:47–akhir): kapal selam riset kuning "KS Bunaken-01" menjelajah lingkungan rintangan bawah laut, kawanan ikan terbelah dan berkumpul lagi.

## Referensi frame video
Terrain low-poly flat-shaded, warna bergradasi menurut ketinggian (kuning puncak → jingga → merah → ungu → biru dasar); bongkahan batu melayang; kabut biru pekat; kawanan ikan hijau & jingga; kamera *follow* di belakang kapal selam gelap.

## Keputusan
- Batu melayang → **pinnacle/bommie** karang + satu **lengkungan swim-through**
- Terrain **procedural Python** (noise → low-poly → warna vertex per ketinggian, palet Bunaken), dirapikan sculpt di jalur kamera
- Karang low-poly disebar Geometry Nodes scatter
- **150 ikan** boids, skrip Python bake keyframe; aturan separation/alignment/cohesion + penghindaran rintangan sinar *golden spiral* (BVHTree); kapal selam = rintangan bergerak
- Kapal selam riset kuning (aset publik dimodifikasi), lampu sorot, baling-baling berputar

## Shot list (40 s)

| Shot | Durasi | Isi |
|---|---|---|
| 1 | 8 s | *Establishing* lebar, kapal selam masuk dari kejauhan |
| 2 | 14 s | *Follow-cam* belakang (seperti frame referensi), kawanan terbelah oleh kapal selam |
| 3 | 10 s | Lewat lengkungan karang, ikan menghindari rintangan |
| 4 | 8 s | Lampu sorot menyala, kapal selam turun ke jurang, *fade out* |

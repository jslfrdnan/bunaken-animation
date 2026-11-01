---
tags: [panduan, ketergantungan, jadwal]
---

# Urutan Kerja & Peta Ketergantungan

Dokumen ini menjawab satu pertanyaan yang paling sering muncul di project
kelompok: **"aku harus nunggu siapa?"**

## Tiga cara peran memengaruhi orang lain

| Jenis | Arti | Contoh di project ini |
|---|---|---|
| **Memblokir mulainya** | Orang lain benar-benar tidak bisa mulai | Rigger tidak bisa mulai tanpa blockout Nara |
| **Menetapkan standar** | Semua orang wajib ikut | Lead mengunci palette → semua artist memakai warna yang sama |
| **Menentukan tempo** | Kalau telat, semua ikut telat | Storyboard telat → 6 orang menganggur |

## Peta ketergantungan

```
                    ┌──────────────────────────────────┐
                    │ 1. LEAD — shot list + style lock │
                    └────────────────┬─────────────────┘
                                     │ membuka semua
        ┌──────────────┬─────────────┴─────────────┬──────────────┐
        ▼              ▼                           ▼              ▼
  ┌───────────┐  ┌───────────┐              ┌───────────┐  ┌───────────┐
  │2.STORYBOARD│  │3.ENV AIR  │              │4.ENV DARAT│  │5.KARAKTER │
  └─────┬─────┘  └─────┬─────┘              └─────┬─────┘  └─────┬─────┘
        │              └───────────┬──────────────┘              │
        │                          ▼                             ▼
        │                   ┌────────────┐               ┌────────────┐
        │                   │7.LIGHTING  │◄──────────────┤6.RIG+ANIM  │
        │                   └──────┬─────┘               └─────┬──────┘
        ▼                          ▼                           │
  ┌───────────┐              ┌────────────┐                    │
  │8.POST     │              │   RENDER   │◄───────────────────┘
  │(audio+edit)│             └────────────┘
  └───────────┘

JALUR KRITIS  ▸ 1 → 2 → 5 → 6 → 7 → RENDER
JALUR PARALEL ▸ 3, 4, 8  (tidak pernah menunggu 5 atau 6)
```

## Siapa menunggu siapa

| Peran | Baru bisa mulai setelah… | Kalau telat, siapa yang kena |
|---|---|---|
| **1. Lead** | — (paling awal) | **Semua** |
| **2. Storyboard** | Lead kunci shot list | Semua — kamera, framing, timing audio |
| **3. Env Air** | Shot list (tidak perlu tunggu karakter) | Lighting tidak punya scene untuk look dev |
| **4. Env Darat** | Shot list | Sama + Editor tidak punya latar shot 010/090 |
| **5. Karakter** | Style guide + character sheet | **Rigger menganggur total** |
| **6. Rig & Animasi** | Blockout Nara dari (5) | Lighting tidak bisa final, Editor tidak punya gerakan |
| **7. Lighting** | Blockout env (3,4) + model (5) | Render final tidak bisa jalan |
| **8. Post (audio+edit)** | **Timing shot** dari (2), bukan aset 3D | Timing berubah → narasi harus direkam ulang |

## Jalur kritis

```
Shot list (1+2) → Blockout Nara (5) → Rig (6) → Animasi (6) → Lighting (7) → Render
```

Enam peran lain punya kelonggaran. **Dua peran ini tidak:**

- **Anggota 5 (Karakter)** — tanpa blockout Nara, Anggota 6 tidak bisa kerja.
- **Anggota 6 (Rig & Animasi)** — 10 shot animasi hanya bisa dia kerjakan.

Kalau salah satu dari dua ini sakit atau hilang, jadwal 6 November gugur.

## Empat aturan untuk mengurangi saling tunggu

1. **Blockout bukan penunggu.**
   Anggota 6 boleh mulai rig dari blockout primitif Anggota 5 di hari pertama.
   Model final masuk belakangan lewat *link/append*.

2. **Aset detail tidak memblokir.**
   Anggota 3 & 4 mulai dari shot list, bukan dari model karakter. Mereka tidak
   pernah perlu menunggu Anggota 5.

3. **Audio pakai narasi sementara.**
   Anggota 8 merekam versi kasar **sebelum** picture lock, jadi tidak menganggur
   menunggu animasi selesai.

4. **Definition of ready.**
   Tugas baru boleh dimulai kalau: shot list-nya ada, pemiliknya jelas, dan file
   tempatnya sudah ada. Kalau belum, jangan mulai — itu yang bikin kerja ulang.

## Tugas yang memblokir (🔒 di board)

| Tugas | Pemilik | Memblokir |
|---|---|---|
| 🔒 Shot list Scene 1 | 1 + 2 | semua |
| 🔒 Blockout Nara | 5 | 6 |
| 🔒 Blockout Pak Daniel | 5 | lighting final, animatic shot 080 |
| 🔒 Blockout terumbu | 3 | 7 |
| 🔒 Blockout permukaan + dermaga | 4 | 7 |
| 🔒 Rig dasar Nara | 6 | animasi, lighting final |
| 🔒 Animasi 10 shot | 6 | render |

Tugas yang **tidak** memblokir siapa pun: sketsa frame, look dev awal, narasi
sementara, dokumentasi, prompt image-gen. Kalau salah satunya telat, jadwal
tidak langsung runtuh — ini yang bisa dipakai sebagai buffer.

## Kalau satu orang hilang

| Peran hilang | Dampak | Tindakan cepat |
|---|---|---|
| 5 (Karakter) | Jalur kritis putus | Lead ambil blockout, rig jalan dengan primitif |
| 6 (Rig & Animasi) | Animasi berhenti | Turunkan target jadi animatic statis + camera move |
| 3 atau 4 (Env) | Lighting tertunda | Pakai aset Poly Haven/Poly Pizza sementara |
| 8 (Post) | Audio + edit berhenti | Lead potong animatic, audio pakai musik library |
| 2 (Storyboard) | Framing tidak jelas | Pakai shot list yang sudah ada + prompt Gemini |

## Aturan tenggat

- Lewat **2 tenggat tanpa kabar** → tugas pindah ke lead.
- Kabar proaktif ("butuh 2 hari lagi") **tidak** dihitung pelanggaran.
- Kalau tugas 🔒 telat, lead **wajib** mengumumkan pergeseran tanggal di hari
  yang sama, bukan menunggu check-in Jumat.

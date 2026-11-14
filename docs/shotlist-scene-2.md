# Shot List — Scene 2 "Retak" (35 detik)

Status: **draft 13 Nov 2026**, menunggu review lead. 0:35–1:10. Subuh biru,
kontras tinggi, saturasi turun. Musik strings tanpa melodi; ambient laut dan
perahu. Narasi tetap dominan.

| Shot | Waktu | Durasi | Visual | Kamera | Audio |
|---|---|---|---|---|---|
| **010** | 0:00–0:04 | 4 s | Perahu Pak Haris di kejauhan, air tenang sebelum terang | Wide static, horizon rendah | Ambient subuh, dayung jauh, strings masuk |
| **020** | 0:04–0:08 | 4 s | Percikan + gelembung dari bom di bawah permukaan; burung terbang | Medium dari permukaan, static | Ledakan tertahan (bukan "BOOM"), air bergolak |
| **030** | 0:08–0:12 | 4 s | Jaring dasar menyapu karang; karang patah, ikan kabur | Tracking lambat di dasar, rendah | Gesekan jaring di karang, gelembung |
| **040** | 0:12–0:16 | 4 s | Pagi berikutnya: hamparan karang hancur, air keruh | Wide menyusur dasar | Hening, hanya desis air |
| **050** | 0:16–0:20 | 4 s | Ikan mati mengapung; Nara masuk frame, diam | Medium dari samping, static | Napas Nara, musik turun |
| **060** | 0:20–0:24 | 4 s | Nara memprotes Haris di dermaga; warga menonton | Medium dua orang, handheld halus | Dialog, ambient dermaga |
| **070** | 0:24–0:27 | 3 s | Warga membela Haris — ia yang membeli hasil tangkapan | Wide dermaga, static | Murmur warga, dialog tumpang tindih |
| **080** | 0:27–0:31 | 4 s | Haris menjawab: tangkapan menurun, ia berutang. Wajah lelah, bukan jahat | Close-up Haris, static | Dialog Haris, strings menekan |
| **090** | 0:31–0:35 | 4 s | Pukulan: Pak Daniel naik ke perahu Haris; Nara melihat dari dermaga | Wide dari belakang Nara, static | Musik berhenti, langkah dan mesin perahu |

**Total: 35 detik.**

## Catatan produksi

- **020** — satu-satunya ledakan di film; jangan sinematik.
- **030** — `PRP_gear_fishnet` sudah ada, tetapi versi terbentang di dasar belum.
- **040–050** — butuh karang rusak dan ikan mati (belum ada).
- **090** — momen terberat; tanpa dialog. Nara tidak menari.

## Status produksi (15 Nov 2026)

| Shot | Status |
|---|---|
| 010–050 | ✅ file animasi v001 ada di `scenes/scene-2_shot-*`; preview di `renders/stills/anim-s2-*` |
| 060–090 | ✅ v001 ada; 090 (`daniel-naik`) diperbarui: island-detail_v003 + crowd_v003 |

**Pembaruan 15 Nov 2026 (@technical):** 010 pulau → `island-detail_v003` + perahu
Haris (`haris-boat.blend`, tanpa kanopi) di 58 m, kamera wide 30 mm horizon
rendah. 020 dibangun ulang sebagai FX bom **bawah permukaan** (kamera z −3 m):
gelembung f1–12, kilatan f12–18, **cincin tekanan torus 0,2 → 6,0 m** (f12–34),
kolom 48 gelembung f18–60, 12 puing karang, 12 cakalang ber-rig kabur; tanpa
camera shake dan tanpa volumetrik. 030: jaring menyapu x −3,2 → +3,6 m,
**6 ikan ber-rig tersangkut** (3 cakalang + 3 kakatua, menempel di jaring) dan
**20 ikan lain kabur**; kamera tracking rendah 26 mm. 090: island v003 +
crowd_v003 (10 warga) + Daniel rig (22 bone) naik perahu Haris. Backup lama:
`*_v000.blend`.

Catatan: laporan akhir subagent hilang saat server OpenCode restart; file dan
preview sudah ter-commit, tetapi audit isi file perlu diulang saat Blender hidup.

## Aset baru

Karang rusak, jaring terbentang, ikan mati, Pak Haris, crowd warga, varian
perahu Haris. Lihat `PROJECT.md` §5 untuk status & pemilik.


/**
 * Subtitle animatic — diambil dari `docs/narasi.md` (draft 13 Nov 2026).
 *
 * Waktu dalam detik, absolut dari awal film. Baris dipecah manual supaya tetap
 * maksimal 2 baris / ±42 karakter (PROJECT.md §3).
 *
 * Cue terakhir (tagline, 2:20) tidak didaftarkan di sini karena sudah tampil
 * sebagai kartu teks di shot 090 Scene 4 — jangan dobel.
 */

export type Cue = {
  start: number;
  end: number;
  lines: [string] | [string, string];
};

export const CUES: Cue[] = [
  // Scene 1 — Permata (0:00–0:35)
  { start: 1, end: 5.5, lines: ["Di utara Sulawesi, laut adalah rumah."] },
  { start: 9, end: 13.5, lines: ["Bagi Nara, laut adalah segalanya."] },
  { start: 17, end: 22, lines: ["Ia pemandu selam di kampungnya sendiri."] },
  { start: 26, end: 31, lines: ["Setiap hari, ia menyapa penghuninya."] },

  // Scene 2 — Retak (0:35–1:10)
  { start: 37, end: 41, lines: ["Tapi laut mulai berubah."] },
  {
    start: 45,
    end: 50.5,
    lines: ["Hasil tangkapan menurun, dan sebagian", "orang memilih jalan pintas."],
  },
  {
    start: 54,
    end: 59,
    lines: ["Bom dan jaring dasar merusak", "tempat hidup ikan."],
  },
  { start: 62, end: 67, lines: ["Yang paling menyakitkan:", "ayah Nara ikut."] },

  // Scene 3 — Titik Balik (1:10–1:50)
  { start: 72, end: 76, lines: ["Nara mengumpulkan bukti."] },
  {
    start: 80,
    end: 85,
    lines: ["Ia menemukan bahwa yang merusak pun", "punya alasan."],
  },
  { start: 88, end: 93, lines: ["Utang, tekanan, dan ketakutan yang sama."] },
  { start: 106, end: 110, lines: ['"Kalau bukan kita yang jaga, siapa lagi?"'] },

  // Scene 4 — Warisan (1:50–2:25)
  {
    start: 112,
    end: 117,
    lines: ["Mereka memilih memperbaiki,", "bukan menghukum."],
  },
  {
    start: 120,
    end: 125,
    lines: ["Pelampung tambat, karang baru,", "dan pekerjaan baru."],
  },
  {
    start: 129,
    end: 134,
    lines: ["Laut pulih perlahan,", "dan kampung ikut pulih."],
  },
];

export const FPS = 24;

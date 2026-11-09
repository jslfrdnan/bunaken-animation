/**
 * Daftar 11 shot Scene 1 (PROJECT.md §4), 35 detik @ 24 fps = 840 frame.
 *
 * Setiap shot memakai aset yang SUDAH ada di repo:
 * - `board/panel-*`  potongan papan cerita v002 (pencil, belum berwarna)
 * - `ref/ref-*`      foto acuan bentuk & warna (referensi internal, bukan
 *                    bagian film; dipakai di animatic sebagai pengganti
 *                    sementara selama belum ada render 3D)
 *
 * `from`/`to` adalah posisi kamera palsu: skala + titik fokus dalam persen.
 * Angka ini yang membuat gambar diam terasa bergerak.
 */

export type Grade = "golden" | "shallow" | "reef" | "deep" | "deck" | "warm";

export type Shot = {
  id: string;
  start: number;
  duration: number;
  title: string;
  camera: string;
  src: string;
  asset: string;
  kind: "board" | "ref";
  grade: Grade;
  from: { scale: number; x: number; y: number };
  to: { scale: number; x: number; y: number };
  shake?: boolean;
  fadeToBlack?: boolean;
};

export const FPS = 24;
export const TOTAL_FRAMES = 840;

export const SHOTS: Shot[] = [
  {
    id: "010",
    start: 0,
    duration: 96,
    title: "Aerial Bunaken, Manado Tua di kiri",
    camera: "Drone push-in lambat",
    src: "board/panel-1a.jpg",
    asset: "Papan cerita 1A",
    kind: "board",
    grade: "golden",
    from: { scale: 1.02, x: 50, y: 42 },
    to: { scale: 1.14, x: 47, y: 45 },
  },
  {
    id: "020",
    start: 96,
    duration: 96,
    title: "Turun ke permukaan air tosca",
    camera: "Tilt down + descent",
    src: "board/panel-1a.jpg",
    asset: "Papan cerita 1A",
    kind: "board",
    grade: "shallow",
    from: { scale: 1.2, x: 52, y: 52 },
    to: { scale: 1.34, x: 50, y: 78 },
  },
  {
    id: "030",
    start: 192,
    duration: 96,
    title: "Terumbu hidup, cahaya menembus air",
    camera: "Tracking lambat ke depan",
    src: "ref/ref-reef.jpg",
    asset: "Foto acuan terumbu",
    kind: "ref",
    grade: "reef",
    from: { scale: 1.04, x: 50, y: 52 },
    to: { scale: 1.16, x: 48, y: 50 },
  },
  {
    id: "040",
    start: 288,
    duration: 72,
    title: "Penyu hijau melewati karang",
    camera: "Follow dari samping",
    src: "board/panel-1b.jpg",
    asset: "Papan cerita 1B",
    kind: "board",
    grade: "reef",
    from: { scale: 1.3, x: 74, y: 62 },
    to: { scale: 1.42, x: 80, y: 58 },
  },
  {
    id: "050",
    start: 360,
    duration: 96,
    title: "Nara muncul dari balik karang",
    camera: "Medium, tracking",
    src: "board/panel-1b.jpg",
    asset: "Papan cerita 1B",
    kind: "board",
    grade: "reef",
    from: { scale: 1.06, x: 44, y: 44 },
    to: { scale: 1.2, x: 42, y: 47 },
  },
  {
    id: "060",
    start: 456,
    duration: 72,
    title: 'Close-up masker, isyarat "OK"',
    camera: "Close-up, statis",
    src: "board/panel-1b.jpg",
    asset: "Papan cerita 1B",
    kind: "board",
    grade: "deep",
    from: { scale: 1.58, x: 49, y: 34 },
    to: { scale: 1.72, x: 49, y: 33 },
  },
  {
    id: "070",
    start: 528,
    duration: 96,
    title: "Nara naik ke perahu, lepas masker",
    camera: "Low angle dari permukaan air",
    src: "ref/ref-perahu.jpg",
    asset: "Foto acuan perahu bercadik",
    kind: "ref",
    grade: "warm",
    from: { scale: 1.02, x: 50, y: 56 },
    to: { scale: 1.14, x: 46, y: 52 },
  },
  {
    id: "080",
    start: 624,
    duration: 72,
    title: "Dive shop: Pak Daniel memperbaiki jaring",
    camera: "Static wide",
    src: "board/panel-1c.jpg",
    asset: "Papan cerita 1C",
    kind: "board",
    grade: "deck",
    from: { scale: 1.14, x: 26, y: 55 },
    to: { scale: 1.26, x: 29, y: 53 },
  },
  {
    id: "090",
    start: 696,
    duration: 72,
    title: "Anak-anak berlari di dermaga",
    camera: "Handheld follow",
    src: "board/panel-1c.jpg",
    asset: "Papan cerita 1C",
    kind: "board",
    grade: "warm",
    from: { scale: 1.3, x: 74, y: 40 },
    to: { scale: 1.44, x: 68, y: 46 },
    shake: true,
  },
  {
    id: "100",
    start: 768,
    duration: 72,
    title: "Nara di ujung dermaga, memandang laut",
    camera: "Medium dari belakang, statis",
    src: "board/panel-4b.jpg",
    asset: "Papan cerita 4B (pinjam)",
    kind: "board",
    grade: "golden",
    from: { scale: 1.04, x: 60, y: 44 },
    to: { scale: 1.14, x: 63, y: 46 },
    fadeToBlack: true,
  },
];

/**
 * Kamera 10 shot Scene 1 untuk versi 3D (Remotion + three.js).
 *
 * Semua angka ditulis dalam koordinat BLENDER supaya bisa dibandingkan
 * langsung dengan `scenes/scene-1.blend`:
 *   x = kiri/kanan, y = menjauhi pantai (negatif = laut), z = atas.
 * Fungsi `B()` mengubahnya ke koordinat three.js (Y-up).
 */

export const B = (x: number, y: number, z: number): [number, number, number] => [x, z, -y];

export type Shot3D = {
  id: string;
  start: number;
  duration: number;
  name: string;
  underwater: boolean;
  fov: number;
  posFrom: [number, number, number];
  posTo: [number, number, number];
  lookFrom: [number, number, number];
  lookTo: [number, number, number];
  shake?: boolean;
};

export const SHOTS_3D: Shot3D[] = [
  {
    id: "010",
    start: 0,
    duration: 96,
    name: "Aerial Bunaken",
    underwater: false,
    fov: 46,
    posFrom: B(320, -520, 200),
    posTo: B(278, -462, 174),
    lookFrom: B(-260, 320, 60),
    lookTo: B(-286, 330, 70),
  },
  {
    id: "020",
    start: 96,
    duration: 96,
    name: "Turun ke permukaan",
    underwater: false,
    fov: 46,
    posFrom: B(34, -132, 26),
    posTo: B(27, -96, 3.4),
    lookFrom: B(18, -55, 2.2),
    lookTo: B(18.5, -56, 0.6),
  },
  {
    id: "030",
    start: 192,
    duration: 96,
    name: "Terumbu hidup",
    underwater: true,
    fov: 50,
    posFrom: B(26.5, -49, -3.6),
    posTo: B(28, -51, -4.0),
    lookFrom: B(34, -59, -4.8),
    lookTo: B(35, -60.5, -5.0),
  },
  {
    id: "040",
    start: 288,
    duration: 72,
    name: "Penyu hijau",
    underwater: true,
    fov: 44,
    posFrom: B(33.5, -53.5, -4.0),
    posTo: B(32.5, -54.5, -4.1),
    lookFrom: B(34, -60.5, -4.35),
    lookTo: B(34, -60.5, -4.4),
  },
  {
    id: "050",
    start: 360,
    duration: 96,
    name: "Nara muncul",
    underwater: true,
    fov: 42,
    posFrom: B(26.5, -49, -4.0),
    posTo: B(27.5, -51.5, -4.2),
    lookFrom: B(28.5, -57.5, -3.6),
    lookTo: B(28.5, -57.5, -3.7),
  },
  {
    id: "060",
    start: 456,
    duration: 72,
    name: "Close-up masker",
    underwater: true,
    fov: 38,
    posFrom: B(27.2, -55.0, -2.85),
    posTo: B(27.45, -55.35, -2.87),
    lookFrom: B(28.5, -57.3, -2.8),
    lookTo: B(28.5, -57.35, -2.81),
  },
  {
    id: "070",
    start: 528,
    duration: 96,
    name: "Nara naik ke perahu",
    underwater: false,
    fov: 40,
    posFrom: B(11, -66, 0.75),
    posTo: B(13, -64, 0.85),
    lookFrom: B(18.6, -55, 1.6),
    lookTo: B(18.6, -54.6, 1.55),
  },
  {
    id: "080",
    start: 624,
    duration: 72,
    name: "Dive shop, Pak Daniel",
    underwater: false,
    fov: 48,
    posFrom: B(9.5, -15, 2.7),
    posTo: B(9.0, -13, 2.55),
    lookFrom: B(2.4, -6, 1.9),
    lookTo: B(2.2, -6.2, 1.85),
  },
  {
    id: "090",
    start: 696,
    duration: 72,
    name: "Anak-anak di dermaga",
    underwater: false,
    fov: 44,
    posFrom: B(0.2, -34, 2.25),
    posTo: B(0.5, -41, 2.15),
    lookFrom: B(0, -70, 1.75),
    lookTo: B(0.4, -72, 1.7),
    shake: true,
  },
  {
    id: "100",
    start: 768,
    duration: 72,
    name: "Nara di ujung dermaga",
    underwater: false,
    fov: 40,
    posFrom: B(0.4, -95, 1.95),
    posTo: B(0.3, -96.5, 1.9),
    lookFrom: B(-0.4, -101, 1.7),
    lookTo: B(-0.45, -101.5, 1.68),
  },
];

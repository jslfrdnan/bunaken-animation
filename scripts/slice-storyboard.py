"""
Memotong papan cerita 3x3 (storyboard-2shot-per-scene_v002.jpg) menjadi 9 panel.

Hasil: motion/public/board/panel-<kode>.jpg untuk 1A, 1B, 1C, 2A, 2B, 3A,
3B, 4A, 4B — dipakai animatic Remotion sebagai plate sementara.

Garis panel dideteksi dari profil piksel gelap, jadi angka di bawah adalah hasil
deteksi, bukan tebakan: batas baris (66, 503), (554, 982), (1032, 1458) dan
batas kolom (113, 900), (986, 1775), (1863, 2650).

Jalankan: python scripts/slice-storyboard.py
"""

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "storyboard" / "frames" / "storyboard-2shot-per-scene_v002.jpg"
OUT = ROOT / "motion" / "public" / "board"

ROWS = [(66, 503), (554, 982), (1032, 1458)]
COLS = [(113, 900), (986, 1775), (1863, 2650)]
NAMES = [["1a", "1b", "1c"], ["2a", "2b", "3a"], ["3b", "4a", "4b"]]

INSET = 3  # buang garis tepi hitam


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    img = Image.open(SRC).convert("RGB")
    print("sumber:", SRC, img.size)

    for r, (y0, y1) in enumerate(ROWS):
        for c, (x0, x1) in enumerate(COLS):
            box = (x0 + INSET, y0 + INSET, x1 - INSET, y1 - INSET)
            crop = img.crop(box)
            name = NAMES[r][c]
            path = OUT / f"panel-{name}.jpg"
            crop.save(path, quality=90, optimize=True)
            print(f"panel-{name}: {crop.size[0]}x{crop.size[1]} -> {path.name} "
                  f"({path.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()

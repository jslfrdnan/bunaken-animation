"""
Membuat bed ambience sementara untuk animatic 2:25 (bukan audio final).

Hasil: renders/audio/warisan-bunaken_ambience_v001.wav
  48 kHz, stereo, 16-bit, 145 detik.

Isi:
- noise pink (laut jauh) dengan LFO lambat
- gelombang rendah (underwater bed) yang bergeser pelan
- gelembung sesekali (blip pendek) di 40-70 s
- fade in 2 s, fade out 3 s

Ini BUKAN musik tema dan BUKAN narasi. Tujuannya supaya animatic tidak bisu
saat direview. Audio final (narasi, kolintang, SFX) tetap tugas peran 8 dan
harus direkam/dilisensikan manusia.

Jalankan: python scripts/make-ambience.py
"""

import math
import random
import struct
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "renders" / "audio" / "warisan-bunaken_ambience_v001.wav"

SR = 48000
DUR = 145.0
N = int(SR * DUR)


def pink_noise(n, rng):
    """Pink noise sederhana lewat filter satu-pole berantai (Paul Kellet)."""
    white = rng.normal(0.0, 1.0, n)
    b = [0.0] * 7
    out = np.empty(n, dtype=np.float64)
    for i in range(n):
        w = white[i]
        b[0] = 0.99886 * b[0] + w * 0.0555179
        b[1] = 0.99332 * b[1] + w * 0.0750759
        b[2] = 0.96900 * b[2] + w * 0.1538520
        b[3] = 0.86650 * b[3] + w * 0.3104856
        b[4] = 0.55000 * b[4] + w * 0.5329522
        b[5] = -0.7616 * b[5] - w * 0.0168980
        out[i] = b[0] + b[1] + b[2] + b[3] + b[4] + b[5] + b[6] + w * 0.5362
        b[6] = w * 0.115926
    return out / np.max(np.abs(out))


def main():
    rng = np.random.default_rng(20261114)
    t = np.arange(N) / SR

    # laut jauh: pink noise + LFO
    sea = pink_noise(N, rng)
    lfo = 0.62 + 0.18 * np.sin(2 * math.pi * 0.055 * t) + 0.08 * np.sin(2 * math.pi * 0.021 * t + 1.1)
    sea = sea * lfo

    # bed bawah air: dua sinus rendah yang bergeser
    bed = 0.16 * np.sin(2 * math.pi * 46.0 * t + 0.4 * np.sin(2 * math.pi * 0.03 * t))
    bed += 0.10 * np.sin(2 * math.pi * 69.0 * t + 0.6 * np.sin(2 * math.pi * 0.017 * t + 2.0))

    # gelembung: 14 blip pendek antara 40-70 s
    bubbles = np.zeros(N)
    for _ in range(14):
        start = rng.uniform(40.0, 70.0)
        f0 = rng.uniform(320.0, 780.0)
        dur = rng.uniform(0.05, 0.12)
        i0 = int(start * SR)
        n = int(dur * SR)
        if i0 + n >= N:
            continue
        tt = np.arange(n) / SR
        env = np.exp(-tt * 38.0)
        bubbles[i0 : i0 + n] += 0.11 * np.sin(2 * math.pi * f0 * tt * (1.0 + 2.2 * tt)) * env

    mix = sea * 0.55 + bed * 0.5 + bubbles

    # fade in/out
    fade_in = int(2.0 * SR)
    fade_out = int(3.0 * SR)
    mix[:fade_in] *= np.linspace(0.0, 1.0, fade_in)
    mix[-fade_out:] *= np.linspace(1.0, 0.0, fade_out)

    # normalisasi ke -14 dBFS kira-kira (headroom untuk narasi nanti)
    peak = np.max(np.abs(mix))
    mix = mix / peak * 0.42

    # stereo: kanan-kiri sedikit berbeda fase supaya tidak mono kaku
    left = mix
    right = np.roll(mix, int(0.007 * SR)) * 0.97
    stereo = np.stack([left, right], axis=1)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    pcm = (np.clip(stereo, -1.0, 1.0) * 32767.0).astype("<i2")
    with wave.open(str(OUT), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())

    size = OUT.stat().st_size
    print(f"WROTE {OUT} ({size/1024/1024:.1f} MB, {DUR:.0f} s, {SR} Hz stereo)")


if __name__ == "__main__":
    main()

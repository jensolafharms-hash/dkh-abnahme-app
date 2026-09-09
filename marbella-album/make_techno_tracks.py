#!/usr/bin/env python3
"""Einzeltitel der Techno-Fassung: aus out/mix-techno/parts/NN.wav fertige MP3 (320 kbit/s, ID3, Cover)."""
import json
import os
import sys

import numpy as np
import soundfile as sf
import lameenc

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import album  # noqa: E402
from tag_mp3 import id3_tag, COVER  # noqa: E402

PARTS = os.path.join(HERE, "out", "mix-techno", "parts")
OUT = os.path.join(HERE, "out", "techno")
SR = 44100


def main(only=None):
    os.makedirs(OUT, exist_ok=True)
    cover = open(COVER, "rb").read() if os.path.exists(COVER) else None
    for i in range(1, 11):
        if only and i != only:
            continue
        wav = os.path.join(PARTS, f"{i:02d}.wav")
        meta_p = os.path.join(PARTS, f"{i:02d}.json")
        if not (os.path.exists(wav) and os.path.exists(meta_p)):
            continue
        meta = json.load(open(meta_p))
        spec = next(t for t in album.TRACKS if t["nr"] == meta["nr"])
        x, _ = sf.read(wav, dtype="float64")
        n_in, n_out = int(1.0 * SR), int(6.0 * SR)
        x[:n_in] *= np.linspace(0, 1, n_in)[:, None]
        x[-n_out:] *= np.linspace(1, 0, n_out)[:, None] ** 1.5
        pcm = np.clip(x * 32767, -32768, 32767).astype(np.int16)
        enc = lameenc.Encoder()
        enc.set_bit_rate(320)
        enc.set_in_sample_rate(SR)
        enc.set_channels(2)
        enc.set_quality(2)
        mp3 = enc.encode(pcm.tobytes()) + enc.flush()
        title = meta["title"].split(" (")[0] + " (Techno Mix)"
        tag = id3_tag(title, album.ALBUM_ARTIST, album.ALBUM_TITLE + " (Techno Mix)", i, 10, 2026, cover, genre="Techno")
        path = os.path.join(OUT, f"{album.slug_of(spec)}-techno.mp3")
        with open(path, "wb") as fh:
            fh.write(tag + mp3)
        print(f"{path}  {len(x) / SR / 60:.1f} min  {os.path.getsize(path) / 1e6:.1f} MB", flush=True)


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else None)

#!/usr/bin/env python3
"""Versandpakete der Techno-Remixe: ZIP in voller Qualitaet (320 kbit/s), WhatsApp (96 kbit/s, < 30 MB)
und E-Mail (64 kbit/s, < 20 MB), jeweils mit Cover, Techno-Rueckseite und Playlist."""
import io
import os
import sys
import zipfile

import lameenc
import miniaudio
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import album  # noqa: E402
from tag_mp3 import id3_tag  # noqa: E402

SRC = os.path.join(HERE, "out", "techno")
OUT = os.path.join(HERE, "out", "techno-release")
ALBUM = album.ALBUM_TITLE + " (Techno Mix)"
FOLDER = "Sounds of Marbella 2026 - Techno Mix"


def main():
    os.makedirs(OUT, exist_ok=True)
    files = sorted(f for f in os.listdir(SRC) if f.endswith(".mp3"))
    im = Image.open(os.path.join(HERE, "cover", "front-1400.jpg")).resize((600, 600), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=82)
    small_cover = buf.getvalue()
    decoded = {}
    for f in files:
        d = miniaudio.decode_file(os.path.join(SRC, f), output_format=miniaudio.SampleFormat.SIGNED16, nchannels=2, sample_rate=44100)
        decoded[f] = (bytes(d.samples), len(d.samples) / 2 / 44100)
    for name, kbps in (("Sounds-of-Marbella-2026-Techno-MP3.zip", 0), ("Sounds-of-Marbella-2026-Techno-WhatsApp.zip", 96),
                       ("Sounds-of-Marbella-2026-Techno-E-Mail.zip", 64)):
        zpath = os.path.join(OUT, name)
        m3u = ["#EXTM3U"]
        with zipfile.ZipFile(zpath, "w", zipfile.ZIP_STORED) as z:
            for i, f in enumerate(files, 1):
                spec = next(t for t in album.TRACKS if int(t["nr"]) == i)
                title = spec["title"] + " (Techno Mix)"
                pcm, secs = decoded[f]
                if kbps:
                    enc = lameenc.Encoder()
                    enc.set_bit_rate(kbps)
                    enc.set_in_sample_rate(44100)
                    enc.set_channels(2)
                    enc.set_quality(2)
                    data = enc.encode(pcm) + enc.flush()
                    tag = id3_tag(title, album.ALBUM_ARTIST, ALBUM, i, len(files), 2026, small_cover, genre="Techno")
                    z.writestr(f"{FOLDER}/{f}", tag + data)
                else:
                    z.write(os.path.join(SRC, f), f"{FOLDER}/{f}")
                m3u += [f"#EXTINF:{int(secs)},{album.ALBUM_ARTIST} - {title}", f]
            z.write(os.path.join(HERE, "cover", "front-1400.jpg"), f"{FOLDER}/folder.jpg")
            z.write(os.path.join(HERE, "cover", "back-techno-1400.jpg"), f"{FOLDER}/back.jpg")
            z.writestr(f"{FOLDER}/{FOLDER}.m3u", "\n".join(m3u) + "\n")
        print(name, f"{os.path.getsize(zpath) / 1024 / 1024:.1f} MB", flush=True)


if __name__ == "__main__":
    main()

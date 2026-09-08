#!/usr/bin/env python3
"""
Schreibt ID3v2.3-Tags (Titel, Interpret, Album, Tracknummer, Jahr, Cover) in die
MP3-Dateien in ./out und packt Album plus Cover als ZIP.

    python3 tag_mp3.py
"""
import json
import os
import struct
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
COVER = os.path.join(HERE, "cover", "front-1400.jpg")


def _frame(fid, payload):
    return fid.encode("ascii") + struct.pack(">I", len(payload)) + b"\x00\x00" + payload


def _text(fid, text):
    return _frame(fid, b"\x01" + text.encode("utf-16"))  # UTF-16 mit BOM


def id3_tag(title, artist, album, track, total, year, cover_bytes=None, genre="House"):
    frames = b"".join([
        _text("TIT2", title), _text("TPE1", artist), _text("TPE2", artist), _text("TALB", album),
        _text("TRCK", f"{track}/{total}"), _text("TYER", str(year)), _text("TCON", genre),
        _text("TCOM", artist),
    ])
    if cover_bytes:
        frames += _frame("APIC", b"\x00" + b"image/jpeg\x00" + b"\x03" + b"\x00" + cover_bytes)
    frames += b"\x00" * 1024  # Padding
    size = len(frames)
    syncsafe = bytes([(size >> 21) & 0x7F, (size >> 14) & 0x7F, (size >> 7) & 0x7F, size & 0x7F])
    return b"ID3\x03\x00\x00" + syncsafe + frames


def strip_existing_tag(data):
    if data[:3] == b"ID3":
        size = (data[6] << 21) | (data[7] << 14) | (data[8] << 7) | data[9]
        return data[10 + size:]
    return data


def main():
    with open(os.path.join(OUT, "tracklist.json"), encoding="utf-8") as fh:
        tl = json.load(fh)
    cover = open(COVER, "rb").read() if os.path.exists(COVER) else None
    total = len(tl["tracks"])
    for tr in tl["tracks"]:
        path = os.path.join(OUT, tr["file"])
        if not os.path.exists(path):
            print("fehlt:", path, file=sys.stderr)
            continue
        audio = strip_existing_tag(open(path, "rb").read())
        tag = id3_tag(tr["title"], tl["artist"], tl["album"], tr["nr"], total, tl.get("year", 2026), cover)
        with open(path, "wb") as fh:
            fh.write(tag + audio)
        print("getaggt:", tr["file"])
    zpath = os.path.join(HERE, "Sounds-of-Marbella-2026.zip")
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_STORED) as z:
        for tr in tl["tracks"]:
            z.write(os.path.join(OUT, tr["file"]), f"Sounds of Marbella 2026/{tr['file']}")
        for name in ("front.png", "back.png", "cover.pdf"):
            p = os.path.join(HERE, "cover", name)
            if os.path.exists(p):
                z.write(p, f"Sounds of Marbella 2026/cover/{name}")
    print("ZIP:", zpath)


if __name__ == "__main__":
    main()

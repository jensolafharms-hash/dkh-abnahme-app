#!/usr/bin/env python3
"""
Release-Paket bauen:
  out/master/cd/     WAV 16 Bit / 44,1 kHz je Titel + Cue-Sheet mit CD-Text (zum Brennen einer Audio-CD)
  out/master/flac/   FLAC-Master je Titel (für Distributoren)
  out/Sounds-of-Marbella-2026-MP3.zip        Album als ZIP: getaggte MP3s (192 kbit/s), Cover, Playlist
  out/Sounds-of-Marbella-2026-WhatsApp.zip   dasselbe mit 96 kbit/s (unter 30 MB, als WhatsApp-Dokument senden)
  out/Sounds-of-Marbella-2026-E-Mail.zip     dasselbe mit 64 kbit/s (unter 20 MB, passt als E-Mail-Anhang)

    python3 make_release.py
"""
import json
import os
import shutil
import zipfile

import numpy as np
import soundfile as sf
from scipy.io import wavfile

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
ALBUM = "Sounds of Marbella 2026"
ARTIST = "DJ Jensi"


def cue_time(seconds):
    frames = int(round(seconds * 75))
    m, rest = divmod(frames, 75 * 60)
    s, f = divmod(rest, 75)
    return f"{m:02d}:{s:02d}:{f:02d}"


def main():
    tl = json.load(open(os.path.join(OUT, "tracklist.json"), encoding="utf-8"))
    cd_dir = os.path.join(OUT, "master", "cd")
    flac_dir = os.path.join(OUT, "master", "flac")
    os.makedirs(cd_dir, exist_ok=True)
    os.makedirs(flac_dir, exist_ok=True)
    cue = [f'TITLE "{ALBUM}"', f'PERFORMER "{ARTIST}"', 'REM GENRE "Chill House"', 'REM DATE 2026']
    for i, tr in enumerate(tl["tracks"], 1):
        base = tr["file"][:-4]
        src = os.path.join(OUT, base + ".wav")
        sr, x = wavfile.read(src)
        assert sr == 44100 and x.dtype == np.int16, (sr, x.dtype)
        dst = os.path.join(cd_dir, base + ".wav")
        shutil.copy(src, dst)
        sf.write(os.path.join(flac_dir, base + ".flac"), x, sr, subtype="PCM_16")
        cue += [f'FILE "{base}.wav" WAVE', f"  TRACK {i:02d} AUDIO", f'    TITLE "{tr["title"]}"', f'    PERFORMER "{ARTIST}"', "    INDEX 01 00:00:00"]
        print(f"  {i:02d} {tr['title']}: {len(x)/sr:.1f} s -> WAV + FLAC", flush=True)
    with open(os.path.join(cd_dir, "Sounds-of-Marbella-2026.cue"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(cue) + "\n")
    with open(os.path.join(cd_dir, "README-CD.txt"), "w", encoding="utf-8") as fh:
        fh.write("Audio-CD brennen\n================\n\n"
                 "Die Cue-Datei in ein Brennprogramm laden (z. B. ImgBurn, CDBurnerXP, Burn auf dem Mac, K3b) und als Audio-CD\n"
                 "brennen. Titel, Interpret und Albumname werden als CD-Text mitgeschrieben. Gesamtspielzeit 36:03,\n"
                 "passt auf eine 74- oder 80-Minuten-CD-R.\n")
    for name, kbps in (("Sounds-of-Marbella-2026-MP3.zip", 0), ("Sounds-of-Marbella-2026-WhatsApp.zip", 96), ("Sounds-of-Marbella-2026-E-Mail.zip", 64)):
        zpath = os.path.join(OUT, name)
        folder = ALBUM
        m3u = ["#EXTM3U"]
        with zipfile.ZipFile(zpath, "w", zipfile.ZIP_STORED) as z:
            for tr in tl["tracks"]:
                path = os.path.join(OUT, tr["file"])
                if kbps:
                    import lameenc
                    import miniaudio
                    d = miniaudio.decode_file(path, output_format=miniaudio.SampleFormat.SIGNED16, nchannels=2, sample_rate=44100)
                    enc = lameenc.Encoder()
                    enc.set_bit_rate(kbps)
                    enc.set_in_sample_rate(44100)
                    enc.set_channels(2)
                    enc.set_quality(2)
                    data = enc.encode(bytes(d.samples)) + enc.flush()
                    # ID3-Tag der Originaldatei übernehmen
                    raw = open(path, "rb").read()
                    tag = raw[: 10 + ((raw[6] << 21) | (raw[7] << 14) | (raw[8] << 7) | raw[9])] if raw[:3] == b"ID3" else b""
                    z.writestr(f"{folder}/{tr['file']}", tag + data)
                else:
                    z.write(path, f"{folder}/{tr['file']}")
                m3u += [f"#EXTINF:{int(tr['duration_s'])},{ARTIST} - {tr['title']}", tr["file"]]
            if not kbps:
                z.write(os.path.join(HERE, "cover", "front.png"), f"{folder}/cover.png")
            z.write(os.path.join(HERE, "cover", "front-1400.jpg"), f"{folder}/folder.jpg")
            z.write(os.path.join(HERE, "cover", "back-1400.jpg"), f"{folder}/back.jpg")
            z.writestr(f"{folder}/{ALBUM}.m3u", "\n".join(m3u) + "\n")
        print(name, f"{os.path.getsize(zpath)/1024/1024:.1f} MB")


if __name__ == "__main__":
    main()

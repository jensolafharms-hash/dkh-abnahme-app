#!/usr/bin/env python3
"""Die zehn Album-Titel einzeln im Techno-Stil neu gemischt (out/techno/): Original-Partitur, Techno-Tempo,
Four-on-the-floor, rollender Synth-Bass, Effekte, Aufbau/Breakdown/Drop. MP3 320 kbit/s mit Tags und Cover."""
import copy
import os
import sys

import numpy as np
import soundfile as sf
import lameenc

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import album  # noqa: E402
import sf_render  # noqa: E402
from album import S, mel, SR, Track, write_midi  # noqa: E402
from mix import by_nr, bul_to_44, TECHNO_BPM, techno_tweaks, techno_structure, club_master  # noqa: E402
from tag_mp3 import id3_tag, COVER  # noqa: E402

OUT = os.path.join(HERE, "out", "techno")
MAX_BARS = 24   # kuerzer: kein Abschnitt laenger als 24 Takte


_PLAN = {}


def techno_spec(nr):
    bpm, bpm_end = TECHNO_BPM[nr]
    if nr in (3, 4, 7):                            # 4/4-Fassungen aus dem Mix-Plan (Bulería, Paseo, 6/8-Sierra), ohne Mix-Ein-/Ausstieg
        if not _PLAN:
            from mix import build_plan
            _PLAN.update({p["nr"]: p for p in build_plan()})
        spec = copy.deepcopy(_PLAN[nr])
        spec["title"] = spec["title"].split(" (")[0]
        spec["sections"] = [s for s in spec["sections"] if s["name"] not in ("mix_in", "mix_out")]
        spec["sections"].append(S("end", 2, bpm=bpm, dyn=0.55, fx=["final_chord"]))
    else:
        spec = by_nr(nr)
    if nr == 9:                                    # Farola: Laterne als Kick-Breakdown mit Drop
        spec["sections"] = [
            S("lantern", 16, bpm=bpm, dyn=0.7, drums="kickonly", drum_level=0.8, bass="one", bass_level=0.7, sub=0.45, pad=550,
              choir="oo", choir_level=0.1, choir_every=2, fx=["bell", "riser", "siren"], bell_motif=[(0, 0), (8, 7)],
              melody=[mel("motif", "guitar", 0.32, legato=1.5, humanize=0.02)], atmos=dict(crickets=0.4)),
            S("lantern_drop", 24, bpm=bpm, dyn=0.95, drums="house", drum_level=1.0, hats="full", bass="house", bass_level=0.95, sub=0.6,
              pad=800, pad_level=0.5, choir="ah", choir_level=0.1, acid=0.18, acid_cut=380.0, stabs="dub", stab_steps=(2, 10), stab_level=0.14,
              fx=["impact", "crash", "downlifter", "bell"], bell_motif=[(0, 0), (8, 7)], fill=True,
              melody=[mel("motif", "guitar", 0.3, legato=1.2), mel("motif", "ney", 0.16, octave=12, pan=0.3, offset=4)]),
            S("end", 2, bpm=bpm, dyn=0.55, fx=["final_chord"], atmos=dict(crickets=0.5)),
        ]
    for s in spec["sections"]:                     # Techno-Tempo, 4/4, kuerzere Abschnitte
        s["meter"] = "4/4"
        s["bpm"], s["bpm_end"] = bpm, None
        s["bars"] = min(s["bars"], 16 if s["parts"].get("drums") == "kickonly" else MAX_BARS)
    body = [s for s in spec["sections"] if s["parts"].get("drums")]
    if body and bpm_end != bpm:
        body[-1]["bpm_end"] = bpm_end
    techno_tweaks(spec)
    techno_structure(spec, bd_min=16, alternate=True)
    spec["title"] = spec["title"] + " (Techno Mix)"
    return spec


def render(spec, nr, cover):
    os.makedirs(os.path.join(OUT, "midi"), exist_ok=True)
    album.master_chain = lambda x: x
    tr = Track(spec)
    slug = album.slug_of(spec).replace("-techno-mix", "") + "-techno"

    def hook(t):
        mp = os.path.join(OUT, "midi", slug + ".mid")
        write_midi(t, mp)
        sf_render.replace_layers(t, mp, verbose=False)
    tr.pre_mix = hook
    pre = tr.render()
    del tr.layers
    x = club_master(pre)
    end = min(len(x), int(tr.bar_start[tr.total_bars] * SR) + int(4.0 * SR))
    x = x[:end]
    n_out = int(3.0 * SR)
    x[-n_out:] *= np.linspace(1, 0, n_out)[:, None]
    pcm = np.clip(x * 32767, -32768, 32767).astype(np.int16)
    enc = lameenc.Encoder()
    enc.set_bit_rate(320)
    enc.set_in_sample_rate(SR)
    enc.set_channels(2)
    enc.set_quality(2)
    mp3 = enc.encode(pcm.tobytes()) + enc.flush()
    tag = id3_tag(spec["title"], album.ALBUM_ARTIST, album.ALBUM_TITLE + " (Techno Mix)", nr, 10, 2026, cover, genre="Techno")
    path = os.path.join(OUT, slug + ".mp3")
    with open(path, "wb") as fh:
        fh.write(tag + mp3)
    print(f"{path}  {len(x) / SR / 60:.1f} min  {os.path.getsize(path) / 1e6:.1f} MB", flush=True)
    return path


def main():
    only = [int(a) for a in sys.argv[1:]]
    sf_render.SF_MAP = {k: v for k, v in sf_render.SF_MAP.items() if k != "Bass"}   # Synth-Bass bleibt synthetisch
    cover = open(COVER, "rb").read() if os.path.exists(COVER) else None
    os.makedirs(OUT, exist_ok=True)
    for nr in range(1, 11):
        if only and nr not in only:
            continue
        spec = techno_spec(nr)
        d = album.track_duration(spec) - 10
        print(f"[{nr}/10] {spec['title']}  ({int(d // 60)}:{int(d % 60):02d})  " +
              " | ".join(f"{s['name']}:{s['bars']}" for s in spec["sections"]), flush=True)
        render(spec, nr, cover)


if __name__ == "__main__":
    main()

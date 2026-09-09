#!/usr/bin/env python3
"""
Sounds of Marbella 2026 – Continuous Mix (55 bis 60 Minuten, tanzbar).

Baut aus der Album-Partitur verlängerte, durchgehend tanzbare Fassungen aller
Stücke, hängt sie mit taktgenauen Beat-Übergängen aneinander und mastert
club-tauglich (kräftiger Bass, Sub-Layer, Limiter).

    python3 mix.py            # rendert alle Teile (ca. 70 Minuten Rechenzeit) und baut den Mix
    python3 mix.py --assemble # nur zusammensetzen (Teile liegen schon in out/mix/parts)
"""
import argparse
import copy
import json
import os
import sys

import numpy as np
import soundfile as sf
from scipy import signal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import album  # noqa: E402
import generate_album as ga  # noqa: E402
import sf_render  # noqa: E402
from album import S, mel, SR, Track, write_midi, apply_defaults  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out", "mix")
PARTS = os.path.join(OUT, "parts")
MIX_NAME = "Sounds-of-Marbella-2026-Continuous-Mix"
TITLE = "Sounds of Marbella 2026 – Continuous Mix"

TECHNO_BPM = {1: (126, 128), 2: (128, 128), 3: (128, 130), 4: (130, 130), 5: (130, 130), 6: (130, 132),
              7: (132, 132), 8: (132, 132), 9: (132, 132), 10: (132, 134)}
BEAT_IN = dict(drums="house", drum_level=0.85, hats="offbeat", bass="house", bass_inst="pluck", bass_level=0.9, sub=0.55,
               comping="strum", comp_level=0.12, pad=800, pad_level=0.5, perc=["shaker"], perc_level=0.7, dyn=0.86)
DROP = {"end", "outro", "outro1", "outro2", "after2", "fade2", "embers", "stop", "coda"}
EXTEND = ("groove", "lift", "peak", "chorus", "deep", "refrain", "dance", "return", "trance", "estribillo", "copla", "call",
          "circle", "break", "sun", "glow", "warming", "verse", "climax", "walk", "release", "build")


def by_nr(nr):
    return copy.deepcopy(next(t for t in album.TRACKS if t["nr"] == nr))


def bul_to_44(theme):
    """Bulería-Compás (12 Zählzeiten) -> zwei 4/4-Takte (16 Achtel)."""
    return [[(int(round(p * 16 / 12)), s_, max(1, int(round(d * 16 / 12)))) for p, s_, d in ph] for ph in theme]


def set_tempo(spec, bpm, bpm_next=None, keep_ramps=False):
    secs = [s for s in spec["sections"] if s["name"] not in DROP]
    for s in secs:
        if not keep_ramps:
            s["bpm"], s["bpm_end"] = bpm, None
        if s["meter"] != "4/4":
            s["meter"] = "4/4"
    if bpm_next is not None and secs:
        secs[-1]["bpm_end"] = bpm_next
        secs.append(S("mix_out", 8, bpm=bpm_next, fill=True, **BEAT_IN))
    spec["sections"] = secs
    return spec


def add_mix_in(spec, bpm):
    spec["sections"].insert(0, S("mix_in", 8, bpm=bpm, **BEAT_IN))
    return spec


def stretch(spec, target_s):
    """Verlängert die Groove-Abschnitte, bis die Zielspielzeit erreicht ist (in 4-Takt-Schritten)."""
    for _ in range(60):
        dur = album.track_duration(spec) - 10.0
        if dur >= target_s:
            break
        cands = [s for s in spec["sections"] if any(k in s["name"] for k in EXTEND) and s["name"] not in ("mix_in", "mix_out")
                 and not s["name"].endswith(("_bd", "_drop"))]
        if not cands:
            break
        cands.sort(key=lambda s: s["bars"])
        cands[0]["bars"] += 4
    return spec


def club_tweaks(spec):
    spec["kick_punch"] = 1.3
    spec["duck"] = 0.66
    spec["bass_boost"] = max(spec.get("bass_boost", 0.62), 0.78)
    for s in spec["sections"]:
        P = s["parts"]
        if P.get("bass") and P["bass"] != "one":
            P["sub"] = max(P.get("sub", 0.0), 0.5)
            P["bass_level"] = max(P.get("bass_level", 0.8), 0.9)
        if P.get("drums") in ("deep", "halftime", "soft") and s["bars"] >= 8 and s["name"] not in ("intro", "dawn"):
            P["drums"] = "house"
            P.setdefault("hats", "offbeat")
    return spec


def retempo(spec, bpm, bpm_next):
    """Setzt alle Abschnitte auf ein Tempo; der letzte Groove-Abschnitt zieht zum Folgetempo an."""
    secs = spec["sections"]
    for s in secs:
        s["bpm"], s["bpm_end"] = bpm, None
    body = [s for s in secs if s["name"] != "mix_out"]
    if body:
        body[-1]["bpm_end"] = bpm_next
    for s in secs:
        if s["name"] == "mix_out":
            s["bpm"] = bpm_next
    return spec


PEAKS = ("peak", "chorus", "refrain", "climax", "sun", "trance", "dance", "lift", "estribillo", "call", "glow")


def techno_tweaks(spec):
    """Techno-Fassung: Four-on-the-floor, 16tel-Hats, rollender Synth-Bass, mehr Acid und Stabs."""
    spec["kick_punch"] = 1.45
    spec["duck"] = 0.72
    spec["bass_boost"] = max(spec.get("bass_boost", 0.62), 0.85)
    for s in spec["sections"]:
        P = s["parts"]
        name = s["name"]
        if P.get("drums") and P["drums"] != "kickonly":
            P["drums"] = "techno"
            P["drum_level"] = max(P.get("drum_level", 0.9), 0.95)
            P["hats"] = "techno16" if any(k in name for k in PEAKS) or name in ("mix_in", "mix_out") else "techno_off"
            P["hats_alt"] = "full" if P["hats"] == "techno16" else "techno16"
        if P.get("bass") and P["bass"] != "one":
            P["bass"] = "techno"
            P["bass_inst"] = "synth"
            P["bass_level"] = max(P.get("bass_level", 0.8), 0.95)
            P.setdefault("bass_cut", 520.0)
            P.setdefault("bass_drive", 1.9)
            P["sub"] = max(P.get("sub", 0.0), 0.55)
        if P.get("drums") and s["bars"] >= 8:
            P["acid"] = max(P.get("acid", 0.0), 0.16 if any(k in name for k in PEAKS) else 0.12)
            P.setdefault("acid_cut", 360.0)
        if any(k in name for k in PEAKS) and P.get("drums"):
            P.setdefault("stabs", "dub")
            P.setdefault("stab_steps", (2, 10))
            P.setdefault("stab_level", 0.12)
        if P.get("comping"):
            P["comp_level"] = P.get("comp_level", 0.18) * 0.7
        for m in P.get("melody", []):
            m["level"] *= 0.9
        if P.get("drums") == "techno":
            P.update(hat_var=True, acid_var=True, acid_open=True, kick_out=True, kick_out_every=8)
    return spec


def techno_structure(spec, bd_min=40, alternate=False):
    """Lange Groove-Teile -> Aufbau, (Breakdown), Drop. Weniger Schleife, mehr Dramaturgie. Nach stretch() aufrufen.
    alternate: jeder zweite Groove-Teil bekommt Breakdown + Drop, die anderen nur den Drop."""
    new = []
    n_split = 0
    for s in spec["sections"]:
        P = s["parts"]
        if P.get("drums") == "techno" and s["bars"] >= 16 and s["name"] not in ("mix_in", "mix_out"):
            n_bd = 4 if s["bars"] >= bd_min and (not alternate or n_split % 2 == 0) else 0
            n_split += 1
            main = copy.deepcopy(s)
            main["bars"] = s["bars"] - 8 - n_bd
            mp = main["parts"]
            # Aufbau bleibt nackt: keine Melodie, kein Comping, Pad leiser -> weniger ist mehr
            mp["melody"] = [m for m in mp.get("melody", []) if m["theme"] == "frag"][:1]
            mp.pop("comping", None)
            mp.pop("stabs", None)
            mp["pad_level"] = mp.get("pad_level", 0.5) * 0.7
            mp["fx"] = sorted(set(mp.get("fx", [])) | {"sweep_up", "hp_build", "roll", "gate", "siren"} | ({"cut"} if not n_bd else set()))
            mp["fill"] = True
            new.append(main)
            if n_bd:
                bd = copy.deepcopy(s)
                bd["name"] = s["name"] + "_bd"
                bd["bars"] = n_bd
                bd["dyn"] = min(s["dyn"], 0.8)
                bp = bd["parts"]
                for k in ("drums", "hats", "hats_alt", "perc", "stabs", "ride", "fill", "kick_out"):
                    bp.pop(k, None)
                bp.update(bass="one", bass_level=0.7, sub=0.4, acid=max(bp.get("acid", 0.12), 0.18), acid_cut=300.0,
                          acid_open=True, fx=["riser", "siren", "cut", "gate"])
                new.append(bd)
            drop = copy.deepcopy(s)
            drop["name"] = s["name"] + "_drop"
            drop["bars"] = 8
            drop["dyn"] = min(1.0, s["dyn"] + 0.06)
            dp = drop["parts"]
            dp.update(hats="techno16", hats_alt="full", drum_level=1.0, fx=["impact", "crash", "reverse", "downlifter", "throw", "cut"], fill=True)
            dp.pop("comping", None)
            dp.setdefault("stabs", "dub")
            dp.setdefault("stab_steps", (2, 10))
            dp["stab_level"] = max(dp.get("stab_level", 0.12), 0.14)
            new.append(drop)
        else:
            if P.get("drums") == "techno" and s["bars"] >= 8 and s["name"] not in ("mix_in", "mix_out"):
                P["fx"] = sorted(set(P.get("fx", [])) | {"sweep_up", "roll", "crash", "cut", "throw"})
            new.append(s)
    spec["sections"] = new
    return spec


# --------------------------------------------------------------------------- #
# Die zehn Teile des Mixes
# --------------------------------------------------------------------------- #
def build_plan(techno=False):
    plan = []

    t = by_nr(1)                                   # Playa: Opener, eigenes Intro bleibt
    set_tempo(t, 118, 120)
    plan.append((t, 420))

    t = by_nr(2)
    set_tempo(t, 120, 122)
    add_mix_in(t, 120)
    plan.append((t, 420))

    g = by_nr(3)                                   # Golden Mile als 4/4-Rumba-House
    g["title"] = "Golden Mile Breeze (4/4 Rumba House)"
    g["units"] = 8
    g["themes"] = dict(A=bul_to_44(g["themes"]["A"]), B=bul_to_44(g["themes"]["B"]), frag=bul_to_44(g["themes"]["frag"]))
    g["progs"] = dict(verse=["I", "I", "bIImaj", "bIImaj"], refrain=["iv", "iv", "bIII", "bIII", "bIImaj", "bIImaj", "I", "I"])
    g["sections"] = [
        S("mix_in", 8, bpm=122, **BEAT_IN),
        S("intro", 8, bpm=122, dyn=0.78, drums="house", drum_level=0.8, hats="offbeat", bass="house", bass_inst="pluck", bass_level=0.9, sub=0.5,
          perc=["cajon", "darbuka"], perc_level=0.8, pad=700, pad_level=0.5, melody=[mel("A", "guitar", 0.42, ornaments=True)]),
        S("groove1", 16, bpm=122, dyn=0.86, drums="house", drum_level=0.9, hats="offbeat", hats_alt="full", bass="house", bass_inst="pluck", bass_level=0.92, sub=0.55,
          comping="rumba", comp_level=0.15, perc=["palmas", "darbuka", "cajon"], perc_level=0.85, pad=800, pad_level=0.5, fill=True,
          melody=[mel("A", "guitar", 0.4, ornaments=True, alt="ney")], answer="steel", answer_level=0.1),
        S("refrain1", 16, bpm=122, prog="refrain", dyn=0.94, drums="house", drum_level=0.95, hats="full", hats_alt="techno16", bass="house", bass_inst="pluck", bass_level=0.95, sub=0.6,
          comping="rumba", comp_level=0.16, perc=["palmas", "castanets", "darbuka"], perc_level=0.95, pad=1000, pad_level=0.45, stabs="dub", stab_steps=(2, 10), stab_level=0.1, fill=True,
          melody=[mel("B", "choir", 0.16), mel("B", "guitar", 0.32, octave=0, legato=0.8), mel("B", "flute", 0.14, octave=24, pan=0.3)]),
        S("break", 8, bpm=122, prog="refrain", dyn=0.9, drums="kickonly", drum_level=1.0, hats="offbeat", bass="house", bass_inst="pluck", bass_level=0.95, sub=0.6, acid=0.16, acid_cut=380.0,
          comping="rumba", comp_level=0.26, perc=["palmas", "castanets"], perc_level=1.1, fill=True),
        S("groove2", 16, bpm=122, dyn=0.88, drums="house", drum_level=0.92, hats="offbeat", hats_alt="full", bass="house", bass_inst="pluck", bass_level=0.92, sub=0.55, acid=0.14, acid_cut=340.0,
          comping="oudarp", comp_level=0.15, perc=["palmas", "darbuka", "cajon"], perc_level=0.85, pad=800, pad_level=0.45, fill=True,
          melody=[mel("A", "ney", 0.26, alt="guitar", alt_level=0.4)], answer="guitar", answer_level=0.12),
        S("refrain2", 16, bpm=122, prog="refrain", dyn=1.0, drums="house", drum_level=1.0, hats="techno16", hats_alt="full", ride=True, bass="house", bass_inst="pluck", bass_level=0.98, sub=0.62,
          comping="rumba", comp_level=0.16, perc=["palmas", "castanets", "darbuka", "cajon"], perc_level=1.0, pad=1100, pad_level=0.45, fx=["crash"], fill=True,
          melody=[mel("B", "choir", 0.18), mel("B", "guitar", 0.32, octave=0, legato=0.8), mel("B", "ney", 0.16, octave=12, pan=0.3)]),
        S("mix_out", 8, bpm=122, fill=True, **BEAT_IN),
    ]
    apply_defaults([g])
    plan.append((g, 390))

    p = by_nr(4)                                   # Paseo mit Beat
    p["sections"] = [
        S("mix_in", 8, bpm=122, **BEAT_IN),
        S("walk", 24, bpm=122, dyn=0.86, drums="house", drum_level=0.9, hats="offbeat", hats_alt="full", bass="house", bass_inst="pluck", bass_level=0.92, sub=0.55,
          comping="oudarp", comp_level=0.14, perc=["darbuka", "cajon", "shaker"], perc_level=0.85, pad=700, pad_level=0.5, fill=True,
          melody=[mel("walk", "guitar", 0.4, ornaments=True, alt="ney")], atmos=dict(cicadas=0.4)),
        S("mix_out", 8, bpm=122, fill=True, **BEAT_IN),
    ]
    plan.append((p, 120))

    t = by_nr(5)
    set_tempo(t, 122, 124)
    add_mix_in(t, 122)
    plan.append((t, 420))

    t = by_nr(6)
    for s in t["sections"]:
        s["shift"] = s["shift"]  # Modulation bleibt
    set_tempo(t, 124, 122)
    add_mix_in(t, 124)
    plan.append((t, 450))

    sb = by_nr(7)                                  # Sierra Blanca als Shuffle-House (Themen behalten ihren 6er-Puls)
    sb["title"] = "Sierra Blanca Drift (Shuffle House)"
    sb["sections"] = [
        S("mix_in", 8, bpm=122, **BEAT_IN),
        S("verse1", 16, bpm=122, dyn=0.84, drums="house", drum_level=0.88, hats="eighths", bass="house", bass_inst="pluck", bass_level=0.9, sub=0.55,
          comping="arp6", comp_level=0.16, perc=["shaker", "congas"], perc_level=0.75, pad=800, pad_level=0.5, fill=True,
          melody=[mel("A", "flute", 0.24, alt="guitar", alt_level=0.4)], answer="steel", answer_level=0.1),
        S("refrain1", 16, bpm=122, prog="refrain", dyn=0.92, drums="house", drum_level=0.95, hats="full", hats_alt="techno16", bass="house", bass_inst="pluck", bass_level=0.94, sub=0.6,
          comping="arp6", comp_level=0.17, perc=["shaker", "congas", "cajon"], perc_level=0.8, pad=1000, pad_level=0.45, choir="oo", choir_level=0.1, stabs="dub", stab_steps=(2, 10), stab_level=0.1, fill=True,
          melody=[mel("B", "flute", 0.26), mel("B", "steel", 0.12, octave=24, pan=-0.3, legato=0.7)]),
        S("verse2", 16, bpm=122, dyn=0.86, drums="house", drum_level=0.9, hats="eighths", hats_alt="offbeat", bass="house", bass_inst="pluck", bass_level=0.9, sub=0.55,
          comping="arp6", comp_level=0.16, perc=["shaker", "congas"], perc_level=0.75, pad=800, pad_level=0.5, fill=True,
          melody=[mel("A", "guitar", 0.4, ornaments=True, alt="flute", alt_level=0.24)], answer="flute", answer_level=0.12),
        S("quiet", 8, bpm=122, prog="quiet", dyn=0.7, bass="one", bass_inst="pluck", bass_level=0.7, sub=0.4, comping="arp6", comp_level=0.13, pad=650, pad_level=0.6,
          melody=[mel("frag", "guitar", 0.36, humanize=0.02, legato=1.2)], fx=["riser", "roll"], atmos=dict(crickets=0.4)),
        S("climax", 24, bpm=122, prog="major", dyn=1.0, drums="house", drum_level=1.0, hats="full", hats_alt="techno16", ride=True, bass="house", bass_inst="pluck", bass_level=0.98, sub=0.62,
          comping="arp6", comp_level=0.18, perc=["cajon", "shaker", "congas"], perc_level=0.85, pad=1300, pad_level=0.45, choir="ah", choir_level=0.14, fx=["crash"], fill=True,
          melody=[mel("Bmaj", "flute", 0.28), mel("Bmaj", "trumpet", 0.16, octave=12, pan=0.3, legato=0.85), mel("Bmaj", "steel", 0.1, octave=24, pan=-0.4, legato=0.6)]),
        S("mix_out", 8, bpm=122, prog="major", fill=True, **BEAT_IN),
    ]
    plan.append((sb, 360))

    t = by_nr(8)
    set_tempo(t, 122, 122)
    add_mix_in(t, 122)
    plan.append((t, 420))

    f = by_nr(9)                                   # Farola: einzige Atempause, ohne Beat
    f["sections"] = [
        S("lantern", 24, bpm=80, dyn=0.6, pad=550, choir="oo", choir_level=0.1, choir_every=2, fx=["bell"], bell_motif=[(0, 0), (8, 7)],
          melody=[mel("motif", "guitar", 0.32, legato=1.5, humanize=0.02)], atmos=dict(crickets=0.6)),
    ]
    if techno:                                     # Techno: Farola als Kick-Breakdown, der Beat laeuft durch
        f["sections"] = [
            S("mix_in", 8, bpm=132, **BEAT_IN),
            S("lantern", 16, bpm=132, dyn=0.7, drums="kickonly", drum_level=0.8, bass="one", bass_level=0.7, sub=0.45, pad=550,
              choir="oo", choir_level=0.1, choir_every=2, fx=["bell", "riser"], bell_motif=[(0, 0), (8, 7)],
              melody=[mel("motif", "guitar", 0.32, legato=1.5, humanize=0.02)], atmos=dict(crickets=0.4)),
            S("mix_out", 8, bpm=132, fill=True, **BEAT_IN),
        ]
    plan.append((f, 80))

    t = by_nr(10)                                  # Finale: Beat ab dem ersten Takt, Aufbau bis zum Schluss
    secs = {s["name"]: s for s in t["sections"]}
    secs["dawn"]["parts"].update(drums="house", drum_level=0.8, hats="offbeat", bass="house", bass_inst="pluck", bass_level=0.9, sub=0.5, dyn=0.8)
    secs["dawn"]["dyn"] = 0.8
    secs["dawn"]["bpm"] = 118
    secs["first_light"]["bpm"], secs["first_light"]["bpm_end"] = 118, 120
    secs["warming"]["bpm"], secs["warming"]["bpm_end"] = 120, 122
    secs["glow"]["bpm"], secs["glow"]["bpm_end"] = 122, 124
    for n in ("sun", "after1", "after2", "end"):
        secs[n]["bpm"] = 124
    secs["sun"]["bars"] = 40
    t["sections"] = [s for s in t["sections"] if s["name"] not in ("dawn",)]
    t["sections"].insert(0, S("mix_in", 8, bpm=118, **BEAT_IN))
    t["sections"].insert(1, secs["dawn"])
    plan.append((t, 480))

    out = []
    for spec, target in plan:
        # Drumlose 8-Takt-Intros direkt nach mix_in fallen im Mix weg: der Beat laeuft durch.
        secs = spec["sections"]
        if len(secs) > 2 and secs[0]["name"] == "mix_in" and not secs[1]["parts"].get("drums") and secs[1]["bars"] <= 8:
            del secs[1]
        club_tweaks(spec)
        if techno:
            retempo(spec, *TECHNO_BPM[spec["nr"]])
            techno_tweaks(spec)
        if spec["nr"] not in (9,) or techno:
            stretch(spec, target)
        if techno:
            techno_structure(spec)
        out.append(spec)
    return out


# --------------------------------------------------------------------------- #
# Club-Master
# --------------------------------------------------------------------------- #
def limiter(x, ceiling=0.95, lookahead_ms=2.0, release_ms=120.0):
    """Spitzenbegrenzer mit Vorausschau: Verstärkung wird weich abgesenkt, die Wellenform bleibt intakt."""
    from scipy.ndimage import minimum_filter1d
    blk = int(SR * 0.001)                         # 1-ms-Blöcke
    n = len(x)
    nb = (n + blk - 1) // blk
    pad = np.zeros((nb * blk, 2))
    pad[:n] = x
    peaks = np.abs(pad).reshape(nb, blk, 2).max(axis=(1, 2)) + 1e-9
    g = np.minimum(1.0, ceiling / peaks)
    g = minimum_filter1d(g, size=int(lookahead_ms) * 2 + 1)     # Vorausschau in beide Richtungen
    rel = np.exp(-1.0 / max(1.0, release_ms))                   # Release über Blöcke
    out = np.empty_like(g)
    cur = 1.0
    for i in range(nb):
        cur = g[i] if g[i] < cur else cur + (g[i] - cur) * (1.0 - rel)
        out[i] = cur
    gain = np.interp(np.arange(n), np.arange(nb) * blk + blk / 2, out)
    return x * gain[:, None]


def club_master(x):
    # Tiefbass formen: Rumpeln unter ~45 Hz absenken (kleine Lautsprecher/Handys verzerren dort),
    # dafuer Punch bei 60-140 Hz anheben. Nullphasige Filter, damit nichts ausloescht.
    x = ga.highpass(x, 32.0, 4)
    lo = signal.sosfiltfilt(signal.butter(2, 48.0, "low", fs=SR, output="sos"), x, axis=0)
    punch = signal.sosfiltfilt(signal.butter(2, [60.0, 140.0], "band", fs=SR, output="sos"), x, axis=0)
    x = x - 0.45 * lo + 0.35 * punch + 0.15 * ga.bandpass(x, 2000.0, 5000.0)
    del lo, punch
    win = SR
    n = len(x) // win
    blocks = np.sqrt(np.mean(x[: n * win].reshape(n, win, 2) ** 2, axis=(1, 2)))
    loud = np.percentile(blocks, 95) + 1e-9
    x *= 0.21 / loud
    x = ga.bus_compressor(x, threshold=0.3, ratio=2.0, attack=0.006, release=0.22)
    x = limiter(x, ceiling=0.95)
    return x


def render_part(spec, idx):
    os.makedirs(PARTS, exist_ok=True)
    album.master_chain = lambda x: x  # Master übernimmt club_master
    tr = Track(spec)

    def hook(t):
        mp = os.path.join(PARTS, f"{idx:02d}.mid")
        write_midi(t, mp)
        sf_render.replace_layers(t, mp, verbose=False)
    tr.pre_mix = hook
    pre = tr.render()
    del tr.layers
    sf.write(os.path.join(PARTS, f"{idx:02d}-pre.wav"), np.clip(pre / (np.abs(pre).max() + 1e-9) * 0.9, -1, 1).astype(np.float32), SR, subtype="FLOAT")
    x = club_master(pre)
    # Übergangsfenster: Länge von mix_in und mix_out in Samples
    names = [s["name"] for s in tr.sections]
    full_end = int(tr.bar_start[tr.total_bars] * SR)
    n_in = tr.s(tr.sec_start[names.index("mix_in")] + 8) if "mix_in" in names else int(8.0 * SR)
    n_out = (full_end - tr.s(tr.sec_start[names.index("mix_out")])) if "mix_out" in names else int(8.0 * SR)
    end = full_end if "mix_out" in names else len(x)
    x = x[:end]
    sf.write(os.path.join(PARTS, f"{idx:02d}.wav"), np.clip(x, -1, 1).astype(np.float32), SR, subtype="PCM_16")
    meta = dict(idx=idx, nr=spec["nr"], title=spec["title"], n=int(end), n_in=int(n_in), n_out=int(n_out), beat_in="mix_in" in names, beat_out="mix_out" in names)
    json.dump(meta, open(os.path.join(PARTS, f"{idx:02d}.json"), "w"))
    return meta


def _rms_env(x, win=SR // 2):
    """Blockweise RMS-Huellkurve (0,5 s), per Sample interpoliert."""
    n = max(1, len(x) // win)
    blk = np.sqrt(np.mean(x[: n * win].astype(np.float64).reshape(n, win, -1) ** 2, axis=(1, 2))) + 1e-6
    centers = (np.arange(n) + 0.5) * win
    return np.interp(np.arange(len(x)), centers, blk)


def _match_level(seg, ref, window, max_gain=2.0):
    """Hebt einen duennen Abschnitt auf den Referenzpegel an (max. +6 dB), gewichtet mit window (0..1)."""
    env = _rms_env(seg)
    g = np.clip(ref / env, 1.0, max_gain)
    gain = (1.0 + (g - 1.0) * window)[:, None]
    return limiter(seg.astype(np.float64) * gain, ceiling=0.95).astype(np.float32)


def assemble(metas):
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, MIX_NAME + ".wav")
    writer = sf.SoundFile(path, "w", SR, 2, subtype="PCM_16")
    chapters = []
    pos = 0            # Startposition des aktuellen Teils im Mix
    tail = None        # noch nicht geschriebener Ausklang des vorherigen Teils
    ref_body = 20 * SR
    for k, m in enumerate(metas):
        x, _ = sf.read(os.path.join(PARTS, f"{m['idx']:02d}.wav"), dtype="float32")
        n_tail = m["n_out"] if m["beat_out"] else min(int(8.0 * SR), len(x) // 3)
        if tail is None:
            head_len = 0
        else:
            L = min(len(tail), m["n_in"], len(x) // 2)
            # Pegelausgleich: mix_in/intro sind duenner als der Groove danach -> auf dessen
            # Pegel anheben; die Anhebung laeuft ueber 2*L auf 1.0 zurueck.
            R = min(2 * L, len(x) - n_tail)
            ref_in = np.sqrt(np.mean(x[R: R + ref_body].astype(np.float64) ** 2))
            w = np.ones(R)
            w[L:] = np.linspace(1, 0, R - L)
            x[:R] = _match_level(x[:R], ref_in, w)
            t = np.linspace(0, 1, L)[:, None]
            a = tail[:L]
            # Bass des ausgehenden Teils ausblenden (Hochpass mischt sich ein), Lautstärke gleichmächtig
            a_hp = ga.highpass(a.astype(np.float64), 220.0).astype(np.float32)
            w = np.clip(t * 2, 0, 1)
            a = a * (1 - w) + a_hp * w
            fade_out = np.cos(t * np.pi / 2)
            fade_in = np.sin(t * np.pi / 2)
            mixed = a * fade_out + x[:L] * fade_in
            mixed = limiter(mixed.astype(np.float64), ceiling=0.95).astype(np.float32)
            writer.write(np.clip(mixed, -1, 1))
            head_len = L
        chapters.append((pos, m["title"]))
        body = x[head_len: len(x) - n_tail]
        writer.write(body)
        tail = x[len(x) - n_tail:]
        if m["beat_out"]:
            # mix_out ebenfalls auf den Pegel des Grooves davor anheben
            ref_out = np.sqrt(np.mean(x[len(x) - n_tail - ref_body: len(x) - n_tail].astype(np.float64) ** 2))
            tail = _match_level(tail, ref_out, np.ones(len(tail)))
        pos_next = pos + len(x) - n_tail
        pos = pos_next
    writer.write(tail)
    writer.close()
    total = pos + len(tail)
    with open(os.path.join(OUT, "chapters.txt"), "w", encoding="utf-8") as fh:
        for p_, title in chapters:
            s_ = p_ / SR
            fh.write(f"{int(s_ // 60):02d}:{int(s_ % 60):02d} {title}\n")
        fh.write(f"\nGesamt {int(total / SR // 60)}:{int(total / SR % 60):02d}\n")
    print("Mix:", path, f"{total / SR / 60:.1f} min")
    return path


def encode(path):
    import lameenc
    x, sr = sf.read(path, dtype="int16")
    enc = lameenc.Encoder()
    enc.set_bit_rate(320)
    enc.set_in_sample_rate(sr)
    enc.set_channels(2)
    enc.set_quality(2)
    mp3 = path[:-4] + ".mp3"
    with open(mp3, "wb") as fh:
        fh.write(enc.encode(x.tobytes()) + enc.flush())
    sf.write(path[:-4] + ".flac", x, sr, subtype="PCM_16")
    print("MP3 und FLAC geschrieben")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--assemble", action="store_true")
    ap.add_argument("--only", type=int, default=None, help="nur Teil-Index rendern (1..10)")
    ap.add_argument("--remaster", action="store_true", help="vorhandene *-pre.wav neu mastern, ohne Render")
    ap.add_argument("--techno", action="store_true", help="Techno-Fassung (126-134 BPM) nach out/mix-techno/")
    args = ap.parse_args()
    global OUT, PARTS, MIX_NAME
    if args.techno:
        OUT = os.path.join(HERE, "out", "mix-techno")
        PARTS = os.path.join(OUT, "parts")
        MIX_NAME = "Sounds-of-Marbella-2026-Techno-Mix"
        sf_render.SF_MAP = {k: v for k, v in sf_render.SF_MAP.items() if k != "Bass"}   # Synth-Bass bleibt synthetisch
    if args.remaster:
        for i in range(1, 11):
            pre_path = os.path.join(PARTS, f"{i:02d}-pre.wav")
            if not os.path.exists(pre_path):
                continue
            pre, _ = sf.read(pre_path, dtype="float64")
            x = club_master(pre)
            meta = json.load(open(os.path.join(PARTS, f"{i:02d}.json")))
            sf.write(os.path.join(PARTS, f"{i:02d}.wav"), np.clip(x[: meta["n"]], -1, 1).astype(np.float32), SR, subtype="PCM_16")
            print(f"  Teil {i} neu gemastert", flush=True)
        args.assemble = True
    plan = build_plan(techno=args.techno)
    if args.techno:
        for spec in plan:
            spec["title"] = spec["title"].split(" (")[0]
    for i, spec in enumerate(plan, 1):
        d = album.track_duration(spec) - 10
        print(f"  {i:2d}. {spec['title']:45s} {int(d // 60)}:{int(d % 60):02d}", flush=True)
    if not args.assemble:
        for i, spec in enumerate(plan, 1):
            if args.only and i != args.only:
                continue
            print(f"[{i}/10] {spec['title']} ...", flush=True)
            m = render_part(spec, i)
            print(f"    {m['n'] / SR / 60:.1f} min", flush=True)
    if args.only:
        return
    metas = [json.load(open(os.path.join(PARTS, f"{i:02d}.json"))) for i in range(1, len(plan) + 1)]
    path = assemble(metas)
    encode(path)


if __name__ == "__main__":
    main()

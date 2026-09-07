#!/usr/bin/env python3
"""
Songform-Komposition mit handgeschriebenen Themen für das Album
"Sounds of Marbella 2026" (DJ Jensi).

Jeder Titel ist ein erzählter Song: Intro, Strophe, Strophe, Refrain, Strophe,
Refrain, Zwischenteil mit Stille, Höhepunkt (einen Ganzton höher moduliert),
Coda mit dem Hauptthema, das im Meer ausläuft.

Alle Themen, Gegenmelodien und Akkordfolgen sind hier notiert und eigene
Kompositionen. Klangerzeugung: generate_album.py (Synthese) plus die hier
modellierten "akustischen" Instrumente: Konzertgitarre (gezupft, Rasgueado,
Tremolo, Picado), Trompete und Bläsersatz, Flöte, Steel Drum, E-Bass, Cajón,
Palmas, Kastagnetten, Congas.

    python3 compose_song.py                 # alle Titel nach ./out
    python3 compose_song.py --track 3       # nur Titel 3
    python3 compose_song.py --wav           # zusätzlich WAV
"""
import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import generate_album as ga  # noqa: E402
from generate_album import (SR, place, to_stereo, lowpass, highpass, bandpass, reverb, delay, chorus_widen,  # noqa: E402
                            make_reverb_ir, kick, hat, clap, shaker, snare_layer, ride, crash, rim, open_hat_909,
                            synth_bass, pad_chord, ks_guitar, lead, supersaw_lead, trance_pluck, riser, acid_note,
                            house_stab, ocean, seagulls, master_chain, midi_to_hz, soft_clip, fit, envelope, saw)

ALBUM_TITLE = "Sounds of Marbella 2026"
ALBUM_ARTIST = "DJ Jensi"


# --------------------------------------------------------------------------- #
# Modellierte Instrumente
# --------------------------------------------------------------------------- #
def nylon_guitar(rng, midi, n_hold, level=0.4, pan=0.0):
    sig = ks_guitar(rng, midi, n_hold, level=level, damp=0.9935, pan=pan)
    return lowpass(sig, 4200.0)


def strum_chord(rng, midis, n_hold, level=0.3, spread=0.016, pan=0.0, down=True, muted=False):
    """Rasgueado/Anschlag: Saiten zeitlich versetzt, optional abgedämpft."""
    order = list(midis) if down else list(midis)[::-1]
    n = n_hold + int(1.4 * SR) + int(spread * SR * len(order))
    out = np.zeros((n, 2))
    for i, m in enumerate(order):
        g = ks_guitar(rng, m, n_hold, level=level * (0.8 + 0.2 * (i == 0)), damp=0.985 if muted else 0.9935,
                      pan=pan + (i - len(order) / 2) * 0.07)
        place(out, int(i * spread * SR), lowpass(g, 3800.0))
    return out


def tremolo_note(rng, midi, n_hold, level=0.3, pan=0.0, rate=11.0):
    """Tremolo-Gitarre: schnelle Wiederholung derselben Note."""
    n = n_hold + int(1.2 * SR)
    out = np.zeros((n, 2))
    step = int(SR / rate)
    k = 0
    pos = 0
    while pos < n_hold:
        out_sig = nylon_guitar(rng, midi, int(step * 0.9), level=level * rng.uniform(0.75, 1.0) * (1.0 if k % 3 == 0 else 0.8), pan=pan)
        place(out, pos, out_sig)
        pos += step
        k += 1
    return out


def steel_drum(rng, midi, n_hold, level=0.3, pan=0.0):
    f = float(midi_to_hz(midi))
    n = n_hold + int(1.4 * SR)
    t = np.arange(n) / SR
    bend = 1.0 + 0.012 * np.exp(-t * 40.0)
    x = np.zeros(n)
    for ratio, amp, dec in ((1.0, 1.0, 2.2), (2.0, 0.55, 3.5), (3.0, 0.3, 5.0), (4.05, 0.18, 7.0), (5.6, 0.08, 9.0)):
        ph = np.cumsum(f * ratio * bend) / SR
        x += amp * np.sin(2 * np.pi * ph + rng.random() * 6.28) * np.exp(-t * dec)
    x += 0.2 * highpass(rng.standard_normal(n), 3000.0) * np.exp(-t * 90.0)
    env = fit(envelope(n_hold, 0.002, 0.6, 0.5, 0.9), n)
    x = soft_clip(x * env * 1.2, 1.4)
    return to_stereo(x * level, pan)


def flute(rng, midi, n_hold, level=0.3, pan=0.0):
    f = float(midi_to_hz(midi))
    n = n_hold + int(0.5 * SR)
    t = np.arange(n) / SR
    vib = 1.0 + 0.004 * np.sin(2 * np.pi * 5.0 * t) * np.clip((t - 0.15) / 0.3, 0.0, 1.0)
    ph = np.cumsum(f * vib) / SR
    x = np.sin(2 * np.pi * ph) + 0.25 * np.sin(2 * np.pi * 2 * ph) + 0.08 * np.sin(2 * np.pi * 3 * ph)
    breath = bandpass(rng.standard_normal(n), f * 0.7, f * 1.6) * 0.18
    breath *= 1.0 + 1.5 * np.exp(-t * 12.0)
    env = fit(envelope(n_hold, 0.07, 0.2, 0.85, 0.22), n)
    x = (x + breath) * env
    return to_stereo(lowpass(x, 7000.0) * level, pan)


def trumpet(rng, midi, n_hold, level=0.3, pan=0.0):
    """Trompete: Sägezahn durch Formantfilter, Ansatz-Scoop, Vibrato, Sättigung."""
    f = float(midi_to_hz(midi))
    n = n_hold + int(0.45 * SR)
    t = np.arange(n) / SR
    scoop = 1.0 - 0.03 * np.exp(-t * 35.0)
    vib = 1.0 + 0.0045 * np.sin(2 * np.pi * 5.5 * t) * np.clip((t - 0.2) / 0.3, 0.0, 1.0)
    ph = np.cumsum(f * scoop * vib) / SR
    x = 2.0 * (ph % 1.0) - 1.0
    y = 0.55 * bandpass(x, 700.0, 1500.0) + 0.5 * bandpass(x, 1700.0, 3200.0) + 0.4 * lowpass(x, 1100.0)
    y += 0.06 * bandpass(rng.standard_normal(n), 2000.0, 6000.0) * np.exp(-t * 20.0)
    env = fit(envelope(n_hold, 0.045, 0.15, 0.85, 0.12), n)
    bright = 0.6 + 0.4 * np.clip(t / 0.12, 0.0, 1.0)
    y = soft_clip(y * env * bright * 1.6, 1.3)
    return to_stereo(y * level, pan)


def brass_stab(rng, midis, n_hold, level=0.3, pan=0.0):
    """Bläsersatz-Stab: drei leicht verstimmte Trompeten plus Oktave darunter."""
    n = n_hold + int(0.6 * SR)
    out = np.zeros((n, 2))
    for m in midis:
        for cents, pn in ((-6.0, -0.3), (0.0, 0.0), (6.0, 0.3)):
            sig = trumpet(rng, m + cents / 100.0, n_hold, level=level * 0.4, pan=pan + pn)
            place(out, int(rng.uniform(0, 0.012) * SR), sig)
    place(out, 0, trumpet(rng, midis[0] - 12, n_hold, level=level * 0.5, pan=pan))
    return out


def pluck_bass(rng, midi, n_hold, level=0.6):
    sig = ks_guitar(rng, midi, n_hold, level=1.0, damp=0.998, pan=0.0)
    n = len(sig)
    t = np.arange(n) / SR
    x = lowpass(sig[:, 0], 900.0)
    x += 0.5 * np.sin(2 * np.pi * float(midi_to_hz(midi)) * t) * fit(envelope(n_hold, 0.005, 0.3, 0.7, 0.15), n)
    x = soft_clip(x * 1.6, 1.5)
    return to_stereo(highpass(x, 30.0) * level, 0.0)


def cajon_bass(rng, level=0.6):
    n = int(0.3 * SR)
    t = np.arange(n) / SR
    f = 72.0 + 40.0 * np.exp(-t * 45.0)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 16.0)
    x += 0.5 * lowpass(rng.standard_normal(n), 500.0) * np.exp(-t * 45.0)
    x += 0.15 * bandpass(rng.standard_normal(n), 1500.0, 4000.0) * np.exp(-t * 120.0)
    return to_stereo(soft_clip(x * 1.3, 1.4) * level, 0.0)


def cajon_slap(rng, level=0.45):
    n = int(0.18 * SR)
    t = np.arange(n) / SR
    x = bandpass(rng.standard_normal(n), 1400.0, 6500.0) * np.exp(-t * 40.0)
    x += 0.35 * np.sin(2 * np.pi * 320.0 * t) * np.exp(-t * 70.0)
    x += 0.2 * lowpass(rng.standard_normal(n), 400.0) * np.exp(-t * 90.0)
    return to_stereo(x * level, 0.1)


def palmas(rng, bright=True, level=0.4):
    """Flamenco-Handclaps: zwei Personen, leicht versetzt. bright = 'secas', sonst 'sordas'."""
    n = int(0.16 * SR)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for off, amp in ((0.0, 1.0), (0.009, 0.8), (0.017, 0.5)):
        g = (t >= off) * np.exp(-np.maximum(t - off, 0) * (70.0 if bright else 55.0))
        x += amp * rng.standard_normal(n) * g
    x = bandpass(x, 1800.0, 6500.0) if bright else bandpass(x, 500.0, 2400.0)
    return to_stereo(x * level, -0.2 if bright else 0.25)


def castanet(rng, level=0.3):
    n = int(0.09 * SR)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for off in (0.0, 0.028):
        g = (t >= off) * np.exp(-np.maximum(t - off, 0) * 260.0)
        x += bandpass(rng.standard_normal(n), 3200.0, 7500.0) * g
        x += 0.6 * np.sin(2 * np.pi * 4300.0 * t) * g
    return to_stereo(x * level, 0.45)


# --------------------------------------------------------------------------- #
# Harmonik
#   Akkorde als Halbtöne relativ zum Grundton; die Voicing-Funktion stapelt sie kompakt.
# --------------------------------------------------------------------------- #
CH = {
    # Moll/Äolisch, Dorisch, Phrygisch
    "i": [0, 3, 7], "i7": [0, 3, 7, 10], "i9": [0, 3, 7, 10, 14],
    "bII": [1, 5, 8], "bII7": [1, 5, 8, 12], "II7": [2, 5, 9, 12], "ii7": [2, 5, 9, 12],
    "III": [3, 7, 10], "III7": [3, 7, 10, 14], "bIII": [3, 7, 10],
    "iv": [5, 8, 12], "iv7": [5, 8, 12, 15], "IV": [5, 9, 12], "IV7": [5, 9, 12, 15],
    "v": [7, 10, 14], "v7": [7, 10, 14, 17], "V": [7, 11, 14], "V7": [7, 11, 14, 17],
    "VI": [8, 12, 15], "VI7": [8, 12, 15, 19], "bVI": [8, 12, 15],
    "VII": [10, 14, 17], "VII7": [10, 14, 17, 20], "bVII": [10, 14, 17], "bvii": [10, 13, 17],
    # Dur / Mixolydisch / Phrygisch-dominant
    "I": [0, 4, 7], "I7": [0, 4, 7, 11], "I9": [0, 4, 7, 11, 14], "vi": [9, 12, 16], "vi7": [9, 12, 16, 19],
    "ii": [2, 5, 9], "iii": [4, 7, 11], "IVmaj": [5, 9, 12, 16], "IVadd9": [5, 9, 12, 19],
    "bIImaj": [1, 5, 8],
}


def voice(tones, root, low=0, high=19):
    """Kompaktes Voicing: Töne aufsteigend gestapelt, in den Bereich root+low .. root+high gefaltet."""
    pcs = []
    for t_ in tones:
        pc = t_ % 12
        if pc not in pcs:
            pcs.append(pc)
    out = []
    cur = pcs[0]
    for pc in pcs:
        while pc < cur:
            pc += 12
        out.append(pc)
        cur = pc
    out = [p if p <= high else p - 12 for p in out]
    return sorted(root + p for p in out)


# --------------------------------------------------------------------------- #
# Songform (Standard; einzelne Titel überschreiben)
#   (Name, Takte, Grundton-Verschiebung, Akkordfolge-Schlüssel, Dynamik)
# --------------------------------------------------------------------------- #
def default_sections(intro=8, coda=12, climax=16, refrain=8):
    return [
        ("intro", intro, 0, "verse", 0.62),
        ("verse1", 8, 0, "verse", 0.72),
        ("verse2", 8, 0, "verse", 0.82),
        ("refrain1", refrain, 0, "refrain", 0.90),
        ("verse3", 8, 0, "verse", 0.80),
        ("refrain2", refrain, 0, "refrain", 0.95),
        ("bridge", 8, 0, "bridge", 0.66),
        ("climax", climax, 2, "climax", 1.00),
        ("coda", coda, 2, "verse", 0.70),
    ]


# --------------------------------------------------------------------------- #
# Die Titel: Themen als Phrasen [(pos8, halbton, dauer8), ...], 4 Takte je Phrase
# --------------------------------------------------------------------------- #
SONGS = [
    dict(nr=1, title="La Fontanilla Sunrise", seed=1101, bpm=118, root=52, mode="E phrygisch",
         scale=[0, 1, 3, 5, 7, 8, 10],
         progs=dict(verse=["i", "bII", "bIII", "bII"], refrain=["bVI", "bvii", "i", "bII"],
                    bridge=["iv7", "bIII", "bII", "bII"], climax=["bVI", "bvii", "i9", "bII"]),
         theme_a=[[(0, 7, 2), (2, 8, 1), (3, 7, 1), (4, 3, 4), (8, 5, 2), (10, 8, 2), (12, 13, 2), (14, 12, 2),
                   (16, 10, 3), (19, 12, 1), (20, 7, 2), (22, 10, 2), (24, 8, 4), (28, 7, 2), (30, 5, 2)],
                  [(0, 7, 2), (2, 8, 1), (3, 7, 1), (4, 3, 4), (8, 5, 2), (10, 8, 2), (12, 12, 2), (14, 15, 2),
                   (16, 13, 3), (19, 12, 1), (20, 10, 2), (22, 8, 2), (24, 7, 4), (28, 1, 2), (30, 0, 2)]],
         theme_b=[[(0, 12, 2), (2, 15, 1), (3, 12, 1), (4, 8, 2), (6, 7, 2), (8, 10, 2), (10, 13, 1), (11, 10, 1),
                   (12, 8, 2), (14, 5, 2), (16, 7, 3), (19, 8, 1), (20, 12, 2), (22, 15, 2),
                   (24, 13, 2), (26, 12, 2), (28, 13, 2), (30, 12, 2)],
                  [(0, 12, 2), (2, 15, 1), (3, 12, 1), (4, 8, 2), (6, 7, 2), (8, 10, 2), (10, 13, 1), (11, 10, 1),
                   (12, 8, 2), (14, 5, 2), (16, 7, 2), (18, 8, 2), (20, 10, 2), (22, 12, 2), (24, 13, 3), (27, 12, 1), (28, 12, 4)]],
         palette=dict(intro="guitar", verse1="flute", verse2="guitar_trem", refrain=["flute", "guitar"], verse3="guitar",
                      bridge="guitar", climax=["trumpet", "flute"], counter="steel", answer="steel",
                      comping="strum", perc=["congas", "palmas"], acid=False, stabs=None, hook=False, cajon=True),
         sections=default_sections(intro=12, coda=12)),

    dict(nr=2, title="La Concha Horizon", seed=2202, bpm=122, root=50, mode="D-Moll, andalusische Kadenz",
         scale=[0, 2, 3, 5, 7, 8, 10],
         progs=dict(verse=["i", "VII", "VI", "V"], refrain=["VI", "VII", "i", "V7"],
                    bridge=["iv7", "V", "iv7", "V"], climax=["VI7", "VII", "i9", "V7"]),
         theme_a=[[(0, 12, 3), (3, 10, 1), (4, 8, 2), (6, 7, 2), (8, 7, 2), (10, 10, 2), (12, 12, 3), (15, 10, 1),
                   (16, 8, 3), (19, 7, 1), (20, 5, 2), (22, 3, 2), (24, 2, 3), (27, 11, 1), (28, 7, 4)],
                  [(0, 12, 3), (3, 10, 1), (4, 8, 2), (6, 7, 2), (8, 7, 2), (10, 10, 2), (12, 14, 2), (14, 15, 2),
                   (16, 12, 3), (19, 10, 1), (20, 8, 2), (22, 7, 2), (24, 5, 2), (26, 3, 2), (28, 2, 2), (30, 11, 2)]],
         theme_b=[[(0, 7, 1), (1, 8, 1), (2, 10, 2), (4, 12, 4), (8, 10, 1), (9, 12, 1), (10, 14, 2), (12, 15, 2), (14, 14, 2),
                   (16, 12, 3), (19, 10, 1), (20, 7, 2), (22, 8, 2), (24, 7, 2), (26, 11, 2), (28, 14, 4)],
                  [(0, 7, 1), (1, 8, 1), (2, 10, 2), (4, 12, 4), (8, 10, 1), (9, 12, 1), (10, 14, 2), (12, 15, 2), (14, 14, 2),
                   (16, 12, 2), (18, 15, 2), (20, 17, 2), (22, 15, 2), (24, 14, 2), (26, 11, 2), (28, 12, 4)]],
         palette=dict(intro="guitar_trem", verse1="guitar", verse2="guitar", refrain=["trumpet", "guitar"], verse3="guitar_trem",
                      bridge="guitar", climax=["trumpet", "hook"], counter="steel", answer="guitar",
                      comping="rumba", perc=["palmas", "cajon", "congas", "castanets"], acid=True, stabs="brass", hook=True, cajon=True),
         sections=default_sections()),

    dict(nr=3, title="Golden Mile Breeze", seed=3303, bpm=124, root=55, mode="G mixolydisch, Rumba",
         scale=[0, 2, 4, 5, 7, 9, 10],
         progs=dict(verse=["I", "bVII", "IV", "I"], refrain=["IV", "V", "I", "bVII"],
                    bridge=["vi7", "IV", "ii7", "V"], climax=["IVmaj", "V", "I9", "bVII"]),
         theme_a=[[(0, 7, 1), (1, 9, 1), (2, 7, 2), (4, 4, 2), (6, 7, 2), (8, 10, 2), (10, 9, 1), (11, 7, 1), (12, 5, 2), (14, 9, 2),
                   (16, 12, 3), (19, 9, 1), (20, 7, 2), (22, 5, 2), (24, 4, 2), (26, 2, 2), (28, 0, 4)],
                  [(0, 7, 1), (1, 9, 1), (2, 7, 2), (4, 4, 2), (6, 7, 2), (8, 10, 2), (10, 12, 2), (12, 14, 2), (14, 12, 2),
                   (16, 9, 3), (19, 7, 1), (20, 5, 2), (22, 4, 2), (24, 2, 2), (26, 4, 2), (28, 7, 4)]],
         theme_b=[[(0, 12, 2), (2, 14, 1), (3, 12, 1), (4, 9, 2), (6, 7, 2), (8, 11, 1), (9, 9, 1), (10, 11, 2), (12, 14, 2), (14, 12, 2),
                   (16, 16, 3), (19, 14, 1), (20, 12, 2), (22, 9, 2), (24, 10, 2), (26, 9, 2), (28, 7, 4)],
                  [(0, 12, 2), (2, 14, 1), (3, 12, 1), (4, 9, 2), (6, 7, 2), (8, 11, 1), (9, 9, 1), (10, 11, 2), (12, 14, 2), (14, 12, 2),
                   (16, 16, 2), (18, 14, 2), (20, 16, 2), (22, 19, 2), (24, 17, 2), (26, 16, 2), (28, 12, 4)]],
         palette=dict(intro="guitar", verse1="guitar", verse2="trumpet", refrain=["trumpet", "guitar"], verse3="guitar",
                      bridge="guitar", climax=["trumpet", "flute"], counter="steel", answer="guitar",
                      comping="rumba", perc=["palmas", "cajon", "castanets", "congas"], acid=False, stabs="brass", hook=False, cajon=True),
         sections=default_sections(climax=16, coda=8)),

    dict(nr=4, title="Cabopino Drum Circle", seed=4404, bpm=120, root=57, mode="A phrygisch-dominant",
         scale=[0, 1, 4, 5, 7, 8, 10],
         progs=dict(verse=["I", "bIImaj", "I", "bIImaj"], refrain=["iv", "bVI", "bIImaj", "I"],
                    bridge=["bVI", "bvii", "bIImaj", "bIImaj"], climax=["iv7", "bVI", "bIImaj", "I"]),
         theme_a=[[(0, 4, 2), (2, 5, 1), (3, 4, 1), (4, 0, 2), (6, 7, 2), (8, 8, 2), (10, 7, 1), (11, 5, 1), (12, 1, 2), (14, 5, 2),
                   (16, 4, 3), (19, 7, 1), (20, 12, 2), (22, 10, 2), (24, 8, 4), (28, 7, 2), (30, 5, 2)],
                  [(0, 4, 2), (2, 5, 1), (3, 4, 1), (4, 0, 2), (6, 7, 2), (8, 8, 2), (10, 10, 2), (12, 12, 2), (14, 13, 2),
                   (16, 12, 3), (19, 10, 1), (20, 8, 2), (22, 7, 2), (24, 5, 2), (26, 1, 2), (28, 0, 4)]],
         theme_b=[[(0, 12, 2), (2, 13, 1), (3, 12, 1), (4, 8, 2), (6, 5, 2), (8, 8, 2), (10, 12, 1), (11, 8, 1), (12, 15, 2), (14, 12, 2),
                   (16, 13, 3), (19, 12, 1), (20, 8, 2), (22, 5, 2), (24, 4, 2), (26, 7, 2), (28, 12, 4)],
                  [(0, 12, 2), (2, 13, 1), (3, 12, 1), (4, 8, 2), (6, 5, 2), (8, 8, 2), (10, 12, 1), (11, 8, 1), (12, 15, 2), (14, 12, 2),
                   (16, 13, 2), (18, 12, 2), (20, 10, 2), (22, 8, 2), (24, 7, 2), (26, 4, 2), (28, 12, 4)]],
         palette=dict(intro="guitar", verse1="guitar", verse2="guitar", refrain=["flute", "guitar"], verse3="guitar_trem",
                      bridge="guitar", climax=["trumpet", "guitar"], counter="steel", answer="steel",
                      comping="rumba", perc=["cajon", "congas", "palmas", "castanets"], acid=True, stabs=None, hook=False, cajon=True),
         sections=default_sections(intro=8, coda=10)),

    dict(nr=5, title="Puerto Banús Nights", seed=5505, bpm=122, root=57, mode="A-Moll",
         scale=[0, 2, 3, 5, 7, 8, 10],
         progs=dict(verse=["i7", "VI7", "III7", "VII"], refrain=["VI7", "VII", "i7", "III7"],
                    bridge=["iv7", "v7", "VI7", "VI7"], climax=["VI7", "VII", "i9", "III7"]),
         theme_a=[[(0, 7, 3), (3, 12, 1), (4, 10, 2), (6, 7, 2), (8, 8, 3), (11, 12, 1), (12, 15, 2), (14, 12, 2),
                   (16, 10, 3), (19, 7, 1), (20, 3, 2), (22, 7, 2), (24, 5, 4), (28, 2, 2), (30, 5, 2)],
                  [(0, 7, 3), (3, 12, 1), (4, 10, 2), (6, 7, 2), (8, 8, 2), (10, 10, 2), (12, 12, 2), (14, 15, 2),
                   (16, 14, 3), (19, 12, 1), (20, 10, 2), (22, 7, 2), (24, 3, 4), (28, 0, 4)]],
         theme_b=[[(0, 0, 2), (2, 3, 1), (3, 5, 1), (4, 7, 4), (8, 5, 2), (10, 3, 1), (11, 5, 1), (12, 7, 2), (14, 10, 2),
                   (16, 12, 3), (19, 10, 1), (20, 7, 2), (22, 3, 2), (24, 5, 2), (26, 3, 2), (28, 0, 4)],
                  [(0, 0, 2), (2, 3, 1), (3, 5, 1), (4, 7, 4), (8, 5, 2), (10, 3, 1), (11, 5, 1), (12, 7, 2), (14, 10, 2),
                   (16, 12, 2), (18, 14, 2), (20, 15, 2), (22, 12, 2), (24, 10, 2), (26, 7, 2), (28, 7, 4)]],
         palette=dict(intro="guitar", verse1="flute", verse2="lead", refrain=["lead", "steel"], verse3="guitar",
                      bridge="guitar", climax=["hook", "lead"], counter="steel", answer="steel",
                      comping="strum", perc=["congas"], acid=True, stabs="house", hook=True, cajon=False),
         sections=default_sections()),

    dict(nr=6, title="Sierra Blanca Drift", seed=6606, bpm=118, root=52, mode="E dorisch",
         scale=[0, 2, 3, 5, 7, 9, 10],
         progs=dict(verse=["i7", "IV", "i7", "bVII"], refrain=["IV", "bVII", "i7", "IV"],
                    bridge=["ii7", "IV", "ii7", "bVII"], climax=["IVadd9", "bVII", "i9", "IV"]),
         theme_a=[[(0, 7, 3), (3, 9, 1), (4, 7, 2), (6, 3, 2), (8, 5, 2), (10, 9, 2), (12, 12, 3), (15, 9, 1),
                   (16, 7, 3), (19, 5, 1), (20, 3, 2), (22, 2, 2), (24, 5, 4), (28, 2, 2), (30, 5, 2)],
                  [(0, 7, 3), (3, 9, 1), (4, 7, 2), (6, 3, 2), (8, 5, 2), (10, 9, 2), (12, 14, 2), (14, 12, 2),
                   (16, 10, 3), (19, 9, 1), (20, 7, 2), (22, 5, 2), (24, 3, 4), (28, 0, 4)]],
         theme_b=[[(0, 9, 2), (2, 12, 1), (3, 14, 1), (4, 17, 4), (8, 14, 2), (10, 12, 1), (11, 14, 1), (12, 10, 2), (14, 12, 2),
                   (16, 15, 3), (19, 14, 1), (20, 12, 2), (22, 7, 2), (24, 9, 2), (26, 12, 2), (28, 9, 4)],
                  [(0, 9, 2), (2, 12, 1), (3, 14, 1), (4, 17, 4), (8, 14, 2), (10, 12, 1), (11, 14, 1), (12, 10, 2), (14, 12, 2),
                   (16, 15, 2), (18, 14, 2), (20, 15, 2), (22, 17, 2), (24, 14, 2), (26, 12, 2), (28, 12, 4)]],
         palette=dict(intro="guitar", verse1="flute", verse2="guitar", refrain=["flute", "steel"], verse3="guitar_trem",
                      bridge="guitar", climax=["trumpet", "flute"], counter="guitar", answer="steel",
                      comping="strum", perc=["congas", "palmas"], acid=False, stabs=None, hook=False, cajon=True),
         sections=default_sections(coda=12)),

    dict(nr=7, title="Casco Antiguo Echoes", seed=7707, bpm=124, root=59, mode="H phrygisch",
         scale=[0, 1, 3, 5, 7, 8, 10],
         progs=dict(verse=["i", "bII", "i", "bvii"], refrain=["bVI", "bvii", "i", "bII"],
                    bridge=["iv7", "bIII", "bII", "bII"], climax=["bVI", "bvii", "i9", "bII"]),
         theme_a=[[(0, 3, 2), (2, 5, 1), (3, 3, 1), (4, 1, 2), (6, 0, 2), (8, 5, 2), (10, 7, 2), (12, 8, 3), (15, 7, 1),
                   (16, 3, 3), (19, 5, 1), (20, 7, 2), (22, 10, 2), (24, 8, 4), (28, 7, 2), (30, 5, 2)],
                  [(0, 3, 2), (2, 5, 1), (3, 3, 1), (4, 1, 2), (6, 0, 2), (8, 5, 2), (10, 7, 2), (12, 10, 2), (14, 12, 2),
                   (16, 13, 3), (19, 12, 1), (20, 10, 2), (22, 8, 2), (24, 7, 2), (26, 3, 2), (28, 1, 2), (30, 0, 2)]],
         theme_b=[[(0, 12, 2), (2, 15, 1), (3, 12, 1), (4, 8, 2), (6, 7, 2), (8, 10, 2), (10, 12, 1), (11, 13, 1), (12, 12, 2), (14, 10, 2),
                   (16, 7, 3), (19, 8, 1), (20, 12, 2), (22, 15, 2), (24, 13, 2), (26, 12, 2), (28, 13, 4)],
                  [(0, 12, 2), (2, 15, 1), (3, 12, 1), (4, 8, 2), (6, 7, 2), (8, 10, 2), (10, 12, 1), (11, 13, 1), (12, 12, 2), (14, 10, 2),
                   (16, 7, 2), (18, 10, 2), (20, 12, 2), (22, 15, 2), (24, 17, 2), (26, 15, 2), (28, 12, 4)]],
         palette=dict(intro="guitar", verse1="trumpet", verse2="guitar", refrain=["trumpet", "guitar"], verse3="guitar",
                      bridge="guitar", climax=["trumpet", "lead"], counter="steel", answer="guitar",
                      comping="rumba", perc=["palmas", "cajon", "castanets"], acid=True, stabs="brass", hook=False, cajon=True,
                      dub=True),
         sections=default_sections()),

    dict(nr=8, title="Playa de Nagüeles, 6 a.m.", seed=8808, bpm=116, root=50, mode="D dorisch",
         scale=[0, 2, 3, 5, 7, 9, 10],
         progs=dict(verse=["i7", "IV", "i7", "IV"], refrain=["bVII", "IV", "i7", "ii7"],
                    bridge=["ii7", "bVII", "ii7", "IV"], climax=["bVII", "IVadd9", "i9", "ii7"]),
         theme_a=[[(0, 7, 4), (4, 9, 2), (6, 7, 2), (8, 5, 3), (11, 7, 1), (12, 3, 4), (16, 2, 2), (18, 3, 2), (20, 7, 2), (22, 12, 2),
                   (24, 9, 4), (28, 7, 4)],
                  [(0, 7, 4), (4, 9, 2), (6, 7, 2), (8, 5, 2), (10, 7, 2), (12, 9, 2), (14, 12, 2), (16, 14, 3), (19, 12, 1), (20, 9, 2), (22, 7, 2),
                   (24, 5, 4), (28, 0, 4)]],
         theme_b=[[(0, 12, 3), (3, 14, 1), (4, 12, 2), (6, 9, 2), (8, 7, 2), (10, 9, 1), (11, 7, 1), (12, 5, 2), (14, 7, 2),
                   (16, 12, 3), (19, 15, 1), (20, 14, 2), (22, 12, 2), (24, 9, 2), (26, 7, 2), (28, 7, 4)],
                  [(0, 12, 3), (3, 14, 1), (4, 12, 2), (6, 9, 2), (8, 7, 2), (10, 9, 1), (11, 7, 1), (12, 5, 2), (14, 7, 2),
                   (16, 15, 2), (18, 14, 2), (20, 12, 2), (22, 9, 2), (24, 7, 2), (26, 5, 2), (28, 12, 4)]],
         palette=dict(intro="guitar", verse1="flute", verse2="guitar_trem", refrain=["flute", "steel"], verse3="guitar",
                      bridge="guitar", climax=["trumpet", "flute"], counter="steel", answer="steel",
                      comping="strum", perc=["congas", "palmas"], acid=False, stabs=None, hook=False, cajon=True),
         sections=default_sections(intro=8, coda=16)),
]


def fragment_of(theme_a):
    """Zwischenteil-Fragment: Anfang des Hauptthemas, dann Stille."""
    first = theme_a[0][:3]
    f1 = [(p, s_, d) for p, s_, d in first]
    if f1:
        p, s_, d = f1[-1]
        f1[-1] = (p, s_, max(d, 4))
    f2 = f1[:2] + [(f1[-1][0], f1[-1][1], 6)] if len(f1) >= 2 else f1
    return [f1, f2]


# --------------------------------------------------------------------------- #
# Song
# --------------------------------------------------------------------------- #
class Song:
    def __init__(self, spec):
        self.spec = spec
        self.rng = np.random.default_rng(spec["seed"])
        self.root = spec["root"]
        self.beat = 60.0 / spec["bpm"]
        self.sections = spec["sections"]
        self.pal = spec["palette"]
        self.scale = spec["scale"]
        self.bar_len = []
        for name, bars, _, _, _ in self.sections:
            for b in range(bars):
                mult = 1.0
                if name == "coda":
                    mult = 1.0 + 0.45 * (b / max(1, bars - 1)) ** 1.5
                self.bar_len.append(4 * self.beat * mult)
        self.bar_start = np.concatenate([[0.0], np.cumsum(self.bar_len)])
        self.total_bars = len(self.bar_len)
        self.n = int((self.bar_start[-1] + 10.0) * SR)
        self.layers = {k: np.zeros((self.n, 2)) for k in
                       ("drums", "perc", "bass", "pad", "lead", "guitar", "atmos", "acid", "stab", "trance", "flute", "steel", "brass")}
        self.kick_times = []

    # ---- Zeit -----------------------------------------------------------------
    def s(self, bar, step16=0.0):
        bar = min(bar, self.total_bars - 1)
        return int((self.bar_start[bar] + step16 * self.bar_len[bar] / 16.0) * SR)

    def step_len(self, bar, steps16):
        return int(steps16 * self.bar_len[min(bar, self.total_bars - 1)] / 16.0 * SR)

    # ---- Instrumente auf Melodie-Ebene ------------------------------------------
    def voice_note(self, instrument, midi, hold, vel, pan):
        rng = self.rng
        if instrument == "guitar":
            return "guitar", nylon_guitar(rng, midi, hold, level=vel, pan=pan)
        if instrument == "guitar_trem":
            return "guitar", tremolo_note(rng, midi, hold, level=vel * 0.8, pan=pan)
        if instrument == "flute":
            return "flute", flute(rng, midi, hold, level=vel, pan=pan)
        if instrument == "trumpet":
            return "brass", trumpet(rng, midi, hold, level=vel, pan=pan)
        if instrument == "steel":
            return "steel", steel_drum(rng, midi, hold, level=vel, pan=pan)
        if instrument == "lead":
            return "lead", lead(rng, midi, hold, level=vel, pan=pan)
        if instrument == "hook":
            return "trance", supersaw_lead(rng, midi - 12, hold, level=vel, cutoff=3000.0, pan=pan)
        raise ValueError(instrument)

    def scale_run(self, target_midi, root, steps=3):
        """Picado: kurze Skalenbewegung von unten in den Zielton."""
        pcs = sorted(self.scale)
        rel = (target_midi - root) % 12
        idx = min(range(len(pcs)), key=lambda i: abs(pcs[i] - rel))
        notes = []
        m = target_midi
        for k in range(steps):
            idx -= 1
            if idx < 0:
                idx += len(pcs)
                m -= 12
            m = m - ((m - root) % 12) + pcs[idx] if True else m
            notes.append(m)
        # notes liegen absteigend unter dem Ziel; umkehren -> aufsteigend in den Zielton
        return notes[::-1]

    def play_phrases(self, phrases, start_bar, root, instrument, level, humanize=0.006, legato=0.9,
                     octave=12, pan=0.0, ornaments=False):
        rng = self.rng
        default_oct = {"guitar": 0, "guitar_trem": 0, "flute": 12, "trumpet": 12, "steel": 12, "lead": 12, "hook": 12}
        if octave is None:
            octave = default_oct[instrument]
        for pi, phrase in enumerate(phrases):
            for pos8, semi, dur8 in phrase:
                bar = start_bar + pi * 4 + pos8 // 8
                if bar >= self.total_bars:
                    continue
                st = (pos8 % 8) * 2
                hold = int(self.step_len(bar, dur8 * 2) * legato)
                midi = root + octave + semi
                vel = level * rng.uniform(0.9, 1.05) * (1.08 if pos8 % 8 == 0 else 1.0)
                off = int(rng.normal(0, humanize) * SR)
                if ornaments and pos8 % 8 == 0 and dur8 >= 2 and rng.random() < 0.6:
                    run = self.scale_run(midi, root, steps=3)
                    for k, m in enumerate(run):
                        layer, sig = self.voice_note("guitar", m, self.step_len(bar, 0.9), vel * 0.55, pan)
                        place(self.layers[layer], self.s(bar, st) + off - self.step_len(bar, 3 - k), sig)
                layer, sig = self.voice_note(instrument, midi, hold, vel, pan)
                place(self.layers[layer], self.s(bar, st) + off, sig)

    def answers(self, phrases, start_bar, root, chords_for_bar, instrument, level=0.14):
        """Frage und Antwort: in lange Töne des Themas hinein antwortet ein zweites Instrument."""
        if instrument is None:
            return
        rng = self.rng
        for pi, phrase in enumerate(phrases):
            for pos8, semi, dur8 in phrase:
                if dur8 < 3:
                    continue
                bar = start_bar + pi * 4 + pos8 // 8
                if bar >= self.total_bars:
                    continue
                tones = chords_for_bar(bar)
                st = (pos8 % 8) * 2 + 2
                for k in range(min(3, dur8 - 1)):
                    m = tones[(2 - k) % len(tones)] + (12 if instrument == "steel" else 0)
                    layer, sig = self.voice_note(instrument, m, self.step_len(bar, 2), level * (0.9 - 0.2 * k),
                                                 -0.4 if k % 2 else 0.4)
                    place(self.layers[layer], self.s(bar, st + 2 * k), sig)

    # ---- Rendering ----------------------------------------------------------------
    def render(self):
        rng = self.rng
        pal = self.pal
        spec = self.spec
        theme_a, theme_b = spec["theme_a"], spec["theme_b"]
        fragment = fragment_of(theme_a)

        kick_s = kick(rng, punch=0.9)
        hat_c = hat(rng, 0.045, 8500.0, 0.26)
        ohat = open_hat_909(rng, 0.19)
        clap_s = clap(rng, 0.27)
        snare_s = snare_layer(rng, 0.28)
        shaker_s = shaker(rng, 0.13)
        ride_s = ride(rng, 0.12)
        crash_s = crash(rng, 0.3)
        rim_s = rim(rng, 0.18)
        congas = [ga.conga(rng, f, 0.5, pn) for f, pn in ((190.0, -0.4), (240.0, 0.4), (150.0, 0.1))]
        cj_bass, cj_slap = cajon_bass(rng), cajon_slap(rng)
        pal_secas, pal_sordas = palmas(rng, True), palmas(rng, False)
        cast = castanet(rng)

        ocean_sig, wave_env = ocean(rng, self.n, level=0.24)
        self.wave_env = wave_env
        ocean_level = {"intro": 1.0, "verse1": 0.3, "verse2": 0.18, "refrain1": 0.1, "verse3": 0.22,
                       "refrain2": 0.08, "bridge": 0.75, "climax": 0.06, "coda": 0.9}
        sec_of_bar = []
        for sec in self.sections:
            sec_of_bar += [sec] * sec[1]
        bar_pos = np.array([self.s(b) for b in range(self.total_bars)] + [self.n - 1])
        og = np.array([ocean_level[sec_of_bar[b][0]] for b in range(self.total_bars)] + [1.0])
        coda_start = next(i for i, s_ in enumerate(sec_of_bar) if s_[0] == "coda")
        for b in range(coda_start, self.total_bars):
            og[b] = 0.5 + 0.5 * (b - coda_start) / max(1, self.total_bars - coda_start - 1)
        ocean_gain = lowpass(np.interp(np.arange(self.n), bar_pos, og), 0.4)
        self.layers["atmos"] += ocean_sig * ocean_gain[:, None]
        self.layers["atmos"] += seagulls(rng, self.n, 0.04, count=7) * ocean_gain[:, None]
        self.dyn_curve = lowpass(np.interp(np.arange(self.n), bar_pos,
                                           np.array([sec_of_bar[b][4] for b in range(self.total_bars)] + [0.5])), 0.4)
        self.coda_sample = self.s(coda_start)
        self.coda_bars = self.total_bars - coda_start

        bar = 0
        for name, bars, tr, prog_key, dyn in self.sections:
            root = self.root + tr
            prog = spec["progs"][prog_key]
            sec_start = bar

            def chord_tones(b, _prog=prog, _root=root, _start=sec_start):
                return voice(CH[_prog[(b - _start) % len(_prog)]], _root)

            house = name in ("verse1", "verse2", "refrain1", "verse3", "refrain2", "climax")
            full_hats = name in ("verse2", "refrain1", "refrain2", "climax")
            soft_kick = name in ("coda", "intro")
            drums_on = house or soft_kick
            answer_inst = pal.get("answer")

            # ---------- Melodie-Ebene ----------
            if name == "intro":
                self.play_phrases(theme_a, bar + max(0, bars - 8), root, pal["intro"], 0.42, humanize=0.018, legato=1.1, octave=None, ornaments=True)
                self.answers(theme_a, bar + max(0, bars - 8), root, chord_tones, answer_inst, level=0.12)
            elif name == "verse1":
                self.play_phrases(theme_a, bar, root, pal["verse1"], 0.26, humanize=0.01, octave=None, ornaments=pal["verse1"].startswith("guitar"))
                self.answers(theme_a, bar, root, chord_tones, answer_inst, level=0.14)
            elif name == "verse2":
                self.play_phrases(theme_a, bar, root, pal["verse2"], 0.24, octave=None, ornaments=pal["verse2"].startswith("guitar"))
                if not pal["verse2"].startswith("guitar"):
                    self.play_phrases(theme_a, bar, root, "guitar", 0.22, octave=0, legato=0.8)
                self.answers(theme_a, bar, root, chord_tones, answer_inst, level=0.14)
            elif name in ("refrain1", "refrain2"):
                lead_i, second = pal["refrain"]
                self.play_phrases(theme_b, bar, root, lead_i, 0.25, pan=0.1, octave=None)
                self.play_phrases(theme_b, bar, root, second, 0.18, octave=(24 if second == "steel" else None), pan=-0.3, legato=0.75)
                if name == "refrain2" and lead_i != "flute":
                    self.play_phrases(theme_b, bar, root, "flute", 0.15, octave=24, pan=0.3)
            elif name == "verse3":
                self.play_phrases(theme_a, bar, root, pal["verse3"], 0.4, legato=0.95, octave=None, ornaments=True)
                self.answers(theme_a, bar, root, chord_tones, answer_inst, level=0.12)
            elif name == "bridge":
                self.play_phrases(fragment, bar, root, pal["bridge"], 0.36, humanize=0.015, legato=1.2, octave=None)
            elif name == "climax":
                a, b_ = pal["climax"]
                for half in (0, 8):
                    if half >= bars:
                        break
                    self.play_phrases(theme_b, bar + half, root, a, 0.26 + 0.02 * (half > 0), octave=None, pan=-0.1)
                    self.play_phrases(theme_b, bar + half, root, b_, 0.2, octave=(12 if b_ == "hook" else 24 if b_ in ("flute", "steel") else None), pan=0.25)
                if bars >= 16:
                    self.play_phrases(theme_a, bar + 8, root, pal["counter"], 0.2, octave=(24 if pal["counter"] == "steel" else 12), pan=0.5, legato=0.6)
            elif name == "coda":
                self.play_phrases(theme_a, bar, root, pal["coda"] if "coda" in pal else "guitar", 0.4, humanize=0.025, legato=1.25, octave=None, ornaments=True)
                self.answers(theme_a, bar, root, chord_tones, answer_inst, level=0.1)
                final = voice(CH[prog[0]] + [14], root)
                place(self.layers["guitar"], self.s(bar + 8, 0), strum_chord(rng, final, int(3.0 * SR), level=0.34, spread=0.05))
                place(self.layers["steel"], self.s(bar + 9, 0), steel_drum(rng, root + 24, self.step_len(bar + 9, 16), level=0.18))
                place(self.layers["pad"], self.s(bar + 8, 0), pad_chord(rng, final, int(6.0 * SR), cutoff=650.0,
                                                                        level=0.24, attack=1.5, release=4.0))

            # ---------- Takt-Ebene ----------
            for b in range(bars):
                cur = bar + b
                tones = chord_tones(cur)
                bar_s = self.s(cur)
                bl = self.bar_len[cur]
                st16 = lambda k: self.s(cur, k)  # noqa: E731
                last_bar = b == bars - 1
                bass_root = tones[0]
                while bass_root > 45:
                    bass_root -= 12
                while bass_root < 33:
                    bass_root += 12
                quiet = name in ("intro", "bridge", "coda")

                # Pad (Streicher-Fläche): leise Basis, in der Coda nur bis Takt 8
                if not (name == "coda" and b >= 8):
                    cutoff = {"intro": 650, "verse1": 800, "verse2": 1000, "refrain1": 1400, "verse3": 900,
                              "refrain2": 1600, "bridge": 700, "climax": 2000, "coda": 700}[name]
                    place(self.layers["pad"], bar_s - int(0.12 * SR),
                          pad_chord(rng, tones, int(bl * SR * 1.02), cutoff=cutoff, level=0.19))

                # Gitarren-Begleitung
                comp = pal.get("comping")
                if comp and name in ("verse1", "verse2", "refrain1", "refrain2", "verse3", "climax"):
                    if comp == "strum":
                        hits = [(6, True, 0.2, False), (12, False, 0.18, False)]
                        if name == "verse3":
                            hits = [(6, True, 0.24, False), (7, False, 0.14, False), (12, True, 0.24, False), (14, False, 0.16, False)]
                    else:  # rumba flamenca
                        hits = [(0, True, 0.2, False), (3, False, 0.12, True), (6, True, 0.17, True), (8, True, 0.2, False),
                                (11, False, 0.12, True), (14, True, 0.16, False)]
                        if name == "climax":
                            hits = [(h[0], h[1], h[2] * 1.15, h[3]) for h in hits]
                    for st, down, lvl, muted in hits:
                        place(self.layers["guitar"], st16(st) + int(rng.normal(0, 0.004) * SR),
                              strum_chord(rng, tones, self.step_len(cur, 2 if muted else 3), level=lvl, spread=0.012,
                                          pan=-0.25, down=down, muted=muted))

                # Bass
                if quiet:
                    if (name == "intro" and b < max(0, bars - 4)) or (name == "bridge" and b >= 4) or (name == "coda" and b >= 6):
                        pass
                    else:
                        for st in (0, 8):
                            place(self.layers["bass"], st16(st), pluck_bass(rng, bass_root, self.step_len(cur, 7), level=0.75))
                        if name == "intro":
                            place(self.layers["bass"], st16(14), pluck_bass(rng, bass_root + 12, self.step_len(cur, 2), level=0.5))
                elif house:
                    steps = [0, 2, 4, 6, 8, 10, 12, 14] if name in ("climax", "refrain2", "refrain1") else [0, 3, 6, 8, 11, 14]
                    cut = {"verse1": 520.0, "verse2": 600.0, "refrain1": 700.0, "verse3": 650.0, "refrain2": 760.0, "climax": 900.0}[name]
                    for i, st in enumerate(steps):
                        nxt = steps[i + 1] if i + 1 < len(steps) else 16
                        m = bass_root + (12 if st in (6, 14) and rng.random() < 0.5 else 0)
                        place(self.layers["bass"], st16(st),
                              synth_bass(rng, float(midi_to_hz(m)), int(self.step_len(cur, nxt - st) * 0.65),
                                         level=0.82 if st in (0, 8) else 0.7, cutoff=cut))

                # Drums
                if drums_on and not (name == "coda" and b >= 4) and not (name == "intro" and b < max(0, bars - 4)):
                    if soft_kick:
                        for st in (0, 8):
                            place(self.layers["drums"], st16(st), kick_s * 0.6)
                            self.kick_times.append(st16(st))
                    else:
                        gain = {"verse1": 0.8, "verse2": 0.9, "refrain1": 0.95, "verse3": 0.85, "refrain2": 1.0, "climax": 1.0}[name]
                        for st in (0, 4, 8, 12):
                            if last_bar and st == 12 and name in ("refrain1", "verse3"):
                                continue
                            place(self.layers["drums"], st16(st), kick_s * gain)
                            self.kick_times.append(st16(st))
                    if name in ("verse1", "verse3"):
                        for st in (2, 6, 10, 14):
                            place(self.layers["drums"], st16(st), ohat * 0.7)
                        place(self.layers["drums"], st16(12), clap_s * 0.75)
                        if name == "verse3":
                            place(self.layers["drums"], st16(4), clap_s * 0.6)
                    if full_hats:
                        for st in range(16):
                            h = ohat if st in (2, 6, 10, 14) else hat_c
                            vel = (1.0 if st % 2 == 0 else 0.55) * rng.uniform(0.85, 1.0)
                            place(self.layers["drums"], st16(st) + int(rng.normal(0, 0.0015) * SR), h * vel)
                        for st in (4, 12):
                            place(self.layers["drums"], st16(st), clap_s * 0.95)
                            place(self.layers["drums"], st16(st), snare_s * 0.85)
                    if name == "climax":
                        for st in range(0, 16, 2):
                            place(self.layers["drums"], st16(st), ride_s * (1.0 if st % 4 == 0 else 0.7))
                    if last_bar and name in ("verse1", "verse2", "refrain1", "verse3", "refrain2"):
                        for k, st in enumerate((12, 13, 14, 15)):
                            place(self.layers["drums"], st16(st), snare_s * (0.3 + 0.2 * k))
                    if name == "climax" and b in (7, 15):
                        for k, st in enumerate((12, 13, 14, 15)):
                            place(self.layers["drums"], st16(st), snare_s * (0.35 + 0.2 * k))

                # Spanische Percussion
                perc = pal.get("perc", [])
                perc_on = not (name == "intro" and b < 2) and not (name == "coda" and b >= 8)
                if perc_on:
                    if "cajon" in perc or (pal.get("cajon") and quiet):
                        lvl = 1.0 if quiet else 0.55
                        if not (name == "bridge" and b >= 6):
                            for st in (0, 8):
                                place(self.layers["perc"], st16(st) + int(rng.normal(0, 0.002) * SR), cj_bass * lvl)
                            for st in (4, 12):
                                place(self.layers["perc"], st16(st) + int(rng.normal(0, 0.002) * SR), cj_slap * lvl)
                            for st in (6, 14, 15):
                                if rng.random() < 0.6:
                                    place(self.layers["perc"], st16(st), cj_slap * lvl * 0.35)
                    if "palmas" in perc and not quiet:
                        for st in (2, 6, 10, 14):
                            place(self.layers["perc"], st16(st) + int(rng.normal(0, 0.004) * SR), pal_secas * 0.9)
                        for st in (4, 12):
                            place(self.layers["perc"], st16(st) + int(rng.normal(0, 0.004) * SR), pal_sordas * 0.8)
                        if name in ("refrain1", "refrain2", "climax"):
                            for st in (3, 11):
                                place(self.layers["perc"], st16(st) + int(rng.normal(0, 0.004) * SR), pal_secas * 0.5)
                    if "castanets" in perc and name in ("verse2", "refrain1", "refrain2", "climax", "verse3"):
                        for st in (3, 7, 11):
                            if rng.random() < 0.7:
                                place(self.layers["perc"], st16(st), cast * 0.8)
                        if last_bar or b % 4 == 3:
                            for k in range(5):  # Wirbel
                                place(self.layers["perc"], st16(15) + int(k * 0.04 * SR), cast * (0.5 + 0.1 * k))
                    if "congas" in perc and not quiet:
                        for st, cg in ((3, congas[0]), (7, congas[1]), (11, congas[0]), (13, congas[2])):
                            if rng.random() < 0.8:
                                place(self.layers["perc"], st16(st) + int(rng.normal(0, 0.003) * SR), cg * 0.75)
                    if quiet or "shaker" in perc:
                        for st in range(0, 16, 2):
                            place(self.layers["perc"], st16(st) + int(rng.normal(0, 0.002) * SR),
                                  shaker_s * (1.0 if st % 4 == 0 else 0.5) * 0.6)

                # Zwischenteil: Riser, Snare-Roll, Rim; Crash am Höhepunkt
                if name == "bridge":
                    if b == 4:
                        place(self.layers["trance"], bar_s, riser(rng, int(sum(self.bar_len[cur:cur + 4]) * SR), level=0.17))
                    if b == 7:
                        for st in range(16):
                            place(self.layers["drums"], st16(st), snare_s * (0.25 + 0.75 * st / 15))
                        for st in (0, 8):
                            place(self.layers["drums"], st16(st), rim_s)
                if name == "climax" and b == 0:
                    place(self.layers["drums"], bar_s, crash_s)

                # Stabs: Bläsersatz oder House-Chord
                stabs = pal.get("stabs")
                if stabs and name in ("refrain1", "refrain2", "climax"):
                    steps = (2, 10) if name == "refrain1" else (2, 7, 10, 15)
                    for st in steps:
                        if stabs == "brass":
                            if st in (2, 10) or name == "climax":
                                place(self.layers["brass"], st16(st),
                                      brass_stab(rng, [t_ + 12 for t_ in tones[:3]], self.step_len(cur, 1.5), level=0.22 if name != "climax" else 0.28))
                        else:
                            place(self.layers["stab"], st16(st),
                                  house_stab(rng, [t_ + 12 for t_ in tones[:4]], self.step_len(cur, 1.2),
                                             level=0.2 if name != "climax" else 0.26, cutoff=2200.0, pan=rng.uniform(-0.3, 0.3)))

                # Acid
                if pal.get("acid") and name in ("verse2", "refrain1", "verse3", "refrain2", "climax"):
                    lvl = {"verse2": 0.22, "refrain1": 0.28, "verse3": 0.32, "refrain2": 0.34, "climax": 0.38}[name]
                    cut = {"verse2": 280.0, "refrain1": 340.0, "verse3": 400.0, "refrain2": 460.0, "climax": 560.0}[name]
                    seq = ((0, 0, True, False), (3, 0, False, False), (6, 12, False, True), (8, 0, True, False),
                           (10, 7, False, False), (11, 10, False, True), (14, 0, False, False), (15, 12, False, False))
                    prev = None
                    for st, iv, acc, slide in seq:
                        if name == "verse2" and st in (10, 15):
                            prev = None
                            continue
                        m = bass_root + 12 + iv
                        place(self.layers["acid"], st16(st),
                              acid_note(rng, m, self.step_len(cur, 1.3 if slide else 0.6), prev_midi=prev if slide else None,
                                        accent=acc, level=lvl, base_cut=cut, env_amount=2400.0, q=7.0))
                        prev = m

                # Trance-Arpeggio nur am Höhepunkt und nur bei Titeln mit Hook
                if name == "climax" and pal.get("hook"):
                    arp = sorted({t_ + 12 for t_ in tones[:4]} | {t_ + 24 for t_ in tones[:2]})
                    order = arp + arp[-2:0:-1]
                    for st in range(16):
                        if st % 4 == 3:
                            continue
                        place(self.layers["trance"], st16(st),
                              trance_pluck(rng, order[(st + b * 2) % len(order)], self.step_len(cur, 0.6), level=0.13,
                                           pan=0.55 if st % 2 else -0.55))
            bar += bars
        return self.mix()

    def mix(self):
        rng = self.rng
        L = self.layers
        dub = self.pal.get("dub", False)
        ir_long = make_reverb_ir(rng, 3.2, 1.9, 3600.0)
        ir_room = make_reverb_ir(rng, 1.2, 4.5, 5000.0, 0.008)
        duck = np.ones(self.n)
        curve_n = int(0.32 * SR)
        curve = 1.0 - 0.6 * np.exp(-np.linspace(0, 5, curve_n))
        for kt in self.kick_times:
            end = min(self.n, kt + curve_n)
            if kt < self.n:
                duck[kt:end] = np.minimum(duck[kt:end], curve[: end - kt])
        duck = np.clip(lowpass(duck, 60.0), 0.3, 1.0)
        d = duck[:, None]

        pad = reverb(chorus_widen(L["pad"], rng), ir_long, 0.55) * d
        w = np.clip((np.arange(self.n) - self.coda_sample) / (6 * 4 * self.beat * SR), 0.0, 1.0)
        pad *= ((1.0 - w) + w * (0.5 + 0.5 * self.wave_env))[:, None]
        lead_l = reverb(delay(L["lead"], self.beat * 1.5, 0.42, 6, 2600.0, True, 0.3), ir_long, 0.42)
        guitar = reverb(delay(L["guitar"], self.beat * 0.75, 0.28, 3, 3200.0, False, 0.16), ir_room, 0.3)
        brass = reverb(delay(L["brass"], self.beat * (1.5 if dub else 0.75), 0.5 if dub else 0.3, 6 if dub else 3, 2600.0, True, 0.4 if dub else 0.2), ir_long, 0.38)
        flute_l = reverb(delay(L["flute"], self.beat * 1.5, 0.35, 4, 3000.0, True, 0.22), ir_long, 0.42)
        steel = reverb(delay(L["steel"], self.beat * 0.75, 0.3, 3, 3500.0, True, 0.2), ir_long, 0.35) * (0.6 + 0.4 * d)
        perc = reverb(L["perc"], ir_room, 0.16)
        drums = reverb(L["drums"], ir_room, 0.06)
        bass = L["bass"] * (0.55 + 0.45 * d)
        acid = reverb(delay(L["acid"], self.beat * 0.75, 0.3, 3, 2400.0, True, 0.18), ir_room, 0.16) * (0.7 + 0.3 * d)
        trance = reverb(delay(L["trance"], self.beat * 0.75, 0.4, 5, 3200.0, True, 0.3), ir_long, 0.5) * d
        stab = reverb(delay(L["stab"], self.beat * 1.5, 0.35, 4, 3000.0, True, 0.25), ir_long, 0.3) * d
        atmos = L["atmos"]

        parts = dict(drums=drums * 1.15, perc=perc * 1.25, bass=bass * 1.05, pad=pad * 1.8, lead=lead_l * 1.5,
                     guitar=guitar * 1.9, brass=brass * 1.5, flute=flute_l * 1.6, steel=steel * 1.4, atmos=atmos * 1.8,
                     acid=acid * 1.7, stab=stab * 2.4, trance=trance * 1.7)
        if os.environ.get("ALBUM_DEBUG"):
            for k, v in parts.items():
                r = np.sqrt(np.mean(v ** 2)) + 1e-9
                print(f"      {k:7s} {20*np.log10(r):6.1f} dBFS", file=sys.stderr)
        mixv = sum(parts.values())
        mixv = highpass(mixv, 28.0)
        mixv *= self.dyn_curve[:, None]
        fade_in = int(0.5 * SR)
        mixv[:fade_in] *= np.linspace(0, 1, fade_in)[:, None]
        tail = int(6.0 * SR)
        mixv[-tail:] *= np.linspace(1, 0, tail)[:, None] ** 1.2
        return master_chain(mixv)


def slug_of(spec):
    import unicodedata
    plain = unicodedata.normalize("NFKD", spec["title"]).encode("ascii", "ignore").decode()
    slug = f"{spec['nr']:02d}-" + "".join(c if c.isalnum() else "-" for c in plain.lower()).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug


def song_duration(spec):
    return Song(spec).n / SR


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "out"))
    ap.add_argument("--track", type=int, default=None)
    ap.add_argument("--wav", action="store_true")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    tracklist = []
    for spec in SONGS:
        if args.track is not None and spec["nr"] != args.track:
            continue
        song = Song(spec)
        print(f"[{spec['nr']}/{len(SONGS)}] {spec['title']}  ({spec['bpm']} BPM, {spec['mode']}) ...", flush=True)
        mixv = song.render()
        slug = slug_of(spec)
        ga.write_outputs(mixv, os.path.join(args.out, slug), args.wav, True)
        dur = len(mixv) / SR
        print(f"    {int(dur // 60)}:{int(dur % 60):02d} min, RMS {20*np.log10(np.sqrt(np.mean(mixv**2))):.1f} dBFS", flush=True)
        tracklist.append(dict(nr=spec["nr"], title=spec["title"], bpm=spec["bpm"], key=spec["mode"], seed=spec["seed"],
                              duration_s=round(dur, 1), file=slug + ".mp3"))
    if args.track is None:
        with open(os.path.join(args.out, "tracklist.json"), "w", encoding="utf-8") as fh:
            json.dump(dict(album=ALBUM_TITLE, artist=ALBUM_ARTIST, year=2026, license="CC0-1.0", tracks=tracklist), fh,
                      ensure_ascii=False, indent=2)
    print("fertig:", args.out)


if __name__ == "__main__":
    main()

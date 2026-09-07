#!/usr/bin/env python3
"""
Songform-Komposition mit handgeschriebenen Themen (statt Loop-Generator).

Aufbau wie ein erzählter Song: Intro, Strophe, Strophe, Refrain, Strophe,
Refrain, Zwischenteil mit Stille, Höhepunkt (moduliert einen Ganzton höher),
Coda mit dem Hauptthema, das im Meer ausläuft.

Alle Themen, Gegenmelodien und Akkordfolgen sind in dieser Datei notiert und
eigene Kompositionen. Die Klangerzeugung kommt aus generate_album.py.

    python3 compose_song.py            # rendert ./out/puerto-banus-nights-song.mp3
    python3 compose_song.py --wav
"""
import argparse
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import generate_album as ga  # noqa: E402
from generate_album import (SR, place, to_stereo, lowpass, reverb, delay, chorus_widen, make_reverb_ir,  # noqa: E402
                            kick, hat, clap, shaker, snare_layer, ride, crash, rim, open_hat_909,
                            synth_bass, pad_chord, pluck, ks_guitar, ep_keys, lead, supersaw_lead,
                            trance_pluck, riser, acid_note, house_stab, ocean, seagulls, master_chain,
                            midi_to_hz)

# --------------------------------------------------------------------------- #
# Zusätzliche "akustische" Instrumente (physikalisch/additiv modelliert)
# --------------------------------------------------------------------------- #
def nylon_guitar(rng, midi, n_hold, level=0.4, pan=0.0):
    """Wärmer gedämpfte Saite, an Konzertgitarre angelehnt."""
    sig = ks_guitar(rng, midi, n_hold, level=level, damp=0.9935, pan=pan)
    return lowpass(sig, 4200.0)


def strum_chord(rng, midis, n_hold, level=0.3, spread=0.016, pan=0.0, down=True):
    """Angeschlagener Gitarrenakkord: Saiten zeitlich versetzt."""
    order = list(midis) if down else list(midis)[::-1]
    n = n_hold + int(1.4 * SR) + int(spread * SR * len(order))
    out = np.zeros((n, 2))
    for i, m in enumerate(order):
        place(out, int(i * spread * SR), nylon_guitar(rng, m, n_hold, level=level * (0.8 + 0.2 * (i == 0)), pan=pan + (i - len(order) / 2) * 0.07))
    return out


def steel_drum(rng, midi, n_hold, level=0.3, pan=0.0):
    """Steel-Pan: metallische Teiltöne, kurzer Tonhöhen-Bend im Anschlag."""
    f = float(midi_to_hz(midi))
    n = n_hold + int(1.4 * SR)
    t = np.arange(n) / SR
    bend = 1.0 + 0.012 * np.exp(-t * 40.0)
    x = np.zeros(n)
    for ratio, amp, dec in ((1.0, 1.0, 2.2), (2.0, 0.55, 3.5), (3.0, 0.3, 5.0), (4.05, 0.18, 7.0), (5.6, 0.08, 9.0)):
        ph = np.cumsum(f * ratio * bend) / SR
        x += amp * np.sin(2 * np.pi * ph + rng.random() * 6.28) * np.exp(-t * dec)
    x += 0.2 * ga.highpass(rng.standard_normal(n), 3000.0) * np.exp(-t * 90.0)
    env = ga.fit(ga.envelope(n_hold, 0.002, 0.6, 0.5, 0.9), n)
    x = ga.soft_clip(x * env * 1.2, 1.4)
    return to_stereo(x * level, pan)


def flute(rng, midi, n_hold, level=0.3, pan=0.0):
    """Flötenartig: Sinus mit Oberton, Atemrauschen, einsetzendes Vibrato."""
    f = float(midi_to_hz(midi))
    n = n_hold + int(0.5 * SR)
    t = np.arange(n) / SR
    vib = 1.0 + 0.004 * np.sin(2 * np.pi * 5.0 * t) * np.clip((t - 0.15) / 0.3, 0.0, 1.0)
    ph = np.cumsum(f * vib) / SR
    x = np.sin(2 * np.pi * ph) + 0.25 * np.sin(2 * np.pi * 2 * ph) + 0.08 * np.sin(2 * np.pi * 3 * ph)
    breath = ga.bandpass(rng.standard_normal(n), f * 0.7, f * 1.6) * 0.18
    breath *= 1.0 + 1.5 * np.exp(-t * 12.0)  # Anblasgeräusch
    env = ga.fit(ga.envelope(n_hold, 0.07, 0.2, 0.85, 0.22), n)
    x = (x + breath) * env
    return to_stereo(lowpass(x, 7000.0) * level, pan)


def pluck_bass(rng, midi, n_hold, level=0.6):
    """E-Bass: gezupfte Saite mit Tiefpass, Sub-Anteil und weicher Sättigung."""
    sig = ks_guitar(rng, midi, n_hold, level=1.0, damp=0.998, pan=0.0)
    n = len(sig)
    t = np.arange(n) / SR
    x = lowpass(sig[:, 0], 900.0)
    x += 0.5 * np.sin(2 * np.pi * float(midi_to_hz(midi)) * t) * ga.fit(ga.envelope(n_hold, 0.005, 0.3, 0.7, 0.15), n)
    x = ga.soft_clip(x * 1.6, 1.5)
    return to_stereo(ga.highpass(x, 30.0) * level, 0.0)


# --------------------------------------------------------------------------- #
# Notation
#   Melodien: Liste von 4-Takt-Phrasen; jede Phrase = [(pos8, halbton, dauer8), ...]
#   pos8 = Achtelposition innerhalb der Phrase (0..31), halbton relativ zum Grundton
#   (A-Moll: A=0 B=2 C=3 D=5 E=7 F=8 G=10 A'=12 B'=14 C'=15 D'=17 E'=19)
# --------------------------------------------------------------------------- #
THEME_A = [
    [(0, 7, 3), (3, 12, 1), (4, 10, 2), (6, 7, 2),
     (8, 8, 3), (11, 12, 1), (12, 15, 2), (14, 12, 2),
     (16, 10, 3), (19, 7, 1), (20, 3, 2), (22, 7, 2),
     (24, 5, 4), (28, 2, 2), (30, 5, 2)],
    [(0, 7, 3), (3, 12, 1), (4, 10, 2), (6, 7, 2),
     (8, 8, 2), (10, 10, 2), (12, 12, 2), (14, 15, 2),
     (16, 14, 3), (19, 12, 1), (20, 10, 2), (22, 7, 2),
     (24, 3, 4), (28, 0, 4)],
]

THEME_B = [
    [(0, 0, 2), (2, 3, 1), (3, 5, 1), (4, 7, 4),
     (8, 5, 2), (10, 3, 1), (11, 5, 1), (12, 7, 2), (14, 10, 2),
     (16, 12, 3), (19, 10, 1), (20, 7, 2), (22, 3, 2),
     (24, 5, 2), (26, 3, 2), (28, 0, 4)],
    [(0, 0, 2), (2, 3, 1), (3, 5, 1), (4, 7, 4),
     (8, 5, 2), (10, 3, 1), (11, 5, 1), (12, 7, 2), (14, 10, 2),
     (16, 12, 2), (18, 14, 2), (20, 15, 2), (22, 12, 2),
     (24, 10, 2), (26, 7, 2), (28, 7, 4)],
]

# Fragment für den Zwischenteil: der Anfang des Hauptthemas, dann Stille
FRAGMENT_A = [[(0, 7, 3), (3, 12, 1), (4, 10, 4)], [(0, 7, 3), (3, 12, 1), (4, 10, 2), (6, 7, 6)]]

# Akkorde als Halbtöne relativ zum Grundton
CHORDS = {
    "Am7": [0, 3, 7, 10], "Fmaj7": [-4, 0, 3, 7], "Cmaj7": [3, 7, 10, 14], "G": [-2, 2, 5, 9],
    "Dm7": [5, 8, 12, 15], "Em7": [-5, -2, 2, 5], "Am9": [0, 3, 7, 10, 14], "Fmaj9": [-4, 0, 3, 7, 10],
}
VERSE_PROG = ["Am7", "Fmaj7", "Cmaj7", "G"]
REFRAIN_PROG = ["Fmaj7", "G", "Am7", "Cmaj7"]
BRIDGE_PROG = ["Dm7", "Em7", "Fmaj7", "Fmaj7"]
CLIMAX_PROG = ["Fmaj9", "G", "Am9", "Cmaj7"]

# Songform: (Name, Takte, Grundton-Verschiebung, Akkordfolge, Dynamik 0..1)
SECTIONS = [
    ("intro", 8, 0, VERSE_PROG, 0.62),
    ("verse1", 8, 0, VERSE_PROG, 0.70),
    ("verse2", 8, 0, VERSE_PROG, 0.80),
    ("refrain1", 8, 0, REFRAIN_PROG, 0.90),
    ("verse3", 8, 0, VERSE_PROG, 0.78),
    ("refrain2", 8, 0, REFRAIN_PROG, 0.95),
    ("bridge", 8, 0, BRIDGE_PROG, 0.66),
    ("climax", 16, 2, CLIMAX_PROG, 1.00),
    ("coda", 12, 2, VERSE_PROG, 0.70),
]

ROOT = 57      # A3
BPM = 122
SEED = 5505


class Song:
    def __init__(self, seed=SEED, bpm=BPM, root=ROOT):
        self.rng = np.random.default_rng(seed)
        self.root = root
        self.beat = 60.0 / bpm
        # Taktlängen: in der Coda wird es langsamer (Ritardando)
        self.bar_len = []
        for name, bars, _, _, _ in SECTIONS:
            for b in range(bars):
                mult = 1.0
                if name == "coda":
                    mult = 1.0 + 0.45 * (b / max(1, bars - 1)) ** 1.5
                self.bar_len.append(4 * self.beat * mult)
        self.bar_start = np.concatenate([[0.0], np.cumsum(self.bar_len)])
        self.total_bars = len(self.bar_len)
        self.n = int((self.bar_start[-1] + 10.0) * SR)
        self.layers = {k: np.zeros((self.n, 2)) for k in
                       ("drums", "perc", "bass", "pad", "keys", "pluck", "lead", "guitar", "atmos", "acid", "stab", "trance", "flute", "steel")}
        self.kick_times = []

    # ---- Zeit ---------------------------------------------------------------
    def s(self, bar, step16=0.0):
        bar = min(bar, self.total_bars - 1)
        return int((self.bar_start[bar] + step16 * self.bar_len[bar] / 16.0) * SR)

    def step_len(self, bar, steps16):
        return int(steps16 * self.bar_len[min(bar, self.total_bars - 1)] / 16.0 * SR)

    # ---- Melodie ---------------------------------------------------------------
    def play_phrases(self, layer, phrases, start_bar, root, instrument, level, humanize=0.006, legato=0.9,
                     octave=12, pan=0.0, **kw):
        rng = self.rng
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
                if instrument == "keys":
                    sig = ep_keys(rng, midi, hold, level=vel, pan=pan)
                elif instrument == "lead":
                    sig = lead(rng, midi, hold, level=vel, pan=pan)
                elif instrument == "hook":
                    sig = supersaw_lead(rng, midi - 12, hold, level=vel, cutoff=3000.0, pan=pan)
                elif instrument == "pluck":
                    sig = pluck(rng, midi, hold, level=vel, brightness=2600.0, pan=pan)
                elif instrument == "guitar":
                    sig = nylon_guitar(rng, midi, hold, level=vel, pan=pan)
                elif instrument == "flute":
                    sig = flute(rng, midi, hold, level=vel, pan=pan)
                elif instrument == "steel":
                    sig = steel_drum(rng, midi, hold, level=vel, pan=pan)
                else:
                    raise ValueError(instrument)
                place(self.layers[layer], self.s(bar, st) + off, sig)

    def answers(self, phrases, start_bar, root, chords_for_bar, level=0.14):
        """Frage und Antwort: In lange Töne des Themas hinein antwortet der Pluck mit Akkordtönen."""
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
                    m = root + 24 + tones[(2 - k) % len(tones)]
                    place(self.layers["steel"], self.s(bar, st + 2 * k),
                          steel_drum(rng, m - 12, self.step_len(bar, 2), level=level * (0.9 - 0.2 * k),
                                     pan=-0.4 if k % 2 else 0.4))

    # ---- Rendering ----------------------------------------------------------
    def render(self):
        rng = self.rng
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

        ocean_sig, wave_env = ocean(rng, self.n, level=0.24)
        self.wave_env = wave_env
        ocean_level = {"intro": 1.0, "verse1": 0.35, "verse2": 0.2, "refrain1": 0.12, "verse3": 0.25,
                       "refrain2": 0.1, "bridge": 0.75, "climax": 0.08, "coda": 0.9}
        sec_of_bar = []
        for name, bars, tr, prog, dyn in SECTIONS:
            sec_of_bar += [(name, bars, tr, prog, dyn)] * bars
        bar_pos = np.array([self.s(b) for b in range(self.total_bars)] + [self.n - 1])
        og = np.array([ocean_level[sec_of_bar[b][0]] for b in range(self.total_bars)] + [1.0])
        # In der Coda schwillt das Meer weiter an
        coda_start = sum(bars for name, bars, *_ in SECTIONS if name != "coda") - 0
        coda_start = next(i for i, s in enumerate(sec_of_bar) if s[0] == "coda")
        for b in range(coda_start, self.total_bars):
            og[b] = 0.5 + 0.5 * (b - coda_start) / max(1, self.total_bars - coda_start - 1)
        ocean_gain = lowpass(np.interp(np.arange(self.n), bar_pos, og), 0.4)
        self.layers["atmos"] += ocean_sig * ocean_gain[:, None]
        self.layers["atmos"] += seagulls(rng, self.n, 0.04, count=7) * ocean_gain[:, None]
        self.dyn_curve = lowpass(np.interp(np.arange(self.n), bar_pos,
                                           np.array([sec_of_bar[b][4] for b in range(self.total_bars)] + [0.5])), 0.4)

        bar = 0
        for name, bars, tr, prog, dyn in SECTIONS:
            root = self.root + tr
            sec_start = bar

            def chord_tones(b, _prog=prog):
                return CHORDS[_prog[(b - sec_start) % len(_prog)]]

            house = name in ("verse1", "verse2", "refrain1", "verse3", "refrain2", "climax")
            full_hats = name in ("verse2", "refrain1", "refrain2", "climax")
            soft_kick = name == "coda" or name == "intro"
            drums_on = house or soft_kick

            # ---------- Melodie-Ebene je Abschnitt ----------
            if name == "intro":
                self.play_phrases("guitar", THEME_A, bar, root, "guitar", 0.4, humanize=0.018, legato=1.1, octave=0)
                self.answers(THEME_A, bar, root, chord_tones, level=0.12)
            elif name == "verse1":
                self.play_phrases("flute", THEME_A, bar, root, "flute", 0.24, humanize=0.01)
                self.answers(THEME_A, bar, root, chord_tones, level=0.14)
            elif name == "verse2":
                self.play_phrases("lead", THEME_A, bar, root, "lead", 0.2)
                self.play_phrases("guitar", THEME_A, bar, root, "guitar", 0.22, octave=0, legato=0.8)
                self.answers(THEME_A, bar, root, chord_tones, level=0.14)
            elif name in ("refrain1", "refrain2"):
                self.play_phrases("lead", THEME_B, bar, root, "lead", 0.21, pan=0.1)
                self.play_phrases("steel", THEME_B, bar, root, "steel", 0.16, octave=24, pan=-0.3, legato=0.7)
                if name == "refrain2":
                    self.play_phrases("flute", THEME_B, bar, root, "flute", 0.16, octave=12, pan=0.3)
            elif name == "verse3":
                self.play_phrases("guitar", THEME_A, bar, root, "guitar", 0.42, legato=0.95, octave=0)
                self.answers(THEME_A, bar, root, chord_tones, level=0.12)
            elif name == "bridge":
                self.play_phrases("guitar", FRAGMENT_A, bar, root, "guitar", 0.36, humanize=0.015, legato=1.2, octave=0)
            elif name == "climax":
                self.play_phrases("trance", THEME_B, bar, root, "hook", 0.2)
                self.play_phrases("lead", THEME_B, bar, root, "lead", 0.22, octave=24, pan=-0.1)
                self.play_phrases("trance", THEME_B, bar + 8, root, "hook", 0.22)
                self.play_phrases("lead", THEME_B, bar + 8, root, "lead", 0.24, octave=24, pan=-0.1)
                self.play_phrases("steel", THEME_A, bar + 8, root, "steel", 0.2, octave=24, pan=0.5, legato=0.6)
            elif name == "coda":
                self.play_phrases("guitar", THEME_A, bar, root, "guitar", 0.4, humanize=0.025, legato=1.25, octave=0)
                self.answers(THEME_A, bar, root, chord_tones, level=0.1)
                place(self.layers["guitar"], self.s(bar + 8, 0), strum_chord(rng, [root + s_ for s_ in CHORDS["Am9"]], int(3.0 * SR), level=0.34, spread=0.05))
                place(self.layers["steel"], self.s(bar + 9, 0), steel_drum(rng, root + 24, self.step_len(bar + 9, 16), level=0.2))
                final = [root + s_ for s_ in CHORDS["Am9"]]
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
                bass_root = root + tones[0]
                while bass_root > 45:
                    bass_root -= 12

                # Pad: Akkord pro Takt, in der Coda nur bis Takt 8
                if not (name == "coda" and b >= 8):
                    cutoff = {"intro": 650, "verse1": 800, "verse2": 1000, "refrain1": 1400, "verse3": 900,
                              "refrain2": 1600, "bridge": 700, "climax": 2000, "coda": 700}[name]
                    voicing = [root + s for s in tones]
                    place(self.layers["pad"], bar_s - int(0.12 * SR),
                          pad_chord(rng, voicing, int(bl * SR * 1.02), cutoff=cutoff, level=0.22))

                # Gitarren-Strums auf den Offbeats (2+ und 4), in Strophe 3 als Rasgueado-Figur
                if name in ("verse1", "verse2", "refrain1", "refrain2", "verse3"):
                    voicing_g = [root + s_ for s_ in tones[:4]]
                    hits = [(6, True), (12, False)] if name != "verse3" else [(6, True), (7, False), (12, True), (14, False)]
                    for st, down in hits:
                        place(self.layers["guitar"], st16(st) + int(rng.normal(0, 0.004) * SR),
                              strum_chord(rng, voicing_g, self.step_len(cur, 3), level=0.2 if name != "verse3" else 0.24,
                                          spread=0.012, pan=-0.25, down=down))

                # Bass: E-Bass in Intro/Zwischenteil/Coda, rollender Synth-Bass in den House-Teilen
                if name in ("intro", "bridge") or name == "coda":
                    if name == "intro" and b < 4:
                        pass
                    elif name == "bridge" and b >= 4:
                        pass  # Stille vor dem Höhepunkt
                    elif name == "coda" and b >= 6:
                        pass
                    else:
                        for st in (0, 8):
                            place(self.layers["bass"], st16(st), pluck_bass(rng, bass_root, self.step_len(cur, 7), level=0.75))
                        if name == "intro":
                            place(self.layers["bass"], st16(14), pluck_bass(rng, bass_root + 12, self.step_len(cur, 2), level=0.5))
                elif house:
                    steps = [0, 2, 4, 6, 8, 10, 12, 14] if name in ("climax", "refrain2", "refrain1") else [0, 3, 6, 8, 11, 14]
                    for i, st in enumerate(steps):
                        nxt = steps[i + 1] if i + 1 < len(steps) else 16
                        m = bass_root + (12 if st in (6, 14) and rng.random() < 0.5 else 0)
                        cut = {"verse1": 520.0, "verse2": 600.0, "refrain1": 700.0, "verse3": 650.0, "refrain2": 760.0, "climax": 900.0}[name]
                        place(self.layers["bass"], st16(st),
                              synth_bass(rng, float(midi_to_hz(m)), int(self.step_len(cur, nxt - st) * 0.65),
                                         level=0.82 if st in (0, 8) else 0.7, cutoff=cut))

                # Drums
                if drums_on and not (name == "coda" and b >= 4) and not (name == "intro" and b < 4):
                    if soft_kick:
                        for st in (0, 8):
                            place(self.layers["drums"], st16(st), kick_s * 0.6)
                            self.kick_times.append(st16(st))
                    else:
                        gain = {"verse1": 0.8, "verse2": 0.9, "refrain1": 0.95, "verse3": 0.85, "refrain2": 1.0, "climax": 1.0}[name]
                        for st in (0, 4, 8, 12):
                            if last_bar and st == 12 and name in ("refrain1", "verse3"):
                                continue  # Fill: letztes Viertel ohne Kick
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
                # Shaker: fast überall außer Intro-Anfang und Coda-Ende
                if not (name == "intro" and b < 4) and not (name == "coda" and b >= 6):
                    dens = 0.5 if name in ("intro", "bridge", "coda") else 0.85
                    for st in range(16):
                        if st % 2 == 0 or rng.random() < dens:
                            place(self.layers["perc"], st16(st) + int(rng.normal(0, 0.002) * SR),
                                  shaker_s * (1.0 if st % 4 == 0 else 0.5) * (0.6 if name in ("intro", "bridge", "coda") else 1.0))

                # Congas in Strophen und Refrains
                if name in ("verse1", "verse2", "verse3", "refrain1", "refrain2"):
                    for st, cg in ((3, congas[0]), (7, congas[1]), (11, congas[0]), (13, congas[2])):
                        if rng.random() < 0.8:
                            place(self.layers["perc"], st16(st) + int(rng.normal(0, 0.003) * SR), cg * 0.8)

                # Zwischenteil: Riser über die letzten 4 Takte, Snare-Roll im letzten Takt
                if name == "bridge":
                    if b == 4:
                        place(self.layers["trance"], bar_s, riser(rng, int(sum(self.bar_len[cur:cur + 4]) * SR), level=0.18))
                    if b == 7:
                        for st in range(16):
                            place(self.layers["drums"], st16(st), snare_s * (0.25 + 0.75 * st / 15))
                        for st in (0, 8):
                            place(self.layers["drums"], st16(st), rim_s)
                if name == "climax" and b == 0:
                    place(self.layers["drums"], bar_s, crash_s)

                # Stabs im Refrain und Höhepunkt
                if name in ("refrain1", "refrain2", "climax"):
                    for st in ((2, 10) if name == "refrain1" else (2, 7, 10, 15)):
                        place(self.layers["stab"], st16(st),
                              house_stab(rng, [root + 12 + s for s in tones[:4]], self.step_len(cur, 1.2),
                                         level=0.2 if name != "climax" else 0.26, cutoff=2200.0, pan=rng.uniform(-0.3, 0.3)))

                # Acid: ab Strophe 2, wächst bis zum Höhepunkt
                if name in ("verse2", "refrain1", "verse3", "refrain2", "climax"):
                    lvl = {"verse2": 0.24, "refrain1": 0.3, "verse3": 0.34, "refrain2": 0.36, "climax": 0.4}[name]
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

                # Trance-Arpeggio in Refrain 2 und Höhepunkt
                if name == "climax":
                    arp = sorted({root + 12 + s for s in tones[:4]} | {root + 24 + s for s in tones[:2]})
                    order = arp + arp[-2:0:-1]
                    for st in range(16):
                        if st % 4 == 3:
                            continue
                        place(self.layers["trance"], st16(st),
                              trance_pluck(rng, order[(st + b * 2) % len(order)], self.step_len(cur, 0.6),
                                           level=0.11 if name == "refrain2" else 0.14, pan=0.55 if st % 2 else -0.55))
            bar += bars
        return self.mix()

    def mix(self):
        rng = self.rng
        L = self.layers
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
        # Coda: Pad atmet mit den Wellen
        coda_s = self.s(self.total_bars - 12)
        w = np.clip((np.arange(self.n) - coda_s) / (6 * 4 * self.beat * SR), 0.0, 1.0)
        pad *= ((1.0 - w) + w * (0.5 + 0.5 * self.wave_env))[:, None]
        keys = reverb(delay(L["keys"], self.beat * 0.75, 0.35, 4, 2800.0, True, 0.22), ir_long, 0.4)
        pluck_l = reverb(delay(L["pluck"], self.beat * 1.5, 0.4, 5, 3000.0, True, 0.3), ir_room, 0.3) * (0.5 + 0.5 * d)
        lead_l = reverb(delay(L["lead"], self.beat * 1.5, 0.42, 6, 2600.0, True, 0.3), ir_long, 0.42)
        guitar = reverb(delay(L["guitar"], self.beat * 0.75, 0.3, 3, 3000.0, False, 0.2), ir_room, 0.35)
        perc = reverb(L["perc"], ir_room, 0.18)
        drums = reverb(L["drums"], ir_room, 0.06)
        bass = L["bass"] * (0.55 + 0.45 * d)
        acid = reverb(delay(L["acid"], self.beat * 0.75, 0.3, 3, 2400.0, True, 0.18), ir_room, 0.16) * (0.7 + 0.3 * d)
        trance = reverb(delay(L["trance"], self.beat * 0.75, 0.4, 5, 3200.0, True, 0.3), ir_long, 0.5) * d
        stab = reverb(delay(L["stab"], self.beat * 1.5, 0.35, 4, 3000.0, True, 0.25), ir_long, 0.3) * d
        atmos = L["atmos"]
        flute_l = reverb(delay(L["flute"], self.beat * 1.5, 0.35, 4, 3000.0, True, 0.22), ir_long, 0.42)
        steel = reverb(delay(L["steel"], self.beat * 0.75, 0.3, 3, 3500.0, True, 0.2), ir_long, 0.35) * (0.6 + 0.4 * d)

        parts = dict(drums=drums * 1.15, perc=perc * 1.1, bass=bass * 1.05, pad=pad * 2.0, keys=keys * 1.0,
                     pluck=pluck_l * 1.6, lead=lead_l * 1.5, guitar=guitar * 1.8, atmos=atmos * 1.8,
                     acid=acid * 1.7, stab=stab * 2.4, trance=trance * 1.7, flute=flute_l * 1.6, steel=steel * 1.4)
        if os.environ.get("ALBUM_DEBUG"):
            for k, v in parts.items():
                r = np.sqrt(np.mean(v ** 2)) + 1e-9
                print(f"      {k:7s} {20*np.log10(r):6.1f} dBFS", file=sys.stderr)
        mixv = sum(parts.values())
        mixv = ga.highpass(mixv, 28.0)
        mixv *= self.dyn_curve[:, None]
        fade_in = int(0.5 * SR)
        mixv[:fade_in] *= np.linspace(0, 1, fade_in)[:, None]
        tail = int(6.0 * SR)
        mixv[-tail:] *= np.linspace(1, 0, tail)[:, None] ** 1.2
        return master_chain(mixv)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "out"))
    ap.add_argument("--wav", action="store_true")
    ap.add_argument("--name", default="05-puerto-banus-nights")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    song = Song()
    print(f"Songform: {song.total_bars} Takte, ca. {int(song.bar_start[-1] // 60)}:{int(song.bar_start[-1] % 60):02d} min", flush=True)
    mixv = song.render()
    ga.write_outputs(mixv, os.path.join(args.out, args.name), args.wav, True)
    dur = len(mixv) / SR
    print(f"fertig: {args.name}  {int(dur // 60)}:{int(dur % 60):02d} min, RMS {20*np.log10(np.sqrt(np.mean(mixv**2))):.1f} dBFS")


if __name__ == "__main__":
    main()

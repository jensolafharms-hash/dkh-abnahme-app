#!/usr/bin/env python3
"""
Sounds of Marbella 2026 (DJ Jensi) – das Album als Partitur.

Jeder Titel hat eine eigene Geschichte, eigene Stimme, eigenen Groove und eine
eigene Form. Dramaturgie des Albums: Abend, Nacht, Morgen.

    python3 album.py                # alle Titel + Zwischenspiele nach ./out
    python3 album.py --track 4      # nur Titel 4 (Zwischenspiele: 3.5 und 7.5)
    python3 album.py --wav
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
from compose_song import (nylon_guitar, strum_chord, tremolo_note, steel_drum, flute, trumpet, brass_stab,  # noqa: E402
                          pluck_bass, cajon_bass, cajon_slap, palmas, castanet, CH, voice, ALBUM_TITLE, ALBUM_ARTIST)


# --------------------------------------------------------------------------- #
# Weitere Instrumente und Atmosphären
# --------------------------------------------------------------------------- #
def choir_chord(rng, midis, n_hold, level=0.2, vowel="ah", attack=0.9, release=1.6):
    """Ferner Chor: Sägezahn-Stimmen durch Formantfilter (Vokal), leicht verstimmt."""
    formants = {"ah": ((730, 1.0), (1090, 0.5), (2440, 0.2)), "oh": ((570, 1.0), (840, 0.45), (2410, 0.15)),
                "oo": ((300, 1.0), (870, 0.3), (2240, 0.1))}[vowel]
    n = n_hold + int(release * SR)
    t = np.arange(n) / SR
    out = np.zeros((n, 2))
    for m in midis:
        f = float(midi_to_hz(m))
        for ch in range(2):
            v = np.zeros(n)
            for cents in (-7.0, 0.0, 7.0):
                vib = 1.0 + 0.003 * np.sin(2 * np.pi * (4.8 + rng.uniform(-0.4, 0.4)) * t + rng.random() * 6.28)
                ph = np.cumsum(f * 2.0 ** (cents / 1200.0) * vib) / SR + rng.random()
                v += 2.0 * (ph % 1.0) - 1.0
            y = np.zeros(n)
            for fc, g in formants:
                y += g * bandpass(v, fc * 0.88, fc * 1.12)
            y += 0.12 * lowpass(v, 500.0)
            out[:, ch] += y
    env = fit(envelope(n_hold, attack, 0.5, 0.9, release), n)
    out = lowpass(out * env[:, None], 5000.0)
    return out * level / max(1, len(midis)) * 1.6


def muted_trumpet(rng, midi, n_hold, level=0.3, pan=0.0):
    x = trumpet(rng, midi, n_hold, level=1.0, pan=pan)
    y = 0.25 * lowpass(x, 1100.0) + 1.0 * bandpass(x, 1000.0, 3400.0) + 0.3 * bandpass(x, 3400.0, 6000.0)
    return y * level * 0.9


def bell(rng, midi, n_hold, level=0.3, pan=0.0):
    """Hafenglocke / Laterne: unharmonische Teiltöne, langes Abklingen."""
    f = float(midi_to_hz(midi))
    n = n_hold + int(4.0 * SR)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for ratio, amp, dec in ((1.0, 1.0, 0.9), (2.0, 0.6, 1.3), (2.4, 0.45, 1.8), (3.0, 0.3, 2.2), (4.5, 0.15, 3.0), (5.2, 0.08, 3.6)):
        x += amp * np.sin(2 * np.pi * f * ratio * t + rng.random() * 6.28) * np.exp(-t * dec)
    x += 0.3 * highpass(rng.standard_normal(n), 2500.0) * np.exp(-t * 60.0)
    return to_stereo(x * level * 0.5, pan)


def tom(rng, freq=150.0, level=0.5, pan=0.0):
    n = int(0.35 * SR)
    t = np.arange(n) / SR
    f = freq * (1.0 + 0.6 * np.exp(-t * 40.0))
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 10.0)
    x += 0.2 * bandpass(rng.standard_normal(n), 800.0, 4000.0) * np.exp(-t * 120.0)
    return to_stereo(soft_clip(x * 1.4, 1.3) * level, pan)


def cicadas(rng, n, level=0.05, count=5):
    """Zikaden: Impulsfolgen aus hochfrequentem Rauschen, in Schüben, mehrere Tiere."""
    out = np.zeros((n, 2))
    t = np.arange(n) / SR
    for _ in range(count):
        rate = rng.uniform(80.0, 140.0)
        band = rng.uniform(4200.0, 6500.0)
        pulse = (np.sin(2 * np.pi * rate * t + rng.random() * 6.28) > 0.55).astype(float)
        noise = bandpass(rng.standard_normal(n), band * 0.85, band * 1.15)
        env = np.zeros(n)
        pos = rng.uniform(0, 4.0)
        while pos < t[-1]:
            dur = rng.uniform(0.8, 3.5)
            a, b = int(pos * SR), int(min(n, (pos + dur) * SR))
            seg = np.linspace(0, 1, max(1, b - a))
            env[a:b] = np.minimum(1.0, np.minimum(seg * 6, (1 - seg) * 6))
            pos += dur + rng.uniform(1.0, 6.0)
        sig = noise * pulse * env * rng.uniform(0.6, 1.0)
        out += to_stereo(sig, rng.uniform(-0.8, 0.8))
    return out * level


def crickets(rng, n, level=0.04, count=3):
    """Grillen: kurze Zirp-Gruppen aus einem Sinus um 4 kHz."""
    out = np.zeros((n, 2))
    for _ in range(count):
        f = rng.uniform(3900.0, 4600.0)
        period = rng.uniform(0.42, 0.65)
        chirp_n = int(0.028 * SR)
        tc = np.arange(chirp_n) / SR
        chirp = np.sin(2 * np.pi * f * tc) * np.sin(np.pi * tc / tc[-1]) ** 1.5
        group = np.zeros(int(0.14 * SR))
        for k in range(3):
            place_at = int(k * 0.038 * SR)
            group[place_at:place_at + chirp_n] += chirp
        sig = np.zeros(n)
        pos = rng.uniform(0, 1.0)
        while (pos + 0.2) * SR < n:
            a = int(pos * SR)
            sig[a:a + len(group)] += group * rng.uniform(0.7, 1.0)
            pos += period * rng.uniform(0.95, 1.05)
            if rng.random() < 0.04:
                pos += rng.uniform(1.5, 4.0)  # Pause
        out += to_stereo(sig, rng.uniform(-0.7, 0.7))
    return out * level


# --------------------------------------------------------------------------- #
# Takt- und Groove-Bibliothek
# --------------------------------------------------------------------------- #
METERS = {"4/4": dict(steps=16, beats=4), "6/8": dict(steps=12, beats=2), "bul": dict(steps=24, beats=12)}


def bar_seconds(meter, bpm):
    if meter == "4/4":
        return 4 * 60.0 / bpm
    if meter == "6/8":
        return 2 * 60.0 / bpm          # bpm = punktierte Viertel
    return 12 * 60.0 / bpm             # Bulería: bpm = Zählzeit, 12 pro Compás


# Grooves: Liste von (step, sound, level). Swing verschiebt ungerade 16tel.
GROOVES = {
    "house":    [(0, "kick", 1.0), (4, "kick", 0.95), (8, "kick", 1.0), (12, "kick", 0.95), (4, "clap", 0.9), (12, "clap", 0.9), (4, "snare", 0.7), (12, "snare", 0.7)],
    "deep":     [(0, "kick", 0.85), (4, "kick", 0.8), (8, "kick", 0.85), (12, "kick", 0.8), (4, "rim", 0.6), (12, "clap", 0.6)],
    "halftime": [(0, "kick", 0.9), (10, "kick", 0.45), (8, "snare", 0.75), (8, "clap", 0.5)],
    "shuffle":  [(0, "kick", 0.95), (4, "kick", 0.9), (8, "kick", 0.95), (12, "kick", 0.9), (4, "snare", 0.75), (12, "snare", 0.75), (12, "clap", 0.6)],
    "soft":     [(0, "kick", 0.55), (8, "kick", 0.5)],
    "six8":     [(0, "kick", 0.6), (6, "rim", 0.55), (6, "kick", 0.3)],
    "bul":      [(0, "kick", 0.5), (12, "kick", 0.45)],
    "kickonly": [(0, "kick", 0.9), (4, "kick", 0.85), (8, "kick", 0.9), (12, "kick", 0.85)],
}
HATS = {
    "none": [], "offbeat": [(2, "ohat", 0.6), (6, "ohat", 0.6), (10, "ohat", 0.6), (14, "ohat", 0.6)],
    "eighths": [(s, "hat", 0.6 if s % 4 else 0.85) for s in range(0, 16, 2)],
    "full": [(s, "ohat" if s in (2, 6, 10, 14) else "hat", (0.95 if s % 2 == 0 else 0.5)) for s in range(16)],
    "six8": [(s, "hat", 0.7 if s % 6 == 0 else 0.4) for s in range(0, 12, 2)],
    "techno16": [(s, "hat", 0.9 if s % 4 == 2 else (0.55 if s % 2 == 0 else 0.35)) for s in range(16)] + [(s, "ohat", 0.7) for s in (2, 6, 10, 14)],
}
BASS_STEPS = {"roll": [0, 2, 4, 6, 8, 10, 12, 14], "deep": [0, 3, 6, 8, 11, 14], "long": [0, 8], "half": [0, 10],
              "six8": [0, 6, 10], "bul": [0, 6, 12, 16, 20], "one": [0], "house": [0, 2, 4, 6, 8, 10, 12, 14]}
BASS_INTERVALS = {"house": [0, 12, 0, 7, 0, 12, 0, 10]}   # melodische Bassline: Oktave, Quinte, Septime
BUL_ACCENTS = [0, 6, 12, 16, 20]          # Zählzeiten 12, 3, 6, 8, 10 als 8tel-Schritte
BUL_CONTRA = [3, 9, 15, 19, 23]


# --------------------------------------------------------------------------- #
# Hilfen für die Partitur
# --------------------------------------------------------------------------- #
def S(name, bars, meter="4/4", bpm=120, bpm_end=None, shift=0, prog="verse", dyn=0.8, **parts):
    return dict(name=name, bars=bars, meter=meter, bpm=bpm, bpm_end=bpm_end, shift=shift, prog=prog, dyn=dyn, parts=parts)


def mel(theme, inst, level=0.25, octave=None, pan=0.0, legato=0.9, humanize=0.006, ornaments=False, bars=None, offset=0):
    return dict(theme=theme, inst=inst, level=level, octave=octave, pan=pan, legato=legato, humanize=humanize,
                ornaments=ornaments, bars=bars, offset=offset)


DEFAULT_OCT = {"guitar": 0, "guitar_trem": 0, "flute": 12, "trumpet": 12, "mtrumpet": 12, "steel": 12, "lead": 12,
               "hook": 12, "bell": 12, "choir": 0}


class Track:
    def __init__(self, spec):
        self.spec = spec
        self.rng = np.random.default_rng(spec["seed"])
        self.root = spec["root"]
        self.scale = spec["scale"]
        self.sections = spec["sections"]
        self.bars = []  # dict(sec, meter, steps, len, bpm)
        for si, sec in enumerate(self.sections):
            for b in range(sec["bars"]):
                u = b / max(1, sec["bars"] - 1)
                bpm = sec["bpm"] if sec["bpm_end"] is None else sec["bpm"] + (sec["bpm_end"] - sec["bpm"]) * u
                if sec["parts"].get("rit"):
                    bpm = bpm / (1.0 + 0.5 * u ** 1.5)
                self.bars.append(dict(sec=si, meter=sec["meter"], steps=METERS[sec["meter"]]["steps"],
                                      len=bar_seconds(sec["meter"], bpm), bpm=bpm))
        self.bar_start = np.concatenate([[0.0], np.cumsum([b["len"] for b in self.bars])])
        self.total_bars = len(self.bars)
        self.n = int((self.bar_start[-1] + 10.0) * SR)
        self.layers = {k: np.zeros((self.n, 2)) for k in
                       ("drums", "perc", "bass", "pad", "lead", "guitar", "atmos", "acid", "stab", "trance",
                        "flute", "steel", "brass", "choir", "bell")}
        self.kick_times = []
        self.sec_start = [sum(s["bars"] for s in self.sections[:i]) for i in range(len(self.sections))]

    # ---- Zeit -----------------------------------------------------------------
    def s(self, bar, step=0.0):
        bar = min(bar, self.total_bars - 1)
        b = self.bars[bar]
        return int((self.bar_start[bar] + step * b["len"] / b["steps"]) * SR)

    def step_len(self, bar, steps):
        b = self.bars[min(bar, self.total_bars - 1)]
        return int(steps * b["len"] / b["steps"] * SR)

    def beat_len(self, bar):
        b = self.bars[min(bar, self.total_bars - 1)]
        return b["len"] / METERS[b["meter"]]["beats"]

    # ---- Instrumente ---------------------------------------------------------------
    def note(self, inst, midi, hold, vel, pan):
        rng = self.rng
        if inst == "guitar":
            return "guitar", nylon_guitar(rng, midi, hold, level=vel, pan=pan)
        if inst == "guitar_trem":
            return "guitar", tremolo_note(rng, midi, hold, level=vel * 0.8, pan=pan)
        if inst == "flute":
            return "flute", flute(rng, midi, hold, level=vel, pan=pan)
        if inst == "trumpet":
            return "brass", trumpet(rng, midi, hold, level=vel, pan=pan)
        if inst == "mtrumpet":
            return "brass", muted_trumpet(rng, midi, hold, level=vel, pan=pan)
        if inst == "steel":
            return "steel", steel_drum(rng, midi, hold, level=vel, pan=pan)
        if inst == "lead":
            return "lead", lead(rng, midi, hold, level=vel, pan=pan)
        if inst == "hook":
            return "trance", supersaw_lead(rng, midi - 12, hold, level=vel, cutoff=2600.0, pan=pan)
        if inst == "bell":
            return "bell", bell(rng, midi, hold, level=vel, pan=pan)
        if inst == "choir":
            return "choir", choir_chord(rng, [midi], hold, level=vel * 2.2, vowel="ah", attack=0.25, release=0.8)
        raise ValueError(inst)

    def scale_run(self, target, root, steps=3):
        pcs = sorted(self.scale)
        rel = (target - root) % 12
        idx = min(range(len(pcs)), key=lambda i: abs(pcs[i] - rel))
        notes, m = [], target
        for _ in range(steps):
            idx -= 1
            if idx < 0:
                idx += len(pcs)
                m -= 12
            m = m - ((m - root) % 12) + pcs[idx]
            notes.append(m)
        return notes[::-1]

    def play(self, m, phrases, start_bar, end_bar, root, units):
        """Spielt Phrasen (pos in 'units' je Takt) ab start_bar; endet spätestens bei end_bar."""
        rng = self.rng
        inst = m["inst"]
        octave = DEFAULT_OCT[inst] if m["octave"] is None else m["octave"]
        bars_per_phrase = max(1, len(range(0, max(p for ph in phrases for p, _, _ in ph) + 1, units)))
        bars_per_phrase = 4 if units in (8, 6) else 2
        for pi, phrase in enumerate(phrases):
            for pos, semi, dur in phrase:
                bar = start_bar + m["offset"] + pi * bars_per_phrase + pos // units
                if bar >= end_bar or bar >= self.total_bars:
                    continue
                b = self.bars[bar]
                step = (pos % units) * b["steps"] / units
                hold = int(self.step_len(bar, dur * b["steps"] / units) * m["legato"])
                midi = root + octave + semi
                vel = m["level"] * rng.uniform(0.9, 1.05) * (1.08 if pos % units == 0 else 1.0)
                off = int(rng.normal(0, m["humanize"]) * SR)
                if m["ornaments"] and pos % units == 0 and dur >= 2 and rng.random() < 0.6:
                    for k, rm in enumerate(self.scale_run(midi, root)):
                        layer, sig = self.note("guitar", rm, self.step_len(bar, 0.9), vel * 0.5, m["pan"])
                        place(self.layers[layer], self.s(bar, step) + off - self.step_len(bar, 3 - k), sig)
                layer, sig = self.note(inst, midi, hold, vel, m["pan"])
                place(self.layers[layer], self.s(bar, step) + off, sig)

    def answers(self, phrases, start_bar, end_bar, root, units, chords, inst, level=0.13):
        rng = self.rng
        bars_per_phrase = 4 if units in (8, 6) else 2
        for pi, phrase in enumerate(phrases):
            for pos, semi, dur in phrase:
                if dur < 3:
                    continue
                bar = start_bar + pi * bars_per_phrase + pos // units
                if bar >= end_bar or bar >= self.total_bars:
                    continue
                b = self.bars[bar]
                tones = chords(bar)
                step = (pos % units) * b["steps"] / units + b["steps"] / units
                for k in range(min(3, dur - 1)):
                    mm = tones[(2 - k) % len(tones)] + (12 if inst == "steel" else 0)
                    layer, sig = self.note(inst, mm, self.step_len(bar, 2), level * (0.9 - 0.2 * k), -0.4 if k % 2 else 0.4)
                    place(self.layers[layer], self.s(bar, step + k * b["steps"] / units), sig)

    # ---- Rendering ----------------------------------------------------------------
    def render(self):
        rng = self.rng
        spec = self.spec
        themes = spec["themes"]
        units = spec.get("units", 8)

        snd = dict(kick=kick(rng, punch=spec.get("kick_punch", 0.85)), hat=hat(rng, 0.045, 8000.0, 0.22), ohat=open_hat_909(rng, 0.16),
                   clap=clap(rng, 0.24), snare=snare_layer(rng, 0.24), rim=rim(rng, 0.2), ride=ride(rng, 0.1),
                   crash=crash(rng, 0.22), shaker=shaker(rng, 0.13), cjb=cajon_bass(rng), cjs=cajon_slap(rng),
                   secas=palmas(rng, True), sordas=palmas(rng, False), cast=castanet(rng),
                   tom_l=tom(rng, 110.0, 0.55, -0.3), tom_m=tom(rng, 160.0, 0.5, 0.0), tom_h=tom(rng, 230.0, 0.45, 0.3))
        congas = [ga.conga(rng, f, 0.45, pn) for f, pn in ((190.0, -0.4), (240.0, 0.4), (150.0, 0.1))]

        # Atmosphäre je Abschnitt (Wellen, Zikaden, Grillen), sanft interpoliert
        bar_pos = np.array([self.s(b) for b in range(self.total_bars)] + [self.n - 1])
        atm = {}
        for key, maker, lvl in (("waves", None, 0.24), ("cicadas", cicadas, 0.05), ("crickets", crickets, 0.04)):
            vals = np.array([self.sections[self.bars[b]["sec"]]["parts"].get("atmos", {}).get(key, 0.0) for b in range(self.total_bars)] + [0.0])
            if vals.max() <= 0:
                continue
            vals[-1] = vals[-2]
            gain = lowpass(np.interp(np.arange(self.n), bar_pos, vals), 0.3)
            if key == "waves":
                sig, env = ocean(rng, self.n, level=lvl)
                self.wave_env = env
                sig += seagulls(rng, self.n, 0.035, count=5)
            else:
                sig = maker(rng, self.n, level=lvl)
            self.layers["atmos"] += sig * gain[:, None]
        dyn = np.array([self.sections[self.bars[b]["sec"]]["dyn"] for b in range(self.total_bars)] + [0.5])
        self.dyn_curve = lowpass(np.interp(np.arange(self.n), bar_pos, dyn), 0.35)

        for si, sec in enumerate(self.sections):
            P = sec["parts"]
            root = self.root + sec["shift"]
            start = self.sec_start[si]
            end = start + sec["bars"]
            prog = spec["progs"][sec["prog"]]
            meter = sec["meter"]

            def chords(b, _prog=prog, _root=root, _start=start):
                return voice(CH[_prog[(b - _start) % len(_prog)]], _root)

            # ---- Melodien --------------------------------------------------------
            for m in P.get("melody", []):
                sb = start + m["offset"]
                eb = end if m["bars"] is None else min(end, sb + m["bars"])
                self.play(m, themes[m["theme"]], sb, eb, root, units)
                if P.get("answer") and m.get("theme") == P.get("answer_theme", m["theme"]) and m is P["melody"][0]:
                    self.answers(themes[m["theme"]], sb, eb, root, units, chords, P["answer"], P.get("answer_level", 0.13))

            # ---- Takt-Ebene ------------------------------------------------------
            for b in range(sec["bars"]):
                cur = start + b
                bar = self.bars[cur]
                steps = bar["steps"]
                tones = chords(cur)
                bar_s = self.s(cur)
                last = b == sec["bars"] - 1
                bass_root = tones[0]
                while bass_root > 45:
                    bass_root -= 12
                while bass_root < 33:
                    bass_root += 12
                swing = P.get("swing", 0.0)

                def at(step):
                    if swing and int(step) % 2 == 1:
                        step = step + swing
                    return self.s(cur, step)

                # Pad / Streicher
                if P.get("pad") and b >= P.get("pad_from", 0):
                    place(self.layers["pad"], bar_s - int(0.12 * SR),
                          pad_chord(rng, tones, int(bar["len"] * SR * 1.02), cutoff=P["pad"], level=0.19 * P.get("pad_level", 1.0)))
                # Chor
                if P.get("choir") and b >= P.get("choir_from", 0) and (b % P.get("choir_every", 1) == 0):
                    hold = int(bar["len"] * SR * P.get("choir_every", 1) * 1.02)
                    ch_tones = [t_ + 12 for t_ in tones[:4]]
                    place(self.layers["choir"], bar_s, choir_chord(rng, ch_tones, hold, level=P.get("choir_level", 0.16), vowel=P.get("choir", "ah")))

                # Gitarren-Begleitung
                comp = P.get("comping")
                if comp:
                    lvl = P.get("comp_level", 0.18)
                    if comp == "strum":
                        hits = [(6, True, 1.0, False), (12, False, 0.9, False)]
                    elif comp == "rumba":
                        hits = [(0, True, 1.0, False), (3, False, 0.6, True), (6, True, 0.85, True), (8, True, 1.0, False), (11, False, 0.6, True), (14, True, 0.8, False)]
                    elif comp == "arp6":  # 6/8-Arpeggio
                        hits = None
                        order = [0, 1, 2, 3, 2, 1]
                        for k in range(6):
                            mm = tones[order[k] % len(tones)] + (12 if order[k] == 3 else 0)
                            place(self.layers["guitar"], at(k * 2) + int(rng.normal(0, 0.004) * SR),
                                  nylon_guitar(rng, mm, self.step_len(cur, 3), level=lvl, pan=-0.3 + 0.12 * k))
                    elif comp == "bul":
                        hits = [(st, True, 1.0 if st in (0, 12) else 0.8, False) for st in BUL_ACCENTS] + [(st, False, 0.45, True) for st in BUL_CONTRA]
                    elif comp == "pick":  # ruhiges Zupfmuster
                        hits = None
                        order = [0, 2, 1, 3, 2, 1, 0, 2]
                        for k in range(8):
                            if k % 2 == 1 and rng.random() < 0.3:
                                continue
                            mm = tones[order[k] % len(tones)] + (12 if order[k] == 3 else 0)
                            place(self.layers["guitar"], at(k * 2) + int(rng.normal(0, 0.004) * SR),
                                  nylon_guitar(rng, mm, self.step_len(cur, 3), level=lvl, pan=-0.3 + 0.08 * k))
                    else:
                        hits = None
                    if hits:
                        for st, down, g, muted in hits:
                            place(self.layers["guitar"], at(st) + int(rng.normal(0, 0.004) * SR),
                                  strum_chord(rng, tones, self.step_len(cur, 2 if muted else 3), level=lvl * g, spread=0.012,
                                              pan=-0.25, down=down, muted=muted))

                # Bass
                bass = P.get("bass")
                if bass:
                    blvl = P.get("bass_level", 0.75)
                    stepsb = BASS_STEPS[bass]
                    for i, st in enumerate(stepsb):
                        nxt = stepsb[i + 1] if i + 1 < len(stepsb) else steps
                        m_ = bass_root + (12 if bass in ("roll", "deep") and st in (6, 14) and rng.random() < 0.5 else 0)
                        if bass in BASS_INTERVALS:
                            m_ = bass_root + BASS_INTERVALS[bass][i % len(BASS_INTERVALS[bass])]
                            if b % 4 == 3 and st == 14:
                                m_ = bass_root + 10 if rng.random() < 0.5 else bass_root + 5
                        if P.get("bass_inst", "synth") == "pluck":
                            place(self.layers["bass"], at(st), pluck_bass(rng, m_, int(self.step_len(cur, nxt - st) * 0.9), level=blvl))
                        else:
                            place(self.layers["bass"], at(st),
                                  synth_bass(rng, float(midi_to_hz(m_)), int(self.step_len(cur, nxt - st) * (0.65 if bass in ("roll", "deep", "house") else 0.92)),
                                             level=blvl * (1.0 if st in (0, 8, 12) else 0.85), cutoff=P.get("bass_cut", 600.0), drive=P.get("bass_drive", 1.8)))

                # Drums
                groove = P.get("drums")
                if groove and not (P.get("drums_from", 0) > b):
                    dl = P.get("drum_level", 1.0)
                    for st, sound, g in GROOVES[groove]:
                        if last and P.get("fill") and st >= 12 and sound == "kick" and groove in ("house", "shuffle", "deep"):
                            continue
                        pos = at(st)
                        place(self.layers["drums"], pos, snd[sound] * g * dl)
                        if sound == "kick":
                            self.kick_times.append(pos)
                    for st, sound, g in HATS[P.get("hats", "none")]:
                        place(self.layers["drums"], at(st) + int(rng.normal(0, 0.0015) * SR), snd[sound] * g * dl * rng.uniform(0.85, 1.0))
                    if P.get("ride"):
                        for st in range(0, steps, 2):
                            place(self.layers["drums"], at(st), snd["ride"] * (1.0 if st % 4 == 0 else 0.7))
                    if last and P.get("fill"):
                        for k, st in enumerate((steps - 4, steps - 3, steps - 2, steps - 1)):
                            place(self.layers["drums"], at(st), snd["snare"] * (0.3 + 0.2 * k) * dl)

                # Percussion
                perc = P.get("perc", [])
                pl = P.get("perc_level", 1.0)
                if "cajon" in perc:
                    if meter == "bul":
                        for st in BUL_ACCENTS:
                            place(self.layers["perc"], at(st), (snd["cjb"] if st in (0, 12) else snd["cjs"]) * pl)
                        for st in (4, 8, 18, 22):
                            if rng.random() < 0.6:
                                place(self.layers["perc"], at(st), snd["cjs"] * 0.35 * pl)
                    elif meter == "6/8":
                        place(self.layers["perc"], at(0), snd["cjb"] * pl)
                        place(self.layers["perc"], at(6), snd["cjs"] * 0.8 * pl)
                        for st in (4, 10):
                            place(self.layers["perc"], at(st), snd["cjs"] * 0.3 * pl)
                    else:
                        for st in (0, 8):
                            place(self.layers["perc"], at(st) + int(rng.normal(0, 0.002) * SR), snd["cjb"] * pl)
                        for st in (4, 12):
                            place(self.layers["perc"], at(st) + int(rng.normal(0, 0.002) * SR), snd["cjs"] * pl)
                        for st in (6, 14, 15):
                            if rng.random() < 0.6:
                                place(self.layers["perc"], at(st), snd["cjs"] * 0.35 * pl)
                if "palmas" in perc:
                    if meter == "bul":
                        for st in BUL_ACCENTS:
                            place(self.layers["perc"], at(st) + int(rng.normal(0, 0.004) * SR), snd["secas"] * (1.0 if st in (0, 12) else 0.85) * pl)
                        for st in BUL_CONTRA:
                            place(self.layers["perc"], at(st) + int(rng.normal(0, 0.004) * SR), snd["sordas"] * 0.7 * pl)
                    else:
                        for st in (2, 6, 10, 14):
                            place(self.layers["perc"], at(st) + int(rng.normal(0, 0.004) * SR), snd["secas"] * 0.8 * pl)
                        for st in (4, 12):
                            place(self.layers["perc"], at(st) + int(rng.normal(0, 0.004) * SR), snd["sordas"] * 0.75 * pl)
                if "castanets" in perc:
                    for st in (3, 7, 11) if meter != "bul" else (2, 8, 14, 20):
                        if rng.random() < 0.7:
                            place(self.layers["perc"], at(st), snd["cast"] * 0.75 * pl)
                    if last or b % 4 == 3:
                        for k in range(5):
                            place(self.layers["perc"], at(steps - 1) + int(k * 0.04 * SR), snd["cast"] * (0.45 + 0.1 * k) * pl)
                if "congas" in perc:
                    pat = ((3, 0), (7, 1), (11, 0), (13, 2)) if meter == "4/4" else ((2, 0), (5, 1), (8, 0), (11, 2)) if meter == "6/8" else ((4, 0), (10, 1), (14, 0), (22, 2))
                    for st, ci in pat:
                        if rng.random() < 0.8:
                            place(self.layers["perc"], at(st) + int(rng.normal(0, 0.003) * SR), congas[ci] * 0.75 * pl)
                if "rimloop" in perc:
                    for st in (3, 6, 9, 13) + ((11,) if b % 2 else ()):
                        place(self.layers["perc"], at(st) + int(rng.normal(0, 0.0015) * SR), snd["rim"] * 0.55 * pl)
                if "shaker" in perc:
                    for st in range(0, steps, 2):
                        place(self.layers["perc"], at(st) + int(rng.normal(0, 0.002) * SR), snd["shaker"] * (1.0 if st % 4 == 0 else 0.5) * 0.7 * pl)
                if "toms" in perc:
                    # Trommel-Stakkato: Frage (Cajón) und Antwort (Toms), dichter zum Phrasenende
                    dens = 0.35 + 0.5 * (b % 4) / 3
                    for st in range(steps):
                        if st % 4 == 0 or rng.random() < dens:
                            t_ = (snd["tom_h"], snd["tom_m"], snd["tom_l"])[(st // 2 + b) % 3]
                            if (b % 2 == 0 and st < steps // 2) or (b % 2 == 1 and st >= steps // 2):
                                place(self.layers["perc"], at(st), t_ * (0.9 if st % 4 == 0 else 0.6) * pl)
                    if b % 4 == 3:
                        for k, st in enumerate(range(steps - 6, steps)):
                            place(self.layers["perc"], at(st), (snd["tom_h"], snd["tom_m"], snd["tom_l"])[k % 3] * (0.5 + 0.08 * k) * pl)

                # Stabs
                stabs = P.get("stabs")
                if stabs:
                    for st in P.get("stab_steps", (2, 10)):
                        if stabs == "brass":
                            place(self.layers["brass"], at(st), brass_stab(rng, [t_ + 12 for t_ in tones[:3]], self.step_len(cur, 1.5), level=P.get("stab_level", 0.2)))
                        elif stabs == "dub":
                            place(self.layers["stab"], at(st), house_stab(rng, [t_ + 12 for t_ in tones[:4]], self.step_len(cur, 1.6),
                                                                         level=P.get("stab_level", 0.16), cutoff=1100.0, pan=rng.uniform(-0.2, 0.2)))
                        else:
                            place(self.layers["stab"], at(st), house_stab(rng, [t_ + 12 for t_ in tones[:4]], self.step_len(cur, 1.2),
                                                                         level=P.get("stab_level", 0.18), cutoff=2000.0, pan=rng.uniform(-0.3, 0.3)))

                # Acid
                if P.get("acid"):
                    lvl, cut = P["acid"], P.get("acid_cut", 380.0)
                    prev = None
                    for st, iv, acc, slide in ((0, 0, True, False), (3, 0, False, False), (6, 12, False, True), (8, 0, True, False),
                                               (10, 7, False, False), (11, 10, False, True), (14, 0, False, False), (15, 12, False, False)):
                        m_ = bass_root + 12 + iv
                        place(self.layers["acid"], at(st), acid_note(rng, m_, self.step_len(cur, 1.3 if slide else 0.6), prev_midi=prev if slide else None,
                                                                    accent=acc, level=lvl, base_cut=cut, env_amount=2200.0, q=6.5))
                        prev = m_

                # Trance-Arpeggio
                if P.get("arp"):
                    arp = sorted({t_ + 12 for t_ in tones[:4]} | {t_ + 24 for t_ in tones[:2]})
                    order = arp + arp[-2:0:-1]
                    for st in range(steps):
                        if st % 4 == 3:
                            continue
                        place(self.layers["trance"], at(st), trance_pluck(rng, order[(st + b * 2) % len(order)], self.step_len(cur, 0.6),
                                                                          level=P["arp"], pan=0.55 if st % 2 else -0.55))

                # Effekte
                fx = P.get("fx", [])
                if "riser" in fx and b == max(0, sec["bars"] - 4):
                    place(self.layers["trance"], bar_s, riser(rng, int(sum(x["len"] for x in self.bars[cur:cur + 4]) * SR), level=0.14))
                if "roll" in fx and last:
                    for st in range(steps):
                        place(self.layers["drums"], at(st), snd["snare"] * (0.2 + 0.7 * st / (steps - 1)))
                if "crash" in fx and b == 0:
                    place(self.layers["drums"], bar_s, snd["crash"])
                if "bell" in fx and b % 4 == 0:
                    for k, semi in enumerate(P.get("bell_motif", [(0, 7), (6, 12), (12, 5)])):
                        st, sm = semi
                        place(self.layers["bell"], at(st), bell(rng, root + 12 + sm, self.step_len(cur, 6), level=0.22, pan=0.2 * (k - 1)))
                if "final_chord" in fx and b == 0:
                    final = voice(CH[prog[0]] + [14], root)
                    place(self.layers["guitar"], bar_s, strum_chord(rng, final, int(3.0 * SR), level=0.34, spread=0.05))
                    place(self.layers["pad"], bar_s, pad_chord(rng, final, int(6.0 * SR), cutoff=650.0, level=0.22, attack=1.2, release=4.0))
                if "final_choir" in fx and b == 0:
                    final = voice(CH[prog[0]] + [14], root)
                    place(self.layers["choir"], bar_s, choir_chord(rng, [t_ + 12 for t_ in final[:4]], int(7.0 * SR), level=0.18, vowel="oo", attack=1.5, release=5.0))
                if "stop_note" in fx and b == 0:
                    place(self.layers["flute"], bar_s, flute(rng, root + 19, int(bar["len"] * SR * 1.8), level=0.28, pan=0.0))
        return self.mix()

    def mix(self):
        rng = self.rng
        L = self.layers
        P_all = self.spec
        dub = P_all.get("dub", False)
        ir_long = make_reverb_ir(rng, 3.2, 1.9, 3600.0)
        ir_room = make_reverb_ir(rng, 1.2, 4.5, 5000.0, 0.008)
        ir_huge = make_reverb_ir(rng, 5.5, 1.1, 3000.0, 0.03)
        duck = np.ones(self.n)
        curve_n = int(0.32 * SR)
        curve = 1.0 - P_all.get("duck", 0.5) * np.exp(-np.linspace(0, 5, curve_n))
        for kt in self.kick_times:
            end = min(self.n, kt + curve_n)
            if kt < self.n:
                duck[kt:end] = np.minimum(duck[kt:end], curve[: end - kt])
        d = np.clip(lowpass(duck, 60.0), 0.35, 1.0)[:, None]

        pad = reverb(chorus_widen(L["pad"], rng), ir_long, 0.75) * d   # weit hinten
        if hasattr(self, "wave_env") and P_all.get("pad_breathes", False):
            pad *= (0.6 + 0.4 * self.wave_env)[:, None]
        choir = reverb(chorus_widen(L["choir"], rng, 6.0, 0.18), ir_huge, 0.7)
        lead_l = reverb(delay(L["lead"], self.beat_len(0) * 1.5, 0.42, 6, 2600.0, True, 0.3), ir_long, 0.42)
        guitar = reverb(delay(L["guitar"], self.beat_len(0) * 0.75, 0.22, 2, 3200.0, False, 0.1), ir_room, 0.22)  # vorn, trocken
        brass = reverb(delay(L["brass"], self.beat_len(0) * (1.5 if dub else 0.75), 0.55 if dub else 0.3, 7 if dub else 3, 2400.0, True, 0.45 if dub else 0.2),
                       ir_huge if dub else ir_long, 0.45 if dub else 0.38)
        flute_l = reverb(delay(L["flute"], self.beat_len(0) * 1.5, 0.35, 4, 3000.0, True, 0.22), ir_long, 0.42)
        steel = reverb(delay(L["steel"], self.beat_len(0) * 0.75, 0.3, 3, 3500.0, True, 0.2), ir_long, 0.35) * (0.6 + 0.4 * d)
        bell_l = reverb(delay(L["bell"], self.beat_len(0) * 1.5, 0.4, 5, 3000.0, True, 0.3), ir_huge, 0.6)
        perc = reverb(L["perc"], ir_room, 0.16)
        drums = reverb(L["drums"], ir_room, 0.06)
        bass = L["bass"] * (0.6 + 0.4 * d) * P_all.get("bass_boost", 1.0)
        acid = reverb(delay(L["acid"], self.beat_len(0) * 0.75, 0.3, 3, 2400.0, True, 0.18), ir_room, 0.16) * (0.7 + 0.3 * d)
        trance = reverb(delay(L["trance"], self.beat_len(0) * 0.75, 0.4, 5, 3200.0, True, 0.3), ir_long, 0.5) * d
        stab = reverb(delay(L["stab"], self.beat_len(0) * P_all.get("stab_delay", 1.5), P_all.get("stab_fb", 0.35), 6 if P_all.get("stab_fb", 0.35) > 0.4 else 4, 2600.0, True, 0.3), ir_long, 0.3) * d
        atmos = L["atmos"]

        # Akustische Stimmen vorn, Synthesizer-Flächen hinten
        parts = dict(drums=drums * 1.0, perc=perc * 1.25, bass=bass * 1.0, pad=pad * 1.0, lead=lead_l * 1.05,
                     guitar=guitar * 2.4, brass=brass * 1.65, flute=flute_l * 1.75, steel=steel * 1.5, atmos=atmos * 1.8,
                     acid=acid * 1.3, stab=stab * 1.5, trance=trance * 1.1, choir=choir * 1.05, bell=bell_l * 1.3)
        if os.environ.get("ALBUM_DEBUG"):
            for k, v in parts.items():
                r = np.sqrt(np.mean(v ** 2)) + 1e-9
                print(f"      {k:7s} {20*np.log10(r):6.1f} dBFS", file=sys.stderr)
        mixv = sum(parts.values())
        mixv = highpass(mixv, 28.0)
        mixv *= self.dyn_curve[:, None]
        fade_in = int(0.4 * SR)
        mixv[:fade_in] *= np.linspace(0, 1, fade_in)[:, None]
        tail = int(6.0 * SR)
        mixv[-tail:] *= np.linspace(1, 0, tail)[:, None] ** 1.2
        return master_chain(mixv) * 0.85  # Hintergrundmusik: etwas Luft lassen


# --------------------------------------------------------------------------- #
# Themen (Notation: (pos, halbton, dauer) in Einheiten je Takt: 8 = Achtel im 4/4,
# 6 = Achtel im 6/8, 12 = Zählzeiten im Bulería-Compás)
# --------------------------------------------------------------------------- #
import compose_song as _cs  # noqa: E402

_OLD = {sp["nr"]: sp for sp in _cs.SONGS}


def _major_variant(theme):
    return [[(p, {3: 4, 10: 11}.get(s_, s_), d) for p, s_, d in ph] for ph in theme]


def _frag(theme):
    first = list(theme[0][:3])
    p, s_, d = first[-1]
    first[-1] = (p, s_, max(d, 4))
    return [first, first[:2] + [(first[-1][0], first[-1][1], 6)]]


T_PLAYA = dict(A=_OLD[8]["theme_a"], B=_OLD[8]["theme_b"], frag=_frag(_OLD[8]["theme_a"]))
T_CONCHA = dict(A=_OLD[2]["theme_a"], B=_OLD[2]["theme_b"], frag=_frag(_OLD[2]["theme_a"]))
T_GOLDEN = dict(
    A=[[(0, 7, 2), (2, 8, 1), (3, 7, 2), (5, 5, 1), (6, 4, 2), (8, 5, 1), (9, 7, 1), (10, 8, 2),
        (12, 7, 2), (14, 5, 1), (15, 4, 2), (17, 1, 1), (18, 0, 2), (20, 4, 2), (22, 1, 1), (23, 0, 1)],
       [(0, 12, 2), (2, 13, 1), (3, 12, 2), (5, 10, 1), (6, 8, 2), (8, 7, 1), (9, 8, 1), (10, 10, 2),
        (12, 12, 2), (14, 10, 1), (15, 8, 2), (17, 7, 1), (18, 5, 2), (20, 4, 2), (22, 1, 1), (23, 0, 1)]],
    B=[[(0, 12, 3), (3, 10, 1), (4, 12, 2), (6, 13, 2), (8, 12, 1), (9, 10, 1), (10, 8, 2),
        (12, 7, 3), (15, 8, 1), (16, 7, 2), (18, 5, 2), (20, 4, 2), (22, 0, 2)],
       [(0, 12, 3), (3, 10, 1), (4, 12, 2), (6, 13, 2), (8, 12, 1), (9, 10, 1), (10, 8, 2),
        (12, 7, 2), (14, 8, 1), (15, 10, 1), (16, 12, 2), (18, 13, 2), (20, 12, 4)]],
)
T_GOLDEN["frag"] = [[(0, 7, 2), (2, 8, 1), (3, 7, 4)], [(0, 7, 2), (2, 8, 1), (3, 7, 6)]]
T_CABOPINO = dict(
    A=[[(0, 7, 3), (3, 10, 1), (4, 12, 4), (8, 10, 2), (10, 7, 2), (12, 5, 4), (16, 7, 3), (19, 8, 1), (20, 7, 2), (22, 3, 2), (24, 5, 6), (30, 3, 2)],
       [(0, 7, 3), (3, 10, 1), (4, 12, 4), (8, 10, 2), (10, 12, 2), (12, 15, 4), (16, 14, 3), (19, 12, 1), (20, 10, 2), (22, 7, 2), (24, 8, 4), (28, 7, 4)]],
    B=[[(0, 12, 2), (2, 15, 1), (3, 12, 1), (4, 10, 2), (6, 7, 2), (8, 8, 2), (10, 10, 1), (11, 8, 1), (12, 7, 2), (14, 5, 2),
        (16, 7, 3), (19, 10, 1), (20, 12, 2), (22, 14, 2), (24, 15, 2), (26, 14, 2), (28, 12, 4)],
       [(0, 12, 2), (2, 15, 1), (3, 12, 1), (4, 10, 2), (6, 7, 2), (8, 8, 2), (10, 10, 1), (11, 8, 1), (12, 7, 2), (14, 5, 2),
        (16, 7, 2), (18, 8, 2), (20, 10, 2), (22, 12, 2), (24, 10, 2), (26, 8, 2), (28, 7, 4)]],
    call=[[(0, 7, 6), (8, 12, 8), (16, 10, 4), (20, 7, 8)]],
)
T_CABOPINO["frag"] = _frag(T_CABOPINO["A"])
T_BANUS = dict(A=_OLD[5]["theme_a"], B=_OLD[5]["theme_b"], frag=_frag(_OLD[5]["theme_a"]))
T_SIERRA = dict(
    A=[[(0, 7, 2), (2, 9, 1), (3, 12, 3), (6, 10, 2), (8, 9, 1), (9, 7, 3), (12, 5, 2), (14, 7, 1), (15, 9, 2), (17, 7, 1), (18, 5, 3), (21, 3, 3)],
       [(0, 7, 2), (2, 9, 1), (3, 12, 3), (6, 14, 2), (8, 12, 1), (9, 10, 3), (12, 9, 2), (14, 7, 1), (15, 5, 2), (17, 3, 1), (18, 2, 3), (21, 0, 3)]],
    B=[[(0, 12, 3), (3, 14, 2), (5, 12, 1), (6, 9, 3), (9, 10, 2), (11, 9, 1), (12, 7, 2), (14, 9, 1), (15, 12, 3), (18, 10, 3), (21, 9, 3)],
       [(0, 12, 3), (3, 14, 2), (5, 12, 1), (6, 15, 3), (9, 14, 2), (11, 12, 1), (12, 10, 2), (14, 9, 1), (15, 7, 3), (18, 7, 3), (21, 5, 3)]],
)
T_SIERRA["Bmaj"] = _major_variant(T_SIERRA["B"])
T_SIERRA["Amaj"] = _major_variant(T_SIERRA["A"])
T_SIERRA["frag"] = [[(0, 7, 2), (2, 9, 1), (3, 12, 3)], [(0, 7, 2), (2, 9, 1), (3, 12, 9)]]
T_CASCO = dict(A=_OLD[7]["theme_a"], B=_OLD[7]["theme_b"], frag=_frag(_OLD[7]["theme_a"]))
T_FONTANILLA = dict(A=_OLD[1]["theme_a"], B=_OLD[1]["theme_b"], frag=_frag(_OLD[1]["theme_a"]), opener=_OLD[8]["theme_a"])
T_PASEO = dict(walk=[[(0, 7, 3), (3, 8, 1), (4, 7, 2), (6, 4, 2), (8, 5, 4), (12, 4, 2), (14, 1, 2), (16, 0, 6), (24, 4, 3), (27, 5, 1), (28, 7, 4)],
                     [(0, 7, 3), (3, 8, 1), (4, 10, 2), (6, 8, 2), (8, 7, 4), (12, 5, 2), (14, 4, 2), (16, 1, 6), (24, 0, 8)]])
T_FAROLA = dict(motif=[[(0, 7, 6), (8, 12, 8), (16, 10, 6), (24, 7, 8)]])


# --------------------------------------------------------------------------- #
# Die Partitur: Abend, Nacht, Morgen
# --------------------------------------------------------------------------- #
TRACKS = [
    dict(nr=1, title="Playa de Nagüeles, 9 p.m.", seed=8808, root=50, mode="D dorisch", style="House, Acid, Chill",
         scale=[0, 2, 3, 5, 7, 9, 10], themes=T_PLAYA, pad_breathes=True, kick_punch=1.25, duck=0.62, stab_delay=3.0, stab_fb=0.5, bass_boost=1.25,
         progs=dict(verse=["i7", "IV", "i7", "IV"], refrain=["bVII", "IV", "i7", "ii7"], quiet=["ii7", "bVII", "ii7", "IV"]),
         sections=[
             S("intro", 8, bpm=118, dyn=0.6, melody=[mel("A", "guitar", 0.4, ornaments=True, humanize=0.02, legato=1.1)], atmos=dict(waves=1.0, crickets=0.3)),
             S("arrival", 8, bpm=118, dyn=0.72, drums="kickonly", drum_level=0.8, hats="offbeat", perc=["cajon", "shaker"], perc_level=0.8, bass="house", bass_level=0.85, bass_cut=560.0,
               comping="pick", comp_level=0.15, pad=600, pad_level=0.6, atmos=dict(waves=0.5)),
             S("groove1", 16, bpm=118, dyn=0.82, drums="house", drum_level=0.88, hats="full", bass="house", bass_level=0.9, bass_cut=620.0, acid=0.16, acid_cut=320.0,
               comping="strum", comp_level=0.16, pad=750, pad_level=0.6, perc=["shaker", "congas", "rimloop"], perc_level=0.8, fill=True,
               melody=[mel("A", "flute", 0.23)], answer="steel", answer_level=0.1, atmos=dict(waves=0.25)),
             S("lift1", 16, bpm=118, prog="refrain", dyn=0.92, drums="house", drum_level=0.95, hats="full", bass="house", bass_level=0.92, bass_cut=700.0, acid=0.22, acid_cut=380.0,
               comping="strum", comp_level=0.17, pad=950, pad_level=0.6, choir="ah", choir_level=0.1, perc=["shaker", "congas", "palmas"], stabs="dub", stab_steps=(2, 10), stab_level=0.12, fill=True,
               melody=[mel("B", "flute", 0.25), mel("B", "guitar", 0.3, octave=0, pan=0.3, legato=0.8)], atmos=dict(waves=0.15)),
             S("groove2", 16, bpm=118, dyn=0.88, drums="house", drum_level=0.92, hats="techno16", bass="house", bass_level=0.9, bass_cut=660.0, acid=0.24, acid_cut=420.0,
               comping="pick", comp_level=0.15, pad=800, pad_level=0.55, perc=["shaker", "congas", "rimloop"], perc_level=0.85, fill=True,
               melody=[mel("A", "guitar", 0.4, ornaments=True)], answer="flute", answer_level=0.11),
             S("breath", 8, bpm=118, prog="quiet", dyn=0.68, pad=600, pad_level=0.7, choir="ah", choir_level=0.14, bass="one", bass_level=0.55, bass_cut=380.0, acid=0.14, acid_cut=260.0,
               melody=[mel("frag", "guitar", 0.35, humanize=0.02, legato=1.2)], fx=["riser", "roll"], atmos=dict(waves=0.7, crickets=0.4)),
             S("peak", 24, bpm=118, prog="refrain", dyn=1.0, drums="house", drum_level=1.0, hats="techno16", bass="house", bass_level=0.95, bass_cut=800.0, bass_drive=2.2, acid=0.3, acid_cut=520.0,
               comping="strum", comp_level=0.17, pad=1100, pad_level=0.6, choir="ah", choir_level=0.12, stabs="dub", stab_steps=(2, 7, 10, 15), stab_level=0.14,
               perc=["shaker", "congas", "palmas", "rimloop"], perc_level=0.9, fx=["crash"], fill=True,
               melody=[mel("B", "flute", 0.26), mel("B", "guitar", 0.3, octave=0, pan=0.3, legato=0.8), mel("A", "steel", 0.13, octave=24, pan=0.5, offset=8, bars=16, legato=0.6)],
               atmos=dict(waves=0.1)),
             S("release", 8, bpm=118, dyn=0.78, drums="house", drum_level=0.8, hats="offbeat", bass="house", bass_level=0.8, bass_cut=560.0, acid=0.16, acid_cut=320.0, pad=700, pad_level=0.55,
               choir="oo", choir_level=0.1, comping="pick", comp_level=0.14, perc=["shaker", "congas"], perc_level=0.6, melody=[mel("A", "guitar", 0.38, ornaments=True)], atmos=dict(waves=0.4)),
             S("outro", 8, bpm=118, dyn=0.6, pad=600, pad_level=0.6, choir="oo", choir_level=0.1, melody=[mel("A", "guitar", 0.4, humanize=0.02, legato=1.25)],
               atmos=dict(waves=1.0, crickets=0.4)),
             S("end", 2, bpm=118, dyn=0.55, fx=["final_chord"], atmos=dict(waves=1.0)),
         ]),

    dict(nr=2, title="La Concha Horizon", seed=2202, root=55, mode="G-Moll, andalusische Kadenz", style="Deep House, Acid",
         scale=[0, 2, 3, 5, 7, 8, 10], themes=T_CONCHA, kick_punch=1.2, duck=0.6, bass_boost=1.2, stab_delay=3.0, stab_fb=0.5,
         progs=dict(verse=["i", "VII", "VI", "V"], refrain=["VI", "VII", "i", "V7"], bridge=["iv7", "V", "iv7", "V"], climax=["VI7", "VII", "i9", "V7"]),
         sections=[
             S("intro", 8, bpm=122, dyn=0.64, pad=700, pad_level=0.6, bass="long", bass_level=0.6, bass_cut=400.0, perc=["shaker"], perc_level=0.5,
               melody=[mel("frag", "mtrumpet", 0.24, legato=1.3, humanize=0.02)], atmos=dict(crickets=0.3, cicadas=0.2)),
             S("deep1", 24, bpm=122, dyn=0.8, drums="deep", drum_level=0.9, hats="eighths", bass="house", bass_level=0.88, bass_cut=560.0,
               comping="rumba", comp_level=0.13, pad=850, pad_level=0.6, perc=["shaker", "rimloop"], perc_level=0.8, fill=True,
               melody=[mel("A", "mtrumpet", 0.26)], answer="guitar", answer_level=0.13),
             S("build", 8, bpm=122, dyn=0.88, drums="house", drum_level=0.92, hats="full", bass="house", bass_level=0.9, bass_cut=640.0, acid=0.2, acid_cut=340.0,
               comping="rumba", comp_level=0.14, pad=1000, pad_level=0.6, perc=["shaker", "palmas", "rimloop"], perc_level=0.8, fill=True,
               melody=[mel("A", "guitar", 0.38, ornaments=True)]),
             S("chorus1", 16, bpm=122, prog="refrain", dyn=0.94, drums="house", drum_level=0.96, hats="full", bass="house", bass_level=0.92, bass_cut=720.0, acid=0.24, acid_cut=400.0,
               comping="rumba", comp_level=0.15, pad=1300, pad_level=0.6, stabs="brass", stab_steps=(2, 10), stab_level=0.17, perc=["palmas", "shaker", "congas"], fill=True,
               melody=[mel("B", "trumpet", 0.26), mel("B", "guitar", 0.27, octave=0, pan=0.3, legato=0.8)]),
             S("brass_break", 8, bpm=122, prog="refrain", dyn=0.9, drums="kickonly", drum_level=1.0, hats="techno16", bass="house", bass_level=0.92, bass_cut=700.0, bass_drive=2.2, acid=0.26, acid_cut=440.0,
               stabs="brass", stab_steps=(2, 5, 10, 13), stab_level=0.24, perc=["palmas", "rimloop"], perc_level=0.9, pad=900, pad_level=0.5, fill=True),
             S("deep2", 16, bpm=122, dyn=0.84, drums="deep", drum_level=0.9, hats="eighths", bass="house", bass_level=0.88, bass_cut=580.0, acid=0.18, acid_cut=340.0,
               comping="rumba", comp_level=0.13, pad=850, pad_level=0.55, perc=["shaker", "congas", "rimloop"], perc_level=0.8, melody=[mel("A", "mtrumpet", 0.26)], answer="guitar", answer_level=0.13),
             S("chorus2", 16, bpm=122, prog="refrain", dyn=0.96, drums="house", drum_level=0.96, hats="full", bass="house", bass_level=0.92, bass_cut=740.0, acid=0.24, acid_cut=420.0,
               comping="rumba", comp_level=0.15, pad=1350, pad_level=0.6, stabs="brass", stab_steps=(2, 10), stab_level=0.18, perc=["palmas", "shaker", "congas"], fill=True,
               melody=[mel("B", "trumpet", 0.26), mel("B", "guitar", 0.27, octave=0, pan=0.3, legato=0.8), mel("A", "steel", 0.13, octave=24, pan=0.5, offset=8, bars=8, legato=0.6)]),
             S("breakdown", 8, bpm=122, prog="bridge", dyn=0.7, bass="one", bass_level=0.55, bass_cut=420.0, pad=800, pad_level=0.7, acid=0.14, acid_cut=280.0, fx=["riser", "roll"],
               melody=[mel("frag", "mtrumpet", 0.24, legato=1.3, humanize=0.02)], atmos=dict(cicadas=0.5, crickets=0.3)),
             S("chorus3", 16, bpm=122, prog="climax", dyn=1.0, drums="house", drum_level=1.0, hats="techno16", ride=True, bass="house", bass_level=0.95, bass_cut=820.0, bass_drive=2.2, acid=0.3, acid_cut=520.0,
               comping="rumba", comp_level=0.16, pad=1500, pad_level=0.6, stabs="brass", stab_steps=(2, 10), stab_level=0.2, perc=["palmas", "shaker", "congas", "rimloop"], perc_level=0.9,
               fx=["crash"], fill=True,
               melody=[mel("B", "trumpet", 0.28), mel("B", "guitar", 0.27, octave=0, pan=0.3, legato=0.8), mel("A", "steel", 0.13, octave=24, pan=0.5, offset=8, bars=8, legato=0.6)]),
             S("outro1", 8, bpm=122, dyn=0.76, drums="deep", drum_level=0.8, hats="offbeat", bass="house", bass_level=0.8, bass_cut=520.0, acid=0.14, acid_cut=300.0, pad=850, pad_level=0.55,
               perc=["shaker"], melody=[mel("frag", "mtrumpet", 0.22, legato=1.3)]),
             S("outro2", 8, bpm=122, dyn=0.6, pad=700, pad_level=0.6, melody=[mel("frag", "mtrumpet", 0.22, legato=1.4, humanize=0.02)], atmos=dict(crickets=0.4)),
             S("end", 2, bpm=122, dyn=0.55, fx=["final_chord"]),
         ]),

    dict(nr=3, title="Golden Mile Breeze", seed=3303, root=57, mode="A phrygisch-dominant (por medio)", style="Flamenco Chill, Bulería",
         scale=[0, 1, 4, 5, 7, 8, 10], themes=T_GOLDEN, units=12,
         progs=dict(verse=["I", "bIImaj", "I", "bIImaj"], refrain=["iv", "bIII", "bIImaj", "I"]),
         sections=[
             S("intro", 4, meter="bul", bpm=150, dyn=0.6, melody=[mel("A", "guitar", 0.42, ornaments=True, humanize=0.02, legato=1.1)], atmos=dict(cicadas=0.6)),
             S("copla1", 10, meter="bul", bpm=150, dyn=0.75, perc=["palmas", "cajon"], perc_level=0.8, comping="bul", comp_level=0.15, bass="bul", bass_inst="pluck", bass_level=0.7,
               drums="bul", drum_level=0.6, pad=700, choir="oo", choir_level=0.1, melody=[mel("A", "guitar", 0.4, ornaments=True)], answer="steel", answer_level=0.1, atmos=dict(cicadas=0.4)),
             S("estribillo1", 8, meter="bul", bpm=150, prog="refrain", dyn=0.86, perc=["palmas", "cajon", "castanets"], perc_level=0.9, comping="bul", comp_level=0.16,
               bass="bul", bass_level=0.7, bass_cut=450.0, drums="bul", drum_level=0.7, pad=900,
               melody=[mel("B", "choir", 0.16), mel("B", "guitar", 0.3, octave=0, legato=0.8)]),
             S("copla2", 8, meter="bul", bpm=150, dyn=0.8, perc=["palmas", "cajon"], perc_level=0.85, comping="bul", comp_level=0.15, bass="bul", bass_inst="pluck", bass_level=0.7,
               drums="bul", drum_level=0.6, pad=750, melody=[mel("A", "flute", 0.24)], answer="guitar", answer_level=0.12),
             S("palmas_solo", 4, meter="bul", bpm=150, dyn=0.82, perc=["palmas", "cajon", "castanets"], perc_level=1.2, atmos=dict(cicadas=0.3)),
             S("estribillo2", 10, meter="bul", bpm=150, prog="refrain", dyn=0.95, perc=["palmas", "cajon", "castanets"], perc_level=1.0, comping="bul", comp_level=0.17,
               bass="bul", bass_level=0.75, bass_cut=480.0, drums="bul", drum_level=0.75, pad=1000,
               melody=[mel("B", "choir", 0.18), mel("B", "guitar", 0.3, octave=0, legato=0.8), mel("B", "flute", 0.14, octave=24, pan=0.3)]),
             S("outro", 6, meter="bul", bpm=150, dyn=0.6, choir="oo", choir_level=0.1, melody=[mel("A", "guitar", 0.4, legato=1.2, humanize=0.02)], atmos=dict(cicadas=0.6)),
             S("end", 1, meter="bul", bpm=150, dyn=0.55, fx=["final_chord"], atmos=dict(cicadas=0.6)),
         ]),

    dict(nr=3.5, title="Paseo", seed=3535, root=57, mode="A phrygisch-dominant", style="Zwischenspiel", interlude=True,
         scale=[0, 1, 4, 5, 7, 8, 10], themes=T_PASEO,
         progs=dict(verse=["I", "bIImaj", "I", "bIImaj"]),
         sections=[S("walk", 22, bpm=92, dyn=0.6, comping="pick", comp_level=0.13, perc=["cajon"], perc_level=0.5, pad=600, pad_level=0.6,
                     melody=[mel("walk", "guitar", 0.38, ornaments=True, humanize=0.015, legato=1.1)], atmos=dict(cicadas=0.7, crickets=0.3)),
                   S("end", 1, bpm=92, dyn=0.55, fx=["final_chord"], atmos=dict(cicadas=0.7))]),

    dict(nr=4, title="Cabopino Drum Circle", seed=4404, root=52, mode="E-Moll", style="Chill, tribal, Trommel-Break",
         scale=[0, 2, 3, 5, 7, 8, 10], themes=T_CABOPINO,
         progs=dict(verse=["i7", "VI", "III", "VII"], dance=["i7", "VII", "VI", "VII"], quiet=["iv7", "VI", "VII", "VII"]),
         sections=[
             S("fire", 8, bpm=116, dyn=0.6, perc=["cajon", "shaker"], perc_level=0.7, pad=500, pad_level=0.5, atmos=dict(crickets=0.5, cicadas=0.2)),
             S("circle1", 24, bpm=116, dyn=0.72, perc=["cajon", "congas", "shaker"], perc_level=1.0, drums="halftime", drum_level=0.6, bass="long", bass_inst="pluck", bass_level=0.7,
               pad=600, melody=[mel("call", "flute", 0.22, offset=12, bars=8)]),
             S("call", 20, bpm=116, dyn=0.8, drums="halftime", drum_level=0.7, hats="eighths", bass="long", bass_inst="pluck", bass_level=0.72, comping="strum", comp_level=0.14,
               perc=["cajon", "congas", "shaker"], perc_level=0.9, pad=700, melody=[mel("A", "flute", 0.24)], answer="guitar", answer_level=0.12),
             S("break", 16, bpm=116, prog="quiet", dyn=0.86, perc=["toms", "cajon", "congas"], perc_level=1.1, drums="halftime", drum_level=0.6, bass="one", bass_level=0.6, bass_cut=400.0,
               pad=500, pad_level=0.5, fx=["roll"]),
             S("dance", 16, bpm=116, prog="dance", dyn=0.94, drums="house", drum_level=0.9, hats="full", bass="roll", bass_level=0.75, bass_cut=600.0, acid=0.18, acid_cut=320.0,
               comping="rumba", comp_level=0.12, perc=["congas", "palmas", "cajon"], perc_level=0.8, pad=900, fx=["crash"], fill=True,
               melody=[mel("B", "flute", 0.26)]),
             S("dance2", 20, bpm=116, prog="dance", dyn=1.0, drums="house", drum_level=0.95, hats="full", bass="roll", bass_level=0.8, bass_cut=640.0, acid=0.22, acid_cut=380.0,
               comping="rumba", comp_level=0.13, perc=["congas", "palmas", "cajon", "toms"], perc_level=0.75, pad=1000, fill=True,
               melody=[mel("B", "flute", 0.26), mel("A", "guitar", 0.3, octave=0, pan=0.3, offset=8, bars=8)]),
             S("stop", 2, bpm=116, dyn=0.7, fx=["stop_note"], atmos=dict(crickets=0.4)),
             S("embers", 8, bpm=116, prog="quiet", dyn=0.55, perc=["cajon"], perc_level=0.5, pad=500, pad_level=0.5,
               melody=[mel("frag", "guitar", 0.32, humanize=0.02, legato=1.2)], atmos=dict(crickets=0.6)),
         ]),

    dict(nr=5, title="Puerto Banús Nights", seed=5505, root=59, mode="H-Moll", style="Deep House, dann Trance",
         scale=[0, 2, 3, 5, 7, 8, 10], themes=T_BANUS,
         progs=dict(verse=["i7", "VI7", "III7", "VII"], refrain=["VI7", "VII", "i7", "III7"], bridge=["iv7", "v7", "VI7", "VI7"], climax=["VI7", "VII", "i9", "III7"]),
         sections=[
             S("harbor", 8, bpm=124, dyn=0.6, pad=600, choir="oo", choir_level=0.1, choir_every=2, fx=["bell"], atmos=dict(crickets=0.5)),
             S("deep1", 20, bpm=124, dyn=0.78, drums="deep", drum_level=0.85, hats="offbeat", bass="deep", bass_level=0.75, bass_cut=500.0, stabs="house", stab_steps=(2, 10), stab_level=0.11,
               pad=900, perc=["shaker"], melody=[mel("A", "lead", 0.2)], answer="steel", answer_level=0.1),
             S("deep2", 16, bpm=124, dyn=0.84, drums="deep", drum_level=0.9, hats="full", bass="deep", bass_level=0.8, bass_cut=540.0, acid=0.16, acid_cut=300.0,
               stabs="house", stab_steps=(2, 10), stab_level=0.13, pad=1000, perc=["shaker"], melody=[mel("A", "lead", 0.22)], answer="steel", answer_level=0.1),
             S("lift1", 16, bpm=124, prog="refrain", dyn=0.9, drums="house", drum_level=0.9, hats="full", bass="roll", bass_level=0.8, bass_cut=600.0, choir="ah", choir_level=0.12,
               stabs="house", stab_steps=(2, 7, 10, 15), stab_level=0.15, pad=1300, fill=True,
               melody=[mel("B", "lead", 0.25), mel("B", "steel", 0.12, octave=24, pan=-0.3, legato=0.7)]),
             S("breakdown", 8, bpm=124, prog="bridge", dyn=0.7, pad=900, choir="ah", choir_level=0.16, arp=0.08, bass="one", bass_level=0.5, bass_cut=400.0, fx=["bell"]),
             S("build", 8, bpm=124, prog="bridge", dyn=0.8, drums="house", drums_from=4, drum_level=0.8, hats="full", arp=0.11, bass="roll", bass_level=0.7, bass_cut=560.0,
               pad=1000, choir="ah", choir_level=0.12, fx=["riser", "roll"]),
             S("trance", 16, bpm=124, shift=2, prog="climax", dyn=1.0, drums="house", drum_level=1.0, hats="full", ride=True, bass="roll", bass_level=0.85, bass_cut=800.0, arp=0.12,
               stabs="house", stab_steps=(2, 7, 10, 15), stab_level=0.15, choir="ah", choir_level=0.12, pad=1600, fx=["crash"], fill=True,
               melody=[mel("B", "hook", 0.16), mel("B", "lead", 0.2, octave=24, pan=-0.1)]),
             S("trance2", 16, bpm=124, shift=2, prog="climax", dyn=1.0, drums="house", drum_level=1.0, hats="full", ride=True, bass="roll", bass_level=0.85, bass_cut=800.0, arp=0.12,
               stabs="house", stab_steps=(2, 7, 10, 15), stab_level=0.15, choir="ah", choir_level=0.12, pad=1600, fill=True,
               melody=[mel("B", "hook", 0.17), mel("B", "lead", 0.2, octave=24, pan=-0.1), mel("A", "steel", 0.14, octave=24, pan=0.5, offset=8, bars=8, legato=0.6)]),
             S("fade1", 8, bpm=124, shift=2, dyn=0.7, drums="deep", drum_level=0.7, hats="offbeat", bass="deep", bass_level=0.7, bass_cut=500.0, arp=0.08, pad=1000,
               choir="oo", choir_level=0.12, fx=["bell"]),
             S("fade2", 8, bpm=124, shift=2, dyn=0.55, pad=700, choir="oo", choir_level=0.12, bass="one", bass_level=0.4, bass_cut=380.0, fx=["bell"], atmos=dict(crickets=0.5)),
             S("end", 2, bpm=124, shift=2, dyn=0.5, fx=["final_choir"], atmos=dict(crickets=0.5)),
         ]),

    dict(nr=6, title="Sierra Blanca Drift", seed=6606, root=52, mode="E dorisch, Schluss in E-Dur", style="Ballade im 6/8",
         scale=[0, 2, 3, 5, 7, 9, 10], themes=T_SIERRA, units=6,
         progs=dict(verse=["i7", "IV", "i7", "bVII"], refrain=["IV", "bVII", "i7", "IV"], quiet=["ii7", "IV", "ii7", "bVII"], major=["I", "IVmaj", "V", "I"]),
         sections=[
             S("intro", 8, meter="6/8", bpm=56, dyn=0.6, comping="arp6", comp_level=0.16, pad=550, atmos=dict(crickets=0.5)),
             S("verse1", 20, meter="6/8", bpm=56, dyn=0.74, comping="arp6", comp_level=0.16, drums="six8", drum_level=0.6, hats="six8", bass="six8", bass_inst="pluck", bass_level=0.7,
               perc=["shaker"], perc_level=0.6, pad=700, melody=[mel("A", "flute", 0.24)], answer="steel", answer_level=0.1, atmos=dict(crickets=0.3)),
             S("refrain1", 8, meter="6/8", bpm=56, prog="refrain", dyn=0.84, comping="arp6", comp_level=0.17, drums="six8", drum_level=0.7, hats="six8", bass="six8", bass_inst="pluck", bass_level=0.75,
               perc=["shaker", "cajon"], perc_level=0.7, pad=950, melody=[mel("B", "flute", 0.26), mel("B", "steel", 0.12, octave=24, pan=-0.3, legato=0.7)]),
             S("verse2", 20, meter="6/8", bpm=56, dyn=0.78, comping="arp6", comp_level=0.16, drums="six8", drum_level=0.65, hats="six8", bass="six8", bass_inst="pluck", bass_level=0.7,
               perc=["shaker"], perc_level=0.6, pad=750, melody=[mel("A", "guitar", 0.4, ornaments=True)], answer="flute", answer_level=0.12),
             S("refrain2", 8, meter="6/8", bpm=56, prog="refrain", dyn=0.86, comping="arp6", comp_level=0.17, drums="six8", drum_level=0.7, hats="six8", bass="six8", bass_inst="pluck", bass_level=0.75,
               perc=["shaker", "cajon"], perc_level=0.7, pad=1000, choir="oo", choir_level=0.1, melody=[mel("B", "flute", 0.26), mel("B", "steel", 0.12, octave=24, pan=-0.3, legato=0.7)]),
             S("quiet", 8, meter="6/8", bpm=56, prog="quiet", dyn=0.62, comping="arp6", comp_level=0.12, pad=600, melody=[mel("frag", "guitar", 0.34, humanize=0.02, legato=1.2)],
               atmos=dict(crickets=0.6)),
             S("climax", 20, meter="6/8", bpm=56, prog="major", dyn=0.95, comping="arp6", comp_level=0.18, drums="six8", drum_level=0.75, hats="six8", bass="six8", bass_level=0.75, bass_cut=500.0,
               perc=["cajon", "shaker"], perc_level=0.8, pad=1300, choir="ah", choir_level=0.14,
               melody=[mel("Bmaj", "flute", 0.28), mel("Bmaj", "trumpet", 0.15, octave=12, pan=0.3, legato=0.85), mel("Bmaj", "steel", 0.1, octave=24, pan=-0.4, legato=0.6)]),
             S("coda", 12, meter="6/8", bpm=56, prog="major", dyn=0.6, rit=True, comping="arp6", comp_level=0.15, pad=700, choir="oo", choir_level=0.1,
               melody=[mel("Amaj", "guitar", 0.4, humanize=0.025, legato=1.25)], atmos=dict(crickets=0.6)),
             S("end", 1, meter="6/8", bpm=40, prog="major", dyn=0.55, fx=["final_chord"], atmos=dict(crickets=0.6)),
         ]),

    dict(nr=7, title="Casco Antiguo Echoes", seed=7707, root=54, mode="Fis phrygisch", style="Shuffle House, Dub", dub=True,
         scale=[0, 1, 3, 5, 7, 8, 10], themes=T_CASCO,
         progs=dict(verse=["i", "bII", "i", "bvii"], refrain=["bVI", "bvii", "i", "bII"], bridge=["iv7", "bIII", "bII", "bII"]),
         sections=[
             S("intro", 8, bpm=118, dyn=0.62, comping="pick", comp_level=0.14, pad=650, melody=[mel("frag", "trumpet", 0.2, legato=1.4, humanize=0.02)], atmos=dict(cicadas=0.5)),
             S("groove1", 16, bpm=118, dyn=0.78, swing=0.33, drums="shuffle", drum_level=0.85, hats="offbeat", bass="deep", bass_level=0.75, bass_cut=520.0,
               comping="rumba", comp_level=0.13, perc=["shaker", "cajon"], perc_level=0.6, pad=850, melody=[mel("A", "trumpet", 0.24)], answer="guitar", answer_level=0.12),
             S("groove2", 16, bpm=118, dyn=0.84, swing=0.33, drums="shuffle", drum_level=0.9, hats="full", bass="deep", bass_level=0.8, bass_cut=560.0, acid=0.18, acid_cut=320.0,
               comping="rumba", comp_level=0.13, perc=["shaker", "cajon", "palmas"], perc_level=0.7, pad=950, fill=True,
               melody=[mel("A", "guitar", 0.38, ornaments=True)], answer="trumpet", answer_level=0.12),
             S("refrain1", 16, bpm=118, prog="refrain", dyn=0.92, swing=0.33, drums="shuffle", drum_level=0.95, hats="full", bass="roll", bass_level=0.8, bass_cut=640.0,
               stabs="brass", stab_steps=(2, 10), stab_level=0.16, perc=["palmas", "cajon", "shaker"], pad=1200, fill=True,
               melody=[mel("B", "trumpet", 0.26, bars=8), mel("B", "guitar", 0.3, octave=0, offset=8, bars=8)]),
             S("alley", 8, bpm=118, prog="bridge", dyn=0.6, pad=500, pad_level=0.5, melody=[mel("frag", "trumpet", 0.22, legato=1.5, humanize=0.03)], atmos=dict(cicadas=0.8)),
             S("return", 16, bpm=118, prog="refrain", dyn=0.95, swing=0.33, drums="shuffle", drum_level=0.95, hats="full", bass="roll", bass_level=0.8, bass_cut=660.0,
               stabs="brass", stab_steps=(2, 10), stab_level=0.17, perc=["palmas", "cajon", "shaker", "congas"], pad=1300, fx=["crash"], fill=True,
               melody=[mel("B", "trumpet", 0.26), mel("B", "guitar", 0.28, octave=0, pan=0.3, legato=0.8)]),
             S("groove3", 16, bpm=118, dyn=0.82, swing=0.33, drums="shuffle", drum_level=0.85, hats="offbeat", bass="deep", bass_level=0.78, bass_cut=540.0, acid=0.22, acid_cut=400.0,
               comping="rumba", comp_level=0.13, perc=["shaker", "cajon"], perc_level=0.6, pad=900, melody=[mel("A", "guitar", 0.38, ornaments=True)], answer="trumpet", answer_level=0.12),
             S("refrain2", 16, bpm=118, prog="refrain", dyn=1.0, swing=0.33, drums="shuffle", drum_level=1.0, hats="full", ride=True, bass="roll", bass_level=0.85, bass_cut=720.0,
               stabs="brass", stab_steps=(2, 7, 10, 15), stab_level=0.18, perc=["palmas", "cajon", "shaker", "castanets"], pad=1400, fill=True,
               melody=[mel("B", "trumpet", 0.28), mel("B", "guitar", 0.28, octave=0, pan=0.3, legato=0.8), mel("A", "steel", 0.12, octave=24, pan=0.5, offset=8, bars=8, legato=0.6)]),
             S("outro1", 6, bpm=118, dyn=0.7, swing=0.33, drums="shuffle", drum_level=0.7, hats="offbeat", bass="deep", bass_level=0.7, bass_cut=500.0, pad=800,
               melody=[mel("frag", "trumpet", 0.2, legato=1.4)]),
             S("outro2", 8, bpm=118, dyn=0.58, pad=650, melody=[mel("frag", "trumpet", 0.2, legato=1.5, humanize=0.02)], atmos=dict(cicadas=0.6)),
             S("end", 2, bpm=118, dyn=0.55, fx=["final_chord"], atmos=dict(cicadas=0.6)),
         ]),

    dict(nr=7.5, title="Farola", seed=7575, root=52, mode="E phrygisch", style="Zwischenspiel", interlude=True,
         scale=[0, 1, 3, 5, 7, 8, 10], themes=T_FAROLA,
         progs=dict(verse=["i", "bII", "i", "bII"]),
         sections=[S("lantern", 16, bpm=80, dyn=0.55, pad=550, choir="oo", choir_level=0.1, choir_every=2, fx=["bell"], bell_motif=[(0, 0), (8, 7)],
                     melody=[mel("motif", "guitar", 0.32, legato=1.5, humanize=0.02)], atmos=dict(crickets=0.6)),
                   S("end", 1, bpm=80, dyn=0.5, fx=["final_choir"], atmos=dict(crickets=0.6))]),

    dict(nr=8, title="La Fontanilla Sunrise", seed=1101, root=52, mode="E phrygisch", style="Chill, Aufbau zum Sonnenaufgang",
         scale=[0, 1, 3, 5, 7, 8, 10], themes=T_FONTANILLA, pad_breathes=False,
         progs=dict(verse=["i", "bII", "bIII", "bII"], refrain=["bVI", "bvii", "i", "bII"], climax=["bVI", "bvii", "i9", "bII"]),
         sections=[
             S("dawn", 8, bpm=84, dyn=0.6, melody=[mel("opener", "guitar", 0.4, ornaments=True, humanize=0.025, legato=1.1)], atmos=dict(waves=1.0, crickets=0.3)),
             S("first_light", 16, bpm=84, bpm_end=96, dyn=0.7, drums="soft", drum_level=0.6, bass="long", bass_inst="pluck", bass_level=0.7, comping="pick", comp_level=0.14,
               pad=650, melody=[mel("A", "flute", 0.22)], answer="steel", answer_level=0.1, atmos=dict(waves=0.5)),
             S("warming", 20, bpm=96, bpm_end=108, dyn=0.8, drums="deep", drum_level=0.8, hats="offbeat", bass="deep", bass_level=0.72, bass_cut=520.0, comping="strum", comp_level=0.15,
               pad=850, perc=["shaker", "congas"], perc_level=0.8, fill=True, melody=[mel("A", "guitar", 0.38, ornaments=True)], answer="flute", answer_level=0.12, atmos=dict(waves=0.3)),
             S("glow", 16, bpm=108, bpm_end=118, prog="refrain", dyn=0.9, drums="house", drum_level=0.88, hats="full", bass="roll", bass_level=0.78, bass_cut=620.0, comping="rumba", comp_level=0.14,
               choir="ah", choir_level=0.12, pad=1100, perc=["shaker", "congas", "palmas"], perc_level=0.8, fill=True, fx=["riser", "roll"],
               melody=[mel("B", "flute", 0.26), mel("B", "steel", 0.12, octave=24, pan=-0.3, legato=0.7)], atmos=dict(waves=0.2)),
             S("sun", 32, bpm=118, shift=2, prog="climax", dyn=1.0, drums="house", drum_level=0.95, hats="full", ride=True, bass="roll", bass_level=0.82, bass_cut=760.0,
               comping="rumba", comp_level=0.15, choir="ah", choir_level=0.16, stabs="brass", stab_steps=(2, 10), stab_level=0.14, pad=1500,
               perc=["palmas", "congas", "shaker"], fx=["crash"], fill=True,
               melody=[mel("B", "trumpet", 0.26), mel("B", "flute", 0.16, octave=24, pan=0.3), mel("A", "guitar", 0.3, octave=0, pan=-0.3, offset=16, bars=16)]),
             S("after1", 8, bpm=118, shift=2, dyn=0.72, drums="deep", drum_level=0.7, hats="offbeat", bass="deep", bass_level=0.7, bass_cut=520.0, choir="oo", choir_level=0.14, pad=900,
               melody=[mel("frag", "flute", 0.2, legato=1.3)], atmos=dict(waves=0.5)),
             S("after2", 8, bpm=118, shift=2, dyn=0.6, choir="oo", choir_level=0.14, pad=700, melody=[mel("A", "guitar", 0.38, humanize=0.02, legato=1.2)], atmos=dict(waves=0.9)),
             S("end", 2, bpm=118, shift=2, dyn=0.55, fx=["final_chord", "final_choir"], atmos=dict(waves=1.0)),
         ]),
]


def slug_of(spec):
    import unicodedata
    plain = unicodedata.normalize("NFKD", spec["title"]).encode("ascii", "ignore").decode()
    nr = spec["nr"]
    prefix = f"{int(nr):02d}" if float(nr).is_integer() else f"{int(nr):02d}b"
    slug = prefix + "-" + "".join(c if c.isalnum() else "-" for c in plain.lower()).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug


def track_duration(spec):
    return Track(spec).n / SR


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "out"))
    ap.add_argument("--track", type=float, default=None)
    ap.add_argument("--wav", action="store_true")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    tracklist = []
    for spec in TRACKS:
        if args.track is not None and spec["nr"] != args.track:
            continue
        tr = Track(spec)
        print(f"[{spec['nr']}] {spec['title']}  ({spec['style']}, {spec['mode']}) ...", flush=True)
        mixv = tr.render()
        slug = slug_of(spec)
        ga.write_outputs(mixv, os.path.join(args.out, slug), args.wav, True)
        dur = len(mixv) / SR
        print(f"    {int(dur // 60)}:{int(dur % 60):02d} min, RMS {20*np.log10(np.sqrt(np.mean(mixv**2))):.1f} dBFS", flush=True)
        tracklist.append(dict(nr=spec["nr"], title=spec["title"], style=spec["style"], key=spec["mode"], seed=spec["seed"],
                              interlude=spec.get("interlude", False), duration_s=round(dur, 1), file=slug + ".mp3"))
    if args.track is None:
        with open(os.path.join(args.out, "tracklist.json"), "w", encoding="utf-8") as fh:
            json.dump(dict(album=ALBUM_TITLE, artist=ALBUM_ARTIST, year=2026, license="CC0-1.0", tracks=tracklist), fh, ensure_ascii=False, indent=2)
    print("fertig:", args.out)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Gemafreies Ibiza-Chillout-Album – vollständig algorithmisch erzeugt.

Alles, was hier klingt, entsteht aus Oszillatoren, Rauschen, Filtern und
zufallsgesteuerten (aber per Seed reproduzierbaren) Kompositionsregeln.
Es werden keine Samples, Loops, Presets oder fremden Kompositionen verwendet.

Aufruf:
    python3 generate_album.py                # rendert alle Tracks nach ./out
    python3 generate_album.py --track 3      # nur Track 3
    python3 generate_album.py --wav          # zusätzlich WAV schreiben
    python3 generate_album.py --short        # Kurzfassung (~1 min) zum Testen
"""
import argparse
import json
import os
import sys

import numpy as np
from scipy import signal
from scipy.io import wavfile

SR = 44100
LENGTH_SCALE = 1.6  # Arrangement-Länge relativ zu den Takten in TRACKS


# --------------------------------------------------------------------------- #
# Grundbausteine
# --------------------------------------------------------------------------- #
def midi_to_hz(m):
    return 440.0 * 2.0 ** ((np.asarray(m, dtype=float) - 69.0) / 12.0)


def lowpass(x, cutoff, order=2):
    cutoff = float(np.clip(cutoff, 30.0, SR * 0.45))
    sos = signal.butter(order, cutoff, "low", fs=SR, output="sos")
    return signal.sosfilt(sos, x, axis=0)


def highpass(x, cutoff, order=2):
    cutoff = float(np.clip(cutoff, 20.0, SR * 0.45))
    sos = signal.butter(order, cutoff, "high", fs=SR, output="sos")
    return signal.sosfilt(sos, x, axis=0)


def bandpass(x, lo, hi, order=2):
    lo = float(np.clip(lo, 20.0, SR * 0.44))
    hi = float(np.clip(hi, lo + 10.0, SR * 0.45))
    sos = signal.butter(order, [lo, hi], "band", fs=SR, output="sos")
    return signal.sosfilt(sos, x, axis=0)


def envelope(n_hold, attack, decay, sustain, release):
    """ADSR. n_hold = Samples bis Note-Off, danach Release."""
    a = max(1, int(attack * SR))
    d = max(1, int(decay * SR))
    r = max(1, int(release * SR))
    n_hold = max(n_hold, 1)
    env = np.ones(n_hold + r)
    env[:a] = np.linspace(0.0, 1.0, a)
    if d > 0:
        dec = np.linspace(1.0, sustain, d)
        seg = env[a:a + d]
        env[a:a + d] = dec[: len(seg)]
        env[a + d:n_hold] = sustain
    env[:n_hold] = np.minimum(env[:n_hold], np.maximum(env[:n_hold], 0.0))
    tail = env[n_hold - 1] if n_hold > 0 else sustain
    env[n_hold:] = tail * np.exp(-np.linspace(0.0, 6.0, r))
    return env


def fit(env, n):
    """Hüllkurve auf genau n Samples bringen (mit Nullen auffüllen / kürzen)."""
    if len(env) >= n:
        return env[:n]
    return np.concatenate([env, np.zeros(n - len(env))])


def saw(freq, n, phase=0.0):
    t = np.arange(n) / SR
    return 2.0 * ((t * freq + phase) % 1.0) - 1.0


def sine(freq, n, phase=0.0):
    t = np.arange(n) / SR
    return np.sin(2 * np.pi * (t * freq + phase))


def triangle(freq, n, phase=0.0):
    return 2.0 * np.abs(saw(freq, n, phase)) - 1.0


def square(freq, n, phase=0.0, duty=0.5):
    t = np.arange(n) / SR
    return np.where(((t * freq + phase) % 1.0) < duty, 1.0, -1.0)


def to_stereo(x, pan=0.0):
    """pan: -1 links ... +1 rechts, equal power."""
    ang = (pan + 1.0) * np.pi / 4.0
    return np.stack([x * np.cos(ang), x * np.sin(ang)], axis=1)


def place(buf, start, sig):
    """Addiert sig (stereo) an Sample-Position start in buf."""
    start = int(start)
    if start >= len(buf) or start + len(sig) <= 0:
        return
    if start < 0:
        sig = sig[-start:]
        start = 0
    end = min(len(buf), start + len(sig))
    buf[start:end] += sig[: end - start]


def soft_clip(x, drive=1.0):
    return np.tanh(x * drive) / np.tanh(drive)


def make_reverb_ir(rng, seconds=2.6, decay=2.4, tone=3800.0, predelay=0.018):
    n = int(seconds * SR)
    t = np.arange(n) / SR
    ir = rng.standard_normal((n, 2)) * np.exp(-decay * t)[:, None]
    ir[:, 1] *= 0.92
    ir = lowpass(ir, tone)
    ir = highpass(ir, 120.0)
    pre = np.zeros((int(predelay * SR), 2))
    ir = np.concatenate([pre, ir])
    ir /= np.sqrt(np.sum(ir ** 2, axis=0)).max() + 1e-9
    return ir


def reverb(x, ir, wet):
    if wet <= 0.0:
        return x
    out = x.copy()
    for ch in range(2):
        out[:, ch] += wet * signal.fftconvolve(x[:, ch], ir[:, ch])[: len(x)]
    return out


def delay(x, time_s, feedback=0.42, taps=6, tone=3200.0, pingpong=True, mix=0.35):
    d = int(time_s * SR)
    out = x.copy()
    wet = x.copy()
    for i in range(taps):
        wet = lowpass(wet, tone) * feedback
        if pingpong:
            wet = wet[:, ::-1]
        shifted = np.zeros_like(wet)
        shifted[d:] = wet[:-d]
        wet = shifted
        out += mix * wet
    return out


def chorus_widen(x, rng, depth_ms=4.0, rate=0.25):
    """Leichtes Stereo-Auseinanderziehen durch modulierte Mikro-Verzögerung."""
    n = len(x)
    t = np.arange(n) / SR
    idx = np.arange(n, dtype=float)
    out = x.copy()
    for ch, sgn in ((0, 1.0), (1, -1.0)):
        mod = (depth_ms / 1000.0 * SR) * (0.5 + 0.5 * np.sin(2 * np.pi * rate * t + sgn * 1.3))
        src = np.clip(idx - mod - 1.0, 0, n - 1)
        out[:, ch] = 0.5 * x[:, ch] + 0.5 * np.interp(src, idx, x[:, ch])
    return out


# --------------------------------------------------------------------------- #
# Instrumente (alle synthetisch)
# --------------------------------------------------------------------------- #
def kick(rng, punch=1.0):
    n = int(0.6 * SR)
    t = np.arange(n) / SR
    f = 40.0 + 130.0 * np.exp(-t * 30.0)
    phase = np.cumsum(f) / SR
    body = np.sin(2 * np.pi * phase) * np.exp(-t * 6.0)
    sub = np.sin(2 * np.pi * 46.0 * t + 0.3) * np.exp(-t * 7.5) * 0.4
    click = rng.standard_normal(n) * np.exp(-t * 420.0) * 0.5 * punch
    click = highpass(click, 1800.0)
    x = soft_clip(body * 1.9 + sub + click, 2.0)
    x = lowpass(x, 9000.0)
    x *= np.minimum(1.0, t / 0.0008)
    return to_stereo(x * 1.0, 0.0)


def hat(rng, length=0.06, tone=8000.0, level=0.35):
    n = int((length + 0.05) * SR)
    t = np.arange(n) / SR
    x = rng.standard_normal(n) * np.exp(-t / (length * 0.35))
    x = highpass(x, tone)
    x = bandpass(x, tone * 0.9, min(16000.0, tone * 2.2))
    return to_stereo(x * level, 0.15)


def shaker(rng, level=0.16):
    n = int(0.12 * SR)
    t = np.arange(n) / SR
    env = np.exp(-((t - 0.02) ** 2) / (2 * 0.012 ** 2)) + 0.4 * np.exp(-t * 60)
    x = rng.standard_normal(n) * env
    x = bandpass(x, 3500.0, 9000.0)
    return to_stereo(x * level, -0.3)


def clap(rng, level=0.35):
    n = int(0.35 * SR)
    t = np.arange(n) / SR
    env = np.zeros(n)
    for k, off in enumerate((0.0, 0.011, 0.022, 0.034)):
        env += np.exp(-np.maximum(t - off, 0) * 90.0) * (t >= off) * (0.7 + 0.3 * (k == 3))
    env += 0.5 * np.exp(-np.maximum(t - 0.034, 0) * 14.0) * (t >= 0.034)
    x = rng.standard_normal(n) * env
    x = bandpass(x, 900.0, 5500.0)
    return to_stereo(x * level, 0.1)


def snare_layer(rng, level=0.3):
    n = int(0.25 * SR)
    t = np.arange(n) / SR
    tone = np.sin(2 * np.pi * (185.0 + 60.0 * np.exp(-t * 80)) * t) * np.exp(-t * 28.0)
    noise = bandpass(rng.standard_normal(n), 1200.0, 8000.0) * np.exp(-t * 18.0)
    x = soft_clip(tone * 0.9 + noise * 0.9, 1.5)
    return to_stereo(x * level, -0.05)


def ride(rng, level=0.14):
    n = int(0.5 * SR)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for ratio in (1.0, 1.47, 2.09, 2.56, 3.01):
        x += square(410.0 * ratio, n, rng.random())
    x = highpass(x, 4000.0) + 0.5 * highpass(rng.standard_normal(n), 6000.0)
    x *= np.exp(-t * 6.0)
    return to_stereo(x * level / 3.0, 0.35)


def conga(rng, freq=190.0, level=0.5, pan=0.0):
    n = int(0.3 * SR)
    t = np.arange(n) / SR
    f = freq * (1.0 + 0.35 * np.exp(-t * 60.0))
    phase = np.cumsum(f) / SR
    x = np.sin(2 * np.pi * phase) * np.exp(-t * 14.0)
    x += 0.3 * np.sin(2 * np.pi * phase * 2.3) * np.exp(-t * 40.0)
    x += highpass(rng.standard_normal(n) * np.exp(-t * 200.0), 2000.0) * 0.15
    return to_stereo(x * level, pan)


def rim(rng, level=0.25, pan=0.3):
    n = int(0.08 * SR)
    t = np.arange(n) / SR
    x = np.sin(2 * np.pi * 1700 * t) * np.exp(-t * 120) + rng.standard_normal(n) * np.exp(-t * 300) * 0.5
    x = highpass(x, 1200.0)
    return to_stereo(x * level, pan)


def synth_bass(rng, freq, n_hold, level=0.8, cutoff=700.0, drive=1.8, q=2.2):
    """Druckvoller Synth-Bass: Sägezahn + Rechteck durch Resonanzfilter, Sub-Sinus, Sättigung."""
    n = n_hold + int(0.15 * SR)
    t = np.arange(n) / SR
    osc = saw(freq, n, rng.random()) + 0.6 * square(freq, n, rng.random(), 0.48)
    cut = cutoff * (freq / 55.0) ** 0.5 * (0.35 + np.exp(-t * 9.0)) + 90.0
    y = reso_lowpass_sweep(osc, cut, q, block=128)
    y = soft_clip(y * drive, 1.6)
    sub = np.sin(2 * np.pi * freq * t) * 0.5
    env = fit(envelope(n_hold, 0.004, 0.2, 0.75, 0.10), n)
    x = (y * 0.7 + sub) * env
    x = highpass(x, 28.0)
    return to_stereo(x * level, 0.0)


def pad_chord(rng, midis, n_hold, cutoff=1400.0, level=0.22, attack=0.6, release=1.2):
    n = n_hold + int(release * SR)
    out = np.zeros((n, 2))
    env = fit(envelope(n_hold, attack, 0.8, 0.85, release), n)
    for m in midis:
        f = float(midi_to_hz(m))
        for ch in range(2):
            v = np.zeros(n)
            for cents in (-11.0, -5.0, 0.0, 5.0, 11.0):
                det = f * 2.0 ** ((cents + rng.uniform(-1.5, 1.5)) / 1200.0)
                v += saw(det, n, rng.random())
            v /= 5.0
            v += 0.25 * sine(f, n, rng.random())
            out[:, ch] += v
    out *= env[:, None]
    # langsame Filterbewegung über die Notenlänge
    seg = max(1, n // 8)
    mod = 0.65 + 0.35 * np.sin(np.linspace(0, np.pi, 8))
    res = np.zeros_like(out)
    for i in range(8):
        sl = slice(i * seg, min(n, (i + 1) * seg))
        if sl.start >= n:
            break
        res[sl] = lowpass(out[sl], cutoff * mod[i])
    res = lowpass(res, cutoff * 1.6)
    return res * level / max(1, len(midis)) * 2.2


def pluck(rng, midi, n_hold, level=0.4, brightness=2600.0, pan=0.0):
    f = float(midi_to_hz(midi))
    n = n_hold + int(0.5 * SR)
    x = 0.6 * saw(f, n, rng.random()) + 0.4 * square(f, n, rng.random(), 0.35)
    t = np.arange(n) / SR
    cut_env = brightness * np.exp(-t * 7.0) + 320.0
    seg = max(1, n // 12)
    y = np.zeros(n)
    for i in range(12):
        sl = slice(i * seg, min(n, (i + 1) * seg))
        if sl.start >= n:
            break
        y[sl] = lowpass(x[sl], cut_env[sl.start])
    env = fit(envelope(n_hold, 0.004, 0.35, 0.35, 0.4), n)
    return to_stereo(y * env * level, pan)


def ks_guitar(rng, midi, n_hold, level=0.45, damp=0.996, pan=0.0):
    """Karplus-Strong-Saite über einen Feedback-Kammfilter (scipy.lfilter)."""
    f = float(midi_to_hz(midi))
    L = int(round(SR / f))
    n = n_hold + int(1.2 * SR)
    exc = rng.standard_normal(L)
    exc = lowpass(exc, 6000.0)
    x = np.zeros(n)
    x[:L] = exc
    a = np.zeros(L + 2)
    a[0] = 1.0
    a[L] = -0.5 * damp
    a[L + 1] = -0.5 * damp
    y = signal.lfilter([1.0], a, x)
    env = np.ones(n)
    rel = int(0.6 * SR)
    env[n_hold:] = np.exp(-np.linspace(0, 6, n - n_hold))
    y = y * env
    y = highpass(y, 80.0)
    return to_stereo(y * level, pan)


def ep_keys(rng, midi, n_hold, level=0.35, pan=0.0):
    """E-Piano-artiger Klang aus abklingenden Teiltönen."""
    f = float(midi_to_hz(midi))
    n = n_hold + int(1.0 * SR)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for k, amp, dec in ((1, 1.0, 2.2), (2, 0.5, 5.0), (3, 0.22, 9.0), (4, 0.12, 14.0), (5, 0.05, 18.0)):
        det = 1.0 + 0.0012 * (k - 1)
        x += amp * np.sin(2 * np.pi * f * k * det * t + rng.random() * 6.28) * np.exp(-t * dec)
    x += 0.25 * np.sin(2 * np.pi * f * 7.02 * t) * np.exp(-t * 40.0)  # "Bell"-Anschlag
    x += 0.08 * highpass(rng.standard_normal(n), 2500.0) * np.exp(-t * 120.0)  # Hammer
    x = soft_clip(x * 1.3, 1.5)
    env = fit(envelope(n_hold, 0.003, 0.5, 0.6, 0.7), n)
    x *= env
    x = lowpass(x, 5000.0)
    return to_stereo(x * level, pan)


def lead(rng, midi, n_hold, level=0.3, pan=0.0, vibrato=5.2):
    f = float(midi_to_hz(midi))
    n = n_hold + int(0.7 * SR)
    t = np.arange(n) / SR
    vib = 1.0 + 0.005 * np.sin(2 * np.pi * vibrato * t) * np.minimum(1.0, t / 0.4)
    x = np.zeros(n)
    for cents in (-9.0, 0.0, 9.0):
        phase = np.cumsum(f * vib * 2.0 ** (cents / 1200.0)) / SR + rng.random()
        x += 2.0 * (phase % 1.0) - 1.0
    x /= 3.0
    x += 0.4 * np.sin(2 * np.pi * np.cumsum(f * vib) / SR)
    cut = 900.0 + 2600.0 * np.exp(-t * 3.0) + 600.0 * np.minimum(1.0, t / 0.4)
    x = reso_lowpass_sweep(x, cut, 1.6, block=256)
    env = fit(envelope(n_hold, 0.05, 0.3, 0.8, 0.55), n)
    return to_stereo(x * env * level, pan)


def ocean(rng, n, level=0.12):
    """Wellenrauschen: gefiltertes Rauschen mit langsamer, unregelmäßiger Hüllkurve."""
    t = np.arange(n) / SR
    noise = rng.standard_normal((n, 2))
    noise = lowpass(noise, 900.0)
    noise = highpass(noise, 120.0)
    env = np.zeros(n)
    pos = 0.0
    while pos < t[-1]:
        period = rng.uniform(6.0, 11.0)
        width = period * rng.uniform(0.22, 0.32)
        env += np.exp(-((t - pos - period * 0.5) ** 2) / (2 * width ** 2)) * rng.uniform(0.6, 1.0)
        pos += period
    env = 0.25 + 0.75 * env / (env.max() + 1e-9)
    hiss = highpass(rng.standard_normal((n, 2)), 3000.0) * 0.12 * (env[:, None] ** 2)
    return (noise * env[:, None] + hiss) * level


def seagulls(rng, n, level=0.05, count=6):
    out = np.zeros((n, 2))
    for _ in range(count):
        start = int(rng.uniform(0, max(1, n - 2 * SR)))
        m = int(rng.uniform(0.25, 0.6) * SR)
        t = np.arange(m) / SR
        f0 = rng.uniform(1800, 2600)
        f = f0 * (1.0 + 0.25 * np.sin(2 * np.pi * rng.uniform(4, 7) * t) * np.exp(-t * 3))
        phase = np.cumsum(f) / SR
        x = np.sin(2 * np.pi * phase) * np.sin(np.pi * t / t[-1]) ** 2
        place(out, start, to_stereo(x * level, rng.uniform(-0.8, 0.8)))
    return out




# --------------------------------------------------------------------------- #
# Acid / House
# --------------------------------------------------------------------------- #
_RESO_CACHE = {}


def _reso_coeffs(cutoff, q):
    """2-poliger Resonanz-Tiefpass (analoges Prototyp-Filter, bilinear)."""
    key = (int(cutoff), round(q, 1))
    c = _RESO_CACHE.get(key)
    if c is None:
        w0 = 2 * np.pi * float(np.clip(cutoff, 60.0, 9000.0))
        b, a = signal.bilinear([w0 * w0], [1.0, w0 / q, w0 * w0], fs=SR)
        c = (b, a)
        _RESO_CACHE[key] = c
    return c


def reso_lowpass_sweep(x, cutoff_curve, q, block=128):
    """Tiefpass mit zeitveränderlichem Cutoff, blockweise mit Filterzustand."""
    y = np.zeros_like(x)
    zi = np.zeros(2)
    n = len(x)
    steps = np.geomspace(60.0, 9000.0, 96)
    for start in range(0, n, block):
        end = min(n, start + block)
        fc = cutoff_curve[start]
        fc = steps[np.searchsorted(steps, fc).clip(0, len(steps) - 1)]
        b, a = _reso_coeffs(fc, q)
        y[start:end], zi = signal.lfilter(b, a, x[start:end], zi=zi)
    return y


def acid_note(rng, midi, n_hold, prev_midi=None, accent=False, level=0.4,
              base_cut=380.0, env_amount=2600.0, q=7.0, wave="saw"):
    """303-artige Acid-Note: Oszillator -> Resonanzfilter mit Hüllkurve -> Sättigung."""
    f_end = float(midi_to_hz(midi))
    n = n_hold + int(0.25 * SR)
    t = np.arange(n) / SR
    if prev_midi is not None:
        f_start = float(midi_to_hz(prev_midi))
        glide = int(0.06 * SR)
        freq = np.full(n, f_end)
        freq[:glide] = np.geomspace(f_start, f_end, glide)
    else:
        freq = np.full(n, f_end)
    phase = np.cumsum(freq) / SR
    if wave == "square":
        osc = np.where((phase % 1.0) < 0.5, 1.0, -1.0)
    else:
        osc = 2.0 * (phase % 1.0) - 1.0
    dec = 0.16 if accent else 0.30
    amt = env_amount * (1.6 if accent else 1.0)
    cutoff = base_cut + amt * np.exp(-t / dec)
    y = reso_lowpass_sweep(osc, cutoff, q * (1.25 if accent else 1.0))
    env = fit(envelope(n_hold, 0.003, 0.25, 0.55, 0.08), n)
    y = highpass(y * env * (1.4 if accent else 1.0), 60.0)
    y = soft_clip(y, 2.2) * 0.8
    return to_stereo(y * level, 0.0)


def house_stab(rng, midis, n_hold, level=0.3, cutoff=2200.0, pan=0.0):
    """Kurzer, perkussiver Akkord-Stab (klassischer House-Chord)."""
    n = n_hold + int(0.35 * SR)
    x = np.zeros(n)
    for m in midis:
        f = float(midi_to_hz(m))
        for cents in (-7.0, 0.0, 7.0):
            x += saw(f * 2.0 ** (cents / 1200.0), n, rng.random())
        x += 0.5 * square(f, n, rng.random(), 0.45)
    x /= max(1, len(midis)) * 1.4
    t = np.arange(n) / SR
    cut = cutoff * np.exp(-t * 6.0) + 900.0
    y = reso_lowpass_sweep(x, cut, 1.4, block=256)
    env = fit(envelope(n_hold, 0.004, 0.28, 0.3, 0.25), n)
    return to_stereo(y * env * level, pan)


def open_hat_909(rng, level=0.22):
    """Metallische Open Hat aus sechs unharmonischen Rechtecken plus Rauschen."""
    n = int(0.32 * SR)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for ratio in (1.0, 1.342, 1.2312, 1.6532, 1.9523, 2.1523):
        x += square(320.0 * ratio, n, rng.random())
    x = highpass(x, 5500.0)
    x = bandpass(x, 6000.0, 14000.0)
    x += 0.6 * highpass(rng.standard_normal(n), 7000.0)
    x *= np.exp(-t * 11.0)
    return to_stereo(x * level / 3.0, 0.2)


# --------------------------------------------------------------------------- #
# Trance (chillig dosiert)
# --------------------------------------------------------------------------- #
def supersaw_lead(rng, midi, n_hold, level=0.28, cutoff=3400.0, pan=0.0):
    """Breiter Supersaw-Hook mit langer Release, weich gefiltert."""
    f = float(midi_to_hz(midi))
    n = n_hold + int(1.1 * SR)
    out = np.zeros((n, 2))
    for ch in range(2):
        v = np.zeros(n)
        for cents in (-19.0, -12.0, -5.0, 0.0, 5.0, 12.0, 19.0):
            v += saw(f * 2.0 ** ((cents + rng.uniform(-1.0, 1.0)) / 1200.0), n, rng.random())
        v /= 7.0
        v += 0.35 * saw(f * 0.5, n, rng.random())
        out[:, ch] = v
    out = lowpass(out, cutoff)
    out = highpass(out, 140.0)
    env = fit(envelope(n_hold, 0.03, 0.5, 0.8, 1.0), n)
    out *= env[:, None] * level
    ang = (pan + 1.0) * np.pi / 4.0
    out[:, 0] *= np.cos(ang) * 1.4
    out[:, 1] *= np.sin(ang) * 1.4
    return out


def trance_pluck(rng, midi, n_hold, level=0.25, pan=0.0):
    """Kurzer, heller Pluck für rollende 16tel-Arpeggios."""
    f = float(midi_to_hz(midi))
    n = n_hold + int(0.4 * SR)
    x = np.zeros(n)
    for cents in (-8.0, 0.0, 8.0):
        x += saw(f * 2.0 ** (cents / 1200.0), n, rng.random())
    x /= 3.0
    t = np.arange(n) / SR
    cut = 4500.0 * np.exp(-t * 14.0) + 600.0
    y = reso_lowpass_sweep(x, cut, 1.8, block=256)
    env = fit(envelope(n_hold, 0.002, 0.2, 0.25, 0.3), n)
    return to_stereo(y * env * level, pan)


def riser(rng, n, level=0.2):
    """Weißes Rauschen mit aufsteigendem Filter und ansteigender Lautstärke."""
    t = np.linspace(0.0, 1.0, n)
    noise = rng.standard_normal(n)
    cut = 250.0 * (32.0 ** t)
    y = reso_lowpass_sweep(noise, cut, 2.2, block=512)
    y = highpass(y, 200.0)
    y *= (t ** 2.2) * level
    y[-int(0.02 * SR):] *= np.linspace(1, 0, int(0.02 * SR))
    return to_stereo(y, 0.0)


# --------------------------------------------------------------------------- #
# Musiktheorie
# --------------------------------------------------------------------------- #
SCALES = {
    "minor": [0, 2, 3, 5, 7, 8, 10],
    "dorian": [0, 2, 3, 5, 7, 9, 10],
    "major": [0, 2, 4, 5, 7, 9, 11],
}


def scale_degree_midi(root, scale, degree, octave=0):
    """degree 0-basiert, darf >6 sein (nächste Oktave)."""
    steps = SCALES[scale]
    o, d = divmod(degree, len(steps))
    return root + steps[d] + 12 * (o + octave)


def chord(root, scale, degree, kind="7", octave=0):
    tones = [degree, degree + 2, degree + 4]
    if kind in ("7", "9"):
        tones.append(degree + 6)
    if kind == "9":
        tones.append(degree + 8)
    return [scale_degree_midi(root, scale, d, octave) for d in tones]


# --------------------------------------------------------------------------- #
# Arrangement
# --------------------------------------------------------------------------- #
class Track:
    def __init__(self, spec, short=False):
        self.spec = spec
        self.rng = np.random.default_rng(spec["seed"])
        self.bpm = spec["bpm"]
        self.beat = 60.0 / self.bpm
        self.bar = 4 * self.beat
        self.root = spec["root"]
        self.scale = spec["scale"]
        self.prog = spec["progression"]
        sections = spec["sections"]
        if short:
            sections = [(name, max(2, bars // 4)) for name, bars in sections]
        else:
            sections = [(name, int(round(bars * LENGTH_SCALE))) for name, bars in sections]
        self.sections = sections
        self.total_bars = sum(b for _, b in sections)
        self.n = int((self.total_bars * self.bar + 6.0) * SR)
        self.layers = {k: np.zeros((self.n, 2)) for k in
                       ("drums", "perc", "bass", "pad", "keys", "pluck", "lead", "guitar", "atmos", "acid", "stab", "trance")}
        self.kick_times = []

    # ---- Hilfen ------------------------------------------------------------
    def s(self, bar, step16=0):
        """Sample-Position für Takt + 16tel-Schritt."""
        return int((bar * self.bar + step16 * self.beat / 4.0) * SR)

    def chord_for_bar(self, bar):
        deg, kind = self.prog[bar % len(self.prog)]
        return deg, kind

    def sections_bars_at(self, bar):
        acc = 0
        for name, bars in self.sections:
            if bar < acc + bars:
                return bars
            acc += bars
        return 1

    def section_at(self, bar):
        acc = 0
        for name, bars in self.sections:
            if bar < acc + bars:
                return name, (bar - acc) / bars
            acc += bars
        return "outro", 1.0

    # ---- Motive ------------------------------------------------------------
    def make_motif(self, length16=32, density=0.45, octave=1, rest_bias=0.3):
        """Melodie-Motiv als Liste (step16, degree, dur16)."""
        rng = self.rng
        motif = []
        deg = rng.integers(0, 7) + 7 * octave
        step = 0
        while step < length16:
            if rng.random() < rest_bias and motif:
                step += int(rng.choice([1, 2, 2, 4]))
                continue
            move = int(rng.choice([-3, -2, -1, -1, 0, 1, 1, 2, 3], p=[0.06, 0.12, 0.22, 0.1, 0.06, 0.1, 0.22, 0.08, 0.04]))
            deg = int(np.clip(deg + move, 7 * octave - 2, 7 * octave + 9))
            dur = int(rng.choice([1, 2, 2, 3, 4, 6, 8], p=[0.08, 0.3, 0.2, 0.07, 0.2, 0.08, 0.07]))
            dur = min(dur, length16 - step)
            motif.append((step, deg, dur))
            step += dur if rng.random() < density + 0.35 else dur + int(rng.choice([1, 2]))
        return motif

    def snap_to_chord(self, degree, bar):
        """Bevorzugt Akkordtöne auf schweren Zählzeiten."""
        deg, _ = self.chord_for_bar(bar)
        chord_degs = {(deg + k) % 7 for k in (0, 2, 4, 6)}
        d7 = degree % 7
        if d7 in chord_degs:
            return degree
        for off in (1, -1, 2, -2):
            if (d7 + off) % 7 in chord_degs:
                return degree + off
        return degree

    # ---- Rendering ---------------------------------------------------------
    def render(self):
        spec = self.spec
        rng = self.rng
        style = spec.get("style", "house")
        beat16 = int(self.beat / 4.0 * SR)

        motif_a = self.make_motif(32, octave=spec.get("lead_octave", 1))
        motif_b = self.make_motif(32, octave=spec.get("lead_octave", 1))
        arp_pattern = rng.permutation(4).tolist() + rng.permutation(4).tolist()
        conga_pattern = sorted(rng.choice(16, size=int(rng.integers(4, 7)), replace=False).tolist())
        conga_pitches = rng.choice([150.0, 190.0, 240.0, 300.0], size=len(conga_pattern)).tolist()
        shaker_accents = sorted(rng.choice(16, size=6, replace=False).tolist())
        hat_vel = 0.55 + 0.45 * rng.random(16)
        hat_vel[[2, 6, 10, 14]] = 1.0

        # Acid-Sequenz: 16 Schritte, jeder Schritt (Intervall in Halbtönen | None, accent, slide)
        acid_steps = []
        intervals = [0, 0, 0, 12, 7, 10, 3, 5, -12, 12]
        for st in range(16):
            if rng.random() < spec.get("acid_density", 0.7):
                iv = int(rng.choice(intervals))
                acid_steps.append((iv, rng.random() < 0.3, rng.random() < 0.25))
            else:
                acid_steps.append(None)
        acid_steps[0] = (0, True, False)
        stab_steps = spec.get("stab_pattern", [2, 7, 10, 15] if rng.random() < 0.5 else [4, 12])
        ohat = open_hat_909(rng, 0.2)

        kick_steps_house = [0, 4, 8, 12]
        kick_steps_down = [0, 7, 8, 11] if rng.random() < 0.5 else [0, 6, 10]
        bass_steps_house = [0, 2, 4, 6, 8, 10, 12, 14] if rng.random() < 0.6 else [0, 3, 6, 8, 11, 14]
        bass_steps_down = [0, 7, 10]

        # Drum-/Perc-Sounds einmal erzeugen (Variation über Lautstärke/Filter)
        kick_s = kick(rng, punch=spec.get("kick_punch", 1.0))
        hat_c = hat(rng, 0.045, 8500.0, 0.28)
        hat_o = hat(rng, 0.16, 6500.0, 0.22)
        clap_s = clap(rng, 0.28)
        shaker_s = shaker(rng, 0.14)
        rim_s = rim(rng, 0.2)
        snare_s = snare_layer(rng, 0.3)
        ride_s = ride(rng, 0.13)
        congas = [conga(rng, p, 0.45, rng.uniform(-0.5, 0.5)) for p in conga_pitches]

        for bar in range(self.total_bars):
            sec, frac = self.section_at(bar)
            deg, kind = self.chord_for_bar(bar)
            chord_midis = chord(self.root, self.scale, deg, kind, octave=0)
            bass_midi = scale_degree_midi(self.root, self.scale, deg, -2)
            if bass_midi > 45:
                bass_midi -= 12
            bar_s = self.s(bar)

            drums_on = sec in ("groove", "main", "build") or (sec == "outro" and frac < 0.5)
            full_kit = sec in ("main",) or (sec == "groove" and frac > 0.5)
            pad_on = sec != "intro" or frac > 0.3
            keys_on = sec in ("intro", "break", "outro", "groove") and spec.get("keys", True)
            pluck_on = sec in ("groove", "main", "build") and spec.get("pluck", True)
            lead_on = sec in ("main", "break") and spec.get("lead", True)
            guitar_on = spec.get("guitar", False) and sec in ("intro", "break", "outro", "main")
            perc_on = sec in ("groove", "main", "build", "break") and spec.get("perc", True)
            intensity = {"intro": 0.35, "groove": 0.7, "build": 0.8, "main": 1.0, "break": 0.5, "outro": 0.4}[sec]

            # --- Drums -------------------------------------------------------
            if drums_on:
                ks = kick_steps_house if style == "house" else kick_steps_down
                for st in ks:
                    if sec == "build" and frac > 0.75 and st not in (0, 8):
                        continue
                    pos = bar_s + st * beat16
                    place(self.layers["drums"], pos, kick_s * (0.85 + 0.15 * intensity))
                    self.kick_times.append(pos)
                if full_kit or sec == "build":
                    for st in range(16):
                        if st % 2 == 1 and rng.random() > 0.35 and not full_kit:
                            continue
                        h = (ohat if spec.get("house_kit", False) else hat_o) if st in (2, 6, 10, 14) else hat_c
                        vel = hat_vel[st] * (0.6 if st % 2 == 1 else 1.0)
                        place(self.layers["drums"], bar_s + st * beat16 + int(rng.normal(0, 0.0015) * SR), h * vel)
                    for st in (4, 12):
                        place(self.layers["drums"], bar_s + st * beat16, clap_s * (0.8 + 0.2 * rng.random()))
                        place(self.layers["drums"], bar_s + st * beat16, snare_s * (0.9 if style == "house" else 0.6))
                    if style == "house" and sec == "main":
                        for st in range(0, 16, 2):
                            place(self.layers["drums"], bar_s + st * beat16 + int(rng.normal(0, 0.001) * SR),
                                  ride_s * (1.0 if st % 4 == 0 else 0.7))
                else:
                    for st in (2, 6, 10, 14):
                        place(self.layers["drums"], bar_s + st * beat16, hat_o * 0.7)
                    if sec == "groove":
                        for st in range(0, 16, 2):
                            place(self.layers["drums"], bar_s + st * beat16, hat_c * 0.5)
                if sec == "build" and frac > 0.5:
                    for st in range(0, 16, 2 if frac < 0.85 else 1):
                        place(self.layers["drums"], bar_s + st * beat16, rim_s * (0.4 + 0.6 * frac))

            # --- Percussion ----------------------------------------------------
            if perc_on:
                for st in range(16):
                    vel = 1.0 if st in shaker_accents else 0.45
                    if st % 2 == 0 or rng.random() < 0.6:
                        place(self.layers["perc"], bar_s + st * beat16 + int(rng.normal(0, 0.002) * SR),
                              shaker_s * vel * intensity)
                if spec.get("congas", True):
                    for st, cg in zip(conga_pattern, congas):
                        if rng.random() < 0.85:
                            place(self.layers["perc"], bar_s + st * beat16 + int(rng.normal(0, 0.003) * SR),
                                  cg * (0.7 + 0.3 * rng.random()) * intensity)

            # --- Bass --------------------------------------------------------
            if drums_on or sec == "break":
                bs = bass_steps_house if style == "house" else bass_steps_down
                if sec == "break":
                    bs = [0]
                for i, st in enumerate(bs):
                    nxt = bs[i + 1] if i + 1 < len(bs) else 16
                    hold = int((nxt - st) * beat16 * (0.6 if style == "house" else 0.9))
                    m = bass_midi
                    if style == "house" and st in (6, 14):
                        m = bass_midi + (12 if rng.random() < 0.5 else 7)
                    if st == 11 and rng.random() < 0.5:
                        m = bass_midi + 12
                    vel = 1.0 if st in (0, 8) else 0.85
                    place(self.layers["bass"], bar_s + st * beat16,
                          synth_bass(rng, float(midi_to_hz(m)), hold, level=0.8 * vel * (0.8 + 0.2 * intensity),
                                     cutoff=spec.get("bass_cutoff", 700.0) * (0.7 + 0.5 * intensity)))

            # --- Pad ---------------------------------------------------------
            if pad_on:
                voicing = [m + 12 for m in chord_midis]
                voicing = [m - 12 if m > self.root + 24 + 10 else m for m in voicing]
                hold = int(self.bar * SR * 1.02)
                cutoff = spec.get("pad_cutoff", 1300.0) * (0.7 + 0.5 * intensity)
                place(self.layers["pad"], bar_s - int(0.15 * SR),
                      pad_chord(rng, voicing, hold, cutoff=cutoff, level=0.2 * spec.get("pad_level", 1.0)))

            # --- Keys (E-Piano) ---------------------------------------------
            if keys_on:
                voicing = [m + 12 for m in chord_midis[:4]]
                pattern = spec.get("keys_pattern", [0, 6, 10])
                for st in pattern:
                    if rng.random() < 0.15:
                        continue
                    hold = int(self.beat * SR * rng.uniform(0.9, 1.8))
                    strum = 0
                    for m in voicing:
                        place(self.layers["keys"], bar_s + st * beat16 + strum,
                              ep_keys(rng, m, hold, level=0.16, pan=rng.uniform(-0.4, 0.4)))
                        strum += int(rng.uniform(0.008, 0.02) * SR)

            # --- Pluck-Arpeggio ---------------------------------------------
            if pluck_on:
                notes = [m + 24 for m in chord_midis]
                notes = notes[:4]
                step = 2 if style == "house" else 4
                for i, st in enumerate(range(0, 16, step)):
                    if sec == "groove" and rng.random() < 0.3:
                        continue
                    idx = arp_pattern[i % len(arp_pattern)] % len(notes)
                    m = notes[idx]
                    if rng.random() < 0.12:
                        m += 12
                    hold = int(beat16 * step * 0.55)
                    place(self.layers["pluck"], bar_s + st * beat16,
                          pluck(rng, m, hold, level=0.22 * intensity, brightness=spec.get("pluck_brightness", 2400.0),
                                pan=(-0.5 if i % 2 else 0.5) * 0.6))

            # --- Acid-Line (303-Stil) ------------------------------------------
            acid_on = spec.get("acid", False) and sec in ("groove", "main", "build", "break")
            if acid_on:
                root_m = scale_degree_midi(self.root, self.scale, deg, -1)
                if root_m > 50:
                    root_m -= 12
                prev = None
                variation = (bar // 4) % 3
                for st in range(16):
                    ev = acid_steps[(st + (4 if variation == 2 else 0)) % 16]
                    if ev is None:
                        prev = None
                        continue
                    if sec == "groove" and st % 2 == 1:
                        prev = None
                        continue
                    if sec == "break" and st not in (0, 6, 8, 11):
                        prev = None
                        continue
                    iv, acc, slide = ev
                    if variation == 1 and st in (3, 11):
                        iv = 7 if iv == 0 else iv
                    m = root_m + iv
                    hold = int(beat16 * (1.6 if slide else 0.55))
                    cut = spec.get("acid_cutoff", 380.0) * (0.75 + 0.6 * intensity)
                    if sec == "build":
                        cut *= 1.0 + 1.5 * frac
                    place(self.layers["acid"], bar_s + st * beat16,
                          acid_note(rng, m, hold, prev_midi=prev if slide else None, accent=acc,
                                    level=0.34 * spec.get("acid_level", 1.0) * (0.7 + 0.3 * intensity),
                                    base_cut=cut, env_amount=spec.get("acid_env", 2400.0),
                                    q=spec.get("acid_q", 7.0), wave=spec.get("acid_wave", "saw")))
                    prev = m

            # --- House-Chord-Stabs ---------------------------------------------
            if spec.get("stabs", False) and sec in ("main", "build") and (full_kit or sec == "build"):
                voicing = [m + 12 for m in chord_midis[:4]]
                for st in stab_steps:
                    if rng.random() < 0.15:
                        continue
                    place(self.layers["stab"], bar_s + st * beat16,
                          house_stab(rng, voicing, int(beat16 * 1.2), level=0.26 * intensity,
                                     cutoff=spec.get("stab_cutoff", 2200.0), pan=rng.uniform(-0.3, 0.3)))

            # --- Trance: Arpeggio, Supersaw-Hook, Riser ---------------------------
            if spec.get("trance", False):
                arp_tones = sorted({m + 12 for m in chord_midis[:4]} | {m + 24 for m in chord_midis[:2]})
                order = arp_tones + arp_tones[-2:0:-1]  # auf und ab
                if sec in ("main", "build") and (full_kit or sec == "build"):
                    for st in range(16):
                        if st % 4 == 3 and rng.random() < 0.35:
                            continue
                        m = order[(st + bar * 2) % len(order)]
                        place(self.layers["trance"], bar_s + st * beat16,
                              trance_pluck(rng, m, int(beat16 * 0.6),
                                           level=0.16 * intensity * spec.get("trance_level", 1.0),
                                           pan=0.55 if st % 2 else -0.55))
                if sec == "main" and frac >= 0.5 or (sec == "break" and frac > 0.4):
                    motif = motif_a
                    half = (bar % 2) * 16
                    for st, dgr, dur in motif:
                        if not (half <= st < half + 16) or dur < 2:
                            continue
                        d = self.snap_to_chord(dgr, bar) if st % 4 == 0 else dgr
                        m = scale_degree_midi(self.root, self.scale, d, 1)
                        hold = int(dur * beat16 * 1.1)
                        place(self.layers["trance"], bar_s + (st - half) * beat16,
                              supersaw_lead(rng, m, hold, level=0.2 * spec.get("trance_level", 1.0),
                                            cutoff=spec.get("trance_cutoff", 3200.0), pan=0.0))
                if sec == "build" and frac == 0.0:
                    n_build = int(self.sections_bars_at(bar) * self.bar * SR)
                    place(self.layers["trance"], bar_s, riser(rng, n_build, level=0.16))

            # --- Lead-Melodie -----------------------------------------------
            if lead_on:
                motif = motif_a if (bar // 2) % 4 in (0, 1, 3) else motif_b
                half = (bar % 2) * 16
                for st, dgr, dur in motif:
                    if not (half <= st < half + 16):
                        continue
                    d = self.snap_to_chord(dgr, bar) if (st % 4 == 0) else dgr
                    m = scale_degree_midi(self.root, self.scale, d, 1)
                    hold = int(dur * beat16 * 0.85)
                    place(self.layers["lead"], bar_s + (st - half) * beat16,
                          lead(rng, m, hold, level=0.24 * spec.get("lead_level", 1.0), pan=0.1))

            # --- Gitarre -----------------------------------------------------
            if guitar_on:
                notes = [m for m in chord_midis]
                pattern = spec.get("guitar_pattern", [0, 3, 6, 8, 11, 14])
                for i, st in enumerate(pattern):
                    if rng.random() < 0.2:
                        continue
                    m = notes[i % len(notes)]
                    if i % 3 == 2:
                        m += 12
                    place(self.layers["guitar"], bar_s + st * beat16,
                          ks_guitar(rng, m, int(beat16 * 3), level=0.3, pan=rng.uniform(-0.6, 0.6)))

        # --- Atmosphäre ---------------------------------------------------------
        if spec.get("ocean", False):
            atm = ocean(rng, self.n, level=0.11)
            intro_bars = self.sections[0][1]
            outro_bars = self.sections[-1][1]
            fade = np.ones(self.n)
            a = int(intro_bars * self.bar * SR)
            b = int((self.total_bars - outro_bars) * self.bar * SR)
            fade[a:b] = np.linspace(1.0, 0.25, max(1, b - a)) ** 0.5 * 0.4 + 0.15
            fade[b:] = np.linspace(0.4, 1.0, self.n - b)
            self.layers["atmos"] += atm * fade[:, None]
            if spec.get("seagulls", False):
                self.layers["atmos"] += seagulls(rng, self.n, 0.045, count=5)

        return self.mix()

    def mix(self):
        spec = self.spec
        rng = self.rng
        ir_long = make_reverb_ir(rng, 3.2, 1.9, 3600.0)
        ir_room = make_reverb_ir(rng, 1.2, 4.5, 5000.0, 0.008)
        L = self.layers

        # Sidechain-Kurve aus den Kick-Zeiten
        duck = np.ones(self.n)
        if self.kick_times and spec.get("sidechain", True):
            curve_n = int(0.32 * SR)
            curve = 1.0 - 0.7 * np.exp(-np.linspace(0, 5, curve_n))
            for kt in self.kick_times:
                end = min(self.n, kt + curve_n)
                if kt < self.n:
                    duck[kt:end] = np.minimum(duck[kt:end], curve[: end - kt])
            duck = lowpass(duck, 60.0)
            duck = np.clip(duck, 0.25, 1.0)

        pad = chorus_widen(L["pad"], rng)
        pad = reverb(pad, ir_long, 0.55) * duck[:, None]
        keys = reverb(delay(L["keys"], self.beat * 0.75, 0.35, 4, 2800.0, True, 0.25), ir_long, 0.35)
        pluck = reverb(delay(L["pluck"], self.beat * 1.5, 0.4, 5, 3000.0, True, 0.3), ir_room, 0.3) * (0.5 + 0.5 * duck[:, None])
        lead_l = reverb(delay(L["lead"], self.beat * 1.5, 0.45, 6, 2600.0, True, 0.35), ir_long, 0.45)
        guitar = reverb(delay(L["guitar"], self.beat * 0.75, 0.3, 3, 3000.0, False, 0.2), ir_room, 0.35)
        perc = reverb(L["perc"], ir_room, 0.18)
        drums = reverb(L["drums"], ir_room, 0.06)
        bass = L["bass"] * (0.55 + 0.45 * duck[:, None])
        acid = reverb(delay(L["acid"], self.beat * 0.75, 0.3, 3, 2400.0, True, 0.18), ir_room, 0.16) * (0.7 + 0.3 * duck[:, None])
        trance = reverb(delay(L["trance"], self.beat * 0.75, 0.4, 5, 3200.0, True, 0.3), ir_long, 0.55) * duck[:, None]
        stab = reverb(delay(L["stab"], self.beat * 1.5, 0.35, 4, 3000.0, True, 0.25), ir_long, 0.3) * duck[:, None]
        atmos = L["atmos"]

        parts = dict(drums=drums * 0.95, perc=perc * 1.1, bass=bass * 0.85, pad=pad * 2.4, keys=keys * 1.2,
                     pluck=pluck * 1.9, lead=lead_l * 1.6, guitar=guitar * 1.5, atmos=atmos * 1.8,
                     acid=acid * 1.3, stab=stab * 2.4, trance=trance * 1.7)
        if os.environ.get("ALBUM_DEBUG"):
            for k, v in parts.items():
                r = np.sqrt(np.mean(v ** 2)) + 1e-9
                print(f"      {k:7s} {20*np.log10(r):6.1f} dBFS", file=sys.stderr)
        mixv = sum(parts.values())
        mixv = highpass(mixv, 28.0)

        # Master: Fade-In/-Out, sanfte Kompression, Peak-Normalisierung
        fade_in = int(0.5 * SR)
        mixv[:fade_in] *= np.linspace(0, 1, fade_in)[:, None]
        tail = int(4.0 * SR)
        mixv[-tail:] *= np.linspace(1, 0, tail)[:, None] ** 1.5
        mixv = master_chain(mixv)
        return mixv


def bus_compressor(x, threshold=0.22, ratio=3.5, attack=0.004, release=0.18):
    """Einfacher Feed-Forward-Kompressor auf dem Summensignal (Stereo-Link)."""
    level = np.max(np.abs(x), axis=1)
    a_att = np.exp(-1.0 / (attack * SR))
    a_rel = np.exp(-1.0 / (release * SR))
    # Hüllkurvenfolger (Peak) via lfilter in zwei Stufen: schneller Anstieg, langsamer Abfall
    env = signal.lfilter([1 - a_rel], [1, -a_rel], level)
    env = np.maximum(env, signal.lfilter([1 - a_att], [1, -a_att], level))
    gain = np.ones_like(env)
    over = env > threshold
    gain[over] = (threshold / env[over]) ** (1.0 - 1.0 / ratio)
    gain = lowpass(gain, 400.0)
    return x * gain[:, None]


def master_chain(x):
    # Tilt-EQ: etwas mehr Gewicht unten, Luft oben
    low = lowpass(x, 110.0, 2)
    high = highpass(x, 6500.0, 2)
    x = highpass(x, 32.0)
    x = x + 0.12 * low + 0.3 * high
    # Kompression, Sättigung, Loudness
    rms = np.sqrt(np.mean(x ** 2)) + 1e-9
    x *= 0.16 / rms
    x = bus_compressor(x)
    x = soft_clip(x * 1.1, 1.6)
    rms = np.sqrt(np.mean(x ** 2)) + 1e-9
    x *= 0.17 / rms
    x = soft_clip(x, 1.8)
    x *= 0.98 / (np.abs(x).max() + 1e-9)
    return x


# --------------------------------------------------------------------------- #
# Album
# --------------------------------------------------------------------------- #
ALBUM_TITLE = "Sounds of Marbella 2026"
ALBUM_ARTIST = "DJ Jensi"

TRACKS = [
    dict(nr=1, title="La Fontanilla Sunrise", seed=1101, bpm=98, root=57, scale="minor", style="downtempo",
         progression=[(0, "9"), (5, "7"), (2, "7"), (6, "7")],
         sections=[("intro", 8), ("groove", 12), ("main", 16), ("break", 8), ("main", 12), ("outro", 10)],
         ocean=True, seagulls=True, keys=True, pluck=False, lead=True, guitar=False, congas=True,
         pad_cutoff=1100.0, lead_level=0.9),
    dict(nr=2, title="La Concha Horizon", seed=2202, bpm=106, root=62, scale="dorian", style="house",
         progression=[(0, "7"), (3, "7"), (0, "7"), (6, "7")],
         sections=[("intro", 6), ("groove", 12), ("build", 6), ("main", 16), ("break", 8), ("main", 12), ("outro", 8)],
         ocean=False, keys=False, pluck=True, lead=True, guitar=True, congas=True,
         pad_cutoff=1500.0, guitar_pattern=[0, 3, 6, 8, 11, 14],
         acid=True, acid_level=0.75, acid_density=0.55, acid_cutoff=320.0, acid_q=5.5, house_kit=True,
         trance=True, trance_level=0.8, trance_cutoff=2800.0),
    dict(nr=3, title="Golden Mile Breeze", seed=3303, bpm=112, root=59, scale="minor", style="house",
         progression=[(0, "9"), (5, "9"), (3, "7"), (4, "7")],
         sections=[("intro", 6), ("groove", 12), ("build", 6), ("main", 16), ("break", 8), ("build", 4), ("main", 12), ("outro", 8)],
         ocean=False, keys=True, pluck=True, lead=False, guitar=False, congas=False,
         pad_cutoff=1700.0, pluck_brightness=3200.0, keys_pattern=[0, 4, 8, 12],
         acid=True, acid_level=0.9, acid_density=0.7, acid_cutoff=420.0, acid_q=7.5, acid_wave="square",
         stabs=True, stab_pattern=[2, 7, 10, 15], stab_cutoff=2600.0, house_kit=True,
         trance=True, trance_level=1.0, trance_cutoff=3400.0),
    dict(nr=4, title="Cabopino Drum Circle", seed=4404, bpm=102, root=55, scale="dorian", style="downtempo",
         progression=[(0, "7"), (0, "7"), (3, "7"), (6, "7")],
         sections=[("intro", 6), ("groove", 12), ("main", 16), ("break", 6), ("main", 12), ("outro", 8)],
         ocean=True, seagulls=False, keys=False, pluck=True, lead=True, guitar=True, congas=True,
         pad_cutoff=1200.0, lead_octave=1, sidechain=False, kick_punch=0.6,
         acid=True, acid_level=0.6, acid_density=0.45, acid_cutoff=260.0, acid_q=5.0),
    dict(nr=5, title="Puerto Banús Nights", seed=5505, bpm=118, root=57, scale="minor", style="house",
         progression=[(0, "7"), (5, "7"), (0, "7"), (4, "7")],
         sections=[("intro", 8), ("groove", 12), ("build", 8), ("main", 16), ("break", 8), ("build", 4), ("main", 16), ("outro", 8)],
         ocean=False, keys=False, pluck=True, lead=True, guitar=False, congas=False,
         pad_cutoff=1900.0, pad_level=1.1, pluck_brightness=2800.0,
         acid=True, acid_level=1.0, acid_density=0.75, acid_cutoff=450.0, acid_q=8.5, acid_env=3000.0,
         stabs=True, stab_pattern=[4, 12], stab_cutoff=2000.0, house_kit=True,
         trance=True, trance_level=0.9, trance_cutoff=3000.0),
    dict(nr=6, title="Sierra Blanca Drift", seed=6606, bpm=94, root=64, scale="major", style="downtempo",
         progression=[(0, "9"), (3, "9"), (5, "7"), (4, "7")],
         sections=[("intro", 8), ("groove", 12), ("main", 12), ("break", 8), ("main", 12), ("outro", 10)],
         ocean=True, seagulls=True, keys=True, pluck=False, lead=True, guitar=True, congas=True,
         pad_cutoff=1000.0, keys_pattern=[0, 6, 10, 13], kick_punch=0.7),
    dict(nr=7, title="Casco Antiguo Echoes", seed=7707, bpm=110, root=60, scale="minor", style="house",
         progression=[(0, "7"), (6, "7"), (5, "9"), (6, "7")],
         sections=[("intro", 6), ("groove", 12), ("build", 6), ("main", 16), ("break", 8), ("main", 12), ("outro", 8)],
         ocean=False, keys=True, pluck=True, lead=True, guitar=False, congas=True,
         pad_cutoff=1400.0, keys_pattern=[0, 7, 10], lead_level=0.8,
         acid=True, acid_level=0.8, acid_density=0.6, acid_cutoff=360.0, acid_q=6.5,
         stabs=True, stab_pattern=[2, 10], stab_cutoff=1800.0, house_kit=True),
    dict(nr=8, title="Playa de Nagüeles, 6 a.m.", seed=8808, bpm=96, root=53, scale="dorian", style="downtempo",
         progression=[(0, "9"), (2, "7"), (5, "7"), (3, "7")],
         sections=[("intro", 10), ("groove", 12), ("main", 12), ("break", 8), ("main", 10), ("outro", 12)],
         ocean=True, seagulls=True, keys=True, pluck=False, lead=True, guitar=True, congas=False,
         pad_cutoff=950.0, sidechain=False, kick_punch=0.5, guitar_pattern=[0, 4, 8, 12]),
]


def write_outputs(mixv, base, want_wav, want_mp3):
    pcm = np.clip(mixv, -1.0, 1.0)
    pcm16 = (pcm * 32767.0).astype(np.int16)
    if want_wav:
        wavfile.write(base + ".wav", SR, pcm16)
    if want_mp3:
        try:
            import lameenc
        except ImportError:
            print("  lameenc fehlt (pip install lameenc) – MP3 übersprungen", file=sys.stderr)
            return
        enc = lameenc.Encoder()
        enc.set_bit_rate(192)
        enc.set_in_sample_rate(SR)
        enc.set_channels(2)
        enc.set_quality(2)
        data = enc.encode(pcm16.tobytes()) + enc.flush()
        with open(base + ".mp3", "wb") as fh:
            fh.write(data)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "out"))
    ap.add_argument("--track", type=int, default=None, help="nur Track-Nummer rendern")
    ap.add_argument("--wav", action="store_true", help="zusätzlich WAV schreiben")
    ap.add_argument("--no-mp3", action="store_true")
    ap.add_argument("--short", action="store_true", help="verkürzte Testfassung")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    tracklist = []
    for spec in TRACKS:
        if args.track is not None and spec["nr"] != args.track:
            continue
        print(f"[{spec['nr']}/{len(TRACKS)}] {spec['title']}  ({spec['bpm']} BPM) ...", flush=True)
        tr = Track(spec, short=args.short)
        mixv = tr.render()
        dur = len(mixv) / SR
        import unicodedata
        plain = unicodedata.normalize("NFKD", spec["title"]).encode("ascii", "ignore").decode()
        slug = f"{spec['nr']:02d}-" + "".join(c if c.isalnum() else "-" for c in plain.lower()).strip("-")
        while "--" in slug:
            slug = slug.replace("--", "-")
        write_outputs(mixv, os.path.join(args.out, slug), args.wav, not args.no_mp3)
        rms = float(np.sqrt(np.mean(mixv ** 2)))
        print(f"    {int(dur//60)}:{dur%60:02.0f} min, RMS {20*np.log10(rms):.1f} dBFS", flush=True)
        tracklist.append(dict(nr=spec["nr"], title=spec["title"], bpm=spec["bpm"], seed=spec["seed"],
                              key=f"{['C','C#','D','Eb','E','F','F#','G','Ab','A','Bb','B'][spec['root']%12]} {spec['scale']}",
                              duration_s=round(dur, 1), file=slug + ".mp3"))

    with open(os.path.join(args.out, "tracklist.json"), "w", encoding="utf-8") as fh:
        json.dump(dict(album=ALBUM_TITLE, artist=ALBUM_ARTIST, year=2026, license="CC0-1.0", tracks=tracklist), fh, ensure_ascii=False, indent=2)
    print("fertig:", args.out)


if __name__ == "__main__":
    main()

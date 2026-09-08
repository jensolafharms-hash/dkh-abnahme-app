#!/usr/bin/env python3
"""
Spielt die MIDI-Stimmen des Albums mit aufgenommenen Instrumenten (SoundFont
FluidR3_GM, MIT-Lizenz) über FluidSynth und ersetzt damit die synthetischen
Spuren Gitarre, Bass, Flöte, Trompete, Steel Drum, Percussion und Chor.

Voraussetzung: fluidsynth und fluid-soundfont-gm (Debian/Ubuntu-Pakete).
"""
import os
import subprocess
import tempfile

import numpy as np
from scipy.io import wavfile

SF2 = "/usr/share/sounds/sf2/FluidR3_GM.sf2"
SR = 44100

# MIDI-Spurname -> (Ziel-Layer, GM-Programm, Pegelfaktor relativ zur synthetischen Spur)
SF_MAP = {
    "Guitar": ("guitar", 24, 1.0), "Guitar Comp": ("guitar", 24, 1.0),
    "Bass": ("bass", 33, 1.0), "Sub": ("bass", 38, 1.0),
    "Flute": ("flute", 73, 1.0), "Trumpet": ("brass", 56, 1.0), "Trumpet (muted)": ("brass", 59, 1.0),
    "Brass Stabs": ("brass", 61, 1.0), "Steel Drum": ("steel", 114, 1.0),
    "Percussion": ("perc", None, 1.0), "Choir": ("choir", 52, 1.0), "Choir Lead": ("choir", 52, 1.0),
    "Bell": ("bell", 14, 1.0),
}


def _render_midi(mid, n_samples, gain=0.8):
    with tempfile.TemporaryDirectory() as td:
        mp = os.path.join(td, "part.mid")
        wp = os.path.join(td, "part.wav")
        mid.save(mp)
        cmd = ["fluidsynth", "-ni", "-r", str(SR), "-g", str(gain), "-o", "synth.reverb.active=0", "-o", "synth.chorus.active=0",
               "-F", wp, SF2, mp]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        sr, x = wavfile.read(wp)
    x = x.astype(np.float64) / 32768.0
    if x.ndim == 1:
        x = np.stack([x, x], 1)
    out = np.zeros((n_samples, 2))
    m = min(n_samples, len(x))
    out[:m] = x[:m]
    return out


def replace_layers(track, midi_path, verbose=True):
    """Rendert die Spuren aus SF_MAP mit dem SoundFont und ersetzt die Layer des Tracks (Pegel angeglichen)."""
    import mido
    mid = mido.MidiFile(midi_path)
    conductor = mid.tracks[0]
    groups = {}
    for tr in mid.tracks[1:]:
        if tr.name in SF_MAP:
            groups.setdefault(SF_MAP[tr.name][0], []).append(tr)
    for layer, tracks in groups.items():
        part = mido.MidiFile(ticks_per_beat=mid.ticks_per_beat, type=1)
        part.tracks.append(conductor)
        for tr in tracks:
            part.tracks.append(tr)
        sig = _render_midi(part, track.n)
        old = track.layers[layer]
        rms_old = np.sqrt(np.mean(old ** 2)) + 1e-9
        rms_new = np.sqrt(np.mean(sig ** 2)) + 1e-9
        if rms_old > 1e-6 and rms_new > 1e-6:
            sig *= rms_old / rms_new
        track.layers[layer] = sig
        if verbose:
            print(f"      SoundFont: {layer:7s} <- {', '.join(t.name for t in tracks)}  ({20*np.log10(rms_new):.1f} -> {20*np.log10(rms_old):.1f} dBFS)", flush=True)
    return list(groups)

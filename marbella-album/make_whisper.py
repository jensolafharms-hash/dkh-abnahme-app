#!/usr/bin/env python3
"""
Erzeugt die gehauchte Stimme "golden mile breeze" für das Ende von Titel 3.

Quelle: lokale Sprachsynthese (Piper, Stimme en_US-ljspeech-high, Datensatz
LJ Speech, gemeinfrei). Aus der gesprochenen Fassung wird ein Flüstern:
Die spektrale Hüllkurve der Sprache wird auf Rauschen übertragen, die
Stimmbandschwingung entfällt. Ergebnis: assets/whisper-golden-mile-breeze.wav

    python3 make_whisper.py --voice /pfad/zu/en_US-ljspeech-high.onnx
"""
import argparse
import os
import wave

import numpy as np
from scipy import signal
from scipy.io import wavfile

HERE = os.path.dirname(os.path.abspath(__file__))
SR = 44100


def synthesize(voice_path, text, out_wav, length_scale=1.45):
    from piper import PiperVoice, SynthesisConfig
    v = PiperVoice.load(voice_path, voice_path + ".json")
    cfg = SynthesisConfig(length_scale=length_scale, noise_scale=0.5, noise_w_scale=0.6)
    with wave.open(out_wav, "wb") as w:
        v.synthesize_wav(text, w, syn_config=cfg)


def whisperize(x, sr, seed=3):
    rng = np.random.default_rng(seed)
    nfft, hop = 1024, 256
    f, t, Z = signal.stft(x, sr, nperseg=nfft, noverlap=nfft - hop)
    mag = np.abs(Z)
    # Hüllkurve: über die Frequenz glätten, damit nur Formanten bleiben (keine Tonhöhe)
    k = np.hanning(21)
    k /= k.sum()
    env = np.apply_along_axis(lambda c: np.convolve(c, k, mode="same"), 0, mag)
    noise = rng.standard_normal(len(x))
    _, _, N = signal.stft(noise, sr, nperseg=nfft, noverlap=nfft - hop)
    Y = N / (np.abs(N) + 1e-9) * env * 3.0
    _, y = signal.istft(Y, sr, nperseg=nfft, noverlap=nfft - hop)
    y = y[: len(x)]
    # Flüstern hat wenig Tiefen, etwas Luft oben
    sos = signal.butter(2, [180.0, 9000.0], "band", fs=sr, output="sos")
    y = signal.sosfilt(sos, y)
    return y / (np.abs(y).max() + 1e-9)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--voice", required=True, help="Pfad zur Piper-Stimme (.onnx)")
    ap.add_argument("--text", default="golden mile breeze.")
    args = ap.parse_args()
    tmp = os.path.join(HERE, "assets", "_speech.wav")
    synthesize(args.voice, args.text, tmp)
    sr, x = wavfile.read(tmp)
    x = x.astype(np.float64) / 32768.0
    y = whisperize(x, sr)
    y = signal.resample_poly(y, SR, sr)
    out = os.path.join(HERE, "assets", "whisper-golden-mile-breeze.wav")
    wavfile.write(out, SR, (y * 0.9 * 32767).astype(np.int16))
    os.remove(tmp)
    print("geschrieben:", out, f"{len(y)/SR:.2f} s")


if __name__ == "__main__":
    main()

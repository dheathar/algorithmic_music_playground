"""
ai/analyze.py — describe a sound in numbers (pure numpy, no ML deps).

Supports ear-training (spectrum -> feeling) and ingredient A/B: turns a rendered
signal into plain-language descriptors.
"""
import numpy as np
import synth as S


def analyze(sig):
    x = sig.mean(1) if np.ndim(sig) > 1 else np.asarray(sig)
    n = len(x)
    if n < 4:
        return {"error": "signal too short"}
    dur = n / S.SR
    rms = float(np.sqrt(np.mean(x ** 2)))
    peak = float(np.max(np.abs(x)))
    win = x * np.hanning(n)
    X = np.abs(np.fft.rfft(win))
    freqs = np.fft.rfftfreq(n, 1 / S.SR)
    centroid = float((freqs * X).sum() / (X.sum() + 1e-9))           # "brightness"
    zcr = float(np.mean((np.abs(np.diff(np.sign(x))) > 0).astype(float)))  # "noisiness"
    bright = ("dark" if centroid < 800 else "warm" if centroid < 2000
              else "bright" if centroid < 5000 else "brilliant")
    texture = "noisy" if zcr > 0.2 else "tonal"
    return {
        "dur": round(dur, 2), "rms": round(rms, 3), "peak": round(peak, 3),
        "centroid_hz": round(centroid), "brightness": bright,
        "zcr": round(zcr, 3), "texture": texture,
        "descriptor": f"{bright}, {texture}",
    }

"""
audition_glow.py — hear the new 'glow' organ for The Black Theater v003.

The spirits seen *inside* the watchers (dream `madeline3`): a hollow bell through
shimmer_halo (octave-up wash) + a faint sub-octave + a 3-voice detuned ensemble,
drifting slowly across the field — with a periodic 'crooked jerk' (a quick
downward pitch-bend through ring modulation, gated short). Sits over a hint of
the audience drone so you can judge it in context. A Phrygian.
"""
import numpy as np
import synth as S

DUR = 26.0
N = int(DUR * S.SR)


def place(canvas, st, at, gain=1.0):
    s = int(at * S.SR); e = min(s + len(st), len(canvas))
    if e > s:
        canvas[s:e] += gain * st[:e - s]
    return canvas


def audience_drone():
    """A hint of the watching drone — A Phrygian open fifth, dark and slow."""
    mono = np.zeros(N)
    for note in ("A1", "E2", "A2"):
        f = S.note_to_hz(note)
        v = S.saw(f, DUR, n_harm=10) * 0.5 + S.saw(f * 1.004, DUR, n_harm=10) * 0.5
        mono += v
    mono = S.resonant_lpf(mono / 3, 480, q=0.8)
    mono *= S.adsr(DUR, a=4, d=0, s=1, r=6)[:N]
    return S.reverb_st(S.as_stereo(mono), decay=3.5, mix=0.4, seed=8)


def glow_note(freq, dur):
    """A hollow bell -> shimmer halo + sub-octave + detuned ensemble."""
    n = int(dur * S.SR)
    bell = S.additive(freq, dur, [1, 0, 0.5, 0, 0.3, 0, 0.16, 0, 0.08])  # hollow, odd-ish
    bell *= S.adsr(dur, a=0.6, d=1.2, s=0.55, r=2.2)[:n]
    halo = S.shimmer_halo(bell, decay=4.5, seed=5)[:n]                   # the octave-up wash
    sub = S.sine(freq / 2, dur)[:n] * S.adsr(dur, a=0.8, d=0, s=0.9, r=2.0)[:n] * 0.25
    ens = np.zeros(n)                                                    # 3-voice ensemble (chorus)
    for c in (-7, 0, 6):
        ens += S.sine(freq * 2 ** (c / 1200), dur)[:n]
    ens = ens / 3 * S.adsr(dur, a=1.0, d=0, s=0.85, r=2.0)[:n] * 0.4
    mono = 0.7 * bell + 0.9 * halo + sub + ens
    return mono


def jerk(freq):
    """The crooked head-jerk: a quick downward pitch-bend through ring mod, gated."""
    dur = 0.24
    n = int(dur * S.SR); t = np.arange(n) / S.SR
    f = freq * (1 - 0.16 * np.clip(t / dur, 0, 1))      # the bend, sideways/down
    sig = S.sine(f, dur)
    st = S.ringmod(sig, freq * 1.37)                    # inharmonic = metallic/alien
    env = np.exp(-t / 0.05)
    return st * env[:, None]


def main():
    PHRYG = ["E5", "A5", "A#5", "C6", "E5", "C6"]       # A Phrygian, high
    glow = np.zeros((N, 2))
    # slow blooms of the glow, drifting across the field
    t = 1.5
    rng = np.random.default_rng(3)
    for k in range(6):
        f = S.note_to_hz(PHRYG[k % len(PHRYG)])
        g = glow_note(f, 6.0)
        pan = 0.6 * np.sin(2 * np.pi * 0.03 * np.arange(len(g)) / S.SR + k)  # slow autopan
        ang = (pan + 1) * 0.25 * np.pi
        st = np.stack([g * np.cos(ang), g * np.sin(ang)], axis=1)
        place(glow, st, t, gain=0.5)
        t += rng.uniform(3.0, 4.2)
    # the crooked jerks — irregular, sparse
    tj = 4.0
    for k in range(6):
        f = S.note_to_hz(PHRYG[(k * 2) % len(PHRYG)]) * (1 if k % 2 else 0.5)
        place(glow, jerk(f), tj, gain=0.22)
        tj += rng.uniform(2.8, 4.5)
    glow = S.reverb_st(glow, decay=4.5, mix=0.4, seed=9)

    mix = 0.7 * audience_drone() + 0.95 * glow
    mix = S.soft_clip(mix * 0.9, drive=1.0)
    S.write_wav("glow_audition.wav", mix)
    print("wrote glow_audition.wav", round(DUR, 1), "s")


if __name__ == "__main__":
    main()

"""
vitrine.py — "Vitrine"  (v001: the converter loop)

A piece about the soul put through an ADC and never fully recovered.

Inspired by a photograph of shop-window mannequins — stylized soulless souls,
the digitized image of a person with the person gone. The structure is the
signal chain itself:

    ANALOG soul  -> [ADC: band-limit, sample/hold, QUANTIZE]  -> digital
                 -> [DAC: zero-order hold, reconstruction LPF] -> "analog"
                 -> feed back in, one bit poorer ... forever (lossy).

Quantization error is irreversible: that is the soul we lose. The DAC reaches
back every pass and never quite makes it, so the loop never resolves — it just
keeps going, a notch lower each time.

Lineage (and how each maps to our engine):
  * J.-M. Jarre / Oxygene  — phased string pad (Eminent 310U -> Small Stone),
        additive synthesis, Revox "dry one side / delay the other" = our glass
        reflection.            -> supersaw -> phaser -> soft_clip, reflect()
  * W. Basinski / Disintegration Loops — the same loop re-digitized, losing
        material every pass.   -> render ONE phrase, bitcrush it harder per pass
  * Alva Noto / Ryoji Ikeda — the aesthetics of error: sine pips, grid clicks,
        quantization hiss, the seam.  -> mannequin layer

Soul sings in D minor; the mannequin answers in WHOLE-TONE (no leading tone,
cannot cadence) — the lead literally migrates from one scale to the other as it
is digitized.

And under all of it, a STARDUST bed that never degrades. The signal loses bits
every pass; the dust we are made of was never in the signal path, so it does not
quantize. When the soul is finally gridded to nothing, the dust is still
shimmering — the form is lost, the matter is conserved. (Hardware and people:
we lose and try to regain, endlessly; but we are all made of stardust.)

Key: D minor vs C whole-tone.  ~100 BPM grid.  Length: 300 s.
"""
import os
import shutil
import numpy as np
import synth as S

VERSION = 'v001'
DUR = 300.0
N = int(DUR * S.SR)
L = 44.0                     # length of the source phrase (re-converted each pass)
BPM = 100
EIGHTH = 60 / BPM / 2        # 0.30 s grid

WT = S.scale('C2', 'wholetone', octaves=5)   # whole-tone grid for snapping/mannequin


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def place(canvas, st, at, gain=1.0):
    """Mix a stereo signal into the stereo canvas at time `at` (seconds)."""
    s = int(at * S.SR)
    e = min(s + len(st), len(canvas))
    if e > s:
        canvas[s:e] += gain * st[:e - s]
    return canvas


def lp_st(st, cut, q=0.9):
    """Stereo lowpass (per channel) — used as both anti-alias and reconstruction."""
    return np.stack([S.resonant_lpf(st[:, 0], cut, q),
                     S.resonant_lpf(st[:, 1], cut, q)], axis=1)


def reflect(mono, ms=11.0, atten=0.7):
    """Jarre's Revox trick / a reflection in glass: dry left, delayed copy right."""
    d = int(ms / 1000 * S.SR)
    r = np.zeros_like(mono)
    r[d:] = mono[:-d] * atten
    return np.stack([mono, r], axis=1)


def comb(mono, ms=6.5, g=0.6):
    """Short feed-forward comb = the resonance of the glass pane (the seam)."""
    d = int(ms / 1000 * S.SR)
    y = mono.copy()
    y[d:] += g * mono[:-d]
    return y


def seam_split(mono):
    """The middle mannequin, split by the glass: bright in the left ear, dark in
    the right. One sound, two halves that never meet."""
    bright = S.resonant_lpf(comb(mono), 5200, 1.0)
    dark = S.resonant_lpf(mono, 650, 1.4)
    return np.stack([bright, dark], axis=1)


def snap(f):
    """Pull a frequency onto the nearest whole-tone grid pitch."""
    return min(WT, key=lambda g: abs(np.log(g / f)))


def degrade(st, bits, sr_div, aa_cut, recon_cut, hiss, width, seed=0):
    """One trip through the converter: ADC (anti-alias -> sample/hold -> quantize)
    then DAC (zero-order hold -> reconstruction filter), with the quantization
    noise the DAC can never remove. Returns degraded stereo of the same length."""
    x = lp_st(st, aa_cut)                                   # anti-alias before sampling
    x = S.bitcrush(x, bits=bits, rate=S.SR / sr_div)       # sample/hold + quantize + ZOH
    x = lp_st(x, recon_cut)                                 # DAC reconstruction filter
    if hiss > 0:                                            # irreversible quantization error
        rng = np.random.default_rng(seed)
        lvl = np.clip(np.abs(x).mean(1, keepdims=True) * 3, 0, 1)
        x = x + lvl * hiss * rng.standard_normal(x.shape)
    return S.stereo_width(x, width)


# ---------------------------------------------------------------------------
# the ANALOG source phrase (rendered ONCE, then re-converted each pass)
# ---------------------------------------------------------------------------
PAD = [                                   # (chord notes, bass note, t0, t1) in D minor
    (['D3', 'F3', 'A3'], 'D2', 0.0, 11.0),
    (['A#2', 'D3', 'F3'], 'A#1', 11.0, 22.0),     # Bb
    (['F3', 'A3', 'C4'], 'F2', 22.0, 33.0),
    (['G3', 'A#3', 'D4'], 'G2', 33.0, 44.0),      # Gm
]
LEAD = [                                  # (t, note, dur) — a mournful sigh in D minor
    (2.0, 'A3', 3.0), (6.0, 'F3', 2.5), (9.0, 'E3', 3.5), (14.0, 'D3', 4.0),
    (20.0, 'F3', 2.5), (23.0, 'G3', 2.0), (26.0, 'A3', 4.0), (31.0, 'C4', 3.0),
    (35.0, 'A#3', 3.0), (39.0, 'A3', 4.5),
]


def warm_note(freq, dur, seed=0, vib=0.0):
    n = int(dur * S.SR)
    f = freq * S.drift(dur, amount=0.004, rate=0.8, seed=seed)   # analog is alive
    if vib > 0:
        f = f * (1 + vib * np.sin(2 * np.pi * 5 * np.arange(n) / S.SR))
    sig = S.additive(f, dur, [1, 0.5, 0.25, 0.12, 0.06])
    sig = S.resonant_lpf(sig, 2700, 1.0)
    return sig * S.adsr(dur, a=0.07, d=0.4, s=0.7, r=0.6)[:len(sig)]


def build_bed():
    """Phased Dm string pad + warm bass — the soul's body. Mono -> phaser -> wide."""
    pad = np.zeros(int(L * S.SR))
    for i, (chord, bass, t0, t1) in enumerate(PAD):
        dur = t1 - t0 + 2.0
        for j, note in enumerate(chord):
            f = S.note_to_hz(note)
            v = S.supersaw(f, dur, voices=5, detune_cents=10) * 0.5
            v = S.resonant_lpf(v, 2200, 0.9) * S.adsr(dur, a=1.2, d=1.0, s=0.85, r=2.0)
            pad = S.mix_at(pad, v, t0, gain=0.5)
        b = S.additive(S.note_to_hz(bass), dur, [1, 0.4, 0.15]) * \
            S.adsr(dur, a=0.5, d=0.6, s=0.8, r=1.5)
        pad = S.mix_at(pad, b, t0, gain=0.6)
    pad = S.phaser(pad, rate=0.22, depth=0.7, stages=6, feedback=0.4, mix=0.5)   # Jarre
    pad = S.soft_clip(pad, 1.1)
    st = S.stereo_width(S.as_stereo(pad), 1.4)
    return S.autopan(st, rate=0.04, depth=0.18)


def build_lead(whole_tone):
    mono = np.zeros(int(L * S.SR))
    for k, (t, note, dur) in enumerate(LEAD):
        f = S.note_to_hz(note)
        if whole_tone:
            f = snap(f)
        mono = S.mix_at(mono, warm_note(f, dur, seed=k + 1, vib=0.01), t, gain=0.5)
    return mono


# ---------------------------------------------------------------------------
# the DIGITAL / mannequin layers
# ---------------------------------------------------------------------------
def click(dur=0.045):
    n = int(dur * S.SR)
    e = np.exp(-np.arange(n) / (0.007 * S.SR))
    return S.square(1500, dur)[:n] * e


def grid_clock(t0, t1, gain0, gain1):
    """A mechanical 8th-note tick — the showroom metronome — ramping in level."""
    out = np.zeros((N, 2))
    tk = click()
    st = S.pan(tk, 0.0)
    t = t0
    while t < t1:
        g = gain0 + (gain1 - gain0) * (t - t0) / max(1e-9, t1 - t0)
        place(out, st, t, gain=g)
        t += EIGHTH
    return out


def sine_pip(freq, dur=0.05):
    n = int(dur * S.SR)
    return S.sine(freq, dur) * np.exp(-np.arange(n) / (0.012 * S.SR))


def ikeda_field(t0, t1, density, seed=0):
    """Sparse high sine pips + clicks scattered in stereo — the glitch field."""
    out = np.zeros((N, 2))
    rng = np.random.default_rng(seed)
    for _ in range(int(density * (t1 - t0))):
        f = rng.choice(WT) * rng.choice([4, 8])
        p = rng.uniform(-0.9, 0.9)
        place(out, S.pan(sine_pip(f), p), rng.uniform(t0, t1), gain=rng.uniform(0.15, 0.4))
    return out


def stardust_layer(t0, t1, density, gmax, seed=0):
    """The conserved matter. Sparse decaying sine twinkles at FREE pitches (dust
    obeys no scale), scattered in stereo. This layer is NEVER sent through the
    converter — it does not quantize. It only gently swells across its span."""
    out = np.zeros((N, 2))
    rng = np.random.default_rng(seed)
    glen = int(0.55 * S.SR)
    decay = np.exp(-np.arange(glen) / (0.14 * S.SR))
    for _ in range(int(density * (t1 - t0))):
        tw = S.sine(rng.uniform(1800, 6200), glen / S.SR) * decay
        at = rng.uniform(t0, t1)
        g = gmax * (0.35 + 0.65 * (at - t0) / max(1e-9, t1 - t0))   # gentle swell
        place(out, S.pan(tw, rng.uniform(-0.88, 0.88)), at, gain=g)
    return out


# ---------------------------------------------------------------------------
# assemble
# ---------------------------------------------------------------------------
def main():
    print('vitrine: rendering the analog source phrase (once)...')
    bed = build_bed()
    lead_dm = build_lead(whole_tone=False)
    lead_wt = build_lead(whole_tone=True)

    def source(w):
        """Blend the soul-scale and mannequin-scale leads onto the bed."""
        lead = S.as_stereo((1 - w) * lead_dm + w * lead_wt) * 0.55
        m = min(len(bed), len(lead))
        return bed[:m] + lead[:m]

    # (start, blend_w, bits, sr_div, aa_cut, recon_cut, hiss, width, gain)
    PASSES = [
        (0.0,   0.00, 16, 1, 16000, 16000, 0.000, 1.40, 1.00),   # P0  analog soul
        (46.0,  0.15, 10, 2,  9000,  6000, 0.010, 1.10, 0.96),   # P1  first sampling
        (92.0,  0.40,  7, 3,  6000,  4000, 0.022, 0.80, 0.93),   # P2  quantizing
        (140.0, 0.70,  5, 5,  4200,  3000, 0.040, 0.55, 0.92),   # P3  collapsing
        (186.0, 1.00,  3, 8,  2800,  2200, 0.060, 0.28, 0.92),   # P4  the mannequin
        (214.0, 0.55,  6, 3,  7500,  5200, 0.030, 0.95, 0.92),   # DA  reach back (lossy)
        (244.0, 0.85,  3,10,  2400,  2000, 0.070, 0.22, 0.90),   # P5  ...keep going
    ]

    master = np.zeros((N, 2))
    print('vitrine: converting, pass by pass...')
    for i, (t, w, bits, srd, aa, rec, hs, wd, g) in enumerate(PASSES):
        src = source(w)
        deg = src if bits >= 16 else degrade(src, bits, srd, aa, rec, hs, wd, seed=i)
        place(master, deg, t, gain=g)
        print(f'  pass {i}: t={t:5.0f}s  w={w:.2f}  {bits}bit  /{srd}  -> placed')

    # the ADC waking up: an anti-alias sweep + the clock fading in under P0->P1
    print('vitrine: digital layers (clock, glitch field, seam)...')
    master += grid_clock(44.0, 300.0, 0.05, 0.5) * 1.0
    master += ikeda_field(96.0, 200.0, density=0.6, seed=3)
    master += ikeda_field(186.0, 250.0, density=1.6, seed=4)

    # the seam — the split middle mannequin, held bright-L / dark-R through the
    # mannequin region and kept ringing to the very end (the seam is never closed)
    seam_dur = 120.0
    seam_tone = np.zeros(int(seam_dur * S.SR))
    for f, t0 in [(snap(S.note_to_hz('C5')), 0.0), (snap(S.note_to_hz('E5')), 30.0)]:
        seam_tone = S.mix_at(seam_tone, S.sine(f, 70.0) *
                             S.adsr(70.0, a=6, d=4, s=0.8, r=20), t0, gain=0.5)
    place(master, seam_split(seam_tone), 168.0, gain=0.22)

    # stardust — the conserved matter, under everything, indifferent to the loss;
    # faint throughout, then shining through once the soul is gridded to nothing.
    print('vitrine: stardust (the matter that does not quantize)...')
    master += stardust_layer(0.0, 300.0, density=1.1, gmax=0.20, seed=11)
    master += stardust_layer(248.0, 300.0, density=3.2, gmax=0.42, seed=12)

    # spin-down: the snake eating its tail — quick alternations of bloom and crush
    for k, t in enumerate(np.arange(270.0, 285.0, 3.0)):
        w = 1.0 if k % 2 else 0.4
        snippet = degrade(source(w), bits=3 if k % 2 else 6, sr_div=8, aa_cut=3000,
                          recon_cut=2500, hiss=0.05, width=0.4, seed=20 + k)
        place(master, snippet[:int(3.0 * S.SR)], t, gain=0.6)

    # ending — UNRESOLVED: clock alone, then one held D (soul, lightly crushed)
    # against a whole-tone glass cluster. No cadence. We keep going.
    held = S.additive(S.note_to_hz('D3'), 14.0, [1, 0.5, 0.25, 0.1]) * \
        S.adsr(14.0, a=0.3, d=2, s=0.6, r=9)
    held = S.bitcrush(held, bits=6, rate=S.SR / 3)
    place(master, S.stereo_width(held, 0.6), 286.0, gain=0.5)
    cluster = np.zeros(int(14.0 * S.SR))
    for note in ['C4', 'E4', 'G#4']:
        cluster = S.mix_at(cluster, S.fm2(snap(S.note_to_hz(note)), 14.0, ratio=3.0,
                           index=3.0) * S.adsr(14.0, a=1, d=3, s=0.5, r=9), 0.0, gain=0.4)
    place(master, seam_split(S.bitcrush(cluster, bits=3).mean(1)), 286.0, gain=0.16)

    # master bus: gentle reverb glue + tanh ceiling
    print('vitrine: master bus (reverb + limit)...')
    master = S.reverb_st(master, decay=2.8, mix=0.16)
    master = S.soft_clip(master, 0.95)

    out_dir = os.path.join('versions', f'vitrine-{VERSION}')
    os.makedirs(out_dir, exist_ok=True)
    S.write_wav(os.path.join(out_dir, 'vitrine.wav'), master)
    S.write_wav('vitrine.wav', master)
    # copy this score in beside the render, so the edition is reproducible
    shutil.copy(__file__, os.path.join(out_dir, 'vitrine.py'))
    print(f'vitrine: wrote vitrine.wav and {out_dir}/  ({DUR:.0f}s)')


if __name__ == '__main__':
    main()

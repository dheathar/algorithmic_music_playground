"""
vitrine.py — "Vitrine"  (v002: one continuous AD/DA conversion)

A single warm phrase passed through a CONTINUOUS converter. The loss of fidelity
is intrinsic to the signal, not added on top: the anti-alias filter closes (the
sound darkens), the sample rate falls (aliasing that TRACKS the signal, and a
zero-order-hold stair-step), the bit depth drops (signal-correlated grit, and the
quiet detail FREEZES below the least-significant bit). No clock, no pips, no hiss
— the digital character emerges only from what the converter does to the sound.

The DAC reaches back once (the curves reopen ~3:34) and fails — re-quantizing an
already-quantized signal can't restore the lost bits — so it keeps going, a notch
lower. Stardust, the conserved matter, is the one thing never sent through the
converter; it emerges as the soul is gridded away.

From a photograph of shop-window mannequins: the digitized image with the soul gone.
Soul in D minor; the lead migrates to C whole-tone as it digitizes.  300 s.
"""
import os
import shutil
import numpy as np
import synth as S

VERSION = 'v002'
DUR = 300.0
N = int(DUR * S.SR)
L = 44.0                                   # the analog phrase (loops underneath)
WT = S.scale('C2', 'wholetone', octaves=5)


def snap(f):
    return min(WT, key=lambda g: abs(np.log(g / f)))


# ---------------------------------------------------------------------------
# the ANALOG source — a phased D-minor string pad + bass, and a warm lead.
# ---------------------------------------------------------------------------
PAD = [
    (['D3', 'F3', 'A3'], 'D2', 0.0, 11.0),
    (['A#2', 'D3', 'F3'], 'A#1', 11.0, 22.0),
    (['F3', 'A3', 'C4'], 'F2', 22.0, 33.0),
    (['G3', 'A#3', 'D4'], 'G2', 33.0, 44.0),
]
LEAD = [
    (2.0, 'A3', 3.0), (6.0, 'F3', 2.5), (9.0, 'E3', 3.5), (14.0, 'D3', 4.0),
    (20.0, 'F3', 2.5), (23.0, 'G3', 2.0), (26.0, 'A3', 4.0), (31.0, 'C4', 3.0),
    (35.0, 'A#3', 3.0), (39.0, 'A3', 4.5),
]


def warm_note(freq, dur, seed=0, vib=0.0):
    n = int(dur * S.SR)
    f = freq * S.drift(dur, amount=0.004, rate=0.8, seed=seed)
    if vib > 0:
        f = f * (1 + vib * np.sin(2 * np.pi * 5 * np.arange(n) / S.SR))
    sig = S.additive(f, dur, [1, 0.5, 0.25, 0.12, 0.06])
    sig = S.resonant_lpf(sig, 2700, 1.0)
    return sig * S.adsr(dur, a=0.07, d=0.4, s=0.7, r=0.6)[:len(sig)]


def build_bed():
    pad = np.zeros(int(L * S.SR))
    for chord, bass, t0, t1 in PAD:
        dur = t1 - t0 + 2.0
        for note in chord:
            v = S.supersaw(S.note_to_hz(note), dur, voices=5, detune_cents=10) * 0.5
            v = S.resonant_lpf(v, 2200, 0.9) * S.adsr(dur, a=1.2, d=1.0, s=0.85, r=2.0)
            pad = S.mix_at(pad, v, t0, gain=0.5)
        b = S.additive(S.note_to_hz(bass), dur, [1, 0.4, 0.15]) * S.adsr(dur, a=0.5, d=0.6, s=0.8, r=1.5)
        pad = S.mix_at(pad, b, t0, gain=0.6)
    pad = S.phaser(pad, rate=0.22, depth=0.7, stages=6, feedback=0.4, mix=0.5)      # Jarre
    pad = S.soft_clip(pad, 1.1)
    return S.autopan(S.stereo_width(S.as_stereo(pad), 1.4), rate=0.04, depth=0.18)


def build_lead(whole_tone):
    mono = np.zeros(int(L * S.SR))
    for k, (t, note, dur) in enumerate(LEAD):
        f = S.note_to_hz(note)
        if whole_tone:
            f = snap(f)
        mono = S.mix_at(mono, warm_note(f, dur, seed=k + 1, vib=0.01), t, gain=0.5)
    return mono


def stardust_layer(t0, t1, density, gmax, seed=0):
    """The conserved matter — sparse decaying sine twinkles at free pitches, NEVER
    sent through the converter (it does not quantize). Swells across its span."""
    out = np.zeros((N, 2))
    rng = np.random.default_rng(seed)
    glen = int(0.55 * S.SR)
    decay = np.exp(-np.arange(glen) / (0.14 * S.SR))
    for _ in range(int(density * (t1 - t0))):
        tw = S.sine(rng.uniform(1800, 6200), glen / S.SR) * decay
        at = rng.uniform(t0, t1)
        g = gmax * (0.35 + 0.65 * (at - t0) / max(1e-9, t1 - t0))
        out = S.mix_at(out, S.pan(tw, rng.uniform(-0.88, 0.88)), at, gain=g) if False else out
        s = int(at * S.SR); e = min(s + glen, N)
        ang = (rng.uniform(-0.88, 0.88) + 1) * 0.25 * np.pi
        out[s:e, 0] += g * tw[:e - s] * np.cos(ang)
        out[s:e, 1] += g * tw[:e - s] * np.sin(ang)
    return out


# ---------------------------------------------------------------------------
# the CONVERTER — continuous, time-varying. The loss IS the signal.
# ---------------------------------------------------------------------------
def lp_st(st, cut, q=0.8):
    return np.stack([S.resonant_lpf(st[:, 0], cut, q), S.resonant_lpf(st[:, 1], cut, q)], axis=1)


def sample_hold(st, sr_curve):
    """Sample-and-hold with a per-sample target rate (the ADC's sampling). As the
    rate falls, the held stair-steps lengthen and aliasing folds in — all of it
    tracking the signal. Vectorised: take a new sample each time a phase
    accumulator (rate/SR per sample) crosses an integer; hold it until the next."""
    phase = np.cumsum(np.clip(sr_curve, 200.0, S.SR) / S.SR)
    idx = np.floor(phase).astype(np.int64)
    take = np.where(np.diff(idx, prepend=idx[0] - 1) > 0)[0]      # sample instants
    pos = np.clip(np.searchsorted(take, np.arange(len(st)), side='right') - 1, 0, len(take) - 1)
    return st[take[pos]]                                          # zero-order hold


def quantize(st, bits_curve):
    """Per-sample amplitude quantization. The error is signal-correlated (grit,
    not white noise), and detail below the least-significant bit simply vanishes."""
    lv = (2.0 ** np.clip(bits_curve, 1.5, 16.0))[:, None]
    return np.round(st * lv) / lv


# ---------------------------------------------------------------------------
def main():
    print('vitrine: building the analog phrase (looped underneath)...')
    bed = S.loop_to(build_bed(), N)
    ldm = S.loop_to(S.as_stereo(build_lead(False)), N)
    lwt = S.loop_to(S.as_stereo(build_lead(True)), N)
    # the lead migrates D-minor -> whole-tone continuously as it digitizes
    w = S.curve([(0, 0), (60, 0.15), (120, 0.45), (185, 1.0), (214, 0.55), (244, 0.9), (300, 1.0)], DUR)[:, None]
    stream = bed + ldm * (1 - w) * 0.55 + lwt * w * 0.55

    # the conversion, as continuous curves (one molded arc, no blocks)
    aa = S.curve([(0, 16000), (40, 14000), (90, 7000), (140, 3800), (185, 2000),
                  (214, 9000), (244, 2400), (300, 700)], DUR)         # anti-alias closes
    srr = S.curve([(0, 44100), (40, 38000), (90, 16000), (140, 8000), (185, 4500),
                   (214, 17000), (244, 4200), (300, 3400)], DUR)      # sample rate falls
    bit = S.curve([(0, 16), (40, 14), (90, 9), (140, 6), (185, 3),
                   (214, 7.5), (244, 3), (300, 2)], DUR)              # bit depth falls
    wid = S.curve([(0, 1.4), (60, 1.2), (120, 0.9), (185, 0.3),
                   (214, 0.95), (244, 0.3), (300, 0.16)], DUR)        # the field collapses

    print('vitrine: converting (anti-alias -> sample/hold -> quantize -> reconstruct)...')
    x = lp_st(stream, aa)                                   # 1. band-limit before sampling
    x = sample_hold(x, srr)                                 # 2. sample & hold (decimate/alias)
    x = quantize(x, bit)                                    # 3. quantize (grit + freeze)
    x = lp_st(x, np.clip(srr * 0.45, 800, 16000))          # 4. DAC reconstruction filter
    x = S.stereo_width(x, wid)                              # 5. wide analog -> narrow digital

    # stardust — the conserved matter — a faint thread throughout, blooming as the
    # soul is finally gridded away (never sent through the converter).
    print('vitrine: stardust (the matter that does not quantize)...')
    dust = stardust_layer(0, 300, density=0.5, gmax=0.06, seed=11) \
        + stardust_layer(232, 300, density=2.6, gmax=0.34, seed=12)

    S.write_wav('vit_converter.wav', x)                    # per-organ stems for the visualizer
    S.write_wav('vit_stardust.wav', dust)

    print('vitrine: master bus (hall to mold it whole + ceiling)...')
    master = S.reverb_st(x + dust, decay=3.4, mix=0.18)
    master = S.soft_clip(master, 0.95)

    out_dir = os.path.join('versions', f'vitrine-{VERSION}')
    os.makedirs(out_dir, exist_ok=True)
    S.write_wav(os.path.join(out_dir, 'vitrine.wav'), master)
    S.write_wav('vitrine.wav', master)
    shutil.copy(__file__, os.path.join(out_dir, 'vitrine.py'))
    print(f'vitrine: wrote vitrine.wav and {out_dir}/  ({DUR:.0f}s)')


if __name__ == '__main__':
    main()

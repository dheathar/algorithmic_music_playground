"""
icarus.py — "Icarus, or the Effort of Flight"   (~3 minutes)

A flying dream fused with cosmic horror. You discover you can fly — but only by
clapping furiously (the effort). You rise just above the safe rooftops into joy,
and keep rising into the vast, indifferent churn of the cosmos (a real recording
of Jupiter). The higher the joy, the closer the horror; the effort to stay up is
the effort not to fall.

Organs:
  ROOFTOPS  warm Lydian home below (recedes as you climb)
  CLAP      a fast motoric pulse — the effort; thins when you tire
  ALTITUDE  soaring Lydian pad + lead — the joy; sags & recovers with effort
  VOID      the Jupiter ion-acoustic sample, engineered into the abyss
  FLUTES    alien whole-tone piping — the wrongness, at height

Key: A Lydian (human joy) vs whole-tone/void (the cosmos).  Tempo: 128 BPM.
"""
import os
import shutil
import numpy as np
import synth as S

VERSION = 'icarus-v001'
DUR = 180.0
N = int(DUR * S.SR)
TEMPO = 128
SIX = 60 / TEMPO / 4          # sixteenth-note = the clap grid (~0.117 s, ~8.5/s)

LYD = S.scale('A3', 'lydian', octaves=2)
WT = S.scale('A5', 'wholetone', octaves=1)


def lpf_st(st, cutoff, q=0.7):
    st = S.as_stereo(st)
    return np.stack([S.resonant_lpf(st[:, 0], cutoff, q),
                     S.resonant_lpf(st[:, 1], cutoff, q)], axis=1)


def place_st(canvas, sig, at, gain=1.0):
    sig = S.as_stereo(sig)
    start = int(at * S.SR)
    end = min(start + len(sig), len(canvas))
    canvas[start:end] += gain * sig[:end - start]
    return canvas


# ---- automation lanes (the narrative) ----
def lanes():
    return dict(
        effort=S.curve([(0, 0), (8, 0.4), (35, 0.7), (60, 0.9), (90, 1.0),
                        (120, 0.95), (140, 0.7), (165, 0.3), (180, 0.0)], DUR),
        altitude=S.curve([(0, 0), (12, 0.2), (40, 0.45), (90, 0.85), (115, 1.0),
                          (140, 0.6), (180, 0.08)], DUR),
        ground=S.curve([(0, 1.0), (25, 0.6), (55, 0.25), (95, 0.06),
                        (150, 0.45), (180, 0.85)], DUR),
        voidl=S.curve([(0, 0), (35, 0.08), (70, 0.4), (100, 0.78), (120, 0.72),
                       (150, 0.35), (180, 0.12)], DUR),
        flute=S.curve([(0, 0), (82, 0), (96, 0.5), (120, 0.7), (140, 0.4),
                       (160, 0.05), (180, 0)], DUR),
    )


# ---- ROOFTOPS — warm home below ----
def rooftops(L):
    out = np.zeros(N)
    for note, g in {'A2': 1.0, 'E3': 0.6, 'C#4': 0.45, 'A3': 0.5}.items():
        d = S.drift(DUR, amount=0.003, rate=0.1, seed=abs(hash(note)) % 997)
        out += g * (0.7 * S.sine(S.note_to_hz(note) * d, DUR)
                    + 0.3 * S.saw(S.note_to_hz(note) * d, DUR, n_harm=8))
    out = S.resonant_lpf(out / 2.2, 720, q=0.8) * L['ground']
    return S.reverb_st(S.as_stereo(out), decay=2.6, mix=0.3, seed=11)


# ---- CLAP — the effort ----
def clap_hit(seed=0):
    dur = 0.14
    t = np.arange(int(dur * S.SR)) / S.SR
    nz = S.noise(dur, seed=seed)
    body = S.resonant_bpf(nz, 1700, q=1.1) * 1.3 + S.resonant_bpf(nz, 950, q=1.6) * 0.5
    return body * np.exp(-t / 0.022)


def clap(L):
    Lc, Rc = np.zeros(N), np.zeros(N)
    hit = clap_hit(seed=1)
    nh = len(hit)
    i = 0
    t = 4.0
    while t < DUR - 1:
        idx = int(t * S.SR)
        e = L['effort'][min(idx, N - 1)]
        # stumble: drop hits when tiring
        keep = not (e < 0.55 and (i % 3 == 0))
        if keep and e > 0.05:
            g = e * (0.8 + 0.2 * ((i * 7) % 5) / 4)
            pan = 0.25 * (1 if i % 2 else -1)
            angL, angR = (1 - pan), (1 + pan)
            end = min(idx + nh, N)
            seg = hit[:end - idx]
            Lc[idx:end] += g * seg * angL * 0.5
            Rc[idx:end] += g * seg * angR * 0.5
        i += 1
        t += SIX
    st = np.stack([Lc, Rc], axis=1)
    return S.reverb_st(st, decay=1.4, mix=0.18, seed=12)


# ---- ALTITUDE — joy + strain ----
def altitude(L):
    # soaring Lydian pad (limited harmonics for speed)
    pad = np.zeros(N)
    for note in ['A3', 'C#4', 'E4', 'F#4', 'B4']:
        f = S.note_to_hz(note)
        pad += 0.5 * (S.saw(f * 0.996, DUR, n_harm=16) + S.saw(f * 1.004, DUR, n_harm=16))
    pad /= 5
    cutoff = 500 + 3400 * L['altitude']
    pad = S.resonant_lpf(pad, cutoff, q=0.9)
    # amplitude: needs effort to hold; wavers (the strain)
    waver = 1 - 0.18 * (1 - L['effort']) * (0.5 + 0.5 * S.lfo(0.5, DUR))
    pad *= (0.35 + 0.65 * L['effort']) * (0.4 + 0.6 * L['altitude']) * waver
    pad = S.phaser(pad, rate=0.12, depth=0.6, stages=6, feedback=0.3, mix=0.4)
    pad_st = S.reverb_st(S.as_stereo(pad), decay=3.4, mix=0.4, seed=13)

    # soaring lead — a hopeful rising motif, sagging when effort flags
    lead = np.zeros(N)
    motif = [0, 2, 4, 3, 5, 4, 6, 7, 6, 4, 5, 7]   # indices into LYD
    t = 30.0
    j = 0
    while t < 150:
        idx = int(t * S.SR)
        e = L['effort'][min(idx, N - 1)]
        a = L['altitude'][min(idx, N - 1)]
        deg = motif[j % len(motif)] + (3 if a > 0.7 else 0)   # climbs higher when high
        f = LYD[deg % len(LYD)] * (2 if a > 0.7 else 1)
        dur = 0.45
        sag = 1 - 0.03 * (1 - e)                                # pitch droops when tiring
        tone = (S.sine(f * sag, dur) + 0.4 * S.saw(f * sag, dur, n_harm=10))
        env = S.adsr(dur, a=0.02, d=0.1, s=0.6, r=0.2)
        lead = S.mix_at(lead, tone * env * (0.3 + 0.7 * e), t, gain=0.5 * a)
        j += 1
        t += SIX * 4                                            # quarter-note melody
    lead_st = S.reverb_st(S.as_stereo(lead[:N]), decay=2.8, mix=0.45, seed=14)
    return pad_st + lead_st


# ---- VOID — the Jupiter sample, engineered into the abyss ----
def void(L):
    base = S.load_audio('space_library/jupiter_ion_acoustic.mp3')
    mono = base.mean(1)
    abyss = lpf_st(S.loop_to(S.resample_speed(base, 0.35), N), 700)
    cloud = S.granular_cloud(mono, DUR, grain=0.12, density=22, pitch=0.5,
                             pitch_jitter=4, pan_spread=0.85, seed=3)
    drone = lpf_st(S.spectral_drone(mono, DUR, seg=3.0, seed=5), 1400)
    v = 0.6 * S.as_stereo(abyss) + 0.7 * cloud[:N] + 0.5 * drone[:N]
    v *= L['voidl'][:, None]
    return S.reverb_st(v, decay=5.5, mix=0.5, seed=15)


# ---- FLUTES — alien whole-tone piping at height ----
def flute_note(freq, dur, seed):
    vib = 1 + 0.01 * S.lfo(6.0, dur)
    tone = S.sine(freq * vib, dur) + 0.1 * S.sine(2 * freq * vib, dur)
    air = S.resonant_lpf(S.noise(dur, seed=seed), 3000, q=0.7) * 0.08
    return (tone + air) * S.adsr(dur, a=0.3, d=0.2, s=0.6, r=0.5)


def flutes(L):
    st = np.zeros((N, 2))
    times = [92, 96.5, 101, 104, 110, 116, 121, 127, 133, 138, 145]
    for k, t in enumerate(times):
        f = WT[(k * 3 + 1) % len(WT)]                          # erratic whole-tone
        sig = flute_note(f, 2.2, seed=k + 20)
        pan = 0.7 * (1 if k % 2 else -1)
        ang = (pan + 1) * 0.25 * np.pi
        seg = np.stack([sig * np.cos(ang), sig * np.sin(ang)], axis=1)
        idx = int(t * S.SR)
        a = L['flute'][min(idx, N - 1)]
        st = place_st(st, seg, t, gain=0.6 * a)
    return S.reverb_st(st, decay=6.5, mix=0.6, seed=16)


# ---------------------------------------------------------------------------
if __name__ == '__main__':
    L = lanes()
    organs = {
        'rooftops': (rooftops(L), 0.70),
        'clap':     (clap(L),     0.60),
        'altitude': (altitude(L), 0.75),
        'void':     (void(L),     0.85),
        'flutes':   (flutes(L),   0.45),
    }
    mix = np.zeros((N, 2))
    for name, (sig, lvl) in organs.items():
        sig = S.as_stereo(sig)[:N]
        if len(sig) < N:
            sig = np.vstack([sig, np.zeros((N - len(sig), 2))])
        S.write_wav(f'ic_{name}.wav', sig)
        mix += lvl * sig
        print(f'  ic_{name}.wav')
    mix = S.soft_clip(mix * 0.62, drive=1.0)
    S.write_wav('icarus_mix.wav', mix)
    print('  icarus_mix.wav', round(DUR, 1), 's (stereo)')

    vd = os.path.join('versions', VERSION)
    os.makedirs(vd, exist_ok=True)
    for f in ['icarus_mix.wav'] + [f'ic_{n}.wav' for n in organs] + ['icarus.py', 'synth.py']:
        if os.path.exists(f):
            shutil.copy(f, vd)
    print('  archived ->', vd)

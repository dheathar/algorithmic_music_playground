"""
icarus.py — "Icarus, or the Effort of Flight"  (v002 — dramatic arc)

The shape the dream actually has:
  I.   STRUGGLE (0–45s)    effortful, tense, dissonant — fighting to get up
  II.  BREAKTHROUGH (~45s) a held breath, then it BURSTS into bright Lydian joy
                           — you did it, you're flying, it is unique
  III. KEEP THE PACE       high but relentless: driving bass, locked clap, the
                           altitude soaring yet wavering — great, and hard to hold

Built on the Jupiter ion-acoustic recording (the cosmic Void).
Key: A (tense/minor) → A Lydian (the joy).  Tempo: 128 BPM.
"""
import os
import shutil
import numpy as np
import synth as S

VERSION = 'icarus-v003'
DUR = 180.0
N = int(DUR * S.SR)
TEMPO = 128
SIX = 60 / TEMPO / 4
LYD = S.scale('A3', 'lydian', octaves=2)
WT = S.scale('A5', 'wholetone', octaves=1)


def lpf_st(st, cutoff, q=0.7):
    st = S.as_stereo(st)
    return np.stack([S.resonant_lpf(st[:, 0], cutoff, q),
                     S.resonant_lpf(st[:, 1], cutoff, q)], axis=1)


def place_st(canvas, sig, at, gain=1.0):
    sig = S.as_stereo(sig)
    s = int(at * S.SR)
    e = min(s + len(sig), len(canvas))
    canvas[s:e] += gain * sig[:e - s]
    return canvas


def lanes():
    # EFFORT comes in WAVES: continuous flapping to get up (the struggle), then
    # in the sustain it alternates FLAP (clap on) and GLIDE (clap off — you float).
    effort = S.curve([(0, 0.55), (15, 0.82), (38, 1.0), (44, 1.0), (45.5, 0.2),
                      (50, 0.95), (60, 1.0), (61, 0.05), (66, 0.05), (67, 1.0),   # flap / glide
                      (78, 1.0), (79, 0.05), (84, 0.05), (85, 1.0),
                      (97, 1.0), (98, 0.05), (104, 0.05), (105, 1.0),
                      (118, 1.0), (119, 0.05), (126, 0.05), (127, 1.0),
                      (140, 1.0), (150, 0.9), (168, 0.5), (180, 0)], DUR)
    drive_base = S.curve([(0, 0), (46, 0.3), (60, 1.0), (140, 1.0), (160, 0.7), (180, 0.1)], DUR)
    return dict(
        effort=effort,
        # altitude: struggling low, LIFTOFF at ~46, high & wavering; sags a touch on glides
        altitude=S.curve([(0, 0.05), (38, 0.16), (45, 0.2), (52, 0.72), (70, 0.9),
                          (120, 1.0), (150, 0.92), (180, 0.2)], DUR),
        bright=S.curve([(0, 0.06), (40, 0.12), (47, 0.95), (70, 0.9), (140, 0.85), (180, 0.4)], DUR),
        tension=S.curve([(0, 0.4), (20, 0.75), (40, 1.0), (46, 0.18), (90, 0.12),
                         (125, 0.22), (180, 0.1)], DUR),
        # bass drives only while flapping (rests during glides)
        drive=drive_base * effort,
        voidl=S.curve([(0, 0.2), (25, 0.45), (42, 0.62), (47, 0.22), (90, 0.4),
                       (125, 0.6), (150, 0.45), (180, 0.2)], DUR),
        flute=S.curve([(0, 0), (72, 0), (88, 0.5), (120, 0.7), (150, 0.4), (170, 0.05), (180, 0)], DUR),
    )


def stack(notes, nh, det=0.004):
    out = np.zeros(N)
    for note in notes:
        f = S.note_to_hz(note)
        out += 0.5 * (S.saw(f * (1 - det), DUR, n_harm=nh) + S.saw(f * (1 + det), DUR, n_harm=nh))
    return out / max(1, len(notes))


# ---- TENSION — the stress of getting up (dissonant: root, ♭2, tritone) ----
def tension(L):
    out = np.zeros(N)
    for note, g in {'A1': 1.0, 'A#1': 0.5, 'D#2': 0.45, 'A2': 0.4}.items():
        d = S.drift(DUR, amount=0.004, rate=0.2, seed=abs(hash(note)) % 900)
        out += g * (0.6 * S.sine(S.note_to_hz(note) * d, DUR) + 0.4 * S.saw(S.note_to_hz(note) * d, DUR, n_harm=12))
    out = S.resonant_lpf(out / 1.9, 520, q=1.2) * L['tension']
    return S.reverb_st(S.as_stereo(out), decay=3.5, mix=0.35, seed=18)


# ---- CLAP — the effort (dips at the breakthrough, then relentless) ----
def clap_hit(seed=0):
    dur = 0.14
    t = np.arange(int(dur * S.SR)) / S.SR
    nz = S.noise(dur, seed=seed)
    body = S.resonant_bpf(nz, 1700, q=1.1) * 1.3 + S.resonant_bpf(nz, 950, q=1.6) * 0.5
    return body * np.exp(-t / 0.022)


def clap(L):
    Lc, Rc = np.zeros(N), np.zeros(N)
    hit = clap_hit(seed=1); nh = len(hit)
    i, t = 0, 4.0
    while t < DUR - 1:
        idx = int(t * S.SR); e = L['effort'][min(idx, N - 1)]
        if e > 0.05 and not (e < 0.55 and i % 3 == 0):
            g = e * (0.8 + 0.2 * ((i * 7) % 5) / 4)
            pan = 0.25 * (1 if i % 2 else -1)
            end = min(idx + nh, N); seg = hit[:end - idx]
            Lc[idx:end] += g * seg * (1 - pan) * 0.5
            Rc[idx:end] += g * seg * (1 + pan) * 0.5
        i += 1; t += SIX
    return S.reverb_st(np.stack([Lc, Rc], axis=1), decay=1.4, mix=0.18, seed=12)


# ---- RISER — builds 36→46s into the breakthrough ----
def riser():
    seg = 10.0; n = int(seg * S.SR); t = np.arange(n) / S.SR
    cut = 300 * (40 ** (t / seg))                      # exp rising 300→12k
    sweep = S.resonant_lpf(S.noise(seg, seed=33), cut, q=1.5) * (np.linspace(0, 1, n) ** 2)
    base = S.load_audio('space_library/jupiter_ion_acoustic.mp3')
    rev = S.reverse(S.loop_to(base, n)) * (np.linspace(0, 1, n)[:, None] ** 1.5)
    sig = S.reverb_st(S.as_stereo(sweep) * 0.5 + rev * 0.5, decay=2.0, mix=0.4, seed=34)
    return place_st(np.zeros((N, 2)), sig, 36.0, gain=0.7)


# ---- PAD — dark/tense, crossfading to bright Lydian at the breakthrough ----
def pad(L):
    tense = stack(['A3', 'C4', 'E4', 'G4'], 14)        # minor-ish, darker
    lyd = stack(['A3', 'C#4', 'E4', 'F#4', 'B4'], 16)  # bright Lydian
    mix = tense * (1 - L['bright']) + lyd * L['bright']
    mix = S.resonant_lpf(mix, 400 + 3500 * L['altitude'], q=0.95)
    waver = 1 - 0.16 * (1 - L['effort']) * (0.5 + 0.5 * S.lfo(0.5, DUR))
    mix *= (0.4 + 0.6 * L['effort']) * (0.3 + 0.7 * L['altitude']) * waver
    mix = S.phaser(mix, rate=0.12, depth=0.6, stages=6, feedback=0.3, mix=0.4)
    return S.reverb_st(S.as_stereo(mix), decay=3.2, mix=0.4, seed=13)


# ---- BASS — the drive: keep the pace ----
def bass(L):
    out = np.zeros(N)
    pat = ['A1', 'A1', 'E2', 'A1', 'F#1', 'A1', 'E2', 'D2']
    t, j, eighth = 46.0, 0, SIX * 2
    while t < 176:
        idx = int(t * S.SR); d = L['drive'][min(idx, N - 1)]
        if d > 0.05:
            f = S.note_to_hz(pat[j % len(pat)])
            tone = S.saw(f, 0.22, n_harm=12) * S.adsr(0.22, a=0.005, d=0.12, s=0.3, r=0.06)
            sig = S.resonant_lpf(tone, 300 + 900 * L['altitude'][min(idx, N - 1)], q=1.2)
            out = S.mix_at(out, sig, t, gain=0.85 * d)
        j += 1; t += eighth
    return S.reverb_st(S.as_stereo(out[:N]), decay=1.2, mix=0.14, seed=17)


# ---- LEAD — the joy, emerging at the breakthrough, urgent in the sustain ----
def lead(L):
    out = np.zeros(N)
    motif = [0, 2, 4, 3, 5, 4, 6, 7, 6, 4, 5, 7]
    t, j, step = 48.0, 0, SIX * 2
    while t < 162:
        idx = int(t * S.SR)
        e = L['effort'][min(idx, N - 1)]; a = L['altitude'][min(idx, N - 1)]; br = L['bright'][min(idx, N - 1)]
        deg = motif[j % len(motif)] + (3 if a > 0.75 else 0)
        f = LYD[deg % len(LYD)] * (2 if a > 0.8 else 1)
        sag = 1 - 0.03 * (1 - e)
        tone = (S.sine(f * sag, 0.32) + 0.4 * S.saw(f * sag, 0.32, n_harm=10)) * S.adsr(0.32, a=0.02, d=0.08, s=0.5, r=0.18)
        out = S.mix_at(out, tone * (0.55 + 0.45 * a), t, gain=0.5 * a * br)  # floats on altitude, not effort
        j += 1; t += step
    return S.reverb_st(S.as_stereo(out[:N]), decay=2.6, mix=0.42, seed=14)


# ---- VOID — the Jupiter sample, engineered ----
def void(L):
    base = S.load_audio('space_library/jupiter_ion_acoustic.mp3')
    mono = base.mean(1)
    abyss = lpf_st(S.loop_to(S.resample_speed(base, 0.35), N), 700)
    cloud = S.granular_cloud(mono, DUR, grain=0.12, density=22, pitch=0.5, pitch_jitter=4, pan_spread=0.85, seed=3)
    drone = lpf_st(S.spectral_drone(mono, DUR, seg=3.0, seed=5), 1400)
    v = (0.6 * S.as_stereo(abyss) + 0.7 * cloud[:N] + 0.5 * drone[:N]) * L['voidl'][:, None]
    return S.reverb_st(v, decay=5.5, mix=0.5, seed=15)


# ---- FLUTES — alien whole-tone piping at height ----
def flutes(L):
    st = np.zeros((N, 2))
    times = [90, 95, 100, 104, 110, 116, 122, 128, 134, 140, 147]
    for k, t in enumerate(times):
        f = WT[(k * 3 + 1) % len(WT)]
        vib = 1 + 0.01 * S.lfo(6.0, 2.2)
        sig = (S.sine(f * vib, 2.2) + 0.1 * S.sine(2 * f * vib, 2.2)) * S.adsr(2.2, a=0.3, d=0.2, s=0.6, r=0.5)
        pan = 0.7 * (1 if k % 2 else -1); ang = (pan + 1) * 0.25 * np.pi
        seg = np.stack([sig * np.cos(ang), sig * np.sin(ang)], axis=1)
        st = place_st(st, seg, t, gain=0.6 * L['flute'][min(int(t * S.SR), N - 1)])
    return S.reverb_st(st, decay=6.5, mix=0.6, seed=16)


# ---- WIND — air rushing past, only when you GLIDE (hands still) ----
def wind(L):
    nz = S.noise(DUR, seed=44)
    w = lpf_st(S.as_stereo(nz), 1100)
    tt = np.arange(N) / S.SR
    region = np.clip((tt - 48) / 4, 0, 1) * np.clip((152 - tt) / 8, 0, 1)   # only in the sustain
    glide = np.clip(1 - L['effort'], 0, 1) * region                          # loud when NOT flapping
    w = w * (glide[:, None] * 0.6)
    return S.reverb_st(w, decay=2.8, mix=0.45, seed=45)


# ---------------------------------------------------------------------------
if __name__ == '__main__':
    L = lanes()
    organs = {
        'tension': (tension(L), 0.60), 'clap': (clap(L), 0.60), 'riser': (riser(), 0.55),
        'pad': (pad(L), 0.70), 'bass': (bass(L), 0.72), 'lead': (lead(L), 0.60),
        'void': (void(L), 0.80), 'flutes': (flutes(L), 0.42), 'wind': (wind(L), 0.34),
    }
    mix = np.zeros((N, 2))
    for name, (sig, lvl) in organs.items():
        sig = S.as_stereo(sig)[:N]
        if len(sig) < N:
            sig = np.vstack([sig, np.zeros((N - len(sig), 2))])
        S.write_wav(f'ic_{name}.wav', sig)
        mix += lvl * sig
        print(f'  ic_{name}.wav')
    # the BREATH before the breakthrough: a quick master dip then surge
    gate = S.curve([(0, 1), (43.5, 1), (44.4, 0.16), (45.8, 0.2), (47.3, 1.1), (52, 1)], DUR)
    mix *= gate[:, None]
    mix = S.soft_clip(mix * 0.6, drive=1.0)
    S.write_wav('icarus_mix.wav', mix)
    print('  icarus_mix.wav', round(DUR, 1), 's (stereo)')

    vd = os.path.join('versions', VERSION); os.makedirs(vd, exist_ok=True)
    for f in ['icarus_mix.wav'] + [f'ic_{n}.wav' for n in organs] + ['icarus.py', 'synth.py']:
        if os.path.exists(f):
            shutil.copy(f, vd)
    print('  archived ->', vd)

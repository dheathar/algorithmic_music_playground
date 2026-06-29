"""
dream.py — "The Black Theater"  (v002: stereo, six organs, 3 movements)

A childhood dream as a piece of music. Three movements follow the audience's
EYES: I kind -> II adoration & envy -> III the eyes close.

Now in STEREO, with every organ given volume AND a place in a 3D field:

  organ      role                       dimension            field
  --------   ------------------------   ------------------   ----------------
  PEDAL      the stage floor / ground   bottom               center, low
  PULSE      the child's heartbeat      time (a pulse)       center, near
  CHILD      the child, a wind          the self             center, near
  AUDIENCE   the eyes, the carpet       all around you       WIDE, moving
  GLINT      the line cast upward       top                  high, wide, far
  FISHING    soundings into the void    distance             roaming, far

Key: A Phrygian.  Tempo: 60 BPM.  Length: 96 s.
"""
import os
import shutil
import numpy as np
import synth as S

VERSION = 'v003'
DUR = 96.0
N = int(DUR * S.SR)


def place(canvas, st_sig, at, gain=1.0):
    """Mix a stereo signal into a stereo canvas at time `at` seconds."""
    start = int(at * S.SR)
    end = min(start + len(st_sig), len(canvas))
    canvas[start:end] += gain * st_sig[:end - start]
    return canvas


# ---------------------------------------------------------------------------
# Automation lanes (shared)
# ---------------------------------------------------------------------------
def lanes():
    return dict(
        amp=S.curve([(0, 0.0), (4, 0.5), (30, 0.58), (50, 0.95), (58, 1.0),
                     (66, 0.82), (80, 0.32), (92, 0.04), (96, 0.0)], DUR),
        cut=S.curve([(0, 430), (30, 560), (50, 1020), (58, 1150),
                     (66, 800), (80, 360), (96, 150)], DUR),
        warm=S.curve([(0, 0.0), (6, 0.5), (28, 0.45), (40, 0.08), (96, 0.0)], DUR),
        adore=S.curve([(0, 0), (30, 0.0), (44, 0.5), (56, 0.72),
                       (66, 0.4), (78, 0.05), (96, 0)], DUR),
        envy=S.curve([(0, 0), (40, 0.0), (52, 0.32), (62, 0.55),
                      (68, 0.28), (80, 0.04), (96, 0)], DUR),
        murm=S.curve([(0, 0.0), (6, 0.12), (50, 0.12), (70, 0.05), (86, 0.0), (96, 0)], DUR),
    )


def stack_saws(notes, n_harm, det=0.004):
    out = np.zeros(N)
    for note in notes:
        f = S.note_to_hz(note)
        out += 0.5 * (S.saw(f * (1 - det), DUR, n_harm=n_harm)
                      + S.saw(f * (1 + det), DUR, n_harm=n_harm))
    return out / max(1, len(notes))


# ---------------------------------------------------------------------------
# AUDIENCE — the eyes. Rendered twice (decorrelated) for natural width; the
# image moves; width collapses to mono as the eyes close.
# ---------------------------------------------------------------------------
def audience_dry(seed):
    L = lanes()
    out = np.zeros(N)
    for note, g in {'A1': 1.0, 'E2': 0.6, 'A2': 0.5}.items():
        d = S.drift(DUR, amount=0.004, rate=0.15, seed=(abs(hash(note)) + seed) % 9991)
        out += g * S.sine(S.note_to_hz(note) * d, DUR)
    out /= 2.1
    out += L['warm'] * 0.5 * (S.sine(S.note_to_hz('C3'), DUR) + 0.5 * S.sine(S.note_to_hz('E3'), DUR))
    out += L['adore'] * stack_saws(['E3', 'A3', 'C4', 'E4'], n_harm=20)
    out += L['envy'] * stack_saws(['A#2', 'A#3', 'F3'], n_harm=16, det=0.006)
    out += L['murm'] * S.resonant_lpf(S.noise(DUR, seed=7 + seed), cutoff=260, q=0.6)
    out = S.resonant_lpf(out, L['cut'], q=1.0)
    breath = 0.72 + 0.28 * (0.5 + 0.5 * S.lfo(0.06, DUR))
    return out * breath * L['amp']


def audience():
    Lc = audience_dry(0)
    Rc = audience_dry(137)
    st = np.stack([Lc, Rc], axis=1)
    width = S.curve([(0, 1.1), (50, 1.3), (66, 1.05), (80, 0.4), (96, 0.0)], DUR)
    st = S.stereo_width(st, width)
    st = S.autopan(st, rate=0.025, depth=0.18)           # the eyes drift around
    # adoration shimmer halo (movement II)
    mid = 0.5 * (Lc + Rc)
    halo = S.shimmer_halo(mid) * lanes()['adore']
    st[:, 0] += 0.45 * halo
    st[:, 1] += 0.50 * halo
    return S.reverb_st(st, decay=4.8, mix=0.42, seed=3)


# ---------------------------------------------------------------------------
# CHILD — a wind, dead center and close (intimate); stereo only in its tail.
# ---------------------------------------------------------------------------
def wind_note(freq, dur, seed=0):
    n = int(dur * S.SR)
    t = np.arange(n) / S.SR
    vib = 1.0 + (0.010 * np.clip((t - 0.4) / 0.8, 0, 1)) * np.sin(2 * np.pi * 5.0 * t)
    tone = S.sine(freq * vib, dur) + 0.14 * S.sine(3 * freq * vib, dur)
    nz = S.noise(dur, seed=seed)
    breath = S.resonant_bpf(nz, freq * 2.5, q=5) * 1.4
    chiff = S.adsr(dur, a=0.05, d=0.35, s=0.06, r=0.2)
    air = S.resonant_lpf(nz, 2200, q=0.7) * 0.12
    env = S.adsr(dur, a=0.4, d=0.25, s=0.75, r=0.7)
    return (tone * env) + (breath * chiff * 0.5) + (air * env)


def child():
    out = np.zeros(N)
    phrases = [
        (8, 'E4', 1.4), (9.6, 'D4', 1.2), (11, 'C4', 2.2),
        (16, 'E4', 1.2), (17.4, 'G4', 1.0), (18.6, 'A4', 2.8),
        (34, 'A4', 1.1), (35.3, 'C5', 1.1), (36.8, 'E5', 1.8),
        (40, 'D5', 1.0), (41.1, 'C5', 1.0), (42.3, 'A4', 2.2),
        (50, 'F4', 1.1), (51.3, 'A4', 1.0), (52.5, 'A#4', 1.6), (56, 'E5', 2.6),
        (72, 'C4', 2.4), (75, 'A3', 2.2), (78, 'E3', 3.0), (84, 'A3', 4.5),
    ]
    for i, (t, note, d) in enumerate(phrases):
        g = 0.5 if t < 66 else 0.42
        out = S.mix_at(out, wind_note(S.note_to_hz(note), d, seed=i + 1), t, gain=g)
    return S.reverb_st(out[:N], decay=3.0, mix=0.36, seed=20)   # center dry, stereo tail


# ---------------------------------------------------------------------------
# FISHING — soundings, roaming and rippling into the distance.
# ---------------------------------------------------------------------------
def ping(freq, dur=4.0):
    n = int(dur * S.SR)
    t = np.arange(n) / S.SR
    gl = freq * (1.0 - 0.03 * np.clip(t / 1.0, 0, 1))
    tone = S.sine(gl, dur) + 0.25 * S.sine(2.005 * gl, dur) + 0.08 * S.sine(3 * gl, dur)
    amp = S.adsr(dur, a=0.012, d=2.5, s=0.0, r=1.5)
    return S.resonant_lpf(tone * amp, 1200, q=0.8)


def fishing():
    out = np.zeros(N)
    casts = [(5, 'A3', 4), (22, 'C4', 4), (38, 'E4', 4),
             (46, 'A4', 4), (60, 'A#4', 4.5), (82, 'A3', 8)]
    for t, note, d in casts:
        out = S.mix_at(out, ping(S.note_to_hz(note), d), t, gain=0.7)
    st = S.pingpong(out[:N], time=1.5, feedback=0.45, mix=0.5)   # tempo-synced ripples
    st = S.autopan(st, rate=0.02, depth=0.45)                    # the line roams
    return S.reverb_st(st, decay=6.0, mix=0.55, seed=40)


# ---------------------------------------------------------------------------
# PEDAL — the stage floor. A deep drawbar-organ tone: the ground / bottom.
# ---------------------------------------------------------------------------
def pedal():
    base = S.note_to_hz('A1')
    out = np.zeros(N)
    for r, g in [(1, 1.0), (2, 0.6), (3, 0.4), (4, 0.22), (6, 0.1)]:   # drawbars
        d = S.drift(DUR, amount=0.003, rate=0.1, seed=r * 13)
        out += g * S.sine(base * r * d, DUR)
    out /= 2.3
    out = S.resonant_lpf(out, 600, q=0.8)
    amp = S.curve([(0, 0.0), (6, 0.5), (30, 0.55), (52, 0.8), (58, 0.85),
                   (66, 0.6), (82, 0.2), (96, 0.0)], DUR)
    return S.reverb_st(S.pan(out * amp, 0.0), decay=3.2, mix=0.22, seed=60)


# ---------------------------------------------------------------------------
# PULSE — the child's heartbeat: a soft sub thump. The thread of TIME.
# Present when alone (I, III); faint and quicker amid the crowd (II); slows
# and fades at the end.
# ---------------------------------------------------------------------------
def thump(f0=72, dur=0.5):
    n = int(dur * S.SR)
    t = np.arange(n) / S.SR
    f = f0 * (1.0 - 0.55 * np.clip(t / 0.08, 0, 1))     # quick downward pitch
    return S.sine(f, dur) * np.exp(-t / 0.09)


def pulse():
    out = np.zeros(N)
    beats = []
    tt = 5.0                                            # I — calm lub-dub
    while tt < 28:
        beats += [(tt, 1.0), (tt + 0.32, 0.6)]
        tt += 1.7
    tt = 34.0                                           # II — faint, quicker
    while tt < 62:
        beats.append((tt, 0.35))
        tt += 1.0
    tt, step = 68.0, 1.8                                # III — slowing, dying
    while tt < 92:
        fade = max(0.15, (92 - tt) / 24)
        beats += [(tt, 0.7 * fade), (tt + 0.34, 0.4 * fade)]
        tt += step
        step += 0.12
    for t, g in beats:
        out = S.mix_at(out, thump(), t, gain=g)
    out = S.resonant_lpf(out[:N], 200, q=0.8)
    return S.reverb_st(out, decay=1.8, mix=0.16, seed=80)   # close, intimate


# ---------------------------------------------------------------------------
# GLINT — the line cast upward: a high, glassy thread. The TOP dimension.
# Mostly in movement II (the line taut with hope), wide and far.
# ---------------------------------------------------------------------------
def glint_note(freq, dur):
    vib = 1.0 + 0.007 * S.lfo(4.2, dur)
    tone = S.sine(freq * vib, dur) + 0.3 * S.sine(1.5 * freq * vib, dur)
    return tone * S.adsr(dur, a=1.3, d=0.6, s=0.7, r=1.8)


def glint():
    st = np.zeros((N, 2))
    notes = [(20, 'E5', 6, 0.0, 0.5), (30, 'A5', 7, -0.6, 0.7),
             (40, 'E6', 8, 0.6, 0.8), (50, 'A5', 8, -0.4, 0.7),
             (58, 'B5', 7, 0.5, 0.6), (74, 'E5', 8, 0.0, 0.4)]
    for t, note, d, p, g in notes:
        st = place(st, S.pan(glint_note(S.note_to_hz(note), d), p), t, gain=g)
    return S.reverb_st(st, decay=7.0, mix=0.6, seed=90)        # high and far


# ---------------------------------------------------------------------------
# v003 organs — born from the "Watched & the crowd" dreams (DreamBank).
# ---------------------------------------------------------------------------

# VEIL (dream `bosnak`: two spirits can't both be fully real at once) — two low
# drones a Phrygian ♭2 apart whose amplitudes are ANTI-CORRELATED: as one swells
# the other must thin. Ambient through I & II; gone before the eyes close (III).
def veil():
    a, b = S.note_to_hz('A2'), S.note_to_hz('A#2')          # the ♭2 grind
    lf = 0.5 + 0.5 * S.lfo(0.05, DUR)                        # 0..1 slow breath
    sa = S.resonant_lpf(S.additive(a * S.drift(DUR, 0.003, 0.08, 11), DUR, [1, 0.4, 0.2, 0.1]), 420, q=0.9)
    sb = S.resonant_lpf(S.additive(b * S.drift(DUR, 0.003, 0.08, 23), DUR, [1, 0.4, 0.2, 0.1]), 420, q=0.9)
    pres = S.curve([(0, 0), (8, 0.45), (40, 0.62), (60, 0.55),
                    (66, 0.22), (72, 0.0), (96, 0.0)], DUR)  # gone in movement III
    st = S.pan(sa * lf, -0.4) + S.pan(sb * (1 - lf), 0.4)    # anti-correlated pair
    st = st * pres[:, None]
    return S.reverb_st(st, decay=4.0, mix=0.4, seed=33)


# STUMBLE (dream `b2`: forgotten lines, exposure) — the child falters: the pitch
# dips to a wrong note, a breath is caught (a gap), then it corrects. In II, where
# the child strains under the gaze.
def falter_note(freq, dur=2.2):
    n = int(dur * S.SR); t = np.arange(n) / S.SR
    bend = np.interp(t, [0, 0.5, 0.62, 0.95, 1.05, dur], [1, 1, 0.94, 0.94, 1.0, 1.0])
    tone = S.sine(freq * bend, dur) + 0.14 * S.sine(3 * freq * bend, dur)
    amp = S.adsr(dur, a=0.15, d=0.2, s=0.7, r=0.6)[:n]
    catch = np.interp(t, [0, 0.6, 0.7, 0.86, 0.96, dur], [1, 1, 0.12, 0.18, 1, 1])  # caught breath
    return tone * amp * catch


def stumble():
    out = np.zeros(N)
    for t, note in [(52.5, 'A4'), (55.6, 'E5')]:
        out = S.mix_at(out, falter_note(S.note_to_hz(note)), t, gain=0.5)
    return S.reverb_st(S.as_stereo(out[:N]), decay=3.0, mix=0.34, seed=55)


# MIRROR (dream `b`: an imitative dance on stage) — the child's phrase answered by
# its own INVERSION (contrary motion around A4), panned opposite: call left, the
# mirror-self right. The hinge, just before the eyes close.
def mirror():
    center = S.note_to_hz('A4')
    phrase = ['A4', 'A#4', 'C5', 'A#4', 'A4']               # with the ♭2 color
    t0, step = 59.0, 0.85
    call, ans = np.zeros(N), np.zeros(N)
    for i, note in enumerate(phrase):
        call = S.mix_at(call, wind_note(S.note_to_hz(note), 1.1, seed=50 + i), t0 + i * step, gain=0.5)
    t1 = t0 + 0.45                                           # the answer follows close (a canon)
    for i, note in enumerate(phrase):
        fi = center * center / S.note_to_hz(note)            # inversion around A4
        ans = S.mix_at(ans, wind_note(fi, 1.1, seed=70 + i), t1 + i * step, gain=0.42)
    st = np.stack([call[:N], ans[:N]], axis=1)              # call left, mirror right
    return S.reverb_st(st, decay=4.2, mix=0.45, seed=44)


# ---------------------------------------------------------------------------
# Render, mix (stereo), and ARCHIVE this edition.
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    organs = {
        'audience': (audience(), 0.90),
        'child':    (child(),    0.70),
        'fishing':  (fishing(),  0.60),
        'pedal':    (pedal(),    0.50),
        'pulse':    (pulse(),    0.40),
        'glint':    (glint(),    0.30),
        'veil':     (veil(),     0.32),   # v003 — two presences, anti-correlated (I & II)
        'stumble':  (stumble(),  0.42),   # v003 — the child falters under the gaze (II)
        'mirror':   (mirror(),   0.40),   # v003 — the child answered by its inversion (the hinge)
    }
    mix = np.zeros((N, 2))
    for name, (sig, lvl) in organs.items():
        S.write_wav(f'stem_{name}.wav', sig)
        mix += lvl * sig[:N]
        print(f'  stem_{name}.wav  (stereo)')
    mix = S.soft_clip(mix * 0.7, drive=1.0)
    S.write_wav('dream_mix.wav', mix)
    print('  dream_mix.wav', round(DUR, 1), 's  (stereo)')

    # keep this edition
    vd = os.path.join('versions', VERSION)
    os.makedirs(vd, exist_ok=True)
    for f in ['dream_mix.wav'] + [f'stem_{n}.wav' for n in organs] + ['dream.py', 'synth.py']:
        if os.path.exists(f):
            shutil.copy(f, vd)
    print('  archived ->', vd)

"""
dream.py — "The Black Theater"  (three movements)

A childhood dream as a piece of music, in three movements driven by how the
audience's EYES change over a life:

  I.   KIND EYES (0–30s)          warm, innocent, safe
  II.  ADORATION & ENVY (30–66s)  dazzling admiration + a jealous, dissonant undercurrent
  III. THE EYES CLOSE (66–96s)    voices fall away, the room darkens, solitude, fading

The audience drone is the protagonist: it warms, swells, splits into adoration
and envy, then closes its eyes and turns away. Over it, the CHILD (a wind) and
the FISHING (soundings into the void) live out the same arc.

Key: A Phrygian.  Tempo: 60 BPM (1 bar = 4 s).  Length: 96 s (24 bars).
"""
import numpy as np
import synth as S

DUR = 96.0
N = int(DUR * S.SR)


# ---------------------------------------------------------------------------
# Automation lanes — how each parameter moves across the three movements.
# (t_sec, value) breakpoints; the rest is interpolated.
# ---------------------------------------------------------------------------
def lanes():
    return dict(
        # master amplitude: from nothing -> swell to the peak -> fade to silence
        amp=S.curve([(0, 0.0), (4, 0.5), (30, 0.58), (50, 0.95), (58, 1.0),
                     (66, 0.82), (80, 0.32), (92, 0.04), (96, 0.0)], DUR),
        # brightness / filter: warm -> open (grandeur) -> closes (turning away)
        cut=S.curve([(0, 430), (30, 560), (50, 1020), (58, 1150),
                     (66, 800), (80, 360), (96, 150)], DUR),
        # kindness: a gentle warm third, present in childhood, gone by mastery
        warm=S.curve([(0, 0.0), (6, 0.5), (28, 0.45), (40, 0.08), (96, 0.0)], DUR),
        # adoration: a bright high shimmer swelling through movement II
        adore=S.curve([(0, 0), (30, 0.0), (44, 0.5), (56, 0.72),
                       (66, 0.4), (78, 0.05), (96, 0)], DUR),
        # envy: a dissonant Bb cluster, beating, growing late in movement II
        envy=S.curve([(0, 0), (40, 0.0), (52, 0.32), (62, 0.55),
                      (68, 0.28), (80, 0.04), (96, 0)], DUR),
        # crowd murmur: present, then the room empties
        murm=S.curve([(0, 0.0), (6, 0.12), (50, 0.12), (70, 0.05), (86, 0.0), (96, 0)], DUR),
    )


# ---------------------------------------------------------------------------
# AUDIENCE — the eyes. The protagonist drone that lives the whole arc.
# ---------------------------------------------------------------------------
def stack_saws(notes, n_harm, det=0.004):
    out = np.zeros(N)
    for note in notes:
        f = S.note_to_hz(note)
        out += 0.5 * (S.saw(f * (1 - det), DUR, n_harm=n_harm)
                      + S.saw(f * (1 + det), DUR, n_harm=n_harm))
    return out / max(1, len(notes))


def audience():
    L = lanes()
    out = np.zeros(N)
    # core open fifth (no third = "black"), always present
    for note, g in {'A1': 1.0, 'E2': 0.6, 'A2': 0.5}.items():
        d = S.drift(DUR, amount=0.004, rate=0.15, seed=abs(hash(note)) % 999)
        out += g * S.sine(S.note_to_hz(note) * d, DUR)
    out /= 2.1
    # kindness: warm consonant third (C) + fifth color, faded by movement II
    warm_layer = S.sine(S.note_to_hz('C3'), DUR) + 0.5 * S.sine(S.note_to_hz('E3'), DUR)
    out += L['warm'] * 0.5 * warm_layer
    # adoration: bright, lush, higher shimmer
    out += L['adore'] * stack_saws(['E3', 'A3', 'C4', 'E4'], n_harm=20)
    # envy: dissonant Bb cluster grinding against A (the beating = jealousy)
    out += L['envy'] * stack_saws(['A#2', 'A#3', 'F3'], n_harm=16, det=0.006)
    # crowd murmur
    out += L['murm'] * S.resonant_lpf(S.noise(DUR, seed=7), cutoff=260, q=0.6)
    # global dark filter, swept across the movements
    out = S.resonant_lpf(out, L['cut'], q=1.0)
    # breathing + the master amplitude arc
    breath = 0.72 + 0.28 * (0.5 + 0.5 * S.lfo(0.06, DUR))
    out *= breath * L['amp']
    out = S.phaser(out, rate=0.07, depth=0.55, stages=6, feedback=0.25, mix=0.35)
    out = S.reverb(out, decay=4.5, mix=0.42)
    return S.soft_clip(out, drive=1.05)


# ---------------------------------------------------------------------------
# CHILD — a wind. Hollow flute tone + breath chiff; vibrato fades in.
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
        # I — kind: simple, tender, mid-register, settling warm
        (8, 'E4', 1.4), (9.6, 'D4', 1.2), (11, 'C4', 2.2),
        (16, 'E4', 1.2), (17.4, 'G4', 1.0), (18.6, 'A4', 2.8),
        # II — adoration & envy: soaring, higher, reaching, with a strained Bb
        (34, 'A4', 1.1), (35.3, 'C5', 1.1), (36.8, 'E5', 1.8),
        (40, 'D5', 1.0), (41.1, 'C5', 1.0), (42.3, 'A4', 2.2),
        (50, 'F4', 1.1), (51.3, 'A4', 1.0), (52.5, 'A#4', 1.6), (56, 'E5', 2.6),
        # III — closing: low, slow, resigned, a final fragile breath
        (72, 'C4', 2.4), (75, 'A3', 2.2), (78, 'E3', 3.0), (84, 'A3', 4.5),
    ]
    for i, (t, note, d) in enumerate(phrases):
        g = 0.5 if t < 66 else 0.42   # softer in the closing
        out = S.mix_at(out, wind_note(S.note_to_hz(note), d, seed=i + 1), t, gain=g)
    out = out[:N]
    return S.reverb(out, decay=3.2, mix=0.4)


# ---------------------------------------------------------------------------
# FISHING — soundings cast into the void; deep, round, dropping in pitch.
# ---------------------------------------------------------------------------
def ping(freq, dur=4.0):
    n = int(dur * S.SR)
    t = np.arange(n) / S.SR
    gl = freq * (1.0 - 0.03 * np.clip(t / 1.0, 0, 1))   # the downward "sounding"
    tone = S.sine(gl, dur) + 0.25 * S.sine(2.005 * gl, dur) + 0.08 * S.sine(3 * gl, dur)
    amp = S.adsr(dur, a=0.012, d=2.5, s=0.0, r=1.5)
    return S.resonant_lpf(tone * amp, 1200, q=0.8)


def fishing():
    out = np.zeros(N)
    casts = [
        (5, 'A3', 4), (22, 'C4', 4),            # I — hopeful
        (38, 'E4', 4), (46, 'A4', 4), (60, 'A#4', 4.5),  # II — bolder, tension
        (82, 'A3', 8),                          # III — final, into total void
    ]
    for t, note, d in casts:
        out = S.mix_at(out, ping(S.note_to_hz(note), d), t, gain=0.7)
    out = out[:N]
    out = S.tape_delay(out, time=1.5, feedback=0.28, mix=0.3, wobble=0.002)
    return S.reverb(out, decay=6.0, mix=0.55)


# ---------------------------------------------------------------------------
if __name__ == '__main__':
    stems = {'audience': audience(), 'child': child(), 'fishing': fishing()}
    levels = {'audience': 0.95, 'child': 0.7, 'fishing': 0.62}
    mix = np.zeros(N)
    for name, sig in stems.items():
        sig = sig[:N]
        S.write_wav(f'stem_{name}.wav', sig)
        mix[:len(sig)] += levels[name] * sig
        print(f'  stem_{name}.wav')
    mix = S.soft_clip(mix * 0.8, drive=1.0)
    S.write_wav('dream_mix.wav', mix)
    print('  dream_mix.wav', round(DUR, 1), 's')

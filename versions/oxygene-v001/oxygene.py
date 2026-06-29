"""
oxygene.py — "Homage to Oxygène"

A study in the Jarre signature, built in the real engine (not the toy Lab):
  PADS   lush detuned strings through a phaser (the Eminent-310 + phaser sound)
  ARP    a bubbling 16th-note arpeggio (the hypnotic motion)
  BASS   a pulsing octave bass
  LEAD   a SINGING lead with portamento (pitch glides between notes) — the soul
  PERC   a soft electronic kick / snare / hat

Key: A minor.  Tempo: 104 BPM.  An homage — the spirit, from scratch.
"""
import os
import shutil
import numpy as np
import synth as S

VERSION = 'oxygene-v001'
TEMPO = 104
BEAT = 60 / TEMPO
BAR = 4 * BEAT
SIX = BEAT / 4
BARS = 40
DUR = BARS * BAR
N = int(DUR * S.SR)

# progression: (bass root, chord notes) — Am · F · C · G
PROG = [
    ('A2', ['A3', 'C4', 'E4']),
    ('F2', ['F3', 'A3', 'C4']),
    ('C3', ['C4', 'E4', 'G4']),
    ('G2', ['G3', 'B3', 'D4']),
]


def st(x):
    return S.as_stereo(x)


def place(canvas, sig, at, gain=1.0):
    sig = st(sig)
    s = int(at * S.SR)
    e = min(s + len(sig), len(canvas))
    canvas[s:e] += gain * sig[:e - s]
    return canvas


# ---- PADS — detuned strings through a phaser ----
def pad_chord(notes, dur):
    out = np.zeros(int(dur * S.SR))
    for note in notes:
        f = S.note_to_hz(note)
        out += 0.5 * (S.saw(f * 0.995, dur, n_harm=12) + S.saw(f * 1.005, dur, n_harm=12))
    env = S.adsr(dur, a=0.4, d=0.2, s=0.85, r=0.4)
    return (out / len(notes)) * env


def pads():
    track = np.zeros(N)
    for b in range(BARS):
        _, chord = PROG[b % 4]
        track = S.mix_at(track, pad_chord(chord, BAR * 1.02), b * BAR, gain=0.5)
    track = S.resonant_lpf(track[:N], 2200, q=0.8)
    track = S.phaser(track, rate=0.16, depth=0.8, stages=6, feedback=0.4, mix=0.55)
    return S.reverb_st(st(track), decay=3.0, mix=0.4, seed=2)


# ---- ARP — bubbling 16th-note arpeggio ----
def arp():
    track = np.zeros(N)
    for b in range(BARS):
        if b < 4:
            continue
        _, chord = PROG[b % 4]
        seq = [chord[0], chord[1], chord[2], chord[1]]  # up-down arpeggio
        seq = [S.note_to_hz(n) for n in seq] * 4         # 16 sixteenths per bar
        for i, f in enumerate(seq):
            t = b * BAR + i * SIX
            note = S.square(f * 2, SIX * 1.4, n_harm=10) * S.adsr(SIX * 1.4, a=0.003, d=0.06, s=0.2, r=0.04)
            note = S.resonant_lpf(note, 2600, q=3.5)
            pan = 0.3 * (1 if i % 2 else -1)
            ang = (pan + 1) * 0.25 * np.pi
            track_seg = note
            track = S.mix_at(track, track_seg, t, gain=0.32)
    return S.reverb_st(st(track[:N]), decay=1.6, mix=0.3, seed=3)


# ---- BASS — pulsing octave bass ----
def bass():
    track = np.zeros(N)
    for b in range(BARS):
        if b < 4:
            continue
        root, _ = PROG[b % 4]
        f = S.note_to_hz(root)
        for beat in range(4):
            for half in range(2):
                t = b * BAR + beat * BEAT + half * (BEAT / 2)
                ff = f * (2 if half else 1)
                note = S.saw(ff, BEAT / 2 * 0.9, n_harm=10) * S.adsr(BEAT / 2 * 0.9, a=0.005, d=0.1, s=0.4, r=0.05)
                note = S.resonant_lpf(note, 700, q=1.4)
                track = S.mix_at(track, note, t, gain=0.5)
    return st(track[:N])


# ---- LEAD — singing portamento melody ----
def glide_lead(seq, glide=0.05, start='E4'):
    fparts, aparts = [], []
    prev = S.note_to_hz(start)
    for note, beats in seq:
        n = int(beats * BEAT * S.SR)
        f = prev if note is None else S.note_to_hz(note)
        a = np.zeros(n) if note is None else S.adsr(beats * BEAT, a=0.03, d=0.05, s=0.9, r=0.06)
        gl = min(int(glide * S.SR), n)
        seg = np.empty(n)
        if gl > 1:
            seg[:gl] = np.exp(np.linspace(np.log(prev), np.log(f), gl))
            seg[gl:] = f
        else:
            seg[:] = f
        fparts.append(seg)
        aparts.append(a)
        prev = f
    farr = np.concatenate(fparts)
    amp = np.concatenate(aparts)
    d = len(farr) / S.SR
    vib = 1 + 0.006 * S.lfo(5.5, d)
    tone = 0.6 * S.sine(farr * vib, d) + 0.4 * S.saw(farr * vib, d, n_harm=14)
    tone = S.resonant_lpf(tone, 3200, q=1.0)
    return tone * amp


def lead():
    # a flowing A-minor melody over Am F C G (8 bars), repeated
    phrase = [
        ('E4', 2), ('A4', 1), ('G4', 1),         # Am
        ('F4', 2), ('A4', 1), ('C5', 1),         # F
        ('E4', 2), ('G4', 1), ('E4', 1),         # C
        ('D4', 2), ('G4', 1), ('B4', 1),         # G
        ('C5', 2), ('B4', 1), ('A4', 1),         # Am
        ('A4', 2), ('C5', 1), ('A4', 1),         # F
        ('G4', 3), ('E4', 1),                    # C
        ('D4', 2), (None, 2),                    # G + rest
    ]
    sig = glide_lead(phrase * 2)
    track = np.zeros((N, 2))
    track = place(track, st(sig), 12 * BAR, gain=0.5)   # lead enters at bar 12
    return S.reverb_st(track[:N], decay=2.8, mix=0.4, seed=4)


# ---- PERC — soft electronic kit ----
def perc():
    L = np.zeros(N)
    R = np.zeros(N)
    def kick(t):
        d = 0.3
        n = int(d * S.SR); tt = np.arange(n) / S.SR
        f = 110 * (1 - 0.6 * np.clip(tt / 0.05, 0, 1))
        return S.sine(f, d) * np.exp(-tt / 0.12)
    def snare(t):
        d = 0.2; tt = np.arange(int(d * S.SR)) / S.SR
        return (S.resonant_bpf(S.noise(d, seed=int(t * 10) % 99), 1800, q=0.8) + 0.3 * S.sine(190, d)) * np.exp(-tt / 0.07)
    def hat(t):
        d = 0.05; tt = np.arange(int(d * S.SR)) / S.SR
        return S.resonant_bpf(S.noise(d, seed=int(t * 7) % 99), 9000, q=0.9) * np.exp(-tt / 0.018)
    for b in range(BARS):
        if b < 8:
            continue
        for beat in range(4):
            t = b * BAR + beat * BEAT
            k = kick(t)
            L = S.mix_at(L, k, t, gain=0.7); R = S.mix_at(R, k, t, gain=0.7)
            if beat in (1, 3):
                s = snare(t)
                L = S.mix_at(L, s, t, gain=0.35); R = S.mix_at(R, s, t, gain=0.35)
            for half in range(2):
                th = t + half * (BEAT / 2)
                h = hat(th)
                L = S.mix_at(L, h, th, gain=0.18); R = S.mix_at(R, h, th, gain=0.14)
    return S.reverb_st(np.stack([L[:N], R[:N]], axis=1), decay=1.0, mix=0.12, seed=5)


# ---------------------------------------------------------------------------
if __name__ == '__main__':
    organs = {
        'pads': (pads(), 0.7), 'arp': (arp(), 0.6), 'bass': (bass(), 0.7),
        'lead': (lead(), 0.62), 'perc': (perc(), 0.55),
    }
    mix = np.zeros((N, 2))
    for name, (sig, lvl) in organs.items():
        sig = st(sig)[:N]
        if len(sig) < N:
            sig = np.vstack([sig, np.zeros((N - len(sig), 2))])
        S.write_wav(f'ox_{name}.wav', sig)
        mix += lvl * sig
        print(f'  ox_{name}.wav')
    mix = S.soft_clip(mix * 0.62, drive=1.0)
    S.write_wav('oxygene_mix.wav', mix)
    print('  oxygene_mix.wav', round(DUR, 1), 's (stereo)')
    vd = os.path.join('versions', VERSION); os.makedirs(vd, exist_ok=True)
    for f in ['oxygene_mix.wav'] + [f'ox_{n}.wav' for n in organs] + ['oxygene.py', 'synth.py']:
        if os.path.exists(f):
            shutil.copy(f, vd)
    print('  archived ->', vd)

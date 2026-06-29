"""
phoenix.py — "Coin-Up"  (after Romance Anónimo, in the spirit of Phoenix, 1980)

An early-80s arcade chiptune from first principles. Phoenix's hardware was an
SN76496-style PSG (square/pulse tones + a noise channel) playing the public-domain
"Romance Anónimo" (Spanish Romance) and Für Elise. We voice the Romance ourselves
on pulse waves with PWM, an arpeggiated accompaniment, and the arcade SFX arsenal:
laser zaps, noise explosions, a UFO swoop, and a coin jingle.

No samples, no ROM audio — synthesized. Public-domain theme.
Key: E minor → E major.  3/4.
"""
import os
import shutil
import numpy as np
import synth as S

VERSION = 'v001'
TEMPO = 96
BEAT = 60 / TEMPO
BAR = 3 * BEAT                      # 3/4


# ---------------------------------------------------------------------------
# PSG voices: band-limited pulse with variable width (PWM) + noise SFX
# ---------------------------------------------------------------------------
def pulse(freq, dur, duty=0.5):
    """Band-limited pulse wave via its Fourier series — duty sets the timbre
    (0.5 = square/hollow, 0.25/0.125 = brighter/nasal: the classic chip voices)."""
    nm = min(40, int(S.SR / 2 / max(1.0, float(np.mean(np.atleast_1d(freq))))))
    amps = [(2.0 / (k * np.pi)) * np.sin(k * np.pi * duty) for k in range(1, nm + 1)]
    return S.additive(freq, dur, amps)


def lead_note(freq, dur, duty=0.5):
    n = int(dur * S.SR); t = np.arange(n) / S.SR
    vib = 1 + 0.006 * np.sin(2 * np.pi * 5.5 * t) * np.clip((t - 0.1) / 0.12, 0, 1)
    return pulse(freq * vib, dur, duty)[:n] * S.adsr(dur, a=0.006, d=0.06, s=0.8, r=0.06)[:n]


def arp_note(freq, dur, duty=0.5):
    n = int(dur * S.SR)
    return pulse(freq, dur, duty)[:n] * S.adsr(dur, a=0.002, d=0.05, s=0.2, r=0.02)[:n]


def bass_note(freq, dur):
    n = int(dur * S.SR)
    return pulse(freq, dur, 0.5)[:n] * S.adsr(dur, a=0.004, d=0.09, s=0.5, r=0.05)[:n]


# ---- SFX (the noise channel + tone sweeps) ----
def laser(seed=0):
    dur = 0.26; n = int(dur * S.SR); t = np.arange(n) / S.SR
    f = 200 + 900 * np.exp(-t / 0.06)
    return S.square(f, dur)[:n] * np.exp(-t / 0.08) * 0.5


def explosion(seed=0):
    dur = 0.55; n = int(dur * S.SR); t = np.arange(n) / S.SR
    nz = S.noise(dur, seed=seed)
    return S.resonant_lpf(nz, 200 + 1400 * np.exp(-t / 0.14), q=0.8)[:n] * np.exp(-t / 0.16) * 0.7


def ufo(dur=1.4):
    n = int(dur * S.SR); t = np.arange(n) / S.SR
    f = 440 * (1 + 0.35 * np.sin(2 * np.pi * 7 * t))
    return S.square(f, dur)[:n] * 0.3 * np.hanning(n)


def coin():
    out = np.zeros(int(0.3 * S.SR))
    out = S.mix_at(out, lead_note(S.note_to_hz('B5'), 0.07, 0.5), 0.0, gain=0.5)
    out = S.mix_at(out, lead_note(S.note_to_hz('E6'), 0.18, 0.5), 0.07, gain=0.5)
    return out


# ---------------------------------------------------------------------------
# the score — Romance Anónimo: (bass, [chord tones], melody top) per 3/4 bar
# ---------------------------------------------------------------------------
PART_A = [                                   # E minor
    ('E2', ['E3', 'G3', 'B3'], 'B4'),
    ('B1', ['D#3', 'F#3', 'B3'], 'A4'),      # B7
    ('E2', ['E3', 'G3', 'B3'], 'G4'),
    ('E2', ['E3', 'G3', 'B3'], 'E4'),
    ('A2', ['A3', 'C4', 'E4'], 'C5'),        # Am
    ('E2', ['E3', 'G3', 'B3'], 'B4'),
    ('B1', ['D#3', 'F#3', 'A3'], 'A4'),      # B7
    ('E2', ['E3', 'G3', 'B3'], 'E4'),
]
PART_B = [                                   # E major
    ('E2', ['E3', 'G#3', 'B3'], 'B4'),
    ('E2', ['E3', 'G#3', 'B3'], 'G#4'),
    ('B1', ['D#3', 'F#3', 'B3'], 'F#4'),     # B7
    ('E2', ['E3', 'G#3', 'B3'], 'E4'),
    ('A2', ['A3', 'C#4', 'E4'], 'C#5'),      # A
    ('E2', ['E3', 'G#3', 'B3'], 'B4'),
    ('B1', ['D#3', 'F#3', 'A3'], 'A4'),      # B7
    ('E2', ['E3', 'G#3', 'B3'], 'E4'),
]
PROG = PART_A + PART_B + PART_A              # AABA-ish

DUR = len(PROG) * BAR + 3.0
N = int(DUR * S.SR)


def place(canvas, sig, at, gain=1.0):
    s = int(at * S.SR); e = min(s + len(sig), len(canvas))
    if e > s:
        canvas[s:e] += gain * sig[:e - s]
    return canvas


def main():
    lead = np.zeros(N)
    arp = np.zeros(N)
    bass = np.zeros(N)
    intro = 1.0                              # a beat of room after the coin

    for b, (broot, chord, mel) in enumerate(PROG):
        t0 = intro + b * BAR
        # melody — a sustained pulse lead with vibrato (the top voice)
        lead = place(lead, lead_note(S.note_to_hz(mel), BAR * 0.96, duty=0.5), t0, gain=0.5)
        # bass — root on the downbeat
        bass = place(bass, bass_note(S.note_to_hz(broot), BAR * 0.9), t0, gain=0.55)
        # arpeggio — 6 broken-chord eighths per bar (the Romance triplet feel)
        pat = [chord[0], chord[1], chord[2], chord[1], chord[2], chord[1]]
        step = BAR / 6
        for i, note in enumerate(pat):
            arp = place(arp, arp_note(S.note_to_hz(note), step * 1.1, duty=0.25),
                        t0 + i * step, gain=0.3)

    # SFX — sprinkle the arcade over the music (panned later)
    sfx = np.zeros(N)
    sfx = place(sfx, coin(), 0.05, gain=0.6)                          # insert coin
    for t in (intro + 4 * BAR, intro + 11 * BAR, intro + 19 * BAR):
        sfx = place(sfx, laser(), t, gain=0.5)
        sfx = place(sfx, laser(), t + 0.18, gain=0.4)
    sfx = place(sfx, ufo(), intro + 8 * BAR, gain=0.5)
    sfx = place(sfx, explosion(seed=3), intro + 8 * BAR + 1.4, gain=0.7)
    sfx = place(sfx, explosion(seed=9), intro + 16 * BAR, gain=0.7)

    # mix to stereo: lead center, arp slightly left, bass center, sfx wide right-ish
    mix = (S.pan(lead[:N], 0.0) + S.pan(arp[:N], -0.3) +
           S.pan(bass[:N], 0.0) + S.pan(sfx[:N], 0.25))
    mix = S.reverb_st(mix, decay=1.2, mix=0.12, seed=7)               # a small arcade room
    mix = S.soft_clip(mix * 0.8, drive=1.0)

    # stems for the per-organ visualizer
    for nm, ch, p in [('lead', lead, 0.0), ('arp', arp, -0.3), ('bass', bass, 0.0), ('sfx', sfx, 0.25)]:
        S.write_wav(f'ph_{nm}.wav', S.pan(ch[:N], p))
        print(f'  ph_{nm}.wav')
    S.write_wav('phoenix_mix.wav', mix)
    print('  phoenix_mix.wav', round(DUR, 1), 's')

    vd = os.path.join('versions', f'phoenix-{VERSION}')
    os.makedirs(vd, exist_ok=True)
    for f in ['phoenix_mix.wav', 'phoenix.py', 'synth.py']:
        if os.path.exists(f):
            shutil.copy(f, vd)
    print('  archived ->', vd)


if __name__ == '__main__':
    main()

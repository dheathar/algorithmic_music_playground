"""
phoenix.py — "Coin-Up"  (v002: cyberpunk — Romance Anónimo, gritty & alive)

After Phoenix (1980): the public-domain "Romance Anónimo" voiced on an SN76496-style
PSG (square/pulse + noise), but pushed toward cyberpunk — a bitcrushed, detuned
lead and sub bass, a driving drum kit, noise texture, and the arcade SFX arsenal,
including the EGG-BREAK sounds from Phoenix's hatching stage (a sharp crack, the
shell splitting, and a bird screech).

No samples, no ROM audio — synthesized. Public-domain theme.  E minor → E major, 3/4.
"""
import os
import shutil
import numpy as np
import synth as S

VERSION = 'v002'
TEMPO = 104
BEAT = 60 / TEMPO
BAR = 3 * BEAT                      # 3/4


def crush(x, bits=7):
    """Mono bit-reduction — the cyberpunk grit."""
    lv = 2 ** bits
    return np.round(x * lv) / lv


# ---------------------------------------------------------------------------
# PSG voices
# ---------------------------------------------------------------------------
def pulse(freq, dur, duty=0.5):
    nm = min(40, int(S.SR / 2 / max(1.0, float(np.mean(np.atleast_1d(freq))))))
    amps = [(2.0 / (k * np.pi)) * np.sin(k * np.pi * duty) for k in range(1, nm + 1)]
    return S.additive(freq, dur, amps)


def lead_note(freq, dur, duty=0.5):
    n = int(dur * S.SR); t = np.arange(n) / S.SR
    vib = 1 + 0.007 * np.sin(2 * np.pi * 5.5 * t) * np.clip((t - 0.1) / 0.12, 0, 1)
    a = pulse(freq * vib, dur, duty)[:n]
    b = pulse(freq * vib * 1.006, dur, duty)[:n]                  # detune = thickness
    env = S.adsr(dur, a=0.006, d=0.06, s=0.8, r=0.06)[:n]
    return crush((a + b) * 0.5 * env, bits=7)


def arp_note(freq, dur, duty=0.2):
    n = int(dur * S.SR)
    return crush(pulse(freq, dur, duty)[:n] * S.adsr(dur, a=0.002, d=0.05, s=0.2, r=0.02)[:n], bits=8)


def bass_note(freq, dur):
    n = int(dur * S.SR)
    sub = S.sine(freq / 2, dur)[:n] * 0.5
    p = pulse(freq, dur, 0.5)[:n]
    env = S.adsr(dur, a=0.004, d=0.06, s=0.45, r=0.03)[:n]
    return crush((p + sub) * env, bits=6)                        # heavy, gritty


# ---- drums (the noise channel becomes a kit) ----
def kick():
    dur = 0.24; n = int(dur * S.SR); t = np.arange(n) / S.SR
    return S.sine(130 * (1 - 0.7 * np.clip(t / 0.04, 0, 1)), dur)[:n] * np.exp(-t / 0.09)


def snare():
    dur = 0.18; n = int(dur * S.SR); t = np.arange(n) / S.SR
    return (S.resonant_bpf(S.noise(dur, seed=3), 1800, q=0.7)[:n] + 0.3 * S.sine(190, dur)[:n]) * np.exp(-t / 0.07) * 0.6


def hat(opn=False):
    dur = 0.16 if opn else 0.05; n = int(dur * S.SR); t = np.arange(n) / S.SR
    return S.resonant_hpf(S.noise(dur, seed=2), 7500, q=0.8)[:n] * np.exp(-t / (0.06 if opn else 0.018)) * 0.35


# ---- SFX ----
def laser():
    dur = 0.26; n = int(dur * S.SR); t = np.arange(n) / S.SR
    return S.square(200 + 900 * np.exp(-t / 0.06), dur)[:n] * np.exp(-t / 0.08) * 0.5


def explosion(seed=0):
    dur = 0.6; n = int(dur * S.SR); t = np.arange(n) / S.SR
    nz = S.resonant_lpf(S.noise(dur, seed=seed), 200 + 1400 * np.exp(-t / 0.14), q=0.8)[:n]
    return crush(nz * np.exp(-t / 0.17) * 0.8, bits=6)


def ufo(dur=1.4):
    n = int(dur * S.SR); t = np.arange(n) / S.SR
    return S.square(440 * (1 + 0.35 * np.sin(2 * np.pi * 7 * t)), dur)[:n] * 0.3 * np.hanning(n)


def egg_break(seed=0):
    """The egg cracking: a sharp transient crack + the shell splitting (a quick
    downward chirp) + a brittle rattle. Lightly crushed."""
    dur = 0.32; n = int(dur * S.SR); t = np.arange(n) / S.SR
    crack = S.resonant_hpf(S.noise(dur, seed=seed), 2600, q=0.8)[:n] * np.exp(-t / 0.012)
    shell = S.square(150 + 800 * np.exp(-t / 0.04), dur)[:n] * np.exp(-t / 0.05) * 0.5
    rattle = S.resonant_bpf(S.noise(dur, seed=seed + 1), 1900, q=2.0)[:n] * np.exp(-t / 0.09) * 0.4
    return crush(crack * 0.9 + shell + rattle, bits=6)


def screech():
    """The bird hatching — a quick rising, fluttering square chirp."""
    dur = 0.3; n = int(dur * S.SR); t = np.arange(n) / S.SR
    f = (400 + 1800 * np.clip(t / 0.12, 0, 1)) * (1 + 0.10 * np.sin(2 * np.pi * 30 * t))
    return S.square(f, dur)[:n] * np.exp(-t / 0.12) * 0.4


def coin():
    out = np.zeros(int(0.3 * S.SR))
    out = S.mix_at(out, lead_note(S.note_to_hz('B5'), 0.07, 0.5), 0.0, gain=0.5)
    out = S.mix_at(out, lead_note(S.note_to_hz('E6'), 0.18, 0.5), 0.07, gain=0.5)
    return out


# ---------------------------------------------------------------------------
PART_A = [
    ('E2', ['E3', 'G3', 'B3'], 'B4'), ('B1', ['D#3', 'F#3', 'B3'], 'A4'),
    ('E2', ['E3', 'G3', 'B3'], 'G4'), ('E2', ['E3', 'G3', 'B3'], 'E4'),
    ('A2', ['A3', 'C4', 'E4'], 'C5'), ('E2', ['E3', 'G3', 'B3'], 'B4'),
    ('B1', ['D#3', 'F#3', 'A3'], 'A4'), ('E2', ['E3', 'G3', 'B3'], 'E4'),
]
PART_B = [
    ('E2', ['E3', 'G#3', 'B3'], 'B4'), ('E2', ['E3', 'G#3', 'B3'], 'G#4'),
    ('B1', ['D#3', 'F#3', 'B3'], 'F#4'), ('E2', ['E3', 'G#3', 'B3'], 'E4'),
    ('A2', ['A3', 'C#4', 'E4'], 'C#5'), ('E2', ['E3', 'G#3', 'B3'], 'B4'),
    ('B1', ['D#3', 'F#3', 'A3'], 'A4'), ('E2', ['E3', 'G#3', 'B3'], 'E4'),
]
PROG = PART_A + PART_B + PART_A
DUR = len(PROG) * BAR + 3.0
N = int(DUR * S.SR)


def place(canvas, sig, at, gain=1.0):
    s = int(at * S.SR); e = min(s + len(sig), len(canvas))
    if e > s:
        canvas[s:e] += gain * sig[:e - s]
    return canvas


def main():
    lead = np.zeros(N); arp = np.zeros(N); bass = np.zeros(N); drums = np.zeros(N); sfx = np.zeros(N)
    intro = 1.0
    eighth = BAR / 6
    rng = np.random.default_rng(1)

    for b, (broot, chord, mel) in enumerate(PROG):
        t0 = intro + b * BAR
        lead = place(lead, lead_note(S.note_to_hz(mel), BAR * 0.96, 0.5), t0, gain=0.5)
        # driving gritty bass — eighths, root/fifth
        bpat = [broot, broot, chord[2], broot, chord[2], broot]
        for i, bn in enumerate(bpat):
            bass = place(bass, bass_note(S.note_to_hz(bn), eighth * 0.95), t0 + i * eighth, gain=0.5)
        # arpeggio — 12 brighter notes per bar (busier, livelier)
        pat = [chord[0], chord[1], chord[2], chord[1]] * 3
        for i, note in enumerate(pat):
            arp = place(arp, arp_note(S.note_to_hz(note), (BAR / 12) * 1.1, 0.2), t0 + i * (BAR / 12), gain=0.26)
        # drums — kick on 1 & 4(eighth), snare on beat 2, hats on every eighth
        drums = place(drums, kick(), t0, gain=0.9)
        drums = place(drums, kick(), t0 + 3 * eighth, gain=0.7)
        drums = place(drums, snare(), t0 + 2 * eighth, gain=0.7)
        for i in range(6):
            drums = place(drums, hat(opn=(i == 5)), t0 + i * eighth, gain=0.5 if i % 2 else 0.35)

    # SFX — coin, lasers, the EGG-BREAKING STAGE (Part B), explosions
    sfx = place(sfx, coin(), 0.05, gain=0.6)
    for t in (intro + 3 * BAR, intro + 21 * BAR):
        sfx = place(sfx, laser(), t, gain=0.5)
        sfx = place(sfx, laser(), t + 0.16, gain=0.4)
    # the egg-breaking stage: a rhythmic flurry of cracks over Part B (bars 8..15)
    for k in range(14):
        t = intro + (8 + k * 0.5) * BAR + rng.uniform(-0.05, 0.05)
        sfx = place(sfx, egg_break(seed=k), t, gain=rng.uniform(0.5, 0.8))
        if k % 3 == 2:
            sfx = place(sfx, screech(), t + 0.12, gain=0.5)        # one hatches
    sfx = place(sfx, ufo(), intro + 16 * BAR, gain=0.5)
    sfx = place(sfx, explosion(seed=9), intro + 16 * BAR + 1.2, gain=0.8)
    sfx = place(sfx, explosion(seed=4), intro + 23.5 * BAR, gain=0.8)

    # mix to stereo (panned channels) — gritty arcade
    mix = (S.pan(lead[:N], 0.0) + S.pan(arp[:N], -0.35) + S.pan(bass[:N], 0.0) +
           S.pan(drums[:N], 0.1) + S.pan(sfx[:N], 0.3))
    mix = S.reverb_st(mix, decay=1.1, mix=0.10, seed=7)
    mix = S.soft_clip(mix * 0.85, drive=1.2)

    for nm, ch, p in [('lead', lead, 0.0), ('arp', arp, -0.35), ('bass', bass, 0.0),
                      ('drums', drums, 0.1), ('sfx', sfx, 0.3)]:
        S.write_wav(f'ph_{nm}.wav', S.pan(ch[:N], p)); print(f'  ph_{nm}.wav')
    S.write_wav('phoenix_mix.wav', mix)
    print('  phoenix_mix.wav', round(DUR, 1), 's')

    vd = os.path.join('versions', f'phoenix-{VERSION}'); os.makedirs(vd, exist_ok=True)
    for f in ['phoenix_mix.wav', 'phoenix.py', 'synth.py']:
        if os.path.exists(f):
            shutil.copy(f, vd)
    print('  archived ->', vd)


if __name__ == '__main__':
    main()

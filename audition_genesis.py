"""
audition_genesis.py — Excivilization, Movement I: Genesis (the newborn).

Purity persists, then turns to fear as the newborn arrives — unaware of what lies
beyond. The fear grows; but a first seed of order (the perfect fifth, 3:2) blooms
from the chaos — the glimmer of the wisdom that will, across the ages, outweigh
the fear. Pure Pythagorean tuning. The eternal D is born here. ~60 s.
"""
import numpy as np
import synth as S

DUR = 60.0
N = int(DUR * S.SR)
D2 = S.note_to_hz('D2')
D3 = S.note_to_hz('D3')
D5 = S.note_to_hz('D5')


def lane(points):
    return S.curve(points, DUR)


def main():
    t = np.arange(N) / S.SR

    # --- the eternal D, faint and continuous (the unbroken note is born) ---
    base = S.sine(D2, DUR)[:N] * 0.18
    base *= lane([(0, 0), (3, 0.6), (60, 0.8)])[:N]

    # --- PURITY: a fragile high open-fifth of pure sines, flickering (the newborn breath) ---
    flicker = 0.62 + 0.38 * (0.5 + 0.5 * S.lfo(0.35, DUR))           # tentative, unsure
    pure = (S.sine(D5, DUR)[:N] + 0.6 * S.sine(D5 * 1.5, DUR)[:N]) * flicker[:N]
    pure *= lane([(0, 0), (2, 0.55), (9, 0.6), (16, 0.5),
                  (30, 0.26), (42, 0.22), (50, 0.42), (60, 0.5)])[:N]   # persists, dips under fear, returns
    pure = S.reverb_st(S.stereo_width(S.as_stereo(pure), 1.0), decay=4.0, mix=0.5)

    # --- FEAR: a dark void that grows — a minor-2nd dissonance beating, sub-rumble, shadows ---
    fear = lane([(0, 0), (12, 0.12), (20, 0.38), (34, 0.72), (44, 0.85),
                 (50, 0.6), (60, 0.5)])[:N]                            # grows, then held (not erased)
    void = S.additive(D2, DUR, [1, 0.5, 0.3])[:N] + 0.8 * S.additive(D2 * 2 ** (1 / 12), DUR, [1, 0.5, 0.3])[:N]  # the dread (♭2 beat)
    cutoff = 300 + 1100 * fear                                        # the void presses closer as fear grows
    void = S.resonant_lpf(void, cutoff, 1.1)
    rumble = S.resonant_lpf(S.noise(DUR, seed=4)[:N], 120, 0.8) * 0.6
    shadow = S.ringmod(void, D2 * 1.41).mean(1) * 0.25               # inharmonic shadows of the dread
    fearsig = (void + rumble + shadow) * fear
    fearsig = S.reverb_st(S.stereo_width(S.as_stereo(fearsig), 0.6), decay=3.5, mix=0.4)

    # --- WISDOM'S SEED: the perfect fifth blooms from the chaos at the end ---
    seed = S.additive(D3, DUR, [1, 0.5, 0.3, 0.15])[:N] + 0.8 * S.additive(D3 * 1.5, DUR, [1, 0.5, 0.3])[:N]
    seed = S.resonant_lpf(seed, 2000, 0.8) * lane([(0, 0), (42, 0), (48, 0.3), (55, 0.55), (60, 0.55)])[:N]
    seed = S.reverb_st(S.stereo_width(S.as_stereo(seed), 0.9), decay=4.5, mix=0.45)

    master = S.as_stereo(base) + pure + fearsig + seed
    master = S.soft_clip(master * 0.85, drive=1.0)
    S.write_wav('genesis.wav', master)
    print('wrote genesis.wav', round(DUR, 1), 's')


if __name__ == '__main__':
    main()

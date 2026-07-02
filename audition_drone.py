"""
audition_drone.py — "the eternal drone" (the glue of the Hellas suite).

One tonic D sounds continuously and never stops; it only changes clothes through
the six eras — lyre open-fifth → Roman organ → Byzantine ison → Ottoman ney →
20th-century fracture → today. Pythagorean fifth (3:2). ~56 s.
"""
import numpy as np
import synth as S

DUR = 56.0
N = int(DUR * S.SR)
D = S.note_to_hz('D2')              # the tonic, for 2800 years
FIFTH = D * 1.5                     # Pythagorean perfect fifth (3:2)


def fifth_drone(root, amps, dur, lpf=2000, rev=0.35, decay=3.0, width=0.8):
    sig = S.additive(root, dur, amps) + 0.7 * S.additive(root * 1.5, dur, amps)
    sig = S.resonant_lpf(sig, lpf, 0.8)
    return S.reverb_st(S.stereo_width(S.as_stereo(sig), width), decay=decay, mix=rev)


def archaic(dur):      # lyre / open fifth — warm, luminous
    return fifth_drone(D * 2, [1, 0.5, 0.3, 0.15, 0.08], dur, lpf=2200, rev=0.35, decay=3.0)


def rome(dur):         # the hydraulis — a penetrating drawbar organ
    return fifth_drone(D, [1, 0.6, 0.5, 0.4, 0, 0.3, 0, 0, 0.2], dur, lpf=4000, rev=0.3, decay=2.5, width=0.6)


def byzantium(dur):    # the ison — vast, sacred, Hagia-Sophia reverb
    base = fifth_drone(D * 2, [1, 0.4, 0.25, 0.12, 0.06], dur, lpf=2600, rev=0.6, decay=8.0, width=1.0)
    return base


def ottoman(dur):      # the ney / dem — reedy, with a faint quarter-tone shimmer
    n = int(dur * S.SR)
    reed = S.pulse(D * 2, dur, 0.22)[:n] + 0.5 * S.pulse(FIFTH * 2, dur, 0.22)[:n]
    reed = S.resonant_bpf(reed, 1500, q=2.0) * 1.2
    micro = 0.25 * S.sine(D * 2 * 2 ** (0.5 / 12), dur)[:n]   # a quarter-tone neighbour
    sig = S.resonant_lpf(reed + micro, 2600, 0.8)
    return S.reverb_st(S.stereo_width(S.as_stereo(sig), 0.7), decay=3.0, mix=0.4)


def fire(dur):         # occupation & civil war — the same D, bitcrushed, fractured
    d = fifth_drone(D, [1, 0.5, 0.4, 0.3], dur, lpf=2200, rev=0.3, decay=2.0, width=0.5)
    return S.bitcrush(d, bits=5)[:len(d)]


def today(dur):        # modern — a warm bass D under a soft pad, the drone at rest
    n = int(dur * S.SR)
    bass = S.resonant_lpf(S.saw(D, dur)[:n], 500, 1.2) * 0.6
    pad = S.additive(D * 2, dur, [1, 0.5, 0.3, 0.15])[:n] + 0.7 * S.additive(FIFTH * 2, dur, [1, 0.5, 0.3])[:n]
    pad = S.resonant_lpf(pad, 1800, 0.8)
    return S.reverb_st(S.as_stereo(bass + 0.7 * pad), decay=3.2, mix=0.35)


ERAS = [archaic, rome, byzantium, ottoman, fire, today]
SEG = DUR / len(ERAS)              # ~9.3 s each


def win(i):
    """Crossfading presence lane for era i (linear ramps overlapping neighbours)."""
    s, e = i * SEG, (i + 1) * SEG
    return S.curve([(s - 2.6, 0), (s + 1.2, 1), (e - 1.2, 1), (e + 2.6, 0)], DUR)


def main():
    # a faint open-fifth base under EVERYTHING — the literal unbroken note
    master = fifth_drone(D, [1, 0.5, 0.3], DUR, lpf=1500, rev=0.3, decay=3.0) * 0.28
    for i, era in enumerate(ERAS):
        sig = era(DUR)[:N]
        master[:len(sig)] += sig * win(i)[:len(sig), None]
        print(f"  era {i} ({era.__name__}) placed")
    master = S.soft_clip(master * 0.9, drive=1.0)
    S.write_wav('drone_glue.wav', master)
    print('wrote drone_glue.wav', round(DUR, 1), 's')


if __name__ == '__main__':
    main()

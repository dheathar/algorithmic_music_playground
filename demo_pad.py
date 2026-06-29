"""First sound: an Oxygene-style lush pad chord.

Signal chain:  supersaw (7 detuned saws) per note  ->  sum into a chord
            -> gentle ADSR (slow attack, like a string machine)
            -> resonant lowpass (tames the buzz, adds body)
            -> phaser (the moving notches = the shimmer)
            -> reverb (space)
"""
import numpy as np
import synth as S

DUR = 6.0
chord = ['A3', 'C4', 'E4', 'G4', 'B4']  # Am9 — lush, slightly wistful

voices = np.zeros(int(DUR * S.SR))
for i, note in enumerate(chord):
    f = S.note_to_hz(note)
    d = S.drift(DUR, amount=0.004, seed=i)        # analog pitch drift
    osc = S.supersaw(f * d, DUR, voices=7, detune_cents=14)
    env = S.adsr(DUR, a=0.6, d=0.5, s=0.8, r=1.8)  # slow swell
    voices += osc * env

voices /= len(chord)
filt = S.resonant_lpf(voices, cutoff=2200, q=0.9)   # soften the top
ph = S.phaser(filt, rate=0.18, depth=0.8, stages=6, feedback=0.4, mix=0.55)
out = S.reverb(ph, decay=3.0, mix=0.4)
out = S.soft_clip(out, drive=1.1)

S.write_wav('out_pad.wav', out)
print('wrote out_pad.wav', round(len(out) / S.SR, 2), 's')

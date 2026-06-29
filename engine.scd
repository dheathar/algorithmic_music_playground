// engine.scd — Signal Lab's SuperCollider voices.
// Install SuperCollider, open this in the SC IDE, evaluate the whole block
// (Cmd+Enter inside the parens). Boots scsynth and defines three voices that
// mirror our patch format: \labvoice (subtractive), \labadd (additive),
// \labfm (FM). Python drives them over OSC on port 57110.
(
s.waitForBoot({
    var tail;
    // shared tail: filter (+ env sweep + LFO) -> amp env -> reverb -> pan -> out
    tail = { |sig, amp = 0.25, cutoff = 1500, rq = 0.4, ftype = 0, atk = 0.01, rel = 0.4,
             dur = 2, revmix = 0.3, pan = 0, fenv = 0, lfot = 0, lfor = 5, lfod = 0|
        var env, fsweep, lfo, co;
        lfo = SinOsc.kr(lfor);
        env = EnvGen.kr(Env.linen(atk, (dur - atk - rel).max(0.05), rel, 1, \sin), doneAction: 2);
        fsweep = EnvGen.kr(Env.perc(0.005, (dur * 0.6).max(0.1)));
        co = cutoff * (1 + (fenv * 3 * fsweep));          // filter envelope
        co = co * (1 + ((lfot > 0.5) * (lfot < 1.5) * lfod * 0.9 * lfo)); // LFO->filter
        co = co.clip(30, 18000);
        sig = Select.ar(ftype, [RLPF.ar(sig, co, rq), RHPF.ar(sig, co, rq), BPF.ar(sig, co, rq)]);
        sig = sig * env * amp * (1 - ((lfot > 2.5) * lfod * 0.5 * (lfo * 0.5 + 0.5))); // LFO->amp
        sig = sig.tanh;                                   // per-voice safety: bound to ±1
        sig = FreeVerb.ar(sig, mix: revmix, room: 0.7);
        Out.ar(0, Pan2.ar(sig, pan));
    };

    // --- subtractive (osc.type "wave") ---
    SynthDef(\labvoice, { |freq = 220, wave = 0, voices = 1, detune = 8,
        amp = 0.25, cutoff = 1500, rq = 0.4, ftype = 0, atk = 0.01, rel = 0.4,
        dur = 2, revmix = 0.3, pan = 0, fenv = 0, lfot = 0, lfor = 5, lfod = 0|
        var f, sig, uni, det;
        f = freq * (1 + ((lfot > 1.5) * (lfot < 2.5) * lfod * 0.04 * SinOsc.kr(lfor))); // LFO->pitch
        det = 2 ** (detune / 1200);
        sig = Select.ar(wave, [Saw.ar(f), Pulse.ar(f, 0.5), SinOsc.ar(f), LFTri.ar(f)]);
        uni = Select.ar(wave, [
            Saw.ar(f * det) + Saw.ar(f / det),
            Pulse.ar(f * det, 0.5) + Pulse.ar(f / det, 0.5),
            SinOsc.ar(f * det) + SinOsc.ar(f / det),
            LFTri.ar(f * det) + LFTri.ar(f / det)]);
        sig = sig + (uni * (voices > 1) * 0.4);
        tail.(sig, amp, cutoff, rq, ftype, atk, rel, dur, revmix, pan, fenv, lfot, lfor, lfod);
    }).add;

    // --- additive (osc.type "additive"): 16 harmonic amps h1..h16 ---
    SynthDef(\labadd, { |freq = 220, amp = 0.25, cutoff = 9000, rq = 0.7, ftype = 0,
        atk = 0.01, rel = 0.4, dur = 2, revmix = 0.3, pan = 0, fenv = 0, lfot = 0, lfor = 5, lfod = 0,
        h1=1,h2=0,h3=0,h4=0,h5=0,h6=0,h7=0,h8=0,h9=0,h10=0,h11=0,h12=0,h13=0,h14=0,h15=0,h16=0|
        var f, sig, amps;
        f = freq * (1 + ((lfot > 1.5) * (lfot < 2.5) * lfod * 0.04 * SinOsc.kr(lfor)));
        amps = [h1,h2,h3,h4,h5,h6,h7,h8,h9,h10,h11,h12,h13,h14,h15,h16];
        sig = Mix(Array.fill(16, { |i| SinOsc.ar(f * (i + 1)) * amps[i] })) * 0.5;
        tail.(sig, amp, cutoff, rq, ftype, atk, rel, dur, revmix, pan, fenv, lfot, lfor, lfod);
    }).add;

    // --- FM (osc.type "fm"): carrier/modulator via phase modulation ---
    SynthDef(\labfm, { |freq = 220, ratio = 2, index = 2,
        amp = 0.25, cutoff = 9000, rq = 0.7, ftype = 0, atk = 0.01, rel = 0.4,
        dur = 2, revmix = 0.3, pan = 0, fenv = 0, lfot = 0, lfor = 5, lfod = 0|
        var f, sig;
        f = freq * (1 + ((lfot > 1.5) * (lfot < 2.5) * lfod * 0.04 * SinOsc.kr(lfor)));
        sig = PMOsc.ar(f, f * ratio, index);
        tail.(sig, amp, cutoff, rq, ftype, atk, rel, dur, revmix, pan, fenv, lfot, lfor, lfod);
    }).add;

    // --- stardust: soft random sine twinkles, drenched in reverb (cosmic glitter) ---
    SynthDef(\stardust, { |amp = 0.1, dur = 8, density = 7, revmix = 0.6, lo = 1500, hi = 4500|
        var trig, twinkle, env, freq, sig;
        env = EnvGen.kr(Env.linen(1.5, (dur - 3).max(0.2), 1.5), doneAction: 2);
        trig = Dust.kr(density);
        freq = TExpRand.kr(lo, hi, trig);
        twinkle = SinOsc.ar(freq) * EnvGen.ar(Env.perc(0.02, 0.55), trig) * 0.8;  // softer, longer shimmer
        sig = (twinkle * amp * env).tanh;
        sig = FreeVerb.ar(sig, mix: revmix, room: 0.85);
        Out.ar(0, Pan2.ar(sig, LFNoise1.kr(0.3)));     // twinkles drift gently in the field
    }).add;

    // --- a struck sounding (sonar ping): pitch-drop + body + long decay, not a held sine ---
    SynthDef(\labping, { |freq = 110, amp = 0.18, dur = 4, revmix = 0.55, pan = 0|
        var sig, env, f;
        f = freq * XLine.kr(1.05, 1.0, 1.0);                       // the downward "sonar" drop
        sig = SinOsc.ar(f) + (SinOsc.ar(f * 2.01) * 0.25) + (SinOsc.ar(f * 3) * 0.08);  // body
        env = EnvGen.kr(Env.perc(0.01, dur.max(0.4), 1, -4), doneAction: 2);  // struck, decays
        sig = (LPF.ar(sig, 1300) * env * amp).tanh;
        sig = FreeVerb.ar(sig, mix: revmix, room: 0.9);
        Out.ar(0, Pan2.ar(sig, pan));
    }).add;

    // --- legato voice: ONE held synth whose pitch GLIDES (portamento) between notes ---
    SynthDef(\labglide, { |freq = 220, gate = 1, amp = 0.2, wave = 0, cutoff = 2200, rq = 0.4,
        glide = 0.08, atk = 0.05, rel = 0.6, revmix = 0.3, pan = 0, detune = 8, voices = 1|
        var f, sig, uni, det, env;
        f = Lag.kr(freq, glide);                         // the portamento
        det = 2 ** (detune / 1200);
        sig = Select.ar(wave, [Saw.ar(f), Pulse.ar(f, 0.5), SinOsc.ar(f), LFTri.ar(f)]);
        uni = Select.ar(wave, [
            Saw.ar(f * det) + Saw.ar(f / det),
            Pulse.ar(f * det, 0.5) + Pulse.ar(f / det, 0.5),
            SinOsc.ar(f * det) + SinOsc.ar(f / det),
            LFTri.ar(f * det) + LFTri.ar(f / det)]);
        sig = sig + (uni * (voices > 1) * 0.4);
        sig = RLPF.ar(sig, cutoff.clip(30, 18000), rq);
        env = EnvGen.kr(Env.asr(atk, 1.0, rel), gate, doneAction: 2);   // held while gate=1
        sig = (sig * env * amp).tanh;
        sig = FreeVerb.ar(sig, mix: revmix, room: 0.7);
        Out.ar(0, Pan2.ar(sig, pan));
    }).add;

    // master limiter at the tail of the node tree — sums can never clip to noise
    SynthDef(\masterlimiter, {
        ReplaceOut.ar(0, Limiter.ar(LeakDC.ar(In.ar(0, 2)) * 0.7, 0.9, 0.05));
    }).add;
    s.sync;
    Synth.tail(s, \masterlimiter);

    "Signal Lab: \\labvoice \\labadd \\labfm + master limiter ready on 57110.".postln;
});
)

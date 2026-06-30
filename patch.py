"""
patch.py — the bridge between browser-designed sounds and the Python engine.

A "patch" is a small JSON ingredient (see PATCH-FORMAT.md). This module renders
one into stereo audio using synth.py — so a sound sculpted in a bench can be
auditioned through the real engine and dropped straight into a composition.

  render_patch(patch_dict, dur=None, note=None) -> np.ndarray (N, 2)
  load_patch(path) -> dict
  CLI:  ./.venv/bin/python patch.py in.json out.wav
"""
import sys
import json
import numpy as np
import synth as S

TRIANGLE = [((1.0 / (k * k)) * (1 if k % 4 == 1 else -1) if k % 2 else 0.0)
            for k in range(1, 17)]   # band-limited triangle harmonic recipe


def load_patch(path):
    with open(path) as f:
        return json.load(f)


def _clamp(v, lo, hi, default):
    try:
        return max(lo, min(hi, float(v)))
    except (TypeError, ValueError):
        return default


def validate_patch(d):
    """Coerce/clamp an arbitrary dict (e.g. LLM output) into a safe, renderable
    patch. Never trust raw model JSON — always pass it through here first."""
    if not isinstance(d, dict):
        d = {}
    osc_in = d.get("osc", {}) if isinstance(d.get("osc"), dict) else {}
    otype = osc_in.get("type") if osc_in.get("type") in ("additive", "fm", "wave", "stardust", "ping") else "wave"
    harms = osc_in.get("harmonics") if isinstance(osc_in.get("harmonics"), list) else [1.0]
    harms = [_clamp(h, 0, 1, 0) for h in harms[:16]] or [1.0]
    wave = osc_in.get("wave") if osc_in.get("wave") in ("saw", "square", "sine", "triangle", "pulse") else "saw"
    osc = {"type": otype, "harmonics": harms, "wave": wave,
           "ratio": _clamp(osc_in.get("ratio", 2.0), 0.25, 16, 2.0),
           "index": _clamp(osc_in.get("index", 200), 0, 2000, 200),
           "voices": int(_clamp(osc_in.get("voices", 1), 1, 7, 1)),
           "detune": _clamp(osc_in.get("detune", 8), 0, 30, 8),
           "duty": _clamp(osc_in.get("duty", 0.5), 0.05, 0.95, 0.5)}
    if otype == "stardust":
        osc["density"] = _clamp(osc_in.get("density", 7), 1, 40, 7)
        osc["lo"] = _clamp(osc_in.get("lo", 1500), 200, 8000, 1500)
        osc["hi"] = _clamp(osc_in.get("hi", 4500), 400, 12000, 4500)
    fi = d.get("filter", {}) if isinstance(d.get("filter"), dict) else {}
    ft = fi.get("type") if fi.get("type") in ("lowpass", "highpass", "bandpass", "notch") else "lowpass"
    filt = {"type": ft, "cutoff": _clamp(fi.get("cutoff", 1500), 30, 18000, 1500),
            "q": _clamp(fi.get("q", 3), 0.3, 24, 3), "env_amt": _clamp(fi.get("env_amt", 0), 0, 2, 0)}
    en = d.get("env", {}) if isinstance(d.get("env"), dict) else {}
    env = {"a": _clamp(en.get("a", 0.02), 0, 5, 0.02), "d": _clamp(en.get("d", 0.2), 0, 5, 0.2),
           "s": _clamp(en.get("s", 0.6), 0, 1, 0.6), "r": _clamp(en.get("r", 0.4), 0, 5, 0.4)}
    lf = d.get("lfo", {}) if isinstance(d.get("lfo"), dict) else {}
    lt = lf.get("target") if lf.get("target") in ("none", "filter", "pitch", "amp") else "none"
    lfo = {"target": lt, "rate": _clamp(lf.get("rate", 5), 0, 20, 5), "depth": _clamp(lf.get("depth", 0), 0, 1, 0)}
    fx_in = d.get("fx", {}) if isinstance(d.get("fx"), dict) else {}
    fx = {"reverb": _clamp(fx_in.get("reverb", 0.3), 0, 0.9, 0.3),
          "delay": _clamp(fx_in.get("delay", 0), 0, 0.9, 0),
          "delay_time": _clamp(fx_in.get("delay_time", 0.3), 0.05, 1.2, 0.3),
          "width": _clamp(fx_in.get("width", 0.5), 0, 1, 0.5),
          "drive": _clamp(fx_in.get("drive", 1.0), 0.5, 3, 1.0)}
    out = {"v": 1, "name": str(d.get("name", "ai-patch"))[:40], "osc": osc,
           "filter": filt, "env": env, "lfo": lfo, "fx": fx,
           "dur": _clamp(d.get("dur", 3.0), 0.2, 12, 3.0)}
    if d.get("note"):
        out["note"] = str(d["note"])[:4]
    elif d.get("freq"):
        out["freq"] = _clamp(d.get("freq"), 20, 12000, 220)
    else:
        out["note"] = "A3"
    seq = d.get("sequence")
    if isinstance(seq, list) and seq:
        out["sequence"] = [{"step": int(_clamp(e.get("step", 0), 0, 64, 0)),
                            "deg": int(_clamp(e.get("deg", 0), 0, 20, 0))}
                           for e in seq if isinstance(e, dict)][:64]
        out["tempo"] = _clamp(d.get("tempo", 104), 40, 200, 104)
        out["root"] = str(d.get("root", "A"))[:3]
        out["scale"] = d.get("scale") if d.get("scale") in S.SCALES else "minor"
    return out


def _freq(patch, note):
    if note:
        return S.note_to_hz(note)
    if patch.get('note'):
        return S.note_to_hz(patch['note'])
    return float(patch.get('freq', 220.0))


def _osc(spec, freq, dur):
    """freq may be scalar or a per-sample array (for pitch LFO/glide)."""
    typ = spec.get('type', 'wave')
    if typ == 'additive':
        return S.additive(freq, dur, spec.get('harmonics', [1.0]))
    if typ == 'fm':
        ratio = float(spec.get('ratio', 2.0))
        idx = float(spec.get('index', 2.0))
        fmean = float(np.mean(np.atleast_1d(freq)))
        if idx > 20:                     # browser sends Hz deviation -> FM index β
            idx = idx / max(1.0, fmean * ratio)
        return S.fm2(freq, dur, ratio=ratio, index=idx)
    if typ == 'ping':                    # struck sounding with a downward pitch drop
        n = int(dur * S.SR)
        t = np.arange(n) / S.SR
        f0 = float(np.atleast_1d(freq)[0])
        gl = f0 * (1 - 0.05 * np.clip(t / 1.0, 0, 1))
        return S.sine(gl, dur) + 0.25 * S.sine(2.01 * gl, dur) + 0.08 * S.sine(3 * gl, dur)
    if typ == 'stardust':                # sparse decaying sine twinkles (NOT noise)
        n = int(dur * S.SR)
        out = np.zeros(n)
        rng = np.random.default_rng(7)
        density = float(spec.get('density', 7))
        lo, hi = float(spec.get('lo', 1500)), float(spec.get('hi', 4500))
        glen = int(0.45 * S.SR)
        decay = np.exp(-np.arange(glen) / (0.12 * S.SR))
        for _ in range(int(density * dur)):
            tw = S.sine(rng.uniform(lo, hi), glen / S.SR) * decay
            at = int(rng.uniform(0, max(1, n - glen)))
            out[at:at + glen] += tw
        return out * 0.45
    wave = spec.get('wave', 'saw')
    voices = int(spec.get('voices', 1))
    duty = float(spec.get('duty', 0.5))
    one = {'saw': S.saw, 'square': S.square, 'sine': S.sine}
    def osc1(f):
        if wave == 'triangle':
            return S.additive(f, dur, TRIANGLE)
        if wave == 'pulse':                       # variable pulse width (PWM timbres)
            return S.pulse(f, dur, duty)
        return one.get(wave, S.saw)(f, dur)
    if voices > 1:
        det = float(spec.get('detune', 8.0))
        out = np.zeros(int(dur * S.SR))
        for c in np.linspace(-det, det, voices):
            out += osc1(np.asarray(freq) * 2 ** (c / 1200))
        return out / voices
    return osc1(freq)


def _voice(patch, freq, dur):
    """Render one mono note: osc -> filter -> amp env, with LFO routing."""
    n = int(dur * S.SR)
    t = np.arange(n) / S.SR
    lfo = patch.get('lfo', {}) or {}
    tgt, rate, depth = lfo.get('target', 'none'), float(lfo.get('rate', 5)), float(lfo.get('depth', 0))
    wave = (0.5 + 0.5 * np.sin(2 * np.pi * rate * t)) if depth > 0 else None

    f = freq
    if tgt == 'pitch' and depth > 0:
        f = freq * (1 + depth * 0.04 * np.sin(2 * np.pi * rate * t))
    sig = _osc(patch.get('osc', {}), f, dur)[:n]

    fl = patch.get('filter', {}) or {}
    if fl:
        cut, q = float(fl.get('cutoff', 1200)), float(fl.get('q', 2.0))
        env_amt = float(fl.get('env_amt', 0))
        if tgt == 'filter' and depth > 0:
            cutoff = np.clip(cut * (1 + depth * 0.9 * (wave - 0.5) * 2), 30, 20000)
        elif env_amt > 0:
            e = S.adsr(dur, a=0.005, d=0.35, s=0.25, r=0.2)[:n]
            cutoff = np.clip(cut * (1 + env_amt * 3 * e), 30, 20000)
        else:
            cutoff = cut
        fn = {'lowpass': S.resonant_lpf, 'highpass': S.resonant_hpf,
              'bandpass': S.resonant_bpf, 'notch': S.resonant_notch}.get(fl.get('type', 'lowpass'), S.resonant_lpf)
        sig = fn(sig, cutoff, q)

    e = patch.get('env', {}) or {}
    amp = S.adsr(dur, a=float(e.get('a', 0.01)), d=float(e.get('d', 0.1)),
                 s=float(e.get('s', 0.7)), r=float(e.get('r', 0.2)))[:n]
    if tgt == 'amp' and depth > 0:
        amp = amp * (1 - depth * 0.5 * wave)
    return sig * amp


def _fx_chain(mono, fx, dur):
    """mono -> stereo with delay, reverb, width, saturation."""
    fx = fx or {}
    mono = S.soft_clip(mono, drive=float(fx.get('drive', 1.0)))
    if float(fx.get('delay', 0)) > 0:
        st = S.pingpong(mono, time=float(fx.get('delay_time', 0.3)),
                        feedback=0.4, mix=float(fx['delay']))
    else:
        st = S.as_stereo(mono)
    if float(fx.get('reverb', 0)) > 0:
        st = S.reverb_st(st, decay=2.6, mix=float(fx['reverb']))
    if fx.get('width') is not None:
        st = S.stereo_width(st, 0.4 + float(fx['width']) * 1.1)   # 0..1 -> 0.4..1.5
    return st


def render_patch(patch, dur=None, note=None):
    """Render a patch to stereo (N, 2). A 'sequence' makes a phrase; otherwise
    a single sustained note."""
    seq = patch.get('sequence')
    if seq:
        tempo = float(patch.get('tempo', 104))
        sc = S.scale((patch.get('root', 'A')) + '3', patch.get('scale', 'minor'), octaves=2)
        step = 60 / tempo / 4
        last = max((ev.get('step', 0) for ev in seq), default=0)
        total = (last + 4) * step
        N = int(total * S.SR)
        canvas = np.zeros(N)
        for ev in seq:
            f = sc[int(ev.get('deg', 0)) % len(sc)]
            v = _voice(patch, f, step * 1.6)
            canvas = S.mix_at(canvas, v, ev.get('step', 0) * step, gain=0.6)
        return _fx_chain(canvas[:N], patch.get('fx', {}), total)
    d = float(dur or patch.get('dur', 3.0))
    mono = _voice(patch, _freq(patch, note), d)
    return _fx_chain(mono, patch.get('fx', {}), d)


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('usage: python patch.py in.json out.wav'); sys.exit(1)
    p = load_patch(sys.argv[1])
    sig = render_patch(p)
    S.write_wav(sys.argv[2], sig)
    print('wrote', sys.argv[2], round(len(sig) / S.SR, 2), 's', '·', p.get('name', '(unnamed)'))

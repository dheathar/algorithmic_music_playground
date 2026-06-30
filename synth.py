"""
synth.py — a small modular synthesis engine, from first principles.

Everything is plain numpy float64 arrays at a fixed sample rate. Signals are
mono float arrays in roughly [-1, 1] until the final mix/limiting stage.

Design notes for an audio-DSP reader:
  * Oscillators are band-limited via additive synthesis (sum of harmonics up to
    Nyquist). Slower than a wavetable, but zero aliasing and dead simple to
    reason about — perfect for understanding the harmonic content.
  * The filter is a Direct-Form-II transposed biquad (scipy lfilter) with
    coefficients from the RBJ Audio EQ Cookbook. For a *swept* cutoff we
    recompute coefficients in short blocks (zero-order hold) and carry state
    across blocks so there are no clicks.
"""

import numpy as np
from scipy.signal import lfilter, lfilter_zi, fftconvolve

SR = 44100  # sample rate (Hz)


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def note_to_hz(note: str) -> float:
    """'A4' -> 440.0. Scientific pitch notation, A4 = 440 Hz."""
    names = {'C': 0, 'C#': 1, 'D': 2, 'D#': 3, 'E': 4, 'F': 5,
             'F#': 6, 'G': 7, 'G#': 8, 'A': 9, 'A#': 10, 'B': 11}
    name = note[:-1]
    octave = int(note[-1])
    semis = names[name] + (octave - 4) * 12 - 9  # semitones from A4
    return 440.0 * 2 ** (semis / 12)


def t_axis(dur: float) -> np.ndarray:
    return np.arange(int(dur * SR)) / SR


def db(x: float) -> float:
    """decibels -> linear gain."""
    return 10 ** (x / 20)


# Scale = the allowed-pitches comb (semitone offsets from the root, per octave).
SCALES = {
    'major':    [0, 2, 4, 5, 7, 9, 11],
    'minor':    [0, 2, 3, 5, 7, 8, 10],
    'dorian':   [0, 2, 3, 5, 7, 9, 10],
    'phrygian': [0, 1, 3, 5, 7, 8, 10],   # lowered 2nd -> the dark/ancient color
    'lydian':   [0, 2, 4, 6, 7, 9, 11],   # raised 4th -> bright, soaring, "flight"
    'wholetone':[0, 2, 4, 6, 8, 10],      # no semitones -> floating, alien, no home
}


def scale(root: str, mode: str, octaves=2, start_oct=None):
    """Return ascending list of frequencies for a key — the 'comb' of allowed
    pitches. degree(scale(...), i) then never lets you pick a wrong note."""
    names = {'C': 0, 'C#': 1, 'D': 2, 'D#': 3, 'E': 4, 'F': 5,
             'F#': 6, 'G': 7, 'G#': 8, 'A': 9, 'A#': 10, 'B': 11}
    root_name, root_oct = root[:-1], int(root[-1])
    if start_oct is None:
        start_oct = root_oct
    base = names[root_name]
    out = []
    for o in range(octaves + 1):
        for semi in SCALES[mode]:
            n = base + semi + 12 * (start_oct - 4 + o) - 9  # semis from A4
            out.append(440.0 * 2 ** (n / 12))
    return out


def degree(scale_freqs, i):
    """Index into a scale, wrapping octaves so any integer is valid."""
    return scale_freqs[i % len(scale_freqs)] * 2 ** (i // len(scale_freqs) * 0)


def curve(points, dur):
    """Piecewise-linear automation: points=[(t_sec, value), ...] -> per-sample
    array of length dur*SR. This is how a parameter 'moves' across movements
    (think of it as drawing an automation lane)."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    ts = np.array([p[0] for p in points], dtype=float)
    vs = np.array([p[1] for p in points], dtype=float)
    return np.interp(t, ts, vs)


# ---------------------------------------------------------------------------
# Oscillators (band-limited, additive)
# ---------------------------------------------------------------------------

def _harmonic_sum(freq, dur, amps):
    """Sum harmonics k=1..N with given relative amplitudes, dropping any
    harmonic above Nyquist. `freq` may be a scalar or a per-sample array
    (for vibrato/glide); phase is integrated so frequency can vary."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    if np.isscalar(freq):
        freq = np.full(n, float(freq))
    phase = 2 * np.pi * np.cumsum(freq) / SR  # instantaneous phase
    out = np.zeros(n)
    for k, a in enumerate(amps, start=1):
        # mute harmonics that would alias (use mean freq as a cheap guard)
        if k * np.mean(freq) >= SR / 2:
            break
        out += a * np.sin(k * phase)
    return out


def saw(freq, dur, n_harm=None):
    """Band-limited sawtooth: harmonics 1/k, all of them."""
    n_harm = n_harm or int(SR / 2 / np.mean(np.atleast_1d(freq)))
    amps = [1.0 / k for k in range(1, n_harm + 1)]
    return _harmonic_sum(freq, dur, amps)


def square(freq, dur, n_harm=None):
    """Band-limited square: odd harmonics 1/k."""
    n_harm = n_harm or int(SR / 2 / np.mean(np.atleast_1d(freq)))
    amps = [(1.0 / k if k % 2 else 0.0) for k in range(1, n_harm + 1)]
    return _harmonic_sum(freq, dur, amps)


def sine(freq, dur):
    return _harmonic_sum(freq, dur, [1.0])


def pulse(freq, dur, duty=0.5, n_harm=None):
    """Band-limited pulse via its Fourier series. duty sets the timbre:
    0.5 = square (hollow), 0.25/0.125 = brighter/nasal (the classic pulse lead)."""
    n_harm = n_harm or int(SR / 2 / np.mean(np.atleast_1d(freq)))
    amps = [(2.0 / (k * np.pi)) * np.sin(k * np.pi * duty) for k in range(1, n_harm + 1)]
    return _harmonic_sum(freq, dur, amps)


def supersaw(freq, dur, voices=7, detune_cents=12.0):
    """Several detuned saws summed — the classic fat string/pad oscillator.
    Spread of slight pitch offsets creates slow beating = movement."""
    n = int(dur * SR)
    out = np.zeros(n)
    spread = np.linspace(-detune_cents, detune_cents, voices)
    for c in spread:
        f = freq * 2 ** (c / 1200)
        out += saw(f, dur)
    return out / voices


def additive(freq, dur, amps):
    """Band-limited additive oscillator: sum sine harmonics with the given
    relative amplitudes (amps[0] = fundamental). Public wrapper over the
    internal harmonic summer — used by the patch bridge."""
    return _harmonic_sum(freq, dur, list(amps))


def noise(dur, seed=0):
    """White noise — raw material for wind/breath textures."""
    rng = np.random.default_rng(seed)
    return rng.standard_normal(int(dur * SR))


def fm2(freq, dur, ratio=2.0, index=2.0, mod_env=None):
    """Two-operator FM (phase modulation): one sine modulates another's phase.
    Inharmonic ratios (e.g. 3.5) give bell/metallic tones. `index` may be a
    scalar or a per-sample array; pair with a decaying `mod_env` for a struck
    bell whose timbre dulls as it rings."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    mod = np.sin(2 * np.pi * freq * ratio * t)
    idx = index * (mod_env if mod_env is not None else 1.0)
    return np.sin(2 * np.pi * freq * t + idx * mod)


# ---------------------------------------------------------------------------
# Envelopes & modulation
# ---------------------------------------------------------------------------

def adsr(dur, a=0.01, d=0.1, s=0.7, r=0.2, sustain_level=None):
    """Linear ADSR envelope of total length `dur` (attack/decay happen at the
    start, release at the very end). s = sustain level (0..1)."""
    n = int(dur * SR)
    s = sustain_level if sustain_level is not None else s
    na, nd, nr = int(a * SR), int(d * SR), int(r * SR)
    na, nd, nr = min(na, n), min(nd, n), min(nr, n)
    ns = max(0, n - na - nd - nr)
    env = np.concatenate([
        np.linspace(0, 1, na, endpoint=False),
        np.linspace(1, s, nd, endpoint=False),
        np.full(ns, s),
        np.linspace(s, 0, nr),
    ])
    # pad/trim to exactly n
    if len(env) < n:
        env = np.concatenate([env, np.full(n - len(env), env[-1] if len(env) else 0)])
    return env[:n]


def lfo(rate, dur, shape='sine', depth=1.0, phase=0.0):
    t = t_axis(dur)
    ph = 2 * np.pi * rate * t + phase
    if shape == 'sine':
        w = np.sin(ph)
    elif shape == 'tri':
        w = 2 / np.pi * np.arcsin(np.sin(ph))
    elif shape == 'saw':
        w = 2 * (rate * t - np.floor(0.5 + rate * t))
    else:
        raise ValueError(shape)
    return depth * w


def drift(dur, amount=0.003, rate=0.3, seed=0):
    """Slow random pitch/param drift = the 'analog is alive' factor.
    Smoothed white noise, returns a multiplier centered on 1.0."""
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    # generate noise at a low rate then interpolate up
    n_ctrl = max(2, int(dur * rate * 10))
    ctrl = rng.standard_normal(n_ctrl)
    # smooth
    ctrl = np.convolve(ctrl, np.ones(3) / 3, mode='same')
    x = np.linspace(0, 1, n_ctrl)
    xi = np.linspace(0, 1, n)
    return 1.0 + amount * np.interp(xi, x, ctrl)


# ---------------------------------------------------------------------------
# Resonant filter (RBJ biquad), block-wise for swept cutoff
# ---------------------------------------------------------------------------

def _biquad_lpf(fc, q):
    """RBJ cookbook lowpass coefficients."""
    fc = np.clip(fc, 20, SR / 2 * 0.99)
    w0 = 2 * np.pi * fc / SR
    cw, sw = np.cos(w0), np.sin(w0)
    alpha = sw / (2 * q)
    b0 = (1 - cw) / 2
    b1 = 1 - cw
    b2 = (1 - cw) / 2
    a0 = 1 + alpha
    a1 = -2 * cw
    a2 = 1 - alpha
    b = np.array([b0, b1, b2]) / a0
    a = np.array([1.0, a1 / a0, a2 / a0])
    return b, a


def _biquad_bpf(fc, q):
    """RBJ cookbook bandpass (constant 0 dB peak gain)."""
    fc = np.clip(fc, 20, SR / 2 * 0.99)
    w0 = 2 * np.pi * fc / SR
    cw, sw = np.cos(w0), np.sin(w0)
    alpha = sw / (2 * q)
    b = np.array([alpha, 0.0, -alpha])
    a0 = 1 + alpha
    a = np.array([1.0, -2 * cw, 1 - alpha])
    return b / a0, np.array([1.0, a[1] / a0, a[2] / a0])


def _biquad_hpf(fc, q):
    """RBJ cookbook highpass."""
    fc = np.clip(fc, 20, SR / 2 * 0.99)
    w0 = 2 * np.pi * fc / SR
    cw, sw = np.cos(w0), np.sin(w0)
    alpha = sw / (2 * q)
    a0 = 1 + alpha
    b = np.array([(1 + cw) / 2, -(1 + cw), (1 + cw) / 2]) / a0
    a = np.array([1.0, (-2 * cw) / a0, (1 - alpha) / a0])
    return b, a


def _biquad_notch(fc, q):
    """RBJ cookbook notch (band-reject)."""
    fc = np.clip(fc, 20, SR / 2 * 0.99)
    w0 = 2 * np.pi * fc / SR
    cw, sw = np.cos(w0), np.sin(w0)
    alpha = sw / (2 * q)
    a0 = 1 + alpha
    b = np.array([1.0, -2 * cw, 1.0]) / a0
    a = np.array([1.0, (-2 * cw) / a0, (1 - alpha) / a0])
    return b, a


def _block_filter(x, cutoff, q, coeff_fn, block):
    n = len(x)
    if np.isscalar(cutoff):
        cutoff = np.full(n, float(cutoff))
    out = np.zeros(n)
    zi = None
    for start in range(0, n, block):
        end = min(start + block, n)
        b, a = coeff_fn(float(np.mean(cutoff[start:end])), q)
        if zi is None:
            zi = lfilter_zi(b, a) * x[start]
        out[start:end], zi = lfilter(b, a, x[start:end], zi=zi)
    return out


def resonant_lpf(x, cutoff, q=2.0, block=256):
    """Lowpass with possibly time-varying cutoff (scalar or per-sample array).
    Coefficients update every `block` samples; state carries across blocks so
    a swept cutoff has no clicks."""
    return _block_filter(x, cutoff, q, _biquad_lpf, block)


def resonant_bpf(x, cutoff, q=6.0, block=256):
    """Bandpass — used to 'pitch' noise into a wind/whistle tone."""
    return _block_filter(x, cutoff, q, _biquad_bpf, block)


def resonant_hpf(x, cutoff, q=2.0, block=256):
    """Highpass with possibly time-varying cutoff."""
    return _block_filter(x, cutoff, q, _biquad_hpf, block)


def resonant_notch(x, cutoff, q=4.0, block=256):
    """Notch / band-reject with possibly time-varying cutoff."""
    return _block_filter(x, cutoff, q, _biquad_notch, block)


# ---------------------------------------------------------------------------
# Effects: phaser, tape delay, reverb, soft clip
# ---------------------------------------------------------------------------

def phaser(x, rate=0.3, depth=0.7, stages=6, feedback=0.4, mix=0.5, block=64):
    """Classic phaser: cascade of first-order allpass filters whose break
    frequency is swept by an LFO, summed with the dry signal -> moving notches.
    This is THE string-machine/Oxygene shimmer.

    Block-processed: the LFO barely moves over `block` samples, so we hold the
    allpass coefficient per block and run each stage with lfilter (carrying
    state across blocks). Feedback is injected at each block boundary — an
    approximation that's transparent for the slow phasers we use."""
    n = len(x)
    lfo_sig = 0.5 * (1 + np.sin(2 * np.pi * rate * np.arange(n) / SR))
    fmin, fmax = 300.0, 1600.0
    fc = fmin * (fmax / fmin) ** (depth * lfo_sig)
    tanv = np.tan(np.pi * fc / SR)
    aarr = (tanv - 1) / (tanv + 1)        # first-order allpass coefficient
    out = np.zeros(n)
    states = [None] * stages
    fb = 0.0
    for start in range(0, n, block):
        end = min(start + block, n)
        a = float(np.mean(aarr[start:end]))
        b, ac = np.array([a, 1.0]), np.array([1.0, a])
        s = x[start:end].copy()
        s[0] += feedback * fb
        for st in range(stages):
            zi = states[st] if states[st] is not None else lfilter_zi(b, ac) * s[0]
            s, states[st] = lfilter(b, ac, s, zi=zi)
        fb = s[-1]
        out[start:end] = (1 - mix) * x[start:end] + mix * s
    return out


def tape_delay(x, time=0.375, feedback=0.35, mix=0.3, wobble=0.002):
    """Delay with feedback and slight time wobble (tape flutter)."""
    n = len(x)
    base = int(time * SR)
    out = x.copy()
    buf = np.zeros(n + base + 100)
    buf[:n] = x
    # simple feedback delay with modulated read offset
    flutter = (wobble * SR * np.sin(2 * np.pi * 6 * np.arange(n) / SR)).astype(int)
    y = np.zeros(n)
    d = np.zeros(n + base + 10)
    for i in range(n):
        r = i - base + flutter[i]
        echo = d[r] if r >= 0 else 0.0
        d[i] = x[i] + feedback * echo
        y[i] = (1 - mix) * x[i] + mix * echo
    return y


def _ir(decay, seed):
    """Synthetic exponentially-decaying noise impulse response (plate/hall)."""
    rng = np.random.default_rng(seed)
    n = int(decay * SR)
    t = np.arange(n) / SR
    ir = rng.standard_normal(n) * np.exp(-t / (decay / 4))
    ir[0] = 1.0
    return ir / (np.max(np.abs(ir)) + 1e-9)


def _rev_chan(x, decay, seed):
    wet = fftconvolve(x, _ir(decay, seed))[:len(x)]   # FFT = fast even when long
    return wet / (np.max(np.abs(wet)) + 1e-9)


def reverb(x, decay=2.5, mix=0.35, seed=1):
    """Mono reverb."""
    return (1 - mix) * x + mix * _rev_chan(x, decay, seed)


def reverb_st(x, decay=3.0, mix=0.35, seed=1):
    """Stereo reverb: two DECORRELATED impulse responses (different seeds) for
    L and R -> an enveloping room rather than a mono wash. Accepts mono or
    stereo input, always returns stereo (N, 2)."""
    if np.ndim(x) == 1:
        x = np.stack([x, x], axis=1)
    wet = np.stack([_rev_chan(x[:, 0], decay, seed),
                    _rev_chan(x[:, 1], decay, seed + 101)], axis=1)
    return (1 - mix) * x + mix * wet


def shimmer_halo(x, decay=4.0, seed=5):
    """Shimmer: reverberate, pitch the wet up an octave, reverberate again ->
    a rising angelic halo. Returns a normalized mono signal to add in."""
    wet = _rev_chan(x, decay, seed)
    n = len(wet)
    idx = np.arange(0, n, 2.0)                        # read 2x faster = +1 octave
    up = np.interp(idx, np.arange(n), wet)
    octv = np.zeros(n)
    octv[:len(up)] = up
    return _rev_chan(octv, decay, seed + 7)


def soft_clip(x, drive=1.0):
    """tanh saturation — gentle analog-style nonlinearity / harmonic warmth."""
    return np.tanh(drive * x)


# ---------------------------------------------------------------------------
# Stereo / space — placement, width, motion, rhythmic echo
# ---------------------------------------------------------------------------

def pan(x, p):
    """Constant-power pan of a mono signal. p in [-1, 1] (scalar or per-sample
    array): -1 = hard left, 0 = center, +1 = hard right. Returns (N, 2).
    Normalized so center is ~unity gain."""
    p = np.clip(p, -1, 1)
    ang = (p + 1) * 0.25 * np.pi
    return np.stack([x * np.cos(ang) * np.sqrt(2),
                     x * np.sin(ang) * np.sqrt(2)], axis=1)


def stereo_width(st, w):
    """Mid/side width control. w: 0 = mono, 1 = as-is, >1 = wider. Scalar or
    per-sample array (so width can collapse over time)."""
    L, R = st[:, 0], st[:, 1]
    mid, side = 0.5 * (L + R), 0.5 * (L - R)
    return np.stack([mid + w * side, mid - w * side], axis=1)


def autopan(st, rate=0.1, depth=0.3):
    """Slowly sweep a stereo signal left<->right (the eyes moving around you)."""
    n = st.shape[0]
    p = depth * np.sin(2 * np.pi * rate * np.arange(n) / SR)
    ang = (p + 1) * 0.25 * np.pi
    return np.stack([st[:, 0] * np.cos(ang) * np.sqrt(2),
                     st[:, 1] * np.sin(ang) * np.sqrt(2)], axis=1)


def pingpong(x, time=0.5, feedback=0.45, mix=0.35, taps=10):
    """Tempo-synced ping-pong delay: echoes of a mono signal alternate L/R,
    decaying — rhythmic ripples that move across the field."""
    n = len(x)
    d = int(time * SR)
    L, R = np.zeros(n), np.zeros(n)
    for k in range(1, taps + 1):
        shift = k * d
        if shift >= n:
            break
        seg = np.zeros(n)
        seg[shift:] = x[:n - shift] * (feedback ** k)
        if k % 2:
            L += seg
        else:
            R += seg
    dry = np.stack([x, x], axis=1)
    wet = np.stack([L, R], axis=1)
    return (1 - mix) * dry + mix * wet


def as_stereo(x):
    """Ensure (N, 2)."""
    return x if np.ndim(x) == 2 else np.stack([x, x], axis=1)


# ---------------------------------------------------------------------------
# Sampling — ingest and reshape real recordings (e.g. NASA space audio)
# ---------------------------------------------------------------------------

def load_audio(path, mono=False):
    """Decode any audio file (mp3/wav) to a float array at SR via ffmpeg.
    Peak-normalized. Returns mono (N,) if mono=True, else stereo (N, 2)."""
    import subprocess
    import tempfile
    import os
    from scipy.io import wavfile
    ch = '1' if mono else '2'
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
        tmp = f.name
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', path,
                    '-ar', str(SR), '-ac', ch, tmp], check=True)
    _, x = wavfile.read(tmp)
    os.unlink(tmp)
    x = x.astype(np.float64)
    x /= (np.max(np.abs(x)) + 1e-9)
    return x


def resample_speed(x, speed):
    """Play a signal at `speed` (linear interpolation). speed<1 -> longer and
    lower (pitched down); speed>1 -> shorter and higher. Works on mono/stereo."""
    n = len(x)
    new_n = max(1, int(n / speed))
    idx = np.linspace(0, n - 1, new_n)
    src = np.arange(n)
    if np.ndim(x) == 2:
        return np.stack([np.interp(idx, src, x[:, 0]),
                         np.interp(idx, src, x[:, 1])], axis=1)
    return np.interp(idx, src, x)


def loop_to(x, n_out, xfade=0.5):
    """Loop a signal to exactly n_out samples with a crossfade at each seam so
    it tiles seamlessly into a continuous bed."""
    st = as_stereo(x)
    n = len(st)
    xf = min(int(xfade * SR), n // 2)
    if xf > 0:
        head = st[:xf] * np.linspace(0, 1, xf)[:, None]
        tail = st[-xf:] * np.linspace(1, 0, xf)[:, None]
        body = st[xf:n - xf]
        unit = np.concatenate([head + tail, body])  # seam crossfaded
    else:
        unit = st
    reps = int(np.ceil(n_out / len(unit))) + 1
    out = np.tile(unit, (reps, 1))
    return out[:n_out]


def reverse(x):
    return x[::-1].copy()


def ringmod(x, freq):
    """Ring modulation: multiply by a sine carrier -> inharmonic, metallic, alien."""
    st = as_stereo(x)
    t = np.arange(len(st)) / SR
    car = np.sin(2 * np.pi * freq * t)[:, None]
    return st * car


def bitcrush(x, bits=8, rate=SR):
    """Quantize amplitude (bits) and decimate sample rate (rate) -> grit/decay."""
    st = as_stereo(x).copy()
    levels = 2 ** bits
    st = np.round(st * levels) / levels
    if rate < SR:
        step = int(SR / rate)
        st = np.repeat(st[::step], step, axis=0)[:len(x)]
    return st


def convolve_with(x, ir, mix=1.0):
    """Convolve a signal with `ir` used as an impulse response — imprints the
    spectral/temporal character of `ir` (e.g. the Jupiter sample) onto x."""
    xs = as_stereo(x)
    irm = ir if np.ndim(ir) == 1 else ir.mean(1)
    irm = irm / (np.max(np.abs(irm)) + 1e-9)
    wetL = fftconvolve(xs[:, 0], irm)[:len(xs)]
    wetR = fftconvolve(xs[:, 1], irm)[:len(xs)]
    wet = np.stack([wetL, wetR], axis=1)
    wet /= (np.max(np.abs(wet)) + 1e-9)
    return (1 - mix) * xs + mix * wet


def spectral_drone(x, dur_out, seg=2.0, seed=0):
    """Take the magnitude spectrum of a segment of `x` and re-excite it with
    noise -> a sustained drone carrying the sample's timbre (its 'colour'),
    at any length, with no pitch/loop artifacts."""
    rng = np.random.default_rng(seed)
    mono = x if np.ndim(x) == 1 else x.mean(1)
    s = mono[:int(seg * SR)]
    mag = np.abs(np.fft.rfft(s))
    n_out = int(dur_out * SR)
    out = np.zeros((n_out, 2))
    for ch in range(2):
        noise = rng.standard_normal(n_out)
        Nz = np.fft.rfft(noise)
        shaped = np.interp(np.linspace(0, 1, len(Nz)),
                           np.linspace(0, 1, len(mag)), mag) * np.exp(1j * np.angle(Nz))
        out[:, ch] = np.fft.irfft(shaped, n=n_out)
    return out / (np.max(np.abs(out)) + 1e-9)


def granular_cloud(x, dur_out, grain=0.09, density=28, pitch=1.0,
                   pitch_jitter=0.0, pan_spread=0.6, seed=0):
    """Granular synthesis: chop `x` into windowed grains and scatter them into
    a stereo cloud — the core tool for turning a recording into an evolving
    texture/drone. density = grains per second; pitch shifts each grain."""
    rng = np.random.default_rng(seed)
    mono = x if np.ndim(x) == 1 else x.mean(1)
    n_out = int(dur_out * SR)
    out = np.zeros((n_out, 2))
    gn = int(grain * SR)
    src_n = len(mono)
    for _ in range(int(density * dur_out)):
        pos = int(rng.uniform(0, max(1, src_n - gn)))
        g = mono[pos:pos + gn] * np.hanning(gn)
        p = pitch * 2 ** (rng.uniform(-pitch_jitter, pitch_jitter) / 12)
        if abs(p - 1.0) > 1e-3:
            m = max(4, int(gn / p))
            g = np.interp(np.linspace(0, gn - 1, m), np.arange(gn), g) * np.hanning(m)
        at = int(rng.uniform(0, max(1, n_out - len(g) - 1)))
        pan = rng.uniform(-pan_spread, pan_spread)
        ang = (pan + 1) * 0.25 * np.pi
        out[at:at + len(g), 0] += g * np.cos(ang)
        out[at:at + len(g), 1] += g * np.sin(ang)
    return out / (np.max(np.abs(out)) + 1e-9)


# ---------------------------------------------------------------------------
# Mixing / output
# ---------------------------------------------------------------------------

def mix_at(canvas: np.ndarray, sig: np.ndarray, at: float, gain=1.0):
    """Add `sig` into `canvas` starting at time `at` seconds (in place)."""
    start = int(at * SR)
    end = start + len(sig)
    if end > len(canvas):
        canvas = np.concatenate([canvas, np.zeros(end - len(canvas))])
    canvas[start:end] += gain * sig
    return canvas


def normalize(x, peak=0.89):
    m = np.max(np.abs(x)) + 1e-9
    return x / m * peak


def to_stereo(left, right=None):
    if right is None:
        right = left
    return np.stack([left, right], axis=1)


def write_wav(path, x, peak=0.89):
    """Write mono or stereo float array to 16-bit WAV."""
    from scipy.io import wavfile
    x = np.asarray(x, dtype=np.float64)
    x = x / (np.max(np.abs(x)) + 1e-9) * peak
    pcm = np.int16(np.clip(x, -1, 1) * 32767)
    wavfile.write(path, SR, pcm)
    return path

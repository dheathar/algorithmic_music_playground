# The Patch Format — the shared "ingredient" language

A **patch** is a small JSON file that describes one sound. Both the browser
benches (export) and the Python engine (`patch.py` → `synth.py`) read it, so a
sound you sculpt by hand can be rendered through the real engine and dropped
into a composition.

## Schema

```jsonc
{
  "v": 1,                       // schema version
  "name": "warm-saw",           // used as the download/render filename
  "dur": 3.0,                   // seconds (single-note patches)
  "note": "A3",                 // pitch by name … or:
  "freq": 220,                  // … pitch in Hz (note wins if both present)

  "osc": {                      // the oscillator
    "type": "additive|fm|wave",
    "harmonics": [1, 0.5, 0.3], // additive: amplitude per harmonic (≤16)
    "wave": "saw|square|sine|triangle",   // wave / fm carrier shape
    "ratio": 2.0, "index": 200, // fm: modulator ratio + index (Hz dev or β)
    "voices": 1, "detune": 8    // unison voices + detune (cents)
  },

  "filter": { "type": "lowpass|highpass|bandpass|notch",
              "cutoff": 1200, "q": 6, "env_amt": 0.6 },  // env_amt sweeps cutoff

  "env": { "a": 0.02, "d": 0.2, "s": 0.6, "r": 0.4 },    // amplitude ADSR (sec)

  "lfo": { "target": "none|filter|pitch|amp", "rate": 5, "depth": 0.4 },

  "fx": { "reverb": 0.35, "delay": 0.3, "delay_time": 0.3,
          "width": 0.6, "drive": 1.0 },

  // OPTIONAL — turns the patch into a phrase instead of one note:
  "tempo": 104, "root": "A", "scale": "phrygian",
  "sequence": [ { "step": 0, "deg": 4 }, { "step": 2, "deg": 2 } ]
  //   step = 16th-note index;  deg = scale degree (0 = root, ascending)
}
```

## Render it
- **CLI:** `./.venv/bin/python patch.py mypatch.json out.wav`
- **Backend:** `POST` the JSON to `http://127.0.0.1:7700/render` → returns a WAV
  (this is what the benches' **▶ Render in engine** button does).
- **In a composition:**
  ```python
  from patch import load_patch, render_patch
  organ = render_patch(load_patch('patches/warm-saw.json'), dur=DUR)  # -> (N,2)
  organs['my_voice'] = (organ, 0.6)
  ```

## Which bench exports what
- **Additive** → `osc.type=additive` with `harmonics` (the drawbars).
- **FM** → `osc.type=fm` with `ratio`, `index`.
- **Filter** → `osc.type=wave` + `filter`.
- **Envelope & Mod** → `env` + `lfo`.
- **Space** → `fx` (width / reverb / delay).
- **Live** / **Studio** → a `sequence` patch (the grid → steps + degrees).

All DSP is `synth.py`; nothing is reimplemented. See `CONSTITUTION.md` §6.

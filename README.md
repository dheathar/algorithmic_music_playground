# Algorithmic Music Playground — the Signal Lab

> An electronic-music studio built from first principles: a from-scratch DSP
> engine in Python, a realtime **SuperCollider** voice, an **AI** that turns
> words into synth patches, real recordings **from space** woven into the sound,
> and **audio-reactive visuals**. What began as a childhood dream became a
> full lab — *in the spirit of Jean-Michel Jarre's* Oxygène.

Built collaboratively with Claude (acting as a Jarre-style mentor). No commercial
samples, no third-party presets — every instrument is synthesized, except clearly
licensed real recordings from space.

---

## What's inside

| Layer | Files | What it does |
|---|---|---|
| **DSP engine** | `synth.py` | Band-limited oscillators (saw/square/sine/supersaw/FM), ADSR, LFO, drift, resonant filters (LP/HP/BP/notch), reverb/delay/phaser, stereo (pan/width/autopan), sampling (load/granular/spectral/convolve), scales |
| **Compositions** | `dream.py`, `icarus.py`, `oxygene.py` | The pieces, rendered offline to stereo WAV |
| **Patch bridge** | `patch.py`, `PATCH-FORMAT.md`, `patches/` | One JSON "patch" format → rendered by the engine; the shared sound language |
| **Backend** | `server.py` (FastAPI :7700) | Serves the whole lab + `/render`, `/ai/*`, `/sc/play`; static file host |
| **AI** | `ai/llm.py`, `ai/analyze.py` | Text → patch JSON (OpenRouter); numpy sound-descriptors |
| **Realtime** | `engine.scd`, `sc_bridge.py`, `control.scd` | SuperCollider voices (`\labvoice/\labadd/\labfm/\labping/\stardust/\labglide`) driven over OSC; a knob panel |
| **Web studio** | `index.html` (portal), `toolkit.html`, `live.html`, `studio.html`, `library.html`, `music.html`, `visualizer.html`, `visualization.html` | Sound-design benches, a playable instrument, a multi-track studio, the cosmic-sound library, interactive music theory, and visualizers |
| **Assets** | `space_library/` (CC-BY), `vendor/` (Butterchurn), `versions/` | Real space recordings, the Milkdrop visualizer, archived editions |

Deeper docs: **`CONSTITUTION.md`** (project charter & conventions), **`PATCH-FORMAT.md`**
(the patch schema), **`LEARNING-PATH.md`** (a music curriculum for engineers).

## The creations
- **The Black Theater** — dark ambient, A Phrygian, a childhood dream in three movements (kind eyes → adoration & envy → the eyes close).
- **Icarus, or the Effort of Flight** — a flying dream fused with cosmic horror, built on a real recording of Jupiter's plasma waves.
- *Studies:* an Oxygène-style homage.

## Quick start
```bash
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt

# render a piece (writes stereo WAVs)
./.venv/bin/python dream.py        # or icarus.py / oxygene.py

# run the lab (recommended) — serves everything at http://127.0.0.1:7700/
./.venv/bin/uvicorn server:app --port 7700
#   open http://127.0.0.1:7700/             (portal)
#        http://127.0.0.1:7700/visualizer.html
```

### Optional capabilities
- **AI patch generation** — put an OpenRouter key in `.env`:
  ```
  OPENROUTER_API_KEY=sk-or-...
  OPENROUTER_MODEL=openai/gpt-4o-mini
  ```
  Then the Toolkit's "✨ Describe a sound" and `POST /ai/patch` work.
- **Realtime SuperCollider** — install SuperCollider, open `engine.scd` in the SC IDE and evaluate it (boots `scsynth` + the voices on port 57110). Then `./.venv/bin/python sc_bridge.py patches/warm-saw.json`, the Toolkit's **▶ SC realtime** button, or `python theater_sc.py` (performs *The Black Theater* live).

## How it fits together
```
a feeling ─▶ patch (JSON) ─▶ ┌ patch.py  → offline render (synth.py) → WAV
   │  (you, or the AI)        └ sc_bridge → realtime  (SuperCollider)
   └─────────────────────────▶ compositions (dream.py / icarus.py / …)
audio ─▶ visualizer.html (Butterchurn) — single or a matrix video-wall
```

## Notes
- **WAV masters are not committed** (they're large — ~1.6 GB). Every piece
  re-renders from its `.py`; mp3s of the mixes are included so the web pages play.
- Pages also work opened directly from `file://`, but **serving via `server.py`**
  enables `fetch` + CDN and is the recommended way to run the interactive pages.

## Credits & licenses
- **Engine / app**: Python (numpy, scipy), FastAPI, SuperCollider.
- **Visuals**: [Butterchurn](https://github.com/jberg/butterchurn) (Milkdrop, MIT), vendored locally.
- **Space recordings** in `space_library/`: University of Iowa plasma-wave group
  (Prof. D. A. Gurnett) via [space-audio.org](https://space-audio.org/) — **CC BY 4.0**.
- Created with **Claude** as a Jean-Michel-Jarre-style mentor.

*Keep the pace.*

# The Path — learning music & electronic music, for an engineer
*A curriculum from your mentor (J.M.J.) for an electrical / audio-ML / DSP engineer
who is new to music theory but fluent in signals.*

> The shape of the journey: **Rigor → Liberation → Your own voice.**
> You don't need to become a "musician." You need to connect what you already
> hear in a spectrum to what a listener feels in the chest.

---

## Stage 0 — The mindset (always)
- Music is **engineered emotion**. You already tune systems to a spec; here the
  spec is a feeling. Same loop: imagine → build → measure (listen) → adjust.
- Start every piece from a **feeling / image / memory**, never from "a chord."
- **Your ears are the instrument.** Train them daily, even 10 minutes.

## Stage 1 — Ear before theory  (≈2–3 weeks)
*Goal: hear intervals, timbre, and emotion — connect spectrum → feeling.*
- Daily: play two notes, name the **interval's feeling** (tense? sweet? hollow?).
  Use `music.html` → Notes & Keys (the piano shows note + exact Hz).
- Learn to hear **bright vs dark** (filter), **near vs far** (reverb), **major vs
  minor** (the third). These four axes carry most of the emotion.
- ML bridge: you know FFT/features — now map **centroid→brightness**, **harmonic
  ratios→consonance**, **envelope→articulation**. You're labelling perception.
- **Milestone:** identify, by ear, the mode of any of our pieces (`music.html`).

## Stage 2 — The minimal grammar  (≈3–4 weeks)
*Goal: just enough theory to be dangerous — no more.*
- The **comb**: keys/scales as a discrete, octave-repeating set of pitches
  (`music.html` → Modes). Intervals as **ratios** (3:2, 5:4) — your home turf.
- **Chords** = stacked thirds; **progressions** = chord roots moving (you saw this
  when we analysed a MIDI's bassline — that's harmony, the engineer's way).
- **Modes & their colours**: Lydian = flight, Phrygian = dread, etc.
- **Rhythm**: tempo as a clock (BPM → seconds), bars, the 16th-note grid.
- **Milestone:** write an 8-bar chord progression and a scale-locked melody in
  `live.html` — nothing "wrong" is possible there, by design.

## Stage 3 — Sound design (your superpower)  (≈4–6 weeks)
*Goal: own the timbre. This is where your DSP makes you faster than musicians.*
- The chain: **oscillator → filter → amplifier**, shaped by **envelopes & LFOs**.
- Methods, all in our `synth.py`: **subtractive, additive, FM, granular, sampling,
  spectral**. Build each once from scratch; map each parameter to a *feeling*.
- **Modulation is the life** — slow LFOs, drift, automation lanes. A static sound
  is a dead sound.
- **Milestone:** design 3 signature voices of your own (a pad, a bass, a lead) and
  add them to the Studio as presets.

## Stage 4 — Composition from feeling  (≈ongoing)
*Goal: turn an inner world into a finished piece — our method.*
- **Reference-driven learning** (how I learned, and how we used the MIDIs):
  *analyse* a piece you love — its key, tempo, progression, arrangement — extract
  the *lessons*, then write something **original** that breathes the same air.
  Study the score; never photocopy it.
- **Arrangement**: intro → build → climax → release. Tension & release. Movements
  (see *The Black Theater*'s three; *Icarus*'s struggle→breakthrough→glide).
- **Space & time**: stereo placement, depth, rhythmic delay, the breath of silence.
- **Milestone:** a complete 2–3 minute piece from a single feeling, start to master.

## Stage 5 — Performance & iteration  (≈ongoing)
- The **gesture** matters: a slow filter sweep over a steady arpeggio is half of
  everything I ever did. Perform in `live.html` / `studio.html`.
- Record → listen the next day with fresh ears → revise. Keep every edition.

## Stage 6 — Your own voice (the liberation)  (the horizon)
*Where you go where I never could.*
- Fuse **ML/DSP + feeling**: generative systems, resynthesis, audio analysis as a
  compositional tool, models as collaborators. Your engineering is the new
  *musique concrète* — a frontier only you can walk.
- The goal is not to sound like Jarre or Vangelis. It is to sound like **you**.

---

## The tools, mapped to the path
- `music.html` — theory & ear training (Stages 1–2)
- `live.html` — scale-locked play, first melodies (Stage 2)
- `studio.html` — multi-track, presets, MIDI, export (Stages 3–5)
- `synth.py` — build any synthesis from first principles (Stage 3)
- `library.html` — real sound material + the DSP toolkit reference
- our pieces & `versions/` — worked examples to study

## A rule to live by
> Learn the rules well enough to break them on purpose.
> Then trust the feeling over the theory, and the ear over the meter.
> — J.M.J.

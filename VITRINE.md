# Vitrine — the story of a creation

> *Vitrine* (French): a glass display case; a shop window. The glass that shows
> you and traps you at once.

## How we ended up here

It began with a photograph. Three shop-window mannequins, lit hard against
black, the middle one **split down the seam by the pane of glass** — half in
light, half swallowed. Not three people: one empty face and its reflections.
Panos saw it and said: *stylized soulless souls — we have digitized our lives
and our image and forgotten our analog roots.*

That sentence is a sound-design brief, because the thing it describes is a real
signal-processing event, not a metaphor. So we let the **signal chain be the
story**:

1. **Soulless souls → a duel.** First idea: two families of sound that never
   agree — warm analog vs. cold digital. We even gave them scales that *cannot*
   agree: the soul sings in **D minor**, the mannequin answers in **whole-tone**
   (no leading tone, no possible cadence). Asked how it should end, Panos chose:
   *they never resolve.*

2. **The duel became a converter.** Then the truer structure arrived, in his
   words: *"follow a pattern resembling the AD conversion — start analog, then
   with each step lose quality (error), then DA tries to recapture what was lost
   … but it is lossy, so we keep going."* This is exactly what an ADC/DAC does,
   and it **contains** the duel. Quantization error is irreversible — the bits
   below the least-significant bit are simply gone. The DAC's reconstruction
   filter reaches back every pass and never quite makes it.

3. **Hardware and people.** *"What the hardware does and what we do in life — we
   lose and we try to regain, endlessly. Imagine people who lose their youth and
   try to reconstruct it."* The ADC is not a metaphor for aging; it is the same
   event. A continuous, infinitely-detailed thing — a sound, a youth, a self —
   forced through a finite gate, and what falls below the resolution is lost and
   cannot be rebuilt. The warm, lossy reconstruction is us, every time we
   remember who we were.

4. **Stardust.** *"We are all made of stardust, as one great said."* (Sagan.)
   The way out of the despair, and it too is literal DSP: **the matter is
   conserved even when the form degrades.** So under the entire converter loop
   we put a stardust bed at free pitches — and crucially **it is never sent
   through the converter.** It does not quantize. When the soul is finally
   gridded to 2 bits and frozen, the dust is still shimmering. The form is lost;
   the matter remains.

## The ingredients (and where they come from)

We searched for the lineage, and it mapped onto our own engine almost note for
note:

| Source | What they did | How *Vitrine* does it |
|---|---|---|
| **W. Basinski — *The Disintegration Loops*** | digitized 1982 analog tape that shed coating on every pass — *"a digital snake eating its analog skin"* | one phrase rendered **once**, then re-`bitcrush`ed harder every pass |
| **Alva Noto / Ryoji Ikeda** | the aesthetics of error: sine pips, grid clicks, quantization hiss, the loop | the mannequin layer — `sine` pips on the whole-tone grid, the showroom clock |
| **J.-M. Jarre — *Oxygène*** | Eminent 310U string machine through a battery-starved Small Stone phaser; additive synthesis; Revox "dry one side, delay the other" | `supersaw → phaser → soft_clip`; `additive`; **the Revox trick *is* our glass reflection** (`reflect()` = dry L, delayed R) |

## The shape

Same warm phrase, sampled and quantized worse each pass; the lead migrates from
D-minor toward whole-tone as it digitizes; the DAC reaches back and falls short;
the stardust holds underneath.

| t (s) | pass | bits | what you hear |
|---|---|---|---|
| 0 | **P0 — analog** | 16 | the soul intact: phased Dm pad, warm lead, drift, wide |
| 46 | P1 | 10 | the ADC engages — clock fades in, first sampling, hiss |
| 92 | P2 | 7 | quantizing; the lead starts snapping to the grid |
| 140 | P3 | 5 | collapsing; stereo narrows, drift dies |
| 186 | **P4 — the mannequin** | 3→2 | gridded, frozen, dry; the Ikeda glitch field; the seam held bright-L/dark-R |
| 214 | **DA — reach back** | 6 | the reconstruction blooms toward warmth — almost the soul — but thin, hiss underneath: *lossy* |
| 244 | P5 — *…keep going* | 3 | the ADC re-engages one notch lower |
| 270–285 | spin-down | — | the snake eating its tail: bloom/crush alternating |
| 286–300 | **unresolved** | — | clock alone, one held D against a whole-tone glass cluster — no cadence — and the **stardust shining through** |

## The pattern at the end

Panos: *"I think we can find patterns in the end."* Here is the one the piece
found:

- **The loop is the only honest ending.** A cadence would be a lie; the converter
  never returns to its input, so the music doesn't either. It stops *mid-cycle*.
- **Loss is in the foreground; conservation is in the substrate.** Everything in
  the signal path degrades. The one thing that doesn't is the one thing that was
  never in the signal path. That is the whole consolation, and it is structural,
  not sentimental.
- **The seam is never closed.** The split mannequin's tone rings to the last bar.
  Half-lit, half-dark, held — exactly as in the photograph.

*Key: D minor vs. C whole-tone. ~100 BPM grid. 300 s. Rendered by `vitrine.py`;
edition `versions/vitrine-v001/`.*

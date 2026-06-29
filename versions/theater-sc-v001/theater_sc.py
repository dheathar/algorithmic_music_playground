"""
theater_sc.py — re-voice "The Black Theater" organs on the new instrument.

The FULL pipeline: each organ's *character* is described in words -> the AI
(OpenRouter) writes a patch -> validate -> play in realtime through SuperCollider.
We keep the dream's notes & shape; the AI (or a handcrafted fallback) designs the
timbre. SuperCollider (engine.scd) must be running.

  ./.venv/bin/python theater_sc.py          # AI-designed timbres
  ./.venv/bin/python theater_sc.py --no-ai  # handcrafted fallback only
"""
import sys
import time
import copy
import os
import shutil
import numpy as np
import synth as S
from patch import render_patch

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
except Exception:
    pass

from sc_bridge import play_patch
from patch import validate_patch
try:
    from ai.llm import generate as ai_generate
except Exception:
    ai_generate = None

USE_AI = "--no-ai" not in sys.argv

# how each organ should *sound* (the AI reads these)
PROMPTS = {
    "audience": "a vast, dark, hollow drone — very slow swell, low filter cutoff, heavy reverb, ominous and watching",
    "pedal":    "a deep warm drawbar pipe-organ pedal tone, round and sustained, low",
    "child":    "a breathy hollow flute voice with gentle vibrato, soft, lonely and exposed",
    "fishing":  "a deep round sonar ping, dark, with a long ringing decay and big reverb",
    "glint":    "a high glassy bell-like shimmer, slow attack, distant, drenched in reverb",
    "adore":    "a bright lush shimmering string pad, slowly swelling, adoring and warm",
    "envy":     "a tense dissonant detuned drone, beating and uneasy, dark",
}

# handcrafted fallbacks (also the originals' character)
FALLBACK = {
    "audience": {"osc": {"type": "wave", "wave": "saw", "voices": 2, "detune": 10},
                 "filter": {"type": "lowpass", "cutoff": 460, "q": 0.8},
                 "env": {"a": 3, "d": 0, "s": 1, "r": 4},
                 "lfo": {"target": "filter", "rate": 0.06, "depth": 0.25},
                 "fx": {"reverb": 0.5, "width": 0.6}},
    "pedal":    {"osc": {"type": "additive", "harmonics": [1, 0.6, 0.4, 0.22, 0, 0.1]},
                 "filter": {"type": "lowpass", "cutoff": 600, "q": 0.8},
                 "env": {"a": 3, "d": 0, "s": 1, "r": 4}, "lfo": {"target": "none"},
                 "fx": {"reverb": 0.35}},
    "child":    {"osc": {"type": "additive", "harmonics": [1, 0, 0.14]},
                 "filter": {"type": "lowpass", "cutoff": 2200, "q": 0.8},
                 "env": {"a": 0.4, "d": 0.25, "s": 0.75, "r": 0.7},
                 "lfo": {"target": "pitch", "rate": 5, "depth": 0.12},
                 "fx": {"reverb": 0.45, "width": 0.5}},
    "fishing":  {"osc": {"type": "ping"},   # struck sounding (pitch-drop + decay), not a held sine
                 "filter": {"type": "lowpass", "cutoff": 1200, "q": 0.8},
                 "env": {"a": 0.01, "d": 2.5, "s": 0, "r": 1.5}, "lfo": {"target": "none"},
                 "fx": {"reverb": 0.6, "delay": 0.0, "width": 0.5}},
    "glint":    {"osc": {"type": "additive", "harmonics": [1, 0, 0.3, 0, 0.15]},  # hollow bell body
                 "filter": {"type": "lowpass", "cutoff": 2500, "q": 0.7},          # soft, no glass
                 "env": {"a": 0.2, "d": 0.3, "s": 0.0, "r": 1.2},                  # bloom & FADE (not sustained)
                 "lfo": {"target": "none"}, "fx": {"reverb": 0.7, "width": 0.7}},
    "adore":    {"osc": {"type": "wave", "wave": "saw", "voices": 2, "detune": 12},
                 "filter": {"type": "lowpass", "cutoff": 1500, "q": 0.8},
                 "env": {"a": 4, "d": 0, "s": 1, "r": 5},
                 "lfo": {"target": "filter", "rate": 0.1, "depth": 0.3},
                 "fx": {"reverb": 0.55, "width": 0.7}},
    "envy":     {"osc": {"type": "wave", "wave": "saw", "voices": 2, "detune": 22},
                 "filter": {"type": "lowpass", "cutoff": 800, "q": 0.9},
                 "env": {"a": 3, "d": 0, "s": 1, "r": 4}, "lfo": {"target": "none"},
                 "fx": {"reverb": 0.5, "width": 0.5}},
    # a footstep: a soft, muffled low thud with a faint theatre echo (always handcrafted)
    "footsteps": {"osc": {"type": "wave", "wave": "sine"},
                  "filter": {"type": "lowpass", "cutoff": 300, "q": 0.9},
                  "env": {"a": 0.004, "d": 0.18, "s": 0.0, "r": 0.2}, "lfo": {"target": "none"},
                  "fx": {"reverb": 0.4, "width": 0.4}},
    # soft random sine twinkles — analog cosmic glitter (replaces the bell-glint)
    "stardust": {"osc": {"type": "stardust", "density": 7, "lo": 1500, "hi": 4500},
                 "filter": {"type": "lowpass", "cutoff": 6000, "q": 0.7},
                 "env": {"a": 1.5, "d": 0, "s": 1, "r": 1.5}, "lfo": {"target": "none"},
                 "fx": {"reverb": 0.6, "width": 0.7}},
}


def timbre(name):
    if USE_AI and ai_generate:
        try:
            p = validate_patch(ai_generate(PROMPTS[name]))
            print(f"  {name:9s} ← AI: {p.get('name','patch')}")
            return p
        except Exception as e:
            print(f"  {name:9s} ← AI failed ({e}); using fallback")
    else:
        print(f"  {name:9s} ← handcrafted")
    return validate_patch(FALLBACK[name])


# A Phrygian — the black of the theater. (time, organ, note, dur, amp)
SCORE = [
    # ---- I · KIND EYES (0–30): warm, sparse, safe ----
    (0, "pedal", "A1", 32, 0.09),
    (0, "audience", "A1", 32, 0.07), (0, "audience", "E2", 32, 0.06), (0, "audience", "A2", 32, 0.05),
    # lonely footsteps — the child paces onto the dark stage (uneven, human)
    (2.0, "footsteps", "A2", 0.35, 0.12), (2.8, "footsteps", "G2", 0.35, 0.11),
    (3.7, "footsteps", "A2", 0.35, 0.12), (4.7, "footsteps", "F2", 0.35, 0.10),
    (14, "fishing", "A3", 5, 0.11),   # first sounding enters later, into texture (never naked)
    (7, "child", "E4", 1.6, 0.14), (8.8, "child", "D4", 1.4, 0.14), (10.4, "child", "C4", 2.6, 0.14),
    (15, "glint", "E4", 1.6, 0.05),
    (18, "child", "E4", 1.4, 0.13), (19.6, "child", "G4", 1.2, 0.13), (21, "child", "A4", 3, 0.13),
    (24.5, "footsteps", "A2", 0.35, 0.11), (25.6, "footsteps", "E2", 0.35, 0.10), (26.6, "footsteps", "A2", 0.35, 0.10),
    (22, "fishing", "C4", 5, 0.12),
    (11, "stardust", "A3", 26, 0.022),          # glitter begins — faint, distant (one evolving presence)
    # ---- II · ADORATION & ENVY (30–66): swell, but THINNED so the limiter stays calm ----
    (30, "pedal", "A1", 38, 0.06),
    (30, "audience", "A1", 38, 0.06), (30, "audience", "E2", 38, 0.045),   # 2 drone notes, not 3
    (40, "adore", "E3", 22, 0.04), (43, "adore", "A3", 20, 0.035),          # 2 shimmer notes, staggered
    (50, "envy", "A#3", 14, 0.03),                                          # 1 envy note, faint
    (34, "child", "A4", 1.2, 0.12), (35.3, "child", "C5", 1.2, 0.12), (36.9, "child", "E5", 2.2, 0.12),
    (50, "child", "F4", 1.2, 0.12), (51.4, "child", "A4", 1.1, 0.12), (52.6, "child", "A#4", 1.6, 0.11), (56, "child", "E5", 2.6, 0.12),
    (38, "fishing", "E4", 5, 0.11), (54, "fishing", "A4", 5, 0.10),
    (34, "stardust", "A3", 18, 0.038), (48, "stardust", "A3", 20, 0.055),   # swells into the adoration peak
    # ---- III · THE EYES CLOSE (66–96): thin, dark, fading (lower levels = no end clip) ----
    (66, "pedal", "A1", 30, 0.05),
    (66, "audience", "A1", 30, 0.05), (66, "audience", "E2", 30, 0.035),
    # the final, lonely walk off the stage — steps fading into the dark
    (68, "footsteps", "A2", 0.35, 0.10), (69.1, "footsteps", "G2", 0.35, 0.10),
    (70.3, "footsteps", "E2", 0.35, 0.09), (71.6, "footsteps", "A2", 0.35, 0.08), (73.2, "footsteps", "F2", 0.35, 0.07),
    (72, "child", "C4", 2.4, 0.10), (75, "child", "A3", 2.4, 0.10), (78, "child", "E3", 3.2, 0.09), (84, "child", "A3", 5, 0.09),
    (86, "footsteps", "E2", 0.35, 0.06), (88.4, "footsteps", "A2", 0.35, 0.05),   # last steps, fading
    (82, "fishing", "A3", 6, 0.07),   # one last sounding — softer, so the ending doesn't pile up
    (66, "stardust", "A3", 24, 0.032), (84, "stardust", "A3", 12, 0.02),   # recede, then the last glimmers
]


def save_instruments():
    """Save each organ as a reusable instrument patch in patches/theater/."""
    import json
    d = os.path.join("patches", "theater")
    os.makedirs(d, exist_ok=True)
    for name, p in FALLBACK.items():
        inst = validate_patch(dict(p, name="theater-" + name))
        inst["note"], inst["dur"] = "A3", 3.0
        with open(os.path.join(d, name + ".json"), "w") as f:
            json.dump(inst, f, indent=2)
    print(f"saved {len(FALLBACK)} reusable instruments -> {d}/")


def render_offline(voices, outname="theater_sc"):
    """Render the full score to a WAV via the Python engine, and archive it."""
    total = max(t + dur for (t, org, note, dur, amp) in SCORE) + 4
    N = int(total * S.SR)
    canvas = np.zeros((N, 2))
    for (t, org, note, dur, amp) in SCORE:
        sig = render_patch(copy.deepcopy(voices[org]), dur=dur, note=note)
        start = int(t * S.SR)
        end = min(start + len(sig), N)
        canvas[start:end] += amp * sig[:end - start]
    mix = S.soft_clip(canvas * 0.9, drive=1.0)
    S.write_wav(outname + ".wav", mix)
    vd = os.path.join("versions", "theater-sc-v001")
    os.makedirs(vd, exist_ok=True)
    shutil.copy(outname + ".wav", vd)
    shutil.copy("theater_sc.py", vd)
    print(f"rendered {outname}.wav ({round(total, 1)}s) -> archived {vd}/")
    return outname + ".wav"


def main():
    if "--save" in sys.argv:
        save_instruments()
    print("Designing the organs (" + ("AI pipeline" if USE_AI else "fallback") + ")…")
    voices = {name: timbre(name) for name in PROMPTS}
    # drones must behave like drones — override AI's env/brightness so they can't
    # click on or scream, while keeping the AI's chosen oscillator (its colour).
    DRONE_CUT = {"audience": 600, "pedal": 600, "envy": 700, "adore": 1400}
    for d, cap in DRONE_CUT.items():
        v = voices[d]
        v["env"] = {"a": 2.5, "d": 0, "s": 1, "r": 4}                 # slow swell, no click
        v.setdefault("filter", {})
        v["filter"]["type"] = "lowpass"
        v["filter"]["cutoff"] = min(float(v["filter"].get("cutoff", cap)), cap)  # keep it dark
        v["filter"]["q"] = min(float(v["filter"].get("q", 0.8)), 1.2)            # no resonance peak
        v["lfo"] = {"target": "filter", "rate": 0.06, "depth": 0.2}              # gentle breathing only
    # tame the high glint: soft bloom, dark, far back (keeps the AI's colour, not its glare)
    g = voices["glint"]
    g["env"] = {"a": 0.2, "d": 0.3, "s": 0.0, "r": 1.2}          # brief bell, never sustained
    g.setdefault("filter", {})
    g["filter"]["type"] = "lowpass"
    g["filter"]["cutoff"] = min(float(g["filter"].get("cutoff", 2500)), 2500)
    g["filter"]["q"] = min(float(g["filter"].get("q", 0.7)), 1.0)
    g["lfo"] = {"target": "none"}
    g["fx"] = dict(g.get("fx", {}), reverb=0.7, width=0.7)
    # the child = the singing wind, FORWARD and clear (not a blurred melodica)
    c = voices["child"]
    c["env"] = {"a": 0.15, "d": 0.2, "s": 0.7, "r": 0.5}
    c.setdefault("filter", {})
    c["filter"]["type"] = "lowpass"
    c["filter"]["cutoff"] = min(float(c["filter"].get("cutoff", 2600)), 2600)
    c["filter"]["q"] = min(float(c["filter"].get("q", 0.9)), 1.1)
    c["lfo"] = {"target": "pitch", "rate": 5, "depth": 0.08}
    c["fx"] = dict(c.get("fx", {}), reverb=0.3, width=0.5)
    # cut the reverb WASH across the bed so the music has focus (stardust keeps its tail)
    for nm, v in voices.items():
        v.setdefault("fx", {})
        v["fx"]["reverb"] = min(float(v["fx"].get("reverb", 0.3)), 0.35)
    voices["footsteps"] = validate_patch(FALLBACK["footsteps"])   # precise, never AI
    voices["stardust"] = validate_patch(FALLBACK["stardust"])     # precise, never AI
    if "--render" in sys.argv:
        render_offline(voices)
        return
    print("Performing 'The Black Theater' through SuperCollider…")
    t0 = time.monotonic()
    for (t, organ, note, dur, amp) in sorted(SCORE, key=lambda e: e[0]):
        wait = t - (time.monotonic() - t0)
        if wait > 0:
            time.sleep(wait)
        p = copy.deepcopy(voices[organ])
        p["note"], p["dur"], p["amp"] = note, dur, amp
        play_patch(p)
    time.sleep(6)
    print("…the eyes close.")


if __name__ == "__main__":
    main()

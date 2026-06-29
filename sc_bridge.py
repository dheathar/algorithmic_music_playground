"""
sc_bridge.py — drive SuperCollider (scsynth) in realtime from our patch format.

Translates a patch (the same JSON our engine + AI use) into an OSC /s_new message
for the \\labvoice SynthDef defined in engine.scd. SuperCollider becomes the
realtime voice; our Python stays the brain.

Setup: install SuperCollider, open engine.scd in the SC IDE and evaluate it
(boots scsynth + loads \\labvoice). Then:
    ./.venv/bin/python sc_bridge.py patches/warm-saw.json
or POST a patch to the server's /sc/play.
"""
import sys
import json
import time
import threading
from pythonosc.udp_client import SimpleUDPClient

import synth as S
from patch import validate_patch, load_patch

SC_HOST, SC_PORT = "127.0.0.1", 57110            # scsynth default OSC port

WAVE = {"saw": 0, "square": 1, "sine": 2, "triangle": 3}
FILT = {"lowpass": 0, "highpass": 1, "bandpass": 2, "notch": 0}
LFOT = {"none": 0, "filter": 1, "pitch": 2, "amp": 3}


def _common(pt, dur):
    """Args shared by all three SynthDefs (filter, env, fx, LFO)."""
    fl, env, fx, lf = pt["filter"], pt["env"], pt["fx"], pt["lfo"]
    # SC uses reciprocal-Q; clamp resonance so RLPF/RHPF can't self-oscillate into noise
    rq = 1.0 / max(0.8, min(8.0, float(fl["q"])))
    return ["amp", float(pt.get("amp", 0.25)), "cutoff", float(fl["cutoff"]), "rq", float(rq),
            "ftype", FILT.get(fl["type"], 0), "atk", float(env["a"]), "rel", float(env["r"]),
            "dur", float(dur), "revmix", float(fx["reverb"]), "pan", 0.0,
            "fenv", float(fl.get("env_amt", 0)),
            "lfot", LFOT.get(lf.get("target", "none"), 0),
            "lfor", float(lf.get("rate", 5)), "lfod", float(lf.get("depth", 0))]


def _synth_args(pt, freq, dur):
    """Pick the SuperCollider SynthDef for the patch's osc type, with its args."""
    osc = pt["osc"]
    common = _common(pt, dur)
    if osc["type"] == "ping":
        return "labping", ["freq", float(freq), "amp", float(pt.get("amp", 0.18)),
                           "dur", float(dur), "revmix", float(pt.get("fx", {}).get("reverb", 0.55)),
                           "pan", 0.0]
    if osc["type"] == "stardust":
        return "stardust", ["amp", float(pt.get("amp", 0.1)), "dur", float(dur),
                            "density", float(osc.get("density", 7)),
                            "revmix", float(pt.get("fx", {}).get("reverb", 0.6)),
                            "lo", float(osc.get("lo", 1500)), "hi", float(osc.get("hi", 4500))]
    if osc["type"] == "additive":
        h = (osc.get("harmonics") or [1.0])[:16]
        h = h + [0.0] * (16 - len(h))
        hargs = []
        for i, v in enumerate(h):
            hargs += ["h" + str(i + 1), float(v)]
        return "labadd", ["freq", float(freq)] + common + hargs
    if osc["type"] == "fm":
        ratio = float(osc.get("ratio", 2.0))
        idx = float(osc.get("index", 2.0))
        if idx > 20:                              # Hz deviation -> FM index β
            idx = idx / max(1.0, freq * ratio)
        idx = min(idx, 12.0)                       # cap β so FM can't turn to noise
        return "labfm", ["freq", float(freq), "ratio", ratio, "index", idx] + common
    return "labvoice", ["freq", float(freq), "wave", WAVE.get(osc.get("wave", "saw"), 0),
                        "voices", int(osc.get("voices", 1)), "detune", float(osc.get("detune", 8))] + common


def play_patch(patch, host=SC_HOST, port=SC_PORT):
    """Send the patch to scsynth. A 'sequence' is scheduled in a background
    thread; a single note fires immediately. (UDP — scsynth must be running.)"""
    pt = validate_patch(patch)
    client = SimpleUDPClient(host, port)
    seq = pt.get("sequence")
    if seq:
        tempo = float(pt.get("tempo", 104))
        sc = S.scale((pt.get("root", "A")) + "3", pt.get("scale", "minor"), octaves=2)
        step = 60 / tempo / 4

        def run():
            for ev in sorted(seq, key=lambda e: e["step"]):
                time.sleep(max(0, ev["step"] * step - (time.monotonic() - t0)))
                f = sc[int(ev["deg"]) % len(sc)]
                name, args = _synth_args(pt, f, step * 1.6)
                client.send_message("/s_new", [name, -1, 0, 0] + args)
        t0 = time.monotonic()
        threading.Thread(target=run, daemon=True).start()
    else:
        freq = S.note_to_hz(pt["note"]) if pt.get("note") else pt.get("freq", 220)
        name, args = _synth_args(pt, freq, pt.get("dur", 2.0))
        client.send_message("/s_new", [name, -1, 0, 0] + args)
    return True


_glide_id = [3000]


def play_legato(patch, notes, glide=0.08, host=SC_HOST, port=SC_PORT):
    """Play a monophonic LEGATO line on \\labglide: one held synth whose pitch
    glides between notes (portamento). `notes` = list of (note_name, gap_seconds)."""
    pt = validate_patch(patch)
    osc, fl, env, fx = pt["osc"], pt["filter"], pt["env"], pt["fx"]
    rq = 1.0 / max(0.8, min(8.0, float(fl["q"])))
    nid = _glide_id[0]; _glide_id[0] += 1
    client = SimpleUDPClient(host, port)
    client.send_message("/s_new", [
        "labglide", nid, 0, 0,
        "freq", float(S.note_to_hz(notes[0][0])), "amp", float(pt.get("amp", 0.2)),
        "wave", WAVE.get(osc.get("wave", "saw"), 0), "cutoff", float(fl["cutoff"]), "rq", float(rq),
        "glide", float(glide), "atk", float(env["a"]), "rel", float(env["r"]),
        "revmix", float(fx["reverb"]), "detune", float(osc.get("detune", 8)),
        "voices", int(osc.get("voices", 1))])

    def run():
        t0 = time.monotonic(); t = 0.0
        for name, gap in notes:
            while time.monotonic() - t0 < t:
                time.sleep(0.003)
            client.send_message("/n_set", [nid, "freq", float(S.note_to_hz(name))])
            t += gap
        while time.monotonic() - t0 < t:
            time.sleep(0.003)
        client.send_message("/n_set", [nid, "gate", 0])
    threading.Thread(target=run, daemon=True).start()
    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python sc_bridge.py patch.json   (SuperCollider + engine.scd must be running)")
        sys.exit(1)
    play_patch(load_patch(sys.argv[1]))
    print("sent to scsynth on", f"{SC_HOST}:{SC_PORT}")
    time.sleep(6)   # keep alive so a sequence finishes

"""
ai/llm.py — text -> patch JSON via OpenRouter (cheap model).

Augments creation: describe a sound in words, the LLM writes a patch in our
format, the engine renders it. Key + model come from .env. No audio is sent —
only the prompt and the schema.
"""
import os
import json
import re
from openai import OpenAI

# A compact statement of the patch schema for the model (mirrors PATCH-FORMAT.md).
SCHEMA = """A patch is JSON describing one synth sound. Fields (all optional except osc):
{
 "name": short string,
 "dur": seconds 0.2..12,
 "note": e.g. "A3" (or "freq": Hz),
 "osc": {"type":"additive"|"fm"|"wave",
         "harmonics":[16 floats 0..1],        // additive only
         "wave":"saw"|"square"|"sine"|"triangle",
         "ratio":0.25..16, "index":0..2000,   // fm only
         "voices":1..7, "detune":0..30},
 "filter": {"type":"lowpass"|"highpass"|"bandpass"|"notch","cutoff":30..18000,"q":0.3..24,"env_amt":0..2},
 "env": {"a":0..5,"d":0..5,"s":0..1,"r":0..5},
 "lfo": {"target":"none"|"filter"|"pitch"|"amp","rate":0..20,"depth":0..1},
 "fx": {"reverb":0..0.9,"delay":0..0.9,"delay_time":0.05..1.2,"width":0..1,"drive":0.5..3}
}
Choose osc.type to fit the description (additive/fm for bells & metallic, wave for classic analog).
Dark = low filter cutoff; bright = high. Slow pad = long attack/release. Return ONLY the JSON object."""

SYSTEM = ("You are a synthesizer sound-design assistant. Given a description, "
          "output ONE patch as strict JSON matching this schema. No prose, no code fences.\n\n" + SCHEMA)


def _extract_json(txt):
    txt = txt.strip()
    if txt.startswith("```"):
        txt = re.sub(r"^```[a-zA-Z]*\n?|\n?```$", "", txt).strip()
    try:
        return json.loads(txt)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", txt, re.S)   # grab the first {...} block
        if m:
            return json.loads(m.group(0))
        raise


def generate(prompt):
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY not set (see .env)")
    model = os.environ.get("OPENROUTER_MODEL", "openai/gpt-4o-mini")
    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=key)
    kw = dict(model=model, temperature=0.7, max_tokens=700,
              messages=[{"role": "system", "content": SYSTEM},
                        {"role": "user", "content": prompt}])
    try:
        resp = client.chat.completions.create(response_format={"type": "json_object"}, **kw)
    except Exception:
        resp = client.chat.completions.create(**kw)   # model may not support json_object
    return _extract_json(resp.choices[0].message.content)

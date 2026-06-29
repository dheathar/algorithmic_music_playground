"""
server.py — the local backend bridge (FastAPI).

Lets the browser benches render a designed patch through the REAL Python engine.
Local only. Run:
    ./.venv/bin/uvicorn server:app --port 7700
    (or:  ./.venv/bin/python server.py)

Endpoints:
    GET  /            -> health check
    POST /render      -> body = patch JSON; returns audio/wav
    POST /render-to/{name} -> renders and saves patches/<name>.wav (for compositions)
"""
import io
import os
import numpy as np
from fastapi import FastAPI, Request
from fastapi.responses import Response, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from scipy.io import wavfile

import synth as S
from patch import render_patch, validate_patch

HERE = os.path.dirname(os.path.abspath(__file__))
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(HERE, ".env"))
except Exception:
    pass

app = FastAPI(title="Signal Lab — patch bridge")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def _wav_bytes(sig, peak=0.89):
    sig = np.asarray(sig, dtype=np.float64)
    sig = sig / (np.max(np.abs(sig)) + 1e-9) * peak
    pcm = np.int16(np.clip(sig, -1, 1) * 32767)
    buf = io.BytesIO()
    wavfile.write(buf, S.SR, pcm)
    return buf.getvalue()


@app.get("/api")
def health():
    return {"ok": True, "engine": "synth.py", "sr": S.SR}


@app.post("/render")
async def render(req: Request):
    patch = await req.json()
    try:
        sig = render_patch(patch)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    return Response(content=_wav_bytes(sig), media_type="audio/wav")


@app.post("/ai/patch")
async def ai_patch(req: Request):
    """Text prompt -> a validated patch (browser then renders it via /render)."""
    body = await req.json()
    prompt = (body or {}).get("prompt", "").strip()
    if not prompt:
        return JSONResponse({"error": "no prompt"}, status_code=400)
    try:
        from ai.llm import generate
        patch = validate_patch(generate(prompt))
        return {"patch": patch}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@app.post("/ai/analyze")
async def ai_analyze(req: Request):
    """Render a patch and describe it in numbers (brightness, rms, texture...)."""
    patch = await req.json()
    try:
        from ai.analyze import analyze
        sig = render_patch(validate_patch(patch))
        return analyze(sig)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@app.post("/ai/describe")
async def ai_describe(req: Request):
    """Extract acoustic features from one of OUR creations and turn them into a
    prompt seed for the patch-generator. Restricted to files inside the project."""
    body = await req.json()
    name = (body or {}).get("file", "")
    path = os.path.normpath(os.path.join(HERE, name))
    if not path.startswith(HERE) or not os.path.isfile(path):
        return JSONResponse({"error": "file not found in project"}, status_code=400)
    try:
        from ai.analyze import analyze
        sig = S.load_audio(path)
        sig = sig[:int(10 * S.SR)]                       # first 10 s = representative
        f = analyze(sig)
        prompt = (f"a {f['brightness']}, {f['texture']} sound "
                  f"(spectral centroid ~{f['centroid_hz']} Hz)")
        return {"features": f, "prompt": prompt, "file": name}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@app.post("/sc/play")
async def sc_play(req: Request):
    """Play a patch in REALTIME through SuperCollider (scsynth must be running
    with engine.scd loaded). Audio comes out of SC, not over HTTP."""
    patch = await req.json()
    try:
        from sc_bridge import play_patch
        play_patch(validate_patch(patch))
        return {"ok": True, "engine": "supercollider", "note": "audio plays from scsynth"}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@app.post("/render-to/{name}")
async def render_to(name: str, req: Request):
    patch = await req.json()
    safe = "".join(c for c in name if c.isalnum() or c in "-_")
    sig = render_patch(patch)
    path = os.path.join(HERE, "patches", f"{safe}.wav")
    S.write_wav(path, sig)
    return {"ok": True, "wrote": f"patches/{safe}.wav", "seconds": round(len(sig) / S.SR, 2)}


# serve the whole lab as static files (added LAST so API routes resolve first).
# now http://127.0.0.1:7700/ = the portal, with working fetch + CDN.
app.mount("/", StaticFiles(directory=HERE, html=True), name="site")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=7700)

"""
build_patches.py — render the Patch Library from patches.json.

For each patch: validate it, write the usable file patches/bank/<id>.json, render
a preview to patches/previews/<id>.mp3, then inject everything into
patches_template.html -> patches.html.

    ./.venv/bin/python build_patches.py
"""
import os
import json
import subprocess
import numpy as np
import synth as S
from patch import validate_patch, render_patch

HERE = os.path.dirname(os.path.abspath(__file__))
BANK = os.path.join(HERE, "patches", "bank")
PREV = os.path.join(HERE, "patches", "previews")


def to_mp3(sig, mp3_path):
    sig = np.asarray(sig, dtype=np.float64)
    sig = sig / (np.max(np.abs(sig)) + 1e-9) * 0.89
    wav_path = mp3_path[:-4] + ".wav"
    S.write_wav(wav_path, sig)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav_path,
                    "-b:a", "96k", mp3_path], check=True)
    os.remove(wav_path)


def main():
    data = json.load(open(os.path.join(HERE, "patches.json")))
    os.makedirs(BANK, exist_ok=True)
    os.makedirs(PREV, exist_ok=True)
    for p in data["patches"]:
        pid = p["id"]
        vp = validate_patch(p["patch"])                       # clamp/sanitize -> usable
        json.dump(vp, open(os.path.join(BANK, pid + ".json"), "w"), indent=2)
        sig = render_patch(vp)
        to_mp3(sig, os.path.join(PREV, pid + ".mp3"))
        p["preview"] = f"patches/previews/{pid}.mp3"          # for the page
        print(f"  {pid}: bank/{pid}.json + previews/{pid}.mp3")
    tpl = open(os.path.join(HERE, "patches_template.html")).read()
    blob = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    open(os.path.join(HERE, "patches.html"), "w").write(tpl.replace("__PATCHES_JSON__", blob))
    print(f"built patches.html ({len(data['patches'])} patches, {len(data['rules'])} rules)")


if __name__ == "__main__":
    main()

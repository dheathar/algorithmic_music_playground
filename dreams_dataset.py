"""
dreams_dataset.py — download the FULL DreamBank corpus locally, once.

Pulls every row of gustavecortal/DreamBank-annotated (the open mirror of
DreamBank, Domhoff & Schneider) via the no-auth HuggingFace datasets-server,
into dreams_all.jsonl (one dream per line). Kept LOCAL (gitignored): a research
seed bank we can search offline. Inspiration only — never redistributed, never
in a master.

    ./.venv/bin/python dreams_dataset.py
    ./.venv/bin/python dreams_search.py "lighthouse"   # then search it offline
"""
import os
import json
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "dreams_all.jsonl")
DS = "gustavecortal/DreamBank-annotated"
ROWS = "https://datasets-server.huggingface.co/rows"
PAGE = 100
FIELDS = ["id", "name", "number", "time", "date", "gender", "age", "report", "character", "emotion"]


def page(offset):
    qs = urllib.parse.urlencode({"dataset": DS, "config": "default", "split": "train",
                                 "offset": offset, "length": PAGE})
    for attempt in range(8):
        try:
            with urllib.request.urlopen(f"{ROWS}?{qs}", timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429:                       # rate limited — wait and retry
                wait = min(60, 10 * (attempt + 1))
                print(f"    429 at offset {offset}; backing off {wait}s")
                time.sleep(wait)
            elif attempt == 7:
                raise
            else:
                time.sleep(2 * (attempt + 1))
        except Exception:
            if attempt == 7:
                raise
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"give up at offset {offset}")


def existing_count():
    if not os.path.exists(OUT):
        return 0
    with open(OUT) as f:
        return sum(1 for _ in f)


def main():
    total = page(0).get("num_rows_total", 0)
    start = existing_count()                          # resume from where we stopped
    mode = "a" if start else "w"
    print(f"DreamBank: {total} dreams — resuming at {start} (mode={mode}) ...")
    written = start
    with open(OUT, mode) as f:
        offset = start
        while offset < total:
            data = page(offset)
            rows = data.get("rows", [])
            if not rows:
                break
            for item in rows:
                row = item.get("row", {})
                f.write(json.dumps({k: row.get(k) for k in FIELDS}, ensure_ascii=False) + "\n")
                written += 1
            offset += len(rows)
            f.flush()
            if offset % 2000 < PAGE:
                print(f"  {min(offset, total)}/{total}")
            time.sleep(0.6)                           # be polite — avoid the 429
    print(f"done: {written} dreams -> {OUT}")


if __name__ == "__main__":
    main()

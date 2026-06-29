"""
dreams_fetch.py — pull real, anonymized dream reports into the lab's seed board.

Source: DreamBank (Domhoff & Schneider), via the open HuggingFace dataset
gustavecortal/DreamBank-annotated, queried through the no-auth datasets-server
full-text search. These are INSPIRATION SEEDS ONLY — we read a dream, feel it,
and synthesize something original. The text is kept local (dreams.json is
gitignored) and never shipped or redistributed.

    ./.venv/bin/python dreams_fetch.py --theme "Flight & falling" \\
        --blurb "Dreams of rising and losing altitude" "flying" "falling"
    ./.venv/bin/python build_dreams.py
"""
import os
import sys
import json
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
STORE = os.path.join(HERE, "dreams.json")
DS = "gustavecortal/DreamBank-annotated"
SEARCH = "https://datasets-server.huggingface.co/search"
N_PER = 8


def search(query, n):
    qs = urllib.parse.urlencode({"dataset": DS, "config": "default",
                                 "split": "train", "query": query,
                                 "offset": 0, "length": n})
    with urllib.request.urlopen(f"{SEARCH}?{qs}", timeout=25) as r:
        data = json.load(r)
    out, seen = [], set()
    for item in data.get("rows", []):
        row = item.get("row", {})
        rid = row.get("id", "")
        rep = (row.get("report") or "").strip()
        if not rep or rid + rep[:20] in seen:
            continue
        seen.add(rid + rep[:20])
        out.append({
            "id": rid,
            "dreamer": row.get("name", ""),
            "gender": row.get("gender", ""),
            "age": row.get("age", ""),
            "emotion": row.get("emotion") if row.get("emotion") not in (None, "None") else "",
            "report": rep,
        })
    return {"query": query, "total": data.get("num_rows_total", len(out)), "results": out}


def parse_args(argv):
    theme = blurb = None
    n = N_PER
    queries = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--theme" and i + 1 < len(argv):
            theme = argv[i + 1]; i += 2
        elif a == "--blurb" and i + 1 < len(argv):
            blurb = argv[i + 1]; i += 2
        elif a == "--n" and i + 1 < len(argv):
            n = int(argv[i + 1]); i += 2
        else:
            queries.append(a); i += 1
    return theme, blurb, n, queries


def main(argv):
    theme, blurb, n, queries = parse_args(argv)
    data = {"themes": [], "boards": []}
    if os.path.exists(STORE):
        try:
            data = json.load(open(STORE))
        except Exception:
            pass
    data.setdefault("themes", [])
    data.setdefault("boards", [])
    by_q = {b["query"]: b for b in data["boards"]}
    for q in queries:
        try:
            b = search(q, n)
            by_q[q] = b
            print(f"  '{q}': {len(b['results'])} stored of {b['total']} in DreamBank")
        except Exception as e:
            print(f"  '{q}': failed ({e})")
    data["boards"] = list(by_q.values())
    if theme:
        by_t = {t["name"]: t for t in data["themes"]}
        t = by_t.get(theme, {"name": theme, "blurb": "", "queries": []})
        if blurb:
            t["blurb"] = blurb
        t["queries"] = list(dict.fromkeys((t.get("queries") or []) + queries))
        by_t[theme] = t
        data["themes"] = list(by_t.values())
        print(f"  theme '{theme}': {len(t['queries'])} queries")
    with open(STORE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print(f"wrote {STORE} ({len(data['themes'])} themes, {len(data['boards'])} boards). "
          f"Now: python build_dreams.py")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('usage: python dreams_fetch.py [--theme NAME] [--blurb TEXT] [--n N] "query" [...]')
        sys.exit(1)
    main(sys.argv[1:])

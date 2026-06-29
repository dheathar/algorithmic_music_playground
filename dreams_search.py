"""
dreams_search.py — search the LOCAL DreamBank corpus (offline) into the board.

Once dreams_dataset.py has downloaded dreams_all.jsonl, this searches all ~28k
dreams with no API calls and adds matching reports to dreams.json as a themed
board. Inspiration only; the text stays local.

    ./.venv/bin/python dreams_search.py --theme "Water" --blurb "..." "ocean" "drowning"
    ./.venv/bin/python build_dreams.py
"""
import os
import sys
import json

HERE = os.path.dirname(os.path.abspath(__file__))
CORPUS = os.path.join(HERE, "dreams_all.jsonl")
STORE = os.path.join(HERE, "dreams.json")
N_PER = 8


def load_corpus():
    if not os.path.exists(CORPUS):
        print("No local corpus. Run: ./.venv/bin/python dreams_dataset.py")
        sys.exit(1)
    rows = []
    with open(CORPUS) as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def find(rows, query, n):
    q = query.lower()
    hits = []
    for r in rows:
        rep = (r.get("report") or "")
        if q in rep.lower():
            hits.append(r)
    out = []
    for r in hits[:n]:
        out.append({
            "id": r.get("id", ""), "dreamer": r.get("name", ""),
            "gender": r.get("gender", ""), "age": r.get("age", ""),
            "emotion": r.get("emotion") if r.get("emotion") not in (None, "None") else "",
            "report": (r.get("report") or "").strip(),
        })
    return {"query": query, "total": len(hits), "results": out}


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
    rows = load_corpus()
    data = {"themes": [], "boards": []}
    if os.path.exists(STORE):
        try:
            data = json.load(open(STORE))
        except Exception:
            pass
    data.setdefault("themes", []); data.setdefault("boards", [])
    by_q = {b["query"]: b for b in data["boards"]}
    for q in queries:
        b = find(rows, q, n)
        by_q[q] = b
        print(f"  '{q}': {len(b['results'])} stored of {b['total']} matches in {len(rows)} dreams")
    data["boards"] = list(by_q.values())
    if theme:
        by_t = {t["name"]: t for t in data["themes"]}
        t = by_t.get(theme, {"name": theme, "blurb": "", "queries": []})
        if blurb:
            t["blurb"] = blurb
        t["queries"] = list(dict.fromkeys((t.get("queries") or []) + queries))
        by_t[theme] = t
        data["themes"] = list(by_t.values())
    with open(STORE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print(f"wrote {STORE}. Now: python build_dreams.py")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('usage: python dreams_search.py [--theme NAME] [--blurb TEXT] [--n N] "query" [...]')
        sys.exit(1)
    main(sys.argv[1:])

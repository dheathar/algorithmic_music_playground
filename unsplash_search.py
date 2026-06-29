"""
unsplash_search.py — search Unsplash and add the results to the lab's moodboard.

Keeps your access key server-side (reads it from .mcp.json or the env), so it
never lands in a web page. Each query becomes a "board" in inspiration.json;
re-running a query refreshes that board. Then run build_inspiration.py to render
the Inspiration page.

    ./.venv/bin/python unsplash_search.py "moon" "selene" "lunar eclipse"
    ./.venv/bin/python build_inspiration.py
"""
import os
import re
import sys
import json
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
BOARDS = os.path.join(HERE, "inspiration.json")
API = "https://api.unsplash.com/search/photos"
PER_PAGE = 12


def access_key():
    k = os.environ.get("UNSPLASH_ACCESS_KEY")
    if k:
        return k
    try:                                   # fall back to the project .mcp.json
        with open(os.path.join(HERE, ".mcp.json")) as f:
            cfg = json.load(f)
        return cfg["mcpServers"]["unsplash"]["env"]["UNSPLASH_ACCESS_KEY"]
    except Exception:
        return None


def search(query, key):
    qs = urllib.parse.urlencode({"query": query, "per_page": PER_PAGE})
    req = urllib.request.Request(f"{API}?{qs}", headers={"Authorization": f"Client-ID {key}"})
    with urllib.request.urlopen(req, timeout=20) as r:
        data = json.load(r)
    out = []
    for p in data.get("results", []):
        u, links = p.get("urls", {}), p.get("links", {})
        user = p.get("user", {})
        out.append({
            "id": p.get("id"),
            "desc": p.get("description") or p.get("alt_description") or "",
            "author": user.get("name", ""),
            "author_url": (user.get("links", {}) or {}).get("html", ""),
            "page": links.get("html", ""),
            "thumb": u.get("thumb", ""),
            "small": u.get("small", ""),
            "color": p.get("color", "#12152A"),
            "w": p.get("width", 4), "h": p.get("height", 3),
        })
    return {"query": query, "total": data.get("total", 0), "results": out}


def parse_args(argv):
    """--theme NAME and --blurb TEXT are optional; everything else is a query."""
    theme = blurb = None
    queries = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--theme" and i + 1 < len(argv):
            theme = argv[i + 1]; i += 2
        elif a == "--blurb" and i + 1 < len(argv):
            blurb = argv[i + 1]; i += 2
        else:
            queries.append(a); i += 1
    return theme, blurb, queries


def main(argv):
    key = access_key()
    if not key or key.startswith("PASTE_"):
        print("No Unsplash access key found (set UNSPLASH_ACCESS_KEY or .mcp.json).")
        sys.exit(1)
    theme, blurb, queries = parse_args(argv)
    data = {"themes": [], "boards": []}
    if os.path.exists(BOARDS):
        try:
            data = json.load(open(BOARDS))
        except Exception:
            pass
    data.setdefault("themes", [])
    data.setdefault("boards", [])
    by_q = {b["query"]: b for b in data["boards"]}
    for q in queries:
        try:
            b = search(q, key)
            by_q[q] = b                    # replace/refresh this board
            print(f"  '{q}': {len(b['results'])} shown of {b['total']} total")
        except Exception as e:
            print(f"  '{q}': failed ({e})")
    data["boards"] = list(by_q.values())
    if theme:                              # attach these queries to a named theme
        by_t = {t["name"]: t for t in data["themes"]}
        t = by_t.get(theme, {"name": theme, "blurb": "", "queries": []})
        if blurb:
            t["blurb"] = blurb
        t["queries"] = list(dict.fromkeys((t.get("queries") or []) + queries))
        by_t[theme] = t
        data["themes"] = list(by_t.values())
        print(f"  theme '{theme}': {len(t['queries'])} queries")
    with open(BOARDS, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print(f"wrote {BOARDS} ({len(data['themes'])} themes, {len(data['boards'])} boards). "
          f"Now: python build_inspiration.py")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('usage: python unsplash_search.py [--theme NAME] [--blurb TEXT] "query" ["query2" ...]')
        sys.exit(1)
    main(sys.argv[1:])

"""
build_inspiration.py — render the Inspiration moodboard from inspiration.json.

    ./.venv/bin/python build_inspiration.py
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    src = os.path.join(HERE, "inspiration.json")
    data = json.load(open(src)) if os.path.exists(src) else {"boards": []}
    tpl = open(os.path.join(HERE, "inspiration_template.html")).read()
    blob = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    open(os.path.join(HERE, "inspiration.html"), "w").write(tpl.replace("__BOARDS_JSON__", blob))
    n = sum(len(b.get("results", [])) for b in data.get("boards", []))
    print(f"built inspiration.html ({len(data.get('boards', []))} boards, {n} images)")


if __name__ == "__main__":
    main()

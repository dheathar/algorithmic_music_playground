"""
build_dreams.py — render the Dream-seeds board from dreams.json.

    ./.venv/bin/python build_dreams.py
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    src = os.path.join(HERE, "dreams.json")
    data = json.load(open(src)) if os.path.exists(src) else {"themes": [], "boards": []}
    tpl = open(os.path.join(HERE, "dreams_template.html")).read()
    blob = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    open(os.path.join(HERE, "dreams.html"), "w").write(tpl.replace("__DREAMS_JSON__", blob))
    n = sum(len(b.get("results", [])) for b in data.get("boards", []))
    print(f"built dreams.html ({len(data.get('themes', []))} themes, {n} dreams)")


if __name__ == "__main__":
    main()

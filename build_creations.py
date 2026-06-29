"""
build_creations.py — render the Creations Library from the content model.

Single source of truth: creations.json  (edit that, not the HTML).
Inject it into creations_template.html -> creations.html (self-contained, offline-safe).

    ./.venv/bin/python build_creations.py
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    with open(os.path.join(HERE, "creations.json")) as f:
        data = json.load(f)
    with open(os.path.join(HERE, "creations_template.html")) as f:
        tpl = f.read()
    # inline the model as JSON text inside a <script type=application/json>; escape
    # only the closing-tag sequence so the browser can't end the script early.
    blob = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    html = tpl.replace("__CREATIONS_JSON__", blob)
    out = os.path.join(HERE, "creations.html")
    with open(out, "w") as f:
        f.write(html)
    n = len(data.get("creations", []))
    print(f"built creations.html from creations.json ({n} creations)")


if __name__ == "__main__":
    main()

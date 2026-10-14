#!/usr/bin/env python3
"""Tag the stylesheet and script links in the pages with a version.

Browsers (Safari especially) keep css/style.css and the js/ files cached, so
after a push they can show the new page with an old stylesheet. Each link gets
a short fingerprint of the file's contents, e.g. css/style.css?v=3f2a9c1e: when
the file changes, the link changes and every browser fetches the new copy.

    python3 tools/stamp.py

Run it after editing anything in css/ or js/, before committing.
photos.py runs it automatically.
"""

import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGES = ["index.html", "photography.html"]
ASSET = re.compile(r'((?:href|src)=")((?:css|js)/[\w.-]+\.(?:css|js))(?:\?v=\w+)?(")')


def fingerprint(path):
    return hashlib.sha1((ROOT / path).read_bytes()).hexdigest()[:8]


def stamp():
    for name in PAGES:
        page = ROOT / name
        text = page.read_text(encoding="utf-8")
        new = ASSET.sub(lambda m: f"{m[1]}{m[2]}?v={fingerprint(m[2])}{m[3]}", text)
        if new != text:
            page.write_text(new, encoding="utf-8")
            print(f"Updated versions in {name}")


if __name__ == "__main__":
    stamp()

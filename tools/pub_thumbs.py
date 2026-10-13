#!/usr/bin/env python3
"""Make the small title-page thumbnails for the publications list (img/pubs/<key>.jpg).

Put one file per publication in the source folder, named after its key below:
a PDF (the first page is used) or a screenshot (PNG/JPG). Missing ones get a
blank page as a placeholder until you add the file.

    python3 tools/pub_thumbs.py
    python3 tools/pub_thumbs.py "/some/other/folder"
"""

import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

DEFAULT_SOURCE = Path.home() / "Documents" / "Paperwork" / "Pics" / "publication pages"
OUT = Path(__file__).resolve().parent.parent / "img" / "pubs"
WIDTH = 240            # shown at 80 CSS px, sharp on retina screens
RATIO = 297 / 210      # A4 portrait

# The keys used in index.html (<img src="img/pubs/<key>.jpg">)
KEYS = [
    "scirep-2026", "scidata-2026", "mee-2026", "articulata-2025", "jeb-2025",
    "ploscb-2023", "procb-2022", "arxiv-2026",
    "zenodo-insectset459", "zenodo-insectset47-66", "zenodo-insectset32",
]


def first_page(pdf):
    """Render page 1 of a PDF with macOS's built-in sips."""
    with tempfile.TemporaryDirectory() as tmp:
        png = Path(tmp) / "page.png"
        subprocess.run(["sips", "-s", "format", "png", "-Z", "1400", str(pdf), "--out", str(png)],
                       check=True, capture_output=True)
        return Image.open(png).copy()


def thumbnail(im):
    """White background, cropped from the top to A4 proportions, scaled down."""
    im = im.convert("RGBA")
    flat = Image.new("RGBA", im.size, "white")
    flat.alpha_composite(im)
    im = flat.convert("RGB")
    w, h = im.size
    h = min(h, round(w * RATIO))
    im = im.crop((0, 0, w, h))
    return im.resize((WIDTH, round(WIDTH * h / w)), Image.LANCZOS)


def main():
    source = Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else DEFAULT_SOURCE
    OUT.mkdir(parents=True, exist_ok=True)
    for key in KEYS:
        found = [p for p in source.glob(f"{key}.*") if p.suffix.lower() in {".pdf", ".png", ".jpg", ".jpeg"}]
        if found:
            src = found[0]
            im = first_page(src) if src.suffix.lower() == ".pdf" else Image.open(src)
            thumbnail(im).save(OUT / f"{key}.jpg", "JPEG", quality=85, optimize=True)
            print(f"{src.name} -> img/pubs/{key}.jpg")
        else:
            Image.new("RGB", (WIDTH, round(WIDTH * RATIO)), "white").save(OUT / f"{key}.jpg", "JPEG", quality=85)
            print(f"missing {key}.pdf/.png in {source}: blank placeholder")


if __name__ == "__main__":
    main()

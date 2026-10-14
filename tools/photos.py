#!/usr/bin/env python3
"""Build the photography page from a folder of film scans.

Source layout (outside the repo, originals stay untouched):

    ~/Documents/Paperwork/Pics/website photos/
        01 Iceland 2024/          <- one folder per set; the number only sets the order
            about.txt             <- optional: one or two sentences about the set
            info.csv              <- created for you on first run, then fill it in
            scan001.jpg
            scan002.jpg
        02 Black Forest/
            ...

info.csv columns: order, file, caption, camera, lens, film, date
- New photos get a row automatically, pre-filled from filenames like
      20260829_OlympusOM2n_UltraMax400_MasaiMaraP1037805.jpg  (date_camera_film_place)
  so usually you only need to check them and add the lens.
- Rows for photos you removed from the folder are dropped.
- Photos are shown by the `order` number. After each run the file is sorted and
  renumbered 10, 20, 30, ... so to move a photo between 20 and 30, give it 25.
  Or use the drag-and-drop sorter: python3 tools/sorter.py
- Leave a cell empty to hide it.

Running the script:
    python3 tools/photos.py                  # uses the default source folder below
    python3 tools/photos.py "/some/other/folder"

It writes resized copies to photos/<set>/ in the repo (large ~2000px, thumb ~900px)
and rewrites the gallery between the PHOTOS markers in photography.html.
Uses macOS's built-in `sips` for resizing and Pillow to strip metadata
(camera serials, GPS location) from the published copies.

The folder named in PORTRAITS (photos of you) is resized into photos/me/ but
left out of the gallery; those pictures are placed on the home page by hand.
"""

import csv
import html
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    from PIL import Image, ImageOps
except ImportError:
    sys.exit("Pillow is needed to strip photo metadata: pip install pillow")

DEFAULT_SOURCE = Path.home() / "Documents" / "Paperwork" / "Pics" / "website photos"
PORTRAITS = {"Marius": "me"}  # source folder -> output folder, not shown in the gallery
LARGE_PX = 2000
THUMB_PX = 900
QUALITY = "82"
IMAGE_EXT = {".jpg", ".jpeg", ".tif", ".tiff", ".png", ".heic"}
COLUMNS = ["order", "file", "caption", "camera", "lens", "film", "date"]

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "photos"
PAGE = REPO / "photography.html"
START, END = "<!-- PHOTOS:START -->", "<!-- PHOTOS:END -->"


def slugify(name):
    name = name.lower()
    for a, b in {"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"}.items():
        name = name.replace(a, b)
    return re.sub(r"[^a-z0-9]+", "-", name).strip("-")


def display_name(folder):
    # "01 Iceland 2024" -> "Iceland 2024"
    return re.sub(r"^\d+[\s_.-]+", "", folder)


# Nicer spellings for names found in filenames; anything else is split at capitals
NAMES = {
    "OlympusOM2n": "Olympus OM-2n",
    "MinoltaRivaPanorama": "Minolta Riva Panorama",
    "UltraMax400": "Kodak UltraMax 400",
    "Ektacolor160": "Kodak Ektacolor 160",
    "Phoenix200II": "Harman Phoenix 200 II",
}
MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()


def split_caps(s):
    return re.sub(r"(?<=[a-z])(?=[A-Z0-9])|(?<=[0-9])(?=[A-Z])", " ", s)


def guess_from_filename(name):
    """20260829_OlympusOM2n_UltraMax400_MasaiMaraP1037805.RW2.jpg -> row values.
    The day may be missing: 202609___OlympusOM2n_..."""
    stem = name.split(".")[0]
    m = re.match(r"(\d{4})(\d{2})[\d_]*?_([^_]+)_([^_]+)_([A-Za-z]+?)(?:P?\d+)?$", stem)
    if not m:
        return {}
    year, month, camera, film, place = m.groups()
    return {
        "caption": split_caps(place),
        "camera": NAMES.get(camera, split_caps(camera)),
        "film": NAMES.get(film, split_caps(film)),
        "date": f"{MONTHS[int(month) - 1]} {year}",
    }


def order_key(row, index):
    try:
        return (0, float(row.get("order") or ""), index)
    except ValueError:
        return (1, 0, index)  # no number yet: keep at the end, in file order


class InfoFileError(Exception):
    """An info.csv that can't be read safely; nothing is written in that case."""


def read_csv(info):
    """Read info.csv as saved by this script, Numbers or Excel.

    Copes with a table-name line above the header (Numbers export), semicolon
    or tab separators (Excel), capitalised column names and older encodings.
    Refuses (InfoFileError) rather than guessing if the file column is missing,
    so a file it cannot understand is never overwritten."""
    if not info.exists():
        return [], ","
    raw = info.read_bytes()
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        text = raw.decode("utf-16")
    else:
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = raw.decode("mac_roman")  # older Excel "CSV" on a Mac
    lines = text.splitlines()
    if not any(line.strip() for line in lines):
        return [], ","
    for i, line in enumerate(lines):
        delim = max((",", ";", "\t"), key=line.count)
        cells = [c.strip().strip('"').lower() for c in line.split(delim)]
        if "file" in cells:
            break
    else:
        raise InfoFileError(
            f"{info} has no 'file' column, so it was left untouched.\n"
            "If you edited it in Numbers, export again with File > Export To > CSV and untick\n"
            "'Include table names'; keep the header row (order, file, caption, ...).")
    reader = csv.DictReader(lines[i:], delimiter=delim)
    rows = []
    for r in reader:
        r = {(k or "").strip().lower(): (v or "").strip() for k, v in r.items()}
        if r.get("file"):
            rows.append(r)
    return rows, delim


def write_csv(info, rows, delim):
    # utf-8-sig so Excel shows ß and ü correctly
    with info.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, delimiter=delim, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({c: (r.get(c) or "") for c in COLUMNS})


def sync_info(set_dir, images, order=None):
    """Bring info.csv in line with the folder: add new photos, drop removed ones,
    sort by `order` (or by the given list of filenames) and renumber 10, 20, 30..."""
    info = set_dir / "info.csv"
    rows, delim = read_csv(info)
    if info.exists():
        # Keep the previous version next to it, just in case
        shutil.copy2(info, set_dir / "info.backup.csv")
    names = {p.name for p in images}
    gone = [r["file"] for r in rows if r["file"] not in names]
    rows = [r for r in rows if r["file"] in names]
    listed = {r["file"] for r in rows}
    new = [{"file": p.name, **guess_from_filename(p.name)} for p in images if p.name not in listed]
    rows += new

    if order is not None:
        pos = {name: i for i, name in enumerate(order)}
        rows.sort(key=lambda r: pos.get(r["file"], len(pos)))
    else:
        rows = [r for _, r in sorted(((order_key(r, i), r) for i, r in enumerate(rows)), key=lambda t: t[0])]
    for i, r in enumerate(rows, 1):
        r["order"] = str(i * 10)

    write_csv(info, rows, delim)
    if new:
        print(f"  added {len(new)} new row(s)")
    if gone:
        print(f"  removed {len(gone)} row(s) for missing photos: {', '.join(gone)}")
    by_name = {p.name: p for p in images}
    return [(by_name[r["file"]], r) for r in rows]


def images_in(folder):
    return sorted(p for p in folder.iterdir() if p.suffix.lower() in IMAGE_EXT and not p.name.startswith("."))


def resize(src, dst, px):
    if dst.exists() and dst.stat().st_mtime >= src.stat().st_mtime:
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        # sips reads HEIC and resizes well; save losslessly, then re-encode once
        mid = Path(tmp) / "mid.tiff"
        subprocess.run(["sips", "-Z", str(px), "-s", "format", "tiff", str(src), "--out", str(mid)],
                       check=True, capture_output=True)
        with Image.open(mid) as im:
            icc = im.info.get("icc_profile")
            im = ImageOps.exif_transpose(im).convert("RGB")
            # No exif: drops GPS location, serial numbers and timestamps
            im.save(dst, "JPEG", quality=int(QUALITY), optimize=True, progressive=True, icc_profile=icc)


def size_of(path):
    with Image.open(path) as im:
        return im.size


TONES = ["white", "cream", "offwhite"]  # paper of each set's sheet, in turn
ARROW = ('<svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" '
         'stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M19 12H5M11 6l-6 6 6 6"/></svg>')


def build_set(set_dir):
    """Resize the set's photos and return what the page needs to show it."""
    images = images_in(set_dir)
    if not images:
        return None
    slug = slugify(display_name(set_dir.name))
    print(f"{set_dir.name}: {len(images)} photo(s)")
    keep = set()
    prints = []
    for src, row in sync_info(set_dir, images):
        stem = slugify(src.stem)
        large = OUT / slug / f"{stem}.jpg"
        thumb = OUT / slug / f"{stem}-thumb.jpg"
        resize(src, large, LARGE_PX)
        resize(src, thumb, THUMB_PX)
        keep |= {large, thumb}
        w, h = size_of(thumb)

        e = lambda k: html.escape((row.get(k) or "").strip())
        # Lens wrapped in its own span (with its separator) so phones can hide it
        camera, lens, film = e("camera"), e("lens"), e("film")
        right = camera
        if lens:
            right += f'<span class="cap-lens"> · {lens}</span>' if camera else f'<span class="cap-lens">{lens} · </span>'
        if film:
            right += (" · " if camera else "") + film
        prints.append({
            "large": f"photos/{slug}/{stem}.jpg",
            "thumb": f"photos/{slug}/{stem}-thumb.jpg",
            "w": w, "h": h,
            "left": " · ".join(x for x in (e("caption"), e("date")) if x),
            "right": right,
            "alt": e("caption") or html.escape(display_name(set_dir.name)),
        })

    # Remove web copies of photos that were deleted or renamed
    for old in (OUT / slug).glob("*.jpg"):
        if old not in keep:
            old.unlink()

    about = set_dir / "about.txt"
    about_text = about.read_text(encoding="utf-8").strip() if about.exists() else ""
    return {"slug": slug, "name": html.escape(display_name(set_dir.name)),
            "about": html.escape(about_text), "prints": prints}


def stack_html(s):
    """Overview: the first three photos as a small pile, first photo on top."""
    pile = "".join(
        f'<span class="print" style="--r: {p["w"] / p["h"]:.3f}"><img src="{p["thumb"]}" alt="" loading="lazy"></span>'
        for p in reversed(s["prints"][:3])
    )
    n = len(s["prints"])
    return (
        f'      <a class="stack" href="#{s["slug"]}" data-set="{s["slug"]}">\n'
        f'        <span class="stack-pile">{pile}</span>\n'
        f'        <span class="stack-title">{s["name"]}</span>\n'
        f'        <span class="stack-count">{n} photo{"s" if n != 1 else ""}</span>\n'
        f'      </a>'
    )


def print_rows(prints):
    """Group the prints into rows, keeping their order: consecutive horizontal
    photos share rows (wrapping as the screen allows), vertical photos get rows
    of their own with at most two side by side."""
    rows = []
    for p in prints:
        vertical = p["h"] > p["w"] * 1.05
        last = rows[-1] if rows else None
        if last and last["vertical"] == vertical and (not vertical or len(last["prints"]) < 2):
            last["prints"].append(p)
        else:
            rows.append({"vertical": vertical, "prints": [p]})
    return rows


def set_html(s, tone):
    def figure(p):
        return (
            f'          <figure class="print{" print--wide" if p["w"] > 2 * p["h"] else ""}" style="--r: {p["w"] / p["h"]:.3f}">\n'
            f'            <a class="frame" href="{p["large"]}">'
            f'<img src="{p["thumb"]}" width="{p["w"]}" height="{p["h"]}" alt="{p["alt"]}" loading="lazy"></a>\n'
            f'            <figcaption><span>{p["left"]}</span><span>{p["right"]}</span></figcaption>\n'
            f'          </figure>'
        )
    prints = "\n".join(
        f'        <div class="prints-row{" prints-row--vertical" if row["vertical"] else ""}">\n'
        + "\n".join(figure(p) for p in row["prints"])
        + "\n        </div>"
        for row in print_rows(s["prints"])
    )
    about = f'\n      <p class="set-about">{s["about"]}</p>' if s["about"] else ""
    n = len(s["prints"])
    return (
        f'    <section class="photo-set paper paper--{tone}" id="set-{s["slug"]}" data-set="{s["slug"]}">\n'
        f'      <header class="set-bar paper paper--{tone}">\n'
        f'        <h2><a class="back" href="#" title="Back to all sets">{ARROW}<span>{s["name"]}</span></a></h2>\n'
        f'        <span class="set-count">{n} photo{"s" if n != 1 else ""}</span>\n'
        f'      </header>\n'
        f'      <div class="set-body">{about}\n'
        f'      <div class="prints">\n{prints}\n      </div>\n'
        f'      </div>\n'
        f'    </section>'
    )


def build_portraits(src_dir, out_name):
    out = OUT / out_name
    for src in images_in(src_dir):
        resize(src, out / f"{slugify(src.stem)}.jpg", THUMB_PX)
        print(f"  {src_dir.name}/{src.name} -> photos/{out_name}/{slugify(src.stem)}.jpg")


def gallery_folders(source):
    return [d for d in sorted(source.iterdir()) if d.is_dir() and d.name not in PORTRAITS]


def build(source):
    folders = sorted(d for d in source.iterdir() if d.is_dir())
    for d in folders:
        if d.name in PORTRAITS:
            build_portraits(d, PORTRAITS[d.name])
    sets = [s for s in (build_set(d) for d in folders if d.name not in PORTRAITS) if s]
    for d in (p for p in OUT.iterdir() if p.is_dir()) if OUT.exists() else []:
        if d.name not in {s["slug"] for s in sets} | set(PORTRAITS.values()):
            for f in d.glob("*"):
                f.unlink()
            d.rmdir()

    page = PAGE.read_text(encoding="utf-8")
    if START not in page or END not in page:
        sys.exit(f"Markers {START} / {END} not found in {PAGE.name}")
    body = (
        '    <div class="stacks sheet" id="overview">\n'
        + "\n".join(stack_html(s) for s in sets)
        + '\n    </div>\n    <div class="sets" id="sets" hidden>\n'
        + "\n".join(set_html(s, TONES[i % len(TONES)]) for i, s in enumerate(sets))
        + "\n    </div>"
    )
    page = re.sub(re.escape(START) + r".*?" + re.escape(END),
                  lambda _: f"{START}\n{body}\n    {END}", page, flags=re.S)
    PAGE.write_text(page, encoding="utf-8")
    print(f"Updated {PAGE.name} with {len(sets)} set(s).")


def main():
    source = Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else DEFAULT_SOURCE
    if not source.is_dir():
        sys.exit(f"Source folder not found: {source}\nCreate it, add one subfolder per set, and run again.")
    try:
        build(source)
    except InfoFileError as exc:
        sys.exit(f"Stopped: {exc}")


if __name__ == "__main__":
    main()

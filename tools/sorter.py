#!/usr/bin/env python3
"""Drag-and-drop sorter for the photography page.

    python3 tools/sorter.py

Opens a page in your browser showing every set as a contact sheet. Drag prints
into the order you want and press "Save order". This writes the `order` column
in each set's info.csv and rebuilds photography.html. Press "Done" when you are
finished: it saves anything unsaved and stops the sorter (Ctrl+C here works too).
"""

import html
import json
import re
import sys
import threading
import webbrowser
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import photos  # noqa: E402

PORT = 8001


def page(source):
    sets = []
    for d in photos.gallery_folders(source):
        images = photos.images_in(d)
        if not images:
            continue
        slug = photos.slugify(photos.display_name(d.name))
        rows, _ = photos.read_csv(d / "info.csv")
        cards = []
        for r in rows:
            stem = photos.slugify(Path(r["file"]).stem)
            frame = re.search(r"P?\d{5,}", Path(r["file"]).stem.split("_")[-1])
            note = " · ".join(x for x in (frame and frame.group(0), r.get("film")) if x)
            cards.append(
                f'<li data-file="{html.escape(r["file"], quote=True)}">'
                f'<img src="photos/{slug}/{stem}-thumb.jpg" alt="" loading="lazy">'
                f'<span>{html.escape(note)}</span></li>'
            )
        sets.append(
            f'<section class="sheet paper paper--white" data-folder="{html.escape(d.name, quote=True)}">'
            f'<span class="label">{html.escape(photos.display_name(d.name))}</span>'
            f'<ol class="sheetlist">{"".join(cards)}</ol></section>'
        )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Photo sorter</title>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=Newsreader:opsz,wght@6..72,400;6..72,500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="css/style.css">
<style>
  .bar {{ position: sticky; top: 12px; z-index: 5; display: flex; gap: 16px; align-items: center;
         padding: 14px 22px; font-family: var(--mono); font-size: .8rem; }}
  .bar button {{ font: inherit; padding: 8px 16px; border: 1px solid var(--ink); background: var(--ink);
                 color: var(--white); cursor: pointer; }}
  .bar button:disabled {{ opacity: .4; cursor: default; }}
  .sheet {{ transform: none; margin-top: 28px; }}
  .sheetlist {{ list-style: none; margin: 0; padding: 0; display: grid; gap: 14px;
               grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); counter-reset: n; }}
  .sheetlist li {{ position: relative; padding: 6px 6px 0; background: var(--photo); box-shadow: var(--shadow);
                  cursor: grab; counter-increment: n; }}
  .sheetlist li::before {{ content: counter(n); position: absolute; top: 10px; left: 10px; padding: 1px 6px;
                          background: rgba(0,0,0,.6); color: #fff; font: 500 .7rem var(--mono); }}
  .sheetlist img {{ width: 100%; aspect-ratio: 1; object-fit: contain; background: #2b2925; }}
  .sheetlist span {{ display: block; padding: 4px 2px 6px; font: .65rem var(--mono); color: var(--ink-faint);
                    white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
  .ghost {{ opacity: .35; }}
</style></head>
<body><main class="desk">
<div class="bar paper paper--cream">
  <span>Drag prints to reorder.</span>
  <button id="save" disabled>Save order</button>
  <button id="done">Done</button>
  <span id="status"></span>
</div>
{"".join(sets)}
</main>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Sortable/1.15.2/Sortable.min.js"></script>
<script>
  const save = document.getElementById('save'), status = document.getElementById('status');
  document.querySelectorAll('.sheetlist').forEach(list => new Sortable(list, {{
    animation: 150, ghostClass: 'ghost',
    onEnd: () => {{ save.disabled = false; status.textContent = 'Unsaved changes'; }}
  }}));
  async function saveOrder() {{
    const order = {{}};
    document.querySelectorAll('[data-folder]').forEach(s =>
      order[s.dataset.folder] = [...s.querySelectorAll('li')].map(li => li.dataset.file));
    save.disabled = true; status.textContent = 'Saving…';
    const r = await fetch('/save', {{ method: 'POST', body: JSON.stringify(order) }});
    status.textContent = r.ok ? 'Saved. info.csv files and photography.html are updated.' : 'Saving failed, see terminal';
    if (!r.ok) save.disabled = false;
    return r.ok;
  }}
  save.addEventListener('click', saveOrder);
  document.getElementById('done').addEventListener('click', async () => {{
    if (!save.disabled && !(await saveOrder())) return;  // unsaved changes: save first
    await fetch('/quit', {{ method: 'POST' }});
    document.querySelector('main').innerHTML =
      '<div class="bar paper paper--cream"><span>All saved. The sorter has stopped; you can close this window.</span></div>';
  }});
</script>
</body></html>"""


class Handler(SimpleHTTPRequestHandler):
    source = None

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            body = page(self.source).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            super().do_GET()  # thumbnails and css from the repo

    def do_POST(self):
        if self.path == "/quit":
            self.send_response(204)
            self.end_headers()
            threading.Thread(target=self.server.shutdown).start()
            return
        if self.path != "/save":
            self.send_error(404)
            return
        try:
            order = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            for folder, files in order.items():
                d = self.source / folder
                if d.parent != self.source or not d.is_dir():
                    raise ValueError(f"unknown folder {folder}")
                photos.sync_info(d, photos.images_in(d), order=files)
            photos.build(self.source)
        except Exception as exc:  # report in the browser and the terminal
            print("Save failed:", exc)
            self.send_error(500, str(exc))
            return
        self.send_response(204)
        self.end_headers()

    def log_message(self, *args):
        pass


def main():
    source = Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else photos.DEFAULT_SOURCE
    if not source.is_dir():
        sys.exit(f"Source folder not found: {source}")
    try:
        photos.build(source)  # make sure thumbnails and info.csv are current
    except photos.InfoFileError as exc:
        sys.exit(f"Stopped: {exc}")
    Handler.source = source
    try:
        server = ThreadingHTTPServer(("127.0.0.1", PORT), partial(Handler, directory=str(photos.REPO)))
    except OSError:
        sys.exit(f"Port {PORT} is busy: the sorter is probably still running in another terminal.\n"
                 "Stop it there with Ctrl+C (or close that terminal) and start it again.")
    url = f"http://localhost:{PORT}/"
    print(f"\nSorter running at {url}  (Ctrl+C to stop)")
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    print("\nSorter stopped.")


if __name__ == "__main__":
    main()

# How to work on this website

A reference for updating the site: previewing, publishing, photos, publications,
the CV and the look. Commands are meant to be pasted into Terminal.

## Contents

- [The short version](#the-short-version)
- [What is where](#what-is-where)
- [Preview the site on your Mac](#preview-the-site-on-your-mac)
- [Publish changes](#publish-changes)
- [Photos](#photos)
- [Publications](#publications)
- [CV entries and logos](#cv-entries-and-logos)
- [Text, links and the contact footer](#text-links-and-the-contact-footer)
- [The paper look](#the-paper-look)
- [Troubleshooting](#troubleshooting)

---

## The short version

| I want to… | Do this |
|---|---|
| See the site locally | `cd ~/Documents/GitHub/mariusfaiss.github.io && python3 -m http.server 8000`, open http://localhost:8000 |
| Add or remove photos | Change the files in `~/Documents/Paperwork/Pics/website photos/`, then run `python3 tools/photos.py` |
| Reorder photos | `python3 tools/sorter.py`, drag, press **Done** |
| Edit captions or lenses | Edit `info.csv` in the set folder, then run `python3 tools/photos.py` |
| Add a publication | Add an entry in `index.html`, put its PDF in `publication pages`, run `python3 tools/pub_thumbs.py` |
| Publish | `git add -A`, `git commit -m "..."`, `git push` (see [Publish changes](#publish-changes)) |

All `python3 tools/...` commands are run from inside the website folder
(`cd ~/Documents/GitHub/mariusfaiss.github.io` first), or with the full path,
e.g. `python3 ~/Documents/GitHub/mariusfaiss.github.io/tools/photos.py`.

---

## What is where

### In this repository (published)

| Path | What it is |
|---|---|
| `index.html` | Home page: About, Publications, CV, contact footer |
| `photography.html` | Photography page. The part between `<!-- PHOTOS:START -->` and `<!-- PHOTOS:END -->` is **generated**, don't edit it by hand |
| `css/style.css` | All styling: paper colours, layout, fonts |
| `js/site.js` | Shadow under the top bar when scrolling |
| `js/photos.js` | Photo stacks, set view and the photo viewer |
| `img/paper-*.jpg` | Paper textures (generated, see [The paper look](#the-paper-look)) |
| `img/pubs/` | Title-page thumbnails of the publications (generated) |
| `img/logos/` | Institution logos for the CV |
| `photos/` | Web-sized copies of the photos (generated, never edit or put files here) |
| `tools/` | Helper scripts (below) |

### Outside the repository (private, on your Mac only)

| Folder | What it is |
|---|---|
| `~/Documents/Paperwork/Pics/website photos/` | Original photo scans, one folder per set, plus `Marius/` for portraits |
| `~/Documents/Paperwork/Pics/publication pages/` | PDFs / screenshots used for the publication thumbnails |
| `~/Documents/Paperwork/Pics/paper textures/` | Reference paper scans, only used to measure texture statistics |

Originals and full PDFs stay out of the repository on purpose: the repository is
public, and only small web versions should be published.

### Scripts in `tools/`

| Script | What it does |
|---|---|
| `photos.py` | Resizes photos, strips their metadata (GPS etc.), updates `info.csv` files and rebuilds the photography page |
| `stamp.py` | Tags the CSS/JS links with a version so browsers don't show a stale stylesheet (run after editing `css/` or `js/`; `photos.py` runs it too) |
| `sorter.py` | Drag-and-drop page for reordering photos |
| `pub_thumbs.py` | Makes the publication thumbnails |
| `paper_textures.py` | Makes the paper textures (synthesised, see [The paper look](#the-paper-look)) |
| `make_texture.py` | Older alternative: generates paper textures without scans |

---

## Preview the site on your Mac

```bash
cd ~/Documents/GitHub/mariusfaiss.github.io
python3 -m http.server 8000
```

Then open http://localhost:8000. Stop the server with **Ctrl+C**.

If a change doesn't show up, the browser is showing a cached copy: press
**Cmd+Shift+R** to reload properly.

---

## Publish changes

The site is published by GitHub Pages from the **`main`** branch. About a minute
after a push, https://mariusfaiss.github.io shows the new version.

### Normal workflow

```bash
cd ~/Documents/GitHub/mariusfaiss.github.io
git status                      # see what changed
git add -A                      # stage everything
git commit -m "Add new photos"  # describe the change
git push
```

Check with `git status` before `git add -A` that nothing unexpected is listed,
e.g. a PDF or a big file. PDFs are ignored automatically (`.gitignore`).

### Working on a draft first

If you want to try bigger changes without publishing them, work on a separate
branch. Everything on it stays off the website until it is merged into `main`:

```bash
git switch -c draft        # create and switch to a draft branch
# ...make and commit changes...
git switch main            # when ready to publish
git merge draft
git push
```

Note: a branch you push (`git push -u origin draft`) is not on the website, but
it is visible to anyone looking at the repository on GitHub.

---

## Photos

### How it works

Originals live in `~/Documents/Paperwork/Pics/website photos/`:

```
website photos/
  01 Masai Mara - Hyenas/       <- one folder per set
    info.csv                    <- captions, camera, lens, film, order
    about.txt                   <- optional: a line or two about the set
    20260829_OlympusOM2n_UltraMax400_MasaiMaraP1037805.RW2.jpg
    ...
  02 Masai Mara - Landscape/
  Marius/                       <- portraits for the About section, not in the gallery
```

- The number at the start of a folder name (`01 `, `02 `) only sets the order of
  the sets; it isn't shown. The rest is the set's title.
- On the page, photos keep your order. On tablets and computers they are laid
  out like a photo book (`js/photos.js`): each line holds as many photos as fit,
  all the same height, filling the width. On phones they are grouped into rows
  by orientation: horizontal photos one per line, vertical photos at most two
  side by side. So the order of vertical and horizontal photos decides how they
  pair up.
- `photos.py` makes web copies (2000 px, plus 900 px previews) in `photos/`,
  removes all metadata from them (including GPS location), and rebuilds the
  photography page. Originals are never changed.

After any change to the photo folders or `info.csv` files:

```bash
python3 ~/Documents/GitHub/mariusfaiss.github.io/tools/photos.py
```

### Add photos

1. Put the JPGs in a set folder (TIFF, PNG and HEIC work too).
2. Run `photos.py`. New photos get a row in `info.csv`, pre-filled from the file
   name, and are added at the end of the set.
3. Reorder them if needed (see below).

**File names:** if photos are named like
`20260829_OlympusOM2n_UltraMax400_MasaiMaraP1037805.jpg`
(date_camera_film_place+number), the caption, camera, film and date are filled
in automatically. A missing day works too (`202609___...`).

**New camera or film:** names in the file are turned into nice spellings by the
`NAMES` list near the top of `tools/photos.py`, e.g.

```python
NAMES = {
    "OlympusOM2n": "Olympus OM-2n",
    "UltraMax400": "Kodak UltraMax 400",
    ...
}
```

Add a line for a new camera or film (otherwise `PortraEktar` just becomes
"Portra Ektar", split at capital letters).

### Add a new set

Make a new folder in `website photos`, e.g. `04 Black Forest`, put the photos in,
optionally add `about.txt`, and run `photos.py`. The set gets its own stack on
the photography page; the first photo in the order is the top of the stack.

### Remove photos

Move them out of the set folder and run `photos.py`. Their rows in `info.csv`
and their web copies are removed (anything typed for them is lost).

### Edit captions, lenses and dates (`info.csv`)

Columns: `order, file, caption, camera, lens, film, date`

- `caption` and `date` show on the print in the gallery; `camera · lens · film`
  is added in the full view (the photo viewer). Empty cells are left out.
- Don't change the `file` column or the header row.

**In Numbers:**

1. Right-click `info.csv` → **Open With → Numbers**.
2. Edit, then **File → Export To → CSV…**, name it `info`, save in the same set
   folder and **Replace**. (No need to save the Numbers document.)
3. Run `photos.py`.

Excel works too. The script copes with Numbers' table-name line, Excel's
semicolons and different encodings. If it still can't read a file it **stops
with a message and leaves the file untouched**. Before each rewrite it keeps the
previous version as `info.backup.csv` next to it.

### Change the order

Easiest, with the drag-and-drop sorter:

```bash
python3 ~/Documents/GitHub/mariusfaiss.github.io/tools/sorter.py
```

A page opens in the browser with each set as a contact sheet. Drag prints into
place, press **Save order**, and press **Done** when finished (it saves and stops
the sorter, then you can close the window).

Or edit the `order` column in `info.csv`: after each run the rows are sorted and
renumbered 10, 20, 30…, so to move a photo between 20 and 30, give it 25.

### Portraits on the home page

The `Marius/` folder is resized into `photos/me/` but not shown in the gallery.
The two portraits are placed by hand in `index.html` (search for
`about-prints`). To use a different photo, put it in `Marius/`, run
`photos.py`, and change the file name in that part of `index.html`.

### Looping video in the About section

The map animation below the portraits is `video/honr-movement.mp4` (with a
still frame `video/honr-movement.jpg` shown while it loads, and to visitors
who have reduced motion switched on). To replace it, convert the new video
with ffmpeg (installed via Homebrew):

```bash
ffmpeg -i "input.mp4" -an -map_metadata -1 -vf "scale=600:-2:flags=lanczos" -c:v libx264 -preset slow -crf 26 -pix_fmt yuv420p -movflags +faststart video/honr-movement.mp4
ffmpeg -y -ss 1 -i video/honr-movement.mp4 -frames:v 1 -q:v 4 video/honr-movement.jpg
```

`-an` removes sound, `-map_metadata -1` removes metadata (such as location),
`-crf` sets quality (higher = smaller file; 23–30 is a good range). Keep it
under ~2–3 MB. MP4 is much smaller and nicer than a GIF for this.

---

## Publications

Publications are in `index.html`, in the section `<section id="publications">`,
grouped under `<h3>Papers</h3>`, `<h3>Preprints</h3>` and `<h3>Datasets</h3>`.

### Add a publication

**1. Add the entry.** Copy an existing `<li>…</li>` block and change it. Template:

```html
<li>
  <a class="pub-thumb" href="https://doi.org/10.xxxx/xxxxx" tabindex="-1" aria-hidden="true"><img src="img/pubs/journal-2027.jpg" width="240" height="339" alt="" loading="lazy"></a>
  <span class="title">Title of the paper</span>
  <span class="authors">Co-author, A., <strong>Faiß, M.</strong>, Co-author, B.</span>
  <span class="venue">Journal Name 12(3), 2027</span>
  <span class="links"><a href="https://doi.org/10.xxxx/xxxxx">doi</a><a href="https://link-to.pdf">pdf</a></span>
</li>
```

- Put your name in `<strong>` so it's bold.
- Newest first within each group.
- The `pdf` link is optional; leave out that `<a>` if there is no free PDF.
- `&` must be written as `&amp;` in the text.

**2. Make the thumbnail.** Pick a short key, e.g. `journal-2027`, and use it in
the `<img src="img/pubs/journal-2027.jpg">` above. Then:

- Put the paper's PDF in `~/Documents/Paperwork/Pics/publication pages/` named
  `journal-2027.pdf` (only the first page is used). For a dataset, use a
  screenshot of its Zenodo page instead: `journal-2027.png`, at least 800 px
  wide.
- Add the key to the `KEYS` list at the top of `tools/pub_thumbs.py`.
- Run:

```bash
python3 ~/Documents/GitHub/mariusfaiss.github.io/tools/pub_thumbs.py
```

Keys without a file get a blank page as a placeholder. Never put PDFs into the
website folder itself: the repository is public.

---

## CV entries and logos

The CV is in `index.html`, `<section id="cv">`, with `<h3>Education</h3>` and
`<h3>Experience</h3>`. Template for an entry:

```html
<li>
  <span class="when">Sep 2027 – present</span>
  <span class="what"><strong>Postdoc, Some Lab</strong><span>Institute, City. One line about it.</span></span>
  <span class="cv-logos">
    <span class="cv-logo" role="img" aria-label="Institute name" style="--logo: url(../img/logos/institute.svg)"></span>
  </span>
</li>
```

Several logos go inside the same `cv-logos` group. They flow left to right and
wrap: a wide logo sits alone on its row, smaller ones share a row. Each logo is
92 × 24 px by default; give it its own size (matching its proportions) with
`--w` and `--h`, e.g.
`style="--logo: url(../img/logos/zhaw.svg); --w: 36px; --h: 42px"`.

**Logos** are shown small, under the date, in ink colour: the logo file is used
as a stencil, so its own colours don't matter. To add one:

1. Get an SVG (or a PNG with transparent background) of the logo, e.g. from
   Wikimedia Commons or the institution's website.
2. Save it as `img/logos/institute.svg`.
3. Reference it as above. The path starts with `../` because it is resolved
   from the `css/` folder.

A logo that only exists as a picture on a coloured background (JPG) won't work
as a stencil as it is: it needs to become a PNG where the logo is opaque and the
background transparent (the ISBE 2026 logo was converted that way).

The logo line can be left out. For a text-only wordmark like xeno-canto, see how
it's done in that entry (`cv-logo cv-logo--text`).

---

## Text, links and the contact footer

- **About text, interests and contact icons:** `index.html`, section
  `<section id="about">`.
- **Links in text:** `<a href="https://example.org">linked words</a>`.
- **Footer** (email, icons, licence line): at the bottom of both `index.html` and
  `photography.html`; change both.
- **Menu:** the `<nav>` at the top of both pages.

---

## The paper look

Colours are defined at the top of `css/style.css`:

```css
--white: #faf7f0;     /* About */
--offwhite: #f4eee2;  /* page background, Publications */
--cream: #efe6d1;     /* CV */
--aged: #e9ddc1;      /* contact footer */
--card: #e9dfca;      /* top bar */
```

Which section uses which paper is set by its class in the HTML, e.g.
`class="sheet paper paper--cream"`.

**Textures** (`img/paper-*.jpg`) are synthesised from random noise, shaped to
statistics measured from real paper scans (stored in `tools/paper_stats.json`;
no part of the scans is in the textures). To change how strong a texture is or
how many fibres it has, edit the `PAPERS` list in `tools/paper_textures.py` and
run:

```bash
python3 ~/Documents/GitHub/mariusfaiss.github.io/tools/paper_textures.py
```

`strength` is how visible the texture is (around 2–5 looks subtle), `fibres`
how many fibres a tile has.

---

## Troubleshooting

**A change doesn't show in the browser.** Press **Cmd+Shift+R** (Safari:
**Cmd+Option+R**). On the live site, wait a minute or two after pushing.

**The live site looks half old, half new** (e.g. photos cropped, the video
zoomed in, captions that should be hidden). The browser kept an old
`style.css`. Run `python3 tools/stamp.py` after editing anything in `css/` or
`js/`, commit the changed `.html` files along with it, and push: the links then
carry a new version (`style.css?v=…`) and every browser loads the new file.

**`can't open file '/Users/mfaiss/tools/...'`.** The command was run from the
wrong folder. Use the full path:
`python3 ~/Documents/GitHub/mariusfaiss.github.io/tools/photos.py`.

**Sorter: "Port 8001 is busy".** An older sorter is still running. Press **Done**
on its page or **Ctrl+C** in its terminal, then start it again.

**Preview: port 8000 in use.** A preview server is already running; just open
http://localhost:8000, or stop the other one with Ctrl+C.

**`photos.py` says an `info.csv` has no 'file' column.** The file was saved in a
format it can't read; it was left untouched. Export again from Numbers as CSV
(see above). If needed, `info.backup.csv` in the same folder is the previous
version.

**A photo shows up rotated.** The script follows the photo's rotation flag; rotate
the original in Preview (and save) and run `photos.py` again.

**Never put files into `photos/` or `img/pubs/` by hand.** They are managed by
the scripts: unknown folders in `photos/` are deleted, and files in `img/pubs/`
are overwritten.

---

## Licences

- Code: MIT (`LICENSE`).
- Photographs and text: CC BY-NC 4.0, stated in the footer of both pages.
- Paper textures: synthesised by `tools/paper_textures.py`, MIT like the code.
- Publications: their publishers' licences.

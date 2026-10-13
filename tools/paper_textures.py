#!/usr/bin/env python3
"""Synthesise the site's paper textures (img/paper-<type>.jpg) from measured statistics.

No pixels of any scan end up in the textures. Instead, two statistical
properties are measured from reference scans and stored in paper_stats.json:

  - the frequency profile: how much fine grain vs. coarse cloudiness the
    paper has (radially averaged amplitude spectrum)
  - the tone distribution: how often and how strongly the paper gets lighter
    or darker than average (quantiles), which gives specks their frequency

New textures are then made from random noise, shaped to the same frequency
profile and tone distribution, plus a sprinkling of short, curly synthetic
fibres (amount set per paper below). Built in the frequency domain, they tile
seamlessly. CSS multiplies them onto the paper colours in style.css.

    python3 tools/paper_textures.py                  # build from paper_stats.json
    python3 tools/paper_textures.py measure "<scans>" # re-measure from scans, then build
"""

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_texture import fibre_layer  # noqa: E402
import random  # noqa: E402

Image.MAX_IMAGE_PIXELS = None
TILE = 768                      # device pixels, shown at 384 CSS px
CSS_PX_MM = 25.4 / 96           # one CSS pixel at real-life size
HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "img"
STATS = HERE / "paper_stats.json"
BINS = 48                       # points in the frequency profile
QUANTILES = 201                 # points in the tone distribution

# paper type -> reference scan (for measuring only), overall strength, shading
# removed when measuring, base tone, random seed, and synthetic fibres (count, darkness)
PAPERS = {
    "white":    dict(scan="38.jpg", strength=2.0, keep=40, base=250.5, seed=1, fibres=500, fibre_ink=1.8),
    "offwhite": dict(scan="07.jpg", strength=2.5, keep=45, base=249.5, seed=2, fibres=900, fibre_ink=2.2),
    "cream":    dict(scan="05.jpg", strength=3.0, keep=55, base=248.5, seed=3, fibres=1100, fibre_ink=2.4),
    "aged":     dict(scan="46.jpg", strength=3.6, keep=70, base=247.0, seed=4, fibres=900, fibre_ink=2.4),
    "card":     dict(scan="02.jpg", strength=4.5, keep=60, base=246.0, seed=5, fibres=1400, fibre_ink=2.2),
}


def radius_grid(n):
    f = np.fft.fftfreq(n)
    fx, fy = np.meshgrid(f, f)
    return np.hypot(fx, fy)


def bin_edges():
    # log-spaced radial frequency bins, from the tile size down to the pixel
    return np.geomspace(1 / TILE, np.sqrt(0.5), BINS + 1)


def measure_one(scan, p):
    """Frequency profile and tone quantiles of a scan, averaged over 4 areas."""
    im = Image.open(scan).convert("L")
    w, h = im.size
    side = round(w / 210 * CSS_PX_MM * TILE / 2)
    r = radius_grid(TILE)
    edges = bin_edges()
    profiles, samples = [], []
    for fx, fy in ((0.3, 0.3), (0.7, 0.3), (0.3, 0.7), (0.7, 0.7)):
        cx, cy = int(w * fx), int(h * fy)
        tile = im.crop((cx - side // 2, cy - side // 2, cx + side // 2, cy + side // 2))
        tile = tile.resize((TILE, TILE), Image.LANCZOS)
        a = np.asarray(tile, float)
        detail = a - np.asarray(tile.filter(ImageFilter.GaussianBlur(p["keep"])), float)
        detail = (detail - detail.mean()) / detail.std()
        amp = np.abs(np.fft.fft2(detail * np.hanning(TILE)[:, None] * np.hanning(TILE)[None, :]))
        profiles.append([amp[(r >= lo) & (r < hi)].mean() if ((r >= lo) & (r < hi)).any() else 0
                         for lo, hi in zip(edges[:-1], edges[1:])])
        samples.append(detail.ravel())
    q = np.quantile(np.concatenate(samples), np.linspace(0, 1, QUANTILES))
    return {"profile": list(np.mean(profiles, axis=0)), "quantiles": list(q)}


def synthesise(stats, p):
    rng = np.random.default_rng(p["seed"])
    r = radius_grid(TILE)
    edges = bin_edges()
    centres = np.sqrt(edges[:-1] * edges[1:])
    prof = np.asarray(stats["profile"])
    ok = prof > 0
    shape = np.interp(np.log(np.maximum(r, centres[0])), np.log(centres[ok]), prof[ok])
    shape[0, 0] = 0                                       # no overall offset
    noise = np.real(np.fft.ifft2(np.fft.fft2(rng.standard_normal((TILE, TILE))) * shape))
    # Give the noise the measured tone distribution (rank-based matching)
    q = np.asarray(stats["quantiles"])
    ranks = noise.ravel().argsort().argsort() / (noise.size - 1)
    detail = np.interp(ranks, np.linspace(0, 1, len(q)), q).reshape(noise.shape)
    detail = (detail - detail.mean()) / detail.std()
    # Short, slightly curly dark fibres, in units of the detail's spread
    fibres, _ = fibre_layer(random.Random(p["seed"]), TILE, dict(
        fibres=p["fibres"], fibre_len=(4, 22), fibre_dark=(10, 30), fibre_light=0))
    detail -= p["fibre_ink"] * fibres / 20
    detail = np.clip(detail, -4.5, 3)
    return p["base"] + p["strength"] * detail


def main():
    if len(sys.argv) >= 3 and sys.argv[1] == "measure":
        source = Path(sys.argv[2]).expanduser()
        stats = {name: measure_one(source / p["scan"], p) for name, p in PAPERS.items()}
        STATS.write_text(json.dumps(stats, indent=1))
        print(f"Measured {len(stats)} papers -> {STATS.name}")
    stats = json.loads(STATS.read_text())
    for name, p in PAPERS.items():
        tex = synthesise(stats[name], p)
        img = Image.fromarray(np.clip(np.round(tex), 0, 255).astype(np.uint8), "L")
        out = OUT / f"paper-{name}.jpg"
        img.save(out, "JPEG", quality=88, optimize=True)
        print(f"{out.name}  ({out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()

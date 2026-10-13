#!/usr/bin/env python3
"""Generate the tileable paper textures (img/paper-<type>.jpg), one per paper type.

Real paper at screen size is mostly "formation": a fine, cloudy unevenness where
the pulp settled thicker or thinner. On top of that comes a little surface
grain and a few faint, short fibres. Older paper adds larger, softer mottling.

Each texture is greyscale, nearly white, and multiplied onto the paper colour
in CSS, so the colours stay as defined in style.css. Noise is filtered in the
frequency domain, which makes it wrap around the edges seamlessly; fibres that
cross an edge are drawn again on the opposite side.

    python3 tools/make_texture.py
"""

import math
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

TILE = 768   # device pixels; shown at 384 CSS px, so sharp on retina screens
OUT = Path(__file__).resolve().parent.parent / "img"

# Sizes are in device pixels (2 per CSS pixel). Amounts are in 0-255 grey levels.
PAPERS = {
    "white": dict(base=251, formation=1.3, floc=8, grain=1.2, mottle=0.0,
                  fibres=1400, fibre_len=(4, 14), fibre_dark=(4, 9), fibre_light=0.25, seed=11),
    "offwhite": dict(base=250, formation=1.7, floc=9, grain=1.3, mottle=0.8,
                     fibres=2000, fibre_len=(4, 16), fibre_dark=(5, 10), fibre_light=0.3, seed=12),
    "cream": dict(base=249, formation=2.1, floc=11, grain=1.5, mottle=1.4,
                  fibres=2600, fibre_len=(5, 18), fibre_dark=(5, 11), fibre_light=0.35, seed=13),
    "aged": dict(base=247, formation=2.6, floc=12, grain=1.7, mottle=3.5,
                 fibres=2600, fibre_len=(5, 18), fibre_dark=(6, 13), fibre_light=0.3, seed=14,
                 specks=40),
    "card": dict(base=245, formation=3.6, floc=10, grain=2.4, mottle=1.5,
                 fibres=4200, fibre_len=(5, 20), fibre_dark=(9, 18), fibre_light=0.3, seed=15),
}


def periodic_noise(rng, size, feature):
    """Smooth, seamlessly tiling noise with blobs about `feature` pixels across (std 1)."""
    white = rng.standard_normal((size, size))
    f = np.fft.fftfreq(size)
    fx, fy = np.meshgrid(f, f)
    sigma = 1.0 / (math.pi * feature)  # gaussian low-pass in frequency space
    spectrum = np.fft.fft2(white) * np.exp(-(fx ** 2 + fy ** 2) / (2 * sigma ** 2))
    out = np.real(np.fft.ifft2(spectrum))
    return (out - out.mean()) / out.std()


def fibre_layer(rng, size, p):
    """Faint short fibres, darker and a few lighter than the paper (grey levels as float)."""
    scale = 2
    big = size * scale
    dark = Image.new("L", (big, big), 0)
    light = Image.new("L", (big, big), 0)
    ddraw, ldraw = ImageDraw.Draw(dark), ImageDraw.Draw(light)
    for _ in range(p["fibres"]):
        x, y = rng.uniform(0, big), rng.uniform(0, big)
        length = rng.uniform(*p["fibre_len"]) * scale
        angle = rng.uniform(0, math.pi)
        bend = rng.uniform(-0.6, 0.6) / length
        pts = []
        for i in range(6):
            pts.append((x, y))
            angle += bend * length / 5
            x += math.cos(angle) * length / 5
            y += math.sin(angle) * length / 5
        is_light = rng.random() < p["fibre_light"]
        draw, value = (ldraw, rng.randint(3, 8)) if is_light else (ddraw, rng.randint(*p["fibre_dark"]))
        for dx in (-big, 0, big):
            for dy in (-big, 0, big):
                draw.line([(px + dx, py + dy) for px, py in pts], fill=value, width=scale, joint="curve")
    # Downsample and soften so the fibres sit inside the sheet
    soften = lambda im: im.resize((size, size), Image.LANCZOS).filter(ImageFilter.GaussianBlur(0.6))
    return np.asarray(soften(dark), float), np.asarray(soften(light), float)


def make(name, p):
    rng = np.random.default_rng(p["seed"])
    tex = np.full((TILE, TILE), float(p["base"]))
    tex -= p["formation"] * periodic_noise(rng, TILE, p["floc"])
    tex -= p["formation"] * 0.35 * periodic_noise(rng, TILE, p["floc"] * 3)
    tex -= p["grain"] * periodic_noise(rng, TILE, 0.8)
    if p["mottle"]:
        tex -= p["mottle"] * periodic_noise(rng, TILE, 140)
    dark, light = fibre_layer(random.Random(p["seed"]), TILE, p)
    tex += light - dark
    yy, xx = np.ogrid[:TILE, :TILE]
    for _ in range(p.get("specks", 0)):  # tiny foxing spots on old paper
        x, y = rng.integers(0, TILE, 2)
        r = rng.uniform(0.8, 2.2)
        d = np.hypot((xx - x + TILE / 2) % TILE - TILE / 2, (yy - y + TILE / 2) % TILE - TILE / 2)
        tex -= rng.uniform(6, 16) * np.exp(-(d / r) ** 2)
    img = Image.fromarray(np.clip(np.round(tex), 0, 255).astype(np.uint8), "L")
    out = OUT / f"paper-{name}.jpg"
    img.save(out, "JPEG", quality=88, optimize=True)
    print(f"Wrote {out.name}  mean {tex.mean():.1f}  ({out.stat().st_size // 1024} KB)")


def main():
    OUT.mkdir(exist_ok=True)
    for old in OUT.glob("paper-fibers-*.jpg"):
        old.unlink()
    for name, params in PAPERS.items():
        make(name, params)


if __name__ == "__main__":
    main()

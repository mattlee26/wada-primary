#!/usr/bin/env python3
"""Extend Wada Primary's categorical palette with colors from Sanzo Wada's
*A Dictionary of Color Combinations*, as published at https://sanzo-wada.dmbk.io/.

The first four categories are the theme's own colors (navy, green, rust,
orange). For categories 5 and up, the script finds the Wada colors closest
to those four, collects the combinations they appear in, and picks the other
colors of those combinations that co-occur with our palette most often,
while staying distinct from each other and usable on a white slide.

It rewrites the block between the <wada-palette> markers in wada-primary.scss and
writes palette.csv (for matching figure colors, e.g. in ggplot2).

    python3 wada_palette.py            # 4 extra colors (8 categories)
    python3 wada_palette.py --extra 6  # 10 categories
"""

import argparse
import csv
import datetime
import json
import math
import re
import urllib.request
from pathlib import Path

SITE = "https://sanzo-wada.dmbk.io/"
HERE = Path(__file__).resolve().parent

BASE = [
    ("Navy", "#202d85"),
    ("Green", "#58771e"),
    ("Rust", "#a93400"),
    ("Orange", "#ff8c00"),
]
INK = "#1f2328"
WHITE = "#ffffff"

ANCHOR_DE = 6      # a Wada color this close (CIEDE2000) stands in for a base color
MIN_DE = 22        # extension colors stay at least this far from every chosen color
MIN_LINE_CONTRAST = 1.9   # against white, so thin rules and bars stay visible
MIN_CHROMA = 18    # skip greys, blacks and near-whites
TEXT_CONTRAST = 4.5


# Data -------------------------------------------------------------------------

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "wada-primary-palette"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8")


def load_swatches():
    """Swatches as embedded in the site's JavaScript bundle."""
    page = fetch(SITE)
    bundle = re.search(r'src="/?(main\.[0-9a-f]+\.js)"', page).group(1)
    js = fetch(SITE + bundle)
    # One JSON block per section of the book: swatches_a ... swatches_f
    groups = {}
    for raw in re.findall(r"JSON\.parse\('(\{\"swatches_[a-z]+\".*?\})'\)", js, re.S):
        groups.update(json.loads(raw.replace("\\'", "'").replace("\\\\", "\\")))
    swatches = []
    for key in sorted(groups):
        swatches.extend(groups[key])
    return swatches


def cmyk_to_hex(cmyk):
    """Same conversion the site uses (chroma.js cmyk -> rgb, rounded half up)."""
    c, m, y, k = (v / 100 for v in cmyk)
    if k >= 1:
        return "#000000"
    rgb = [0 if v >= 1 else 255 * (1 - v) * (1 - k) for v in (c, m, y)]
    return "#" + "".join(f"{int(math.floor(v + 0.5)):02x}" for v in rgb)


# Color maths -------------------------------------------------------------------

def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb):
    return "#" + "".join(f"{max(0, min(255, round(v))):02x}" for v in rgb)


def _lin(v):
    v /= 255
    return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4


def luminance(h):
    r, g, b = (_lin(v) for v in hex_to_rgb(h))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def to_lab(h):
    r, g, b = (_lin(v) for v in hex_to_rgb(h))
    x = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883
    f = lambda t: t ** (1 / 3) if t > 216 / 24389 else (24389 / 27 * t + 16) / 116
    fx, fy, fz = f(x), f(y), f(z)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def from_lab(L, a, b):
    fy = (L + 16) / 116
    fx, fz = fy + a / 500, fy - b / 200
    inv = lambda t: t ** 3 if t ** 3 > 216 / 24389 else (116 * t - 16) / (24389 / 27)
    x, y, z = inv(fx) * 0.95047, inv(fy), inv(fz) * 1.08883
    rl = 3.2406 * x - 1.5372 * y - 0.4986 * z
    gl = -0.9689 * x + 1.8758 * y + 0.0415 * z
    bl = 0.0557 * x - 0.2040 * y + 1.0570 * z
    g = lambda v: 255 * (12.92 * v if v <= 0.0031308 else 1.055 * max(v, 0) ** (1 / 2.4) - 0.055)
    return rgb_to_hex((g(rl), g(gl), g(bl)))


def chroma(h):
    _, a, b = to_lab(h)
    return math.hypot(a, b)


def delta_e(h1, h2):
    """CIEDE2000."""
    L1, a1, b1 = to_lab(h1)
    L2, a2, b2 = to_lab(h2)
    C1, C2 = math.hypot(a1, b1), math.hypot(a2, b2)
    Cm = (C1 + C2) / 2
    G = 0.5 * (1 - math.sqrt(Cm ** 7 / (Cm ** 7 + 25 ** 7)))
    a1p, a2p = a1 * (1 + G), a2 * (1 + G)
    C1p, C2p = math.hypot(a1p, b1), math.hypot(a2p, b2)
    h1p = math.degrees(math.atan2(b1, a1p)) % 360
    h2p = math.degrees(math.atan2(b2, a2p)) % 360
    dL, dC = L2 - L1, C2p - C1p
    dh = 0 if C1p * C2p == 0 else (h2p - h1p + 180) % 360 - 180
    dH = 2 * math.sqrt(C1p * C2p) * math.sin(math.radians(dh / 2))
    Lm, Cpm = (L1 + L2) / 2, (C1p + C2p) / 2
    if C1p * C2p == 0:
        hm = h1p + h2p
    elif abs(h1p - h2p) <= 180:
        hm = (h1p + h2p) / 2
    else:
        hm = (h1p + h2p + 360) / 2 if h1p + h2p < 360 else (h1p + h2p - 360) / 2
    T = (1 - 0.17 * math.cos(math.radians(hm - 30)) + 0.24 * math.cos(math.radians(2 * hm))
         + 0.32 * math.cos(math.radians(3 * hm + 6)) - 0.20 * math.cos(math.radians(4 * hm - 63)))
    SL = 1 + 0.015 * (Lm - 50) ** 2 / math.sqrt(20 + (Lm - 50) ** 2)
    SC, SH = 1 + 0.045 * Cpm, 1 + 0.015 * Cpm * T
    RT = (-2 * math.sqrt(Cpm ** 7 / (Cpm ** 7 + 25 ** 7))
          * math.sin(math.radians(60 * math.exp(-(((hm - 275) / 25) ** 2)))))
    return math.sqrt((dL / SL) ** 2 + (dC / SC) ** 2 + (dH / SH) ** 2
                     + RT * (dC / SC) * (dH / SH))


def text_variant(h, others):
    """The color itself if it reads on white; else darkened until it does,
    falling back to ink if darkening makes it look like another palette color."""
    if contrast(h, WHITE) >= TEXT_CONTRAST:
        return h
    L, a, b = to_lab(h)
    while L > 0:
        L -= 1
        d = from_lab(L, a, b)
        if contrast(d, WHITE) >= TEXT_CONTRAST:
            return INK if any(delta_e(d, o) < 15 for o in others) else d
    return INK


def on_color(h):
    """Text color for labels sitting on a bar of this color."""
    return WHITE if contrast(h, WHITE) >= TEXT_CONTRAST else INK


# Selection -----------------------------------------------------------------------

def select(swatches, extra):
    colors = [{"name": s["name"], "hex": cmyk_to_hex(s["cmyk"]), "combos": set(s["combinations"])}
               for s in swatches]
    base_hex = [h for _, h in BASE]

    # Wada colors standing in for each base color
    anchors = {}
    for name, h in BASE:
        near = [c for c in colors if delta_e(c["hex"], h) <= ANCHOR_DE]
        anchors[name] = near or [min(colors, key=lambda c: delta_e(c["hex"], h))]

    # Combinations containing an anchor, weighted by how many base colors they hold
    combo_bases = {}
    for name, cs in anchors.items():
        for c in cs:
            for k in c["combos"]:
                combo_bases.setdefault(k, set()).add(name)

    anchor_names = {c["name"] for cs in anchors.values() for c in cs}
    candidates = []
    for c in colors:
        if c["name"] in anchor_names:
            continue
        shared = {k: combo_bases[k] for k in c["combos"] if k in combo_bases}
        if not shared:
            continue
        score = sum(len(b) for b in shared.values())
        usable = (contrast(c["hex"], WHITE) >= MIN_LINE_CONTRAST
                  and chroma(c["hex"]) >= MIN_CHROMA
                  and delta_e(c["hex"], INK) >= 20)
        if usable:
            candidates.append({**c, "score": score, "shared": shared})
    candidates.sort(key=lambda c: (-c["score"], c["name"]))

    chosen = []
    min_de = MIN_DE
    while len(chosen) < extra and min_de > 5:
        for c in candidates:
            if len(chosen) >= extra:
                break
            if c in chosen:
                continue
            if all(delta_e(c["hex"], o) >= min_de for o in base_hex + [x["hex"] for x in chosen]):
                chosen.append(c)
        min_de -= 3  # relax only if the palette could not be filled
    return anchors, chosen


# Output ----------------------------------------------------------------------------

def scss_block(chosen):
    lines_ = [h for _, h in BASE] + [c["hex"] for c in chosen]
    text = []
    for h in lines_:
        text.append(text_variant(h, [t for t in text]))
    on = [on_color(h) for h in lines_]
    stamp = datetime.date.today().isoformat()
    out = [
        "// <wada-palette> generated by wada_palette.py on " + stamp + "; edit the script, not this block",
        "// Categories 5+ come from Sanzo Wada's Dictionary of Color Combinations (sanzo-wada.dmbk.io)",
    ]
    for i, c in enumerate(chosen, start=len(BASE) + 1):
        with_ = sorted({b for bs in c["shared"].values() for b in bs})
        combos = ", ".join(str(k) for k in sorted(c["shared"]))
        out.append(f"//   {i}. {c['name']} {c['hex']}: Wada combinations {combos} (with {', '.join(with_).lower()})")
    out += [
        "$cat-lines: (" + ", ".join(lines_) + ") !default;   // rules, bars",
        "$cat-text: (" + ", ".join(text) + ") !default;   // numbers on white",
        "$cat-on: (" + ", ".join(on) + ") !default;   // labels on bars",
        "// </wada-palette>",
    ]
    return "\n".join(out), lines_, text, on


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--extra", type=int, default=4, help="colors to add after the base four (default 4)")
    args = ap.parse_args()

    swatches = load_swatches()
    anchors, chosen = select(swatches, args.extra)
    block, lines_, text, on = scss_block(chosen)

    scss = HERE / "wada-primary.scss"
    src = scss.read_text()
    new, n = re.subn(r"// <wada-palette>.*?// </wada-palette>", lambda _: block, src, flags=re.S)
    if n != 1:
        raise SystemExit("wada-primary.scss needs exactly one <wada-palette> ... </wada-palette> block")
    scss.write_text(new)

    names = [n for n, _ in BASE] + [c["name"] for c in chosen]
    with open(HERE / "palette.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["category", "name", "hex", "text_hex", "label_on_fill", "source"])
        for i, (nm, h, t, o) in enumerate(zip(names, lines_, text, on), start=1):
            src_ = "Theme" if i <= len(BASE) else "Wada " + " ".join(
                str(k) for k in sorted(chosen[i - len(BASE) - 1]["shared"]))
            w.writerow([i, nm, h, t, o, src_])

    print(f"{len(swatches)} Wada colors read from {SITE}")
    for name, cs in anchors.items():
        print(f"  {name:<7} ~ " + ", ".join(f"{c['name']} {c['hex']}" for c in cs))
    print(block)


if __name__ == "__main__":
    main()

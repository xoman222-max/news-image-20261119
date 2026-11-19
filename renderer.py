#!/usr/bin/env python3
"""news-image renderer: draw a one-day world news front page (1024x1024 PNG).

Reads stories.json (see schema in BUILD-NOTE.md) and renders entry.png.
Pure PIL, no network, deterministic output: same input -> byte-identical PNG.

Layout (copies the 11/17 champion formula):
  header (eyebrow + giant serif date) -> UTC timeline -> 4x4 featured grid
  -> world map with numbered pins + ALSO ON list -> DATE CHECK bar -> footer.
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1024, 1024
PAPER = (247, 243, 233)      # warm newsprint
PAPER_DARK = (238, 232, 216)
INK = (26, 26, 26)
RED = (158, 28, 28)
RED_DARK = (120, 20, 20)
GREY = (110, 105, 92)
RULE = (60, 55, 45)
MAP_OCEAN = (205, 224, 231)
MAP_LAND = (233, 224, 200)
MAP_LINE = (172, 160, 128)

FONT_DIR_DEJAVU = "/usr/share/fonts/truetype/dejavu"
FONT_DIR_LIB = "/usr/share/fonts/truetype/liberation"
SERIF_B = f"{FONT_DIR_DEJAVU}/DejaVuSerif-Bold.ttf"
SERIF = f"{FONT_DIR_DEJAVU}/DejaVuSerif.ttf"
SANS = f"{FONT_DIR_LIB}/LiberationSans-Regular.ttf"
SANS_B = f"{FONT_DIR_LIB}/LiberationSans-Bold.ttf"
SANS_I = f"{FONT_DIR_LIB}/LiberationSans-Italic.ttf"

_font_cache = {}


def font(path, size):
    key = (path, size)
    if key not in _font_cache:
        _font_cache[key] = ImageFont.truetype(path, size)
    return _font_cache[key]


def text_w(f, s):
    """Pixel width of s in font f."""
    return f.getlength(s)


def wrap(f, text, max_w):
    """Greedy word wrap by pixel width. Returns list of lines."""
    words = text.split()
    if not words:
        return [""]
    lines, cur = [], words[0]
    for w in words[1:]:
        trial = cur + " " + w
        if f.getlength(trial) <= max_w:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    return lines


def fit(f, text, max_w, max_lines, start_size, min_size, path):
    """Shrink font until text fits in max_lines lines of max_w. Returns (font, lines)."""
    size = start_size
    while size >= min_size:
        ff = font(path, size)
        lines = wrap(ff, text, max_w)
        if len(lines) <= max_lines:
            return ff, lines
        size -= 1
    ff = font(path, min_size)
    return ff, wrap(ff, text, max_w)


def ellipsize(f, text, max_w):
    """Trim text to fit max_w, ending with an ellipsis mark."""
    if f.getlength(text) <= max_w:
        return text
    while text and f.getlength(text + "\u2026") > max_w:
        text = text.rsplit(" ", 1)[0] if " " in text else text[:-1]
    return text + "\u2026"


def draw_lines(d, x, y, lines, f, fill, leading):
    for ln in lines:
        d.text((x, y), ln, font=f, fill=fill)
        y += leading
    return y


def draw_centered(d, cx, y, s, f, fill):
    w = f.getlength(s)
    d.text((cx - w / 2, y), s, font=f, fill=fill)


def hline(d, x0, x1, y, fill=INK, w=2):
    d.line([(x0, y), (x1, y)], fill=fill, width=w)


def month_name(m):
    return ["January", "February", "March", "April", "May", "June", "July",
            "August", "September", "October", "November", "December"][m - 1]


def parse_date(date_s):
    y, m, dd = (int(p) for p in date_s.split("-"))
    return y, m, dd


def full_date(data):
    y, m, dd = parse_date(data["date"])
    return f"{data['weekday']} {dd} {month_name(m)} {y}"


def short_date(data):
    y, m, dd = parse_date(data["date"])
    return f"{dd} {month_name(m)} {y}"


# ---------------------------------------------------------------- icons
# Flat vector mini-illustrations. Each draws a simple glyph into box
# (x0, y0, x1, y1); bg is the panel colour, fg the glyph colour.
def _box_geom(box):
    x0, y0, x1, y1 = box
    return x0, y0, x1, y1, (x0 + x1) / 2, (y0 + y1) / 2, x1 - x0, y1 - y0


def ic_bridge(d, box, bg, fg):
    x0, y0, x1, y1, cx, cy, w, h = _box_geom(box)
    d.rectangle(box, fill=bg)
    d.rectangle([x0, y1 - h * 0.28, x1, y1 - h * 0.20], fill=fg)  # deck
    d.rectangle([x0 + w * 0.18, y0 + h * 0.18, x0 + w * 0.26, y1 - h * 0.20], fill=fg)
    d.rectangle([x0 + w * 0.74, y0 + h * 0.18, x0 + w * 0.82, y1 - h * 0.20], fill=fg)
    d.line([(x0 + w * 0.22, y0 + h * 0.18), (cx, y1 - h * 0.24)], fill=fg, width=2)
    d.line([(x0 + w * 0.78, y0 + h * 0.18), (cx, y1 - h * 0.24)], fill=fg, width=2)
    d.polygon([(x0 + w * 0.42, y1 - h * 0.28), (x0 + w * 0.52, y1 - h * 0.28),
               (x0 + w * 0.47, y1 - h * 0.55)], fill=RED)  # broken span
    d.line([(x0 + w * 0.30, y1 - h * 0.10), (x0 + w * 0.70, y1 - h * 0.10)], fill=fg, width=2)


def ic_drone(d, box, bg, fg):
    x0, y0, x1, y1, cx, cy, w, h = _box_geom(box)
    d.rectangle(box, fill=bg)
    for px, py in [(0.25, 0.30), (0.75, 0.30), (0.25, 0.70), (0.75, 0.70)]:
        d.ellipse([x0 + w * px - 5, y0 + h * py - 5, x0 + w * px + 5, y0 + h * py + 5],
                  outline=fg, width=2)
        d.line([(x0 + w * px, y0 + h * py), (cx, cy)], fill=fg, width=2)
    d.ellipse([cx - 12, cy - 8, cx + 12, cy + 8], fill=fg)
    d.ellipse([cx - 4, cy - 3, cx + 4, cy + 3], fill=RED)
    d.line([(cx, cy + 8), (cx, y1 - h * 0.12)], fill=RED, width=3)


def ic_summit(d, box, bg, fg):
    x0, y0, x1, y1, cx, cy, w, h = _box_geom(box)
    d.rectangle(box, fill=bg)
    d.rectangle([x0 + w * 0.12, y0 + h * 0.55, x0 + w * 0.88, y0 + h * 0.66], fill=fg)
    d.rectangle([x0 + w * 0.20, y0 + h * 0.66, x0 + w * 0.26, y1 - h * 0.08], fill=fg)
    d.rectangle([x0 + w * 0.74, y0 + h * 0.66, x0 + w * 0.80, y1 - h * 0.08], fill=fg)
    for i, col in enumerate([(158, 28, 28), (43, 94, 167), (122, 74, 158)]):
        fx = x0 + w * (0.28 + 0.22 * i)
        d.line([(fx, y0 + h * 0.12), (fx, y0 + h * 0.55)], fill=fg, width=2)
        d.rectangle([fx, y0 + h * 0.12, fx + w * 0.13, y0 + h * 0.28], fill=col)


def ic_virus(d, box, bg, fg):
    x0, y0, x1, y1, cx, cy, w, h = _box_geom(box)
    d.rectangle(box, fill=bg)
    for ang in range(0, 360, 45):
        import math
        a = math.radians(ang)
        x2, y2 = cx + 17 * math.cos(a), cy + 17 * math.sin(a)
        d.line([(cx, cy), (x2, y2)], fill=fg, width=3)
        d.ellipse([x2 - 3, y2 - 3, x2 + 3, y2 + 3], fill=fg)
    d.ellipse([cx - 14, cy - 14, cx + 14, cy + 14], fill=fg)
    d.ellipse([cx - 5, cy - 6, cx + 2, cy + 1], fill=bg)


def ic_climate(d, box, bg, fg):
    x0, y0, x1, y1, cx, cy, w, h = _box_geom(box)
    d.rectangle(box, fill=bg)
    d.ellipse([cx - 16, cy - 16, cx + 16, cy + 16], fill=(94, 164, 120))
    d.arc([cx - 16, cy - 16, cx + 16, cy + 16], 200, 340, fill=(255, 255, 255), width=3)
    d.rectangle([x0 + w * 0.72, y0 + h * 0.18, x0 + w * 0.80, y0 + h * 0.82], fill=fg)
    d.ellipse([x0 + w * 0.68, y0 + h * 0.10, x0 + w * 0.84, y0 + h * 0.26], fill=RED)
    d.line([(x0 + w * 0.76, y0 + h * 0.30), (x0 + w * 0.76, y0 + h * 0.70)], fill=(255, 255, 255), width=2)


def ic_gavel(d, box, bg, fg):
    x0, y0, x1, y1, cx, cy, w, h = _box_geom(box)
    d.rectangle(box, fill=bg)
    d.rectangle([x0 + w * 0.30, y0 + h * 0.62, x0 + w * 0.70, y0 + h * 0.72], fill=fg)
    d.line([(x0 + w * 0.50, y0 + h * 0.62), (x0 + w * 0.68, y0 + h * 0.30)], fill=fg, width=4)
    d.rectangle([x0 + w * 0.58, y0 + h * 0.18, x0 + w * 0.82, y0 + h * 0.34], fill=fg)
    d.rectangle([x0 + w * 0.18, y0 + h * 0.78, x0 + w * 0.38, y0 + h * 0.86], fill=RED)


def ic_plane(d, box, bg, fg):
    x0, y0, x1, y1, cx, cy, w, h = _box_geom(box)
    d.rectangle(box, fill=bg)
    d.polygon([(x0 + w * 0.10, cy), (x0 + w * 0.45, cy - h * 0.12),
               (x0 + w * 0.88, cy - h * 0.05), (x0 + w * 0.88, cy + h * 0.05),
               (x0 + w * 0.45, cy + h * 0.12)], fill=fg)
    d.polygon([(x0 + w * 0.42, cy - h * 0.10), (x0 + w * 0.55, cy - h * 0.32),
               (x0 + w * 0.62, cy - h * 0.10)], fill=fg)
    d.polygon([(x0 + w * 0.42, cy + h * 0.10), (x0 + w * 0.55, cy + h * 0.32),
               (x0 + w * 0.62, cy + h * 0.10)], fill=fg)
    d.line([(x0 + w * 0.12, y1 - h * 0.16), (x0 + w * 0.88, y1 - h * 0.16)], fill=fg, width=2)


def ic_chart(d, box, bg, fg):
    x0, y0, x1, y1, cx, cy, w, h = _box_geom(box)
    d.rectangle(box, fill=bg)
    d.line([(x0 + w * 0.15, y0 + h * 0.15), (x0 + w * 0.15, y1 - h * 0.15)], fill=fg, width=2)
    d.line([(x0 + w * 0.15, y1 - h * 0.15), (x0 + w * 0.88, y1 - h * 0.15)], fill=fg, width=2)
    pts = [(0.20, 0.30), (0.36, 0.42), (0.52, 0.38), (0.68, 0.58), (0.84, 0.72)]
    xy = [(x0 + w * px, y0 + h * py) for px, py in pts]
    d.line(xy, fill=RED, width=3)
    for px, py in xy:
        d.ellipse([px - 3, py - 3, px + 3, py + 3], fill=RED)


def ic_march(d, box, bg, fg):
    x0, y0, x1, y1, cx, cy, w, h = _box_geom(box)
    d.rectangle(box, fill=bg)
    for i in range(5):
        px = x0 + w * (0.16 + 0.17 * i)
        d.ellipse([px - 5, y0 + h * 0.22, px + 5, y0 + h * 0.38], fill=fg)
        d.rectangle([px - 6, y0 + h * 0.40, px + 6, y0 + h * 0.78], fill=fg)
    d.rectangle([x0 + w * 0.14, y0 + h * 0.14, x0 + w * 0.86, y0 + h * 0.20], fill=RED)


def ic_resign(d, box, bg, fg):
    x0, y0, x1, y1, cx, cy, w, h = _box_geom(box)
    d.rectangle(box, fill=bg)
    d.rectangle([x0 + w * 0.24, y0 + h * 0.14, x0 + w * 0.68, y0 + h * 0.86], fill=(255, 255, 255),
                outline=fg, width=2)
    for i in range(3):
        d.line([(x0 + w * 0.30, y0 + h * (0.30 + 0.14 * i)),
                (x0 + w * 0.62, y0 + h * (0.30 + 0.14 * i))], fill=fg, width=2)
    d.line([(x0 + w * 0.68, y0 + h * 0.80), (x0 + w * 0.86, y0 + h * 0.30)], fill=RED, width=3)


def ic_parliament(d, box, bg, fg):
    x0, y0, x1, y1, cx, cy, w, h = _box_geom(box)
    d.rectangle(box, fill=bg)
    d.polygon([(x0 + w * 0.12, y0 + h * 0.38), (cx, y0 + h * 0.14),
               (x0 + w * 0.88, y0 + h * 0.38)], fill=fg)
    d.rectangle([x0 + w * 0.14, y0 + h * 0.38, x0 + w * 0.86, y0 + h * 0.44], fill=fg)
    for i in range(4):
        px = x0 + w * (0.22 + 0.18 * i)
        d.rectangle([px - 4, y0 + h * 0.44, px + 4, y0 + h * 0.80], fill=fg)
    d.rectangle([x0 + w * 0.12, y0 + h * 0.80, x0 + w * 0.88, y0 + h * 0.86], fill=fg)


def ic_sanctions(d, box, bg, fg):
    x0, y0, x1, y1, cx, cy, w, h = _box_geom(box)
    d.rectangle(box, fill=bg)
    d.rectangle([x0 + w * 0.30, y0 + h * 0.30, x0 + w * 0.70, y0 + h * 0.70], fill=fg)
    d.ellipse([cx - 20, cy - 20, cx + 20, cy + 20], outline=RED, width=4)
    d.line([(cx - 14, cy + 14), (cx + 14, cy - 14)], fill=RED, width=4)


def ic_conflict(d, box, bg, fg):
    x0, y0, x1, y1, cx, cy, w, h = _box_geom(box)
    import math
    d.rectangle(box, fill=bg)
    pts = []
    for i in range(16):
        a = math.radians(i * 22.5)
        r = 20 if i % 2 == 0 else 9
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    d.polygon(pts, fill=(232, 126, 32))
    d.ellipse([cx - 6, cy - 6, cx + 6, cy + 6], fill=RED)


def ic_factory(d, box, bg, fg):
    x0, y0, x1, y1, cx, cy, w, h = _box_geom(box)
    d.rectangle(box, fill=bg)
    d.rectangle([x0 + w * 0.14, y0 + h * 0.48, x0 + w * 0.86, y0 + h * 0.84], fill=fg)
    d.rectangle([x0 + w * 0.18, y0 + h * 0.20, x0 + w * 0.28, y0 + h * 0.48], fill=fg)
    d.ellipse([x0 + w * 0.16, y0 + h * 0.10, x0 + w * 0.26, y0 + h * 0.20], fill=(255, 255, 255))
    d.ellipse([x0 + w * 0.24, y0 + h * 0.06, x0 + w * 0.34, y0 + h * 0.16], fill=(255, 255, 255))
    for i in range(3):
        d.rectangle([x0 + w * (0.36 + 0.16 * i), y0 + h * 0.58,
                     x0 + w * (0.46 + 0.16 * i), y0 + h * 0.70], fill=bg)


def ic_train(d, box, bg, fg):
    x0, y0, x1, y1, cx, cy, w, h = _box_geom(box)
    d.rectangle(box, fill=bg)
    d.rectangle([x0 + w * 0.14, y0 + h * 0.22, x0 + w * 0.86, y0 + h * 0.68], fill=fg)
    for i in range(3):
        d.rectangle([x0 + w * (0.22 + 0.20 * i), y0 + h * 0.32,
                     x0 + w * (0.34 + 0.20 * i), y0 + h * 0.48], fill=bg)
    d.line([(x0 + w * 0.10, y1 - h * 0.16), (x0 + w * 0.90, y1 - h * 0.16)], fill=fg, width=3)
    d.line([(x0 + w * 0.10, y1 - h * 0.08), (x0 + w * 0.90, y1 - h * 0.08)], fill=fg, width=2)


def ic_cyclone(d, box, bg, fg):
    x0, y0, x1, y1, cx, cy, w, h = _box_geom(box)
    d.rectangle(box, fill=bg)
    for r, a0 in [(18, 0), (13, 60), (8, 120)]:
        d.arc([cx - r, cy - r, cx + r, cy + r], a0, a0 + 220, fill=fg, width=3)
    d.ellipse([cx - 3, cy - 3, cx + 3, cy + 3], fill=RED)
    d.line([(x0 + w * 0.15, y1 - h * 0.14), (x0 + w * 0.85, y1 - h * 0.14)], fill=fg, width=2)


def ic_globe(d, box, bg, fg):
    x0, y0, x1, y1, cx, cy, w, h = _box_geom(box)
    d.rectangle(box, fill=bg)
    d.ellipse([cx - 17, cy - 17, cx + 17, cy + 17], fill=(94, 164, 120))
    d.ellipse([cx - 17, cy - 17, cx + 17, cy + 17], outline=fg, width=2)
    d.arc([cx - 17, cy - 17, cx + 17, cy + 17], 90, 270, fill=(255, 255, 255), width=2)
    d.line([(cx - 17, cy), (cx + 17, cy)], fill=(255, 255, 255), width=2)
    d.ellipse([cx - 17, cy - 17, cx + 17, cy + 17], outline=fg, width=2)


def ic_ship(d, box, bg, fg):
    x0, y0, x1, y1, cx, cy, w, h = _box_geom(box)
    d.rectangle(box, fill=bg)
    d.polygon([(x0 + w * 0.14, y0 + h * 0.58), (x0 + w * 0.86, y0 + h * 0.58),
               (x0 + w * 0.76, y0 + h * 0.78), (x0 + w * 0.24, y0 + h * 0.78)], fill=fg)
    d.rectangle([x0 + w * 0.40, y0 + h * 0.34, x0 + w * 0.60, y0 + h * 0.58], fill=fg)
    d.line([(cx, y0 + h * 0.14), (cx, y0 + h * 0.34)], fill=fg, width=2)
    d.polygon([(cx, y0 + h * 0.14), (cx + w * 0.14, y0 + h * 0.24), (cx, y0 + h * 0.24)], fill=RED)
    d.line([(x0 + w * 0.12, y1 - h * 0.10), (x0 + w * 0.88, y1 - h * 0.10)], fill=fg, width=2)


def ic_fire(d, box, bg, fg):
    x0, y0, x1, y1, cx, cy, w, h = _box_geom(box)
    d.rectangle(box, fill=bg)
    d.polygon([(cx, y0 + h * 0.14), (cx + w * 0.16, y0 + h * 0.50),
               (cx + w * 0.10, y0 + h * 0.50), (cx + w * 0.22, y0 + h * 0.78),
               (cx - w * 0.22, y0 + h * 0.78), (cx - w * 0.10, y0 + h * 0.50),
               (cx - w * 0.16, y0 + h * 0.50)], fill=(232, 126, 32))
    d.ellipse([cx - 7, cy + 2, cx + 7, cy + 16], fill=(245, 197, 66))


def ic_ballot(d, box, bg, fg):
    x0, y0, x1, y1, cx, cy, w, h = _box_geom(box)
    d.rectangle(box, fill=bg)
    d.rectangle([x0 + w * 0.22, y0 + h * 0.16, x0 + w * 0.78, y0 + h * 0.84], fill=(255, 255, 255),
                outline=fg, width=2)
    d.line([(x0 + w * 0.34, y0 + h * 0.50), (x0 + w * 0.46, y0 + h * 0.64),
            (x0 + w * 0.68, y0 + h * 0.30)], fill=RED, width=4)
    d.line([(x0 + w * 0.30, y0 + h * 0.24), (x0 + w * 0.70, y0 + h * 0.24)], fill=fg, width=2)


def ic_quake(d, box, bg, fg):
    x0, y0, x1, y1, cx, cy, w, h = _box_geom(box)
    d.rectangle(box, fill=bg)
    d.line([(x0 + w * 0.12, y0 + h * 0.68), (x0 + w * 0.88, y0 + h * 0.68)], fill=fg, width=3)
    pts = [(0.14, 0.68), (0.24, 0.68), (0.30, 0.40), (0.38, 0.68), (0.46, 0.68),
           (0.54, 0.30), (0.62, 0.68), (0.70, 0.68), (0.78, 0.50), (0.86, 0.68)]
    d.line([(x0 + w * px, y0 + h * py) for px, py in pts], fill=RED, width=2)


def ic_trophy(d, box, bg, fg):
    x0, y0, x1, y1, cx, cy, w, h = _box_geom(box)
    d.rectangle(box, fill=bg)
    d.polygon([(cx - 12, y0 + h * 0.18), (cx + 12, y0 + h * 0.18),
               (cx + 8, y0 + h * 0.48), (cx - 8, y0 + h * 0.48)], fill=(212, 160, 32))
    d.arc([cx - 20, y0 + h * 0.18, cx - 4, y0 + h * 0.44], 90, 270, fill=(212, 160, 32), width=3)
    d.arc([cx + 4, y0 + h * 0.18, cx + 20, y0 + h * 0.44], -90, 90, fill=(212, 160, 32), width=3)
    d.rectangle([cx - 3, y0 + h * 0.48, cx + 3, y0 + h * 0.66], fill=fg)
    d.rectangle([cx - 12, y0 + h * 0.66, cx + 12, y0 + h * 0.74], fill=fg)


def ic_capitol(d, box, bg, fg):
    x0, y0, x1, y1, cx, cy, w, h = _box_geom(box)
    d.rectangle(box, fill=bg)
    d.pieslice([cx - 13, y0 + h * 0.10, cx + 13, y0 + h * 0.46], 180, 360, fill=fg)
    d.rectangle([x0 + w * 0.16, y0 + h * 0.44, x0 + w * 0.84, y0 + h * 0.50], fill=fg)
    for i in range(4):
        px = x0 + w * (0.24 + 0.17 * i)
        d.rectangle([px - 3, y0 + h * 0.50, px + 3, y0 + h * 0.80], fill=fg)
    d.rectangle([x0 + w * 0.14, y0 + h * 0.80, x0 + w * 0.86, y0 + h * 0.86], fill=fg)


def ic_chip(d, box, bg, fg):
    x0, y0, x1, y1, cx, cy, w, h = _box_geom(box)
    d.rectangle(box, fill=bg)
    for i in range(3):
        d.line([(x0 + w * (0.28 + 0.16 * i), y0 + h * 0.16),
                (x0 + w * (0.28 + 0.16 * i), y0 + h * 0.30)], fill=fg, width=2)
        d.line([(x0 + w * (0.28 + 0.16 * i), y0 + h * 0.70),
                (x0 + w * (0.28 + 0.16 * i), y0 + h * 0.84)], fill=fg, width=2)
        d.line([(x0 + w * 0.16, y0 + h * (0.30 + 0.16 * i)),
                (x0 + w * 0.30, y0 + h * (0.30 + 0.16 * i))], fill=fg, width=2)
        d.line([(x0 + w * 0.70, y0 + h * (0.30 + 0.16 * i)),
                (x0 + w * 0.84, y0 + h * (0.30 + 0.16 * i))], fill=fg, width=2)
    d.rectangle([x0 + w * 0.30, y0 + h * 0.30, x0 + w * 0.70, y0 + h * 0.70], fill=fg)
    d.rectangle([x0 + w * 0.40, y0 + h * 0.40, x0 + w * 0.60, y0 + h * 0.60], fill=bg)


def ic_court(d, box, bg, fg):
    x0, y0, x1, y1, cx, cy, w, h = _box_geom(box)
    d.rectangle(box, fill=bg)
    d.line([(cx, y0 + h * 0.16), (cx, y0 + h * 0.78)], fill=fg, width=3)
    d.line([(x0 + w * 0.22, y0 + h * 0.26), (x0 + w * 0.78, y0 + h * 0.26)], fill=fg, width=3)
    for px in (0.22, 0.78):
        d.line([(x0 + w * px, y0 + h * 0.26), (x0 + w * px, y0 + h * 0.42)], fill=fg, width=2)
        d.pieslice([x0 + w * px - 9, y0 + h * 0.40, x0 + w * px + 9, y0 + h * 0.58], 0, 180, fill=fg)
    d.rectangle([cx - 12, y0 + h * 0.78, cx + 12, y0 + h * 0.84], fill=fg)


def ic_drought(d, box, bg, fg):
    x0, y0, x1, y1, cx, cy, w, h = _box_geom(box)
    d.rectangle(box, fill=bg)
    d.ellipse([cx - 11, y0 + h * 0.12, cx + 11, y0 + h * 0.36], fill=(245, 197, 66))
    import math
    for i in range(8):
        a = math.radians(i * 45)
        d.line([(cx + 14 * math.cos(a), y0 + h * 0.24 + 14 * math.sin(a)),
                (cx + 19 * math.cos(a), y0 + h * 0.24 + 19 * math.sin(a))], fill=fg, width=2)
    for i in range(3):
        d.line([(x0 + w * (0.18 + 0.10 * i), y0 + h * 0.62),
                (x0 + w * (0.26 + 0.10 * i), y0 + h * 0.74),
                (x0 + w * (0.38 + 0.10 * i), y0 + h * 0.62)], fill=fg, width=2)
    d.line([(x0 + w * 0.14, y0 + h * 0.84), (x0 + w * 0.86, y0 + h * 0.84)], fill=fg, width=2)


def ic_eu(d, box, bg, fg):
    x0, y0, x1, y1, cx, cy, w, h = _box_geom(box)
    import math
    d.rectangle(box, fill=bg)
    d.rectangle([x0 + w * 0.20, y0 + h * 0.18, x0 + w * 0.80, y0 + h * 0.82], fill=(0, 51, 153))
    for i in range(12):
        a = math.radians(i * 30 - 90)
        sx, sy = cx + 13 * math.cos(a), cy + 13 * math.sin(a)
        d.ellipse([sx - 2, sy - 2, sx + 2, sy + 2], fill=(255, 204, 0))


def ic_football(d, box, bg, fg):
    x0, y0, x1, y1, cx, cy, w, h = _box_geom(box)
    d.rectangle(box, fill=bg)
    d.ellipse([cx - 16, cy - 16, cx + 16, cy + 16], fill=(255, 255, 255), outline=fg, width=2)
    d.polygon([(cx, cy - 7), (cx + 7, cy - 2), (cx + 4, cy + 6),
               (cx - 4, cy + 6), (cx - 7, cy - 2)], fill=fg)
    for px, py in [(0, -16), (15, -5), (9, 13), (-9, 13), (-15, -5)]:
        d.line([(cx, cy), (cx + px, cy + py)], fill=fg, width=1)


def ic_game(d, box, bg, fg):
    x0, y0, x1, y1, cx, cy, w, h = _box_geom(box)
    d.rectangle(box, fill=bg)
    d.rounded_rectangle([x0 + w * 0.12, y0 + h * 0.30, x0 + w * 0.88, y0 + h * 0.72],
                        radius=8, fill=fg)
    d.line([(x0 + w * 0.28, cy - 2), (x0 + w * 0.28, cy + 10)], fill=bg, width=3)
    d.line([(x0 + w * 0.22, cy + 4), (x0 + w * 0.34, cy + 4)], fill=bg, width=3)
    for px, py in [(0.68, 0.44), (0.76, 0.52), (0.68, 0.60), (0.60, 0.52)]:
        d.ellipse([x0 + w * px - 3, y0 + h * py - 3, x0 + w * px + 3, y0 + h * py + 3],
                  fill=RED)


def ic_missile(d, box, bg, fg):
    x0, y0, x1, y1, cx, cy, w, h = _box_geom(box)
    d.rectangle(box, fill=bg)
    d.polygon([(cx, y0 + h * 0.10), (cx + 8, y0 + h * 0.34), (cx + 8, y0 + h * 0.62),
               (cx - 8, y0 + h * 0.62), (cx - 8, y0 + h * 0.34)], fill=fg)
    d.polygon([(cx - 8, y0 + h * 0.50), (cx - 16, y0 + h * 0.70), (cx - 8, y0 + h * 0.66)], fill=fg)
    d.polygon([(cx + 8, y0 + h * 0.50), (cx + 16, y0 + h * 0.70), (cx + 8, y0 + h * 0.66)], fill=fg)
    d.polygon([(cx - 5, y0 + h * 0.62), (cx + 5, y0 + h * 0.62),
               (cx, y0 + h * 0.86)], fill=(232, 126, 32))


def ic_protest(d, box, bg, fg):
    x0, y0, x1, y1, cx, cy, w, h = _box_geom(box)
    d.rectangle(box, fill=bg)
    for i in range(4):
        px = x0 + w * (0.20 + 0.20 * i)
        d.ellipse([px - 5, y0 + h * 0.48, px + 5, y0 + h * 0.62], fill=fg)
        d.rectangle([px - 6, y0 + h * 0.64, px + 6, y0 + h * 0.82], fill=fg)
    d.line([(x0 + w * 0.62, y0 + h * 0.44), (x0 + w * 0.62, y0 + h * 0.18)], fill=fg, width=2)
    d.rectangle([x0 + w * 0.62, y0 + h * 0.12, x0 + w * 0.88, y0 + h * 0.30], fill=RED)


def ic_tank(d, box, bg, fg):
    x0, y0, x1, y1, cx, cy, w, h = _box_geom(box)
    d.rectangle(box, fill=bg)
    d.rectangle([x0 + w * 0.16, y0 + h * 0.46, x0 + w * 0.84, y0 + h * 0.64], fill=fg)
    d.rectangle([x0 + w * 0.34, y0 + h * 0.30, x0 + w * 0.56, y0 + h * 0.46], fill=fg)
    d.line([(x0 + w * 0.56, y0 + h * 0.36), (x0 + w * 0.88, y0 + h * 0.36)], fill=fg, width=3)
    d.rectangle([x0 + w * 0.16, y0 + h * 0.64, x0 + w * 0.84, y0 + h * 0.76], fill=fg)
    for i in range(4):
        d.ellipse([x0 + w * (0.24 + 0.16 * i), y0 + h * 0.67,
                   x0 + w * (0.32 + 0.16 * i), y0 + h * 0.75], fill=bg)


def ic_troops(d, box, bg, fg):
    x0, y0, x1, y1, cx, cy, w, h = _box_geom(box)
    d.rectangle(box, fill=bg)
    for i in range(3):
        px = x0 + w * (0.26 + 0.24 * i)
        d.pieslice([px - 9, y0 + h * 0.22, px + 9, y0 + h * 0.52], 180, 360, fill=fg)
        d.rectangle([px - 9, y0 + h * 0.52, px + 9, y0 + h * 0.82], fill=fg)


ICONS = {
    "bridge": ic_bridge, "drone": ic_drone, "summit": ic_summit, "virus": ic_virus,
    "climate": ic_climate, "gavel": ic_gavel, "plane": ic_plane, "chart": ic_chart,
    "march": ic_march, "resign": ic_resign, "parliament": ic_parliament,
    "sanctions": ic_sanctions, "conflict": ic_conflict, "factory": ic_factory,
    "train": ic_train, "cyclone": ic_cyclone, "globe": ic_globe, "ship": ic_ship,
    "fire": ic_fire, "ballot": ic_ballot, "quake": ic_quake, "trophy": ic_trophy,
    "capitol": ic_capitol, "chip": ic_chip, "court": ic_court, "drought": ic_drought,
    "eu": ic_eu, "football": ic_football, "game": ic_game, "missile": ic_missile,
    "protest": ic_protest, "tank": ic_tank, "troops": ic_troops,
}

ICON_BG = {
    "bridge": (188, 216, 232), "drone": (217, 230, 208), "summit": (232, 220, 192),
    "virus": (242, 215, 215), "climate": (210, 232, 216), "gavel": (227, 211, 184),
    "plane": (213, 220, 232), "chart": (232, 224, 204), "march": (227, 216, 232),
    "resign": (232, 224, 208), "parliament": (216, 220, 232), "sanctions": (240, 220, 210),
    "conflict": (238, 217, 194), "factory": (220, 220, 220), "train": (213, 224, 234),
    "cyclone": (207, 228, 232), "globe": (213, 232, 224), "ship": (207, 223, 234),
    "fire": (240, 213, 194), "ballot": (220, 232, 213), "quake": (232, 220, 200),
    "trophy": (240, 226, 184),
    "capitol": (216, 220, 232), "chip": (220, 224, 228), "court": (221, 216, 238),
    "drought": (240, 228, 196), "eu": (213, 220, 232), "football": (228, 232, 220),
    "game": (222, 216, 232), "missile": (228, 222, 210), "protest": (232, 220, 214),
    "tank": (214, 222, 206), "troops": (220, 226, 214),
}
ICON_FG = (51, 70, 86)


def draw_icon(d, name, box):
    fn = ICONS.get(name, ic_globe)
    fn(d, box, ICON_BG.get(name, (220, 228, 222)), ICON_FG)


# ---------------------------------------------------------------- world map
# Rough continent outlines (lon, lat). Flat style; recognisable at small size.
CONTINENTS = [
    # North America
    [(-168, 66), (-150, 70), (-135, 69), (-125, 71), (-110, 68), (-95, 69), (-85, 66),
     (-80, 62), (-70, 58), (-60, 52), (-55, 47), (-60, 44), (-68, 44), (-75, 38),
     (-76, 34), (-81, 31), (-84, 30), (-90, 21), (-97, 26), (-97, 16), (-92, 14),
     (-86, 12), (-83, 9), (-90, 14), (-97, 16), (-105, 20), (-110, 24), (-114, 29),
     (-120, 34), (-124, 42), (-124, 48), (-130, 55), (-145, 60), (-158, 58),
     (-165, 60), (-168, 66)],
    # South America
    [(-79, 9), (-72, 12), (-64, 10), (-58, 6), (-52, 4), (-50, 0), (-44, -3),
     (-38, -5), (-35, -8), (-38, -15), (-40, -21), (-48, -26), (-53, -33),
     (-58, -38), (-65, -41), (-68, -50), (-70, -54), (-73, -46), (-73, -36),
     (-71, -28), (-70, -19), (-76, -14), (-80, -6), (-81, 0), (-80, 6), (-79, 9)],
    # Greenland
    [(-44, 60), (-40, 64), (-32, 68), (-25, 70), (-20, 74), (-28, 76), (-38, 77),
     (-52, 76), (-56, 73), (-53, 68), (-48, 64), (-44, 60)],
    # Europe
    [(-10, 36), (-9, 38), (-2, 37), (0, 39), (3, 42), (8, 39), (12, 42), (16, 40),
     (19, 42), (23, 40), (26, 40), (28, 41), (30, 46), (28, 48), (24, 50),
     (21, 54), (18, 56), (12, 57), (10, 59), (5, 60), (5, 62), (-2, 58),
     (-5, 56), (-8, 54), (-10, 52), (-10, 48), (-6, 43), (-9, 38), (-10, 36)],
    # Africa
    [(-17, 15), (-16, 20), (-15, 27), (-10, 31), (-5, 35), (0, 36), (10, 37),
     (11, 34), (20, 32), (25, 32), (30, 31), (32, 31), (34, 28), (37, 22),
     (39, 18), (43, 12), (48, 11), (51, 11), (48, 5), (44, 0), (41, -4),
     (40, -10), (36, -18), (35, -22), (33, -26), (29, -30), (26, -34),
     (20, -35), (17, -32), (15, -27), (13, -18), (13, -12), (12, -6), (9, 4),
     (4, 6), (-8, 4), (-13, 8), (-17, 12), (-17, 15)],
    # Asia
    [ (30, 46), (33, 44), (36, 42), (40, 40), (44, 39), (48, 38), (50, 37),
     (54, 36), (57, 33), (57, 28), (60, 25), (62, 25), (66, 25), (68, 23),
     (72, 20), (76, 12), (77, 8), (80, 10), (80, 15), (84, 19), (88, 22),
     (89, 22), (92, 20), (93, 16), (96, 15), (98, 10), (100, 7), (103, 2),
     (104, 8), (107, 11), (109, 14), (106, 20), (110, 20), (114, 22), (118, 25),
     (120, 28), (122, 31), (122, 35), (127, 35), (129, 38), (132, 43), (135, 44),
     (138, 46), (141, 50), (142, 52), (141, 56), (138, 59), (135, 61), (130, 64),
     (125, 68), (120, 72), (115, 73), (110, 74), (105, 76), (100, 77), (95, 76),
     (90, 75), (85, 74), (80, 73), (75, 72), (70, 71), (68, 69), (64, 68),
     (60, 69), (55, 68), (51, 68), (48, 67), (45, 66), (42, 64), (40, 62),
     (38, 58), (36, 55), (33, 52), (31, 48), (30, 46)],
    # Australia
    [(113, -22), (114, -28), (115, -32), (116, -35), (120, -34), (124, -33),
     (129, -32), (132, -32), (135, -35), (138, -35), (140, -38), (144, -38),
     (147, -39), (150, -37), (153, -32), (153, -27), (151, -24), (149, -20),
     (146, -19), (143, -15), (142, -11), (141, -13), (138, -15), (136, -12),
     (135, -15), (132, -12), (130, -13), (128, -14), (126, -14), (124, -16),
     (122, -17), (120, -20), (117, -21), (114, -22), (113, -22)],
    # UK
    [(-5, 50), (-3, 53), (-5, 56), (-3, 58), (-1, 57), (0, 53), (1, 51), (-2, 50), (-5, 50)],
    # Japan
    [(130, 31), (132, 33), (134, 34), (136, 35), (138, 35), (140, 36), (140, 39),
     (141, 41), (142, 43), (144, 44), (143, 42), (141, 40), (140, 37), (138, 35),
     (136, 34), (133, 34), (131, 32), (130, 31)],
    # New Zealand
    [(167, -45), (169, -43), (172, -41), (174, -39), (176, -38), (178, -38),
     (176, -40), (174, -42), (171, -43), (168, -46), (167, -45)],
]

REGION_COLORS = {
    "Europe": (43, 94, 167),
    "Middle East": (179, 84, 30),
    "Asia": (122, 74, 158),
    "Americas": (192, 57, 43),
    "Africa": (30, 125, 70),
    "Oceania": (14, 124, 134),
    "Global": (85, 85, 85),
}

REGION_HOME = {  # fallback pin position (lat, lon) per region
    "Europe": (52, 12), "Middle East": (30, 44), "Asia": (28, 95),
    "Americas": (12, -62), "Africa": (4, 22), "Oceania": (-25, 140),
    "Global": (15, 0),
}


def pin_xy(item, k=0):
    """Deterministic pin lat/lon for a featured story.

    k = index of this story among stories of the same region (0-based):
    same-region pins spread on a small grid so they never pile up.
    """
    if "lat" in item and "lon" in item:
        return item["lat"], item["lon"]
    lat, lon = REGION_HOME.get(item.get("region", "Global"), (15, 0))
    lon += ((k % 3) - 1) * 20
    lat += ((k // 3) - 1) * 13
    lat = max(-55, min(75, lat))
    lon = max(-179, min(179, lon))
    return lat, lon


def draw_map(d, box, featured):
    x0, y0, x1, y1 = box
    d.rectangle(box, fill=MAP_OCEAN)
    mw, mh = x1 - x0, y1 - y0

    def proj(lon, lat):
        return (x0 + (lon + 180.0) / 360.0 * mw,
                y0 + (90.0 - lat) / 180.0 * mh)

    for poly in CONTINENTS:
        pts = [proj(lon, lat) for lon, lat in poly]
        d.polygon(pts, fill=MAP_LAND, outline=MAP_LINE)
    d.rectangle(box, outline=RULE, width=1)
    f_pin = font(SANS_B, 10)
    region_seen = {}
    for item in featured:
        reg = item.get("region", "Global")
        k = region_seen.get(reg, 0)
        region_seen[reg] = k + 1
        lat, lon = pin_xy(item, k)
        px, py = proj(lon, lat)
        col = REGION_COLORS.get(item.get("region", "Global"), (85, 85, 85))
        r = 8
        d.ellipse([px - r, py - r, px + r, py + r], fill=col, outline=(255, 255, 255), width=1)
        num = str(item.get("n", "?"))
        tw = f_pin.getlength(num)
        d.text((px - tw / 2, py - 5), num, font=f_pin, fill=(255, 255, 255))
# ---------------------------------------------------------------- layout
MARGIN = 14
CONTENT_W = W - 2 * MARGIN  # 996


def draw_header(d, data):
    y = 8
    f_eye = font(SANS_B, 13)
    left = "ONE DAY OF WORLD NEWS, ONE PICTURE"
    n_total = len(data["featured"]) + len(data.get("also", []))
    right = (f"{n_total} STORIES \u00b7 {data.get('regions_count', 7)} REGIONS \u00b7 "
             f"EVERY ONE FROM THIS {data['weekday'].upper()}")
    d.text((MARGIN, y), left, font=f_eye, fill=INK)
    rw = f_eye.getlength(right)
    d.text((W - MARGIN - rw, y), right, font=f_eye, fill=INK)
    f_date = font(SERIF_B, 42)
    d.text((MARGIN, y + 20), full_date(data), font=f_date, fill=INK)
    hline(d, MARGIN, W - MARGIN, 82, fill=INK, w=2)
    return 88


def draw_timeline(d, data, y0):
    box_w, box_h = 92, 28
    d.rectangle([MARGIN, y0, MARGIN + box_w, y0 + box_h], fill=RED)
    f_lab = font(SANS_B, 11)
    d.text((MARGIN + 8, y0 + 2), "THE DAY", font=f_lab, fill=(255, 255, 255))
    d.text((MARGIN + 8, y0 + 14), "IN UTC", font=f_lab, fill=(255, 255, 255))
    x0 = MARGIN + box_w + 10
    col_w = (W - MARGIN - x0) / 6.0
    f_time = font(SANS_B, 12)
    for i, item in enumerate(data["timeline"][:6]):
        cx = x0 + col_w * i
        d.text((cx, y0), item["utc"], font=f_time, fill=RED)
        ff, lines = fit(font(SANS, 11), item["label"], col_w - 8, 2, 11, 9, SANS)
        if len(lines) > 2:
            lines = lines[:2]
            lines[1] = ellipsize(ff, lines[1], col_w - 8)
        draw_lines(d, cx, y0 + 14, lines, ff, INK, ff.size + 2)
    hline(d, MARGIN, W - MARGIN, y0 + 36, fill=RULE, w=1)
    return y0 + 40


def draw_featured(d, data, y0, warnings):
    cols, rows = 4, 4
    gap_x, gap_y = 8, 6
    cell_w = (CONTENT_W - gap_x * (cols - 1)) // cols  # 243
    cell_h = 136
    featured = data["featured"][:16]
    for idx, item in enumerate(featured):
        r, c = divmod(idx, cols)
        x = MARGIN + c * (cell_w + gap_x)
        y = y0 + r * (cell_h + gap_y)
        # illustration panel (32px)
        draw_icon(d, item.get("icon", "globe"), (x, y, x + cell_w, y + 32))
        # tag line: number badge + REGION . TOPIC ... status right
        ty = y + 35
        d.rectangle([x, ty, x + 15, ty + 13], fill=RED)
        f_num = font(SANS_B, 10)
        num = str(item.get("n", idx + 1))
        d.text((x + 8 - f_num.getlength(num) / 2, ty + 1), num, font=f_num,
               fill=(255, 255, 255))
        tag = f"{item['region'].upper()} \u00b7 {item['topic'].upper()}"
        f_tag = font(SANS_B, 10)
        tw = f_tag.getlength(tag)
        status = item.get("status", "CONFIRMED")
        f_stat = font(SANS_B, 9)
        sw = f_stat.getlength(status)
        while tw > cell_w - 18 - sw - 8 and f_tag.size > 8:
            f_tag = font(SANS_B, f_tag.size - 1)
            tw = f_tag.getlength(tag)
        d.text((x + 18, ty + 1), tag, font=f_tag, fill=INK)
        scol = RED if status.startswith("CLAIM") else (30, 110, 60)
        d.text((x + cell_w - sw, ty + 1), status, font=f_stat, fill=scol)
        # headline: max 2 lines, 15 -> 12, truncate with ellipsis
        hf, hlines = fit(font(SANS_B, 15), item["headline"], cell_w, 2, 15, 12, SANS_B)
        if len(hlines) > 2:
            hlines = hlines[:2]
            hlines[1] = ellipsize(hf, hlines[1], cell_w)
            warnings.append(f"featured {item.get('n')}: headline longer than 2 lines")
        hy = draw_lines(d, x, y + 50, hlines, hf, INK, hf.size + 3)
        # summary: pick the largest font (11 -> 8) whose lines fit the space
        # left in the cell (max 4 lines, must end inside the cell)
        summary_y = hy + 2
        avail = (y + cell_h - 3) - summary_y
        sf, slines = None, None
        for size in (11, 10, 9, 8):
            ff = font(SANS, size)
            lines = wrap(ff, item["summary"], cell_w)
            if len(lines) <= 4 and len(lines) * (size + 2) <= avail:
                sf, slines = ff, lines
                break
        if sf is None:
            sf = font(SANS, 8)
            slines = wrap(sf, item["summary"], cell_w)
            if len(slines) > 4:
                slines = slines[:4]
                slines[3] = ellipsize(sf, slines[3], cell_w)
            warnings.append(f"featured {item.get('n')}: summary too long even at 8px "
                            f"({len(item['summary'])} chars)")
        draw_lines(d, x, summary_y, slines, sf, (60, 58, 50), sf.size + 2)
    return y0 + rows * cell_h + (rows - 1) * gap_y


def measure_date_check(data):
    """Measure DATE CHECK text: returns (font, lines, bar_height). Max 5 lines."""
    excl = "; ".join(f"{e['item']} ({e['date']})"
                     for e in data.get("date_check_excluded", []))
    notyet = "; ".join(f"{e['item']} ({e['date']})"
                       for e in data.get("date_check_not_yet", []))
    parts = []
    if excl:
        parts.append(f"Left out on purpose because they broke before "
                     f"{data['weekday']}: {excl}.")
    if notyet:
        parts.append(f"Not yet: {notyet}.")
    text = " ".join(parts)
    max_w = W - MARGIN - (MARGIN + 100)
    ff, lines = fit(font(SANS, 11), text, max_w, 5, 11, 9, SANS)
    return ff, lines, text, max_w


def draw_date_check(d, data, y0, warnings, pre=None):
    if pre is None:
        ff, lines, text, max_w = measure_date_check(data)
    else:
        ff, lines, text, max_w = pre
    if len(lines) > 5:
        lines = lines[:5]
        lines[4] = ellipsize(ff, lines[4], max_w)
        warnings.append("date_check: too long for 5 lines - keep <=6 short items")
    bar_h = max(28, len(lines) * (ff.size + 3) + 8)
    d.rectangle([MARGIN, y0, MARGIN + 92, y0 + bar_h], fill=RED)
    f_lab = font(SANS_B, 11)
    d.text((MARGIN + 8, y0 + 9), "DATE CHECK", font=f_lab, fill=(255, 255, 255))
    draw_lines(d, MARGIN + 100, y0 + 3, lines, ff, INK, ff.size + 3)
    return y0 + bar_h


def draw_map_section(d, data, y0, warnings, section_h):
    # left: map (300px wide); right: ALSO ON list
    map_w = 300
    also_x = MARGIN + map_w + 10
    also_w = W - MARGIN - also_x
    f_sec = font(SANS_B, 13)
    d.text((MARGIN, y0), "WHERE IT HAPPENED", font=f_sec, fill=INK)
    d.text((also_x, y0), f"ALSO ON {data['weekday'].upper()} {short_date(data).upper()}",
           font=f_sec, fill=INK)
    map_h = section_h - 50  # title 18 + legend 26 + padding
    map_box = (MARGIN, y0 + 18, MARGIN + map_w, y0 + 18 + map_h)
    draw_map(d, map_box, data["featured"][:16])
    # legend: regions present, two rows
    regs = []
    for it in data["featured"]:
        if it.get("region") not in regs:
            regs.append(it.get("region"))
    f_leg = font(SANS_B, 9)
    lx, ly = MARGIN, y0 + 18 + map_h + 6
    per_row = 3
    for i, reg in enumerate(regs):
        col = REGION_COLORS.get(reg, (85, 85, 85))
        px = lx + (i % per_row) * 104
        py = ly + (i // per_row) * 13
        d.ellipse([px, py + 1, px + 8, py + 9], fill=col)
        d.text((px + 11, py), reg, font=f_leg, fill=INK)
    # ALSO ON list: two columns, numbered from len(featured)+1.
    # Font adapts to the rows available (11 -> 8); each item must fit one line.
    also = data.get("also", [])
    n_feat = len(data["featured"])
    col_w = (also_w - 14) // 2
    rows = (len(also) + 1) // 2
    area_h = section_h - 18
    row_h = area_h / max(rows, 1)
    if row_h >= 13:
        base_size = 11
    elif row_h >= 12:
        base_size = 10
    elif row_h >= 11:
        base_size = 9
    else:
        base_size = 8
    f_item = font(SANS, base_size)
    f_num = font(SANS_B, base_size)
    for i, text in enumerate(also):
        col = i // rows
        row = i % rows
        x = also_x + col * (col_w + 14)
        yy = y0 + 18 + row * row_h
        num = str(n_feat + 1 + i)
        nw = f_num.getlength(num + " ")
        d.text((x, yy), num, font=f_num, fill=RED)
        ff = f_item
        while ff.getlength(text) > col_w - nw and ff.size > 8:
            ff = font(SANS, ff.size - 1)
        if ff.getlength(text) > col_w - nw:
            warnings.append(f"also #{n_feat + 1 + i}: one-liner too long even at 8px "
                            f"({len(text)} chars) - shorten to ~60 chars")
            text = ellipsize(ff, text, col_w - nw)
        d.text((x + nw, yy), text, font=ff, fill=INK)
    return y0 + section_h


def draw_footer(d, data, y0):
    f_f = font(SANS, 11)
    hline(d, MARGIN, W - MARGIN, y0, fill=RULE, w=1)
    stmt = (f"Every story here happened or was first reported on {full_date(data)}. "
            "CLAIM = one side's account, not independently confirmed.")
    ff, lines = fit(f_f, stmt, CONTENT_W, 1, 11, 10, SANS)
    draw_lines(d, MARGIN, y0 + 4, lines, ff, INK, ff.size + 3)
    srcs = "Sources: " + ", ".join(data.get("sources", [])) + ". Original drawings."
    d.text((MARGIN, y0 + 18), srcs, font=font(SANS_B, 11), fill=INK)
    return y0 + 29


def render(data):
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    warnings = []
    y = draw_header(d, data)
    y = draw_timeline(d, data, y + 4)
    y = draw_featured(d, data, y + 6, warnings)
    # two-pass: measure DATE CHECK first, then size the map section so the
    # page is exactly filled (1024px, 2px bottom margin), never overflowing
    ff, lines, text, max_w = measure_date_check(data)
    dc_bar = max(28, len(lines) * (ff.size + 3) + 8)
    if len(lines) > 5:
        dc_bar = max(28, 5 * (ff.size + 3) + 8)
    map_y0 = y + 8
    map_h = 1024 - 2 - 29 - 4 - (dc_bar + 4) - map_y0
    if map_h < 150:  # safety valve, should not happen with <=5 date-check lines
        map_h = 150
    y = draw_map_section(d, data, map_y0, warnings, map_h)
    y = draw_date_check(d, data, y + 4, warnings,
                        pre=(ff, lines, text, max_w))
    draw_footer(d, data, y + 4)
    return img, warnings


def main(argv):
    if len(argv) < 2:
        print("usage: renderer.py stories.json [entry.png]", file=sys.stderr)
        return 2
    inp = Path(argv[1])
    out = Path(argv[2]) if len(argv) > 2 else Path("entry.png")
    data = json.loads(inp.read_text(encoding="utf-8"))
    n_feat = len(data["featured"])
    n_also = len(data.get("also", []))
    if n_feat != 16:
        print(f"WARNING: featured has {n_feat} items (champion formula uses 16)",
              file=sys.stderr)
    if n_feat + n_also < 23:
        print(f"WARNING: only {n_feat + n_also} stories total; "
              "winner formula needs >=23 (target 40-50)", file=sys.stderr)
    img, warnings = render(data)
    img.save(out, format="PNG")
    for w in warnings:
        print(f"FIT WARNING: {w}", file=sys.stderr)
    print(f"wrote {out} ({n_feat} featured + {n_also} also = "
          f"{n_feat + n_also} stories)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

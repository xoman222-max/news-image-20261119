#!/usr/bin/env python3
"""One image that sums up the world news of Thursday 19 November 2026.

A newspaper front page drawn from scratch with the Python standard
library only: a hand-built 5x7 pixel font (each glyph is seven rows of
five bits, stored as integers), a small raster canvas with its own
shapes, and a hand-rolled PNG encoder. No network, no files read, no
clock, no randomness: every run writes byte-identical output.

Run:  MAKEFUN_OUTPUT_DIR=out python3 main.py   -> out/entry.png
"""

import math
import os
import struct
import zlib

W, H = 1024, 1024

# ---- palette ---------------------------------------------------------
PAPER = (246, 240, 224)    # newsprint cream
PANEL = (255, 253, 247)    # story card white
INK = (26, 26, 24)
NAVY = (18, 32, 58)
NAVY_LT = (38, 58, 96)
RED = (176, 32, 40)
GOLD = (198, 158, 38)
GOLD_LT = (233, 198, 92)
TEAL = (28, 108, 104)
BLUE = (44, 88, 134)
SKY = (172, 210, 232)
SEA = (58, 116, 164)
WHITE = (255, 255, 255)
EDGE = (186, 174, 146)     # card border
GREY = (94, 90, 80)
BODY = (56, 52, 44)        # deck text
GREEN = (44, 122, 68)
CRIMSON = (178, 44, 54)
BROWN = (122, 74, 30)
ORANGE = (224, 122, 34)
YELLOW = (240, 196, 60)
PALE = (232, 224, 204)     # light rule / panel tint


# ---- 5x7 pixel font --------------------------------------------------
# Each glyph is a tuple of seven integers. Each integer is one row of
# five pixels, most significant bit on the left (16 = leftmost pixel).
FONT = {
    "A": (0x0E, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11),
    "B": (0x1E, 0x11, 0x11, 0x1E, 0x11, 0x11, 0x1E),
    "C": (0x0E, 0x11, 0x10, 0x10, 0x10, 0x11, 0x0E),
    "D": (0x1E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x1E),
    "E": (0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x1F),
    "F": (0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x10),
    "G": (0x0E, 0x11, 0x10, 0x17, 0x11, 0x11, 0x0F),
    "H": (0x11, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11),
    "I": (0x0E, 0x04, 0x04, 0x04, 0x04, 0x04, 0x0E),
    "J": (0x07, 0x02, 0x02, 0x02, 0x02, 0x12, 0x0C),
    "K": (0x11, 0x12, 0x14, 0x18, 0x14, 0x12, 0x11),
    "L": (0x10, 0x10, 0x10, 0x10, 0x10, 0x10, 0x1F),
    "M": (0x11, 0x1B, 0x15, 0x15, 0x11, 0x11, 0x11),
    "N": (0x11, 0x19, 0x19, 0x15, 0x13, 0x13, 0x11),
    "O": (0x0E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E),
    "P": (0x1E, 0x11, 0x11, 0x1E, 0x10, 0x10, 0x10),
    "Q": (0x0E, 0x11, 0x11, 0x11, 0x15, 0x12, 0x0D),
    "R": (0x1E, 0x11, 0x11, 0x1E, 0x14, 0x12, 0x11),
    "S": (0x0F, 0x10, 0x10, 0x0E, 0x01, 0x01, 0x1E),
    "T": (0x1F, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04),
    "U": (0x11, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E),
    "V": (0x11, 0x11, 0x11, 0x11, 0x11, 0x0A, 0x04),
    "W": (0x11, 0x11, 0x11, 0x15, 0x15, 0x1B, 0x11),
    "X": (0x11, 0x11, 0x0A, 0x04, 0x0A, 0x11, 0x11),
    "Y": (0x11, 0x11, 0x0A, 0x04, 0x04, 0x04, 0x04),
    "Z": (0x1F, 0x01, 0x02, 0x04, 0x08, 0x10, 0x1F),
    "0": (0x0E, 0x11, 0x13, 0x15, 0x19, 0x11, 0x0E),
    "1": (0x04, 0x0C, 0x04, 0x04, 0x04, 0x04, 0x0E),
    "2": (0x0E, 0x11, 0x01, 0x02, 0x04, 0x08, 0x1F),
    "3": (0x1E, 0x01, 0x01, 0x0E, 0x01, 0x01, 0x1E),
    "4": (0x02, 0x06, 0x0A, 0x12, 0x1F, 0x02, 0x02),
    "5": (0x1F, 0x10, 0x1E, 0x01, 0x01, 0x11, 0x0E),
    "6": (0x0E, 0x10, 0x10, 0x1E, 0x11, 0x11, 0x0E),
    "7": (0x1F, 0x01, 0x02, 0x02, 0x04, 0x04, 0x04),
    "8": (0x0E, 0x11, 0x11, 0x0E, 0x11, 0x11, 0x0E),
    "9": (0x0E, 0x11, 0x11, 0x0F, 0x01, 0x01, 0x0E),
    " ": (0, 0, 0, 0, 0, 0, 0),
    ".": (0, 0, 0, 0, 0, 0x06, 0x06),
    ",": (0, 0, 0, 0, 0x06, 0x04, 0x08),
    ":": (0, 0x06, 0x06, 0, 0x06, 0x06, 0),
    ";": (0, 0x06, 0x06, 0, 0x06, 0x04, 0x08),
    "-": (0, 0, 0, 0x0E, 0, 0, 0),
    "'": (0x04, 0x04, 0x08, 0, 0, 0, 0),
    "/": (0x01, 0x01, 0x02, 0x04, 0x08, 0x10, 0x10),
    "(": (0x02, 0x04, 0x08, 0x08, 0x08, 0x04, 0x02),
    ")": (0x08, 0x04, 0x02, 0x02, 0x02, 0x04, 0x08),
    "&": (0x0C, 0x12, 0x14, 0x08, 0x15, 0x12, 0x0D),
    "!": (0x04, 0x04, 0x04, 0x04, 0x04, 0, 0x04),
    "?": (0x0E, 0x11, 0x01, 0x02, 0x04, 0, 0x04),
    "%": (0x19, 0x19, 0x02, 0x04, 0x08, 0x13, 0x13),
    "+": (0, 0x04, 0x04, 0x1F, 0x04, 0x04, 0),
    "=": (0, 0, 0x1F, 0, 0x1F, 0, 0),
    '"': (0x0A, 0x0A, 0, 0, 0, 0, 0),
    "|": (0x04, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04),
    "\u00b7": (0, 0, 0x06, 0x06, 0, 0, 0),
    "$": (0x04, 0x0F, 0x14, 0x0E, 0x05, 0x1E, 0x04),
}


def glyph_width(text, scale):
    """Advance width in pixels of text at the given glyph scale."""
    return len(text) * 6 * scale


def wrap(text, scale, max_w):
    """Greedy word wrap into lines that fit max_w pixels."""
    lines, cur = [], ""
    for word in text.split(" "):
        trial = word if not cur else cur + " " + word
        if glyph_width(trial, scale) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


# ---- raster canvas ---------------------------------------------------
class Board:
    """A flat RGB buffer with filled shapes and bitmap text."""

    def __init__(self, w, h, bg):
        self.w, self.h = w, h
        self.px = bytearray(w * h * 3)
        self.paint(0, 0, w, h, bg)

    def _set(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i], self.px[i + 1], self.px[i + 2] = c

    def paint(self, x, y, w, h, c):
        """Fill a rectangle, clipped to the board."""
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(self.w, x + w), min(self.h, y + h)
        for yy in range(y0, y1):
            base = (yy * self.w + x0) * 3
            for xx in range(x0, x1):
                i = base + (xx - x0) * 3
                self.px[i], self.px[i + 1], self.px[i + 2] = c

    def outline(self, x, y, w, h, c, t=2):
        self.paint(x, y, w, t, c)
        self.paint(x, y + h - t, w, t, c)
        self.paint(x, y, t, h, c)
        self.paint(x + w - t, y, t, h, c)

    def hbar(self, x0, x1, y, c, t=1):
        self.paint(min(x0, x1), y, abs(x1 - x0) + 1, t, c)

    def vbar(self, x, y0, y1, c, t=1):
        self.paint(x, min(y0, y1), t, abs(y1 - y0) + 1, c)

    def seg(self, x0, y0, x1, y1, c, t=1):
        """Bresenham line segment, t pixels thick."""
        dx, dy = abs(x1 - x0), abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        x, y = x0, y0
        while True:
            self.paint(x - t // 2, y - t // 2, t, t, c)
            if x == x1 and y == y1:
                return
            e = 2 * err
            if e > -dy:
                err -= dy
                x += sx
            if e < dx:
                err += dx
                y += sy

    def disc(self, cx, cy, r, c):
        """Filled circle, scanline by scanline."""
        for yy in range(cy - r, cy + r + 1):
            dy = yy - cy
            if abs(dy) > r:
                continue
            half = int((r * r - dy * dy) ** 0.5)
            self.hbar(cx - half, cx + half, yy, c)

    def ring(self, cx, cy, r, c, t=2):
        """Circle outline, drawn as a parametric loop."""
        for k in range(t):
            rr = r - k
            for deg in range(360):
                a = deg * math.pi / 180.0
                self._set(int(cx + rr * math.cos(a)),
                          int(cy + rr * math.sin(a)), c)

    def tri(self, pts, c):
        """Filled triangle via horizontal scanlines."""
        (x0, y0), (x1, y1), (x2, y2) = pts
        lo, hi = min(y0, y1, y2), max(y0, y1, y2)
        for y in range(max(0, lo), min(self.h, hi + 1)):
            xs = []
            for (ax, ay), (bx, by) in (((x0, y0), (x1, y1)),
                                       ((x1, y1), (x2, y2)),
                                       ((x2, y2), (x0, y0))):
                if (ay <= y < by) or (by <= y < ay):
                    xs.append(ax + (y - ay) * (bx - ax) / (by - ay))
            if len(xs) >= 2:
                xs.sort()
                self.hbar(int(xs[0]), int(xs[-1]), y, c)

    def burst(self, cx, cy, r_out, r_in, c, points=8, rot=-90):
        """Starburst polygon (alternating outer/inner radius)."""
        pts = []
        for i in range(points * 2):
            r = r_out if i % 2 == 0 else r_in
            a = (rot + i * 180.0 / points) * math.pi / 180.0
            pts.append((int(cx + r * math.cos(a)),
                        int(cy + r * math.sin(a))))
        # fan-fill from the centre
        for i in range(len(pts)):
            self.tri([(cx, cy), pts[i], pts[(i + 1) % len(pts)]], c)

    # ---- text ----
    def put_text(self, x, y, text, scale, c):
        """Draw upper-case text; returns the pixel width drawn."""
        cx = x
        for ch in text.upper():
            rows = FONT.get(ch, FONT[" "])
            for r, bits in enumerate(rows):
                for col in range(5):
                    if bits & (16 >> col):
                        self.paint(cx + col * scale, y + r * scale,
                                   scale, scale, c)
            cx += 6 * scale
        return cx - x

    def centred(self, y, text, scale, c, mid=None):
        w = glyph_width(text, scale)
        x = (self.w - w) // 2 if mid is None else mid - w // 2
        self.put_text(x, y, text, scale, c)
        return x


# ---- pictograms, one per story ---------------------------------------
def pic_summit(b, x, y, s):
    """Globe with three small flags: the Shenzhen trilateral."""
    b.paint(x, y, s, s, SKY)
    cx, cy, r = x + s // 2, y + int(s * 0.40), int(s * 0.30)
    b.disc(cx, cy, r, BLUE)
    # meridians and parallels
    for k in (-2, -1, 0, 1, 2):
        b.vbar(cx + k * r // 3, cy - r + 6, cy + r - 6, SKY, 2)
    for k in (-1, 0, 1):
        b.hbar(cx - r + 6, cx + r - 6, cy + k * r // 2, SKY, 2)
    b.ring(cx, cy, r, NAVY, 3)
    # gold star marking the summit city
    b.burst(cx + r // 2, cy - r // 3, 12, 5, GOLD_LT)
    # three flags along the bottom
    fw, fh = int(s * 0.24), int(s * 0.16)
    for i, kind in enumerate(("us", "cn", "ru")):
        fx = x + int(s * 0.07) + i * int(s * 0.31)
        fy = y + int(s * 0.78)
        b.vbar(fx + 2, fy - 8, fy + fh + 12, INK, 3)
        if kind == "us":
            for stripe in range(4):
                col = RED if stripe % 2 == 0 else WHITE
                b.paint(fx + 4, fy + stripe * (fh // 4), fw, fh // 4 + 1, col)
            b.paint(fx + 4, fy, fw // 2, fh // 2, NAVY)
        elif kind == "cn":
            b.paint(fx + 4, fy, fw, fh, (222, 41, 16))
            b.burst(fx + 12, fy + 8, 6, 2, GOLD_LT, points=5)
        else:
            b.paint(fx + 4, fy, fw, fh // 3 + 1, WHITE)
            b.paint(fx + 4, fy + fh // 3, fw, fh // 3 + 1, BLUE)
            b.paint(fx + 4, fy + 2 * fh // 3, fw, fh // 3 + 1, RED)


def pic_gamepad(b, x, y, s):
    """A game controller: the GTA VI launch."""
    b.paint(x, y, s, s, (38, 38, 46))
    cx, cy = x + s // 2, y + s // 2
    bw, bh = int(s * 0.78), int(s * 0.46)
    bx, by = cx - bw // 2, cy - bh // 2
    b.paint(bx, by, bw, bh, (236, 236, 240))
    b.paint(bx, by + bh - 8, 22, 22, (236, 236, 240))
    b.paint(bx + bw - 22, by + bh - 8, 22, 22, (236, 236, 240))
    # d-pad
    dx, dy = bx + 26, by + bh // 2
    b.paint(dx - 5, dy - 16, 10, 32, INK)
    b.paint(dx - 16, dy - 5, 32, 10, INK)
    # four buttons
    for ox, oy, col in ((30, -12, GREEN), (44, 2, RED),
                        (16, 2, BLUE), (30, 16, GOLD)):
        b.disc(bx + bw - 34 + ox - 12, by + bh // 2 + oy, 6, col)
    # sticks
    b.disc(cx - 6, by + bh - 12, 8, INK)
    b.disc(cx + 16, by + bh - 12, 8, INK)
    # "VI" tag
    b.put_text(x + int(s * 0.36), y + int(s * 0.06), "VI", 3, GOLD_LT)


def pic_scales(b, x, y, s):
    """Scales of justice: the Hague ruling."""
    b.paint(x, y, s, s, (238, 232, 214))
    cx = x + s // 2
    top = y + int(s * 0.12)
    b.vbar(cx, top, y + int(s * 0.80), INK, 4)
    b.hbar(cx - int(s * 0.30), cx + int(s * 0.30), top + 6, INK, 4)
    b.disc(cx, top + 2, 6, GOLD)
    for side in (-1, 1):
        px = cx + side * int(s * 0.30)
        b.seg(px, top + 8, px - 16, y + int(s * 0.52), INK, 2)
        b.seg(px, top + 8, px + 16, y + int(s * 0.52), INK, 2)
        b.hbar(px - 18, px + 18, y + int(s * 0.52), GOLD, 4)
        b.tri([(px - 18, y + int(s * 0.52)), (px + 18, y + int(s * 0.52)),
               (px, y + int(s * 0.68))], GOLD)
    b.paint(cx - 14, y + int(s * 0.80), 28, 6, INK)


def pic_tanker(b, x, y, s):
    """Oil tanker on fire near the Strait of Hormuz."""
    b.paint(x, y, s, s, SKY)
    b.paint(x, y + int(s * 0.68), s, s - int(s * 0.68), SEA)
    for k in range(3):
        wy = y + int(s * 0.74) + k * int(s * 0.08)
        b.hbar(x + int(s * 0.10), x + int(s * 0.90), wy, WHITE, 2)
    # hull: a long dark block with a sloped bow
    hx, hy = x + int(s * 0.10), y + int(s * 0.52)
    b.paint(hx, hy, int(s * 0.80), int(s * 0.14), INK)
    b.tri([(hx + int(s * 0.80), hy),
           (hx + int(s * 0.80), hy + int(s * 0.14)),
           (hx + int(s * 0.68), hy + int(s * 0.14))], INK)
    # containers
    for i, col in enumerate((RED, GOLD, TEAL)):
        b.paint(hx + 8 + i * 22, hy - 16, 18, 16, col)
    # funnel with flame
    b.paint(hx + int(s * 0.62), hy - 30, 14, 30, WHITE)
    b.burst(hx + int(s * 0.62) + 7, hy - 42, 16, 6, ORANGE)
    b.burst(hx + int(s * 0.62) + 7, hy - 42, 9, 3, YELLOW)
    # smoke
    b.disc(hx + int(s * 0.30), hy - 44, 7, GREY)
    b.disc(hx + int(s * 0.38), hy - 54, 9, GREY)


def pic_pact(b, x, y, s):
    """A signed document with a seal: the Venezuela deal."""
    b.paint(x, y, s, s, (232, 228, 216))
    dx, dy = x + int(s * 0.22), y + int(s * 0.14)
    dw, dh = int(s * 0.56), int(s * 0.68)
    b.paint(dx, dy, dw, dh, WHITE)
    b.outline(dx, dy, dw, dh, INK, 2)
    # folded corner
    b.tri([(dx + dw - 16, dy), (dx + dw, dy + 16), (dx + dw, dy)], PALE)
    # text lines
    for k in range(4):
        b.paint(dx + 8, dy + 12 + k * 12, dw - 16 - (8 if k == 3 else 0),
                3, BODY)
    # two signature squiggles
    b.seg(dx + 8, dy + dh - 18, dx + 20, dy + dh - 24, INK, 2)
    b.seg(dx + 20, dy + dh - 24, dx + 32, dy + dh - 16, INK, 2)
    b.seg(dx + 34, dy + dh - 18, dx + 44, dy + dh - 24, INK, 2)
    # red seal
    b.disc(dx + dw - 14, dy + dh - 14, 11, RED)
    b.ring(dx + dw - 14, dy + dh - 14, 7, GOLD_LT, 2)
    # two small flags on top
    for i, cols in enumerate((((178, 34, 52), WHITE), ((0, 82, 147), RED))):
        fx = x + int(s * 0.16) + i * int(s * 0.42)
        b.paint(fx, y + int(s * 0.06), 26, 5, cols[0])
        b.paint(fx, y + int(s * 0.06) + 5, 26, 5, cols[1])


def pic_sunflower(b, x, y, s):
    """A sunflower in a frame: the record Van Gogh sale."""
    b.paint(x, y, s, s, (24, 44, 72))
    fx, fy = x + 8, y + 8
    b.paint(fx, fy, s - 16, s - 16, (250, 238, 208))
    b.outline(fx, fy, s - 16, s - 16, GOLD, 4)
    cx, cy = x + s // 2, y + int(s * 0.44)
    # petals: twelve thick spokes around the brown centre
    for k in range(12):
        a = k * 30 * math.pi / 180.0
        px = int(cx + 30 * math.cos(a))
        py = int(cy + 30 * math.sin(a))
        b.seg(cx, cy, px, py, YELLOW, 9)
    b.disc(cx, cy, 20, BROWN)
    for ox, oy in ((-7, -6), (6, -4), (-3, 7), (8, 6)):
        b.disc(cx + ox, cy + oy, 3, (60, 36, 12))
    # stem and leaf
    b.vbar(cx, cy + 20, y + s - 24, GREEN, 5)
    b.tri([(cx, y + int(s * 0.72)), (cx - 22, y + int(s * 0.80)),
           (cx, y + int(s * 0.86))], GREEN)
    # price tag, full width of the icon so the text fits
    b.paint(x + 4, y + s - 26, s - 8, 18, RED)
    b.put_text(x + 8, y + s - 24, "$190.4M", 2, WHITE)


# ---- page composition --------------------------------------------------
LEAD_HEAD = "TRUMP, XI AND PUTIN MEET IN SHENZHEN"
LEAD_DECK = ("The first three-way meeting of the American, Chinese and "
             "Russian leaders opens at APEC in Shenzhen. Nuclear arms, "
             "Ukraine and Iran top the agenda.")

ROWS = [
    ("CULTURE - VIDEO GAMES", "GTA VI LAUNCHES WORLDWIDE",
     "Rockstar's blockbuster rolls out around the globe to near-perfect "
     "reviews after a 13-year wait.", pic_gamepad),
    ("LAW - THE HAGUE", "WORLD COURT RULES ON ROHINGYA CASE",
     "Judges in The Hague rule today on Myanmar's alleged genocide "
     "against the Rohingya minority.", pic_scales),
    ("ENERGY - MIDDLE EAST", "TANKERS HIT MINES NEAR HORMUZ",
     "Three oil tankers catch fire east of the Strait of Hormuz after "
     "striking mines, Iran reports.", pic_tanker),
    ("AMERICAS - DIPLOMACY", "US, VENEZUELA RESTORE MILITARY TIES",
     "Defence chief Hegseth signs a deal in Caracas to rebuild training "
     "and intelligence links.", pic_pact),
    ("ARTS - AUCTION", "VAN GOGH SELLS FOR RECORD $190.4M",
     "A Van Gogh painting fetches a record price at auction after a long "
     "ownership dispute.", pic_sunflower),
]

TICKER = ("ALSO TODAY: GAZA GROUND OPERATION  \u00b7  "
          "ETHIOPIA-ERITREA CLASHES RISK WAR  \u00b7  JEFFRIES FIRST BLACK "
          "SPEAKER  \u00b7  QUAKE 5.7 IN KUMAMOTO  \u00b7  VOYAGER 1 PASSES "
          "ONE LIGHT-DAY")


def compose():
    b = Board(W, H, PAPER)

    # ---- masthead ----
    b.paint(0, 0, W, 104, NAVY)
    b.paint(0, 104, W, 6, RED)
    b.centred(18, "THE WORLD IN ONE DAY", 6, WHITE)
    b.centred(70, "THURSDAY  -  19 NOVEMBER 2026", 3, GOLD_LT)
    # small gold diamonds flanking the date
    for dx in (200, W - 200):
        b.disc(dx, 80, 5, GOLD_LT)
    b.centred(122, "SUMMITS, VERDICTS, LAUNCHES AND RECORDS - "
                   "SIX STORIES FROM ONE DAY", 2, GREY)

    # ---- lead story ----
    b.paint(24, 152, 976, 244, PANEL)
    b.outline(24, 152, 976, 244, EDGE, 2)
    b.put_text(48, 170, "DIPLOMACY  -  SHENZHEN  -  APEC", 2, RED)
    yy = 200
    for ln in wrap(LEAD_HEAD, 3, 580):
        b.put_text(48, yy, ln, 3, INK)
        yy += 26
    yy += 8
    for ln in wrap(LEAD_DECK, 2, 580):
        b.put_text(48, yy, ln, 2, BODY)
        yy += 17
    # summit globe on the right of the lead
    b.paint(656, 170, 320, 208, SKY)
    b.outline(656, 170, 320, 208, EDGE, 2)
    pic_summit(b, 728, 176, 176)
    b.put_text(688, 358, "THE FIRST TRILATERAL", 2, NAVY)

    # ---- story rows ----
    y = 408
    for kicker, head, deck, pic in ROWS:
        b.paint(24, y, 976, 102, PANEL)
        b.outline(24, y, 976, 102, EDGE, 2)
        pic(b, 32, y + 3, 96)
        b.outline(32, y + 3, 96, 96, EDGE, 2)
        b.put_text(148, y + 10, kicker, 2, RED)
        b.put_text(148, y + 32, head, 3, INK)
        dy = y + 60
        for ln in wrap(deck, 2, 832):
            b.put_text(148, dy, ln, 2, BODY)
            dy += 16
        y += 110

    # ---- footer ticker ----
    b.paint(0, 958, W, 66, NAVY)
    ty = 964
    for ln in wrap(TICKER, 2, W - 48):
        b.put_text(24, ty, ln, 2, WHITE)
        ty += 16
    return b


# ---- PNG encoding ------------------------------------------------------
def encode_png(b):
    raw = bytearray()
    stride = b.w * 3
    for yy in range(b.h):
        raw.append(0)  # filter type: none
        raw += b.px[yy * stride:(yy + 1) * stride]
    blob = zlib.compress(bytes(raw), 9)

    def chunk(kind, payload):
        out = struct.pack(">I", len(payload)) + kind + payload
        out += struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
        return out

    ihdr = struct.pack(">IIBBBBB", b.w, b.h, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", blob) + chunk(b"IEND", b""))


def main():
    board = compose()
    data = encode_png(board)
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR") or "/output"
    try:
        os.makedirs(out_dir, exist_ok=True)
        path = os.path.join(out_dir, "entry.png")
        with open(path, "wb") as f:
            f.write(data)
    except OSError:
        os.makedirs("out", exist_ok=True)
        path = os.path.join("out", "entry.png")
        with open(path, "wb") as f:
            f.write(data)
    print(f"wrote {path} ({len(data)} bytes, {W}x{H})")


if __name__ == "__main__":
    main()

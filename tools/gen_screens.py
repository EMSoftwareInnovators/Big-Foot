#!/usr/bin/env python3
"""BIG FOOT -- the full-screen pictures: title, intro and ending.

Every picture is built as a silhouette against a black backdrop, because the
PPU shares colour 0 across all four background palettes.  That constraint is
also the look: a storm-lit kingdom with an enormous foot coming down out of
the dark.
"""
import foot
from nesart import Mask, Img
from screens import Screen, paste_mask, W, H

# ---------------------------------------------------------------------------
# palettes -- colour 0 is the shared backdrop and is black everywhere
# ---------------------------------------------------------------------------
TITLE_PAL = [
    0x0F, 0x01, 0x11, 0x21,     # 0 storm sky
    0x0F, 0x07, 0x27, 0x37,     # 1 the foot
    0x0F, 0x00, 0x10, 0x30,     # 2 stone, and white text
    0x0F, 0x06, 0x16, 0x30,     # 3 the logo
    0x0F, 0x07, 0x27, 0x37,     # sprites: the menu cursor
    0x0F, 0x06, 0x16, 0x30,
    0x0F, 0x00, 0x10, 0x30,
    0x0F, 0x01, 0x11, 0x30,
]

ENDING_PAL = [
    0x0F, 0x0C, 0x1C, 0x2C,     # 0 dawn sky
    0x0F, 0x07, 0x27, 0x37,     # 1 the foot
    0x0F, 0x00, 0x10, 0x30,     # 2 the statue and its plinth
    0x0F, 0x08, 0x28, 0x38,     # 3 gold
    0x0F, 0x07, 0x27, 0x37,
    0x0F, 0x08, 0x28, 0x38,
    0x0F, 0x00, 0x10, 0x30,
    0x0F, 0x0C, 0x1C, 0x30,
]

INTRO_PAL = [
    0x0F, 0x01, 0x11, 0x21,     # 0 night
    0x0F, 0x06, 0x16, 0x26,     # 1 fire
    0x0F, 0x00, 0x10, 0x30,     # 2 stone and text
    0x0F, 0x07, 0x17, 0x27,     # 3 earth
    0x0F, 0x07, 0x27, 0x37,
    0x0F, 0x06, 0x16, 0x26,
    0x0F, 0x00, 0x10, 0x30,
    0x0F, 0x01, 0x11, 0x30,
]


# ---------------------------------------------------------------------------
# block lettering for the logo
# ---------------------------------------------------------------------------
LETTERS = {
    "B": ["###.", "#..#", "###.", "#..#", "###."],
    "I": ["####", ".##.", ".##.", ".##.", "####"],
    "G": [".###", "#...", "#.##", "#..#", ".###"],
    "F": ["####", "#...", "###.", "#...", "#..."],
    "O": [".##.", "#..#", "#..#", "#..#", ".##."],
    "T": ["####", ".##.", ".##.", ".##.", ".##."],
    "H": ["#..#", "#..#", "####", "#..#", "#..#"],
    "E": ["####", "#...", "###.", "#...", "####"],
    "N": ["#..#", "##.#", "#.##", "#..#", "#..#"],
    "D": ["###.", "#..#", "#..#", "#..#", "###."],
    "A": [".##.", "#..#", "####", "#..#", "#..#"],
    "R": ["###.", "#..#", "###.", "#.#.", "#..#"],
    "S": [".###", "#...", ".##.", "...#", "###."],
    "W": ["#..#", "#..#", "#..#", "#.##", "##.#"],
    "L": ["#...", "#...", "#...", "#...", "####"],
}

CELL = 8                        # pixels per grid cell
LET_W, LET_H = 4 * CELL, 5 * CELL


def letter_mask(ch):
    """A capital built from whole 8x8 cells, so the logo reuses its tiles."""
    rows = LETTERS[ch]
    m = Mask(LET_W, LET_H)
    for gy, row in enumerate(rows):
        for gx, c in enumerate(row):
            if c == "#":
                m.rect(gx * CELL, gy * CELL,
                       gx * CELL + CELL - 1, gy * CELL + CELL - 1)
    return m


def draw_logo_word(scr, word, x0, y, gap, colours):
    """Cell-aligned lettering: a dark rim, a flat body, a bevel along the top.

    The bevel is measured from the topmost filled pixel of each column, not
    from every internal edge, so the letters read as solid slabs instead of
    being striped by their own bar joins.
    """
    dark, mid, light = colours
    x = x0
    for ch in word:
        m = letter_mask(ch)
        top = []
        for px in range(m.w):
            t = m.h
            for py in range(m.h):
                if m.get(px, py):
                    t = py
                    break
            top.append(t)
        for py in range(m.h):
            for px in range(m.w):
                if not m.get(px, py):
                    continue
                if (not m.get(px - 1, py) or not m.get(px + 1, py)
                        or not m.get(px, py - 1) or not m.get(px, py + 1)):
                    c = dark
                elif py - top[px] <= 3:
                    c = light
                else:
                    c = mid
                scr.img.put(x + px, y + py, c)
        x += LET_W + gap
    return x - gap


def word_span(word, gap):
    return len(word) * LET_W + (len(word) - 1) * gap


# ---------------------------------------------------------------------------
# scenery
# ---------------------------------------------------------------------------
SCALLOP = (0, 1, 2, 3, 3, 3, 2, 1, 0, 1, 2, 2, 3, 2, 1, 0)


def storm(scr, y0, y1, dense=3, phase=0, x0=0, x1=W - 1, height=10):
    """Broken cloud banks whose edges repeat every sixteen pixels.

    The repeat is the point: an irregular sky is lovely and costs two hundred
    unique tiles, which is the entire background pattern table.  Clumps are
    switched on and off in whole 16-pixel groups for the same reason.
    """
    step = max(height + 4, (y1 - y0) // max(1, dense))
    for i in range(dense):
        top = y0 + i * step
        c = 1 if i % 2 == 0 else 2
        for x in range(x0, x1 + 1):
            if ((x // 32) * 5 + i * 3) % 7 >= 4:
                continue
            s0 = SCALLOP[(x + phase + i * 5) % 16]
            s1 = SCALLOP[(x + phase * 2 + i * 9 + 8) % 16]
            for y in range(top + s0, min(y1, top + height - s1)):
                scr.img.put(x, y, c)


def lightning(scr, x, y0, y1, colour=3, spread=7, seed=1):
    """A jagged bolt drawn as short offset segments."""
    y = y0
    cx = x
    r = seed
    while y < y1:
        r = (r * 1103515245 + 12345) & 0x7FFFFFFF
        step = 5 + (r >> 16) % 7
        r = (r * 1103515245 + 12345) & 0x7FFFFFFF
        dx = ((r >> 16) % (2 * spread + 1)) - spread
        for i in range(step):
            if y + i >= y1:
                break
            px = cx + (dx * i) // step
            for w in range(2):
                if 0 <= px + w < W:
                    scr.img.put(px + w, y + i, colour)
        cx += dx
        y += step


def castle(scr, x0, y0, x1, y1, pal=2):
    """A small walled town: curtain wall, gate, three towers, roofs."""
    img = scr.img
    ground = y1
    wall_top = y1 - (y1 - y0) // 3
    img.rect(x0, wall_top, x1, ground, 1)
    for x in range(x0, x1 + 1, 8):          # crenellations
        img.rect(x, wall_top - 4, x + 3, wall_top - 1, 1)
    img.rect(x0, wall_top, x1, wall_top + 1, 2)
    # gate
    gx = (x0 + x1) // 2
    img.rect(gx - 4, ground - 12, gx + 4, ground, 0)
    img.rect(gx - 4, ground - 12, gx + 4, ground - 11, 2)
    # towers
    for i, tx in enumerate((x0 + 4, gx, x1 - 10)):
        th = (y1 - y0) - 6 - i * 4
        img.rect(tx, ground - th, tx + 9, ground, 1)
        img.rect(tx, ground - th, tx + 9, ground - th + 1, 2)
        for x in range(tx, tx + 10, 4):     # tower crenellations
            img.rect(x, ground - th - 4, x + 2, ground - th - 1, 1)
        img.rect(tx + 3, ground - th + 6, tx + 5, ground - th + 10, 2)
    # a keep behind the wall
    img.rect(gx - 14, y0, gx - 6, wall_top, 1)
    img.rect(gx - 14, y0, gx - 6, y0 + 1, 2)


def soldiers(scr, xs, y, colour=2):
    """Tiny figures: two pixels of head, a body and legs.  Four pixels wide."""
    for x in xs:
        scr.img.rect(x + 1, y, x + 2, y + 1, colour)
        scr.img.rect(x, y + 2, x + 3, y + 4, colour)
        scr.img.put(x, y + 5, colour)
        scr.img.put(x + 3, y + 5, colour)


def clear_cells(scr, x0, y0, x1, y1):
    """Blank whole 16x16 cells so a region can own its palette outright."""
    for y in range(y0 & ~15, min(H, (y1 | 15) + 1)):
        for x in range(x0 & ~15, min(W, (x1 | 15) + 1)):
            scr.img.put(x, y, 0)


def ground_strip(scr, y0, y1, near=1, far=2):
    scr.img.rect(0, y0, W - 1, y1, near)
    scr.img.rect(0, y0, W - 1, y0 + 1, far)
    for x in range(0, W, 16):
        scr.img.put(x + 3, y0 + 4, far)
        scr.img.put(x + 10, y0 + 6, far)


# ---------------------------------------------------------------------------
# the title screen
# ---------------------------------------------------------------------------
def build_title():
    scr = Screen("title")
    scr.region(0, 0, W - 1, H - 1, 0)

    # ---- the logo, on black, with lightning down either side -------------
    logo = (1, 2, 3)
    gap = 8
    ft = word_span("FOOT", gap)
    lx0, lx1 = (W - ft) // 2, (W + ft) // 2 - 1
    big = word_span("BIG", gap)
    draw_logo_word(scr, "BIG", (W - big) // 2, 12, gap, logo)
    draw_logo_word(scr, "FOOT", lx0, 56, gap, logo)
    scr.region(lx0, 0, lx1, 95, 3)
    lightning(scr, 12, 0, 92, seed=7)
    lightning(scr, 240, 0, 76, seed=31)

    # ---- the storm the foot is coming out of ------------------------------
    storm(scr, 100, 152, dense=3, height=13, x1=143)

    # ---- the foot ---------------------------------------------------------
    # Its cells stop at row 11 so the ground strip below can own row 12: a
    # 16-pixel cell holding both takes one palette and spoils the other.
    body, toes = foot.model_masks(2.4)
    whole = body.clone()
    for t in toes:
        whole.union(t)
    fx, fy = 152, 96
    clear_cells(scr, fx, fy, fx + whole.w - 1, 191)
    paste_mask(scr.img, whole, fx, fy, (1, 2, 3), bevel=11)
    for t in toes:                  # again, so each toe keeps its own rim
        paste_mask(scr.img, t, fx, fy, (1, 2, 3), bevel=5)
    scr.region(fx, fy, fx + whole.w - 1, 191, 1)

    # ---- the kingdom, directly underneath ---------------------------------
    clear_cells(scr, 8, 144, 143, 191)
    castle(scr, 20, 150, 100, 191)
    soldiers(scr, (110, 118, 124), 186)
    scr.region(8, 144, 143, 191, 2)
    ground_strip(scr, 192, 205)
    scr.region(0, 192, W - 1, 205, 2)
    scr.region(0, 206, W - 1, H - 1, 2)     # the menu prints here
    return scr


# ---------------------------------------------------------------------------
# the intro picture: the kingdom at night, before anything has happened
# ---------------------------------------------------------------------------
def build_intro():
    scr = Screen("intro")
    scr.region(0, 0, W - 1, H - 1, 0)
    storm(scr, 8, 76, dense=3, phase=3, height=13)
    for x in (30, 210):
        lightning(scr, x, 0, 56, seed=x)
    castle(scr, 60, 92, 196, 150)
    scr.region(48, 88, 207, 151, 2)
    soldiers(scr, (40, 48, 56, 204, 212), 144)
    ground_strip(scr, 152, 163)
    scr.region(0, 152, W - 1, 163, 2)
    scr.region(0, 164, W - 1, H - 1, 2)     # the report is printed here
    return scr


# ---------------------------------------------------------------------------
# the ending picture: the statue, whole again
# ---------------------------------------------------------------------------
def build_ending():
    scr = Screen("ending")
    scr.region(0, 0, W - 1, H - 1, 0)
    storm(scr, 4, 60, dense=3, phase=5, height=12)

    # plinth
    img = scr.img
    img.rect(96, 190, 160, 205, 1)
    img.rect(96, 190, 160, 191, 2)
    img.rect(88, 200, 168, 205, 1)
    img.rect(88, 200, 168, 201, 2)
    scr.region(80, 184, 175, 207, 2)

    # the statue: a robed figure with one foot missing, standing on the plinth
    m = Mask(64, 128)
    m.poly([(24, 6), (40, 6), (46, 40), (52, 118), (12, 118), (18, 40)])
    m.ellipse(32, 10, 11, 11)               # head
    m.ellipse(32, 34, 22, 12)               # shoulders
    m.poly([(10, 34), (18, 34), (14, 78), (6, 78)])      # left arm
    m.poly([(46, 34), (54, 34), (58, 78), (50, 78)])     # right arm
    paste_mask(img, m, 96, 66, (1, 2, 3))
    scr.region(96, 64, 159, 189, 2)

    # the right foot, restored, at the base of the statue
    body, toes = foot.model_masks(1.1)
    whole = body.clone()
    for t in toes:
        whole.union(t)
    paste_mask(img, whole, 128, 162, (1, 2, 3))
    for t in toes:
        paste_mask(img, t, 128, 162, (1, 2, 3))
    scr.region(128, 160, 128 + whole.w - 1, 189, 1)

    ground_strip(scr, 206, 215)
    scr.region(0, 206, W - 1, 215, 2)
    scr.region(0, 216, W - 1, H - 1, 2)
    return scr


SCREENS = [
    ("SCR_TITLE", build_title, TITLE_PAL),
    ("SCR_INTRO", build_intro, INTRO_PAL),
    ("SCR_ENDING", build_ending, ENDING_PAL),
]


# ---------------------------------------------------------------------------
def build(write, chr_rom):
    from screens import unrle
    asm = ["; Generated by tools/gen_screens.py -- do not edit.\n",
           '.export scr_bank, scr_nt_lo, scr_nt_hi, scr_at_lo, scr_at_hi\n'
           '.export scr_pal_lo, scr_pal_hi\n\n']
    body = ['.segment "B02"\n']
    inc = ["; Generated by tools/gen_screens.py -- do not edit.\n"]
    banks = []
    log = []
    total = 0
    for i, (name, fn, pal) in enumerate(SCREENS):
        scr = fn()
        tiles, nt, at = scr.compile()
        while len(tiles) < 192:
            tiles.append(Img(8, 8))
        b0 = None
        for k in range(0, 192, 64):
            b = chr_rom.add_1k("screen %s %d" % (scr.name, k // 64),
                               tiles[k:k + 64])
            if b0 is None:
                b0 = b
        banks.append(b0)
        assert len(unrle(nt)) == 960 and len(unrle(at)) == 64, scr.name
        inc.append("%s = %d\n" % (name, i))
        body.append("scr%d_nt:\n" % i + _bytes(nt))
        body.append("scr%d_at:\n" % i + _bytes(at))
        body.append("scr%d_pal:\n" % i + _bytes(bytes(pal)))
        total += len(nt) + len(at) + len(pal)
        log.append("  %-8s nametable %4d b  attr %2d b  chr $%02X..$%02X\n"
                   % (scr.name, len(nt), len(at), b0, b0 + 2))
        preview(scr, pal, "build/preview_%s.png" % scr.name)

    n = len(SCREENS)
    asm.append('.segment "RODATA"\n')
    asm.append("scr_bank:\n        .byte " +
               ",".join(str(b) for b in banks) + "\n")
    for tag in ("nt", "at", "pal"):
        asm.append("scr_%s_lo:\n        .byte " % tag +
                   ",".join("<scr%d_%s" % (i, tag) for i in range(n)) + "\n")
        asm.append("scr_%s_hi:\n        .byte " % tag +
                   ",".join(">scr%d_%s" % (i, tag) for i in range(n)) + "\n")
    asm.append("\n")
    asm.extend(body)
    inc.append("NUM_SCREENS = %d\n" % n)
    write("screen_data.s", "".join(asm))
    write("screens.inc", "".join(inc))
    log.append("  bank 2: %d/8192 bytes\n" % total)
    return "screens:\n" + "".join(log)


def _bytes(data):
    out = []
    for i in range(0, len(data), 16):
        out.append("        .byte " +
                   ",".join("$%02X" % b for b in data[i:i + 16]) + "\n")
    return "".join(out)


def preview(scr, pal, path):
    """Render the screen the way the PPU would, four palettes and all."""
    from nesart import NES_RGB, write_png_rgb
    px = []
    for y in range(H):
        row = []
        for x in range(W):
            p = scr.attr[min(14, y // 16)][min(15, x // 16)]
            row.append(NES_RGB[pal[p * 4 + scr.img.get(x, y)] & 0x3F])
        px.append(row)
    write_png_rgb(path, px, W, H, 2)


if __name__ == "__main__":
    import os
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from chrpack import ChrRom
    OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "..", "data", "generated")

    def w(name, text):
        open(os.path.join(OUT, name), "w").write(text)
        return len(text)

    print(build(w, ChrRom()))

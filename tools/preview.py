#!/usr/bin/env python3
"""Render the background metatiles of every theme as a labelled sheet.

Judging tile art through emulator screenshots is slow and only ever shows
the handful of metatiles that happen to be on screen.  This draws all of
them, in their real palettes, so a whole theme can be looked at at once.

    python3 tools/preview.py            # build/preview_themes.png
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from nesart import NES_RGB, write_png_rgb          # noqa: E402
import gen_bg                                       # noqa: E402
import gen_font                                     # noqa: E402

CELL = 16
GAP = 2
COLS = 16


def theme_sheet(th):
    """-> (pixels, width, height) for one theme."""
    items = []
    for name, (img, pal, col) in sorted(th.tiles.items()):
        items.append((name, img, pal, col))
    for name, (imgs, pal, col) in sorted(th.anim.items()):
        items.append((name + "*", imgs[0], pal, col))
    rows = (len(items) + COLS - 1) // COLS
    w = COLS * (CELL + GAP) + GAP
    h = rows * (CELL + GAP) + GAP
    px = [[(20, 20, 24) for _ in range(w)] for _ in range(h)]
    for i, (name, img, pal, col) in enumerate(items):
        cx = GAP + (i % COLS) * (CELL + GAP)
        cy = GAP + (i // COLS) * (CELL + GAP)
        colours = [th.bg] + list(th.pals[pal])
        for y in range(CELL):
            for x in range(CELL):
                c = img.px[y][x] if y < img.h and x < img.w else 0
                px[cy + y][cx + x] = NES_RGB[colours[c] & 0x3F]
    return px, w, h, items


def sprite_sheet(pal_of):
    """Every enemy, object and boss frame, in its sprite palette."""
    import gen_sprites
    import gen_levels
    items = []
    for table in (gen_sprites.ENEMY_ART, gen_sprites.OBJECT_ART):
        for name, (frames, pal, w, h) in sorted(table.items()):
            for i, img in enumerate(frames):
                items.append((name if i == 0 else "", img, pal))
    for b, fn in enumerate(gen_levels.BOSS_ART):
        for i in range(gen_levels.BOSS_FRAMES[b]):
            items.append((gen_levels.BOSS_NAMES[b] if i == 0 else "",
                          fn(i), 1))
    cw = max(i[1].w for i in items) + 2
    ch = max(i[1].h for i in items) + 2
    cols = max(1, 512 // cw)
    rows = (len(items) + cols - 1) // cols
    w, h = cols * cw, rows * ch
    px = [[(20, 20, 24) for _ in range(w)] for _ in range(h)]
    names = []
    for i, (name, img, pal) in enumerate(items):
        ox = (i % cols) * cw + 1
        oy = (i // cols) * ch + 1
        colours = [0x0F] + list(gen_levels.SPR_PALS[0][pal])
        for y in range(img.h):
            for x in range(img.w):
                c = img.px[y][x]
                if c:
                    px[oy + y][ox + x] = NES_RGB[colours[c] & 0x3F]
        if name:
            names.append("%s@%d" % (name, i))
    return px, w, h, names


def main():
    themes = [fn() for fn in gen_bg.THEMES]
    if len(sys.argv) > 1:
        themes = [t for t in themes if t.name in sys.argv[1:]]

    sheets = [theme_sheet(th) for th in themes]
    width = max(s[1] for s in sheets)
    height = sum(s[2] + 8 for s in sheets)
    out = [[(12, 12, 14) for _ in range(width)] for _ in range(height)]
    y = 0
    report = []
    for th, (px, w, h, items) in zip(themes, sheets):
        for r in range(h):
            for c in range(w):
                out[y + r][c] = px[r][c]
        report.append("\n%s  backdrop $%02X  %d metatiles\n"
                      % (th.name.upper(), th.bg, len(items)))
        for r in range(0, len(items), COLS):
            report.append("   " + " ".join("%-8s" % items[i][0]
                                           for i in range(r, min(r + COLS, len(items))))
                          + "\n")
        y += h + 8
    name = "build/preview_%s.png" % ("_".join(sys.argv[1:]) or "themes")
    write_png_rgb(name, out, width, height, 3)
    if not sys.argv[1:]:
        spx, sw, sh, snames = sprite_sheet(None)
        write_png_rgb("build/preview_sprites.png", spx, sw, sh, 3)
        for i in range(0, len(snames), 6):
            sys.stdout.write("   " + "  ".join(snames[i:i + 6]) + "\n")
        sys.stdout.write("wrote build/preview_sprites.png\n")
    sys.stdout.write("".join(report))
    sys.stdout.write("wrote %s (%dx%d)\n" % (name, width * 3, height * 3))


if __name__ == "__main__":
    main()

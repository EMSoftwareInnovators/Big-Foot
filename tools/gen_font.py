#!/usr/bin/env python3
"""The shared HUD / font CHR bank (MMC3 R5, tile indices $C0..$FF).

A compact 5x7 uppercase face in the style of NES-era fantasy localisations,
plus the health meter, icons and window furniture the HUD needs.
"""
from nesart import Img

GLYPHS = {
    'A': ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    'B': ["11110", "10001", "11110", "10001", "10001", "10001", "11110"],
    'C': ["01110", "10001", "10000", "10000", "10000", "10001", "01110"],
    'D': ["11110", "10001", "10001", "10001", "10001", "10001", "11110"],
    'E': ["11111", "10000", "11110", "10000", "10000", "10000", "11111"],
    'F': ["11111", "10000", "11110", "10000", "10000", "10000", "10000"],
    'G': ["01110", "10001", "10000", "10111", "10001", "10001", "01111"],
    'H': ["10001", "10001", "11111", "10001", "10001", "10001", "10001"],
    'I': ["01110", "00100", "00100", "00100", "00100", "00100", "01110"],
    'J': ["00111", "00010", "00010", "00010", "00010", "10010", "01100"],
    'K': ["10001", "10010", "10100", "11000", "10100", "10010", "10001"],
    'L': ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
    'M': ["10001", "11011", "10101", "10101", "10001", "10001", "10001"],
    'N': ["10001", "11001", "10101", "10011", "10001", "10001", "10001"],
    'O': ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    'P': ["11110", "10001", "10001", "11110", "10000", "10000", "10000"],
    'Q': ["01110", "10001", "10001", "10001", "10101", "10010", "01101"],
    'R': ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
    'S': ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
    'T': ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
    'U': ["10001", "10001", "10001", "10001", "10001", "10001", "01110"],
    'V': ["10001", "10001", "10001", "10001", "10001", "01010", "00100"],
    'W': ["10001", "10001", "10001", "10101", "10101", "11011", "10001"],
    'X': ["10001", "10001", "01010", "00100", "01010", "10001", "10001"],
    'Y': ["10001", "10001", "01010", "00100", "00100", "00100", "00100"],
    'Z': ["11111", "00001", "00010", "00100", "01000", "10000", "11111"],
    '0': ["01110", "10001", "10011", "10101", "11001", "10001", "01110"],
    '1': ["00100", "01100", "00100", "00100", "00100", "00100", "01110"],
    '2': ["01110", "10001", "00001", "00110", "01000", "10000", "11111"],
    '3': ["11111", "00010", "00100", "00010", "00001", "10001", "01110"],
    '4': ["00010", "00110", "01010", "10010", "11111", "00010", "00010"],
    '5': ["11111", "10000", "11110", "00001", "00001", "10001", "01110"],
    '6': ["00110", "01000", "10000", "11110", "10001", "10001", "01110"],
    '7': ["11111", "00001", "00010", "00100", "01000", "01000", "01000"],
    '8': ["01110", "10001", "10001", "01110", "10001", "10001", "01110"],
    '9': ["01110", "10001", "10001", "01111", "00001", "00010", "01100"],
    '.': ["00000", "00000", "00000", "00000", "00000", "01100", "01100"],
    ',': ["00000", "00000", "00000", "00000", "01100", "01100", "01000"],
    '!': ["00100", "00100", "00100", "00100", "00100", "00000", "00100"],
    '?': ["01110", "10001", "00001", "00110", "00100", "00000", "00100"],
    "'": ["00100", "00100", "01000", "00000", "00000", "00000", "00000"],
    '-': ["00000", "00000", "00000", "11111", "00000", "00000", "00000"],
    ':': ["00000", "01100", "01100", "00000", "01100", "01100", "00000"],
    '/': ["00001", "00010", "00010", "00100", "01000", "01000", "10000"],
    '(': ["00010", "00100", "01000", "01000", "01000", "00100", "00010"],
    ')': ["01000", "00100", "00010", "00010", "00010", "00100", "01000"],
    '*': ["00000", "10101", "01110", "11111", "01110", "10101", "00000"],
    '"': ["01010", "01010", "01010", "00000", "00000", "00000", "00000"],
    '+': ["00000", "00100", "00100", "11111", "00100", "00100", "00000"],
}

# order defines the tile index within the shared bank
CHARSET = (" ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.,!?'-:/()*\"+")


def glyph_img(ch, fg=3, shadow=1):
    im = Img(8, 8)
    rows = GLYPHS.get(ch)
    if not rows:
        return im
    for y, r in enumerate(rows):
        for x, c in enumerate(r):
            if c == '1':
                im.px[y + 1][x + 1] = fg
    # a one-pixel drop shadow keeps text readable over busy backgrounds
    for y in range(6, -1, -1):
        for x in range(6, -1, -1):
            if im.px[y][x] == fg and im.px[y + 1][x + 1] == 0:
                im.px[y + 1][x + 1] = shadow
    return im


def _bar(fill):
    """Health meter cell: 0 = empty, 1 = half, 2 = full."""
    im = Img(8, 8)
    for x in range(8):
        im.px[1][x] = 1
        im.px[6][x] = 1
    for y in range(1, 7):
        im.px[y][0] = 1
        im.px[y][7] = 1
    for y in range(2, 6):
        for x in range(1, 7):
            im.px[y][x] = 0
    if fill:
        w = 6 if fill == 2 else 3
        for y in range(2, 6):
            for x in range(1, 1 + w):
                im.px[y][x] = 3 if y < 4 else 2
    return im


def _foot_icon():
    im = Img(8, 8)
    pts = [(2, 1), (3, 1), (4, 1), (1, 2), (2, 2), (3, 2), (4, 2), (5, 2),
           (1, 3), (2, 3), (3, 3), (4, 3), (5, 3), (2, 4), (3, 4), (4, 4),
           (5, 4), (2, 5), (3, 5), (4, 5), (5, 5), (6, 5), (3, 6), (4, 6),
           (5, 6), (6, 6)]
    for x, y in pts:
        im.px[y][x] = 2
    for x, y in [(2, 1), (3, 1), (1, 2), (1, 3), (6, 5), (6, 6)]:
        im.px[y][x] = 3
    for x in range(1, 7):
        if im.px[7][x] == 0 and im.px[6][x]:
            im.px[7][x] = 1
    return im


def _shoe_icon():
    im = Img(8, 8)
    for y in range(3, 7):
        for x in range(1, 7):
            im.px[y][x] = 2
    for x in range(1, 7):
        im.px[6][x] = 1
    for y in range(2, 5):
        im.px[y][1] = 3
    im.px[2][2] = 2
    im.px[2][3] = 2
    return im


def _divider(kind):
    im = Img(8, 8)
    if kind == 0:      # solid rule used for the sprite-0 split row
        for x in range(8):
            im.px[0][x] = 1
            im.px[1][x] = 2
            im.px[2][x] = 3
            for y in range(3, 8):
                im.px[y][x] = 1
    elif kind == 1:    # plain filled tile
        for y in range(8):
            for x in range(8):
                im.px[y][x] = 1
    elif kind == 2:    # woven HUD backing
        for y in range(8):
            for x in range(8):
                im.px[y][x] = 1 if ((x ^ y) & 4) else 2
    return im


def _boss_bar(fill):
    im = Img(8, 8)
    for x in range(8):
        im.px[2][x] = 1
        im.px[6][x] = 1
    for y in range(3, 6):
        for x in range(8):
            im.px[y][x] = 3 if fill else 0
    if fill:
        for x in range(8):
            im.px[3][x] = 3
            im.px[4][x] = 2
            im.px[5][x] = 2
    return im


def _arrow(dirn):
    im = Img(8, 8)
    if dirn == 0:
        for i in range(4):
            for y in range(3 - i, 5 + i):
                im.px[y][2 + i] = 3
    else:
        for i in range(4):
            for y in range(3 - i, 5 + i):
                im.px[y][5 - i] = 3
    return im


def build_tiles():
    """Returns the 64 tiles of the shared bank, plus name -> index map."""
    tiles = []
    names = {}
    for ch in CHARSET:
        names[ch] = len(tiles)
        tiles.append(glyph_img(ch))
    names['#BAR0'] = len(tiles); tiles.append(_bar(0))
    names['#BAR1'] = len(tiles); tiles.append(_bar(1))
    names['#BAR2'] = len(tiles); tiles.append(_bar(2))
    names['#FOOT'] = len(tiles); tiles.append(_foot_icon())
    names['#SHOE'] = len(tiles); tiles.append(_shoe_icon())
    names['#RULE'] = len(tiles); tiles.append(_divider(0))
    names['#SOLID'] = len(tiles); tiles.append(_divider(1))
    names['#WEAVE'] = len(tiles); tiles.append(_divider(2))
    names['#BOSS0'] = len(tiles); tiles.append(_boss_bar(0))
    names['#BOSS1'] = len(tiles); tiles.append(_boss_bar(1))
    names['#ARROWL'] = len(tiles); tiles.append(_arrow(0))
    names['#ARROWR'] = len(tiles); tiles.append(_arrow(1))
    if len(tiles) > 64:
        raise RuntimeError("HUD bank overflow: %d tiles" % len(tiles))
    while len(tiles) < 64:
        tiles.append(Img(8, 8))
    return tiles, names

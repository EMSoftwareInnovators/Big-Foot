#!/usr/bin/env python3
"""
Footwear.

Every shoe completely encloses the foot, so the whole player metasprite can
use a single sprite palette that is simply swapped when footwear changes.
Each shoe is derived from the current frame's foot masks, which means all of
them animate exactly as well as the bare foot does.
"""
from nesart import Img, Mask, shade_mask

from foot import CW, CH


def _combined(body, toes):
    m = body.clone()
    for t in toes:
        m.union(t)
    return m


def _sole(mask, thickness, extend_front=0, extend_back=0):
    """A slab under the whole footprint."""
    s = Mask(CW, CH)
    cols = []
    for x in range(CW):
        col = [y for y in range(CH) if mask.m[y][x]]
        cols.append(col[-1] if col else None)
    lo = min([x for x in range(CW) if cols[x] is not None] or [0])
    hi = max([x for x in range(CW) if cols[x] is not None] or [0])
    base = max(c for c in cols if c is not None)
    for x in range(max(0, lo - extend_back), min(CW, hi + 1 + extend_front)):
        top = cols[x] if cols[x] is not None else base
        top = min(top, base)
        for y in range(top - thickness + 1, base + 1):
            s.put(x, y)
    return s


def _shade_shoe(shape, detail=None, light_erode=4):
    img = shade_mask(shape, 1, 2, 3, -1, -2, light_erode)
    if detail:
        detail(img, shape)
    return img


def _base_shoe(body, toes, grow=1, collar=0):
    m = _combined(body, toes).dilate(grow)
    if collar:
        bb = _bbox(body)
        if bb:
            x0, y0, x1, y1 = bb
            c = Mask(CW, CH)
            c.rect(x0 - 1, y0 + collar, x1 + 1, y0 + collar + 3)
            c.intersect(_combined(body, toes).dilate(grow + 1))
            m.union(c)
    return m


def _bbox(m):
    x0, y0, x1, y1 = m.w, m.h, -1, -1
    for y in range(m.h):
        for x in range(m.w):
            if m.m[y][x]:
                x0 = min(x0, x); y0 = min(y0, y)
                x1 = max(x1, x); y1 = max(y1, y)
    return None if x1 < 0 else (x0, y0, x1, y1)


def _opening(img, body):
    """Draw the boot opening on the flat top of the ankle stump."""
    bb = _bbox(body)
    if not bb:
        return
    x0, y0, x1, y1 = bb
    for y in range(y0, min(y0 + 3, y1 + 1)):
        for x in range(x0, x1 + 1):
            if body.m[y][x]:
                img.put(x, y, 1 if y == y0 else 3)


# ---------------------------------------------------------------------------
def shoe_running(img, body, toes, pose):
    shape = _base_shoe(body, toes, 1)
    sole = _sole(shape, 3, 1, 1)
    shape.union(sole)
    out = _shade_shoe(shape)
    # white sole slab
    for y in range(CH):
        for x in range(CW):
            if sole.m[y][x] and out.px[y][x]:
                out.px[y][x] = 3
    # three racing stripes across the flank
    bb = _bbox(shape)
    if bb:
        x0, y0, x1, y1 = bb
        for i in range(3):
            sx = x0 + 6 + i * 4
            for k in range(5):
                yy = y1 - 6 - k
                xx = sx + k
                if shape.get(xx, yy) and not sole.get(xx, yy):
                    out.put(xx, yy, 1)
    _opening(out, body)
    return out


def shoe_steel(img, body, toes, pose):
    shape = _base_shoe(body, toes, 2, collar=6)
    sole = _sole(shape, 4, 1, 2)
    shape.union(sole)
    out = _shade_shoe(shape, light_erode=5)
    for y in range(CH):
        for x in range(CW):
            if sole.m[y][x] and out.px[y][x]:
                out.px[y][x] = 1
    # steel toe cap: a bright plate over the front third
    bb = _bbox(shape)
    if bb:
        x0, y0, x1, y1 = bb
        capx = x1 - (x1 - x0) // 3
        for y in range(y0, y1 + 1):
            for x in range(capx, x1 + 1):
                if shape.get(x, y) and not sole.get(x, y) and out.px[y][x] != 1:
                    out.px[y][x] = 3
        # rivets along the seam
        for y in range(y0 + 4, y1 - 3, 4):
            if shape.get(capx - 1, y):
                out.put(capx - 1, y, 1)
    _opening(out, body)
    return out


def shoe_cowboy(img, body, toes, pose):
    shape = _base_shoe(body, toes, 1)
    bb = _bbox(body)
    if bb:
        x0, y0, x1, y1 = bb
        shaft = Mask(CW, CH)
        shaft.rect(x0 - 2, y0, x1 + 2, y0 + 16)
        shaft.intersect(body.dilate(3))
        shape.union(shaft)
    sole = _sole(shape, 2, 1, 0)
    heel = Mask(CW, CH)
    fb = _bbox(shape)
    if fb:
        x0, y0, x1, y1 = fb
        heel.rect(x0, y1 - 4, x0 + 6, y1)
        heel.intersect(_sole(shape, 6, 0, 0))
    shape.union(sole)
    shape.union(heel)
    # spur
    spur = Mask(CW, CH)
    if fb:
        x0, y0, x1, y1 = fb
        spur.ellipse(x0 - 1, y1 - 5, 2.5, 2.5)
        shape.union(spur)
    out = _shade_shoe(shape)
    for y in range(CH):
        for x in range(CW):
            if (sole.m[y][x] or heel.m[y][x]) and out.px[y][x]:
                out.px[y][x] = 1
            elif spur.m[y][x] and out.px[y][x]:
                out.px[y][x] = 3
    # decorative stitching
    if bb:
        x0, y0, x1, y1 = bb
        for x in range(x0, x1 + 1):
            if shape.get(x, y0 + 12) and out.px[y0 + 12][x] not in (1,):
                out.put(x, y0 + 12, 1)
    _opening(out, body)
    return out


def shoe_cleat(img, body, toes, pose):
    shape = _base_shoe(body, toes, 1)
    sole = _sole(shape, 3, 0, 0)
    shape.union(sole)
    out = _shade_shoe(shape)
    for y in range(CH):
        for x in range(CW):
            if sole.m[y][x] and out.px[y][x] == 3:
                out.px[y][x] = 2
    # studded sole: alternating bright teeth chewed into the bottom edge
    for x in range(CW):
        col = [y for y in range(CH) if shape.m[y][x]]
        if not col:
            continue
        b = col[-1]
        if (x & 1) == 0:
            out.put(x, b, 3)
            out.put(x, b - 1, 3)
        else:
            out.put(x, b, 1)
    # frost highlights over the upper
    bb = _bbox(shape)
    if bb:
        x0, y0, x1, y1 = bb
        for k in range(4):
            xx = x0 + 4 + k * 4
            yy = y0 + 14 + (k & 1) * 3
            if shape.get(xx, yy):
                out.put(xx, yy, 3)
    _opening(out, body)
    return out


def shoe_flipper(img, body, toes, pose):
    shape = _base_shoe(body, toes, 1)
    fin = Mask(CW, CH)
    bb = _bbox(shape)
    if bb:
        x0, y0, x1, y1 = bb
        # a broad swim fin running the length of the sole and out past the toes
        fin.poly([(x0 - 1, y1 - 2), (x1 + 1, y1 - 6), (CW - 1, y1 - 5),
                  (CW - 1, y1), (x0 - 1, y1)])
        shape.union(fin)
    out = _shade_shoe(shape)
    if bb:
        x0, y0, x1, y1 = bb
        for x in range(x0, CW, 3):
            for y in range(y1 - 6, y1 + 1):
                if fin.get(x, y) and out.px[y][x]:
                    out.put(x, y, 1)
        for x in range(x0, CW):
            if fin.get(x, y1 - 6) and out.px[y1 - 6][x]:
                out.put(x, y1 - 6, 3)
    _opening(out, body)
    return out


def shoe_slipper(img, body, toes, pose):
    shape = _base_shoe(body, toes, 2)
    out = _shade_shoe(shape, light_erode=3)
    # fluffy trim: break up the silhouette with alternating light pixels
    bb = _bbox(shape)
    if bb:
        x0, y0, x1, y1 = bb
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                if out.px[y][x] == 1 and ((x + y) & 1) == 0:
                    out.px[y][x] = 3
        # a soft collar band
        for x in range(x0, x1 + 1):
            yy = y0 + 10
            if shape.get(x, yy):
                out.put(x, yy, 3)
    _opening(out, body)
    return out


def shoe_big(img, body, toes, pose):
    shape = _base_shoe(body, toes, 3, collar=4)
    sole = _sole(shape, 5, 2, 2)
    shape.union(sole)
    out = _shade_shoe(shape, light_erode=6)
    for y in range(CH):
        for x in range(CW):
            if sole.m[y][x] and out.px[y][x]:
                out.px[y][x] = 1
    bb = _bbox(shape)
    if bb:
        x0, y0, x1, y1 = bb
        # an enormous buckle
        cx = x0 + (x1 - x0) // 2 + 1
        cy = y1 - 13
        for y in range(cy - 3, cy + 4):
            for x in range(cx - 3, cx + 4):
                if shape.get(x, y):
                    edge = (y in (cy - 3, cy + 3)) or (x in (cx - 3, cx + 3))
                    out.put(x, y, 3 if edge else 2)
        for x in range(x0, x1 + 1):
            if shape.get(x, cy):
                if not (cx - 3 <= x <= cx + 3):
                    out.put(x, cy, 1)
    _opening(out, body)
    return out


SHOES = [
    None,             # 0 bare
    shoe_running,     # 1
    shoe_steel,       # 2
    shoe_cowboy,      # 3
    shoe_cleat,       # 4
    shoe_flipper,     # 5
    shoe_slipper,     # 6
    shoe_big,         # 7
]

SHOE_NAMES = ["BARE", "RUNNING SHOE", "STEEL-TOED BOOT", "COWBOY BOOT",
              "ICE CLEAT", "FLIPPER", "SLIPPER", "BIG SHOE"]

# sprite palettes: (colour1, colour2, colour3); entry 0 is transparent
SHOE_PALETTES = [
    (0x16, 0x27, 0x37),   # bare skin
    (0x06, 0x16, 0x30),   # running shoe: red and white
    (0x0F, 0x00, 0x10),   # steel boot: black and grey
    (0x07, 0x17, 0x28),   # cowboy boot: leather and brass
    (0x01, 0x11, 0x31),   # ice cleat: blue and frost
    (0x0B, 0x1A, 0x2A),   # flipper: deep green rubber
    (0x04, 0x14, 0x34),   # slipper: plush pink
    (0x0F, 0x18, 0x28),   # big shoe: black leather and gold
]

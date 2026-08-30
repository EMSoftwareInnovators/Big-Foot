#!/usr/bin/env python3
"""Procedural 16x16 metatile textures.

Every helper draws with colour indices 0..3 of whichever background palette
the metatile is assigned, so the same routine produces stone, timber or steel
depending on the palette it is paired with.
"""
from nesart import Img


class Rnd(object):
    """Deterministic LCG so a build is reproducible."""

    def __init__(self, seed):
        self.s = (seed * 1103515245 + 12345) & 0x7FFFFFFF

    def next(self):
        self.s = (self.s * 1103515245 + 12345) & 0x7FFFFFFF
        return (self.s >> 16) & 0x7FFF

    def rng(self, n):
        return self.next() % n

    def chance(self, num, den):
        return self.rng(den) < num


def mt(fill=0):
    return Img(16, 16, fill)


# ---------------------------------------------------------------------------
def speckle(img, colour, seed, density=8, x0=0, y0=0, x1=15, y1=15, over=None):
    r = Rnd(seed)
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            if over is not None and img.px[y][x] != over:
                continue
            if r.rng(32) < density:
                img.px[y][x] = colour


def bricks(seed, base=2, mortar=1, light=3, bw=8, bh=4, offset=True,
           damage=0, moss=0, moss_c=3):
    """Coursed masonry with per-course offsets, chipped corners and moss."""
    img = mt(base)
    r = Rnd(seed)
    for y in range(16):
        row = y // bh
        shift = (row * (bw // 2)) if offset else 0
        if y % bh == bh - 1:
            for x in range(16):
                img.px[y][x] = mortar
            continue
        for x in range(16):
            if (x + shift) % bw == 0:
                img.px[y][x] = mortar
        # top highlight of each course
        if y % bh == 0:
            for x in range(16):
                if img.px[y][x] == base and r.rng(8) < 6:
                    img.px[y][x] = light
    if damage:
        for _ in range(damage):
            cx, cy = r.rng(14) + 1, r.rng(14) + 1
            for dy in range(-1, 2):
                for dx in range(-1, 2):
                    if 0 <= cx + dx < 16 and 0 <= cy + dy < 16 and r.chance(2, 3):
                        img.px[cy + dy][cx + dx] = mortar
    if moss:
        for _ in range(moss):
            cx, cy = r.rng(15), r.rng(13)
            for dy in range(3):
                for dx in range(r.rng(4) + 1):
                    if cx + dx < 16 and cy + dy < 16 and r.chance(2, 3):
                        img.px[cy + dy][cx + dx] = moss_c
    return img


def rubble(seed, base=2, dark=1, light=3, density=10):
    """Loose broken stone / gravel fill."""
    img = mt(base)
    r = Rnd(seed)
    for _ in range(density):
        w = r.rng(4) + 2
        h = r.rng(3) + 2
        x = r.rng(16 - w)
        y = r.rng(16 - h)
        c = light if r.chance(1, 2) else dark
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                img.px[yy][xx] = c
        for xx in range(x, x + w):
            img.px[y][xx] = light if c == dark else dark
    speckle(img, dark, seed + 7, 4)
    return img


def soil(seed, base=2, dark=1, light=3, grain=7):
    img = mt(base)
    r = Rnd(seed)
    for y in range(16):
        for x in range(16):
            n = r.rng(24)
            if n < 3:
                img.px[y][x] = dark
            elif n < 6:
                img.px[y][x] = light
    for _ in range(grain // 2):
        x, y = r.rng(13), r.rng(14)
        for k in range(r.rng(4) + 2):
            if x + k < 16:
                img.px[y][x + k] = dark
    return img


def grass_cap(seed, top=3, blade=3, body=2, dark=1, depth=5):
    """A grass-topped ground metatile: tufted top edge over soil."""
    img = soil(seed, body, dark, body)
    r = Rnd(seed + 3)
    for x in range(16):
        h = depth + r.rng(3) - 1
        for y in range(h):
            img.px[y][x] = top
        img.px[h][x] = top if r.chance(1, 3) else dark
        if r.chance(1, 4) and h + 1 < 16:
            img.px[h + 1][x] = blade
    for x in range(0, 16, 2):
        if r.chance(1, 2):
            img.px[0][x] = top
    speckle(img, dark, seed + 11, 3, 0, depth + 2)
    return img


def planks(seed, base=2, dark=1, light=3, horizontal=True, ph=5):
    img = mt(base)
    r = Rnd(seed)
    for i in range(16):
        if horizontal:
            if i % ph == 0:
                for x in range(16):
                    img.px[i][x] = dark
            elif i % ph == 1:
                for x in range(16):
                    if r.chance(3, 4):
                        img.px[i][x] = light
        else:
            if i % ph == 0:
                for y in range(16):
                    img.px[y][i] = dark
            elif i % ph == 1:
                for y in range(16):
                    if r.chance(3, 4):
                        img.px[y][i] = light
    # knots and grain
    for _ in range(3):
        x, y = r.rng(14) + 1, r.rng(14) + 1
        img.px[y][x] = dark
        if r.chance(1, 2):
            img.px[y][x + 1] = dark
    return img


def metal_plate(seed, base=2, dark=1, light=3, rivets=True):
    img = mt(base)
    r = Rnd(seed)
    for x in range(16):
        img.px[0][x] = light
        img.px[15][x] = dark
    for y in range(16):
        img.px[y][0] = light
        img.px[y][15] = dark
    if rivets:
        for cy in (3, 12):
            for cx in (3, 12):
                img.px[cy][cx] = light
                img.px[cy + 1][cx] = dark
                img.px[cy][cx + 1] = dark
    for _ in range(2):
        y = r.rng(10) + 3
        for x in range(r.rng(6) + 4):
            img.px[y][x + 2] = dark
    return img


def foliage(seed, dark=1, mid=2, light=3, density=6):
    """Leaf canopy: clumped blobs with a lit upper edge."""
    img = mt(mid)
    r = Rnd(seed)
    for _ in range(density):
        cx, cy = r.rng(16), r.rng(16)
        rr = r.rng(3) + 2
        for y in range(cy - rr, cy + rr + 1):
            for x in range(cx - rr, cx + rr + 1):
                if 0 <= x < 16 and 0 <= y < 16:
                    d = (x - cx) ** 2 + (y - cy) ** 2
                    if d <= rr * rr:
                        img.px[y][x] = light if (y < cy) else mid
                    elif d <= rr * rr + rr:
                        img.px[y][x] = dark
    speckle(img, dark, seed + 5, 5)
    speckle(img, light, seed + 9, 3)
    return img


def water(seed, dark=1, mid=2, light=3, phase=0, surface=False):
    img = mt(mid)
    r = Rnd(seed)
    for y in range(16):
        for x in range(16):
            w = (x + phase * 3 + (y // 2) * 5) % 16
            if w < 3:
                img.px[y][x] = light
            elif w < 6:
                img.px[y][x] = dark
    if surface:
        for x in range(16):
            h = 1 + ((x + phase * 4) // 4) % 2
            for y in range(h):
                img.px[y][x] = light
            img.px[h][x] = dark
    speckle(img, dark, seed + phase, 2)
    return img


def spikes(seed, dark=1, mid=2, light=3, base_c=2, up=True):
    img = mt(0)
    for x in range(16):
        img.px[15][x] = base_c
        img.px[14][x] = dark
    for i in range(4):
        cx = i * 4 + 2
        for k in range(11):
            y = 13 - k
            half = max(0, (11 - k) // 3)
            for x in range(cx - half, cx + half + 1):
                if 0 <= x < 16:
                    img.px[y][x] = mid
            if cx - half >= 0:
                img.px[y][cx - half] = light
            if cx + half < 16:
                img.px[y][cx + half] = dark
    if not up:
        f = mt(0)
        for y in range(16):
            f.px[y] = img.px[15 - y]
        img = f
    return img


def gear(seed, dark=1, mid=2, light=3, phase=0):
    img = mt(0)
    cx = cy = 8
    for y in range(16):
        for x in range(16):
            d2 = (x - cx + 0.5) ** 2 + (y - cy + 0.5) ** 2
            if d2 < 25:
                img.px[y][x] = mid
            if d2 < 9:
                img.px[y][x] = dark
            if d2 < 4:
                img.px[y][x] = 0
    import math
    for i in range(8):
        a = (i * 45 + phase * 15) * math.pi / 180.0
        tx = int(cx + math.cos(a) * 6.4)
        ty = int(cy + math.sin(a) * 6.4)
        for dy in range(-1, 2):
            for dx in range(-1, 2):
                if 0 <= tx + dx < 16 and 0 <= ty + dy < 16:
                    img.px[ty + dy][tx + dx] = light
    return img


def fence(seed, post=2, dark=1, light=3):
    img = mt(0)
    for x in (2, 3, 10, 11):
        for y in range(4, 16):
            img.px[y][x] = post
        img.px[4][x] = light
        img.px[15][x] = dark
    for y in (6, 7, 11, 12):
        for x in range(16):
            img.px[y][x] = post if y % 2 == 0 else dark
    return img


def cloud(seed, light=3, mid=2):
    img = mt(0)
    r = Rnd(seed)
    for _ in range(5):
        cx, cy = r.rng(14) + 1, r.rng(6) + 5
        rr = r.rng(3) + 2
        for y in range(cy - rr, cy + rr + 1):
            for x in range(cx - rr, cx + rr + 1):
                if 0 <= x < 16 and 0 <= y < 16:
                    if (x - cx) ** 2 + (y - cy) ** 2 <= rr * rr:
                        img.px[y][x] = light if y <= cy else mid
    return img


def arch_window(seed, frame=2, dark=1, glass=3):
    img = mt(frame)
    for y in range(16):
        for x in range(16):
            if 3 <= x <= 12 and 4 <= y <= 15:
                img.px[y][x] = glass
    for x in range(4, 12):
        img.px[3][x] = glass
    for x in range(5, 11):
        img.px[2][x] = glass
    for y in range(16):
        for x in range(16):
            if img.px[y][x] == glass:
                if (x + y) % 5 == 0:
                    img.px[y][x] = dark
    for y in range(2, 16):
        for x in range(16):
            if img.px[y][x] == glass and (x == 3 or x == 12):
                img.px[y][x] = dark
    return img


def stairs(seed, base=2, dark=1, light=3, step=4):
    img = mt(base)
    for y in range(16):
        for x in range(16):
            if (y // step) * step == y:
                img.px[y][x] = light
            if y % step == step - 1:
                img.px[y][x] = dark
    for i in range(4):
        x0 = i * 4
        for y in range(i * 4, 16):
            img.px[y][x0] = dark
    return img


def banner(seed, cloth=2, dark=1, light=3):
    img = mt(0)
    for y in range(16):
        for x in range(4, 12):
            img.px[y][x] = cloth
        img.px[y][4] = light
        img.px[y][11] = dark
    for x in range(4, 12):
        img.px[0][x] = dark
    for x in range(6, 10):
        img.px[7][x] = light
    img.px[6][7] = light
    img.px[8][8] = light
    return img


def pipes(seed, base=2, dark=1, light=3):
    img = mt(0)
    for y in range(3, 8):
        for x in range(16):
            img.px[y][x] = base
    for x in range(16):
        img.px[3][x] = light
        img.px[7][x] = dark
    for y in range(10, 15):
        for x in range(16):
            img.px[y][x] = base
    for x in range(16):
        img.px[10][x] = light
        img.px[14][x] = dark
    for x in (2, 11):
        for y in range(2, 9):
            img.px[y][x] = dark
        for y in range(9, 16):
            img.px[y][x] = dark
    return img


def chain(seed, dark=1, mid=2, light=3):
    img = mt(0)
    for k in range(4):
        cy = k * 4 + 2
        for dy in (-1, 0, 1):
            for dx in (-2, -1, 0, 1, 2):
                y, x = cy + dy, 8 + dx
                if 0 <= x < 16 and 0 <= y < 16:
                    img.px[y][x] = mid
        img.px[cy][6] = light
        img.px[cy][10] = dark
        img.px[cy - 1][8] = light
    return img

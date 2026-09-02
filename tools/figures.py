#!/usr/bin/env python3
"""
Sprite art for everything that is not Big Foot.

Humans are built from the same mask-and-shade pipeline as the foot so the
whole cast reads as one game.  They are deliberately tiny next to the
protagonist -- a knight is 16x24 against a 40x48 foot -- because the scale
gag only works if the kingdom looks helpless.
"""
import math
from nesart import Img, Mask, shade_mask

D, M, L = 1, 2, 3           # dark outline, mid tone, light accent


def canvas(w, h):
    return Mask(w, h)


def compose(*layers):
    """layers: (mask, dark, mid, light, erode, outline) drawn back to front.
    Thin parts (weapon shafts, spokes) pass outline=False, otherwise erosion
    turns them entirely into rim and they vanish."""
    w = layers[0][0].w
    h = layers[0][0].h
    img = Img(w, h)
    for spec in layers:
        m = spec[0]
        dk = spec[1] if len(spec) > 1 else D
        md = spec[2] if len(spec) > 2 else M
        lt = spec[3] if len(spec) > 3 else L
        er = spec[4] if len(spec) > 4 else 2
        ol = spec[5] if len(spec) > 5 else True
        si = shade_mask(m, dk, md, lt, -1, -1, er, outline=ol)
        img.blit(si, 0, 0)
    return img


def dots(img, pts, c):
    for x, y in pts:
        img.put(x, y, c)


# ---------------------------------------------------------------------------
def human(w=16, h=24, *, helmet="none", weapon="none", stride=0, arm=0,
          cloak=False, shield=False, plume=False, crouch=0):
    """A small human figure.

    Parts are composed as separate shaded layers so each keeps its own dark
    rim -- at 16x24 that separation is the only thing that makes a helmet
    read as a helmet and a spear read as a spear.
    """
    cx = w // 2
    ground = h - 1
    hipy = ground - 8 + crouch
    heady = hipy - 10

    legs = canvas(w, h)
    for i, dx in enumerate((-2, 2)):
        sw = stride if i == 0 else -stride
        legs.poly([(cx + dx - 1, hipy - 1), (cx + dx + 1, hipy - 1),
                   (cx + dx + 1 + sw, ground - 1), (cx + dx - 1 + sw, ground - 1)])
        legs.rect(cx + dx - 2 + sw, ground - 1, cx + dx + 1 + sw, ground)

    torso = canvas(w, h)
    if cloak:
        torso.poly([(cx - 5, hipy + 2), (cx + 5, hipy + 2),
                    (cx + 3, heady + 3), (cx - 3, heady + 3)])
    else:
        torso.poly([(cx - 3, hipy + 1), (cx + 3, hipy + 1),
                    (cx + 4, heady + 4), (cx - 4, heady + 4)])

    head = canvas(w, h)
    head.ellipse(cx, heady, 2.8, 3.0)
    hat = canvas(w, h)
    if helmet == "conical":
        hat.poly([(cx - 4, heady + 1), (cx + 4, heady + 1), (cx, heady - 6)])
    elif helmet == "flat":
        hat.rect(cx - 4, heady - 4, cx + 4, heady)
    elif helmet == "great":
        hat.rect(cx - 4, heady - 4, cx + 4, heady + 3)
    elif helmet == "hood":
        hat.ellipse(cx - 1, heady - 1, 4.2, 4.4)
    elif helmet == "mitre":
        hat.poly([(cx - 3, heady + 1), (cx + 3, heady + 1), (cx, heady - 9)])
    elif helmet == "cap":
        hat.rect(cx - 3, heady - 4, cx + 3, heady - 1)
        hat.rect(cx - 4, heady - 2, cx + 1, heady - 1)
    if plume:
        for k in range(6):
            hat.put(cx - 1 + (k % 2), heady - 6 - k)

    sh = canvas(w, h)
    ay = hipy - 5 + arm
    if shield:
        sh.rect(cx - 8, ay - 5, cx - 4, ay + 5)

    wep = canvas(w, h)
    tip = canvas(w, h)
    if weapon == "spear":
        wep.rect(cx, ay - 1, cx + 8, ay)
        tip.poly([(cx + 7, ay - 3), (w - 1, ay), (cx + 7, ay + 3)])
    elif weapon == "pitchfork":
        wep.rect(cx, ay - 1, cx + 6, ay)
        tip.rect(cx + 6, ay - 3, cx + 7, ay + 3)
        for k in (-3, 0, 3):
            tip.rect(cx + 7, ay + k, cx + 9, ay + k)
    elif weapon == "bow":
        for a in range(-10, 11):
            yy = ay + a // 2
            xx = cx + 5 + int(2.4 * math.cos(a * 0.15))
            wep.put(xx, yy)
            wep.put(xx + 1, yy)
        tip.rect(cx + 4, ay - 5, cx + 4, ay + 5)
        wep.rect(cx, ay - 1, cx + 4, ay)
    elif weapon == "sword":
        wep.rect(cx + 2, ay - 9, cx + 3, ay + 1)
        tip.rect(cx, ay - 2, cx + 5, ay - 1)
        wep.rect(cx, ay - 1, cx + 4, ay)
    elif weapon == "staff":
        wep.rect(cx + 4, ay - 8, cx + 5, ay + 6)
        wep.rect(cx, ay - 1, cx + 5, ay)
        tip.ellipse(cx + 4.5, ay - 10, 2.6, 2.6)
    elif weapon == "hammer":
        wep.rect(cx + 3, ay - 8, cx + 4, ay + 2)
        tip.rect(cx + 1, ay - 12, cx + 8, ay - 7)
        wep.rect(cx, ay - 1, cx + 4, ay)
    elif weapon == "bell":
        wep.poly([(cx + 3, ay - 7), (cx + 8, ay - 7), (cx + 9, ay + 1),
                  (cx + 2, ay + 1)])
        tip.rect(cx + 4, ay + 1, cx + 7, ay + 2)
        wep.rect(cx, ay - 2, cx + 4, ay - 1)
    elif weapon == "trap":
        wep.rect(cx + 3, ay, cx + 8, ay + 2)
        for k in range(cx + 3, cx + 9, 2):
            tip.rect(k, ay - 2, k, ay - 1)
        wep.rect(cx, ay - 1, cx + 4, ay)
    elif weapon == "arms":
        wep.poly([(cx - 3, ay), (cx - 7, ay - 7), (cx - 5, ay - 7), (cx - 1, ay)])
        wep.poly([(cx + 3, ay), (cx + 7, ay - 7), (cx + 5, ay - 7), (cx + 1, ay)])

    img = compose(
        (sh, D, M, L, 2),
        (legs, D, M, M, 3),
        (torso, D, M, L, 4),
        (head, D, M, L, 2),
        (hat, D, M, L, 2),
        (wep, D, L, L, 1, False),
        (tip, D, L, L, 1, False),
    )
    # a dark rim under the weapon keeps it off the body silhouette
    for y in range(h):
        for x in range(w):
            if wep.m[y][x] or tip.m[y][x]:
                if not (wep.get(x, y + 1) or tip.get(x, y + 1)):
                    if y + 1 < h and img.px[y + 1][x]:
                        img.px[y + 1][x] = D
    return img


# ---------------------------------------------------------------------------
def beetle(frame=0):
    w, h = 16, 14
    b = canvas(w, h)
    b.ellipse(8, 8, 6.5, 4.5)
    b.ellipse(8, 6, 5.5, 3.5)
    legs = canvas(w, h)
    for i, x in enumerate((3, 8, 13)):
        d = 1 if ((i + frame) & 1) else -1
        legs.rect(x - 1, 11, x, 13)
        legs.rect(x - 1 + d, 12, x + d, 13)
    img = compose((legs, D, M, M, 1), (b, D, M, L, 3))
    for x in range(4, 13, 3):
        img.put(x, 5, D)
        img.put(x, 6, L)
    return img


def crow(frame=0):
    w, h = 16, 14
    b = canvas(w, h)
    b.ellipse(8, 8, 4.5, 3.0)
    b.poly([(11, 7), (15, 8), (11, 9)])
    wing = canvas(w, h)
    if frame == 0:
        wing.poly([(6, 6), (2, 1), (0, 5), (5, 9)])
        wing.poly([(9, 6), (13, 1), (15, 5), (10, 9)])
    else:
        wing.poly([(6, 8), (1, 11), (3, 13), (7, 11)])
        wing.poly([(9, 8), (14, 11), (12, 13), (8, 11)])
    img = compose((wing, D, M, L, 2), (b, D, M, L, 2))
    img.put(11, 7, L)
    return img


def gargoyle(frame=0):
    w, h = 24, 22
    b = canvas(w, h)
    b.ellipse(12, 13, 4.5, 5.0)
    b.ellipse(12, 6, 3.2, 3.2)
    b.poly([(9, 4), (10, 0), (11, 4)])
    b.poly([(13, 4), (14, 0), (15, 4)])
    b.rect(9, 18, 15, 21)
    wing = canvas(w, h)
    if frame == 0:
        wing.poly([(8, 10), (0, 3), (1, 12), (8, 15)])
        wing.poly([(16, 10), (23, 3), (22, 12), (16, 15)])
    else:
        wing.poly([(8, 11), (2, 15), (4, 19), (9, 16)])
        wing.poly([(16, 11), (21, 15), (19, 19), (15, 16)])
    img = compose((wing, D, M, M, 2), (b, D, M, L, 3))
    dots(img, [(10, 6), (14, 6)], L)
    return img


def chicken(frame=0):
    w, h = 12, 12
    b = canvas(w, h)
    b.ellipse(6, 7, 3.6, 3.2)
    b.ellipse(4, 3, 2.2, 2.2)
    b.poly([(2, 3), (0, 4), (2, 5)])
    b.rect(5, 10, 6, 11)
    b.rect(8, 10, 9, 11)
    if frame:
        b.rect(5, 9, 6, 11)
    img = compose((b, D, M, L, 2))
    dots(img, [(4, 1), (5, 0)], L)
    return img


def drone(frame=0):
    w, h = 16, 14
    b = canvas(w, h)
    b.ellipse(8, 8, 4.5, 3.5)
    b.rect(2, 4, 14, 5)
    b.rect(7, 2, 9, 5)
    rot = canvas(w, h)
    if frame == 0:
        rot.rect(0, 3, 15, 3)
    else:
        rot.rect(5, 3, 11, 3)
        rot.rect(6, 2, 10, 2)
    img = compose((rot, D, L, L, 1), (b, D, M, L, 2))
    dots(img, [(6, 8), (10, 8)], L)
    img.put(8, 11, D)
    return img


def clamp(frame=0):
    w, h = 24, 14
    b = canvas(w, h)
    b.rect(2, 9, 21, 13)
    open_ = 4 if frame == 0 else 1
    b.poly([(4, 9), (9, 9), (7, 9 - open_ * 2), (3, 9 - open_)])
    b.poly([(19, 9), (14, 9), (16, 9 - open_ * 2), (20, 9 - open_)])
    img = compose((b, D, M, L, 2))
    for x in range(4, 21, 3):
        img.put(x, 9, L)
    return img


def crusher(frame=0):
    w, h = 24, 32
    b = canvas(w, h)
    b.rect(2, 0, 21, 4)
    b.rect(10, 4, 13, 12 + frame * 8)
    b.rect(4, 12 + frame * 8, 19, 20 + frame * 8)
    img = compose((b, D, M, L, 2))
    for x in range(5, 19, 3):
        img.put(x, 19 + frame * 8, D)
    return img


def ballista(frame=0):
    w, h = 32, 24
    b = canvas(w, h)
    b.rect(2, 16, 29, 21)
    b.poly([(4, 16), (12, 6), (16, 6), (8, 16)])
    b.rect(8, 5, 27, 7)
    if frame == 0:
        b.rect(20, 3, 22, 10)
        b.rect(22, 5, 30, 7)
    else:
        b.rect(10, 3, 12, 10)
        b.rect(12, 5, 24, 7)
    b.ellipse(7, 21, 3, 2.4)
    b.ellipse(24, 21, 3, 2.4)
    img = compose((b, D, M, L, 3))
    return img


def turret(frame=0):
    w, h = 16, 16
    b = canvas(w, h)
    b.ellipse(8, 10, 5.5, 4.5)
    b.rect(3, 14, 13, 15)
    for i in range(4):
        a = (i * 45 + frame * 20) * math.pi / 180
        b.poly([(8 + math.cos(a) * 4, 10 + math.sin(a) * 4),
                (8 + math.cos(a) * 8, 10 + math.sin(a) * 8),
                (8 + math.cos(a + 0.4) * 4, 10 + math.sin(a + 0.4) * 4)])
    img = compose((b, D, M, L, 2))
    return img


def lurker(frame=0):
    w, h = 20, 16
    b = canvas(w, h)
    lift = 0 if frame == 0 else 3
    b.ellipse(10, 12 - lift, 6.5, 4.5)
    b.poly([(4, 12 - lift), (2, 5 - lift), (5, 9 - lift)])
    b.poly([(16, 12 - lift), (18, 5 - lift), (15, 9 - lift)])
    b.rect(2, 13, 18, 15)
    img = compose((b, D, M, L, 2))
    dots(img, [(7, 10 - lift), (13, 10 - lift)], L)
    return img


# ---------------------------------------------------------------------------
def rock(size=12):
    b = canvas(size, size)
    b.poly([(1, size - 1), (2, size // 2), (size // 2, 1),
            (size - 2, size // 3), (size - 1, size - 1)])
    return compose((b, D, M, L, 2))


def barrel(w=14, h=16):
    img = Img(w, h)
    b = canvas(w, h)
    b.rect(1, 1, w - 2, h - 2)
    b.ellipse(w / 2.0, 1, w / 2.0 - 1, 1.6)
    b.ellipse(w / 2.0, h - 2, w / 2.0 - 1, 1.6)
    img = compose((b, D, M, L, 3))
    for y in (4, h - 5):
        for x in range(1, w - 1):
            if img.px[y][x]:
                img.px[y][x] = D
    return img


def cannonball(size=10):
    b = canvas(size, size)
    b.ellipse(size / 2.0, size / 2.0, size / 2.0 - 0.5, size / 2.0 - 0.5)
    return compose((b, D, M, L, 2))


def crate(w=14, h=14):
    b = canvas(w, h)
    b.rect(0, 0, w - 1, h - 1)
    img = compose((b, D, M, L, 4))
    for i in range(min(w, h)):
        img.put(i, i, D)
        img.put(w - 1 - i, i, D)
    return img


def bomb(size=12):
    b = canvas(size, size)
    b.ellipse(size / 2.0, size / 2.0 + 1, size / 2.0 - 1, size / 2.0 - 1.5)
    b.rect(size // 2 - 1, 1, size // 2, 3)
    img = compose((b, D, M, L, 2))
    img.put(size // 2 + 1, 0, L)
    return img


def arrow():
    img = Img(16, 8)
    for x in range(2, 13):
        img.put(x, 4, M)
    for x in range(12, 16):
        img.put(x, 4, L)
    img.put(13, 3, L)
    img.put(13, 5, L)
    img.put(2, 3, L)
    img.put(2, 5, L)
    for x in range(2, 14):
        img.put(x, 5, D)
    return img


def bolt(frame=0):
    b = canvas(10, 10)
    b.ellipse(5, 5, 3.4 - frame * 0.5, 3.4 - frame * 0.5)
    img = compose((b, D, L, L, 1))
    return img


def spit(frame=0):
    b = canvas(8, 8)
    b.ellipse(4, 4, 2.6, 2.2 + frame * 0.4)
    return compose((b, D, M, L, 1))


def health_pickup():
    """A rolled bandage: absurd, but the kingdom is fresh out of potions."""
    b = canvas(14, 14)
    b.ellipse(7, 7, 5.5, 5.0)
    img = compose((b, D, L, L, 3))
    for x in range(2, 12):
        img.put(x, 6, D)
        img.put(x, 9, D)
    for x in range(5, 10):
        img.put(x, 4, M)
    return img


def shoebox():
    b = canvas(20, 16)
    b.rect(1, 4, 18, 14)
    b.rect(0, 2, 19, 5)
    img = compose((b, D, M, L, 3))
    for x in range(2, 18):
        img.put(x, 5, D)
    for y in range(6, 14):
        img.put(9, y, D)
        img.put(10, y, L)
    return img


def life_pickup():
    b = canvas(12, 12)
    b.ellipse(6, 8, 4.5, 3.2)
    b.ellipse(3, 4, 2.4, 2.6)
    for i in range(4):
        b.ellipse(8.5 + i * 0.6, 4.5 + i * 1.4, 1.3 - i * 0.15, 1.2 - i * 0.12)
    return compose((b, D, M, L, 2))


def dust(frame=0):
    b = canvas(16, 12)
    r = 2 + frame
    b.ellipse(4, 9 - frame, r, r * 0.7)
    b.ellipse(12, 9 - frame, r, r * 0.7)
    b.ellipse(8, 10 - frame, r * 0.8, r * 0.6)
    return compose((b, D, L, L, 1))


def spark(frame=0):
    img = Img(8, 8)
    pts = [[(4, 1), (4, 6), (1, 4), (6, 4), (2, 2), (5, 5)],
           [(3, 2), (5, 5), (2, 5), (5, 2), (4, 0), (4, 7)],
           [(4, 3), (3, 4), (5, 4), (4, 5)]][frame]
    for x, y in pts:
        img.put(x, y, L)
        img.put(x, y + 1, M)
    return img


def splash(frame=0):
    b = canvas(16, 10)
    b.rect(0, 8, 15, 9)
    for i, x in enumerate((3, 8, 12)):
        hh = 3 + ((i + frame) % 3) * 2
        b.rect(x, 8 - hh, x + 1, 8)
    return compose((b, D, M, L, 1))


# ---------------------------------------------------------------------------
# Bosses.  Each is a composite of shaded masks; the kingdom's engineers keep
# building bigger machines and the silhouettes escalate with them.
# ---------------------------------------------------------------------------
def boss_ironboot(frame=0):
    """CAPTAIN IRONBOOT -- a knight who has had one boot enlarged for the
    express purpose of stepping on the Foot."""
    w, h = 32, 44
    body = canvas(w, h)
    plate = canvas(w, h)
    boot = canvas(w, h)
    wep = canvas(w, h)
    cx = 15
    lift = 6 if frame == 2 else 0
    # oversized right boot -- the reason he was given the command
    by = h - 1 - (lift if frame == 2 else 0)
    boot.rect(1, by - 8, 17, by)
    boot.ellipse(3, by - 6, 4.0, 6.0)
    boot.rect(4, by - 16, 12, by - 6)
    boot.ellipse(15, by - 4, 4.0, 4.0)
    # standing leg
    body.rect(18, h - 20, 23, h - 1)
    body.rect(16, h - 3, 26, h - 1)
    # torso
    body.poly([(cx - 6, h - 18), (cx + 9, h - 18), (cx + 8, 14), (cx - 5, 14)])
    plate.rect(cx - 4, 18, cx + 6, 26)
    # pauldrons
    body.ellipse(cx - 6, 16, 4.5, 3.2)
    body.ellipse(cx + 10, 16, 4.5, 3.2)
    # head
    body.ellipse(cx + 2, 8, 4.4, 4.6)
    plate.rect(cx - 1, 6, cx + 5, 8)
    for k in range(5):
        body.put(cx + 1 + (k % 2), 2 + k)
    # sword
    if frame == 1:
        wep.rect(cx + 12, 6, cx + 14, 30)
        wep.rect(cx + 9, 12, cx + 17, 14)
    else:
        wep.rect(cx + 11, 2, cx + 13, 24)
        wep.rect(cx + 8, 20, cx + 16, 22)
    img = compose((boot, D, M, L, 3), (body, D, M, L, 4),
                  (plate, D, L, L, 2), (wep, D, L, L, 1, False))
    return img


def boss_huntsman(frame=0):
    """THE ROYAL HUNTSMAN -- brought traps built for a beast with a body."""
    w, h = 32, 42
    body = canvas(w, h)
    cloak = canvas(w, h)
    wep = canvas(w, h)
    acc = canvas(w, h)
    cx = 14
    cloak.poly([(cx - 10, h - 1), (cx + 10, h - 1), (cx + 7, 12), (cx - 7, 12)])
    body.rect(cx - 3, h - 16, cx + 1, h - 1)
    body.rect(cx + 4, h - 16, cx + 8, h - 1)
    body.poly([(cx - 5, h - 14), (cx + 9, h - 14), (cx + 7, 12), (cx - 4, 12)])
    body.ellipse(cx + 2, 8, 4.6, 4.8)
    acc.poly([(cx - 3, 8), (cx + 8, 6), (cx + 2, 1)])
    if frame == 0:
        wep.rect(cx + 6, 14, cx + 22, 16)
        wep.rect(cx + 18, 8, cx + 20, 24)
        acc.rect(cx + 20, 12, cx + 22, 18)
    elif frame == 1:
        wep.rect(cx + 6, 10, cx + 20, 12)
        wep.rect(cx + 16, 4, cx + 18, 20)
    else:
        for k in range(6):
            wep.rect(cx + 6 + k * 3, 20 + (k % 2) * 3, cx + 7 + k * 3, 26 + (k % 2) * 3)
    img = compose((cloak, D, M, M, 4), (body, D, M, L, 3),
                  (acc, D, L, L, 2), (wep, D, L, L, 1, False))
    return img


def boss_warboot(frame=0):
    """THE WAR BOOT -- the Royal Cobbler's masterpiece, piloted from the cuff."""
    w, h = 48, 48
    hull = canvas(w, h)
    sole = canvas(w, h)
    acc = canvas(w, h)
    pilot = canvas(w, h)
    lift = (0, 3, 7)[frame]
    base = h - 4 - lift
    # sole slab with a heel block and a toe
    sole.rect(3, base - 5, 45, base)
    sole.rect(3, base - 11, 12, base)
    sole.ellipse(41, base - 6, 5.0, 5.5)
    # boot body: instep sweeping up to a tall cuff at the back
    hull.poly([(6, base - 8), (14, base - 26), (30, base - 22),
               (42, base - 12), (44, base - 6), (6, base - 6)])
    hull.rect(8, base - 40, 22, base - 20)
    hull.ellipse(15, base - 40, 7.5, 4.0)
    # laces and plating
    for i in range(5):
        acc.rect(10, base - 38 + i * 4, 20, base - 37 + i * 4)
    for i in range(4):
        acc.rect(24 + i * 5, base - 20 + i, 26 + i * 5, base - 18 + i)
    # the Royal Cobbler, riding in the cuff
    pilot.rect(12, base - 50, 18, base - 42)
    pilot.ellipse(15, base - 53, 3.2, 3.4)
    pilot.rect(18, base - 49, 26, base - 47)
    img = compose((sole, D, D, M, 3), (hull, D, M, L, 5),
                  (acc, D, L, L, 1, False), (pilot, D, M, L, 2))
    return img


def boss_troll(frame=0):
    """THE MARSH TROLL -- roughly the Foot's own size, and furious about it."""
    w, h = 40, 42
    body = canvas(w, h)
    arms = canvas(w, h)
    acc = canvas(w, h)
    cx = 20
    body.ellipse(cx, h - 14, 12.0, 11.0)
    body.ellipse(cx, 12, 8.0, 8.0)
    body.rect(cx - 10, h - 6, cx - 2, h - 1)
    body.rect(cx + 2, h - 6, cx + 10, h - 1)
    if frame == 0:
        arms.poly([(cx - 10, 16), (cx - 19, 24), (cx - 15, 30), (cx - 8, 22)])
        arms.poly([(cx + 10, 16), (cx + 19, 24), (cx + 15, 30), (cx + 8, 22)])
    else:
        arms.poly([(cx - 10, 16), (cx - 20, 8), (cx - 16, 3), (cx - 8, 12)])
        arms.poly([(cx + 10, 16), (cx + 20, 8), (cx + 16, 3), (cx + 8, 12)])
    acc.ellipse(cx - 4, 10, 1.8, 1.8)
    acc.ellipse(cx + 4, 10, 1.8, 1.8)
    for k in range(4):
        acc.rect(cx - 6 + k * 4, 16, cx - 5 + k * 4, 18)
    img = compose((arms, D, M, M, 3), (body, D, M, L, 6), (acc, D, L, L, 1, False))
    return img


def boss_toebreaker(frame=0):
    """THE TOE BREAKER -- five hydraulic presses, one per toe."""
    w, h = 48, 48
    frame_m = canvas(w, h)
    press = canvas(w, h)
    acc = canvas(w, h)
    frame_m.rect(0, 0, w - 1, 8)
    frame_m.rect(0, 8, 5, h - 1)
    frame_m.rect(w - 6, 8, w - 1, h - 1)
    drop = [0, 10, 20][frame]
    for i in range(5):
        x = 8 + i * 7
        d = drop if i % 2 == 0 else drop // 2
        press.rect(x, 8, x + 4, 20 + d)
        press.rect(x - 1, 20 + d, x + 5, 26 + d)
    for i in range(6):
        acc.rect(3 + i * 8, 2, 6 + i * 8, 5)
    img = compose((frame_m, D, M, L, 3), (press, D, M, L, 2),
                  (acc, D, L, L, 1, False))
    return img


def boss_archbishop(frame=0):
    """THE ARCHBISHOP OF PODIATRY -- holy instruments, terrible convictions."""
    w, h = 34, 48
    robe = canvas(w, h)
    body = canvas(w, h)
    acc = canvas(w, h)
    wep = canvas(w, h)
    cx = 15
    robe.poly([(cx - 13, h - 1), (cx + 13, h - 1), (cx + 7, 20), (cx - 7, 20)])
    body.poly([(cx - 6, 26), (cx + 7, 26), (cx + 6, 14), (cx - 5, 14)])
    body.ellipse(cx + 1, 11, 4.0, 4.2)
    # mitre: tall but narrow, so the figure still reads as a man
    body.poly([(cx - 3, 9), (cx + 5, 9), (cx + 1, 1)])
    acc.poly([(cx - 1, 8), (cx + 3, 8), (cx + 1, 3)])
    # stole down the front and a hem band
    acc.rect(cx - 1, 16, cx + 2, 30)
    acc.rect(cx - 11, h - 6, cx + 11, h - 5)
    for y in range(24, h - 8, 7):
        acc.rect(cx - 8, y, cx + 8, y + 1)
    if frame == 0:
        body.poly([(cx + 5, 18), (cx + 13, 14), (cx + 14, 18), (cx + 6, 22)])
        wep.rect(cx + 12, 4, cx + 14, 32)
        wep.rect(cx + 7, 0, cx + 19, 7)
    elif frame == 1:
        body.poly([(cx + 5, 18), (cx + 15, 20), (cx + 15, 24), (cx + 6, 22)])
        wep.rect(cx + 12, 20, cx + 30, 22)
        wep.rect(cx + 26, 14, cx + 32, 28)
    else:
        body.poly([(cx + 5, 16), (cx + 12, 8), (cx + 14, 11), (cx + 7, 20)])
        wep.ellipse(cx + 15, 6, 5.0, 5.0)
        acc.ellipse(cx + 15, 6, 2.0, 2.0)
    img = compose((robe, D, M, L, 6), (body, D, M, L, 3),
                  (acc, D, L, L, 1, False), (wep, D, L, L, 2))
    return img


def boss_warmachine(frame=0):
    """THE KING'S WAR MACHINE -- a mechanical knight built at Foot scale."""
    w, h = 56, 56
    body = canvas(w, h)
    arms = canvas(w, h)
    acc = canvas(w, h)
    cx = 28
    body.rect(cx - 6, h - 22, cx - 1, h - 4)
    body.rect(cx + 2, h - 22, cx + 7, h - 4)
    body.rect(cx - 10, h - 5, cx - 1, h - 1)
    body.rect(cx + 2, h - 5, cx + 11, h - 1)
    body.poly([(cx - 13, h - 20), (cx + 13, h - 20), (cx + 11, 16), (cx - 11, 16)])
    body.ellipse(cx - 13, 20, 6.0, 5.0)
    body.ellipse(cx + 13, 20, 6.0, 5.0)
    body.rect(cx - 7, 4, cx + 7, 16)
    acc.rect(cx - 5, 8, cx + 5, 11)
    for k in range(7):
        acc.rect(cx - 5 + k * 2, 8, cx - 4 + k * 2, 11)
    for k in range(6):
        body.put(cx - 3 + (k % 2), 0 + k // 2)
    if frame == 0:
        arms.rect(cx - 22, 22, cx - 14, 40)
        arms.rect(cx + 14, 22, cx + 22, 40)
        acc.rect(cx - 24, 38, cx - 12, 46)
    elif frame == 1:
        arms.rect(cx - 26, 18, cx - 14, 26)
        arms.rect(cx + 14, 22, cx + 22, 40)
        acc.ellipse(cx - 26, 22, 5.0, 5.0)
    else:
        arms.rect(cx - 22, 22, cx - 14, 40)
        arms.rect(cx + 14, 10, cx + 26, 20)
        acc.ellipse(cx + 26, 15, 5.0, 5.0)
    for y in range(20, h - 22, 6):
        acc.rect(cx - 9, y, cx + 9, y + 1)
    img = compose((arms, D, M, L, 3), (body, D, M, L, 6),
                  (acc, D, L, L, 1, False))
    return img

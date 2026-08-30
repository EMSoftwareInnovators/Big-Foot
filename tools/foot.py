#!/usr/bin/env python3
"""
BIG FOOT -- the protagonist.

An enormous disembodied right foot: heel, arch, ball, five toes and a short
ankle stump that simply ends.  No face, no eyes, no body.

The foot is modelled once in a local 2x-resolution space out of ellipses and
polygons, then each animation frame applies an affine transform (heel lift,
toe lift, squash, lean) plus per-toe rotation.  Shading is applied *after*
the transform so outlines always follow the final silhouette.
"""
import math
from nesart import Img, Mask, shade_mask

S = 2                       # supersampling factor
MODEL_W, MODEL_H = 32, 40   # the foot model's own coordinate space
MARGIN_X, MARGIN_Y = 4, 4   # slack so rotated / thrust poses do not clip
CW, CH = MODEL_W + 8, MODEL_H + 8       # 40 x 48 output canvas
LW, LH = MODEL_W * S, MODEL_H * S       # local (supersampled) canvas

# Origin used by the engine: centre of the collision box, one pixel below the
# sole.  Metasprite offsets are relative to this point.
ORIGIN_X = 16 + MARGIN_X
ORIGIN_Y = 39 + MARGIN_Y

GROUND = 38.0               # sole rests here in canvas coords
PIVOT_BALL = (19.0, 33.0)   # rotation centre when the heel lifts
PIVOT_HEEL = (7.0, 33.0)    # rotation centre when the toes lift

# ---------------------------------------------------------------------------
# Local-space model (canvas coordinates; scaled by S when rasterised)
# ---------------------------------------------------------------------------

def _body_mask():
    m = Mask(LW, LH)
    # heel -- a heavy rounded mass at the back
    m.ellipse(7.2 * S, 31.4 * S, 6.8 * S, 6.8 * S)
    # ball of the foot
    m.ellipse(17.4 * S, 33.0 * S, 7.4 * S, 5.2 * S)
    # bridge between them; the instep slopes down toward the toes
    m.poly([(3.6 * S, 30.0 * S), (8.0 * S, 24.4 * S), (13.5 * S, 26.0 * S),
            (19.0 * S, 28.6 * S), (22.8 * S, 32.6 * S), (22.0 * S, 37.2 * S),
            (4.5 * S, 37.2 * S)])
    # ankle stump
    m.poly([(6.2 * S, 26.0 * S), (5.8 * S, 7.6 * S), (14.6 * S, 7.6 * S),
            (15.0 * S, 27.0 * S)])
    m.ellipse(10.2 * S, 7.8 * S, 4.4 * S, 2.4 * S)     # flat cut top
    m.ellipse(10.4 * S, 21.5 * S, 5.4 * S, 6.2 * S)    # ankle joint
    # carve the arch out of the sole
    cut = Mask(LW, LH)
    cut.ellipse(13.0 * S, 45.6 * S, 6.2 * S, 10.2 * S)
    m.subtract(cut)
    # flatten anything below the ground line
    below = Mask(LW, LH)
    below.rect(0, GROUND * S, LW - 1, LH - 1)
    m.subtract(below)
    return m


# toe: (cx, cy, rx, ry, pivot_x, pivot_y)  -- pivot is the toe's knuckle
TOES = [
    (27.4, 34.8, 4.2, 3.6, 21.6, 34.6),     # big toe -- frontmost, on the floor
    (27.6, 31.0, 3.2, 2.9, 21.8, 32.0),
    (26.8, 28.2, 2.7, 2.5, 21.4, 29.8),
    (25.4, 26.2, 2.3, 2.1, 20.6, 28.2),
    (23.8, 24.9, 1.9, 1.8, 19.8, 26.8),
]


def _toe_mask(i, curl=0.0, spread=0.0):
    """One toe as its own mask so it keeps a separating outline.
    curl > 0 curls the toe down toward the sole; < 0 flexes it up."""
    cx, cy, rx, ry, px, py = TOES[i]
    # rotate the toe centre around its knuckle
    a = curl * (0.55 + 0.12 * i)
    ca, sa = math.cos(a), math.sin(a)
    dx, dy = cx - px, cy - py
    nx = px + dx * ca - dy * sa
    ny = py + dx * sa + dy * ca
    ny -= spread * (4 - i) * 0.5
    m = Mask(LW, LH)
    m.ellipse(nx * S, ny * S, rx * S, ry * S)
    # a short root connecting the toe to the foot so it never floats
    rx0 = px
    ry0 = py
    m.poly([(rx0 * S, (ry0 - ry * 0.85) * S), (rx0 * S, (ry0 + ry * 0.85) * S),
            (nx * S, (ny + ry * 0.9) * S), (nx * S, (ny - ry * 0.9) * S)])
    return m


# ---------------------------------------------------------------------------
def _affine(angle, pivot, squash=1.0, stretch=1.0, lean=0.0, offset=(0, 0)):
    """Return the inverse transform (dest -> local) as a callable."""
    ca, sa = math.cos(angle), math.sin(angle)
    px, py = pivot
    ox, oy = offset

    def fwd(x, y):
        x = px + (x - px) * stretch
        y = py + (y - py) * squash
        x = x + lean * (py - y)
        dx, dy = x - px, y - py
        return (px + dx * ca - dy * sa + ox, py + dx * sa + dy * ca + oy)

    # numeric inverse of the 2x2 part
    x0, y0 = fwd(0.0, 0.0)
    x1, y1 = fwd(1.0, 0.0)
    x2, y2 = fwd(0.0, 1.0)
    a, b = x1 - x0, x2 - x0
    c, d = y1 - y0, y2 - y0
    det = a * d - b * c
    if abs(det) < 1e-9:
        det = 1e-9
    ia, ib = d / det, -b / det
    ic, idd = -c / det, a / det

    def inv(x, y):
        ux, uy = x - x0, y - y0
        return (ia * ux + ib * uy, ic * ux + idd * uy)

    return inv


def _sample(mask, inv):
    """Resample a local-space mask through `inv` into final canvas size."""
    out = Mask(CW, CH)
    for y in range(CH):
        for x in range(CW):
            hits = 0
            for sy in (0.25, 0.75):
                for sx in (0.25, 0.75):
                    u, v = inv(x - MARGIN_X + sx, y - MARGIN_Y + sy)
                    if mask.get(int(u * S), int(v * S)):
                        hits += 1
            if hits >= 2:
                out.m[y][x] = 1
    return out


# ---------------------------------------------------------------------------
class Pose(object):
    """One animation frame's worth of parameters."""

    def __init__(self, heel=0.0, toe=0.0, squash=1.0, stretch=1.0, lean=0.0,
                 curl=0.0, spread=0.0, dx=0, dy=0, angle=None, pivot=None,
                 toe_curls=None, roll=0.0):
        self.heel = heel            # radians, positive lifts the heel
        self.toe = toe              # radians, positive lifts the toes
        self.squash = squash
        self.stretch = stretch
        self.lean = lean
        self.curl = curl
        self.spread = spread
        self.dx = dx
        self.dy = dy
        self.angle = angle
        self.pivot = pivot
        self.toe_curls = toe_curls
        self.roll = roll

    def transform(self):
        if self.angle is not None:
            ang, piv = self.angle, (self.pivot or PIVOT_BALL)
        elif self.heel:
            ang, piv = -self.heel, PIVOT_BALL
        elif self.toe:
            ang, piv = self.toe, PIVOT_HEEL
        else:
            ang, piv = 0.0, PIVOT_BALL
        return _affine(ang, piv, self.squash, self.stretch, self.lean,
                       (self.dx, self.dy))


# ---------------------------------------------------------------------------
def render_foot(pose, shoe=None):
    """Render one frame.  Returns a 32x40 Img with colours 0..3."""
    inv = pose.transform()
    body = _sample(_body_mask(), inv)

    toes = []
    for i in range(5):
        curl = pose.curl
        if pose.toe_curls:
            curl = pose.toe_curls[i]
        toes.append(_sample(_toe_mask(i, curl, pose.spread), inv))

    img = Img(CW, CH)
    bi = shade_mask(body, 1, 2, 3, -1, -2, 4)
    img.blit(bi, 0, 0)

    # Toes sit in front of the ball of the foot.  Drawing them back to front
    # keeps a dark separating rim between neighbours, but that rim is dropped
    # where a toe overlaps the foot itself so the big toe reads as attached.
    inner = body.erode(1)
    for i in range(4, -1, -1):
        ti = shade_mask(toes[i], 1, 2, 3, -1, -1, 2)
        for y in range(CH):
            for x in range(CW):
                c = ti.px[y][x]
                if not c:
                    continue
                if c == 1 and inner.m[y][x]:
                    continue
                img.px[y][x] = c

    _detail(img, body, toes, pose)
    if shoe:
        img = shoe(img, body, toes, pose)
    return img


def _detail(img, body, toes, pose):
    """Toenails, the severed ankle cut, the arch shadow and the sole line."""
    full = body.clone()
    for t in toes:
        full.union(t)

    # underside shading: the bottom three rows of solid pixels go to mid/dark
    for x in range(img.w):
        col = [y for y in range(img.h) if full.m[y][x]]
        if not col:
            continue
        bottom = col[-1]
        for y in range(max(col[0] + 2, bottom - 2), bottom):
            if img.px[y][x] == 3:
                img.px[y][x] = 2
        img.px[bottom][x] = 1

    # toenails: a pale plate with a dark rim on the outer face of each toe
    for i, t in enumerate(toes):
        bb = _mask_bbox(t)
        if not bb:
            continue
        x0, y0, x1, y1 = bb
        w, h = x1 - x0, y1 - y0
        if w < 4 or h < 4:
            continue
        if i >= 2:
            continue
        nw = 3 if i == 0 else 2
        nh = 3 if i == 0 else 2
        nx = x1 - nw - 1
        ny = y0 + 1
        for yy in range(ny, ny + nh):
            for xx in range(nx, nx + nw):
                if t.get(xx, yy):
                    img.put(xx, yy, 3)

    # the ankle stump ends in a flat cut: a dark rim with a mid-tone interior
    bb = _mask_bbox(body)
    if bb:
        x0, y0, x1, y1 = bb
        for y in range(y0, min(y0 + 3, y1)):
            for x in range(x0, x1 + 1):
                if body.m[y][x]:
                    if y == y0:
                        img.px[y][x] = 1
                    elif y == y0 + 1:
                        img.px[y][x] = 2
                    else:
                        img.px[y][x] = 2 if img.px[y][x] == 3 else img.px[y][x]

    # arch shadow: darken the notch under the middle of the foot
    for x in range(img.w):
        col = [y for y in range(img.h) if full.m[y][x]]
        if not col:
            continue
        bottom = col[-1]
        if bottom < GROUND + MARGIN_Y - 2:
            img.px[bottom][x] = 1
            if bottom - 1 > col[0]:
                img.px[bottom - 1][x] = 2


def _mask_bbox(m):
    x0, y0, x1, y1 = m.w, m.h, -1, -1
    for y in range(m.h):
        for x in range(m.w):
            if m.m[y][x]:
                x0 = min(x0, x); y0 = min(y0, y)
                x1 = max(x1, x); y1 = max(y1, y)
    if x1 < 0:
        return None
    return (x0, y0, x1, y1)

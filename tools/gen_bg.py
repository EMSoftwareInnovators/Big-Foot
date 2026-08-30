#!/usr/bin/env python3
"""Background tilesets: eight themed metatile sets plus the shared HUD/font
bank, packed into MMC3 1 KiB CHR banks.

Tile index layout inside the background pattern table ($1000-$1FFF):
    R2 -> $00..$3F   theme tiles (static)
    R3 -> $40..$7F   theme tiles (static)
    R4 -> $80..$BF   theme tiles (animated; three bank variants)
    R5 -> $C0..$FF   shared HUD, font and effects (never swapped)
"""
from nesart import Img, TileSet, asm_bytes
import texture as T
from texture import Rnd, mt

# collision classes, mirroring constants.inc
EMPTY, SOLID, PLATFORM, HAZARD, BREAK, WATER, ICE, MUD = 0, 1, 2, 3, 4, 5, 6, 7
SWITCH, DEATH, CLIMB, CONV_R, CONV_L, EXIT, CHECKPOINT, SECRET = 8, 9, 10, 11, 12, 13, 14, 15

# every theme must define these so one level compiler serves all stages
REQUIRED = ["SKY", "BGA", "BGB", "BGC", "BGD",
            "TOP1", "TOP2", "TOP3", "FILL1", "FILL2", "FILL3",
            "PLAT1", "PLAT2", "WALL1", "WALL2", "EDGEL", "EDGER",
            "SPIKE", "BREAK", "D1", "D2", "D3", "D4", "D5", "D6",
            "CHAINT", "WATERS", "WATERB", "SWITCHM", "CHECK", "EXITM"]


class Theme(object):
    def __init__(self, name, bg, pals):
        self.name = name
        self.bg = bg
        self.pals = pals            # four tuples of three NES colours
        self.tiles = {}             # name -> (img, pal, collision)
        self.anim = {}              # name -> ([img,img,img], pal, collision)

    def add(self, name, img, pal, col=EMPTY):
        self.tiles[name] = (img, pal, col)

    def addanim(self, name, imgs, pal, col=EMPTY):
        self.anim[name] = (imgs, pal, col)

    def check(self):
        missing = [n for n in REQUIRED if n not in self.tiles and n not in self.anim]
        if missing:
            raise RuntimeError("%s missing metatiles: %s" % (self.name, missing))


# ---------------------------------------------------------------------------
def _standard(th, seed, *, ground_pal, soil_pal, stone_pal, accent_pal,
              grass=True, top_kw=None, fill_kw=None, wall_fn=None,
              plat_fn=None, spike_pal=None):
    """The structural metatiles every stage needs, tuned per theme."""
    tk = top_kw or {}
    fk = fill_kw or {}
    if grass:
        th.add("TOP1", T.grass_cap(seed + 1, **tk), ground_pal, SOLID)
        th.add("TOP2", T.grass_cap(seed + 2, **tk), ground_pal, SOLID)
        tk3 = dict(tk)
        tk3.setdefault("depth", 6)
        th.add("TOP3", T.grass_cap(seed + 3, **tk3), ground_pal, SOLID)
    else:
        th.add("TOP1", T.bricks(seed + 1, **tk), ground_pal, SOLID)
        th.add("TOP2", T.bricks(seed + 2, **tk), ground_pal, SOLID)
        tk3 = dict(tk)
        tk3["damage"] = tk.get("damage", 0) + 2
        th.add("TOP3", T.bricks(seed + 3, **tk3), ground_pal, SOLID)
    th.add("FILL1", T.soil(seed + 4, **fk), soil_pal, SOLID)
    th.add("FILL2", T.soil(seed + 5, **fk), soil_pal, SOLID)
    th.add("FILL3", T.rubble(seed + 6), soil_pal, SOLID)
    wf = wall_fn or (lambda s: T.bricks(s, damage=1))
    th.add("WALL1", wf(seed + 7), stone_pal, SOLID)
    th.add("WALL2", wf(seed + 8), stone_pal, SOLID)
    pf = plat_fn or (lambda s: _plat(T.planks(s, horizontal=True, ph=6)))
    th.add("PLAT1", pf(seed + 9), stone_pal, PLATFORM)
    th.add("PLAT2", pf(seed + 10), stone_pal, PLATFORM)
    th.add("EDGEL", _edge(wf(seed + 11), left=True), stone_pal, SOLID)
    th.add("EDGER", _edge(wf(seed + 12), left=False), stone_pal, SOLID)
    th.add("SPIKE", T.spikes(seed + 13), spike_pal if spike_pal is not None else stone_pal, HAZARD)
    th.add("BREAK", _cracked(wf(seed + 14)), accent_pal, BREAK)
    th.add("SWITCHM", _switch(), accent_pal, SWITCH)
    th.add("CHECK", _flagstone(), accent_pal, CHECKPOINT)
    th.add("EXITM", _gate(), accent_pal, EXIT)
    th.add("CHAINT", T.chain(seed + 15), stone_pal, CLIMB)


def _plat(img):
    """Give a platform a lit top lip and a shadowed underside."""
    out = img.clone()
    for x in range(16):
        out.px[0][x] = 3
        out.px[1][x] = 3 if (x & 3) else 1
        out.px[14][x] = 1
        out.px[15][x] = 1
    for y in range(2, 14):
        out.px[y][0] = 1
        out.px[y][15] = 1
    return out


def _edge(img, left=True):
    out = img.clone()
    x = 0 if left else 15
    for y in range(16):
        out.px[y][x] = 1
        out.px[y][x + (1 if left else -1)] = 3 if (y & 1) else 1
    return out


def _cracked(img):
    out = img.clone()
    pts = [(3, 1), (4, 3), (5, 5), (4, 7), (6, 9), (7, 11), (6, 13)]
    for x, y in pts:
        out.px[y][x] = 1
        out.px[y][x + 1] = 1
    for x, y in [(10, 2), (11, 4), (10, 6), (12, 8)]:
        out.px[y][x] = 1
    for x in range(16):
        out.px[0][x] = 3 if (x & 1) else out.px[0][x]
    return out


def _switch():
    img = mt(0)
    for x in range(2, 14):
        img.px[13][x] = 1
        img.px[14][x] = 2
        img.px[15][x] = 1
    for x in range(4, 12):
        img.px[10][x] = 3
        img.px[11][x] = 2
        img.px[12][x] = 1
    img.px[9][7] = 3
    img.px[9][8] = 3
    return img


def _flagstone():
    img = mt(2)
    for x in range(16):
        img.px[0][x] = 3
        img.px[15][x] = 1
    for y in range(16):
        img.px[y][0] = 1
        img.px[y][15] = 1
    for y in range(3, 13):
        img.px[y][7] = 3
        img.px[y][8] = 3
    for y in range(3, 8):
        for x in range(9, 14):
            img.px[y][x] = 3 if (x + y) % 2 else 1
    return img


def _gate():
    img = mt(0)
    for y in range(2, 16):
        for x in range(3, 13):
            img.px[y][x] = 2
    for y in range(2, 16):
        img.px[y][3] = 3
        img.px[y][12] = 1
    for x in range(3, 13):
        img.px[2][x] = 3
    for y in range(4, 16, 3):
        for x in range(4, 12):
            img.px[y][x] = 1
    return img


def _silhouette(seed, shape, colour=1):
    """Distant background art drawn as a flat two-tone silhouette.
    "flat" is the body tile that stacks under any crest tile."""
    img = mt(0)
    r = Rnd(seed)
    if shape == "flat":
        for y in range(16):
            for x in range(16):
                img.px[y][x] = colour
        for x in range(0, 16, 5):
            for y in range(2, 14, 3):
                img.px[y][x] = colour + 1
    elif shape == "hillcrest":
        for x in range(16):
            h = 3 + (abs(8 - x) * 3) // 8 + r.rng(2)
            for y in range(h, 16):
                img.px[y][x] = colour
            img.px[h][x] = colour + 1
    elif shape == "peak":
        for x in range(16):
            h = 1 + abs(8 - x)
            for y in range(min(h, 15), 16):
                img.px[y][x] = colour
            img.px[min(h, 15)][x] = colour + 1
    elif shape == "canopy":
        for x in range(16):
            h = 4 + ((x * 5) % 7) // 2
            for y in range(h, 16):
                img.px[y][x] = colour
            img.px[h][x] = colour + 1
        for i in range(4):
            cx, cy = r.rng(14) + 1, r.rng(4) + 3
            for y in range(cy, cy + 3):
                for x in range(cx - 2, cx + 3):
                    if 0 <= x < 16 and 0 <= y < 16:
                        img.px[y][x] = colour
    elif shape == "battlecrest":
        for x in range(16):
            h = 6 if (x // 3) % 2 == 0 else 3
            for y in range(h, 16):
                img.px[y][x] = colour
            img.px[h][x] = colour + 1
    elif shape == "machinecrest":
        for x in range(16):
            h = [5, 5, 2, 2, 7, 7, 7, 4, 4, 9, 9, 3, 3, 3, 6, 6][x]
            for y in range(h, 16):
                img.px[y][x] = colour
            img.px[h][x] = colour + 1
    elif shape == "archcrest":
        for x in range(16):
            d = abs(8 - x)
            h = 2 + d * d // 12
            for y in range(h, 16):
                img.px[y][x] = colour
            img.px[h][x] = colour + 1
    elif shape == "village":
        for y in range(10, 16):
            for x in range(16):
                img.px[y][x] = colour
        for x in range(2, 7):
            for y in range(6, 10):
                img.px[y][x] = colour
        for x in range(2, 7):
            img.px[6][x] = colour + 1
        for x in range(9, 14):
            for y in range(7, 10):
                img.px[y][x] = colour
        img.px[7][9] = colour + 1
        img.px[7][13] = colour + 1
        img.px[5][4] = colour + 1
    elif shape == "trees":
        for y in range(12, 16):
            for x in range(16):
                img.px[y][x] = colour
        for i in range(3):
            cx = i * 6 + 3
            for y in range(4, 13):
                w = max(0, (y - 3) // 2)
                for x in range(cx - w, cx + w + 1):
                    if 0 <= x < 16:
                        img.px[y][x] = colour
            img.px[4][cx] = colour + 1
    elif shape == "deadwood":
        for y in range(12, 16):
            for x in range(16):
                img.px[y][x] = colour
        for i, cx in enumerate((3, 9, 14)):
            for y in range(4 + i, 13):
                img.px[y][cx] = colour
                if cx + 1 < 16:
                    img.px[y][cx + 1] = colour
            for dx, dy in ((-2, 6), (2, 8), (-3, 9)):
                if 0 <= cx + dx < 16:
                    img.px[dy + i][cx + dx] = colour
    elif shape == "towerfar":
        for y in range(12, 16):
            for x in range(16):
                img.px[y][x] = colour
        for y in range(3, 13):
            for x in range(5, 12):
                img.px[y][x] = colour
        for x in range(4, 13):
            img.px[3][x] = colour + 1
        for x in (5, 7, 9, 11):
            img.px[2][x] = colour
        img.px[7][8] = colour + 1
    elif shape == "ruinfar":
        for y in range(11, 16):
            for x in range(16):
                img.px[y][x] = colour
        for y in range(5, 12):
            for x in range(2, 7):
                img.px[y][x] = colour
        for x in range(2, 7):
            img.px[5][x] = colour + 1
        for y in range(8, 12):
            for x in range(10, 14):
                img.px[y][x] = colour
        img.px[8][10] = colour + 1
        img.px[8][12] = colour + 1
    elif shape == "statuefar":
        for y in range(13, 16):
            for x in range(16):
                img.px[y][x] = colour
        for y in range(2, 14):
            for x in range(6, 11):
                img.px[y][x] = colour
        for y in range(4, 9):
            for x in (4, 5, 11, 12):
                img.px[y][x] = colour
        for x in range(6, 11):
            img.px[2][x] = colour + 1
        img.px[5][7] = colour + 1
        img.px[5][9] = colour + 1
    elif shape == "clouddark":
        for i in range(4):
            cx, cy = r.rng(14) + 1, r.rng(8) + 4
            rr = r.rng(3) + 2
            for y in range(cy - rr, cy + rr + 1):
                for x in range(cx - rr, cx + rr + 1):
                    if 0 <= x < 16 and 0 <= y < 16:
                        if (x - cx) ** 2 + (y - cy) ** 2 <= rr * rr:
                            img.px[y][x] = colour + (1 if y < cy else 0)
    elif shape == "arch":
        for y in range(16):
            for x in range(16):
                d = (x - 8) ** 2 + (y - 14) ** 2
                if d > 36 and d < 150:
                    img.px[y][x] = colour
    return img


def _torch(phase):
    img = mt(0)
    for y in range(9, 16):
        for x in range(6, 10):
            img.px[y][x] = 1
        img.px[y][6] = 2
    flame = [(7, 8), (8, 8), (7, 7), (8, 7), (7, 6), (8, 6), (6, 7), (9, 7)]
    for x, y in flame:
        img.px[y][x] = 3
    tips = [[(7, 4), (8, 5)], [(8, 4), (7, 5)], [(7, 5), (8, 3)]][phase]
    for x, y in tips:
        img.px[y][x] = 3
    for x, y in [(6, 8), (9, 8), (6, 6), (9, 6)]:
        img.px[y][x] = 2
    return img


# ---------------------------------------------------------------------------
def theme_village():
    th = Theme("village", 0x21, [(0x09, 0x2A, 0x38),   # 0 grass
                                 (0x07, 0x17, 0x28),   # 1 soil, thatch, roofs
                                 (0x0C, 0x11, 0x21),   # 2 distance, clouds
                                 (0x0F, 0x10, 0x30)])  # 3 stone + HUD
    _standard(th, 100, ground_pal=0, soil_pal=1, stone_pal=2, accent_pal=3,
              grass=True)
    th.add("SKY", mt(0), 0, EMPTY)
    th.add("BGA", T.cloud(101), 2, EMPTY)
    th.add("BGB", _silhouette(102, "hillcrest"), 2, EMPTY)
    th.add("BGC", _silhouette(103, "flat"), 2, EMPTY)
    th.add("BGD", _silhouette(104, "village"), 2, EMPTY)
    th.add("D1", T.fence(105), 1, EMPTY)
    th.add("D2", _silhouette(106, "roof"), 3, EMPTY)
    th.add("D3", T.planks(107, horizontal=False), 1, SOLID)
    th.add("D4", _haystack(), 1, SOLID)
    th.add("D5", _tree_trunk(), 1, EMPTY)
    th.add("D6", _bush(), 0, EMPTY)
    th.add("WATERS", T.water(108, surface=True), 2, WATER)
    th.add("WATERB", T.water(109), 2, WATER)
    th.addanim("TORCH", [_torch(0), _torch(1), _torch(2)], 3, EMPTY)
    return th


def _haystack():
    img = mt(2)
    r = Rnd(55)
    for y in range(16):
        for x in range(16):
            if y < 3 - abs(8 - x) // 4:
                img.px[y][x] = 0
    for _ in range(30):
        x, y = r.rng(15), r.rng(14) + 2
        for k in range(3):
            if x + k < 16:
                img.px[y][x + k] = 3 if r.chance(1, 2) else 1
    for x in range(16):
        img.px[15][x] = 1
    return img


def _tree_trunk():
    img = mt(0)
    for y in range(16):
        for x in range(5, 12):
            img.px[y][x] = 2
        img.px[y][5] = 1
        img.px[y][11] = 1
        if y % 3 == 0:
            img.px[y][7] = 1
            img.px[y][9] = 3
    return img


def _bush():
    img = T.foliage(77, density=4)
    for y in range(16):
        for x in range(16):
            if y < 4 or (y > 13):
                img.px[y][x] = 0
    return img


def theme_forest():
    th = Theme("forest", 0x0F, [(0x09, 0x1A, 0x2A),   # 0 leaves
                                (0x07, 0x17, 0x27),   # 1 bark, soil
                                (0x01, 0x0C, 0x1C),   # 2 depths, mist
                                (0x00, 0x10, 0x30)])  # 3 stone + HUD
    _standard(th, 200, ground_pal=0, soil_pal=1, stone_pal=2, accent_pal=1,
              grass=True, fill_kw={})
    th.add("SKY", mt(0), 0, EMPTY)
    th.add("BGA", _shaft(), 2, EMPTY)
    th.add("BGB", _silhouette(202, "canopy"), 2, EMPTY)
    th.add("BGC", _silhouette(2021, "flat"), 2, EMPTY)
    th.add("BGD", _silhouette(203, "trees"), 2, EMPTY)
    th.add("VINE", _vines(), 0, EMPTY)
    th.add("D1", _tree_trunk(), 1, EMPTY)
    th.add("D2", T.foliage(203, density=6), 0, SOLID)
    th.add("D3", _roots(), 1, SOLID)
    th.add("D4", _mushroom(), 3, EMPTY)
    th.add("D5", _log(), 1, PLATFORM)
    th.add("D6", _bush(), 0, EMPTY)
    th.addanim("WATERS", [T.water(204, phase=p, surface=True) for p in range(3)], 3, WATER)
    th.addanim("WATERB", [T.water(205, phase=p) for p in range(3)], 3, WATER)
    th.addanim("FALL", [T.water(206, phase=p) for p in range(3)], 3, EMPTY)
    return th


def _vines():
    img = mt(0)
    r = Rnd(88)
    for i in range(3):
        x = i * 5 + 2
        for y in range(16):
            xx = x + (1 if (y // 3) % 2 else 0)
            if xx < 16:
                img.px[y][xx] = 2
                if r.chance(1, 3) and xx + 1 < 16:
                    img.px[y][xx + 1] = 3
    return img


def _shaft():
    img = mt(0)
    for y in range(16):
        for x in range(16):
            if (x + y) % 8 < 2:
                img.px[y][x] = 3
    return img


def _roots():
    img = T.soil(91, 2, 1, 3)
    for i in range(3):
        y = i * 5 + 2
        for x in range(16):
            yy = y + (x // 4) % 2
            if yy < 16:
                img.px[yy][x] = 1
                if yy + 1 < 16:
                    img.px[yy + 1][x] = 3
    return img


def _mushroom():
    img = mt(0)
    for y in range(10, 16):
        for x in range(6, 10):
            img.px[y][x] = 2
    for y in range(6, 10):
        w = 6 - (y - 6)
        for x in range(8 - w, 8 + w):
            if 0 <= x < 16:
                img.px[y][x] = 3
    for x in range(4, 12):
        img.px[9][x] = 1
    img.px[7][6] = 1
    img.px[8][10] = 1
    return img


def _log():
    img = mt(0)
    for y in range(4, 12):
        for x in range(16):
            img.px[y][x] = 2
    for x in range(16):
        img.px[4][x] = 3
        img.px[11][x] = 1
    for y in range(5, 11):
        img.px[y][0] = 1
        img.px[y][15] = 1
    for y in range(6, 10):
        for x in range(1, 4):
            img.px[y][x] = 1
    return img


def theme_fortress():
    th = Theme("fortress", 0x0F, [(0x00, 0x10, 0x30),   # 0 cut stone
                                  (0x07, 0x17, 0x27),   # 1 timber
                                  (0x01, 0x11, 0x21),   # 2 distance, sky
                                  (0x06, 0x16, 0x37)])  # 3 banners, fire + HUD
    _standard(th, 300, ground_pal=0, soil_pal=0, stone_pal=0, accent_pal=3,
              grass=False, top_kw={"bw": 8, "bh": 4}, wall_fn=lambda s: T.bricks(s, bw=4, bh=4, damage=1))
    th.add("SKY", mt(0), 2, EMPTY)
    th.add("BGA", _silhouette(301, "clouddark"), 2, EMPTY)
    th.add("BGB", _silhouette(302, "battlecrest"), 2, EMPTY)
    th.add("BGC", _silhouette(3021, "flat"), 2, EMPTY)
    th.add("BGD", _silhouette(303, "towerfar"), 2, EMPTY)
    th.add("BACKWALL", T.bricks(3022, base=1, mortar=1, light=1), 2, EMPTY)
    th.add("SLIT", _arrowslit(), 2, EMPTY)
    th.add("D1", T.banner(304), 3, EMPTY)
    th.add("D2", _battlement(), 0, SOLID)
    th.add("D3", T.planks(305, horizontal=False), 1, SOLID)
    th.add("D4", _barrel(), 1, SOLID)
    th.add("D5", T.chain(306), 0, EMPTY)
    th.add("D6", _cannon(), 0, SOLID)
    th.add("WATERS", T.water(307, surface=True), 2, WATER)
    th.add("WATERB", T.water(308), 2, WATER)
    th.addanim("TORCH", [_torch(p) for p in range(3)], 3, EMPTY)
    th.addanim("OIL", [_oil(p) for p in range(3)], 3, HAZARD)
    return th


def _arrowslit():
    img = T.bricks(310, base=1, mortar=1, light=1)
    for y in range(3, 13):
        img.px[y][7] = 0
        img.px[y][8] = 0
    for x in range(6, 10):
        img.px[3][x] = 0
    return img


def _battlement():
    img = T.bricks(311, bw=8, bh=4)
    for x in range(16):
        if (x // 4) % 2 == 0:
            for y in range(0, 5):
                img.px[y][x] = 0
    return img


def _barrel():
    img = mt(0)
    for y in range(2, 16):
        for x in range(3, 13):
            img.px[y][x] = 2
    for y in range(2, 16):
        img.px[y][3] = 3
        img.px[y][12] = 1
    for x in range(3, 13):
        img.px[2][x] = 3
        img.px[15][x] = 1
    for y in (5, 6, 11, 12):
        for x in range(3, 13):
            img.px[y][x] = 1
    return img


def _cannon():
    img = mt(0)
    for y in range(6, 11):
        for x in range(16):
            img.px[y][x] = 2
    for x in range(16):
        img.px[6][x] = 3
        img.px[10][x] = 1
    for y in range(4, 13):
        for x in range(0, 4):
            img.px[y][x] = 2
        img.px[y][0] = 1
    for y in range(11, 16):
        for x in range(4, 10):
            img.px[y][x] = 1
    return img


def _oil(phase):
    img = mt(0)
    for y in range(16):
        for x in range(16):
            if (x + phase * 5 + y * 3) % 12 < 5:
                img.px[y][x] = 3
            elif (x + phase * 5 + y * 3) % 12 < 8:
                img.px[y][x] = 2
    for x in range(16):
        img.px[0][x] = 3
    return img


def theme_marsh():
    th = Theme("marsh", 0x0F, [(0x09, 0x19, 0x29),   # 0 sickly reeds
                               (0x07, 0x08, 0x18),   # 1 mud
                               (0x01, 0x0C, 0x1C),   # 2 fog, water
                               (0x03, 0x14, 0x30)])  # 3 witchlight + HUD
    _standard(th, 400, ground_pal=1, soil_pal=1, stone_pal=2, accent_pal=3,
              grass=True, top_kw={"top": 3, "blade": 3, "body": 2, "dark": 1})
    th.add("SKY", mt(0), 2, EMPTY)
    th.add("BGA", _fog(0), 2, EMPTY)
    th.add("BGB", _silhouette(401, "canopy"), 2, EMPTY)
    th.add("BGC", _silhouette(4011, "flat"), 2, EMPTY)
    th.add("BGD", _silhouette(402, "deadwood"), 2, EMPTY)
    th.add("D1", _reeds(), 0, EMPTY)
    th.add("D2", T.rubble(403), 2, SOLID)
    th.add("D3", _deadtree(), 1, SOLID)
    th.add("D4", T.soil(404, 2, 1, 3), 1, MUD)
    th.add("D5", _log(), 1, PLATFORM)
    th.add("D6", _fog(1), 2, EMPTY)
    th.addanim("WATERS", [T.water(405, phase=p, surface=True) for p in range(3)], 2, WATER)
    th.addanim("WATERB", [T.water(406, phase=p) for p in range(3)], 2, WATER)
    th.addanim("BUBBLE", [_bubbles(p) for p in range(3)], 2, WATER)
    return th


def _fog(k):
    img = mt(0)
    r = Rnd(410 + k)
    for _ in range(6):
        cx, cy = r.rng(16), r.rng(16)
        for y in range(cy - 2, cy + 3):
            for x in range(cx - 4, cx + 5):
                if 0 <= x < 16 and 0 <= y < 16 and r.chance(2, 3):
                    img.px[y][x] = 1
    return img


def _deadtree():
    img = mt(0)
    for y in range(16):
        for x in range(6, 10):
            img.px[y][x] = 2
        img.px[y][6] = 1
        img.px[y][9] = 1
    for i, (x, y) in enumerate([(4, 5), (3, 4), (11, 7), (12, 6), (2, 3), (13, 5)]):
        img.px[y][x] = 2
        img.px[y - 1][x] = 1
    return img


def _reeds():
    img = mt(0)
    r = Rnd(420)
    for i in range(6):
        x = r.rng(15)
        h = r.rng(8) + 6
        for y in range(16 - h, 16):
            xx = x + ((16 - y) // 5)
            if xx < 16:
                img.px[y][xx] = 2 if r.chance(2, 3) else 3
    return img


def _bubbles(phase):
    img = mt(0)
    r = Rnd(430)
    for i in range(5):
        x = r.rng(14) + 1
        y = (r.rng(14) + phase * 5) % 14 + 1
        img.px[y][x] = 3
        img.px[y][x + 1] = 3
        img.px[y + 1][x] = 3
        img.px[y + 1][x + 1] = 1
    return img


def theme_factory():
    th = Theme("factory", 0x0F, [(0x00, 0x10, 0x30),   # 0 steel
                                 (0x06, 0x16, 0x27),   # 1 rust, hot metal
                                 (0x01, 0x02, 0x11),   # 2 far machinery
                                 (0x07, 0x27, 0x37)])  # 3 furnace glow + HUD
    _standard(th, 500, ground_pal=0, soil_pal=0, stone_pal=0, accent_pal=1,
              grass=False, top_kw={"bw": 4, "bh": 4},
              wall_fn=lambda s: T.metal_plate(s),
              plat_fn=lambda s: _plat(T.metal_plate(s)))
    th.add("SKY", mt(0), 2, EMPTY)
    th.add("BGA", T.pipes(501), 2, EMPTY)
    th.add("BGB", _silhouette(502, "machinecrest"), 2, EMPTY)
    th.add("BGC", _silhouette(5021, "flat"), 2, EMPTY)
    th.add("BGD", _silhouette(503, "towerfar"), 2, EMPTY)
    th.add("BACKWALL", T.metal_plate(5022, base=1, dark=1, light=1), 2, EMPTY)
    th.add("GRID", _grid(), 2, EMPTY)
    th.add("D1", T.pipes(504), 0, SOLID)
    th.add("D2", _girder(), 0, SOLID)
    th.add("D3", _vent(), 0, EMPTY)
    th.add("D4", _crate(), 1, SOLID)
    th.add("D5", T.chain(505), 0, EMPTY)
    th.add("D6", _grid(), 0, PLATFORM)
    th.add("WATERS", T.water(506, surface=True), 3, WATER)
    th.add("WATERB", T.water(507), 3, WATER)
    th.addanim("GEAR", [T.gear(508, phase=p) for p in range(3)], 0, EMPTY)
    th.addanim("BELT", [_belt(p) for p in range(3)], 0, CONV_R)
    th.addanim("FURNACE", [_furnace(p) for p in range(3)], 3, HAZARD)
    return th


def _grid():
    img = mt(0)
    for y in range(16):
        for x in range(16):
            if x % 4 == 0 or y % 4 == 0:
                img.px[y][x] = 2
            if x % 4 == 1 and y % 4 == 1:
                img.px[y][x] = 1
    return img


def _girder():
    img = mt(0)
    for y in range(5, 11):
        for x in range(16):
            img.px[y][x] = 2
    for x in range(16):
        img.px[5][x] = 3
        img.px[10][x] = 1
    for x in range(2, 15, 4):
        img.px[7][x] = 1
        img.px[8][x] = 3
    for y in range(0, 16):
        for x in (0, 15):
            img.px[y][x] = 2 if 3 <= y <= 12 else 0
    return img


def _vent():
    img = T.metal_plate(520)
    for y in range(4, 13, 3):
        for x in range(3, 13):
            img.px[y][x] = 1
            img.px[y + 1][x] = 3
    return img


def _crate():
    img = T.planks(521, horizontal=True, ph=4)
    for x in range(16):
        img.px[0][x] = 3
        img.px[15][x] = 1
    for y in range(16):
        img.px[y][0] = 3
        img.px[y][15] = 1
    for k in range(16):
        img.px[k][k] = 1
        img.px[k][15 - k] = 1
    return img


def _belt(phase):
    img = mt(0)
    for y in range(4, 12):
        for x in range(16):
            img.px[y][x] = 2
    for x in range(16):
        img.px[4][x] = 3
        img.px[11][x] = 1
    for x in range(16):
        if (x + phase * 2) % 6 < 2:
            img.px[5][x] = 1
            img.px[10][x] = 3
    return img


def _furnace(phase):
    img = mt(1)
    r = Rnd(530 + phase)
    for y in range(16):
        for x in range(16):
            n = (x * 3 + y * 5 + phase * 7) % 16
            if n < 4:
                img.px[y][x] = 3
            elif n < 9:
                img.px[y][x] = 2
    for x in range(16):
        img.px[0][x] = 3 if r.chance(1, 2) else 2
    return img


def theme_cathedral():
    th = Theme("cathedral", 0x0F, [(0x00, 0x10, 0x30),   # 0 pale stone
                                   (0x02, 0x12, 0x22),   # 1 shadowed vaults
                                   (0x04, 0x14, 0x24),   # 2 stained glass
                                   (0x07, 0x28, 0x38)])  # 3 gold, candlelight + HUD
    _standard(th, 600, ground_pal=0, soil_pal=1, stone_pal=0, accent_pal=3,
              grass=False, top_kw={"bw": 8, "bh": 4},
              wall_fn=lambda s: T.bricks(s, bw=8, bh=8))
    th.add("SKY", mt(0), 1, EMPTY)
    th.add("BGA", T.arch_window(601), 2, EMPTY)
    th.add("BGB", _silhouette(602, "archcrest"), 1, EMPTY)
    th.add("BGC", _silhouette(6021, "flat"), 1, EMPTY)
    th.add("BGD", _column(), 1, EMPTY)
    th.add("BACKWALL", T.bricks(603, base=1, mortar=1, light=1), 1, EMPTY)
    th.add("D1", _column(), 0, SOLID)
    th.add("D2", T.arch_window(604), 2, EMPTY)
    th.add("D3", _pew(), 3, SOLID)
    th.add("D4", _bell(), 3, SOLID)
    th.add("D5", T.chain(605), 0, EMPTY)
    th.add("D6", _gargoyle(), 0, SOLID)
    th.add("WATERS", T.water(606, surface=True), 2, WATER)
    th.add("WATERB", T.water(607), 2, WATER)
    th.addanim("CANDLE", [_torch(p) for p in range(3)], 3, EMPTY)
    return th


def _column():
    img = mt(0)
    for y in range(16):
        for x in range(3, 13):
            img.px[y][x] = 2
        img.px[y][3] = 3
        img.px[y][12] = 1
        img.px[y][6] = 3
        img.px[y][9] = 1
    for x in range(2, 14):
        img.px[0][x] = 3
        img.px[1][x] = 1
    return img


def _pew():
    img = mt(0)
    for y in range(6, 9):
        for x in range(16):
            img.px[y][x] = 2
    for x in range(16):
        img.px[6][x] = 3
    for y in range(9, 16):
        for x in (2, 3, 12, 13):
            img.px[y][x] = 1
    for y in range(2, 6):
        for x in range(12, 15):
            img.px[y][x] = 2
    return img


def _bell():
    img = mt(0)
    for y in range(3, 13):
        w = 2 + (y - 3) // 2
        for x in range(8 - w, 8 + w):
            if 0 <= x < 16:
                img.px[y][x] = 2
        if 8 - w >= 0:
            img.px[y][8 - w] = 3
        if 8 + w - 1 < 16:
            img.px[y][8 + w - 1] = 1
    for x in range(3, 13):
        img.px[13][x] = 1
    img.px[14][7] = 3
    img.px[14][8] = 3
    for y in range(0, 3):
        img.px[y][7] = 3
        img.px[y][8] = 1
    return img


def _gargoyle():
    img = mt(0)
    for y in range(6, 16):
        for x in range(4, 12):
            img.px[y][x] = 2
    for x in range(3, 13):
        img.px[6][x] = 3
    for y in range(8, 12):
        img.px[y][3] = 2
        img.px[y][12] = 2
    img.px[9][5] = 1
    img.px[9][10] = 1
    for x in range(5, 11):
        img.px[12][x] = 1
    for y in range(14, 16):
        for x in range(2, 14):
            img.px[y][x] = 1
    return img


def theme_battlefield():
    th = Theme("battlefield", 0x0F, [(0x07, 0x17, 0x27),   # 0 scorched earth
                                     (0x00, 0x10, 0x30),   # 1 broken stone
                                     (0x01, 0x11, 0x21),   # 2 smoke, distance
                                     (0x06, 0x16, 0x37)])  # 3 fire, banners + HUD
    _standard(th, 700, ground_pal=0, soil_pal=0, stone_pal=1, accent_pal=2,
              grass=False, top_kw={"base": 2, "mortar": 1, "light": 3, "bw": 6, "bh": 3, "damage": 3},
              wall_fn=lambda s: T.bricks(s, damage=4, bw=6, bh=4))
    th.add("SKY", mt(0), 3, EMPTY)
    th.add("BGA", _smoke(0), 2, EMPTY)
    th.add("BGB", _silhouette(701, "hillcrest"), 2, EMPTY)
    th.add("BGC", _silhouette(7011, "flat"), 2, EMPTY)
    th.add("BGD", _silhouette(702, "ruinfar"), 2, EMPTY)
    th.add("RUIN", _ruin(), 2, EMPTY)
    th.add("D1", _palisade(), 0, SOLID)
    th.add("D2", T.rubble(703), 1, SOLID)
    th.add("D3", _shield_wall(), 1, SOLID)
    th.add("D4", _barrel(), 0, SOLID)
    th.add("D5", T.banner(704), 2, EMPTY)
    th.add("D6", _smoke(1), 3, EMPTY)
    th.add("WATERS", T.water(705, surface=True), 3, WATER)
    th.add("WATERB", T.water(706), 3, WATER)
    th.addanim("FIRE", [_torch(p) for p in range(3)], 2, HAZARD)
    return th


def _smoke(k):
    img = mt(0)
    r = Rnd(710 + k)
    for _ in range(7):
        cx, cy = r.rng(16), r.rng(16)
        rr = r.rng(3) + 2
        for y in range(cy - rr, cy + rr + 1):
            for x in range(cx - rr, cx + rr + 1):
                if 0 <= x < 16 and 0 <= y < 16:
                    if (x - cx) ** 2 + (y - cy) ** 2 <= rr * rr:
                        img.px[y][x] = 1 if r.chance(2, 3) else 2
    return img


def _ruin():
    img = T.bricks(720, base=1, mortar=1, light=1, damage=6)
    for y in range(0, 8):
        for x in range(16):
            if (x + y) % 7 < 3:
                img.px[y][x] = 0
    return img


def _palisade():
    img = mt(0)
    for i in range(4):
        x0 = i * 4
        for y in range(2, 16):
            for x in range(x0, x0 + 3):
                img.px[y][x] = 2
            img.px[y][x0] = 3
            img.px[y][x0 + 2] = 1
        img.px[1][x0 + 1] = 2
    for y in (6, 11):
        for x in range(16):
            img.px[y][x] = 1
    return img


def _shield_wall():
    img = mt(0)
    for cy in (4, 12):
        for cx in (4, 12):
            for y in range(cy - 4, cy + 4):
                for x in range(cx - 4, cx + 4):
                    if 0 <= x < 16 and 0 <= y < 16:
                        d = abs(x - cx) + abs(y - cy)
                        if d <= 4:
                            img.px[y][x] = 2 if d < 4 else 1
            if 0 <= cy < 16:
                img.px[cy][cx] = 3
    return img


def theme_mountain():
    th = Theme("mountain", 0x0F, [(0x00, 0x10, 0x30),   # 0 ancient masonry
                                  (0x01, 0x11, 0x21),   # 1 ice, cold stone
                                  (0x0C, 0x1C, 0x2C),   # 2 distance, strange glow
                                  (0x07, 0x28, 0x38)])  # 3 old gold + HUD
    _standard(th, 800, ground_pal=0, soil_pal=0, stone_pal=0, accent_pal=2,
              grass=False, top_kw={"bw": 8, "bh": 8},
              wall_fn=lambda s: T.bricks(s, bw=8, bh=8, damage=1))
    th.add("SKY", mt(0), 1, EMPTY)
    th.add("BGA", _stars(), 2, EMPTY)
    th.add("BGB", _silhouette(801, "peak"), 2, EMPTY)
    th.add("BGC", _silhouette(8011, "flat"), 2, EMPTY)
    th.add("BGD", _silhouette(802, "statuefar"), 2, EMPTY)
    th.add("GLYPH", _glyphs(), 3, EMPTY)
    th.add("D1", T.stairs(803), 0, SOLID)
    th.add("D2", _glyphs(), 2, SOLID)
    th.add("D3", _statue_leg(), 0, SOLID)
    th.add("D4", _pillar_broken(), 0, SOLID)
    th.add("D5", T.chain(804), 0, EMPTY)
    th.add("D6", _icecap(), 1, ICE)
    th.add("WATERS", T.water(805, surface=True), 1, WATER)
    th.add("WATERB", T.water(806), 1, WATER)
    th.addanim("GLOW", [_glowrune(p) for p in range(3)], 3, EMPTY)
    return th


def _stars():
    img = mt(0)
    r = Rnd(810)
    for _ in range(6):
        img.px[r.rng(16)][r.rng(16)] = 3
    for _ in range(3):
        x, y = r.rng(14) + 1, r.rng(14) + 1
        img.px[y][x] = 3
        img.px[y][x + 1] = 2
    return img


def _glyphs():
    img = T.bricks(820, bw=8, bh=8)
    marks = [(3, 3), (4, 3), (5, 3), (4, 4), (4, 5), (3, 6), (5, 6),
             (11, 4), (12, 4), (11, 5), (12, 6), (11, 7), (12, 8),
             (6, 11), (7, 11), (8, 11), (7, 12), (7, 13), (6, 13), (8, 13)]
    for x, y in marks:
        img.px[y][x] = 3
        if y + 1 < 16:
            img.px[y + 1][x] = 1
    return img


def _statue_leg():
    img = mt(0)
    for y in range(16):
        for x in range(2, 14):
            img.px[y][x] = 2
        img.px[y][2] = 1
        img.px[y][13] = 1
        img.px[y][4] = 3
    for y in (3, 9, 14):
        for x in range(2, 14):
            img.px[y][x] = 1
    return img


def _pillar_broken():
    img = mt(0)
    r = Rnd(830)
    for y in range(16):
        h = 3 if y > 4 else 0
        for x in range(3, 13):
            img.px[y][x] = 2
    for y in range(0, 5):
        for x in range(3, 13):
            if r.chance(1, 2):
                img.px[y][x] = 0
    for y in range(16):
        img.px[y][3] = 3
        img.px[y][12] = 1
    return img


def _icecap():
    img = mt(2)
    r = Rnd(840)
    for x in range(16):
        for y in range(0, 4):
            img.px[y][x] = 3
    for _ in range(10):
        x, y = r.rng(15), r.rng(11) + 4
        img.px[y][x] = 3 if r.chance(1, 2) else 1
    for x in range(16):
        img.px[15][x] = 1
    return img


def _glowrune(phase):
    img = mt(0)
    pts = [(7, 3), (8, 3), (6, 4), (9, 4), (5, 5), (10, 5),
           (7, 7), (8, 7), (7, 8), (8, 8),
           (5, 10), (10, 10), (6, 11), (9, 11), (7, 12), (8, 12)]
    for i, (x, y) in enumerate(pts):
        c = 3 if ((i + phase) % 3) else 2
        img.px[y][x] = c
    return img


THEMES = [theme_village, theme_forest, theme_fortress, theme_marsh,
          theme_factory, theme_cathedral, theme_battlefield, theme_mountain]
THEME_NAMES = ["VILLAGE", "FOREST", "FORTRESS", "MARSH", "FACTORY",
               "CATHEDRAL", "BATTLEFIELD", "MOUNTAIN"]


# ---------------------------------------------------------------------------
# CHR packing
# ---------------------------------------------------------------------------
R2_BASE, R3_BASE, R4_BASE, R5_BASE = 0x00, 0x40, 0x80, 0xC0


class ThemeData(object):
    pass


def pack_theme(th, chr_rom):
    """Cut every metatile into 8x8 tiles and lay them out across R2..R4."""
    static = TileSet(th.name + "-s", capacity=128)          # slot 0 = blank
    anim = [TileSet(th.name + "-a%d" % i, capacity=64) for i in range(3)]
    anim_index = {}

    order = list(REQUIRED)
    extras = sorted([n for n in list(th.tiles) + list(th.anim) if n not in REQUIRED])
    order += extras
    if len(order) > 64:
        raise RuntimeError("%s has %d metatiles (max 64)" % (th.name, len(order)))

    tl, tr, bl, br, at, fl = [], [], [], [], [], []
    names = {}
    for i, nm in enumerate(order):
        names[nm] = i
        if nm in th.anim:
            imgs, pal, col = th.anim[nm]
            quads = []
            for qy in (0, 8):
                for qx in (0, 8):
                    key = tuple(TileSet.key(im.sub(qx, qy, 8, 8)) for im in imgs)
                    slot = anim_index.get(key)
                    if slot is None:
                        slot = len(anim[0].tiles)
                        if slot >= 64:
                            raise RuntimeError("%s animated bank overflow" % th.name)
                        for k in range(3):
                            anim[k].add_at(slot, imgs[k].sub(qx, qy, 8, 8))
                        anim_index[key] = slot
                    quads.append(R4_BASE + slot)
        else:
            img, pal, col = th.tiles[nm]
            quads = []
            for qy in (0, 8):
                for qx in (0, 8):
                    quads.append(static.add(img.sub(qx, qy, 8, 8)))
        tl.append(quads[0]); tr.append(quads[1])
        bl.append(quads[2]); br.append(quads[3])
        at.append(pal & 3)
        fl.append(col)

    while len(tl) < 64:
        tl.append(0); tr.append(0); bl.append(0); br.append(0)
        at.append(0); fl.append(EMPTY)

    # static tiles fill R2 then R3; R4 carries the animated bank variants
    st = static.tiles
    r2 = chr_rom.add_1k("%s bg lo" % th.name, st[:64])
    r3 = chr_rom.add_1k("%s bg hi" % th.name, st[64:128])
    r4 = [chr_rom.add_1k("%s anim %d" % (th.name, i), anim[i].tiles)
          for i in range(3)]

    d = ThemeData()
    d.name = th.name
    d.r2, d.r3, d.r4 = r2, r3, r4
    d.names = names
    d.table = bytes(tl) + bytes(tr) + bytes(bl) + bytes(br) + bytes(at) + bytes(fl)
    d.collision = fl
    pal = bytearray()
    for p in th.pals:
        pal.append(th.bg)
        pal.extend(p)
    d.palette = bytes(pal)
    d.bg = th.bg
    d.static_used = len(st)
    d.anim_used = len(anim[0].tiles)
    return d


def build(chr_rom, write):
    """Render all themes plus the shared HUD bank."""
    import gen_font
    hud_tiles, hud_names = gen_font.build_tiles()
    hud_bank = chr_rom.add_1k("HUD + font", hud_tiles)

    data = []
    lines = []
    for fn in THEMES:
        th = fn()
        th.check()
        data.append(pack_theme(th, chr_rom))

    a = ['; Generated by tools/gen_bg.py -- do not edit.\n']
    a.append('.export theme_chr, theme_pal, hud_chr_bank\n')
    a.append('.segment "B00"\n')
    a.append("hud_chr_bank = $%02X\n" % hud_bank)
    a.append("theme_chr:\n")
    for d in data:
        a.append("        .byte $%02X,$%02X,$%02X,$%02X,$%02X\n"
                 % (d.r2, d.r3, d.r4[0], d.r4[1], d.r4[2]))
    a.append("theme_pal:\n")
    for d in data:
        a.append("        .byte " + ",".join("$%02X" % b for b in d.palette) + "\n")
    write("bg_data.s", "".join(a))

    inc = ['; Generated by tools/gen_bg.py -- do not edit.\n']
    for k, v in sorted(hud_names.items()):
        key = k[1:] if k.startswith('#') else "CH_%d" % ord(k)
        if k.startswith('#'):
            inc.append("TILE_%s = $%02X\n" % (key, R5_BASE + v))
    inc.append("FONT_BASE = $%02X\n" % R5_BASE)
    inc.append("HUD_CHR_BANK = $%02X\n" % hud_bank)
    for i, nm in enumerate(THEME_NAMES):
        inc.append("THEME_%s = %d\n" % (nm, i))
    write("bg.inc", "".join(inc))

    for d in data:
        lines.append("theme %-12s static %3d/128  anim %2d/64\n"
                     % (d.name, d.static_used, d.anim_used))
    build.themes = data
    build.hud_names = hud_names
    build.hud_bank = hud_bank
    return "".join(lines)

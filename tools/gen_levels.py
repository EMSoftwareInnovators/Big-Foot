#!/usr/bin/env python3
"""Compile the eight stages from chunk sequences into per-bank level data."""
import chunks as CH
from chunks import W as CW, H as CHH
from entdef import NAME2ID as E
from nesart import asm_bytes

MAP_STRIDE = 16


def rot(col, n):
    """Deterministic variation index."""
    return ((col * 37 + (col >> 3) * 11) % n)


TERRAIN = {
    '.': "SKY", ' ': "SKY",
    '%': "WALL", '=': "PLAT1", '-': "PLAT2", '^': "SPIKE", 'x': "BREAK",
    '~': "WATERS", 'w': "WATERB", 'c': "CHAINT", '!': "SWITCHM",
    '*': "CHECK", 'X': "EXITM",
    'o': "D3", 'O': "D4", 'v': "D5", ',': "D6", "'": "D1", '"': "D2",
    'a': "BGA", 'b': "BGB", 'd': "BGC", 'e': "BGD",
}
SPAWNCHR = {
    '1': 0, '2': 1, '3': 2, '4': 3, '5': 4, '6': 5,
    'k': 'KICK', 'g': 'GRAB', 'h': 'HEALTH', 'p': 'SHOE', 'L': 'LIFE',
}


class Stage(object):
    def __init__(self, num, name, theme, music, seq, roster, shoe=None,
                 boss=0, kick_object="ROCK", horizon=True, bossmusic=9,
                 backdrop="sky"):
        self.num = num
        self.name = name
        self.theme = theme
        self.music = music
        self.seq = seq
        self.roster = roster
        self.shoe = shoe
        self.boss = boss
        self.kick_object = kick_object
        self.horizon = horizon
        self.bossmusic = bossmusic
        self.backdrop = backdrop


STAGES = [
    Stage(0, "THE LITTLE KINGDOM", 0, 1,
          ["start", "flat", "steps", "flat2", "ambush", "gap", "checkpoint",
           "crates", "ledges", "wall", "archers", "shoeroom", "gap2",
           "checkpoint", "gauntlet", "bossgate", "arena", "arena2"],
          ["SPEAR_GUARD", "ARCHER", "SHIELD_KNIGHT", "PEASANT", "CHICKEN", "PEASANT"],
          shoe=1, boss=0, kick_object="ROCK"),

    Stage(1, "THE ROYAL FOREST", 1, 2,
          ["start", "flat", "high", "ledges", "chains", "checkpoint",
           "gap", "crates", "climbup", "secret", "ambush", "bridge",
           "checkpoint", "gauntlet", "pit", "bossgate", "arena", "arena2"],
          ["SPEAR_GUARD", "TRAPPER", "BEETLE", "CROW", "ARCHER", "PEASANT"],
          shoe=None, boss=1, kick_object="ROCK"),

    Stage(2, "FORT STONEHEEL", 2, 3,
          ["start", "hall", "wall", "archers", "gate", "checkpoint",
           "shaft", "kickpuzzle", "chains", "crush", "shoeroom",
           "checkpoint", "gauntlet", "descent", "bossgate", "arena", "arena2"],
          ["SHIELD_KNIGHT", "ARCHER", "BALLISTA", "SPEAR_GUARD", "ROYAL_MAGE", "KINGS_ELITE"],
          shoe=2, boss=2, kick_object="CANNONBALL", backdrop="wall"),

    Stage(3, "THE MIASMA MARSH", 3, 4,
          ["start", "flat", "shore", "wade", "shoeroom", "swim",
           "checkpoint", "swim2", "wade", "ledges", "ambush", "pit",
           "checkpoint", "gauntlet", "bridge", "bossgate", "arena", "arena2"],
          ["LURKER", "BEETLE", "CROW", "LURKER", "TRAPPER", "ARCHER"],
          shoe=5, boss=3, kick_object="ROCK"),

    Stage(4, "THE KING'S WAR FACTORY", 4, 5,
          ["start", "hall", "crush", "kickpuzzle", "shaft", "checkpoint",
           "high", "chains", "gate", "shoeroom", "crush", "ambush",
           "checkpoint", "gauntlet", "descent", "bossgate", "arena", "arena2"],
          ["DRONE", "HEEL_CLAMP", "TOE_CRUSHER", "SHIELD_KNIGHT", "PIKE_TURRET", "KINGS_ELITE"],
          shoe=3, boss=4, kick_object="CRATE", backdrop="wall"),

    Stage(5, "THE HOLY CITY", 5, 6,
          ["start", "hall", "gate", "archers", "climbup", "checkpoint",
           "high", "chains", "secret", "shoeroom", "ambush", "gate",
           "checkpoint", "gauntlet", "ledges", "bossgate", "arena", "arena2"],
          ["BELL_MONK", "GARGOYLE", "ROYAL_MAGE", "SHIELD_KNIGHT", "ARCHER", "KINGS_ELITE"],
          shoe=6, boss=5, kick_object="BARREL", backdrop="wall"),

    Stage(6, "THE LAST MARCH", 6, 7,
          ["start", "ambush", "gauntlet", "wall", "archers", "checkpoint",
           "gap2", "crates", "gate", "shoeroom", "gauntlet", "crush",
           "checkpoint", "ambush", "descent", "bossgate", "arena", "arena2"],
          ["KINGS_ELITE", "ARCHER", "SHIELD_KNIGHT", "ROYAL_MAGE", "BALLISTA", "SPEAR_GUARD"],
          shoe=4, boss=6, kick_object="CANNONBALL"),

    Stage(7, "THE MOUNTAIN OF THE GIANT", 7, 8,
          ["start", "steps", "high", "climbup", "checkpoint", "shaft",
           "ledges", "chains", "descent", "shoeroom", "gap", "high",
           "checkpoint", "gauntlet", "steps", "bossgate", "arena", "arena2"],
          ["GARGOYLE", "KINGS_ELITE", "BEETLE", "DRONE", "GARGOYLE", "KINGS_ELITE"],
          shoe=7, boss=7, kick_object="ROCK", bossmusic=10),
]

SHOE_ITEM = ["BARE", "RUNNING", "STEEL", "COWBOY", "CLEAT", "FLIPPER",
             "SLIPPER", "BIG"]

# Sprite palettes per stage.  Palette 0 is overwritten at runtime with the
# palette of whatever footwear Big Foot is currently wearing.
SPR_PALS = [
    [(0x16, 0x27, 0x37), (0x0F, 0x16, 0x30), (0x0F, 0x17, 0x27), (0x0F, 0x28, 0x30)],
    [(0x16, 0x27, 0x37), (0x0F, 0x16, 0x30), (0x0F, 0x09, 0x29), (0x0F, 0x27, 0x37)],
    [(0x16, 0x27, 0x37), (0x0F, 0x16, 0x30), (0x0F, 0x00, 0x10), (0x0F, 0x27, 0x37)],
    [(0x16, 0x27, 0x37), (0x0F, 0x0C, 0x2C), (0x0F, 0x08, 0x28), (0x0F, 0x21, 0x31)],
    [(0x16, 0x27, 0x37), (0x0F, 0x00, 0x10), (0x0F, 0x16, 0x27), (0x0F, 0x28, 0x38)],
    [(0x16, 0x27, 0x37), (0x0F, 0x02, 0x30), (0x0F, 0x00, 0x10), (0x0F, 0x28, 0x38)],
    [(0x16, 0x27, 0x37), (0x0F, 0x16, 0x30), (0x0F, 0x00, 0x10), (0x0F, 0x27, 0x37)],
    [(0x16, 0x27, 0x37), (0x0F, 0x00, 0x30), (0x0F, 0x0C, 0x2C), (0x0F, 0x28, 0x38)],
]


def compile_stage(st, theme):
    """Returns (map_bytes, spawns, checkpoints, start, boss_col, cols)."""
    grid = []
    for name in st.seq:
        ch = CH.CHUNKS[name]
        for x in range(CW):
            grid.append([ch[y][x] for y in range(CHH)])
    cols = len(grid)

    names = theme.names
    def idx(n):
        return names[n]

    mapdata = bytearray(cols * MAP_STRIDE)
    spawns = []
    checkpoints = []
    start = (3, 9)
    boss_col = None
    # the boss arena begins at the first "arena" chunk
    for i, name in enumerate(st.seq):
        if name == "arena":
            boss_col = i * CW
            break
    if boss_col is None:
        boss_col = cols - CW

    for col in range(cols):
        column = grid[col]
        for row in range(CHH):
            c = column[row]
            mt = "SKY"
            if c in SPAWNCHR:
                what = SPAWNCHR[c]
                if what == 'KICK':
                    spawns.append((col, row, E[st.kick_object]))
                elif what == 'GRAB':
                    spawns.append((col, row, E["CRATE"]))
                elif what == 'HEALTH':
                    spawns.append((col, row, E["HEALTH"]))
                elif what == 'LIFE':
                    spawns.append((col, row, E["LIFE"]))
                elif what == 'SHOE':
                    if st.shoe is not None:
                        spawns.append((col, row, E["SHOEBOX"]))
                else:
                    spawns.append((col, row, E[st.roster[what]]))
            elif c == '@':
                start = (col, row)
            else:
                mt = TERRAIN.get(c, "SKY")
                if mt == "WALL":
                    mt = ["WALL1", "WALL2"][rot(col + row, 2)]
                elif mt == "SKY" and c == '#':
                    mt = "SKY"
            if c == '#':
                above = column[row - 1] if row > 0 else '.'
                if above in ('#', '%'):
                    mt = ["FILL1", "FILL2", "FILL3"][rot(col + row * 3, 3)]
                else:
                    mt = ["TOP1", "TOP2", "TOP3"][rot(col, 3)]
            if c == '*':
                checkpoints.append((col, row))
            mapdata[col * MAP_STRIDE + row] = idx(mt)

    # ---- backdrop ------------------------------------------------------
    # Outdoor stages get a rolling silhouette skyline behind the playfield;
    # indoor stages get a back wall with periodic windows and columns.  Both
    # exist to keep the single background layer from reading as empty space.
    solid_chars = set('#%')
    tops = []
    for col in range(cols):
        column = grid[col]
        t = None
        for row in range(CHH):
            if column[row] in solid_chars:
                t = row
                break
        tops.append(t if t is not None else CHH)

    if st.backdrop == "sky":
        h = 2
        seed = 12345 + st.num * 977
        step = 0
        for col in range(cols):
            if step == 0:
                seed = (seed * 1103515245 + 12345) & 0x7FFFFFFF
                delta = ((seed >> 16) % 3) - 1
                h = max(2, min(5, h + delta))
                step = 2 + ((seed >> 8) % 4)
            step -= 1
            top = tops[col]
            if top >= CHH:
                top = CHH - 1
            if top < 5:
                continue
            crest = top - h
            for row in range(crest, top):
                if grid[col][row] not in ('.', ' '):
                    continue
                if mapdata[col * MAP_STRIDE + row] != idx("SKY"):
                    continue
                mt = "BGB" if row == crest else "BGC"
                mapdata[col * MAP_STRIDE + row] = idx(mt)
            # a nearer detail band every so often
            if (col % 23) in (0, 1) and crest - 1 >= 2:
                if mapdata[col * MAP_STRIDE + top - 1] == idx("BGC"):
                    mapdata[col * MAP_STRIDE + top - 1] = idx("BGD")
            # sky accents
            if (col % 17) == 3:
                for row in (1, 2):
                    if mapdata[col * MAP_STRIDE + row] == idx("SKY"):
                        mapdata[col * MAP_STRIDE + row] = idx("BGA")
    elif st.backdrop == "wall":
        back = "BACKWALL" if "BACKWALL" in names else "BGC"
        for col in range(cols):
            for row in range(CHH):
                if mapdata[col * MAP_STRIDE + row] != idx("SKY"):
                    continue
                mt = back
                if (col % 8) == 4 and 2 <= row <= 9 and "BGD" in names:
                    mt = "BGD"
                elif (col % 8) == 1 and (row % 5) == 2 and "BGA" in names:
                    mt = "BGA"
                mapdata[col * MAP_STRIDE + row] = idx(mt)

    # ---- ground clutter -------------------------------------------------
    # Scatter the theme's non-solid props along the ground line so no stretch
    # of floor is ever a bare stripe.
    prop_seed = 777 + st.num * 131
    for col in range(cols):
        top = tops[col]
        if top >= CHH or top < 2:
            continue
        row = top - 1
        if grid[col][row] not in ('.', ' '):
            continue
        cur = mapdata[col * MAP_STRIDE + row]
        if cur not in (idx("SKY"), idx("BGC"), idx("BGB"), idx("BGD")):
            continue
        prop_seed = (prop_seed * 1103515245 + 12345) & 0x7FFFFFFF
        roll = (prop_seed >> 16) % 100
        if roll < 14:
            mapdata[col * MAP_STRIDE + row] = idx("D6")
        elif roll < 22:
            mapdata[col * MAP_STRIDE + row] = idx("D1")
        elif roll < 26 and row >= 2:
            mapdata[col * MAP_STRIDE + row] = idx("D5")

    spawns.sort(key=lambda s: s[0])
    return mapdata, spawns, checkpoints, start, boss_col, cols


def build(write):
    import gen_bg
    themes = gen_bg.build.themes
    out = []
    log = []
    for st in STAGES:
        theme = themes[st.theme]
        mapdata, spawns, cps, start, boss_col, cols = compile_stage(st, theme)
        seg = "B%02d" % (2 + st.num)
        a = ['; Generated by tools/gen_levels.py -- do not edit.\n']
        a.append('.export stage%d_header\n' % st.num)
        a.append('.segment "%s"\n' % seg)
        a.append("stage%d_header:\n" % st.num)
        a.append("        .addr s%d_map, s%d_mt, s%d_spawn, s%d_pal\n"
                 % (st.num, st.num, st.num, st.num))
        a.append("        .addr s%d_check\n" % st.num)
        a.append("        .word %d\n" % cols)
        a.append("        .word %d\n" % boss_col)
        a.append("        .byte %d, %d, %d, %d, %d, %d\n"
                 % (st.theme, st.music, start[0] & 0xFF, start[0] >> 8,
                    start[1], st.boss))
        a.append("        .byte %d, %d\n" % (st.shoe if st.shoe is not None else 0,
                                             st.bossmusic))
        a.append("        .byte " + ",".join(str(E[r]) for r in st.roster) + "\n")

        sp = bytearray()
        for col, row, typ in spawns:
            sp += bytes([col & 0xFF, col >> 8, row, typ])
        sp += bytes([0xFF, 0xFF, 0, 0])
        cp = bytearray([len(cps)])
        for col, row in cps:
            cp += bytes([col & 0xFF, col >> 8, row])

        pal = bytearray(theme.palette)
        for p3 in SPR_PALS[st.num]:
            pal.append(theme.bg)
            pal.extend(p3)
        a.append(asm_bytes("s%d_mt" % st.num, theme.table))
        a.append(asm_bytes("s%d_pal" % st.num, pal))
        a.append(asm_bytes("s%d_spawn" % st.num, bytes(sp)))
        a.append(asm_bytes("s%d_check" % st.num, bytes(cp)))
        a.append(asm_bytes("s%d_map" % st.num, bytes(mapdata), per_line=16))
        write("level_s%d.s" % st.num, "".join(a))
        total = len(mapdata) + len(theme.table) + len(pal) + len(sp) + len(cp)
        log.append("stage %d %-26s %3d cols, %2d spawns, bank %d/8192 bytes\n"
                   % (st.num, st.name, cols, len(spawns), total))
        out.append(st)

    a = ['; Generated by tools/gen_levels.py -- do not edit.\n']
    a.append('.export stage_bank, stage_name_lo, stage_name_hi\n')
    a.append('.segment "B00"\n')
    a.append("stage_bank:\n        .byte " +
             ",".join(str(2 + s.num) for s in STAGES) + "\n")
    for s in STAGES:
        a.append('stage_name%d: .byte "%s",0\n' % (s.num, s.name))
    a.append("stage_name_lo:\n        .lobytes " +
             ",".join("stage_name%d" % s.num for s in STAGES) + "\n")
    a.append("stage_name_hi:\n        .hibytes " +
             ",".join("stage_name%d" % s.num for s in STAGES) + "\n")
    write("level_data.s", "".join(a))

    inc = ["NUM_STAGES = %d\n" % len(STAGES)]
    write("levels.inc", "".join(inc))
    return "".join(log)

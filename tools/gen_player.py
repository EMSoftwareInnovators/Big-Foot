#!/usr/bin/env python3
"""Generate every Big Foot animation frame, for every footwear, plus the
frame/animation tables the engine walks."""
import math
from foot import Pose as P, render_foot, ORIGIN_X, ORIGIN_Y
from shoes import SHOES, SHOE_PALETTES, SHOE_NAMES
from nesart import asm_bytes, Img

# ---------------------------------------------------------------------------
# Logical frames.  The engine only ever refers to these names; each footwear
# provides its own art for them through a remap table.
# ---------------------------------------------------------------------------
FRAMES = [
    ("IDLE0",  P()),
    ("IDLE1",  P(toe_curls=[-0.16] * 5)),
    ("IDLE2",  P(toe_curls=[0.14, 0.11, 0.08, 0.06, 0.04])),

    # walk cycle: heel strike, roll through, push off, swing
    ("WALK0",  P(toe=0.28, dx=1)),
    ("WALK1",  P(toe=0.10)),
    ("WALK2",  P(squash=0.97)),
    ("WALK3",  P(heel=0.18)),
    ("WALK4",  P(heel=0.42, curl=0.35)),
    ("WALK5",  P(heel=0.56, curl=0.75, dy=-3, dx=-2)),
    ("WALK6",  P(heel=0.26, curl=0.30, dy=-6, dx=-1)),
    ("WALK7",  P(toe=0.18, dy=-3, dx=1)),

    # run cycle: the same shapes, pushed harder
    ("RUN0",   P(toe=0.42, dx=2, squash=0.96)),
    ("RUN1",   P(squash=0.92, stretch=1.05)),
    ("RUN2",   P(heel=0.42, curl=0.45)),
    ("RUN3",   P(heel=0.72, curl=0.95, dy=-5, dx=-3)),
    ("RUN4",   P(heel=0.30, curl=0.50, dy=-9, dx=-1)),
    ("RUN5",   P(toe=0.36, dy=-4, dx=3, stretch=1.06)),

    ("JUMP0",  P(heel=0.55, curl=0.85, squash=0.90)),
    ("JUMP1",  P(toe=0.12, stretch=1.06, squash=1.06, curl=-0.35)),
    ("FALL0",  P(heel=0.20, curl=-0.20, squash=1.05)),
    ("FALL1",  P(heel=0.36, curl=0.10, squash=1.07)),
    ("LAND0",  P(squash=0.68, stretch=1.20, spread=0.5)),
    ("LAND1",  P(squash=0.86, stretch=1.08)),

    ("STOMP0", P(toe=0.34, dy=-5, curl=-0.45)),
    ("STOMP1", P(squash=1.12, stretch=0.93, curl=-0.20)),
    ("STOMP2", P(squash=0.60, stretch=1.28, spread=0.7)),

    ("KICK0",  P(toe=0.32, dx=-4, curl=0.55)),
    ("KICK1",  P(stretch=1.30, dx=5, curl=-0.55)),
    ("KICK2",  P(stretch=1.10, dx=2, curl=-0.10)),

    ("GRAB0",  P(curl=1.5, dy=-2)),
    ("GRAB1",  P(curl=1.9, dy=-3, toe=0.10)),

    ("HURT0",  P(angle=0.32, dx=-3, dy=-2, curl=-0.75)),

    ("DIE0",   P(angle=-0.60, dy=-4, curl=-0.6)),
    ("DIE1",   P(angle=-1.50, dy=-9, curl=-0.3)),
    ("DIE2",   P(angle=-2.60, dy=-5, curl=0.2)),
    ("DIE3",   P(angle=-3.10, dy=0, curl=0.5, squash=0.92)),

    ("SWIM0",  P(angle=-0.38, dy=-2, curl=-0.35)),
    ("SWIM1",  P(angle=-0.16, dy=-1, curl=0.25)),
    ("SWIM2",  P(angle=-0.32, dy=-2, curl=0.65)),
    ("SWIM3",  P(angle=-0.20, dy=-3, curl=0.00)),
]
NAME2IDX = {n: i for i, (n, _) in enumerate(FRAMES)}
NFRAMES = len(FRAMES)

# The reduced set every shoe is drawn in ...
SHOE_SET = ["IDLE0", "WALK0", "WALK2", "WALK3", "WALK4", "WALK5", "WALK7",
            "JUMP1", "FALL1", "LAND0", "KICK0", "KICK1", "STOMP0", "STOMP2",
            "HURT0", "DIE1", "SWIM0", "SWIM2"]
# ... and how the 40 logical frames map onto it.
SHOE_REMAP = {
    "IDLE0": "IDLE0", "IDLE1": "IDLE0", "IDLE2": "IDLE0",
    "WALK0": "WALK0", "WALK1": "WALK2", "WALK2": "WALK2", "WALK3": "WALK3",
    "WALK4": "WALK4", "WALK5": "WALK5", "WALK6": "WALK5", "WALK7": "WALK7",
    "RUN0": "WALK0", "RUN1": "WALK2", "RUN2": "WALK3", "RUN3": "WALK5",
    "RUN4": "WALK5", "RUN5": "WALK7",
    "JUMP0": "WALK4", "JUMP1": "JUMP1", "FALL0": "FALL1", "FALL1": "FALL1",
    "LAND0": "LAND0", "LAND1": "LAND0",
    "STOMP0": "STOMP0", "STOMP1": "STOMP0", "STOMP2": "STOMP2",
    "KICK0": "KICK0", "KICK1": "KICK1", "KICK2": "KICK1",
    "GRAB0": "WALK4", "GRAB1": "WALK4",
    "HURT0": "HURT0",
    "DIE0": "DIE1", "DIE1": "DIE1", "DIE2": "DIE1", "DIE3": "DIE1",
    "SWIM0": "SWIM0", "SWIM1": "SWIM2", "SWIM2": "SWIM2", "SWIM3": "SWIM0",
}

# ---------------------------------------------------------------------------
# Animations: (name, [(frame, duration), ...], loop_point or -1 to hold)
# ---------------------------------------------------------------------------
ANIMS = [
    ("IDLE",   [("IDLE0", 40), ("IDLE1", 10), ("IDLE0", 50), ("IDLE2", 12)], 0),
    ("WALK",   [("WALK0", 5), ("WALK1", 4), ("WALK2", 5), ("WALK3", 4),
                ("WALK4", 4), ("WALK5", 5), ("WALK6", 5), ("WALK7", 4)], 0),
    ("RUN",    [("RUN0", 3), ("RUN1", 3), ("RUN2", 3), ("RUN3", 4),
                ("RUN4", 3), ("RUN5", 3)], 0),
    ("JUMP",   [("JUMP0", 4), ("JUMP1", 60)], -1),
    ("FALL",   [("FALL0", 8), ("FALL1", 60)], -1),
    ("LAND",   [("LAND0", 4), ("LAND1", 4)], -1),
    ("STOMP",  [("STOMP0", 6), ("STOMP1", 60)], -1),
    ("SLAM",   [("STOMP2", 8), ("LAND1", 5)], -1),
    ("KICK",   [("KICK0", 5), ("KICK1", 7), ("KICK2", 6)], -1),
    ("GRAB",   [("GRAB0", 6), ("GRAB1", 30)], -1),
    ("HURT",   [("HURT0", 30)], -1),
    ("DIE",    [("DIE0", 8), ("DIE1", 10), ("DIE2", 10), ("DIE3", 60)], -1),
    ("SWIM",   [("SWIM0", 8), ("SWIM1", 7), ("SWIM2", 8), ("SWIM3", 7)], 0),
    ("PUSH",   [("WALK2", 8), ("WALK3", 8)], 0),
]


def build(chr_rom, packer_cls):
    """Render everything and return (asm_text, include_text)."""
    solid = Img(8, 8, 1)                # opaque tile reserved for sprite 0
    pk = packer_cls(chr_rom, "foot", reserve_top=solid)

    frame_ids = []          # [shoe][logical] -> packed frame index
    render_cache = {}

    # --- bare foot: the full expressive set ------------------------------
    bare = []
    for name, pose in FRAMES:
        img = render_foot(pose)
        bare.append(pk.add(img, ORIGIN_X, ORIGIN_Y, 0))
    frame_ids.append(bare)

    # --- footwear: the reduced set, remapped -----------------------------
    for si in range(1, len(SHOES)):
        fn = SHOES[si]
        local = {}
        for nm in SHOE_SET:
            pose = FRAMES[NAME2IDX[nm]][1]
            img = render_foot(pose, fn)
            local[nm] = pk.add(img, ORIGIN_X, ORIGIN_Y, 1)
        frame_ids.append([local[SHOE_REMAP[n]] for n, _ in FRAMES])

    bank_names = ["foot bank %d" % i for i in range(len(pk.banks))]
    pk.flush(bank_names)

    # --- emit -------------------------------------------------------------
    ms_blob = bytearray()
    offsets = []
    for _, ms in pk.frames:
        offsets.append(len(ms_blob))
        ms_blob += ms

    a = []
    a.append('; Generated by tools/gen_player.py -- do not edit.\n')
    a.append('.export pf_bank, pf_ms_lo, pf_ms_hi, pf_remap, panim_tbl_lo\n')
    a.append('.export panim_tbl_hi, player_ms_data\n')
    a.append('.segment "B00"\n\n')
    a.append(asm_bytes("player_ms_data", bytes(ms_blob)))
    a.append("\npf_bank:\n")
    banks = pk.frame_bank_bytes()
    a.append(asm_bytes("", banks).replace(":\n", "", 1) if False else "")
    for i in range(0, len(banks), 16):
        a.append("        .byte " + ",".join("$%02X" % b for b in banks[i:i + 16]) + "\n")
    a.append("\npf_ms_lo:\n")
    for i in range(0, len(offsets), 8):
        a.append("        .lobytes " + ",".join(
            "player_ms_data+%d" % o for o in offsets[i:i + 8]) + "\n")
    a.append("pf_ms_hi:\n")
    for i in range(0, len(offsets), 8):
        a.append("        .hibytes " + ",".join(
            "player_ms_data+%d" % o for o in offsets[i:i + 8]) + "\n")

    a.append("\n; remap[shoe*%d + logical_frame] -> packed frame id\n" % NFRAMES)
    a.append("pf_remap:\n")
    flat = []
    for row in frame_ids:
        flat.extend(row)
    for i in range(0, len(flat), 16):
        a.append("        .byte " + ",".join("$%02X" % b for b in flat[i:i + 16]) + "\n")

    # animations
    anim_blob = []
    for nm, seq, loop in ANIMS:
        b = bytearray()
        for f, dur in seq:
            b.append(NAME2IDX[f])
            b.append(dur)
        b.append(0xFF)
        b.append(loop & 0xFF)
        anim_blob.append((nm, bytes(b)))
    a.append("\n")
    for nm, b in anim_blob:
        a.append(asm_bytes("panim_%s" % nm, b))
    a.append("panim_tbl_lo:\n        .lobytes " +
             ",".join("panim_%s" % nm for nm, _ in anim_blob) + "\n")
    a.append("panim_tbl_hi:\n        .hibytes " +
             ",".join("panim_%s" % nm for nm, _ in anim_blob) + "\n")

    inc = ["; Generated by tools/gen_player.py -- do not edit.\n"]
    for i, (nm, _) in enumerate(FRAMES):
        inc.append("PF_%s = %d\n" % (nm, i))
    inc.append("PF_COUNT = %d\n" % NFRAMES)
    for i, (nm, _, _) in enumerate(ANIMS):
        inc.append("ANIM_%s = %d\n" % (nm, i))
    inc.append("ANIM_COUNT = %d\n" % len(ANIMS))
    inc.append("PLAYER_SPR0_TILE = 127\n")
    inc.append("PLAYER_ORIGIN_X = %d\n" % ORIGIN_X)
    inc.append("PLAYER_ORIGIN_Y = %d\n" % ORIGIN_Y)

    stats = "player: %d packed frames, %d banks %s\n" % (
        len(pk.frames), len(pk.banks), pk.tile_counts())
    return "".join(a), "".join(inc), stats

#!/usr/bin/env python3
"""Entity type table shared by the level compiler, the sprite generator and
the engine."""

# (name, category)  category: 'enemy', 'object', 'shot', 'pickup', 'boss', 'fx'
ENTITIES = [
    ("NONE",         "none"),
    ("SPEAR_GUARD",  "enemy"),
    ("ARCHER",       "enemy"),
    ("SHIELD_KNIGHT","enemy"),
    ("PEASANT",      "enemy"),
    ("CHICKEN",      "enemy"),
    ("ROYAL_MAGE",   "enemy"),
    ("TRAPPER",      "enemy"),
    ("BEETLE",       "enemy"),
    ("CROW",         "enemy"),
    ("BALLISTA",     "enemy"),
    ("GARGOYLE",     "enemy"),
    ("DRONE",        "enemy"),
    ("HEEL_CLAMP",   "enemy"),
    ("TOE_CRUSHER",  "enemy"),
    ("BELL_MONK",    "enemy"),
    ("KINGS_ELITE",  "enemy"),
    ("LURKER",       "enemy"),
    ("PIKE_TURRET",  "enemy"),
    ("ROCK",         "object"),
    ("BARREL",       "object"),
    ("CANNONBALL",   "object"),
    ("CRATE",        "object"),
    ("BOMB",         "object"),
    ("ARROW",        "shot"),
    ("BOLT",         "shot"),
    ("SPIT",         "shot"),
    ("HEALTH",       "pickup"),
    ("SHOEBOX",      "pickup"),
    ("LIFE",         "pickup"),
    ("BOSS",         "boss"),
    ("BOSSPART",     "boss"),
    ("DUST",         "fx"),
    ("SPARK",        "fx"),
    ("SPLASH",       "fx"),
]
NAME2ID = {n: i for i, (n, _) in enumerate(ENTITIES)}
ID2NAME = {i: n for i, (n, _) in enumerate(ENTITIES)}


def cat(i):
    return ENTITIES[i][1]

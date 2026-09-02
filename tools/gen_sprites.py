#!/usr/bin/env python3
"""Enemy, object, projectile, pickup, effect and boss artwork, keyed by the
entity ids in entdef.py.

Each stage packs the six enemies of its roster plus the shared object/effect
set into one 2 KiB CHR bank (MMC3 R1); bosses get a bank of their own that is
swapped in when the fight starts.
"""
import figures as F
from foot import Pose, render_foot, ORIGIN_X, ORIGIN_Y
from nesart import Img

# palette assignments: 1 = humans, 2 = creatures and machines, 3 = objects/FX
PAL_HUMAN, PAL_BEAST, PAL_OBJ = 1, 2, 3


def _h(**kw):
    return F.human(**kw)


# name -> (frames, palette, hitbox w, hitbox h, origin mode)
# origin mode "foot" puts the origin at the bottom centre, "mid" at the centre.
ENEMY_ART = {
    "SPEAR_GUARD": ([_h(helmet="conical", weapon="spear"),
                     _h(helmet="conical", weapon="spear", stride=3),
                     _h(helmet="conical", weapon="spear", stride=-3, arm=1),
                     _h(helmet="conical", weapon="spear", arm=-3, crouch=2)],
                    PAL_HUMAN, 12, 22),
    "ARCHER": ([_h(helmet="cap", weapon="bow"),
                _h(helmet="cap", weapon="bow", arm=-2),
                _h(helmet="cap", weapon="bow", stride=2)],
               PAL_HUMAN, 12, 22),
    "SHIELD_KNIGHT": ([_h(helmet="flat", weapon="sword", shield=True),
                       _h(helmet="flat", weapon="sword", shield=True, stride=3),
                       _h(helmet="flat", weapon="sword", shield=True, arm=-4)],
                      PAL_HUMAN, 14, 22),
    "PEASANT": ([_h(helmet="none", weapon="arms", stride=3),
                 _h(helmet="none", weapon="arms", stride=-3, arm=-1),
                 _h(helmet="none", weapon="pitchfork")],
                PAL_HUMAN, 10, 22),
    "CHICKEN": ([F.chicken(0), F.chicken(1)], PAL_OBJ, 10, 10),
    "ROYAL_MAGE": ([_h(helmet="conical", weapon="staff", cloak=True),
                    _h(helmet="conical", weapon="staff", cloak=True, arm=-3),
                    _h(helmet="conical", weapon="staff", cloak=True, stride=2)],
                   PAL_HUMAN, 12, 22),
    "TRAPPER": ([_h(helmet="hood", weapon="trap"),
                 _h(helmet="hood", weapon="trap", stride=3),
                 _h(helmet="hood", weapon="trap", crouch=4)],
                PAL_HUMAN, 12, 22),
    "BEETLE": ([F.beetle(0), F.beetle(1)], PAL_BEAST, 14, 12),
    "CROW": ([F.crow(0), F.crow(1)], PAL_BEAST, 12, 10),
    "BALLISTA": ([F.ballista(0), F.ballista(1)], PAL_BEAST, 28, 20),
    "GARGOYLE": ([F.gargoyle(0), F.gargoyle(1)], PAL_BEAST, 16, 20),
    "DRONE": ([F.drone(0), F.drone(1)], PAL_BEAST, 14, 12),
    "HEEL_CLAMP": ([F.clamp(0), F.clamp(1)], PAL_BEAST, 20, 12),
    "TOE_CRUSHER": ([F.crusher(0), F.crusher(1)], PAL_BEAST, 16, 30),
    "BELL_MONK": ([_h(helmet="hood", weapon="bell", cloak=True),
                   _h(helmet="hood", weapon="bell", cloak=True, arm=-3),
                   _h(helmet="hood", weapon="bell", cloak=True, stride=2)],
                  PAL_HUMAN, 12, 22),
    "KINGS_ELITE": ([_h(helmet="great", weapon="sword", plume=True, shield=True),
                     _h(helmet="great", weapon="sword", plume=True, shield=True, stride=3),
                     _h(helmet="great", weapon="sword", plume=True, shield=True, arm=-5)],
                    PAL_HUMAN, 14, 22),
    "LURKER": ([F.lurker(0), F.lurker(1)], PAL_BEAST, 16, 14),
    "PIKE_TURRET": ([F.turret(0), F.turret(1)], PAL_BEAST, 14, 14),
}

OBJECT_ART = {
    "ROCK": ([F.rock(12)], PAL_OBJ, 12, 12),
    "BARREL": ([F.barrel()], PAL_OBJ, 12, 14),
    "CANNONBALL": ([F.cannonball(10)], PAL_OBJ, 10, 10),
    "CRATE": ([F.crate()], PAL_OBJ, 12, 12),
    "BOMB": ([F.bomb(12)], PAL_OBJ, 10, 10),
    "ARROW": ([F.arrow()], PAL_OBJ, 12, 6),
    "BOLT": ([F.bolt(0), F.bolt(1)], PAL_OBJ, 8, 8),
    "SPIT": ([F.spit(0), F.spit(1)], PAL_OBJ, 6, 6),
    "HEALTH": ([F.health_pickup()], PAL_OBJ, 12, 12),
    "SHOEBOX": ([F.shoebox()], PAL_OBJ, 18, 14),
    "LIFE": ([F.life_pickup()], PAL_OBJ, 10, 10),
    "DUST": ([F.dust(0), F.dust(1), F.dust(2)], PAL_OBJ, 8, 8),
    "SPARK": ([F.spark(0), F.spark(1), F.spark(2)], PAL_OBJ, 8, 8),
    "SPLASH": ([F.splash(0), F.splash(1), F.splash(2)], PAL_OBJ, 8, 8),
}

# origin is bottom-centre for anything that stands on the floor and centre
# for anything that flies or is thrown
MID_ORIGIN = {"CROW", "GARGOYLE", "DRONE", "ARROW", "BOLT", "SPIT",
              "CANNONBALL", "SPARK", "ROCK", "BOMB"}


def origin_of(name, img):
    if name in MID_ORIGIN:
        return (img.w // 2, img.h // 2)
    return (img.w // 2, img.h)

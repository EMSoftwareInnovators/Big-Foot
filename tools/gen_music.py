#!/usr/bin/env python3
"""BIG FOOT -- instruments, sound effects and the fifteen themes.

Everything here compiles to the byte format documented in tools/music.py and
is emitted into the audio banks (bank 1 holds the driver tables, the sound
effects and as many songs as fit; further songs spill into banks 2 and 3).
"""
from music import (Song, SFX, Instrument, Envelope, compile_pattern,
                   pattern_rows, period_table, sfx_tone, sfx_noise, decay)

AUDIO_BANK = 1
SPILL_BANKS = [2, 3]
BANK_SIZE = 8192

# ---------------------------------------------------------------------------
# envelopes
# ---------------------------------------------------------------------------
E_LEAD = Envelope([13, 13, 12, 12, 11, 11, 10])
E_PLUCK = Envelope([15, 14, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1, 0])
E_STAB = Envelope([15, 13, 10, 6, 3, 1, 0])
E_SUS = Envelope([7, 9, 10, 11, 11, 12])
E_FLAT = Envelope([11])
E_TRI = Envelope([15])
E_TRIB = Envelope([15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 0])
E_KICK = Envelope([13, 11, 8, 5, 2, 0])
E_SNARE = Envelope([13, 12, 10, 8, 6, 5, 4, 3, 2, 1, 0])
E_HAT = Envelope([6, 3, 1, 0])
E_CYM = Envelope([11, 10, 10, 9, 8, 8, 7, 6, 6, 5, 4, 4, 3, 2, 2, 1, 0])
E_BELL = Envelope([15, 13, 11, 10, 9, 8, 7, 6, 5, 4, 3, 3, 2, 2, 1, 1, 0])

A_NONE = Envelope([0], signed=True)
A_MAJ = Envelope([0, 4, 7], loop=0, signed=True)
A_MIN = Envelope([0, 3, 7], loop=0, signed=True)
A_DIM = Envelope([0, 3, 6], loop=0, signed=True)
A_VIB = Envelope([0, 0, 0, 0, 0, 0, 1, 1, 0, 0, -1, -1], loop=6, signed=True)

# ---------------------------------------------------------------------------
# instruments -- index order matters, patterns select them with '@n'
# ---------------------------------------------------------------------------
INSTRUMENTS = [
    Instrument("LEAD",   0x80, E_LEAD,  A_NONE),   # 0  round 50% lead
    Instrument("LEAD2",  0x40, E_LEAD,  A_NONE),   # 1  reedy 25% lead
    Instrument("THIN",   0x00, E_LEAD,  A_NONE),   # 2  thin 12.5% counter
    Instrument("ORGAN",  0x80, E_SUS,   A_NONE),   # 3  swelling organ
    Instrument("STAB",   0x40, E_STAB,  A_NONE),   # 4  percussive stab
    Instrument("ARPMAJ", 0x40, E_FLAT,  A_MAJ),    # 5  major chord bed
    Instrument("ARPMIN", 0x40, E_FLAT,  A_MIN),    # 6  minor chord bed
    Instrument("ARPDIM", 0x40, E_FLAT,  A_DIM),    # 7  diminished chord bed
    Instrument("TRI",    0x00, E_TRI,   A_NONE),   # 8  sustained triangle
    Instrument("TRIB",   0x00, E_TRIB,  A_NONE),   # 9  detached triangle bass
    Instrument("KICK",   0x00, E_KICK,  A_NONE),   # 10 noise: kick
    Instrument("SNARE",  0x00, E_SNARE, A_NONE),   # 11 noise: snare
    Instrument("HAT",    0x00, E_HAT,   A_NONE),   # 12 noise: hi-hat
    Instrument("CYM",    0x00, E_CYM,   A_NONE),   # 13 noise: crash
    Instrument("VIB",    0x80, E_LEAD,  A_VIB),    # 14 lead with vibrato
    Instrument("BELL",   0x00, E_BELL,  A_NONE),   # 15 bell / pluck
]

# ---------------------------------------------------------------------------
# drum notation: one character per row
# ---------------------------------------------------------------------------
DRUM = {
    "K": (10, "x13"),   # kick
    "B": (10, "x15"),   # deep kick
    "S": (11, "x8"),    # snare
    "s": (11, "x9"),    # soft snare
    "t": (11, "x11"),   # tom
    "h": (12, "x3"),    # hi-hat
    "H": (12, "x1"),    # bright hi-hat
    "C": (13, "x6"),    # crash
    "R": (13, "x2"),    # ride / sizzle
}


def drums(s, vol=15):
    """'K.h.S.h.' -> a noise-voice pattern source, one row per character."""
    out = ["L1", "v%d" % vol]
    last = None
    for c in s:
        if c in " |":
            continue
        if c == ".":
            out.append("-")
            continue
        ins, note = DRUM[c]
        if ins != last:
            out.append("@%d" % ins)
            last = ins
        out.append(note)
    return " ".join(out)


# ---------------------------------------------------------------------------
# the songs
# ---------------------------------------------------------------------------
def build_songs():
    S = {}

    # ---- 0  TITLE -- the kingdom's doom, stated plainly -----------------
    t_lead_a = ("@0 v14 L4 d5 L2 a4 L2 d5 L4 f5 L4 e5 "
                "L4 c5 L2 g4 L2 c5 L4 e5 L4 d5 "
                "L4 a4 L2 e5 L2 a4 L4 c5 L4 b4 "
                "L4 g4 L2 d5 L2 g4 L4 b4 L4 -")
    t_lead_b = ("@0 v14 L4 f5 L2 e5 L2 d5 L4 c5 L4 a4 "
                "L4 g4 L2 a4 L2 c5 L4 e5 L4 d5 "
                "L4 g5 L2 f5 L2 e5 L4 d5 L4 c5 "
                "L4 a4 L2 c5 L2 e5 L8 a4")
    t_arp_a = "@6 v11 L16 d4 @5 L16 c4 @6 L16 a3 @5 L16 g3"
    t_arp_b = "@5 v11 L16 f3 @5 L16 c4 @6 L16 a3 @6 L16 a3"
    t_bass_a = ("@8 v15 L4 d2 L4 d3 L4 a2 L4 d3 L4 c2 L4 c3 L4 g2 L4 c3 "
                "L4 a2 L4 a3 L4 e3 L4 a3 L4 g2 L4 g3 L4 d3 L4 g3")
    t_bass_b = ("@8 v15 L4 f2 L4 f3 L4 c3 L4 f3 L4 c2 L4 c3 L4 g2 L4 c3 "
                "L4 a2 L4 a3 L4 e3 L4 a3 L4 a2 L4 e3 L4 a3 L4 e3")
    t_dr_a = drums("C..K..K.S...K..h" "K..K..K.S..K.S.h"
                   "K..K..K.S...K..h" "K..K..K.S.S.S.SS")
    S[0] = Song("TITLE", 8,
                ch0=[t_lead_a, t_lead_b],
                ch1=[t_arp_a, t_arp_b],
                ch2=[t_bass_a, t_bass_b],
                ch3=[t_dr_a])

    # ---- 1  VILLAGE -- Little Kingdom, a doomed little march ------------
    v_lead_a = ("@1 v14 L2 a4 b4 L2 c5 e5 L2 d5 c5 L2 b4 - "
                "L2 f4 g4 L2 a4 c5 L4 a4 L4 - "
                "L2 g4 a4 L2 b4 d5 L2 c5 b4 L2 a4 - "
                "L2 b4 c5 L2 d5 - L4 g4 L4 -")
    v_lead_b = ("@1 v14 L2 e5 - L2 e5 d5 L2 c5 b4 L2 a4 - "
                "L2 f5 - L2 f5 e5 L2 d5 c5 L2 a4 - "
                "L2 g5 e5 L2 c5 e5 L2 g5 e5 L2 d5 c5 "
                "L4 b4 L2 d5 - L4 e5 L4 -")
    v_arp_a = "@6 v10 L16 a3 @5 L16 f3 @5 L16 c4 @5 L16 g3"
    v_arp_b = "@6 v10 L16 a3 @5 L16 f3 @5 L16 c4 @6 L16 e3"
    v_bass = ("@9 v15 L2 a2 a3 e3 a3 a2 a3 e3 a3 "
              "L2 f2 f3 c3 f3 f2 f3 c3 f3 "
              "L2 c2 c3 g2 c3 c2 c3 g2 c3 "
              "L2 g2 g3 d3 g3 g2 g3 d3 g3")
    v_dr = drums("K..h.hS.K..h.hS." * 2 + "K..h.hS.K..h.hS." + "K.KhS.S.K.KhSSSS")
    S[1] = Song("VILLAGE", 7,
                ch0=[v_lead_a, v_lead_b],
                ch1=[v_arp_a, v_arp_b],
                ch2=[v_bass],
                ch3=[v_dr])

    # ---- 2  FOREST -- Royal Forest, flowing and green --------------------
    f_lead_a = ("@14 v13 L3 e5 L3 g5 L2 b5 L4 a5 L4 - "
                "L3 d5 L3 f5 L2 a5 L4 g5 L4 - "
                "L3 c5 L3 e5 L2 g5 L4 b5 L4 a5 "
                "L2 g5 f5 e5 d5 L8 e5")
    f_lead_b = ("@14 v13 L4 b4 L4 e5 L4 g5 L4 f5 "
                "L4 e5 L4 b4 L4 c5 L4 d5 "
                "L4 e5 L4 a5 L4 g5 L4 e5 "
                "L8 d5 L8 b4")
    f_arp_a = "@6 v10 L16 e3 @5 L16 g3 @6 L16 a3 @5 L16 d4"
    f_arp_b = "@6 v10 L16 e3 @5 L16 c4 @5 L16 g3 @6 L16 b3"
    f_bass_a = ("@9 v15 L3 e2 L3 e3 L2 b2 L3 e2 L3 b2 L2 e3 "
                "L3 g2 L3 g3 L2 d3 L3 g2 L3 d3 L2 g3 "
                "L3 a2 L3 a3 L2 e3 L3 a2 L3 e3 L2 a3 "
                "L3 d3 L3 d3 L2 a2 L3 d3 L3 a2 L2 d3")
    f_bass_b = ("@9 v15 L3 e2 L3 e3 L2 b2 L3 e2 L3 b2 L2 e3 "
                "L3 c3 L3 c3 L2 g2 L3 c3 L3 g2 L2 c3 "
                "L3 g2 L3 g3 L2 d3 L3 g2 L3 d3 L2 g3 "
                "L3 b2 L3 b3 L2 f3 L3 b2 L3 b3 L2 f3")
    f_dr = drums("K..h..S..h.K..S." * 3 + "K..h..S..K.S.SSS")
    S[2] = Song("FOREST", 7,
                ch0=[f_lead_a, f_lead_b],
                ch1=[f_arp_a, f_arp_b],
                ch2=[f_bass_a, f_bass_b],
                ch3=[f_dr])

    # ---- 3  FORTRESS -- Fort Stoneheel, martial and square ---------------
    x_lead_a = ("@1 v14 L3 c5 L1 c5 L2 g4 L2 c5 L3 eb5 L1 d5 L4 c5 "
                "L3 g4 L1 g4 L2 eb4 L2 g4 L3 bb4 L1 ab4 L4 g4 "
                "L3 ab4 L1 ab4 L2 c5 L2 eb5 L3 d5 L1 c5 L4 bb4 "
                "L2 g4 ab4 bb4 c5 L4 g4 L4 -")
    x_lead_b = ("@1 v14 L2 c5 eb5 g5 eb5 L4 f5 L4 eb5 "
                "L2 d5 f5 bb5 f5 L4 g5 L4 f5 "
                "L2 eb5 g5 c6 g5 L4 ab5 L4 g5 "
                "L4 f5 L4 eb5 L4 d5 L4 c5")
    x_arp_a = "@6 v11 L8 c4 L8 c4 @6 L8 g3 L8 g3 @5 L8 ab3 L8 ab3 @5 L8 bb3 L8 bb3"
    x_arp_b = "@6 v11 L8 c4 L8 c4 @5 L8 bb3 L8 bb3 @5 L8 ab3 L8 ab3 @6 L8 g3 L8 g3"
    x_bass = ("@9 v15 L2 c2 c2 g2 c3 c2 c2 g2 bb2 "
              "L2 g2 g2 d3 g3 g2 g2 d3 f3 "
              "L2 ab2 ab2 eb3 ab3 ab2 ab2 eb3 g3 "
              "L2 bb2 bb2 f3 bb3 g2 g2 d3 g3")
    x_dr = drums("K.K.S...K.K.S..." * 3 + "K.K.S...K.KSSKSS")
    S[3] = Song("FORTRESS", 6,
                ch0=[x_lead_a, x_lead_b],
                ch1=[x_arp_a, x_arp_b],
                ch2=[x_bass],
                ch3=[x_dr])

    # ---- 4  SWAMP -- Miasma Marsh, sunken and unwell ---------------------
    m_lead_a = ("@14 v12 L6 f#4 L2 a4 L8 c#5 "
                "L6 e5 L2 c#5 L8 b4 "
                "L4 a4 L4 g4 L8 f#4 "
                "L16 -")
    m_lead_b = ("@14 v12 L6 c#5 L2 d5 L8 e5 "
                "L6 f#5 L2 e5 L8 c#5 "
                "L4 b4 L4 a4 L4 g4 L4 f#4 "
                "L16 -")
    m_arp_a = "@6 v9 L16 f#3 @7 L16 g3 @6 L16 a3 @7 L16 g3"
    m_arp_b = "@6 v9 L16 f#3 @6 L16 b3 @7 L16 d#3 @6 L16 e3"
    m_bass = ("@9 v14 L4 f#2 L4 - L4 f#2 L4 c#3 "
              "L4 d3 L4 - L4 d3 L4 a2 "
              "L4 e2 L4 - L4 e2 L4 b2 "
              "L4 f#2 L4 c#3 L4 f#2 L4 e3")
    m_dr = drums("B.......s......." * 3 + "B......ss.s.s.s.")
    S[4] = Song("SWAMP", 9,
                ch0=[m_lead_a, m_lead_b],
                ch1=[m_arp_a, m_arp_b],
                ch2=[m_bass],
                ch3=[m_dr])

    # ---- 5  FACTORY -- the King's War Factory, all machinery -------------
    k_lead_a = ("@4 v14 L2 e5 - e5 - L2 g5 - e5 - "
                "L2 d5 - d5 - L2 f5 - d5 - "
                "L2 c5 - c5 - L2 e5 - c5 - "
                "L2 b4 - d5 - L2 e5 - - -")
    k_lead_b = ("@4 v14 L2 e5 g5 b5 g5 L2 e5 g5 b5 g5 "
                "L2 d5 f5 a5 f5 L2 d5 f5 a5 f5 "
                "L2 c5 e5 g5 e5 L2 c5 e5 g5 e5 "
                "L2 b4 d5 f5 d5 L2 b4 e5 g5 b5")
    k_ost_a = ("@2 v10 L1 e3 b3 e3 b3 e3 b3 e3 b3 e3 b3 e3 b3 e3 b3 e3 b3 "
               "L1 d3 a3 d3 a3 d3 a3 d3 a3 d3 a3 d3 a3 d3 a3 d3 a3 "
               "L1 c3 g3 c3 g3 c3 g3 c3 g3 c3 g3 c3 g3 c3 g3 c3 g3 "
               "L1 b2 f#3 b2 f#3 b2 f#3 b2 f#3 b2 f#3 b2 f#3 b2 f#3 b2 f#3")
    k_bass = ("@9 v15 L2 e2 e2 e3 e2 e2 e3 e2 e2 "
              "L2 d2 d2 d3 d2 d2 d3 d2 d2 "
              "L2 c2 c2 c3 c2 c2 c3 c2 c2 "
              "L2 b2 b2 b3 b2 b2 b3 b2 d3")
    k_dr = drums("K.HhS.HhK.HhS.Hh" * 3 + "K.HhS.HhK.KSSKSS")
    S[5] = Song("FACTORY", 5,
                ch0=[k_lead_a, k_lead_b],
                ch1=[k_ost_a],
                ch2=[k_bass],
                ch3=[k_dr])

    # ---- 6  CATHEDRAL -- the Holy City, a hymn for the end of days -------
    h_lead_a = ("@3 v13 L8 d5 L8 f5 L8 e5 L8 d5 "
                "L8 a5 L8 g5 L16 f5 "
                "L8 e5 L8 d5 L8 c5 L8 d5 "
                "L16 a4 L16 -")
    h_lead_b = ("@3 v13 L8 f5 L8 g5 L8 a5 L8 d6 "
                "L8 c6 L8 bb5 L16 a5 "
                "L8 g5 L8 f5 L8 e5 L8 d5 "
                "L16 d5 L16 -")
    h_arp_a = ("@6 v10 L16 d4 L16 d4 @5 L16 f3 L16 f3 "
               "@6 L16 a3 L16 a3 @5 L16 c4 L16 c4")
    h_arp_b = ("@5 v10 L16 bb3 L16 bb3 @5 L16 f3 L16 f3 "
               "@6 L16 g3 L16 g3 @6 L16 d4 L16 d4")
    h_bass = ("@8 v15 L8 d2 L8 d3 L8 f2 L8 c3 "
              "L8 a2 L8 e3 L8 c3 L8 g2 "
              "L8 bb2 L8 f3 L8 g2 L8 d3 "
              "L8 a2 L8 a2 L16 d2")
    h_dr = drums("C..............." + "." * 111 + "R")
    S[6] = Song("CATHEDRAL", 9,
                ch0=[h_lead_a, h_lead_b],
                ch1=[h_arp_a, h_arp_b],
                ch2=[h_bass],
                ch3=[h_dr])

    # ---- 7  BATTLE -- The Last March, everything is thrown at you --------
    w_lead_a = ("@1 v15 L2 a4 e5 a5 e5 L2 a5 g5 f5 e5 "
                "L2 f4 c5 f5 c5 L2 f5 e5 d5 c5 "
                "L2 g4 d5 g5 d5 L2 g5 f5 e5 d5 "
                "L2 e5 - e5 f5 L2 g5 - a5 -")
    w_lead_b = ("@1 v15 L4 a5 L2 g5 f5 L4 e5 L2 d5 c5 "
                "L4 d5 L2 e5 f5 L4 e5 L4 - "
                "L4 c6 L2 b5 a5 L4 g5 L2 f5 e5 "
                "L4 f5 L2 g5 a5 L8 e5")
    w_arp_a = "@6 v11 L8 a3 L8 a3 @5 L8 f3 L8 f3 @5 L8 c4 L8 c4 @5 L8 g3 L8 g3"
    w_arp_b = "@6 v11 L8 a3 L8 e3 @5 L8 f3 L8 c4 @5 L8 g3 L8 d4 @6 L8 a3 L8 e4"
    w_bass = ("@9 v15 L1 a2 a2 a2 a2 e3 e3 a2 a2 a2 a2 a2 a2 e3 e3 g2 g2 "
              "L1 f2 f2 f2 f2 c3 c3 f2 f2 f2 f2 f2 f2 c3 c3 e2 e2 "
              "L1 g2 g2 g2 g2 d3 d3 g2 g2 g2 g2 g2 g2 d3 d3 f2 f2 "
              "L1 e2 e2 e2 e2 b2 b2 e2 e2 e3 e3 d3 d3 c3 c3 b2 b2")
    w_dr = drums("K.hKS.hKK.hKS.hK" * 3 + "K.hKS.hKKSKSSKSS")
    S[7] = Song("BATTLE", 5,
                ch0=[w_lead_a, w_lead_b],
                ch1=[w_arp_a, w_arp_b],
                ch2=[w_bass],
                ch3=[w_dr])

    # ---- 8  MOUNTAIN -- Mountain of the Giant, wide and cold -------------
    g_lead_a = ("@0 v14 L8 b4 L4 f#5 L4 e5 L8 d5 L8 b4 "
                "L8 e5 L4 b5 L4 a5 L16 f#5 "
                "L8 g5 L4 d5 L4 e5 L8 f#5 L8 a5 "
                "L16 b5 L8 f#5 L8 -")
    g_lead_b = ("@0 v14 L8 d6 L8 c#6 L8 b5 L8 a5 "
                "L8 g5 L8 f#5 L16 e5 "
                "L8 f#5 L8 g5 L8 a5 L8 b5 "
                "L16 f#5 L16 -")
    g_arp_a = ("@6 v10 L16 b3 L16 b3 @5 L16 g3 L16 g3 "
               "@6 L16 e3 L16 e3 @5 L16 d4 L16 d4")
    g_arp_b = ("@6 v10 L16 b3 L16 b3 @5 L16 d4 L16 d4 "
               "@6 L16 e3 L16 e3 @6 L16 f#3 L16 f#3")
    g_bass = ("@8 v15 L8 b2 L8 f#2 L8 g2 L8 d3 "
              "L8 e2 L8 b2 L8 d3 L8 a2 "
              "L8 g2 L8 d3 L8 e2 L8 b2 "
              "L8 f#2 L8 c#3 L8 b2 L8 f#3")
    g_dr = drums("K...t...S...t..h" * 7 + "K...t...S.t.SSSS")
    S[8] = Song("MOUNTAIN", 7,
                ch0=[g_lead_a, g_lead_b],
                ch1=[g_arp_a, g_arp_b],
                ch2=[g_bass],
                ch3=[g_dr])

    # ---- 9  BOSS -- something enormous is in the room --------------------
    b_lead_a = ("@1 v15 L2 d5 d5 eb5 d5 L2 c5 - d5 - "
                "L2 bb4 bb4 c5 bb4 L2 a4 - bb4 - "
                "L2 d5 d5 eb5 f5 L2 e5 - f5 - "
                "L2 g5 f5 e5 eb5 L2 d5 - - -")
    b_lead_b = ("@1 v15 L1 d5 eb5 d5 c#5 d5 eb5 d5 c#5 L4 d5 L4 a5 "
                "L1 g5 ab5 g5 f#5 g5 ab5 g5 f#5 L4 g5 L4 d5 "
                "L2 f5 - e5 - L2 eb5 - d5 - "
                "L2 c#5 d5 eb5 e5 L4 f5 L4 -")
    b_arp_a = "@6 v11 L8 d4 L8 d4 @7 L8 c#4 L8 c#4 @6 L8 d4 L8 d4 @7 L8 a3 L8 a3"
    b_arp_b = "@6 v11 L8 g3 L8 g3 @7 L8 f#3 L8 f#3 @6 L8 d4 L8 d4 @7 L8 a3 L8 a3"
    b_bass = ("@9 v15 L1 d2 d2 d3 d2 d2 d3 d2 d2 d2 d2 d3 d2 eb2 eb2 eb3 eb2 "
              "L1 bb1 bb1 bb2 bb1 bb1 bb2 bb1 bb1 a1 a1 a2 a1 a1 a2 a1 a1 "
              "L1 d2 d2 d3 d2 d2 d3 d2 d2 f2 f2 f3 f2 f2 f3 f2 f2 "
              "L1 g2 g2 g3 g2 f2 f2 f3 f2 e2 e2 e3 e2 a1 a1 a2 a2")
    b_dr = drums("KKhhS.hhKKhhS.hh" * 3 + "KKhhS.hhKSKSSKSS")
    S[9] = Song("BOSS", 5,
                ch0=[b_lead_a, b_lead_b],
                ch1=[b_arp_a, b_arp_b],
                ch2=[b_bass],
                ch3=[b_dr])

    # ---- 10 FINALBOSS -- the Left Foot ----------------------------------
    l_lead_a = ("@1 v15 L2 c5 c5 eb5 c5 g5 c5 eb5 c5 "
                "L2 c5 c5 eb5 c5 ab5 g5 f#5 f5 "
                "L2 eb5 eb5 g5 eb5 bb5 eb5 g5 eb5 "
                "L2 f5 f5 ab5 f5 c6 bb5 ab5 g5")
    l_lead_b = ("@1 v15 L2 c6 - bb5 - L2 ab5 - g5 - "
                "L2 f5 - eb5 - L2 d5 - c5 - "
                "L2 c5 d5 eb5 f5 g5 ab5 bb5 c6 "
                "L4 c6 L4 g5 L4 eb5 L4 c5")
    l_arp_a = "@6 v12 L4 c4 L4 c4 L4 c4 @7 L4 b3 @6 L4 c4 L4 c4 @7 L4 b3 L4 b3"
    l_arp_b = "@6 v12 L4 eb4 L4 eb4 @7 L4 d4 L4 d4 @6 L4 f4 L4 f4 @7 L4 e4 L4 e4"
    l_bass = ("@9 v15 L1 c2 c2 c3 c2 c2 c3 c2 c2 c2 c2 c3 c2 c2 c3 b1 b1 "
              "L1 c2 c2 c3 c2 c2 c3 c2 c2 ab1 ab1 ab2 ab1 g1 g1 g2 g1 "
              "L1 eb2 eb2 eb3 eb2 eb2 eb3 eb2 eb2 bb1 bb1 bb2 bb1 bb1 bb2 bb1 bb1 "
              "L1 f2 f2 f3 f2 f2 f3 f2 f2 g2 g2 g3 g2 g2 g3 g2 g2")
    l_dr = drums("KKhKS.hKKKhKS.hK" * 3 + "KKhKS.hKKSKSSKSS")
    S[10] = Song("FINALBOSS", 4,
                 ch0=[l_lead_a, l_lead_b],
                 ch1=[l_arp_a, l_arp_b],
                 ch2=[l_bass],
                 ch3=[l_dr])

    # ---- 11 ENDING -- the statue is whole ---------------------------------
    n_lead_a = ("@0 v14 L4 g4 L4 c5 L8 e5 L4 d5 L4 c5 L8 d5 "
                "L4 e5 L4 g5 L8 e5 L8 c5 L8 - "
                "L4 f4 L4 a4 L8 c5 L4 b4 L4 a4 L8 g4 "
                "L8 c5 L8 b4 L16 c5")
    n_lead_b = ("@0 v14 L4 c6 L4 b5 L8 a5 L4 g5 L4 e5 L8 g5 "
                "L4 f5 L4 e5 L8 d5 L8 c5 L8 - "
                "L4 d5 L4 e5 L8 f5 L4 g5 L4 a5 L8 b5 "
                "L16 c6 L16 -")
    n_arp_a = ("@5 v10 L16 c4 L16 c4 @5 L16 g3 L16 g3 "
               "@6 L16 a3 L16 a3 @5 L16 f3 L16 f3")
    n_arp_b = ("@5 v10 L16 c4 L16 c4 @5 L16 f3 L16 f3 "
               "@5 L16 g3 L16 g3 @5 L16 c4 L16 c4")
    n_bass = ("@8 v15 L8 c2 L8 g2 L8 c3 L8 g2 "
              "L8 a2 L8 e3 L8 f2 L8 c3 "
              "L8 f2 L8 c3 L8 g2 L8 d3 "
              "L8 c2 L8 g2 L16 c2")
    n_dr = drums("C..............." + "." * 80 + "h.h.h.h." * 4)
    S[11] = Song("ENDING", 9,
                 ch0=[n_lead_a, n_lead_b],
                 ch1=[n_arp_a, n_arp_b],
                 ch2=[n_bass],
                 ch3=[n_dr])

    # ---- 12 GAMEOVER -- plays once and stops ------------------------------
    o_lead = ("@0 v13 L6 d5 L2 c5 L8 bb4 L6 a4 L2 g4 L8 f4 "
              "L8 e4 L8 d4 L16 d4 L16 -")
    o_arp = "@6 v10 L16 d4 @7 L16 c4 @6 L16 a3 L16 d4 L16 -"
    o_bass = ("@8 v15 L8 d2 L8 bb1 L8 a1 L8 f1 "
              "L8 e1 L8 d1 L16 d1 L16 -")
    o_dr = drums("B...............B..............." + "." * 48)
    S[12] = Song("GAMEOVER", 12, ch0=[o_lead], ch1=[o_arp],
                 ch2=[o_bass], ch3=[o_dr])
    S[12].loop = False

    # ---- 13 CLEAR -- stage-clear fanfare, plays once ----------------------
    c_lead = ("@0 v15 L2 c5 e5 g5 L4 c6 L2 g5 L4 c6 "
              "L2 - e5 g5 L4 c6 L2 e6 L4 g6 "
              "L16 c6")
    c_arp = "@5 v11 L16 c4 L16 c4 L16 c4"
    c_bass = ("@9 v15 L2 c2 c3 c2 L4 c3 L2 g2 L4 c3 "
              "L2 - c2 c3 L4 e3 L2 g3 L4 c3 "
              "L16 c2")
    c_dr = drums("K.K.K.K.C.......K.K.K.K.C......." + "C" + "." * 15)
    S[13] = Song("CLEAR", 6, ch0=[c_lead], ch1=[c_arp],
                 ch2=[c_bass], ch3=[c_dr])
    S[13].loop = False

    # ---- 14 INTRO -- the messenger's report ------------------------------
    i_lead = ("@3 v12 L16 d4 L8 a4 L8 f4 L16 e4 L16 - "
              "L16 f4 L8 c5 L8 a4 L16 g4 L16 -")
    i_arp = "@6 v8 L16 d3 L16 d3 @7 L16 c#3 L16 - @6 L16 f3 L16 f3 @7 L16 e3 L16 -"
    i_bass = ("@8 v14 L16 d1 L16 d2 L16 a1 L16 d2 "
              "L16 f1 L16 f2 L16 e1 L16 a1")
    i_dr = drums("B..............." * 6 + "B......s.s.s.s.s" + "B...s.s.ssssssss")
    S[14] = Song("INTRO", 10, ch0=[i_lead], ch1=[i_arp],
                 ch2=[i_bass], ch3=[i_dr])

    return S


# ---------------------------------------------------------------------------
# sound effects
# ---------------------------------------------------------------------------
def build_sfx():
    fx = [None] * 23
    fx[0] = sfx_tone("JUMP", 1, 2, [60, 64, 67, 70, 72, 74, 75, 76],
                     [11, 11, 10, 10, 9, 8, 6, 3], duty=0x40)
    fx[1] = sfx_noise("LAND", 2, [13, 14, 15, 15], [8, 6, 3, 1, 0])
    fx[2] = sfx_noise("STEP", 1, [12, 13], [4, 2, 0])
    fx[3] = sfx_tone("KICK", 1, 4, [84, 78, 72, 66, 60],
                     [12, 11, 9, 6, 3, 0], duty=0x00)
    fx[4] = sfx_tone("HEAVYKICK", 1, 5, [80, 72, 64, 56, 50, 46, 44],
                     [13, 13, 11, 9, 6, 3, 1, 0], duty=0x40)
    fx[5] = sfx_noise("STOMP", 5, [15, 15, 14, 13, 12, 11],
                      [14, 13, 11, 8, 5, 3, 1, 0])
    fx[6] = sfx_noise("MEGASTOMP", 6,
                      [15, 15, 15, 15, 14, 14, 14, 13, 13, 13, 12, 12, 11, 10],
                      decay(15, 18))
    fx[7] = sfx_tone("GRAB", 1, 2, [72, 79, 79], [9, 9, 6, 3, 0], duty=0x00)
    fx[8] = sfx_tone("THROW", 1, 3, [88, 82, 76, 70, 64],
                     [10, 10, 8, 6, 3, 0], duty=0x40)
    fx[9] = sfx_noise("HIT", 3, [8, 9, 10], [11, 8, 5, 2, 0])
    fx[10] = sfx_noise("SQUASH", 4, [10, 11, 12, 13, 14],
                       [12, 11, 9, 6, 4, 2, 0])
    fx[11] = sfx_noise("BREAK", 4, [6, 9, 7, 11, 8, 12, 10, 13],
                       [12, 12, 10, 9, 8, 6, 4, 2, 0])
    fx[12] = sfx_tone("DEFLECT", 1, 4, [91, 91, 86, 86],
                      [11, 10, 8, 6, 4, 2, 0], duty=0x00)
    fx[13] = sfx_tone("PICKUP", 1, 4, [76, 76, 83, 83, 83],
                      [11, 11, 12, 10, 7, 4, 1, 0], duty=0x40)
    fx[14] = sfx_tone("SHOE", 1, 6,
                      [72, 76, 79, 84, 84, 79, 84, 88, 88, 88],
                      [12, 12, 12, 13, 13, 12, 12, 12, 9, 6, 3, 0], duty=0x40)
    fx[15] = sfx_tone("HURT", 1, 6, [72, 69, 66, 63, 60, 57, 54, 52],
                      [13, 12, 12, 11, 9, 7, 4, 2, 0], duty=0x40)
    fx[16] = sfx_tone("DIE", 1, 7,
                      list(range(76, 40, -2)),
                      [13] * 8 + decay(13, 12), duty=0x80)
    fx[17] = sfx_tone("BOSSHIT", 1, 5, [50, 56, 50, 56, 50, 44],
                      [13, 12, 11, 9, 6, 3, 0], duty=0x00)
    fx[18] = sfx_noise("BOSSDIE", 7,
                       [15, 12, 15, 13, 15, 14, 12, 15, 13, 15, 14, 15,
                        13, 15, 14, 15, 12, 15, 14, 13],
                       decay(15, 30, 0))
    fx[19] = sfx_tone("SELECT", 1, 3, [79, 79, 86, 86],
                      [10, 10, 10, 8, 5, 2, 0], duty=0x40)
    fx[20] = sfx_tone("PAUSE", 1, 3, [84, 84, 84, 84, 72, 72, 72],
                      [10, 8, 4, 0, 10, 8, 4, 0], duty=0x40)
    fx[21] = sfx_noise("SPLASH", 3, [4, 5, 6, 7, 8, 9],
                       [10, 10, 8, 7, 5, 3, 1, 0])
    fx[22] = sfx_tone("ARROW", 1, 2, [60, 68, 76, 84], [8, 7, 5, 2, 0],
                      duty=0x00)
    return fx


# ---------------------------------------------------------------------------
# emitter
# ---------------------------------------------------------------------------
class Blob:
    """A bank being filled with labelled byte runs."""

    def __init__(self, bank, limit=BANK_SIZE):
        self.bank = bank
        self.limit = limit
        self.size = 0
        self.lines = ['.segment "B%02d"\n' % bank]

    def add(self, label, data, comment=None):
        if self.size + len(data) > self.limit:
            return False
        if comment:
            self.lines.append("; %s\n" % comment)
        self.lines.append("%s:\n" % label)
        for i in range(0, len(data), 16):
            self.lines.append("        .byte " +
                              ",".join("$%02X" % b for b in data[i:i + 16]) + "\n")
        self.size += len(data)
        return True

    def text(self):
        return "".join(self.lines)


def build(write):
    songs = build_songs()
    fx = build_sfx()

    asm = ["; Generated by tools/gen_music.py -- do not edit.\n",
           '.include "constants.inc"\n\n']

    # ---- fixed-bank song directory -------------------------------------
    asm.append('.export song_bank, song_lo, song_hi\n')
    asm.append('.segment "RODATA"\n')

    banks = {AUDIO_BANK: Blob(AUDIO_BANK)}
    for b in SPILL_BANKS:
        banks[b] = Blob(b)

    # ---- driver tables --------------------------------------------------
    audio = banks[AUDIO_BANK]
    tbl = period_table()
    per = bytearray()
    for p in tbl:
        per += bytes([p & 0xFF, p >> 8])
    audio.add("period_tbl", per, "NTSC pulse periods, note 0 = C-0")

    env_bytes = {}
    env_order = []

    def env_label(env):
        key = bytes(env.bytes())
        if key not in env_bytes:
            env_bytes[key] = "aenv_%d" % len(env_bytes)
            env_order.append((env_bytes[key], key))
        return env_bytes[key]

    labels = [(env_label(i.env), env_label(i.arp)) for i in INSTRUMENTS]
    for name, data in env_order:
        audio.add(name, data)

    audio.lines.append("ins_duty:\n        .byte " +
                       ",".join("$%02X" % i.duty for i in INSTRUMENTS) + "\n")
    audio.lines.append("ins_env_lo:\n        .byte " +
                       ",".join("<%s" % l[0] for l in labels) + "\n")
    audio.lines.append("ins_env_hi:\n        .byte " +
                       ",".join(">%s" % l[0] for l in labels) + "\n")
    audio.lines.append("ins_arp_lo:\n        .byte " +
                       ",".join("<%s" % l[1] for l in labels) + "\n")
    audio.lines.append("ins_arp_hi:\n        .byte " +
                       ",".join(">%s" % l[1] for l in labels) + "\n")
    # An instrument with no pitch envelope produces a constant output once
    # its volume envelope settles, which lets the mixer skip the voice.
    audio.lines.append("ins_settle:\n        .byte " +
                       ",".join("1" if i.arp is A_NONE else "0"
                                for i in INSTRUMENTS) + "\n")
    audio.size += 6 * len(INSTRUMENTS)
    audio.lines.insert(1, ".export period_tbl, ins_duty, ins_env_lo, ins_env_hi\n"
                          ".export ins_arp_lo, ins_arp_hi, ins_settle\n"
                          ".export sfx_lo, sfx_hi\n")

    # ---- sound effects ---------------------------------------------------
    sfx_total = 0
    for i, f in enumerate(fx):
        data = f.bytes()
        sfx_total += len(data)
        audio.add("sfx_%d" % i, data, "%s -- voice %d, priority %d" %
                  (f.name, f.chan, f.prio))
    audio.lines.append("sfx_lo:\n        .byte " +
                       ",".join("<sfx_%d" % i for i in range(len(fx))) + "\n")
    audio.lines.append("sfx_hi:\n        .byte " +
                       ",".join(">sfx_%d" % i for i in range(len(fx))) + "\n")
    audio.size += 2 * len(fx)

    # ---- songs ----------------------------------------------------------
    order = [AUDIO_BANK] + SPILL_BANKS
    song_bank = [0] * 15
    song_lo = ["0"] * 15
    song_hi = ["0"] * 15
    stats = []

    for sid in range(15):
        song = songs[sid]
        pats = {}
        ch_rows = [0, 0, 0, 0]
        pat_lines = []
        size = 0
        order_lines = []
        for ch in range(4):
            entries = []
            for src in song.orders[ch]:
                data = compile_pattern(src)
                rows = pattern_rows(src)
                for b in data:
                    if 0x80 <= b <= 0xBF:
                        span = b - 0x7F
                        if span * song.speed > 255:
                            raise SystemExit(
                                "%s ch%d: length %d at speed %d overflows the "
                                "wait counter" % (song.name, ch, span, song.speed))
                ch_rows[ch] += rows
                key = bytes(data)
                if key not in pats:
                    name = "s%d_p%d" % (sid, len(pats))
                    pats[key] = name
                    pat_lines.append((name, key))
                    size += len(key)
                entries.append(pats[key])
            order_lines.append((ch, entries))
            size += 2 * (len(entries) + 1)

        # A voice may loop several times inside the longest phrase, but its
        # length has to divide that phrase or the song slowly falls apart.
        used = [r for i, r in enumerate(ch_rows) if song.orders[i]]
        if used and any(max(used) % r for r in used):
            raise SystemExit("%s: voices drift apart -- rows per voice %r"
                             % (song.name, ch_rows))
        body = bytearray()
        # assemble as text because the pattern addresses are link-time values
        lines = ["s%d_hdr:\n" % sid,
                 "        .byte %d\n" % song.speed]
        for ch in range(4):
            lines.append("        .word s%d_ord%d\n" % (sid, ch))
        for ch, entries in order_lines:
            lines.append("s%d_ord%d:\n" % (sid, ch))
            if entries:
                lines.append("        .word " + ",".join(entries) + "\n")
            tail = "$0000" if getattr(song, "loop", True) else "$FFFF"
            lines.append("        .word %s\n" % tail)
        size += 9

        blob = None
        for b in order:
            if banks[b].size + size <= banks[b].limit:
                blob = banks[b]
                break
        if blob is None:
            raise SystemExit("no audio bank has room for song %s" % song.name)
        blob.lines.extend(lines)
        for name, data in pat_lines:
            blob.add(name, data)
        blob.size += 9 + sum(2 * (len(e) + 1) for _, e in order_lines)
        song_bank[sid] = blob.bank
        song_lo[sid] = "<s%d_hdr" % sid
        song_hi[sid] = ">s%d_hdr" % sid
        stats.append("  %-10s speed %2d  %3d bytes  bank %d\n"
                     % (song.name, song.speed, size, blob.bank))
        _ = body

    asm.append("song_bank:\n        .byte " +
               ",".join(str(b) for b in song_bank) + "\n")
    asm.append("song_lo:\n        .byte " + ",".join(song_lo) + "\n")
    asm.append("song_hi:\n        .byte " + ",".join(song_hi) + "\n\n")
    for b in order:
        if banks[b].size:
            asm.append(banks[b].text())

    write("music_data.s", "".join(asm))
    write("music.inc", "; music ids are declared in constants.inc\n")

    log = ["music: %d instruments, %d envelopes, %d effects (%d bytes)\n"
           % (len(INSTRUMENTS), len(env_order), len(fx), sfx_total)]
    log += stats
    for b in order:
        if banks[b].size:
            log.append("  bank %d: %d/%d bytes\n"
                       % (b, banks[b].size, banks[b].limit))
    return "".join(log)


if __name__ == "__main__":
    import os
    OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "..", "data", "generated")

    def w(name, text):
        open(os.path.join(OUT, name), "w").write(text)
        return len(text)

    print(build(w))

#!/usr/bin/env python3
"""BIG FOOT music format -- composition helpers and byte-stream compiler.

The NES sound driver (src/audio.s) plays four voices:

    0  pulse 1      1  pulse 2      2  triangle      3  noise

Every voice reads an *order list* of pattern pointers; every pattern is a
byte stream of events.  Notes are indices into a 108-entry NTSC period
table where 0 = C-0, so 48 = C-4 and 57 = A-4 (440 Hz).

Pattern byte stream
    $00..$5F   note on, note index 0..95
    $60        rest (note off)
    $61        tie  (hold the sounding note for another span)
    $80..$BF   set note length to (b - $80) + 1 rows
    $C0..$CF   set instrument
    $D0..$DF   set channel volume
    $E0        end of pattern -- fetch the next order entry

Order list
    a sequence of little-endian pattern addresses terminated by $0000,
    which loops back to the start of the list.

Envelopes
    volume : bytes $00..$0F, $FD <index> = loop, $FE = hold last value
    arpeggio/pitch : signed semitone offsets, $7D <index> = loop, $7E = hold
"""

CPU_HZ = 1789773.0

NOTE_REST = 0x60
NOTE_TIE = 0x61
PAT_END = 0xE0

ENV_LOOP = 0xFD
ENV_HOLD = 0xFE
ARP_LOOP = 0x7D
ARP_HOLD = 0x7E

NOTE_NAMES = {"c": 0, "d": 2, "e": 4, "f": 5, "g": 7, "a": 9, "b": 11}


def period_table(n=108):
    """NTSC pulse periods for note indices 0..n-1 (0 = C-0)."""
    out = []
    for i in range(n):
        freq = 440.0 * (2.0 ** ((i - 57) / 12.0))
        p = int(round(CPU_HZ / (16.0 * freq))) - 1
        out.append(max(8, min(2047, p)))
    return out


def note_index(tok):
    """'c4' 'c#4' 'cs4' 'eb3' -> note index.  Raises on bad input."""
    t = tok.lower()
    if t[0] not in NOTE_NAMES:
        raise ValueError("bad note %r" % tok)
    v = NOTE_NAMES[t[0]]
    i = 1
    while i < len(t) and t[i] in "#sb":
        v += 1 if t[i] in "#s" else -1
        i += 1
    if i >= len(t):
        raise ValueError("bad note %r" % tok)
    v += 12 * int(t[i:])
    if not 0 <= v <= 95:
        raise ValueError("note %r out of range" % tok)
    return v


def note_name(idx):
    names = ["C-", "C#", "D-", "D#", "E-", "F-", "F#", "G-", "G#", "A-", "A#", "B-"]
    return "%s%d" % (names[idx % 12], idx // 12)


# ---------------------------------------------------------------------------
# pattern source language
# ---------------------------------------------------------------------------
# Whitespace separated tokens:
#     @n      select instrument n
#     vN      set volume N (0..15)
#     LN      set default note length to N rows
#     c4      note (optionally 'c4/8' to give this note a length of 8 rows)
#     xN      raw noise period index N (noise voice only)
#     -       rest for the default length ('-/4' for an explicit length)
#     =       tie: hold the sounding note for another default length
#     |       bar separator, ignored (readability only)
#
# A leading '*n' on the whole pattern repeats the rest of it n times.


def compile_pattern(src, transpose=0):
    out = bytearray()
    cur_len = None
    toks = src.replace("|", " ").split()
    i = 0
    if toks and toks[0].startswith("*"):
        rep = int(toks[0][1:])
        toks = toks[1:] * rep
    while i < len(toks):
        t = toks[i]
        i += 1
        if t[0] == "@":
            out.append(0xC0 | (int(t[1:]) & 0x0F))
            continue
        if t[0] in "vV":
            out.append(0xD0 | (int(t[1:]) & 0x0F))
            continue
        if t[0] in "lL":
            n = int(t[1:])
            cur_len = n
            out.append(0x80 + (n - 1))
            continue
        span = None
        if "/" in t:
            t, s = t.split("/")
            span = int(s)
        if span is not None and span != cur_len:
            out.append(0x80 + (span - 1))
            cur_len = span
        if cur_len is None:
            raise ValueError("no length set before %r" % t)
        if t == "-":
            out.append(NOTE_REST)
        elif t == "=":
            out.append(NOTE_TIE)
        elif t[0] in "xX":
            out.append(int(t[1:]) & 0x0F)
        else:
            out.append(note_index(t) + transpose)
    out.append(PAT_END)
    return bytes(out)


def pattern_rows(src):
    """Row count of a pattern source, for sanity checking bar lengths."""
    rows = 0
    cur = None
    toks = src.replace("|", " ").split()
    if toks and toks[0].startswith("*"):
        toks = toks[1:] * int(toks[0][1:])
    for t in toks:
        if t[0] in "@vV":
            continue
        if t[0] in "lL":
            cur = int(t[1:])
            continue
        if "/" in t:
            t, s = t.split("/")
            cur = int(s)
        rows += cur
    return rows


# ---------------------------------------------------------------------------
# instruments and envelopes
# ---------------------------------------------------------------------------
class Envelope:
    """A volume or pitch envelope.  `loop` is an index into `values`."""

    def __init__(self, values, loop=None, hold=True, signed=False):
        self.values = list(values)
        self.loop = loop
        self.hold = hold
        self.signed = signed

    def bytes(self):
        out = []
        for v in self.values:
            if self.signed:
                out.append(v & 0xFF)
            else:
                out.append(v & 0x0F)
        if self.loop is not None:
            out.append(ARP_LOOP if self.signed else ENV_LOOP)
            out.append(self.loop)
        else:
            out.append(ARP_HOLD if self.signed else ENV_HOLD)
        return bytes(out)


class Instrument:
    def __init__(self, name, duty, env, arp=None):
        self.name = name
        self.duty = duty          # pulse: $00/$40/$80/$C0 -- noise: $00/$80
        self.env = env
        self.arp = arp


# handy envelope shapes -----------------------------------------------------
def decay(start, length, floor=0):
    """Linear decay from `start` down to `floor` over `length` frames."""
    if length <= 1:
        return [start]
    step = (start - floor) / float(length - 1)
    return [max(floor, int(round(start - step * i))) for i in range(length)]


def pluck(peak, hold_v, attack=0):
    v = list(range(1, peak + 1)) if attack else [peak]
    v += [peak, peak - 1, peak - 2]
    v = [max(0, x) for x in v]
    return v + [hold_v]


# ---------------------------------------------------------------------------
# songs
# ---------------------------------------------------------------------------
class Song:
    def __init__(self, name, speed, ch0=(), ch1=(), ch2=(), ch3=(), transpose=0):
        self.name = name
        self.speed = speed
        self.orders = [list(ch0), list(ch1), list(ch2), list(ch3)]
        self.transpose = transpose


class SFX:
    """A sound effect: a list of (reg0, period_lo, period_hi) frames."""

    def __init__(self, name, chan, prio, frames):
        self.name = name
        self.chan = chan
        self.prio = prio
        self.frames = frames

    def bytes(self):
        out = bytearray([self.chan, self.prio])
        prev = None
        run = 0
        for f in self.frames:
            if f == prev:
                run += 1
                if run == 255:
                    out += bytes([0xFE, run])
                    run = 0
                continue
            if run:
                out += bytes([0xFE, run])
                run = 0
            out += bytes(f)
            prev = f
        if run:
            out += bytes([0xFE, run])
        out.append(0xFF)
        return bytes(out)


def sfx_tone(name, chan, prio, notes, vols, duty=0x80, periods=None):
    """Build a tonal effect from parallel note / volume frame lists."""
    tbl = period_table()
    frames = []
    n = max(len(notes) if notes else 0, len(vols))
    for i in range(n):
        v = vols[min(i, len(vols) - 1)]
        if periods is not None:
            p = periods[min(i, len(periods) - 1)]
        else:
            idx = notes[min(i, len(notes) - 1)]
            p = tbl[max(0, min(107, idx))]
        frames.append((duty | 0x30 | (v & 0x0F), p & 0xFF, 0x08 | (p >> 8)))
    return SFX(name, chan, prio, frames)


def sfx_noise(name, prio, periods, vols, mode=0x00):
    frames = []
    n = max(len(periods), len(vols))
    for i in range(n):
        v = vols[min(i, len(vols) - 1)]
        p = periods[min(i, len(periods) - 1)]
        frames.append((0x30 | (v & 0x0F), mode | (p & 0x0F), 0x08))
    return SFX(name, 3, prio, frames)

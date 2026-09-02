#!/usr/bin/env python3
"""Turn an -apulog register trace back into a readable score.

    build/nesemu build/big_foot.nes -frames 400 -apulog build/apu.txt 0
    python3 tools/check_music.py build/apu.txt

Prints, for every voice, the notes it actually played: pitch, the frame the
note started, and how long it was held.  This is how the driver and the song
data are verified without being able to listen to the ROM.
"""
import sys
from music import period_table, note_name

CPU = 1789773.0
VOICE = {0x4000: 0, 0x4004: 1, 0x4008: 2, 0x400C: 3}
NAMES = ["pulse1", "pulse2", "tri   ", "noise "]


def nearest_note(period, triangle):
    if period < 1:
        return "?"
    hz = CPU / ((32.0 if triangle else 16.0) * (period + 1))
    if hz <= 0:
        return "?"
    import math
    n = int(round(57 + 12 * math.log(hz / 440.0, 2)))
    if not 0 <= n <= 119:
        return "?%.0fHz" % hz
    return "%s(%5.1fHz)" % (note_name(n), hz)


def main(path, limit=200):
    vol = [0] * 4
    plo = [0] * 4
    phi = [0] * 4
    cur = [None] * 4
    start = [0] * 4
    events = [[] for _ in range(4)]
    frame = 0

    def state(v):
        if vol[v] == 0:
            return None
        if v == 3:
            return "noise p%d%s" % (plo[v] & 0x0F, " short" if plo[v] & 0x80 else "")
        p = plo[v] | ((phi[v] & 7) << 8)
        return nearest_note(p, v == 2)

    def settle(v):
        st = state(v)
        if st != cur[v]:
            if cur[v] is not None:
                events[v].append((start[v], frame - start[v], cur[v]))
            cur[v] = st
            start[v] = frame

    for line in open(path):
        f, a, val = line.split()
        frame = int(f)
        a = int(a, 16)
        val = int(val, 16)
        base = a & 0xFFFC
        if base not in VOICE:
            continue
        v = VOICE[base]
        off = a - base
        if off == 0:
            if v == 2:
                vol[v] = 15 if val == 0xFF else 0
            else:
                vol[v] = val & 0x0F
        elif off == 2:
            plo[v] = val
        elif off == 3:
            phi[v] = val
        settle(v)
    for v in range(4):
        if cur[v] is not None:
            events[v].append((start[v], frame - start[v], cur[v]))

    for v in range(4):
        print("--- %s : %d note events" %
              (NAMES[v], len([e for e in events[v] if e[1] > 0])))
        # A register pair is written low byte first, so the trace briefly
        # shows a nonsense pitch between the two writes; those zero-length
        # states are an artefact of sampling per write, not of the driver.
        real = [e for e in events[v] if e[1] > 0]
        for e in real[:limit]:
            print("    f%-6d %3d frames  %s" % e)


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 200)

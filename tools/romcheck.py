#!/usr/bin/env python3
"""Validate the iNES header, size and vectors of the built ROM."""
import sys

def main(path):
    d = open(path, "rb").read()
    ok = True
    if d[:4] != b"NES\x1a":
        print("FAIL: bad iNES magic"); ok = False
    prg = d[4] * 16384
    chr_ = d[5] * 8192
    mapper = (d[6] >> 4) | (d[7] & 0xF0)
    want = 16 + prg + chr_
    print("iNES : mapper %d, PRG %d KiB, CHR %d KiB, mirroring %s"
          % (mapper, prg // 1024, chr_ // 1024,
             "vertical" if (d[6] & 1) == 0 else "horizontal"))
    if len(d) != want:
        print("FAIL: file is %d bytes, header implies %d" % (len(d), want)); ok = False
    # vectors live in the last 6 bytes of PRG
    v = 16 + prg - 6
    nmi = d[v] | (d[v + 1] << 8)
    res = d[v + 2] | (d[v + 3] << 8)
    irq = d[v + 4] | (d[v + 5] << 8)
    print("vectors: NMI $%04X  RESET $%04X  IRQ $%04X" % (nmi, res, irq))
    for nm, a in (("NMI", nmi), ("RESET", res), ("IRQ", irq)):
        if a < 0xE000:
            print("FAIL: %s vector $%04X is not in the fixed bank" % (nm, a)); ok = False
    print("ROM  : %s (%d bytes)  %s" % (path, len(d), "OK" if ok else "PROBLEMS"))
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))

#!/usr/bin/env python3
"""CHR-ROM allocation for BIG FOOT.

The MMC3 maps CHR in 1 KiB units (2 KiB for registers R0/R1), so the ROM is
managed as a list of 1 KiB banks and every allocation records what it holds
for the bank map printed at the end of the build.
"""
from nesart import TileSet, tile_to_chr, Img

BANK_KB = 256           # 256 KiB of CHR-ROM (the MMC3 maximum)


class ChrRom(object):
    def __init__(self, kb=BANK_KB):
        self.kb = kb
        self.data = bytearray(kb * 1024)
        self.cursor = 0
        self.map = []

    def _alloc(self, n, align):
        while self.cursor % align:
            self.cursor += 1
        start = self.cursor
        if start + n > self.kb:
            raise RuntimeError("CHR-ROM overflow (needed bank %d of %d)"
                               % (start + n, self.kb))
        self.cursor += n
        return start

    def add_2k(self, name, tiles):
        """tiles: list of Img (max 128).  Returns the 1 KiB bank index."""
        if len(tiles) > 128:
            raise RuntimeError("%s: %d tiles in a 2 KiB bank" % (name, len(tiles)))
        b = self._alloc(2, 2)
        off = b * 1024
        for i, t in enumerate(tiles):
            self.data[off + i * 16:off + i * 16 + 16] = tile_to_chr(t)
        self.map.append((b, 2, name, len(tiles)))
        return b

    def add_1k(self, name, tiles):
        if len(tiles) > 64:
            raise RuntimeError("%s: %d tiles in a 1 KiB bank" % (name, len(tiles)))
        b = self._alloc(1, 1)
        off = b * 1024
        for i, t in enumerate(tiles):
            self.data[off + i * 16:off + i * 16 + 16] = tile_to_chr(t)
        self.map.append((b, 1, name, len(tiles)))
        return b

    def used(self):
        return self.cursor

    def report(self):
        out = ["CHR-ROM bank map (1 KiB units)\n"]
        for b, n, name, cnt in self.map:
            out.append("  $%02X +%d  %-28s %3d tiles\n" % (b, n, name, cnt))
        out.append("  used %d / %d KiB\n" % (self.cursor, self.kb))
        return "".join(out)


# ---------------------------------------------------------------------------
class FramePacker(object):
    """Packs a stream of rendered frames into 128-tile sprite banks."""

    def __init__(self, chr_rom, prefix, capacity=128, reserve_top=None):
        """reserve_top: an Img forced into the last slot of every bank
        (used for the opaque sprite-0 tile that drives the HUD split)."""
        self.reserve_top = reserve_top
        self.chr = chr_rom
        self.prefix = prefix
        self.capacity = capacity
        self.banks = []          # list of TileSet
        self.frames = []         # (bank_slot, metasprite bytes)
        if reserve_top is not None:
            self.capacity = capacity - 1
        self._new_bank()

    def _new_bank(self):
        ts = TileSet("%s%d" % (self.prefix, len(self.banks)),
                     capacity=self.capacity)
        self.banks.append(ts)
        return ts

    def add(self, img, ox, oy, attr=0):
        """Cut `img` into a grid metasprite and place its tiles in a bank."""
        cells, x0, y0, w, h = grid_cells(img)
        ts = self.banks[-1]
        if not _fits(ts, cells):
            ts = self._new_bank()
            if not _fits(ts, cells):
                raise RuntimeError("frame does not fit an empty bank")
        idx = []
        for c in cells:
            idx.append(0 if c is None else ts.add(c))
        ms = bytearray()
        ms.append((x0 * 8 - ox) & 0xFF)
        ms.append((y0 * 8 - oy) & 0xFF)
        ms.append(w)
        ms.append(h)
        ms.append(attr)
        ms += bytes(idx)
        self.frames.append((len(self.banks) - 1, bytes(ms)))
        return len(self.frames) - 1

    def flush(self, names=None):
        """Write the banks into CHR-ROM; returns a list of 1 KiB bank indices."""
        out = []
        for i, ts in enumerate(self.banks):
            nm = names[i] if names and i < len(names) else "%s%d" % (self.prefix, i)
            tiles = list(ts.tiles)
            if self.reserve_top is not None:
                while len(tiles) < 127:
                    tiles.append(Img(8, 8))
                tiles.append(self.reserve_top)
            out.append(self.chr.add_2k(nm, tiles))
        self.bank_ids = out
        return out

    def frame_bank_bytes(self):
        return bytes(self.bank_ids[b] for b, _ in self.frames)

    def tile_counts(self):
        return [len(ts) for ts in self.banks]


def _fits(ts, cells):
    need = 0
    seen = set()
    for c in cells:
        if c is None:
            continue
        k = TileSet.key(c)
        if k in ts.index or k in seen:
            continue
        seen.add(k)
        need += 1
    return len(ts) + need <= ts.capacity


def grid_cells(img):
    """Crop an image to the 8x8 grid cells it actually uses.
    Returns (cells, x0, y0, w, h) where cells is row-major, None = blank."""
    bb = img.bbox()
    if bb is None:
        return ([None], 0, 0, 1, 1)
    bx0, by0, bx1, by1 = bb
    x0, y0 = bx0 // 8, by0 // 8
    x1, y1 = bx1 // 8, by1 // 8
    w, h = x1 - x0 + 1, y1 - y0 + 1
    cells = []
    for ty in range(y0, y1 + 1):
        for tx in range(x0, x1 + 1):
            t = img.sub(tx * 8, ty * 8, 8, 8)
            cells.append(None if t.is_empty() else t)
    return (cells, x0, y0, w, h)

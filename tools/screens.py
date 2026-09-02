#!/usr/bin/env python3
"""Full-screen background pictures.

A screen is a 256x240 image of colour indices 0..3 plus a per-16x16-cell
palette assignment.  Compiling one deduplicates its 8x8 tiles into three
1 KiB CHR banks (192 tiles, mapped at $1000/$1400/$1800) and run-length
encodes the nametable and attribute table.  The fourth background bank stays
on the shared HUD/font tiles so screens can print text with the same font
the status bar uses.

Colour 0 is the PPU backdrop and is therefore the same in every palette;
every screen here uses black for it, which is why the art is built as
silhouettes against a night sky.
"""
from nesart import Img

W, H = 256, 240
COLS, ROWS = 32, 30
PIC_TILES = 192                 # $00..$BF; $C0..$FF belongs to the font bank
OVERFLOW_OK = False             # set by the tile-budget report


class Screen(object):
    def __init__(self, name):
        self.name = name
        self.img = Img(W, H, 0)
        self.attr = [[0] * 16 for _ in range(15)]

    # -- palette assignment -------------------------------------------------
    def region(self, x0, y0, x1, y1, pal):
        """Assign a palette to every 16x16 attribute cell the box touches."""
        for cy in range(max(0, y0 // 16), min(15, y1 // 16) + 1):
            for cx in range(max(0, x0 // 16), min(15, x1 // 16) + 1):
                self.attr[cy][cx] = pal

    # -- compilation --------------------------------------------------------
    def compile(self):
        """-> (tiles, nametable_rle, attr_rle) with the tiles as 8x8 Imgs."""
        tiles = []
        index = {}
        nt = bytearray()
        for ty in range(ROWS):
            for tx in range(COLS):
                key = bytes(self.img.get(tx * 8 + x, ty * 8 + y)
                            for y in range(8) for x in range(8))
                if key not in index:
                    if len(tiles) >= PIC_TILES and not OVERFLOW_OK:
                        raise SystemExit(
                            "%s needs more than %d unique tiles"
                            % (self.name, PIC_TILES))
                    index[key] = len(tiles)
                    tiles.append(self.img.sub(tx * 8, ty * 8, 8, 8))
                nt.append(index[key])

        at = bytearray()
        for by in range(0, 15, 2):
            for bx in range(0, 16, 2):
                v = 0
                for i, (dx, dy) in enumerate(((0, 0), (1, 0), (0, 1), (1, 1))):
                    cx, cy = bx + dx, by + dy
                    p = self.attr[cy][cx] if cy < 15 and cx < 16 else 0
                    v |= (p & 3) << (i * 2)
                at.append(v)
        return tiles, rle(nt), rle(at)


def rle(data):
    """Mixed literal/run coding.

        $00        end of stream
        $01..$7F   copy this many bytes literally
        $81..$FF   repeat the next byte (b & $7F) times

    Pictures are mostly detail with occasional flat sky, so a pure run
    encoder made the title screen *larger* than the raw nametable.
    """
    out = bytearray()
    i = 0
    lit = bytearray()

    def flush():
        while lit:
            n = min(127, len(lit))
            out.append(n)
            out.extend(lit[:n])
            del lit[:n]

    while i < len(data):
        n = 1
        while i + n < len(data) and data[i + n] == data[i] and n < 127:
            n += 1
        if n >= 3:
            flush()
            out.append(0x80 | n)
            out.append(data[i])
            i += n
        else:
            lit.extend(data[i:i + n])
            i += n
    flush()
    out.append(0)
    return bytes(out)


def unrle(data):
    """Reference decoder, used by the build to check the encoder."""
    out = bytearray()
    i = 0
    while data[i]:
        b = data[i]
        i += 1
        if b & 0x80:
            out.extend(bytes([data[i]]) * (b & 0x7F))
            i += 1
        else:
            out.extend(data[i:i + b])
            i += b
    return bytes(out)


# ---------------------------------------------------------------------------
# drawing helpers that work in screen pixels
# ---------------------------------------------------------------------------
def paste_mask(img, mask, ox, oy, colours, outline=True, bevel=4):
    """Draw a mask at (ox, oy) with a dark rim, a flat body and a top bevel.

    The bevel is measured down from the topmost filled pixel of each column,
    which keeps the light on the upper surface.  Shading from a diagonal
    neighbour instead lights the underside of anything with a hollow in it,
    and the foot has an arch.
    """
    dark, mid, light = colours
    top = []
    for x in range(mask.w):
        t = mask.h
        for y in range(mask.h):
            if mask.get(x, y):
                t = y
                break
        top.append(t)
    for y in range(mask.h):
        for x in range(mask.w):
            if not mask.get(x, y):
                continue
            px, py = ox + x, oy + y
            if not (0 <= px < W and 0 <= py < H):
                continue
            edge = outline and (not mask.get(x - 1, y) or not mask.get(x + 1, y)
                                or not mask.get(x, y - 1)
                                or not mask.get(x, y + 1))
            if edge:
                img.put(px, py, dark)
            elif y - top[x] <= bevel:
                img.put(px, py, light)
            else:
                img.put(px, py, mid)

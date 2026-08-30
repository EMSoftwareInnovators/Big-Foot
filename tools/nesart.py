#!/usr/bin/env python3
"""
BIG FOOT -- NES art library.

Everything the game draws is produced by this module: there is no external
image editor in the pipeline.  Art is described with shapes and masks, then
rasterised to 2bpp NES pattern data with automatic tile de-duplication.

Colour indices inside an Img are 0..3 and mean "entry N of whichever 4-colour
palette this graphic is drawn with".  Index 0 is transparent for sprites and
the universal background colour for tiles.
"""
import os
import struct
import zlib

# ---------------------------------------------------------------------------
# NES master palette (2C02, one common approximation) for PNG previews only.
# ---------------------------------------------------------------------------
NES_RGB = [
    (0x62,0x62,0x62),(0x00,0x1F,0xB2),(0x24,0x04,0xC8),(0x52,0x00,0xB2),
    (0x73,0x00,0x76),(0x80,0x00,0x24),(0x73,0x0B,0x00),(0x52,0x28,0x00),
    (0x24,0x44,0x00),(0x00,0x57,0x00),(0x00,0x5C,0x00),(0x00,0x53,0x24),
    (0x00,0x3C,0x76),(0x00,0x00,0x00),(0x00,0x00,0x00),(0x00,0x00,0x00),
    (0xAB,0xAB,0xAB),(0x0D,0x57,0xFF),(0x4B,0x30,0xFF),(0x8A,0x13,0xFF),
    (0xBC,0x08,0xD6),(0xD2,0x12,0x69),(0xC7,0x2E,0x00),(0x9D,0x54,0x00),
    (0x60,0x7B,0x00),(0x20,0x98,0x00),(0x00,0xA3,0x00),(0x00,0x99,0x42),
    (0x00,0x7D,0xB4),(0x00,0x00,0x00),(0x00,0x00,0x00),(0x00,0x00,0x00),
    (0xFF,0xFF,0xFF),(0x53,0xAE,0xFF),(0x90,0x85,0xFF),(0xD3,0x65,0xFF),
    (0xFF,0x57,0xFF),(0xFF,0x5D,0xCF),(0xFF,0x77,0x57),(0xFA,0x9E,0x00),
    (0xBD,0xC7,0x00),(0x7A,0xE7,0x00),(0x43,0xF6,0x11),(0x26,0xEF,0x7E),
    (0x2C,0xD5,0xF6),(0x4E,0x4E,0x4E),(0x00,0x00,0x00),(0x00,0x00,0x00),
    (0xFF,0xFF,0xFF),(0xB6,0xE1,0xFF),(0xCE,0xD1,0xFF),(0xE9,0xC3,0xFF),
    (0xFF,0xBC,0xFF),(0xFF,0xBD,0xF4),(0xFF,0xC6,0xC3),(0xFF,0xD5,0x9A),
    (0xE9,0xE6,0x81),(0xCE,0xF4,0x81),(0xB6,0xFB,0x9A),(0xA9,0xFA,0xC3),
    (0xA9,0xF0,0xF4),(0xB8,0xB8,0xB8),(0x00,0x00,0x00),(0x00,0x00,0x00),
]


# ---------------------------------------------------------------------------
class Img(object):
    """An indexed bitmap with colour values 0..3."""

    def __init__(self, w, h, fill=0):
        self.w = w
        self.h = h
        self.px = [[fill] * w for _ in range(h)]

    def clone(self):
        n = Img(self.w, self.h)
        n.px = [row[:] for row in self.px]
        return n

    def get(self, x, y):
        if 0 <= x < self.w and 0 <= y < self.h:
            return self.px[y][x]
        return 0

    def put(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.px[y][x] = c

    def rect(self, x0, y0, x1, y1, c):
        for y in range(max(0, y0), min(self.h, y1 + 1)):
            for x in range(max(0, x0), min(self.w, x1 + 1)):
                self.px[y][x] = c

    def hline(self, x0, x1, y, c):
        if x1 < x0:
            x0, x1 = x1, x0
        for x in range(max(0, x0), min(self.w, x1 + 1)):
            if 0 <= y < self.h:
                self.px[y][x] = c

    def vline(self, x, y0, y1, c):
        if y1 < y0:
            y0, y1 = y1, y0
        for y in range(max(0, y0), min(self.h, y1 + 1)):
            if 0 <= x < self.w:
                self.px[y][x] = c

    def line(self, x0, y0, x1, y1, c):
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            self.put(x0, y0, c)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def blit(self, other, ox, oy, transparent=0):
        for y in range(other.h):
            for x in range(other.w):
                c = other.px[y][x]
                if c != transparent:
                    self.put(x + ox, y + oy, c)

    def flip_h(self):
        n = Img(self.w, self.h)
        for y in range(self.h):
            n.px[y] = self.px[y][::-1]
        return n

    def sub(self, x0, y0, w, h):
        n = Img(w, h)
        for y in range(h):
            for x in range(w):
                n.px[y][x] = self.get(x0 + x, y0 + y)
        return n

    def replace(self, a, b):
        for y in range(self.h):
            for x in range(self.w):
                if self.px[y][x] == a:
                    self.px[y][x] = b

    def shift(self, dx, dy):
        n = Img(self.w, self.h)
        for y in range(self.h):
            for x in range(self.w):
                n.px[y][x] = self.get(x - dx, y - dy)
        return n

    def is_empty(self):
        for row in self.px:
            for c in row:
                if c:
                    return False
        return True

    def bbox(self):
        x0, y0, x1, y1 = self.w, self.h, -1, -1
        for y in range(self.h):
            for x in range(self.w):
                if self.px[y][x]:
                    x0 = min(x0, x); y0 = min(y0, y)
                    x1 = max(x1, x); y1 = max(y1, y)
        if x1 < 0:
            return None
        return (x0, y0, x1, y1)


# ---------------------------------------------------------------------------
class Mask(object):
    """A boolean coverage mask used to build shaded blobs."""

    def __init__(self, w, h):
        self.w = w
        self.h = h
        self.m = [[0] * w for _ in range(h)]

    def clone(self):
        n = Mask(self.w, self.h)
        n.m = [row[:] for row in self.m]
        return n

    def get(self, x, y):
        if 0 <= x < self.w and 0 <= y < self.h:
            return self.m[y][x]
        return 0

    def put(self, x, y, v=1):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.m[y][x] = v

    def ellipse(self, cx, cy, rx, ry, v=1):
        if rx <= 0 or ry <= 0:
            return
        for y in range(int(cy - ry - 1), int(cy + ry + 2)):
            for x in range(int(cx - rx - 1), int(cx + rx + 2)):
                dx = (x + 0.5 - cx) / float(rx)
                dy = (y + 0.5 - cy) / float(ry)
                if dx * dx + dy * dy <= 1.0:
                    self.put(x, y, v)

    def poly(self, pts, v=1):
        if len(pts) < 3:
            return
        ys = [p[1] for p in pts]
        y0 = max(0, int(min(ys)))
        y1 = min(self.h - 1, int(max(ys)) + 1)
        for y in range(y0, y1 + 1):
            yc = y + 0.5
            xs = []
            n = len(pts)
            for i in range(n):
                ax, ay = pts[i]
                bx, by = pts[(i + 1) % n]
                if (ay <= yc < by) or (by <= yc < ay):
                    t = (yc - ay) / float(by - ay)
                    xs.append(ax + t * (bx - ax))
            xs.sort()
            for i in range(0, len(xs) - 1, 2):
                for x in range(int(round(xs[i])), int(round(xs[i + 1]))):
                    self.put(x, y, v)

    def rect(self, x0, y0, x1, y1, v=1):
        for y in range(int(y0), int(y1) + 1):
            for x in range(int(x0), int(x1) + 1):
                self.put(x, y, v)

    def union(self, other):
        for y in range(self.h):
            for x in range(self.w):
                if other.m[y][x]:
                    self.m[y][x] = 1
        return self

    def subtract(self, other):
        for y in range(self.h):
            for x in range(self.w):
                if other.m[y][x]:
                    self.m[y][x] = 0
        return self

    def intersect(self, other):
        for y in range(self.h):
            for x in range(self.w):
                if not other.m[y][x]:
                    self.m[y][x] = 0
        return self

    def erode(self, n=1):
        cur = self
        for _ in range(n):
            nx = Mask(self.w, self.h)
            for y in range(self.h):
                for x in range(self.w):
                    if (cur.get(x, y) and cur.get(x - 1, y) and cur.get(x + 1, y)
                            and cur.get(x, y - 1) and cur.get(x, y + 1)):
                        nx.m[y][x] = 1
            cur = nx
        return cur

    def dilate(self, n=1):
        cur = self
        for _ in range(n):
            nx = Mask(self.w, self.h)
            for y in range(self.h):
                for x in range(self.w):
                    if (cur.get(x, y) or cur.get(x - 1, y) or cur.get(x + 1, y)
                            or cur.get(x, y - 1) or cur.get(x, y + 1)):
                        nx.m[y][x] = 1
            cur = nx
        return cur

    def shift(self, dx, dy):
        n = Mask(self.w, self.h)
        for y in range(self.h):
            for x in range(self.w):
                n.m[y][x] = self.get(x - dx, y - dy)
        return n

    def to_img(self, c=1):
        im = Img(self.w, self.h)
        for y in range(self.h):
            for x in range(self.w):
                if self.m[y][x]:
                    im.px[y][x] = c
        return im


def shade_mask(mask, dark=1, mid=2, light=3, light_dx=-1, light_dy=-1,
               light_erode=3, outline=True):
    """Standard blob shading: dark rim, mid body, light lobe toward the
    light source.  Produces the chunky-but-readable look used throughout."""
    img = Img(mask.w, mask.h)
    body = mask
    inner = body.erode(1)
    hi = body.erode(light_erode).shift(light_dx, light_dy)
    hi.intersect(inner)
    for y in range(mask.h):
        for x in range(mask.w):
            if not body.m[y][x]:
                continue
            if outline and not inner.m[y][x]:
                img.px[y][x] = dark
            elif hi.m[y][x]:
                img.px[y][x] = light
            else:
                img.px[y][x] = mid
    return img


# ---------------------------------------------------------------------------
def img_from_ascii(rows, mapping=None):
    """Build an Img from a list of strings.  Default mapping:
       '.' or ' ' -> 0, '1'/'o' -> 1, '2'/'x' -> 2, '3'/'#' -> 3"""
    if mapping is None:
        mapping = {'.': 0, ' ': 0, '0': 0,
                   '1': 1, 'o': 1, '-': 1,
                   '2': 2, 'x': 2, '+': 2,
                   '3': 3, '#': 3, '*': 3}
    h = len(rows)
    w = max(len(r) for r in rows)
    im = Img(w, h)
    for y, r in enumerate(rows):
        for x, ch in enumerate(r):
            im.px[y][x] = mapping.get(ch, 0)
    return im


# ---------------------------------------------------------------------------
class TileSet(object):
    """Collects unique 8x8 tiles and emits CHR data."""

    def __init__(self, name, capacity=256, reserve_blank=True):
        self.name = name
        self.capacity = capacity
        self.tiles = []
        self.index = {}
        if reserve_blank:
            self.add(Img(8, 8))

    @staticmethod
    def key(tile):
        return tuple(tuple(r) for r in tile.px)

    def add(self, tile):
        k = self.key(tile)
        if k in self.index:
            return self.index[k]
        i = len(self.tiles)
        if i >= self.capacity:
            raise RuntimeError("tileset '%s' overflow (%d tiles)" % (self.name, i + 1))
        self.tiles.append(tile)
        self.index[k] = i
        return i

    def add_at(self, slot, tile):
        while len(self.tiles) <= slot:
            self.tiles.append(Img(8, 8))
        self.tiles[slot] = tile
        self.index[self.key(tile)] = slot
        return slot

    def find(self, tile):
        return self.index.get(self.key(tile))

    def __len__(self):
        return len(self.tiles)

    def chr_bytes(self, pad_to=None):
        out = bytearray()
        for t in self.tiles:
            out += tile_to_chr(t)
        n = pad_to if pad_to is not None else self.capacity
        while len(out) < n * 16:
            out += bytes(16)
        return bytes(out)


def tile_to_chr(t):
    lo = bytearray(8)
    hi = bytearray(8)
    for y in range(8):
        a = 0
        b = 0
        for x in range(8):
            c = t.px[y][x]
            a = (a << 1) | (c & 1)
            b = (b << 1) | ((c >> 1) & 1)
        lo[y] = a
        hi[y] = b
    return bytes(lo) + bytes(hi)


# ---------------------------------------------------------------------------
def make_metasprite(img, tileset, ox, oy, pal=0, prio=False, skip_empty=True,
                    order=None):
    """Cut `img` into 8x8 tiles, register them and return a metasprite:
    a list of (dx, dy, tile, attr) with dx/dy relative to (ox, oy)."""
    out = []
    cells = []
    for ty in range(0, img.h, 8):
        for tx in range(0, img.w, 8):
            cells.append((tx, ty))
    if order:
        cells.sort(key=order)
    for tx, ty in cells:
        t = img.sub(tx, ty, 8, 8)
        if skip_empty and t.is_empty():
            continue
        idx = tileset.add(t)
        attr = pal & 3
        if prio:
            attr |= 0x20
        out.append((tx - ox, ty - oy, idx, attr))
    return out


def encode_metasprite(ms):
    """count, then (dx, dy, tile, attr) records."""
    out = bytearray()
    out.append(len(ms))
    for dx, dy, tile, attr in ms:
        out.append(dx & 0xFF)
        out.append(dy & 0xFF)
        out.append(tile & 0xFF)
        out.append(attr & 0xFF)
    return bytes(out)


# ---------------------------------------------------------------------------
def write_png(path, img, palette, scale=4, bg=(24, 24, 32)):
    """Write an indexed Img as a PNG preview.  `palette` is 4 NES colour
    numbers; index 0 renders as `bg`."""
    w, h = img.w * scale, img.h * scale
    rows = []
    for y in range(img.h):
        line = bytearray()
        for x in range(img.w):
            c = img.px[y][x]
            if c == 0:
                rgb = bg
            else:
                rgb = NES_RGB[palette[c] & 0x3F]
            line += bytes(rgb) * scale
        for _ in range(scale):
            rows.append(b'\x00' + bytes(line))
    raw = b''.join(rows)

    def chunk(tag, data):
        c = struct.pack('>I', len(data)) + tag + data
        return c + struct.pack('>I', zlib.crc32(tag + data) & 0xFFFFFFFF)

    png = b'\x89PNG\r\n\x1a\n'
    png += chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0))
    png += chunk(b'IDAT', zlib.compress(raw, 9))
    png += chunk(b'IEND', b'')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, 'wb').write(png)


def write_png_rgb(path, pixels, w, h, scale=1):
    rows = []
    for y in range(h):
        line = bytearray()
        for x in range(w):
            line += bytes(pixels[y][x]) * scale
        for _ in range(scale):
            rows.append(b'\x00' + bytes(line))
    raw = b''.join(rows)

    def chunk(tag, data):
        c = struct.pack('>I', len(data)) + tag + data
        return c + struct.pack('>I', zlib.crc32(tag + data) & 0xFFFFFFFF)

    png = b'\x89PNG\r\n\x1a\n'
    png += chunk(b'IHDR', struct.pack('>IIBBBBB', w * scale, h * scale, 8, 2, 0, 0, 0))
    png += chunk(b'IDAT', zlib.compress(raw, 9))
    png += chunk(b'IEND', b'')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, 'wb').write(png)


# ---------------------------------------------------------------------------
def asm_bytes(name, data, per_line=16, seg=None):
    """Format a byte blob as a ca65 label + .byte lines."""
    out = []
    if seg:
        out.append('.segment "%s"\n' % seg)
    out.append("%s:\n" % name)
    for i in range(0, len(data), per_line):
        chunk = data[i:i + per_line]
        out.append("        .byte " + ",".join("$%02X" % b for b in chunk) + "\n")
    return "".join(out)


def asm_table(name, values, hi=False):
    out = ["%s:\n" % name]
    for i in range(0, len(values), 8):
        chunk = values[i:i + 8]
        fn = ".hibytes" if hi else ".lobytes"
        out.append("        %s %s\n" % (fn, ",".join(chunk)))
    return "".join(out)

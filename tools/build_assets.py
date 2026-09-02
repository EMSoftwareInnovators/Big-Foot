#!/usr/bin/env python3
"""BIG FOOT asset build.

Renders every graphic, compiles every level and song, and writes the
generated ca65 sources plus the CHR-ROM blob into data/generated/.
"""
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
OUT = os.path.join(ROOT, "data", "generated")
sys.path.insert(0, HERE)

from chrpack import ChrRom, FramePacker            # noqa: E402
import gen_player                                   # noqa: E402


def write(name, text):
    path = os.path.join(OUT, name)
    old = None
    if os.path.exists(path):
        old = open(path).read()
    if old != text:
        open(path, "w").write(text)
    return len(text)


def main():
    t0 = time.time()
    os.makedirs(OUT, exist_ok=True)
    chr_rom = ChrRom()
    log = []

    # ---- player ---------------------------------------------------------
    asm, inc, stats = gen_player.build(chr_rom, FramePacker)
    write("player_data.s", asm)
    write("player_frames.inc", inc)
    log.append(stats)

    # ---- graphics: backgrounds, enemies, bosses, screens -----------------
    try:
        import gen_bg
        log.append(gen_bg.build(chr_rom, write))
    except ImportError:
        write("bg_data.s", "; not generated yet\n")
        write("bg.inc", "")

    import gen_entities
    log.append(gen_entities.build(write))

    import gen_screens
    log.append(gen_screens.build(write, chr_rom))

    import gen_text
    log.append(gen_text.build(write))

    import gen_levels
    log.append(gen_levels.build(write, chr_rom))

    try:
        import gen_music
        log.append(gen_music.build(write))
    except ImportError:
        write("music_data.s", "; not generated yet\n")
        write("music.inc", "")

    # ---- CHR-ROM ---------------------------------------------------------
    chr_path = os.path.join(OUT, "bigfoot.chr")
    blob = bytes(chr_rom.data)
    if not os.path.exists(chr_path) or open(chr_path, "rb").read() != blob:
        open(chr_path, "wb").write(blob)
    write("chr_map.txt", chr_rom.report())

    sys.stdout.write("".join(log))
    sys.stdout.write("CHR: %d / %d KiB used\n" % (chr_rom.used(), chr_rom.kb))
    sys.stdout.write("assets built in %.1fs\n" % (time.time() - t0))


if __name__ == "__main__":
    main()

# BIG FOOT

A homebrew action-platformer for the Nintendo Entertainment System.

You are an enormous disembodied right foot. Five toes, a heel, an arch, a
ball, and a short ankle stump that simply ends. You have no eyes, no mouth
and no body, and you never speak. A medieval kingdom has decided you are
the end of the world, and it is not wrong.

```
    THE GREAT HEEL HAS BREACHED THE EASTERN WALL!
```

Everything in the game takes that premise entirely seriously. Nobody winks
at the camera. The kingdom sends dispatches, the priests call it a
judgement, and the last army forms up on the field to be stepped on.

---

## Building

You need [cc65](https://cc65.github.io/) (`ca65` and `ld65`) and Python 3.
Nothing else.

```sh
make            # build/big_foot.nes
make clean      # remove build products
make assets     # regenerate graphics, levels, music and text only
make DEBUG=1    # the same ROM plus the development shortcuts
```

The output is a 512 KiB iNES file: mapper 4 (MMC3), 256 KiB PRG, 256 KiB
CHR, vertical mirroring, NTSC timing. It runs on real hardware and on any
emulator with reasonable MMC3 support.

`make assets` runs the Python asset pipeline. It renders every sprite,
tile, background picture and level from code — there are no image files in
the repository, and the `assets/` directory holds no bitmaps. Everything
the PPU displays was rasterised by `tools/`.

## Playing

| | |
|---|---|
| **D-pad** | walk; keep walking and the foot works up to a run |
| **A** | jump — the longer you hold, the higher you go |
| **B** | kick |
| **Down + B** | stomp on the ground, or dive-stomp in the air |
| **Up + B** | toe-grab |
| **B** *(holding something)* | throw it |
| **Down + B** *(holding something)* | put it down |
| **START** | pause |
| **SELECT** | (title screen) change menu selection |

There is no run button. Hold a direction for about two-thirds of a second
on the ground and the speed cap rises on its own; take a hit or turn around
and it drops again.

You have no sword and no gun. The body **is** the weapon:

- **Kick** knocks enemies back, punts loose objects and reflects arrows and
  cannonballs back the way they came.
- **Stomp** flattens whatever is underneath. The aerial dive-stomp breaks
  weak ground and shakes the screen.
- **Toe-grab** picks up a rock, crate, barrel or bomb and carries it in
  front of the toes. Throwing it hurts what it hits.
- **Kicking one thing into another thing** is the core of the combat. A
  punted barrel will take out a line of soldiers that a kick could not
  reach.

Some enemies are armoured against a frontal kick and have to be stomped or
hit from behind. Some are too heavy to flatten and have to be kicked.

The ground is not always safe either: spikes, spilled oil and open furnace
mouths hurt, and a pit floor kills outright. Weak ground gives way under a
dive-stomp, ice will not hold a turn, and deep water needs the flipper.

### Footwear

Eight things a giant foot can wear, each with its own physics table —
walking speed, running speed, acceleration, friction, jump height, kick
power and stomp power all change:

| | | |
|---|---|---|
| **BARE** | the default | balanced, quiet |
| **RUNNING SHOE** | stage 1 | fast, light, weak kick |
| **STEEL-TOED BOOT** | stage 3 | slow and heavy, enormous kick |
| **COWBOY BOOT** | stage 5 | high jump, sharp stop |
| **ICE CLEAT** | stage 7 | grip: no slide on ice |
| **FLIPPER** | stage 4 | swims, useless on land |
| **SLIPPER** | stage 6 | silent, almost frictionless |
| **BIG SHOE** | stage 8 | the legendary one |

Footwear is kept between stages and travels in the password.

### Passwords

The stage-clear screen prints a six-letter password that resumes at the
next stage with the footwear and lives you had. `PASSWORD` on the title
screen enters one. A mistyped password is refused rather than loading a
half-initialised game — the six letters carry a checksum.

## The stages

| | | |
|---|---|---|
| 1 | **The Little Kingdom** | a village, a wall, and the first mistake |
| 2 | **The Royal Forest** | canopy, deadfall, and the huntsmen |
| 3 | **Fort Stoneheel** | a fortress built specifically against you |
| 4 | **The Miasma Marsh** | water, sinking ground, and things below it |
| 5 | **The King's War Factory** | the kingdom's answer, on rails |
| 6 | **The Holy City** | the cathedral, and the blessing |
| 7 | **The Last March** | the whole remaining army, at once |
| 8 | **The Mountain of the Giant** | where the other one is |

Each ends with a named boss. The last is the LEFT FOOT.

---

## How it is built

### Memory map

```
PRG-ROM   256 KiB = 32 x 8 KiB banks
  bank  0    $A000   shared tables: player metasprites, animation,
                     entity definitions, per-theme metatiles, names
  bank  1    $A000   audio: period table, instruments, envelopes,
                     sound effects, all fifteen songs
  bank  2    $A000   full-screen pictures (title, intro, ending)
  bank  3    $A000   menu and cutscene code, scripts and dialogue
  banks 4-11 $8000   one stage each: map, spawns, palette, checkpoints
  bank 30    $C000   fixed: level streaming, player, entities, menus
  bank 31    $E000   fixed: NMI, IRQ, audio driver, bosses, HUD, camera

CHR-ROM   256 KiB = 256 x 1 KiB banks, about 132 KiB used
  R0/R1  $0000  2 KiB each: the player (25 banks of packed frames)
  R2-R4  $1000  background: 64 static, 64 static, 64 animated (x3)
  R5     $1C00  the shared HUD, font and effects bank -- never swapped

RAM       2 KiB
  $0000-$00FF  zero page: engine hot variables (223 of 256 used)
  $0100-$01FF  stack
  $0200-$02FF  OAM shadow (DMA source, page aligned)
  $0300-$07FF  BSS: entity pool, particles, level bookkeeping (697
               of 1280 used)
```

`docs/ram_map.txt` is generated by `tools/gen_ram.py`, which is the single
source of truth for the layout; every translation unit includes the same
generated `src/ram.inc`.

### Frame

```
main loop            NMI
-----------          ---------------------------------
read pads            OAM DMA
run the mode         drain the VRAM update queue
  update player      push CHR bank changes
  update entities    park the scroll for the status bar
  update boss        arm the MMC3 scanline IRQ
  build OAM          tick the sound driver
wait for NMI
                     IRQ (scanline 29)
                     hand the playfield its own scroll
```

The status bar is split from the playfield with the MMC3 scanline counter
rather than a sprite-0 hit, which frees sprite 0 and costs nothing during
rendering. The scroll and the split are re-armed on **every** NMI, not only
on frames the main loop finished, so an overrun slows the game down without
the status bar sliding away with the level.

When the main loop misses vblank the game drops to 30 fps for that frame,
which is what an NES game of this shape did in 1990 and what it does here
in dense scenes. Logic currently completes about 505 of every 557 frames
in heavy stage-1 traffic.

### Levels

Levels are 16x16 metatiles, 64 per theme, stored column-major. A stage
header names its map, metatile set, spawn list, palette, checkpoints,
music, theme, boss, footwear and CHR banks. Columns stream in as the camera
moves, split across three frames — left strip, right strip, attributes —
so no single frame does more VRAM work than vblank allows.

The eight themes and their metatiles are generated (`tools/gen_bg.py`) from
one palette convention: colour 1 is the primary surface, 2 the secondary,
3 the atmosphere, and colour 3 of the last palette is always bright so the
font stays readable over anything.

Level layout comes from `tools/chunks.py`, a library of 35 theme-independent
16x13 chunks written as ASCII. A stage is a sequence of chunk names, and
the compiler dresses each one in its theme's tiles, then adds a skyline or
a back wall and scatters ground clutter.

### Entities

A fixed pool of twelve, structure-of-arrays, with the slot index in X
throughout. Twelve behaviours (walker, shooter, flyer, hopper, ambush,
crusher, sound, object, shot, pickup, static, none) dispatch through a
table. Entities freeze when they leave the camera and are recycled when
they leave for good; the spawn list is a cursor with a used-bitmap so
walking back and forth does not duplicate anything.

Damage has classes rather than a single number: a kick is blocked from the
front by armour, a stomp is blocked by weight, a punted object hurts
whatever it lands on, and a reflected projectile hurts whoever fired it.

Bosses are the same pool plus a parameter table: hit points, size, speed,
jump, delay, contact damage, four attack slots and a projectile type. Every
boss has a second phase at half health that shortens its delays.

### Sound

Four voices driven from one per-frame tick inside the NMI:

```
0 pulse 1  $4000    1 pulse 2  $4004    2 triangle $4008    3 noise $400C
```

Every voice has the same register layout relative to `$4000 + voice*4`, so
the mixer and the sound-effect player share one code path for all four.

Songs are order lists of pattern byte streams; instruments pair a volume
envelope with an optional pitch envelope, which is where the arpeggiated
chord beds come from. Fifteen songs and twenty-three effects fit in one
8 KiB bank alongside the driver's tables.

Sound effects claim one voice each and only displace a lower priority. A
borrowed voice is skipped by the music entirely and reclaimed on the frame
after the effect ends, so an effect can never leave a note stuck on.
Voices whose envelopes have settled are marked static and skipped until
something changes them, which keeps the whole tick near 900 cycles.

### Graphics

Nothing is hand-drawn. `tools/foot.py` models the protagonist once, out of
ellipses and polygons in a local coordinate space: heel, ball, instep,
ankle stump with its flat cut, an arch subtracted from the sole, and five
separately articulated toes. Each animation frame applies an affine
transform plus per-toe rotation, and shading is applied *after* the
transform so the outline always follows the final silhouette.

Footwear is derived from the same masks (`tools/shoes.py`). Every shoe
completely encloses the foot, which is why eight kinds of footwear need one
palette swap instead of eight times the artwork.

Frames are packed into 128-tile sprite banks with deduplication
(`tools/chrpack.py`); 166 packed player frames occupy 25 banks. The
metasprite renderer picks a fast or slow path per metasprite and cycles the
draw order every frame so that when a scanline overflows eight sprites, the
flicker is even rather than one entity vanishing.

The three full-screen pictures are built as silhouettes against black,
because colour 0 is shared by all four background palettes. That is a
constraint, and it is also the look: a storm-lit kingdom with something
enormous coming down out of the dark.

### The narrative

The intro, the seven dispatches from the kingdom, the ending and the
credits are one bytecode with fourteen commands — load a picture, print a
centred line through the VRAM queue, wait, hold for a button, shake the
screen for a footfall, name the mode that follows. Every line of dialogue
is in `tools/gen_text.py`.

---

## The repository

```
src/          6502 assembly -- the game itself (about 10,000 lines)
tools/        the Python asset pipeline (about 7,600 lines)
emu/          a headless NES emulator used for testing
cfg/          generated linker configuration
data/         generated assembly, CHR-ROM and include files
docs/         generated RAM map
```

Nothing under `data/generated/` or `cfg/` is edited by hand; `make assets`
rebuilds all of it. The pipeline is Python, but nothing in the running game
is — the ROM is entirely 6502.

### The emulator

`emu/nesemu.c` is a headless NTSC NES emulator written for this project,
because testing a ROM you cannot run is guesswork. It is not a general
emulator, but it is accurate enough for the parts this game leans on: MMC3
banking and scanline IRQs, the PPU's rendering and address logic, and cycle
counting.

```sh
cc -O2 -o build/nesemu emu/nesemu.c -lm

build/nesemu build/big_foot.nes -frames 600 -input script.txt \
    -shot 500:build/frame.png
```

| option | what it does |
|---|---|
| `-frames N` | run N frames |
| `-input FILE` | scripted controller input, one range per line |
| `-shot F:FILE` | write a PNG of frame F |
| `-watch ADDR` | print a RAM address every frame |
| `-work ADDR` | measure how much of each frame the main loop uses |
| `-prof LO:HI:NAME` | count cycles spent in an address range |
| `-hot` | a PC histogram, for finding the expensive code |
| `-apulog FILE F` | trace every APU register write |
| `-callat ADDR` | print A and X whenever a routine is entered |
| `-guard` | stop the instant the program counter leaves ROM |

A jam or a guard trip prints the last thousand program counters, which is
how a bad dispatch was traced from zero page back to the table it came
from.

`tools/check_music.py` turns an `-apulog` trace back into a readable score —
pitch, start frame and duration per voice. Since this environment has no
sound, that is how the driver and the songs were verified.

### Testing

The emulator has driven every stage of development: screenshots for the
graphics, watchpoints and the guard for the logic, the cycle profiler for
the frame budget, and the APU trace for the music.

`tools/pwtest.py` generates an input script that types a given stage's
password, which is how each stage is reached for testing -- exactly, and
exercising the password screen on the way. All eight bosses have been
triggered, damaged and killed this way, through the stage-clear screen and
the kingdom's next dispatch, and the Left Foot through to the ending.

**Not** verified: audio has never been listened to, only inspected as
register writes; and the ROM has not been run on real hardware or on a
mainstream emulator. Everything stated above about how it behaves comes
from `emu/nesemu.c`.

### Development shortcuts

`make DEBUG=1` builds the same ROM with SELECT as a modifier during play:

| | |
|---|---|
| SELECT + START | clear the stage outright |
| SELECT + B | hand over every piece of footwear |
| SELECT + A | drop a rock at the player's feet |
| SELECT + UP | toggle invulnerability |
| SELECT + RIGHT | warp four metatiles forward |

None of it is assembled into a normal build.

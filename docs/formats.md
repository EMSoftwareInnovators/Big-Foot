# BIG FOOT — data formats

Every one of these is produced by a generator in `tools/` and consumed by a
reader in `src/`. The pairs are named in each section; if you change one,
change the other.

---

## Stage header

`tools/gen_levels.py` → `src/level.s` (`level_load`)

One per stage, at the head of its own 8 KiB bank.

```
+0   .addr map, metatiles, spawns, palette
+8   .addr checkpoints
+10  .word columns          map width in metatile columns
+12  .word boss_col         column that triggers the boss
+14  .byte theme            which metatile set and CHR banks
+15  .byte music
+16  .word start_col
+18  .byte start_row
+19  .byte boss_id
+20  .byte shoe             footwear this stage awards
+21  .byte boss_music
+22  .byte roster[6]        entity types this stage's sprite bank holds
+28  .byte enemy_chr, boss_chr
+30  .addr ms_lo, ms_hi     enemy metasprite tables
+34  .addr bms_lo, bms_hi   boss metasprite tables
+38  .byte kick_type        the loose object this stage scatters
```

### Map

Column-major, stride 16, thirteen playfield rows. Each byte is a metatile
index 0..63. Rows 4..29 of the nametable are the playfield; rows 0..3 are
the status bar and never scroll.

### Metatile set

Six parallel 64-byte tables per theme — `tl`, `tr`, `bl`, `br` (the four
8x8 tiles), `attr` (palette 0..3) and a collision class:

```
 0  empty                    8  stomp switch
 1  solid                    9  instant death
 2  one-way platform        10  climbable (toe-grab)
 3  hazard, damage on touch 11  conveyor, rightward
 4  breakable by a stomp    12  conveyor, leftward
 5  water                   13  stage exit
 6  ice                     14  checkpoint
 7  mud                     15  secret: looks solid, is passable
```

### Spawn list

Four bytes each, sorted by column, terminated by `$FF` in the column's high
byte. Up to 96 entries.

```
+0  .word column
+2  .byte row
+3  .byte entity type
```

The reader keeps a cursor and a 96-bit used-map, so walking back and forth
across a spawn point does not spawn it twice, and walking away and
returning after it despawned does.

### Checkpoints

`.word column` each, `$FFFF` terminated.

---

## Metasprite

`tools/gen_player.py`, `tools/gen_levels.py` → `src/sprites.s`
(`draw_metasprite`)

```
+0  .byte dx, dy           offset from the entity origin, signed
+2  .byte w, h             size in 8x8 tiles
+4  .byte attr             palette and flip bits
+5  .byte tiles[w*h]       row-major; 0 means "skip this cell"
```

The origin is the centre of the collision box, one pixel below the sole.
The renderer chooses a fast or a slow path per metasprite depending on
whether it can skip the per-tile clipping.

---

## Music

`tools/gen_music.py`, `tools/music.py` → `src/audio.s`

### Song

```
+0  .byte speed            frames per row
+1  .word order[4]         one order list per voice
```

### Order list

A sequence of little-endian pattern addresses. `$0000` loops back to the
start of the list; `$FFFF` stops that voice, which is how the one-shot
cues (stage clear, game over) end.

### Pattern

```
$00..$5F   note on, index into the period table (0 = C-0, 48 = C-4)
$60        rest
$61        tie -- hold the sounding note for another span
$80..$BF   set the note length to (b - $80) + 1 rows
$C0..$CF   set the instrument
$D0..$DF   set the channel volume
$E0        end of pattern; fetch the next order entry
```

On the noise voice a note byte's low nibble is the period index and the
instrument's duty bit 7 selects the short, tonal mode.

### Instrument

Six parallel tables indexed by instrument number: `duty`, `env_lo`,
`env_hi`, `arp_lo`, `arp_hi`, `settle`. `settle` is 1 for an instrument
with no pitch envelope, which lets the mixer mark the voice static once its
volume envelope stops changing.

### Envelope

```
volume    $00..$0F values, $FD <index> loops, $FE holds the last value
pitch     signed semitone offsets, $7D <index> loops, $7E holds
```

### Sound effect

```
+0  .byte voice, priority
    then frames:
      vv pp qq     write to +0, +2 and +3 of the voice's registers
      $FE n        hold those registers for n more frames
      $FF          end; release the voice
```

---

## Cutscene script

`tools/gen_text.py` → `src/script.s`

One command runs per frame. Operand counts include the opcode.

```
 0  END                        (1)
 1  SCREEN  picture            (2)
 2  BLANK                      (1)
 3  TEXT    row, addr          (4)   centred
 4  TEXTAT  col, row, addr     (5)
 5  WAIT    frames             (2)
 6  MUSIC   song               (2)
 7  SFX     effect             (2)
 8  CLEAR   row, count         (3)   one row per frame
 9  PAUSE                      (1)   until START or A
10  MODE    game mode          (2)   and stop
11  FADE    attenuation        (2)
12  SHAKE   frames             (2)
13  STEP                       (1)   one enormous footfall
```

Strings are font glyph indices terminated by `$FF`. Index 0 is the space
glyph, which is why the terminator is not zero.

---

## Full-screen picture

`tools/gen_screens.py`, `tools/screens.py` → `src/screen.s` (`screen_load`)

A nametable and an attribute table, each run-length encoded, plus a 32-byte
palette. The picture's 192 unique tiles occupy three consecutive 1 KiB CHR
banks, mapped into R2/R3/R4; R5 keeps the shared font bank so a picture can
print text.

```
$00        end of stream
$01..$7F   copy this many following bytes literally
$81..$FF   repeat the next byte (b & $7F) times
```

Pictures are mostly detail with occasional flat sky, so a pure run encoder
made the title screen *larger* than the raw nametable; the literal runs are
what make the encoding worth having.

---

## VRAM update queue

`src/ppu.s` (`vq_open`, `vq_byte`, `vq_close`) → `src/nmi.s` (`vram_flush`)

Packets back to back in `vram_buf`, a zero length terminating:

```
+0  .byte length           1..64 data bytes
+1  .byte ctrl             $00 = increment by 1, $04 = by 32
+2  .byte addr_hi, addr_lo
+4  .byte data[length]
```

The main thread builds packets; the NMI drains them. Nothing else writes
`$2007` while rendering is on.

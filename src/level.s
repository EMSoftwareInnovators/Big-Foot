;
; Level loading, metatile lookup and nametable column streaming.
;
; A stage lives in one switchable $8000 bank and begins with a 28-byte header:
;
;   +0  .addr map          column-major metatile indices, 16 bytes per column
;   +2  .addr metatiles    tl[64] tr[64] bl[64] br[64] attr[64] flags[64]
;   +4  .addr spawns       (col_lo, col_hi, row, type) sorted by column
;   +6  .addr palette      16 background + 16 sprite bytes
;   +8  .addr checkpoints  count, then (col_lo, col_hi, row)
;   +10 .word columns
;   +12 .word boss column
;   +14 .byte theme, music, start_col_lo, start_col_hi, start_row, boss id
;   +20 .byte stage footwear, boss music
;   +22 .byte enemy roster (6 entries)
;
; The playfield occupies nametable rows 4..29 (13 metatiles); rows 0..3 are the
; HUD, which the sprite-0 split keeps unscrolled.
;
.include "constants.inc"
.include "ram.inc"
.include "bg.inc"

.import set_prg8000, set_prga000, vq_open, vq_close, ppu_off, ppu_on
.import load_palette, apply_chr
.import stage_bank, theme_chr, theme_pal
.export level_load, level_stream, mt_at, mt_flags_at, flags_at_xy
.export draw_full_screen, break_tile, is_broken, level_anim

.segment "CODE2"

; ---------------------------------------------------------------------------
; level_load -- A = stage number.  Maps the stage bank, caches its header in
; zero page and paints both nametables.  Rendering must already be off.
; ---------------------------------------------------------------------------
.proc level_load
        sta stage_num
        tax
        lda stage_bank,x
        jsr set_prg8000

        lda #$00
        sta hdr_ptr
        lda #$80
        sta hdr_ptr+1

        ldy #0
        lda (hdr_ptr),y
        sta map_ptr
        iny
        lda (hdr_ptr),y
        sta map_ptr+1
        iny
        lda (hdr_ptr),y
        sta mt_ptr
        iny
        lda (hdr_ptr),y
        sta mt_ptr+1
        iny
        lda (hdr_ptr),y
        sta spawn_ptr
        iny
        lda (hdr_ptr),y
        sta spawn_ptr+1
        iny
        lda (hdr_ptr),y
        sta ptr1
        iny
        lda (hdr_ptr),y
        sta ptr1+1
        iny
        lda (hdr_ptr),y
        sta check_ptr
        iny
        lda (hdr_ptr),y
        sta check_ptr+1
        iny
        lda (hdr_ptr),y
        sta level_cols
        iny
        lda (hdr_ptr),y
        sta level_cols+1
        iny
        lda (hdr_ptr),y
        sta boss_col
        iny
        lda (hdr_ptr),y
        sta boss_col+1
        iny
        lda (hdr_ptr),y
        sta theme
        iny
        lda (hdr_ptr),y
        sta level_music
        iny
        lda (hdr_ptr),y
        sta start_col
        iny
        lda (hdr_ptr),y
        sta start_col+1
        iny
        lda (hdr_ptr),y
        sta start_row
        iny
        lda (hdr_ptr),y
        sta boss_id
        iny
        lda (hdr_ptr),y
        sta stage_shoe
        iny
        lda (hdr_ptr),y
        sta boss_music
        iny
        tya
        pha
        clc
        adc hdr_ptr
        sta roster_ptr
        lda hdr_ptr+1
        adc #0
        sta roster_ptr+1
        pla
        clc
        adc #6                          ; skip the six roster bytes
        tay
        lda (hdr_ptr),y
        sta enemy_chr
        iny
        lda (hdr_ptr),y
        sta boss_chr
        iny
        lda (hdr_ptr),y
        sta ms_lo_ptr
        iny
        lda (hdr_ptr),y
        sta ms_lo_ptr+1
        iny
        lda (hdr_ptr),y
        sta ms_hi_ptr
        iny
        lda (hdr_ptr),y
        sta ms_hi_ptr+1
        iny
        lda (hdr_ptr),y
        sta bms_lo_ptr
        iny
        lda (hdr_ptr),y
        sta bms_lo_ptr+1
        iny
        lda (hdr_ptr),y
        sta bms_hi_ptr
        iny
        lda (hdr_ptr),y
        sta bms_hi_ptr+1
        iny
        lda (hdr_ptr),y
        sta kick_type
        lda enemy_chr
        sta chr_bank_hi

        ; ---- palettes -------------------------------------------------
        lda ptr1
        sta ptr0
        lda ptr1+1
        sta ptr0+1
        jsr load_palette

        ; ---- CHR banks for this theme ---------------------------------
        lda theme
        asl a
        asl a
        adc theme                       ; theme * 5
        tay
        lda theme_chr,y
        sta chr_bg0
        iny
        lda theme_chr,y
        sta chr_bg1
        iny
        lda theme_chr,y
        sta chr_bg2
        sta anim_bank
        lda #HUD_CHR_BANK
        sta chr_bg3
        jsr apply_chr

        jsr mt_setup

        lda #$FF
        sta mtc_row
        lda #0
        sta dmg_count
        sta stream_state
        sta anim_timer
        rts
.endproc

; ---------------------------------------------------------------------------
; mt_setup -- cache pointers to the five metatile sub-tables so that lookups
; are a single indexed indirect load instead of an add chain.
; ---------------------------------------------------------------------------
.proc mt_setup
        lda mt_ptr
        clc
        adc #64
        sta mt_tr
        lda mt_ptr+1
        adc #0
        sta mt_tr+1
        ldx #0
:       lda mt_tr,x
        clc
        adc #64
        sta mt_bl,x
        lda mt_tr+1,x
        adc #0
        sta mt_bl+1,x
        inx
        inx
        cpx #8
        bcc :-
        rts
.endproc

; ---------------------------------------------------------------------------
; level_anim -- rotate the animated CHR bank (R4) every eight frames
; ---------------------------------------------------------------------------
.proc level_anim
        inc anim_timer
        lda anim_timer
        and #$07
        bne @done
        lda theme
        asl a
        asl a
        adc theme
        clc
        adc #2                          ; theme_chr + 2 = first animated bank
        tay
        lda chr_bg2
        sec
        sbc theme_chr,y
        clc
        adc #1
        cmp #3
        bcc :+
        lda #0
:       clc
        adc theme_chr,y
        sta chr_bg2
        lda #1
        sta chr_dirty
@done:  rts
.endproc

; ---------------------------------------------------------------------------
; mt_at -- tmp0/tmp1 = column, tmp2 = row.  Returns the metatile index in A.
; Columns outside the level read as solid so the player cannot walk out.
; ---------------------------------------------------------------------------
; ---------------------------------------------------------------------------
; mt_col_base -- tmp0/tmp1 = column, sets col_base = map + column * 16.
; Callers that walk a whole column use this once and then index by row.
; ---------------------------------------------------------------------------
.proc mt_col_base
        lda tmp0
        asl a
        asl a
        asl a
        asl a
        clc
        adc map_ptr
        sta col_base
        lda tmp0
        lsr a
        lsr a
        lsr a
        lsr a
        sta tmp3
        lda tmp1
        asl a
        asl a
        asl a
        asl a
        ora tmp3
        adc map_ptr+1
        sta col_base+1
        rts
.endproc

; mt_col_at -- Y = row, metatile of the cached column in A
.proc mt_col_at
        cpy #PLAY_ROWS
        bcs @open
        lda (col_base),y
        rts
@open:  lda #0
        rts
.endproc

.proc mt_at
        lda tmp1
        bmi @solid
        lda tmp2
        cmp #PLAY_ROWS
        bcs @open
        lda tmp1
        cmp level_cols+1
        bcc @ok
        bne @solid
        lda tmp0
        cmp level_cols
        bcs @solid
@ok:
        ; offset = column * 16 + row
        lda tmp0
        asl a
        asl a
        asl a
        asl a
        clc
        adc tmp2
        sta ptr2
        lda tmp0
        lsr a
        lsr a
        lsr a
        lsr a
        sta tmp3
        lda tmp1
        asl a
        asl a
        asl a
        asl a
        ora tmp3
        sta ptr2+1
        lda ptr2
        clc
        adc map_ptr
        sta ptr2
        lda ptr2+1
        adc map_ptr+1
        sta ptr2+1
        ldy #0
        lda (ptr2),y
        rts
@open:  lda #0
        rts
@solid: lda #$FF                        ; sentinel: treated as solid
        rts
.endproc

; ---------------------------------------------------------------------------
; mt_flags_at -- as mt_at but returns the collision class in A
; ---------------------------------------------------------------------------
; ---------------------------------------------------------------------------
; mt_flags_at -- collision class of the metatile at tmp0/tmp1 (column),
; tmp2 (row).  A one-entry cache absorbs the many repeated probes an entity
; makes into the same tile within a frame.
; ---------------------------------------------------------------------------
.proc mt_flags_at
        lda tmp2
        cmp mtc_row
        bne @miss
        lda tmp0
        cmp mtc_col
        bne @miss
        lda tmp1
        cmp mtc_col+1
        bne @miss
        lda mtc_val
        rts
@miss:
        lda tmp0
        sta mtc_col
        lda tmp1
        sta mtc_col+1
        lda tmp2
        sta mtc_row
        jsr mt_flags_calc
        sta mtc_val
        rts
.endproc

.proc mt_flags_calc
        jsr mt_at
        cmp #$FF
        beq @wall
        tay
        lda (mt_fl_p),y
        cmp #COL_BREAK
        bne @out
        txa
        pha
        jsr is_broken
        pla
        tax
        bcc @out
        lda #COL_EMPTY
@out:   rts
@wall:  lda #COL_SOLID
        rts
.endproc

; ---------------------------------------------------------------------------
; flags_at_xy -- ptr0 = world X (16-bit), tmp4 = world Y.
;                Returns the collision class in A.
; ---------------------------------------------------------------------------
.proc flags_at_xy
        lda ptr0
        lsr a
        lsr a
        lsr a
        lsr a
        sta tmp0
        lda ptr0+1
        asl a
        asl a
        asl a
        asl a
        ora tmp0
        sta tmp0
        lda ptr0+1
        lsr a
        lsr a
        lsr a
        lsr a
        sta tmp1
        lda tmp4
        lsr a
        lsr a
        lsr a
        lsr a
        sta tmp2
        jmp mt_flags_at
.endproc

; ---------------------------------------------------------------------------
; break_tile -- record tmp0/tmp1 = column, tmp2 = row as destroyed
; ---------------------------------------------------------------------------
.proc break_tile
        lda dmg_count
        cmp #8
        bcc :+
        lda #0
        sta dmg_count
:       lda dmg_count
        asl a
        adc dmg_count                   ; *3
        tax
        lda tmp0
        sta tile_dmg,x
        lda tmp1
        sta tile_dmg+1,x
        lda tmp2
        sta tile_dmg+2,x
        inc dmg_count
        lda #$FF
        sta mtc_row
        rts
.endproc

; ---------------------------------------------------------------------------
; is_broken -- carry set if tmp0/tmp1/tmp2 names a destroyed tile
; ---------------------------------------------------------------------------
.proc is_broken
        ldx dmg_count
        beq @no
        ldx #0
        ldy #0
@loop:  lda tile_dmg,x
        cmp tmp0
        bne @next
        lda tile_dmg+1,x
        cmp tmp1
        bne @next
        lda tile_dmg+2,x
        cmp tmp2
        bne @next
        sec
        rts
@next:  inx
        inx
        inx
        iny
        cpy dmg_count
        bcc @loop
@no:    clc
        rts
.endproc

; ---------------------------------------------------------------------------
; column_addr -- tmp0/tmp1 = column.  Produces:
;   tmp2 = nametable high byte, tmp3 = low byte of the first tile row
;   tmp5 = attribute low byte base
; ---------------------------------------------------------------------------
.proc column_addr
        lda tmp0
        and #$0F
        asl a                           ; tile column within the nametable
        sta tmp6
        lda tmp0
        lsr a
        lsr a
        lsr a
        lsr a
        and #1
        beq :+
        lda #$24
        bne :++
:       lda #$20
:       sta tmp2
        lda tmp6
        clc
        adc #<(4 * 32)                  ; playfield starts at tile row 4
        sta tmp3
        rts
.endproc

; ---------------------------------------------------------------------------
; draw_column_tiles -- queue both 8-pixel tile columns of metatile column
; tmp0/tmp1.  Uses increment-by-32 so each packet is one vertical strip.
; ---------------------------------------------------------------------------
.proc draw_column_left
        lda #0
        sta tmpF
        jmp draw_strip
.endproc

.proc draw_column_right
        lda #1
        sta tmpF
        jmp draw_strip
.endproc

; ---------------------------------------------------------------------------
; draw_strip -- queue one 8-pixel-wide strip (26 tiles) of metatile column
; tmp0/tmp1.  tmpF selects the left (0) or right (1) half.
;
; One strip per frame keeps the NMI's VRAM burst well inside vblank, which
; matters because the HUD scroll is only re-armed after the queue drains.
; ---------------------------------------------------------------------------
.proc draw_strip
        lda tmp0
        sta tmpA
        lda tmp1
        sta tmpB
        jsr mt_col_base
        lda tmpA
        sta tmp0
        lda tmpB
        sta tmp1
        jsr column_addr
        lda tmpF
        clc
        adc tmp3
        sta tmp3
        lda #26
        ldx #$04
        jsr vq_open
        sty tmpC
        ldx #0
@row:   stx tmpD
        txa
        tay
        jsr mt_col_at
        jsr mt_quads
        ldy tmpC
        lda tmpF
        bne @right
        lda tmp7
        sta vram_buf,y
        iny
        lda tmp9
        sta vram_buf,y
        jmp @next
@right:
        lda tmp8
        sta vram_buf,y
        iny
        lda tmpE
        sta vram_buf,y
@next:
        iny
        sty tmpC
        ldx tmpD
        inx
        cpx #PLAY_ROWS
        bcc @row
        ldy tmpC
        jmp vq_close
.endproc

; ---------------------------------------------------------------------------
; mt_quads -- A = metatile index.  Returns the four tile indices in
; tmp7 (tl), tmp8 (tr), tmp9 (bl), tmpE (br).  $FF (out of bounds) draws as
; the solid wall metatile so edges look intentional.
; ---------------------------------------------------------------------------
.proc mt_quads
        cmp #$FF
        bne :+
        lda #0
:       tay
        lda (mt_ptr),y
        sta tmp7
        lda (mt_tr),y
        sta tmp8
        lda (mt_bl),y
        sta tmp9
        lda (mt_br),y
        sta tmpE
        rts
.endproc

; ---------------------------------------------------------------------------
; mt_attr -- A = metatile index, returns its palette (0..3) in A
; ---------------------------------------------------------------------------
.proc mt_attr
        cmp #$FF
        bne :+
        lda #0
:       tay
        lda (mt_at_p),y
        and #3
        rts
.endproc

; ---------------------------------------------------------------------------
; draw_column_attr -- queue the seven attribute bytes covering the metatile
; column pair that contains tmp0/tmp1.
; ---------------------------------------------------------------------------
.proc draw_column_attr
        lda tmp0
        and #$FE
        sta tmpA                        ; even column of the pair
        lda tmp1
        sta tmpB
        ; base pointers for both columns of the pair
        lda tmpA
        sta tmp0
        lda tmpB
        sta tmp1
        jsr mt_col_base
        lda col_base
        sta ptr2
        lda col_base+1
        sta ptr2+1
        lda tmpA
        clc
        adc #1
        sta tmp0
        lda tmpB
        adc #0
        sta tmp1
        jsr mt_col_base                 ; col_base now holds the odd column

        lda tmpA
        lsr a
        lsr a
        lsr a
        lsr a
        and #1
        beq :+
        lda #$27
        bne :++
:       lda #$23
:       sta tmp5                        ; attribute table page
        lda tmpA
        and #$0F
        lsr a
        sta tmp6                        ; attribute column 0..7

        ldx #0                          ; attribute row 0..6 -> rows 1..7
@row:   stx tmpD
        txa
        asl a
        tay                             ; metatile row of the upper half
        lda (ptr2),y
        jsr pal_of
        sta tmpF
        lda (col_base),y
        jsr pal_of
        asl a
        asl a
        ora tmpF
        sta tmpF
        iny
        cpy #PLAY_ROWS
        bcs @half
        lda (ptr2),y
        jsr pal_of
        asl a
        asl a
        asl a
        asl a
        ora tmpF
        sta tmpF
        lda (col_base),y
        jsr pal_of
        asl a
        asl a
        asl a
        asl a
        asl a
        asl a
        ora tmpF
        sta tmpF
@half:
        lda tmp5
        sta tmp2
        lda tmpD
        asl a
        asl a
        asl a
        clc
        adc #<($C0 + 8)                 ; attribute row 0 belongs to the HUD
        adc tmp6
        sta tmp3
        lda #1
        ldx #$00
        jsr vq_open
        lda tmpF
        sta vram_buf,y
        iny
        jsr vq_close
        ldx tmpD
        inx
        cpx #7
        bcc @row
        rts
.endproc

; pal_of -- A = metatile index, returns its palette in the low two bits
.proc pal_of
        sty tmpC
        tay
        lda (mt_at_p),y
        and #3
        ldy tmpC
        rts
.endproc

; ---------------------------------------------------------------------------
; draw_full_screen -- paint 32 metatile columns starting at cam_x.
; Rendering must be off; writes go straight to the PPU.
; ---------------------------------------------------------------------------
.proc draw_full_screen
        lda cam_x
        sta col_left
        lda cam_x+1
        sta col_left+1
        lsr col_left+1
        ror col_left
        lsr col_left+1
        ror col_left
        lsr col_left+1
        ror col_left
        lsr col_left+1
        ror col_left
        lda col_left
        sta col_next
        lda col_left+1
        sta col_next+1

        ldx #32
@loop:  txa
        pha
        lda #0
        sta vram_len
        sta vram_buf
        lda col_next
        sta tmp0
        lda col_next+1
        sta tmp1
        jsr draw_column_left
        lda col_next
        sta tmp0
        lda col_next+1
        sta tmp1
        jsr draw_column_right
        lda col_next
        sta tmp0
        lda col_next+1
        sta tmp1
        jsr draw_column_attr
        jsr vram_direct
        inc col_next
        bne :+
        inc col_next+1
:       pla
        tax
        dex
        bne @loop
        lda #0
        sta vram_len
        sta vram_buf
        rts
.endproc

; ---------------------------------------------------------------------------
; vram_direct -- drain the queue immediately (rendering off)
; ---------------------------------------------------------------------------
.proc vram_direct
        ldx #0
@packet:
        lda vram_buf,x
        beq @done
        sta tmp0
        inx
        lda ppu_ctrl
        and #$FB
        ora vram_buf,x
        sta PPUCTRL
        inx
        bit PPUSTATUS
        lda vram_buf,x
        sta PPUADDR
        inx
        lda vram_buf,x
        sta PPUADDR
        inx
        ldy tmp0
@copy:  lda vram_buf,x
        sta PPUDATA
        inx
        dey
        bne @copy
        jmp @packet
@done:  lda #0
        sta vram_len
        sta vram_buf
        lda ppu_ctrl
        sta PPUCTRL
        rts
.endproc

; ---------------------------------------------------------------------------
; level_stream -- keep the nametables ahead of the camera.  One step per
; frame: tiles first, attributes next, which keeps every vblank short.
; ---------------------------------------------------------------------------
.proc level_stream
        lda stream_state
        beq @check
        lda stream_col
        sta tmp0
        lda stream_col+1
        sta tmp1
        lda stream_state
        cmp #1
        bne @attr
        jsr draw_column_right
        lda #2
        sta stream_state
        rts
@attr:
        jsr draw_column_attr
        lda #0
        sta stream_state
        rts

@check:
        ; camera column = cam_x / 16
        lda cam_x
        sta tmp0
        lda cam_x+1
        sta tmp1
        lsr tmp1
        ror tmp0
        lsr tmp1
        ror tmp0
        lsr tmp1
        ror tmp0
        lsr tmp1
        ror tmp0
        lda tmp0
        clc
        adc #17
        sta tmp4
        lda tmp1
        adc #0
        sta tmp5
        lda col_next
        cmp tmp4
        lda col_next+1
        sbc tmp5
        bcs @left
        lda col_next
        sta stream_col
        lda col_next+1
        sta stream_col+1
        inc col_next
        bne @go
        inc col_next+1
        jmp @go
@left:
        lda tmp0
        sec
        sbc #1
        sta tmp4
        lda tmp1
        sbc #0
        sta tmp5
        bmi @none
        lda tmp4
        cmp col_left
        lda tmp5
        sbc col_left+1
        bcs @none
        lda col_left
        sec
        sbc #1
        sta col_left
        sta stream_col
        lda col_left+1
        sbc #0
        sta col_left+1
        sta stream_col+1
@go:
        lda stream_col
        sta tmp0
        lda stream_col+1
        sta tmp1
        jsr draw_column_left
        lda #1
        sta stream_state
@none:  rts
.endproc



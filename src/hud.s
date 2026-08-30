;
; Status bar.
;
; Nametable rows 0..2 carry the HUD, row 3 is a uniform rule.  The sprite-0
; hit lands inside row 3, so the two or three scanlines that render with the
; playfield's scroll are indistinguishable -- both nametables share that row.
;
.include "constants.inc"
.include "ram.inc"
.include "bg.inc"

.import vq_open, vq_close, stage_name_lo, stage_name_hi
.export hud_draw_full, hud_update, hud_boss_bar, hud_text_at, hud_clear_rows

.segment "CODE2"

; ---------------------------------------------------------------------------
; hud_draw_full -- paint the whole bar.  Rendering must be off.
; ---------------------------------------------------------------------------
.proc hud_draw_full
        ; rows 0..2 of nametable A: clear
        ldx #0
        lda #$20
        sta tmp2
        lda #$00
        sta tmp3
        jsr set_addr
        ldy #0
        lda #FONT_BASE                  ; space
:       sta PPUDATA
        iny
        cpy #96
        bne :-

        ; row 3 of both nametables: the uniform rule
        lda #$20
        sta tmp2
        lda #96
        sta tmp3
        jsr set_addr
        ldy #32
        lda #TILE_RULE
:       sta PPUDATA
        dey
        bne :-
        lda #$24
        sta tmp2
        lda #96
        sta tmp3
        jsr set_addr
        ldy #32
        lda #TILE_RULE
:       sta PPUDATA
        dey
        bne :-

        ; attribute row 0 of both nametables -> palette 3
        lda #$23
        sta tmp2
        lda #$C0
        sta tmp3
        jsr set_addr
        ldy #8
        lda #$FF
:       sta PPUDATA
        dey
        bne :-
        lda #$27
        sta tmp2
        lda #$C0
        sta tmp3
        jsr set_addr
        ldy #8
        lda #$FF
:       sta PPUDATA
        dey
        bne :-

        jsr hud_static_text
        jsr hud_direct_meters
        rts
.endproc

.proc set_addr
        bit PPUSTATUS
        lda tmp2
        sta PPUADDR
        lda tmp3
        sta PPUADDR
        rts
.endproc

; ---------------------------------------------------------------------------
; hud_static_text -- the parts that never change during a stage
; ---------------------------------------------------------------------------
.proc hud_static_text
        lda #$20
        sta tmp2
        lda #34                         ; row 1, column 2
        sta tmp3
        jsr set_addr
        lda #TILE_FOOT
        sta PPUDATA

        lda #$20
        sta tmp2
        lda #(32 + 13)
        sta tmp3
        jsr set_addr
        ldx #0
:       lda txt_stage,x
        beq :+
        clc
        adc #FONT_BASE
        sta PPUDATA
        inx
        bne :-
:       lda stage_num
        clc
        adc #1
        clc
        adc #(FONT_BASE + 27)           ; '0' is glyph 27
        sta PPUDATA

        lda #$20
        sta tmp2
        lda #(32 + 26)
        sta tmp3
        jsr set_addr
        lda #TILE_SHOE
        sta PPUDATA
        rts
txt_stage: .byte 19,20,1,7,5,0          ; "STAGE"
.endproc

; ---------------------------------------------------------------------------
; hud_direct_meters -- immediate (rendering off) version of hud_update
; ---------------------------------------------------------------------------
.proc hud_direct_meters
        lda #$20
        sta tmp2
        lda #36
        sta tmp3
        jsr set_addr
        jsr build_health
        ldx #0
:       lda scratch,x
        sta PPUDATA
        inx
        cpx #6
        bne :-

        lda #$20
        sta tmp2
        lda #(32 + 28)
        sta tmp3
        jsr set_addr
        lda #(FONT_BASE + 24)           ; 'X'
        sta PPUDATA
        lda lives
        cmp #10
        bcc :+
        lda #9
:       clc
        adc #(FONT_BASE + 27)
        sta PPUDATA
        lda #0
        sta hud_dirty
        rts
.endproc

; ---------------------------------------------------------------------------
; build_health -- six meter tiles in `scratch`, two health units per tile
; ---------------------------------------------------------------------------
.proc build_health
        lda p_hp
        sta tmp0
        ldx #0
@loop:  lda tmp0
        beq @empty
        cmp #2
        bcc @half
        lda #TILE_BAR2
        sta scratch,x
        dec tmp0
        dec tmp0
        jmp @next
@half:  lda #TILE_BAR1
        sta scratch,x
        lda #0
        sta tmp0
        jmp @next
@empty: lda #TILE_BAR0
        sta scratch,x
@next:  inx
        cpx #6
        bne @loop
        rts
.endproc

; ---------------------------------------------------------------------------
; hud_update -- queue the changing parts for the next NMI
; ---------------------------------------------------------------------------
.proc hud_update
        lda hud_dirty
        beq @done
        jsr build_health
        lda #$20
        sta tmp2
        lda #36
        sta tmp3
        lda #6
        ldx #0
        jsr vq_open
        ldx #0
:       lda scratch,x
        sta vram_buf,y
        iny
        inx
        cpx #6
        bne :-
        jsr vq_close

        lda #$20
        sta tmp2
        lda #(32 + 29)
        sta tmp3
        lda #1
        ldx #0
        jsr vq_open
        lda lives
        cmp #10
        bcc :+
        lda #9
:       clc
        adc #(FONT_BASE + 27)
        sta vram_buf,y
        iny
        jsr vq_close
        lda #0
        sta hud_dirty
@done:  rts
.endproc

; ---------------------------------------------------------------------------
; hud_boss_bar -- 16 meter cells on row 2 driven by boss_hp / boss_maxhp
; ---------------------------------------------------------------------------
.proc hud_boss_bar
        lda boss_active
        beq @done
        ; cells = boss_hp * 16 / boss_maxhp, approximated by repeated subtract
        lda #0
        sta tmp1
        lda boss_hp
        sta tmp0
        ldx #0
@count: lda tmp0
        beq @fill
        sec
        sbc boss_step
        bcc @fill
        sta tmp0
        inx
        cpx #16
        bcc @count
@fill:  stx tmp1
        lda #$20
        sta tmp2
        lda #(64 + 8)
        sta tmp3
        lda #16
        ldx #0
        jsr vq_open
        ldx #0
:       cpx tmp1
        bcs :+
        lda #TILE_BOSS1
        bne :++
:       lda #TILE_BOSS0
:       sta vram_buf,y
        iny
        inx
        cpx #16
        bne :---
        jsr vq_close
@done:  rts
.endproc

; ---------------------------------------------------------------------------
; hud_text_at -- queue a zero-terminated string: ptr1 = text,
; tmp2/tmp3 = nametable address.  Characters are font indices already.
; ---------------------------------------------------------------------------
.proc hud_text_at
        ldy #0
:       lda (ptr1),y
        beq :+
        iny
        cpy #28
        bcc :-
:       tya
        beq @done
        pha
        ldx #0
        jsr vq_open
        pla
        sta tmp0
        tya
        tax                             ; X = queue cursor
        ldy #0
:       lda (ptr1),y
        clc
        adc #FONT_BASE
        sta vram_buf,x
        inx
        iny
        cpy tmp0
        bcc :-
        txa
        tay
        jmp vq_close
@done:  rts
.endproc

; ---------------------------------------------------------------------------
; hud_clear_rows -- blank HUD rows 0..2 (used by cutscenes)
; ---------------------------------------------------------------------------
.proc hud_clear_rows
        lda #$20
        sta tmp2
        lda #$00
        sta tmp3
        jsr set_addr
        ldy #0
        lda #FONT_BASE
:       sta PPUDATA
        iny
        cpy #96
        bne :-
        rts
.endproc

.segment "BSS"
boss_step: .res 1
.export boss_step

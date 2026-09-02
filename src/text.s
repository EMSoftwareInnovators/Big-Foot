;
; Text and full-screen drawing helpers used by the title, cutscenes and menus.
; All of these write straight to VRAM and require rendering to be off.
;
.include "constants.inc"
.include "ram.inc"
.include "bg.inc"

.import ppu_addr_xy, vq_open, vq_byte, vq_close

.export text_at, text_center, screen_clear, screen_fill_attr, text_len
.export draw_num2, text_at_ram, text_queue, text_center_queue, text_blank_row

.segment "CODE"

; ---------------------------------------------------------------------------
; ppuaddr_rowcol -- tmp0 = column, tmp1 = row -> PPUADDR of nametable A
; ---------------------------------------------------------------------------
.proc ppuaddr_rowcol
        bit PPUSTATUS
        lda tmp1
        lsr a
        lsr a
        lsr a
        clc
        adc #$20
        sta PPUADDR
        lda tmp1
        asl a
        asl a
        asl a
        asl a
        asl a
        clc
        adc tmp0
        sta PPUADDR
        rts
.endproc

; ---------------------------------------------------------------------------
; text_at -- ptr1 = $FF-terminated font-index string, tmp0 = column,
;            tmp1 = row.  Rendering must be off.  Index 0 is the space
;            glyph, which is why the terminator is not zero.
; ---------------------------------------------------------------------------
.proc text_at
        jsr ppuaddr_rowcol
        ldy #0
:       lda (ptr1),y
        cmp #$FF
        beq @done
        clc
        adc #FONT_BASE
        sta PPUDATA
        iny
        cpy #32
        bcc :-
@done:  rts
.endproc

; text_at_ram -- same but the source is the `scratch` buffer
.proc text_at_ram
        jsr ppuaddr_rowcol
        ldy #0
:       lda scratch,y
        cmp #$FF
        beq @done
        clc
        adc #FONT_BASE
        sta PPUDATA
        iny
        cpy #32
        bcc :-
@done:  rts
.endproc

; ---------------------------------------------------------------------------
; text_len -- ptr1 -> length in Y
; ---------------------------------------------------------------------------
.proc text_len
        ldy #0
:       lda (ptr1),y
        cmp #$FF
        beq @done
        iny
        cpy #32
        bcc :-
@done:  rts
.endproc

; ---------------------------------------------------------------------------
; text_center -- ptr1 = string, tmp1 = row
; ---------------------------------------------------------------------------
.proc text_center
        jsr text_len
        tya
        lsr a
        sta tmp0
        lda #16
        sec
        sbc tmp0
        sta tmp0
        jmp text_at
.endproc

; ---------------------------------------------------------------------------
; text_queue -- like text_at but through the VRAM queue, so a cutscene can
; print a line without switching rendering off.  ptr1 = string, tmp0 =
; column, tmp1 = row.  At most one line per frame; the queue is 176 bytes.
; ---------------------------------------------------------------------------
.proc text_queue
        ldy #0
:       lda (ptr1),y
        sta scratch,y
        cmp #$FF
        beq :+
        iny
        cpy #30
        bcc :-
:       sty tmp4
        tya                     ; sty leaves the flags alone
        beq done
        lda #0
        jsr ppu_addr_xy
        lda tmp4
        ldx #0
        jsr vq_open
        ldx #0
:       lda scratch,x
        clc
        adc #FONT_BASE
        jsr vq_byte
        inx
        cpx tmp4
        bcc :-
        jmp vq_close
done:   rts
.endproc

; text_center_queue -- ptr1 = string, tmp1 = row
.proc text_center_queue
        jsr text_len
        tya
        lsr a
        sta tmp0
        lda #16
        sec
        sbc tmp0
        sta tmp0
        jmp text_queue
.endproc

; ---------------------------------------------------------------------------
; text_blank_row -- queue 32 spaces over row A
; ---------------------------------------------------------------------------
.proc text_blank_row
        sta tmp1
        lda #0
        sta tmp0
        jsr ppu_addr_xy
        lda #32
        ldx #0
        jsr vq_open
        ldx #32
:       lda #FONT_BASE
        jsr vq_byte
        dex
        bne :-
        jmp vq_close
.endproc

; ---------------------------------------------------------------------------
; screen_clear -- blank both nametables with the space glyph
; ---------------------------------------------------------------------------
.proc screen_clear
        bit PPUSTATUS
        lda #$20
        sta PPUADDR
        lda #$00
        sta PPUADDR
        ldx #8
        ldy #0
        lda #FONT_BASE
:       sta PPUDATA
        iny
        bne :-
        dex
        bne :-
        rts
.endproc

; ---------------------------------------------------------------------------
; screen_fill_attr -- A = attribute byte, filled across both nametables
; ---------------------------------------------------------------------------
.proc screen_fill_attr
        sta tmp0
        bit PPUSTATUS
        lda #$23
        sta PPUADDR
        lda #$C0
        sta PPUADDR
        ldy #64
        lda tmp0
:       sta PPUDATA
        dey
        bne :-
        bit PPUSTATUS
        lda #$27
        sta PPUADDR
        lda #$C0
        sta PPUADDR
        ldy #64
        lda tmp0
:       sta PPUDATA
        dey
        bne :-
        rts
.endproc

; ---------------------------------------------------------------------------
; draw_num2 -- A = value 0..99 written as two glyphs at the current PPUADDR
; ---------------------------------------------------------------------------
.proc draw_num2
        ldx #0
:       cmp #10
        bcc :+
        sec
        sbc #10
        inx
        bne :-
:       pha
        txa
        clc
        adc #(FONT_BASE + 27)
        sta PPUDATA
        pla
        clc
        adc #(FONT_BASE + 27)
        sta PPUDATA
        rts
.endproc

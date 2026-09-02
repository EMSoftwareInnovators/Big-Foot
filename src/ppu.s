;
; PPU helpers: rendering control, palette upload, VRAM queue front end
;
.include "constants.inc"
.include "ram.inc"

.import wait_nmi
.export ppu_off, ppu_on, load_palette, vq_open, vq_close, vq_byte
.export fill_nametable, ppu_addr_xy, queue_palette, pal_buf_flush
.export set_ppu_addr

.segment "CODE"

; ---------------------------------------------------------------------------
; ppu_off -- stop rendering (safe to call at any time)
; ---------------------------------------------------------------------------
.proc ppu_off
        lda #0
        sta MMC3_IRQDISABLE
        lda #0
        sta render_on
        sta split_on
        sta nmi_ready
        lda ppu_ctrl
        and #$7F                ; NMI off while we work on VRAM
        sta ppu_ctrl
:       bit PPUSTATUS
        bpl :-
        lda #0
        sta PPUMASK
        sta ppu_mask
        sta PPUCTRL
        rts
.endproc

; ---------------------------------------------------------------------------
; ppu_on -- resume rendering on the next frame
; ---------------------------------------------------------------------------
.proc ppu_on
        lda #0
        sta vram_len
        sta vram_buf
:       bit PPUSTATUS
        bpl :-
        lda #$1E
        sta ppu_mask
        lda ppu_ctrl
        ora #$80
        sta ppu_ctrl
        sta PPUCTRL
        lda #1
        sta render_on
        rts
.endproc

; ---------------------------------------------------------------------------
; load_palette -- copy 32 bytes from (ptr0) into $3F00.  Rendering must be off.
; ---------------------------------------------------------------------------
.proc load_palette
        bit PPUSTATUS
        lda #$3F
        sta PPUADDR
        lda #$00
        sta PPUADDR
        ldy #0
:       lda (ptr0),y
        sta PPUDATA
        iny
        cpy #32
        bne :-
        rts
.endproc

; ---------------------------------------------------------------------------
; queue_palette -- queue all 32 palette bytes from (ptr0) for the next NMI
; ---------------------------------------------------------------------------
.proc queue_palette
        lda #$3F
        sta tmp2
        lda #$00
        sta tmp3
        lda #16
        ldx #0
        jsr vq_open
        tya
        tax                     ; X = queue cursor, Y = source index
        ldy #0
:       lda (ptr0),y
        sta vram_buf,x
        inx
        iny
        cpy #16
        bne :-
        txa
        tay
        jsr vq_close

        lda #$3F
        sta tmp2
        lda #$10
        sta tmp3
        lda #16
        ldx #0
        jsr vq_open
        tya
        tax
        ldy #16
:       lda (ptr0),y
        sta vram_buf,x
        inx
        iny
        cpy #32
        bne :-
        txa
        tay
        jmp vq_close
.endproc


; ---------------------------------------------------------------------------
; pal_buf_flush -- immediate palette write of 32 bytes from (ptr0)
; ---------------------------------------------------------------------------
pal_buf_flush = load_palette

; ---------------------------------------------------------------------------
; vq_open  -- start a VRAM packet.  A = data length, X = ctrl ($00 = +1,
;             $04 = +32), tmp2/tmp3 = destination address (hi/lo).
;             Returns Y positioned for the data bytes.
; ---------------------------------------------------------------------------
.proc vq_open
        ldy vram_len
        sta vram_buf,y
        iny
        txa
        sta vram_buf,y
        iny
        lda tmp2
        sta vram_buf,y
        iny
        lda tmp3
        sta vram_buf,y
        iny
        rts
.endproc

; ---------------------------------------------------------------------------
; vq_byte  -- append A as a data byte (Y = cursor)
; ---------------------------------------------------------------------------
.proc vq_byte
        sta vram_buf,y
        iny
        rts
.endproc

; ---------------------------------------------------------------------------
; vq_close -- terminate the queue (Y = cursor)
; ---------------------------------------------------------------------------
.proc vq_close
        sty vram_len
        lda #0
        sta vram_buf,y
        rts
.endproc

; ---------------------------------------------------------------------------
; set_ppu_addr -- tmp2/tmp3 -> PPUADDR (rendering must be off)
; ---------------------------------------------------------------------------
.proc set_ppu_addr
        bit PPUSTATUS
        lda tmp2
        sta PPUADDR
        lda tmp3
        sta PPUADDR
        rts
.endproc

; ---------------------------------------------------------------------------
; fill_nametable -- fill nametable A (tmp2 = high byte of base) with tile A.
;                   Rendering must be off.
; ---------------------------------------------------------------------------
.proc fill_nametable
        sta tmp0
        bit PPUSTATUS
        lda tmp2
        sta PPUADDR
        lda #0
        sta PPUADDR
        ldx #4
        ldy #0
        lda tmp0
:       sta PPUDATA
        iny
        bne :-
        dex
        bne :-
        rts
.endproc

; ---------------------------------------------------------------------------
; ppu_addr_xy -- tmp0 = tile column, tmp1 = tile row, A = nametable (0/1)
;                result in tmp2/tmp3
; ---------------------------------------------------------------------------
.proc ppu_addr_xy
        and #1
        lsr a                   ; carry = nametable select
        lda #$20
        bcc :+
        lda #$24
:       sta tmp2
        lda tmp1
        lsr a
        lsr a
        lsr a                   ; row >> 3
        ora tmp2
        sta tmp2
        lda tmp1
        asl a
        asl a
        asl a
        asl a
        asl a                   ; (row & 7) * 32
        ora tmp0
        sta tmp3
        rts
.endproc

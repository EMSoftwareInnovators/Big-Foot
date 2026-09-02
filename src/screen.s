;
; Full-screen picture loader.
;
; The title, intro and ending pictures live in the screen bank as a
; run-length encoded nametable, an encoded attribute table and a palette.
; Each picture also owns three 1 KiB CHR banks holding its 192 unique tiles,
; which are mapped into R2/R3/R4; R5 keeps the shared HUD/font bank so a
; picture can still print text with the game's own typeface.
;
.include "constants.inc"
.include "ram.inc"
.include "bg.inc"

.import set_prga000, apply_chr, load_palette, queue_palette
.import scr_bank, scr_nt_lo, scr_nt_hi, scr_at_lo, scr_at_hi
.import scr_pal_lo, scr_pal_hi

.export screen_load, screen_chr, screen_palette

; This has to live in a fixed bank: it maps the picture bank into $A000,
; which is exactly where the menu code that calls it would otherwise be.
.segment "CODE2"

; ---------------------------------------------------------------------------
; screen_load -- A = picture id.  Rendering must already be off.
; ---------------------------------------------------------------------------
.proc screen_load
        sta tmp8
        lda bank_a000
        sta tmp9
        lda #SCREEN_BANK
        jsr set_prga000

        ldx tmp8
        lda scr_pal_lo,x
        sta ptr0
        lda scr_pal_hi,x
        sta ptr0+1
        jsr load_palette

        bit PPUSTATUS
        lda #$20
        sta PPUADDR
        lda #$00
        sta PPUADDR
        ldx tmp8
        lda scr_nt_lo,x
        sta ptr0
        lda scr_nt_hi,x
        sta ptr0+1
        jsr rle_to_ppu

        bit PPUSTATUS
        lda #$23
        sta PPUADDR
        lda #$C0
        sta PPUADDR
        ldx tmp8
        lda scr_at_lo,x
        sta ptr0
        lda scr_at_hi,x
        sta ptr0+1
        jsr rle_to_ppu

        lda tmp9
        jsr set_prga000
        lda tmp8
        ; fall through
.endproc

; ---------------------------------------------------------------------------
; screen_chr -- A = picture id.  Point the background banks at its tiles.
; ---------------------------------------------------------------------------
.proc screen_chr
        tax
        lda bank_a000
        pha
        lda #SCREEN_BANK
        jsr set_prga000
        lda scr_bank,x
        sta chr_bg0
        clc
        adc #1
        sta chr_bg1
        clc
        adc #1
        sta chr_bg2
        lda #HUD_CHR_BANK
        sta chr_bg3
        pla
        jsr set_prga000
        jmp apply_chr
.endproc

; ---------------------------------------------------------------------------
; rle_to_ppu -- expand the stream at ptr0 straight into PPUDATA.
;
;       $00        end of stream
;       $01..$7F   copy this many following bytes
;       $81..$FF   repeat the next byte (b & $7F) times
; ---------------------------------------------------------------------------
.proc rle_to_ppu
        ldy #0
next:   lda (ptr0),y
        beq done
        bmi run
        sta tmp0                ; literal run
        jsr advance
lit:    lda (ptr0),y
        sta PPUDATA
        jsr advance
        dec tmp0
        bne lit
        beq next
run:    and #$7F
        sta tmp0
        jsr advance
        lda (ptr0),y
        sta tmp1
        jsr advance
rep:    lda tmp1
        sta PPUDATA
        dec tmp0
        bne rep
        beq next
done:   rts

advance:
        inc ptr0
        bne :+
        inc ptr0+1
:       rts
.endproc

; ---------------------------------------------------------------------------
; screen_palette -- A = picture id.  Queue that picture's palette for the
; next NMI, which is how the title screen comes back from a lightning flash.
; ---------------------------------------------------------------------------
.proc screen_palette
        tax
        lda bank_a000
        pha
        lda #SCREEN_BANK
        jsr set_prga000
        lda scr_pal_lo,x
        sta ptr0
        lda scr_pal_hi,x
        sta ptr0+1
        jsr queue_palette
        pla
        jmp set_prga000
.endproc

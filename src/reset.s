;
; Power-on / reset initialisation
;
.include "constants.inc"
.include "ram.inc"

.import mmc3_init, main_loop, ppu_off, audio_init
.export reset, warm_reset

.segment "CODE"

.proc reset
        sei
        cld
        ldx #$40
        stx APUFRAME            ; silence the frame IRQ
        ldx #$FF
        txs
        inx                     ; X = 0
        stx PPUCTRL             ; NMI off
        stx PPUMASK             ; rendering off
        stx $4010               ; DMC IRQ off

        bit PPUSTATUS
:       bit PPUSTATUS           ; first vblank
        bpl :-

        ; --- clear RAM while the PPU warms up ---------------------------
        lda #0
        tax
:       sta $0000,x
        sta $0100,x
        sta $0300,x
        sta $0400,x
        sta $0500,x
        sta $0600,x
        sta $0700,x
        lda #$FF                ; OAM shadow: park sprites off screen
        sta $0200,x
        lda #0
        inx
        bne :-

        jsr mmc3_init

:       bit PPUSTATUS           ; second vblank -- PPU is now stable
        bpl :-

        jsr clear_vram

        ; --- APU ---------------------------------------------------------
        lda #$0F
        sta APUSTATUS
        jsr audio_init

        ; --- engine defaults --------------------------------------------
        lda #$90                ; NMI on, BG pattern table at $1000
        sta ppu_ctrl
        lda #$1E
        sta ppu_mask
        lda #1
        sta render_on
        lda #$AC                ; a non-zero RNG seed
        sta rng_lo
        lda #$35
        sta rng_hi
        lda #3
        sta lives
        lda #MODE_TITLE
        sta game_mode
        sta mode_next

        lda #$80
        sta PPUCTRL             ; enable NMI (rendering still off)
        jmp main_loop
.endproc

; ---------------------------------------------------------------------------
; warm_reset -- soft restart used by the game-over "TITLE" option
; ---------------------------------------------------------------------------
.proc warm_reset
        jsr ppu_off
        ldx #$FF
        txs
        lda #3
        sta lives
        lda #0
        sta stage_num
        sta checkpoint
        sta shoe_flags
        lda #MODE_TITLE
        sta mode_next
        jmp main_loop
.endproc

; ---------------------------------------------------------------------------
; clear_vram -- blank nametables, attributes and palettes
; ---------------------------------------------------------------------------
.proc clear_vram
        lda #$3F
        sta PPUADDR
        lda #$00
        sta PPUADDR
        ldx #32
        lda #$0F
:       sta PPUDATA
        dex
        bne :-

        lda #$20
        sta PPUADDR
        lda #$00
        sta PPUADDR
        lda #0
        ldx #16                 ; 16 * 256 = 4096 bytes = all four nametables
        ldy #0
:       sta PPUDATA
        iny
        bne :-
        dex
        bne :-
        rts
.endproc

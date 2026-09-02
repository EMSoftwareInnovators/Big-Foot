;
; NMI handler.
;
; Frame order:
;   1. OAM DMA                       (must be first, needs full vblank)
;   2. drain the VRAM update queue
;   3. push CHR bank changes
;   4. park the scroll at (0,0) so the HUD renders unscrolled
;   5. arm the MMC3 scanline IRQ, which hands the playfield its own scroll
;      at the bottom of the status bar
;   6. tick the sound driver
;
; Steps 4 and 5 run on every NMI, not only on frames the main loop finished:
; if the HUD scroll were skipped the status bar would slide with the
; playfield whenever a frame overruns.
;
.include "constants.inc"
.include "ram.inc"

.import apply_chr, audio_tick
.export nmi_handler, irq_handler, wait_nmi

.segment "CODE"

.proc nmi_handler
        pha
        txa
        pha
        tya
        pha

        lda nmi_ready
        beq @noupdate

        ; ---- sprite DMA -------------------------------------------------
        lda #0
        sta OAMADDR
        lda #>oam_buf
        sta OAMDMA

        ; ---- queued VRAM writes ----------------------------------------
        jsr vram_flush

        ; ---- CHR banking ------------------------------------------------
        lda chr_dirty
        beq :+
        jsr apply_chr
:
        lda #0
        sta nmi_ready
@noupdate:
        ; ---- rendering flags --------------------------------------------
        ; These run on every NMI, not just on frames the main loop finished:
        ; if the HUD scroll were skipped the status bar would slide with the
        ; playfield whenever a frame overruns.
        lda ppu_mask
        sta PPUMASK
        lda ppu_ctrl
        and #$FE                ; force nametable 0 for the HUD strip
        sta PPUCTRL
        lda #0
        sta PPUSCROLL
        sta PPUSCROLL

        ; ---- arm the scanline split -------------------------------------
        ; The MMC3 counter clocks once per scanline off the PPU's A12 line
        ; (background patterns live at $1000, sprites at $0000), so latching
        ; 29 here fires the IRQ just before the playfield starts.
        lda split_on
        beq @nosplit
        lda render_on
        beq @nosplit
        lda #29
        sta MMC3_IRQLATCH
        sta MMC3_IRQRELOAD
        sta MMC3_IRQENABLE
        jmp @armed
@nosplit:
        lda #0
        sta MMC3_IRQDISABLE
@armed:
        inc nmi_count
        inc frame_count
        jsr audio_tick

        pla
        tay
        pla
        tax
        pla
        rti
.endproc

; ---------------------------------------------------------------------------
; vram_flush -- drain the update queue built by the main thread.
;
; Queue format (in vram_buf), packets back to back, $00 length terminates:
;       len            number of data bytes (1..64)
;       ctrl           $00 = increment by 1, $04 = increment by 32
;       addr_hi
;       addr_lo
;       data * len
; ---------------------------------------------------------------------------
.proc vram_flush
        lda vram_len
        beq @done
        ldx #0
@packet:
        lda vram_buf,x
        beq @finish
        sta nmi_tmp                ; length
        inx
        lda ppu_ctrl
        and #$FB                ; clear the increment bit ...
        ora vram_buf,x          ; ... and take it from the packet
        sta PPUCTRL
        inx
        lda vram_buf,x
        sta PPUADDR
        inx
        lda vram_buf,x
        sta PPUADDR
        inx
        ldy nmi_tmp
@copy:  lda vram_buf,x
        sta PPUDATA
        inx
        dey
        bne @copy
        jmp @packet
@finish:
        lda ppu_ctrl
        sta PPUCTRL
        lda #0
        sta vram_len
        sta vram_buf
@done:
        rts
.endproc

; ---------------------------------------------------------------------------
; wait_nmi -- hand the frame to the NMI and block until it has run
; ---------------------------------------------------------------------------
.proc wait_nmi
        lda #1
        sta nmi_ready
        lda nmi_count
:       cmp nmi_count
        beq :-
        rts
.endproc

; ---------------------------------------------------------------------------
; irq_handler -- the HUD/playfield split.
;
; Fires in the hblank after scanline 29.  Everything above stays at scroll
; (0,0) from nametable 0; from here down the playfield scroll takes over.
; The handler is deliberately tiny: it must finish inside hblank.
; ---------------------------------------------------------------------------
.proc irq_handler
        pha
        lda #0
        sta MMC3_IRQDISABLE             ; acknowledge
        lda ppu_ctrl
        ora scroll_nt
        sta PPUCTRL
        lda scroll_x
        sta PPUSCROLL
        lda #0
        sta PPUSCROLL
        pla
        rti
.endproc

.segment "VECTORS"
        .addr nmi_handler
        .import reset
        .addr reset
        .addr irq_handler

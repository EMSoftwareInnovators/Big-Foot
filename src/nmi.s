;
; NMI handler.
;
; Frame order:
;   1. OAM DMA                       (must be first, needs full vblank)
;   2. drain the VRAM update queue
;   3. push CHR bank changes
;   4. park the scroll at (0,0) so the HUD renders unscrolled
;   5. wait for the sprite-0 hit at scanline 24 and switch to the
;      camera scroll for the playfield
;   6. tick the music engine
;
; The sprite-0 split is used instead of an MMC3 scanline IRQ: it needs no
; cycle-exact timing and cannot desynchronise, which matters more here than
; the ~3000 cycles it costs.
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
        beq @light

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
        ; ---- rendering flags --------------------------------------------
        lda ppu_mask
        sta PPUMASK
        lda ppu_ctrl
        and #$FE                ; force nametable 0 for the HUD strip
        sta PPUCTRL
        lda #0
        sta PPUSCROLL
        sta PPUSCROLL

        lda split_on
        beq @nosplit
        lda render_on
        beq @nosplit
        jsr do_split
@nosplit:
        lda #0
        sta nmi_ready
@light:
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
; do_split -- wait for the sprite-0 hit, then hand the rest of the frame to
; the scrolled playfield.  Both waits are bounded so a missing hit can only
; cost one frame instead of hanging the machine.
; ---------------------------------------------------------------------------
.proc do_split
        ldx #8                  ; wait for the stale hit flag to clear
@clr:   ldy #0
@clr1:  bit PPUSTATUS
        bvc @hit
        dey
        bne @clr1
        dex
        bne @clr
        rts
@hit:   ldx #8                  ; wait for this frame's hit
@wait:  ldy #0
@wait1: bit PPUSTATUS
        bvs @done
        dey
        bne @wait1
        dex
        bne @wait
        rts
@done:
        lda ppu_ctrl
        ora scroll_nt
        sta PPUCTRL
        lda scroll_x
        sta PPUSCROLL
        lda #0
        sta PPUSCROLL
        rts
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
        sta tmp0                ; length
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
        ldy tmp0
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
; irq_handler -- unused (the MMC3 IRQ stays disabled)
; ---------------------------------------------------------------------------
.proc irq_handler
        rti
.endproc

.segment "VECTORS"
        .addr nmi_handler
        .import reset
        .addr reset
        .addr irq_handler

;
; MMC3 (mapper 4) control
;
; PRG mode 0:  $8000 = R6 (swappable)   $A000 = R7 (swappable)
;              $C000 = bank $1E fixed   $E000 = bank $1F fixed
; CHR mode 0:  R0 = 2 KiB @ $0000   R1 = 2 KiB @ $0800
;              R2..R5 = 1 KiB @ $1000/$1400/$1800/$1C00
;
; $0000-$0FFF is the sprite pattern table, $1000-$1FFF the background one.
;
.include "constants.inc"
.include "ram.inc"

.segment "CODE"

.export mmc3_init, set_prg8000, set_prga000, set_chr, apply_chr
.export bank_call_8000

; ---------------------------------------------------------------------------
; mmc3_init -- put the mapper in a known state
; ---------------------------------------------------------------------------
.proc mmc3_init
        lda #$00                ; horizontal-scrolling layout
        sta MMC3_MIRROR
        lda #$00
        sta MMC3_PRGRAM
        sta MMC3_IRQDISABLE     ; IRQs off until the NMI arms the HUD split
        ; sane default banks
        lda #0
        sta bank_8000
        lda #0                  ; bank 0 holds the shared data the engine needs
        sta bank_a000
        jsr set_prg_regs
        lda #0
        sta chr_bank_lo
        lda #2
        sta chr_bank_hi
        lda #4
        sta chr_bg0
        lda #5
        sta chr_bg1
        lda #6
        sta chr_bg2
        lda #7
        sta chr_bg3
        jmp apply_chr
.endproc

; ---------------------------------------------------------------------------
; set_prg_regs -- push bank_8000 / bank_a000 into R6 / R7
; ---------------------------------------------------------------------------
.proc set_prg_regs
        lda #6
        sta MMC3_BANKSEL
        lda bank_8000
        sta MMC3_BANKDATA
        lda #7
        sta MMC3_BANKSEL
        lda bank_a000
        sta MMC3_BANKDATA
        rts
.endproc

; ---------------------------------------------------------------------------
; set_prg8000 -- A = 8 KiB bank number for the $8000 window
;
; X and Y are preserved: callers routinely hold an index across a bank
; change, and a helper that quietly ate one caused a genuinely baffling bug.
; ---------------------------------------------------------------------------
.proc set_prg8000
        sta bank_8000
        pha
        lda #6
        sta MMC3_BANKSEL
        pla
        sta MMC3_BANKDATA
        rts
.endproc

; ---------------------------------------------------------------------------
; set_prga000 -- A = 8 KiB bank number for the $A000 window
; ---------------------------------------------------------------------------
.proc set_prga000
        sta bank_a000
        pha
        lda #7
        sta MMC3_BANKSEL
        pla
        sta MMC3_BANKDATA
        rts
.endproc

; ---------------------------------------------------------------------------
; set_chr -- X = MMC3 CHR register (0..5), A = 1 KiB bank value
;            (registers 0 and 1 select 2 KiB and ignore the low bit)
; ---------------------------------------------------------------------------
.proc set_chr
        stx MMC3_BANKSEL
        sta MMC3_BANKDATA
        rts
.endproc

; ---------------------------------------------------------------------------
; apply_chr -- push all six CHR shadow registers to the mapper
; ---------------------------------------------------------------------------
.proc apply_chr
        lda #0
        sta MMC3_BANKSEL
        lda chr_bank_lo
        sta MMC3_BANKDATA
        lda #1
        sta MMC3_BANKSEL
        lda chr_bank_hi
        sta MMC3_BANKDATA
        lda #2
        sta MMC3_BANKSEL
        lda chr_bg0
        sta MMC3_BANKDATA
        lda #3
        sta MMC3_BANKSEL
        lda chr_bg1
        sta MMC3_BANKDATA
        lda #4
        sta MMC3_BANKSEL
        lda chr_bg2
        sta MMC3_BANKDATA
        lda #5
        sta MMC3_BANKSEL
        lda chr_bg3
        sta MMC3_BANKDATA
        lda #0
        sta chr_dirty
        rts
.endproc

; ---------------------------------------------------------------------------
; bank_call_8000 -- call a routine that lives in a switchable $8000 bank.
;   A      = bank number
;   ptr0   = target address
; The previous bank is restored afterwards.  Y and X are passed through.
; ---------------------------------------------------------------------------
.proc bank_call_8000
        ldx bank_8000
        stx bank_save
        jsr set_prg8000
        jsr trampoline
        lda bank_save
        jmp set_prg8000
trampoline:
        jmp (ptr0)
.endproc

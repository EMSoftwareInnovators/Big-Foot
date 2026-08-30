;
; Controller polling
;
.include "constants.inc"
.include "ram.inc"

.export read_pads

.segment "CODE"

.proc read_pads
        lda pad1
        sta pad1_prev
        lda pad2
        sta pad2_prev
@again:
        lda #1
        sta JOY1
        lda #0
        sta JOY1
        ldx #8
:       lda JOY1
        lsr a
        rol tmp0
        lda JOY2
        lsr a
        rol tmp1
        dex
        bne :-
        ; read a second time and only accept a stable result (guards against
        ; the DMC/OAM read glitch on real hardware)
        lda #1
        sta JOY1
        lda #0
        sta JOY1
        ldx #8
:       lda JOY1
        lsr a
        rol tmp2
        lda JOY2
        lsr a
        rol tmp3
        dex
        bne :-
        lda tmp0
        cmp tmp2
        bne @again
        lda tmp1
        cmp tmp3
        bne @again

        lda tmp0
        sta pad1
        eor pad1_prev
        and pad1
        sta pad1_new
        lda tmp1
        sta pad2
        eor pad2_prev
        and pad2
        sta pad2_new
        rts
.endproc

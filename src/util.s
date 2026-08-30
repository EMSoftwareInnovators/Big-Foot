;
; Small shared helpers
;
.include "constants.inc"
.include "ram.inc"

.export rand, rand16, abs_a, neg16_ptr, memcpy_ptr, mul16x13, div_by_13
.export sign_extend_y

.segment "CODE"

; ---------------------------------------------------------------------------
; rand -- 16-bit xorshift-ish LFSR, returns a byte in A
; ---------------------------------------------------------------------------
.proc rand
        lda rng_hi
        lsr a
        lda rng_lo
        ror a
        eor rng_hi
        sta rng_hi
        lsr a
        eor rng_hi
        eor rng_lo
        sta rng_lo
        eor rng_hi
        rts
.endproc

rand16 = rand

; ---------------------------------------------------------------------------
; abs_a -- |A| with the original sign returned in carry (1 = was negative)
; ---------------------------------------------------------------------------
.proc abs_a
        cmp #$80
        bcc @pos
        eor #$FF
        clc
        adc #1
        sec
        rts
@pos:   clc
        rts
.endproc

; ---------------------------------------------------------------------------
; mul16x13 -- tmp0 = 8-bit value, result tmp0/tmp1 = value * 16
;             (column index -> byte offset in a stride-16 map)
; ---------------------------------------------------------------------------
.proc mul16x13
        lda tmp0
        sta tmp1
        lda #0
        sta tmp0
        lsr tmp1
        ror tmp0
        lsr tmp1
        ror tmp0
        lsr tmp1
        ror tmp0
        lsr tmp1
        ror tmp0
        rts
.endproc

div_by_13 = mul16x13

; ---------------------------------------------------------------------------
; neg16_ptr -- negate the 16-bit value in tmp0/tmp1
; ---------------------------------------------------------------------------
.proc neg16_ptr
        lda tmp0
        eor #$FF
        clc
        adc #1
        sta tmp0
        lda tmp1
        eor #$FF
        adc #0
        sta tmp1
        rts
.endproc

; ---------------------------------------------------------------------------
; sign_extend_y -- A holds a signed byte; returns A = A, Y = $FF or $00
; ---------------------------------------------------------------------------
.proc sign_extend_y
        ldy #0
        cmp #$80
        bcc :+
        ldy #$FF
:       rts
.endproc

; ---------------------------------------------------------------------------
; memcpy_ptr -- copy Y bytes from (ptr0) to (ptr1)
; ---------------------------------------------------------------------------
.proc memcpy_ptr
        sty tmp0
        ldy #0
:       lda (ptr0),y
        sta (ptr1),y
        iny
        cpy tmp0
        bne :-
        rts
.endproc

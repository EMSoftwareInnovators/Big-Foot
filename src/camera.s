;
; Camera: follows the player with a forward bias, clamps to the level and
; applies stomp screen shake.
;
.include "constants.inc"
.include "ram.inc"

.export camera_update, camera_snap, camera_apply, shake_start

.segment "CODE"

CAM_CENTER = 104

; ---------------------------------------------------------------------------
; camera_target -> ptr2 = desired cam_x, clamped to the level
; ---------------------------------------------------------------------------
.proc camera_target
        lda px
        sec
        sbc #CAM_CENTER
        sta ptr2
        lda px+1
        sbc #0
        sta ptr2+1
        bpl @hi
        lda #0
        sta ptr2
        sta ptr2+1
        rts
@hi:
        ; clamp to (level_cols * 16) - 256
        lda level_cols
        sta tmp0
        lda level_cols+1
        sta tmp1
        ldx #4
:       asl tmp0
        rol tmp1
        dex
        bne :-
        lda tmp0
        sec
        sbc #0
        sta tmp0
        lda tmp1
        sbc #1
        sta tmp1
        bmi @zero
        lda ptr2
        cmp tmp0
        lda ptr2+1
        sbc tmp1
        bcc @done
        lda tmp0
        sta ptr2
        lda tmp1
        sta ptr2+1
@done:  rts
@zero:  lda #0
        sta ptr2
        sta ptr2+1
        rts
.endproc

; ---------------------------------------------------------------------------
; camera_snap -- jump straight to the target (level start, respawn)
; ---------------------------------------------------------------------------
.proc camera_snap
        jsr camera_target
        lda ptr2
        sta cam_x
        lda ptr2+1
        sta cam_x+1
        rts
.endproc

; ---------------------------------------------------------------------------
; camera_update -- ease toward the target unless the camera is locked
; ---------------------------------------------------------------------------
.proc camera_update
        lda cam_lock
        bne @shake
        jsr camera_target
        ; move up to 4 pixels per frame toward ptr2
        lda ptr2
        sec
        sbc cam_x
        sta tmp0
        lda ptr2+1
        sbc cam_x+1
        sta tmp1
        ora tmp0
        beq @shake
        lda tmp1
        bmi @neg
        ; positive delta
        lda tmp1
        bne @fast
        lda tmp0
        cmp #5
        bcc @exact
@fast:  lda #4
        clc
        adc cam_x
        sta cam_x
        lda cam_x+1
        adc #0
        sta cam_x+1
        jmp @shake
@exact: clc
        adc cam_x
        sta cam_x
        lda cam_x+1
        adc #0
        sta cam_x+1
        jmp @shake
@neg:
        lda tmp1
        cmp #$FF
        bne @nfast
        lda tmp0
        cmp #$FC
        bcs @nexact
@nfast: lda cam_x
        sec
        sbc #4
        sta cam_x
        lda cam_x+1
        sbc #0
        sta cam_x+1
        jmp @shake
@nexact:
        lda cam_x
        clc
        adc tmp0
        sta cam_x
        lda cam_x+1
        adc tmp1
        sta cam_x+1
@shake:
        lda shake_timer
        beq camera_apply
        dec shake_timer
        jmp camera_apply
.endproc

; ---------------------------------------------------------------------------
; camera_apply -- publish cam_x to the scroll registers, adding shake
; ---------------------------------------------------------------------------
.proc camera_apply
        lda cam_x
        sta scroll_x
        lda cam_x+1
        and #1
        sta scroll_nt
        lda shake_timer
        beq @done
        lsr a
        bcc @done
        lda scroll_x
        clc
        adc shake_amt
        sta scroll_x
@done:  rts
.endproc

; ---------------------------------------------------------------------------
; shake_start -- A = duration in frames, X = amplitude
; ---------------------------------------------------------------------------
.proc shake_start
        sta shake_timer
        stx shake_amt
        rts
.endproc

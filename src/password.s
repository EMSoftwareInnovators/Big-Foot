;
; Passwords.
;
; Six letters carry the stage, the footwear the player has collected and the
; lives in hand, plus a checksum so a mistyped password is rejected rather
; than dropping someone into a half-initialised game.
;
;   byte 0  stage in bits 0..2, lives - 1 in bits 3..5
;   byte 1  the footwear bitmask
;   byte 2  checksum
;
; Those 24 bits become six nibbles, each rotated by its position so that
; adjacent stages do not produce nearly identical passwords, and each nibble
; indexes a sixteen-letter alphabet chosen to avoid look-alikes.
;
.include "constants.inc"
.include "ram.inc"
.include "bg.inc"
.include "levels.inc"

.import blank_screen, ppu_on, ppu_off, text_at, text_center
.import sfx_play, music_play
.import txt_pwenter, txt_pwbad, txt_pwhow, txt_pwyours
.import vq_open, vq_byte, vq_close, ppu_addr_xy

.export password_enter, password_run, pw_make, pw_draw_at

PW_LEN          = 6
PW_ROW          = 14
PW_COL          = 10            ; letters sit two columns apart
PW_STEP         = 2

.segment "MENU"

; the sixteen letters, as font glyph indices (A = 1)
pw_alpha:
        .byte 2, 4, 6, 7, 8, 10, 11, 12, 13, 14, 16, 18, 19, 20, 22, 26
        ;      B  D  F  G  H   J   K   L   M   N   P   R   S   T   V   Z

; ---------------------------------------------------------------------------
; pw_encode -- pack the current run into password_buf as six nibbles
; ---------------------------------------------------------------------------
.proc pw_encode
        lda lives
        beq :+
        sec
        sbc #1
:       and #7
        asl a
        asl a
        asl a
        ora stage_num
        sta tmp0                ; byte 0
        lda shoe_flags
        sta tmp1                ; byte 1
        lda tmp1                ; checksum: byte1*3 + byte0 + a constant
        asl a
        clc
        adc tmp1
        clc
        adc tmp0
        clc
        adc #$5A
        sta tmp2                ; byte 2

        ldx #0
        ldy #0
split:  lda tmp0,y
        lsr a
        lsr a
        lsr a
        lsr a
        sta password_buf,x
        inx
        lda tmp0,y
        and #$0F
        sta password_buf,x
        inx
        iny
        cpy #3
        bcc split

        ldx #0                  ; rotate each nibble by its position
rot:    txa
        asl a
        asl a
        clc
        adc password_buf,x
        and #$0F
        sta password_buf,x
        inx
        cpx #PW_LEN
        bcc rot
        rts
.endproc

; ---------------------------------------------------------------------------
; pw_decode -- unpack password_buf.  Returns carry set if it checks out.
; ---------------------------------------------------------------------------
.proc pw_decode
        ldx #0
unrot:  lda password_buf,x
        sta scratch,x
        txa
        asl a
        asl a
        sta tmp3
        lda scratch,x
        sec
        sbc tmp3
        and #$0F
        sta scratch,x
        inx
        cpx #PW_LEN
        bcc unrot

        ldx #0
        ldy #0
join:   lda scratch,x
        asl a
        asl a
        asl a
        asl a
        sta tmp3
        inx
        lda scratch,x
        ora tmp3
        sta tmp0,y
        inx
        iny
        cpy #3
        bcc join

        lda tmp1
        asl a
        clc
        adc tmp1
        clc
        adc tmp0
        clc
        adc #$5A
        cmp tmp2
        beq ok
        clc
        rts
ok:     lda tmp0
        and #7
        cmp #NUM_STAGES
        bcs bad
        sta stage_num
        lda tmp0
        lsr a
        lsr a
        lsr a
        and #7
        clc
        adc #1
        sta lives
        lda tmp1
        ora #1                  ; bare feet are never taken away
        sta shoe_flags
        lda #0
        sta checkpoint
        sec
        rts
bad:    clc
        rts
.endproc

; ---------------------------------------------------------------------------
; pw_make -- fill password_buf from the current run (for the clear screen)
; ---------------------------------------------------------------------------
.proc pw_make
        jmp pw_encode
.endproc

; ---------------------------------------------------------------------------
; pw_draw_at -- print password_buf at tmp0 = column, tmp1 = row, with
; rendering off.  Used by the stage-clear screen.
; ---------------------------------------------------------------------------
.proc pw_draw_at
        jsr ppu_addr_xy
        bit PPUSTATUS
        lda tmp2
        sta PPUADDR
        lda tmp3
        sta PPUADDR
        ldx #0
:       ldy password_buf,x
        lda pw_alpha,y
        clc
        adc #FONT_BASE
        sta PPUDATA
        lda #FONT_BASE          ; a space between letters
        sta PPUDATA
        inx
        cpx #PW_LEN
        bcc :-
        rts
.endproc

; ---------------------------------------------------------------------------
; the password entry screen
; ---------------------------------------------------------------------------
.proc password_enter
        jsr blank_screen
        lda #<txt_pwenter
        sta ptr1
        lda #>txt_pwenter
        sta ptr1+1
        lda #8
        sta tmp1
        jsr text_center
        lda #<txt_pwhow
        sta ptr1
        lda #>txt_pwhow
        sta ptr1+1
        lda #24
        sta tmp1
        jsr text_center
        ldx #PW_LEN - 1
        lda #0
:       sta password_buf,x
        dex
        bpl :-
        sta pw_cursor
        sta sub_state
        jsr ppu_on
        jmp pw_refresh
.endproc

.proc password_run
        lda sub_state
        beq @input
        dec sub_state           ; still showing the rejection message
        beq :+
        rts
:       jmp pw_refresh
@input:
        lda pad1_new
        and #BTN_RIGHT
        beq :+
        inc pw_cursor
        lda pw_cursor
        cmp #PW_LEN
        bcc @jmoved
        lda #0
        sta pw_cursor
@jmoved:
        jmp @moved
:       lda pad1_new
        and #BTN_LEFT
        beq :+
        dec pw_cursor
        lda pw_cursor
        bpl @jmoved
        lda #(PW_LEN - 1)
        sta pw_cursor
        jmp @moved
:       lda pad1_new
        and #(BTN_UP | BTN_SELECT)
        beq :+
        ldx pw_cursor
        inc password_buf,x
        lda password_buf,x
        and #$0F
        sta password_buf,x
        jmp @moved
:       lda pad1_new
        and #BTN_DOWN
        beq :+
        ldx pw_cursor
        dec password_buf,x
        lda password_buf,x
        and #$0F
        sta password_buf,x
        jmp @moved
:       lda pad1_new
        and #BTN_B
        beq :+
        lda #MODE_TITLE
        sta mode_next
        rts
:       lda pad1_new
        and #BTN_START
        beq @done
        jsr pw_decode
        bcc @bad
        lda #SFX_SHOE
        jsr sfx_play
        lda #MODE_STAGE_INTRO
        sta mode_next
        rts
@bad:
        lda #SFX_HURT
        jsr sfx_play
        lda #120
        sta sub_state
        lda #<txt_pwbad
        sta ptr1
        lda #>txt_pwbad
        sta ptr1+1
        lda #18
        sta tmp1
        jmp pw_center_queue
@moved:
        lda #SFX_SELECT
        jsr sfx_play
        jmp pw_refresh
@done:  rts
.endproc

; ---------------------------------------------------------------------------
; pw_refresh -- redraw the six letters and the marker under the cursor
; ---------------------------------------------------------------------------
.proc pw_refresh
        lda #PW_COL
        sta tmp0
        lda #PW_ROW
        sta tmp1
        lda #0
        jsr ppu_addr_xy
        lda #(PW_LEN * PW_STEP)
        ldx #0
        jsr vq_open
        ldx #0
letters:
        stx tmp4
        lda password_buf,x
        tax
        lda pw_alpha,x
        clc
        adc #FONT_BASE
        jsr vq_byte
        lda #FONT_BASE
        jsr vq_byte
        ldx tmp4
        inx
        cpx #PW_LEN
        bcc letters
        jsr vq_close

        lda #PW_COL
        sta tmp0
        lda #(PW_ROW + 1)
        sta tmp1
        lda #0
        jsr ppu_addr_xy
        lda #(PW_LEN * PW_STEP)
        ldx #0
        jsr vq_open
        ldx #0
marks:  cpx pw_cursor
        bne :+
        lda #TILE_RULE
        bne :++
:       lda #FONT_BASE
:       jsr vq_byte
        lda #FONT_BASE
        jsr vq_byte
        inx
        cpx #PW_LEN
        bcc marks
        jmp vq_close
.endproc

; ---------------------------------------------------------------------------
; pw_center_queue -- ptr1 = string, tmp1 = row, through the VRAM queue
; ---------------------------------------------------------------------------
.import text_center_queue
.proc pw_center_queue
        jmp text_center_queue
.endproc

;
; Title screen.
;
; The picture is a full-screen background (see tools/gen_screens.py); this
; file adds the menu, the cursor, the storm and the attract timeout.  The
; cursor is drawn as background tiles rather than a sprite because the
; sprite pattern table belongs to the foot, and the foot is not on this
; screen -- it is standing on the kingdom, in the picture.
;
.include "constants.inc"
.include "ram.inc"
.include "bg.inc"
.include "screens.inc"

.import ppu_off, ppu_on, screen_load, screen_palette, queue_palette
.import text_at, text_center, music_play, sfx_play, audio_stop
.import txt_pressstart, txt_pw
.import vq_open, vq_byte, vq_close, ppu_addr_xy

.export title_enter, title_run

ROW_START       = 26
ROW_PASSWORD    = 28
CURSOR_COL      = 8
ATTRACT         = 240           ; frames of silence before the intro plays

.segment "MENU"

; ---------------------------------------------------------------------------
.proc title_enter
        jsr audio_stop
        jsr ppu_off

        lda #SCR_TITLE
        jsr screen_load

        lda #10                 ; "PRESS START"
        sta tmp0
        lda #ROW_START
        sta tmp1
        lda #<txt_pressstart
        sta ptr1
        lda #>txt_pressstart
        sta ptr1+1
        jsr text_at

        lda #12                 ; "PASSWORD"
        sta tmp0
        lda #ROW_PASSWORD
        sta tmp1
        lda #<txt_pw
        sta ptr1
        lda #>txt_pw
        sta ptr1+1
        jsr text_at

        ; ---- a fresh run ------------------------------------------------
        lda #0
        sta stage_num
        sta checkpoint
        sta sub_state
        sta progress_flags
        sta score
        sta score+1
        sta score+2
        lda #1
        sta shoe_flags          ; bare feet are always available
        lda #3
        sta lives
        lda #0
        sta split_on

        lda #$10                ; background patterns at $1000, VRAM step 1
        sta ppu_ctrl
        jsr ppu_on
        jsr draw_cursor
        lda #MUS_TITLE
        jmp music_play
.endproc

; ---------------------------------------------------------------------------
.proc title_run
        lda pad1_new
        and #(BTN_UP | BTN_DOWN | BTN_SELECT)
        beq @nomove
        lda sub_state
        eor #1
        sta sub_state
        lda #SFX_SELECT
        jsr sfx_play
        jsr draw_cursor
        lda #0
        sta mode_timer          ; the attract timer restarts on any input
        beq @check
@nomove:
        jsr storm

@check:
        lda pad1_new
        and #(BTN_START | BTN_A)
        beq @attract
        lda #SFX_SELECT
        jsr sfx_play
        lda sub_state
        bne @password
        lda #MODE_INTRO
        sta mode_next
        rts
@password:
        lda #MODE_PASSWORD
        sta mode_next
        rts

@attract:
        lda mode_timer
        cmp #ATTRACT
        bcc @done
        lda #MODE_INTRO
        sta mode_next
@done:  rts
.endproc

; ---------------------------------------------------------------------------
; draw_cursor -- an arrow beside whichever line is selected
; ---------------------------------------------------------------------------
.proc draw_cursor
        lda #ROW_START
        sta tmp1
        lda sub_state
        beq :+
        lda #ROW_PASSWORD
        sta tmp1
:       lda #CURSOR_COL
        sta tmp0
        lda #0
        jsr ppu_addr_xy
        lda #1
        ldx #0
        jsr vq_open
        lda #TILE_ARROWR
        jsr vq_byte
        jsr vq_close

        lda #ROW_PASSWORD       ; and blank the other line's marker
        sta tmp1
        lda sub_state
        beq :+
        lda #ROW_START
        sta tmp1
:       lda #CURSOR_COL
        sta tmp0
        lda #0
        jsr ppu_addr_xy
        lda #1
        ldx #0
        jsr vq_open
        lda #FONT_BASE          ; the space glyph
        jsr vq_byte
        jmp vq_close
.endproc

; ---------------------------------------------------------------------------
; storm -- lightning: three frames of white sky every couple of seconds,
; then the picture's own palette is put back.
; ---------------------------------------------------------------------------
.proc storm
        lda frame_count
        and #$7F
        cmp #$70
        bne @maybe_restore
        lda #<flash_pal
        sta ptr0
        lda #>flash_pal
        sta ptr0+1
        jmp queue_palette
@maybe_restore:
        cmp #$74
        bne @done
        lda #SCR_TITLE
        jmp screen_palette
@done:  rts
.endproc

; The flash keeps the logo and the stonework where they are and blows out
; only the sky, which is what a lightning strike actually looks like.
flash_pal:
        .byte $30,$30,$30,$30
        .byte $0F,$27,$37,$30
        .byte $0F,$10,$30,$30
        .byte $0F,$16,$30,$30
        .byte $0F,$07,$27,$37
        .byte $0F,$06,$16,$30
        .byte $0F,$00,$10,$30
        .byte $0F,$01,$11,$30

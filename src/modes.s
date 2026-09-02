;
; Game-flow modes: stage intro, death, game over and stage clear.
;
.include "constants.inc"
.include "ram.inc"
.include "bg.inc"
.include "levels.inc"

.import ppu_off, ppu_on, screen_clear, text_at, text_center, screen_fill_attr
.import load_palette, oam_reset, oam_finish, music_play, audio_stop, sfx_play
.import stage_name_lo, stage_name_hi, warm_reset
.import start_stage, reload_stage
.import pw_make, pw_draw_at

.export stageintro_enter, stageintro_run
.export death_enter, death_run
.export gameover_enter, gameover_run
.export stageclear_enter, stageclear_run
.export map_enter, map_run
.export menu_palette, txt_stageword, blank_screen

.segment "MENU"

; ---------------------------------------------------------------------------
menu_palette:
        .byte $0F,$00,$10,$30, $0F,$06,$16,$30, $0F,$07,$28,$30, $0F,$01,$11,$21
        .byte $0F,$16,$27,$37, $0F,$00,$10,$30, $0F,$07,$17,$28, $0F,$01,$21,$31

txt_stageword:  .byte 19,20,1,7,5,$FF                       ; "STAGE"
txt_gameover:   .byte 7,1,13,5,0,15,22,5,18,$FF             ; "GAME OVER"
txt_continue:   .byte 3,15,14,20,9,14,21,5,$FF              ; "CONTINUE"
txt_password:   .byte 16,1,19,19,23,15,18,4,$FF             ; "PASSWORD"
txt_title:      .byte 20,9,20,12,5,$FF                      ; "TITLE"
txt_clear:      .byte 3,12,5,1,18,$FF                       ; "CLEAR"
txt_theend:     .byte 20,8,5,0,6,15,15,20,$FF               ; "THE FOOT"
txt_marches:    .byte 13,1,18,3,8,5,19,0,15,14,$FF          ; "MARCHES ON"
txt_lives:      .byte 12,9,22,5,19,$FF                      ; "LIVES"
txt_pwis:       .byte 16,1,19,19,23,15,18,4,43,$FF           ; "PASSWORD:"

; ---------------------------------------------------------------------------
; shared: paint a plain text screen
; ---------------------------------------------------------------------------
.proc plain_screen
        jsr ppu_off
        lda #<menu_palette
        sta ptr0
        lda #>menu_palette
        sta ptr0+1
        jsr load_palette
        jsr screen_clear
        lda #$00
        jsr screen_fill_attr
        lda #0
        sta split_on
        rts
.endproc

.proc show_screen
        jsr oam_reset
        jsr oam_finish
        lda #0
        sta scroll_x
        sta scroll_nt
        jmp ppu_on
.endproc

; ---------------------------------------------------------------------------
; blank_screen -- a plain black page with the menu palette, ready for text
; ---------------------------------------------------------------------------
.proc blank_screen
        jsr plain_screen
        jmp show_screen
.endproc

; ---------------------------------------------------------------------------
; STAGE INTRO -- "STAGE n" and the stage's name on black, then play
; ---------------------------------------------------------------------------
.proc stageintro_enter
        jsr audio_stop
        jsr plain_screen
        lda #12
        sta tmp0
        lda #11
        sta tmp1
        lda #<txt_stageword
        sta ptr1
        lda #>txt_stageword
        sta ptr1+1
        jsr text_at
        lda #18
        sta tmp0
        lda #11
        sta tmp1
        jsr stage_digit
        ldx stage_num
        lda stage_name_lo,x
        sta ptr1
        lda stage_name_hi,x
        sta ptr1+1
        lda #14
        sta tmp1
        jsr text_center
        lda #<txt_lives
        sta ptr1
        lda #>txt_lives
        sta ptr1+1
        lda #12
        sta tmp0
        lda #18
        sta tmp1
        jsr text_at
        lda #18
        sta tmp0
        lda #18
        sta tmp1
        jsr lives_digit
        jmp show_screen
.endproc

.proc stage_digit
        jsr ppuaddr_here
        lda stage_num
        clc
        adc #1
        clc
        adc #(FONT_BASE + 27)
        sta PPUDATA
        rts
.endproc

.proc lives_digit
        jsr ppuaddr_here
        lda lives
        cmp #10
        bcc :+
        lda #9
:       clc
        adc #(FONT_BASE + 27)
        sta PPUDATA
        rts
.endproc

.proc ppuaddr_here
        bit PPUSTATUS
        lda tmp1
        lsr a
        lsr a
        lsr a
        clc
        adc #$20
        sta PPUADDR
        lda tmp1
        asl a
        asl a
        asl a
        asl a
        asl a
        clc
        adc tmp0
        sta PPUADDR
        rts
.endproc

.proc stageintro_run
        lda mode_timer
        cmp #120
        bcc @wait
        lda #MODE_PLAY
        sta mode_next
        rts
@wait:
        lda pad1_new
        and #(BTN_START | BTN_A)
        beq :+
        lda #MODE_PLAY
        sta mode_next
:       rts
.endproc

; ---------------------------------------------------------------------------
; DEATH -- a short pause, then respawn at the last checkpoint
; ---------------------------------------------------------------------------
.proc death_enter
        jsr audio_stop
        lda lives
        beq :+
        dec lives
:       rts
.endproc

.proc death_run
        lda mode_timer
        cmp #60
        bcc @done
        lda lives
        beq @over
        lda #MODE_PLAY
        sta mode_next
        rts
@over:
        lda #MODE_GAMEOVER
        sta mode_next
@done:  rts
.endproc

; ---------------------------------------------------------------------------
; GAME OVER -- continue, password or title
; ---------------------------------------------------------------------------
.proc gameover_enter
        jsr audio_stop
        jsr plain_screen
        lda #<txt_gameover
        sta ptr1
        lda #>txt_gameover
        sta ptr1+1
        lda #9
        sta tmp1
        jsr text_center
        lda #<txt_continue
        sta ptr1
        lda #>txt_continue
        sta ptr1+1
        lda #13
        sta tmp0
        lda #15
        sta tmp1
        jsr text_at
        lda #<txt_password
        sta ptr1
        lda #>txt_password
        sta ptr1+1
        lda #13
        sta tmp0
        lda #17
        sta tmp1
        jsr text_at
        lda #<txt_title
        sta ptr1
        lda #>txt_title
        sta ptr1+1
        lda #13
        sta tmp0
        lda #19
        sta tmp1
        jsr text_at
        lda #0
        sta sub_state
        jsr show_screen
        lda #MUS_GAMEOVER
        jmp music_play
.endproc

.proc gameover_run
        lda pad1_new
        and #BTN_DOWN
        beq :+
        inc sub_state
        lda sub_state
        cmp #3
        bcc :+
        lda #0
        sta sub_state
:       lda pad1_new
        and #BTN_UP
        beq :+
        dec sub_state
        lda sub_state
        cmp #3
        bcc :+
        lda #2
        sta sub_state
:
        jsr cursor_sprite
        lda pad1_new
        and #(BTN_START | BTN_A)
        beq @done
        lda #SFX_SELECT
        jsr sfx_play
        lda sub_state
        beq @continue
        cmp #1
        beq @password
        jmp warm_reset
@continue:
        lda #3
        sta lives
        lda #MODE_PLAY
        sta mode_next
        rts
@password:
        lda #MODE_PASSWORD
        sta mode_next
@done:  rts
.endproc

; a foot glyph marks the highlighted menu row
.proc cursor_sprite
        jsr oam_reset
        lda sub_state
        asl a
        asl a
        asl a
        asl a
        clc
        adc #(15 * 8 - 1)
        ldx oam_idx
        sta oam_buf,x
        lda #TILE_FOOT
        sta oam_buf+1,x
        lda #2
        sta oam_buf+2,x
        lda #(11 * 8)
        sta oam_buf+3,x
        lda oam_idx
        clc
        adc #4
        sta oam_idx
        jmp oam_finish
.endproc

; ---------------------------------------------------------------------------
; STAGE CLEAR -- award the stage, then move on (or end the game)
; ---------------------------------------------------------------------------
.proc stageclear_enter
        jsr audio_stop
        jsr plain_screen
        lda #<txt_stageword
        sta ptr1
        lda #>txt_stageword
        sta ptr1+1
        lda #11
        sta tmp0
        lda #12
        sta tmp1
        jsr text_at
        lda #17
        sta tmp0
        lda #12
        sta tmp1
        jsr stage_digit
        lda #<txt_clear
        sta ptr1
        lda #>txt_clear
        sta ptr1+1
        lda #19
        sta tmp0
        lda #12
        sta tmp1
        jsr text_at

        ; The password resumes the run at the stage that comes next, so it
        ; is generated one stage ahead of the one just cleared.
        lda stage_num
        pha
        cmp #(NUM_STAGES - 1)
        bcs :+
        clc
        adc #1
        sta stage_num
:       jsr pw_make
        pla
        sta stage_num
        lda #<txt_pwis
        sta ptr1
        lda #>txt_pwis
        sta ptr1+1
        lda #16
        sta tmp1
        jsr text_center
        lda #10
        sta tmp0
        lda #18
        sta tmp1
        jsr pw_draw_at

        jsr show_screen
        lda #MUS_CLEAR
        jmp music_play
.endproc

.proc stageclear_run
        lda mode_timer
        cmp #180
        bcc @wait
@go:
        lda #0
        sta checkpoint
        inc stage_num
        lda stage_num
        cmp #NUM_STAGES
        bcc @next
        lda #(NUM_STAGES - 1)
        sta stage_num
        lda #MODE_ENDING
        sta mode_next
        rts
@next:
        lda #MODE_CUTSCENE
        sta mode_next
        rts
@wait:
        lda pad1_new
        and #(BTN_START | BTN_A)
        beq :+
        jmp @go
:       rts
.endproc

; ---------------------------------------------------------------------------
; MAP -- unused placeholder kept so the mode table stays dense
; ---------------------------------------------------------------------------
.proc map_enter
        rts
.endproc

.proc map_run
        lda #MODE_TITLE
        sta mode_next
        rts
.endproc

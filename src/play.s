;
; MODE_PLAY -- the main gameplay loop.
;
.include "constants.inc"
.include "ram.inc"
.include "bg.inc"
.include "levels.inc"

.import level_load, level_stream, level_anim, draw_full_screen
.import player_init, player_update, player_draw, player_respawn
.import camera_update, camera_snap, camera_apply
.import oam_reset, oam_finish
.import hud_draw_full, hud_update, hud_boss_bar
.import ppu_off, ppu_on, wait_nmi
.import entities_init, entities_update, entities_draw, spawn_check
.import particles_update, particles_draw
.import music_play, sfx_play, audio_stop
.import boss_update, boss_draw, boss_trigger

.export play_enter, play_run, start_stage, reload_stage

.segment "CODE2"

; ---------------------------------------------------------------------------
; start_stage -- A = stage number; enters MODE_PLAY from scratch
; ---------------------------------------------------------------------------
.proc start_stage
        sta stage_num
        lda #0
        sta checkpoint
        lda #MODE_PLAY
        sta mode_next
        rts
.endproc

.proc reload_stage
        lda #MODE_PLAY
        sta mode_next
        rts
.endproc

; ---------------------------------------------------------------------------
.proc play_enter
        jsr audio_stop
        jsr ppu_off
        lda #0
        sta cam_lock
        sta boss_active
        sta shake_timer
        sta pause_flag

        lda stage_num
        jsr level_load
        jsr entities_init
        jsr apply_checkpoint
        jsr player_respawn
        jsr camera_snap
        jsr draw_full_screen
        jsr hud_draw_full
        lda #1
        sta split_on
        jsr oam_reset
        jsr oam_finish
        jsr camera_apply
        jsr ppu_on
        lda level_music
        jsr music_play
        rts
.endproc

; ---------------------------------------------------------------------------
; apply_checkpoint -- move the start position to the reached checkpoint
; ---------------------------------------------------------------------------
.proc apply_checkpoint
        lda checkpoint
        beq @done
        ldy #0
        lda (check_ptr),y
        cmp checkpoint
        bcs :+
        sta checkpoint
:       lda checkpoint
        beq @done
        sec
        sbc #1
        sta tmp0
        asl a
        clc
        adc tmp0                        ; index * 3
        clc
        adc #1
        tay
        lda (check_ptr),y
        sta start_col
        iny
        lda (check_ptr),y
        sta start_col+1
        iny
        lda (check_ptr),y
        sta start_row
@done:  rts
.endproc

; ---------------------------------------------------------------------------
.proc play_run
        lda pad1_new
        and #BTN_START
        beq @nopause
        lda pause_flag
        eor #1
        sta pause_flag
        lda #SFX_PAUSE
        jsr sfx_play
@nopause:
        lda pause_flag
        beq :+
        rts
:
        jsr player_update
        jsr spawn_check
        jsr entities_update
        jsr boss_update
        jsr particles_update
        jsr camera_update
        jsr level_stream
        jsr level_anim
        jsr boss_trigger

        jsr oam_reset
        jsr player_draw
        jsr boss_draw
        jsr entities_draw
        jsr particles_draw
        jsr oam_finish
        jsr hud_update
        jsr hud_boss_bar

        ; ---- death handling ---------------------------------------------
        lda p_state
        cmp #PSTATE_DEAD
        bne @done
        lda p_timer
        bne @done
        lda #MODE_DEATH
        sta mode_next
@done:  rts
.endproc

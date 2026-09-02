;
; MODE_PLAY -- the main gameplay loop.
;
.include "constants.inc"
.include "ram.inc"
.include "bg.inc"
.include "levels.inc"
.include "entities.inc"

.import level_load, level_stream, level_anim, draw_full_screen
.import player_init, player_update, player_draw, player_respawn
.import camera_update, camera_snap, camera_apply
.import oam_reset, oam_finish
.import hud_draw_full, hud_update, hud_boss_bar
.import ppu_off, ppu_on, wait_nmi
.import entities_init, entities_update, entities_draw, spawn_check
.import particles_update, particles_draw
.import music_play, sfx_play, audio_stop
.import hud_text_at, hud_stage_label, txt_paused
.import boss_update, boss_trigger, boss_draw
.ifdef BF_DEBUG
.import spawn_entity
.endif

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
.ifdef BF_DEBUG
; ---------------------------------------------------------------------------
; debug_keys -- only assembled by `make DEBUG=1`.  SELECT is the modifier.
;   SELECT + START   clear the stage outright
;   SELECT + B       hand over every piece of footwear
;   SELECT + A       drop a rock at the player's toes
;   SELECT + UP      toggle invulnerability
;   SELECT + RIGHT   warp four metatiles forward
; ---------------------------------------------------------------------------
; The invulnerability flag borrows a byte of obj_state rather than
; adding one to the RAM map, which the release build would then carry.
dbg_inv = obj_state + 15

.proc debug_keys
        lda dbg_inv
        beq :+
        lda #$FF
        sta p_inv
:       lda pad1
        and #BTN_SELECT
        beq @done
        lda pad1_new
        and #BTN_START
        beq :+
        lda #MODE_STAGECLEAR
        sta mode_next
        rts
:       lda pad1_new
        and #BTN_B
        beq :+
        lda #$FF
        sta shoe_flags
        rts
:       lda pad1_new
        and #BTN_UP
        beq :+
        lda dbg_inv
        eor #1
        sta dbg_inv
        rts
:       lda pad1_new
        and #BTN_RIGHT
        beq :+
        lda px
        clc
        adc #64
        sta px
        lda px+1
        adc #0
        sta px+1
        jsr camera_snap         ; or the camera trails and the boss spawns
        jmp camera_apply        ; wherever the camera happens to be

:       lda pad1_new
        and #BTN_A
        beq @done
        lda px
        clc
        adc #10
        sta ptr2
        lda px+1
        adc #0
        sta ptr2+1
        lda py
        sta tmp7
        lda #ET_ROCK
        jsr spawn_entity
@done:  rts
.endproc
.endif

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
        sta hud_dirty           ; fills in the meter, lives and footwear
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
; check_checkpoint -- record the furthest checkpoint the player has passed
; ---------------------------------------------------------------------------
.proc check_checkpoint
        ldy #0
        lda (check_ptr),y
        beq @done
        sta tmp5                        ; number of checkpoints
        ; player column
        lda px
        sta tmp0
        lda px+1
        sta tmp1
        lsr tmp1
        ror tmp0
        lsr tmp1
        ror tmp0
        lsr tmp1
        ror tmp0
        lsr tmp1
        ror tmp0
        ldx #0
@loop:  cpx tmp5
        bcs @done
        txa
        asl a
        clc
        adc #1
        sta tmp6
        stx tmp7
        ldy tmp6
        lda (check_ptr),y
        sta tmp2
        iny
        lda (check_ptr),y
        sta tmp3
        lda tmp0
        cmp tmp2
        lda tmp1
        sbc tmp3
        bcc @next
        ldx tmp7
        inx
        cpx checkpoint
        bcc @next2
        beq @next2
        stx checkpoint
        lda #SFX_SELECT
        jsr sfx_play
@next2: ldx tmp7
@next:  ldx tmp7
        inx
        bne @loop
@done:  rts
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
.ifdef BF_DEBUG
        jsr debug_keys
        lda pad1
        and #BTN_SELECT
        beq :+
        rts                     ; SELECT is the debug modifier, not a pause
:
.endif
        lda pad1_new
        and #BTN_START
        beq @nopause
        lda pause_flag
        eor #1
        sta pause_flag
        lda #SFX_PAUSE
        jsr sfx_play
        lda pause_flag
        beq @unpause
        ; The status bar does not scroll, so the notice goes there rather
        ; than into the playfield, where it would slide away.
        lda #$20
        sta tmp2
        lda #(32 + 13)
        sta tmp3
        lda #<txt_paused
        sta ptr1
        lda #>txt_paused
        sta ptr1+1
        jsr hud_text_at
        jmp @nopause
@unpause:
        jsr hud_stage_label
        lda #1
        sta hud_dirty
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
        jsr check_checkpoint

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

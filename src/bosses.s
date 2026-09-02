;
; Bosses.
;
; Eight fights share one state machine driven by a per-boss parameter table
; and a four-step attack script.  That keeps every pattern learnable and
; telegraphed -- the boss always announces an attack with a wind-up frame --
; while still giving each encounter its own rhythm and reach.
;
.include "constants.inc"
.include "ram.inc"
.include "entities.inc"
.include "bg.inc"

.import draw_metasprite, spr_set_world, shake_start, sfx_play
.import spawn_entity, spawn_particle, entity_hurt_area, entities_init
.import player_hurt, music_play, apply_chr, hud_text_at, boss_step
.import boss_name_lo, boss_name_hi
.import rand

.export boss_update, boss_draw, boss_trigger, boss_hit_test, boss_damage

; boss states
BS_NONE   = 0
BS_INTRO  = 1
BS_IDLE   = 2
BS_WALK   = 3
BS_WIND   = 4
BS_ATTACK = 5
BS_RECOV  = 6
BS_HURT   = 7
BS_DEAD   = 8

; attack kinds
AK_SHOCK  = 0           ; ground shockwave in both directions
AK_SHOT   = 1           ; aimed projectile
AK_CHARGE = 2           ; horizontal dash
AK_SLAM   = 3           ; leap and crash down
AK_SPREAD = 4           ; three projectiles
AK_DROP   = 5           ; rise, hang, then drop on the player

.segment "CODE"

; ---------------------------------------------------------------------------
; per-boss parameters
; ---------------------------------------------------------------------------
b_hp:      .byte  16,  18,  22,  24,  26,  28,  32,  36
b_w:       .byte  28,  28,  44,  36,  44,  30,  52,  36
b_h:       .byte  42,  40,  46,  40,  46,  46,  54,  44
b_spd:     .byte $50, $70, $40, $68, $00, $58, $48, $80
b_jump:    .byte $04, $05, $04, $05, $00, $04, $03, $05
b_delay:   .byte  70,  60,  64,  56,  40,  58,  54,  46
b_touch:   .byte   2,   2,   3,   3,   3,   3,   4,   4
b_atk0:    .byte AK_CHARGE, AK_SHOT,   AK_SLAM,  AK_CHARGE, AK_SHOCK, AK_SHOT,   AK_SHOT,   AK_SLAM
b_atk1:    .byte AK_SHOCK,  AK_SPREAD, AK_SHOCK, AK_SLAM,   AK_DROP,  AK_SPREAD, AK_SLAM,   AK_CHARGE
b_atk2:    .byte AK_SLAM,   AK_DROP,   AK_DROP,  AK_SHOCK,  AK_SHOCK, AK_SLAM,   AK_SPREAD, AK_SHOCK
b_atk3:    .byte AK_CHARGE, AK_SHOT,   AK_SHOCK, AK_CHARGE, AK_DROP,  AK_DROP,   AK_CHARGE, AK_DROP
b_shot:    .byte ET_ARROW, ET_ARROW, ET_BOLT, ET_SPIT, ET_BOLT, ET_BOLT, ET_ARROW, ET_SPIT

FLOOR_Y = 176

; ---------------------------------------------------------------------------
; boss_trigger -- start the fight once the player enters the arena
; ---------------------------------------------------------------------------
.proc boss_trigger
        lda boss_active
        bne @done
        lda p_state
        cmp #PSTATE_DEAD
        beq @done
        ; player column >= boss_col + 3 ?
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
        lda boss_col
        clc
        adc #3
        sta tmp2
        lda boss_col+1
        adc #0
        sta tmp3
        lda tmp0
        cmp tmp2
        lda tmp1
        sbc tmp3
        bcc @done
        jsr boss_start
@done:  rts
.endproc

; ---------------------------------------------------------------------------
.proc boss_start
        lda #1
        sta boss_active
        sta cam_lock
        jsr entities_init

        ; the boss bank replaces the stage's enemy graphics for the fight
        lda boss_chr
        sta chr_bank_hi
        lda #1
        sta chr_dirty
        lda bms_lo_ptr
        sta ms_lo_ptr
        lda bms_lo_ptr+1
        sta ms_lo_ptr+1
        lda bms_hi_ptr
        sta ms_hi_ptr
        lda bms_hi_ptr+1
        sta ms_hi_ptr+1

        ldx boss_id
        lda b_hp,x
        sta boss_hp
        sta boss_maxhp
        lsr a
        lsr a
        lsr a
        lsr a
        ora #1
        sta boss_step
        lda #0
        sta boss_phase
        sta boss_sub
        sta boss_atk
        sta boss_frm
        sta boss_flash
        sta boss_vx
        sta boss_vx+1
        sta boss_vy
        sta boss_vy+1
        lda #BS_INTRO
        sta boss_state
        lda #120
        sta boss_timer

        ; place the boss on the right of the arena
        lda cam_x
        clc
        adc #200
        sta boss_x
        lda cam_x+1
        adc #0
        sta boss_x+1
        lda #FLOOR_Y
        sta boss_y
        lda #0
        sta boss_y+1
        lda #1
        sta boss_dir                    ; facing left
        lda boss_music
        jsr music_play
        jsr boss_banner
        lda #20
        ldx #3
        jmp shake_start
.endproc

; ---------------------------------------------------------------------------
; boss_banner -- print the boss's name across HUD row 2
; ---------------------------------------------------------------------------
.proc boss_banner
        ldx boss_id
        lda boss_name_lo,x
        sta ptr1
        lda boss_name_hi,x
        sta ptr1+1
        lda #$20
        sta tmp2
        lda #(64 + 3)
        sta tmp3
        jmp hud_text_at
.endproc

; ---------------------------------------------------------------------------
.proc boss_update
        lda boss_active
        bne :+
        rts
:       lda boss_flash
        beq :+
        dec boss_flash
:
        lda boss_state
        cmp #BS_DEAD
        bne :+
        jmp st_dead
:       cmp #BS_INTRO
        bne :+
        jmp st_intro
:
        jsr boss_face
        lda boss_state
        cmp #BS_WALK
        bne :+
        jmp st_walk
:       cmp #BS_WIND
        bne :+
        jmp st_wind
:       cmp #BS_ATTACK
        bne :+
        jmp st_attack
:       cmp #BS_RECOV
        bne :+
        jmp st_recov
:       jmp st_idle
.endproc

; ---------------------------------------------------------------------------
.proc st_intro
        dec boss_timer
        bne @wait
        lda #BS_WALK
        sta boss_state
        ldx boss_id
        lda b_delay,x
        sta boss_timer
@wait:
        lda #0
        sta boss_frm
        rts
.endproc

.proc st_dead
        lda boss_timer
        beq @over
        dec boss_timer
        lda boss_timer
        and #7
        bne @fall
        jsr boss_explode
@fall:
        lda boss_y
        cmp #(FLOOR_Y + 8)
        bcs :+
        inc boss_y
:       lda #2
        sta boss_frm
        rts
@over:
        lda #0
        sta boss_active
        sta cam_lock
        lda #MODE_STAGECLEAR
        sta mode_next
        rts
.endproc

; ---------------------------------------------------------------------------
.proc boss_face
        lda px+1
        cmp boss_x+1
        bcc @left
        bne @right
        lda px
        cmp boss_x
        bcc @left
@right: lda #0
        sta boss_dir
        rts
@left:  lda #1
        sta boss_dir
        rts
.endproc

; ---------------------------------------------------------------------------
.proc st_idle
        dec boss_timer
        bne @done
        lda #BS_WALK
        sta boss_state
        ldx boss_id
        lda b_delay,x
        sta boss_timer
@done:  lda #0
        sta boss_frm
        jmp boss_gravity
.endproc

; ---------------------------------------------------------------------------
.proc st_walk
        ldx boss_id
        lda b_spd,x
        beq @nowalk
        sta tmp0
        lda boss_dir
        beq @right
        lda boss_x
        sec
        sbc tmp0
        sta boss_x
        lda boss_x+1
        sbc #0
        sta boss_x+1
        jmp @clamp
@right:
        lda boss_x
        clc
        adc tmp0
        sta boss_x
        lda boss_x+1
        adc #0
        sta boss_x+1
@clamp: jsr boss_clamp
@nowalk:
        jsr boss_gravity
        inc boss_sub
        lda boss_sub
        lsr a
        lsr a
        lsr a
        and #1
        sta boss_frm
        dec boss_timer
        bne @done
        lda #BS_WIND
        sta boss_state
        lda #26
        sta boss_timer
@done:  rts
.endproc

; ---------------------------------------------------------------------------
; st_wind -- the telegraph.  Every attack is announced for 26 frames.
; ---------------------------------------------------------------------------
.proc st_wind
        jsr boss_gravity
        lda #1
        sta boss_frm
        dec boss_timer
        bne @done
        lda #BS_ATTACK
        sta boss_state
        lda #40
        sta boss_timer
        jsr boss_begin_attack
@done:  rts
.endproc

; ---------------------------------------------------------------------------
.proc boss_current_attack
        lda boss_atk
        and #3
        tay
        ldx boss_id
        cpy #0
        bne :+
        lda b_atk0,x
        rts
:       cpy #1
        bne :+
        lda b_atk1,x
        rts
:       cpy #2
        bne :+
        lda b_atk2,x
        rts
:       lda b_atk3,x
        rts
.endproc

.proc boss_begin_attack
        jsr boss_current_attack
        sta ent_tmp
        cmp #AK_SHOCK
        bne :+
        jmp atk_shock
:       cmp #AK_SHOT
        bne :+
        jmp atk_shot
:       cmp #AK_CHARGE
        bne :+
        jmp atk_charge
:       cmp #AK_SLAM
        bne :+
        jmp atk_slam
:       cmp #AK_SPREAD
        bne :+
        jmp atk_spread
:       jmp atk_drop
.endproc

; ---------------------------------------------------------------------------
.proc atk_shock
        lda #12
        sta boss_timer
        lda #20
        ldx #3
        jsr shake_start
        lda #SFX_MEGASTOMP
        jsr sfx_play
        ; two ground shots travelling apart
        jsr shot_pos
        ldx boss_id
        lda b_shot,x
        jsr spawn_entity
        bcs :+
        lda #$00
        sta e_vxl,x
        lda #$02
        sta e_vxh,x
        lda #FLOOR_Y
        sta e_yl,x
:       jsr shot_pos
        ldx boss_id
        lda b_shot,x
        jsr spawn_entity
        bcs :+
        lda #$00
        sta e_vxl,x
        lda #$FE
        sta e_vxh,x
        lda e_flags,x
        ora #EF_FACELEFT
        sta e_flags,x
        lda #FLOOR_Y
        sta e_yl,x
:       rts
.endproc

.proc shot_pos
        lda boss_x
        sta ptr2
        lda boss_x+1
        sta ptr2+1
        lda boss_y
        sec
        sbc #16
        sta tmp7
        rts
.endproc

.proc atk_shot
        lda #24
        sta boss_timer
        jsr shot_pos
        ldx boss_id
        lda b_shot,x
        jsr spawn_entity
        bcs @done
        jsr aim_shot
@done:  lda #SFX_ARROW
        jmp sfx_play
.endproc

.proc atk_spread
        lda #30
        sta boss_timer
        ldy #3
@loop:  sty ent_tmp2
        jsr shot_pos
        lda ent_tmp2
        sec
        sbc #1
        asl a
        asl a
        asl a
        clc
        adc tmp7
        sta tmp7
        ldx boss_id
        lda b_shot,x
        jsr spawn_entity
        bcs @next
        jsr aim_shot
@next:  ldy ent_tmp2
        dey
        bne @loop
        lda #SFX_ARROW
        jmp sfx_play
.endproc

; aim_shot -- send the freshly spawned entity X toward the player
.proc aim_shot
        lda boss_dir
        beq @right
        lda #$00
        sta e_vxl,x
        lda #$FE
        sta e_vxh,x
        lda e_flags,x
        ora #EF_FACELEFT
        sta e_flags,x
        rts
@right: lda #$00
        sta e_vxl,x
        lda #$02
        sta e_vxh,x
        rts
.endproc

.proc atk_charge
        lda #36
        sta boss_timer
        ldx boss_id
        lda b_spd,x
        asl a
        sta tmp0
        lda boss_dir
        beq @right
        lda #0
        sec
        sbc tmp0
        sta boss_vx
        lda #$FF
        sta boss_vx+1
        rts
@right: lda tmp0
        sta boss_vx
        lda #0
        sta boss_vx+1
        rts
.endproc

.proc atk_slam
        lda #48
        sta boss_timer
        ldx boss_id
        lda b_jump,x
        eor #$FF
        clc
        adc #1
        sta boss_vy+1
        lda #0
        sta boss_vy
        ldx boss_id
        lda b_spd,x
        sta tmp0
        lda boss_dir
        beq @right
        lda #0
        sec
        sbc tmp0
        sta boss_vx
        lda #$FF
        sta boss_vx+1
        rts
@right: lda tmp0
        sta boss_vx
        lda #0
        sta boss_vx+1
        rts
.endproc

.proc atk_drop
        lda #56
        sta boss_timer
        lda #$FC
        sta boss_vy+1
        lda #0
        sta boss_vy
        sta boss_vx
        sta boss_vx+1
        lda #1
        sta boss_sub
        rts
.endproc

; ---------------------------------------------------------------------------
.proc st_attack
        lda #2
        sta boss_frm
        ; horizontal motion
        lda boss_x
        clc
        adc boss_vx
        sta boss_x
        lda boss_x+1
        adc boss_vx+1
        sta boss_x+1
        jsr boss_clamp
        jsr boss_gravity
        dec boss_timer
        bne @done
        lda #0
        sta boss_vx
        sta boss_vx+1
        sta boss_sub
        lda #BS_RECOV
        sta boss_state
        lda #34
        sta boss_timer
        inc boss_atk
@done:  rts
.endproc

.proc st_recov
        jsr boss_gravity
        lda #0
        sta boss_frm
        dec boss_timer
        bne @done
        lda #BS_WALK
        sta boss_state
        ldx boss_id
        lda b_delay,x
        sta boss_timer
        ; phase two: half health makes the boss noticeably more aggressive
        lda boss_hp
        asl a
        cmp boss_maxhp
        bcs @done
        lda #1
        sta boss_phase
        lda boss_timer
        lsr a
        sta boss_timer
@done:  rts
.endproc

; ---------------------------------------------------------------------------
.proc boss_gravity
        lda boss_vy
        clc
        adc #$40
        sta boss_vy
        lda boss_vy+1
        adc #0
        sta boss_vy+1
        cmp #6
        bcc :+
        lda #6
        sta boss_vy+1
:
        lda boss_y+1
        clc
        adc boss_vy
        sta boss_y+1
        lda boss_y
        adc boss_vy+1
        sta boss_y
        cmp #FLOOR_Y
        bcc @air
        lda boss_vy+1
        bmi @air
        lda #FLOOR_Y
        sta boss_y
        lda #0
        sta boss_y+1
        sta boss_vy
        sta boss_vy+1
        lda boss_sub
        beq @done
        lda #0
        sta boss_sub
        lda #16
        ldx #4
        jsr shake_start
        lda #SFX_MEGASTOMP
        jsr sfx_play
@air:
@done:  rts
.endproc

; keep the boss inside the visible arena
.proc boss_clamp
        lda boss_x
        sec
        sbc cam_x
        sta tmp0
        lda boss_x+1
        sbc cam_x+1
        bne @fix
        lda tmp0
        cmp #24
        bcc @fix
        cmp #216
        bcs @fixr
        rts
@fix:
        lda cam_x
        clc
        adc #24
        sta boss_x
        lda cam_x+1
        adc #0
        sta boss_x+1
        rts
@fixr:
        lda cam_x
        clc
        adc #216
        sta boss_x
        lda cam_x+1
        adc #0
        sta boss_x+1
        rts
.endproc

; ---------------------------------------------------------------------------
; boss_hit_test -- carry set when the attack box overlaps the boss
; ---------------------------------------------------------------------------
.proc boss_hit_test
        lda boss_active
        beq @no
        lda boss_state
        cmp #BS_INTRO
        beq @no
        cmp #BS_DEAD
        beq @no
        ldx boss_id
        lda boss_x
        cmp atk_x1
        lda boss_x+1
        sbc atk_x1+1
        bcc @no
        lda atk_x2
        cmp boss_x
        lda atk_x2+1
        sbc boss_x+1
        bcc @no
        lda boss_y
        cmp atk_y1
        bcc @no
        lda boss_y
        sec
        sbc b_h,x
        cmp atk_y2
        bcs @no
        sec
        rts
@no:    clc
        rts
.endproc

; ---------------------------------------------------------------------------
; boss_damage -- A = damage
; ---------------------------------------------------------------------------
.proc boss_damage
        ldx boss_flash
        bne @done
        sta tmp0
        lda boss_hp
        sec
        sbc tmp0
        bcc @die
        beq @die
        sta boss_hp
        lda #16
        sta boss_flash
        lda #SFX_BOSSHIT
        jsr sfx_play
        jmp boss_spark
@die:
        lda #0
        sta boss_hp
        lda #BS_DEAD
        sta boss_state
        lda #150
        sta boss_timer
        lda #SFX_BOSSDIE
        jsr sfx_play
        lda #60
        ldx #4
        jmp shake_start
@done:  rts
.endproc

.proc boss_spark
        lda boss_x
        sta ptr2
        lda boss_x+1
        sta ptr2+1
        ldx boss_id
        lda boss_y
        sec
        sbc b_h,x
        clc
        adc #12
        sta tmp7
        lda #ET_SPARK
        jmp spawn_particle
.endproc

.proc boss_explode
        jsr rand
        and #$1F
        sta tmp0
        lda boss_x
        clc
        adc tmp0
        sec
        sbc #16
        sta ptr2
        lda boss_x+1
        adc #0
        sta ptr2+1
        jsr rand
        and #$1F
        sta tmp0
        ldx boss_id
        lda boss_y
        sec
        sbc b_h,x
        clc
        adc tmp0
        sta tmp7
        lda #ET_SPARK
        jsr spawn_particle
        lda #SFX_BOSSHIT
        jmp sfx_play
.endproc

; ---------------------------------------------------------------------------
; boss contact damage and drawing
; ---------------------------------------------------------------------------
.proc boss_draw
        lda boss_active
        bne :+
        rts
:       lda boss_flash
        beq :+
        and #2
        beq :+
        rts
:
        jsr boss_touch
        lda #ET_BOSS
        asl a
        asl a
        clc
        adc boss_frm
        tay
        lda (ms_lo_ptr),y
        sta ptr1
        lda (ms_hi_ptr),y
        sta ptr1+1
        ora ptr1
        bne :+
        rts
:       lda boss_x
        sta ptr2
        lda boss_x+1
        sta ptr2+1
        lda boss_y
        sta tmp4
        jsr spr_set_world
        bcs @done
        lda #1
        sta spr_attr
        lda boss_dir
        beq :+
        lda #$40
:       sta spr_flip
        jsr draw_metasprite
@done:  rts
.endproc

.proc boss_touch
        lda boss_state
        cmp #BS_INTRO
        beq @no
        cmp #BS_DEAD
        beq @no
        ldx boss_id
        ; horizontal overlap
        lda boss_x
        sec
        sbc px
        sta tmp0
        lda boss_x+1
        sbc px+1
        bpl :+
        lda #0
        sec
        sbc tmp0
        sta tmp0
        lda #0
:       bne @no
        lda b_w,x
        lsr a
        clc
        adc #(PBOX_W / 2)
        cmp tmp0
        bcc @no
        ; vertical overlap
        lda boss_y
        sec
        sbc b_h,x
        sta tmp2
        lda py
        sec
        sbc #PBOX_H
        cmp boss_y
        bcs @no
        lda py
        cmp tmp2
        bcc @no
        lda b_touch,x
        pha
        lda px+1
        cmp boss_x+1
        bcc @kleft
        bne @kright
        lda px
        cmp boss_x
        bcc @kleft
@kright: ldx #0
        beq @hurt
@kleft: ldx #1
@hurt:  pla
        jmp player_hurt
@no:    rts
.endproc

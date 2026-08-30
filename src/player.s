;
; Big Foot: movement, collision, combat states and animation.
;
; Positions are 16.8 fixed point (px/px_sub).  The collision box is 20x22
; pixels with its origin at the bottom centre, which is much smaller than the
; 40x48 metasprite -- the visible toes and ankle never take a hit that the
; player could not see coming.
;
.include "constants.inc"
.include "ram.inc"
.include "player_frames.inc"

.import flags_at_xy, mt_at, break_tile, rand
.import pf_bank, pf_ms_lo, pf_ms_hi, pf_remap, panim_tbl_lo, panim_tbl_hi
.import draw_metasprite, spr_set_world, shake_start
.import sfx_play, spawn_particle, player_attack_box, entity_hurt_area
.import set_prga000

.export player_init, player_update, player_draw, player_anim_set
.export player_hurt, player_respawn, probe_flags, p_solid_below
.export player_kill, add_health, give_shoe

PBOX_HALF   = 10
PBOX_TOP    = 22

GRAVITY     = $38
GRAV_WATER  = $14
MAXFALL     = $0480
MAXFALL_W   = $0140
JUMP_VEL    = $0470
JUMP_CUT    = $0180
AIRSTOMP_V  = $0700

.segment "CODE2"

; ---------------------------------------------------------------------------
; per-footwear physics: bare, running, steel, cowboy, cleat, flipper,
; slipper, big shoe
; ---------------------------------------------------------------------------
shoe_maxwalk_l: .byte $40,$00,$C0,$20,$40,$80,$60,$00
shoe_maxwalk_h: .byte $01,$02,$00,$01,$01,$00,$01,$01
shoe_maxrun_l:  .byte $30,$40,$80,$00,$20,$00,$60,$C0
shoe_maxrun_h:  .byte $02,$03,$01,$02,$02,$01,$02,$01
shoe_accel:     .byte $20,$2C,$16,$1E,$24,$14,$26,$18
shoe_friction:  .byte $18,$10,$20,$1A,$26,$0C,$08,$1C
shoe_jump_l:    .byte $70,$D0,$C0,$60,$80,$00,$90,$20
shoe_jump_h:    .byte $04,$04,$03,$04,$04,$04,$04,$04
shoe_kick:      .byte $02,$01,$04,$05,$02,$03,$01,$06
shoe_stomp:     .byte $03,$01,$04,$02,$03,$01,$01,$06

; ---------------------------------------------------------------------------
.proc player_init
        lda #0
        sta vx
        sta vx+1
        sta vy
        sta vy+1
        sta p_state
        sta p_inv
        sta p_timer
        sta p_coyote
        sta p_jumpbuf
        sta p_recoil
        sta p_walkdist
        sta p_bounce
        sta p_flash
        lda #$FF
        sta p_carry
        lda #PLAYER_MAX_HP
        sta p_hp_max
        sta p_hp
        lda #ANIM_IDLE
        jsr player_anim_set
        rts
.endproc

; ---------------------------------------------------------------------------
; player_respawn -- place the foot at start_col/start_row
; ---------------------------------------------------------------------------
.proc player_respawn
        lda start_col
        sta px
        lda start_col+1
        sta px+1
        ldx #4
:       asl px
        rol px+1
        dex
        bne :-
        lda px
        clc
        adc #8
        sta px
        lda px+1
        adc #0
        sta px+1
        lda start_row
        asl a
        asl a
        asl a
        asl a
        clc
        adc #16
        sta py
        lda #0
        sta py+1
        sta px_sub
        sta py_sub
        jsr player_init
        rts
.endproc

; ---------------------------------------------------------------------------
; probe_flags -- collision class at (px + signed A, py + signed X)
; ---------------------------------------------------------------------------
.proc probe_flags
        sta tmp8
        stx tmp9
        lda tmp8
        bmi @negx
        clc
        adc px
        sta ptr0
        lda px+1
        adc #0
        sta ptr0+1
        jmp @yy
@negx:
        clc
        adc px
        sta ptr0
        lda px+1
        adc #$FF
        sta ptr0+1
@yy:
        lda tmp9
        clc
        adc py
        sta tmp4
        jmp flags_at_xy
.endproc

; ---------------------------------------------------------------------------
; is_solid_class -- carry set when A blocks movement
; ---------------------------------------------------------------------------
.proc is_solid_class
        cmp #COL_SOLID
        beq @yes
        cmp #COL_BREAK
        beq @yes
        cmp #COL_ICE
        beq @yes
        clc
        rts
@yes:   sec
        rts
.endproc

; ---------------------------------------------------------------------------
; p_solid_below -- carry set if solid ground is directly under the box.
; Also records the ground's collision class in p_ground_type.
; ---------------------------------------------------------------------------
.proc p_solid_below
        ldx #0
        lda #(256 - PBOX_HALF)
        jsr probe_flags
        sta tmp0
        ldx #0
        lda #0
        jsr probe_flags
        cmp tmp0
        beq :+
        jsr merge_class
        jmp :++
:       lda tmp0
:       sta tmp0
        ldx #0
        lda #(PBOX_HALF - 1)
        jsr probe_flags
        jsr merge_class
        sta p_ground_type
        jmp is_solid_class
.endproc

.proc merge_class
        cmp #COL_EMPTY
        bne :+
        lda tmp0
        rts
:       sta tmp1
        lda tmp0
        cmp #COL_EMPTY
        bne :+
        lda tmp1
        rts
:       lda tmp1
        rts
.endproc

; ---------------------------------------------------------------------------
; player_update
; ---------------------------------------------------------------------------
.proc player_update
        lda p_inv
        beq :+
        dec p_inv
:       lda p_flash
        beq :+
        dec p_flash
:       lda p_shoetimer
        beq :+
        dec p_shoetimer
:
        lda p_state
        cmp #PSTATE_DEAD
        bne :+
        jmp state_dead
:       cmp #PSTATE_HURT
        bne :+
        jmp state_hurt
:
        jsr read_ground
        jsr do_input
        jsr apply_physics
        jsr anim_select
        jsr anim_tick
        rts
.endproc

; ---------------------------------------------------------------------------
.proc read_ground
        lda p_ground
        sta p_wasground
        jsr p_solid_below
        bcs @on
        lda p_ground_type
        cmp #COL_PLATFORM
        beq @maybe
        lda #0
        sta p_ground
        lda p_coyote
        beq :+
        dec p_coyote
:       rts
@maybe:
        ; one-way platforms only catch a descending foot near the tile top
        lda vy+1
        bmi @off
        lda py
        and #$0F
        cmp #6
        bcs @off
        lda #1
        sta p_ground
        lda #6
        sta p_coyote
        rts
@off:   lda #0
        sta p_ground
        rts
@on:    lda #1
        sta p_ground
        lda #6
        sta p_coyote
        rts
.endproc

; ---------------------------------------------------------------------------
.proc do_input
        lda p_state
        cmp #PSTATE_KICK
        beq @busy
        cmp #PSTATE_STOMP
        beq @busy
        cmp #PSTATE_AIRSTOMP
        beq @airstomp
        cmp #PSTATE_LAND
        bne @free
        dec p_timer
        bne @nomove
        lda #PSTATE_NORMAL
        sta p_state
@free:
        jsr walk_input
        jsr jump_input
        jsr attack_input
        rts
@busy:
        dec p_timer
        bne :+
        lda #PSTATE_NORMAL
        sta p_state
:       jsr friction_only
        rts
@airstomp:
        lda p_ground
        beq :+
        jmp stomp_land
:       lda #<AIRSTOMP_V
        sta vy
        lda #>AIRSTOMP_V
        sta vy+1
        rts
@nomove:
        jmp friction_only
.endproc

; ---------------------------------------------------------------------------
.proc walk_input
        lda pad1
        and #(BTN_LEFT | BTN_RIGHT)
        beq @nokey
        and #BTN_RIGHT
        beq @left
        lda #0
        sta p_face
        jsr accel_right
        jmp @dist
@left:  lda #1
        sta p_face
        jsr accel_left
@dist:
        lda p_ground
        beq :+
        inc p_walkdist
:       rts
@nokey: jmp friction_only
.endproc

.proc accel_right
        ldx p_shoe
        lda shoe_accel,x
        sta tmp0
        lda p_ground
        bne :+
        lsr tmp0                        ; reduced air control
:       lda vx
        clc
        adc tmp0
        sta vx
        lda vx+1
        adc #0
        sta vx+1
        jmp clamp_speed
.endproc

.proc accel_left
        ldx p_shoe
        lda shoe_accel,x
        sta tmp0
        lda p_ground
        bne :+
        lsr tmp0
:       lda vx
        sec
        sbc tmp0
        sta vx
        lda vx+1
        sbc #0
        sta vx+1
        jmp clamp_speed
.endproc

; ---------------------------------------------------------------------------
; clamp_speed -- hold |vx| under the current footwear's limit.  Holding B
; while running is not required: the foot simply builds up speed.
; ---------------------------------------------------------------------------
.proc clamp_speed
        ldx p_shoe
        lda p_walkdist
        cmp #40
        bcc @walkcap
        lda shoe_maxrun_l,x
        sta tmp0
        lda shoe_maxrun_h,x
        sta tmp1
        jmp @clamp
@walkcap:
        lda shoe_maxwalk_l,x
        sta tmp0
        lda shoe_maxwalk_h,x
        sta tmp1
@clamp:
        lda vx+1
        bmi @neg
        lda vx+1
        cmp tmp1
        bcc @done
        bne @sethi
        lda vx
        cmp tmp0
        bcc @done
@sethi: lda tmp0
        sta vx
        lda tmp1
        sta vx+1
        rts
@neg:
        ; compare |vx| against the cap
        lda #0
        sec
        sbc tmp0
        sta tmp2
        lda #0
        sbc tmp1
        sta tmp3
        lda vx+1
        cmp tmp3
        bcc @setlo
        bne @done
        lda vx
        cmp tmp2
        bcs @done
@setlo: lda tmp2
        sta vx
        lda tmp3
        sta vx+1
@done:  rts
.endproc

; ---------------------------------------------------------------------------
.proc friction_only
        ldx p_shoe
        lda shoe_friction,x
        sta tmp0
        lda p_ground_type
        cmp #COL_ICE
        bne :+
        lda #4
        sta tmp0
:       lda p_ground
        bne :+
        lsr tmp0
        lsr tmp0
:       lda #0
        sta p_walkdist
        lda vx+1
        bmi @neg
        ora vx
        beq @zero
        lda vx
        sec
        sbc tmp0
        sta vx
        lda vx+1
        sbc #0
        sta vx+1
        bpl @done
@zero:  lda #0
        sta vx
        sta vx+1
        rts
@neg:
        lda vx
        clc
        adc tmp0
        sta vx
        lda vx+1
        adc #0
        sta vx+1
        bmi @done
        lda #0
        sta vx
        sta vx+1
@done:  rts
.endproc

; ---------------------------------------------------------------------------
.proc jump_input
        lda pad1_new
        and #BTN_A
        beq @held
        lda #6
        sta p_jumpbuf
@held:
        lda p_jumpbuf
        beq @cut
        lda p_coyote
        beq @cut
        lda p_inwater
        bne @swim
        lda #0
        sta p_jumpbuf
        sta p_coyote
        sta p_ground
        ldx p_shoe
        lda shoe_jump_l,x
        sta tmp0
        lda shoe_jump_h,x
        sta tmp1
        lda #0
        sec
        sbc tmp0
        sta vy
        lda #0
        sbc tmp1
        sta vy+1
        lda #1
        sta p_jumphold
        lda #ANIM_JUMP
        jsr player_anim_set
        lda #SFX_JUMP
        jmp sfx_play
@swim:
        lda #0
        sta p_jumpbuf
        lda #<$FE80
        sta vy
        lda #>$FE80
        sta vy+1
        lda #SFX_JUMP
        jmp sfx_play
@cut:
        lda p_jumpbuf
        beq :+
        dec p_jumpbuf
:       lda p_jumphold
        beq @done
        lda pad1
        and #BTN_A
        bne @done
        lda #0
        sta p_jumphold
        lda vy+1
        bpl @done
        ; clip a released jump short
        lda vy+1
        cmp #$FF
        beq @done
        lda #<(65536 - JUMP_CUT)
        sta vy
        lda #>(65536 - JUMP_CUT)
        sta vy+1
@done:  rts
.endproc

; ---------------------------------------------------------------------------
.proc attack_input
        lda pad1_new
        and #BTN_B
        beq @done
        lda pad1
        and #BTN_DOWN
        bne @stomp
        lda pad1
        and #BTN_UP
        bne @grab
        ; ---- kick ------------------------------------------------------
        lda #PSTATE_KICK
        sta p_state
        lda #18
        sta p_timer
        lda #0
        sta p_kickhit
        lda #ANIM_KICK
        jsr player_anim_set
        lda #SFX_KICK
        jmp sfx_play
@stomp:
        lda p_ground
        beq @air
        lda #PSTATE_STOMP
        sta p_state
        lda #20
        sta p_timer
        lda #0
        sta p_kickhit
        lda #ANIM_STOMP
        jsr player_anim_set
        lda #SFX_STOMP
        jmp sfx_play
@air:
        lda #PSTATE_AIRSTOMP
        sta p_state
        lda #0
        sta vx
        sta vx+1
        sta p_kickhit
        lda #ANIM_STOMP
        jsr player_anim_set
        lda #SFX_STOMP
        jmp sfx_play
@grab:
        lda #PSTATE_GRAB
        sta p_state
        lda #16
        sta p_timer
        lda #ANIM_GRAB
        jsr player_anim_set
        lda #SFX_GRAB
        jmp sfx_play
@done:  rts
.endproc

; ---------------------------------------------------------------------------
; stomp_land -- an aerial stomp reaching the ground
; ---------------------------------------------------------------------------
.proc stomp_land
        lda #PSTATE_LAND
        sta p_state
        lda #10
        sta p_timer
        lda #ANIM_SLAM
        jsr player_anim_set
        lda #10
        ldx #4
        jsr shake_start
        lda #SFX_MEGASTOMP
        jsr sfx_play
        lda #2
        sta p_bounce
        jsr break_below
        jmp friction_only
.endproc

; ---------------------------------------------------------------------------
; break_below -- a heavy stomp destroys breakable floor tiles
; ---------------------------------------------------------------------------
.proc break_below
        ldx #0
        lda #0
        jsr probe_flags
        cmp #COL_BREAK
        bne @done
        ; flags_at_xy left the column/row in tmp0..tmp2
        jsr break_tile
        lda #SFX_BREAK
        jsr sfx_play
@done:  rts
.endproc

; ---------------------------------------------------------------------------
.proc apply_physics
        jsr water_check
        jsr move_x
        jsr move_y
        rts
.endproc

; ---------------------------------------------------------------------------
.proc water_check
        ldx #(256 - 8)
        lda #0
        jsr probe_flags
        cmp #COL_WATER
        beq @wet
        lda #0
        sta p_inwater
        rts
@wet:   lda #1
        sta p_inwater
        rts
.endproc

; ---------------------------------------------------------------------------
.proc move_x
        lda vx
        ora vx+1
        bne :+
        rts
:       lda px_sub
        clc
        adc vx
        sta px_sub
        lda px
        adc vx+1
        sta tmp6
        lda px+1
        adc #0
        sta tmp7
        lda vx+1
        bpl @right
        ; ---- moving left --------------------------------------------
        lda tmp6
        sta px
        lda tmp7
        sta px+1
        lda #(256 - PBOX_HALF)
        ldx #(256 - 1)
        jsr probe_flags
        jsr is_solid_class
        bcs @hitl
        lda #(256 - PBOX_HALF)
        ldx #(256 - 12)
        jsr probe_flags
        jsr is_solid_class
        bcs @hitl
        lda #(256 - PBOX_HALF)
        ldx #(256 - PBOX_TOP)
        jsr probe_flags
        jsr is_solid_class
        bcc @okl
@hitl:
        lda px
        and #$F0
        clc
        adc #PBOX_HALF
        sta px
        lda #0
        sta px_sub
        sta vx
        sta vx+1
@okl:   rts
@right:
        lda tmp6
        sta px
        lda tmp7
        sta px+1
        lda #(PBOX_HALF - 1)
        ldx #(256 - 1)
        jsr probe_flags
        jsr is_solid_class
        bcs @hitr
        lda #(PBOX_HALF - 1)
        ldx #(256 - 12)
        jsr probe_flags
        jsr is_solid_class
        bcs @hitr
        lda #(PBOX_HALF - 1)
        ldx #(256 - PBOX_TOP)
        jsr probe_flags
        jsr is_solid_class
        bcc @okr
@hitr:
        lda px
        clc
        adc #(PBOX_HALF - 1)
        and #$F0
        sec
        sbc #PBOX_HALF
        sta px
        lda #0
        sta px_sub
        sta vx
        sta vx+1
@okr:   rts
.endproc

; ---------------------------------------------------------------------------
.proc move_y
        ; gravity
        lda p_inwater
        bne @wgrav
        lda #GRAVITY
        sta tmp0
        lda #<MAXFALL
        sta tmp2
        lda #>MAXFALL
        sta tmp3
        jmp @add
@wgrav:
        lda #GRAV_WATER
        sta tmp0
        lda #<MAXFALL_W
        sta tmp2
        lda #>MAXFALL_W
        sta tmp3
@add:
        lda vy
        clc
        adc tmp0
        sta vy
        lda vy+1
        adc #0
        sta vy+1
        bmi @move
        cmp tmp3
        bcc @move
        bne @cap
        lda vy
        cmp tmp2
        bcc @move
@cap:   lda tmp2
        sta vy
        lda tmp3
        sta vy+1
@move:
        lda py_sub
        clc
        adc vy
        sta py_sub
        lda py
        adc vy+1
        sta py
        lda vy+1
        bmi @up

        ; ---- falling --------------------------------------------------
        jsr p_solid_below
        bcs @landed
        lda p_ground_type
        cmp #COL_PLATFORM
        bne @nofloor
        lda py
        and #$0F
        cmp #7
        bcs @nofloor
@landed:
        lda py
        and #$F0
        sta py
        lda #0
        sta py_sub
        sta vy
        sta vy+1
        lda p_wasground
        bne @nofloor
        jsr on_land
@nofloor:
        lda py
        cmp #(LEVEL_HEIGHT_PX + 24)
        bcc :+
        jmp player_kill
:       rts
@up:
        lda #(256 - PBOX_HALF)
        ldx #(256 - PBOX_TOP)
        jsr probe_flags
        jsr is_solid_class
        bcs @bonk
        lda #(PBOX_HALF - 1)
        ldx #(256 - PBOX_TOP)
        jsr probe_flags
        jsr is_solid_class
        bcc @okup
@bonk:
        lda py
        sec
        sbc #PBOX_TOP
        and #$F0
        clc
        adc #(16 + PBOX_TOP)
        sta py
        lda #0
        sta py_sub
        sta vy
        sta vy+1
@okup:  rts
.endproc

; ---------------------------------------------------------------------------
.proc on_land
        lda p_state
        cmp #PSTATE_AIRSTOMP
        beq :+
        lda #PSTATE_LAND
        sta p_state
        lda #7
        sta p_timer
        lda #ANIM_LAND
        jsr player_anim_set
        lda #SFX_LAND
        jsr sfx_play
        lda #4
        ldx #1
        jsr shake_start
:       rts
.endproc

; ---------------------------------------------------------------------------
.proc state_hurt
        dec p_timer
        bne :+
        lda #PSTATE_NORMAL
        sta p_state
:       jsr read_ground
        jsr friction_only
        jsr move_x
        jsr move_y
        jmp anim_tick
.endproc

.proc state_dead
        lda p_timer
        beq :+
        dec p_timer
:       lda py
        cmp #(LEVEL_HEIGHT_PX + 40)
        bcs :+
        lda py_sub
        clc
        adc vy
        sta py_sub
        lda py
        adc vy+1
        sta py
        lda vy
        clc
        adc #GRAVITY
        sta vy
        lda vy+1
        adc #0
        sta vy+1
:       jmp anim_tick
.endproc

; ---------------------------------------------------------------------------
; player_hurt -- A = damage, X = knockback direction (0 right, 1 left)
; ---------------------------------------------------------------------------
.proc player_hurt
        ldy p_inv
        bne @no
        sta tmp0
        stx tmp1
        lda p_hp
        sec
        sbc tmp0
        bcc @dead
        beq @dead
        sta p_hp
        lda #PSTATE_HURT
        sta p_state
        lda #24
        sta p_timer
        lda #60
        sta p_inv
        lda #ANIM_HURT
        jsr player_anim_set
        lda #<$FE00
        sta vy
        lda #>$FE00
        sta vy+1
        lda tmp1
        bne @kleft
        lda #<$FF40
        sta vx
        lda #>$FF40
        sta vx+1
        jmp @snd
@kleft: lda #<$00C0
        sta vx
        lda #>$00C0
        sta vx+1
@snd:   lda #1
        sta hud_dirty
        lda #SFX_HURT
        jmp sfx_play
@dead:
        lda #0
        sta p_hp
        jmp player_kill
@no:    rts
.endproc

; ---------------------------------------------------------------------------
.proc player_kill
        lda p_state
        cmp #PSTATE_DEAD
        beq @done
        lda #PSTATE_DEAD
        sta p_state
        lda #0
        sta p_hp
        sta vx
        sta vx+1
        sta cam_lock
        lda #<$FB80
        sta vy
        lda #>$FB80
        sta vy+1
        lda #120
        sta p_timer
        lda #ANIM_DIE
        jsr player_anim_set
        lda #1
        sta hud_dirty
        lda #SFX_DIE
        jmp sfx_play
@done:  rts
.endproc

; ---------------------------------------------------------------------------
.proc add_health
        clc
        adc p_hp
        cmp p_hp_max
        bcc :+
        lda p_hp_max
:       sta p_hp
        lda #1
        sta hud_dirty
        rts
.endproc

; ---------------------------------------------------------------------------
; give_shoe -- A = footwear index
; ---------------------------------------------------------------------------
.proc give_shoe
        sta p_shoe
        tax
        lda bitmask,x
        ora shoe_flags
        sta shoe_flags
        lda #90
        sta p_shoetimer
        lda #1
        sta hud_dirty
        lda #SFX_SHOE
        jmp sfx_play
bitmask: .byte 1,2,4,8,16,32,64,128
.endproc

; ---------------------------------------------------------------------------
; animation
; ---------------------------------------------------------------------------
.proc player_anim_set
        cmp p_anim
        beq @same
        sta p_anim
        lda #0
        sta p_frame
        sta p_atimer
        jsr anim_load
@same:  rts
.endproc

.proc anim_load
        ldx p_anim
        lda panim_tbl_lo,x
        sta ptr1
        lda panim_tbl_hi,x
        sta ptr1+1
        ldy p_frame
        lda (ptr1),y
        cmp #$FF
        bne @ok
        iny
        lda (ptr1),y
        bmi @hold
        sta p_frame
        tay
        lda (ptr1),y
        sta p_curframe
        iny
        lda (ptr1),y
        sta p_atimer
        rts
@hold:
        ; hold on the final frame
        lda p_frame
        sec
        sbc #2
        sta p_frame
        tay
        lda (ptr1),y
        sta p_curframe
        lda #60
        sta p_atimer
        rts
@ok:    sta p_curframe
        iny
        lda (ptr1),y
        sta p_atimer
        rts
.endproc

.proc anim_tick
        lda p_atimer
        beq @next
        dec p_atimer
        bne @done
@next:
        lda p_frame
        clc
        adc #2
        sta p_frame
        jsr anim_load
@done:  rts
.endproc

; ---------------------------------------------------------------------------
; anim_select -- pick an animation from the current state
; ---------------------------------------------------------------------------
.proc anim_select
        lda p_state
        cmp #PSTATE_NORMAL
        bne @done
        lda p_inwater
        beq :+
        lda #ANIM_SWIM
        jmp player_anim_set
:       lda p_ground
        beq @air
        lda vx
        ora vx+1
        beq @idle
        lda p_walkdist
        cmp #40
        bcs @run
        lda #ANIM_WALK
        jmp player_anim_set
@run:   lda #ANIM_RUN
        jmp player_anim_set
@idle:  lda #ANIM_IDLE
        jmp player_anim_set
@air:
        lda vy+1
        bmi @up
        lda #ANIM_FALL
        jmp player_anim_set
@up:    lda #ANIM_JUMP
        jmp player_anim_set
@done:  rts
.endproc

; ---------------------------------------------------------------------------
; player_draw
; ---------------------------------------------------------------------------
.proc player_draw
        lda p_inv
        beq @show
        and #2
        beq @show
        rts
@show:
        ; frame = pf_remap[shoe * PF_COUNT + logical]
        ldx p_shoe
        lda shoe_off_lo,x
        clc
        adc p_curframe
        sta ptr0
        lda shoe_off_hi,x
        adc #0
        sta ptr0+1
        lda #<pf_remap
        clc
        adc ptr0
        sta ptr0
        lda #>pf_remap
        adc ptr0+1
        sta ptr0+1
        ldy #0
        lda (ptr0),y
        tax
        lda pf_bank,x
        sta chr_bank_lo
        lda #1
        sta chr_dirty
        lda pf_ms_lo,x
        sta ptr1
        lda pf_ms_hi,x
        sta ptr1+1

        lda px
        sta ptr2
        lda px+1
        sta ptr2+1
        lda py
        sta tmp4
        jsr spr_set_world
        bcs @off
        lda #0
        sta spr_attr
        lda p_face
        beq :+
        lda #$40
:       sta spr_flip
        jmp draw_metasprite
@off:   rts
.endproc

shoe_off_lo:
        .lobytes 0*PF_COUNT, 1*PF_COUNT, 2*PF_COUNT, 3*PF_COUNT
        .lobytes 4*PF_COUNT, 5*PF_COUNT, 6*PF_COUNT, 7*PF_COUNT
shoe_off_hi:
        .hibytes 0*PF_COUNT, 1*PF_COUNT, 2*PF_COUNT, 3*PF_COUNT
        .hibytes 4*PF_COUNT, 5*PF_COUNT, 6*PF_COUNT, 7*PF_COUNT

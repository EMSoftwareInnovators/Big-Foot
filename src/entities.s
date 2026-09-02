;
; Entity pool: enemies, kickable objects, projectiles, pickups.
;
; A fixed pool of 12 slots held as a structure of arrays -- with X as the slot
; index every field is one indexed load, which is what a 6502 is good at.
; Positions are 16.8 fixed point like the player's.
;
.include "constants.inc"
.include "ram.inc"
.include "entities.inc"
.include "bg.inc"

.import flags_at_xy, mt_at, mt_flags_at, rand, sfx_play
.import draw_metasprite, spr_set_world, player_hurt, add_health, give_shoe
.import ed_behav, ed_hp, ed_w, ed_h, ed_dmg, ed_flags, ed_frames, ed_pal
.import ed_spd_lo, ed_spd_hi, ed_shot
.import shake_start

.export entities_init, entities_update, entities_draw, spawn_check
.export entity_alloc, entity_free, spawn_entity, entity_hurt_area
.export particles_update, particles_draw, spawn_particle
.export ent_probe, ent_solid_below, kill_entity

GRAV_E   = $30
MAXFALL_E = $0400

.segment "CODE2"

; ---------------------------------------------------------------------------
.proc entities_init
        ldx #MAX_ENTITIES-1
        lda #ES_FREE
:       sta e_state,x
        dex
        bpl :-
        ldx #MAX_PARTICLES-1
        lda #0
:       sta pa_type,x
        dex
        bpl :-
        ldx #11
        lda #0
:       sta spawn_used,x
        dex
        bpl :-
        lda #0
        sta spawn_cur
        sta oam_order
        rts
.endproc

; ---------------------------------------------------------------------------
; entity_alloc -- returns a free slot in X, carry set if the pool is full
; ---------------------------------------------------------------------------
.proc entity_alloc
        ldx #0
:       lda e_state,x
        beq @found
        inx
        cpx #MAX_ENTITIES
        bcc :-
        sec
        rts
@found: clc
        rts
.endproc

.proc entity_free
        lda #ES_FREE
        sta e_state,x
        rts
.endproc

; ---------------------------------------------------------------------------
; spawn_entity -- A = type, ptr2 = world X, tmp7 = world Y (bottom edge)
;                 returns the slot in X, carry set on failure
; ---------------------------------------------------------------------------
.proc spawn_entity
        sta ent_tmp
        jsr entity_alloc
        bcc :+
        rts
:       lda ent_tmp
        sta e_type,x
        tay
        lda #ES_ACTIVE
        sta e_state,x
        lda ptr2
        sta e_xl,x
        lda ptr2+1
        sta e_xh,x
        lda tmp7
        sta e_yl,x
        lda #0
        sta e_yh,x
        sta e_xs,x
        sta e_ys,x
        sta e_vxl,x
        sta e_vxh,x
        sta e_vyl,x
        sta e_vyh,x
        sta e_anim,x
        sta e_frm,x
        sta e_hurt,x
        sta e_sub,x
        lda ed_hp,y
        sta e_hp,x
        lda ed_flags,y
        sta e_flags,x
        lda #$FF
        sta e_slot,x
        lda #30
        sta e_tmr,x
        ; face the player
        lda e_xh,x
        cmp px+1
        bcc @right
        bne @left
        lda e_xl,x
        cmp px
        bcc @right
@left:  lda e_flags,x
        ora #EF_FACELEFT
        sta e_flags,x
@right: clc
        rts
.endproc

; ---------------------------------------------------------------------------
; spawn_check -- bring entities in as their column enters the right edge and
; let them back out (and back in) when the player retreats.
; ---------------------------------------------------------------------------
.proc spawn_check
        ; camera column
        lda cam_x
        sta tmp0
        lda cam_x+1
        sta tmp1
        lsr tmp1
        ror tmp0
        lsr tmp1
        ror tmp0
        lsr tmp1
        ror tmp0
        lsr tmp1
        ror tmp0

        ; rewind when the camera has moved back past earlier entries
@rewind:
        lda spawn_cur
        beq @forward
        sec
        sbc #1
        jsr entry_ptr
        ldy #0
        lda (ptr3),y
        sta tmp2
        iny
        lda (ptr3),y
        sta tmp3
        lda tmp0
        cmp tmp2
        lda tmp1
        sbc tmp3
        bcs @forward
        dec spawn_cur
        lda spawn_cur
        jsr clear_used
        jmp @rewind

@forward:
        lda spawn_cur
        cmp #96
        bcs @done
        jsr entry_ptr
        ldy #1
        lda (ptr3),y
        cmp #$FF
        beq @done
        sta tmp3
        dey
        lda (ptr3),y
        sta tmp2
        ; spawn when column <= cam_col + 17
        lda tmp0
        clc
        adc #17
        sta tmp4
        lda tmp1
        adc #0
        sta tmp5
        lda tmp2
        cmp tmp4
        lda tmp3
        sbc tmp5
        bcs @done

        lda spawn_cur
        jsr test_used
        bcs @next
        ; world position from the map cell
        lda tmp2
        sta ptr2
        lda tmp3
        sta ptr2+1
        ldx #4
:       asl ptr2
        rol ptr2+1
        dex
        bne :-
        lda ptr2
        clc
        adc #8
        sta ptr2
        lda ptr2+1
        adc #0
        sta ptr2+1
        ldy #2
        lda (ptr3),y
        asl a
        asl a
        asl a
        asl a
        clc
        adc #16
        sta tmp7
        ldy #3
        lda (ptr3),y
        jsr spawn_entity
        bcs @next
        lda spawn_cur
        sta e_slot,x
        lda spawn_cur
        jsr set_used
@next:
        inc spawn_cur
        jmp @forward
@done:  rts
.endproc

; ---------------------------------------------------------------------------
; entry_ptr -- A = spawn index, sets ptr3 to that four-byte record
; ---------------------------------------------------------------------------
.proc entry_ptr
        asl a
        asl a
        clc
        adc spawn_ptr
        sta ptr3
        lda #0
        adc spawn_ptr+1
        sta ptr3+1
        rts
.endproc

; ---------------------------------------------------------------------------
; used-bit helpers: A = spawn index
; ---------------------------------------------------------------------------
.proc used_addr
        pha
        lsr a
        lsr a
        lsr a
        tay
        pla
        and #7
        tax
        lda bit_tbl,x
        rts
bit_tbl: .byte 1,2,4,8,16,32,64,128
.endproc

.proc set_used
        jsr used_addr
        ora spawn_used,y
        sta spawn_used,y
        rts
.endproc

.proc clear_used
        jsr used_addr
        eor #$FF
        and spawn_used,y
        sta spawn_used,y
        rts
.endproc

.proc test_used
        jsr used_addr
        and spawn_used,y
        beq @no
        sec
        rts
@no:    clc
        rts
.endproc

; ---------------------------------------------------------------------------
; ent_probe -- collision class at (entity X + tmp8, entity Y + tmp9)
; ---------------------------------------------------------------------------
.proc ent_probe
        lda tmp8
        bmi @neg
        clc
        adc e_xl,x
        sta ptr0
        lda e_xh,x
        adc #0
        sta ptr0+1
        jmp @y
@neg:   clc
        adc e_xl,x
        sta ptr0
        lda e_xh,x
        adc #$FF
        sta ptr0+1
@y:     lda tmp9
        clc
        adc e_yl,x
        sta tmp4
        jmp flags_at_xy
.endproc

.proc solid_class
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
; ent_solid_below -- carry set when the entity is standing on something
; ---------------------------------------------------------------------------
.proc ent_solid_below
        lda #0
        sta tmp8
        sta tmp9
        jsr ent_probe
        jsr solid_class
        bcs @yes
        cmp #COL_PLATFORM
        bne @no
        lda e_vyh,x
        bmi @no
        lda e_yl,x
        and #$0F
        cmp #6
        bcs @no
        sec
        rts
@yes:   sec
        rts
@no:    clc
        rts
.endproc

; ---------------------------------------------------------------------------
; ent_gravity -- apply gravity and resolve vertical tile collision
; ---------------------------------------------------------------------------
.proc ent_gravity
        lda e_vyl,x
        clc
        adc #GRAV_E
        sta e_vyl,x
        lda e_vyh,x
        adc #0
        sta e_vyh,x
        cmp #>MAXFALL_E
        bcc :+
        lda #<MAXFALL_E
        sta e_vyl,x
        lda #>MAXFALL_E
        sta e_vyh,x
:
        lda e_ys,x
        clc
        adc e_vyl,x
        sta e_ys,x
        lda e_yl,x
        adc e_vyh,x
        sta e_yl,x
        lda e_vyh,x
        bmi @up
        jsr ent_solid_below
        bcc @air
        lda e_yl,x
        and #$F0
        sta e_yl,x
        lda #0
        sta e_ys,x
        sta e_vyl,x
        sta e_vyh,x
        lda e_flags,x
        ora #EF_GROUNDED
        sta e_flags,x
        rts
@air:
        lda e_flags,x
        and #<~EF_GROUNDED
        sta e_flags,x
        lda e_yl,x
        cmp #(LEVEL_HEIGHT_PX + 32)
        bcc :+
        jsr entity_free
:       rts
@up:
        lda e_flags,x
        and #<~EF_GROUNDED
        sta e_flags,x
        rts
.endproc

; ---------------------------------------------------------------------------
; ent_move_x -- advance by the horizontal velocity, stopping at walls.
; Carry set if a wall was hit.
; ---------------------------------------------------------------------------
.proc ent_move_x
        lda e_xs,x
        clc
        adc e_vxl,x
        sta e_xs,x
        lda e_xl,x
        adc e_vxh,x
        sta e_xl,x
        lda e_vxh,x
        bmi @neg
        lda e_xh,x
        adc #0
        sta e_xh,x
        ldy e_type,x
        lda ed_w,y
        lsr a
        sta tmp8
        jmp @test
@neg:   lda e_xh,x
        adc #$FF
        sta e_xh,x
        ldy e_type,x
        lda ed_w,y
        lsr a
        eor #$FF
        clc
        adc #1
        sta tmp8
@test:
        ldy e_type,x
        lda ed_h,y
        lsr a
        eor #$FF
        clc
        adc #1
        sta tmp9                        ; probe at mid height
        jsr ent_probe
        jsr solid_class
        bcs @hit
        clc
        rts
@hit:
        ; back off to the tile edge
        lda e_vxh,x
        bmi @hleft
        lda e_xl,x
        clc
        adc tmp8
        and #$F0
        sec
        sbc tmp8
        sta e_xl,x
        jmp @stop
@hleft:
        lda e_xl,x
        and #$F0
        sec
        sbc tmp8
        sta e_xl,x
@stop:
        lda #0
        sta e_xs,x
        sec
        rts
.endproc

; ---------------------------------------------------------------------------
; ent_face_player / ent_set_speed
; ---------------------------------------------------------------------------
.proc ent_face_player
        lda e_xh,x
        cmp px+1
        bcc @right
        bne @left
        lda e_xl,x
        cmp px
        bcc @right
@left:  lda e_flags,x
        ora #EF_FACELEFT
        sta e_flags,x
        rts
@right: lda e_flags,x
        and #<~EF_FACELEFT
        sta e_flags,x
        rts
.endproc

; ent_set_speed -- vx = +/- ed_spd according to the facing flag
.proc ent_set_speed
        ldy e_type,x
        lda e_flags,x
        and #EF_FACELEFT
        bne @left
        lda ed_spd_lo,y
        sta e_vxl,x
        lda ed_spd_hi,y
        sta e_vxh,x
        rts
@left:  lda #0
        sec
        sbc ed_spd_lo,y
        sta e_vxl,x
        lda #0
        sbc ed_spd_hi,y
        sta e_vxh,x
        rts
.endproc

.proc ent_turn
        lda e_flags,x
        eor #EF_FACELEFT
        sta e_flags,x
        rts
.endproc

; ---------------------------------------------------------------------------
; entities_update
; ---------------------------------------------------------------------------
.proc entities_update
        ldx #0
@loop:  stx cur_ent
        lda e_state,x
        beq @next
        cmp #ES_DYING
        bne @alive
        dec e_tmr,x
        bne @next
        jsr entity_free
        jmp @next
@alive:
        lda e_hurt,x
        beq :+
        dec e_hurt,x
:       jsr despawn_check
        lda e_state,x
        beq @next
        jsr on_camera
        bcc @next                       ; off screen: freeze until it scrolls in
        ldy e_type,x
        lda ed_behav,y
        asl a
        tay
        lda behav_lo,y
        sta ptr1
        lda behav_hi,y
        sta ptr1+1
        jsr call_behav
        ldx cur_ent
        lda e_state,x
        beq @next
        jsr touch_player
@next:
        ldx cur_ent
        inx
        cpx #MAX_ENTITIES
        bcs :+
        jmp @loop
:       rts
.endproc

.proc call_behav
        jmp (ptr1)
.endproc

; ---------------------------------------------------------------------------
; on_camera -- carry set when the entity is close enough to matter.  Entities
; outside this band keep their state but stop simulating, which is both
; cheaper and closer to how the era's games behaved.
; ---------------------------------------------------------------------------
.proc on_camera
        lda e_xh,x
        sec
        sbc cam_x+1
        beq @yes
        cmp #1
        beq @yes
        cmp #$FF
        beq @yes
        clc
        rts
@yes:   sec
        rts
.endproc

; ---------------------------------------------------------------------------
; despawn_check -- release entities that have fallen far behind the camera
; ---------------------------------------------------------------------------
.proc despawn_check
        lda e_xl,x
        sec
        sbc cam_x
        sta tmp0
        lda e_xh,x
        sbc cam_x+1
        sta tmp1
        bmi @behind
        lda tmp1
        beq @ok
        cmp #2                          ; more than 512 px ahead
        bcc @ok
        jmp @gone
@behind:
        lda tmp1
        cmp #$FF
        bne @gone
        lda tmp0
        cmp #$60                        ; up to 160 px behind
        bcs @ok
@gone:
        lda e_slot,x
        cmp #$FF
        beq :+
        jsr clear_used
:       jsr entity_free
@ok:    rts
.endproc

; ---------------------------------------------------------------------------
; touch_player -- contact damage and pickups
; ---------------------------------------------------------------------------
.proc touch_player
        lda p_state
        cmp #PSTATE_DEAD
        beq @no
        jsr overlap_player
        bcc @no
        ldy e_type,x
        lda e_flags,x
        and #EF_HARMLESS
        bne @friendly
        lda ed_dmg,y
        beq @no
        sta tmp0
        ; knock the player away from the entity
        lda px+1
        cmp e_xh,x
        bcc @kleft
        bne @kright
        lda px
        cmp e_xl,x
        bcc @kleft
@kright: ldx #0
        beq @hurt
@kleft: ldx #1
@hurt:  lda tmp0
        jsr player_hurt
        ldx cur_ent
        ldy e_type,x
        lda e_flags,x
        and #EF_PROJECTILE
        beq @no
        jsr entity_free
@no:    rts
@friendly:
        lda e_type,x
        cmp #ET_HEALTH
        beq @heal
        cmp #ET_SHOEBOX
        beq @shoe
        cmp #ET_LIFE
        beq @life
        rts
@heal:  lda #4
        jsr add_health
        lda #SFX_PICKUP
        jsr sfx_play
        ldx cur_ent
        jmp entity_free
@life:  inc lives
        lda #1
        sta hud_dirty
        lda #SFX_PICKUP
        jsr sfx_play
        ldx cur_ent
        jmp entity_free
@shoe:  lda stage_shoe
        jsr give_shoe
        ldx cur_ent
        jmp entity_free
.endproc

; ---------------------------------------------------------------------------
; overlap_player -- carry set when entity X overlaps the player's box
; ---------------------------------------------------------------------------
.proc overlap_player
        ldy e_type,x
        ; horizontal: |ex - px| < (ew + pw) / 2
        lda e_xl,x
        sec
        sbc px
        sta tmp0
        lda e_xh,x
        sbc px+1
        sta tmp1
        bpl :+
        ; negate
        lda #0
        sec
        sbc tmp0
        sta tmp0
        lda #0
        sbc tmp1
        sta tmp1
:       lda tmp1
        bne @no
        lda ed_w,y
        lsr a
        clc
        adc #(PBOX_W / 2)
        cmp tmp0
        bcc @no
        ; vertical: entity spans (ey - eh) .. ey, player (py - 22) .. py
        lda e_yl,x
        sec
        sbc ed_h,y
        sta tmp2                        ; entity top
        lda py
        sec
        sbc #PBOX_H
        sta tmp3                        ; player top
        lda e_yl,x
        cmp tmp3
        bcc @no                         ; entity bottom above player top
        lda py
        cmp tmp2
        bcc @no                         ; player bottom above entity top
        sec
        rts
@no:    clc
        rts
.endproc

; ---------------------------------------------------------------------------
; behaviours
; ---------------------------------------------------------------------------
behav_lo:
        .lobytes b_none, b_walker, b_shooter, b_flyer, b_hopper, b_ambush
        .lobytes b_crusher, b_sound, b_object, b_shot, b_pickup, b_static
behav_hi:
        .hibytes b_none, b_walker, b_shooter, b_flyer, b_hopper, b_ambush
        .hibytes b_crusher, b_sound, b_object, b_shot, b_pickup, b_static

.proc b_none
        rts
.endproc

.proc b_static
        jsr ent_gravity
        jmp anim_two
.endproc

; --- walker ---------------------------------------------------------------
.proc b_walker
        lda e_state,x
        cmp #ES_STUNNED
        bne :+
        dec e_tmr,x
        bne @grav
        lda #ES_ACTIVE
        sta e_state,x
:
        jsr ent_set_speed
        jsr ent_move_x
        bcc :+
        jsr ent_turn
:       jsr ledge_check
@grav:  jsr ent_gravity
        jmp anim_walk
.endproc

; turn around at the edge of a platform so walkers never stroll into pits
.proc ledge_check
        lda e_flags,x
        and #EF_GROUNDED
        beq @done
        ldy e_type,x
        lda e_flags,x
        and #EF_FACELEFT
        bne @left
        lda ed_w,y
        lsr a
        clc
        adc #2
        sta tmp8
        jmp @probe
@left:  lda ed_w,y
        lsr a
        clc
        adc #2
        eor #$FF
        clc
        adc #1
        sta tmp8
@probe: lda #6
        sta tmp9
        jsr ent_probe
        jsr solid_class
        bcs @done
        cmp #COL_PLATFORM
        beq @done
        jsr ent_turn
@done:  rts
.endproc

; --- shooter --------------------------------------------------------------
.proc b_shooter
        jsr ent_gravity
        jsr ent_face_player
        dec e_tmr,x
        bne @anim
        lda #90
        sta e_tmr,x
        jsr near_player
        bcc @anim
        jsr fire_shot
        lda #20
        sta e_sub,x
@anim:
        lda e_sub,x
        beq :+
        dec e_sub,x
        lda #1
        sta e_frm,x
        rts
:       lda #0
        sta e_frm,x
        rts
.endproc

; near_player -- carry set when the player is within about a screen
.proc near_player
        lda e_xl,x
        sec
        sbc px
        sta tmp0
        lda e_xh,x
        sbc px+1
        bpl :+
        lda #0
        sec
        sbc tmp0
        sta tmp0
        lda #0
:       bne @no
        lda tmp0
        cmp #144
        bcs @no
        sec
        rts
@no:    clc
        rts
.endproc

.proc fire_shot
        ldy e_type,x
        lda ed_shot,y
        beq @done
        sta ent_tmp
        lda e_xl,x
        sta ptr2
        lda e_xh,x
        sta ptr2+1
        lda e_yl,x
        sec
        sbc #12
        sta tmp7
        lda e_flags,x
        and #EF_FACELEFT
        sta ent_tmp2
        stx cur_ent
        lda ent_tmp
        jsr spawn_entity
        bcs @done
        ldy e_type,x
        lda ent_tmp2
        beq @right
        lda e_flags,x
        ora #EF_FACELEFT
        sta e_flags,x
        lda #0
        sec
        sbc ed_spd_lo,y
        sta e_vxl,x
        lda #0
        sbc ed_spd_hi,y
        sta e_vxh,x
        jmp @snd
@right: lda ed_spd_lo,y
        sta e_vxl,x
        lda ed_spd_hi,y
        sta e_vxh,x
@snd:   ldx cur_ent
        lda #SFX_ARROW
        jsr sfx_play
        ldx cur_ent
@done:  rts
.endproc

; --- flyer ----------------------------------------------------------------
.proc b_flyer
        jsr ent_face_player
        jsr ent_set_speed
        jsr ent_move_x
        ; bob toward the player's height
        lda e_yl,x
        cmp py
        bcs @up
        inc e_sub,x
        lda e_sub,x
        and #1
        bne :+
        inc e_yl,x
:       jmp anim_two
@up:    dec e_sub,x
        lda e_sub,x
        and #1
        bne :+
        dec e_yl,x
:       jmp anim_two
.endproc

; --- hopper ---------------------------------------------------------------
.proc b_hopper
        jsr ent_gravity
        lda e_flags,x
        and #EF_GROUNDED
        beq @move
        dec e_tmr,x
        bne @move
        jsr rand
        ldx cur_ent
        and #$1F
        clc
        adc #24
        sta e_tmr,x
        lda #<$FD00
        sta e_vyl,x
        lda #>$FD00
        sta e_vyh,x
        jsr rand
        ldx cur_ent
        and #$80
        beq :+
        lda e_flags,x
        ora #EF_FACELEFT
        sta e_flags,x
        jmp @move
:       lda e_flags,x
        and #<~EF_FACELEFT
        sta e_flags,x
@move:
        jsr ent_set_speed
        jsr ent_move_x
        bcc :+
        jsr ent_turn
:       jmp anim_two
.endproc

; --- ambush ---------------------------------------------------------------
.proc b_ambush
        lda e_sub,x
        bne @up
        jsr near_close
        bcc @hidden
        lda #40
        sta e_sub,x
        lda #SFX_HIT
        jsr sfx_play
        ldx cur_ent
@hidden:
        lda #0
        sta e_frm,x
        rts
@up:
        dec e_sub,x
        lda #1
        sta e_frm,x
        jsr ent_gravity
        rts
.endproc

.proc near_close
        lda e_xl,x
        sec
        sbc px
        sta tmp0
        lda e_xh,x
        sbc px+1
        bpl :+
        lda #0
        sec
        sbc tmp0
        sta tmp0
        lda #0
:       bne @no
        lda tmp0
        cmp #40
        bcs @no
        sec
        rts
@no:    clc
        rts
.endproc

; --- crusher --------------------------------------------------------------
.proc b_crusher
        dec e_tmr,x
        bne @done
        lda #48
        sta e_tmr,x
        lda e_frm,x
        eor #1
        sta e_frm,x
        bne @done
        lda #6
        ldx #2
        jsr shake_start
        ldx cur_ent
        lda #SFX_STOMP
        jsr sfx_play
        ldx cur_ent
@done:  rts
.endproc

; --- sound ----------------------------------------------------------------
.proc b_sound
        jsr ent_gravity
        jsr ent_face_player
        dec e_tmr,x
        bne @anim
        lda #120
        sta e_tmr,x
        jsr near_player
        bcc @anim
        jsr fire_shot
        ldx cur_ent
        lda #30
        sta e_sub,x
@anim:
        lda e_sub,x
        beq :+
        dec e_sub,x
        lda #1
        sta e_frm,x
        rts
:       lda #0
        sta e_frm,x
        rts
.endproc

; --- object ---------------------------------------------------------------
; Kickable props: they roll, bounce and hurt whatever they hit.  Kicking a
; barrel into a shield knight is the intended answer to a shield knight.
.proc b_object
        jsr ent_gravity
        lda e_vxh,x
        ora e_vxl,x
        beq @rest
        jsr ent_move_x
        bcc :+
        ; bounce off the wall at half speed
        jsr neg_vx
        jsr halve_vx
        lda #SFX_HIT
        jsr sfx_play
        ldx cur_ent
:       lda e_flags,x
        and #EF_GROUNDED
        beq @spin
        jsr friction_vx
@spin:
        jsr object_strike
        jmp anim_two
@rest:  rts
.endproc

.proc neg_vx
        lda #0
        sec
        sbc e_vxl,x
        sta e_vxl,x
        lda #0
        sbc e_vxh,x
        sta e_vxh,x
        rts
.endproc

.proc halve_vx
        lda e_vxh,x
        cmp #$80
        ror e_vxh,x
        ror e_vxl,x
        rts
.endproc

.proc friction_vx
        lda e_vxh,x
        bmi @neg
        lda e_vxl,x
        sec
        sbc #$10
        sta e_vxl,x
        lda e_vxh,x
        sbc #0
        sta e_vxh,x
        bpl @done
        jmp @zero
@neg:
        lda e_vxl,x
        clc
        adc #$10
        sta e_vxl,x
        lda e_vxh,x
        adc #0
        sta e_vxh,x
        bmi @done
@zero:  lda #0
        sta e_vxl,x
        sta e_vxh,x
@done:  rts
.endproc

; a moving object damages any enemy it touches
.proc object_strike
        lda e_vxh,x
        jsr abs_speed
        cmp #1
        bcc @done
        stx ent_tmp
        ldy #0
@loop:  cpy ent_tmp
        beq @next
        lda e_state,y
        beq @next
        cmp #ES_ACTIVE
        bne @next
        lda e_flags,y
        and #(EF_HARMLESS | EF_PROJECTILE)
        bne @next
        jsr boxes_overlap
        bcc @next
        ldx ent_tmp
        lda #3
        sta atk_dmg
        sty ent_tmp2
        tya
        tax
        lda #3
        jsr hurt_entity
        ldx ent_tmp
        jsr neg_vx
        jsr halve_vx
        lda #SFX_HIT
        jsr sfx_play
        ldx ent_tmp
        rts
@next:  iny
        cpy #MAX_ENTITIES
        bcc @loop
        ldx ent_tmp
@done:  rts
.endproc

.proc abs_speed
        cmp #$80
        bcc :+
        eor #$FF
        clc
        adc #1
:       rts
.endproc

; boxes_overlap -- entity ent_tmp against entity Y (rough, 16 px)
.proc boxes_overlap
        ldx ent_tmp
        lda e_xl,x
        sec
        sbc e_xl,y
        sta tmp0
        lda e_xh,x
        sbc e_xh,y
        bpl :+
        lda #0
        sec
        sbc tmp0
        sta tmp0
        lda #0
:       bne @no
        lda tmp0
        cmp #18
        bcs @no
        lda e_yl,x
        sec
        sbc e_yl,y
        bpl :+
        eor #$FF
        clc
        adc #1
:       cmp #22
        bcs @no
        sec
        rts
@no:    clc
        rts
.endproc

; --- shot -----------------------------------------------------------------
.proc b_shot
        jsr ent_move_x
        bcs @gone
        lda #0
        sta tmp8
        sta tmp9
        jsr ent_probe
        jsr solid_class
        bcs @gone
        jmp anim_two
@gone:
        jsr spark_here
        ldx cur_ent
        jmp entity_free
.endproc

; --- pickup ---------------------------------------------------------------
.proc b_pickup
        inc e_anim,x
        lda e_anim,x
        and #$0F
        bne @done
        lda e_anim,x
        and #$10
        beq :+
        inc e_yl,x
        rts
:       dec e_yl,x
@done:  rts
.endproc

; ---------------------------------------------------------------------------
; animation helpers
; ---------------------------------------------------------------------------
.proc anim_two
        inc e_anim,x
        lda e_anim,x
        lsr a
        lsr a
        lsr a
        and #1
        sta e_frm,x
        rts
.endproc

.proc anim_walk
        lda e_state,x
        cmp #ES_STUNNED
        beq @stun
        inc e_anim,x
        lda e_anim,x
        lsr a
        lsr a
        lsr a
        and #1
        clc
        adc #1
        sta e_frm,x
        rts
@stun:  lda #0
        sta e_frm,x
        rts
.endproc

; ---------------------------------------------------------------------------
; entity_hurt_area -- damage every entity inside the current attack box.
; atk_x1/atk_x2 (16-bit), atk_y1/atk_y2, atk_dmg, atk_kind
;   kind 0 = kick, 1 = stomp, 2 = shockwave
; ---------------------------------------------------------------------------
.proc entity_hurt_area
        ldx #0
@loop:  stx cur_ent
        lda e_state,x
        beq @next
        cmp #ES_ACTIVE
        beq :+
        cmp #ES_STUNNED
        bne @next
:       jsr in_attack_box
        bcc @next
        lda e_flags,x
        and #EF_PROJECTILE
        beq @solid
        ; kicking a projectile sends it back
        lda atk_kind
        bne @kill
        jsr reflect_shot
        jmp @next
@kill:  jsr entity_free
        jmp @next
@solid:
        lda e_flags,x
        and #EF_HARMLESS
        beq @enemy
        ; props get punted rather than damaged
        jsr punt_object
        jmp @next
@enemy:
        lda atk_kind
        cmp #1
        bne @kick
        lda e_flags,x
        and #EF_HEAVY
        bne @clang
        jmp @dmg
@kick:
        lda e_flags,x
        and #EF_ARMORED
        beq @dmg
        ; armour only protects the front
        jsr attack_from_behind
        bcs @dmg
@clang:
        lda e_hurt,x
        bne @next
        lda #12
        sta e_hurt,x
        jsr spark_at_entity
        ldx cur_ent
        lda #SFX_DEFLECT
        jsr sfx_play
        jmp @next
@dmg:
        lda atk_dmg
        jsr hurt_entity
@next:
        ldx cur_ent
        inx
        cpx #MAX_ENTITIES
        bcc @loop
        rts
.endproc

.proc in_attack_box
        lda e_xl,x
        cmp atk_x1
        lda e_xh,x
        sbc atk_x1+1
        bcc @no
        lda atk_x2
        cmp e_xl,x
        lda atk_x2+1
        sbc e_xh,x
        bcc @no
        ldy e_type,x
        lda e_yl,x
        cmp atk_y1
        bcc @no
        lda e_yl,x
        sec
        sbc ed_h,y
        cmp atk_y2
        bcs @no
        sec
        rts
@no:    clc
        rts
.endproc

; carry set when the player is behind the entity
.proc attack_from_behind
        lda e_flags,x
        and #EF_FACELEFT
        bne @faceleft
        ; entity faces right: hit from behind if the player is to its left
        lda px+1
        cmp e_xh,x
        bcc @yes
        bne @no
        lda px
        cmp e_xl,x
        bcc @yes
        bcs @no
@faceleft:
        lda e_xh,x
        cmp px+1
        bcc @yes
        bne @no
        lda e_xl,x
        cmp px
        bcc @yes
@no:    clc
        rts
@yes:   sec
        rts
.endproc

; ---------------------------------------------------------------------------
; hurt_entity -- A = damage, entity in X
; ---------------------------------------------------------------------------
.proc hurt_entity
        sta tmp0
        lda e_hurt,x
        bne @done
        lda e_hp,x
        cmp #255
        beq @invuln
        sec
        sbc tmp0
        bcc @die
        beq @die
        sta e_hp,x
        lda #14
        sta e_hurt,x
        lda #ES_STUNNED
        sta e_state,x
        lda #24
        sta e_tmr,x
        jsr knock_back
        jsr spark_at_entity
        ldx cur_ent
        lda #SFX_HIT
        jmp sfx_play
@invuln:
        lda #10
        sta e_hurt,x
        jsr spark_at_entity
        ldx cur_ent
        lda #SFX_DEFLECT
        jmp sfx_play
@die:
        jmp kill_entity
@done:  rts
.endproc

.proc kill_entity
        lda #0
        sta e_hp,x
        lda #ES_DYING
        sta e_state,x
        lda #16
        sta e_tmr,x
        jsr spark_at_entity
        ldx cur_ent
        lda #SFX_SQUASH
        jmp sfx_play
.endproc

.proc knock_back
        lda px+1
        cmp e_xh,x
        bcc @fromleft
        bne @fromright
        lda px
        cmp e_xl,x
        bcc @fromleft
@fromright:
        lda #<$FF00
        sta e_vxl,x
        lda #>$FF00
        sta e_vxh,x
        rts
@fromleft:
        lda #<$0100
        sta e_vxl,x
        lda #>$0100
        sta e_vxh,x
        rts
.endproc

; punt_object -- a kicked prop flies in the direction the foot is facing
.proc punt_object
        ldy p_shoe
        lda kick_power,y
        sta tmp0
        lda p_face
        bne @left
        lda #0
        sta e_vxl,x
        lda tmp0
        sta e_vxh,x
        jmp @up
@left:  lda #0
        sec
        sbc #0
        sta e_vxl,x
        lda #0
        sec
        sbc tmp0
        sta e_vxh,x
@up:
        lda #<$FE80
        sta e_vyl,x
        lda #>$FE80
        sta e_vyh,x
        lda #SFX_THROW
        jsr sfx_play
        ldx cur_ent
        rts
kick_power: .byte 3,2,5,6,3,3,2,7
.endproc

.proc reflect_shot
        jsr neg_vx
        lda e_flags,x
        eor #EF_FACELEFT
        and #<~EF_PROJECTILE
        sta e_flags,x
        lda #SFX_DEFLECT
        jsr sfx_play
        ldx cur_ent
        rts
.endproc

; ---------------------------------------------------------------------------
; particles
; ---------------------------------------------------------------------------
; spawn_particle -- A = type (ET_DUST / ET_SPARK / ET_SPLASH),
;                   ptr2 = world X, tmp7 = world Y
.proc spawn_particle
        sta ent_tmp
        ldy #0
@find:  lda pa_type,y
        beq @got
        iny
        cpy #MAX_PARTICLES
        bcc @find
        rts
@got:
        lda ent_tmp
        sta pa_type,y
        lda ptr2
        sta pa_xl,y
        lda ptr2+1
        sta pa_xh,y
        lda tmp7
        sta pa_y,y
        lda #0
        sta pa_vx,y
        sta pa_vy,y
        sta pa_frm,y
        lda #18
        sta pa_tmr,y
        rts
.endproc

.proc spark_at_entity
        lda e_xl,x
        sta ptr2
        lda e_xh,x
        sta ptr2+1
        ldy e_type,x
        lda e_yl,x
        sec
        sbc ed_h,y
        clc
        adc #4
        sta tmp7
        lda #ET_SPARK
        jmp spawn_particle
.endproc

.proc spark_here
        lda e_xl,x
        sta ptr2
        lda e_xh,x
        sta ptr2+1
        lda e_yl,x
        sta tmp7
        lda #ET_SPARK
        jmp spawn_particle
.endproc

.proc particles_update
        ldx #MAX_PARTICLES-1
@loop:  lda pa_type,x
        beq @next
        dec pa_tmr,x
        bne :+
        lda #0
        sta pa_type,x
        jmp @next
:       lda pa_tmr,x
        lsr a
        lsr a
        and #3
        cmp #3
        bcc :+
        lda #2
:       sta pa_frm,x
        lda pa_y,x
        sec
        sbc #1
        sta pa_y,x
@next:  dex
        bpl @loop
        rts
.endproc

.proc particles_draw
        ldy #MAX_PARTICLES-1
@loop:  sty ent_tmp
        lda pa_type,y
        beq @next
        sta tmp5
        lda pa_frm,y
        sta tmp6
        lda pa_xl,y
        sta ptr2
        lda pa_xh,y
        sta ptr2+1
        lda pa_y,y
        sta tmp4
        jsr spr_set_world
        bcs @next
        lda tmp5
        asl a
        asl a
        clc
        adc tmp6
        tay
        lda (ms_lo_ptr),y
        sta ptr1
        lda (ms_hi_ptr),y
        sta ptr1+1
        ora ptr1
        beq @next
        lda #0
        sta spr_attr
        sta spr_flip
        jsr draw_metasprite
@next:  ldy ent_tmp
        dey
        bpl @loop
        rts
.endproc

; ---------------------------------------------------------------------------
; entities_draw -- rotate the draw order every frame so that when the
; 8-sprites-per-scanline limit bites, the flicker is shared out evenly.
; ---------------------------------------------------------------------------
.proc entities_draw
        inc oam_order
        lda oam_order
        and #(MAX_ENTITIES - 1)
        cmp #MAX_ENTITIES
        bcc :+
        lda #0
:       sta ent_tmp2
        ldy #MAX_ENTITIES
@loop:  sty ent_tmp
        ldx ent_tmp2
        lda e_state,x
        beq @next
        stx cur_ent
        lda e_xl,x
        sta ptr2
        lda e_xh,x
        sta ptr2+1
        lda e_yl,x
        sta tmp4
        jsr spr_set_world
        bcs @next
        ldx cur_ent
        lda e_type,x
        asl a
        asl a
        clc
        adc e_frm,x
        tay
        lda (ms_lo_ptr),y
        sta ptr1
        lda (ms_hi_ptr),y
        sta ptr1+1
        ora ptr1
        beq @next
        ldx cur_ent
        ldy e_type,x
        lda ed_pal,y
        sta spr_attr
        lda e_hurt,x
        beq :+
        and #2
        beq :+
        lda #3                          ; flash palette on hit
        sta spr_attr
:       lda e_flags,x
        and #EF_FACELEFT
        beq :+
        lda #$40
:       sta spr_flip
        jsr draw_metasprite
@next:
        inc ent_tmp2
        lda ent_tmp2
        cmp #MAX_ENTITIES
        bcc :+
        lda #0
        sta ent_tmp2
:       ldy ent_tmp
        dey
        bne @loop
        rts
.endproc

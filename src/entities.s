;
; Entity pool.
;
.include "constants.inc"
.include "ram.inc"

.export entities_init, entities_update, entities_draw, spawn_check
.export entity_alloc, entity_free, spawn_at
.export particles_update, particles_draw, spawn_particle
.export boss_update, boss_draw, boss_trigger
.export player_attack_box, entity_hurt_area

.segment "CODE2"

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
        rts
.endproc

.proc entities_update
        rts
.endproc

.proc entities_draw
        rts
.endproc

.proc spawn_check
        rts
.endproc

.proc entity_alloc
        rts
.endproc

.proc entity_free
        rts
.endproc

.proc spawn_at
        rts
.endproc

.proc particles_update
        rts
.endproc

.proc particles_draw
        rts
.endproc

.proc spawn_particle
        rts
.endproc

.proc boss_update
        rts
.endproc

.proc boss_draw
        rts
.endproc

.proc boss_trigger
        rts
.endproc

.proc player_attack_box
        rts
.endproc

.proc entity_hurt_area
        rts
.endproc

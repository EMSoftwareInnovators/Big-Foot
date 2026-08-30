;
; Audio placeholder -- replaced by the real APU engine.
;
.include "constants.inc"
.include "ram.inc"

.export audio_init, audio_tick, sfx_play, music_play, audio_stop

.segment "CODE"

.proc audio_init
        lda #$0F
        sta APUSTATUS
        lda #MUS_NONE
        sta mus_song
        rts
.endproc

.proc audio_tick
        rts
.endproc

.proc sfx_play
        rts
.endproc

.proc music_play
        sta mus_song
        rts
.endproc

.proc audio_stop
        lda #$00
        sta APUSTATUS
        lda #$0F
        sta APUSTATUS
        lda #MUS_NONE
        sta mus_song
        rts
.endproc

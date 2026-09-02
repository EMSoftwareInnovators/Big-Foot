;
; BIG FOOT -- APU sound driver
;
; Four voices are driven from a single per-frame tick that runs inside the
; NMI once the PPU work is finished:
;
;   0  pulse 1   $4000    1  pulse 2   $4004
;   2  triangle  $4008    3  noise     $400C
;
; Every voice has the same register layout relative to its base address
; ($4000 + voice*4): +0 = volume/duty, +2 = period low, +3 = period high
; plus length reload.  That symmetry lets the mixer and the sound-effect
; player share one code path for all four voices.
;
; Music data lives in switchable banks reached through the $A000 window.
; The tick maps the bank it needs, does its work and puts the previous bank
; back before returning, so the main thread never sees the window move.
;
; Sound effects take over one voice each.  A request only displaces a
; playing effect of lower priority; while an effect owns a voice the music
; keeps running its envelopes but writes no registers, so when the effect
; ends the music reclaims the voice on the very next frame.
;
.include "constants.inc"
.include "ram.inc"

.import set_prga000
.import period_tbl, ins_duty, ins_env_lo, ins_env_hi
.import ins_arp_lo, ins_arp_hi, ins_settle
.import sfx_lo, sfx_hi
.import song_bank, song_lo, song_hi

.export audio_init, audio_tick, sfx_play, music_play, audio_stop, music_fade

NOTE_OFF        = $FF
PAT_END         = $E0
ENV_LOOP        = $FD
ENV_HOLD        = $FE
ARP_LOOP        = $7D
ARP_HOLD        = $7E

.segment "CODE"

; ---------------------------------------------------------------------------
; audio_init -- silence everything and put the APU in a known state
; ---------------------------------------------------------------------------
.proc audio_init
        lda #$0F                ; enable pulse 1/2, triangle and noise
        sta APUSTATUS
        lda #$40                ; four-step frame counter, no frame IRQ
        sta APUFRAME
        lda #$30                ; constant volume 0, length counter halted
        sta $4000
        sta $4004
        sta $400C
        lda #$08                ; sweep unit disabled
        sta $4001
        sta $4005
        lda #$80                ; triangle linear counter reload 0 = silent
        sta $4008
        lda #$08                ; load a non-zero length counter once; the
        sta $4003               ; halt flags above freeze it there, so the
        sta $4007               ; channels stay ungated from here on
        sta $400B
        sta $400F
        lda #0
        sta aud_busy
        ; fall through into audio_stop
.endproc

; ---------------------------------------------------------------------------
; audio_stop -- stop the music and every sound effect
; ---------------------------------------------------------------------------
.proc audio_stop
        inc aud_busy
        lda #MUS_NONE
        sta mus_song
        lda #0
        sta mus_fade
        ldx #3
loop:   sta ch_on,x
        sta ch_static,x
        sta sfxc_pri,x
        sta sfxc_rep,x
        dex
        bpl loop
        lda #$30
        sta $4000
        sta $4004
        sta $400C
        lda #$80
        sta $4008
        dec aud_busy
        rts
.endproc

; ---------------------------------------------------------------------------
; music_play -- A = song id.  MUS_NONE stops the music; replaying the song
; that is already running is ignored so that re-entering a room does not
; restart the theme.
; ---------------------------------------------------------------------------
.proc music_play
        cmp #MUS_NONE
        bne check
        jmp audio_stop
check:  cmp #NUM_SONGS
        bcc known
        rts
known:  cmp mus_song
        bne go
        rts
go:     inc aud_busy
        sta mus_song
        tax
        lda #0
        sta mus_fade
        lda bank_a000
        sta aud_bank
        lda song_bank,x
        jsr set_prga000
        ldx mus_song
        lda song_lo,x
        sta aud_p0
        lda song_hi,x
        sta aud_p0+1

        ldy #0
        lda (aud_p0),y          ; frames per row
        sta mus_speed
        iny
        ldx #0
hdr:    lda (aud_p0),y          ; four order-list pointers
        sta ch_ordb,x
        sta ch_ord,x
        iny
        inx
        cpx #8
        bcc hdr

        ldx #3
init:   lda #1
        sta ch_wait,x           ; the first event is read on the next tick
        sta ch_on,x
        sta ch_trig,x
        lda #4
        sta ch_len,x
        lda #15
        sta ch_vol,x
        lda #0
        sta ch_instr,x
        sta ch_ep,x
        sta ch_ap,x
        sta ch_static,x
        lda #NOTE_OFF
        sta ch_note,x
        sta ch_lasth,x
        dex
        bpl init

        ldx #3
ord:    jsr next_pattern        ; prime each voice with its first pattern
        ldx aud_ch
        dex
        bpl ord

        lda aud_bank
        jsr set_prga000
        dec aud_busy
        rts
.endproc

; ---------------------------------------------------------------------------
; music_fade -- A = attenuation, 0 = full volume, 15 = silent
; ---------------------------------------------------------------------------
.proc music_fade
        sta mus_fade
        ldx #3
        lda #0
:       sta ch_static,x         ; the new level has to reach the registers
        dex
        bpl :-
        rts
.endproc

; ---------------------------------------------------------------------------
; sfx_play -- A = effect id.  Claims one voice when the priority allows it.
; ---------------------------------------------------------------------------
.proc sfx_play
        cmp #NUM_SFX
        bcs out
        tax
        inc aud_busy
        lda bank_a000
        sta aud_bank
        lda #AUDIO_BANK
        jsr set_prga000
        lda sfx_lo,x
        sta aud_p0
        lda sfx_hi,x
        sta aud_p0+1
        ldy #0
        lda (aud_p0),y          ; voice
        and #3
        tax
        iny
        lda (aud_p0),y          ; priority
        cmp sfxc_pri,x
        bcc done                ; a louder effect already owns this voice
        pha
        txa
        asl a
        tay                     ; Y = voice*2
        lda aud_p0
        clc
        adc #2
        sta sfxc_ptr,y
        lda aud_p0+1
        adc #0
        sta sfxc_ptr+1,y
        lda #0
        sta sfxc_rep,x
        pla
        sta sfxc_pri,x          ; armed last: this is the "in use" flag
done:   lda aud_bank
        jsr set_prga000
        dec aud_busy
out:    rts
.endproc

; ---------------------------------------------------------------------------
; audio_tick -- one frame of sound.  Called from the NMI.
; ---------------------------------------------------------------------------
.proc audio_tick
        lda aud_busy
        beq run
        rts                     ; the main thread is mid-edit; skip a frame
run:    lda bank_a000
        sta aud_bank

        lda mus_song
        cmp #MUS_NONE
        beq no_music

        ; ---- phase 1: advance the pattern streams (song bank mapped) ----
        tax
        lda song_bank,x
        jsr set_prga000
        ldx #3
step:   stx aud_ch
        lda ch_on,x
        beq :+
        dec ch_wait,x
        bne :+
        jsr read_events
:       ldx aud_ch
        dex
        bpl step

        ; ---- phase 2: envelopes and register writes (audio bank) --------
        ; Unrolled: voice_out keeps the voice in X, so the loop would exist
        ; only to spill and reload it.
        lda #AUDIO_BANK
        jsr set_prga000
        ldx #0
        jsr voice_out
        ldx #1
        jsr voice_out
        ldx #2
        jsr voice_out
        ldx #3
        jsr voice_out
        jmp do_sfx

no_music:
        lda #AUDIO_BANK
        jsr set_prga000
do_sfx:
        ldx #3
sfx:    stx aud_ch
        lda sfxc_pri,x
        beq :+
        jsr sfx_frame
:       ldx aud_ch
        dex
        bpl sfx
        lda aud_bank
        jmp set_prga000
.endproc

; ---------------------------------------------------------------------------
; next_pattern -- X = voice.  Take the next entry from the order list; a
; $0000 entry rewinds to the head of the list so every song loops.
; ---------------------------------------------------------------------------
.proc next_pattern
        stx aud_ch
        txa
        asl a
        tay
        lda ch_ord,y
        sta aud_p1
        lda ch_ord+1,y
        sta aud_p1+1
        jsr fetch
        lda aud_p2
        ora aud_p2+1
        bne got
        lda aud_ch              ; end of list -- rewind
        asl a
        tay
        lda ch_ordb,y
        sta aud_p1
        lda ch_ordb+1,y
        sta aud_p1+1
        jsr fetch
        lda aud_p2
        ora aud_p2+1
        bne got
        ldx aud_ch              ; an empty list: this voice has nothing to do
        lda #0
        sta ch_on,x
        rts
got:    lda aud_ch
        asl a
        tay
        lda aud_p2
        sta ch_ptr,y
        lda aud_p2+1
        sta ch_ptr+1,y
        lda aud_p1
        clc
        adc #2
        sta ch_ord,y
        lda aud_p1+1
        adc #0
        sta ch_ord+1,y
        ldx aud_ch
        rts
fetch:  ldy #0
        lda (aud_p1),y
        sta aud_p2
        iny
        lda (aud_p1),y
        sta aud_p2+1
        rts
.endproc

; ---------------------------------------------------------------------------
; read_events -- aud_ch = voice.  Consume pattern bytes until one of them
; costs time, then charge length*speed frames to the wait counter.
; ---------------------------------------------------------------------------
.proc read_events
        lda aud_ch
        asl a
        tay
        lda ch_ptr,y
        sta aud_p0
        lda ch_ptr+1,y
        sta aud_p0+1
        lda #64                 ; guard against malformed data
        sta aud_tmp
next:   ldy #0
        lda (aud_p0),y
        inc aud_p0
        bne :+
        inc aud_p0+1
:       cmp #$60
        bcs not_note
        ; ---- note on ----------------------------------------------------
        ldx aud_ch
        sta ch_note,x
        lda #0
        sta ch_ep,x
        sta ch_ap,x
        sta ch_static,x
        lda #1
        sta ch_trig,x
        jmp set_wait
not_note:
        cmp #$62
        bcs command
        cmp #$61
        beq set_wait            ; tie: let the sounding note run on
        ldx aud_ch              ; rest
        lda #NOTE_OFF
        sta ch_note,x
        lda #0
        sta ch_static,x
        jmp set_wait
command:
        cmp #$C0
        bcs not_len
        sec                     ; $80..$BF -- note length in rows
        sbc #$7F
        ldx aud_ch
        sta ch_len,x
        jmp again
not_len:
        cmp #$D0
        bcs not_ins
        and #$0F                ; $C0..$CF -- instrument
        ldx aud_ch
        sta ch_instr,x
        lda #0
        sta ch_ep,x
        sta ch_ap,x
        sta ch_static,x
        jmp again
not_ins:
        cmp #PAT_END
        bcs end_pat
        and #$0F                ; $D0..$DF -- channel volume
        ldx aud_ch
        sta ch_vol,x
        lda #0
        sta ch_static,x
        jmp again
end_pat:
        ldx aud_ch
        jsr next_pattern
        lda ch_on,x
        beq stop
        lda aud_ch
        asl a
        tay
        lda ch_ptr,y
        sta aud_p0
        lda ch_ptr+1,y
        sta aud_p0+1
again:  dec aud_tmp
        beq :+
        jmp next
:       ldx aud_ch              ; runaway data: shut the voice up
        lda #0
        sta ch_on,x
stop:   rts

set_wait:
        ldx aud_ch
        ldy ch_len,x
        lda #0
mul:    clc
        adc mus_speed
        dey
        bne mul
        sta ch_wait,x
        lda aud_ch
        asl a
        tay
        lda aud_p0
        sta ch_ptr,y
        lda aud_p0+1
        sta ch_ptr+1,y
        rts
.endproc

; ---------------------------------------------------------------------------
; voice_out -- X = aud_ch = voice.  Run the instrument envelopes and push the
; result to the APU.
;
; Two early exits keep the mixer cheap.  A voice a sound effect has borrowed
; is left completely alone: its envelope freezes for those few frames, which
; nobody can hear, and the effect's release retriggers it.  A voice whose
; envelopes have run to their final values is marked static and skipped
; until a new note, instrument, volume or fade disturbs it -- which covers
; most of a sustained lead, the whole triangle bass and every drum that has
; decayed to silence.
; ---------------------------------------------------------------------------
.proc voice_out
        lda sfxc_pri,x
        ora ch_static,x
        beq go
        rts
go:     txa
        asl a
        asl a
        sta aud_reg             ; 0, 4, 8, 12

        lda ch_on,x
        bne :+
        jmp silent
:       lda ch_note,x
        cmp #NOTE_OFF
        bne :+
        jmp silent
:       sta aud_note

        ldy ch_instr,x
        lda ins_env_lo,y
        sta aud_p0
        lda ins_env_hi,y
        sta aud_p0+1
        jsr env_step            ; A = 0..15, carry set once the envelope holds
        sta aud_vol
        bcc live
        ldy ch_instr,x
        lda ins_settle,y
        beq live
        sta ch_static,x         ; nothing can change this voice from here
live:
        lda #15                 ; attenuate by the pattern volume and the fade
        sec
        sbc ch_vol,x
        clc
        adc mus_fade
        sta aud_tmp
        lda aud_vol
        sec
        sbc aud_tmp
        bcs :+
        lda #0
:       sta aud_vol

        ; ---- volume / duty register -------------------------------------
        cpx #2
        beq tri_vol
        ldy ch_instr,x
        lda ins_duty,y
        ora #$30
        ora aud_vol
        bne put_vol             ; always taken: bit 4 of $30 is set
tri_vol:
        lda aud_vol
        beq tri_off
        lda #$FF
        bne put_vol
tri_off:
        lda #$80
put_vol:
        ldy aud_reg
        sta $4000,y

        ; ---- pitch ------------------------------------------------------
        ldy ch_instr,x
        lda ins_settle,y
        bne noarp
        lda ins_arp_lo,y
        sta aud_p1
        lda ins_arp_hi,y
        sta aud_p1+1
        jsr arp_step            ; A = signed semitone offset
        clc
        adc aud_note
        jmp shifted
noarp:  lda aud_note
shifted:
        cpx #3
        beq noise
        cpx #2
        bne :+
        clc
        adc #12                 ; the triangle sounds an octave below a pulse
:       asl a
        tay
        lda period_tbl,y
        sta aud_p2
        lda period_tbl+1,y
        sta aud_p2+1
        jmp emit
noise:
        and #$0F
        sta aud_tmp
        ldy ch_instr,x
        lda ins_duty,y
        and #$80                ; bit 7 selects the short (tonal) mode
        ora aud_tmp
        sta aud_p2
        lda #0
        sta aud_p2+1

emit:   ldy aud_reg
        lda aud_p2
        sta $4002,y
        lda ch_trig,x
        bne write_hi
        lda aud_p2+1
        cmp ch_lasth,x
        beq done
write_hi:
        lda aud_p2+1
        sta ch_lasth,x
        ora #$08                ; length counter reload index 1
        sta $4003,y
        lda #0
        sta ch_trig,x
done:   rts

silent: lda #0
        sta ch_trig,x
        sta aud_vol
        lda #1
        sta ch_static,x         ; one write is enough until something changes
        ldy aud_reg
        cpx #2
        beq tri_quiet
        lda #$30
        sta $4000,y
        rts
tri_quiet:
        lda #$80
        sta $4008
        rts
.endproc

; ---------------------------------------------------------------------------
; env_step -- aud_p0 = envelope, X = voice.  Returns the next value in A and
; advances ch_ep; $FD <index> loops, $FE holds the previous value forever.
; ---------------------------------------------------------------------------
.proc env_step
        ldy ch_ep,x
step:   lda (aud_p0),y
        cmp #ENV_LOOP
        beq do_loop
        cmp #ENV_HOLD
        beq do_hold
        iny
        tya
        sta ch_ep,x
        dey
        lda (aud_p0),y
        clc                     ; more envelope to come
        rts
do_loop:
        iny
        lda (aud_p0),y
        tay
        jmp step
do_hold:
        dey
        bmi zero
        tya
        sta ch_ep,x
        lda (aud_p0),y
        sec                     ; this value repeats for ever
        rts
zero:   lda #0
        sec
        rts
.endproc

; ---------------------------------------------------------------------------
; arp_step -- as env_step but for the signed pitch envelope in aud_p1.
; An instrument with no pitch envelope points at a single $7E byte.
; ---------------------------------------------------------------------------
.proc arp_step
        ldy ch_ap,x
step:   lda (aud_p1),y
        cmp #ARP_LOOP
        beq do_loop
        cmp #ARP_HOLD
        beq do_hold
        iny
        tya
        sta ch_ap,x
        dey
        lda (aud_p1),y
        rts
do_loop:
        iny
        lda (aud_p1),y
        tay
        jmp step
do_hold:
        dey
        bmi zero
        tya
        sta ch_ap,x
        lda (aud_p1),y
        rts
zero:   lda #0
        rts
.endproc

; ---------------------------------------------------------------------------
; sfx_frame -- aud_ch = X = voice with a running effect.
;
; Stream format, from the third byte of the record onwards:
;       vv pp qq        write vv/pp/qq to +0/+2/+3 and consume one frame
;       $FE n           hold the registers as they are for n more frames
;       $FF             end of effect: release the voice
; ---------------------------------------------------------------------------
.proc sfx_frame
        lda sfxc_rep,x
        beq fetch
        dec sfxc_rep,x
        rts
fetch:  txa
        asl a
        tay
        lda sfxc_ptr,y
        sta aud_p0
        lda sfxc_ptr+1,y
        sta aud_p0+1
        ldy #0
        lda (aud_p0),y
        cmp #$FF
        beq finish
        cmp #$FE
        beq hold
        lda aud_ch
        asl a
        asl a
        tax                     ; X = voice*4
        lda (aud_p0),y
        sta $4000,x
        iny
        lda (aud_p0),y
        sta $4002,x
        iny
        lda (aud_p0),y
        sta $4003,x
        iny
adv:    tya
        clc
        adc aud_p0
        sta aud_p0
        lda aud_p0+1
        adc #0
        sta aud_p0+1
        lda aud_ch
        asl a
        tay
        lda aud_p0
        sta sfxc_ptr,y
        lda aud_p0+1
        sta sfxc_ptr+1,y
        rts
hold:   iny
        lda (aud_p0),y
        ldx aud_ch
        sta sfxc_rep,x
        iny
        jmp adv
finish: ldx aud_ch
        lda #0
        sta sfxc_pri,x
        sta sfxc_rep,x
        sta ch_static,x         ; hand the voice back to the music
        lda #$FF
        sta ch_lasth,x          ; force the music to rewrite this voice
        lda #1
        sta ch_trig,x
        cpx #2
        beq tri_off
        txa
        asl a
        asl a
        tax
        lda #$30
        sta $4000,x
        rts
tri_off:
        lda #$80
        sta $4008
        rts
.endproc

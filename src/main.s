;
; Main loop and game-mode dispatch
;
.include "constants.inc"
.include "ram.inc"

.import read_pads, wait_nmi, ppu_off
.import title_enter, title_run
.import intro_enter, intro_run
.import stageintro_enter, stageintro_run
.import play_enter, play_run
.import death_enter, death_run
.import gameover_enter, gameover_run
.import password_enter, password_run
.import cutscene_enter, cutscene_run
.import ending_enter, ending_run
.import credits_enter, credits_run
.import stageclear_enter, stageclear_run
.import map_enter, map_run

.export main_loop, call_ptr0

.segment "CODE"

.proc main_loop
        cli
@loop:
        jsr read_pads

        lda mode_next
        cmp game_mode
        beq @dispatch
        sta game_mode
        lda #0
        sta mode_timer
        sta sub_state
        ldx game_mode
        lda enter_lo,x
        sta ptr0
        lda enter_hi,x
        sta ptr0+1
        jsr call_ptr0

@dispatch:
        ldx game_mode
        lda run_lo,x
        sta ptr0
        lda run_hi,x
        sta ptr0+1
        jsr call_ptr0

        inc mode_timer
        jsr wait_nmi
        jmp @loop
.endproc

.proc call_ptr0
        jmp (ptr0)
.endproc

enter_lo:
        .lobytes title_enter, intro_enter, stageintro_enter, play_enter
        .lobytes death_enter, gameover_enter, password_enter, cutscene_enter
        .lobytes ending_enter, credits_enter, stageclear_enter, map_enter
enter_hi:
        .hibytes title_enter, intro_enter, stageintro_enter, play_enter
        .hibytes death_enter, gameover_enter, password_enter, cutscene_enter
        .hibytes ending_enter, credits_enter, stageclear_enter, map_enter
run_lo:
        .lobytes title_run, intro_run, stageintro_run, play_run
        .lobytes death_run, gameover_run, password_run, cutscene_run
        .lobytes ending_run, credits_run, stageclear_run, map_run
run_hi:
        .hibytes title_run, intro_run, stageintro_run, play_run
        .hibytes death_run, gameover_run, password_run, cutscene_run
        .hibytes ending_run, credits_run, stageclear_run, map_run

;
; The narrative modes.
;
; Each one is a thin wrapper around the cutscene interpreter: choose a
; script, then let it run.  The scripts themselves are in
; tools/gen_text.py and end by naming the mode that follows.
;
.include "constants.inc"
.include "ram.inc"
.include "text.inc"

.import script_start, script_run

.export intro_enter, intro_run
.export cutscene_enter, cutscene_run
.export ending_enter, ending_run
.export credits_enter, credits_run

.segment "MENU"

.proc intro_enter
        lda #SCRIPT_INTRO
        jmp script_start
.endproc

.proc intro_run
        jmp script_run
.endproc

; The dispatch that follows a cleared stage.  stage_num has already been
; advanced, so stage 1 reports the fall of the village in stage 0.
.proc cutscene_enter
        lda stage_num
        beq :+
        sec
        sbc #1
:       clc
        adc #SCRIPT_CUT0
        jmp script_start
.endproc

.proc cutscene_run
        jmp script_run
.endproc

.proc ending_enter
        lda #SCRIPT_ENDING
        jmp script_start
.endproc

.proc ending_run
        jmp script_run
.endproc

.proc credits_enter
        lda #SCRIPT_CREDITS
        jmp script_start
.endproc

.proc credits_run
        jmp script_run
.endproc

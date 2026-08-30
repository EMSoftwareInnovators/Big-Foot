; Temporary title stub: drops straight into stage 1 so the engine can be
; exercised.  Replaced by the real title screen later in the build.
.include "constants.inc"
.include "ram.inc"
.import start_stage
.export title_enter, title_run
.segment "CODE2"
.proc title_enter
        rts
.endproc
.proc title_run
        lda #0
        jmp start_stage
.endproc

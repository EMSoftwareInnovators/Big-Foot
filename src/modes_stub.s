.include "constants.inc"
.include "ram.inc"
.segment "CODE2"
.macro STUBMODE name
        .export name
        .proc name
                rts
        .endproc
.endmacro
STUBMODE intro_enter
STUBMODE intro_run
STUBMODE stageintro_enter
STUBMODE stageintro_run
STUBMODE death_enter
STUBMODE death_run
STUBMODE gameover_enter
STUBMODE gameover_run
STUBMODE password_enter
STUBMODE password_run
STUBMODE cutscene_enter
STUBMODE cutscene_run
STUBMODE ending_enter
STUBMODE ending_run
STUBMODE credits_enter
STUBMODE credits_run
STUBMODE stageclear_enter
STUBMODE stageclear_run
STUBMODE map_enter
STUBMODE map_run

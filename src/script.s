;
; Cutscene interpreter.
;
; The intro, the seven dispatches from the kingdom, the ending and the
; credits are all the same thing: a short bytecode program that paints a
; picture, prints lines of text through the VRAM queue, waits, and finally
; hands control to another game mode.  Keeping them as data rather than code
; means the whole narrative lives in one place (tools/gen_text.py) and costs
; the fixed banks nothing.
;
; One command runs per frame.  That is deliberate: printing a line takes a
; VRAM packet, and a packet per frame is exactly what the NMI can drain.
;
.include "constants.inc"
.include "ram.inc"
.include "text.inc"

.import set_prga000, script_lo, script_hi
.import text_center_queue, text_queue, text_blank_row
.import screen_load, blank_screen, ppu_off, ppu_on
.import music_play, sfx_play, music_fade, shake_start
.import call_ptr0

.export script_start, script_run, script_done

; MENU_BANK and TEXT_BANK are the same bank, so mapping the text bank from
; here never swaps this code out from under itself.
.segment "MENU"

; ---------------------------------------------------------------------------
; script_start -- A = script id
; ---------------------------------------------------------------------------
.proc script_start
        sta tmp0
        lda bank_a000
        sta sc_bank
        lda #TEXT_BANK
        jsr set_prga000
        ldx tmp0
        lda script_lo,x
        sta sc_ptr
        lda script_hi,x
        sta sc_ptr+1
        lda sc_bank
        jsr set_prga000
        lda #0
        sta sc_wait
        sta sc_hold
        sta sc_count
        rts
.endproc

; ---------------------------------------------------------------------------
; script_run -- advance the program by at most one command
; ---------------------------------------------------------------------------
.proc script_run
        lda sc_hold
        beq @timer
        lda pad1_new
        and #(BTN_START | BTN_A)
        beq @done
        lda #0
        sta sc_hold
        beq @work
@timer:
        lda sc_wait
        beq @work
        dec sc_wait
        rts
@work:
        lda sc_count            ; a multi-row wipe is still running
        beq @fetch
        dec sc_count
        lda sc_row
        inc sc_row
        jmp text_blank_row
@fetch:
        lda bank_a000
        sta sc_bank
        lda #TEXT_BANK
        jsr set_prga000
        jsr exec
        lda sc_bank
        jmp set_prga000
@done:  rts
.endproc

; script_done -- non-zero once the program has run off its end
.proc script_done
        lda sc_ptr
        ora sc_ptr+1
        rts
.endproc

; ---------------------------------------------------------------------------
; exec -- one command, with the text bank mapped
; ---------------------------------------------------------------------------
.proc exec
        ldy #0
        lda (sc_ptr),y
        cmp #14
        bcc :+
        lda #SC_END
:       asl a
        tax
        lda handlers,x
        sta ptr0
        lda handlers+1,x
        sta ptr0+1
        jmp call_ptr0

handlers:
        .word do_end, do_screen, do_blank, do_text, do_textat
        .word do_wait, do_music, do_sfx, do_clear, do_pause
        .word do_mode, do_fade, do_shake, do_step
.endproc

; ---------------------------------------------------------------------------
; advancing the program counter
; ---------------------------------------------------------------------------
.proc adv                       ; A = operand bytes including the opcode
        clc
        adc sc_ptr
        sta sc_ptr
        bcc :+
        inc sc_ptr+1
:       rts
.endproc

.proc arg1                      ; -> A = first operand
        ldy #1
        lda (sc_ptr),y
        rts
.endproc

; ---------------------------------------------------------------------------
; the commands
; ---------------------------------------------------------------------------
.proc do_end
        lda #255
        sta sc_wait             ; park: the script should have ended in MODE
        rts
.endproc

.proc do_screen
        jsr arg1
        pha
        jsr ppu_off
        pla
        jsr screen_load         ; also points the CHR banks at the picture
        lda #$10                ; background patterns at $1000, VRAM step 1
        sta ppu_ctrl
        jsr ppu_on
        lda #2
        jmp adv
.endproc

.proc do_blank
        jsr blank_screen
        lda #1
        jmp adv
.endproc

.proc do_text
        jsr arg1
        sta tmp1                ; row
        ldy #2
        lda (sc_ptr),y
        sta ptr1
        iny
        lda (sc_ptr),y
        sta ptr1+1
        jsr text_center_queue
        lda #4
        jmp adv
.endproc

.proc do_textat
        jsr arg1
        sta tmp0                ; column
        ldy #2
        lda (sc_ptr),y
        sta tmp1                ; row
        iny
        lda (sc_ptr),y
        sta ptr1
        iny
        lda (sc_ptr),y
        sta ptr1+1
        jsr text_queue
        lda #5
        jmp adv
.endproc

.proc do_wait
        jsr arg1
        sta sc_wait
        lda #2
        jmp adv
.endproc

.proc do_music
        jsr arg1
        jsr music_play
        lda #2
        jmp adv
.endproc

.proc do_sfx
        jsr arg1
        jsr sfx_play
        lda #2
        jmp adv
.endproc

.proc do_clear
        jsr arg1
        sta sc_row
        ldy #2
        lda (sc_ptr),y
        sta sc_count
        lda #3
        jmp adv
.endproc

.proc do_pause
        lda #1
        sta sc_hold
        lda #1
        jmp adv
.endproc

.proc do_mode
        jsr arg1
        sta mode_next
        lda #0                  ; the script is spent
        sta sc_ptr
        sta sc_ptr+1
        rts
.endproc

.proc do_fade
        jsr arg1
        jsr music_fade
        lda #2
        jmp adv
.endproc

.proc do_shake
        jsr arg1
        ldx #3
        jsr shake_start
        lda #2
        jmp adv
.endproc

; One enormous footfall: the screen jolts, the noise channel takes the hit,
; and the scene holds still for a moment afterwards.
.proc do_step
        lda #24
        ldx #5
        jsr shake_start
        lda #SFX_MEGASTOMP
        jsr sfx_play
        lda #45
        sta sc_wait
        lda #1
        jmp adv
.endproc

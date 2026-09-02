;
; Metasprite rendering.
;
; A metasprite is a rectangular grid of 8x8 cells so that one compact record
; serves the 5x6 player, a 2x2 enemy and a 6x6 boss alike:
;
;   .byte dx, dy        signed pixel offset of the top-left cell
;   .byte w, h          grid size in tiles
;   .byte attr          palette and priority
;   .byte tile * (w*h)  row major, 0 = skip this cell
;
; OAM entry 0 is reserved for the sprite-0 hit that drives the HUD split.
;
.include "constants.inc"
.include "ram.inc"
.include "bg.inc"
.include "player_frames.inc"

.export oam_reset, oam_finish, draw_metasprite, spr_set_world

.segment "CODE"

SPR0_Y  = 23
SPR0_X  = 248

; ---------------------------------------------------------------------------
; oam_reset -- start a frame's sprite list
; ---------------------------------------------------------------------------
.proc oam_reset
        lda #$F8
        sta oam_buf+0                   ; entry 0 is no longer reserved
        lda #0
        sta oam_idx
        rts
.endproc

; ---------------------------------------------------------------------------
; oam_finish -- hide every entry left over from the previous frame
; ---------------------------------------------------------------------------
.proc oam_finish
        ldx oam_idx
        lda #$F8
@loop:  cpx oam_hi
        bcs @done
        sta oam_buf,x
        inx
        inx
        inx
        inx
        bne @loop
@done:  lda oam_idx
        sta oam_hi
        rts
.endproc

; ---------------------------------------------------------------------------
; spr_set_world -- convert a world position to screen space.
;   ptr2 = world X (16-bit), tmp4 = world Y
; Result in spr_x (signed 16-bit) and spr_y; carry set if the object is far
; enough off screen to skip entirely.
; ---------------------------------------------------------------------------
.proc spr_set_world
        lda ptr2
        sec
        sbc cam_x
        sta spr_x
        lda ptr2+1
        sbc cam_x+1
        sta spr_x+1
        lda tmp4
        clc
        adc #PLAY_TOP
        sta spr_y
        lda spr_x+1
        beq @ok                         ; 0..255: on screen
        cmp #$FF
        beq @leftedge
        cmp #$01
        beq @rightedge
        sec
        rts
@leftedge:
        lda spr_x
        cmp #$C0                        ; -64 .. -1
        bcc @off
        clc
        rts
@rightedge:
        lda spr_x
        cmp #$40                        ; 256 .. 319
        bcs @off
@ok:    clc
        rts
@off:   sec
        rts
.endproc

; ---------------------------------------------------------------------------
; draw_metasprite -- ptr1 = metasprite, spr_x/spr_y = origin, spr_flip = $40
; to mirror horizontally, spr_attr ORed into every entry.
; ---------------------------------------------------------------------------
.proc draw_metasprite
        ldy #0
        lda (ptr1),y                    ; dx
        sta tmp0
        iny
        lda (ptr1),y                    ; dy
        sta tmp1
        iny
        lda (ptr1),y                    ; w
        sta tmp2
        iny
        lda (ptr1),y                    ; h
        sta tmp3
        iny
        lda (ptr1),y                    ; attr
        ora spr_attr
        ora spr_flip
        sta tmp4

        ; ---- screen X of the leftmost cell, and the per-cell step --------
        lda spr_flip
        bne @flip
        lda tmp0
        bpl :+
        ldx #$FF
        bne :++
:       ldx #0
:       clc
        adc spr_x
        sta tmp6
        txa
        adc spr_x+1
        sta tmp7
        lda #8
        sta tmp5
        lda #0
        sta tmp8
        jmp @ystart
@flip:
        ; mirrored: the row starts at origin - dx - 8 and walks backwards
        lda tmp0
        bpl :+
        ldx #$FF
        bne :++
:       ldx #0
:       clc
        adc spr_x
        sta tmp6
        txa
        adc spr_x+1
        sta tmp7
        lda tmp2
        asl a
        asl a
        asl a
        sta tmpA
        lda tmp6
        clc
        adc tmpA
        sta tmp6
        lda tmp7
        adc #0
        sta tmp7
        lda tmp6
        sec
        sbc #8
        sta tmp6
        lda tmp7
        sbc #0
        sta tmp7
        lda #$F8
        sta tmp5
        lda #$FF
        sta tmp8
@ystart:
        lda tmp1
        clc
        adc spr_y
        sta tmp9                        ; screen Y of the first row

        ; Decide once whether every cell lands inside the screen; if so the
        ; per-cell high byte never changes and the fast loop applies.
        lda #0
        sta tmpA
        lda spr_flip
        bne @slowpath
        lda tmp7
        bne @slowpath
        lda tmp2
        asl a
        asl a
        asl a
        clc
        adc tmp6
        bcs @slowpath
        lda #1
        sta tmpA
@slowpath:
        ldy #5                          ; cursor into the tile stream
        lda #0
        sta tmpB                        ; row
@row:
        lda tmpB
        asl a
        asl a
        asl a
        clc
        adc tmp9
        cmp #$F0
        bcc :+
        jmp @skiprow
:       cmp #8
        bcs :+
        jmp @skiprow
:       sec
        sbc #1
        sta tmpF                        ; OAM Y for this row (screen Y - 1)
        lda tmp6
        sta tmpD                        ; running screen X
        lda tmp7
        sta tmpE
        ldx tmp2                        ; columns remaining
        lda tmpA
        beq @col
        jmp @fast
@col:
        lda (ptr1),y
        beq @step
        sta tmpA
        lda tmpE
        bne @step                       ; this cell is off screen horizontally
        stx tmpC
        ldx oam_idx
        cpx #252
        bcs @full
        lda tmpF
        sta oam_buf,x
        lda tmpA
        sta oam_buf+1,x
        lda tmp4
        sta oam_buf+2,x
        lda tmpD
        sta oam_buf+3,x
        txa
        clc
        adc #4
        sta oam_idx
@full:  ldx tmpC
@step:
        iny
        lda tmpD
        clc
        adc tmp5
        sta tmpD
        lda tmpE
        adc tmp8
        sta tmpE
        dex
        bne @col
        jmp @nextrow
@fast:
        lda (ptr1),y
        beq @fstep
        stx tmpC
        ldx oam_idx
        cpx #252
        bcs @fdone
        sta oam_buf+1,x
        lda tmpF
        sta oam_buf,x
        lda tmp4
        sta oam_buf+2,x
        lda tmpD
        sta oam_buf+3,x
        txa
        clc
        adc #4
        sta oam_idx
@fdone: ldx tmpC
@fstep:
        iny
        lda tmpD
        clc
        adc #8
        sta tmpD
        dex
        bne @fast
        jmp @nextrow

@skiprow:
        tya
        clc
        adc tmp2
        tay
@nextrow:
        inc tmpB
        lda tmpB
        cmp tmp3
        bcs @done
        jmp @row
@done:  rts
.endproc

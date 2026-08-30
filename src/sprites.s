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
        lda split_on
        beq @nosplit
        lda #SPR0_Y
        sta oam_buf+0
        lda #PLAYER_SPR0_TILE
        sta oam_buf+1
        lda #$20                        ; behind background, palette 0
        sta oam_buf+2
        lda #SPR0_X
        sta oam_buf+3
        lda #4
        sta oam_idx
        rts
@nosplit:
        lda #$FF
        sta oam_buf+0
        lda #4
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
        sta tmp4
        iny
        sty tmp5                        ; index of the first tile byte

        ; ---- starting screen X ------------------------------------------
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
        sta tmp8                        ; column step
        jmp @ystart
@flip:
        ; mirrored: x = origin - dx - w*8
        lda tmp2
        asl a
        asl a
        asl a
        clc
        adc tmp0
        sta tmp9
        lda #0
        sbc #0
        sta tmpA
        lda spr_x
        sec
        sbc tmp9
        sta tmp6
        lda spr_x+1
        sbc #0
        sta tmp7
        lda #8
        sta tmp8
@ystart:
        lda tmp1
        clc
        adc spr_y
        sta tmp9                        ; screen Y of the first row

        ldx #0                          ; row counter
@row:   stx tmpB
        ldy #0                          ; column counter
@col:   sty tmpC
        ; tile index = tiles[row * w + col]
        lda tmpB
        beq @noskip
        sta tmpD
        lda #0
@mul:   clc
        adc tmp2
        dec tmpD
        bne @mul
        jmp @havebase
@noskip:
        lda #0
@havebase:
        clc
        adc tmpC
        clc
        adc tmp5
        tay
        lda (ptr1),y
        beq @next
        sta tmpE                        ; tile

        ; screen Y for this row
        lda tmpB
        asl a
        asl a
        asl a
        clc
        adc tmp9
        sta tmpF
        cmp #$F0
        bcs @next
        cmp #8
        bcc @next

        ; screen X for this column
        lda spr_flip
        bne @fx
        lda tmpC
        asl a
        asl a
        asl a
        clc
        adc tmp6
        sta tmpD
        lda tmp7
        adc #0
        bne @next                       ; off screen left or right
        jmp @emit
@fx:    lda tmp2
        sec
        sbc tmpC
        sec
        sbc #1
        asl a
        asl a
        asl a
        clc
        adc tmp6
        sta tmpD
        lda tmp7
        adc #0
        bne @next
@emit:
        ldx oam_idx
        cpx #252
        bcs @done
        lda tmpF
        sec
        sbc #1
        sta oam_buf,x
        inx
        lda tmpE
        sta oam_buf,x
        inx
        lda tmp4
        ora spr_flip
        sta oam_buf,x
        inx
        lda tmpD
        sta oam_buf,x
        inx
        stx oam_idx
@next:
        ldy tmpC
        iny
        cpy tmp2
        bcs :+
        jmp @col
:       ldx tmpB
        inx
        cpx tmp3
        bcs @done
        jmp @row
@done:  rts
.endproc

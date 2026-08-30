;
; iNES header -- MMC3 (mapper 4), 256 KiB PRG, 128 KiB CHR, vertical mirroring
;
.segment "HDR"
        .byte "NES", $1A
        .byte 16                ; 16 x 16 KiB PRG-ROM = 256 KiB
        .byte 32                ; 32 x  8 KiB CHR-ROM = 256 KiB
        .byte $40               ; mapper low nibble = 4, vertical mirroring
        .byte $00               ; mapper high nibble = 0, iNES 1.0
        .byte 0, 0, 0, 0, 0, 0, 0, 0

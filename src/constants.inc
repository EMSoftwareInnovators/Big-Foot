;
; BIG FOOT -- global constants
;

; ---------------------------------------------------------------- PPU / APU
PPUCTRL         = $2000
PPUMASK         = $2001
PPUSTATUS       = $2002
OAMADDR         = $2003
OAMDATA         = $2004
PPUSCROLL       = $2005
PPUADDR         = $2006
PPUDATA         = $2007
OAMDMA          = $4014
APUSTATUS       = $4015
JOY1            = $4016
JOY2            = $4017
APUFRAME        = $4017

; ---------------------------------------------------------------- MMC3
MMC3_BANKSEL    = $8000
MMC3_BANKDATA   = $8001
MMC3_MIRROR     = $A000
MMC3_PRGRAM     = $A001
MMC3_IRQLATCH   = $C000
MMC3_IRQRELOAD  = $C001
MMC3_IRQDISABLE = $E000
MMC3_IRQENABLE  = $E001

; ---------------------------------------------------------------- controller
BTN_RIGHT       = $01
BTN_LEFT        = $02
BTN_DOWN        = $04
BTN_UP          = $08
BTN_START       = $10
BTN_SELECT      = $20
BTN_B           = $40
BTN_A           = $80

; ---------------------------------------------------------------- game modes
MODE_TITLE      = 0
MODE_INTRO      = 1
MODE_STAGE_INTRO= 2
MODE_PLAY       = 3
MODE_DEATH      = 4
MODE_GAMEOVER   = 5
MODE_PASSWORD   = 6
MODE_CUTSCENE   = 7
MODE_ENDING     = 8
MODE_CREDITS    = 9
MODE_STAGECLEAR = 10
MODE_MAP        = 11

; ---------------------------------------------------------------- screen
; The HUD occupies nametable rows 0..3 (scanlines 0..31).  The playfield
; occupies rows 4..29 => 13 metatiles of 16px = 208 px tall.
PLAY_TOP        = 32            ; first playfield scanline
PLAY_ROWS       = 13            ; metatile rows in the playfield
LEVEL_HEIGHT_PX = 208
MAP_STRIDE      = 16            ; bytes per level column in ROM

; ---------------------------------------------------------------- collision
COL_EMPTY       = 0
COL_SOLID       = 1
COL_PLATFORM    = 2             ; one-way (top only)
COL_HAZARD      = 3             ; spikes / lava - damage on touch
COL_BREAK       = 4             ; breakable by stomp / steel toe
COL_WATER       = 5
COL_ICE         = 6
COL_MUD         = 7
COL_SWITCH      = 8             ; stomp switch
COL_DEATH       = 9             ; instant death (pit spikes, crusher)
COL_CLIMB       = 10            ; chain / vine (toe-grab)
COL_CONVEYOR_R  = 11
COL_CONVEYOR_L  = 12
COL_EXIT        = 13            ; stage exit trigger
COL_CHECKPOINT  = 14
COL_SECRET      = 15            ; looks solid, is passable

; ---------------------------------------------------------------- player
PSTATE_NORMAL   = 0
PSTATE_KICK     = 1
PSTATE_STOMP    = 2
PSTATE_AIRSTOMP = 3
PSTATE_HURT     = 4
PSTATE_DEAD     = 5
PSTATE_GRAB     = 6
PSTATE_LAND     = 7
PSTATE_SWIM     = 8
PSTATE_ENTER    = 9

; footwear
SHOE_BARE       = 0
SHOE_RUNNING    = 1
SHOE_STEEL      = 2
SHOE_COWBOY     = 3
SHOE_CLEAT      = 4
SHOE_FLIPPER    = 5
SHOE_SLIPPER    = 6
SHOE_BIG        = 7
NUM_SHOES       = 8

PLAYER_MAX_HP   = 12

; player hitbox (logical, smaller than the metasprite)
PBOX_W          = 20
PBOX_H          = 22

; ---------------------------------------------------------------- entities
MAX_ENTITIES    = 12
MAX_PARTICLES   = 6

; entity states
ES_FREE         = 0
ES_ACTIVE       = 1
ES_DYING        = 2
ES_HELD         = 3
ES_FLAT         = 4
ES_STUNNED      = 5

; entity flag bits
EF_FACELEFT     = $01
EF_GROUNDED     = $02
EF_KICKABLE     = $04           ; can be punted by a kick
EF_GRABBABLE    = $08           ; toe-grab target
EF_ARMORED      = $10           ; immune to frontal kicks
EF_HEAVY        = $20           ; immune to being flattened
EF_HARMLESS     = $40           ; does not hurt the player on contact
EF_PROJECTILE   = $80

; ---------------------------------------------------------------- sound
SFX_JUMP        = 0
SFX_LAND        = 1
SFX_STEP        = 2
SFX_KICK        = 3
SFX_HEAVYKICK   = 4
SFX_STOMP       = 5
SFX_MEGASTOMP   = 6
SFX_GRAB        = 7
SFX_THROW       = 8
SFX_HIT         = 9
SFX_SQUASH      = 10
SFX_BREAK       = 11
SFX_DEFLECT     = 12
SFX_PICKUP      = 13
SFX_SHOE        = 14
SFX_HURT        = 15
SFX_DIE         = 16
SFX_BOSSHIT     = 17
SFX_BOSSDIE     = 18
SFX_SELECT      = 19
SFX_PAUSE       = 20
SFX_SPLASH      = 21
SFX_ARROW       = 22

; songs
MUS_NONE        = $FF
MUS_TITLE       = 0
MUS_VILLAGE     = 1
MUS_FOREST      = 2
MUS_FORTRESS    = 3
MUS_SWAMP       = 4
MUS_FACTORY     = 5
MUS_CATHEDRAL   = 6
MUS_BATTLE      = 7
MUS_MOUNTAIN    = 8
MUS_BOSS        = 9
MUS_FINALBOSS   = 10
MUS_ENDING      = 11
MUS_GAMEOVER    = 12
MUS_CLEAR       = 13
MUS_INTRO       = 14
NUM_SONGS       = 15

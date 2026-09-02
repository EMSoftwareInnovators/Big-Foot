#!/usr/bin/env python3
"""Single source of truth for the BIG FOOT RAM map.

Emits src/ram.s (definitions) and src/ram.inc (declarations) so that every
translation unit sees exactly the same layout.  Also emits docs/ram_map.txt.

NES RAM budget:
    $0000-$00FF   zero page   (engine hot variables)
    $0100-$01FF   6502 stack
    $0200-$02FF   OAM shadow  (DMA source, must be page aligned)
    $0300-$07FF   BSS         (1280 bytes)
"""
import os

MAX_ENTITIES = 12
MAX_PARTICLES = 6

# (name, size)  -- zero page
ZP = [
    # scratch -------------------------------------------------------------
    ("tmp0", 1), ("tmp1", 1), ("tmp2", 1), ("tmp3", 1),
    ("tmp4", 1), ("tmp5", 1), ("tmp6", 1), ("tmp7", 1),
    ("tmp8", 1), ("tmp9", 1), ("tmpA", 1), ("tmpB", 1),
    ("tmpC", 1), ("tmpD", 1), ("tmpE", 1), ("tmpF", 1),
    # 16-bit pointers -----------------------------------------------------
    ("ptr0", 2), ("ptr1", 2), ("ptr2", 2), ("ptr3", 2),
    # engine --------------------------------------------------------------
    ("frame_count", 1),
    ("nmi_count", 1),
    ("nmi_ready", 1),          # 1 = NMI should do a full update
    ("ppu_ctrl", 1),
    ("ppu_mask", 1),
    ("render_on", 1),
    ("split_on", 1),           # 1 = perform the sprite-0 HUD split
    ("bank_8000", 1),
    ("bank_save", 1),
    ("bank_a000", 1),
    ("chr_bank_lo", 1),        # R0 : $0000 sprite bank (player)
    ("chr_bank_hi", 1),        # R1 : $0800 sprite bank (enemies)
    ("chr_bg0", 1),            # R2
    ("chr_bg1", 1),            # R3
    ("chr_bg2", 1),            # R4 (animated)
    ("chr_bg3", 1),            # R5 (HUD/font)
    ("chr_dirty", 1),
    ("vram_len", 1),
    ("oam_idx", 1),
    ("spr_x", 2),
    ("spr_y", 1),
    ("spr_attr", 1),
    ("spr_flip", 1),
    ("oam_hi", 1),             # high-water mark from previous frame
    ("rng_lo", 1), ("rng_hi", 1),
    ("pad1", 1), ("pad1_new", 1), ("pad1_prev", 1),
    ("pad2", 1), ("pad2_new", 1), ("pad2_prev", 1),
    # global game state ---------------------------------------------------
    ("game_mode", 1),
    ("mode_next", 1),
    ("mode_timer", 1),
    ("sub_state", 1),
    ("stage_num", 1),
    ("checkpoint", 1),
    ("lives", 1),
    ("continues", 1),
    ("progress_flags", 1),     # bit per unlocked footwear group
    ("shoe_flags", 1),         # bitmask of owned footwear
    ("pause_flag", 1),
    # camera --------------------------------------------------------------
    ("cam_x", 2),
    ("cam_x_max", 2),
    ("cam_y", 1),
    ("scroll_x", 1),
    ("scroll_nt", 1),
    ("shake_timer", 1),
    ("shake_amt", 1),
    ("cam_lock", 1),
    # level ---------------------------------------------------------------
    ("level_cols", 2),
    ("map_ptr", 2),
    ("col_next", 2),           # next column index to stream
    ("col_left", 2),
    ("stream_side", 1),
    ("theme", 1),
    ("spawn_cur", 1),
    ("cur_ent", 1),
    ("atk_x1", 2),
    ("atk_x2", 2),
    ("atk_y1", 1),
    ("atk_y2", 1),
    ("atk_dmg", 1),
    ("atk_kind", 1),
    ("enemy_chr", 1),
    ("boss_chr", 1),
    ("kick_type", 1),
    ("ent_tmp", 1),
    ("ent_tmp2", 1),
    ("spawn_ptr", 2),
    ("mt_ptr", 2),
    ("mt_tr", 2),
    ("mt_bl", 2),
    ("mt_br", 2),
    ("mt_at_p", 2),
    ("mt_fl_p", 2),
    ("col_base", 2),
    ("mtc_col", 2),
    ("mtc_row", 1),
    ("mtc_val", 1),
    ("ms_lo_ptr", 2),
    ("ms_hi_ptr", 2),
    ("bms_lo_ptr", 2),
    ("bms_hi_ptr", 2),
    ("hdr_ptr", 2),
    ("check_ptr", 2),
    ("roster_ptr", 2),
    ("boss_col", 2),
    ("stream_state", 1),
    ("stream_col", 2),
    ("dmg_count", 1),
    ("start_col", 2),
    ("start_row", 1),
    ("boss_id", 1),
    ("stage_shoe", 1),
    ("boss_music", 1),
    ("level_music", 1),
    ("anim_bank", 1),
    ("anim_timer", 1),
    # player --------------------------------------------------------------
    ("px", 2), ("px_sub", 1),
    ("py", 2), ("py_sub", 1),
    ("vx", 2), ("vy", 2),
    ("p_state", 1),
    ("p_anim", 1),
    ("p_frame", 1),
    ("p_atimer", 1),
    ("p_face", 1),
    ("p_ground", 1),
    ("p_wasground", 1),
    ("p_hp", 1),
    ("p_hp_max", 1),
    ("p_inv", 1),
    ("p_shoe", 1),
    ("p_coyote", 1),
    ("p_jumpbuf", 1),
    ("p_jumphold", 1),
    ("p_timer", 1),
    ("p_carry", 1),
    ("p_ground_type", 1),
    ("p_inwater", 1),
    ("p_stompcharge", 1),
    ("p_recoil", 1),
    ("p_walkdist", 1),
    ("p_flash", 1),
    ("p_curframe", 1),
    ("p_kickhit", 1),
    ("p_bounce", 1),
    ("p_shoetimer", 1),
    # boss ----------------------------------------------------------------
    ("boss_active", 1),
    ("boss_hp", 1),
    ("boss_maxhp", 1),
    ("boss_phase", 1),
    ("boss_timer", 1),
    ("boss_state", 1),
    ("boss_flash", 1),
    # audio ---------------------------------------------------------------
    ("mus_song", 1),
    ("mus_tick", 1),
    ("mus_speed", 1),
    ("sfx_req", 1),
    ("aud_tmp", 1),
    # hud -----------------------------------------------------------------
    ("hud_dirty", 1),
    ("score", 3),
]

BSS = [
    ("vram_buf", 176),
    ("oam_order", 8),
    # entity pool (structure of arrays) ----------------------------------
    ("e_type", MAX_ENTITIES),
    ("e_state", MAX_ENTITIES),
    ("e_xl", MAX_ENTITIES),
    ("e_xh", MAX_ENTITIES),
    ("e_xs", MAX_ENTITIES),
    ("e_yl", MAX_ENTITIES),
    ("e_yh", MAX_ENTITIES),
    ("e_ys", MAX_ENTITIES),
    ("e_vxl", MAX_ENTITIES),
    ("e_vxh", MAX_ENTITIES),
    ("e_vyl", MAX_ENTITIES),
    ("e_vyh", MAX_ENTITIES),
    ("e_hp", MAX_ENTITIES),
    ("e_tmr", MAX_ENTITIES),
    ("e_anim", MAX_ENTITIES),
    ("e_frm", MAX_ENTITIES),
    ("e_flags", MAX_ENTITIES),
    ("e_hurt", MAX_ENTITIES),
    ("e_sub", MAX_ENTITIES),
    ("e_slot", MAX_ENTITIES),   # spawn-list slot that produced this entity
    ("e_dir", MAX_ENTITIES),
    # particles -----------------------------------------------------------
    ("pa_type", MAX_PARTICLES),
    ("pa_xl", MAX_PARTICLES),
    ("pa_xh", MAX_PARTICLES),
    ("pa_y", MAX_PARTICLES),
    ("pa_vx", MAX_PARTICLES),
    ("pa_vy", MAX_PARTICLES),
    ("pa_tmr", MAX_PARTICLES),
    ("pa_frm", MAX_PARTICLES),
    # level bookkeeping ---------------------------------------------------
    ("spawn_used", 12),         # bitmap, 96 spawn slots per stage
    ("tile_dmg", 24),           # up to 8 broken tiles: col_lo, col_hi, row
    ("column_buf", 16),
    # text / dialogue ------------------------------------------------------
    ("text_ptr", 2),
    ("text_x", 1),
    ("text_y", 1),
    ("text_delay", 1),
    ("text_line", 1),
    ("password_buf", 8),
    ("pw_cursor", 1),
    # audio ---------------------------------------------------------------
    ("ch_ptr", 8),              # 4 channels x 2 bytes stream pointer
    ("ch_wait", 4),
    ("ch_note", 4),
    ("ch_instr", 4),
    ("ch_env", 4),
    ("ch_envpos", 4),
    ("ch_len", 4),
    ("ch_loop", 8),
    ("ch_vol", 4),
    ("ch_arp", 4),
    ("ch_detune", 4),
    ("ch_pattern", 4),
    ("ch_row", 4),
    ("ch_transpose", 4),
    ("sfx_ptr", 2),
    ("sfx_timer", 1),
    ("sfx_chan", 1),
    ("sfx_prio", 1),
    ("sfx_id", 1),
    ("mus_order", 1),
    ("mus_ptr", 2),
    ("mus_len", 1),
    # misc ----------------------------------------------------------------
    ("obj_state", 16),          # per-room switch / door state
    ("boss_x", 2),
    ("boss_y", 2),
    ("boss_vx", 2),
    ("boss_vy", 2),
    ("boss_frm", 1),
    ("boss_sub", 1),
    ("boss_atk", 1),
    ("boss_dir", 1),
    ("boss_anchor", 2),
    ("scratch", 32),
]


def emit(path_s, path_inc, path_doc):
    lines_s = [
        "; Generated by tools/gen_ram.py -- do not edit.\n",
        '.include "constants.inc"\n\n',
        '.segment "ZEROPAGE"\n',
    ]
    lines_i = [
        "; Generated by tools/gen_ram.py -- do not edit.\n",
        ".ifndef RAM_INC_\n",
        "RAM_INC_ = 1\n",
    ]
    doc = ["BIG FOOT -- RAM map (generated)\n", "\nZERO PAGE $0000-$00FF\n"]
    off = 0
    for name, size in ZP:
        lines_s.append(".exportzp %s\n%s: .res %d\n" % (name, name, size))
        lines_i.append(".globalzp %s\n" % name)
        doc.append("  $%02X  %-16s %d\n" % (off, name, size))
        off += size
    if off > 256:
        raise SystemExit("zero page overflow: %d bytes" % off)
    zp_used = off

    lines_s.append('\n.segment "OAM"\n.export oam_buf\noam_buf: .res 256\n')
    lines_i.append(".global oam_buf\n")

    lines_s.append('\n.segment "BSS"\n')
    doc.append("\nBSS $0300-$07FF\n")
    off = 0x300
    for name, size in BSS:
        lines_s.append(".export %s\n%s: .res %d\n" % (name, name, size))
        lines_i.append(".global %s\n" % name)
        doc.append("  $%03X  %-16s %d\n" % (off, name, size))
        off += size
    if off > 0x800:
        raise SystemExit("BSS overflow: ends at $%04X" % off)
    lines_i.append(".endif\n")
    doc.append("\nzero page used : %d / 256\n" % zp_used)
    doc.append("BSS used       : %d / 1280 (ends $%04X)\n" % (off - 0x300, off))

    open(path_s, "w").write("".join(lines_s))
    open(path_inc, "w").write("".join(lines_i))
    open(path_doc, "w").write("".join(doc))
    print("zero page: %d/256   BSS: %d/1280" % (zp_used, off - 0x300))


if __name__ == "__main__":
    root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
    os.makedirs(os.path.join(root, "docs"), exist_ok=True)
    emit(os.path.join(root, "src", "ram.s"),
         os.path.join(root, "src", "ram.inc"),
         os.path.join(root, "docs", "ram_map.txt"))

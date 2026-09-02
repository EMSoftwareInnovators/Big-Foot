/*
 * Minimal headless NES emulator used to smoke-test BIG FOOT during the build.
 *
 * Implements: 6502 (official opcodes + the common unofficial NOPs), a
 * dot-accurate PPU with the loopy v/t/x scroll model, sprite evaluation with
 * sprite-0 hit and overflow, MMC3 (PRG/CHR banking, scanline IRQ) and NROM,
 * standard controllers.  Audio registers are accepted and logged but not
 * synthesised.
 *
 * Usage:
 *   nesemu rom.nes [-frames N] [-shot FRAME:file.png]... [-input script]
 *                  [-log file] [-trace N]
 *
 * Input script lines:  FRAME BUTTONS      (buttons: A B SEL ST U D L R, or -)
 *                      FRAME-FRAME BUTTONS
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

typedef uint8_t u8;
typedef uint16_t u16;
typedef uint32_t u32;

/* ------------------------------------------------------------------ ROM */
static u8 *prg, *chrrom;
static int prg_size, chr_size, mapper, mirror4, chr_is_ram;
static u8 chrram[8192];

/* ------------------------------------------------------------------ MMC3 */
static u8 mmc3_bank[8], mmc3_sel, mmc3_mirror;
static u8 irq_latch, irq_counter, irq_enable, irq_reload, irq_pending;
static u8 prgram[8192];

static u8 *prg_ptr[4];      /* $8000,$A000,$C000,$E000 -> 8 KiB */
static int chr_bank1k[8];   /* $0000..$1C00 -> 1 KiB */

static void mmc3_sync(void)
{
    int nb = prg_size / 8192;
    int r6 = mmc3_bank[6] % nb, r7 = mmc3_bank[7] % nb;
    if (mmc3_sel & 0x40) {
        prg_ptr[0] = prg + (nb - 2) * 8192;
        prg_ptr[1] = prg + r7 * 8192;
        prg_ptr[2] = prg + r6 * 8192;
    } else {
        prg_ptr[0] = prg + r6 * 8192;
        prg_ptr[1] = prg + r7 * 8192;
        prg_ptr[2] = prg + (nb - 2) * 8192;
    }
    prg_ptr[3] = prg + (nb - 1) * 8192;

    int inv = (mmc3_sel & 0x80) ? 4 : 0;
    int nc = chr_is_ram ? 8 : chr_size / 1024;
    if (nc <= 0) nc = 8;
    chr_bank1k[(0 ^ inv)] = (mmc3_bank[0] & 0xFE) % nc;
    chr_bank1k[(1 ^ inv)] = ((mmc3_bank[0] & 0xFE) + 1) % nc;
    chr_bank1k[(2 ^ inv)] = (mmc3_bank[1] & 0xFE) % nc;
    chr_bank1k[(3 ^ inv)] = ((mmc3_bank[1] & 0xFE) + 1) % nc;
    chr_bank1k[(4 ^ inv) & 7] = mmc3_bank[2] % nc;
    chr_bank1k[(5 ^ inv) & 7] = mmc3_bank[3] % nc;
    chr_bank1k[(6 ^ inv) & 7] = mmc3_bank[4] % nc;
    chr_bank1k[(7 ^ inv) & 7] = mmc3_bank[5] % nc;
}

static u8 chr_read(u16 a)
{
    a &= 0x1FFF;
    if (chr_is_ram) return chrram[a];
    int b = chr_bank1k[a >> 10];
    return chrrom[b * 1024 + (a & 0x3FF)];
}
static void chr_write(u16 a, u8 v)
{
    if (chr_is_ram) chrram[a & 0x1FFF] = v;
}

/* ------------------------------------------------------------------ PPU */
static u8 vram[2048];
static u8 palram[32];
static u8 oam[256];
static u8 oam2[32];
static u8 ppuctrl, ppumask, ppustatus, oamaddr;
static u16 loopy_v, loopy_t;
static u8 loopy_x, loopy_w, ppu_buffer;
static int scanline, dot, frame_odd;
static u8 framebuf[240][256];      /* palette indices */
static long frame_count;

static u16 nt_mirror(u16 a)
{
    a &= 0x0FFF;
    int table = a >> 10;
    int off = a & 0x3FF;
    int phys;
    if (mirror4) phys = table;
    else if (mmc3_mirror & 1) phys = (table >> 1);        /* horizontal */
    else phys = (table & 1);                              /* vertical */
    return (phys & 1) * 0x400 + off;
}

static u8 ppu_read(u16 a)
{
    a &= 0x3FFF;
    if (a < 0x2000) return chr_read(a);
    if (a < 0x3F00) return vram[nt_mirror(a)];
    a &= 0x1F;
    if ((a & 0x13) == 0x10) a &= ~0x10;
    return palram[a];
}
static void ppu_write(u16 a, u8 v)
{
    a &= 0x3FFF;
    if (a < 0x2000) { chr_write(a, v); return; }
    if (a < 0x3F00) { vram[nt_mirror(a)] = v; return; }
    a &= 0x1F;
    if ((a & 0x13) == 0x10) a &= ~0x10;
    palram[a] = v & 0x3F;
}

/* background shift pipeline */
static u16 bg_lo, bg_hi, at_lo, at_hi;
static u8 nt_byte, at_byte, pt_lo, pt_hi;

/* sprite line buffer */
static u8 sp_pat_lo[8], sp_pat_hi[8], sp_attr[8], sp_x[8];
static int sp_count, sp_zero_in_line;

static int nmi_line;
static int cpu_nmi_pending, cpu_irq_line;

static void ppu_incx(void)
{
    if ((loopy_v & 0x001F) == 31) { loopy_v &= ~0x001F; loopy_v ^= 0x0400; }
    else loopy_v++;
}
static void ppu_incy(void)
{
    if ((loopy_v & 0x7000) != 0x7000) loopy_v += 0x1000;
    else {
        loopy_v &= ~0x7000;
        int y = (loopy_v & 0x03E0) >> 5;
        if (y == 29) { y = 0; loopy_v ^= 0x0800; }
        else if (y == 31) y = 0;
        else y++;
        loopy_v = (loopy_v & ~0x03E0) | (y << 5);
    }
}

static int rendering(void) { return (ppumask & 0x18) != 0; }

static void sprite_eval(int line)
{
    int h = (ppuctrl & 0x20) ? 16 : 8;
    sp_count = 0; sp_zero_in_line = 0;
    memset(oam2, 0xFF, 32);
    for (int i = 0; i < 64; i++) {
        int y = oam[i * 4];
        if (line >= y + 1 && line < y + 1 + h) {
            if (sp_count < 8) {
                memcpy(oam2 + sp_count * 4, oam + i * 4, 4);
                if (i == 0) sp_zero_in_line = 1;
                sp_count++;
            } else { ppustatus |= 0x20; break; }
        }
    }
    for (int i = 0; i < sp_count; i++) {
        int y = oam2[i * 4], tile = oam2[i * 4 + 1];
        int at = oam2[i * 4 + 2];
        sp_x[i] = oam2[i * 4 + 3];
        sp_attr[i] = at;
        int row = line - (y + 1);
        if (at & 0x80) row = h - 1 - row;
        u16 addr;
        if (h == 16) {
            addr = ((tile & 1) ? 0x1000 : 0x0000) + ((tile & 0xFE) << 4);
            if (row >= 8) { addr += 16; row -= 8; }
        } else {
            addr = ((ppuctrl & 0x08) ? 0x1000 : 0x0000) + (tile << 4);
        }
        sp_pat_lo[i] = chr_read(addr + row);
        sp_pat_hi[i] = chr_read(addr + row + 8);
    }
}

static void render_pixel(void)
{
    int x = dot - 1;
    int bgpix = 0, bgpal = 0;
    if ((ppumask & 0x08) && (x >= 8 || (ppumask & 0x02))) {
        int b = 15 - loopy_x;
        bgpix = ((bg_lo >> b) & 1) | (((bg_hi >> b) & 1) << 1);
        bgpal = ((at_lo >> b) & 1) | (((at_hi >> b) & 1) << 1);
    }
    int sppix = 0, sppal = 0, sppri = 0, spzero = 0;
    if ((ppumask & 0x10) && (x >= 8 || (ppumask & 0x04))) {
        for (int i = 0; i < sp_count; i++) {
            int dx = x - sp_x[i];
            if (dx < 0 || dx > 7) continue;
            int b = (sp_attr[i] & 0x40) ? dx : 7 - dx;
            int p = ((sp_pat_lo[i] >> b) & 1) | (((sp_pat_hi[i] >> b) & 1) << 1);
            if (!p) continue;
            sppix = p;
            sppal = (sp_attr[i] & 3) + 4;
            sppri = (sp_attr[i] >> 5) & 1;
            spzero = (i == 0 && sp_zero_in_line);
            break;
        }
    }
    int pal = 0;
    if (!bgpix && !sppix) pal = 0;
    else if (!bgpix) pal = sppal * 4 + sppix;
    else if (!sppix) pal = bgpal * 4 + bgpix;
    else {
        if (spzero && x < 255) ppustatus |= 0x40;
        pal = sppri ? (bgpal * 4 + bgpix) : (sppal * 4 + sppix);
    }
    int idx = pal & 0x1F;
    if ((idx & 0x13) == 0x10) idx &= ~0x10;
    if ((idx & 3) == 0) idx = 0;
    framebuf[scanline][x] = palram[idx] & 0x3F;
}

static void ppu_tick(void)
{
    int visible = (scanline < 240);
    int pre = (scanline == 261);

    if ((visible || pre) && rendering()) {
        if ((dot >= 1 && dot <= 256) || (dot >= 321 && dot <= 336)) {
            if (dot >= 1 && dot <= 256 && visible) render_pixel();
            bg_lo <<= 1; bg_hi <<= 1;
            at_lo <<= 1; at_hi <<= 1;
            switch (dot & 7) {
            case 1: nt_byte = ppu_read(0x2000 | (loopy_v & 0x0FFF)); break;
            case 3: {
                u16 a = 0x23C0 | (loopy_v & 0x0C00) | ((loopy_v >> 4) & 0x38)
                        | ((loopy_v >> 2) & 0x07);
                at_byte = ppu_read(a);
                int shift = ((loopy_v >> 4) & 4) | (loopy_v & 2);
                at_byte = (at_byte >> shift) & 3;
                break; }
            case 5: {
                u16 a = ((ppuctrl & 0x10) ? 0x1000 : 0) + (nt_byte << 4)
                        + ((loopy_v >> 12) & 7);
                pt_lo = chr_read(a); break; }
            case 7: {
                u16 a = ((ppuctrl & 0x10) ? 0x1000 : 0) + (nt_byte << 4)
                        + ((loopy_v >> 12) & 7) + 8;
                pt_hi = chr_read(a); break; }
            case 0:
                bg_lo = (bg_lo & 0xFF00) | pt_lo;
                bg_hi = (bg_hi & 0xFF00) | pt_hi;
                at_lo = (at_lo & 0xFF00) | ((at_byte & 1) ? 0xFF : 0x00);
                at_hi = (at_hi & 0xFF00) | ((at_byte & 2) ? 0xFF : 0x00);
                ppu_incx();
                break;
            }
        }
        if (dot == 256) ppu_incy();
        if (dot == 257) loopy_v = (loopy_v & ~0x041F) | (loopy_t & 0x041F);
        if (pre && dot >= 280 && dot <= 304)
            loopy_v = (loopy_v & ~0x7BE0) | (loopy_t & 0x7BE0);
        /* MMC3 scanline counter: driven by the A12 rise at dot 260 */
        if (dot == 260 && (visible || pre)) {
            if (irq_counter == 0 || irq_reload) { irq_counter = irq_latch; irq_reload = 0; }
            else irq_counter--;
            if (irq_counter == 0 && irq_enable) irq_pending = 1;
        }
    }
    if (visible && dot == 257) sprite_eval(scanline + 1 <= 239 ? scanline + 1 : 400);
    if (pre && dot == 257) sprite_eval(0);

    if (scanline == 241 && dot == 1) {
        ppustatus |= 0x80;
        if (ppuctrl & 0x80) cpu_nmi_pending = 1;
        frame_count++;
    }
    if (pre && dot == 1) ppustatus &= ~(0x80 | 0x40 | 0x20);

    dot++;
    if (dot > 340) {
        dot = 0;
        scanline++;
        if (scanline > 261) {
            scanline = 0;
            frame_odd ^= 1;
            if (frame_odd && rendering()) dot = 1;
        }
    }
    (void)nmi_line;
}

/* ------------------------------------------------------------------ CPU */
static u8 ram[2048];
static u8 A, X, Y, SP, P;
static u16 PC;
static long cpu_cycles;
static u8 pad_state[2], pad_shift[2], pad_strobe;
static u8 pad_buttons[2];

static u8 apu_regs[0x20];
static long stall_cycles;

static u8 cpu_read(u16 a);
static void cpu_write(u16 a, u8 v);

int logppu = 0; long logppu_frame = -1;
extern long total_cycles;
int workaddr = -1; long work_t0 = 0, work_sum = 0, work_n = 0, work_max = 0;
long work_maxframe = 0;
long work_hist[8];
static void ppu_reg_write(u16 a, u8 v)
{
    if (logppu && frame_count >= logppu_frame && frame_count < logppu_frame + 2
        && ((a & 7) == 5 || (a & 7) == 0 || (a & 7) == 6))
        printf("  reg $%04X=%02X at sl=%d dot=%d\n", 0x2000 + (a & 7), v, scanline, dot);
    switch (a & 7) {
    case 0:
        ppuctrl = v;
        loopy_t = (loopy_t & ~0x0C00) | ((v & 3) << 10);
        break;
    case 1: ppumask = v; break;
    case 3: oamaddr = v; break;
    case 4: oam[oamaddr++] = v; break;
    case 5:
        if (!loopy_w) { loopy_t = (loopy_t & ~0x001F) | (v >> 3); loopy_x = v & 7; loopy_w = 1; }
        else { loopy_t = (loopy_t & ~0x73E0) | ((v & 7) << 12) | ((v & 0xF8) << 2); loopy_w = 0; }
        break;
    case 6:
        if (!loopy_w) { loopy_t = (loopy_t & 0x00FF) | ((v & 0x3F) << 8); loopy_w = 1; }
        else { loopy_t = (loopy_t & 0xFF00) | v; loopy_v = loopy_t; loopy_w = 0; }
        break;
    case 7:
        ppu_write(loopy_v, v);
        loopy_v += (ppuctrl & 4) ? 32 : 1;
        break;
    }
}

static u8 ppu_reg_read(u16 a)
{
    u8 r = 0;
    switch (a & 7) {
    case 2: r = (ppustatus & 0xE0); ppustatus &= ~0x80; loopy_w = 0; break;
    case 4: r = oam[oamaddr]; break;
    case 7:
        if ((loopy_v & 0x3FFF) >= 0x3F00) { r = ppu_read(loopy_v); ppu_buffer = vram[nt_mirror(loopy_v)]; }
        else { r = ppu_buffer; ppu_buffer = ppu_read(loopy_v); }
        loopy_v += (ppuctrl & 4) ? 32 : 1;
        break;
    }
    return r;
}

static u8 cpu_read(u16 a)
{
    if (a < 0x2000) return ram[a & 0x7FF];
    if (a < 0x4000) return ppu_reg_read(a);
    if (a == 0x4015) return 0;
    if (a == 0x4016 || a == 0x4017) {
        int i = a & 1;
        u8 r = pad_shift[i] & 1;
        pad_shift[i] = (pad_shift[i] >> 1) | 0x80;
        return r | 0x40;
    }
    if (a < 0x4020) return 0;
    if (a < 0x6000) return 0;
    if (a < 0x8000) return prgram[a & 0x1FFF];
    return prg_ptr[(a >> 13) & 3][a & 0x1FFF];
}

static void cpu_write(u16 a, u8 v)
{
    if (a < 0x2000) {
        if ((int)(a & 0x7FF) == workaddr) {
            if (v == 0 && ram[a & 0x7FF] != 0) work_t0 = total_cycles;
            else if (v == 1 && ram[a & 0x7FF] == 0 && work_t0) {
                long d = total_cycles - work_t0;
                if (d < 200000) {
                    work_sum += d; work_n++;
                    if (d > work_max) { work_max = d; work_maxframe = frame_count; }
                    int b = (int)(d * 8 / 29781); if (b > 7) b = 7;
                    work_hist[b]++;
                }
            }
        }
        ram[a & 0x7FF] = v; return;
    }
    if (a < 0x4000) { ppu_reg_write(a, v); return; }
    if (a == 0x4014) {
        u16 base = v << 8;
        for (int i = 0; i < 256; i++) oam[(oamaddr + i) & 0xFF] = cpu_read(base + i);
        stall_cycles += 513;
        return;
    }
    if (a == 0x4016) {
        pad_strobe = v & 1;
        if (pad_strobe) { pad_shift[0] = pad_buttons[0]; pad_shift[1] = pad_buttons[1]; }
        return;
    }
    if (a < 0x4020) { apu_regs[a & 0x1F] = v; return; }
    if (a >= 0x6000 && a < 0x8000) { prgram[a & 0x1FFF] = v; return; }
    if (a >= 0x8000) {
        if (mapper == 4) {
            switch (a & 0xE001) {
            case 0x8000: mmc3_sel = v; mmc3_sync(); break;
            case 0x8001: mmc3_bank[mmc3_sel & 7] = v; mmc3_sync(); break;
            case 0xA000: mmc3_mirror = v; break;
            case 0xA001: break;
            case 0xC000: irq_latch = v; break;
            case 0xC001: irq_reload = 1; irq_counter = 0; break;
            case 0xE000: irq_enable = 0; irq_pending = 0; break;
            case 0xE001: irq_enable = 1; break;
            }
        } else if (mapper == 2) {
            mmc3_bank[6] = v * 2; mmc3_bank[7] = v * 2 + 1; mmc3_sync();
        }
    }
}

#define FC 0x01
#define FZ 0x02
#define FI 0x04
#define FD 0x08
#define FB 0x10
#define FU 0x20
#define FV 0x40
#define FN 0x80

static void setzn(u8 v) { P = (P & ~(FZ | FN)) | (v ? 0 : FZ) | (v & 0x80); }
static void push(u8 v) { ram[0x100 + SP] = v; SP--; }
static u8 pull(void) { SP++; return ram[0x100 + SP]; }

long total_cycles;
static int jam_flag;

static void tick(int n)
{
    for (int i = 0; i < n; i++) { ppu_tick(); ppu_tick(); ppu_tick(); total_cycles++; }
}

static u16 rd16(u16 a) { return cpu_read(a) | (cpu_read(a + 1) << 8); }
static u16 rd16z(u8 a) { return cpu_read(a) | (cpu_read((u8)(a + 1)) << 8); }

static int page_cross(u16 a, u16 b) { return (a & 0xFF00) != (b & 0xFF00); }

static void cpu_step(void)
{
    if (stall_cycles > 0) { tick(1); stall_cycles--; return; }
    if (cpu_nmi_pending) {
        cpu_nmi_pending = 0;
        push(PC >> 8); push(PC & 0xFF); push((P | FU) & ~FB);
        P |= FI; PC = rd16(0xFFFA); tick(7); return;
    }
    if (irq_pending && !(P & FI)) {
        push(PC >> 8); push(PC & 0xFF); push((P | FU) & ~FB);
        P |= FI; PC = rd16(0xFFFE); tick(7); return;
    }
    u8 op = cpu_read(PC++);
    u16 addr = 0; u8 v; int c = 2; int pc_extra = 0;

#define IMM()   (addr = PC++, c = 2)
#define ZP()    (addr = cpu_read(PC++), c = 3)
#define ZPX()   (addr = (u8)(cpu_read(PC++) + X), c = 4)
#define ZPY()   (addr = (u8)(cpu_read(PC++) + Y), c = 4)
#define ABS()   (addr = rd16(PC), PC += 2, c = 4)
#define ABSX(p) do { u16 b = rd16(PC); PC += 2; addr = b + X; \
                     c = 4 + ((p) && page_cross(b, addr)); } while (0)
#define ABSY(p) do { u16 b = rd16(PC); PC += 2; addr = b + Y; \
                     c = 4 + ((p) && page_cross(b, addr)); } while (0)
#define INDX()  do { u8 z = cpu_read(PC++) + X; addr = rd16z(z); c = 6; } while (0)
#define INDY(p) do { u8 z = cpu_read(PC++); u16 b = rd16z(z); addr = b + Y; \
                     c = 5 + ((p) && page_cross(b, addr)); } while (0)

    switch (op) {
    /* ---- load / store ---- */
    case 0xA9: IMM(); A = cpu_read(addr); setzn(A); break;
    case 0xA5: ZP();  A = cpu_read(addr); setzn(A); break;
    case 0xB5: ZPX(); A = cpu_read(addr); setzn(A); break;
    case 0xAD: ABS(); A = cpu_read(addr); setzn(A); break;
    case 0xBD: ABSX(1); A = cpu_read(addr); setzn(A); break;
    case 0xB9: ABSY(1); A = cpu_read(addr); setzn(A); break;
    case 0xA1: INDX(); A = cpu_read(addr); setzn(A); break;
    case 0xB1: INDY(1); A = cpu_read(addr); setzn(A); break;
    case 0xA2: IMM(); X = cpu_read(addr); setzn(X); break;
    case 0xA6: ZP();  X = cpu_read(addr); setzn(X); break;
    case 0xB6: ZPY(); X = cpu_read(addr); setzn(X); break;
    case 0xAE: ABS(); X = cpu_read(addr); setzn(X); break;
    case 0xBE: ABSY(1); X = cpu_read(addr); setzn(X); break;
    case 0xA0: IMM(); Y = cpu_read(addr); setzn(Y); break;
    case 0xA4: ZP();  Y = cpu_read(addr); setzn(Y); break;
    case 0xB4: ZPX(); Y = cpu_read(addr); setzn(Y); break;
    case 0xAC: ABS(); Y = cpu_read(addr); setzn(Y); break;
    case 0xBC: ABSX(1); Y = cpu_read(addr); setzn(Y); break;
    case 0x85: ZP();  cpu_write(addr, A); break;
    case 0x95: ZPX(); cpu_write(addr, A); break;
    case 0x8D: ABS(); cpu_write(addr, A); break;
    case 0x9D: ABSX(0); c = 5; cpu_write(addr, A); break;
    case 0x99: ABSY(0); c = 5; cpu_write(addr, A); break;
    case 0x81: INDX(); cpu_write(addr, A); break;
    case 0x91: INDY(0); c = 6; cpu_write(addr, A); break;
    case 0x86: ZP();  cpu_write(addr, X); break;
    case 0x96: ZPY(); cpu_write(addr, X); break;
    case 0x8E: ABS(); cpu_write(addr, X); break;
    case 0x84: ZP();  cpu_write(addr, Y); break;
    case 0x94: ZPX(); cpu_write(addr, Y); break;
    case 0x8C: ABS(); cpu_write(addr, Y); break;
    /* ---- transfers ---- */
    case 0xAA: X = A; setzn(X); break;
    case 0xA8: Y = A; setzn(Y); break;
    case 0x8A: A = X; setzn(A); break;
    case 0x98: A = Y; setzn(A); break;
    case 0xBA: X = SP; setzn(X); break;
    case 0x9A: SP = X; break;
    /* ---- stack ---- */
    case 0x48: push(A); c = 3; break;
    case 0x68: A = pull(); setzn(A); c = 4; break;
    case 0x08: push(P | FU | FB); c = 3; break;
    case 0x28: P = (pull() | FU) & ~FB; c = 4; break;
    /* ---- logic ---- */
    case 0x29: IMM(); A &= cpu_read(addr); setzn(A); break;
    case 0x25: ZP();  A &= cpu_read(addr); setzn(A); break;
    case 0x35: ZPX(); A &= cpu_read(addr); setzn(A); break;
    case 0x2D: ABS(); A &= cpu_read(addr); setzn(A); break;
    case 0x3D: ABSX(1); A &= cpu_read(addr); setzn(A); break;
    case 0x39: ABSY(1); A &= cpu_read(addr); setzn(A); break;
    case 0x21: INDX(); A &= cpu_read(addr); setzn(A); break;
    case 0x31: INDY(1); A &= cpu_read(addr); setzn(A); break;
    case 0x09: IMM(); A |= cpu_read(addr); setzn(A); break;
    case 0x05: ZP();  A |= cpu_read(addr); setzn(A); break;
    case 0x15: ZPX(); A |= cpu_read(addr); setzn(A); break;
    case 0x0D: ABS(); A |= cpu_read(addr); setzn(A); break;
    case 0x1D: ABSX(1); A |= cpu_read(addr); setzn(A); break;
    case 0x19: ABSY(1); A |= cpu_read(addr); setzn(A); break;
    case 0x01: INDX(); A |= cpu_read(addr); setzn(A); break;
    case 0x11: INDY(1); A |= cpu_read(addr); setzn(A); break;
    case 0x49: IMM(); A ^= cpu_read(addr); setzn(A); break;
    case 0x45: ZP();  A ^= cpu_read(addr); setzn(A); break;
    case 0x55: ZPX(); A ^= cpu_read(addr); setzn(A); break;
    case 0x4D: ABS(); A ^= cpu_read(addr); setzn(A); break;
    case 0x5D: ABSX(1); A ^= cpu_read(addr); setzn(A); break;
    case 0x59: ABSY(1); A ^= cpu_read(addr); setzn(A); break;
    case 0x41: INDX(); A ^= cpu_read(addr); setzn(A); break;
    case 0x51: INDY(1); A ^= cpu_read(addr); setzn(A); break;
    case 0x24: ZP(); v = cpu_read(addr);
        P = (P & ~(FZ | FV | FN)) | ((A & v) ? 0 : FZ) | (v & 0xC0); break;
    case 0x2C: ABS(); v = cpu_read(addr);
        P = (P & ~(FZ | FV | FN)) | ((A & v) ? 0 : FZ) | (v & 0xC0); break;
    /* ---- arithmetic ---- */
#define ADC(m) do { u8 mm = (m); u16 s = A + mm + (P & FC); \
        P = (P & ~(FC|FV)) | ((s > 0xFF) ? FC : 0) | \
            ((~(A ^ mm) & (A ^ s) & 0x80) ? FV : 0); A = (u8)s; setzn(A); } while (0)
#define SBC(m) ADC((u8)~(m))
    case 0x69: IMM(); ADC(cpu_read(addr)); break;
    case 0x65: ZP();  ADC(cpu_read(addr)); break;
    case 0x75: ZPX(); ADC(cpu_read(addr)); break;
    case 0x6D: ABS(); ADC(cpu_read(addr)); break;
    case 0x7D: ABSX(1); ADC(cpu_read(addr)); break;
    case 0x79: ABSY(1); ADC(cpu_read(addr)); break;
    case 0x61: INDX(); ADC(cpu_read(addr)); break;
    case 0x71: INDY(1); ADC(cpu_read(addr)); break;
    case 0xE9: case 0xEB: IMM(); SBC(cpu_read(addr)); break;
    case 0xE5: ZP();  SBC(cpu_read(addr)); break;
    case 0xF5: ZPX(); SBC(cpu_read(addr)); break;
    case 0xED: ABS(); SBC(cpu_read(addr)); break;
    case 0xFD: ABSX(1); SBC(cpu_read(addr)); break;
    case 0xF9: ABSY(1); SBC(cpu_read(addr)); break;
    case 0xE1: INDX(); SBC(cpu_read(addr)); break;
    case 0xF1: INDY(1); SBC(cpu_read(addr)); break;
#define CMPR(r,m) do { u8 mm = (m); u16 d = (u16)(r) - mm; \
        P = (P & ~FC) | (((r) >= mm) ? FC : 0); setzn((u8)d); } while (0)
    case 0xC9: IMM(); CMPR(A, cpu_read(addr)); break;
    case 0xC5: ZP();  CMPR(A, cpu_read(addr)); break;
    case 0xD5: ZPX(); CMPR(A, cpu_read(addr)); break;
    case 0xCD: ABS(); CMPR(A, cpu_read(addr)); break;
    case 0xDD: ABSX(1); CMPR(A, cpu_read(addr)); break;
    case 0xD9: ABSY(1); CMPR(A, cpu_read(addr)); break;
    case 0xC1: INDX(); CMPR(A, cpu_read(addr)); break;
    case 0xD1: INDY(1); CMPR(A, cpu_read(addr)); break;
    case 0xE0: IMM(); CMPR(X, cpu_read(addr)); break;
    case 0xE4: ZP();  CMPR(X, cpu_read(addr)); break;
    case 0xEC: ABS(); CMPR(X, cpu_read(addr)); break;
    case 0xC0: IMM(); CMPR(Y, cpu_read(addr)); break;
    case 0xC4: ZP();  CMPR(Y, cpu_read(addr)); break;
    case 0xCC: ABS(); CMPR(Y, cpu_read(addr)); break;
    /* ---- inc / dec ---- */
    case 0xE6: ZP(); c = 5; v = cpu_read(addr) + 1; cpu_write(addr, v); setzn(v); break;
    case 0xF6: ZPX(); c = 6; v = cpu_read(addr) + 1; cpu_write(addr, v); setzn(v); break;
    case 0xEE: ABS(); c = 6; v = cpu_read(addr) + 1; cpu_write(addr, v); setzn(v); break;
    case 0xFE: ABSX(0); c = 7; v = cpu_read(addr) + 1; cpu_write(addr, v); setzn(v); break;
    case 0xC6: ZP(); c = 5; v = cpu_read(addr) - 1; cpu_write(addr, v); setzn(v); break;
    case 0xD6: ZPX(); c = 6; v = cpu_read(addr) - 1; cpu_write(addr, v); setzn(v); break;
    case 0xCE: ABS(); c = 6; v = cpu_read(addr) - 1; cpu_write(addr, v); setzn(v); break;
    case 0xDE: ABSX(0); c = 7; v = cpu_read(addr) - 1; cpu_write(addr, v); setzn(v); break;
    case 0xE8: X++; setzn(X); break;
    case 0xC8: Y++; setzn(Y); break;
    case 0xCA: X--; setzn(X); break;
    case 0x88: Y--; setzn(Y); break;
    /* ---- shifts ---- */
    case 0x0A: P = (P & ~FC) | ((A >> 7) & 1); A <<= 1; setzn(A); break;
    case 0x06: ZP(); c = 5; goto asl_m;
    case 0x16: ZPX(); c = 6; goto asl_m;
    case 0x0E: ABS(); c = 6; goto asl_m;
    case 0x1E: ABSX(0); c = 7; goto asl_m;
    asl_m: v = cpu_read(addr); P = (P & ~FC) | ((v >> 7) & 1); v <<= 1;
           cpu_write(addr, v); setzn(v); break;
    case 0x4A: P = (P & ~FC) | (A & 1); A >>= 1; setzn(A); break;
    case 0x46: ZP(); c = 5; goto lsr_m;
    case 0x56: ZPX(); c = 6; goto lsr_m;
    case 0x4E: ABS(); c = 6; goto lsr_m;
    case 0x5E: ABSX(0); c = 7; goto lsr_m;
    lsr_m: v = cpu_read(addr); P = (P & ~FC) | (v & 1); v >>= 1;
           cpu_write(addr, v); setzn(v); break;
    case 0x2A: { u8 oc = P & FC; P = (P & ~FC) | ((A >> 7) & 1);
                 A = (A << 1) | oc; setzn(A); } break;
    case 0x26: ZP(); c = 5; goto rol_m;
    case 0x36: ZPX(); c = 6; goto rol_m;
    case 0x2E: ABS(); c = 6; goto rol_m;
    case 0x3E: ABSX(0); c = 7; goto rol_m;
    rol_m: { u8 oc = P & FC; v = cpu_read(addr); P = (P & ~FC) | ((v >> 7) & 1);
             v = (v << 1) | oc; cpu_write(addr, v); setzn(v); } break;
    case 0x6A: { u8 oc = (P & FC) << 7; P = (P & ~FC) | (A & 1);
                 A = (A >> 1) | oc; setzn(A); } break;
    case 0x66: ZP(); c = 5; goto ror_m;
    case 0x76: ZPX(); c = 6; goto ror_m;
    case 0x6E: ABS(); c = 6; goto ror_m;
    case 0x7E: ABSX(0); c = 7; goto ror_m;
    ror_m: { u8 oc = (P & FC) << 7; v = cpu_read(addr); P = (P & ~FC) | (v & 1);
             v = (v >> 1) | oc; cpu_write(addr, v); setzn(v); } break;
    /* ---- jumps / branches ---- */
    case 0x4C: PC = rd16(PC); c = 3; break;
    case 0x6C: { u16 p = rd16(PC);
                 u16 lo = cpu_read(p);
                 u16 hi = cpu_read((p & 0xFF00) | ((p + 1) & 0xFF));
                 PC = lo | (hi << 8); c = 5; } break;
    case 0x20: { u16 t = rd16(PC); PC++; push(PC >> 8); push(PC & 0xFF);
                 PC = t; c = 6; } break;
    case 0x60: PC = pull() | (pull() << 8); PC++; c = 6; break;
    case 0x40: P = (pull() | FU) & ~FB; PC = pull() | (pull() << 8); c = 6; break;
    case 0x00: PC++; push(PC >> 8); push(PC & 0xFF); push(P | FU | FB);
               P |= FI; PC = rd16(0xFFFE); c = 7; break;
#define BRANCH(cond) do { int8_t d = (int8_t)cpu_read(PC++); c = 2; \
        if (cond) { u16 np = PC + d; c += 1 + page_cross(PC, np); PC = np; } } while (0)
    case 0x10: BRANCH(!(P & FN)); break;
    case 0x30: BRANCH(P & FN); break;
    case 0x50: BRANCH(!(P & FV)); break;
    case 0x70: BRANCH(P & FV); break;
    case 0x90: BRANCH(!(P & FC)); break;
    case 0xB0: BRANCH(P & FC); break;
    case 0xD0: BRANCH(!(P & FZ)); break;
    case 0xF0: BRANCH(P & FZ); break;
    /* ---- flags ---- */
    case 0x18: P &= ~FC; break;
    case 0x38: P |= FC; break;
    case 0x58: P &= ~FI; break;
    case 0x78: P |= FI; break;
    case 0xB8: P &= ~FV; break;
    case 0xD8: P &= ~FD; break;
    case 0xF8: P |= FD; break;
    case 0xEA: break;
    /* ---- common unofficial NOPs ---- */
    case 0x1A: case 0x3A: case 0x5A: case 0x7A: case 0xDA: case 0xFA: break;
    case 0x80: case 0x82: case 0x89: case 0xC2: case 0xE2: PC++; break;
    case 0x04: case 0x44: case 0x64: PC++; c = 3; break;
    case 0x14: case 0x34: case 0x54: case 0x74: case 0xD4: case 0xF4: PC++; c = 4; break;
    case 0x0C: PC += 2; c = 4; break;
    case 0x1C: case 0x3C: case 0x5C: case 0x7C: case 0xDC: case 0xFC:
        ABSX(1); break;
    default:
        jam_flag = 1;
        fprintf(stderr, "JAM: unimplemented opcode $%02X at $%04X\n", op, PC - 1);
        break;
    }
    (void)pc_extra;
    tick(c);
}

/* ------------------------------------------------------------------ PNG */
static const u8 nes_rgb[64][3] = {
 {0x62,0x62,0x62},{0x00,0x1F,0xB2},{0x24,0x04,0xC8},{0x52,0x00,0xB2},
 {0x73,0x00,0x76},{0x80,0x00,0x24},{0x73,0x0B,0x00},{0x52,0x28,0x00},
 {0x24,0x44,0x00},{0x00,0x57,0x00},{0x00,0x5C,0x00},{0x00,0x53,0x24},
 {0x00,0x3C,0x76},{0x00,0x00,0x00},{0x00,0x00,0x00},{0x00,0x00,0x00},
 {0xAB,0xAB,0xAB},{0x0D,0x57,0xFF},{0x4B,0x30,0xFF},{0x8A,0x13,0xFF},
 {0xBC,0x08,0xD6},{0xD2,0x12,0x69},{0xC7,0x2E,0x00},{0x9D,0x54,0x00},
 {0x60,0x7B,0x00},{0x20,0x98,0x00},{0x00,0xA3,0x00},{0x00,0x99,0x42},
 {0x00,0x7D,0xB4},{0x00,0x00,0x00},{0x00,0x00,0x00},{0x00,0x00,0x00},
 {0xFF,0xFF,0xFF},{0x53,0xAE,0xFF},{0x90,0x85,0xFF},{0xD3,0x65,0xFF},
 {0xFF,0x57,0xFF},{0xFF,0x5D,0xCF},{0xFF,0x77,0x57},{0xFA,0x9E,0x00},
 {0xBD,0xC7,0x00},{0x7A,0xE7,0x00},{0x43,0xF6,0x11},{0x26,0xEF,0x7E},
 {0x2C,0xD5,0xF6},{0x4E,0x4E,0x4E},{0x00,0x00,0x00},{0x00,0x00,0x00},
 {0xFF,0xFF,0xFF},{0xB6,0xE1,0xFF},{0xCE,0xD1,0xFF},{0xE9,0xC3,0xFF},
 {0xFF,0xBC,0xFF},{0xFF,0xBD,0xF4},{0xFF,0xC6,0xC3},{0xFF,0xD5,0x9A},
 {0xE9,0xE6,0x81},{0xCE,0xF4,0x81},{0xB6,0xFB,0x9A},{0xA9,0xFA,0xC3},
 {0xA9,0xF0,0xF4},{0xB8,0xB8,0xB8},{0x00,0x00,0x00},{0x00,0x00,0x00},
};

static u32 crc_table[256];
static void crc_init(void)
{
    for (u32 n = 0; n < 256; n++) {
        u32 c = n;
        for (int k = 0; k < 8; k++) c = (c & 1) ? 0xEDB88320u ^ (c >> 1) : c >> 1;
        crc_table[n] = c;
    }
}
static u32 crc32b(const u8 *b, long n, u32 c)
{
    c ^= 0xFFFFFFFFu;
    for (long i = 0; i < n; i++) c = crc_table[(c ^ b[i]) & 0xFF] ^ (c >> 8);
    return c ^ 0xFFFFFFFFu;
}
static u32 adler32(const u8 *d, long n)
{
    u32 a = 1, b = 0;
    for (long i = 0; i < n; i++) { a = (a + d[i]) % 65521; b = (b + a) % 65521; }
    return (b << 16) | a;
}
static void put32(FILE *f, u32 v)
{
    fputc(v >> 24, f); fputc(v >> 16, f); fputc(v >> 8, f); fputc(v, f);
}
static void png_chunk(FILE *f, const char *tag, const u8 *data, long n)
{
    put32(f, (u32)n);
    u8 *buf = malloc(n + 4);
    memcpy(buf, tag, 4); memcpy(buf + 4, data, n);
    fwrite(buf, 1, n + 4, f);
    put32(f, crc32b(buf, n + 4, 0));
    free(buf);
}
static void save_png(const char *path, int scale)
{
    int W = 256 * scale, H = 240 * scale;
    long rawn = (long)H * (W * 3 + 1);
    u8 *raw = malloc(rawn);
    long p = 0;
    for (int y = 0; y < 240; y++)
        for (int s = 0; s < scale; s++) {
            raw[p++] = 0;
            for (int x = 0; x < 256; x++) {
                const u8 *c = nes_rgb[framebuf[y][x] & 0x3F];
                for (int t = 0; t < scale; t++) {
                    raw[p++] = c[0]; raw[p++] = c[1]; raw[p++] = c[2];
                }
            }
        }
    /* stored-mode zlib stream */
    long zn = 2 + rawn + ((rawn + 65534) / 65535) * 5 + 4;
    u8 *z = malloc(zn); long q = 0;
    z[q++] = 0x78; z[q++] = 0x01;
    long off = 0;
    while (off < rawn) {
        long blk = rawn - off; if (blk > 65535) blk = 65535;
        int last = (off + blk >= rawn);
        z[q++] = last;
        z[q++] = blk & 0xFF; z[q++] = (blk >> 8) & 0xFF;
        z[q++] = (~blk) & 0xFF; z[q++] = ((~blk) >> 8) & 0xFF;
        memcpy(z + q, raw + off, blk); q += blk; off += blk;
    }
    u32 ad = adler32(raw, rawn);
    z[q++] = ad >> 24; z[q++] = ad >> 16; z[q++] = ad >> 8; z[q++] = ad;

    FILE *f = fopen(path, "wb");
    if (!f) { free(raw); free(z); return; }
    static const u8 sig[8] = {0x89,'P','N','G','\r','\n',0x1A,'\n'};
    fwrite(sig, 1, 8, f);
    u8 ihdr[13];
    ihdr[0] = W >> 24; ihdr[1] = W >> 16; ihdr[2] = W >> 8; ihdr[3] = W;
    ihdr[4] = H >> 24; ihdr[5] = H >> 16; ihdr[6] = H >> 8; ihdr[7] = H;
    ihdr[8] = 8; ihdr[9] = 2; ihdr[10] = 0; ihdr[11] = 0; ihdr[12] = 0;
    png_chunk(f, "IHDR", ihdr, 13);
    png_chunk(f, "IDAT", z, q);
    png_chunk(f, "IEND", (const u8 *)"", 0);
    fclose(f);
    free(raw); free(z);
}

/* ------------------------------------------------------------------ main */
#define MAXSHOTS 64
static long shot_frame[MAXSHOTS];
static const char *shot_name[MAXSHOTS];
static int nshots;

#define MAXIN 512
static long in_from[MAXIN], in_to[MAXIN];
static u8 in_btn[MAXIN];
static int nin;

static u8 parse_buttons(char *s)
{
    u8 b = 0;
    for (char *t = strtok(s, ","); t; t = strtok(NULL, ",")) {
        /* the shift register clocks out A first, so A is bit 0 */
        if (!strcmp(t, "A")) b |= 0x01;
        else if (!strcmp(t, "B")) b |= 0x02;
        else if (!strcmp(t, "SEL")) b |= 0x04;
        else if (!strcmp(t, "ST")) b |= 0x08;
        else if (!strcmp(t, "U")) b |= 0x10;
        else if (!strcmp(t, "D")) b |= 0x20;
        else if (!strcmp(t, "L")) b |= 0x40;
        else if (!strcmp(t, "R")) b |= 0x80;
    }
    return b;
}

int main(int argc, char **argv)
{
    crc_init();
    if (argc < 2) { fprintf(stderr, "usage: nesemu rom.nes [opts]\n"); return 2; }
    long frames = 120; int scale = 1; const char *dumpram = NULL;
    const char *dumpvram = NULL; int watchn = 0; int watch[8]; long watchfrom = 0;
    int deltaaddr = -1; long deltalast = -1, deltamax = 0, deltasum = 0, deltan = 0;
    long deltahist[8]; memset(deltahist, 0, sizeof deltahist);
    static long hot[1024]; int hoton = 0; long hotfrom = 0, hotto = 1L<<40;
    int spin_lo = 0, spin_hi = 0; long spin_last = 0, worst = 0; long worst_pc = 0;
    long worst_at = 0; long gap_start_frame = 0, worst_frame = 0;
    int cntn = 0; int cntaddr[8]; long cnthit[8];
    memset(cnthit, 0, sizeof cnthit);
    int pfn = 0; int pfa[24], pfb[24]; long pfc[24]; char pfname[24][32];
    memset(pfc, 0, sizeof pfc);
    const char *rompath = argv[1];

    for (int i = 2; i < argc; i++) {
        if (!strcmp(argv[i], "-frames") && i + 1 < argc) frames = atol(argv[++i]);
        else if (!strcmp(argv[i], "-scale") && i + 1 < argc) scale = atoi(argv[++i]);
        else if (!strcmp(argv[i], "-dumpram") && i + 1 < argc) dumpram = argv[++i];
        else if (!strcmp(argv[i], "-dumpvram") && i + 1 < argc) dumpvram = argv[++i];
        else if (!strcmp(argv[i], "-watch") && i + 1 < argc) {
            if (watchn < 8) watch[watchn++] = (int)strtol(argv[++i], NULL, 0);
        }
        else if (!strcmp(argv[i], "-watchfrom") && i + 1 < argc) watchfrom = atol(argv[++i]);
        else if (!strcmp(argv[i], "-logppu") && i + 1 < argc) {
            extern int logppu; extern long logppu_frame;
            logppu = 1; logppu_frame = atol(argv[++i]);
        }
        else if (!strcmp(argv[i], "-prof") && i + 1 < argc && pfn < 24) {
            char *a = argv[++i];
            char *c1 = strchr(a, ':');
            char *c2 = c1 ? strchr(c1 + 1, ':') : NULL;
            if (c1 && c2) {
                *c1 = 0; *c2 = 0;
                pfa[pfn] = (int)strtol(a, NULL, 0);
                pfb[pfn] = (int)strtol(c1 + 1, NULL, 0);
                snprintf(pfname[pfn], 32, "%s", c2 + 1);
                pfn++;
            }
        }
        else if (!strcmp(argv[i], "-hot")) { hoton = 1; }
        else if (!strcmp(argv[i], "-hotrange") && i + 1 < argc) {
            char *a = argv[++i]; char *c = strchr(a, ':');
            hoton = 1;
            if (c) { *c = 0; hotfrom = atol(a); hotto = atol(c + 1); }
        }
        else if (!strcmp(argv[i], "-work") && i + 1 < argc) {
            extern int workaddr; workaddr = (int)strtol(argv[++i], NULL, 0);
        }
        else if (!strcmp(argv[i], "-spin") && i + 1 < argc) {
            char *a = argv[++i]; char *c = strchr(a, ':');
            if (c) { *c = 0; spin_lo = (int)strtol(a, NULL, 0);
                     spin_hi = (int)strtol(c + 1, NULL, 0); }
        }
        else if (!strcmp(argv[i], "-delta") && i + 1 < argc) {
            deltaaddr = (int)strtol(argv[++i], NULL, 0);
        }
        else if (!strcmp(argv[i], "-count") && i + 1 < argc) {
            if (cntn < 8) cntaddr[cntn++] = (int)strtol(argv[++i], NULL, 0);
        }
        else if (!strcmp(argv[i], "-shot") && i + 1 < argc) {
            char *a = argv[++i]; char *colon = strchr(a, ':');
            if (colon && nshots < MAXSHOTS) {
                *colon = 0;
                shot_frame[nshots] = atol(a);
                shot_name[nshots] = colon + 1;
                nshots++;
            }
        } else if (!strcmp(argv[i], "-input") && i + 1 < argc) {
            FILE *f = fopen(argv[++i], "r");
            if (f) {
                char line[256];
                while (fgets(line, sizeof line, f)) {
                    if (line[0] == '#' || line[0] == '\n') continue;
                    char range[64], btn[128];
                    if (sscanf(line, "%63s %127s", range, btn) != 2) continue;
                    long a2, b2; char *dash = strchr(range, '-');
                    if (dash) { *dash = 0; a2 = atol(range); b2 = atol(dash + 1); }
                    else { a2 = b2 = atol(range); }
                    if (nin < MAXIN) {
                        in_from[nin] = a2; in_to[nin] = b2;
                        in_btn[nin] = strcmp(btn, "-") ? parse_buttons(btn) : 0;
                        nin++;
                    }
                }
                fclose(f);
            }
        }
    }

    FILE *f = fopen(rompath, "rb");
    if (!f) { perror(rompath); return 2; }
    u8 hdr[16];
    if (fread(hdr, 1, 16, f) != 16 || memcmp(hdr, "NES\x1a", 4)) {
        fprintf(stderr, "not an iNES file\n"); return 2;
    }
    prg_size = hdr[4] * 16384;
    chr_size = hdr[5] * 8192;
    mapper = (hdr[6] >> 4) | (hdr[7] & 0xF0);
    mmc3_mirror = (hdr[6] & 1) ? 1 : 0;
    mirror4 = (hdr[6] & 8) ? 1 : 0;
    if (hdr[6] & 4) fseek(f, 512, SEEK_CUR);
    prg = malloc(prg_size);
    if (fread(prg, 1, prg_size, f) != (size_t)prg_size) {
        fprintf(stderr, "short PRG\n"); return 2;
    }
    if (chr_size) {
        chrrom = malloc(chr_size);
        if (fread(chrrom, 1, chr_size, f) != (size_t)chr_size) {
            fprintf(stderr, "short CHR\n"); return 2;
        }
    } else chr_is_ram = 1;
    fclose(f);

    memset(mmc3_bank, 0, sizeof mmc3_bank);
    mmc3_bank[6] = 0; mmc3_bank[7] = 1;
    mmc3_sel = 0;
    mmc3_sync();

    P = FU | FI; SP = 0xFD; A = X = Y = 0;
    PC = rd16(0xFFFC);
    scanline = 0; dot = 0;

    long last_frame = -1;
    long stuck = 0;
    u16 last_pc = 0xFFFF; long same_pc = 0;

    while (frame_count < frames && !jam_flag) {
        /* controller state for this frame */
        if (frame_count != last_frame) {
            last_frame = frame_count;
            if (watchn && frame_count >= watchfrom) {
                printf("f%-5ld", frame_count);
                for (int i = 0; i < watchn; i++)
                    printf(" [%04X]=%02X", watch[i], ram[watch[i] & 0x7FF]);
                printf("\n");
            }
            u8 b = 0;
            for (int i = 0; i < nin; i++)
                if (frame_count >= in_from[i] && frame_count <= in_to[i]) b |= in_btn[i];
            pad_buttons[0] = b;
            for (int i = 0; i < nshots; i++)
                if (shot_frame[i] == frame_count) {
                    /* the frame is drawn by the time we get here */
                }
        }
        u16 pc0 = PC;
        for (int i = 0; i < cntn; i++) if (pc0 == cntaddr[i]) cnthit[i]++;
        if (deltaaddr >= 0 && pc0 == deltaaddr) {
            if (deltalast >= 0) {
                long d = total_cycles - deltalast;
                if (d > deltamax) deltamax = d;
                deltasum += d; deltan++;
                int b = (int)(d / 29781); if (b > 7) b = 7;
                deltahist[b]++;
            }
            deltalast = total_cycles;
        }
        long c_before = total_cycles;
        cpu_step();
        if (hoton && pc0 >= 0xC000 && frame_count >= hotfrom && frame_count <= hotto)
            hot[(pc0 - 0xC000) >> 6] += total_cycles - c_before;
        if (spin_hi) {
            if (pc0 >= spin_lo && pc0 < spin_hi) {
                long gap = total_cycles - spin_last;
                if (gap > worst && frame_count > 100) { worst = gap; worst_pc = 0; worst_frame = gap_start_frame; }
                if (frame_count > 100 && gap > 200) { worst_at += gap; worst_pc++; }
                spin_last = total_cycles;
                gap_start_frame = frame_count;
            }
        }
        for (int i = 0; i < pfn; i++)
            if (pc0 >= pfa[i] && pc0 < pfb[i]) pfc[i] += total_cycles - c_before;
        if (PC == pc0) { if (++same_pc > 2000000) {
            fprintf(stderr, "HANG: stuck at $%04X\n", PC); jam_flag = 2; break; } }
        else same_pc = 0;
        last_pc = pc0;
        if (++stuck > 400000000L) { fprintf(stderr, "runaway\n"); break; }

        /* take screenshots right after vblank starts */
        for (int i = 0; i < nshots; i++)
            if (shot_frame[i] == frame_count && scanline == 241 && dot > 2) {
                save_png(shot_name[i], scale);
                shot_frame[i] = -1;
            }
    }
    for (int i = 0; i < nshots; i++)
        if (shot_frame[i] >= 0 && shot_frame[i] < frames + 2) save_png(shot_name[i], scale);

    if (dumpvram) {
        FILE *g = fopen(dumpvram, "wb");
        if (g) { fwrite(vram, 1, 2048, g); fwrite(palram, 1, 32, g); fclose(g); }
    }
    if (dumpram) {
        FILE *g = fopen(dumpram, "wb");
        if (g) { fwrite(ram, 1, 2048, g); fclose(g); }
    }
    if (hoton) {
        for (int k = 0; k < 20; k++) {
            int best = 0;
            for (int i = 1; i < 1024; i++) if (hot[i] > hot[best]) best = i;
            if (!hot[best]) break;
            printf("hot $%04X-$%04X  %8ld cycles (%.1f%%)\n",
                   0xC000 + (best << 6), 0xC000 + (best << 6) + 63, hot[best],
                   100.0 * hot[best] / total_cycles);
            hot[best] = 0;
        }
    }
    if (workaddr >= 0 && work_n) {
        printf("main-loop work: avg %ld max %ld (at frame %ld) over %ld frames\n",
               work_sum / work_n, work_max, work_maxframe, work_n);
        printf("  eighths of a frame:");
        for (int i = 0; i < 8; i++) printf(" %d:%ld", i + 1, work_hist[i]);
        printf("\n");
    }
    if (spin_hi) printf("work gap: worst %ld (%.2f frames), avg %ld over %d gaps\n",
                        worst, worst / 29781.0,
                        worst_pc ? worst_at / worst_pc : 0, worst_pc);
    if (deltaaddr >= 0 && deltan) {
        printf("delta $%04X: n=%ld avg=%ld max=%ld\n", deltaaddr, deltan,
               deltasum / deltan, deltamax);
        printf("  frames/iteration:");
        for (int i = 0; i < 8; i++) printf(" %d:%ld", i + 1, deltahist[i]);
        printf("\n");
    }
    for (int i = 0; i < pfn; i++)
        printf("prof %-20s %8ld cycles  (%.1f%% of %ld frames)\n", pfname[i], pfc[i],
               100.0 * pfc[i] / (frame_count * 29781.0), frame_count);
    for (int i = 0; i < cntn; i++)
        printf("count $%04X = %ld\n", cntaddr[i], cnthit[i]);
    printf("ppuctrl=%02X ppumask=%02X v=%04X t=%04X x=%d chr=[%d %d %d %d %d %d %d %d] prg=[%d %d]\n",
           ppuctrl, ppumask, loopy_v, loopy_t, loopy_x,
           chr_bank1k[0], chr_bank1k[1], chr_bank1k[2], chr_bank1k[3],
           chr_bank1k[4], chr_bank1k[5], chr_bank1k[6], chr_bank1k[7],
           (int)((prg_ptr[0]-prg)/8192), (int)((prg_ptr[1]-prg)/8192));
    {   int nz=0; for (int i=0;i<4096;i++) if (chr_read(0x1000+i)) nz++;
        printf("BG pattern non-zero bytes: %d\n", nz); }
    printf("frames=%ld cycles=%ld PC=$%04X A=%02X X=%02X Y=%02X SP=%02X P=%02X%s\n",
           frame_count, total_cycles, PC, A, X, Y, SP, P,
           jam_flag ? (jam_flag == 2 ? "  [HANG]" : "  [JAM]") : "");
    (void)last_pc;
    return jam_flag ? 1 : 0;
}

# ---------------------------------------------------------------------------
# BIG FOOT -- NES action platformer
#
#   make          build build/big_foot.nes
#   make clean    remove build products
#   make assets   regenerate graphics / levels / music only
#   make run      launch the ROM in an emulator if one is installed
#   make test     run the headless ROM smoke test
# ---------------------------------------------------------------------------

AS      := ca65
LD      := ld65
PYTHON  := python3

CFG     := cfg/big_foot.cfg
BUILD   := build
GEN     := data/generated
ROM     := $(BUILD)/big_foot.nes

ASFLAGS := -g -I src -I $(GEN) --cpu 6502
LDFLAGS := -C $(CFG) -m $(BUILD)/big_foot.map -Ln $(BUILD)/big_foot.labels

SRCS    := $(wildcard src/*.s)
GENSRCS := $(wildcard $(GEN)/*.s)
OBJS    := $(patsubst src/%.s,$(BUILD)/%.o,$(SRCS)) \
           $(patsubst $(GEN)/%.s,$(BUILD)/gen_%.o,$(GENSRCS))

.PHONY: all clean assets run test emu

all: assets
	@$(MAKE) --no-print-directory rom

rom: $(ROM)

assets:
	@$(PYTHON) tools/gen_cfg.py >/dev/null
	@$(PYTHON) tools/gen_ram.py
	@$(PYTHON) tools/build_assets.py

$(BUILD)/%.o: src/%.s | $(BUILD)
	@$(AS) $(ASFLAGS) -o $@ $<

$(BUILD)/gen_%.o: $(GEN)/%.s | $(BUILD)
	@$(AS) $(ASFLAGS) -o $@ $<

$(BUILD)/chr.o: src/chr.s $(GEN)/bigfoot.chr | $(BUILD)
	@$(AS) $(ASFLAGS) -o $@ $<

$(ROM): $(OBJS) $(CFG)
	@$(LD) $(LDFLAGS) -o $@ $(OBJS)
	@$(PYTHON) tools/romcheck.py $@

$(BUILD):
	@mkdir -p $(BUILD)

clean:
	rm -rf $(BUILD) $(GEN)

test: all
	@$(PYTHON) tools/nestest.py $(ROM)

run: all
	@if command -v mednafen >/dev/null 2>&1; then \
		mednafen $(ROM); \
	elif command -v fceux >/dev/null 2>&1; then \
		fceux $(ROM); \
	else \
		echo "no emulator installed; ROM is at $(ROM)"; \
	fi

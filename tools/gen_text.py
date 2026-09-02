#!/usr/bin/env python3
"""BIG FOOT -- every line of text, and the cutscene scripts that show them.

The kingdom reports the catastrophe the way an NES-era localisation would:
in capitals, in short declarative sentences, and entirely without irony.

Scripts are a tiny bytecode interpreted by src/script.s, one command per
frame until something asks to wait.
"""
from gen_font import CHARSET

# ---- bytecode (mirrored in src/constants.inc) -----------------------------
SC_END, SC_SCREEN, SC_BLANK, SC_TEXT, SC_TEXTAT = 0, 1, 2, 3, 4
SC_WAIT, SC_MUSIC, SC_SFX, SC_CLEAR, SC_PAUSE = 5, 6, 7, 8, 9
SC_MODE, SC_FADE, SC_SHAKE, SC_STEP = 10, 11, 12, 13

SCR_TITLE, SCR_INTRO, SCR_ENDING = 0, 1, 2

MODE_TITLE, MODE_STAGE_INTRO, MODE_CREDITS = 0, 2, 9


def encode(text):
    out = []
    for ch in text.upper():
        if ch not in CHARSET:
            raise SystemExit("no glyph for %r in %r" % (ch, text))
        out.append(CHARSET.index(ch))
    out.append(0xFF)
    return out


# ---------------------------------------------------------------------------
# the script assembler
# ---------------------------------------------------------------------------
class Script(object):
    def __init__(self, name):
        self.name = name
        self.ops = []
        self.strings = []

    def _str(self, text):
        self.strings.append(text)
        return text

    def screen(self, i):
        self.ops.append((SC_SCREEN, i))

    def blank(self):
        self.ops.append((SC_BLANK,))

    def text(self, row, s):
        self.ops.append((SC_TEXT, row, self._str(s)))

    def text_at(self, col, row, s):
        self.ops.append((SC_TEXTAT, col, row, self._str(s)))

    def wait(self, n):
        while n > 255:
            self.ops.append((SC_WAIT, 255))
            n -= 255
        self.ops.append((SC_WAIT, n))

    def music(self, i):
        self.ops.append((SC_MUSIC, i))

    def sfx(self, i):
        self.ops.append((SC_SFX, i))

    def clear(self, row, n=1):
        self.ops.append((SC_CLEAR, row, n))

    def pause(self):
        self.ops.append((SC_PAUSE,))

    def mode(self, m):
        self.ops.append((SC_MODE, m))

    def fade(self, level):
        self.ops.append((SC_FADE, level))

    def shake(self, n):
        self.ops.append((SC_SHAKE, n))

    def step(self):
        """One enormous footfall: shake, noise, and a beat of silence."""
        self.ops.append((SC_STEP,))

    def page(self, lines, row=None, hold=150):
        """Print a block of centred lines, hold, then wipe it."""
        base = row if row is not None else 22 - len(lines)
        for i, line in enumerate(lines):
            self.text(base + i * 2, line)
        self.wait(hold)
        self.pause()
        self.clear(base, len(lines) * 2)


# ---------------------------------------------------------------------------
# the scripts
# ---------------------------------------------------------------------------
def build_scripts():
    out = {}

    # ---- the opening report ----------------------------------------------
    s = Script("intro")
    s.screen(SCR_INTRO)
    s.music(14)                                     # MUS_INTRO
    s.page(["IN THE FIRST YEAR OF",
            "ALDRIC THE THIRD,",
            "THE KINGDOM KNEW PEACE."], row=21)
    s.page(["THEN CAME THE TREMORS."], row=23)
    s.step()
    s.page(["A SHAPE CROSSED THE MOON.",
            "IT HAD FIVE TOES."], row=22)
    s.page(["MY LORD -- IT IS A FOOT.",
            "A FOOT THE SIZE OF A HILL."], row=22)
    s.step()
    s.page(["THE GREAT HEEL HAS BREACHED",
            "THE EASTERN WALL!"], row=22)
    s.page(["SOUND EVERY BELL.",
            "IT IS COMING."], row=22)
    s.mode(MODE_STAGE_INTRO)
    out["intro"] = s

    # ---- between the stages ----------------------------------------------
    reports = [
        ["THE VILLAGE IS GONE.",
         "IT WALKS TOWARD THE FOREST."],
        ["THE ROYAL WOOD LIES FLAT.",
         "THE HUNTSMEN DID NOT RETURN."],
        ["STONEHEEL HAS FALLEN.",
         "THE GARRISON REPORTS",
         "ONE ENORMOUS ARCH."],
        ["IT CROSSED THE MARSH",
         "WITHOUT SINKING."],
        ["OUR WAR ENGINES ARE SCRAP.",
         "THE KING HAS SENT TO THE",
         "HOLY CITY FOR A BLESSING."],
        ["THE CATHEDRAL IS RUBBLE.",
         "THE PRIESTS SAY THE FOOT",
         "IS A JUDGEMENT."],
        ["THE LAST ARMY IS BROKEN.",
         "IT CLIMBS THE MOUNTAIN.",
         "SOMETHING WAITS UP THERE."],
    ]
    for i, lines in enumerate(reports):
        s = Script("cut%d" % i)
        s.blank()
        s.music(14)
        s.wait(40)
        s.page(lines, row=12, hold=200)
        s.mode(MODE_STAGE_INTRO)
        out["cut%d" % i] = s

    # ---- the ending -------------------------------------------------------
    s = Script("ending")
    s.blank()
    s.music(11)                                     # MUS_ENDING
    s.wait(60)
    s.page(["THE MOUNTAIN IS QUIET.",
            "THE LEFT FOOT IS STILL."], row=12, hold=200)
    s.screen(SCR_ENDING)
    s.page(["IN THE SQUARE BELOW,",
            "THEY RAISED A STATUE",
            "OF THE KING."], row=24, hold=200)
    s.page(["IT WAS MISSING",
            "ITS RIGHT FOOT."], row=25, hold=200)
    s.wait(90)
    s.sfx(13)                                       # SFX_PICKUP
    s.page(["THE STATUE IS WHOLE NOW."], row=26, hold=200)
    s.page(["THE STATUE'S EYES OPENED."], row=26, hold=200)
    s.step()
    s.page(["IT TOOK ONE STEP."], row=26, hold=200)
    s.mode(MODE_CREDITS)
    out["ending"] = s

    # ---- the credits ------------------------------------------------------
    s = Script("credits")
    s.blank()
    s.music(11)
    s.wait(40)
    s.text(4, "BIG FOOT")
    s.text(8, "GAME DESIGN")
    s.text(10, "PROGRAM")
    s.text(12, "GRAPHICS")
    s.text(14, "MUSIC")
    s.text(16, "SOUND EFFECTS")
    s.text(19, "THE FOOT")
    s.text(21, "PLAYED BY ITSELF")
    s.wait(255)
    s.wait(255)
    s.pause()
    s.blank()
    s.wait(60)
    s.text(12, "BIG FOOT WILL RETURN")
    s.wait(255)
    s.pause()
    s.clear(12, 1)
    s.wait(60)
    s.text(12, "IN")
    s.wait(120)
    s.text(15, "BIG HAND")
    s.wait(255)
    s.wait(255)
    s.pause()
    s.mode(MODE_TITLE)
    out["credits"] = s
    return out


SCRIPT_ORDER = (["intro"] + ["cut%d" % i for i in range(7)] +
                ["ending", "credits"])
SCRIPT_IDS = {
    "intro": "SCRIPT_INTRO",
    "ending": "SCRIPT_ENDING",
    "credits": "SCRIPT_CREDITS",
}

# ---------------------------------------------------------------------------
# standalone strings used by the menus
# ---------------------------------------------------------------------------
MENU_STRINGS = [
    ("txt_pressstart", "PRESS START"),
    ("txt_pw", "PASSWORD"),
    ("txt_pwenter", "ENTER PASSWORD"),
    ("txt_pwbad", "THAT IS NOT A PASSWORD"),
    ("txt_pwyours", "YOUR PASSWORD"),
    ("txt_pwhow", "SELECT CHANGES  START ACCEPTS"),
    ("txt_paused", "PAUSED"),
    ("txt_getshoe", "YOU MAY NOW WEAR"),
]


# ---------------------------------------------------------------------------
def build(write):
    asm = ["; Generated by tools/gen_text.py -- do not edit.\n",
           '.include "constants.inc"\n\n',
           ".export script_lo, script_hi\n",
           ".export " + ", ".join(n for n, _ in MENU_STRINGS) + "\n\n"]
    inc = ["; Generated by tools/gen_text.py -- do not edit.\n"]

    scripts = build_scripts()
    pool = {}
    pool_order = []

    def slabel(text):
        if text not in pool:
            pool[text] = "tx_%d" % len(pool)
            pool_order.append(text)
        return pool[text]

    body = ['.segment "B03"\n']
    for i, name in enumerate(SCRIPT_ORDER):
        s = scripts[name]
        body.append("script_%s:\n" % name)
        for op in s.ops:
            k = op[0]
            if k == SC_TEXT:
                body.append("        .byte %d,%d\n        .word %s\n"
                            % (k, op[1], slabel(op[2])))
            elif k == SC_TEXTAT:
                body.append("        .byte %d,%d,%d\n        .word %s\n"
                            % (k, op[1], op[2], slabel(op[3])))
            else:
                body.append("        .byte " +
                            ",".join(str(v) for v in op) + "\n")
        body.append("        .byte %d\n" % SC_END)
        if name in SCRIPT_IDS:
            inc.append("%s = %d\n" % (SCRIPT_IDS[name], i))
    inc.append("SCRIPT_CUT0 = 1\n")
    inc.append("NUM_SCRIPTS = %d\n" % len(SCRIPT_ORDER))

    for text in pool_order:
        body.append("%s:\n        .byte %s\n"
                    % (pool[text], ",".join(str(b) for b in encode(text))))

    asm.append('.segment "RODATA2"\n')
    asm.append("script_lo:\n        .byte " +
               ",".join("<script_%s" % n for n in SCRIPT_ORDER) + "\n")
    asm.append("script_hi:\n        .byte " +
               ",".join(">script_%s" % n for n in SCRIPT_ORDER) + "\n")
    for name, text in MENU_STRINGS:
        asm.append("%s:\n        .byte %s\n"
                   % (name, ",".join(str(b) for b in encode(text))))
    asm.append("\n")
    asm.extend(body)

    size = sum(len(l.split(".byte ")[-1].split(",")) for l in body
               if ".byte" in l)
    write("text_data.s", "".join(asm))
    write("text.inc", "".join(inc))
    return ("text: %d scripts, %d strings, about %d bytes in bank 3\n"
            % (len(SCRIPT_ORDER), len(pool), size))


if __name__ == "__main__":
    import os

    OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "..", "data", "generated")

    def w(name, text):
        open(os.path.join(OUT, name), "w").write(text)
        return len(text)

    print(build(w))

#!/usr/bin/env python3
"""Generate an emulator input script that types a password.

Reaching stage six to look at its boss meant skipping five stages with the
debug key and hoping the timing held.  Typing the password instead is exact,
and it exercises the password screen at the same time.
"""
import sys


def password(stage, lives=3, shoes=1):
    """Mirror of pw_encode in src/password.s -> six nibbles."""
    b0 = (((lives - 1) & 7) << 3) | (stage & 7)
    b1 = shoes & 0xFF
    b2 = (b1 * 3 + b0 + 0x5A) & 0xFF
    n = [b0 >> 4, b0 & 15, b1 >> 4, b1 & 15, b2 >> 4, b2 & 15]
    return [(v + i * 4) & 15 for i, v in enumerate(n)]


ALPHA = "BDFGHJKLMNPRSTVZ"


def script(stage, path, tail=None, start=100):
    """Title -> PASSWORD -> type it -> START.  Returns the frame play begins."""
    ls = []
    f = start
    ls.append('%d D' % f)                       # move the cursor to PASSWORD
    f += 10
    ls.append('%d ST' % f)                      # enter the password screen
    f += 20
    for i, nib in enumerate(password(stage)):
        for _ in range(nib):
            ls.append('%d U' % f)
            f += 6
        if i < 5:
            ls.append('%d R' % f)
            f += 8
    f += 10
    ls.append('%d ST' % f)                      # accept
    # The stage intro times out on its own after 120 frames.  Pressing START
    # to hurry it along overshoots into play, where START is the pause key.
    f += 170
    if tail:
        ls += tail(f)
    open(path, 'w').write('\n'.join(ls) + '\n')
    return f


if __name__ == "__main__":
    for s in range(8):
        print("stage %d: %s" % (s + 1,
              "".join(ALPHA[n] for n in password(s))))

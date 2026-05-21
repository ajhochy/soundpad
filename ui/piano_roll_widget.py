"""
piano_roll_widget.py — falling notes visualiser and 49-key piano display.

Key layout algorithm ported from Neothesia piano-layout/src/lib.rs (MIT).
Repository: https://github.com/PolyMeilex/Neothesia

The widget is a custom QWidget drawn entirely with QPainter.
No external rendering libraries.

Piano range: C2–C6 (MIDI 36–84), 49 keys — matches Novation Launchkey MK3 49.
"""

from PyQt5.QtWidgets import QWidget
from PyQt5.QtGui import QPainter, QColor, QPen
from PyQt5.QtCore import Qt


# ---------------------------------------------------------------------------
# Piano key layout — Neothesia algorithm (pure, no Qt)
# ---------------------------------------------------------------------------

#: MIDI note numbers of white keys within an octave (semitone offsets from C)
_WHITE_SEMITONES = frozenset({0, 2, 4, 5, 7, 9, 11})

#: First and last MIDI notes of the 49-key range
FIRST_NOTE = 36  # C2
LAST_NOTE = 84   # C6


def compute_key_layout(widget_width, piano_height):
    """
    Compute pixel positions and sizes for all 49 piano keys (C2–C6).

    Returns a dict mapping MIDI note number → key descriptor:
        {
            'x': float,       # left edge in pixels (from widget left)
            'w': float,       # width in pixels
            'h': float,       # height in pixels
            'is_black': bool  # True for black keys
        }

    Algorithm ported verbatim from Neothesia piano-layout/src/lib.rs:
      - White keys: evenly spaced (white_w = total_width / 29)
      - Black keys: two groups per octave
          CDE group  (C#, D#):     block = 3×white_w / 5
          FGAB group (F#, G#, A#): block = 4×white_w / 7
        Each black key is centred on its block index (1, 3 or 1, 3, 5).
      - Black key size: 62.5% width, 63.5% height of white key.
    """
    white_count = sum(
        1 for n in range(FIRST_NOTE, LAST_NOTE + 1) if n % 12 in _WHITE_SEMITONES
    )

    white_w = widget_width / white_count
    white_h = float(piano_height)
    black_w = white_w * 0.625
    black_h = white_h * 0.635

    layout = {}
    white_x = 0.0
    octave_c_x = {}  # octave index -> x of C key

    # First pass: place white keys and record where each C lands
    for note in range(FIRST_NOTE, LAST_NOTE + 1):
        semitone = note % 12
        if semitone in _WHITE_SEMITONES:
            layout[note] = {'x': white_x, 'w': white_w, 'h': white_h, 'is_black': False}
            if semitone == 0:
                octave_c_x[note // 12] = white_x
            white_x += white_w

    # Second pass: place black keys using the Neothesia two-group algorithm
    for note in range(FIRST_NOTE, LAST_NOTE + 1):
        semitone = note % 12
        if semitone not in (1, 3, 6, 8, 10):
            continue

        octave = note // 12
        c_x = octave_c_x.get(octave, 0.0)
        f_x = c_x + 3 * white_w   # F is the 4th white key of the octave

        cde_block = 3 * white_w / 5
        fgab_block = 4 * white_w / 7

        if semitone == 1:    # C# — CDE block 1
            x = c_x + 1 * cde_block - black_w / 2
        elif semitone == 3:  # D# — CDE block 3
            x = c_x + 3 * cde_block - black_w / 2
        elif semitone == 6:  # F# — FGAB block 1
            x = f_x + 1 * fgab_block - black_w / 2
        elif semitone == 8:  # G# — FGAB block 3
            x = f_x + 3 * fgab_block - black_w / 2
        else:                # A# (semitone 10) — FGAB block 5
            x = f_x + 5 * fgab_block - black_w / 2

        layout[note] = {'x': x, 'w': black_w, 'h': black_h, 'is_black': True}

    return layout

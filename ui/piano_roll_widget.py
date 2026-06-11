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


# ---------------------------------------------------------------------------
# PianoRollWidget — the full Qt widget
# ---------------------------------------------------------------------------

#: Colour constants for key states
_COLOUR_BG = QColor("#0a0a14")
_COLOUR_WHITE_KEY = QColor("#e8e8e8")
_COLOUR_BLACK_KEY = QColor("#1a1a1a")
_COLOUR_KEY_BORDER = QColor("#333333")
_COLOUR_HIT_LINE = QColor("#ffffff")
_COLOUR_NOTE_DEFAULT = QColor("#00bcd4")   # cyan — free mode playback

#: How much vertical height the piano keys occupy (fraction of total widget height)
_PIANO_HEIGHT_FRACTION = 0.20

#: Lookahead window in microseconds (3 s — must match MidiFilePlayer.LOOKAHEAD_US)
_LOOKAHEAD_US = 3_000_000


class PianoRollWidget(QWidget):
    """
    Falling-notes piano roll visualiser.

    Renders:
      1. Black background
      2. Falling note bars (upcoming notes scrolling down toward the hit line)
      3. Hit line (white horizontal rule at the top of the piano)
      4. White piano keys (bottom 20% of widget)
      5. Black piano keys (on top of white keys)
      6. Lit key overlays (colour-coded: cyan / green / amber / red)

    Update cycle:
      PracticeWindow calls set_state() every ~16ms (60fps) with the current
      playback clock and upcoming note list. set_state() triggers a repaint.

    Key colour meanings:
      Cyan   (#00bcd4) — currently playing (free mode)
      Green  (#00e676) — correctly hit (waiting mode)
      Amber  (#ffa726) — waiting for input (waiting mode)
      Red    (#ef5350) — wrong note pressed (200ms flash)
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._layout = {}
        self._clock_us = 0
        self._upcoming_notes = []
        self._lit_keys = {}  # note -> QColor override
        self.setMinimumSize(600, 200)
        self._recompute_layout()

    def set_state(self, clock_us, upcoming_notes, lit_keys):
        """
        Update display state and schedule a repaint.

        Args:
            clock_us:       current playback position in microseconds
            upcoming_notes: list of (timestamp_us, note, velocity, duration_us)
                            for notes within the lookahead window
            lit_keys:       {midi_note: QColor} overrides for key colours
        """
        self._clock_us = clock_us
        self._upcoming_notes = upcoming_notes
        self._lit_keys = lit_keys
        self.update()

    # ------------------------------------------------------------------
    # Qt event overrides
    # ------------------------------------------------------------------

    def resizeEvent(self, event):
        self._recompute_layout()
        super().resizeEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)  # pixel-sharp edges

        w = self.width()
        h = self.height()
        piano_h = max(60, int(h * _PIANO_HEIGHT_FRACTION))
        roll_h = h - piano_h
        hit_line_y = roll_h

        # 1. Black background
        painter.fillRect(0, 0, w, h, _COLOUR_BG)

        # 2. Falling note bars
        if self._upcoming_notes and self._layout:
            us_per_pixel = _LOOKAHEAD_US / roll_h if roll_h > 0 else 1
            for ts_us, note, vel, dur_us in self._upcoming_notes:
                key = self._layout.get(note)
                if key is None:
                    continue
                bar_top = int((ts_us - self._clock_us) / us_per_pixel)
                bar_h = max(4, int(dur_us / us_per_pixel))
                colour = self._lit_keys.get(note, _COLOUR_NOTE_DEFAULT)
                painter.fillRect(
                    int(key['x']), bar_top,
                    max(1, int(key['w']) - 1), bar_h,
                    colour,
                )

        # 3. Hit line
        painter.setPen(QPen(_COLOUR_HIT_LINE, 2))
        painter.drawLine(0, hit_line_y, w, hit_line_y)

        # 4. White piano keys (bottom section)
        piano_y = hit_line_y + 1
        for note, key in self._layout.items():
            if key['is_black']:
                continue
            colour = self._lit_keys.get(note, _COLOUR_WHITE_KEY)
            x, kw, kh = int(key['x']), max(1, int(key['w']) - 1), int(key['h'])
            painter.fillRect(x, piano_y, kw, kh, colour)
            painter.setPen(QPen(_COLOUR_KEY_BORDER, 1))
            painter.drawRect(x, piano_y, kw, kh)

        # 5. Black piano keys (drawn on top of white keys)
        for note, key in self._layout.items():
            if not key['is_black']:
                continue
            colour = self._lit_keys.get(note, _COLOUR_BLACK_KEY)
            x, kw, kh = int(key['x']), max(1, int(key['w'])), int(key['h'])
            painter.fillRect(x, piano_y, kw, kh, colour)

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _recompute_layout(self):
        if self.width() > 0 and self.height() > 0:
            piano_h = max(60, int(self.height() * _PIANO_HEIGHT_FRACTION))
            self._layout = compute_key_layout(self.width(), piano_h)

"""
note_matcher.py — waiting-mode note matching logic.

Ported from Linthesia src/PlayingState.cpp (GPL-2.0).
Specifically: areAllRequiredKeysPressed() and the NOTE_WINDOW_LENGTH constant.

Usage:
    from core.note_matcher import MatchResult, check, all_required_pressed

    result = check(pressed_note, required_notes)
    if result == MatchResult.HIT:
        required_notes.discard(pressed_note)
        if all_required_pressed(pressed_notes, required_notes):
            resume_clock()
"""

from enum import Enum


NOTE_WINDOW_LENGTH_MS = 400  # Linthesia: NoteWindowLength constant (ms)


class MatchResult(Enum):
    HIT = "hit"      # pressed note is in the required set
    MISS = "miss"    # required notes exist but pressed note is not one of them
    NOT_YET = "not_yet"  # no notes currently required (clock not paused)


def check(pressed_note, required_notes):
    """
    Compare a single pressed MIDI note against the set of currently required notes.

    Args:
        pressed_note: MIDI note number (0-127)
        required_notes: set of MIDI notes the player must press before clock resumes

    Returns:
        HIT     — pressed_note is in required_notes
        MISS    — required_notes is non-empty but pressed_note is not in it
        NOT_YET — required_notes is empty (nothing currently required)
    """
    if not required_notes:
        return MatchResult.NOT_YET
    if pressed_note in required_notes:
        return MatchResult.HIT
    return MatchResult.MISS


def all_required_pressed(pressed_notes, required_notes):
    """
    Return True when every note in required_notes has been pressed.
    Ported from Linthesia areAllRequiredKeysPressed().

    Args:
        pressed_notes: all MIDI notes currently held down
        required_notes: notes that must all be pressed to resume

    Returns:
        True if required_notes is a subset of pressed_notes (or required_notes is empty)
    """
    return required_notes.issubset(pressed_notes)

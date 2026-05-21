"""Tests for key_pressed / key_released signals in core/midi_handler.py.

These tests exercise the signal definitions on MidiSignals and the
event routing in MidiHandler._on_midi_message without opening a real
rtmidi port.
"""
import pytest
from unittest.mock import MagicMock
from core.midi_handler import MidiSignals, MidiHandler


# ---------------------------------------------------------------------------
# Signal definition tests
# ---------------------------------------------------------------------------

def test_midi_signals_has_key_pressed():
    sigs = MidiSignals()
    assert hasattr(sigs, 'key_pressed')


def test_midi_signals_has_key_released():
    sigs = MidiSignals()
    assert hasattr(sigs, 'key_released')


def test_key_pressed_signature(qtbot):
    """key_pressed must emit two ints: note and velocity."""
    sigs = MidiSignals()
    received = []
    sigs.key_pressed.connect(lambda n, v: received.append((n, v)))
    sigs.key_pressed.emit(60, 80)
    assert received == [(60, 80)]


def test_key_released_signature(qtbot):
    """key_released must emit one int: note."""
    sigs = MidiSignals()
    received = []
    sigs.key_released.connect(lambda n: received.append(n))
    sigs.key_released.emit(60)
    assert received == [60]


# ---------------------------------------------------------------------------
# Routing tests — feed bytes directly to _on_midi_message
# ---------------------------------------------------------------------------

def _make_handler():
    config = MagicMock()
    config.midi_map = {
        "pads": [{"channel": 9, "note": 36, "pad": 1}],
        "knobs": [{"channel": 0, "cc": 21, "pad": 1}],
        "master_fader": {"channel": 0, "cc": 9},
    }
    return MidiHandler(config)


def test_key_pressed_emitted_for_piano_note_on(qtbot):
    h = _make_handler()
    received = []
    h.signals.key_pressed.connect(lambda n, v: received.append((n, v)))
    # Note-on on channel 0 (not a pad — pad is channel 9 note 36)
    h._on_midi_message(([0x90, 60, 80], None))
    assert received == [(60, 80)]


def test_key_released_emitted_for_note_off(qtbot):
    h = _make_handler()
    received = []
    h.signals.key_released.connect(lambda n: received.append(n))
    h._on_midi_message(([0x80, 60, 0], None))
    assert received == [60]


def test_key_released_emitted_for_note_on_velocity_zero(qtbot):
    h = _make_handler()
    received = []
    h.signals.key_released.connect(lambda n: received.append(n))
    h._on_midi_message(([0x90, 60, 0], None))
    assert received == [60]


def test_channel_9_does_not_emit_key_pressed(qtbot):
    """Percussion channel must be filtered out."""
    h = _make_handler()
    received = []
    h.signals.key_pressed.connect(lambda n, v: received.append((n, v)))
    # Note-on on channel 9 (percussion) — not a configured pad (note 36 is)
    h._on_midi_message(([0x99, 40, 80], None))  # 0x99 = note-on channel 9
    assert received == []


def test_existing_pad_toggle_still_works(qtbot):
    """No regression: configured pad note-on still emits pad_toggled."""
    h = _make_handler()
    received = []
    h.signals.pad_toggled.connect(lambda idx: received.append(idx))
    h.signals.key_pressed.connect(lambda n, v: pytest.fail("should not emit key_pressed for pad"))
    # Pad is channel 9 note 36 -> status 0x99
    h._on_midi_message(([0x99, 36, 100], None))
    assert received == [0]   # pad index 0 (pad 1 in 1-indexed)


def test_existing_knob_still_works(qtbot):
    h = _make_handler()
    received = []
    h.signals.knob_moved.connect(lambda idx, val: received.append((idx, val)))
    h._on_midi_message(([0xB0, 21, 64], None))
    assert received == [(0, 64)]


def test_existing_fader_still_works(qtbot):
    h = _make_handler()
    received = []
    h.signals.fader_moved.connect(lambda val: received.append(val))
    h._on_midi_message(([0xB0, 9, 100], None))
    assert received == [100]

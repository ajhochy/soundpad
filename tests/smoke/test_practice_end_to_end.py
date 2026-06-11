"""End-to-end Practice Mode smoke: simulates the full pipeline without audio.

Loads a real MIDI file built in memory, opens PracticeWindow with mocked
synth + a real MidiSignals object, exercises:
  - Open + Play flow (Free mode auto-advances)
  - Waiting mode: clock pauses on first note
  - Correct key press resumes the clock
  - Wrong key press flashes red
  - Mute toggle suppresses synth calls but visuals continue
  - Stop clears state

This is the closest we can get to a real device smoke test from a
headless macOS dev box. Real-device manual smoke happens on the Linux
target box (docs/testing/manual-smoke.md).
"""
import os
import tempfile
from pathlib import Path

import mido
import pytest
from unittest.mock import MagicMock
from PyQt5.QtGui import QColor

from core.midi_handler import MidiSignals
from core.note_matcher import MatchResult
from ui.practice_window import PracticeWindow


def _make_two_chord_midi():
    """Build a tiny MIDI file with one single note then one two-note chord."""
    mid = mido.MidiFile(ticks_per_beat=480, type=0)
    track = mido.MidiTrack()
    mid.tracks.append(track)
    # Note C4 at tick 0 for 480 ticks (500ms)
    track.append(mido.Message('note_on', channel=0, note=60, velocity=80, time=0))
    track.append(mido.Message('note_off', channel=0, note=60, velocity=0, time=480))
    # Chord E4+G4 at tick 480
    track.append(mido.Message('note_on', channel=0, note=64, velocity=80, time=0))
    track.append(mido.Message('note_on', channel=0, note=67, velocity=80, time=0))
    track.append(mido.Message('note_off', channel=0, note=64, velocity=0, time=480))
    track.append(mido.Message('note_off', channel=0, note=67, velocity=0, time=0))
    f = tempfile.NamedTemporaryFile(suffix='.mid', delete=False)
    mid.save(f.name)
    f.close()
    return f.name


def _make_window(qtbot):
    synth = MagicMock()
    synth.init_practice_channel.return_value = None
    synth.practice_note_on.return_value = None
    synth.practice_note_off.return_value = None
    midi = MagicMock()
    midi.signals = MidiSignals()
    win = PracticeWindow(synth, midi)
    qtbot.addWidget(win)
    win.resize(900, 500)
    win.show()
    return win, synth, midi


def test_free_mode_playback_emits_practice_notes(qtbot):
    """Open a MIDI file in Free mode and verify synth receives the notes."""
    win, synth, _ = _make_window(qtbot)
    path = _make_two_chord_midi()
    try:
        win._player.load(path)
        win._mode_combo.setCurrentText("Free")
        win._speed_slider.setValue(150)  # fast
        win._play_btn.setChecked(True)
        win._toggle_play(True)
        qtbot.wait(800)
        win._stop()
        # Synth must have received at least the C4 + E4 + G4 notes
        called_notes = [c.args[1] for c in synth.practice_note_on.call_args_list]
        assert 60 in called_notes
        assert 64 in called_notes
        assert 67 in called_notes
    finally:
        os.unlink(path)


def test_waiting_mode_resumes_on_correct_press(qtbot):
    """Waiting mode: clock pauses, correct key resumes, wrong key stays paused."""
    win, _, midi = _make_window(qtbot)
    path = _make_two_chord_midi()
    try:
        win._player.load(path)
        # Combo defaults to "Waiting" and PracticeWindow now syncs the
        # player to the combo on init, so just assert and proceed.
        assert win._mode_combo.currentText() == "Waiting"
        assert win._player._mode == "waiting"
        # Wait specifically for the waiting_for signal to fire — guarantees
        # the clock has paused, regardless of QTimer scheduling jitter.
        with qtbot.waitSignal(win._player.signals.waiting_for, timeout=2000):
            win._toggle_play(True)
        assert win._player.is_playing is False
        # Wrong key (D4 instead of C4) — should be MISS, clock stays paused
        midi.signals.key_pressed.emit(62, 80)
        qtbot.wait(20)
        assert win._player.is_playing is False
        assert win._lit_keys.get(62) is not None
        # QColor equality is identity-based; compare by hex name
        assert win._lit_keys[62].name() == "#ef5350"
        qtbot.wait(220)
        assert 62 not in win._lit_keys
        # Correct key — HIT, clock resumes
        midi.signals.key_pressed.emit(60, 80)
        qtbot.wait(20)
        assert win._player.is_playing is True
    finally:
        win._stop()
        os.unlink(path)


def test_mute_suppresses_synth_in_free_mode(qtbot):
    win, synth, _ = _make_window(qtbot)
    path = _make_two_chord_midi()
    try:
        win._player.load(path)
        win._mode_combo.setCurrentText("Free")
        win._speed_slider.setValue(150)
        win._mute_btn.setChecked(True)
        win._on_mute_toggled(True)
        win._toggle_play(True)
        qtbot.wait(400)
        win._stop()
        synth.practice_note_on.assert_not_called()
    finally:
        os.unlink(path)


def test_song_finished_resets_play_button(qtbot):
    win, _, _ = _make_window(qtbot)
    path = _make_two_chord_midi()
    try:
        win._player.load(path)
        win._mode_combo.setCurrentText("Free")
        win._speed_slider.setValue(150)
        win._play_btn.setChecked(True)
        win._toggle_play(True)
        qtbot.wait(1500)
        assert win._play_btn.isChecked() is False
        assert win._play_btn.text() == "▶ Play"
    finally:
        win._stop()
        os.unlink(path)


def test_e2e_screenshot_after_playback(qtbot):
    """Render a screenshot mid-playback with notes flowing."""
    win, _, _ = _make_window(qtbot)
    path = _make_two_chord_midi()
    try:
        win._player.load(path)
        win._mode_combo.setCurrentText("Free")
        win._speed_slider.setValue(100)
        win._toggle_play(True)
        qtbot.wait(150)
        pm = win.grab()
        out_dir = Path(__file__).parent / "_artifacts"
        out_dir.mkdir(parents=True, exist_ok=True)
        assert pm.save(str(out_dir / "practice_mid_playback.png")) is True
    finally:
        win._stop()
        os.unlink(path)


def test_e2e_screenshot_in_waiting_mode(qtbot):
    """Screenshot showing amber waiting key + falling notes."""
    win, _, _ = _make_window(qtbot)
    path = _make_two_chord_midi()
    try:
        win._player.load(path)
        # Combo defaults to "Waiting" and PracticeWindow now syncs the
        # player to the combo on init, so just assert and proceed.
        assert win._mode_combo.currentText() == "Waiting"
        assert win._player._mode == "waiting"
        win._toggle_play(True)
        qtbot.wait(500)  # let it reach first note and pause
        pm = win.grab()
        out_dir = Path(__file__).parent / "_artifacts"
        out_dir.mkdir(parents=True, exist_ok=True)
        assert pm.save(str(out_dir / "practice_waiting_amber.png")) is True
    finally:
        win._stop()
        os.unlink(path)

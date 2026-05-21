"""Smoke tests for ui/practice_window.py."""
from pathlib import Path
import pytest
from unittest.mock import MagicMock, patch
from PyQt5.QtGui import QColor


def make_practice_window(qtbot):
    """Build a PracticeWindow with fully mocked synth and midi."""
    from ui.practice_window import PracticeWindow

    mock_synth = MagicMock()
    mock_synth.init_practice_channel.return_value = None
    mock_synth.practice_note_on.return_value = None
    mock_synth.practice_note_off.return_value = None

    mock_midi = MagicMock()
    from core.midi_handler import MidiSignals
    mock_midi.signals = MidiSignals()

    win = PracticeWindow(mock_synth, mock_midi)
    qtbot.addWidget(win)
    return win, mock_synth, mock_midi


def test_window_creates_without_crash(qtbot):
    win, _, _ = make_practice_window(qtbot)
    win.show()
    assert win.isVisible()


def test_window_has_minimum_size(qtbot):
    win, _, _ = make_practice_window(qtbot)
    assert win.minimumWidth() >= 900
    assert win.minimumHeight() >= 500


def test_play_button_exists(qtbot):
    win, _, _ = make_practice_window(qtbot)
    assert win._play_btn is not None


def test_stop_button_exists(qtbot):
    win, _, _ = make_practice_window(qtbot)
    assert win._stop_btn is not None


def test_speed_slider_range(qtbot):
    win, _, _ = make_practice_window(qtbot)
    assert win._speed_slider.minimum() == 25
    assert win._speed_slider.maximum() == 150
    assert win._speed_slider.value() == 100


def test_mode_combo_has_waiting_and_free(qtbot):
    win, _, _ = make_practice_window(qtbot)
    items = [win._mode_combo.itemText(i) for i in range(win._mode_combo.count())]
    assert "Waiting" in items
    assert "Free" in items


def test_stop_clears_lit_keys(qtbot):
    win, _, _ = make_practice_window(qtbot)
    win._lit_keys = {60: QColor("#ff0000")}
    win._stop()
    assert win._lit_keys == {}


def test_init_practice_channel_called_on_init(qtbot):
    win, mock_synth, _ = make_practice_window(qtbot)
    mock_synth.init_practice_channel.assert_called_once_with(channel=15)


def test_speed_label_updates_with_slider(qtbot):
    win, _, _ = make_practice_window(qtbot)
    win._speed_slider.setValue(75)
    assert win._speed_label.text() == "75%"


def test_mute_toggle_suppresses_note_on(qtbot):
    win, mock_synth, _ = make_practice_window(qtbot)
    win._muted = True
    win._on_playback_note_on(60, 80)
    mock_synth.practice_note_on.assert_not_called()


def test_mute_off_allows_note_on(qtbot):
    win, mock_synth, _ = make_practice_window(qtbot)
    win._muted = False
    win._on_playback_note_on(60, 80)
    mock_synth.practice_note_on.assert_called_once_with(15, 60, 80)


def test_live_midi_key_pressed_routed_to_player(qtbot):
    """Live key press from MidiHandler should flow through _on_key_pressed
    -> player.note_pressed and update _lit_keys."""
    win, _, mock_midi = make_practice_window(qtbot)
    # Free mode -> NOT_YET -> green light on key 60
    win._player.set_mode("free")
    mock_midi.signals.key_pressed.emit(60, 80)
    qtbot.wait(20)
    assert 60 in win._lit_keys


def test_live_midi_key_released_routed_to_player(qtbot):
    win, _, mock_midi = make_practice_window(qtbot)
    win._lit_keys[60] = QColor("#00e676")
    mock_midi.signals.key_released.emit(60)
    qtbot.wait(20)
    # _on_playback_note_off (triggered by note_released -> note_off signal)
    # should pop the key from _lit_keys.
    assert 60 not in win._lit_keys


def test_window_screenshot_offscreen(qtbot):
    """Capture a screenshot of the full practice window for visual smoke."""
    win, _, _ = make_practice_window(qtbot)
    win.resize(900, 500)
    win.show()
    qtbot.wait(50)
    pm = win.grab()
    assert not pm.isNull()
    out_dir = Path(__file__).parent / "smoke" / "_artifacts"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "practice_window.png"
    assert pm.save(str(out)) is True
    assert out.exists() and out.stat().st_size > 0

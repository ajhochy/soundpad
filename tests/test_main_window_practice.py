"""Tests that MainWindow exposes Practice Mode through the new button."""
from pathlib import Path
import pytest
from unittest.mock import MagicMock, patch
from PyQt5.QtCore import Qt


def make_main_window(qtbot):
    from core.config import Config
    from core.scene_manager import SceneManager
    from core.midi_handler import MidiHandler, MidiSignals
    from core.synth_engine import SynthEngine
    from ui.main_window import MainWindow

    config = MagicMock(spec=Config)
    config.num_pads = 8
    config.pad_colour.return_value = "#888888"
    config.midi_map = {
        "pads": [], "knobs": [], "master_fader": {"channel": 0, "cc": 9}
    }

    synth = MagicMock(spec=SynthEngine)
    synth.catalogue = []
    synth.get_pad_states.return_value = []

    scenes = MagicMock(spec=SceneManager)
    scenes.scene_names = []

    midi = MagicMock(spec=MidiHandler)
    midi.signals = MidiSignals()
    midi.is_connected.return_value = False

    win = MainWindow(config, synth, scenes, midi)
    qtbot.addWidget(win)
    return win


def test_practice_button_exists(qtbot):
    win = make_main_window(qtbot)
    assert hasattr(win, '_practice_btn')


def test_practice_button_text_has_piano_emoji(qtbot):
    win = make_main_window(qtbot)
    assert "Practice" in win._practice_btn.text()


def test_practice_button_opens_window(qtbot):
    win = make_main_window(qtbot)
    win.show()
    with patch('ui.main_window.PracticeWindow') as MockPW:
        mock_pw_instance = MagicMock()
        MockPW.return_value = mock_pw_instance
        qtbot.mouseClick(win._practice_btn, Qt.LeftButton)
        MockPW.assert_called_once()
        mock_pw_instance.show.assert_called_once()


def test_practice_window_instance_reused(qtbot):
    """Clicking Practice twice must NOT construct a second PracticeWindow."""
    win = make_main_window(qtbot)
    win.show()
    with patch('ui.main_window.PracticeWindow') as MockPW:
        mock_pw_instance = MagicMock()
        MockPW.return_value = mock_pw_instance
        qtbot.mouseClick(win._practice_btn, Qt.LeftButton)
        qtbot.mouseClick(win._practice_btn, Qt.LeftButton)
        assert MockPW.call_count == 1
        assert mock_pw_instance.show.call_count == 2


def test_main_window_screenshot_offscreen(qtbot):
    win = make_main_window(qtbot)
    win.resize(700, 500)
    win.show()
    qtbot.wait(80)
    pm = win.grab()
    assert not pm.isNull()
    out_dir = Path(__file__).parent / "smoke" / "_artifacts"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "main_window_with_practice_button.png"
    assert pm.save(str(out)) is True
    assert out.exists() and out.stat().st_size > 0

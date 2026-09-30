"""Tests for practice channel methods on SynthEngine."""
from unittest.mock import MagicMock, patch
import pytest


def make_mock_synth_engine():
    """
    Build a SynthEngine with FluidSynth mocked out.
    Avoids needing real soundfonts or audio hardware during tests.
    """
    with patch('fluidsynth.Synth') as MockFs:
        mock_fs = MagicMock()
        MockFs.return_value = mock_fs
        mock_fs.start.return_value = None
        mock_fs.sfload.return_value = 1

        from core.config import Config
        from core.synth_engine import SynthEngine

        config = MagicMock(spec=Config)
        config.num_pads = 8
        config.soundfont_dir = MagicMock()
        config.soundfont_dir.glob.return_value = []

        engine = SynthEngine(config)
        engine._sf_ids = {"fake.sf2": 1}
        engine._fs = mock_fs
        return engine, mock_fs


def test_synth_engine_has_init_practice_channel():
    engine, _ = make_mock_synth_engine()
    assert hasattr(engine, 'init_practice_channel')


def test_synth_engine_has_practice_note_on():
    engine, _ = make_mock_synth_engine()
    assert hasattr(engine, 'practice_note_on')


def test_synth_engine_has_practice_note_off():
    engine, _ = make_mock_synth_engine()
    assert hasattr(engine, 'practice_note_off')


def test_init_practice_channel_calls_program_select():
    engine, mock_fs = make_mock_synth_engine()
    engine.init_practice_channel(channel=15)
    mock_fs.program_select.assert_called_with(15, 1, 0, 0)


def test_init_practice_channel_default_channel_is_15():
    engine, mock_fs = make_mock_synth_engine()
    engine.init_practice_channel()
    mock_fs.program_select.assert_called_with(15, 1, 0, 0)


def test_practice_note_on_calls_noteon():
    engine, mock_fs = make_mock_synth_engine()
    engine.practice_note_on(15, 60, 80)
    mock_fs.noteon.assert_called_with(15, 60, 80)


def test_practice_note_off_calls_noteoff():
    engine, mock_fs = make_mock_synth_engine()
    engine.practice_note_off(15, 60)
    mock_fs.noteoff.assert_called_with(15, 60)


def test_init_practice_channel_does_nothing_when_no_soundfonts():
    engine, mock_fs = make_mock_synth_engine()
    engine._sf_ids = {}
    engine.init_practice_channel(channel=15)
    mock_fs.program_select.assert_not_called()


def test_existing_play_note_still_works():
    """Regression: existing play_note path must continue to call noteon."""
    engine, mock_fs = make_mock_synth_engine()
    # Activate pad 0 manually for the test
    engine._pads[0].soundfont_path = "fake.sf2"
    engine._pads[0].active = True
    engine.play_note(60, 80)
    mock_fs.noteon.assert_called_with(0, 60, 80)

"""Tests for MidiFilePlayer in core/midi_file_player.py."""
import os
import tempfile
import pytest
import mido
from core.midi_file_player import MidiFilePlayer
from core.note_matcher import MatchResult


def make_two_note_midi():
    """C4 at t=0 (500ms), D4 at t=500ms (500ms). Returns temp file path."""
    mid = mido.MidiFile(ticks_per_beat=480, type=0)
    track = mido.MidiTrack()
    mid.tracks.append(track)
    track.append(mido.Message('note_on',  channel=0, note=60, velocity=64, time=0))
    track.append(mido.Message('note_off', channel=0, note=60, velocity=0,  time=480))
    track.append(mido.Message('note_on',  channel=0, note=62, velocity=64, time=0))
    track.append(mido.Message('note_off', channel=0, note=62, velocity=0,  time=480))
    f = tempfile.NamedTemporaryFile(suffix='.mid', delete=False)
    mid.save(f.name)
    f.close()
    return f.name


def test_initial_state(qtbot):
    player = MidiFilePlayer()
    assert player.clock_us == 0
    assert player.is_playing is False


def test_load_sets_events(qtbot):
    player = MidiFilePlayer()
    path = make_two_note_midi()
    try:
        player.load(path)
        assert len(player._events) == 2
    finally:
        os.unlink(path)


def test_stop_resets_clock(qtbot):
    player = MidiFilePlayer()
    path = make_two_note_midi()
    try:
        player.load(path)
        player.play()
        qtbot.wait(50)
        player.stop()
        assert player.clock_us == 0
        assert player.is_playing is False
    finally:
        os.unlink(path)


def test_set_speed(qtbot):
    player = MidiFilePlayer()
    player.set_speed(50)
    assert player._speed == pytest.approx(0.5)
    player.set_speed(150)
    assert player._speed == pytest.approx(1.5)


def test_set_mode(qtbot):
    player = MidiFilePlayer()
    player.set_mode("waiting")
    assert player._mode == "waiting"
    player.set_mode("free")
    assert player._mode == "free"


def test_play_advances_clock(qtbot):
    player = MidiFilePlayer()
    path = make_two_note_midi()
    try:
        player.load(path)
        player.set_mode("free")
        player.play()
        qtbot.wait(100)
        player.pause()
        assert player.clock_us > 10_000
    finally:
        os.unlink(path)
        player.stop()


def test_pause_stops_clock_advancing(qtbot):
    player = MidiFilePlayer()
    path = make_two_note_midi()
    try:
        player.load(path)
        player.set_mode("free")
        player.play()
        qtbot.wait(50)
        player.pause()
        clock_at_pause = player.clock_us
        qtbot.wait(50)
        assert player.clock_us == clock_at_pause
    finally:
        os.unlink(path)


def test_note_on_signal_emitted_in_free_mode(qtbot):
    player = MidiFilePlayer()
    player.set_mode("free")
    path = make_two_note_midi()
    try:
        player.load(path)
        received = []
        player.signals.note_on.connect(lambda n, v: received.append(n))
        player.play()
        qtbot.wait(600)
        player.stop()
        assert 60 in received
    finally:
        os.unlink(path)
        player.stop()


def test_waiting_mode_pauses_on_first_note(qtbot):
    player = MidiFilePlayer()
    player.set_mode("waiting")
    path = make_two_note_midi()
    try:
        player.load(path)
        waiting_received = []
        player.signals.waiting_for.connect(lambda notes: waiting_received.append(list(notes)))
        player.play()
        qtbot.wait(600)
        assert len(waiting_received) >= 1
        assert 60 in waiting_received[0]
        assert player.is_playing is False
    finally:
        os.unlink(path)
        player.stop()


def test_note_pressed_hit_resumes_in_waiting_mode(qtbot):
    player = MidiFilePlayer()
    player.set_mode("waiting")
    path = make_two_note_midi()
    try:
        player.load(path)
        player.play()
        qtbot.wait(600)
        assert player.is_playing is False
        result = player.note_pressed(60, 64)
        assert result == MatchResult.HIT
        assert player.is_playing is True
    finally:
        os.unlink(path)
        player.stop()


def test_note_pressed_miss_in_waiting_mode(qtbot):
    player = MidiFilePlayer()
    player.set_mode("waiting")
    path = make_two_note_midi()
    try:
        player.load(path)
        player.play()
        qtbot.wait(600)
        assert player.is_playing is False
        result = player.note_pressed(59, 64)
        assert result == MatchResult.MISS
        assert player.is_playing is False
    finally:
        os.unlink(path)
        player.stop()


def test_song_finished_signal(qtbot):
    player = MidiFilePlayer()
    player.set_mode("free")
    path = make_two_note_midi()
    try:
        player.load(path)
        player.set_speed(400)
        finished = []
        player.signals.song_finished.connect(lambda: finished.append(True))
        player.play()
        qtbot.wait(800)
        assert len(finished) >= 1
    finally:
        os.unlink(path)
        player.stop()


def test_upcoming_snapshot_returns_events(qtbot):
    """_upcoming_snapshot used by PracticeWindow for instant widget refresh."""
    player = MidiFilePlayer()
    path = make_two_note_midi()
    try:
        player.load(path)
        snap = player._upcoming_snapshot()
        assert len(snap) == 2
        assert snap[0][1] == 60
        assert snap[1][1] == 62
    finally:
        os.unlink(path)

"""Tests for MIDI parsing in core/midi_file_player.py."""
import tempfile
import os
import pytest
import mido
from core.midi_file_player import load_midi_file, _build_tempo_map, _tick_to_us


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_simple_midi(notes):
    """
    Create a temporary type-0 MIDI file.

    notes: list of (note, start_ticks, duration_ticks)
    Returns the file path (caller must os.unlink() it).

    Uses ticks_per_beat=480, default tempo=500000 us/beat (120 BPM).
    At 480 ticks/beat and 500000 us/beat: 1 tick = 500000/480 us.
    480 ticks = 500000 us = 0.5 s.
    """
    mid = mido.MidiFile(ticks_per_beat=480, type=0)
    track = mido.MidiTrack()
    mid.tracks.append(track)

    raw = []
    for note, start_ticks, dur_ticks in notes:
        raw.append((start_ticks, 'note_on', note, 64))
        raw.append((start_ticks + dur_ticks, 'note_off', note, 0))
    raw.sort()

    prev = 0
    for abs_tick, msg_type, note, vel in raw:
        delta = abs_tick - prev
        prev = abs_tick
        if msg_type == 'note_on':
            track.append(mido.Message('note_on', channel=0, note=note, velocity=vel, time=delta))
        else:
            track.append(mido.Message('note_off', channel=0, note=note, velocity=0, time=delta))

    f = tempfile.NamedTemporaryFile(suffix='.mid', delete=False)
    mid.save(f.name)
    f.close()
    return f.name


def make_percussion_midi():
    """MIDI file with notes only on channel 9 (percussion). Should yield no events."""
    mid = mido.MidiFile(ticks_per_beat=480, type=0)
    track = mido.MidiTrack()
    mid.tracks.append(track)
    track.append(mido.Message('note_on', channel=9, note=36, velocity=100, time=0))
    track.append(mido.Message('note_off', channel=9, note=36, velocity=0, time=480))
    f = tempfile.NamedTemporaryFile(suffix='.mid', delete=False)
    mid.save(f.name)
    f.close()
    return f.name


# ---------------------------------------------------------------------------
# Tests — strict acceptance contract
# ---------------------------------------------------------------------------

def test_single_note_returns_one_event():
    path = make_simple_midi([(60, 0, 480)])
    try:
        events = load_midi_file(path)
        assert len(events) == 1
    finally:
        os.unlink(path)


def test_event_format_is_tuple_of_four():
    path = make_simple_midi([(60, 0, 480)])
    try:
        events = load_midi_file(path)
        ts, note, vel, dur = events[0]
        assert isinstance(ts, int)
        assert isinstance(note, int)
        assert isinstance(vel, int)
        assert isinstance(dur, int)
    finally:
        os.unlink(path)


def test_single_note_timing():
    # 480 ticks at 500000 us/beat = 500000 us duration
    path = make_simple_midi([(60, 0, 480)])
    try:
        events = load_midi_file(path)
        ts, note, vel, dur = events[0]
        assert ts == 0
        assert note == 60
        assert vel == 64
        assert dur == 500_000
    finally:
        os.unlink(path)


def test_three_sequential_notes_sorted():
    path = make_simple_midi([(60, 0, 480), (62, 480, 480), (64, 960, 480)])
    try:
        events = load_midi_file(path)
        assert len(events) == 3
        timestamps = [e[0] for e in events]
        assert timestamps == sorted(timestamps)
        assert events[0][1] == 60
        assert events[1][1] == 62
        assert events[2][1] == 64
    finally:
        os.unlink(path)


def test_percussion_channel_excluded():
    path = make_percussion_midi()
    try:
        events = load_midi_file(path)
        assert events == []
    finally:
        os.unlink(path)


def test_empty_file_returns_empty_list():
    mid = mido.MidiFile(ticks_per_beat=480, type=0)
    mid.tracks.append(mido.MidiTrack())
    f = tempfile.NamedTemporaryFile(suffix='.mid', delete=False)
    mid.save(f.name)
    f.close()
    try:
        events = load_midi_file(f.name)
        assert events == []
    finally:
        os.unlink(f.name)


def test_second_note_start_time_is_correct():
    # D4 starts at tick 480 = 500000 us
    path = make_simple_midi([(60, 0, 480), (62, 480, 480)])
    try:
        events = load_midi_file(path)
        assert events[1][0] == 500_000
    finally:
        os.unlink(path)


# ---------------------------------------------------------------------------
# Extra strict acceptance: tempo-change handling
# ---------------------------------------------------------------------------

def test_tempo_change_is_applied():
    """
    Insert a set_tempo at tick 480 that doubles the tempo (250000 us/beat).
    Note 1 starts at tick 0 — must be at 0 us.
    Note 2 starts at tick 480 — must be at 500000 us (first segment).
    Note 3 starts at tick 960 — must be at 500000 + 250000 = 750000 us.
    """
    mid = mido.MidiFile(ticks_per_beat=480, type=0)
    track = mido.MidiTrack()
    mid.tracks.append(track)
    # Note 1 at tick 0
    track.append(mido.Message('note_on', channel=0, note=60, velocity=64, time=0))
    track.append(mido.Message('note_off', channel=0, note=60, velocity=0, time=480))
    # Tempo change at tick 480 (doubles speed to 250k us/beat)
    track.append(mido.MetaMessage('set_tempo', tempo=250_000, time=0))
    # Note 2 at tick 480
    track.append(mido.Message('note_on', channel=0, note=62, velocity=64, time=0))
    track.append(mido.Message('note_off', channel=0, note=62, velocity=0, time=480))
    # Note 3 at tick 960
    track.append(mido.Message('note_on', channel=0, note=64, velocity=64, time=0))
    track.append(mido.Message('note_off', channel=0, note=64, velocity=0, time=480))

    f = tempfile.NamedTemporaryFile(suffix='.mid', delete=False)
    mid.save(f.name)
    f.close()
    try:
        events = load_midi_file(f.name)
        assert len(events) == 3
        assert events[0][0] == 0
        assert events[1][0] == 500_000
        assert events[2][0] == 750_000
    finally:
        os.unlink(f.name)


def test_build_tempo_map_default_when_no_set_tempo():
    mid = mido.MidiFile(ticks_per_beat=480, type=0)
    mid.tracks.append(mido.MidiTrack())
    tempo_map = _build_tempo_map(mid)
    assert tempo_map == [(0, 500_000)]


def test_tick_to_us_simple():
    # No tempo changes — 480 ticks at 500000 us/beat with ticks_per_beat=480
    # = 500000 us
    assert _tick_to_us(480, [(0, 500_000)], 480) == 500_000
    assert _tick_to_us(0, [(0, 500_000)], 480) == 0

"""
midi_file_player.py — MIDI file parsing and playback engine.

Parsing:    load_midi_file() — pure Python, no Qt
Playback:   MidiFilePlayer  — QObject with signals, QTimer, speed, waiting mode
            (added in Issue #27 / Task 4)

References:
  Linthesia src/PlayingState.cpp (GPL-2.0) — waiting mode state machine
"""

import mido


# ---------------------------------------------------------------------------
# Parsing helpers (pure Python, no Qt)
# ---------------------------------------------------------------------------

def _build_tempo_map(mid):
    """
    Scan all tracks for set_tempo messages.
    Returns a sorted list of (abs_tick, tempo_us_per_beat).
    Always starts with (0, 500000) = 120 BPM default.
    """
    events = [(0, 500_000)]
    for track in mid.tracks:
        abs_tick = 0
        for msg in track:
            abs_tick += msg.time
            if msg.type == 'set_tempo':
                events.append((abs_tick, msg.tempo))
    # Deduplicate and sort; later entries at same tick override earlier
    seen = {}
    for tick, tempo in events:
        seen[tick] = tempo
    return sorted(seen.items())


def _tick_to_us(abs_tick, tempo_map, ticks_per_beat):
    """
    Convert absolute MIDI ticks to microseconds using a tempo map.
    Handles mid-song tempo changes correctly.
    """
    us = 0
    for i, (tick, tempo) in enumerate(tempo_map):
        if tick >= abs_tick:
            break
        next_tick = tempo_map[i + 1][0] if i + 1 < len(tempo_map) else abs_tick
        segment_end = min(next_tick, abs_tick)
        us += (segment_end - tick) * tempo // ticks_per_beat
    return us


def load_midi_file(path):
    """
    Parse a .mid file and return a flat, time-sorted list of note events.

    Each event: (timestamp_us, note, velocity, duration_us)
      - timestamp_us: when the note starts, in microseconds from song start
      - note:         MIDI note number (0-127)
      - velocity:     note-on velocity (1-127)
      - duration_us:  how long the note lasts, in microseconds

    Track selection: uses the first track that has note_on events on a
    non-percussion channel (channel 9 is always excluded).

    Handles type 0 (single-track) and type 1 (multi-track) MIDI files.
    Handles tempo changes correctly via tempo map.
    """
    try:
        mid = mido.MidiFile(path)
    except Exception:
        return []

    ticks_per_beat = mid.ticks_per_beat
    tempo_map = _build_tempo_map(mid)

    # Find first track with non-percussion note events
    target_track = None
    for track in mid.tracks:
        has_notes = any(
            msg.type == 'note_on' and msg.channel != 9 and msg.velocity > 0
            for msg in track
        )
        if has_notes:
            target_track = track
            break

    if target_track is None:
        return []

    # Walk the track, accumulating absolute ticks and matching note_on/note_off pairs
    events = []
    note_starts = {}  # note -> (abs_tick, velocity)
    abs_tick = 0

    for msg in target_track:
        abs_tick += msg.time

        if msg.type == 'note_on' and msg.channel != 9 and msg.velocity > 0:
            note_starts[msg.note] = (abs_tick, msg.velocity)

        elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
            if msg.channel == 9:
                continue
            if msg.note in note_starts:
                start_tick, vel = note_starts.pop(msg.note)
                start_us = _tick_to_us(start_tick, tempo_map, ticks_per_beat)
                end_us = _tick_to_us(abs_tick, tempo_map, ticks_per_beat)
                dur_us = max(0, end_us - start_us)
                events.append((start_us, msg.note, vel, dur_us))

    events.sort(key=lambda e: e[0])
    return events

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


# ---------------------------------------------------------------------------
# Qt imports — only needed for MidiFilePlayer (kept separate from pure parsing)
# ---------------------------------------------------------------------------

from PyQt5.QtCore import QObject, QTimer, pyqtSignal
from core.note_matcher import MatchResult, check, all_required_pressed


class _PlayerSignals(QObject):
    """Qt signal container for MidiFilePlayer (QObject subclass required for signals)."""
    note_on = pyqtSignal(int, int)         # note (0-127), velocity (0-127)
    note_off = pyqtSignal(int)             # note (0-127)
    playback_tick = pyqtSignal(int, list)  # clock_us, upcoming_notes
    waiting_for = pyqtSignal(list)         # list[int] — notes that must be pressed
    song_finished = pyqtSignal()


class MidiFilePlayer:
    """
    Playback engine for a single MIDI file.

    Owns a QTimer (16ms / ~60fps). Each tick advances the playback clock
    by 16ms x speed_multiplier microseconds.

    Free mode:   notes fire automatically; note_on/note_off signals emitted.
    Waiting mode: clock pauses when required notes arrive; resumes when all
                  are pressed via note_pressed().

    Usage:
        player = MidiFilePlayer()
        player.signals.note_on.connect(synth.practice_note_on)
        player.load("/path/to/song.mid")
        player.set_mode("waiting")
        player.play()
    """

    TICK_MS = 16              # timer interval (ms) -> ~60fps
    LOOKAHEAD_US = 3_000_000  # 3 seconds of upcoming notes sent to widget

    def __init__(self):
        self.signals = _PlayerSignals()
        self._events = []
        self._clock_us = 0
        self._event_idx = 0
        self._speed = 1.0
        self._mode = "free"
        self._waiting_notes = set()
        self._pressed_notes = set()

        self._timer = QTimer()
        self._timer.setInterval(self.TICK_MS)
        self._timer.timeout.connect(self._tick)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def clock_us(self):
        return self._clock_us

    @property
    def is_playing(self):
        return self._timer.isActive()

    def load(self, path):
        """Parse a MIDI file and reset playback to the start."""
        self.stop()
        self._events = load_midi_file(path)

    def play(self):
        """Start or resume playback."""
        if self._events:
            self._timer.start()

    def pause(self):
        """Pause playback without resetting the clock."""
        self._timer.stop()

    def stop(self):
        """Stop playback and reset clock to zero."""
        self._timer.stop()
        self._clock_us = 0
        self._event_idx = 0
        self._waiting_notes.clear()
        self._pressed_notes.clear()

    def set_speed(self, percent):
        """Set playback speed. percent=100 -> real time. Clamped to 25-400."""
        self._speed = max(0.25, min(4.0, percent / 100.0))

    def set_mode(self, mode):
        """Set mode: 'free' or 'waiting'. Takes effect immediately."""
        self._mode = mode.lower()
        if self._mode == "free":
            self._waiting_notes.clear()

    def note_pressed(self, note, velocity):
        """
        Called by PracticeWindow when a live MIDI key is pressed.

        In waiting mode: checks the note against required notes.
          - HIT  -> removes note from waiting set; resumes timer if set is now empty;
                   emits note_on so FluidSynth plays the sound.
          - MISS -> returns MISS; caller (PracticeWindow) handles red flash.
        In free mode: returns NOT_YET (live notes are displayed by PracticeWindow directly).
        """
        self._pressed_notes.add(note)

        if self._mode == "waiting" and self._waiting_notes:
            result = check(note, self._waiting_notes)
            if result == MatchResult.HIT:
                self._waiting_notes.discard(note)
                self.signals.note_on.emit(note, velocity)
                if not self._waiting_notes:
                    self._timer.start()
            return result

        return MatchResult.NOT_YET

    def note_released(self, note):
        """Called by PracticeWindow when a live MIDI key is released."""
        self._pressed_notes.discard(note)
        self.signals.note_off.emit(note)

    def _upcoming_snapshot(self):
        """Return the current lookahead window of upcoming note events."""
        return [
            e for e in self._events[self._event_idx:]
            if e[0] <= self._clock_us + self.LOOKAHEAD_US
        ]

    # ------------------------------------------------------------------
    # Timer tick (private)
    # ------------------------------------------------------------------

    def _tick(self):
        delta_us = int(self.TICK_MS * 1_000 * self._speed)
        self._clock_us += delta_us

        if self._mode == "waiting":
            self._process_waiting_tick()
        else:
            self._process_free_tick()

        # Check for end of song
        if self._event_idx >= len(self._events):
            self._timer.stop()
            self.signals.song_finished.emit()
            return

        upcoming = [
            e for e in self._events[self._event_idx:]
            if e[0] <= self._clock_us + self.LOOKAHEAD_US
        ]
        self.signals.playback_tick.emit(self._clock_us, upcoming)

    def _process_free_tick(self):
        """Fire note events whose time has arrived (free mode)."""
        while (self._event_idx < len(self._events) and
               self._events[self._event_idx][0] <= self._clock_us):
            ts_us, note, vel, dur_us = self._events[self._event_idx]
            self._event_idx += 1
            self.signals.note_on.emit(note, vel)
            delay_ms = max(50, dur_us // 1_000)
            QTimer.singleShot(delay_ms, lambda n=note: self.signals.note_off.emit(n))

    def _process_waiting_tick(self):
        """
        Collect notes whose time has arrived, pause the clock, and emit
        waiting_for with the full set of notes that must be pressed.
        """
        while (self._event_idx < len(self._events) and
               self._events[self._event_idx][0] <= self._clock_us):
            ts_us, note, vel, dur_us = self._events[self._event_idx]
            self._event_idx += 1
            self._waiting_notes.add(note)

        if self._waiting_notes:
            self._timer.stop()
            self.signals.waiting_for.emit(list(self._waiting_notes))

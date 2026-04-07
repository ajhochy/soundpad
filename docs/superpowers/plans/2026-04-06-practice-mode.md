# Practice Mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a separate Practice window to SoundPad where a child can load a MIDI file, see falling coloured notes above a 49-key piano, and practice in either Waiting mode (song pauses until correct note pressed) or Free mode (plays at adjustable speed).

**Architecture:** Four new files across `core/` (pure logic, no Qt: MIDI parsing and note matching) and `ui/` (Qt rendering: piano roll widget and practice window). Two existing files (`midi_handler.py`, `main_window.py`) get small additions. Rendering is entirely via `QPainter` — no new GUI library. Piano key layout algorithm ported from Neothesia; waiting-mode state machine ported from Linthesia.

**Tech Stack:** PyQt5, mido (MIDI file parsing), pyFluidSynth (existing), python-rtmidi (existing), pytest + pytest-qt (testing)

**Spec:** `docs/superpowers/specs/2026-04-06-practice-mode-design.md`

**GitHub repo:** `ajhochy/soundpad`

---

## File Map

| File | Status | Responsibility |
|---|---|---|
| `core/note_matcher.py` | **CREATE** | Linthesia waiting-mode logic: HIT/MISS/NOT_YET for a pressed note vs required set |
| `core/midi_file_player.py` | **CREATE** | mido MIDI parsing + QObject playback engine with signals, clock, speed, waiting state |
| `ui/piano_roll_widget.py` | **CREATE** | QPainter widget: 49-key piano (Neothesia layout) + falling note bars + key lighting |
| `ui/practice_window.py` | **CREATE** | QMainWindow shell: toolbar + PianoRollWidget + wiring to player and MIDI signals |
| `core/midi_handler.py` | **MODIFY** | Add `key_pressed(note, velocity)` and `key_released(note)` Qt signals |
| `core/synth_engine.py` | **MODIFY** | Add `init_practice_channel()`, `practice_note_on()`, `practice_note_off()` |
| `ui/main_window.py` | **MODIFY** | Add 🎹 Practice button that opens PracticeWindow |
| `requirements.txt` | **MODIFY** | Add `mido>=1.3` |
| `tests/` | **CREATE** | Test directory with conftest.py, one test file per new module |

---

## Task 1: Install mido and set up test scaffolding

**Files:**
- Modify: `requirements.txt`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Install new dependencies**

```bash
pip3 install mido pytest pytest-qt
```

Expected output: Successfully installed mido-x.x.x pytest-x.x.x pytest-qt-x.x.x (versions may vary)

- [ ] **Step 2: Add mido to requirements.txt**

Open `requirements.txt`. It currently reads:
```
PyQt5>=5.15
pyFluidSynth>=1.3
python-rtmidi>=1.5
```

Replace the entire file with:
```
PyQt5>=5.15
pyFluidSynth>=1.3
python-rtmidi>=1.5
mido>=1.3
```

- [ ] **Step 3: Create tests directory and files**

```bash
mkdir -p tests
touch tests/__init__.py
```

Create `tests/conftest.py` with this exact content:
```python
"""
conftest.py — pytest fixtures shared across the test suite.

pytest-qt provides the `qtbot` fixture automatically once installed.
QApplication is created automatically by pytest-qt for widget tests.
This file exists to mark tests/ as a package and to document that
no manual QApplication setup is needed.
"""
```

- [ ] **Step 4: Verify pytest is wired up**

```bash
cd /opt/soundpad   # or wherever the project lives; use the actual project root
pytest --collect-only
```

Expected: "no tests ran" (0 errors, 0 failures — just nothing collected yet)

- [ ] **Step 5: Commit**

```bash
git add requirements.txt tests/__init__.py tests/conftest.py
git commit -m "chore: add mido + pytest test scaffolding for practice mode"
```

---

## Task 2: core/note_matcher.py — Linthesia waiting-mode logic

Ported from Linthesia `src/PlayingState.cpp`. The `areAllRequiredKeysPressed()` function pauses the playback clock until all notes in the required set (a chord) have been pressed. This module is pure Python — no Qt, no mido.

**Files:**
- Create: `core/note_matcher.py`
- Create: `tests/test_note_matcher.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_note_matcher.py`:

```python
"""Tests for core/note_matcher.py — Linthesia waiting-mode logic port."""
import pytest
from core.note_matcher import MatchResult, NOTE_WINDOW_LENGTH_MS, check, all_required_pressed


def test_hit_when_note_in_required():
    assert check(60, {60}) == MatchResult.HIT


def test_hit_one_of_chord():
    # Pressing one note of a two-note chord is still a HIT for that note
    assert check(60, {60, 64}) == MatchResult.HIT


def test_miss_when_wrong_note():
    assert check(61, {60}) == MatchResult.MISS


def test_miss_wrong_note_in_chord():
    assert check(59, {60, 64}) == MatchResult.MISS


def test_not_yet_when_no_required_notes():
    assert check(60, set()) == MatchResult.NOT_YET


def test_not_yet_empty_required():
    assert check(0, set()) == MatchResult.NOT_YET


def test_all_required_pressed_single_note():
    assert all_required_pressed({60}, {60}) is True


def test_all_required_pressed_chord_complete():
    assert all_required_pressed({60, 64, 67}, {60, 64, 67}) is True


def test_all_required_pressed_chord_incomplete():
    assert all_required_pressed({60}, {60, 64}) is False


def test_all_required_pressed_superset():
    # Extra pressed notes are fine — the chord is still satisfied
    assert all_required_pressed({60, 64, 67, 72}, {60, 64, 67}) is True


def test_all_required_pressed_empty_required():
    assert all_required_pressed({60}, set()) is True


def test_note_window_length_is_400ms():
    assert NOTE_WINDOW_LENGTH_MS == 400
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_note_matcher.py -v
```

Expected: ImportError — `core.note_matcher` does not exist yet.

- [ ] **Step 3: Implement core/note_matcher.py**

Create `core/note_matcher.py`:

```python
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


def check(pressed_note: int, required_notes: set[int]) -> MatchResult:
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


def all_required_pressed(pressed_notes: set[int], required_notes: set[int]) -> bool:
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_note_matcher.py -v
```

Expected: 12 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add core/note_matcher.py tests/test_note_matcher.py
git commit -m "feat: add note_matcher.py — Linthesia waiting-mode logic port"
```

---

## Task 3: core/midi_file_player.py — MIDI file parsing

This covers the pure-Python parsing half of `midi_file_player.py`: reading a `.mid` file with `mido` and producing a flat, time-sorted list of `(timestamp_us, note, velocity, duration_us)` tuples. No Qt. No QObject. No timer.

**Files:**
- Create: `core/midi_file_player.py` (parsing functions only)
- Create: `tests/test_midi_file_player_parsing.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_midi_file_player_parsing.py`:

```python
"""Tests for MIDI parsing in core/midi_file_player.py."""
import tempfile
import os
import pytest
import mido
from core.midi_file_player import load_midi_file


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_simple_midi(notes: list[tuple[int, int, int]]) -> str:
    """
    Create a temporary type-0 MIDI file.

    notes: list of (note, start_ticks, duration_ticks)
    Returns the file path (caller must os.unlink() it).

    Uses ticks_per_beat=480, default tempo=500000 us/beat (120 BPM).
    At 480 ticks/beat and 500000 us/beat: 1 tick = 500000/480 ≈ 1041.67 us.
    480 ticks = 500000 us = 0.5 s.
    """
    mid = mido.MidiFile(ticks_per_beat=480, type=0)
    track = mido.MidiTrack()
    mid.tracks.append(track)

    # Build a sorted event list, then convert to delta-time messages
    raw: list[tuple[int, str, int, int]] = []  # (abs_tick, type, note, velocity)
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


def make_percussion_midi() -> str:
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
# Tests
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
        ts, note, vel, dur = events[0]  # must unpack cleanly
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
    # C4 at 0, D4 at 480, E4 at 960 (each 480 ticks = 500ms)
    path = make_simple_midi([(60, 0, 480), (62, 480, 480), (64, 960, 480)])
    try:
        events = load_midi_file(path)
        assert len(events) == 3
        timestamps = [e[0] for e in events]
        assert timestamps == sorted(timestamps)
        assert events[0][1] == 60  # C4 first
        assert events[1][1] == 62  # D4 second
        assert events[2][1] == 64  # E4 third
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_midi_file_player_parsing.py -v
```

Expected: ImportError — `core.midi_file_player` does not exist.

- [ ] **Step 3: Create core/midi_file_player.py with parsing only**

Create `core/midi_file_player.py`:

```python
"""
midi_file_player.py — MIDI file parsing and playback engine.

Parsing:    load_midi_file() — pure Python, no Qt
Playback:   MidiFilePlayer  — QObject with signals, QTimer, speed, waiting mode

References:
  Linthesia src/PlayingState.cpp (GPL-2.0) — waiting mode state machine
"""

import mido


# ---------------------------------------------------------------------------
# Parsing helpers (pure Python, no Qt)
# ---------------------------------------------------------------------------

def _build_tempo_map(mid: mido.MidiFile) -> list[tuple[int, int]]:
    """
    Scan all tracks for set_tempo messages.
    Returns a sorted list of (abs_tick, tempo_us_per_beat).
    Always starts with (0, 500000) = 120 BPM default.
    """
    events: list[tuple[int, int]] = [(0, 500_000)]
    for track in mid.tracks:
        abs_tick = 0
        for msg in track:
            abs_tick += msg.time
            if msg.type == 'set_tempo':
                events.append((abs_tick, msg.tempo))
    # Deduplicate and sort; later entries at same tick override earlier
    seen: dict[int, int] = {}
    for tick, tempo in events:
        seen[tick] = tempo
    return sorted(seen.items())


def _tick_to_us(abs_tick: int, tempo_map: list[tuple[int, int]], ticks_per_beat: int) -> int:
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


def load_midi_file(path: str) -> list[tuple[int, int, int, int]]:
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
    events: list[tuple[int, int, int, int]] = []
    note_starts: dict[int, tuple[int, int]] = {}  # note → (abs_tick, velocity)
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_midi_file_player_parsing.py -v
```

Expected: 7 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add core/midi_file_player.py tests/test_midi_file_player_parsing.py
git commit -m "feat: add midi_file_player.py parsing — load_midi_file() with tempo map support"
```

---

## Task 4: core/midi_file_player.py — MidiFilePlayer QObject playback engine

Add the `MidiFilePlayer` class to the existing `core/midi_file_player.py`. This is a QObject that owns a `QTimer` (16ms / ~60fps), advances a microsecond playback clock, emits signals, and implements waiting mode.

**Files:**
- Modify: `core/midi_file_player.py` (append MidiFilePlayer class)
- Create: `tests/test_midi_file_player_player.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_midi_file_player_player.py`:

```python
"""Tests for MidiFilePlayer in core/midi_file_player.py."""
import os
import tempfile
import pytest
import mido
from core.midi_file_player import MidiFilePlayer
from core.note_matcher import MatchResult


def make_two_note_midi() -> str:
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


def test_initial_state():
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
        player.play()
        qtbot.wait(100)   # wait 100ms real time
        player.pause()
        # Clock should have advanced by ~100ms × speed (1.0) = ~100000 us
        # Allow generous tolerance since timer intervals are approximate
        assert player.clock_us > 10_000
    finally:
        os.unlink(path)
        player.stop()


def test_pause_stops_clock_advancing(qtbot):
    player = MidiFilePlayer()
    path = make_two_note_midi()
    try:
        player.load(path)
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
        qtbot.wait(600)   # wait past both notes (each 500ms)
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
        qtbot.wait(600)   # enough time to reach first note
        # Clock should be paused waiting for note 60
        assert len(waiting_received) >= 1
        assert 60 in waiting_received[0]
        assert player.is_playing is False  # timer stopped, waiting
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
        # Wait for player to reach first note and pause
        qtbot.wait(600)
        assert player.is_playing is False
        # Press the correct note
        result = player.note_pressed(60, 64)
        assert result == MatchResult.HIT
        # Player should resume
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
        result = player.note_pressed(59, 64)   # wrong note
        assert result == MatchResult.MISS
        assert player.is_playing is False       # still waiting
    finally:
        os.unlink(path)
        player.stop()


def test_song_finished_signal(qtbot):
    player = MidiFilePlayer()
    player.set_mode("free")
    path = make_two_note_midi()
    try:
        player.load(path)
        player.set_speed(400)  # go fast
        finished = []
        player.signals.song_finished.connect(lambda: finished.append(True))
        player.play()
        qtbot.wait(500)
        assert len(finished) == 1
    finally:
        os.unlink(path)
        player.stop()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_midi_file_player_player.py -v
```

Expected: ImportError — `MidiFilePlayer` not yet defined.

- [ ] **Step 3: Append MidiFilePlayer to core/midi_file_player.py**

Open `core/midi_file_player.py` and append this block after the `load_midi_file()` function:

```python
# ---------------------------------------------------------------------------
# Qt imports (only needed for MidiFilePlayer — kept separate from pure parsing)
# ---------------------------------------------------------------------------

from PyQt5.QtCore import QObject, QTimer, pyqtSignal
from core.note_matcher import MatchResult, check, all_required_pressed


class _PlayerSignals(QObject):
    """Qt signal container for MidiFilePlayer (QObject subclass required for signals)."""
    note_on = pyqtSignal(int, int)    # note (0-127), velocity (0-127)
    note_off = pyqtSignal(int)        # note (0-127)
    playback_tick = pyqtSignal(int, list)  # clock_us, upcoming_notes list[tuple]
    waiting_for = pyqtSignal(list)    # list[int] — notes that must be pressed
    song_finished = pyqtSignal()


class MidiFilePlayer:
    """
    Playback engine for a single MIDI file.

    Owns a QTimer (16ms / ~60fps). Each tick advances the playback clock
    by 16ms × speed_multiplier microseconds.

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

    TICK_MS = 16          # timer interval (ms) → ~60fps
    LOOKAHEAD_US = 3_000_000  # 3 seconds of upcoming notes sent to widget

    def __init__(self):
        self.signals = _PlayerSignals()
        self._events: list[tuple[int, int, int, int]] = []
        self._clock_us: int = 0
        self._event_idx: int = 0
        self._speed: float = 1.0
        self._mode: str = "free"
        self._waiting_notes: set[int] = set()
        self._pressed_notes: set[int] = set()

        self._timer = QTimer()
        self._timer.setInterval(self.TICK_MS)
        self._timer.timeout.connect(self._tick)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def clock_us(self) -> int:
        return self._clock_us

    @property
    def is_playing(self) -> bool:
        return self._timer.isActive()

    def load(self, path: str) -> None:
        """Parse a MIDI file and reset playback to the start."""
        self.stop()
        self._events = load_midi_file(path)

    def play(self) -> None:
        """Start or resume playback."""
        if self._events:
            self._timer.start()

    def pause(self) -> None:
        """Pause playback without resetting the clock."""
        self._timer.stop()

    def stop(self) -> None:
        """Stop playback and reset clock to zero."""
        self._timer.stop()
        self._clock_us = 0
        self._event_idx = 0
        self._waiting_notes.clear()
        self._pressed_notes.clear()

    def set_speed(self, percent: int) -> None:
        """Set playback speed. percent=100 → real time. Range 25–400."""
        self._speed = max(0.25, min(4.0, percent / 100.0))

    def set_mode(self, mode: str) -> None:
        """Set mode: 'free' or 'waiting'. Takes effect immediately."""
        self._mode = mode.lower()
        if self._mode == "free":
            self._waiting_notes.clear()

    def note_pressed(self, note: int, velocity: int) -> MatchResult:
        """
        Called by PracticeWindow when a live MIDI key is pressed.

        In waiting mode: checks the note against required notes.
          - HIT  → removes note from waiting set; resumes timer if set is now empty;
                   emits note_on so FluidSynth plays the sound.
          - MISS → returns MISS; caller (PracticeWindow) handles red flash.
        In free mode: returns NOT_YET (live notes are displayed by PracticeWindow directly).
        """
        self._pressed_notes.add(note)

        if self._mode == "waiting" and self._waiting_notes:
            result = check(note, self._waiting_notes)
            if result == MatchResult.HIT:
                self._waiting_notes.discard(note)
                self.signals.note_on.emit(note, velocity)
                if not self._waiting_notes:
                    self._timer.start()  # all chord notes hit — resume
            return result

        return MatchResult.NOT_YET

    def note_released(self, note: int) -> None:
        """Called by PracticeWindow when a live MIDI key is released."""
        self._pressed_notes.discard(note)
        self.signals.note_off.emit(note)

    # ------------------------------------------------------------------
    # Timer tick (private)
    # ------------------------------------------------------------------

    def _tick(self) -> None:
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

        # Emit 60fps tick with upcoming notes for the widget
        upcoming = [
            e for e in self._events[self._event_idx:]
            if e[0] <= self._clock_us + self.LOOKAHEAD_US
        ]
        self.signals.playback_tick.emit(self._clock_us, upcoming)

    def _process_free_tick(self) -> None:
        """Fire note events whose time has arrived (free mode)."""
        while (self._event_idx < len(self._events) and
               self._events[self._event_idx][0] <= self._clock_us):
            ts_us, note, vel, dur_us = self._events[self._event_idx]
            self._event_idx += 1
            self.signals.note_on.emit(note, vel)
            delay_ms = max(50, dur_us // 1_000)
            QTimer.singleShot(delay_ms, lambda n=note: self.signals.note_off.emit(n))

    def _process_waiting_tick(self) -> None:
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_midi_file_player_player.py -v
```

Expected: 11 tests PASSED. (The `song_finished` test may be slightly timing-sensitive; allow a second re-run if it flickers.)

- [ ] **Step 5: Commit**

```bash
git add core/midi_file_player.py tests/test_midi_file_player_player.py
git commit -m "feat: add MidiFilePlayer — QObject playback engine with waiting mode"
```

---

## Task 5: core/midi_handler.py — add key_pressed / key_released signals

The existing `MidiHandler` already receives note-on/note-off MIDI messages from the keyboard but currently ignores any note that isn't a pad note. This task adds two new signals and emits them for keyboard notes.

**Context:** The Launchkey MK3 49 sends pad notes on channel 10 (0-indexed channel 9). All other note-on/note-off messages on channel 1 (0-indexed channel 0) are from the 49 piano keys.

**Files:**
- Modify: `core/midi_handler.py`
- Create: `tests/test_midi_handler_keys.py`

- [ ] **Step 1: Read the current midi_handler.py**

Read `core/midi_handler.py` in full. Note:
- `MidiSignals` at the top has `pad_toggled`, `knob_moved`, `fader_moved`
- `_on_midi_message` handles `0x90` (note-on) only for pad note matching
- Note-on messages that don't match any pad entry are silently discarded

- [ ] **Step 2: Write failing tests**

Create `tests/test_midi_handler_keys.py`:

```python
"""Tests for key_pressed / key_released signals in core/midi_handler.py."""
import pytest
from unittest.mock import MagicMock
from core.midi_handler import MidiSignals


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
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
pytest tests/test_midi_handler_keys.py -v
```

Expected: FAILED — `MidiSignals` has no `key_pressed` attribute.

- [ ] **Step 4: Add signals to MidiSignals**

Open `core/midi_handler.py`. Find the `MidiSignals` class:

```python
class MidiSignals(QObject):
    pad_toggled = pyqtSignal(int)        # pad_index (0-based)
    knob_moved = pyqtSignal(int, int)    # pad_index (0-based), value 0-127
    fader_moved = pyqtSignal(int)        # value 0-127
```

Replace it with:

```python
class MidiSignals(QObject):
    pad_toggled = pyqtSignal(int)        # pad_index (0-based)
    knob_moved = pyqtSignal(int, int)    # pad_index (0-based), value 0-127
    fader_moved = pyqtSignal(int)        # value 0-127
    key_pressed = pyqtSignal(int, int)   # note (0-127), velocity (0-127)
    key_released = pyqtSignal(int)       # note (0-127)
```

- [ ] **Step 5: Emit the new signals in _on_midi_message**

In `core/midi_handler.py`, find the `_on_midi_message` method. After the block that handles CC messages (the `if msg_type == 0xB0:` block), add the following. The complete method should look like this:

```python
    def _on_midi_message(self, event, data=None):
        """
        Called by rtmidi on the MIDI thread.
        Emits Qt signals — safe because Qt queues cross-thread signals.
        """
        message, _ = event
        if len(message) < 3:
            return

        status, byte1, byte2 = message[0], message[1], message[2]
        msg_type = status & 0xF0
        channel = status & 0x0F

        midi_map = self._config.midi_map

        # Note-on (pad toggles)
        if msg_type == 0x90 and byte2 > 0:
            for entry in midi_map["pads"]:
                if entry["channel"] == channel and entry["note"] == byte1:
                    self.signals.pad_toggled.emit(entry["pad"] - 1)
                    return
            # Not a pad note — it's a piano key press
            # Exclude channel 9 (percussion / drum pads on channel 10 in 1-indexed)
            if channel != 9:
                self.signals.key_pressed.emit(byte1, byte2)
            return

        # Note-off
        if msg_type == 0x80:
            if channel != 9:
                self.signals.key_released.emit(byte1)
            return

        # Note-on with velocity 0 = note-off
        if msg_type == 0x90 and byte2 == 0:
            if channel != 9:
                self.signals.key_released.emit(byte1)
            return

        # CC (knobs + fader)
        if msg_type == 0xB0:
            for entry in midi_map["knobs"]:
                if entry["channel"] == channel and entry["cc"] == byte1:
                    self.signals.knob_moved.emit(entry["pad"] - 1, byte2)
                    return
            fader = midi_map["master_fader"]
            if fader["channel"] == channel and fader["cc"] == byte1:
                self.signals.fader_moved.emit(byte2)
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
pytest tests/test_midi_handler_keys.py -v
```

Expected: 4 tests PASSED.

- [ ] **Step 7: Commit**

```bash
git add core/midi_handler.py tests/test_midi_handler_keys.py
git commit -m "feat: add key_pressed/key_released signals to MidiHandler"
```

---

## Task 6: core/synth_engine.py — practice channel methods

`PracticeWindow` needs to play notes through FluidSynth on channel 15 (reserved for practice, away from the 8 pad channels 0–7). Three small public methods are added to `SynthEngine`.

**Files:**
- Modify: `core/synth_engine.py`
- Create: `tests/test_synth_engine_practice.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_synth_engine_practice.py`:

```python
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
        mock_fs.sfload.return_value = 1  # fake soundfont ID

        from core.config import Config
        from core.synth_engine import SynthEngine

        config = MagicMock(spec=Config)
        config.num_pads = 8
        config.soundfont_dir = MagicMock()
        config.soundfont_dir.glob.return_value = []  # no real soundfonts

        engine = SynthEngine(config)
        engine._sf_ids = {"fake.sf2": 1}   # inject a fake soundfont
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
    engine._sf_ids = {}   # simulate no soundfonts loaded
    engine.init_practice_channel(channel=15)
    mock_fs.program_select.assert_not_called()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_synth_engine_practice.py -v
```

Expected: FAILED — `SynthEngine` has no `init_practice_channel` attribute.

- [ ] **Step 3: Add practice channel methods to SynthEngine**

Open `core/synth_engine.py`. Find the `shutdown` method (at the bottom of the class). Insert these three methods immediately before `shutdown`:

```python
    # ------------------------------------------------------------------
    # Practice channel (channel 15, reserved for PracticeWindow)
    # ------------------------------------------------------------------

    def init_practice_channel(self, channel: int = 15) -> None:
        """
        Set up a dedicated FluidSynth channel for practice mode.
        Uses the first loaded soundfont with bank 0, program 0 (Grand Piano).
        Safe to call even if no soundfonts are loaded — does nothing in that case.
        """
        if not self._sf_ids:
            return
        sfid = next(iter(self._sf_ids.values()))
        self._fs.program_select(channel, sfid, 0, 0)

    def practice_note_on(self, channel: int, note: int, velocity: int) -> None:
        """Send a note-on to a FluidSynth channel (used by PracticeWindow)."""
        self._fs.noteon(channel, note, velocity)

    def practice_note_off(self, channel: int, note: int) -> None:
        """Send a note-off to a FluidSynth channel (used by PracticeWindow)."""
        self._fs.noteoff(channel, note)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_synth_engine_practice.py -v
```

Expected: 7 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add core/synth_engine.py tests/test_synth_engine_practice.py
git commit -m "feat: add practice channel methods to SynthEngine"
```

---

## Task 7: ui/piano_roll_widget.py — key layout algorithm (Neothesia port)

The `compute_key_layout()` function produces pixel coordinates for all 49 keys (C2–C6). This is a direct Python port of Neothesia's `piano-layout/src/lib.rs`. The function is pure — no Qt, no side effects — so it can be tested in isolation.

**Algorithm summary (from Neothesia):**
- White keys are evenly spaced: `white_w = total_width / 29`
- Black key dimensions: `black_w = white_w × 0.625`, `black_h = piano_height × 0.635`
- Black key X positions use two separate groups per octave:
  - **C-D-E group** (C#, D#): block width = `3×white_w / 5`; C# at block 1 centre, D# at block 3 centre
  - **F-G-A-B group** (F#, G#, A#): block width = `4×white_w / 7`; F# at block 1, G# at block 3, A# at block 5

**Files:**
- Create: `ui/piano_roll_widget.py` (layout function only — widget class added in Task 8)
- Create: `tests/test_piano_roll_widget.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_piano_roll_widget.py`:

```python
"""Tests for ui/piano_roll_widget.py — piano key layout and widget."""
import pytest
from ui.piano_roll_widget import compute_key_layout

# Test with a widget width that gives clean numbers:
# white_w = 580 / 29 = 20.0 exactly
WIDGET_W = 580
PIANO_H = 100


def test_returns_all_49_keys():
    layout = compute_key_layout(WIDGET_W, PIANO_H)
    # MIDI 36 (C2) to MIDI 84 (C6) inclusive
    assert len(layout) == 49
    for note in range(36, 85):
        assert note in layout


def test_white_key_count():
    layout = compute_key_layout(WIDGET_W, PIANO_H)
    white_keys = [k for k, v in layout.items() if not v['is_black']]
    assert len(white_keys) == 29


def test_black_key_count():
    layout = compute_key_layout(WIDGET_W, PIANO_H)
    black_keys = [k for k, v in layout.items() if v['is_black']]
    assert len(black_keys) == 20


def test_c2_starts_at_x_zero():
    layout = compute_key_layout(WIDGET_W, PIANO_H)
    assert layout[36]['x'] == pytest.approx(0.0)


def test_white_key_width():
    layout = compute_key_layout(WIDGET_W, PIANO_H)
    expected_w = WIDGET_W / 29  # 20.0
    assert layout[36]['w'] == pytest.approx(expected_w)


def test_black_key_width_is_62_5_percent():
    layout = compute_key_layout(WIDGET_W, PIANO_H)
    white_w = WIDGET_W / 29
    expected_bw = white_w * 0.625
    assert layout[37]['w'] == pytest.approx(expected_bw)  # C#2


def test_black_key_height_is_63_5_percent():
    layout = compute_key_layout(WIDGET_W, PIANO_H)
    assert layout[37]['h'] == pytest.approx(PIANO_H * 0.635)  # C#2


def test_white_key_height_equals_piano_height():
    layout = compute_key_layout(WIDGET_W, PIANO_H)
    assert layout[36]['h'] == pytest.approx(float(PIANO_H))


def test_c_sharp_2_is_black():
    layout = compute_key_layout(WIDGET_W, PIANO_H)
    assert layout[37]['is_black'] is True


def test_d2_is_white():
    layout = compute_key_layout(WIDGET_W, PIANO_H)
    assert layout[38]['is_black'] is False


def test_c_sharp_position_neothesia_algorithm():
    # white_w=20, cde_block = 3*20/5 = 12, black_w = 12.5
    # C#2 x = 0 + 1*12 - 12.5/2 = 5.75
    layout = compute_key_layout(WIDGET_W, PIANO_H)
    assert layout[37]['x'] == pytest.approx(5.75)


def test_d_sharp_position_neothesia_algorithm():
    # D#2 x = 0 + 3*12 - 6.25 = 29.75
    layout = compute_key_layout(WIDGET_W, PIANO_H)
    assert layout[39]['x'] == pytest.approx(29.75)


def test_f_sharp_position_neothesia_algorithm():
    # F is at x=60 (3 white keys × 20), fgab_block=4*20/7≈11.4286
    # F#2 x = 60 + 1*fgab_block - 6.25
    layout = compute_key_layout(WIDGET_W, PIANO_H)
    white_w = 20.0
    f_x = 3 * white_w  # 60.0
    fgab_block = 4 * white_w / 7
    black_w = white_w * 0.625
    expected_x = f_x + fgab_block - black_w / 2
    assert layout[42]['x'] == pytest.approx(expected_x)


def test_c6_is_last_key_and_white():
    layout = compute_key_layout(WIDGET_W, PIANO_H)
    assert layout[84]['is_black'] is False
    # C6 is the 29th white key, 0-indexed position 28
    white_w = WIDGET_W / 29
    assert layout[84]['x'] == pytest.approx(28 * white_w)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_piano_roll_widget.py -v
```

Expected: ImportError — `ui.piano_roll_widget` does not exist.

- [ ] **Step 3: Create ui/piano_roll_widget.py with layout function**

Create `ui/piano_roll_widget.py`:

```python
"""
piano_roll_widget.py — falling notes visualiser and 49-key piano display.

Key layout algorithm ported from Neothesia piano-layout/src/lib.rs (MIT).
Repository: https://github.com/PolyMeilex/Neothesia

The widget is a custom QWidget drawn entirely with QPainter.
No external rendering libraries.

Piano range: C2–C6 (MIDI 36–84), 49 keys — matches Novation Launchkey MK3 49.
"""

from PyQt5.QtWidgets import QWidget
from PyQt5.QtGui import QPainter, QColor, QPen
from PyQt5.QtCore import Qt


# ---------------------------------------------------------------------------
# Piano key layout — Neothesia algorithm (pure, no Qt)
# ---------------------------------------------------------------------------

#: MIDI note numbers of white keys within an octave (semitone offsets from C)
_WHITE_SEMITONES: frozenset[int] = frozenset({0, 2, 4, 5, 7, 9, 11})

#: First and last MIDI notes of the 49-key range
FIRST_NOTE = 36  # C2
LAST_NOTE = 84   # C6


def compute_key_layout(widget_width: int, piano_height: int) -> dict[int, dict]:
    """
    Compute pixel positions and sizes for all 49 piano keys (C2–C6).

    Returns a dict mapping MIDI note number → key descriptor:
        {
            'x': float,       # left edge in pixels (from widget left)
            'w': float,       # width in pixels
            'h': float,       # height in pixels
            'is_black': bool  # True for black keys
        }

    Algorithm ported verbatim from Neothesia piano-layout/src/lib.rs:
      - White keys: evenly spaced (white_w = total_width / 29)
      - Black keys: two groups per octave
          CDE group  (C#, D#):     block = 3×white_w / 5
          FGAB group (F#, G#, A#): block = 4×white_w / 7
        Each black key is centred on its block index (1, 3 or 1, 3, 5).
      - Black key size: 62.5% width, 63.5% height of white key.
    """
    white_count = sum(
        1 for n in range(FIRST_NOTE, LAST_NOTE + 1) if n % 12 in _WHITE_SEMITONES
    )

    white_w = widget_width / white_count
    white_h = float(piano_height)
    black_w = white_w * 0.625
    black_h = white_h * 0.635

    layout: dict[int, dict] = {}
    white_x = 0.0
    octave_c_x: dict[int, float] = {}  # octave index → x of C key

    # First pass: place white keys and record where each C lands
    for note in range(FIRST_NOTE, LAST_NOTE + 1):
        semitone = note % 12
        if semitone in _WHITE_SEMITONES:
            layout[note] = {'x': white_x, 'w': white_w, 'h': white_h, 'is_black': False}
            if semitone == 0:
                octave_c_x[note // 12] = white_x
            white_x += white_w

    # Second pass: place black keys using the Neothesia two-group algorithm
    for note in range(FIRST_NOTE, LAST_NOTE + 1):
        semitone = note % 12
        if semitone not in (1, 3, 6, 8, 10):
            continue

        octave = note // 12
        c_x = octave_c_x.get(octave, 0.0)
        f_x = c_x + 3 * white_w   # F is the 4th white key of the octave

        cde_block = 3 * white_w / 5
        fgab_block = 4 * white_w / 7

        if semitone == 1:    # C# — CDE block 1
            x = c_x + 1 * cde_block - black_w / 2
        elif semitone == 3:  # D# — CDE block 3
            x = c_x + 3 * cde_block - black_w / 2
        elif semitone == 6:  # F# — FGAB block 1
            x = f_x + 1 * fgab_block - black_w / 2
        elif semitone == 8:  # G# — FGAB block 3
            x = f_x + 3 * fgab_block - black_w / 2
        else:                # A# (semitone 10) — FGAB block 5
            x = f_x + 5 * fgab_block - black_w / 2

        layout[note] = {'x': x, 'w': black_w, 'h': black_h, 'is_black': True}

    return layout
```

*(The `PianoRollWidget` class will be added to this same file in Task 8.)*

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_piano_roll_widget.py -v
```

Expected: 14 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add ui/piano_roll_widget.py tests/test_piano_roll_widget.py
git commit -m "feat: add piano_roll_widget.py — Neothesia key layout algorithm"
```

---

## Task 8: ui/piano_roll_widget.py — PianoRollWidget (full rendering widget)

Append the `PianoRollWidget` class to `ui/piano_roll_widget.py`. This is the `QWidget` that `PracticeWindow` embeds. It receives display state via `set_state()` and redraws itself on every call using `QPainter`.

**Files:**
- Modify: `ui/piano_roll_widget.py` (append PianoRollWidget class)
- Modify: `tests/test_piano_roll_widget.py` (append widget smoke tests)

- [ ] **Step 1: Add widget smoke tests to tests/test_piano_roll_widget.py**

Append to `tests/test_piano_roll_widget.py`:

```python
# ---------------------------------------------------------------------------
# Widget tests (require Qt — need qtbot fixture from pytest-qt)
# ---------------------------------------------------------------------------

from PyQt5.QtGui import QColor
from ui.piano_roll_widget import PianoRollWidget


def test_widget_creates_without_crash(qtbot):
    widget = PianoRollWidget()
    qtbot.addWidget(widget)
    widget.show()
    assert widget.isVisible()


def test_widget_set_state_does_not_crash(qtbot):
    widget = PianoRollWidget()
    qtbot.addWidget(widget)
    widget.show()
    widget.set_state(0, [], {})
    widget.set_state(500_000, [(500_000, 60, 64, 200_000)], {60: QColor("#00ff00")})


def test_widget_resize_recomputes_layout(qtbot):
    widget = PianoRollWidget()
    qtbot.addWidget(widget)
    widget.resize(580, 300)
    qtbot.wait(50)  # allow resize event to process
    assert len(widget._layout) == 49


def test_widget_has_minimum_size(qtbot):
    widget = PianoRollWidget()
    qtbot.addWidget(widget)
    assert widget.minimumWidth() >= 600
    assert widget.minimumHeight() >= 200
```

- [ ] **Step 2: Run to verify new tests fail**

```bash
pytest tests/test_piano_roll_widget.py::test_widget_creates_without_crash -v
```

Expected: ImportError — `PianoRollWidget` not yet defined.

- [ ] **Step 3: Append PianoRollWidget to ui/piano_roll_widget.py**

Open `ui/piano_roll_widget.py`. Append this class after `compute_key_layout()`:

```python
# ---------------------------------------------------------------------------
# PianoRollWidget — the full Qt widget
# ---------------------------------------------------------------------------

#: Colour constants for key states
_COLOUR_BG = QColor("#0a0a14")
_COLOUR_WHITE_KEY = QColor("#e8e8e8")
_COLOUR_BLACK_KEY = QColor("#1a1a1a")
_COLOUR_KEY_BORDER = QColor("#333333")
_COLOUR_HIT_LINE = QColor("#ffffff")
_COLOUR_NOTE_DEFAULT = QColor("#00bcd4")   # cyan — free mode playback

#: How much vertical height the piano keys occupy (fraction of total widget height)
_PIANO_HEIGHT_FRACTION = 0.20

#: Lookahead window in microseconds (3 s — must match MidiFilePlayer.LOOKAHEAD_US)
_LOOKAHEAD_US = 3_000_000


class PianoRollWidget(QWidget):
    """
    Falling-notes piano roll visualiser.

    Renders:
      1. Black background
      2. Falling note bars (upcoming notes scrolling down toward the hit line)
      3. Hit line (white horizontal rule at the top of the piano)
      4. White piano keys (bottom 20% of widget)
      5. Black piano keys (on top of white keys)
      6. Lit key overlays (colour-coded: cyan / green / amber / red)

    Update cycle:
      PracticeWindow calls set_state() every ~16ms (60fps) with the current
      playback clock and upcoming note list. set_state() triggers a repaint.

    Key colour meanings:
      Cyan   (#00bcd4) — currently playing (free mode)
      Green  (#00e676) — correctly hit (waiting mode)
      Amber  (#ffa726) — waiting for input (waiting mode)
      Red    (#ef5350) — wrong note pressed (200ms flash)
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._layout: dict[int, dict] = {}
        self._clock_us: int = 0
        self._upcoming_notes: list[tuple] = []
        self._lit_keys: dict[int, QColor] = {}  # note → colour override
        self.setMinimumSize(600, 200)
        # Compute initial layout (will be 0-width until first resize, that's fine)
        self._recompute_layout()

    def set_state(
        self,
        clock_us: int,
        upcoming_notes: list[tuple],
        lit_keys: dict[int, QColor],
    ) -> None:
        """
        Update display state and schedule a repaint.

        Args:
            clock_us:       current playback position in microseconds
            upcoming_notes: list of (timestamp_us, note, velocity, duration_us)
                            for notes within the lookahead window
            lit_keys:       {midi_note: QColor} overrides for key colours
        """
        self._clock_us = clock_us
        self._upcoming_notes = upcoming_notes
        self._lit_keys = lit_keys
        self.update()

    # ------------------------------------------------------------------
    # Qt event overrides
    # ------------------------------------------------------------------

    def resizeEvent(self, event):
        self._recompute_layout()
        super().resizeEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)  # pixel-sharp edges

        w = self.width()
        h = self.height()
        piano_h = max(60, int(h * _PIANO_HEIGHT_FRACTION))
        roll_h = h - piano_h
        hit_line_y = roll_h   # y coordinate of the hit line

        # 1. Black background
        painter.fillRect(0, 0, w, h, _COLOUR_BG)

        # 2. Falling note bars
        if self._upcoming_notes and self._layout:
            us_per_pixel = _LOOKAHEAD_US / roll_h if roll_h > 0 else 1
            for ts_us, note, vel, dur_us in self._upcoming_notes:
                key = self._layout.get(note)
                if key is None:
                    continue
                bar_top = int((ts_us - self._clock_us) / us_per_pixel)
                bar_h = max(4, int(dur_us / us_per_pixel))
                colour = self._lit_keys.get(note, _COLOUR_NOTE_DEFAULT)
                painter.fillRect(
                    int(key['x']), bar_top,
                    max(1, int(key['w']) - 1), bar_h,
                    colour,
                )

        # 3. Hit line
        painter.setPen(QPen(_COLOUR_HIT_LINE, 2))
        painter.drawLine(0, hit_line_y, w, hit_line_y)

        # 4. White piano keys (bottom section)
        piano_y = hit_line_y + 1
        for note, key in self._layout.items():
            if key['is_black']:
                continue
            colour = self._lit_keys.get(note, _COLOUR_WHITE_KEY)
            x, kw, kh = int(key['x']), max(1, int(key['w']) - 1), int(key['h'])
            painter.fillRect(x, piano_y, kw, kh, colour)
            painter.setPen(QPen(_COLOUR_KEY_BORDER, 1))
            painter.drawRect(x, piano_y, kw, kh)

        # 5. Black piano keys (drawn on top of white keys)
        for note, key in self._layout.items():
            if not key['is_black']:
                continue
            colour = self._lit_keys.get(note, _COLOUR_BLACK_KEY)
            x, kw, kh = int(key['x']), max(1, int(key['w'])), int(key['h'])
            painter.fillRect(x, piano_y, kw, kh, colour)

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _recompute_layout(self) -> None:
        if self.width() > 0 and self.height() > 0:
            piano_h = max(60, int(self.height() * _PIANO_HEIGHT_FRACTION))
            self._layout = compute_key_layout(self.width(), piano_h)
```

- [ ] **Step 4: Run all piano_roll_widget tests**

```bash
pytest tests/test_piano_roll_widget.py -v
```

Expected: all 18 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add ui/piano_roll_widget.py tests/test_piano_roll_widget.py
git commit -m "feat: add PianoRollWidget — QPainter falling notes + piano keys"
```

---

## Task 9: ui/practice_window.py — full practice window

`PracticeWindow` is the top-level `QMainWindow` that the user sees. It owns a `MidiFilePlayer`, embeds `PianoRollWidget`, provides the toolbar, wires all signals, and manages lit-key state.

**Files:**
- Create: `ui/practice_window.py`
- Create: `tests/test_practice_window.py`

- [ ] **Step 1: Write failing smoke tests**

Create `tests/test_practice_window.py`:

```python
"""Smoke tests for ui/practice_window.py."""
import pytest
from unittest.mock import MagicMock, patch
from PyQt5.QtWidgets import QFileDialog
from ui.practice_window import PracticeWindow


def make_practice_window(qtbot):
    """Build a PracticeWindow with fully mocked synth and midi."""
    mock_synth = MagicMock()
    mock_synth.init_practice_channel.return_value = None
    mock_synth.practice_note_on.return_value = None
    mock_synth.practice_note_off.return_value = None

    mock_midi = MagicMock()
    # Give signals real Qt signal-like objects so connect() calls succeed
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
    from PyQt5.QtGui import QColor
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
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/test_practice_window.py -v
```

Expected: ImportError — `ui.practice_window` does not exist.

- [ ] **Step 3: Create ui/practice_window.py**

Create `ui/practice_window.py`:

```python
"""
practice_window.py — standalone MIDI practice window.

Opens as a separate QMainWindow (not embedded in MainWindow).
Launched by the 🎹 Practice button in main_window.py.

Constructor: PracticeWindow(synth_engine, midi_handler, parent=None)
  synth_engine:  core.synth_engine.SynthEngine — shared FluidSynth instance
  midi_handler:  core.midi_handler.MidiHandler — shared MIDI input handler

Practice uses FluidSynth channel 15 (Grand Piano, reserved).
"""

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QSlider, QLabel, QComboBox, QFileDialog,
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor, QFont

from core.midi_file_player import MidiFilePlayer
from core.note_matcher import MatchResult
from ui.piano_roll_widget import PianoRollWidget

_PRACTICE_CHANNEL = 15   # FluidSynth channel reserved for practice playback


class PracticeWindow(QMainWindow):
    """
    Separate practice window — see module docstring for full description.

    Key responsibilities:
      - Owns the MidiFilePlayer (playback engine)
      - Wires player signals → FluidSynth (note_on/off) and widget (display)
      - Wires live MIDI key signals → note matching (waiting mode) and key lighting
      - Manages _lit_keys dict (note → QColor) passed to PianoRollWidget each frame
      - Handles mute toggle: suppresses FluidSynth calls, visuals always run
    """

    def __init__(self, synth_engine, midi_handler, parent=None):
        super().__init__(parent)
        self._synth = synth_engine
        self._midi = midi_handler
        self._player = MidiFilePlayer()
        self._muted = False
        self._lit_keys: dict[int, QColor] = {}   # note → colour for current frame

        self.setWindowTitle("SoundPad — Practice 🎹")
        self.setMinimumSize(900, 500)
        self._apply_dark_theme()

        self._build_ui()
        self._wire_signals()

        # Reserve FluidSynth channel 15 with Grand Piano
        self._synth.init_practice_channel(channel=_PRACTICE_CHANNEL)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        toolbar_widget = QWidget()
        toolbar_widget.setStyleSheet("background: #1a192a; border-bottom: 1px solid #2e2d3e;")
        toolbar_layout = QVBoxLayout(toolbar_widget)
        toolbar_layout.setContentsMargins(12, 8, 12, 8)
        toolbar_layout.setSpacing(6)
        toolbar_layout.addLayout(self._build_toolbar_row1())
        toolbar_layout.addLayout(self._build_toolbar_row2())
        root.addWidget(toolbar_widget)

        self._roll = PianoRollWidget()
        root.addWidget(self._roll, stretch=1)

    def _build_toolbar_row1(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(8)

        self._open_btn = QPushButton("📂 Open")
        self._open_btn.setCursor(Qt.PointingHandCursor)
        self._open_btn.clicked.connect(self._open_file)
        row.addWidget(self._open_btn)

        self._play_btn = QPushButton("▶ Play")
        self._play_btn.setCheckable(True)
        self._play_btn.setCursor(Qt.PointingHandCursor)
        self._play_btn.clicked.connect(self._toggle_play)
        row.addWidget(self._play_btn)

        self._stop_btn = QPushButton("⏹ Stop")
        self._stop_btn.setCursor(Qt.PointingHandCursor)
        self._stop_btn.clicked.connect(self._stop)
        row.addWidget(self._stop_btn)

        row.addSpacing(16)

        speed_lbl = QLabel("Speed:")
        speed_lbl.setStyleSheet("color: #a0a0c0; font-size: 11px;")
        row.addWidget(speed_lbl)

        self._speed_slider = QSlider(Qt.Horizontal)
        self._speed_slider.setRange(25, 150)
        self._speed_slider.setValue(100)
        self._speed_slider.setFixedWidth(120)
        self._speed_slider.valueChanged.connect(self._on_speed_changed)
        row.addWidget(self._speed_slider)

        self._speed_label = QLabel("100%")
        self._speed_label.setFixedWidth(40)
        self._speed_label.setStyleSheet("color: #e0e0f0; font-size: 11px;")
        row.addWidget(self._speed_label)

        row.addStretch()
        return row

    def _build_toolbar_row2(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(8)

        mode_lbl = QLabel("Mode:")
        mode_lbl.setStyleSheet("color: #a0a0c0; font-size: 11px;")
        row.addWidget(mode_lbl)

        self._mode_combo = QComboBox()
        self._mode_combo.addItems(["Waiting", "Free"])
        self._mode_combo.currentTextChanged.connect(self._on_mode_changed)
        row.addWidget(self._mode_combo)

        self._mute_btn = QPushButton("🔇 Mute")
        self._mute_btn.setCheckable(True)
        self._mute_btn.setCursor(Qt.PointingHandCursor)
        self._mute_btn.clicked.connect(self._on_mute_toggled)
        row.addWidget(self._mute_btn)

        row.addStretch()
        return row

    # ------------------------------------------------------------------
    # Signal wiring
    # ------------------------------------------------------------------

    def _wire_signals(self):
        # MidiFilePlayer → this window
        self._player.signals.note_on.connect(self._on_playback_note_on)
        self._player.signals.note_off.connect(self._on_playback_note_off)
        self._player.signals.playback_tick.connect(self._on_tick)
        self._player.signals.waiting_for.connect(self._on_waiting_for)
        self._player.signals.song_finished.connect(self._on_song_finished)

        # Live MIDI keyboard → this window
        self._midi.signals.key_pressed.connect(self._on_key_pressed)
        self._midi.signals.key_released.connect(self._on_key_released)

    # ------------------------------------------------------------------
    # Toolbar handlers
    # ------------------------------------------------------------------

    def _open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open MIDI File", "",
            "MIDI Files (*.mid *.midi);;All Files (*)"
        )
        if path:
            self._player.load(path)
            self._play_btn.setChecked(False)
            self._play_btn.setText("▶ Play")
            self._lit_keys.clear()
            self._roll.set_state(0, [], {})

    def _toggle_play(self, checked: bool):
        if checked:
            self._player.play()
            self._play_btn.setText("⏸ Pause")
        else:
            self._player.pause()
            self._play_btn.setText("▶ Play")

    def _stop(self):
        self._player.stop()
        self._play_btn.setChecked(False)
        self._play_btn.setText("▶ Play")
        self._lit_keys.clear()
        self._roll.set_state(0, [], {})

    def _on_speed_changed(self, value: int):
        self._speed_label.setText(f"{value}%")
        self._player.set_speed(value)

    def _on_mode_changed(self, mode: str):
        self._player.set_mode(mode.lower())

    def _on_mute_toggled(self, checked: bool):
        self._muted = checked

    # ------------------------------------------------------------------
    # Player signal handlers
    # ------------------------------------------------------------------

    def _on_playback_note_on(self, note: int, velocity: int):
        """Fired by MidiFilePlayer in free mode or when a waiting note is hit."""
        if not self._muted:
            self._synth.practice_note_on(_PRACTICE_CHANNEL, note, velocity)
        self._lit_keys[note] = QColor("#00bcd4")   # cyan — playing

    def _on_playback_note_off(self, note: int):
        """Fired by MidiFilePlayer (free mode note_off or on key_released)."""
        if not self._muted:
            self._synth.practice_note_off(_PRACTICE_CHANNEL, note)
        self._lit_keys.pop(note, None)

    def _on_tick(self, clock_us: int, upcoming_notes: list):
        """60fps update from MidiFilePlayer — refresh widget display."""
        self._roll.set_state(clock_us, upcoming_notes, dict(self._lit_keys))

    def _on_waiting_for(self, required_notes: list):
        """Clock has paused. Highlight required notes in amber."""
        for note in required_notes:
            self._lit_keys[note] = QColor("#ffa726")   # amber — waiting
        self._roll.set_state(self._player.clock_us, [], dict(self._lit_keys))

    def _on_song_finished(self):
        self._play_btn.setChecked(False)
        self._play_btn.setText("▶ Play")

    # ------------------------------------------------------------------
    # Live MIDI key handlers
    # ------------------------------------------------------------------

    def _on_key_pressed(self, note: int, velocity: int):
        """
        Live key press from the physical keyboard.
        In waiting mode: check against required notes; flash red on miss.
        Always lights the key (green for live play) then passes to player.
        """
        result = self._player.note_pressed(note, velocity)

        if result == MatchResult.MISS:
            # Red flash for 200ms then remove
            self._lit_keys[note] = QColor("#ef5350")
            QTimer.singleShot(200, lambda n=note: self._lit_keys.pop(n, None))
        elif result == MatchResult.HIT:
            # Green — will be lit while the note plays via _on_playback_note_on
            self._lit_keys[note] = QColor("#00e676")
        else:
            # Free mode / NOT_YET — light green for live key
            self._lit_keys[note] = QColor("#00e676")

        self._roll.set_state(
            self._player.clock_us,
            self._player._upcoming_snapshot(),
            dict(self._lit_keys),
        )

    def _on_key_released(self, note: int):
        self._player.note_released(note)
        # note_released emits note_off → _on_playback_note_off clears the lit key

    # ------------------------------------------------------------------
    # Theme
    # ------------------------------------------------------------------

    def _apply_dark_theme(self):
        self.setStyleSheet("""
            QMainWindow, QWidget { background: #12111a; color: #e0e0f0; }
            QPushButton {
                background: #1e1d2e; color: #a0a0c0;
                border: 1px solid #2e2d3e; border-radius: 6px;
                padding: 4px 10px; font-size: 12px;
            }
            QPushButton:hover  { background: #2a2940; border-color: #4a4870; }
            QPushButton:checked { background: #2e4a2e; color: #00e676; border-color: #00e676; }
            QComboBox {
                background: #1e1d2e; color: #ffffff;
                border: 1px solid #2e2d3e; border-radius: 6px;
                padding: 4px 10px;
            }
            QComboBox::drop-down { border: none; }
            QSlider::groove:horizontal { background: #2e2d3e; height: 4px; border-radius: 2px; }
            QSlider::handle:horizontal {
                background: #a0a0c0; width: 12px; height: 12px;
                margin: -4px 0; border-radius: 6px;
            }
        """)
```

- [ ] **Step 4: Add `_upcoming_snapshot()` to MidiFilePlayer**

`PracticeWindow._on_key_pressed` calls `self._player._upcoming_snapshot()` to get the current upcoming notes for an immediate widget refresh (outside the 60fps tick). Add this method to `MidiFilePlayer` in `core/midi_file_player.py`, inside the class, after `note_released`:

```python
    def _upcoming_snapshot(self) -> list:
        """Return the current lookahead window of upcoming note events."""
        return [
            e for e in self._events[self._event_idx:]
            if e[0] <= self._clock_us + self.LOOKAHEAD_US
        ]
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_practice_window.py -v
```

Expected: 11 tests PASSED.

- [ ] **Step 6: Run the full test suite**

```bash
pytest -v
```

Expected: all tests PASSED.

- [ ] **Step 7: Commit**

```bash
git add ui/practice_window.py core/midi_file_player.py tests/test_practice_window.py
git commit -m "feat: add practice_window.py — full practice UI with toolbar and signal wiring"
```

---

## Task 10: ui/main_window.py — add 🎹 Practice button

Wire the Practice button into the existing main window. The button appears between the pad grid and the master volume bar. Clicking it opens `PracticeWindow` as a separate, non-modal window.

**Files:**
- Modify: `ui/main_window.py`
- Modify: `tests/test_main_window_practice.py` (new test file)

- [ ] **Step 1: Write failing test**

Create `tests/test_main_window_practice.py`:

```python
"""Test that MainWindow opens PracticeWindow on button click."""
import pytest
from unittest.mock import MagicMock, patch
from PyQt5.QtCore import Qt


def make_main_window(qtbot):
    from core.config import Config
    from core.synth_engine import SynthEngine
    from core.scene_manager import SceneManager
    from core.midi_handler import MidiHandler
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
    from core.midi_handler import MidiSignals
    midi.signals = MidiSignals()

    win = MainWindow(config, synth, scenes, midi)
    qtbot.addWidget(win)
    return win


def test_practice_button_exists(qtbot):
    win = make_main_window(qtbot)
    assert hasattr(win, '_practice_btn')


def test_practice_button_opens_window(qtbot):
    win = make_main_window(qtbot)
    win.show()
    with patch('ui.main_window.PracticeWindow') as MockPW:
        mock_pw_instance = MagicMock()
        MockPW.return_value = mock_pw_instance
        qtbot.mouseClick(win._practice_btn, Qt.LeftButton)
        MockPW.assert_called_once()
        mock_pw_instance.show.assert_called_once()
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/test_main_window_practice.py -v
```

Expected: FAILED — `MainWindow` has no `_practice_btn`.

- [ ] **Step 3: Add import and button to main_window.py**

Open `ui/main_window.py`.

**Add import** at the top of the file, after the existing `from ui.settings_dialog import SettingsDialog` line:

```python
from ui.practice_window import PracticeWindow
```

**In `_build_main_view`**, find:

```python
        layout.addLayout(self._build_scene_bar())
        layout.addLayout(self._build_pad_grid())
        layout.addWidget(self._build_master_bar())
```

Replace with:

```python
        layout.addLayout(self._build_scene_bar())
        layout.addLayout(self._build_pad_grid())
        layout.addLayout(self._build_practice_row())
        layout.addWidget(self._build_master_bar())
```

**Add the new method** anywhere inside `MainWindow`, after `_build_master_bar`:

```python
    def _build_practice_row(self):
        row = QHBoxLayout()
        self._practice_btn = QPushButton("🎹 Practice")
        self._practice_btn.setCursor(Qt.PointingHandCursor)
        self._practice_btn.setStyleSheet(
            "QPushButton { background: #1e2a2e; color: #00bcd4; border: 1px solid #00bcd4; "
            "border-radius: 6px; padding: 6px 16px; font-size: 12px; }"
            "QPushButton:hover { background: #253535; }"
        )
        self._practice_btn.clicked.connect(self._open_practice)
        row.addStretch()
        row.addWidget(self._practice_btn)
        row.addStretch()
        return row

    def _open_practice(self):
        if not hasattr(self, '_practice_window') or self._practice_window is None:
            self._practice_window = PracticeWindow(self._synth, self._midi, parent=None)
        self._practice_window.show()
        self._practice_window.activateWindow()
        self._practice_window.raise_()
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_main_window_practice.py -v
```

Expected: 2 tests PASSED.

- [ ] **Step 5: Run the full test suite**

```bash
pytest -v
```

Expected: all tests PASSED (no regressions).

- [ ] **Step 6: Commit**

```bash
git add ui/main_window.py tests/test_main_window_practice.py
git commit -m "feat: add Practice button to MainWindow — opens PracticeWindow"
```

---

## Task 11: Create GitHub milestone and issues

Create one milestone and one issue per logical task group on `ajhochy/soundpad`. Each issue body contains full context so an AI agent can implement it without referring to any other document.

**Files:** None (GitHub only)

- [ ] **Step 1: Create the milestone**

```bash
gh api repos/ajhochy/soundpad/milestones \
  -X POST \
  -f title="Practice Mode v1" \
  -f description="Midiano-inspired MIDI song learning feature: falling notes over a 49-key piano, waiting mode (pauses until correct note pressed), speed control, mute toggle. Spec: docs/superpowers/specs/2026-04-06-practice-mode-design.md" \
  -f state="open" \
  --jq '.number' > /tmp/milestone_number.txt
cat /tmp/milestone_number.txt
```

Note the milestone number printed — you will use it as `<MILESTONE>` in every `gh issue create` command below.

- [ ] **Step 2: Create Issue 1 — Test scaffolding + mido**

```bash
MILESTONE=$(cat /tmp/milestone_number.txt)
gh issue create \
  --title "chore: install mido and set up pytest test scaffolding" \
  --milestone "$MILESTONE" \
  --label "chore" \
  --body "$(cat <<'EOF'
## Context
SoundPad is a PyQt5/FluidSynth pad launcher (Ubuntu 24.04). We are adding Practice Mode — a Midiano-style falling-notes MIDI learning window. This issue sets up the new dependency and test infrastructure needed for all subsequent Practice Mode issues.

**Spec:** \`docs/superpowers/specs/2026-04-06-practice-mode-design.md\`
**Plan:** \`docs/superpowers/plans/2026-04-06-practice-mode.md\` — Task 1

## Work Required

1. Run: \`pip3 install mido pytest pytest-qt\`
2. Add \`mido>=1.3\` to \`requirements.txt\`
3. Create \`tests/__init__.py\` (empty)
4. Create \`tests/conftest.py\` (documents that pytest-qt handles QApplication automatically — no manual setup needed)
5. Verify \`pytest --collect-only\` runs without errors

## Acceptance Criteria
- [ ] \`mido\` importable in the project Python environment
- [ ] \`pytest --collect-only\` exits 0
- [ ] \`requirements.txt\` includes \`mido>=1.3\`
EOF
)"
```

- [ ] **Step 3: Create Issue 2 — note_matcher.py**

```bash
MILESTONE=$(cat /tmp/milestone_number.txt)
gh issue create \
  --title "feat: implement core/note_matcher.py — Linthesia waiting-mode logic" \
  --milestone "$MILESTONE" \
  --label "enhancement" \
  --body "$(cat <<'EOF'
## Context
SoundPad Practice Mode pauses playback until the user plays the correct note(s) — ported from Linthesia \`src/PlayingState.cpp\` (GPL-2.0, https://github.com/linthesia/linthesia).

**Spec:** \`docs/superpowers/specs/2026-04-06-practice-mode-design.md\` — "Linthesia — Waiting Mode & Note Matching" section
**Plan:** \`docs/superpowers/plans/2026-04-06-practice-mode.md\` — Task 2

## Work Required

Create \`core/note_matcher.py\` with:

```python
NOTE_WINDOW_LENGTH_MS = 400  # from Linthesia NoteWindowLength

class MatchResult(Enum):
    HIT = "hit"
    MISS = "miss"
    NOT_YET = "not_yet"

def check(pressed_note: int, required_notes: set[int]) -> MatchResult: ...
def all_required_pressed(pressed_notes: set[int], required_notes: set[int]) -> bool: ...
```

Logic:
- \`check()\`: returns HIT if pressed_note in required_notes, MISS if required_notes non-empty and note not in it, NOT_YET if required_notes empty
- \`all_required_pressed()\`: returns True if required_notes ⊆ pressed_notes (handles chords)

No Qt. No mido. Pure Python.

Create \`tests/test_note_matcher.py\` with TDD tests first.

## Acceptance Criteria
- [ ] \`pytest tests/test_note_matcher.py\` — all tests pass
- [ ] No Qt or mido imports in the file
EOF
)"
```

- [ ] **Step 4: Create Issue 3 — midi_file_player.py parsing**

```bash
MILESTONE=$(cat /tmp/milestone_number.txt)
gh issue create \
  --title "feat: implement MIDI file parsing in core/midi_file_player.py" \
  --milestone "$MILESTONE" \
  --label "enhancement" \
  --body "$(cat <<'EOF'
## Context
Practice Mode loads \`.mid\` files using \`mido\`. This issue covers the pure-Python parsing half of \`core/midi_file_player.py\` — no Qt, no QObject.

**Spec:** \`docs/superpowers/specs/2026-04-06-practice-mode-design.md\` — "MidiFilePlayer / Responsibilities" section
**Plan:** \`docs/superpowers/plans/2026-04-06-practice-mode.md\` — Task 3

## Work Required

Create \`core/midi_file_player.py\` with these functions:

- \`_build_tempo_map(mid) -> list[tuple[int, int]]\` — scan all tracks for set_tempo messages; return sorted \`[(abs_tick, tempo_us), ...]\` starting with \`(0, 500000)\`
- \`_tick_to_us(abs_tick, tempo_map, ticks_per_beat) -> int\` — convert ticks to microseconds, handling tempo changes
- \`load_midi_file(path) -> list[tuple[int, int, int, int]]\` — returns \`[(timestamp_us, note, velocity, duration_us), ...]\` sorted by time

Track selection: skip track 0 if metadata-only; use first track with note_on events on a non-percussion channel (channel 9 excluded).

Create \`tests/test_midi_file_player_parsing.py\` — write tests first using \`mido\` to construct temp MIDI files in memory.

## Acceptance Criteria
- [ ] \`pytest tests/test_midi_file_player_parsing.py\` — all tests pass
- [ ] Percussion channel (9) is excluded
- [ ] Empty/metadata-only files return \`[]\`
- [ ] Tempo changes handled correctly
EOF
)"
```

- [ ] **Step 5: Create Issue 4 — MidiFilePlayer QObject**

```bash
MILESTONE=$(cat /tmp/milestone_number.txt)
gh issue create \
  --title "feat: implement MidiFilePlayer playback engine in core/midi_file_player.py" \
  --milestone "$MILESTONE" \
  --label "enhancement" \
  --body "$(cat <<'EOF'
## Context
The playback engine for Practice Mode. Appended to \`core/midi_file_player.py\` after the parsing functions (Issue 3 must be merged first).

**Spec:** \`docs/superpowers/specs/2026-04-06-practice-mode-design.md\` — "MidiFilePlayer" and "Data Flow" sections
**Plan:** \`docs/superpowers/plans/2026-04-06-practice-mode.md\` — Task 4
**Linthesia reference:** \`src/PlayingState.cpp\` — \`areAllRequiredKeysPressed()\` and the waiting-clock pattern

## Work Required

Append to \`core/midi_file_player.py\`:

```python
class _PlayerSignals(QObject):
    note_on = pyqtSignal(int, int)       # note, velocity
    note_off = pyqtSignal(int)           # note
    playback_tick = pyqtSignal(int, list) # clock_us, upcoming_notes
    waiting_for = pyqtSignal(list)       # list[int] required notes
    song_finished = pyqtSignal()

class MidiFilePlayer:
    TICK_MS = 16
    LOOKAHEAD_US = 3_000_000
    # play(), pause(), stop(), load(), set_speed(), set_mode()
    # note_pressed() -> MatchResult, note_released()
    # _tick() — QTimer callback
```

Key behaviour:
- **Free mode**: QTimer fires every 16ms; clock advances by 16ms × speed; notes fire via \`note_on\`/\`note_off\` signals
- **Waiting mode**: clock pauses when required notes arrive; resumes when \`note_pressed()\` returns HIT and \`_waiting_notes\` is empty; emits \`waiting_for\` with note list
- \`note_pressed()\` returns \`MatchResult\` from \`core.note_matcher\`
- \`_upcoming_snapshot()\` returns lookahead slice (used by PracticeWindow for instant widget refresh)

Create \`tests/test_midi_file_player_player.py\` — use \`qtbot\` fixture for Qt tests.

## Acceptance Criteria
- [ ] \`pytest tests/test_midi_file_player_player.py\` — all tests pass
- [ ] Waiting mode pauses timer; correct note resumes it
- [ ] Wrong note returns MISS; timer stays stopped
- [ ] \`song_finished\` signal emitted after last note in free mode
EOF
)"
```

- [ ] **Step 6: Create Issue 5 — midi_handler.py key signals**

```bash
MILESTONE=$(cat /tmp/milestone_number.txt)
gh issue create \
  --title "feat: add key_pressed/key_released signals to MidiHandler" \
  --milestone "$MILESTONE" \
  --label "enhancement" \
  --body "$(cat <<'EOF'
## Context
\`core/midi_handler.py\` currently handles pad notes, knobs, and fader. It ignores piano key note-on/note-off messages. Practice Mode needs to receive live key presses to drive waiting-mode matching and key lighting.

**Spec:** \`docs/superpowers/specs/2026-04-06-practice-mode-design.md\` — "MIDI Handler Changes" section
**Plan:** \`docs/superpowers/plans/2026-04-06-practice-mode.md\` — Task 5

## Work Required

**Modify \`core/midi_handler.py\`:**

1. Add to \`MidiSignals\`:
```python
key_pressed = pyqtSignal(int, int)   # note (0-127), velocity (0-127)
key_released = pyqtSignal(int)       # note (0-127)
```

2. In \`_on_midi_message\`, after the pad-note check:
   - Note-on not matching any pad + channel != 9 → emit \`key_pressed(note, velocity)\`
   - Note-off (0x80) + channel != 9 → emit \`key_released(note)\`
   - Note-on with velocity 0 + channel != 9 → also emit \`key_released(note)\`

Channel 9 is the percussion/drum channel (Launchkey pads). All other channels are piano keys.

Create \`tests/test_midi_handler_keys.py\`.

## Acceptance Criteria
- [ ] \`pytest tests/test_midi_handler_keys.py\` — all tests pass
- [ ] Existing pad/knob/fader behaviour unchanged (no regressions)
EOF
)"
```

- [ ] **Step 7: Create Issue 6 — synth_engine.py practice methods**

```bash
MILESTONE=$(cat /tmp/milestone_number.txt)
gh issue create \
  --title "feat: add practice channel methods to SynthEngine" \
  --milestone "$MILESTONE" \
  --label "enhancement" \
  --body "$(cat <<'EOF'
## Context
Practice Mode plays notes through FluidSynth channel 15 (reserved, separate from pad channels 0–7). \`SynthEngine\` needs three new public methods for this.

**Spec:** \`docs/superpowers/specs/2026-04-06-practice-mode-design.md\` — "FluidSynth Integration" section
**Plan:** \`docs/superpowers/plans/2026-04-06-practice-mode.md\` — Task 6

## Work Required

**Modify \`core/synth_engine.py\`** — add before \`shutdown()\`:

```python
def init_practice_channel(self, channel: int = 15) -> None:
    """Set up channel with Grand Piano (bank 0, program 0) using first loaded soundfont."""
    if not self._sf_ids:
        return
    sfid = next(iter(self._sf_ids.values()))
    self._fs.program_select(channel, sfid, 0, 0)

def practice_note_on(self, channel: int, note: int, velocity: int) -> None:
    self._fs.noteon(channel, note, velocity)

def practice_note_off(self, channel: int, note: int) -> None:
    self._fs.noteoff(channel, note)
```

Create \`tests/test_synth_engine_practice.py\` — mock FluidSynth to avoid needing real audio hardware.

## Acceptance Criteria
- [ ] \`pytest tests/test_synth_engine_practice.py\` — all tests pass
- [ ] Existing SynthEngine behaviour unchanged (no regressions)
EOF
)"
```

- [ ] **Step 8: Create Issue 7 — piano_roll_widget.py layout**

```bash
MILESTONE=$(cat /tmp/milestone_number.txt)
gh issue create \
  --title "feat: implement piano key layout algorithm in ui/piano_roll_widget.py" \
  --milestone "$MILESTONE" \
  --label "enhancement" \
  --body "$(cat <<'EOF'
## Context
The 49-key piano display requires correct black-key positioning. This uses the algorithm from Neothesia \`piano-layout/src/lib.rs\` (https://github.com/PolyMeilex/Neothesia), ported to Python.

**Spec:** \`docs/superpowers/specs/2026-04-06-practice-mode-design.md\` — "Neothesia — Piano Key Layout" section
**Plan:** \`docs/superpowers/plans/2026-04-06-practice-mode.md\` — Task 7

## Work Required

Create \`ui/piano_roll_widget.py\` with \`compute_key_layout(widget_width, piano_height) -> dict[int, dict]\`.

Piano range: MIDI 36 (C2) – MIDI 84 (C6) = 49 keys, 29 white + 20 black.

Return format: \`{midi_note: {'x': float, 'w': float, 'h': float, 'is_black': bool}}\`

**Neothesia algorithm:**
- \`white_w = widget_width / 29\`
- \`black_w = white_w × 0.625\`, \`black_h = piano_height × 0.635\`
- Per octave, split black keys into two groups:
  - **CDE group** (C#=semitone 1, D#=3): \`cde_block = 3×white_w / 5\`; C# at block 1 centre, D# at block 3 centre
  - **FGAB group** (F#=6, G#=8, A#=10): \`fgab_block = 4×white_w / 7\`; F# at block 1, G# at block 3, A# at block 5
- "Centre" = \`octave_c_x + block_index × block_size - black_w/2\`
- F is at \`octave_c_x + 3×white_w\` (the 4th white key of the octave)

Create \`tests/test_piano_roll_widget.py\` — test key counts, white key positions, black key positions using \`pytest.approx\`.

## Acceptance Criteria
- [ ] \`pytest tests/test_piano_roll_widget.py\` — layout tests pass
- [ ] 29 white keys, 20 black keys returned
- [ ] C2 (MIDI 36) starts at x=0
- [ ] C#2 position matches Neothesia formula exactly
EOF
)"
```

- [ ] **Step 9: Create Issue 8 — PianoRollWidget rendering**

```bash
MILESTONE=$(cat /tmp/milestone_number.txt)
gh issue create \
  --title "feat: implement PianoRollWidget QPainter rendering in ui/piano_roll_widget.py" \
  --milestone "$MILESTONE" \
  --label "enhancement" \
  --body "$(cat <<'EOF'
## Context
The visual widget for Practice Mode. Appended to \`ui/piano_roll_widget.py\` after \`compute_key_layout()\` (Issue 7 must be merged first).

**Spec:** \`docs/superpowers/specs/2026-04-06-practice-mode-design.md\` — "PianoRollWidget Rendering" section
**Plan:** \`docs/superpowers/plans/2026-04-06-practice-mode.md\` — Task 8

## Work Required

Append \`PianoRollWidget(QWidget)\` to \`ui/piano_roll_widget.py\`:

**Public API:**
- \`set_state(clock_us, upcoming_notes, lit_keys)\` — called every 16ms by PracticeWindow; schedules repaint
- \`resizeEvent\` — recomputes key layout on window resize

**\`paintEvent\` draw order:**
1. Black background (\`#0a0a14\`)
2. Falling note bars: \`bar_top = (note_time_us - clock_us) / us_per_pixel\`; bar height from duration; colour from \`lit_keys\` or default cyan \`#00bcd4\`
3. Hit line: white horizontal rule at \`y = roll_height\`
4. White piano keys (bottom 20% of widget) — grey \`#e8e8e8\` or lit colour
5. Black piano keys on top — dark \`#1a1a1a\` or lit colour

**Key colours:**
- Cyan \`#00bcd4\` — playing (free mode)
- Green \`#00e676\` — correctly hit (waiting)
- Amber \`#ffa726\` — awaiting input (waiting)
- Red \`#ef5350\` — wrong note (200ms flash)

Lookahead window: \`LOOKAHEAD_US = 3_000_000\` (3 seconds) spans full roll height.

Add smoke tests to \`tests/test_piano_roll_widget.py\` using \`qtbot\`.

## Acceptance Criteria
- [ ] Widget renders without crash (smoke test passes)
- [ ] \`set_state()\` with a note event triggers visual update without crash
- [ ] Layout recomputes on resize
EOF
)"
```

- [ ] **Step 10: Create Issue 9 — practice_window.py**

```bash
MILESTONE=$(cat /tmp/milestone_number.txt)
gh issue create \
  --title "feat: implement ui/practice_window.py — full practice window" \
  --milestone "$MILESTONE" \
  --label "enhancement" \
  --body "$(cat <<'EOF'
## Context
The top-level \`QMainWindow\` for Practice Mode. Depends on Issues 2–8 being merged first.

**Spec:** \`docs/superpowers/specs/2026-04-06-practice-mode-design.md\` — "PracticeWindow UI Layout" and "Toolbar Controls" sections
**Plan:** \`docs/superpowers/plans/2026-04-06-practice-mode.md\` — Task 9

## Work Required

Create \`ui/practice_window.py\` with \`PracticeWindow(QMainWindow)\`:

**Constructor:** \`PracticeWindow(synth_engine, midi_handler, parent=None)\`
- Calls \`synth_engine.init_practice_channel(channel=15)\`
- Instantiates \`MidiFilePlayer\` and \`PianoRollWidget\`
- Wires all signals

**Toolbar (2 rows):**
- Row 1: 📂 Open, ▶/⏸ Play toggle, ⏹ Stop, Speed slider (25–150, default 100), speed % label
- Row 2: Mode combo (Waiting/Free), 🔇 Mute toggle

**Signal wiring:**
- \`_player.signals.note_on\` → \`synth.practice_note_on(15, note, vel)\` (unless muted) + light key cyan
- \`_player.signals.note_off\` → \`synth.practice_note_off(15, note)\` (unless muted) + clear key
- \`_player.signals.playback_tick\` → \`_roll.set_state(clock_us, upcoming, lit_keys)\`
- \`_player.signals.waiting_for\` → light required keys amber + call \`_roll.set_state\`
- \`_player.signals.song_finished\` → reset Play button
- \`_midi.signals.key_pressed\` → \`_player.note_pressed()\`; HIT→green, MISS→red 200ms flash
- \`_midi.signals.key_released\` → \`_player.note_released()\`

Practice channel: FluidSynth channel 15 throughout. Mute suppresses all \`practice_note_on/off\` calls; visuals always run.

Create \`tests/test_practice_window.py\` with mocked synth+midi.

## Acceptance Criteria
- [ ] \`pytest tests/test_practice_window.py\` — all tests pass
- [ ] Mute suppresses FluidSynth calls
- [ ] Stop clears all lit keys
- [ ] Speed label updates live with slider
EOF
)"
```

- [ ] **Step 11: Create Issue 10 — main_window.py Practice button**

```bash
MILESTONE=$(cat /tmp/milestone_number.txt)
gh issue create \
  --title "feat: add 🎹 Practice button to MainWindow" \
  --milestone "$MILESTONE" \
  --label "enhancement" \
  --body "$(cat <<'EOF'
## Context
Final wiring — exposes Practice Mode to the user via the existing main pad grid window. Depends on Issue 9 being merged.

**Spec:** \`docs/superpowers/specs/2026-04-06-practice-mode-design.md\` — "Modified Files / ui/main_window.py" section
**Plan:** \`docs/superpowers/plans/2026-04-06-practice-mode.md\` — Task 10

## Work Required

**Modify \`ui/main_window.py\`:**

1. Add import: \`from ui.practice_window import PracticeWindow\`

2. In \`_build_main_view\`, add a call to \`self._build_practice_row()\` between the pad grid and master bar:
```python
layout.addLayout(self._build_scene_bar())
layout.addLayout(self._build_pad_grid())
layout.addLayout(self._build_practice_row())   # NEW
layout.addWidget(self._build_master_bar())
```

3. Add two new methods:
```python
def _build_practice_row(self):
    # centred 🎹 Practice button, cyan border style

def _open_practice(self):
    # Instantiate PracticeWindow once (reuse on re-click)
    # pass self._synth and self._midi
    # call show(), activateWindow(), raise_()
```

Create \`tests/test_main_window_practice.py\`.

## Acceptance Criteria
- [ ] \`pytest tests/test_main_window_practice.py\` — all tests pass
- [ ] \`pytest -v\` — full suite passes (no regressions)
- [ ] Button is visible in the main window between pad grid and master bar
EOF
)"
```

- [ ] **Step 12: Verify all issues and milestone created**

```bash
gh issue list --milestone "Practice Mode v1"
```

Expected: 10 issues listed.

- [ ] **Step 13: Commit the plan document**

```bash
git add docs/superpowers/plans/2026-04-06-practice-mode.md
git commit -m "docs: add Practice Mode implementation plan with GitHub issues and milestone"
```

---

## Self-Review Checklist

**Spec coverage:**
| Spec requirement | Task |
|---|---|
| load_midi_file() with tempo map | Task 3 |
| MidiFilePlayer — play/pause/stop/speed | Task 4 |
| Waiting mode state machine (Linthesia) | Tasks 2 + 4 |
| key_pressed / key_released signals | Task 5 |
| SynthEngine practice channel | Task 6 |
| 49-key piano layout (Neothesia) | Task 7 |
| Falling note bars + hit line + key colouring | Task 8 |
| Toolbar: Open, Play, Stop, Speed, Mode, Mute | Task 9 |
| PracticeWindow wiring | Task 9 |
| 🎹 Practice button in MainWindow | Task 10 |
| Separate window (QMainWindow) | Task 9 |
| FluidSynth channel 15 reserved | Tasks 6 + 9 |
| mido dependency | Task 1 |
| GitHub issues + milestone | Task 11 |

All spec requirements covered. ✓

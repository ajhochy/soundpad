# Practice Mode — Design Spec
**Date:** 2026-04-06
**Feature:** Midiano-inspired MIDI song learning mode
**App:** SoundPad (PyQt5/FluidSynth, Ubuntu 24.04, Novation Launchkey MK3 49)

---

## Overview

A separate Practice window that lets the user load a MIDI file and follow along on her physical keyboard. Notes appear as falling coloured bars above a 49-key on-screen piano. Two modes: **Free** (song plays at adjustable speed, she follows visually) and **Waiting** (song pauses until she plays each correct note). Audio playback through FluidSynth is optional via a mute toggle.

The core algorithms are ported from two open-source reference implementations:
- **Neothesia** (`piano-layout` crate, MIT-compatible portion) — piano key layout mathematics
- **Linthesia** (`PlayingState.cpp`, GPL-2.0) — waiting mode state machine and note-match timing window logic

---

## Reference Implementations

### Neothesia — Piano Key Layout
Repository: https://github.com/PolyMeilex/Neothesia
File: `piano-layout/src/lib.rs`

Black keys cannot be evenly distributed across octaves mathematically. Neothesia solves this by splitting each octave into two groups:
- **C-D-E group**: the 2 black keys are positioned within a block divided into 5 equal units
- **F-G-A-B group**: the 3 black keys are positioned within a block divided into 7 equal units

Black keys render at **62.5% the width** and **63.5% the height** of white keys.

This algorithm is ported verbatim to Python in `ui/piano_roll_widget.py`.

### Linthesia — Waiting Mode & Note Matching
Repository: https://github.com/linthesia/linthesia
File: `src/PlayingState.cpp`

Key logic to port:
- `areAllRequiredKeysPressed()` — playback clock pauses until all required notes in a chord are pressed
- `NOTE_WINDOW_LENGTH` = 400ms constant — timing tolerance window
- Note matching: pressed note is compared against required notes within the window; returns hit or miss
- Miss = key lights red briefly, clock stays paused; Hit = key lights green, note consumed, clock resumes

---

## Architecture

### New Files

| File | Responsibility |
|---|---|
| `core/midi_file_player.py` | Parses MIDI file with `mido`. Owns the playback clock (microseconds), time-sorted note event queue, speed multiplier, and waiting-mode state machine. No Qt imports, no drawing. |
| `core/note_matcher.py` | Self-contained module ported from Linthesia `PlayingState.cpp`. Given a live-pressed MIDI note and the set of currently-required notes, returns `HIT`, `MISS`, or `NOT_YET`. Defines `NOTE_WINDOW_LENGTH = 400` (ms). |
| `ui/piano_roll_widget.py` | Custom `QWidget`. All rendering via `QPainter`. Implements Neothesia's black-key layout algorithm for C2–C6 (49 keys). Draws falling note bars and lit keys. Accepts display state from `PracticeWindow` each frame. |
| `ui/practice_window.py` | Separate `QMainWindow`. Contains `PianoRollWidget` + toolbar. Owns the `MidiFilePlayer` instance. Wires player events and live MIDI signals to widget display updates. |

### Modified Files

| File | Change |
|---|---|
| `core/midi_handler.py` | Add `key_pressed = pyqtSignal(int, int)` (note, velocity) and `key_released = pyqtSignal(int)` signals. The MIDI callback already receives these messages but currently ignores non-pad note-ons. |
| `ui/main_window.py` | Add a 🎹 **Practice** button (bottom of window, above master volume bar). Clicking it instantiates and shows `PracticeWindow`. |

### New Dependency

```
mido
```

Pure-Python MIDI file parser. No C extensions. Install: `pip3 install mido`

---

## Data Flow

```
User clicks Play
       │
       ▼
QTimer (16ms / ~60fps)
       │
       ▼
MidiFilePlayer.tick(delta_ms × speed_multiplier)
       │
       ├─► [Free mode]   advance clock, trigger FluidSynth note-on/off (if not muted)
       │
       └─► [Waiting mode]
               │
               ├─ clock reaches required note window → PAUSE clock, highlight keys amber
               │
               └─ live key_pressed signal fires
                       │
                       ▼
               NoteMatcher.check(pressed_note, required_notes)
                       │
                       ├─ HIT   → key green, note consumed, resume clock
                       └─ MISS  → key red (200ms), clock stays paused
       │
       ▼
PianoRollWidget.set_state(playback_clock, active_notes, lit_keys)
       │
       ▼
widget.update() → QPainter redraws entire widget each frame
```

---

## PianoRollWidget Rendering

Each frame, `QPainter` draws in this order:
1. **Black background** — full widget
2. **Falling note bars** — for each upcoming note event within the lookahead window:
   - `y = (note_time_μs - playback_clock_μs) / μs_per_pixel`
   - Bar width = key width from layout; colour = track colour (cyan default)
   - Bars that have passed the hit line are discarded
3. **White piano keys** — bottom 20% of widget height, evenly spaced
4. **Black piano keys** — drawn on top, Neothesia layout algorithm
5. **Lit keys** — coloured overlay on active keys:
   - Cyan = currently playing (Free mode / muted playback visual)
   - Green = correctly hit (Waiting mode)
   - Amber = waiting for input (Waiting mode)
   - Red = wrong note pressed (200ms flash, Waiting mode)

**Hit line** — a thin white horizontal line at the top of the piano keys; notes must reach this line to count.

---

## MidiFilePlayer

### Responsibilities
- Parse `.mid` file using `mido.MidiFile`
- Flatten all events to a single time-sorted list: `[(timestamp_μs, note, velocity, duration_μs), ...]`
- Emit Qt signals consumed by `PracticeWindow`:
  - `note_on(note, velocity)` — trigger FluidSynth if not muted
  - `note_off(note)` — release FluidSynth note if not muted
  - `playback_tick(clock_μs, upcoming_notes)` — 60fps display update
  - `waiting_for(required_notes)` — clock paused, these notes are needed
  - `song_finished()` — reached end of file
- Accept `resume()` call from `PracticeWindow` when waiting-mode notes are satisfied

### Track Selection
Loads the first track that contains note events on a non-percussion channel (i.e. not channel 10). Many MIDI files have an empty or metadata-only track 0 — the player skips these and picks the first track with actual playable notes. No manual track selection UI in this version.

### Speed Range
25% – 150%, default 100%. Controlled by slider in `PracticeWindow` toolbar.

---

## PracticeWindow UI Layout

```
┌─────────────────────────────────────────────────────┐
│  [📂 Open]  [▶ Play] [⏹ Stop]  Speed: [──●──] 100%  │
│  Mode: [Waiting ▼]   [🔇 Mute]                       │
├─────────────────────────────────────────────────────┤
│                                                     │
│              (falling note bars)                    │
│                                                     │
│  ═══════════════ hit line ═══════════════           │
│  ┌─┬┬─┬─┬┬─┬┬─┬─┬┬─┬─┬┬─┬┬─┬─┬┬─┬─┬┬─┬┬─┬─┬┬─┐   │
│  │ ││ │ ││ ││ │ ││ │ ││ ││ │ ││ │ ││ ││ │ ││ │   │
│  │ ││ │ ││ ││ │ ││ │ ││ ││ │ ││ │ ││ ││ │ ││ │   │
│  └─┴┴─┴─┴┴─┴┴─┴─┴┴─┴─┴┴─┴┴─┴─┴┴─┴─┴┴─┴┴─┴─┴┴─┘   │
└─────────────────────────────────────────────────────┘
```

- Piano occupies bottom 20% of window height
- Toolbar is fixed height at top
- Falling notes fill the remaining space
- Minimum window size: 900 × 500px
- Window is resizable; layout scales proportionally

---

## Toolbar Controls

| Control | Type | Behaviour |
|---|---|---|
| 📂 Open | Button | `QFileDialog` filtered to `*.mid *.midi`. Loads file, stops any current playback, resets clock to 0. |
| ▶ Play / ⏸ Pause | Toggle button | Starts/pauses QTimer and playback clock. |
| ⏹ Stop | Button | Stops playback, resets clock to 0, clears all lit keys. |
| Speed | `QSlider` | Range 25–150, default 100. Label shows current % value. Updates `speed_multiplier` in real time. |
| Mode | `QComboBox` | "Waiting" / "Free". Switching mid-song takes effect immediately. |
| 🔇 Mute | Toggle button | Suppresses FluidSynth note-on/off calls. Visuals always run. |

---

## FluidSynth Integration

`PracticeWindow` receives a reference to the existing `SynthEngine` instance passed as a constructor argument: `PracticeWindow(synth_engine, midi_handler, parent=None)`. `MainWindow` holds both instances and passes them when opening the practice window. Practice playback uses a dedicated FluidSynth channel (channel 15, reserved) with program 0 (Grand Piano) by default. This avoids interfering with any active pad sounds. The mute toggle suppresses all `note_on` / `note_off` calls to FluidSynth for the practice channel only.

---

## MIDI Handler Changes

Two new signals added to `MidiSignals` in `core/midi_handler.py`:

```python
key_pressed = pyqtSignal(int, int)   # note (0-127), velocity (0-127)
key_released = pyqtSignal(int)       # note (0-127)
```

In `_on_midi_message`, note-on events on the keyboard channel (not channel 10, not pad notes) emit `key_pressed`. Note-off events emit `key_released`. These are consumed by `PracticeWindow` to drive waiting-mode note matching and live key highlighting.

---

## Future Features

The following are explicitly deferred. They are good candidates for a v2 of Practice Mode:

- **Sheet music / staff notation display** — render the song as scrolling standard notation alongside or instead of falling notes
- **Loop / repeat section** — let the user mark a range of bars to loop for focused practice
- **Note labelling** — show note names (C, D, E…) inside the falling bars or on the piano keys
- **Fingering guides** — show suggested finger numbers above keys
- **Progress statistics and scoring** — track hit rate, streaks, accuracy over time
- **Multi-track selection** — let the user choose which MIDI tracks to practice (melody only, both hands, etc.)

---

## File Structure After Feature

```
/opt/soundpad/
  soundpad.py
  ui/
    main_window.py       # modified: adds 🎹 Practice button
    preset_browser.py
    pad_widget.py
    settings_dialog.py
    piano_roll_widget.py # NEW
    practice_window.py   # NEW
  core/
    midi_handler.py      # modified: adds key_pressed / key_released signals
    synth_engine.py
    scene_manager.py
    config.py
    midi_file_player.py  # NEW
    note_matcher.py      # NEW
```

---

## Dependencies Summary

```bash
pip3 install mido
```

All other dependencies (`PyQt5`, `pyFluidSynth`, `python-rtmidi`) already installed per original spec.

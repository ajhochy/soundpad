# Current plan — Practice Mode v1

**Source of truth:** `docs/superpowers/plans/2026-04-06-practice-mode.md`

This file is a one-page index. The full plan with code blocks per task lives in the source-of-truth file.

## User request

Add a Midiano-style "Practice Mode" window: load a MIDI file, falling note bars scroll above a 49-key piano, in either Waiting mode (clock pauses until correct note is pressed) or Free mode (auto-plays at adjustable speed).

## Goal

A 9-year-old can load a `.mid` file, pick a mode, see exactly which key to press next, and learn the song hands-on.

## Non-goals (v2 later)

- Sheet music / staff notation
- Loop / repeat section
- Note name labels on keys
- Fingering numbers
- Scoring / streaks / accuracy stats
- Multi-track / hand selection

## Constraints

- PyQt5 only — no new GUI library
- Pure-Python MIDI parsing (mido) — no C extensions
- FluidSynth channel 15 reserved for practice (channels 0–7 are pads)
- Must not regress existing pad/knob/fader behaviour

## Phases / issues

| Plan task | Module(s) | GitHub issue |
|---|---|---|
| Task 1 | `requirements.txt`, `tests/` | Issue 1 |
| Task 2 | `core/note_matcher.py` | Issue 2 |
| Task 3 | `core/midi_file_player.py` parsing | Issue 3 |
| Task 4 | `core/midi_file_player.py` MidiFilePlayer | Issue 4 |
| Task 5 | `core/midi_handler.py` signals | Issue 5 |
| Task 6 | `core/synth_engine.py` practice methods | Issue 6 |
| Task 7 | `ui/piano_roll_widget.py` layout | Issue 7 |
| Task 8 | `ui/piano_roll_widget.py` PianoRollWidget | Issue 8 |
| Task 9 | `ui/practice_window.py` | Issue 9 |
| Task 10 | `ui/main_window.py` button | Issue 10 |

## Validation plan

- TDD per task: failing test → implementation → green test.
- Full `pytest -v` green between every issue.
- Headless widget smoke screenshots saved to `tests/smoke/_artifacts/`.
- Final manual smoke by user on Ubuntu target with real Launchkey.

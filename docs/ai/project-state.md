# Project State — soundpad

## Current focus

Practice Mode v1 — Midiano-inspired MIDI song learning window. Implemented end-to-end; awaiting manual smoke on the Ubuntu target before merge.
Spec: `docs/superpowers/specs/2026-04-06-practice-mode-design.md`
Plan: `docs/superpowers/plans/2026-04-06-practice-mode.md`

## Active branch / PR

- Branch: `workflow/run-2026-05-20-practice-mode` (run-scoped). No uncommitted changes.
- PR: draft [PR #34](https://github.com/ajhochy/soundpad/pull/34) open. Merging closes #24–#33.

## In progress

- Practice Mode v1 ready for manual smoke on the Ubuntu target box (`aj@192.168.0.50`, real Launchkey MK3 49).

## Risks / known issues

- pyFluidSynth requires native libfluidsynth at import time. On macOS dev box use `DYLD_LIBRARY_PATH=/opt/homebrew/lib`; on the target Ubuntu box the apt package supplies it.
- macOS Qt `offscreen` plugin segfaults (Bus error) when a `QMainWindow` is shown/grabbed; `tests/conftest.py` falls back `offscreen→minimal` on macOS (`SOUNDPAD_KEEP_QT_PLATFORM=1` to force offscreen). Linux uses offscreen unchanged.
- `MidiHandler` emits the new `key_pressed`/`key_released` signals alongside the existing `note_on`/`note_off` (no rename, no regression to the pad-sound path).

## Test status

- 102 / 102 pytest green on Python 3.12 (95 unit/widget + 6 end-to-end smoke + regression).
- Run command: `DYLD_LIBRARY_PATH=/opt/homebrew/lib QT_QPA_PLATFORM=offscreen pytest -v` from repo root in `.venv` (see [[testing-guide]]).
- Headless screenshots saved to `tests/smoke/_artifacts/` validate the full UI.

## Next step

Run manual smoke on `aj@192.168.0.50` per `docs/testing/manual-smoke.md`. Merge PR #34 when smoke is green.

---
**Run history:** one file per run under `docs/ai/runs/` (surfaced as `ai-runs/`). This snapshot is overwritten in place.

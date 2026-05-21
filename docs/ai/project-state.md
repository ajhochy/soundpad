# Project state

**Last updated:** 2026-05-20

## Current focus

Practice Mode v1 — Midiano-inspired MIDI song learning window.
Spec: `docs/superpowers/specs/2026-04-06-practice-mode-design.md`
Plan: `docs/superpowers/plans/2026-04-06-practice-mode.md`

## Active branch / PR

- Branch: `workflow/run-2026-05-20-practice-mode` (run-scoped)
- PR: to be opened after all 10 issues are implemented and green locally

## Recently completed

- M1–M4 milestones (issues #1–#23) — all closed, shipped.
- Design spec and implementation plan committed (`b14aad4`, `bf648b2`).
- **Practice Mode v1** (milestone #5) — issues #24–#33 implemented and locally green.
  - 95 unit/widget tests + 6 end-to-end smoke tests = 102 pass on Python 3.12.
  - Headless screenshots saved to `tests/smoke/_artifacts/` validate full UI.

## In progress

- Practice Mode v1 ready for manual smoke on the Ubuntu target box.

## Risks

- pyFluidSynth requires native libfluidsynth at import time. On macOS dev box use `DYLD_LIBRARY_PATH=/opt/homebrew/lib`; on the target Ubuntu box the apt package supplies it.
- `MidiHandler` already emits `note_on`/`note_off`; the new `key_pressed`/`key_released` signals are added alongside (no rename, no regression).
- pytest-qt needs a real `QApplication`; tests run with `QT_QPA_PLATFORM=offscreen` so no display is required.

## Test status

- pytest target: `pytest -v` (run from repo root, in `.venv` with `DYLD_LIBRARY_PATH=/opt/homebrew/lib QT_QPA_PLATFORM=offscreen`).
- No existing test suite before Practice Mode work began.

## Next step

Open draft PR for `workflow/run-2026-05-20-practice-mode`, then run manual smoke on `aj@192.168.0.50` per `docs/testing/manual-smoke.md`. Merge when smoke is green.

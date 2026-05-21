# Decisions log

## 2026-05-20 — Run all 10 Practice Mode issues on one workflow run branch

**Context:** The 10 issues are sequentially dependent (Issue 4 imports from Issue 2, Issue 8 from Issue 7, Issue 9 from Issues 2–8, etc.).

**Alternative considered:** Per-issue branches and per-issue draft PRs.

**Decision:** Single feature branch `workflow/run-2026-05-20-practice-mode`, all 10 commits on it, one combined draft PR at the end.

**Consequences:** Less granular history but matches the dependency chain. Reviewer reads sequential commits in order.

## 2026-05-20 — `key_pressed`/`key_released` added alongside existing `note_on`/`note_off`

**Context:** `MidiHandler` already emits `note_on(note, velocity)` and `note_off(note)` for keyboard keys (used by `SynthEngine.play_note`).

**Alternative considered:** Rename existing signals to match the spec.

**Decision:** Add the new `key_pressed`/`key_released` signals alongside, emitting from the same code path. Existing consumers continue to use `note_on`/`note_off`; Practice Mode uses the new names.

**Consequences:** No regressions to pad sound playback; spec terminology preserved in Practice Mode code.

## 2026-05-20 — pyFluidSynth tests run against real lib via DYLD_LIBRARY_PATH on macOS

**Context:** `core/synth_engine.py` calls `ctypes.CDLL` at module import time. Mocking via `sys.modules['fluidsynth']` doesn't help because that path runs before the patch.

**Alternative considered:** Refactor synth_engine to lazy-load the ctypes lib.

**Decision:** Install `fluid-synth` via Homebrew on macOS dev box; set `DYLD_LIBRARY_PATH=/opt/homebrew/lib`. Tests of synth_engine still patch `fluidsynth.Synth` to avoid touching audio hardware.

**Consequences:** Tests run identically on Linux (system lib found automatically) and on macOS (with the env var). No code changes required to synth_engine.

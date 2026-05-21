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

## 2026-05-20 — Sync MidiFilePlayer mode to mode combo on PracticeWindow init

**Context:** `QComboBox.currentTextChanged` does NOT fire when `setCurrentText()` is called with the value already selected. The combo defaults to "Waiting" at construction time, so the player would stay in its constructor-default "free" mode until the user manually toggles to "Free" and back.

**Alternative considered:** Set the combo to "Free" first then "Waiting" so the change fires. Brittle.

**Decision:** Explicitly call `self._player.set_mode(self._mode_combo.currentText().lower())` at the end of `PracticeWindow.__init__` after wiring. Backed by a dedicated regression test `test_player_mode_matches_combo_default_on_init`.

**Consequences:** Practice Mode now actually starts in Waiting mode by default, matching the visible UI state. Two-line fix in `practice_window.py`.

## 2026-05-20 — Run targets Python 3.10+

**Context:** Existing `core/scene_manager.py` uses `dict | None` type unions, requiring Python 3.10+. Local macOS dev box had Python 3.9.6 which broke `from core.scene_manager import SceneManager`. Ubuntu 24.04 target ships Python 3.12.

**Alternative considered:** Add `from __future__ import annotations` to `scene_manager.py`. Out of scope for Practice Mode and risks behavioural change elsewhere.

**Decision:** Recreate local `.venv` against `python3.12` from Homebrew. Run-state documented in `docs/ai/testing-guide.md` and `AGENTS.md`.

**Consequences:** Project effectively requires Python 3.10+ — already true for the target deployment. Local dev box matches target now.

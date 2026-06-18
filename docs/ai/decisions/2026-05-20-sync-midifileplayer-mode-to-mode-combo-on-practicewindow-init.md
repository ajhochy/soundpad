---
date: 2026-05-20
repo: soundpad
tags: [decision, soundpad]
---

# Sync MidiFilePlayer mode to mode combo on PracticeWindow init

**Context:** `QComboBox.currentTextChanged` does NOT fire when `setCurrentText()` is called with the value already selected. The combo defaults to "Waiting" at construction time, so the player would stay in its constructor-default "free" mode until the user manually toggles to "Free" and back.

**Alternative considered:** Set the combo to "Free" first then "Waiting" so the change fires. Brittle.

**Decision:** Explicitly call `self._player.set_mode(self._mode_combo.currentText().lower())` at the end of `PracticeWindow.__init__` after wiring. Backed by a dedicated regression test `test_player_mode_matches_combo_default_on_init`.

**Consequences:** Practice Mode now actually starts in Waiting mode by default, matching the visible UI state. Two-line fix in `practice_window.py`.

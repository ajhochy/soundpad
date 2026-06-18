---
date: 2026-05-20
repo: soundpad
tags: [decision, soundpad]
---

# `key_pressed`/`key_released` added alongside existing `note_on`/`note_off`

**Context:** `MidiHandler` already emits `note_on(note, velocity)` and `note_off(note)` for keyboard keys (used by `SynthEngine.play_note`).

**Alternative considered:** Rename existing signals to match the spec.

**Decision:** Add the new `key_pressed`/`key_released` signals alongside, emitting from the same code path. Existing consumers continue to use `note_on`/`note_off`; Practice Mode uses the new names.

**Consequences:** No regressions to pad sound playback; spec terminology preserved in Practice Mode code.

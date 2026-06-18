---
date: 2026-05-20
repo: soundpad
tags: [decision, soundpad]
---

# pyFluidSynth tests run against real lib via DYLD_LIBRARY_PATH on macOS

**Context:** `core/synth_engine.py` calls `ctypes.CDLL` at module import time. Mocking via `sys.modules['fluidsynth']` doesn't help because that path runs before the patch.

**Alternative considered:** Refactor synth_engine to lazy-load the ctypes lib.

**Decision:** Install `fluid-synth` via Homebrew on macOS dev box; set `DYLD_LIBRARY_PATH=/opt/homebrew/lib`. Tests of synth_engine still patch `fluidsynth.Synth` to avoid touching audio hardware.

**Consequences:** Tests run identically on Linux (system lib found automatically) and on macOS (with the env var). No code changes required to synth_engine.

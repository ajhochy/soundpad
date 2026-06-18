---
date: 2026-05-20
repo: soundpad
tags: [decision, soundpad]
---

# Run targets Python 3.10+

**Context:** Existing `core/scene_manager.py` uses `dict | None` type unions, requiring Python 3.10+. Local macOS dev box had Python 3.9.6 which broke `from core.scene_manager import SceneManager`. Ubuntu 24.04 target ships Python 3.12.

**Alternative considered:** Add `from __future__ import annotations` to `scene_manager.py`. Out of scope for Practice Mode and risks behavioural change elsewhere.

**Decision:** Recreate local `.venv` against `python3.12` from Homebrew. Run-state documented in `docs/ai/testing-guide.md` and `AGENTS.md`.

**Consequences:** Project effectively requires Python 3.10+ — already true for the target deployment. Local dev box matches target now.

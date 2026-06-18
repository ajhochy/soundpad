---
date: 2026-05-20
repo: soundpad
tags: [decision, soundpad]
---

# Run all 10 Practice Mode issues on one workflow run branch

**Context:** The 10 issues are sequentially dependent (Issue 4 imports from Issue 2, Issue 8 from Issue 7, Issue 9 from Issues 2–8, etc.).

**Alternative considered:** Per-issue branches and per-issue draft PRs.

**Decision:** Single feature branch `workflow/run-2026-05-20-practice-mode`, all 10 commits on it, one combined draft PR at the end.

**Consequences:** Less granular history but matches the dependency chain. Reviewer reads sequential commits in order.

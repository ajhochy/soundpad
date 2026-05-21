# AGENTS.md — SoundPad

## First files to read

- `CLAUDE.md` — SSH key + deployment notes
- `docs/ai/project-state.md`
- `docs/ai/architecture.md`
- `docs/ai/repo-map.md`
- `docs/ai/testing-guide.md`
- `docs/ai/current-plan.md`
- `docs/ai/decisions.md`
- `docs/superpowers/specs/2026-04-06-practice-mode-design.md` (active feature spec)
- `docs/superpowers/plans/2026-04-06-practice-mode.md` (implementation plan)

## Data-safety rules

- Never commit `.env`, soundfont binaries, scene/config JSON dumps, audio dumps, or any user data.
- The `~/.ssh/id_soundpad` private key stays local and never gets committed.
- Hardcoding passwords, IPs, or usernames is forbidden (see `CLAUDE.md`).

## Testing rules

- Local: use `.venv` with `pip install -r requirements.txt mido pytest pytest-qt`.
- macOS needs `DYLD_LIBRARY_PATH=/opt/homebrew/lib` for `fluidsynth` to load.
- Run pytest with `QT_QPA_PLATFORM=offscreen` for headless Qt widget smoke.
- TDD is required for every new module — write the failing tests first.
- Acceptance criteria from the GitHub issue are the contract; tests verify them strictly.

## Git/manual-merge rules

- Never push to `main` directly; every workflow run goes through a feature branch + draft PR.
- Never run destructive git ops (force push, reset --hard, branch -D) without explicit user request.
- Merge is always a manual human step after CI green + manual smoke pass.

## Memory-update rules

- After each green issue: append to `docs/ai/project-state.md`.
- For non-obvious architectural choices: append a dated decision to `docs/ai/decisions.md`.
- Practice Mode feature memory lives in `docs/superpowers/{specs,plans}/`.

## Target deployment

- Linux box at `aj@192.168.0.50` (account `kids` for desktop).
- Deploy with `bash install.sh aj@192.168.0.50 kids`.
- All manual smoke is on the Linux box with a real Launchkey MK3 49 attached.

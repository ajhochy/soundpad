# Testing guide

## Install / setup

```bash
# macOS dev
brew install fluid-synth
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt mido pytest pytest-qt python-rtmidi pyFluidSynth
```

## Run tests (headless, offscreen Qt)

```bash
source .venv/bin/activate
DYLD_LIBRARY_PATH=/opt/homebrew/lib QT_QPA_PLATFORM=offscreen pytest -v
```

The `DYLD_LIBRARY_PATH` is only required on macOS so pyFluidSynth can find `libfluidsynth.dylib`.
On the Linux target box, neither var is needed.

## Smoke-test ladder

1. **Static**: `python3 -m py_compile <file>` for syntax sanity.
2. **Unit (pure logic)**: `pytest tests/test_note_matcher.py tests/test_midi_file_player_parsing.py tests/test_piano_roll_widget.py::test_returns_all_49_keys -v` (no Qt needed for layout function).
3. **Widget (Qt offscreen)**: `pytest tests/test_practice_window.py tests/test_piano_roll_widget.py tests/test_main_window_practice.py -v` — uses `qtbot` fixture from `pytest-qt`.
4. **Visual smoke (headless screenshot)**: rendering script that builds widgets in offscreen Qt and saves a PNG via `widget.grab().save(...)` — see `tests/smoke/render_practice_window.py`.
5. **Manual smoke**: `docs/testing/manual-smoke.md` on the Ubuntu box with the real Launchkey.

## Acceptance contracts

Each Practice Mode issue has its acceptance criteria captured in `docs/ai/contracts/issue-N.json` with a pointer to the failing test command. Coding agents must make the contract tests pass.

## Manual-only checks

- Launchkey MK3 49 pad/knob/fader bindings still work after changes to `midi_handler.py`.
- Audio output through PipeWire still works (`pulseaudio` driver is what FluidSynth uses).
- Practice mode visuals on a real display at 900×500+ resolution.

# Repo map

```
soundpad/
├── soundpad.py           # entry point
├── install.sh            # SSH deploy to aj@192.168.0.50
├── download_soundfonts.sh
├── requirements.txt
├── CLAUDE.md             # SSH + deploy notes
├── AGENTS.md             # this workflow context
├── core/
│   ├── config.py
│   ├── synth_engine.py   # FluidSynth wrapper (8 pad channels + channel 15 practice)
│   ├── scene_manager.py
│   ├── midi_handler.py   # rtmidi callback → Qt signals
│   ├── note_matcher.py   # NEW (Practice Mode — Linthesia port)
│   └── midi_file_player.py  # NEW (Practice Mode — mido parsing + QObject playback)
├── ui/
│   ├── main_window.py    # main pad grid + (NEW) Practice button
│   ├── pad_widget.py
│   ├── preset_browser.py
│   ├── settings_dialog.py
│   ├── piano_roll_widget.py  # NEW (Practice Mode — Neothesia layout + QPainter)
│   └── practice_window.py    # NEW (Practice Mode — QMainWindow)
├── tests/                # NEW (pytest + pytest-qt)
└── docs/
    ├── ai/               # workflow memory (this skill's home)
    ├── specs/2026-04-06-soundpad-design.md
    ├── superpowers/specs/2026-04-06-practice-mode-design.md
    └── superpowers/plans/2026-04-06-practice-mode.md
```

## Generated / ignored

- `__pycache__/`, `*.pyc`, `.venv/`, `.superpowers/`, `.agent-stack/` are gitignored.

## Common searches

- New Practice Mode module → `core/note_matcher.py`, `core/midi_file_player.py`
- Practice UI → `ui/piano_roll_widget.py`, `ui/practice_window.py`
- FluidSynth channel 15 wiring → `core/synth_engine.py` (`init_practice_channel`)
- MIDI handler signals → `core/midi_handler.py` `MidiSignals` class

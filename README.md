# SoundPad 🎹

A simple, child-friendly soundfont player built for the **Novation Launchkey MK3 49**.
Replaces QSynth with an interface a kid can use without help.

## What it does

- **8 pad grid** — each pad holds a sound (piano, strings, drums, etc.)
- **Physical pads toggle sounds on/off** — press a pad on the keyboard to activate/deactivate that layer
- **Layer any combination** — all active pads play simultaneously
- **Knobs control per-pad volume** — Knob 1 = Pad 1, Knob 2 = Pad 2, etc.
- **Fader controls master volume**
- **Save/load named scenes** — "School Practice", "Fun Sounds", etc.
- **Auto-launches on login**

## Stack

| Layer | Library |
|-------|---------|
| UI | PyQt5 |
| MIDI | python-rtmidi |
| Audio | pyFluidSynth (FluidSynth 2.x) |
| Audio routing | PipeWire via pw-jack |

## Project Structure

```
soundpad.py            Entry point
core/
  config.py            MIDI defaults + config file paths
  synth_engine.py      FluidSynth wrapper, 8-channel pad management
  midi_handler.py      rtmidi background thread, emits Qt signals
  scene_manager.py     Load/save named scenes to ~/.config/soundpad/
ui/
  main_window.py       Screen 1: pad grid, scene bar, master volume
  preset_browser.py    Screen 2: instrument picker (opened from ✎ on each pad)
  pad_widget.py        Individual pad tile component
  settings_dialog.py   MIDI remap (⚙ button, tucked away)
```

## MIDI Defaults (Launchkey MK3 49)

| Control | MIDI Message | Action |
|---------|-------------|--------|
| Pads 1–8 | Note-on Ch 10, notes 96–103 (Session mode) | Toggle pad on/off |
| Knobs 1–8 | CC 21–28, Ch 1 | Per-pad volume |
| Fader | CC 9, Ch 1 | Master volume |

All mappings are remappable via ⚙ Settings > Learn.

## Install on the target machine

```bash
bash install.sh
```

This copies the app to `/opt/soundpad/`, installs dependencies, and sets up
autostart for the `kids` account on `192.168.0.50`.

## Manual run (for testing)

```bash
pw-jack python3 soundpad.py
```

## Dependencies

```bash
sudo apt install python3-pyqt5 python3-pip libfluidsynth-dev
pip3 install pyFluidSynth python-rtmidi
```

## Design spec

See [`docs/superpowers/specs/2026-04-06-soundpad-design.md`](docs/superpowers/specs/2026-04-06-soundpad-design.md)

## Notes for Codex / AI agents

- `synth_engine.py` contains a `TODO` in `_build_catalogue` — the preset enumeration
  needs to use FluidSynth's `fluid_sfont_iteration_start/next` API properly.
  The current implementation is a placeholder that needs completing.
- `settings_dialog.py` has a `TODO` in `_start_learn` — MIDI learn mode needs
  to hook into `MidiHandler` to capture the next incoming CC/note.
- All FluidSynth calls must happen on the **main thread** (not the MIDI thread).
  The MIDI thread only emits Qt signals.

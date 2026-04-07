# SoundPad

A simple, child-friendly soundfont player for the **Novation Launchkey MK3 49**.
Replaces QSynth with an interface a kid can use without help.

## What it does

- **8 pad grid** — each pad holds a sound (piano, strings, drums, etc.)
- **Physical pads toggle sounds on/off** — press a pad on the keyboard to activate/deactivate that layer
- **Layer any combination** — all active pads play simultaneously
- **Knobs control per-pad volume** — Knob 1 = Pad 1, Knob 2 = Pad 2, etc.
- **Fader controls master volume**
- **Save/load named scenes** — "School Practice", "Fun Sounds", etc.
- **Instrument browser** — search and filter 1000+ sounds across all loaded soundfonts
- **Auto-launches on login**

## Stack

| Layer | Library |
|-------|---------|
| UI | PyQt5 |
| MIDI | python-rtmidi |
| Audio | pyFluidSynth (FluidSynth 2.x) |
| Audio routing | PipeWire (PulseAudio compatibility layer) |

## Project structure

```
soundpad.py            Entry point
core/
  config.py            MIDI defaults + config file paths
  synth_engine.py      FluidSynth wrapper, 8-channel pad management, instrument catalogue
  midi_handler.py      rtmidi background thread, emits Qt signals
  scene_manager.py     Load/save named scenes to ~/.config/soundpad/
ui/
  main_window.py       Screen 1: pad grid, scene bar, master volume
  preset_browser.py    Screen 2: instrument picker (opened from ✏️ on each pad)
  pad_widget.py        Individual pad tile component
  settings_dialog.py   MIDI remap (⚙ button)
```

## Install on a target Ubuntu machine

```bash
bash install.sh user@host [desktop-user]
```

**Examples:**
```bash
bash install.sh aj@192.168.0.50 kids    # deploy to "kids" account
bash install.sh pi@raspberrypi.local pi  # Raspberry Pi
```

Or use environment variables:
```bash
export SOUNDPAD_HOST=aj@192.168.0.50
export SOUNDPAD_USER=kids
bash install.sh
```

`install.sh` will:
1. Copy app files to `/opt/soundpad/` on the target machine
2. Install system dependencies via `apt` (PyQt5, FluidSynth, fonts)
3. Create a Python venv and install Python packages
4. Download soundfonts into `/usr/share/sounds/sf2/` (failures are non-fatal — the app works with any soundfont)
5. Set up autostart for the desktop user
6. Install an app launcher icon in the applications menu

**Requirements on this machine:** `ssh`, `rsync`
**Requirements on target:** Ubuntu 22.04+, PipeWire with PulseAudio support

SSH key auth is recommended: `ssh-copy-id user@host`

## Manual run (for testing)

```bash
python3 soundpad.py
```

## Manual install (no install.sh)

```bash
# System dependencies
sudo apt install python3-pyqt5 python3-pip libfluidsynth-dev \
    fluid-soundfont-gm fluid-soundfont-gs \
    fonts-noto fonts-noto-color-emoji

# Python packages
pip3 install pyFluidSynth python-rtmidi PyQt5
```

Soundfonts go in `/usr/share/sounds/sf2/` (any `.sf2` file is auto-loaded).

## MIDI defaults (Launchkey MK3 49 — Drum mode)

| Control | MIDI message | Action |
|---------|-------------|--------|
| Pads 1–8 | Note-on Ch 10, notes 40–47 (Drum mode) | Toggle pad on/off |
| Knobs 1–8 | CC 21–28, Ch 1 | Per-pad volume |
| Fader | CC 9, Ch 1 | Master volume |

All mappings are remappable via ⚙ Settings > Learn.

> **Note:** The Launchkey must be in **Drum mode** for the pads to send notes 40–47.
> In Session mode the pads send notes 96–103, which can be remapped in Settings.

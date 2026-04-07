# SoundPad

A simple, child-friendly soundfont player for MIDI keyboards.
Designed for the Novation Launchkey MK3 49, but works with any MIDI keyboard via the built-in remap.

## What it does

- **8 pad grid** — each pad holds a sound (piano, strings, drums, etc.)
- **Physical pads toggle sounds on/off** — press a pad on the keyboard to activate/deactivate that layer
- **Layer any combination** — all active pads play simultaneously
- **Knobs control per-pad volume** — Knob 1 = Pad 1, Knob 2 = Pad 2, etc.
- **Fader controls master volume**
- **Save/load named scenes** — "School Practice", "Fun Sounds", etc.
- **Instrument browser** — search and filter 1000+ sounds across all loaded soundfonts
- **Auto-launches on login** (optional)

## Requirements

- Ubuntu 22.04+ (or any Linux with PipeWire and PulseAudio support)
- A USB MIDI keyboard (any device works — remap controls in ⚙ Settings)
- Python 3.10+

## Install

```bash
git clone https://github.com/ajhochy/soundpad.git
cd soundpad

# System dependencies
sudo apt install python3-pyqt5 python3-pip libfluidsynth-dev \
    fluid-soundfont-gm fluid-soundfont-gs \
    fonts-noto fonts-noto-color-emoji

# Python packages
pip3 install pyFluidSynth python-rtmidi

# Download soundfont packs (free, ~200 MB total, non-fatal if any fail)
sudo bash download_soundfonts.sh
```

`download_soundfonts.sh` fetches TimGM6mb, Arachno, SGM, Timbres of Heaven, and OPL-3 FM into `/usr/share/sounds/sf2/`. You can skip it — `fluid-soundfont-gm` from apt gives you a working GM set to start with. Any `.sf2` file in that directory is auto-loaded at startup.

## Run

```bash
python3 soundpad.py
```

## MIDI defaults (Launchkey MK3 49 — Drum mode)

| Control | MIDI message | Action |
|---------|-------------|--------|
| Pads 1–8 | Note-on Ch 10, notes 40–47 | Toggle pad on/off |
| Knobs 1–8 | CC 21–28, Ch 1 | Per-pad volume |
| Fader | CC 9, Ch 1 | Master volume |

> **Launchkey note:** the pads must be in **Drum mode** to send notes 40–47. Session mode sends 96–103 instead.

All mappings are remappable via ⚙ Settings > Learn — so any MIDI controller will work.

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

## Remote deployment

`install.sh` deploys SoundPad to a remote Ubuntu machine over SSH — useful for setting it up on a separate computer (e.g. a shared family PC or Raspberry Pi) from your own machine:

```bash
bash install.sh user@host [desktop-user]

# Examples:
bash install.sh aj@192.168.0.50 kids    # deploy to "kids" account on a remote machine
bash install.sh pi@raspberrypi.local pi
```

It copies the app, installs dependencies, downloads additional soundfonts, sets up autostart, and installs an app launcher icon. SSH key auth is recommended: `ssh-copy-id user@host`.

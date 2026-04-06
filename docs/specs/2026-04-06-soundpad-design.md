# SoundPad — Design Spec
**Date:** 2026-04-06
**Target machine:** Ubuntu 24.04, iMac14,3, PipeWire audio, Novation Launchkey MK3 49

---

## Overview

A child-friendly Python/Qt desktop app that wraps FluidSynth, designed for a young musician using a Novation Launchkey MK3 49 MIDI keyboard. Replaces QSynth with a simple, self-explanatory interface she can operate without help.

---

## Stack

| Component | Choice | Reason |
|-----------|--------|--------|
| GUI | PyQt5 | Stable on Ubuntu 24.04, apt-installable |
| MIDI | python-rtmidi | Real-time CC + note handling |
| Audio engine | pyFluidSynth | Direct FluidSynth bindings, no subprocess IPC |
| Audio routing | pw-jack | Already configured; app launches via `pw-jack` |
| Config storage | JSON | Simple, human-readable, no database needed |

---

## Architecture

Single Python process. Three concurrent concerns:

1. **Main thread** — PyQt5 UI event loop
2. **MIDI thread** — `python-rtmidi` callback, runs in background, emits Qt signals to update UI safely
3. **FluidSynth** — embedded via `pyFluidSynth`, called from main thread in response to signals

No subprocesses. No sockets. App entry point: `pw-jack python3 /opt/soundpad/soundpad.py`

---

## MIDI Mapping

### Defaults (Launchkey MK3 49)

| Physical control | MIDI message | App action |
|-----------------|-------------|-----------|
| Pad 1–8 | Note-on, Ch 10, notes 96–103 (Session mode) | Toggle pad 1–8 on/off |
| Knob 1–8 | CC 21–28, Ch 1 | Set volume for pad 1–8 (0–127 → 0–100%) |
| Fader | CC 9, Ch 1 | Set master volume (0–127 → 0–100%) |

### Remap

All CC numbers and pad note values are editable in ⚙ Settings. Settings saved to `~/.config/soundpad/midi_map.json`. On change, MIDI thread reloads mapping without restart.

---

## UI

### Screen 1 — Main View

- **Scene bar (top):** dropdown to load a saved scene, "+ Save" button to name and save current state, ⚙ Settings button (small, top-right)
- **Pad grid:** 2 rows × 4 columns, 8 pads total
  - Each pad shows: pad number + knob number ("PAD 1 · KN 1"), sound label, volume bar
  - Active pads: coloured background + glow, volume bar reflects knob position live
  - Inactive/empty pads: dark, dashed border
  - Small ✎ edit button (top-right of pad) opens Screen 2 scoped to that pad
  - Tapping a pad on screen or pressing the physical pad toggles it on/off
- **Master volume bar (bottom):** full-width bar reflecting fader position, labelled "MASTER · FADER"

### Screen 2 — Preset Browser

- Opened by tapping ✎ on a specific pad
- Header: "← Back" button + "Choose sound for Pad N"
- Grid of instrument tiles: emoji icon, instrument name, soundfont name
- Tapping a tile assigns it to the pad and returns to Screen 1
- Instruments are sourced from all loaded soundfonts, organised by the 16 standard GM families (Piano, Chromatic Perc, Organ, Guitar, Bass, Strings, Ensemble, Brass, Reed, Pipe, Synth Lead, Synth Pad, Ethnic, Percussive, etc.)

---

## Soundfonts

All soundfonts in `/usr/share/sounds/sf2/` are loaded at startup. The preset browser pulls instrument names from them using FluidSynth's SF2 bank/program enumeration. Each preset entry stores: `{soundfont_path, bank, program, label}`.

---

## Pad Behaviour

- All 8 pads are independent toggles
- Any combination can be active simultaneously (full layering)
- Each active pad = one FluidSynth MIDI channel playing the assigned program
- Toggling a pad off: sets that channel's volume to 0 (preserves state, instant re-enable)
- Toggling a pad on: restores that channel's volume to the pad's stored `volume` value (not the knob's current position — knob updates the stored value in real time while active)

---

## Scene / Config Data Model

### `~/.config/soundpad/scenes.json`

```json
{
  "last_scene": "School Practice",
  "scenes": {
    "School Practice": {
      "master_volume": 62,
      "pads": [
        {"pad": 1, "active": true,  "soundfont": "/usr/share/sounds/sf2/FluidR3_GM.sf2", "bank": 0, "program": 0,  "label": "Grand Piano", "volume": 72},
        {"pad": 2, "active": true,  "soundfont": "/usr/share/sounds/sf2/Arachno SoundFont - Version 1.0.sf2", "bank": 0, "program": 48, "label": "Strings", "volume": 48},
        {"pad": 3, "active": false, "soundfont": null, "bank": 0, "program": 0, "label": null, "volume": 100},
        {"pad": 4, "active": false, "soundfont": null, "bank": 0, "program": 0, "label": null, "volume": 100},
        {"pad": 5, "active": false, "soundfont": null, "bank": 0, "program": 0, "label": null, "volume": 100},
        {"pad": 6, "active": false, "soundfont": null, "bank": 0, "program": 0, "label": null, "volume": 100},
        {"pad": 7, "active": false, "soundfont": null, "bank": 0, "program": 0, "label": null, "volume": 100},
        {"pad": 8, "active": false, "soundfont": null, "bank": 0, "program": 0, "label": null, "volume": 100}
      ]
    }
  }
}
```

App saves current state to `last_scene` on exit and restores it on next launch.

### `~/.config/soundpad/midi_map.json`

```json
{
  "pads": [
    {"pad": 1, "channel": 9, "note": 96},
    {"pad": 2, "channel": 9, "note": 97},
    {"pad": 3, "channel": 9, "note": 98},
    {"pad": 4, "channel": 9, "note": 99},
    {"pad": 5, "channel": 9, "note": 100},
    {"pad": 6, "channel": 9, "note": 101},
    {"pad": 7, "channel": 9, "note": 102},
    {"pad": 8, "channel": 9, "note": 103}
  ],
  "knobs": [
    {"pad": 1, "channel": 0, "cc": 21},
    {"pad": 2, "channel": 0, "cc": 22},
    {"pad": 3, "channel": 0, "cc": 23},
    {"pad": 4, "channel": 0, "cc": 24},
    {"pad": 5, "channel": 0, "cc": 25},
    {"pad": 6, "channel": 0, "cc": 26},
    {"pad": 7, "channel": 0, "cc": 27},
    {"pad": 8, "channel": 0, "cc": 28}
  ],
  "master_fader": {"channel": 0, "cc": 9}
}
```

---

## Auto-Launch

File: `~/.config/autostart/soundpad.desktop`

```ini
[Desktop Entry]
Type=Application
Name=SoundPad
Exec=pw-jack python3 /opt/soundpad/soundpad.py
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
```

App installed to `/opt/soundpad/`. Dependencies installed system-wide via pip/apt.

> Note: PipeWire starts as a user session service. The autostart entry runs after the session initialises, so `pw-jack` will have a live PipeWire instance to connect to. No explicit delay needed.

---

## File Structure

```
/opt/soundpad/
  soundpad.py          # entry point, Qt app init
  ui/
    main_window.py     # Screen 1: pad grid, scene bar, master volume
    preset_browser.py  # Screen 2: instrument picker
    pad_widget.py      # individual pad component
    settings_dialog.py # MIDI remap UI
  core/
    midi_handler.py    # rtmidi thread, emits Qt signals
    synth_engine.py    # pyFluidSynth wrapper, channel management
    scene_manager.py   # load/save scenes.json
    config.py          # load/save midi_map.json, constants
```

---

## Dependencies to Install

```bash
sudo apt install python3-pyqt5 python3-pip
pip3 install pyFluidSynth python-rtmidi
```

---

## Out of Scope

- Recording/playback
- MIDI file loading
- Multiple MIDI device support (Launchkey only)
- Arpeggiator, effects chain

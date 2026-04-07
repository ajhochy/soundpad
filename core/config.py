"""
config.py — loads and saves all persistent settings.

Manages two JSON files in ~/.config/soundpad/:
  - midi_map.json  : which MIDI CC/note numbers map to which pads/knobs/fader
  - (scenes stored separately in scene_manager.py)

Also defines all hard-coded defaults for the Novation Launchkey MK3 49:
  - Pads 1-8 : MIDI channel 9 (0-indexed = ch 10), notes 96-103 (Session mode)
  - Knobs 1-8: MIDI channel 0 (0-indexed = ch 1), CC 21-28
  - Fader     : MIDI channel 0 (0-indexed = ch 1), CC 9

Note: python-rtmidi uses 0-indexed channels internally.
MIDI spec channels 1-16 map to rtmidi channels 0-15.
"""

import copy
import json
import os
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "soundpad"
MIDI_MAP_PATH = CONFIG_DIR / "midi_map.json"
SOUNDFONT_DIR = Path("/usr/share/sounds/sf2")
NUM_PADS = 8

DEFAULT_MIDI_MAP = {
    "pads": [
        {"pad": i + 1, "channel": 9, "note": 96 + i}
        for i in range(NUM_PADS)
    ],
    "knobs": [
        {"pad": i + 1, "channel": 0, "cc": 21 + i}
        for i in range(NUM_PADS)
    ],
    "master_fader": {"channel": 0, "cc": 9},
}

# Each pad gets a distinct accent colour for its active state
PAD_COLOURS = [
    "#00c49a",  # teal
    "#e05b8a",  # pink
    "#7c5cbf",  # purple
    "#e07b2a",  # orange
    "#3a9bd5",  # blue
    "#c4b800",  # yellow
    "#d54a4a",  # red
    "#4ac47e",  # green
]


class Config:
    def __init__(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        self.midi_map = self._load_midi_map()

    def _load_midi_map(self) -> dict:
        if MIDI_MAP_PATH.exists():
            with open(MIDI_MAP_PATH) as f:
                return json.load(f)
        return copy.deepcopy(DEFAULT_MIDI_MAP)

    def save_midi_map(self):
        with open(MIDI_MAP_PATH, "w") as f:
            json.dump(self.midi_map, f, indent=2)

    def reset_midi_map(self):
        """Restore factory defaults and save."""
        self.midi_map = copy.deepcopy(DEFAULT_MIDI_MAP)
        self.save_midi_map()

    @property
    def soundfont_dir(self) -> Path:
        return SOUNDFONT_DIR

    @property
    def num_pads(self) -> int:
        return NUM_PADS

    def pad_colour(self, pad_index: int) -> str:
        """Return the hex accent colour for a pad (0-indexed)."""
        return PAD_COLOURS[pad_index % len(PAD_COLOURS)]

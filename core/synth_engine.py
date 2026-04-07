"""
synth_engine.py — FluidSynth wrapper.

Manages one FluidSynth instance with 8 independent MIDI channels (one per pad).
All soundfonts in /usr/share/sounds/sf2/ are loaded at startup.

Pad-to-channel mapping:
  Pad 1 → FluidSynth channel 0
  Pad 2 → FluidSynth channel 1
  ...
  Pad 8 → FluidSynth channel 7

Toggling a pad off sets its channel volume to 0 (CC 7 = 0).
Toggling a pad on restores its stored volume.

The synth is created with the JACK audio driver so pw-jack routes it through
PipeWire automatically.
"""

import ctypes
import ctypes.util as _ctypes_util
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import fluidsynth
from core.config import Config

log = logging.getLogger("soundpad")

_lib_path = _ctypes_util.find_library("fluidsynth") or "libfluidsynth.so.3"
_fluid_lib = ctypes.CDLL(_lib_path)


@dataclass
class PadState:
    soundfont_path: Optional[str] = None
    soundfont_id: Optional[int] = None   # FluidSynth sfont ID
    bank: int = 0
    program: int = 0
    label: str = ""
    volume: int = 100    # 0-100, mirrors knob position
    active: bool = False


class SynthEngine:
    def __init__(self, config: Config):
        self._config = config
        self._fs = fluidsynth.Synth()
        self._fs.start(driver="pulseaudio")

        # Load all soundfonts; store path→id mapping
        self._sf_ids: dict[str, int] = {}
        self._load_all_soundfonts()

        # One PadState per pad (0-indexed)
        self._pads: list[PadState] = [PadState() for _ in range(config.num_pads)]

        # Build instrument catalogue from loaded soundfonts
        self._catalogue: list[dict] = []
        self._build_catalogue()

        # Align FluidSynth gain with the UI's default master volume of 80
        self.set_master_volume(80)

    # ------------------------------------------------------------------
    # Soundfont management
    # ------------------------------------------------------------------

    def _load_all_soundfonts(self):
        sf_dir = self._config.soundfont_dir
        for sf_path in sorted(sf_dir.glob("*.sf2")):
            sfid = self._fs.sfload(str(sf_path))
            if sfid != -1:
                self._sf_ids[str(sf_path)] = sfid

    def _build_catalogue(self):
        """
        Enumerate every preset that actually exists in each loaded soundfont
        using FluidSynth's sfont iteration API via ctypes.

        Each entry: {soundfont_path, soundfont_name, bank, program, label, gm_family}
        Sorted by GM family (bank-0 program // 8) then label.
        """
        self._catalogue = []

        _lib = _fluid_lib
        _lib.fluid_synth_get_sfont_by_id.restype = ctypes.c_void_p
        _lib.fluid_sfont_iteration_start.restype = None   # void
        _lib.fluid_sfont_iteration_next.restype = ctypes.c_void_p
        _lib.fluid_preset_get_name.restype = ctypes.c_char_p
        _lib.fluid_preset_get_banknum.restype = ctypes.c_int
        _lib.fluid_preset_get_num.restype = ctypes.c_int

        for sf_path, sfid in self._sf_ids.items():
            sf_name = Path(sf_path).stem
            sfont_ptr = _lib.fluid_synth_get_sfont_by_id(self._fs.synth, ctypes.c_uint(sfid))
            if not sfont_ptr:
                continue

            _lib.fluid_sfont_iteration_start(ctypes.c_void_p(sfont_ptr))
            while True:
                preset_ptr = _lib.fluid_sfont_iteration_next(ctypes.c_void_p(sfont_ptr))
                if not preset_ptr:
                    break

                bank = _lib.fluid_preset_get_banknum(ctypes.c_void_p(preset_ptr))
                prog = _lib.fluid_preset_get_num(ctypes.c_void_p(preset_ptr))
                raw_name = _lib.fluid_preset_get_name(ctypes.c_void_p(preset_ptr))
                name = (raw_name.decode("utf-8", errors="replace")
                        if raw_name else GM_PROGRAM_NAMES.get(prog, f"Program {prog}"))

                # Skip internal/garbage presets (names that are just dashes or blanks)
                clean = name.strip("-_ \t")
                if not clean:
                    continue

                # GM family assignment — hybrid approach:
                #   1. Bank 128 is always percussion (GM spec)
                #   2. prog // 8 gives the correct GM family for banks 0–127
                #   3. Name-based override only for unambiguous drum kit names
                #      appearing on non-standard banks (e.g. "TR-808", "STANDARD 1")
                if bank == 128:
                    gm_family = 14
                elif bank == 64:
                    gm_family = 15  # XG sound effects bank (Timbres of Heaven)
                else:
                    gm_family = prog // 8
                    name_lower = name.lower()

                    # Split Piano (0) → Electric Piano (16) for progs 4-7:
                    # EP1, EP2, Harpsichord, Clavinet — keep as Piano only
                    # if the name explicitly says "piano" and isn't an EP
                    if gm_family == 0 and prog >= 4:
                        ep_keywords = {"electric piano", "e. piano", "ep ", "ep1", "ep2",
                                       "rhodes", "wurli", "dx ", "dx7", "clav", "harpsi",
                                       "honky", "tack", "stage"}
                        acoustic_keywords = {"grand", "upright", "acoustic", "concert"}
                        if any(k in name_lower for k in acoustic_keywords):
                            pass  # keep as Piano
                        else:
                            gm_family = 16  # Electric Piano

                    # Name-based overrides for instruments in the wrong family
                    if gm_family in (0, 16) and "guitar" in name_lower:
                        gm_family = 3
                    if gm_family in (0, 16) and "bass" in name_lower and "contrabass" not in name_lower:
                        gm_family = 4
                    if gm_family in (0, 16) and any(k in name_lower for k in ("tb-303", "c64", "synth bass")):
                        gm_family = 10  # Synth Lead
                    if gm_family == 0 and any(k in name_lower for k in ("room", "standard 1", "standard 2", "standard 3")):
                        gm_family = 14  # drum kit named wrongly

                    # Drum kit override for GS alternate drum banks
                    _drum_kit_names = {
                        "standard", "room kit", "power kit", "electronic kit",
                        "tr-808", "tr-909", "tr-707", "cr-78", "hip hop",
                        "jungle kit", "techno kit", "dance kit", "house kit",
                        "sfx kit", "brush kit",
                    }
                    if bank in (120, 126, 127) and any(k in name_lower for k in _drum_kit_names):
                        gm_family = 14

                self._catalogue.append({
                    "soundfont_path": sf_path,
                    "soundfont_name": sf_name,
                    "bank": bank,
                    "program": prog,
                    "label": name,
                    "gm_family": gm_family,
                })

        self._catalogue.sort(key=lambda e: (e["gm_family"], e["label"]))

    @property
    def catalogue(self) -> list[dict]:
        return self._catalogue

    # ------------------------------------------------------------------
    # Pad control (called from main thread only)
    # ------------------------------------------------------------------

    def assign_pad(self, pad_index: int, soundfont_path: str, bank: int, program: int, label: str):
        """Assign a sound to a pad and load it into the corresponding channel."""
        state = self._pads[pad_index]
        sfid = self._sf_ids.get(soundfont_path)
        if sfid is None:
            log.warning("assign_pad %d: soundfont not found: %s", pad_index, soundfont_path)
            state.label = "[missing]"
            state.active = False
            return

        state.soundfont_path = soundfont_path
        state.soundfont_id = sfid
        state.bank = bank
        state.program = program
        state.label = label

        ch = pad_index
        self._fs.program_select(ch, sfid, bank, program)
        # Apply current volume if pad is active
        if state.active:
            self._set_channel_volume(ch, state.volume)

    def toggle_pad(self, pad_index: int) -> bool:
        """Toggle pad on/off. Returns new active state."""
        state = self._pads[pad_index]
        if state.soundfont_path is None:
            return False  # nothing assigned, ignore toggle

        state.active = not state.active
        ch = pad_index
        if state.active:
            self._set_channel_volume(ch, state.volume)
        else:
            self._set_channel_volume(ch, 0)
        return state.active

    def set_pad_volume(self, pad_index: int, volume: int):
        """Set pad volume (0-100). Updates live if pad is active."""
        state = self._pads[pad_index]
        state.volume = max(0, min(100, volume))
        if state.active:
            self._set_channel_volume(pad_index, state.volume)

    def play_note(self, note: int, velocity: int):
        """Play a note on all active pad channels (called from MIDI thread via Qt signal)."""
        for i, state in enumerate(self._pads):
            if state.active and state.soundfont_path:
                self._fs.noteon(i, note, velocity)

    def stop_note(self, note: int):
        """Stop a note on all pad channels."""
        for i in range(len(self._pads)):
            self._fs.noteoff(i, note)

    def set_master_volume(self, volume: int):
        """Set master gain (0-100)."""
        # FluidSynth gain range: 0.0-10.0; map 0-100 → 0.0-2.0
        gain = (volume / 100.0) * 2.0
        self._fs.setting("synth.gain", gain)

    def _set_channel_volume(self, channel: int, volume: int):
        """Send CC7 (main volume) on a FluidSynth channel. volume: 0-100 → 0-127."""
        cc_value = int((volume / 100.0) * 127)
        self._fs.cc(channel, 7, cc_value)

    # ------------------------------------------------------------------
    # State snapshot (used by SceneManager)
    # ------------------------------------------------------------------

    def get_pad_states(self) -> list[dict]:
        result = []
        for i, s in enumerate(self._pads):
            result.append({
                "pad": i + 1,
                "active": s.active,
                "soundfont": s.soundfont_path,
                "bank": s.bank,
                "program": s.program,
                "label": s.label,
                "volume": s.volume,
            })
        return result

    def apply_pad_states(self, pad_states: list[dict]):
        """Restore pad states from a loaded scene."""
        for entry in pad_states:
            idx = entry["pad"] - 1
            if entry.get("soundfont"):
                self.assign_pad(idx, entry["soundfont"], entry["bank"], entry["program"], entry["label"])
                self._pads[idx].volume = entry.get("volume", 100)
                if entry.get("active"):
                    self._pads[idx].active = True
                    self._set_channel_volume(idx, self._pads[idx].volume)

    def shutdown(self):
        self._fs.delete()


# General MIDI program name lookup (program 0-127)
GM_PROGRAM_NAMES = {
    0: "Acoustic Grand Piano", 1: "Bright Acoustic Piano", 2: "Electric Grand Piano",
    3: "Honky-tonk Piano", 4: "Electric Piano 1", 5: "Electric Piano 2",
    6: "Harpsichord", 7: "Clavinet", 8: "Celesta", 9: "Glockenspiel",
    10: "Music Box", 11: "Vibraphone", 12: "Marimba", 13: "Xylophone",
    14: "Tubular Bells", 15: "Dulcimer", 16: "Drawbar Organ", 17: "Percussive Organ",
    18: "Rock Organ", 19: "Church Organ", 20: "Reed Organ", 21: "Accordion",
    22: "Harmonica", 23: "Tango Accordion", 24: "Nylon Guitar", 25: "Steel Guitar",
    26: "Jazz Guitar", 27: "Clean Electric Guitar", 28: "Muted Electric Guitar",
    29: "Overdriven Guitar", 30: "Distortion Guitar", 31: "Guitar Harmonics",
    32: "Acoustic Bass", 33: "Finger Bass", 34: "Pick Bass", 35: "Fretless Bass",
    36: "Slap Bass 1", 37: "Slap Bass 2", 38: "Synth Bass 1", 39: "Synth Bass 2",
    40: "Violin", 41: "Viola", 42: "Cello", 43: "Contrabass",
    44: "Tremolo Strings", 45: "Pizzicato Strings", 46: "Orchestral Harp", 47: "Timpani",
    48: "String Ensemble 1", 49: "String Ensemble 2", 50: "Synth Strings 1", 51: "Synth Strings 2",
    52: "Choir Aahs", 53: "Voice Oohs", 54: "Synth Voice", 55: "Orchestra Hit",
    56: "Trumpet", 57: "Trombone", 58: "Tuba", 59: "Muted Trumpet",
    60: "French Horn", 61: "Brass Section", 62: "Synth Brass 1", 63: "Synth Brass 2",
    64: "Soprano Sax", 65: "Alto Sax", 66: "Tenor Sax", 67: "Baritone Sax",
    68: "Oboe", 69: "English Horn", 70: "Bassoon", 71: "Clarinet",
    72: "Piccolo", 73: "Flute", 74: "Recorder", 75: "Pan Flute",
    76: "Blown Bottle", 77: "Shakuhachi", 78: "Whistle", 79: "Ocarina",
    80: "Square Lead", 81: "Sawtooth Lead", 82: "Calliope Lead", 83: "Chiff Lead",
    84: "Charang Lead", 85: "Voice Lead", 86: "Fifths Lead", 87: "Bass+Lead",
    88: "New Age Pad", 89: "Warm Pad", 90: "Polysynth Pad", 91: "Choir Pad",
    92: "Bowed Pad", 93: "Metallic Pad", 94: "Halo Pad", 95: "Sweep Pad",
    96: "Rain", 97: "Soundtrack", 98: "Crystal", 99: "Atmosphere",
    100: "Brightness", 101: "Goblins", 102: "Echoes", 103: "Sci-fi",
    104: "Sitar", 105: "Banjo", 106: "Shamisen", 107: "Koto",
    108: "Kalimba", 109: "Bag Pipe", 110: "Fiddle", 111: "Shanai",
    112: "Tinkle Bell", 113: "Agogo", 114: "Steel Drums", 115: "Woodblock",
    116: "Taiko Drum", 117: "Melodic Tom", 118: "Synth Drum", 119: "Reverse Cymbal",
    120: "Guitar Fret Noise", 121: "Breath Noise", 122: "Seashore", 123: "Bird Tweet",
    124: "Telephone Ring", 125: "Helicopter", 126: "Applause", 127: "Gunshot",
}

GM_FAMILIES = [
    "Piano", "Chromatic Perc", "Organ", "Guitar",
    "Bass", "Strings", "Ensemble", "Brass",
    "Reed", "Pipe", "Synth Lead", "Synth Pad",
    "Synth Effects", "Ethnic", "Percussive", "Sound Effects",
    "Electric Piano",   # index 16 — EP/Rhodes/Clav/Harpsichord split from Piano
]

GM_FAMILY_EMOJI = [
    "🎹", "🔔", "🎹", "🎸",
    "🎸", "🎻", "🎻", "🎺",
    "🎷", "🪈", "🎛", "🎛",
    "✨", "🪘", "🥁", "💥",
    "🪗",  # Electric Piano
]


def gm_family_emoji(bank: int, program: int) -> str:
    """Return the emoji for a sound's GM family."""
    if bank == 128:
        family = 14  # percussion
    elif program >= 4 and program <= 7 and bank in (0,):
        family = 16  # Electric Piano split
    else:
        family = program // 8
    return GM_FAMILY_EMOJI[family % len(GM_FAMILY_EMOJI)]

"""
midi_handler.py — real-time MIDI input thread.

Listens on all available MIDI input ports for the Launchkey MK3 49.
Runs in a background thread via python-rtmidi's callback mechanism.
Communicates with the UI/synth by emitting PyQt5 signals — never calls
Qt widgets directly from the MIDI thread.

Messages handled:
  - Note-on  on pad channel/notes → PadToggled signal
  - CC on knob channel/CCs        → KnobMoved signal  (value 0-127)
  - CC on fader channel/CC        → FaderMoved signal (value 0-127)

The handler reloads the MIDI map from Config on demand (called by
SettingsDialog after the user saves new CC assignments).
"""

import rtmidi
from PyQt5.QtCore import QObject, pyqtSignal


class MidiSignals(QObject):
    pad_toggled = pyqtSignal(int)        # pad_index (0-based)
    knob_moved = pyqtSignal(int, int)    # pad_index (0-based), value 0-127
    fader_moved = pyqtSignal(int)        # value 0-127


class MidiHandler:
    def __init__(self, config):
        self._config = config
        self.signals = MidiSignals()
        self._midi_in = rtmidi.MidiIn()
        self._running = False

    def start(self):
        """Open the first available MIDI port and start listening."""
        ports = self._midi_in.get_ports()
        if not ports:
            return  # No MIDI device connected

        # Prefer Launchkey if present, else use first port
        target = next((i for i, p in enumerate(ports) if "Launchkey" in p), 0)
        self._midi_in.open_port(target)
        self._midi_in.set_callback(self._on_midi_message)
        self._running = True

    def stop(self):
        if self._running:
            self._midi_in.close_port()
            self._running = False

    def reload_map(self):
        """Call after saving new MIDI mappings in SettingsDialog."""
        # Callback reads from config.midi_map on every message — no restart needed.
        pass

    def _on_midi_message(self, event, data=None):
        """
        Called by rtmidi on the MIDI thread.
        Emits Qt signals — safe because Qt queues cross-thread signals.
        """
        message, _ = event
        if len(message) < 3:
            return

        status, byte1, byte2 = message[0], message[1], message[2]
        msg_type = status & 0xF0
        channel = status & 0x0F

        midi_map = self._config.midi_map

        # Note-on (pad toggles)
        if msg_type == 0x90 and byte2 > 0:
            for entry in midi_map["pads"]:
                if entry["channel"] == channel and entry["note"] == byte1:
                    self.signals.pad_toggled.emit(entry["pad"] - 1)
                    return

        # CC (knobs + fader)
        if msg_type == 0xB0:
            for entry in midi_map["knobs"]:
                if entry["channel"] == channel and entry["cc"] == byte1:
                    self.signals.knob_moved.emit(entry["pad"] - 1, byte2)
                    return
            fader = midi_map["master_fader"]
            if fader["channel"] == channel and fader["cc"] == byte1:
                self.signals.fader_moved.emit(byte2)

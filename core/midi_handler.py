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

import threading
import rtmidi
from PyQt5.QtCore import QObject, pyqtSignal


class MidiSignals(QObject):
    pad_toggled = pyqtSignal(int)        # pad_index (0-based)
    knob_moved = pyqtSignal(int, int)    # pad_index (0-based), value 0-127
    fader_moved = pyqtSignal(int)        # value 0-127
    learn_captured = pyqtSignal(int, int, int)  # msg_type (0x90/0xB0), channel, byte1
    learn_timeout = pyqtSignal()         # emitted when learn mode expires with no input
    note_on = pyqtSignal(int, int)       # note (0-127), velocity (1-127)
    note_off = pyqtSignal(int)           # note (0-127)


class MidiHandler:
    def __init__(self, config):
        self._config = config
        self.signals = MidiSignals()
        self._midi_in = rtmidi.MidiIn()
        self._running = False
        self._learn_mode = False
        self._learn_timer: threading.Timer | None = None

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

    def is_connected(self) -> bool:
        """Return True if a MIDI port was successfully opened."""
        return self._running

    def set_learn_mode(self, active: bool):
        """Enable or disable MIDI learn mode.

        While active, the next Note-on or CC message is captured and emitted
        via signals.learn_captured instead of being processed normally.
        """
        self._learn_mode = active

    def start_learn(self):
        """Enter MIDI learn mode with a 10-second timeout.

        If no MIDI message is received within 10 seconds, learn mode is
        cancelled automatically and signals.learn_timeout is emitted.
        """
        self._cancel_learn_timer()
        self._learn_mode = True
        self._learn_timer = threading.Timer(10.0, self._on_learn_timeout)
        self._learn_timer.daemon = True
        self._learn_timer.start()

    def _cancel_learn_timer(self):
        if self._learn_timer is not None:
            self._learn_timer.cancel()
            self._learn_timer = None

    def _on_learn_timeout(self):
        """Called on the timer thread when learn mode expires."""
        self._learn_mode = False
        self._learn_timer = None
        self.signals.learn_timeout.emit()

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

        # Learn mode: capture the next Note-on or CC and hand it to the dialog
        if self._learn_mode and msg_type in (0x90, 0xB0) and byte2 > 0:
            self._learn_mode = False
            self._cancel_learn_timer()
            self.signals.learn_captured.emit(msg_type, channel, byte1)
            return

        midi_map = self._config.midi_map

        # Note-on: check pad toggles first, then forward as keyboard note
        if msg_type == 0x90 and byte2 > 0:
            for entry in midi_map["pads"]:
                if entry["channel"] == channel and entry["note"] == byte1:
                    self.signals.pad_toggled.emit(entry["pad"] - 1)
                    return
            # Not a pad toggle — keyboard key pressed, forward to synth
            self.signals.note_on.emit(byte1, byte2)
            return

        # Note-off (explicit note-off or note-on with velocity 0)
        if msg_type == 0x80 or (msg_type == 0x90 and byte2 == 0):
            self.signals.note_off.emit(byte1)
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

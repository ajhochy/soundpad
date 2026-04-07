"""
SoundPad — entry point.

Initialises the Qt application, loads config, starts the synth engine and
MIDI handler, then shows the main window.  Launched via:

    pw-jack python3 soundpad.py

The pw-jack wrapper ensures PipeWire's JACK bridge is active so FluidSynth
can connect to the system audio graph.
"""

import sys
import os
import logging

logging.basicConfig(
    filename="/tmp/soundpad.log",
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(message)s",
    force=True,
)
log = logging.getLogger("soundpad")

from PyQt5.QtWidgets import QApplication, QMessageBox
from core.config import Config
from core.synth_engine import SynthEngine
from core.scene_manager import SceneManager
from core.midi_handler import MidiHandler
from ui.main_window import MainWindow


def main():
    log.info("=== SoundPad starting ===")
    log.info("JACK_NO_AUDIO_RESERVATION=%s", os.environ.get("JACK_NO_AUDIO_RESERVATION"))
    log.info("LD_LIBRARY_PATH=%s", os.environ.get("LD_LIBRARY_PATH"))
    log.info("XDG_RUNTIME_DIR=%s", os.environ.get("XDG_RUNTIME_DIR"))
    log.info("DISPLAY=%s WAYLAND_DISPLAY=%s", os.environ.get("DISPLAY"), os.environ.get("WAYLAND_DISPLAY"))

    app = QApplication(sys.argv)
    app.setApplicationName("SoundPad")
    app.setStyle("Fusion")

    # Set global font: larger size + emoji fallback
    from PyQt5.QtGui import QFont
    _font = app.font()
    _font.setFamilies(["Ubuntu", "Noto Sans", "Noto Color Emoji"])
    _font.setPointSize(13)
    app.setFont(_font)

    config = Config()
    log.info("Config loaded. soundfont_dir=%s", config.soundfont_dir)
    try:
        log.info("Starting SynthEngine...")
        synth = SynthEngine(config)
        log.info("SynthEngine started. catalogue size=%d", len(synth.catalogue))
    except Exception as exc:
        log.exception("Could not start audio engine")
        print(f"ERROR: Could not start audio engine: {exc}", file=sys.stderr)
        QMessageBox.critical(
            None,
            "Audio Engine Error",
            "Could not start audio engine.\n\n"
            "Make sure the Launchkey is plugged in and PipeWire/JACK is running, "
            "then try again.",
        )
        sys.exit(1)
    scenes = SceneManager(config)
    midi = MidiHandler(config)

    window = MainWindow(config, synth, scenes, midi)
    window.show()

    # Restore last scene
    scenes.restore_last(synth, window)

    # Start MIDI listening — update status indicator after start() so
    # is_connected() reflects the real connection state
    import rtmidi
    _tmp_in = rtmidi.MidiIn()
    log.info("Available MIDI ports: %s", _tmp_in.get_ports())
    del _tmp_in
    midi.start()
    log.info("MIDI started. connected=%s", midi.is_connected())
    window.update_midi_status(midi.is_connected())

    exit_code = app.exec_()

    # Clean shutdown
    midi.stop()
    synth.shutdown()
    scenes.save_last(window.get_current_state())

    sys.exit(exit_code)


if __name__ == "__main__":
    main()

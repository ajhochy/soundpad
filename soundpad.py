"""
SoundPad — entry point.

Initialises the Qt application, loads config, starts the synth engine and
MIDI handler, then shows the main window.  Launched via:

    pw-jack python3 soundpad.py

The pw-jack wrapper ensures PipeWire's JACK bridge is active so FluidSynth
can connect to the system audio graph.
"""

import sys
from PyQt5.QtWidgets import QApplication, QMessageBox
from core.config import Config
from core.synth_engine import SynthEngine
from core.scene_manager import SceneManager
from core.midi_handler import MidiHandler
from ui.main_window import MainWindow


def main():
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
    try:
        synth = SynthEngine(config)
    except Exception as exc:
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
    midi.start()
    window.update_midi_status(midi.is_connected())

    exit_code = app.exec_()

    # Clean shutdown
    midi.stop()
    synth.shutdown()
    scenes.save_last(window.get_current_state())

    sys.exit(exit_code)


if __name__ == "__main__":
    main()

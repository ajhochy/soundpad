"""
SoundPad — entry point.

Initialises the Qt application, loads config, starts the synth engine and
MIDI handler, then shows the main window.  Launched via:

    pw-jack python3 soundpad.py

The pw-jack wrapper ensures PipeWire's JACK bridge is active so FluidSynth
can connect to the system audio graph.
"""

import sys
from PyQt5.QtWidgets import QApplication
from core.config import Config
from core.synth_engine import SynthEngine
from core.scene_manager import SceneManager
from core.midi_handler import MidiHandler
from ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("SoundPad")
    app.setStyle("Fusion")

    config = Config()
    synth = SynthEngine(config)
    scenes = SceneManager(config)
    midi = MidiHandler(config)

    window = MainWindow(config, synth, scenes, midi)
    window.show()

    # Restore last scene
    scenes.restore_last(synth, window)

    # Start MIDI listening
    midi.start()

    exit_code = app.exec_()

    # Clean shutdown
    midi.stop()
    synth.shutdown()
    scenes.save_last(window.get_current_state())

    sys.exit(exit_code)


if __name__ == "__main__":
    main()

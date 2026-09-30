"""
practice_window.py — standalone MIDI practice window.

Opens as a separate QMainWindow (not embedded in MainWindow).
Launched by the 🎹 Practice button in main_window.py.

Constructor: PracticeWindow(synth_engine, midi_handler, parent=None)
  synth_engine:  core.synth_engine.SynthEngine — shared FluidSynth instance
  midi_handler:  core.midi_handler.MidiHandler — shared MIDI input handler

Practice uses FluidSynth channel 15 (Grand Piano, reserved).
"""

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QSlider, QLabel, QComboBox, QFileDialog,
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor

from core.midi_file_player import MidiFilePlayer
from core.note_matcher import MatchResult
from ui.piano_roll_widget import PianoRollWidget

_PRACTICE_CHANNEL = 15   # FluidSynth channel reserved for practice playback


class PracticeWindow(QMainWindow):
    """
    Separate practice window — see module docstring for full description.

    Key responsibilities:
      - Owns the MidiFilePlayer (playback engine)
      - Wires player signals -> FluidSynth (note_on/off) and widget (display)
      - Wires live MIDI key signals -> note matching (waiting mode) and key lighting
      - Manages _lit_keys dict (note -> QColor) passed to PianoRollWidget each frame
      - Handles mute toggle: suppresses FluidSynth calls, visuals always run
    """

    def __init__(self, synth_engine, midi_handler, parent=None):
        super().__init__(parent)
        self._synth = synth_engine
        self._midi = midi_handler
        self._player = MidiFilePlayer()
        self._muted = False
        self._lit_keys = {}   # note -> colour for current frame

        self.setWindowTitle("SoundPad — Practice 🎹")
        self.setMinimumSize(900, 500)
        self._apply_dark_theme()

        self._build_ui()
        self._wire_signals()

        # Reserve FluidSynth channel 15 with Grand Piano
        self._synth.init_practice_channel(channel=_PRACTICE_CHANNEL)

        # Sync player to whatever the combo defaulted to. setCurrentText
        # does not fire currentTextChanged when the value is already
        # selected (default "Waiting"), so the player would stay in its
        # constructor default ("free") otherwise.
        self._player.set_mode(self._mode_combo.currentText().lower())

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        toolbar_widget = QWidget()
        toolbar_widget.setStyleSheet("background: #1a192a; border-bottom: 1px solid #2e2d3e;")
        toolbar_layout = QVBoxLayout(toolbar_widget)
        toolbar_layout.setContentsMargins(12, 8, 12, 8)
        toolbar_layout.setSpacing(6)
        toolbar_layout.addLayout(self._build_toolbar_row1())
        toolbar_layout.addLayout(self._build_toolbar_row2())
        root.addWidget(toolbar_widget)

        self._roll = PianoRollWidget()
        root.addWidget(self._roll, stretch=1)

    def _build_toolbar_row1(self):
        row = QHBoxLayout()
        row.setSpacing(8)

        self._open_btn = QPushButton("📂 Open")
        self._open_btn.setCursor(Qt.PointingHandCursor)
        self._open_btn.clicked.connect(self._open_file)
        row.addWidget(self._open_btn)

        self._play_btn = QPushButton("▶ Play")
        self._play_btn.setCheckable(True)
        self._play_btn.setCursor(Qt.PointingHandCursor)
        self._play_btn.clicked.connect(self._toggle_play)
        row.addWidget(self._play_btn)

        self._stop_btn = QPushButton("⏹ Stop")
        self._stop_btn.setCursor(Qt.PointingHandCursor)
        self._stop_btn.clicked.connect(self._stop)
        row.addWidget(self._stop_btn)

        row.addSpacing(16)

        speed_lbl = QLabel("Speed:")
        speed_lbl.setStyleSheet("color: #a0a0c0; font-size: 11px;")
        row.addWidget(speed_lbl)

        self._speed_slider = QSlider(Qt.Horizontal)
        self._speed_slider.setRange(25, 150)
        self._speed_slider.setValue(100)
        self._speed_slider.setFixedWidth(120)
        self._speed_slider.valueChanged.connect(self._on_speed_changed)
        row.addWidget(self._speed_slider)

        self._speed_label = QLabel("100%")
        self._speed_label.setFixedWidth(40)
        self._speed_label.setStyleSheet("color: #e0e0f0; font-size: 11px;")
        row.addWidget(self._speed_label)

        row.addStretch()
        return row

    def _build_toolbar_row2(self):
        row = QHBoxLayout()
        row.setSpacing(8)

        mode_lbl = QLabel("Mode:")
        mode_lbl.setStyleSheet("color: #a0a0c0; font-size: 11px;")
        row.addWidget(mode_lbl)

        self._mode_combo = QComboBox()
        self._mode_combo.addItems(["Waiting", "Free"])
        self._mode_combo.currentTextChanged.connect(self._on_mode_changed)
        row.addWidget(self._mode_combo)

        self._mute_btn = QPushButton("🔇 Mute")
        self._mute_btn.setCheckable(True)
        self._mute_btn.setCursor(Qt.PointingHandCursor)
        self._mute_btn.clicked.connect(self._on_mute_toggled)
        row.addWidget(self._mute_btn)

        row.addStretch()
        return row

    # ------------------------------------------------------------------
    # Signal wiring
    # ------------------------------------------------------------------

    def _wire_signals(self):
        # MidiFilePlayer -> this window
        self._player.signals.note_on.connect(self._on_playback_note_on)
        self._player.signals.note_off.connect(self._on_playback_note_off)
        self._player.signals.playback_tick.connect(self._on_tick)
        self._player.signals.waiting_for.connect(self._on_waiting_for)
        self._player.signals.song_finished.connect(self._on_song_finished)

        # Live MIDI keyboard -> this window
        self._midi.signals.key_pressed.connect(self._on_key_pressed)
        self._midi.signals.key_released.connect(self._on_key_released)

    # ------------------------------------------------------------------
    # Toolbar handlers
    # ------------------------------------------------------------------

    def _open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open MIDI File", "",
            "MIDI Files (*.mid *.midi);;All Files (*)"
        )
        if path:
            self._player.load(path)
            self._play_btn.setChecked(False)
            self._play_btn.setText("▶ Play")
            self._lit_keys.clear()
            self._roll.set_state(0, [], {})

    def _toggle_play(self, checked):
        if checked:
            self._player.play()
            self._play_btn.setText("⏸ Pause")
        else:
            self._player.pause()
            self._play_btn.setText("▶ Play")

    def _stop(self):
        self._player.stop()
        self._play_btn.setChecked(False)
        self._play_btn.setText("▶ Play")
        self._lit_keys.clear()
        self._roll.set_state(0, [], {})

    def _on_speed_changed(self, value):
        self._speed_label.setText("%d%%" % value)
        self._player.set_speed(value)

    def _on_mode_changed(self, mode):
        self._player.set_mode(mode.lower())

    def _on_mute_toggled(self, checked):
        self._muted = checked

    # ------------------------------------------------------------------
    # Player signal handlers
    # ------------------------------------------------------------------

    def _on_playback_note_on(self, note, velocity):
        """Fired by MidiFilePlayer in free mode or when a waiting note is hit."""
        if not self._muted:
            self._synth.practice_note_on(_PRACTICE_CHANNEL, note, velocity)
        self._lit_keys[note] = QColor("#00bcd4")   # cyan — playing

    def _on_playback_note_off(self, note):
        """Fired by MidiFilePlayer (free mode note_off or on key_released)."""
        if not self._muted:
            self._synth.practice_note_off(_PRACTICE_CHANNEL, note)
        self._lit_keys.pop(note, None)

    def _on_tick(self, clock_us, upcoming_notes):
        """60fps update from MidiFilePlayer — refresh widget display."""
        self._roll.set_state(clock_us, upcoming_notes, dict(self._lit_keys))

    def _on_waiting_for(self, required_notes):
        """Clock has paused. Highlight required notes in amber."""
        for note in required_notes:
            self._lit_keys[note] = QColor("#ffa726")   # amber — waiting
        self._roll.set_state(self._player.clock_us, [], dict(self._lit_keys))

    def _on_song_finished(self):
        self._play_btn.setChecked(False)
        self._play_btn.setText("▶ Play")

    # ------------------------------------------------------------------
    # Live MIDI key handlers
    # ------------------------------------------------------------------

    def _on_key_pressed(self, note, velocity):
        """
        Live key press from the physical keyboard.
        In waiting mode: check against required notes; flash red on miss.
        Always lights the key (green for live play) then passes to player.
        """
        result = self._player.note_pressed(note, velocity)

        if result == MatchResult.MISS:
            self._lit_keys[note] = QColor("#ef5350")   # red flash
            QTimer.singleShot(200, lambda n=note: self._lit_keys.pop(n, None))
        else:
            # HIT or NOT_YET — green for live key
            self._lit_keys[note] = QColor("#00e676")

        self._roll.set_state(
            self._player.clock_us,
            self._player._upcoming_snapshot(),
            dict(self._lit_keys),
        )

    def _on_key_released(self, note):
        self._player.note_released(note)
        # note_released emits note_off -> _on_playback_note_off clears the lit key

    # ------------------------------------------------------------------
    # Theme
    # ------------------------------------------------------------------

    def _apply_dark_theme(self):
        self.setStyleSheet("""
            QMainWindow, QWidget { background: #12111a; color: #e0e0f0; }
            QPushButton {
                background: #1e1d2e; color: #a0a0c0;
                border: 1px solid #2e2d3e; border-radius: 6px;
                padding: 4px 10px; font-size: 12px;
            }
            QPushButton:hover  { background: #2a2940; border-color: #4a4870; }
            QPushButton:checked { background: #2e4a2e; color: #00e676; border-color: #00e676; }
            QComboBox {
                background: #1e1d2e; color: #ffffff;
                border: 1px solid #2e2d3e; border-radius: 6px;
                padding: 4px 10px;
            }
            QComboBox::drop-down { border: none; }
            QSlider::groove:horizontal { background: #2e2d3e; height: 4px; border-radius: 2px; }
            QSlider::handle:horizontal {
                background: #a0a0c0; width: 12px; height: 12px;
                margin: -4px 0; border-radius: 6px;
            }
        """)

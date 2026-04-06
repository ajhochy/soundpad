"""
settings_dialog.py — MIDI remap screen.

Accessible via the ⚙ button in the top-right of the main view.
Tucked away so kids don't accidentally open it.

Shows a table of all 8 pad note assignments + 8 knob CC assignments +
master fader CC.  Each row has a "Learn" button: click Learn, press the
physical control, the CC/note is captured and filled in automatically.

Saves to ~/.config/soundpad/midi_map.json on "OK".
Calls midi_handler.reload_map() so changes take effect without restarting.
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QDialogButtonBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
import copy


class SettingsDialog(QDialog):
    def __init__(self, config, midi_handler, parent=None):
        super().__init__(parent)
        self._config = config
        self._midi = midi_handler
        self._working_map = copy.deepcopy(config.midi_map)
        self._learning_target = None   # (type, index) while waiting for MIDI

        self.setWindowTitle("MIDI Settings")
        self.setMinimumWidth(460)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("<b>Pad Note Assignments</b> (Launchkey Session mode pads)"))
        self._pad_table = self._make_table(["Pad", "MIDI Channel", "Note", "Learn"])
        self._populate_pad_table()
        layout.addWidget(self._pad_table)

        layout.addWidget(QLabel("<b>Knob CC Assignments</b> (one per pad)"))
        self._knob_table = self._make_table(["Pad", "MIDI Channel", "CC Number", "Learn"])
        self._populate_knob_table()
        layout.addWidget(self._knob_table)

        layout.addWidget(QLabel("<b>Master Fader CC</b>"))
        fader_row = QHBoxLayout()
        fader = self._working_map["master_fader"]
        self._fader_ch = QTableWidgetItem(str(fader["channel"] + 1))
        self._fader_cc = QTableWidgetItem(str(fader["cc"]))
        fader_label = QLabel(f"Channel: {fader['channel'] + 1}   CC: {fader['cc']}")
        fader_label.setStyleSheet("color: #a0a0c0;")
        fader_row.addWidget(fader_label)
        learn_fader = QPushButton("Learn")
        learn_fader.clicked.connect(lambda: self._start_learn("fader", 0))
        fader_row.addWidget(learn_fader)
        layout.addLayout(fader_row)

        reset_btn = QPushButton("Reset to Launchkey MK3 defaults")
        reset_btn.clicked.connect(self._reset_defaults)
        layout.addWidget(reset_btn)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._save_and_close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _make_table(self, headers: list[str]) -> QTableWidget:
        table = QTableWidget(8, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        return table

    def _populate_pad_table(self):
        for i, entry in enumerate(self._working_map["pads"]):
            self._pad_table.setItem(i, 0, QTableWidgetItem(f"Pad {entry['pad']}"))
            self._pad_table.setItem(i, 1, QTableWidgetItem(str(entry["channel"] + 1)))
            self._pad_table.setItem(i, 2, QTableWidgetItem(str(entry["note"])))
            btn = QPushButton("Learn")
            btn.clicked.connect(lambda checked, idx=i: self._start_learn("pad", idx))
            self._pad_table.setCellWidget(i, 3, btn)

    def _populate_knob_table(self):
        for i, entry in enumerate(self._working_map["knobs"]):
            self._knob_table.setItem(i, 0, QTableWidgetItem(f"Pad {entry['pad']}"))
            self._knob_table.setItem(i, 1, QTableWidgetItem(str(entry["channel"] + 1)))
            self._knob_table.setItem(i, 2, QTableWidgetItem(str(entry["cc"])))
            btn = QPushButton("Learn")
            btn.clicked.connect(lambda checked, idx=i: self._start_learn("knob", idx))
            self._knob_table.setCellWidget(i, 3, btn)

    def _start_learn(self, target_type: str, index: int):
        """Temporarily redirect MIDI input to capture the next message."""
        self._learning_target = (target_type, index)
        # TODO: hook into MidiHandler's learn mode and update table on capture

    def _reset_defaults(self):
        from core.config import DEFAULT_MIDI_MAP
        import copy
        self._working_map = copy.deepcopy(DEFAULT_MIDI_MAP)
        self._populate_pad_table()
        self._populate_knob_table()

    def _save_and_close(self):
        self._config.midi_map = self._working_map
        self._config.save_midi_map()
        self._midi.reload_map()
        self.accept()

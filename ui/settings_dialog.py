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

from typing import Optional
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
        self._active_learn_btn: Optional[QPushButton] = None
        self._midi.signals.learn_captured.connect(self._on_learn_captured)
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
        self._fader_label = QLabel(f"Channel: {fader['channel'] + 1}   CC: {fader['cc']}")
        self._fader_label.setStyleSheet("color: #a0a0c0;")
        fader_row.addWidget(self._fader_label)
        learn_fader = QPushButton("Learn")
        learn_fader.clicked.connect(lambda checked=False, b=learn_fader: self._start_learn("fader", 0, b))
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
        self._active_learn_btn = None  # stale after table rebuild
        for i, entry in enumerate(self._working_map["pads"]):
            self._pad_table.setItem(i, 0, QTableWidgetItem(f"Pad {entry['pad']}"))
            self._pad_table.setItem(i, 1, QTableWidgetItem(str(entry["channel"] + 1)))
            self._pad_table.setItem(i, 2, QTableWidgetItem(str(entry["note"])))
            btn = QPushButton("Learn")
            btn.clicked.connect(lambda checked, idx=i, b=btn: self._start_learn("pad", idx, b))
            self._pad_table.setCellWidget(i, 3, btn)

    def _populate_knob_table(self):
        self._active_learn_btn = None  # stale after table rebuild
        for i, entry in enumerate(self._working_map["knobs"]):
            self._knob_table.setItem(i, 0, QTableWidgetItem(f"Pad {entry['pad']}"))
            self._knob_table.setItem(i, 1, QTableWidgetItem(str(entry["channel"] + 1)))
            self._knob_table.setItem(i, 2, QTableWidgetItem(str(entry["cc"])))
            btn = QPushButton("Learn")
            btn.clicked.connect(lambda checked, idx=i, b=btn: self._start_learn("knob", idx, b))
            self._knob_table.setCellWidget(i, 3, btn)

    def _start_learn(self, target_type: str, index: int, btn: QPushButton):
        """Activate MIDI learn: next Note-on or CC updates the target row."""
        # Cancel any previous pending learn
        if self._active_learn_btn is not None:
            self._active_learn_btn.setText("Learn")
            self._active_learn_btn.setEnabled(True)

        self._learning_target = (target_type, index)
        self._active_learn_btn = btn
        btn.setText("Waiting…")
        btn.setEnabled(False)
        self._midi.set_learn_mode(True)

    def _on_learn_captured(self, msg_type: int, channel: int, byte1: int):
        """Receive the captured MIDI message and update the mapping."""
        if self._active_learn_btn is not None:
            self._active_learn_btn.setText("Learn")
            self._active_learn_btn.setEnabled(True)
            self._active_learn_btn = None

        if self._learning_target is None:
            return

        target_type, index = self._learning_target
        self._learning_target = None

        if target_type == "pad" and msg_type == 0x90:
            self._working_map["pads"][index]["channel"] = channel
            self._working_map["pads"][index]["note"] = byte1
            self._populate_pad_table()
        elif target_type == "knob" and msg_type == 0xB0:
            self._working_map["knobs"][index]["channel"] = channel
            self._working_map["knobs"][index]["cc"] = byte1
            self._populate_knob_table()
        elif target_type == "fader" and msg_type == 0xB0:
            self._working_map["master_fader"]["channel"] = channel
            self._working_map["master_fader"]["cc"] = byte1
            self._fader_label.setText(f"Channel: {channel + 1}   CC: {byte1}")

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

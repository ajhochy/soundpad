"""
pad_widget.py — a single pad tile in the 4x2 grid.

Visual states:
  - Empty   : dark background, dashed border, "empty" label
  - Inactive: dark background, solid dim border, sound name shown dimly
  - Active  : coloured background + glow, sound name bright, volume bar live

Each pad widget emits:
  - toggle_requested(pad_index)  when clicked on screen
  - edit_requested(pad_index)    when the ✎ button is clicked

The parent (MainWindow) connects these to the synth and preset browser.
Volume bar updates live as the corresponding knob is turned.
"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QProgressBar
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QFont


class PadWidget(QWidget):
    toggle_requested = pyqtSignal(int)   # pad_index 0-based
    edit_requested = pyqtSignal(int)     # pad_index 0-based

    def __init__(self, pad_index: int, colour: str, parent=None):
        super().__init__(parent)
        self._pad_index = pad_index
        self._colour = colour
        self._active = False
        self._label = ""
        self._volume = 100

        self._build_ui()
        self._apply_style(active=False, has_sound=False)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        # Header row: pad label + edit button
        header = QHBoxLayout()
        self._pad_label = QLabel(f"PAD {self._pad_index + 1} · KN {self._pad_index + 1}")
        self._pad_label.setFont(QFont("Sans", 7, QFont.Bold))
        header.addWidget(self._pad_label)
        header.addStretch()

        self._edit_btn = QPushButton("✎")
        self._edit_btn.setFixedSize(20, 18)
        self._edit_btn.setCursor(Qt.PointingHandCursor)
        self._edit_btn.clicked.connect(lambda: self.edit_requested.emit(self._pad_index))
        header.addWidget(self._edit_btn)
        layout.addLayout(header)

        # Sound name
        self._sound_label = QLabel("empty")
        self._sound_label.setFont(QFont("Sans", 11, QFont.Bold))
        self._sound_label.setWordWrap(True)
        layout.addWidget(self._sound_label)

        layout.addStretch()

        # Volume bar
        self._volume_bar = QProgressBar()
        self._volume_bar.setRange(0, 100)
        self._volume_bar.setValue(100)
        self._volume_bar.setTextVisible(False)
        self._volume_bar.setFixedHeight(5)
        layout.addWidget(self._volume_bar)

        self.setCursor(Qt.PointingHandCursor)

    def mousePressEvent(self, event):
        self.toggle_requested.emit(self._pad_index)

    # ------------------------------------------------------------------
    # Public update API (called from MainWindow)
    # ------------------------------------------------------------------

    def set_active(self, active: bool):
        self._active = active
        self._apply_style(active=active, has_sound=bool(self._label))

    def set_sound(self, label: str):
        self._label = label
        self._sound_label.setText(label or "empty")
        self._apply_style(active=self._active, has_sound=bool(label))

    def set_volume(self, volume: int):
        self._volume = volume
        self._volume_bar.setValue(volume)

    def _apply_style(self, active: bool, has_sound: bool):
        if active:
            # Always white text — all accent colours are saturated enough to support it
            self.setStyleSheet(f"""
                PadWidget {{
                    background: {self._colour};
                    border-radius: 10px;
                    border: 3px solid white;
                }}
            """)
            self._pad_label.setStyleSheet("color: rgba(255,255,255,0.75); font-weight: bold;")
            self._sound_label.setStyleSheet("color: #ffffff;")
            self._volume_bar.setStyleSheet("""
                QProgressBar { background: rgba(0,0,0,0.3); border-radius: 2px; border: none; }
                QProgressBar::chunk { background: rgba(255,255,255,0.8); border-radius: 2px; }
            """)
        elif has_sound:
            self.setStyleSheet("""
                PadWidget {
                    background: #1e1d2e;
                    border-radius: 10px;
                    border: 1px solid #5a5880;
                }
            """)
            self._pad_label.setStyleSheet("color: #7a78a0;")
            self._sound_label.setStyleSheet("color: #c0c0e0;")
            self._volume_bar.setStyleSheet("""
                QProgressBar { background: #0d0c18; border-radius: 2px; border: none; }
                QProgressBar::chunk { background: #5a5880; border-radius: 2px; }
            """)
        else:
            self.setStyleSheet("""
                PadWidget {
                    background: #1a192a;
                    border-radius: 10px;
                    border: 1px dashed #2e2d3e;
                }
            """)
            self._pad_label.setStyleSheet("color: #3a3858;")
            self._sound_label.setStyleSheet("color: #3a3858;")
            self._volume_bar.setStyleSheet("""
                QProgressBar { background: #0d0c18; border-radius: 2px; border: none; }
                QProgressBar::chunk { background: #2e2d3e; border-radius: 2px; }
            """)

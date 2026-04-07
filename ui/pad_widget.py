"""
pad_widget.py — a single pad tile in the 4x2 grid.

Visual states:
  - Empty   : dark background, dashed border, "empty" label
  - Inactive: dark background, solid dim border, sound name shown dimly
  - Active  : bright green background + border, sound name bright

Fonts scale with widget height so the UI looks good at any window size.

Each pad widget emits:
  - toggle_requested(pad_index)  when clicked on screen
  - edit_requested(pad_index)    when the ✎ button is clicked
"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QProgressBar
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QFont


class PadWidget(QWidget):
    toggle_requested = pyqtSignal(int)
    edit_requested = pyqtSignal(int)

    def __init__(self, pad_index: int, colour: str, parent=None):
        super().__init__(parent)
        self._pad_index = pad_index
        self._colour = colour
        self._active = False
        self._label = ""
        self._emoji = ""
        self._volume = 100

        self._build_ui()
        self._apply_style(active=False, has_sound=False)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        header = QHBoxLayout()
        self._pad_label = QLabel(f"PAD {self._pad_index + 1}")
        self._pad_label.setFont(QFont("Sans", 9, QFont.Bold))
        header.addWidget(self._pad_label)
        header.addStretch()

        self._edit_btn = QPushButton("✎")
        self._edit_btn.setFont(QFont("Sans", 16))
        self._edit_btn.setCursor(Qt.PointingHandCursor)
        self._edit_btn.clicked.connect(lambda: self.edit_requested.emit(self._pad_index))
        header.addWidget(self._edit_btn)
        layout.addLayout(header)

        self._sound_label = QLabel("empty")
        self._sound_label.setFont(QFont("Sans", 12, QFont.Bold))
        self._sound_label.setWordWrap(True)
        self._sound_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._sound_label, stretch=1)

        self._volume_bar = QProgressBar()
        self._volume_bar.setRange(0, 100)
        self._volume_bar.setValue(100)
        self._volume_bar.setTextVisible(False)
        self._volume_bar.setFixedHeight(6)
        layout.addWidget(self._volume_bar)

        self.setCursor(Qt.PointingHandCursor)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        h = self.height()
        pad_pt = max(8, h // 14)
        sound_pt = max(10, h // 9)
        btn_pt = max(14, h // 8)
        self._pad_label.setFont(QFont("Sans", pad_pt, QFont.Bold))
        self._sound_label.setFont(QFont("Sans", sound_pt, QFont.Bold))
        self._edit_btn.setFont(QFont("Sans", btn_pt))
        self._edit_btn.updateGeometry()

    def mousePressEvent(self, event):
        self.toggle_requested.emit(self._pad_index)

    # ------------------------------------------------------------------
    # Public update API
    # ------------------------------------------------------------------

    def set_active(self, active: bool):
        self._active = active
        self._apply_style(active=active, has_sound=bool(self._label))

    def set_sound(self, label: str, emoji: str = ""):
        self._label = label
        self._emoji = emoji
        if label:
            self._sound_label.setText(f"{emoji} {label}" if emoji else label)
        else:
            self._sound_label.setText("empty")
        self._apply_style(active=self._active, has_sound=bool(label))

    def set_volume(self, volume: int):
        self._volume = volume
        self._volume_bar.setValue(volume)

    def _apply_style(self, active: bool, has_sound: bool):
        if active:
            self.setStyleSheet(f"""
                PadWidget {{
                    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                        stop:0 #28a85a, stop:1 #1a6b3a);
                    border-radius: 10px;
                    border: 3px solid #6effa0;
                }}
            """)
            self._pad_label.setStyleSheet("color: rgba(255,255,255,0.8); font-weight: bold;")
            self._sound_label.setStyleSheet("color: #ffffff;")
            self._volume_bar.setStyleSheet("""
                QProgressBar { background: rgba(0,0,0,0.3); border-radius: 3px; border: none; }
                QProgressBar::chunk { background: #6effa0; border-radius: 3px; }
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
                QProgressBar { background: #0d0c18; border-radius: 3px; border: none; }
                QProgressBar::chunk { background: #5a5880; border-radius: 3px; }
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
                QProgressBar { background: #0d0c18; border-radius: 3px; border: none; }
                QProgressBar::chunk { background: #2e2d3e; border-radius: 3px; }
            """)

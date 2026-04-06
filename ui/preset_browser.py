"""
preset_browser.py — Screen 2, instrument picker for a single pad.

Opened when the user clicks ✎ on a pad.  Shows all instruments across all
loaded soundfonts, grouped into the 16 GM families.

Selecting an instrument:
  1. Calls synth.assign_pad(pad_index, soundfont_path, bank, program, label)
  2. Emits sound_selected(pad_index, label) so MainWindow updates the pad widget
  3. Navigates back to Screen 1 (MainWindow.show_main())

Layout:
  - Header: ← Back | "Choose sound for Pad N"
  - Family filter row (scrollable chips): Piano | Strings | Brass | ...
  - Instrument grid (3 columns): emoji + name + soundfont name tiles
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QGridLayout, QFrame
)
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QFont
from core.synth_engine import GM_FAMILIES


# One emoji per GM family
FAMILY_EMOJI = ["🎹","🔔","🎹","🎸","🎸","🎻","🎻","🎺","🎷","🪈","🎹","🎹","✨","🪘","🥁","💥"]


class PresetBrowser(QWidget):
    sound_selected = pyqtSignal(int, str)   # pad_index, label

    def __init__(self, synth, parent=None):
        super().__init__(parent)
        self._synth = synth
        self._pad_index = 0
        self._active_family = None   # None = show all
        self._build_ui()

    def open_for_pad(self, pad_index: int):
        self._pad_index = pad_index
        self._header_label.setText(
            f"Choose sound for <b style='color:#a78bfa;'>Pad {pad_index + 1}</b>"
        )
        self._refresh_grid()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header row
        header = QHBoxLayout()
        back_btn = QPushButton("← Back")
        back_btn.setCursor(Qt.PointingHandCursor)
        back_btn.setStyleSheet("QPushButton { background: #1e1d2e; color: #a0a0c0; border-radius: 6px; padding: 6px 12px; border: none; }")
        back_btn.clicked.connect(self._go_back)
        header.addWidget(back_btn)

        self._header_label = QLabel()
        self._header_label.setFont(QFont("Sans", 13, QFont.Bold))
        self._header_label.setStyleSheet("color: #ffffff;")
        header.addWidget(self._header_label)
        header.addStretch()
        layout.addLayout(header)

        # Family filter chips
        family_scroll = QScrollArea()
        family_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        family_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        family_scroll.setFixedHeight(40)
        family_scroll.setFrameShape(QFrame.NoFrame)
        family_widget = QWidget()
        family_layout = QHBoxLayout(family_widget)
        family_layout.setContentsMargins(0, 0, 0, 0)
        family_layout.setSpacing(6)

        all_btn = QPushButton("All")
        all_btn.setCursor(Qt.PointingHandCursor)
        all_btn.clicked.connect(lambda: self._filter_family(None))
        family_layout.addWidget(all_btn)

        for i, name in enumerate(GM_FAMILIES):
            btn = QPushButton(f"{FAMILY_EMOJI[i]} {name}")
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked, idx=i: self._filter_family(idx))
            family_layout.addWidget(btn)

        family_scroll.setWidget(family_widget)
        layout.addWidget(family_scroll)

        # Instrument grid (scrollable)
        self._grid_scroll = QScrollArea()
        self._grid_scroll.setWidgetResizable(True)
        self._grid_scroll.setFrameShape(QFrame.NoFrame)
        layout.addWidget(self._grid_scroll)

        self._grid_widget = QWidget()
        self._grid_layout = QGridLayout(self._grid_widget)
        self._grid_layout.setSpacing(8)
        self._grid_scroll.setWidget(self._grid_widget)

    def _filter_family(self, family_index):
        self._active_family = family_index
        self._refresh_grid()

    def _refresh_grid(self):
        # Clear existing grid items
        while self._grid_layout.count():
            item = self._grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        catalogue = self._synth.catalogue
        if self._active_family is not None:
            catalogue = [e for e in catalogue if e["gm_family"] == self._active_family]

        # Deduplicate by label for cleaner display
        seen = set()
        unique = []
        for entry in catalogue:
            key = entry["label"]
            if key not in seen:
                seen.add(key)
                unique.append(entry)

        cols = 3
        for i, entry in enumerate(unique):
            row, col = divmod(i, cols)
            tile = self._make_tile(entry)
            self._grid_layout.addWidget(tile, row, col)

    def _make_tile(self, entry: dict) -> QWidget:
        tile = QFrame()
        tile.setStyleSheet("""
            QFrame { background: #1e1d2e; border-radius: 8px; border: 1px solid #2e2d3e; }
            QFrame:hover { border: 1px solid #a78bfa; }
        """)
        tile.setCursor(Qt.PointingHandCursor)

        layout = QVBoxLayout(tile)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setAlignment(Qt.AlignCenter)

        emoji = FAMILY_EMOJI[entry["gm_family"]]
        emoji_label = QLabel(emoji)
        emoji_label.setFont(QFont("Sans", 20))
        emoji_label.setAlignment(Qt.AlignCenter)
        emoji_label.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(emoji_label)

        name_label = QLabel(entry["label"])
        name_label.setFont(QFont("Sans", 10, QFont.Bold))
        name_label.setAlignment(Qt.AlignCenter)
        name_label.setWordWrap(True)
        name_label.setStyleSheet("color: #ffffff; background: transparent; border: none;")
        layout.addWidget(name_label)

        sf_label = QLabel(entry["soundfont_name"])
        sf_label.setFont(QFont("Sans", 8))
        sf_label.setAlignment(Qt.AlignCenter)
        sf_label.setStyleSheet("color: #555570; background: transparent; border: none;")
        layout.addWidget(sf_label)

        # Capture entry in closure
        def on_click(checked=False, e=entry):
            self._select(e)

        tile.mousePressEvent = lambda event, fn=on_click: fn()
        return tile

    def _select(self, entry: dict):
        self._synth.assign_pad(
            self._pad_index,
            entry["soundfont_path"],
            entry["bank"],
            entry["program"],
            entry["label"],
        )
        self.sound_selected.emit(self._pad_index, entry["label"])

    def _go_back(self):
        # Parent (MainWindow) connects this widget's parent stack to handle navigation
        self.parent().show_main()

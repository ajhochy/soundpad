"""
main_window.py — Screen 1, the main pad grid view.

Layout (top to bottom):
  1. Scene bar: scene dropdown | + Save button | ⚙ Settings button
  2. 4×2 pad grid (8 PadWidget instances)
  3. Master volume bar (reflects fader CC)

Uses QStackedWidget to switch between Screen 1 (this) and Screen 2
(PresetBrowser) without re-creating widgets.

Signal wiring:
  - PadWidget.toggle_requested  → synth.toggle_pad + update pad colour
  - PadWidget.edit_requested    → show preset browser for that pad
  - MidiHandler.pad_toggled     → same as above, from physical pad press
  - MidiHandler.knob_moved      → synth.set_pad_volume + update volume bar
  - MidiHandler.fader_moved     → synth.set_master_volume + update master bar
"""

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QProgressBar,
    QStackedWidget, QInputDialog, QGridLayout
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from ui.pad_widget import PadWidget
from ui.preset_browser import PresetBrowser
from ui.settings_dialog import SettingsDialog


class MainWindow(QMainWindow):
    def __init__(self, config, synth, scenes, midi):
        super().__init__()
        self._config = config
        self._synth = synth
        self._scenes = scenes
        self._midi = midi
        self._current_scene_name = None

        self.setWindowTitle("SoundPad 🎹")
        self.setMinimumSize(600, 420)
        self._apply_dark_theme()

        # Stacked widget: index 0 = main view, index 1 = preset browser
        self._stack = QStackedWidget()
        self.setCentralWidget(self._stack)

        self._build_main_view()
        self._preset_browser = PresetBrowser(synth, self)
        self._preset_browser.sound_selected.connect(self._on_sound_selected)
        self._stack.addWidget(self._main_widget)
        self._stack.addWidget(self._preset_browser)

        self._wire_midi_signals()

    # ------------------------------------------------------------------
    # Main view construction
    # ------------------------------------------------------------------

    def _build_main_view(self):
        self._main_widget = QWidget()
        layout = QVBoxLayout(self._main_widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        layout.addLayout(self._build_scene_bar())
        layout.addLayout(self._build_pad_grid())
        layout.addWidget(self._build_master_bar())

    def _build_scene_bar(self):
        bar = QHBoxLayout()

        scene_label = QLabel("Scene:")
        scene_label.setStyleSheet("color: #a0a0c0; font-size: 10px;")
        bar.addWidget(scene_label)

        self._scene_combo = QComboBox()
        self._scene_combo.setMinimumWidth(160)
        self._scene_combo.currentTextChanged.connect(self._on_scene_selected)
        self._refresh_scene_list()
        bar.addWidget(self._scene_combo)

        save_btn = QPushButton("＋ Save")
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.clicked.connect(self._save_scene)
        bar.addWidget(save_btn)

        bar.addStretch()

        settings_btn = QPushButton("⚙")
        settings_btn.setFixedWidth(36)
        settings_btn.setCursor(Qt.PointingHandCursor)
        settings_btn.clicked.connect(self._open_settings)
        bar.addWidget(settings_btn)

        return bar

    def _build_pad_grid(self):
        self._pad_widgets: list[PadWidget] = []
        grid = QGridLayout()
        grid.setSpacing(10)

        for i in range(self._config.num_pads):
            pw = PadWidget(i, self._config.pad_colour(i))
            pw.toggle_requested.connect(self._on_pad_toggle)
            pw.edit_requested.connect(self._on_edit_pad)
            pw.setMinimumHeight(100)
            self._pad_widgets.append(pw)
            grid.addWidget(pw, i // 4, i % 4)

        return grid

    def _build_master_bar(self):
        container = QWidget()
        container.setStyleSheet("background: #1a192a; border-radius: 10px;")
        layout = QHBoxLayout(container)
        layout.setContentsMargins(14, 10, 14, 10)

        label = QLabel("⬛ MASTER")
        label.setFont(QFont("Sans", 9, QFont.Bold))
        label.setStyleSheet("color: #f0c040;")
        layout.addWidget(label)

        self._master_bar = QProgressBar()
        self._master_bar.setRange(0, 100)
        self._master_bar.setValue(80)
        self._master_bar.setTextVisible(False)
        self._master_bar.setFixedHeight(10)
        self._master_bar.setStyleSheet("""
            QProgressBar { background: #0d0c18; border-radius: 5px; border: none; }
            QProgressBar::chunk { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #f0c040,stop:1 #ff9020); border-radius: 5px; }
        """)
        layout.addWidget(self._master_bar)

        self._master_pct = QLabel("80%")
        self._master_pct.setFont(QFont("Sans", 11, QFont.Bold))
        self._master_pct.setStyleSheet("color: #f0c040;")
        self._master_pct.setFixedWidth(38)
        layout.addWidget(self._master_pct)

        fader_hint = QLabel("FADER")
        fader_hint.setStyleSheet("color: #333248; font-size: 9px;")
        layout.addWidget(fader_hint)

        return container

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def show_main(self):
        self._stack.setCurrentIndex(0)

    def show_preset_browser(self, pad_index: int):
        self._preset_browser.open_for_pad(pad_index)
        self._stack.setCurrentIndex(1)

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_pad_toggle(self, pad_index: int):
        active = self._synth.toggle_pad(pad_index)
        self._pad_widgets[pad_index].set_active(active)

    def _on_edit_pad(self, pad_index: int):
        self.show_preset_browser(pad_index)

    def _on_sound_selected(self, pad_index: int, label: str):
        self._pad_widgets[pad_index].set_sound(label)
        self.show_main()

    def _on_scene_selected(self, name: str):
        scene = self._scenes.load_scene(name)
        if scene:
            self._current_scene_name = name
            self._synth.apply_pad_states(scene["pads"])
            self._synth.set_master_volume(scene.get("master_volume", 80))
            self.apply_scene(name, scene)

    def _save_scene(self):
        name, ok = QInputDialog.getText(self, "Save Scene", "Scene name:")
        if ok and name:
            state = self.get_current_state()
            self._scenes.save_scene(name, state["master_volume"], state["pads"])
            self._current_scene_name = name
            self._refresh_scene_list()
            self._scene_combo.setCurrentText(name)

    def _open_settings(self):
        dlg = SettingsDialog(self._config, self._midi, self)
        dlg.exec_()

    # ------------------------------------------------------------------
    # MIDI signal wiring
    # ------------------------------------------------------------------

    def _wire_midi_signals(self):
        sigs = self._midi.signals
        sigs.pad_toggled.connect(self._on_pad_toggle)
        sigs.knob_moved.connect(self._on_knob_moved)
        sigs.fader_moved.connect(self._on_fader_moved)

    def _on_knob_moved(self, pad_index: int, value: int):
        volume = int((value / 127.0) * 100)
        self._synth.set_pad_volume(pad_index, volume)
        self._pad_widgets[pad_index].set_volume(volume)

    def _on_fader_moved(self, value: int):
        volume = int((value / 127.0) * 100)
        self._synth.set_master_volume(volume)
        self._master_bar.setValue(volume)
        self._master_pct.setText(f"{volume}%")

    # ------------------------------------------------------------------
    # State helpers
    # ------------------------------------------------------------------

    def apply_scene(self, name: str, scene: dict):
        self._current_scene_name = name
        for entry in scene["pads"]:
            idx = entry["pad"] - 1
            pw = self._pad_widgets[idx]
            pw.set_sound(entry.get("label") or "")
            pw.set_active(entry.get("active", False))
            pw.set_volume(entry.get("volume", 100))
        mv = scene.get("master_volume", 80)
        self._master_bar.setValue(mv)
        self._master_pct.setText(f"{mv}%")

    def get_current_state(self) -> dict:
        return {
            "scene_name": self._current_scene_name,
            "master_volume": self._master_bar.value(),
            "pads": self._synth.get_pad_states(),
        }

    def _refresh_scene_list(self):
        self._scene_combo.blockSignals(True)
        self._scene_combo.clear()
        self._scene_combo.addItems(self._scenes.scene_names)
        if self._current_scene_name:
            self._scene_combo.setCurrentText(self._current_scene_name)
        self._scene_combo.blockSignals(False)

    # ------------------------------------------------------------------
    # Theme
    # ------------------------------------------------------------------

    def _apply_dark_theme(self):
        self.setStyleSheet("""
            QMainWindow, QWidget { background: #12111a; color: #e0e0f0; }
            QPushButton {
                background: #1e1d2e; color: #a0a0c0;
                border: 1px solid #2e2d3e; border-radius: 6px;
                padding: 5px 10px; font-size: 12px;
            }
            QPushButton:hover { background: #2a2940; border-color: #4a4870; }
            QComboBox {
                background: #1e1d2e; color: #ffffff;
                border: 1px solid #2e2d3e; border-radius: 6px;
                padding: 5px 10px;
            }
            QComboBox::drop-down { border: none; }
            QScrollBar { background: #1a192a; }
        """)

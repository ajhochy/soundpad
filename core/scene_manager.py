"""
scene_manager.py — save and load named scenes.

A scene captures the full state of all 8 pads (sound assignment, volume,
active/inactive) plus master volume.  Scenes are stored in:

    ~/.config/soundpad/scenes.json

The "last_scene" key records which scene was active when the app closed,
so the app restores it on next launch.
"""

import json
from pathlib import Path
from core.config import CONFIG_DIR

SCENES_PATH = CONFIG_DIR / "scenes.json"

DEFAULT_SCENES = {
    "last_scene": None,
    "scenes": {},
}


class SceneManager:
    def __init__(self, config):
        self._config = config
        self._data = self._load()

    def _load(self) -> dict:
        if SCENES_PATH.exists():
            with open(SCENES_PATH) as f:
                return json.load(f)
        return DEFAULT_SCENES.copy()

    def _save(self):
        with open(SCENES_PATH, "w") as f:
            json.dump(self._data, f, indent=2)

    # ------------------------------------------------------------------
    # Scene CRUD
    # ------------------------------------------------------------------

    @property
    def scene_names(self) -> list[str]:
        return list(self._data["scenes"].keys())

    def save_scene(self, name: str, master_volume: int, pad_states: list[dict]):
        self._data["scenes"][name] = {
            "master_volume": master_volume,
            "pads": pad_states,
        }
        self._data["last_scene"] = name
        self._save()

    def load_scene(self, name: str) -> dict | None:
        return self._data["scenes"].get(name)

    def delete_scene(self, name: str):
        self._data["scenes"].pop(name, None)
        if self._data["last_scene"] == name:
            self._data["last_scene"] = None
        self._save()

    # ------------------------------------------------------------------
    # App lifecycle helpers
    # ------------------------------------------------------------------

    def restore_last(self, synth, window):
        """Load the last-used scene into synth + update UI on startup."""
        last = self._data.get("last_scene")
        if last and last in self._data["scenes"]:
            scene = self._data["scenes"][last]
            synth.apply_pad_states(scene["pads"])
            synth.set_master_volume(scene.get("master_volume", 80))
            window.apply_scene(last, scene)

    def save_last(self, state: dict):
        """Called on app exit to persist current state."""
        if state.get("scene_name"):
            self.save_scene(
                state["scene_name"],
                state["master_volume"],
                state["pads"],
            )

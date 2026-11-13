"""Read/write the app settings file `config.json`."""

import json
from pathlib import Path

from devpipe.models.app_config import AppConfig

_LAST_STATE_FOLDER_KEY = "last_state_folder"


class ConfigRepository:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> AppConfig:
        data = self._read_raw()
        maximized = data.get("window_maximized", False)
        return AppConfig(
            window_maximized=maximized if isinstance(maximized, bool) else False,
            last_state_folder=self._read_path(data, _LAST_STATE_FOLDER_KEY),
        )

    def save(self, config: AppConfig) -> None:
        # Keep keys this version does not know about.
        data = self._read_raw()
        data["window_maximized"] = config.window_maximized
        data[_LAST_STATE_FOLDER_KEY] = (
            str(config.last_state_folder) if config.last_state_folder is not None else None
        )
        self.path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    def _read_raw(self) -> dict:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return data if isinstance(data, dict) else {}

    @staticmethod
    def _read_path(data: dict, key: str) -> Path | None:
        """Path from a non-empty string value; None for a missing key or any other value."""
        value = data.get(key)
        return Path(value) if isinstance(value, str) and value != "" else None

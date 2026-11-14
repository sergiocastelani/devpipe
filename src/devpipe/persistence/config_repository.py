"""Read/write the app settings file `config.json`."""

import json
from pathlib import Path

from devpipe.models.app_config import AppConfig

_LAST_STATE_FOLDER_KEY = "last_state_folder"
_OPEN_STATE_FILES_KEY = "open_state_files"
_ACTIVE_STATE_FILE_KEY = "active_state_file"


class ConfigRepository:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> AppConfig:
        data = self._read_raw()
        maximized = data.get("window_maximized", False)
        return AppConfig(
            window_maximized=maximized if isinstance(maximized, bool) else False,
            last_state_folder=self._read_path(data, _LAST_STATE_FOLDER_KEY),
            open_state_files=self._read_path_list(data, _OPEN_STATE_FILES_KEY),
            active_state_file=self._read_path(data, _ACTIVE_STATE_FILE_KEY),
        )

    def save(self, config: AppConfig) -> None:
        # Keep keys this version does not know about.
        data = self._read_raw()
        data["window_maximized"] = config.window_maximized
        data[_LAST_STATE_FOLDER_KEY] = (
            str(config.last_state_folder) if config.last_state_folder is not None else None
        )
        data[_OPEN_STATE_FILES_KEY] = [str(path) for path in config.open_state_files]
        data[_ACTIVE_STATE_FILE_KEY] = (
            str(config.active_state_file) if config.active_state_file is not None else None
        )
        self.path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    def _read_raw(self) -> dict:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return data if isinstance(data, dict) else {}

    @staticmethod
    def _as_path(value: object) -> Path | None:
        """Path from a non-empty string without NUL characters; None for any other value."""
        if isinstance(value, str) and value != "" and "\0" not in value:
            return Path(value)
        return None

    @staticmethod
    def _read_path(data: dict, key: str) -> Path | None:
        """Path from a non-empty string value; None for a missing key or any other value."""
        return ConfigRepository._as_path(data.get(key))

    @staticmethod
    def _read_path_list(data: dict, key: str) -> list[Path]:
        """Paths of the non-empty string items of a list value, in order.

        [] for a missing key or a value that is not a list; other items are skipped.
        """
        value = data.get(key)
        if not isinstance(value, list):
            return []
        return [path for path in map(ConfigRepository._as_path, value) if path is not None]

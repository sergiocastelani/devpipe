"""Read/write the app settings file `config.json`."""

import json
from pathlib import Path

from devpipe.models.app_config import AppConfig


class ConfigRepository:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> AppConfig:
        data = self._read_raw()
        maximized = data.get("window_maximized", False)
        return AppConfig(window_maximized=maximized if isinstance(maximized, bool) else False)

    def save(self, config: AppConfig) -> None:
        # Keep keys this version does not know about.
        data = self._read_raw()
        data["window_maximized"] = config.window_maximized
        self.path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    def _read_raw(self) -> dict:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return data if isinstance(data, dict) else {}

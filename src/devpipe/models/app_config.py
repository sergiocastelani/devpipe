"""App settings stored in `config.json`."""

from dataclasses import dataclass
from pathlib import Path


@dataclass
class AppConfig:
    window_maximized: bool = False
    last_state_folder: Path | None = None  # folder of the last saved/opened state file

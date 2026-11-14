"""App settings stored in `config.json`."""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class AppConfig:
    window_maximized: bool = False
    last_state_folder: Path | None = None  # folder of the last saved/opened state file
    open_state_files: list[Path] = field(default_factory=list)  # saved open tabs, in tab order
    active_state_file: Path | None = None  # state file of the selected tab

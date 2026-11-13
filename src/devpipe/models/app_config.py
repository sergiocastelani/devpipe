"""App settings stored in `config.json`."""

from dataclasses import dataclass


@dataclass
class AppConfig:
    window_maximized: bool = False

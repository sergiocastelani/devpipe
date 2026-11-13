"""Composition root: builds repositories and services and injects them into views.

This is the only module allowed to import from every layer.
"""

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from devpipe.persistence.config_repository import ConfigRepository
from devpipe.services.window_state_service import WindowStateService
from devpipe.views.main_window import MainWindow

# config.json lives in the devpipe project folder (src/devpipe/app.py -> ../../).
CONFIG_PATH = Path(__file__).resolve().parents[2] / "config.json"


def main() -> int:
    app = QApplication(sys.argv)
    window_state = WindowStateService(ConfigRepository(CONFIG_PATH))
    window = MainWindow(window_state)
    window.show_initial()
    return app.exec()

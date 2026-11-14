"""Composition root: builds repositories, infrastructure implementations and services and injects them into views.

This is the only module allowed to import from every layer.
"""

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from devpipe.infrastructure.git_worktrees import SubprocessGitWorktrees
from devpipe.persistence.config_repository import ConfigRepository
from devpipe.persistence.tab_state_repository import TabStateRepository
from devpipe.services.session_service import SessionService
from devpipe.services.tab_state_service import TabStateService
from devpipe.services.window_state_service import WindowStateService
from devpipe.services.worktree_service import WorktreeService
from devpipe.views.main_window import MainWindow

# config.json lives in the devpipe project folder (src/devpipe/app.py -> ../../).
CONFIG_PATH = Path(__file__).resolve().parents[2] / "config.json"


def main() -> int:
    app = QApplication(sys.argv)
    config = ConfigRepository(CONFIG_PATH)
    window = MainWindow(
        WindowStateService(config),
        TabStateService(TabStateRepository()),
        SessionService(config),
        WorktreeService(SubprocessGitWorktrees()),
    )
    window.show_initial()
    return app.exec()

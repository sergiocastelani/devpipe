from collections.abc import Callable

import pytest

from devpipe.persistence.config_repository import ConfigRepository
from devpipe.persistence.tab_state_repository import TabStateRepository
from devpipe.services.session_service import SessionService
from devpipe.services.tab_state_service import TabStateService
from devpipe.services.window_state_service import WindowStateService
from devpipe.views.main_window import MainWindow


@pytest.fixture
def tab_states() -> TabStateService:
    return TabStateService(TabStateRepository())


@pytest.fixture
def make_window(qtbot, tmp_path, tab_states) -> Callable[[], MainWindow]:
    """Return a callable building a new MainWindow with real repositories on
    tmp_path / "config.json" (same file on every call: a second call simulates a
    restart). Each window is registered with qtbot.addWidget."""

    def make() -> MainWindow:
        config = ConfigRepository(tmp_path / "config.json")
        window = MainWindow(WindowStateService(config), tab_states, SessionService(config))
        qtbot.addWidget(window)
        return window

    return make

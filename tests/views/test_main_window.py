import pytest

from devpipe.persistence.config_repository import ConfigRepository
from devpipe.services.window_state_service import WindowStateService
from devpipe.views.main_window import MainWindow
from devpipe.views.start_tab import StartTab


@pytest.fixture
def window_state(tmp_path):
    return WindowStateService(ConfigRepository(tmp_path / "config.json"))


def test_main_window_opens_with_a_start_tab(qtbot, window_state):
    window = MainWindow(window_state)
    qtbot.addWidget(window)
    assert window.tabs.count() == 1
    assert isinstance(window.tabs.widget(0), StartTab)


@pytest.mark.parametrize("maximized", [True, False])
def test_close_saves_and_next_launch_restores_maximized(qtbot, window_state, maximized):
    first = MainWindow(window_state)
    qtbot.addWidget(first)
    first.show_initial()
    if maximized:
        first.showMaximized()
    qtbot.waitUntil(lambda: first.isMaximized() == maximized)
    first.close()
    assert window_state.was_maximized() is maximized

    second = MainWindow(window_state)
    qtbot.addWidget(second)
    second.show_initial()
    qtbot.waitUntil(lambda: second.isMaximized() == maximized)

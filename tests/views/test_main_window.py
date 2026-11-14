import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox

from devpipe.models.tab_state import TabState
from devpipe.persistence.config_repository import ConfigRepository
from devpipe.views.pipeline_tab import PipelineTab


@pytest.fixture
def window(make_window):
    return make_window()


class IdentityTab(PipelineTab):
    """PipelineTab whose identity the test can change."""

    def __init__(self, tab_states, worktrees) -> None:
        super().__init__(tab_states, worktrees)
        self.title_text = "t1"
        self.tooltip_text = "p1"

    def title(self) -> str:
        return self.title_text

    def tooltip(self) -> str:
        return self.tooltip_text


def add_identity_tab(qtbot, window, tab_states, worktree_service):
    tab = IdentityTab(tab_states, worktree_service)
    qtbot.addWidget(tab)
    return tab, window.add_pipeline_tab(tab)


def test_main_window_opens_with_one_new_pipeline_tab(window):
    assert window.tabs.count() == 1
    assert isinstance(window.tabs.widget(0), PipelineTab)
    assert window.tabs.tabText(0) == "New pipeline"
    assert window.tabs.tabToolTip(0) == ""
    assert window.tabs.currentIndex() == 0


def test_tabs_are_closable(window):
    assert window.tabs.tabsClosable()


def test_plus_button_is_the_tab_corner_widget(window):
    assert window.tabs.cornerWidget(Qt.Corner.TopRightCorner) is window.new_tab_button
    assert window.new_tab_button.text() == "+"


def test_plus_button_adds_and_selects_a_new_tab(qtbot, window):
    first = window.tabs.widget(0)
    qtbot.mouseClick(window.new_tab_button, Qt.MouseButton.LeftButton)
    assert window.tabs.count() == 2
    assert window.tabs.currentIndex() == 1
    new = window.tabs.widget(1)
    assert isinstance(new, PipelineTab)
    assert new is not first
    assert window.tabs.tabText(1) == "New pipeline"


def test_add_new_tab_returns_the_selected_tab(window):
    tab = window.add_new_tab()
    assert window.tabs.currentWidget() is tab


def test_close_request_removes_the_tab(window):
    a = window.tabs.widget(0)
    b = window.add_new_tab()
    assert a is not b
    window.tabs.tabCloseRequested.emit(0)
    assert window.tabs.count() == 1
    assert window.tabs.widget(0) is b


def test_closing_the_last_tab_adds_a_new_one(window):
    old = window.tabs.widget(0)
    window.close_tab(0)
    assert window.tabs.count() == 1
    new = window.tabs.widget(0)
    assert isinstance(new, PipelineTab)
    assert new is not old
    assert window.tabs.tabText(0) == "New pipeline"
    assert window.tabs.currentIndex() == 0


def test_closing_every_tab_leaves_one_new_tab(qtbot, window):
    qtbot.mouseClick(window.new_tab_button, Qt.MouseButton.LeftButton)
    qtbot.mouseClick(window.new_tab_button, Qt.MouseButton.LeftButton)
    assert window.tabs.count() == 3
    for _ in range(3):
        window.close_tab(0)
    assert window.tabs.count() == 1
    assert window.tabs.tabText(0) == "New pipeline"


def test_close_tab_with_invalid_index_does_nothing(window):
    tab = window.tabs.widget(0)
    window.close_tab(5)
    window.close_tab(-1)
    assert window.tabs.count() == 1
    assert window.tabs.widget(0) is tab


def test_closing_unsaved_tabs_asks_nothing(qtbot, window, monkeypatch):
    def fail(*args, **kwargs):
        pytest.fail("a dialog was shown")

    for name in ("question", "warning", "information", "critical"):
        monkeypatch.setattr(QMessageBox, name, fail)
    window.show()
    qtbot.waitExposed(window)
    window.add_new_tab()
    window.tabs.tabCloseRequested.emit(0)
    window.close()
    assert window.isHidden()


def test_add_pipeline_tab_uses_tab_identity(qtbot, window, tab_states, worktree_service):
    current = window.tabs.currentIndex()
    tab, index = add_identity_tab(qtbot, window, tab_states, worktree_service)
    assert window.tabs.widget(index) is tab
    assert window.tabs.tabText(index) == "t1"
    assert window.tabs.tabToolTip(index) == "p1"
    assert window.tabs.currentIndex() == current


def test_identity_changed_refreshes_tab_text(qtbot, window, tab_states, worktree_service):
    tab, _ = add_identity_tab(qtbot, window, tab_states, worktree_service)
    tab.title_text = "t2"
    tab.tooltip_text = "p2"
    tab.identity_changed.emit()
    index = window.tabs.indexOf(tab)
    assert window.tabs.tabText(index) == "t2"
    assert window.tabs.tabToolTip(index) == "p2"


def test_identity_changed_after_close_is_ignored(qtbot, window, tab_states, worktree_service):
    tab, index = add_identity_tab(qtbot, window, tab_states, worktree_service)
    window.close_tab(index)
    tab.title_text = "t2"
    tab.tooltip_text = "p2"
    tab.identity_changed.emit()
    assert window.tabs.count() == 1
    assert window.tabs.tabText(0) == "New pipeline"
    assert window.tabs.tabToolTip(0) == ""


@pytest.mark.parametrize("maximized", [True, False])
def test_close_saves_and_next_launch_restores_maximized(
    qtbot, make_window, tmp_path, maximized
):
    first = make_window()
    first.show_initial()
    if maximized:
        first.showMaximized()
    qtbot.waitUntil(lambda: first.isMaximized() == maximized)
    first.close()
    assert ConfigRepository(tmp_path / "config.json").load().window_maximized is maximized

    second = make_window()
    second.show_initial()
    qtbot.waitUntil(lambda: second.isMaximized() == maximized)


def test_add_saved_tab_adds_and_selects_a_saved_tab(window, tmp_path):
    path = tmp_path / "a.json"
    tab = window.add_saved_tab(path, TabState("a"))
    assert window.tabs.count() == 2
    assert window.tabs.currentWidget() is tab
    index = window.tabs.indexOf(tab)
    assert window.tabs.tabText(index) == "a"
    assert window.tabs.tabToolTip(index) == str(path)
    assert not path.exists()


def test_find_tab_returns_index_of_saved_tab(window, tmp_path):
    window.add_saved_tab(tmp_path / "a.json", TabState("a"))
    assert window.tabs.widget(0).state_path is None
    assert window.find_tab(tmp_path / "a.json") == 1
    assert window.find_tab(tmp_path / "x" / ".." / "a.json") == 1
    assert window.find_tab(tmp_path / "b.json") is None

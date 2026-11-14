"""Closing a tab or the window is refused while a worktree creation run is in progress."""

import threading
from pathlib import Path

import pytest
from PySide6.QtWidgets import QMessageBox

from devpipe.models.tab_state import TabState
from devpipe.persistence.config_repository import ConfigRepository
from devpipe.services.window_state_service import WindowStateService
from devpipe.views.pipeline_tab import PipelineTab

RUN_TIMEOUT_MS = 5000
REFUSAL = ("Worktree creation in progress", "Wait for the worktree creation to finish before closing.")


@pytest.fixture
def infos(monkeypatch):
    """(title, text) of every QMessageBox.information call."""
    shown = []

    def fake(parent, title, text, *args):
        shown.append((title, text))
        return QMessageBox.StandardButton.Ok

    monkeypatch.setattr(QMessageBox, "information", fake)
    return shown


@pytest.fixture
def window(qtbot, make_window):
    window = make_window()
    window.show()
    qtbot.waitExposed(window)
    return window


def config_bytes(tmp_path) -> bytes:
    return (tmp_path / "config.json").read_bytes()


def open_files(tmp_path) -> list[Path]:
    return ConfigRepository(tmp_path / "config.json").load().open_state_files


def saved_tab(window, tab_states, tmp_path, name) -> PipelineTab:
    folder = tmp_path / "states"
    folder.mkdir(exist_ok=True)
    path = folder / f"{name}.json"
    state = TabState(name)
    tab_states.save(path, state)
    return window.add_saved_tab(path, state)


def start_gated_run(tab, fake_git, tmp_path) -> None:
    fake_git.gate = threading.Event()
    tab.open_new_worktree_panel()
    source = tmp_path / f"src-{tab.title()}"
    parent = tmp_path / f"wt-{tab.title()}"
    source.mkdir()
    parent.mkdir()
    panel = tab.new_worktree_panel
    group = panel.groups()[0]
    group.source_input.setText(str(source))
    group.parent_input.setText(str(parent))
    assert panel.create_button.isEnabled()
    panel.create_button.click()
    assert tab.run_in_progress


def finish_run(qtbot, tab, fake_git) -> None:
    fake_git.gate.set()
    qtbot.waitUntil(lambda: not tab.run_in_progress, timeout=RUN_TIMEOUT_MS)


def test_closing_running_tab_is_refused(qtbot, tmp_path, window, tab_states, fake_git, infos):
    a = saved_tab(window, tab_states, tmp_path, "feat-a")
    saved_tab(window, tab_states, tmp_path, "feat-b")
    count = window.tabs.count()
    start_gated_run(a, fake_git, tmp_path)
    try:
        before = config_bytes(tmp_path)
        window.tabs.tabCloseRequested.emit(window.tabs.indexOf(a))
        assert infos == [REFUSAL]
        assert window.tabs.count() == count
        assert window.tabs.indexOf(a) >= 0
        assert config_bytes(tmp_path) == before
    finally:
        finish_run(qtbot, a, fake_git)


def test_closing_running_tab_directly_is_refused(
    qtbot, tmp_path, window, tab_states, fake_git, infos
):
    a = saved_tab(window, tab_states, tmp_path, "feat-a")
    window.close_tab(0)  # the initial unsaved tab, so that A is the only tab
    assert window.tabs.count() == 1
    assert window.tabs.widget(0) is a
    start_gated_run(a, fake_git, tmp_path)
    try:
        window.close_tab(0)
        assert infos == [REFUSAL]
        assert window.tabs.count() == 1
        assert window.tabs.widget(0) is a
    finally:
        finish_run(qtbot, a, fake_git)


def test_other_tab_closes_during_run(qtbot, tmp_path, window, tab_states, fake_git, infos):
    a = saved_tab(window, tab_states, tmp_path, "feat-a")
    b = saved_tab(window, tab_states, tmp_path, "feat-b")
    b_path = b.state_path
    count = window.tabs.count()
    start_gated_run(a, fake_git, tmp_path)
    try:
        assert b_path in open_files(tmp_path)
        window.close_tab(window.tabs.indexOf(b))
        assert infos == []
        assert window.tabs.count() == count - 1
        assert window.find_tab(b_path) is None
        assert b_path not in open_files(tmp_path)
        assert a.state_path in open_files(tmp_path)
    finally:
        finish_run(qtbot, a, fake_git)


def test_closing_window_during_run_is_refused(
    qtbot, tmp_path, window, tab_states, fake_git, infos, monkeypatch
):
    a = saved_tab(window, tab_states, tmp_path, "feat-a")
    b = saved_tab(window, tab_states, tmp_path, "feat-b")
    b_path = b.state_path
    assert window.tabs.currentWidget() is b
    count = window.tabs.count()
    remembered = []
    monkeypatch.setattr(
        WindowStateService, "remember_maximized", lambda self, value: remembered.append(value)
    )
    start_gated_run(a, fake_git, tmp_path)
    try:
        before = config_bytes(tmp_path)
        assert window.close() is False
        assert infos == [REFUSAL]
        assert window.isVisible()
        assert window.tabs.count() == count
        assert config_bytes(tmp_path) == before
        assert remembered == []
        window.close_tab(window.tabs.indexOf(b))
        assert b_path not in open_files(tmp_path)
        assert a.state_path in open_files(tmp_path)
    finally:
        finish_run(qtbot, a, fake_git)


def test_closing_works_after_run_finished(qtbot, tmp_path, window, tab_states, fake_git, infos):
    a = saved_tab(window, tab_states, tmp_path, "feat-a")
    saved_tab(window, tab_states, tmp_path, "feat-b")
    start_gated_run(a, fake_git, tmp_path)
    try:
        window.close_tab(window.tabs.indexOf(a))
        assert infos == [REFUSAL]
        with qtbot.waitSignal(a.run_finished, timeout=RUN_TIMEOUT_MS):
            fake_git.gate.set()
        window.close_tab(window.tabs.indexOf(a))
        assert window.tabs.indexOf(a) < 0
        assert infos == [REFUSAL]
    finally:
        finish_run(qtbot, a, fake_git)
    assert window.close() is True
    assert window.isHidden()


def test_out_of_range_close_during_run_does_nothing(
    qtbot, tmp_path, window, tab_states, fake_git, infos
):
    a = saved_tab(window, tab_states, tmp_path, "feat-a")
    count = window.tabs.count()
    start_gated_run(a, fake_git, tmp_path)
    try:
        window.close_tab(5)
        assert infos == []
        assert window.tabs.count() == count
    finally:
        finish_run(qtbot, a, fake_git)

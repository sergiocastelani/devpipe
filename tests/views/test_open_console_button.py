from pathlib import Path

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox

from devpipe.models.tab_state import Panel, TabState
from devpipe.models.terminal import TerminalError, TerminalId
from devpipe.persistence.skills_files import SkillsFiles
from devpipe.services.skills_service import SkillsService
from devpipe.views.open_console_button import OpenConsoleButton
from devpipe.views.pipeline_tab import PipelineTab

UNUSED_SKILLS = SkillsService(SkillsFiles(), Path("ai-skills"))  # never installed in these tests


@pytest.fixture
def warnings(monkeypatch):
    shown = []
    monkeypatch.setattr(
        QMessageBox, "warning", lambda parent, title, text, *a: shown.append((title, text))
    )
    return shown


def make_button(qtbot, terminal_service, folder=None):
    button = OpenConsoleButton(terminal_service, lambda: folder)
    qtbot.addWidget(button)
    return button


def test_no_folder_warns_and_opens_nothing(qtbot, terminal_service, fake_terminals, warnings):
    button = make_button(qtbot, terminal_service)
    with qtbot.assertNotEmitted(button.console_opened):
        assert button.open_console() is None
    assert fake_terminals.opened == []
    assert len(warnings) == 1


def test_folder_source_is_read_only_on_click(qtbot, terminal_service, fake_terminals, tmp_path):
    calls = []
    folders = iter([tmp_path / "a", tmp_path / "b"])
    for name in ("a", "b"):
        (tmp_path / name).mkdir()

    def source():
        calls.append(1)
        return next(folders)

    button = OpenConsoleButton(terminal_service, source)
    qtbot.addWidget(button)
    assert calls == []
    qtbot.mouseClick(button, Qt.MouseButton.LeftButton)
    qtbot.mouseClick(button, Qt.MouseButton.LeftButton)
    assert fake_terminals.opened == [tmp_path / "a", tmp_path / "b"]


def test_click_opens_a_new_console_in_the_folder_each_time(qtbot, terminal_service, fake_terminals, tmp_path):
    button = make_button(qtbot, terminal_service, tmp_path)
    with qtbot.waitSignal(button.console_opened, timeout=1000) as first:
        qtbot.mouseClick(button, Qt.MouseButton.LeftButton)
    with qtbot.waitSignal(button.console_opened, timeout=1000) as second:
        qtbot.mouseClick(button, Qt.MouseButton.LeftButton)
    assert fake_terminals.opened == [tmp_path, tmp_path]
    assert (first.args, second.args) == ([TerminalId("1")], [TerminalId("2")])


def test_missing_folder_warns_and_emits_nothing(qtbot, terminal_service, fake_terminals, tmp_path, warnings):
    button = make_button(qtbot, terminal_service, tmp_path / "missing")
    with qtbot.assertNotEmitted(button.console_opened):
        assert button.open_console() is None
    assert fake_terminals.opened == []
    assert len(warnings) == 1


def test_open_failure_warns(qtbot, terminal_service, fake_terminals, tmp_path, warnings):
    fake_terminals.open_error = TerminalError("cannot open terminal: boom")
    button = make_button(qtbot, terminal_service, tmp_path)
    assert button.open_console() is None
    assert "boom" in warnings[0][1]


def make_tab(qtbot, tab_states, worktree_service, terminal_service):
    tab = PipelineTab(tab_states, worktree_service, UNUSED_SKILLS, terminal_service)
    qtbot.addWidget(tab)
    return tab


def test_create_panel_console_starts_in_the_current_first_worktree(
    qtbot, tab_states, worktree_service, terminal_service, fake_terminals, tmp_path, warnings
):
    tab = make_tab(qtbot, tab_states, worktree_service, terminal_service)
    button = tab.devpipe_create_panel.open_console_button
    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir()
    b.mkdir()
    tab.apply_saved(tmp_path / "x.json", TabState("x", Panel.DEVPIPE_CREATE, [b, a]))
    button.open_console()
    tab.remove_worktree(b)
    button.open_console()
    tab.remove_worktree(a)
    assert button.open_console() is None
    assert fake_terminals.opened == [b, a]
    assert len(warnings) == 1


def test_last_console_id_is_kept_in_the_tab_session_not_the_file(
    qtbot, tab_states, worktree_service, terminal_service, tmp_path
):
    tab = make_tab(qtbot, tab_states, worktree_service, terminal_service)
    path = tmp_path / "x.json"
    tab.apply_saved(path, TabState("x", Panel.START, [tmp_path]))
    tab.show_panel(Panel.DEVPIPE_CREATE)
    file_before = path.read_text("utf-8")
    assert tab.session.last_console is None

    button = tab.devpipe_create_panel.open_console_button
    qtbot.mouseClick(button, Qt.MouseButton.LeftButton)
    qtbot.mouseClick(button, Qt.MouseButton.LeftButton)

    assert tab.session.last_console == TerminalId("2")
    tab.show_panel(Panel.DEVPIPE_CREATE)  # a later write still holds no terminal id
    assert path.read_text("utf-8") == file_before

from pathlib import Path

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox

from devpipe.models.tab_state import Panel, TabState
from devpipe.models.terminal import TerminalError, TerminalId
from devpipe.persistence.config_repository import ConfigRepository
from devpipe.persistence.control_files import ControlFiles
from devpipe.persistence.skills_files import SkillsFiles
from devpipe.services.session_service import SessionService
from devpipe.services.skills_service import SkillsService
from devpipe.views.open_console_button import OpenConsoleButton
from devpipe.views.pipeline_tab import PipelineTab

UNUSED_SKILLS = SkillsService(SkillsFiles(), Path("ai-skills"))  # never installed in these tests
UNUSED_SESSION = SessionService(ConfigRepository(Path("unused-config.json")), ControlFiles())  # no feature spec: stage CREATE


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


def test_second_click_brings_the_open_console_to_front(qtbot, terminal_service, fake_terminals, tmp_path):
    button = make_button(qtbot, terminal_service, tmp_path)
    with qtbot.waitSignal(button.console_opened, timeout=1000) as first:
        qtbot.mouseClick(button, Qt.MouseButton.LeftButton)
    with qtbot.waitSignal(button.console_opened, timeout=1000) as second:
        qtbot.mouseClick(button, Qt.MouseButton.LeftButton)
    assert fake_terminals.opened == [tmp_path]
    assert fake_terminals.fronted == [TerminalId("1")]
    assert (first.args, second.args) == ([TerminalId("1")], [TerminalId("1")])


def test_click_opens_a_new_console_after_the_user_closed_it(qtbot, terminal_service, fake_terminals, tmp_path):
    button = make_button(qtbot, terminal_service, tmp_path)
    button.open_console()
    fake_terminals.closed.add(TerminalId("1"))
    assert button.open_console() == TerminalId("2")
    assert fake_terminals.opened == [tmp_path, tmp_path]
    assert fake_terminals.fronted == []


def test_bring_to_front_failure_warns(qtbot, terminal_service, fake_terminals, tmp_path, warnings):
    button = make_button(qtbot, terminal_service, tmp_path)
    button.open_console()
    fake_terminals.front_error = TerminalError("cannot find terminal window: boom")
    with qtbot.assertNotEmitted(button.console_opened):
        assert button.open_console() is None
    assert "boom" in warnings[0][1]


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
    tab = PipelineTab(tab_states, worktree_service, UNUSED_SKILLS, terminal_service, UNUSED_SESSION)
    qtbot.addWidget(tab)
    return tab


def test_tab_console_starts_in_the_current_first_worktree(
    qtbot, tab_states, worktree_service, terminal_service, fake_terminals, tmp_path, warnings
):
    tab = make_tab(qtbot, tab_states, worktree_service, terminal_service)
    button = tab.open_console_button
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

    button = tab.open_console_button
    qtbot.mouseClick(button, Qt.MouseButton.LeftButton)
    tab.session.last_console = None
    qtbot.mouseClick(button, Qt.MouseButton.LeftButton)  # brings the same console to front

    assert tab.session.last_console == TerminalId("1")
    tab.show_panel(Panel.DEVPIPE_CREATE)  # a later write still holds no terminal id
    assert path.read_text("utf-8") == file_before

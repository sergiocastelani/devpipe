"""The "Send prompt to terminal" button of the devpipe create panel."""

from pathlib import Path

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox

from devpipe.models.tab_state import Panel, TabState
from devpipe.models.terminal import TerminalError, TerminalId
from devpipe.persistence.control_files import ControlFiles
from devpipe.persistence.skills_files import SkillsFiles
from devpipe.services.control_files_service import ControlFilesService
from devpipe.services.skills_service import SkillsService
from devpipe.views.pipeline_tab import PipelineTab

UNUSED_SKILLS = SkillsService(SkillsFiles(), Path("ai-skills"))
UNUSED_CONTROL_FILES = ControlFilesService(ControlFiles())  # no feature spec in these tests


@pytest.fixture
def warnings(monkeypatch):
    shown = []
    monkeypatch.setattr(QMessageBox, "warning", lambda parent, title, text, *a: shown.append((title, text)))
    return shown


@pytest.fixture
def tab(qtbot, tab_states, worktree_service, terminal_service, tmp_path):
    tab = PipelineTab(tab_states, worktree_service, UNUSED_SKILLS, terminal_service, UNUSED_CONTROL_FILES)
    qtbot.addWidget(tab)
    tab.show()  # show events only reach visible widgets
    tab.apply_saved(tmp_path / "x.json", TabState("feat", Panel.START, [tmp_path], "build it"))
    tab.show_panel(Panel.DEVPIPE_CREATE)
    return tab


def click(qtbot, button):
    qtbot.mouseClick(button, Qt.MouseButton.LeftButton)


def test_disabled_until_the_console_button_opens_a_terminal(qtbot, tab):
    panel = tab.devpipe_create_panel
    assert not panel.send_prompt_button.isEnabled()
    click(qtbot, tab.open_console_button)
    assert panel.send_prompt_button.isEnabled()


def test_state_is_refreshed_when_the_panel_is_shown(qtbot, tab, fake_terminals):
    panel = tab.devpipe_create_panel
    click(qtbot, tab.open_console_button)
    tab.show_panel(Panel.START)
    fake_terminals.closed.add(TerminalId("1"))
    tab.show_panel(Panel.DEVPIPE_CREATE)
    assert not panel.send_prompt_button.isEnabled()


def test_console_button_failure_keeps_it_disabled(qtbot, tab, fake_terminals, warnings):
    fake_terminals.open_error = TerminalError("boom")
    panel = tab.devpipe_create_panel
    click(qtbot, tab.open_console_button)
    assert not panel.send_prompt_button.isEnabled()


def test_click_brings_the_terminal_to_front_and_types_the_command(qtbot, tab, fake_terminals, warnings):
    panel = tab.devpipe_create_panel
    click(qtbot, tab.open_console_button)
    panel.prompt_input.setPlainText("line 1\nline 2")  # the current text, even before it is saved
    fake_terminals.fronted.clear()
    click(qtbot, panel.send_prompt_button)
    assert fake_terminals.fronted == [TerminalId("1")]
    assert fake_terminals.sent == [(TerminalId("1"), "/devpipe-create feat \n line 1\nline 2", False, True)]
    assert warnings == []


def test_terminal_closed_before_the_click_disables_without_sending(qtbot, tab, fake_terminals, warnings):
    panel = tab.devpipe_create_panel
    click(qtbot, tab.open_console_button)
    fake_terminals.closed.add(TerminalId("1"))
    panel.send_prompt()
    assert fake_terminals.sent == []
    assert not panel.send_prompt_button.isEnabled()


def test_send_failure_warns(qtbot, tab, fake_terminals, warnings):
    panel = tab.devpipe_create_panel
    click(qtbot, tab.open_console_button)
    fake_terminals.send_error = TerminalError("write failed: boom")
    click(qtbot, panel.send_prompt_button)
    assert "boom" in warnings[0][1]
    assert panel.send_prompt_button.isEnabled()

"""The "Send 'create' prompt", "Send 'plan' prompt", "Send 'steps' prompt" and
"Send 'implementation' prompt" buttons of the devpipe create panel."""

from pathlib import Path

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox

from devpipe.models.control_files import (
    DESIGN_CONTRACT_FILE_NAME,
    FEATURE_SPEC_FILE_NAME,
    PLAN_FILE_NAME,
    DevpipeStage,
    feature_folder,
)
from devpipe.models.tab_state import Panel, TabState
from devpipe.models.terminal import TerminalError, TerminalId
from devpipe.persistence.config_repository import ConfigRepository
from devpipe.persistence.control_files import ControlFiles
from devpipe.persistence.skills_files import SkillsFiles
from devpipe.services.session_service import SessionService
from devpipe.services.skills_service import SkillsService
from devpipe.views.pipeline_tab import PipelineTab

UNUSED_SKILLS = SkillsService(SkillsFiles(), Path("ai-skills"))

# The control files each stage needs; only the session (the stage) sees them.
STAGE_FILES = {
    DevpipeStage.CREATE: (),
    DevpipeStage.PLAN: (FEATURE_SPEC_FILE_NAME,),
    DevpipeStage.STEPS: (FEATURE_SPEC_FILE_NAME, PLAN_FILE_NAME),
    DevpipeStage.IMPLEMENTATION: (FEATURE_SPEC_FILE_NAME, PLAN_FILE_NAME, DESIGN_CONTRACT_FILE_NAME),
}

APPROVED_CONTRACT = "| Step | Status |\n|---|---|\n| 01 | approved |\n"


class FakeControlFiles:
    def __init__(self) -> None:
        self.existing: set[Path] = set()

    def file_exists(self, path: Path) -> bool:
        return path in self.existing

    def read_text(self, path: Path) -> str | None:
        # A listed design contract has every step approved (stage IMPLEMENTATION);
        # without one the stage is STEPS once the plan exists.
        if path.name == DESIGN_CONTRACT_FILE_NAME and path in self.existing:
            return APPROVED_CONTRACT
        return None


@pytest.fixture
def warnings(monkeypatch):
    shown = []
    monkeypatch.setattr(QMessageBox, "warning", lambda parent, title, text, *a: shown.append((title, text)))
    return shown


@pytest.fixture
def stage_files(tmp_path):
    """Control files seen by the tab's session; call set_stage to move the tab's stage."""
    return FakeControlFiles()


def set_stage(stage_files, worktree, stage):
    folder = feature_folder(worktree, "feat")
    stage_files.existing = {folder / name for name in STAGE_FILES[stage]}


@pytest.fixture
def tab(qtbot, tab_states, worktree_service, terminal_service, tmp_path, stage_files):
    session = SessionService(ConfigRepository(tmp_path / "config.json"), stage_files)
    tab = PipelineTab(tab_states, worktree_service, UNUSED_SKILLS, terminal_service, session)
    qtbot.addWidget(tab)
    tab.show()  # show events only reach visible widgets
    tab.apply_saved(tmp_path / "x.json", TabState("feat", Panel.START, [tmp_path], "build it"))
    tab.show_panel(Panel.DEVPIPE_CREATE)
    return tab


@pytest.fixture
def plan_tab(tab, stage_files, tmp_path):
    """The tab at the PLAN stage (feature spec written, no plan yet)."""
    set_stage(stage_files, tmp_path, DevpipeStage.PLAN)
    return tab


def click(qtbot, button):
    qtbot.mouseClick(button, Qt.MouseButton.LeftButton)


def test_disabled_until_the_console_button_opens_a_terminal(qtbot, tab):
    panel = tab.devpipe_create_panel
    assert not panel.send_create_button.isEnabled()
    click(qtbot, tab.open_console_button)
    assert panel.send_create_button.isEnabled()


def test_state_is_refreshed_when_the_panel_is_shown(qtbot, tab, fake_terminals):
    panel = tab.devpipe_create_panel
    click(qtbot, tab.open_console_button)
    tab.show_panel(Panel.START)
    fake_terminals.closed.add(TerminalId("1"))
    tab.show_panel(Panel.DEVPIPE_CREATE)
    assert not panel.send_create_button.isEnabled()


def test_console_button_failure_keeps_it_disabled(qtbot, tab, fake_terminals, warnings):
    fake_terminals.open_error = TerminalError("boom")
    panel = tab.devpipe_create_panel
    click(qtbot, tab.open_console_button)
    assert not panel.send_create_button.isEnabled()


def test_click_brings_the_terminal_to_front_and_types_the_command(qtbot, tab, fake_terminals, warnings):
    panel = tab.devpipe_create_panel
    click(qtbot, tab.open_console_button)
    panel.prompt_input.setPlainText("line 1\nline 2")  # the current text, even before it is saved
    fake_terminals.fronted.clear()
    click(qtbot, panel.send_create_button)
    assert fake_terminals.fronted == [TerminalId("1")]
    assert fake_terminals.sent == [(TerminalId("1"), "/devpipe-create feat \n line 1\nline 2", False, True)]
    assert warnings == []


def test_terminal_closed_before_the_click_disables_without_sending(qtbot, tab, fake_terminals, warnings):
    panel = tab.devpipe_create_panel
    click(qtbot, tab.open_console_button)
    fake_terminals.closed.add(TerminalId("1"))
    panel.send_create_prompt()
    assert fake_terminals.sent == []
    assert not panel.send_create_button.isEnabled()


def test_send_failure_warns(qtbot, tab, fake_terminals, warnings):
    panel = tab.devpipe_create_panel
    click(qtbot, tab.open_console_button)
    fake_terminals.send_error = TerminalError("write failed: boom")
    click(qtbot, panel.send_create_button)
    assert "boom" in warnings[0][1]
    assert panel.send_create_button.isEnabled()


def test_plan_button_is_disabled_until_the_console_button_opens_a_terminal(qtbot, plan_tab):
    tab = plan_tab
    panel = tab.devpipe_create_panel
    assert not panel.send_plan_button.isEnabled()
    click(qtbot, tab.open_console_button)
    assert panel.send_plan_button.isEnabled()


def test_plan_click_brings_the_terminal_to_front_and_types_the_plan_command(qtbot, plan_tab, fake_terminals, warnings):
    tab = plan_tab
    panel = tab.devpipe_create_panel
    click(qtbot, tab.open_console_button)
    panel.prompt_input.setPlainText("not sent")  # the plan command carries no prompt
    fake_terminals.fronted.clear()
    click(qtbot, panel.send_plan_button)
    assert fake_terminals.fronted == [TerminalId("1")]
    assert fake_terminals.sent == [(TerminalId("1"), "/devpipe-plan feat", False, True)]
    assert warnings == []


def test_plan_terminal_closed_before_the_click_disables_without_sending(qtbot, plan_tab, fake_terminals, warnings):
    tab = plan_tab
    panel = tab.devpipe_create_panel
    click(qtbot, tab.open_console_button)
    fake_terminals.closed.add(TerminalId("1"))
    panel.send_plan_prompt()
    assert fake_terminals.sent == []
    assert not panel.send_plan_button.isEnabled()


def test_plan_send_failure_warns(qtbot, plan_tab, fake_terminals, warnings):
    tab = plan_tab
    panel = tab.devpipe_create_panel
    click(qtbot, tab.open_console_button)
    fake_terminals.send_error = TerminalError("write failed: boom")
    click(qtbot, panel.send_plan_button)
    assert "boom" in warnings[0][1]
    assert panel.send_plan_button.isEnabled()


def test_steps_click_brings_the_terminal_to_front_and_types_the_steps_command(
    qtbot, tab, stage_files, tmp_path, fake_terminals, warnings
):
    panel = tab.devpipe_create_panel
    set_stage(stage_files, tmp_path, DevpipeStage.STEPS)
    click(qtbot, tab.open_console_button)
    panel.prompt_input.setPlainText("not sent")  # the steps command carries its own prompt
    fake_terminals.fronted.clear()
    click(qtbot, panel.send_steps_button)
    assert fake_terminals.fronted == [TerminalId("1")]
    assert fake_terminals.sent == [(TerminalId("1"), "/devpipe-steps feat \n Detail remaining steps", False, True)]
    assert warnings == []


def test_implementation_click_brings_the_terminal_to_front_and_types_the_implement_command(
    qtbot, tab, stage_files, tmp_path, fake_terminals, warnings
):
    panel = tab.devpipe_create_panel
    set_stage(stage_files, tmp_path, DevpipeStage.IMPLEMENTATION)
    click(qtbot, tab.open_console_button)
    panel.prompt_input.setPlainText("not sent")  # the implement command carries its own prompt
    fake_terminals.fronted.clear()
    click(qtbot, panel.send_implementation_button)
    assert fake_terminals.fronted == [TerminalId("1")]
    assert fake_terminals.sent == [
        (TerminalId("1"), "/devpipe-implement feat \n Implement the next stage", False, True)
    ]
    assert warnings == []


@pytest.mark.parametrize(
    "stage, create_enabled, plan_enabled, steps_enabled, implementation_enabled",
    [
        (DevpipeStage.CREATE, True, False, False, False),
        (DevpipeStage.PLAN, False, True, False, False),
        (DevpipeStage.STEPS, False, False, True, False),
        (DevpipeStage.IMPLEMENTATION, False, False, False, True),
    ],
)
def test_each_button_is_enabled_only_at_its_stage(
    qtbot, tab, stage_files, tmp_path, stage, create_enabled, plan_enabled, steps_enabled, implementation_enabled
):
    panel = tab.devpipe_create_panel
    set_stage(stage_files, tmp_path, stage)
    click(qtbot, tab.open_console_button)
    assert panel.send_create_button.isEnabled() is create_enabled
    assert panel.send_plan_button.isEnabled() is plan_enabled
    assert panel.send_steps_button.isEnabled() is steps_enabled
    assert panel.send_implementation_button.isEnabled() is implementation_enabled


def test_buttons_follow_the_stage_on_refresh(qtbot, tab, stage_files, tmp_path):
    panel = tab.devpipe_create_panel
    click(qtbot, tab.open_console_button)
    set_stage(stage_files, tmp_path, DevpipeStage.PLAN)
    click(qtbot, tab.refresh_button)
    assert not panel.send_create_button.isEnabled()
    assert panel.send_plan_button.isEnabled()

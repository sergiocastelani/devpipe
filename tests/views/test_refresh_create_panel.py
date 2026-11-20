"""The devpipe create panel's refresh: the Refresh button and showing the panel keep
the tab on the create panel, also once `.devpipe/<feature-name>/feature-spec.md` exists."""

import json
from pathlib import Path

import pytest
from PySide6.QtCore import Qt

from devpipe.models.tab_state import Panel, TabState
from devpipe.models.terminal import TerminalId
from devpipe.persistence.config_repository import ConfigRepository
from devpipe.persistence.control_files import ControlFiles
from devpipe.persistence.skills_files import SkillsFiles
from devpipe.services.session_service import SessionService
from devpipe.services.skills_service import SkillsService
from devpipe.views.pipeline_tab import PipelineTab

UNUSED_SKILLS = SkillsService(SkillsFiles(), Path("ai-skills"))
SESSION = SessionService(ConfigRepository(Path("unused-config.json")), ControlFiles())  # stage from the real files
WAIT_MS = 2000


@pytest.fixture
def worktree(tmp_path) -> Path:
    path = tmp_path / "wt"
    path.mkdir()
    return path


@pytest.fixture
def make_tab(qtbot, tab_states, worktree_service, terminal_service, tmp_path, worktree):
    def make(active_panel=Panel.START):
        tab = PipelineTab(tab_states, worktree_service, UNUSED_SKILLS, terminal_service, SESSION)
        qtbot.addWidget(tab)
        tab.show()  # show events only reach visible widgets
        tab.apply_saved(tmp_path / "x.json", TabState("feat", active_panel, [worktree], "build it"))
        return tab

    return make


def make_feature_folder(worktree: Path) -> Path:
    folder = worktree / ".devpipe" / "feat"
    folder.mkdir(parents=True)
    return folder


def make_feature_spec(worktree: Path) -> None:
    (make_feature_folder(worktree) / "feature-spec.md").write_text("# spec", encoding="utf-8")


def click(qtbot, button):
    qtbot.mouseClick(button, Qt.MouseButton.LeftButton)


def test_refresh_with_the_spec_stays_on_the_create_panel(qtbot, make_tab, worktree, tmp_path):
    tab = make_tab()
    tab.show_panel(Panel.DEVPIPE_CREATE)
    make_feature_spec(worktree)
    click(qtbot, tab.refresh_button)
    qtbot.wait(50)  # let a queued switch run, if any
    assert tab.stack.currentWidget() is tab.devpipe_create_panel
    assert json.loads((tmp_path / "x.json").read_text(encoding="utf-8"))["active_panel"] == "devpipe-create"


def test_restoring_a_tab_on_the_create_panel_with_the_spec_stays_on_it(qtbot, make_tab, worktree):
    make_feature_spec(worktree)
    tab = make_tab(Panel.DEVPIPE_CREATE)
    qtbot.wait(50)
    assert tab.stack.currentWidget() is tab.devpipe_create_panel


def test_refresh_keeps_a_pending_prompt_edit(qtbot, make_tab, tmp_path):
    tab = make_tab()
    tab.show_panel(Panel.DEVPIPE_CREATE)
    panel = tab.devpipe_create_panel
    panel.prompt_input.setPlainText("new text")  # pending: the save delay has not passed
    click(qtbot, tab.refresh_button)
    assert panel.prompt_input.toPlainText() == "new text"
    assert json.loads((tmp_path / "x.json").read_text(encoding="utf-8"))["create_prompt"] == "new text"


def test_refresh_updates_the_send_button(qtbot, make_tab, fake_terminals):
    tab = make_tab()
    tab.show_panel(Panel.DEVPIPE_CREATE)
    panel = tab.devpipe_create_panel
    click(qtbot, tab.open_console_button)
    assert panel.send_create_button.isEnabled()
    assert not panel.send_plan_button.isEnabled()  # no feature spec: stage CREATE
    fake_terminals.closed.add(TerminalId("1"))
    click(qtbot, tab.refresh_button)
    assert not panel.send_create_button.isEnabled()
    assert not panel.send_plan_button.isEnabled()


def test_refresh_only_refreshes_the_active_panel(qtbot, make_tab, worktree):
    tab = make_tab()  # start panel active
    make_feature_spec(worktree)
    click(qtbot, tab.refresh_button)
    qtbot.wait(50)  # let a queued switch run, if any
    assert tab.active_panel is Panel.START

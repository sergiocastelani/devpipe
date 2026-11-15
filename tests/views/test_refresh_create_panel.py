"""The devpipe create panel's refresh: the Refresh button and showing the panel
move the tab on to the devpipe plan panel once `.devpipe/<feature-name>/feature-spec.md` exists."""

import json
from pathlib import Path

import pytest
from PySide6.QtCore import Qt

from devpipe.models.tab_state import Panel, TabState
from devpipe.models.terminal import TerminalId
from devpipe.persistence.skills_files import SkillsFiles
from devpipe.services.skills_service import SkillsService
from devpipe.views.pipeline_tab import PipelineTab

UNUSED_SKILLS = SkillsService(SkillsFiles(), Path("ai-skills"))
WAIT_MS = 2000


@pytest.fixture
def worktree(tmp_path) -> Path:
    path = tmp_path / "wt"
    path.mkdir()
    return path


@pytest.fixture
def make_tab(qtbot, tab_states, worktree_service, terminal_service, control_files, tmp_path, worktree):
    def make(active_panel=Panel.START):
        tab = PipelineTab(tab_states, worktree_service, UNUSED_SKILLS, terminal_service, control_files)
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


def test_refresh_without_the_spec_stays_on_the_create_panel(qtbot, make_tab, worktree):
    tab = make_tab()
    tab.show_panel(Panel.DEVPIPE_CREATE)
    make_feature_folder(worktree)  # the folder alone is not enough
    click(qtbot, tab.devpipe_create_panel.refresh_button)
    qtbot.wait(50)  # let a queued switch run, if any
    assert tab.active_panel is Panel.DEVPIPE_CREATE


def test_refresh_with_the_spec_shows_the_plan_panel_and_saves_it(qtbot, make_tab, worktree, tmp_path):
    tab = make_tab()
    tab.show_panel(Panel.DEVPIPE_CREATE)
    make_feature_spec(worktree)
    click(qtbot, tab.devpipe_create_panel.refresh_button)
    qtbot.waitUntil(lambda: tab.active_panel is Panel.DEVPIPE_PLAN, timeout=WAIT_MS)
    assert tab.stack.currentWidget() is tab.devpipe_plan_panel
    assert json.loads((tmp_path / "x.json").read_text(encoding="utf-8"))["active_panel"] == "devpipe-plan"


def test_showing_the_create_panel_with_the_spec_shows_the_plan_panel(qtbot, make_tab, worktree):
    tab = make_tab()
    make_feature_spec(worktree)
    tab.show_panel(Panel.DEVPIPE_CREATE)
    qtbot.waitUntil(lambda: tab.active_panel is Panel.DEVPIPE_PLAN, timeout=WAIT_MS)


def test_restoring_a_tab_on_the_create_panel_with_the_spec_shows_the_plan_panel(qtbot, make_tab, worktree):
    make_feature_spec(worktree)
    tab = make_tab(Panel.DEVPIPE_CREATE)
    qtbot.waitUntil(lambda: tab.active_panel is Panel.DEVPIPE_PLAN, timeout=WAIT_MS)


def test_refresh_keeps_a_pending_prompt_edit(qtbot, make_tab, tmp_path):
    tab = make_tab()
    tab.show_panel(Panel.DEVPIPE_CREATE)
    panel = tab.devpipe_create_panel
    panel.prompt_input.setPlainText("new text")  # pending: the save delay has not passed
    click(qtbot, panel.refresh_button)
    assert panel.prompt_input.toPlainText() == "new text"
    assert json.loads((tmp_path / "x.json").read_text(encoding="utf-8"))["create_prompt"] == "new text"


def test_refresh_updates_the_send_button(qtbot, make_tab, fake_terminals):
    tab = make_tab()
    tab.show_panel(Panel.DEVPIPE_CREATE)
    panel = tab.devpipe_create_panel
    click(qtbot, tab.open_console_button)
    assert panel.send_prompt_button.isEnabled()
    fake_terminals.closed.add(TerminalId("1"))
    click(qtbot, panel.refresh_button)
    assert not panel.send_prompt_button.isEnabled()

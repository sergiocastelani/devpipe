"""The '/devpipe-create' prompt box of the devpipe create panel: debounced save,
flush on hide, refresh on show."""

import json
from pathlib import Path

import pytest
from PySide6.QtWidgets import QMessageBox

from devpipe.models.tab_state import Panel, TabState
from devpipe.persistence.control_files import ControlFiles
from devpipe.persistence.skills_files import SkillsFiles
from devpipe.persistence.tab_state_repository import TabStateRepository
from devpipe.services.control_files_service import ControlFilesService
from devpipe.services.skills_service import SkillsService
from devpipe.services.tab_state_service import TabStateService
from devpipe.services.terminal_service import TerminalService
from devpipe.views import devpipe_create_panel
from devpipe.views.pipeline_tab import PipelineTab

UNUSED_SKILLS = SkillsService(SkillsFiles(), Path("ai-skills"))
UNUSED_CONTROL_FILES = ControlFilesService(ControlFiles())  # no feature spec in these tests
UNUSED_TERMINALS = TerminalService(None)
SHORT_DELAY_MS = 50
WAIT_MS = 2000


class CountingStore(TabStateRepository):
    """The real repository, recording the create_prompt of every save."""

    def __init__(self) -> None:
        self.saved_prompts: list[str] = []

    def save(self, path, state):
        self.saved_prompts.append(state.create_prompt)
        super().save(path, state)


@pytest.fixture
def store() -> CountingStore:
    return CountingStore()


@pytest.fixture
def short_delay(monkeypatch):
    monkeypatch.setattr(devpipe_create_panel, "PROMPT_SAVE_DELAY_MS", SHORT_DELAY_MS)


@pytest.fixture
def warnings(monkeypatch):
    shown = []
    monkeypatch.setattr(QMessageBox, "warning", lambda parent, title, text, *a: shown.append((title, text)))
    return shown


def make_tab(qtbot, store, worktree_service):
    tab = PipelineTab(
        TabStateService(store), worktree_service, UNUSED_SKILLS, UNUSED_TERMINALS, UNUSED_CONTROL_FILES
    )
    qtbot.addWidget(tab)
    tab.show()  # the panel reads the kept prompt on show; show and hide events only reach visible widgets
    return tab


def saved_prompt(path):
    return json.loads(path.read_text("utf-8"))["create_prompt"]


def open_create_panel(tab, path, prompt=""):
    tab.apply_saved(path, TabState("x", Panel.START, [], prompt))
    tab.show_panel(Panel.DEVPIPE_CREATE)


def test_prompt_is_saved_after_the_delay(qtbot, store, worktree_service, tmp_path, short_delay, warnings):
    tab = make_tab(qtbot, store, worktree_service)
    path = tmp_path / "x.json"
    open_create_panel(tab, path)
    tab.devpipe_create_panel.prompt_input.setPlainText("build it")
    assert saved_prompt(path) == ""  # not before the delay
    qtbot.waitUntil(lambda: saved_prompt(path) == "build it", timeout=WAIT_MS)
    assert warnings == []


def test_edits_within_the_delay_are_saved_once(qtbot, store, worktree_service, tmp_path, short_delay):
    tab = make_tab(qtbot, store, worktree_service)
    path = tmp_path / "x.json"
    open_create_panel(tab, path)
    store.saved_prompts.clear()
    box = tab.devpipe_create_panel.prompt_input
    box.setPlainText("a")
    box.setPlainText("ab")
    box.setPlainText("abc")
    with qtbot.waitSignal(tab.devpipe_create_panel.prompt_changed, timeout=WAIT_MS):
        pass
    assert store.saved_prompts == ["abc"]
    assert saved_prompt(path) == "abc"


def test_unchanged_prompt_is_not_written(qtbot, store, worktree_service, tmp_path, short_delay):
    tab = make_tab(qtbot, store, worktree_service)
    path = tmp_path / "x.json"
    open_create_panel(tab, path, "same")
    store.saved_prompts.clear()
    with qtbot.waitSignal(tab.devpipe_create_panel.prompt_changed, timeout=WAIT_MS):
        tab.devpipe_create_panel.prompt_input.setPlainText("same")
    assert store.saved_prompts == []


def test_leaving_the_panel_saves_a_pending_edit(qtbot, store, worktree_service, tmp_path):
    tab = make_tab(qtbot, store, worktree_service)
    path = tmp_path / "x.json"
    open_create_panel(tab, path)
    tab.devpipe_create_panel.prompt_input.setPlainText("typed")  # default delay: still pending
    tab.show_panel(Panel.START)
    assert saved_prompt(path) == "typed"
    tab.show_panel(Panel.DEVPIPE_CREATE)
    assert tab.devpipe_create_panel.prompt_input.toPlainText() == "typed"


def test_showing_the_panel_shows_the_saved_prompt(qtbot, store, worktree_service, tmp_path):
    tab = make_tab(qtbot, store, worktree_service)
    path = tmp_path / "x.json"
    open_create_panel(tab, path, "saved prompt")
    panel = tab.devpipe_create_panel
    assert panel.prompt_input.toPlainText() == "saved prompt"
    assert panel.prompt_label.text() == "Prompt for '/devpipe-create x':"


def test_showing_the_panel_does_not_save(qtbot, store, worktree_service, tmp_path, short_delay):
    tab = make_tab(qtbot, store, worktree_service)
    path = tmp_path / "x.json"
    open_create_panel(tab, path, "saved prompt")
    store.saved_prompts.clear()
    with qtbot.assertNotEmitted(tab.devpipe_create_panel.prompt_changed, wait=SHORT_DELAY_MS * 4):
        pass
    assert store.saved_prompts == []


def test_saved_prompt_reloads_into_the_panel(qtbot, store, worktree_service, tmp_path, short_delay):
    tab = make_tab(qtbot, store, worktree_service)
    path = tmp_path / "x.json"
    open_create_panel(tab, path)
    with qtbot.waitSignal(tab.devpipe_create_panel.prompt_changed, timeout=WAIT_MS):
        tab.devpipe_create_panel.prompt_input.setPlainText("line 1\nline 2")
    reloaded = make_tab(qtbot, store, worktree_service)
    reloaded.apply_saved(path, TabStateService(store).load(path))
    assert reloaded.active_panel is Panel.DEVPIPE_CREATE
    assert reloaded.devpipe_create_panel.prompt_input.toPlainText() == "line 1\nline 2"


def test_unsaved_tab_keeps_the_prompt_for_the_first_save(qtbot, store, worktree_service, tmp_path, short_delay):
    tab = make_tab(qtbot, store, worktree_service)
    tab.show_panel(Panel.DEVPIPE_CREATE)
    with qtbot.waitSignal(tab.devpipe_create_panel.prompt_changed, timeout=WAIT_MS):
        tab.devpipe_create_panel.prompt_input.setPlainText("early")
    assert list(tmp_path.iterdir()) == []
    path = tmp_path / "x.json"
    assert tab.save_as(path, "x")
    assert saved_prompt(path) == "early"


def test_label_marks_a_pending_edit_until_it_is_saved(qtbot, store, worktree_service, tmp_path, short_delay):
    tab = make_tab(qtbot, store, worktree_service)
    path = tmp_path / "x.json"
    open_create_panel(tab, path)
    label = tab.devpipe_create_panel.prompt_label
    clean_text = label.text()
    assert not clean_text.endswith(devpipe_create_panel.PENDING_MARK)
    tab.devpipe_create_panel.prompt_input.setPlainText("typed")
    assert label.text() == clean_text + devpipe_create_panel.PENDING_MARK
    with qtbot.waitSignal(tab.devpipe_create_panel.prompt_changed, timeout=WAIT_MS):
        pass
    assert label.text() == clean_text

import json
import shutil
from pathlib import Path

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFileDialog, QMessageBox

from devpipe.models.tab_state import Panel, TabState
from devpipe.persistence.config_repository import ConfigRepository
from devpipe.persistence.control_files import ControlFiles
from devpipe.persistence.skills_files import SkillsFiles
from devpipe.services.session_service import SessionService
from devpipe.services.skills_service import SkillsService
from devpipe.services.terminal_service import TerminalService
from devpipe.views.pipeline_tab import PipelineTab

EXPECTED_FILE = {"version": 3, "feature_name": "x", "active_panel": "start", "worktrees": [], "create_prompt": ""}
UNUSED_SKILLS = SkillsService(SkillsFiles(), Path("ai-skills"))  # never installed in these tests
UNUSED_SESSION = SessionService(ConfigRepository(Path("unused-config.json")), ControlFiles())  # no feature spec: stage CREATE
UNUSED_TERMINALS = TerminalService(None)  # never opens a console in these tests


def make_tab(qtbot, tab_states, worktree_service):
    tab = PipelineTab(tab_states, worktree_service, UNUSED_SKILLS, UNUSED_TERMINALS, UNUSED_SESSION)
    qtbot.addWidget(tab)
    return tab


@pytest.fixture
def warnings(monkeypatch):
    """(title, text) of every QMessageBox.warning call."""
    shown = []

    def fake(parent, title, text, *args):
        shown.append((title, text))
        return QMessageBox.StandardButton.Ok

    monkeypatch.setattr(QMessageBox, "warning", fake)
    return shown


def read_json(path):
    return json.loads(path.read_text("utf-8"))


def test_new_tab_starts_on_start_panel(qtbot, tab_states, worktree_service):
    tab = make_tab(qtbot, tab_states, worktree_service)
    assert tab.stack.currentWidget() is tab.start_panel
    assert tab.active_panel is Panel.START


def test_new_tab_identity(qtbot, tab_states, worktree_service):
    tab = make_tab(qtbot, tab_states, worktree_service)
    assert tab.title() == "New pipeline"
    assert tab.tooltip() == ""


def test_new_tab_start_panel_is_unsaved(qtbot, tab_states, worktree_service):
    tab = make_tab(qtbot, tab_states, worktree_service)
    panel = tab.start_panel
    assert not panel.save_button.isEnabled()
    assert not panel.new_worktree_button.isEnabled()


def test_new_tab_is_unsaved(qtbot, tab_states, worktree_service):
    tab = make_tab(qtbot, tab_states, worktree_service)
    assert tab.state_path is None
    assert tab.active_panel is Panel.START
    assert tab.title() == "New pipeline"
    assert tab.tooltip() == ""


def test_apply_saved_switches_to_saved_mode_without_writing(qtbot, tab_states, worktree_service, tmp_path):
    tab = make_tab(qtbot, tab_states, worktree_service)
    path = tmp_path / "x.json"
    with qtbot.waitSignal(tab.identity_changed, timeout=1000):
        tab.apply_saved(path, TabState("x"))
    assert tab.state_path == path
    assert tab.title() == "x"
    assert tab.tooltip() == str(path)
    assert tab.stack.currentWidget() is tab.start_panel
    panel = tab.start_panel
    assert panel.name_input.text() == "x"
    assert not panel.name_input.isEnabled()
    assert not panel.save_button.isEnabled()
    assert panel.new_worktree_button.isEnabled()
    assert not path.exists()


def test_show_panel_when_unsaved_writes_nothing(qtbot, tab_states, worktree_service, tmp_path, warnings):
    tab = make_tab(qtbot, tab_states, worktree_service)
    tab.show_panel(Panel.START)
    assert tab.active_panel is Panel.START
    assert list(tmp_path.iterdir()) == []
    assert warnings == []


def test_show_panel_when_saved_writes_the_file(qtbot, tab_states, worktree_service, tmp_path):
    tab = make_tab(qtbot, tab_states, worktree_service)
    path = tmp_path / "x.json"
    tab.apply_saved(path, TabState("x"))
    tab.show_panel(Panel.START)
    assert read_json(path) == EXPECTED_FILE


def test_save_as_writes_and_switches_to_saved_mode(qtbot, tab_states, worktree_service, tmp_path):
    tab = make_tab(qtbot, tab_states, worktree_service)
    path = tmp_path / "x.json"
    assert tab.save_as(path, "x") is True
    assert read_json(path) == EXPECTED_FILE
    assert tab.state_path == path
    assert tab.title() == "x"


def test_save_as_failure_warns_and_stays_unsaved(qtbot, tab_states, worktree_service, tmp_path, warnings):
    tab = make_tab(qtbot, tab_states, worktree_service)
    path = tmp_path / "missing" / "x.json"
    assert tab.save_as(path, "x") is False
    assert len(warnings) == 1
    title, text = warnings[0]
    assert title == "Cannot save state file"
    assert str(path) in text
    assert "cannot write file" in text
    assert tab.state_path is None
    assert tab.title() == "New pipeline"
    panel = tab.start_panel
    assert panel.name_input.isEnabled()
    assert not panel.new_worktree_button.isEnabled()


def test_auto_save_failure_keeps_state_and_retries(qtbot, tab_states, worktree_service, tmp_path, warnings):
    tab = make_tab(qtbot, tab_states, worktree_service)
    folder = tmp_path / "d"
    folder.mkdir()
    path = folder / "x.json"
    assert tab.save_as(path, "x") is True
    a = tmp_path / "wt" / "a"
    tab.apply_saved(path, TabState("x", Panel.START, [a]))

    shutil.rmtree(folder)
    tab.show_panel(Panel.START)
    assert len(warnings) == 1
    title, text = warnings[0]
    assert title == "Cannot save state file"
    assert str(path) in text
    assert "cannot write file" in text
    assert tab.state_path == path
    assert tab.title() == "x"

    folder.mkdir()
    tab.show_panel(Panel.START)
    assert read_json(path) == {**EXPECTED_FILE, "worktrees": [str(a)]}
    assert len(warnings) == 1


def test_show_panel_keeps_loaded_worktrees(qtbot, tab_states, worktree_service, tmp_path):
    tab = make_tab(qtbot, tab_states, worktree_service)
    path = tmp_path / "x.json"
    a = tmp_path / "wt" / "a"
    b = tmp_path / "wt" / "b"
    tab.apply_saved(path, TabState("x", Panel.START, [a, b]))
    for _ in range(2):
        tab.show_panel(Panel.START)
        assert read_json(path)["worktrees"] == [str(a), str(b)]


def test_apply_saved_copies_worktrees(qtbot, tab_states, worktree_service, tmp_path):
    tab = make_tab(qtbot, tab_states, worktree_service)
    path = tmp_path / "x.json"
    a = tmp_path / "wt" / "a"
    state = TabState("x", Panel.START, [a])
    tab.apply_saved(path, state)
    state.worktrees.append(tmp_path / "wt" / "b")
    tab.show_panel(Panel.START)
    assert read_json(path)["worktrees"] == [str(a)]


def test_save_as_writes_empty_worktrees(qtbot, tab_states, worktree_service, tmp_path):
    tab = make_tab(qtbot, tab_states, worktree_service)
    path = tmp_path / "x.json"
    assert tab.save_as(path, "x") is True
    assert read_json(path) == EXPECTED_FILE


def worktree_texts(tab):
    worktrees = tab.start_panel.worktrees_list
    return [worktrees.item(i).text() for i in range(worktrees.count())]


def test_apply_saved_shows_worktrees_on_start_panel(qtbot, tab_states, worktree_service, tmp_path):
    tab = make_tab(qtbot, tab_states, worktree_service)
    a = tmp_path / "wt" / "a"
    b = tmp_path / "wt" / "b"
    tab.apply_saved(tmp_path / "x.json", TabState("x", Panel.START, [a, b]))
    assert worktree_texts(tab) == [str(a), str(b)]
    assert not tab.start_panel.worktrees_label.isHidden()


def test_apply_saved_without_worktrees_hides_list(qtbot, tab_states, worktree_service, tmp_path):
    tab = make_tab(qtbot, tab_states, worktree_service)
    path = tmp_path / "x.json"
    tab.apply_saved(path, TabState("x", Panel.START, [tmp_path / "wt" / "a"]))
    tab.apply_saved(path, TabState("x"))
    assert worktree_texts(tab) == []
    assert tab.start_panel.worktrees_list.isHidden()
    assert tab.start_panel.worktrees_label.isHidden()


def test_save_as_keeps_worktrees_hidden(qtbot, tab_states, worktree_service, tmp_path):
    tab = make_tab(qtbot, tab_states, worktree_service)
    assert tab.save_as(tmp_path / "x.json", "x") is True
    assert tab.start_panel.worktrees_list.isHidden()


# --- New worktree panel ---------------------------------------------------------


def click_new_worktree(qtbot, tab):
    qtbot.mouseClick(tab.start_panel.new_worktree_button, Qt.MouseButton.LeftButton)


def assert_fresh_panel(panel):
    groups = panel.groups()
    assert len(groups) == 1
    assert groups[0].source_input.text() == ""
    assert groups[0].parent_input.text() == ""
    assert groups[0].remove_button.isHidden()
    assert not panel.create_button.isEnabled()


def test_clicking_new_worktree_opens_fresh_panel(qtbot, tab_states, worktree_service, tmp_path):
    tab = make_tab(qtbot, tab_states, worktree_service)
    path = tmp_path / "x.json"
    tab.apply_saved(path, TabState("x"))
    click_new_worktree(qtbot, tab)
    assert tab.stack.currentWidget() is tab.new_worktree_panel
    assert tab.active_panel is Panel.NEW_WORKTREE
    assert_fresh_panel(tab.new_worktree_panel)
    assert read_json(path) == EXPECTED_FILE


def test_reopening_new_worktree_panel_is_fresh(qtbot, tab_states, worktree_service, tmp_path):
    tab = make_tab(qtbot, tab_states, worktree_service)
    tab.apply_saved(tmp_path / "x.json", TabState("x"))
    click_new_worktree(qtbot, tab)
    panel = tab.new_worktree_panel
    qtbot.mouseClick(panel.add_button, Qt.MouseButton.LeftButton)
    panel.groups()[0].source_input.setText("C:/src")
    assert len(panel.groups()) == 2
    tab.show_panel(Panel.START)
    click_new_worktree(qtbot, tab)
    assert tab.stack.currentWidget() is panel
    groups = panel.groups()
    assert len(groups) == 1
    assert groups[0].source_input.text() == ""
    assert groups[0].parent_input.text() == ""


def test_open_new_worktree_panel_resets_panel(qtbot, tab_states, worktree_service, tmp_path):
    tab = make_tab(qtbot, tab_states, worktree_service)
    tab.apply_saved(tmp_path / "x.json", TabState("x"))
    panel = tab.new_worktree_panel
    qtbot.mouseClick(panel.add_button, Qt.MouseButton.LeftButton)
    assert len(panel.groups()) == 2
    tab.open_new_worktree_panel()
    assert len(panel.groups()) == 1
    assert tab.stack.currentWidget() is panel


def test_new_worktree_panel_is_never_written_as_active(qtbot, tab_states, worktree_service, tmp_path):
    tab = make_tab(qtbot, tab_states, worktree_service)
    path = tmp_path / "x.json"
    a = tmp_path / "wt" / "a"
    tab.apply_saved(path, TabState("x", Panel.START, [a]))
    expected = {**EXPECTED_FILE, "worktrees": [str(a)]}
    tab.show_panel(Panel.NEW_WORKTREE)
    assert read_json(path) == expected
    tab.show_panel(Panel.START)
    assert read_json(path) == expected


def test_open_panel_on_unsaved_tab_writes_nothing(qtbot, tab_states, worktree_service, tmp_path, warnings):
    tab = make_tab(qtbot, tab_states, worktree_service)
    tab.open_new_worktree_panel()
    assert tab.stack.currentWidget() is tab.new_worktree_panel
    assert list(tmp_path.iterdir()) == []
    assert warnings == []


def test_save_as_while_panel_shown_writes_start(qtbot, tab_states, worktree_service, tmp_path):
    tab = make_tab(qtbot, tab_states, worktree_service)
    tab.open_new_worktree_panel()
    path = tmp_path / "x.json"
    assert tab.save_as(path, "x") is True
    assert read_json(path) == EXPECTED_FILE
    assert tab.stack.currentWidget() is tab.start_panel


def test_open_panel_write_failure_warns_and_shows_panel(qtbot, tab_states, worktree_service, tmp_path, warnings):
    tab = make_tab(qtbot, tab_states, worktree_service)
    folder = tmp_path / "d"
    folder.mkdir()
    path = folder / "x.json"
    assert tab.save_as(path, "x") is True
    shutil.rmtree(folder)
    click_new_worktree(qtbot, tab)
    assert len(warnings) == 1
    assert warnings[0][0] == "Cannot save state file"
    assert tab.stack.currentWidget() is tab.new_worktree_panel
    assert tab.state_path == path

    folder.mkdir()
    tab.show_panel(Panel.START)
    assert read_json(path) == EXPECTED_FILE


def test_open_new_worktree_panel_prefills_folder_name(qtbot, tab_states, worktree_service, tmp_path):
    tab = make_tab(qtbot, tab_states, worktree_service)
    tab.apply_saved(tmp_path / "x.json", TabState("feat-x"))
    tab.open_new_worktree_panel()
    panel = tab.new_worktree_panel
    qtbot.mouseClick(panel.add_button, Qt.MouseButton.LeftButton)
    assert [group.folder_name_input.text() for group in panel.groups()] == [
        "worktree-feat-x",
        "worktree-feat-x",
    ]


def test_remove_worktree_updates_list_and_state_file(qtbot, tab_states, worktree_service, tmp_path):
    tab = make_tab(qtbot, tab_states, worktree_service)
    path = tmp_path / "x.json"
    a = tmp_path / "wt" / "a"
    b = tmp_path / "wt" / "b"
    a.mkdir(parents=True)
    tab.apply_saved(path, TabState("x", Panel.START, [a, b]))
    tab.start_panel.worktrees_list.setCurrentRow(0)
    qtbot.mouseClick(tab.start_panel.remove_worktree_button, Qt.MouseButton.LeftButton)
    assert worktree_texts(tab) == [str(b)]
    assert read_json(path) == {**EXPECTED_FILE, "worktrees": [str(b)]}
    assert a.is_dir()  # only the list entry is removed, never the folder


def test_remove_last_worktree_hides_list(qtbot, tab_states, worktree_service, tmp_path):
    tab = make_tab(qtbot, tab_states, worktree_service)
    path = tmp_path / "x.json"
    a = tmp_path / "wt" / "a"
    tab.apply_saved(path, TabState("x", Panel.START, [a]))
    tab.remove_worktree(a)
    assert tab.start_panel.worktrees_list.isHidden()
    assert read_json(path) == EXPECTED_FILE


def test_remove_unknown_worktree_writes_nothing(qtbot, tab_states, worktree_service, tmp_path):
    tab = make_tab(qtbot, tab_states, worktree_service)
    path = tmp_path / "x.json"
    a = tmp_path / "wt" / "a"
    tab.apply_saved(path, TabState("x", Panel.START, [a]))
    tab.remove_worktree(tmp_path / "wt" / "other")
    assert not path.exists()
    assert worktree_texts(tab) == [str(a)]


def test_remove_worktree_write_failure_warns_and_keeps_removal(qtbot, tab_states, worktree_service, tmp_path, warnings):
    tab = make_tab(qtbot, tab_states, worktree_service)
    path = tmp_path / "missing-dir" / "x.json"
    a = tmp_path / "wt" / "a"
    b = tmp_path / "wt" / "b"
    tab.apply_saved(path, TabState("x", Panel.START, [a, b]))
    tab.remove_worktree(a)
    assert len(warnings) == 1
    assert worktree_texts(tab) == [str(b)]
    path.parent.mkdir()
    tab.show_panel(Panel.START)
    assert read_json(path)["worktrees"] == [str(b)]


def answer_folder(monkeypatch, answer: str) -> list:
    """Fake QFileDialog.getExistingDirectory: records calls, returns `answer` ("" cancels)."""
    calls = []

    def fake(*args, **kwargs):
        calls.append(args)
        return answer

    monkeypatch.setattr(QFileDialog, "getExistingDirectory", fake)
    return calls


def test_start_pipeline_opens_devpipe_create_panel(qtbot, tab_states, worktree_service, tmp_path):
    tab = make_tab(qtbot, tab_states, worktree_service)
    path = tmp_path / "x.json"
    a = tmp_path / "wt" / "a"
    tab.apply_saved(path, TabState("x", Panel.START, [a]))
    qtbot.mouseClick(tab.start_panel.start_pipeline_button, Qt.MouseButton.LeftButton)
    assert tab.stack.currentWidget() is tab.devpipe_create_panel
    assert tab.active_panel is Panel.DEVPIPE_CREATE
    assert read_json(path) == {**EXPECTED_FILE, "active_panel": "devpipe-create", "worktrees": [str(a)]}


def test_start_pipeline_without_worktrees_saves_chosen_folder(
    qtbot, tab_states, worktree_service, tmp_path, monkeypatch
):
    tab = make_tab(qtbot, tab_states, worktree_service)
    path = tmp_path / "x.json"
    folder = tmp_path / "project"
    tab.apply_saved(path, TabState("x"))
    answer_folder(monkeypatch, str(folder))
    qtbot.mouseClick(tab.start_panel.start_pipeline_button, Qt.MouseButton.LeftButton)
    assert tab.active_panel is Panel.DEVPIPE_CREATE
    assert worktree_texts(tab) == [str(folder)]
    assert read_json(path) == {**EXPECTED_FILE, "active_panel": "devpipe-create", "worktrees": [str(folder)]}


def test_start_pipeline_folder_cancel_stays_on_start(
    qtbot, tab_states, worktree_service, tmp_path, monkeypatch
):
    tab = make_tab(qtbot, tab_states, worktree_service)
    path = tmp_path / "x.json"
    tab.apply_saved(path, TabState("x"))
    answer_folder(monkeypatch, "")
    qtbot.mouseClick(tab.start_panel.start_pipeline_button, Qt.MouseButton.LeftButton)
    assert tab.stack.currentWidget() is tab.start_panel
    assert tab.active_panel is Panel.START
    assert worktree_texts(tab) == []
    assert not path.exists()  # apply_saved does not write; nothing else did


def test_apply_saved_shows_devpipe_create_panel(qtbot, tab_states, worktree_service, tmp_path):
    tab = make_tab(qtbot, tab_states, worktree_service)
    tab.apply_saved(tmp_path / "x.json", TabState("x", Panel.DEVPIPE_CREATE))
    assert tab.stack.currentWidget() is tab.devpipe_create_panel
    assert tab.active_panel is Panel.DEVPIPE_CREATE


def test_active_panel_change_keeps_worktrees(qtbot, tab_states, worktree_service, tmp_path):
    tab = make_tab(qtbot, tab_states, worktree_service)
    path = tmp_path / "x.json"
    a = tmp_path / "wt" / "a"
    b = tmp_path / "wt" / "b"
    tab.apply_saved(path, TabState("x", Panel.START, [b, a]))
    expected = {**EXPECTED_FILE, "worktrees": [str(b), str(a)]}
    qtbot.mouseClick(tab.start_panel.start_pipeline_button, Qt.MouseButton.LeftButton)
    assert read_json(path) == {**expected, "active_panel": "devpipe-create"}
    tab.show_panel(Panel.START)
    assert read_json(path) == expected


def test_saved_devpipe_create_panel_reloads_with_worktrees(qtbot, tab_states, worktree_service, tmp_path):
    tab = make_tab(qtbot, tab_states, worktree_service)
    path = tmp_path / "x.json"
    a = tmp_path / "wt" / "a"
    tab.apply_saved(path, TabState("x", Panel.START, [a]))
    tab.show_panel(Panel.DEVPIPE_CREATE)
    reloaded = make_tab(qtbot, tab_states, worktree_service)
    reloaded.apply_saved(path, tab_states.load(path))
    assert reloaded.active_panel is Panel.DEVPIPE_CREATE
    assert reloaded.stack.currentWidget() is reloaded.devpipe_create_panel
    assert reloaded.start_panel.worktrees_list.count() == 1
    assert reloaded.start_panel.worktrees_list.item(0).text() == str(a)

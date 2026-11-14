import json
import shutil

import pytest
from PySide6.QtWidgets import QMessageBox, QStackedWidget

from devpipe.models.tab_state import Panel, TabState
from devpipe.views.pipeline_tab import PipelineTab
from devpipe.views.start_panel import StartPanel

EXPECTED_FILE = {"version": 2, "feature_name": "x", "active_panel": "start", "worktrees": []}


def make_tab(qtbot, tab_states):
    tab = PipelineTab(tab_states)
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


def test_tab_shows_start_panel_in_a_stack(qtbot, tab_states):
    tab = make_tab(qtbot, tab_states)
    assert isinstance(tab.stack, QStackedWidget)
    assert tab.stack.count() == 1
    assert tab.stack.widget(0) is tab.start_panel
    assert tab.stack.currentWidget() is tab.start_panel
    assert isinstance(tab.start_panel, StartPanel)


def test_new_tab_identity(qtbot, tab_states):
    tab = make_tab(qtbot, tab_states)
    assert tab.title() == "New pipeline"
    assert tab.tooltip() == ""


def test_new_tab_start_panel_is_unsaved(qtbot, tab_states):
    tab = make_tab(qtbot, tab_states)
    panel = tab.start_panel
    assert not panel.save_button.isEnabled()
    assert not panel.open_button.isEnabled()
    assert not panel.create_button.isEnabled()


def test_new_tab_is_unsaved(qtbot, tab_states):
    tab = make_tab(qtbot, tab_states)
    assert tab.state_path is None
    assert tab.active_panel is Panel.START
    assert tab.title() == "New pipeline"
    assert tab.tooltip() == ""


def test_apply_saved_switches_to_saved_mode_without_writing(qtbot, tab_states, tmp_path):
    tab = make_tab(qtbot, tab_states)
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
    assert panel.open_button.isEnabled()
    assert panel.create_button.isEnabled()
    assert not path.exists()


def test_show_panel_when_unsaved_writes_nothing(qtbot, tab_states, tmp_path, warnings):
    tab = make_tab(qtbot, tab_states)
    tab.show_panel(Panel.START)
    assert tab.active_panel is Panel.START
    assert list(tmp_path.iterdir()) == []
    assert warnings == []


def test_show_panel_when_saved_writes_the_file(qtbot, tab_states, tmp_path):
    tab = make_tab(qtbot, tab_states)
    path = tmp_path / "x.json"
    tab.apply_saved(path, TabState("x"))
    tab.show_panel(Panel.START)
    assert read_json(path) == EXPECTED_FILE


def test_save_as_writes_and_switches_to_saved_mode(qtbot, tab_states, tmp_path):
    tab = make_tab(qtbot, tab_states)
    path = tmp_path / "x.json"
    assert tab.save_as(path, "x") is True
    assert read_json(path) == EXPECTED_FILE
    assert tab.state_path == path
    assert tab.title() == "x"


def test_save_as_failure_warns_and_stays_unsaved(qtbot, tab_states, tmp_path, warnings):
    tab = make_tab(qtbot, tab_states)
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
    assert not panel.open_button.isEnabled()
    assert not panel.create_button.isEnabled()


def test_auto_save_failure_keeps_state_and_retries(qtbot, tab_states, tmp_path, warnings):
    tab = make_tab(qtbot, tab_states)
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


def test_show_panel_keeps_loaded_worktrees(qtbot, tab_states, tmp_path):
    tab = make_tab(qtbot, tab_states)
    path = tmp_path / "x.json"
    a = tmp_path / "wt" / "a"
    b = tmp_path / "wt" / "b"
    tab.apply_saved(path, TabState("x", Panel.START, [a, b]))
    for _ in range(2):
        tab.show_panel(Panel.START)
        assert read_json(path)["worktrees"] == [str(a), str(b)]


def test_apply_saved_copies_worktrees(qtbot, tab_states, tmp_path):
    tab = make_tab(qtbot, tab_states)
    path = tmp_path / "x.json"
    a = tmp_path / "wt" / "a"
    state = TabState("x", Panel.START, [a])
    tab.apply_saved(path, state)
    state.worktrees.append(tmp_path / "wt" / "b")
    tab.show_panel(Panel.START)
    assert read_json(path)["worktrees"] == [str(a)]


def test_save_as_writes_empty_worktrees(qtbot, tab_states, tmp_path):
    tab = make_tab(qtbot, tab_states)
    path = tmp_path / "x.json"
    assert tab.save_as(path, "x") is True
    assert read_json(path) == EXPECTED_FILE


def worktree_texts(tab):
    worktrees = tab.start_panel.worktrees_list
    return [worktrees.item(i).text() for i in range(worktrees.count())]


def test_apply_saved_shows_worktrees_on_start_panel(qtbot, tab_states, tmp_path):
    tab = make_tab(qtbot, tab_states)
    a = tmp_path / "wt" / "a"
    b = tmp_path / "wt" / "b"
    tab.apply_saved(tmp_path / "x.json", TabState("x", Panel.START, [a, b]))
    assert worktree_texts(tab) == [str(a), str(b)]
    assert not tab.start_panel.worktrees_label.isHidden()


def test_apply_saved_without_worktrees_hides_list(qtbot, tab_states, tmp_path):
    tab = make_tab(qtbot, tab_states)
    path = tmp_path / "x.json"
    tab.apply_saved(path, TabState("x", Panel.START, [tmp_path / "wt" / "a"]))
    tab.apply_saved(path, TabState("x"))
    assert worktree_texts(tab) == []
    assert tab.start_panel.worktrees_list.isHidden()
    assert tab.start_panel.worktrees_label.isHidden()


def test_save_as_keeps_worktrees_hidden(qtbot, tab_states, tmp_path):
    tab = make_tab(qtbot, tab_states)
    assert tab.save_as(tmp_path / "x.json", "x") is True
    assert tab.start_panel.worktrees_list.isHidden()

"""File > Open flow end to end through MainWindow."""

import json
import sys
from pathlib import Path

import pytest
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QFileDialog, QMessageBox

from devpipe.models.tab_state import Panel, TabState
from devpipe.persistence.config_repository import ConfigRepository
from devpipe.views.main_window import STATE_FILE_FILTER
from devpipe.views.pipeline_tab import PipelineTab


def write_state(path: Path, feature_name: str) -> Path:
    state = {"version": 1, "feature_name": feature_name, "active_panel": "start"}
    path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    return path


def last_state_folder(tmp_path: Path) -> Path | None:
    return ConfigRepository(tmp_path / "config.json").load().last_state_folder


class OpenDialog:
    """Fake QFileDialog.getOpenFileName: records calls, returns `answer` (None cancels)."""

    def __init__(self) -> None:
        self.calls = []
        self.answer: str | None = None

    def __call__(self, parent, caption, dir, filter, *args):
        self.calls.append((parent, caption, dir, filter))
        if self.answer is None:
            return "", ""
        return self.answer, STATE_FILE_FILTER


@pytest.fixture
def open_dialog(monkeypatch):
    fake = OpenDialog()
    monkeypatch.setattr(QFileDialog, "getOpenFileName", fake)
    return fake


@pytest.fixture
def warnings(monkeypatch):
    """(title, text) of every QMessageBox.warning call."""
    shown = []

    def fake(parent, title, text, *args):
        shown.append((title, text))
        return QMessageBox.StandardButton.Ok

    monkeypatch.setattr(QMessageBox, "warning", fake)
    return shown


def test_file_menu_holds_open_action(make_window):
    window = make_window()
    file_action = window.menuBar().actions()[0]
    assert file_action.text() == "&File"
    assert window.open_action in file_action.menu().actions()
    assert window.open_action.text() == "&Open..."


def test_open_action_shortcut_is_ctrl_o(make_window):
    window = make_window()
    assert window.open_action.shortcut() == QKeySequence("Ctrl+O")


def test_open_dialog_uses_home_and_json_filter(make_window, open_dialog, warnings):
    window = make_window()
    window.open_action.trigger()
    assert len(open_dialog.calls) == 1
    parent, caption, start, file_filter = open_dialog.calls[0]
    assert parent is window
    assert caption == "Open pipeline state"
    assert Path(start) == Path.home()
    assert file_filter == "JSON files (*.json)"


def test_cancel_changes_nothing(tmp_path, make_window, open_dialog, warnings):
    window = make_window()
    before = window.tabs.count()
    current = window.tabs.currentIndex()
    window.open_action.trigger()
    assert window.tabs.count() == before
    assert window.tabs.currentIndex() == current
    assert warnings == []
    assert last_state_folder(tmp_path) is None


@pytest.fixture
def valid_file(tmp_path) -> Path:
    (tmp_path / "states").mkdir()
    return write_state(tmp_path / "states" / "a.json", "a")


def test_open_valid_file_adds_selected_saved_tab(make_window, open_dialog, warnings, valid_file):
    text_before = valid_file.read_text(encoding="utf-8")
    window = make_window()
    before = window.tabs.count()
    open_dialog.answer = str(valid_file)
    window.open_action.trigger()
    assert window.tabs.count() == before + 1
    tab = window.tabs.currentWidget()
    assert isinstance(tab, PipelineTab)
    assert tab.state_path == valid_file
    index = window.tabs.currentIndex()
    assert window.tabs.tabText(index) == "a"
    assert window.tabs.tabToolTip(index) == str(valid_file)
    assert tab.active_panel is Panel.START
    assert tab.stack.currentWidget() is tab.start_panel
    panel = tab.start_panel
    assert panel.name_input.text() == "a"
    assert not panel.name_input.isEnabled()
    assert not panel.save_button.isEnabled()
    assert panel.open_button.isEnabled()
    assert panel.create_button.isEnabled()
    assert warnings == []
    assert valid_file.read_text(encoding="utf-8") == text_before


def test_open_valid_file_remembers_its_folder(
    tmp_path, make_window, open_dialog, warnings, valid_file
):
    window = make_window()
    open_dialog.answer = str(valid_file)
    window.open_action.trigger()
    assert last_state_folder(tmp_path) == tmp_path / "states"


def test_next_open_dialog_starts_in_last_used_folder(
    tmp_path, make_window, open_dialog, warnings, valid_file
):
    window = make_window()
    open_dialog.answer = str(valid_file)
    window.open_action.trigger()
    open_dialog.answer = None
    window.open_action.trigger()
    assert len(open_dialog.calls) == 2
    assert Path(open_dialog.calls[1][2]) == tmp_path / "states"


def open_saved_then_new(window, tmp_path) -> PipelineTab:
    saved = window.add_saved_tab(tmp_path / "a.json", TabState("a"))
    window.add_new_tab()
    assert window.tabs.currentWidget() is not saved
    return saved


@pytest.mark.parametrize("parts", [("a.json",), ("x", "..", "a.json")])
def test_open_already_open_file_selects_its_tab(
    tmp_path, make_window, open_dialog, warnings, parts
):
    window = make_window()
    saved = open_saved_then_new(window, tmp_path)
    before = window.tabs.count()
    open_dialog.answer = str(tmp_path.joinpath(*parts))
    window.open_action.trigger()
    assert window.tabs.currentWidget() is saved
    assert window.tabs.count() == before
    assert warnings == []
    assert last_state_folder(tmp_path) == tmp_path


@pytest.mark.skipif(sys.platform != "win32", reason="case-insensitive paths on Windows only")
def test_open_already_open_file_ignores_case_on_windows(
    tmp_path, make_window, open_dialog, warnings
):
    window = make_window()
    saved = open_saved_then_new(window, tmp_path)
    before = window.tabs.count()
    open_dialog.answer = str(tmp_path / "A.JSON")
    window.open_action.trigger()
    assert window.tabs.currentWidget() is saved
    assert window.tabs.count() == before
    assert last_state_folder(tmp_path) == tmp_path


@pytest.mark.parametrize(
    ("content", "reason"),
    [
        (None, "file not found"),
        ("{not json", "not valid JSON"),
        ({"version": 3, "feature_name": "a", "active_panel": "start"}, "unsupported version"),
        ({"version": 1, "feature_name": "a", "active_panel": "process"}, "unknown active_panel"),
        (
            {"version": 2, "feature_name": "a", "active_panel": "start", "worktrees": "x"},
            "invalid worktrees",
        ),
        (
            {"version": 2, "feature_name": "a", "active_panel": "new-worktree", "worktrees": []},
            "unknown active_panel",
        ),
    ],
)
def test_open_invalid_file_warns_and_adds_no_tab(
    tmp_path, make_window, open_dialog, warnings, content, reason
):
    path = tmp_path / "bad.json"
    if isinstance(content, str):
        path.write_text(content, encoding="utf-8")
    elif content is not None:
        path.write_text(json.dumps(content), encoding="utf-8")
    window = make_window()
    before = window.tabs.count()
    current = window.tabs.currentIndex()
    open_dialog.answer = str(path)
    window.open_action.trigger()
    assert len(warnings) == 1
    title, text = warnings[0]
    assert title == "Cannot open state file"
    assert str(path) in text
    assert reason in text
    assert window.tabs.count() == before
    assert window.tabs.currentIndex() == current
    assert last_state_folder(tmp_path) is None


def test_open_v1_file_loads_and_next_write_is_v2(tmp_path, make_window, open_dialog, warnings):
    path = write_state(tmp_path / "a.json", "a")
    bytes_before = path.read_bytes()
    window = make_window()
    before = window.tabs.count()
    open_dialog.answer = str(path)
    window.open_action.trigger()
    assert window.tabs.count() == before + 1
    tab = window.tabs.currentWidget()
    assert isinstance(tab, PipelineTab)
    assert tab.state_path == path
    assert path.read_bytes() == bytes_before
    tab.show_panel(Panel.START)
    assert json.loads(path.read_text(encoding="utf-8")) == {
        "version": 2,
        "feature_name": "a",
        "active_panel": "start",
        "worktrees": [],
    }
    assert warnings == []


def test_open_two_files_adds_two_tabs(tmp_path, make_window, open_dialog, warnings):
    a = write_state(tmp_path / "a.json", "a")
    b = write_state(tmp_path / "b.json", "b")
    window = make_window()
    before = window.tabs.count()
    for path in (a, b):
        open_dialog.answer = str(path)
        window.open_action.trigger()
    assert window.tabs.count() == before + 2
    assert window.tabs.tabText(before) == "a"
    assert window.tabs.tabText(before + 1) == "b"
    assert window.tabs.currentWidget() is window.tabs.widget(before + 1)


def test_open_two_files_with_same_feature_name_adds_two_tabs(
    tmp_path, make_window, open_dialog, warnings
):
    paths = []
    for folder in ("x", "y"):
        (tmp_path / folder).mkdir()
        paths.append(write_state(tmp_path / folder / "a.json", "a"))
    window = make_window()
    before = window.tabs.count()
    for path in paths:
        open_dialog.answer = str(path)
        window.open_action.trigger()
    assert window.tabs.count() == before + 2
    assert window.tabs.tabText(before) == "a"
    assert window.tabs.tabText(before + 1) == "a"
    assert window.tabs.tabToolTip(before) == str(tmp_path / "x" / "a.json")
    assert window.tabs.tabToolTip(before + 1) == str(tmp_path / "y" / "a.json")
    assert window.tabs.currentWidget() is window.tabs.widget(before + 1)
    assert warnings == []

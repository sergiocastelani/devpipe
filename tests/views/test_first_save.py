"""Save dialog flow end to end through MainWindow."""

import json
import sys
from pathlib import Path

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFileDialog, QMessageBox

from devpipe.models.tab_state import Panel, TabState
from devpipe.views.main_window import STATE_FILE_FILTER


@pytest.fixture
def warnings(monkeypatch):
    """(title, text) of every QMessageBox.warning call."""
    shown = []

    def fake(parent, title, text, *args):
        shown.append((title, text))
        return QMessageBox.StandardButton.Ok

    monkeypatch.setattr(QMessageBox, "warning", fake)
    return shown


class SaveDialog:
    """Fake QFileDialog.getSaveFileName: records calls, returns `answer` (None cancels)."""

    def __init__(self, monkeypatch) -> None:
        self.calls = []
        self.answer: Path | None = None
        monkeypatch.setattr(QFileDialog, "getSaveFileName", self)

    def __call__(self, parent, caption, dir, filter):
        self.calls.append((parent, caption, dir, filter))
        if self.answer is None:
            return "", ""
        return str(self.answer), STATE_FILE_FILTER


@pytest.fixture
def dialog(monkeypatch):
    return SaveDialog(monkeypatch)


def request_save(qtbot, tab, name):
    tab.start_panel.name_input.setText(name)
    qtbot.mouseClick(tab.start_panel.save_button, Qt.MouseButton.LeftButton)


def stored_folder(tmp_path):
    path = tmp_path / "config.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8")).get("last_state_folder")


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def assert_unsaved(window, tab, name, slug):
    panel = tab.start_panel
    assert tab.state_path is None
    assert window.tabs.tabText(window.tabs.indexOf(tab)) == "New pipeline"
    assert panel.name_input.isEnabled()
    assert panel.save_button.isEnabled()
    assert not panel.open_button.isEnabled()
    assert not panel.create_button.isEnabled()
    assert panel.name_input.text() == name
    assert panel.slug_label.text() == slug


def test_save_opens_dialog_with_slug_filter_and_start_folder(qtbot, make_window, dialog):
    window = make_window()
    request_save(qtbot, window.tabs.widget(0), "New Feature")
    assert len(dialog.calls) == 1
    parent, caption, start, file_filter = dialog.calls[0]
    assert parent is window
    assert caption == "Save pipeline state"
    assert Path(start) == Path.home() / "new-feature.json"
    assert file_filter == "JSON files (*.json)"


def test_cancel_changes_nothing(qtbot, make_window, dialog, warnings, tmp_path):
    window = make_window()
    tab = window.tabs.widget(0)
    request_save(qtbot, tab, "New Feature")
    assert len(dialog.calls) == 1
    assert list(tmp_path.rglob("*.json")) == []
    assert_unsaved(window, tab, "New Feature", "new-feature")
    assert stored_folder(tmp_path) is None
    assert warnings == []


def test_confirmed_save_writes_file_and_marks_tab_saved(
    qtbot, make_window, dialog, warnings, tmp_path
):
    window = make_window()
    tab = window.tabs.widget(0)
    folder = tmp_path / "states"
    folder.mkdir()
    path = folder / "new-feature.json"
    dialog.answer = path
    request_save(qtbot, tab, "New Feature")

    assert read_json(path) == {
        "version": 2,
        "feature_name": "new-feature",
        "active_panel": "start",
        "worktrees": [],
    }
    panel = tab.start_panel
    assert panel.name_input.text() == "new-feature"
    assert not panel.name_input.isEnabled()
    assert not panel.save_button.isEnabled()
    assert panel.open_button.isEnabled()
    assert panel.create_button.isEnabled()
    index = window.tabs.indexOf(tab)
    assert window.tabs.tabText(index) == "new-feature"
    assert window.tabs.tabToolTip(index) == str(path)
    assert stored_folder(tmp_path) == str(folder)
    assert warnings == []


def test_next_dialog_starts_in_last_used_folder(qtbot, make_window, dialog, tmp_path):
    window = make_window()
    folder = tmp_path / "states"
    folder.mkdir()
    dialog.answer = folder / "new-feature.json"
    request_save(qtbot, window.tabs.widget(0), "New Feature")

    dialog.answer = None
    request_save(qtbot, window.add_new_tab(), "Other")
    assert len(dialog.calls) == 2
    assert Path(dialog.calls[1][2]) == folder / "other.json"


def test_name_without_extension_gets_json(qtbot, make_window, dialog, tmp_path):
    window = make_window()
    tab = window.tabs.widget(0)
    dialog.answer = tmp_path / "new-feature"
    request_save(qtbot, tab, "New Feature")
    assert (tmp_path / "new-feature.json").exists()
    assert not (tmp_path / "new-feature").exists()
    assert window.tabs.tabToolTip(window.tabs.indexOf(tab)).endswith("new-feature.json")


def test_save_to_path_open_in_other_tab_warns(qtbot, make_window, dialog, warnings, tmp_path):
    window = make_window()
    window.add_saved_tab(tmp_path / "a.json", TabState("a"))
    tab = window.add_new_tab()
    dialog.answer = tmp_path / "a.json"
    request_save(qtbot, tab, "b")

    assert len(warnings) == 1
    title, text = warnings[0]
    assert title == "State file already open"
    assert str(tmp_path / "a.json") in text
    assert_unsaved(window, tab, "b", "b")
    assert not (tmp_path / "a.json").exists()
    assert stored_folder(tmp_path) is None


@pytest.mark.skipif(sys.platform != "win32", reason="case-insensitive paths only on Windows")
def test_duplicate_check_ignores_case_on_windows(qtbot, make_window, dialog, warnings, tmp_path):
    window = make_window()
    window.add_saved_tab(tmp_path / "a.json", TabState("a"))
    tab = window.add_new_tab()
    dialog.answer = tmp_path / "A.JSON"
    request_save(qtbot, tab, "b")

    assert len(warnings) == 1
    title, text = warnings[0]
    assert title == "State file already open"
    assert str(tmp_path / "A.JSON") in text
    assert_unsaved(window, tab, "b", "b")
    assert not (tmp_path / "a.json").exists()
    assert stored_folder(tmp_path) is None


def test_write_failure_warns_and_tab_stays_unsaved(
    qtbot, make_window, dialog, warnings, tmp_path
):
    window = make_window()
    tab = window.tabs.widget(0)
    path = tmp_path / "missing" / "x.json"
    dialog.answer = path
    request_save(qtbot, tab, "x")

    assert len(warnings) == 1
    title, text = warnings[0]
    assert title == "Cannot save state file"
    assert str(path) in text
    assert "cannot write file" in text
    assert_unsaved(window, tab, "x", "x")
    assert stored_folder(tmp_path) is None


def test_changes_after_first_save_auto_save_without_dialog(
    qtbot, make_window, dialog, monkeypatch, tmp_path
):
    window = make_window()
    tab = window.tabs.widget(0)
    path = tmp_path / "x.json"
    dialog.answer = path
    request_save(qtbot, tab, "x")
    assert tab.state_path == path

    def fail(*args, **kwargs):
        pytest.fail("a dialog was shown")

    monkeypatch.setattr(QFileDialog, "getSaveFileName", fail)
    path.unlink()
    tab.show_panel(Panel.START)
    assert read_json(path) == {
        "version": 2,
        "feature_name": "x",
        "active_panel": "start",
        "worktrees": [],
    }

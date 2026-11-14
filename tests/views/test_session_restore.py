"""Session sync (config.json open tabs) and startup restore through MainWindow."""

import json
from pathlib import Path

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFileDialog, QMessageBox

from devpipe.models.tab_state import Panel, TabState
from devpipe.persistence.config_repository import ConfigRepository
from devpipe.services.session_service import SessionService
from devpipe.views.main_window import STATE_FILE_FILTER
from devpipe.views.pipeline_tab import NEW_TAB_TITLE


def write_state(tab_states, path: Path, name: str) -> Path:
    tab_states.save(path, TabState(name))
    return path


def session_of(tmp_path) -> tuple[list[Path], Path | None]:
    config = ConfigRepository(tmp_path / "config.json").load()
    return config.open_state_files, config.active_state_file


def remember_session(tmp_path, files, active) -> None:
    SessionService(ConfigRepository(tmp_path / "config.json")).remember_session(files, active)


@pytest.fixture
def no_dialogs(monkeypatch):
    """Make every message box and file dialog fail the test."""

    def fail(*args, **kwargs):
        pytest.fail("unexpected dialog")

    for name in ("warning", "critical", "information", "question"):
        monkeypatch.setattr(QMessageBox, name, fail)
    for name in ("getOpenFileName", "getSaveFileName"):
        monkeypatch.setattr(QFileDialog, name, fail)


def record_session_calls(monkeypatch) -> list:
    """Wrap SessionService.remember_session; return the list of (files, active) it receives.

    The original still runs.
    """
    calls = []
    original = SessionService.remember_session

    def recording(self, files, active):
        calls.append((list(files), active))
        original(self, files, active)

    monkeypatch.setattr(SessionService, "remember_session", recording)
    return calls


def tab_texts(window) -> list[str]:
    return [window.tabs.tabText(index) for index in range(window.tabs.count())]


def state_paths(window) -> list[Path | None]:
    return [window.tabs.widget(index).state_path for index in range(window.tabs.count())]


@pytest.fixture
def files(tmp_path, tab_states):
    """Two valid state files, a.json and b.json."""
    return (
        write_state(tab_states, tmp_path / "a.json", "a"),
        write_state(tab_states, tmp_path / "b.json", "b"),
    )


# --- restore -----------------------------------------------------------------


def test_restart_restores_saved_tabs_in_order_with_active_selected(make_window, files):
    a, b = files
    window = make_window()
    window.add_saved_tab(a, TabState("a"))
    tab_b = window.add_saved_tab(b, TabState("b"))
    window.add_new_tab()
    window.tabs.setCurrentWidget(tab_b)
    window.close()

    restarted = make_window()
    assert restarted.tabs.count() == 2
    assert tab_texts(restarted) == ["a", "b"]
    assert state_paths(restarted) == [a, b]
    assert restarted.tabs.currentWidget() is restarted.tabs.widget(restarted.find_tab(b))


def test_restored_tab_shows_its_active_panel(make_window, files, tmp_path):
    a, _ = files
    remember_session(tmp_path, [a], a)
    window = make_window()
    tab = window.tabs.widget(0)
    assert window.tabs.count() == 1
    assert tab.active_panel is Panel.START
    assert tab.stack.currentWidget() is tab.start_panel
    assert tab.start_panel.name_input.text() == "a"
    assert not tab.start_panel.name_input.isEnabled()
    assert tab.start_panel.open_button.isEnabled()
    assert tab.start_panel.create_button.isEnabled()
    assert window.tabs.tabToolTip(0) == str(a)


def test_unsaved_active_tab_selects_last_active_saved_tab(make_window, files):
    a, b = files
    window = make_window()
    tab_a = window.add_saved_tab(a, TabState("a"))
    window.add_saved_tab(b, TabState("b"))
    window.tabs.setCurrentWidget(tab_a)
    window.add_new_tab()
    window.close()

    restarted = make_window()
    assert restarted.tabs.currentWidget().state_path == a


def test_no_active_file_selects_first_restored_tab(make_window, files, tmp_path):
    a, b = files
    remember_session(tmp_path, [a, b], None)
    window = make_window()
    assert window.tabs.currentIndex() == 0
    assert window.tabs.currentWidget().state_path == a


def test_invalid_active_file_selects_first_restored_tab(make_window, files, tmp_path):
    a, _ = files
    bad = tmp_path / "bad.json"
    remember_session(tmp_path, [a, bad], bad)
    window = make_window()
    assert state_paths(window) == [a]
    assert window.tabs.currentIndex() == 0


@pytest.mark.parametrize("content", [None, "{not json", '{"version": 2}'])
def test_invalid_listed_file_is_skipped_silently_and_dropped(
    make_window, files, tmp_path, no_dialogs, content
):
    a, b = files
    bad = tmp_path / "bad.json"
    if content is not None:
        bad.write_text(content, encoding="utf-8")
    remember_session(tmp_path, [a, bad, b], a)

    window = make_window()
    assert tab_texts(window) == ["a", "b"]
    assert session_of(tmp_path) == ([a, b], a)
    if content is None:
        assert not bad.exists()
    else:
        assert bad.read_text(encoding="utf-8") == content


def test_nothing_restorable_opens_one_unsaved_tab(make_window, tmp_path, no_dialogs):
    missing1, missing2 = tmp_path / "m1.json", tmp_path / "m2.json"
    remember_session(tmp_path, [missing1, missing2], missing1)
    window = make_window()
    assert tab_texts(window) == [NEW_TAB_TITLE]
    assert window.tabs.widget(0).state_path is None
    assert session_of(tmp_path) == ([], None)


def test_empty_session_opens_one_unsaved_tab(make_window, tmp_path):
    window = make_window()
    assert window.tabs.count() == 1
    assert window.tabs.widget(0).state_path is None
    assert not (tmp_path / "config.json").exists()
    assert session_of(tmp_path) == ([], None)


def test_duplicate_entries_restore_one_tab(make_window, files, tmp_path):
    a, _ = files
    remember_session(tmp_path, [a, tmp_path / "x" / ".." / "a.json"], a)
    window = make_window()
    assert window.tabs.count() == 1
    assert session_of(tmp_path)[0] == [a]


def test_restore_writes_session_once(make_window, files, tmp_path, monkeypatch):
    a, b = files
    remember_session(tmp_path, [a, tmp_path / "bad.json", b], b)
    calls = record_session_calls(monkeypatch)
    make_window()
    assert calls == [([a, b], b)]


def test_unchanged_session_is_not_rewritten(make_window, files, tmp_path, monkeypatch):
    a, b = files
    remember_session(tmp_path, [a, b], b)
    calls = record_session_calls(monkeypatch)
    window = make_window()
    assert calls == []
    assert tab_texts(window) == ["a", "b"]
    assert window.tabs.currentWidget().state_path == b


@pytest.mark.parametrize(
    "stored",
    [
        lambda a: {"open_state_files": ["x\u0000y.json", str(a)], "active_state_file": str(a)},
        lambda a: {"open_state_files": [str(a), "x\u0000y.json"], "active_state_file": str(a)},
        lambda a: {"open_state_files": [str(a)], "active_state_file": "z\u0000.json"},
    ],
)
def test_entries_with_nul_characters_are_ignored(make_window, files, tmp_path, no_dialogs, stored):
    a, _ = files
    (tmp_path / "config.json").write_text(json.dumps(stored(a)), encoding="utf-8")
    window = make_window()
    assert state_paths(window) == [a]
    assert session_of(tmp_path) == ([a], a)


def test_restore_shows_no_dialog(make_window, files, tmp_path, no_dialogs):
    a, b = files
    corrupted = tmp_path / "corrupted.json"
    corrupted.write_text("{not json", encoding="utf-8")
    remember_session(tmp_path, [tmp_path / "missing.json", a, corrupted, b], b)
    window = make_window()
    assert tab_texts(window) == ["a", "b"]


# --- sync ------------------------------------------------------------------------


def test_unsaved_tabs_are_never_listed(make_window, tmp_path):
    window = make_window()
    window.add_new_tab()
    window.add_new_tab()
    assert session_of(tmp_path) == ([], None)


def test_added_saved_tab_is_listed_and_active(make_window, files, tmp_path):
    a, _ = files
    window = make_window()
    window.add_saved_tab(a, TabState("a"))
    assert session_of(tmp_path) == ([a], a)


def test_first_save_adds_tab_to_session(qtbot, make_window, tmp_path, monkeypatch):
    target = tmp_path / "new-feature.json"
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName", lambda *args: (str(target), STATE_FILE_FILTER)
    )
    window = make_window()
    panel = window.tabs.widget(0).start_panel
    panel.name_input.setText("New Feature")
    qtbot.mouseClick(panel.save_button, Qt.MouseButton.LeftButton)
    assert session_of(tmp_path) == ([target], target)


def test_closing_a_tab_removes_it_from_session_and_keeps_file(make_window, files, tmp_path):
    a, b = files
    content = a.read_text(encoding="utf-8")
    window = make_window()
    window.add_saved_tab(a, TabState("a"))
    window.add_saved_tab(b, TabState("b"))
    window.close_tab(window.find_tab(a))
    assert session_of(tmp_path) == ([b], b)
    assert a.read_text(encoding="utf-8") == content


def test_closing_the_last_saved_tab_empties_the_session(make_window, files, tmp_path):
    a, _ = files
    remember_session(tmp_path, [a], a)
    window = make_window()
    window.close_tab(0)
    assert window.tabs.count() == 1
    assert window.tabs.widget(0).state_path is None
    assert session_of(tmp_path) == ([], None)
    assert a.exists()


def test_close_tab_with_invalid_index_writes_nothing(make_window, files, tmp_path):
    a, _ = files
    window = make_window()
    window.add_saved_tab(a, TabState("a"))
    before = (tmp_path / "config.json").read_text(encoding="utf-8")
    window.close_tab(5)
    assert (tmp_path / "config.json").read_text(encoding="utf-8") == before


def test_tabs_are_movable(make_window):
    assert make_window().tabs.isMovable()


def test_reorder_updates_session(make_window, files, tmp_path):
    a, b = files
    window = make_window()
    window.add_saved_tab(a, TabState("a"))
    window.add_saved_tab(b, TabState("b"))
    window.tabs.tabBar().moveTab(window.find_tab(a), window.find_tab(b))
    assert session_of(tmp_path)[0] == [b, a]


def test_current_tab_change_updates_active(make_window, files, tmp_path):
    a, b = files
    window = make_window()
    window.add_saved_tab(a, TabState("a"))
    window.add_saved_tab(b, TabState("b"))
    window.tabs.setCurrentIndex(window.find_tab(a))
    assert session_of(tmp_path)[1] == a


def test_selecting_unsaved_tab_keeps_previous_active(make_window, files, tmp_path):
    a, _ = files
    window = make_window()  # index 0: unsaved tab
    window.add_saved_tab(a, TabState("a"))
    window.tabs.setCurrentIndex(0)
    assert session_of(tmp_path)[1] == a
    window.close_tab(window.find_tab(a))
    assert session_of(tmp_path) == ([], None)


def test_closed_window_writes_no_session(make_window, files, tmp_path):
    a, b = files
    window = make_window()
    window.add_saved_tab(a, TabState("a"))
    window.add_saved_tab(b, TabState("b"))
    window.close()
    window.close_tab(window.find_tab(a))
    window.tabs.setCurrentIndex(0)
    assert session_of(tmp_path) == ([a, b], b)

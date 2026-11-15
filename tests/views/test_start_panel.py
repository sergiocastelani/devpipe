from pathlib import Path

import pytest
from PySide6.QtCore import QSize, Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFileDialog, QMessageBox, QVBoxLayout

from devpipe.persistence.skills_files import SkillsFiles
from devpipe.services.skills_service import SkillsService
from devpipe.views.start_panel import (
    BIG_BUTTON_MIN_HEIGHT,
    BIG_BUTTON_MIN_WIDTH,
    BIG_BUTTON_POINT_SIZE,
    BIG_BUTTON_SPACING,
    StartPanel,
)


UNUSED_SKILLS = SkillsService(SkillsFiles(), Path("ai-skills"))  # never installed in these tests


def make_panel(qtbot):
    panel = StartPanel(UNUSED_SKILLS)
    qtbot.addWidget(panel)
    return panel


@pytest.fixture
def warnings(monkeypatch):
    """(title, text) of every QMessageBox.warning call."""
    shown = []

    def fake(parent, title, text, *args):
        shown.append((title, text))
        return QMessageBox.StandardButton.Ok

    monkeypatch.setattr(QMessageBox, "warning", fake)
    return shown


class OpenedUrls(list):
    """QUrl of every QDesktopServices.openUrl call; `result` is what the fake returns."""

    result = True


@pytest.fixture
def opened_urls(monkeypatch):
    opened = OpenedUrls()

    def fake(url):
        opened.append(QUrl(url))
        return opened.result

    monkeypatch.setattr(QDesktopServices, "openUrl", fake)
    return opened


def big_button_column(panel) -> QVBoxLayout:
    """The child layout of the panel's root layout that holds new_worktree_button."""
    root = panel.layout()
    for index in range(root.count()):
        column = root.itemAt(index).layout()
        if column is not None and column.indexOf(panel.new_worktree_button) >= 0:
            return column
    pytest.fail("no child layout holds new_worktree_button")


def item_texts(panel):
    worktrees = panel.worktrees_list
    return [worktrees.item(i).text() for i in range(worktrees.count())]


def double_click(panel, row):
    panel.worktrees_list.itemDoubleClicked.emit(panel.worktrees_list.item(row))


def test_new_panel_is_unsaved_and_empty(qtbot):
    panel = make_panel(qtbot)
    assert panel.name_input.text() == ""
    assert panel.name_input.isEnabled()
    assert panel.slug_label.text() == ""
    assert not panel.save_button.isEnabled()
    assert not panel.new_worktree_button.isEnabled()
    assert panel.new_worktree_button.text() == "Create new worktree"
    assert panel.save_button.text() == "Save"


def test_typing_a_name_previews_slug_and_enables_only_save(qtbot):
    panel = make_panel(qtbot)
    qtbot.keyClicks(panel.name_input, "New Feature")
    assert panel.slug_label.text() == "new-feature"
    assert panel.save_button.isEnabled()
    assert not panel.new_worktree_button.isEnabled()


def test_accented_name_previews_slug(qtbot):
    panel = make_panel(qtbot)
    panel.name_input.setText("Nová Feature_X")
    assert panel.slug_label.text() == "nova-feature-x"
    assert panel.save_button.isEnabled()


def test_name_without_slug_keeps_save_disabled(qtbot):
    panel = make_panel(qtbot)
    panel.name_input.setText("!!!")
    assert panel.slug_label.text() == ""
    assert not panel.save_button.isEnabled()


def test_clearing_the_name_disables_save(qtbot):
    panel = make_panel(qtbot)
    panel.name_input.setText("abc")
    assert panel.save_button.isEnabled()
    panel.name_input.clear()
    assert not panel.save_button.isEnabled()
    assert panel.slug_label.text() == ""


def test_save_click_emits_slug(qtbot):
    panel = make_panel(qtbot)
    panel.name_input.setText("Nová Feature_X")
    with qtbot.waitSignal(panel.save_requested) as blocker:
        qtbot.mouseClick(panel.save_button, Qt.MouseButton.LeftButton)
    assert blocker.args == ["nova-feature-x"]
    assert panel.name_input.isEnabled()


def test_show_saved_switches_to_saved_mode(qtbot):
    panel = make_panel(qtbot)
    panel.name_input.setText("New Feature")
    panel.show_saved("new-feature")
    assert panel.name_input.text() == "new-feature"
    assert not panel.name_input.isEnabled()
    assert panel.slug_label.text() == "new-feature"
    assert not panel.save_button.isEnabled()
    assert panel.new_worktree_button.isEnabled()
    assert not panel.name_input.isHidden()
    assert not panel.save_button.isHidden()


def test_saved_mode_keeps_save_disabled(qtbot):
    panel = make_panel(qtbot)
    panel.show_saved("x")
    panel.name_input.setText("other")
    assert not panel.save_button.isEnabled()
    panel.show_saved("x")
    assert not panel.save_button.isEnabled()
    assert panel.new_worktree_button.isEnabled()


def test_new_worktree_button_matches_install_skills_button_format(qtbot):
    panel = make_panel(qtbot)
    expected_size = QSize(BIG_BUTTON_MIN_WIDTH, BIG_BUTTON_MIN_HEIGHT)
    assert panel.new_worktree_button.minimumSize() == panel.install_skills_button.minimumSize() == expected_size
    assert (
        panel.new_worktree_button.font().pointSize()
        == panel.install_skills_button.font().pointSize()
        == BIG_BUTTON_POINT_SIZE
    )


def test_new_worktree_click_emits_signal(qtbot):
    panel = make_panel(qtbot)
    panel.show_saved("x")
    with qtbot.waitSignal(panel.new_worktree_requested, timeout=1000) as blocker:
        qtbot.mouseClick(panel.new_worktree_button, Qt.MouseButton.LeftButton)
    assert blocker.args == []


def test_install_skills_button_is_big_and_enabled_before_save(qtbot):
    panel = make_panel(qtbot)
    button = panel.install_skills_button
    assert button.text() == "Install/Update skills"
    assert button.isEnabled()
    assert button.minimumSize() == QSize(BIG_BUTTON_MIN_WIDTH, BIG_BUTTON_MIN_HEIGHT)
    assert button.font().pointSize() == BIG_BUTTON_POINT_SIZE


def test_disabled_new_worktree_button_emits_nothing(qtbot):
    panel = make_panel(qtbot)
    with qtbot.assertNotEmitted(panel.new_worktree_requested):
        qtbot.mouseClick(panel.new_worktree_button, Qt.MouseButton.LeftButton)


def test_new_panel_hides_worktrees(qtbot):
    panel = make_panel(qtbot)
    assert panel.worktrees_label.isHidden()
    assert panel.worktrees_list.isHidden()
    assert panel.worktrees_list.count() == 0
    assert panel.worktrees_label.text() == "Worktrees"


def test_show_worktrees_lists_paths_in_order(qtbot, tmp_path):
    panel = make_panel(qtbot)
    a = tmp_path / "a"
    b = tmp_path / "b"
    panel.show_worktrees([b, a])
    assert item_texts(panel) == [str(b), str(a)]
    assert not panel.worktrees_label.isHidden()
    assert not panel.worktrees_list.isHidden()


def test_show_worktrees_replaces_previous_entries(qtbot, tmp_path):
    panel = make_panel(qtbot)
    a, b, c = tmp_path / "a", tmp_path / "b", tmp_path / "c"
    panel.show_worktrees([a, b])
    panel.show_worktrees([c])
    assert item_texts(panel) == [str(c)]


def test_show_worktrees_empty_hides_again(qtbot, tmp_path):
    panel = make_panel(qtbot)
    panel.show_worktrees([tmp_path / "a"])
    panel.show_worktrees([])
    assert panel.worktrees_list.count() == 0
    assert panel.worktrees_label.isHidden()
    assert panel.worktrees_list.isHidden()


def test_show_worktrees_does_not_keep_caller_list(qtbot, tmp_path):
    panel = make_panel(qtbot)
    paths = [tmp_path / "a"]
    panel.show_worktrees(paths)
    paths.append(tmp_path / "b")
    assert panel.worktrees_list.count() == 1
    assert paths == [tmp_path / "a", tmp_path / "b"]


def test_worktrees_are_below_the_big_buttons(qtbot):
    panel = make_panel(qtbot)
    layout = panel.layout()
    header = layout.itemAt(layout.count() - 2).layout()
    assert header is not None
    assert header.indexOf(panel.worktrees_label) == 0
    assert header.indexOf(panel.remove_worktree_button) == 1
    assert layout.indexOf(panel.worktrees_list) == layout.count() - 1


def test_remove_button_hidden_with_the_list(qtbot, tmp_path):
    panel = make_panel(qtbot)
    assert panel.remove_worktree_button.isHidden()
    assert panel.remove_worktree_button.text() == "x"
    panel.show_worktrees([tmp_path / "a"])
    assert not panel.remove_worktree_button.isHidden()
    panel.show_worktrees([])
    assert panel.remove_worktree_button.isHidden()


def test_remove_button_enabled_only_with_a_selection(qtbot, tmp_path):
    panel = make_panel(qtbot)
    panel.show_worktrees([tmp_path / "a", tmp_path / "b"])
    assert not panel.remove_worktree_button.isEnabled()
    panel.worktrees_list.setCurrentRow(1)
    assert panel.remove_worktree_button.isEnabled()
    panel.show_worktrees([tmp_path / "a"])
    assert not panel.remove_worktree_button.isEnabled()


def test_remove_button_emits_selected_path(qtbot, tmp_path):
    panel = make_panel(qtbot)
    a, b = tmp_path / "a", tmp_path / "b"
    panel.show_worktrees([a, b])
    panel.worktrees_list.setCurrentRow(1)
    with qtbot.waitSignal(panel.remove_worktree_requested) as blocker:
        qtbot.mouseClick(panel.remove_worktree_button, Qt.MouseButton.LeftButton)
    assert blocker.args == [b]
    assert panel.worktrees_list.count() == 2  # the panel does not remove it itself


def test_double_click_existing_folder_opens_it(qtbot, tmp_path, opened_urls, warnings):
    panel = make_panel(qtbot)
    d = tmp_path / "d"
    d.mkdir()
    panel.show_worktrees([d])
    double_click(panel, 0)
    assert opened_urls == [QUrl.fromLocalFile(str(d))]
    assert warnings == []


def test_double_click_missing_folder_warns_and_keeps_list(qtbot, tmp_path, opened_urls, warnings):
    panel = make_panel(qtbot)
    d = tmp_path / "d"
    d.mkdir()
    m = tmp_path / "m"
    panel.show_worktrees([d, m])
    double_click(panel, 1)
    assert warnings == [("Folder not found", f"Folder not found: {m}")]
    assert opened_urls == []
    assert item_texts(panel) == [str(d), str(m)]


def test_double_click_folder_the_os_cannot_open_warns(qtbot, tmp_path, opened_urls, warnings):
    panel = make_panel(qtbot)
    d = tmp_path / "d"
    e = tmp_path / "e"
    d.mkdir()
    e.mkdir()
    opened_urls.result = False
    panel.show_worktrees([d, e])
    double_click(panel, 0)
    assert opened_urls == [QUrl.fromLocalFile(str(d))]
    assert warnings == [("Cannot open folder", f"Cannot open folder: {d}")]
    assert item_texts(panel) == [str(d), str(e)]


def test_double_click_file_is_not_a_folder(qtbot, tmp_path, opened_urls, warnings):
    panel = make_panel(qtbot)
    f = tmp_path / "f.txt"
    f.write_text("x", "utf-8")
    panel.show_worktrees([f])
    double_click(panel, 0)
    assert warnings == [("Folder not found", f"Folder not found: {f}")]
    assert opened_urls == []


def test_start_pipeline_button_is_big_and_disabled_before_save(qtbot):
    panel = make_panel(qtbot)
    button = panel.start_pipeline_button
    assert button.text() == "Start Pipeline"
    assert not button.isEnabled()
    assert button.minimumSize() == QSize(BIG_BUTTON_MIN_WIDTH, BIG_BUTTON_MIN_HEIGHT)
    assert button.font().pointSize() == BIG_BUTTON_POINT_SIZE


def answer_folder(monkeypatch, answer: str) -> list:
    """Fake QFileDialog.getExistingDirectory: records calls, returns `answer` ("" cancels)."""
    calls = []

    def fake(*args, **kwargs):
        calls.append(args)
        return answer

    monkeypatch.setattr(QFileDialog, "getExistingDirectory", fake)
    return calls


def test_start_pipeline_click_emits_signal_after_save(qtbot, monkeypatch, tmp_path):
    panel = make_panel(qtbot)
    panel.show_saved("x")
    panel.show_worktrees([tmp_path / "a"])
    calls = answer_folder(monkeypatch, "")
    assert panel.start_pipeline_button.isEnabled()
    with qtbot.assertNotEmitted(panel.worktree_folder_chosen):
        with qtbot.waitSignal(panel.start_pipeline_requested, timeout=1000) as blocker:
            qtbot.mouseClick(panel.start_pipeline_button, Qt.MouseButton.LeftButton)
    assert blocker.args == []
    assert calls == []  # worktrees listed: no folder dialog


def test_start_pipeline_with_no_worktrees_asks_for_folder(qtbot, monkeypatch, tmp_path):
    panel = make_panel(qtbot)
    panel.show_saved("x")
    calls = answer_folder(monkeypatch, str(tmp_path))
    chosen = []
    started = []
    panel.worktree_folder_chosen.connect(lambda path: chosen.append(path))
    panel.start_pipeline_requested.connect(lambda: started.append(list(chosen)))
    qtbot.mouseClick(panel.start_pipeline_button, Qt.MouseButton.LeftButton)
    assert len(calls) == 1
    assert chosen == [tmp_path]
    assert started == [[tmp_path]]  # the folder is reported before the start request


def test_start_pipeline_folder_cancel_emits_nothing(qtbot, monkeypatch):
    panel = make_panel(qtbot)
    panel.show_saved("x")
    calls = answer_folder(monkeypatch, "")
    with qtbot.assertNotEmitted(panel.worktree_folder_chosen):
        with qtbot.assertNotEmitted(panel.start_pipeline_requested):
            qtbot.mouseClick(panel.start_pipeline_button, Qt.MouseButton.LeftButton)
    assert len(calls) == 1


def test_disabled_start_pipeline_button_emits_nothing(qtbot):
    panel = make_panel(qtbot)
    with qtbot.assertNotEmitted(panel.start_pipeline_requested):
        qtbot.mouseClick(panel.start_pipeline_button, Qt.MouseButton.LeftButton)

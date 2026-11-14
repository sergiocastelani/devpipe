import pytest
from PySide6.QtCore import QSize, Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QMessageBox, QVBoxLayout

from devpipe.views.start_panel import (
    BIG_BUTTON_MIN_HEIGHT,
    BIG_BUTTON_MIN_WIDTH,
    BIG_BUTTON_POINT_SIZE,
    BIG_BUTTON_SPACING,
    StartPanel,
)


def make_panel(qtbot):
    panel = StartPanel()
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
    """The child layout of the panel's root layout that holds open_button."""
    root = panel.layout()
    for index in range(root.count()):
        column = root.itemAt(index).layout()
        if column is not None and column.indexOf(panel.open_button) >= 0:
            return column
    pytest.fail("no child layout holds open_button")


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
    assert not panel.open_button.isEnabled()
    assert not panel.create_button.isEnabled()
    assert not panel.new_worktree_button.isEnabled()
    assert panel.new_worktree_button.text() == "Create new worktree"
    assert panel.save_button.text() == "Save"
    assert panel.open_button.text() == "Open a pipeline"
    assert panel.create_button.text() == "Create a pipeline"


def test_typing_a_name_previews_slug_and_enables_only_save(qtbot):
    panel = make_panel(qtbot)
    qtbot.keyClicks(panel.name_input, "New Feature")
    assert panel.slug_label.text() == "new-feature"
    assert panel.save_button.isEnabled()
    assert not panel.open_button.isEnabled()
    assert not panel.create_button.isEnabled()
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
    assert panel.open_button.isEnabled()
    assert panel.create_button.isEnabled()
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
    assert panel.open_button.isEnabled()
    assert panel.create_button.isEnabled()
    assert panel.new_worktree_button.isEnabled()


def test_new_worktree_button_matches_open_button_format(qtbot):
    panel = make_panel(qtbot)
    expected_size = QSize(BIG_BUTTON_MIN_WIDTH, BIG_BUTTON_MIN_HEIGHT)
    assert panel.new_worktree_button.minimumSize() == panel.open_button.minimumSize() == expected_size
    assert (
        panel.new_worktree_button.font().pointSize()
        == panel.open_button.font().pointSize()
        == BIG_BUTTON_POINT_SIZE
    )


def test_new_worktree_button_is_first_in_centered_column(qtbot):
    panel = make_panel(qtbot)
    column = big_button_column(panel)
    assert column.indexOf(panel.new_worktree_button) == 0
    assert column.indexOf(panel.open_button) == 1
    assert column.indexOf(panel.create_button) == 2
    assert column.alignment() == Qt.AlignmentFlag.AlignCenter
    assert column.spacing() == BIG_BUTTON_SPACING


def test_new_worktree_click_emits_signal(qtbot):
    panel = make_panel(qtbot)
    panel.show_saved("x")
    with qtbot.waitSignal(panel.new_worktree_requested, timeout=1000) as blocker:
        qtbot.mouseClick(panel.new_worktree_button, Qt.MouseButton.LeftButton)
    assert blocker.args == []


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
    assert layout.indexOf(panel.worktrees_label) == layout.count() - 2
    assert layout.indexOf(panel.worktrees_list) == layout.count() - 1


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

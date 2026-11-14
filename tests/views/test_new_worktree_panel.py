from pathlib import Path

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFileDialog, QGroupBox, QLabel, QPushButton, QScrollArea, QToolButton

from devpipe.models.worktree import WorktreeRequest
from devpipe.views.new_worktree_panel import NewWorktreePanel


def make_panel(qtbot):
    panel = NewWorktreePanel()
    qtbot.addWidget(panel)
    return panel


def fill(group, source="C:/src", parent="C:/wt"):
    group.source_input.setText(source)
    group.parent_input.setText(parent)


def add_groups(qtbot, panel, total):
    while len(panel.groups()) < total:
        qtbot.mouseClick(panel.add_button, Qt.MouseButton.LeftButton)
    return panel.groups()


def click_create(qtbot, panel):
    with qtbot.waitSignal(panel.create_requested) as blocker:
        qtbot.mouseClick(panel.create_button, Qt.MouseButton.LeftButton)
    return blocker.args


class FakeDialog:
    """Stands in for QFileDialog.getExistingDirectory; records calls, returns `result`."""

    def __init__(self, result=""):
        self.result = result
        self.calls = []

    def __call__(self, parent, caption, directory):
        self.calls.append((parent, caption, directory))
        return self.result


@pytest.fixture
def dialog(monkeypatch):
    fake = FakeDialog()
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", fake)
    return fake


def test_fresh_panel_has_one_empty_group(qtbot):
    panel = make_panel(qtbot)
    groups = panel.groups()
    assert len(groups) == 1
    group = groups[0]
    assert group.title() == "Worktree 1"
    assert group.source_input.text() == ""
    assert group.parent_input.text() == ""
    assert group.remove_button.isHidden()
    assert not panel.create_button.isEnabled()
    assert panel.create_button.text() == "Create"


def test_group_rows_have_labels_inputs_and_pickers(qtbot):
    panel = make_panel(qtbot)
    group = panel.groups()[0]
    assert isinstance(group, QGroupBox)
    labels = {label.text(): label for label in group.findChildren(QLabel)}
    assert labels["Source project folder"].buddy() is group.source_input
    assert labels["Worktree parent folder"].buddy() is group.parent_input
    assert isinstance(group.source_picker, QToolButton)
    assert isinstance(group.parent_picker, QToolButton)


def test_accessible_names_and_tooltips(qtbot):
    panel = make_panel(qtbot)
    group = panel.groups()[0]
    expected = [
        (group.source_picker, "Choose source project folder"),
        (group.parent_picker, "Choose worktree parent folder"),
        (panel.add_button, "Add worktree"),
        (group.remove_button, "Remove worktree"),
    ]
    for widget, text in expected:
        assert widget.toolTip() == text
        assert widget.accessibleName() == text


def test_add_appends_removable_group(qtbot):
    panel = make_panel(qtbot)
    qtbot.mouseClick(panel.add_button, Qt.MouseButton.LeftButton)
    first, second = panel.groups()
    assert second.title() == "Worktree 2"
    assert not second.remove_button.isHidden()
    assert first.remove_button.isHidden()


def test_remove_deletes_group(qtbot):
    panel = make_panel(qtbot)
    first, second = add_groups(qtbot, panel, 2)
    qtbot.mouseClick(second.remove_button, Qt.MouseButton.LeftButton)
    assert panel.groups() == [first]


def test_remove_middle_renumbers(qtbot):
    panel = make_panel(qtbot)
    groups = add_groups(qtbot, panel, 3)
    for text, group in zip(["one", "two", "three"], groups):
        group.source_input.setText(text)
    qtbot.mouseClick(groups[1].remove_button, Qt.MouseButton.LeftButton)
    remaining = panel.groups()
    assert [group.title() for group in remaining] == ["Worktree 1", "Worktree 2"]
    assert remaining[1].source_input.text() == "three"
    assert not remaining[1].remove_button.isHidden()


def test_removed_group_not_in_requests(qtbot):
    panel = make_panel(qtbot)
    groups = add_groups(qtbot, panel, 3)
    for (source, parent), group in zip([("A", "B"), ("C", "D"), ("E", "F")], groups):
        fill(group, source, parent)
    qtbot.mouseClick(groups[1].remove_button, Qt.MouseButton.LeftButton)
    args = click_create(qtbot, panel)
    assert args[0] == [
        WorktreeRequest(Path("A"), Path("B")),
        WorktreeRequest(Path("E"), Path("F")),
    ]


def test_remove_first_group_is_ignored(qtbot):
    panel = make_panel(qtbot)
    add_groups(qtbot, panel, 2)
    panel._remove_group(panel.groups()[0])
    assert len(panel.groups()) == 2


def test_create_enabled_only_when_all_editable_groups_filled(qtbot):
    panel = make_panel(qtbot)
    first, second = add_groups(qtbot, panel, 2)
    fill(first)
    assert not panel.create_button.isEnabled()
    second.source_input.setText("C:/src2")
    assert not panel.create_button.isEnabled()
    second.parent_input.setText("C:/wt2")
    assert panel.create_button.isEnabled()
    first.parent_input.setText("")
    assert not panel.create_button.isEnabled()


@pytest.mark.parametrize("blank", [" ", "\t "])
def test_whitespace_only_counts_as_empty(qtbot, blank):
    panel = make_panel(qtbot)
    fill(panel.groups()[0], parent=blank)
    assert not panel.create_button.isEnabled()


def test_removing_unfilled_group_enables_create(qtbot):
    panel = make_panel(qtbot)
    first, second = add_groups(qtbot, panel, 2)
    fill(first)
    assert not panel.create_button.isEnabled()
    qtbot.mouseClick(second.remove_button, Qt.MouseButton.LeftButton)
    assert panel.create_button.isEnabled()


def test_create_emits_trimmed_requests_in_order(qtbot):
    panel = make_panel(qtbot)
    first, second = add_groups(qtbot, panel, 2)
    fill(first, "  A  ", "B")
    fill(second, "C", " D")
    args = click_create(qtbot, panel)
    assert args == [[WorktreeRequest(Path("A"), Path("B")), WorktreeRequest(Path("C"), Path("D"))]]


def test_picker_writes_chosen_folder(qtbot, dialog, tmp_path):
    panel = make_panel(qtbot)
    group = panel.groups()[0]
    dialog.result = tmp_path.as_posix()
    qtbot.mouseClick(group.source_picker, Qt.MouseButton.LeftButton)
    assert group.source_input.text() == str(tmp_path)
    qtbot.mouseClick(group.parent_picker, Qt.MouseButton.LeftButton)
    assert group.parent_input.text() == str(tmp_path)


def test_picker_cancel_keeps_input(qtbot, dialog):
    panel = make_panel(qtbot)
    group = panel.groups()[0]
    group.source_input.setText("keep")
    dialog.result = ""
    qtbot.mouseClick(group.source_picker, Qt.MouseButton.LeftButton)
    assert len(dialog.calls) == 1
    assert group.source_input.text() == "keep"


def test_picker_starts_in_existing_folder(qtbot, dialog, tmp_path):
    panel = make_panel(qtbot)
    group = panel.groups()[0]
    group.source_input.setText(f"  {tmp_path}  ")
    qtbot.mouseClick(group.source_picker, Qt.MouseButton.LeftButton)
    [(parent, caption, directory)] = dialog.calls
    assert parent is group
    assert directory == str(tmp_path)
    assert caption == "Choose source project folder"


@pytest.mark.parametrize("kind", ["empty", "missing", "file"])
def test_picker_start_empty_when_input_not_a_folder(qtbot, dialog, tmp_path, kind):
    if kind == "empty":
        text = ""
    elif kind == "missing":
        text = str(tmp_path / "missing")
    else:
        file = tmp_path / "file.txt"
        file.write_text("x")
        text = str(file)
    panel = make_panel(qtbot)
    group = panel.groups()[0]
    group.source_input.setText(text)
    qtbot.mouseClick(group.source_picker, Qt.MouseButton.LeftButton)
    [(_parent, _caption, directory)] = dialog.calls
    assert directory == ""


def test_locked_group_is_read_only(qtbot):
    panel = make_panel(qtbot)
    _first, second = add_groups(qtbot, panel, 2)
    second.set_locked(True)
    assert second.is_locked()
    assert second.source_input.isReadOnly()
    assert second.parent_input.isReadOnly()
    assert not second.source_picker.isEnabled()
    assert not second.parent_picker.isEnabled()
    assert second.remove_button.isHidden()


def test_unlocking_restores_controls(qtbot):
    panel = make_panel(qtbot)
    first, second = add_groups(qtbot, panel, 2)
    second.set_locked(True)
    second.set_locked(False)
    assert not second.is_locked()
    assert not second.source_input.isReadOnly()
    assert not second.parent_input.isReadOnly()
    assert second.source_picker.isEnabled()
    assert second.parent_picker.isEnabled()
    assert not second.remove_button.isHidden()
    first.set_locked(True)
    assert first.remove_button.isHidden()
    first.set_locked(False)
    assert first.remove_button.isHidden()


def test_locked_group_excluded_from_check_and_requests(qtbot):
    panel = make_panel(qtbot)
    first, second = add_groups(qtbot, panel, 2)
    first.set_locked(True)
    fill(second, "S", "P")
    assert panel.editable_groups() == [second]
    assert panel.create_button.isEnabled()
    args = click_create(qtbot, panel)
    assert args == [[WorktreeRequest(Path("S"), Path("P"))]]


def test_locking_refreshes_create(qtbot):
    panel = make_panel(qtbot)
    first, second = add_groups(qtbot, panel, 2)
    fill(first)
    assert not panel.create_button.isEnabled()
    second.set_locked(True)
    assert panel.create_button.isEnabled()
    second.set_locked(False)
    assert not panel.create_button.isEnabled()


def test_all_locked_enables_create_and_emits_empty(qtbot):
    panel = make_panel(qtbot)
    for group in add_groups(qtbot, panel, 2):
        group.set_locked(True)
    assert panel.create_button.isEnabled()
    assert click_create(qtbot, panel) == [[]]


def test_add_after_lock_appends_editable_group(qtbot):
    panel = make_panel(qtbot)
    first = panel.groups()[0]
    fill(first)
    first.set_locked(True)
    qtbot.mouseClick(panel.add_button, Qt.MouseButton.LeftButton)
    second = panel.groups()[1]
    assert not second.is_locked()
    assert not second.remove_button.isHidden()
    assert not panel.create_button.isEnabled()


def test_groups_and_editable_groups_keep_display_order(qtbot):
    panel = make_panel(qtbot)
    first, second, third = add_groups(qtbot, panel, 3)
    second.set_locked(True)
    assert panel.groups() == [first, second, third]
    assert panel.editable_groups() == [first, third]
    assert panel.groups() is not panel.groups()


def test_reset_returns_to_one_empty_unlocked_group(qtbot):
    panel = make_panel(qtbot)
    groups = add_groups(qtbot, panel, 3)
    for group in groups:
        fill(group)
    groups[0].set_locked(True)
    panel.reset()
    [group] = panel.groups()
    assert group not in groups
    assert group.title() == "Worktree 1"
    assert group.source_input.text() == ""
    assert group.parent_input.text() == ""
    assert not group.is_locked()
    assert group.remove_button.isHidden()
    assert not panel.create_button.isEnabled()


def test_no_back_or_cancel_button(qtbot):
    panel = make_panel(qtbot)
    add_groups(qtbot, panel, 2)
    buttons = panel.findChildren(QPushButton)
    assert len(buttons) == 2
    assert set(buttons) == {panel.add_button, panel.create_button}


def test_layout_order_scroll_add_create(qtbot):
    panel = make_panel(qtbot)
    layout = panel.layout()
    widgets = [layout.itemAt(i).widget() for i in range(layout.count())]
    assert len(widgets) == 3
    scroll, add, create = widgets
    assert isinstance(scroll, QScrollArea)
    assert add is panel.add_button
    assert create is panel.create_button
    for group in panel.groups():
        assert scroll.widget().isAncestorOf(group)

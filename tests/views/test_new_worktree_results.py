from pathlib import Path

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QScrollArea

from devpipe.models.worktree import WorktreeResult
from devpipe.views.new_worktree_panel import (
    FAILURE_BORDER_COLOR,
    RESULT_STYLE,
    SUCCESS_BORDER_COLOR,
    NewWorktreePanel,
)

GREEN = RESULT_STYLE.format(color=SUCCESS_BORDER_COLOR)
RED = RESULT_STYLE.format(color=FAILURE_BORDER_COLOR)


def make_panel(qtbot):
    panel = NewWorktreePanel()
    qtbot.addWidget(panel)
    return panel


def fill(group, source, parent="C:/wt"):
    group.source_input.setText(source)
    group.parent_input.setText(parent)


def ok(group):
    return WorktreeResult(group.request(), Path(group.parent_input.text()) / "feat-x", None)


def failed(group, error="boom"):
    return WorktreeResult(group.request(), Path(group.parent_input.text()) / "feat-x", error)


def make_panel_with(qtbot, n):
    panel = make_panel(qtbot)
    for _ in range(n - 1):
        qtbot.mouseClick(panel.add_button, Qt.MouseButton.LeftButton)
    for i, group in enumerate(panel.groups(), start=1):
        fill(group, f"C:/src{i}")
    return panel


def assert_plain(group):
    assert group.styleSheet() == ""
    assert group.toolTip() == ""
    assert group.accessibleDescription() == ""


def assert_text(group, text):
    assert group.toolTip() == text
    assert group.accessibleDescription() == text


def controls(group):
    return [group.source_input, group.parent_input, group.source_picker, group.parent_picker]


def partial_failure(qtbot):
    panel = make_panel_with(qtbot, 2)
    g1, g2 = panel.groups()
    r1, r2 = ok(g1), failed(g2, "not a git repository")
    panel.show_results([r1, r2])
    return panel, g1, g2, r1, r2


def test_fresh_panel_has_hidden_error_box_and_progress(qtbot):
    panel = make_panel(qtbot)
    assert panel.error_box.isHidden()
    assert panel.error_box.isReadOnly()
    assert panel.error_box.toPlainText() == ""
    assert panel.progress_bar.isHidden()
    assert panel.progress_bar.minimum() == panel.progress_bar.maximum() == 0
    assert panel.error_box.accessibleName() == "Worktree errors"
    assert panel.progress_bar.accessibleName() == "Creating worktrees"
    assert_plain(panel.groups()[0])
    assert panel.create_button.text() == "Create"


def test_layout_order_add_error_progress_create(qtbot):
    panel = make_panel(qtbot)
    layout = panel.layout()
    widgets = [layout.itemAt(i).widget() for i in range(layout.count())]
    assert len(widgets) == 5
    assert isinstance(widgets[0], QScrollArea)
    assert widgets[1:] == [panel.add_button, panel.error_box, panel.progress_bar, panel.create_button]


def test_set_busy_disables_panel_and_shows_progress(qtbot):
    panel = make_panel_with(qtbot, 2)
    g1, g2 = panel.groups()
    assert panel.create_button.isEnabled()
    panel.set_busy(True)
    for widget in controls(g1) + controls(g2) + [g2.remove_button]:
        assert not widget.isEnabled()
    assert not panel.add_button.isEnabled()
    assert not panel.create_button.isEnabled()
    assert not panel.progress_bar.isHidden()
    with qtbot.assertNotEmitted(panel.create_requested):
        qtbot.mouseClick(panel.create_button, Qt.MouseButton.LeftButton)


def test_set_busy_false_restores_panel(qtbot):
    panel = make_panel_with(qtbot, 2)
    g1, g2 = panel.groups()
    panel.set_busy(True)
    panel.set_busy(False)
    for widget in controls(g1) + controls(g2) + [g2.remove_button]:
        assert widget.isEnabled()
    assert panel.add_button.isEnabled()
    assert panel.create_button.isEnabled()
    assert panel.progress_bar.isHidden()


def test_set_busy_false_keeps_locked_group_locked(qtbot):
    panel = make_panel_with(qtbot, 2)
    g1, g2 = panel.groups()
    g1.set_locked(True)
    panel.set_busy(True)
    panel.set_busy(False)
    assert g1.source_input.isReadOnly()
    assert g1.parent_input.isReadOnly()
    assert not g1.source_picker.isEnabled()
    assert not g1.parent_picker.isEnabled()
    assert g2.source_picker.isEnabled()
    assert g2.parent_picker.isEnabled()


def test_set_busy_false_keeps_create_disabled_when_unfilled(qtbot):
    panel = make_panel(qtbot)
    panel.set_busy(True)
    panel.set_busy(False)
    assert not panel.create_button.isEnabled()


def test_partial_failure_shows_green_red_and_retry(qtbot):
    panel, g1, g2, r1, r2 = partial_failure(qtbot)
    assert g1.styleSheet() == GREEN
    assert g1.is_locked()
    assert_text(g1, f"Created: {r1.target}")
    assert g1.remove_button.isHidden()
    assert g2.styleSheet() == RED
    assert not g2.is_locked()
    assert_text(g2, "Failed: not a git repository")
    assert not g2.remove_button.isHidden()
    assert panel.error_box.toPlainText() == f"{Path('C:/src2')} \u2192 {r2.target}: not a git repository"
    assert not panel.error_box.isHidden()
    assert panel.create_button.text() == "Retry"


def test_retry_success_clears_errors(qtbot):
    panel, g1, g2, _r1, _r2 = partial_failure(qtbot)
    g2.source_input.setText("C:/fixed")
    panel.show_results([ok(g2)])
    for group in (g1, g2):
        assert group.styleSheet() == GREEN
        assert group.is_locked()
    assert panel.error_box.toPlainText() == ""
    assert panel.error_box.isHidden()
    assert panel.create_button.text() == "Retry"


def test_new_failure_replaces_error_list(qtbot):
    panel, _g1, g2, _r1, _r2 = partial_failure(qtbot)
    panel.show_results([failed(g2, "other")])
    lines = panel.error_box.toPlainText().split("\n")
    assert len(lines) == 1
    assert lines[0].endswith(": other")
    assert g2.toolTip() == "Failed: other"


def test_results_pair_with_editable_groups_only(qtbot):
    panel = make_panel_with(qtbot, 3)
    g1, g2, g3 = panel.groups()
    r1 = ok(g1)
    panel.show_results([r1, failed(g2), failed(g3)])
    panel.show_results([ok(g2), failed(g3, "x")])
    assert g1.styleSheet() == GREEN
    assert_text(g1, f"Created: {r1.target}")
    assert g2.styleSheet() == GREEN
    assert g2.is_locked()
    assert g3.styleSheet() == RED
    assert_text(g3, "Failed: x")


def test_group_added_after_results_is_plain_and_paired_next(qtbot):
    panel, _g1, g2, _r1, _r2 = partial_failure(qtbot)
    qtbot.mouseClick(panel.add_button, Qt.MouseButton.LeftButton)
    g3 = panel.groups()[2]
    assert_plain(g3)
    assert not g3.is_locked()
    assert g3 in panel.editable_groups()
    fill(g3, "C:/src3")
    panel.show_results([ok(g2), failed(g3)])
    assert g3.styleSheet() == RED


def test_edited_red_group_stays_red_until_next_results(qtbot):
    _panel, _g1, g2, _r1, _r2 = partial_failure(qtbot)
    g2.source_input.setText("C:/edited")
    assert g2.styleSheet() == RED
    assert g2.toolTip() == "Failed: not a git repository"


def test_all_ok_keeps_create_label(qtbot):
    panel = make_panel_with(qtbot, 2)
    g1, g2 = panel.groups()
    panel.show_results([ok(g1), ok(g2)])
    for group in (g1, g2):
        assert group.styleSheet() == GREEN
        assert group.is_locked()
    assert panel.error_box.isHidden()
    assert panel.create_button.text() == "Create"
    assert panel.create_button.isEnabled()


@pytest.mark.parametrize("count", [1, 3])
def test_show_results_length_mismatch_raises(qtbot, count):
    panel = make_panel_with(qtbot, 2)
    g1, g2 = panel.groups()
    results = [failed(g1)] * count
    with pytest.raises(ValueError):
        panel.show_results(results)
    for group in (g1, g2):
        assert_plain(group)
        assert not group.is_locked()
    assert panel.error_box.isHidden()
    assert panel.create_button.text() == "Create"


def test_show_empty_results_with_no_editable_groups(qtbot):
    panel = make_panel_with(qtbot, 2)
    g1, g2 = panel.groups()
    g1.set_locked(True)
    g2.set_locked(True)
    panel.show_results([])
    for group in (g1, g2):
        assert_plain(group)
        assert group.is_locked()
    assert panel.error_box.isHidden()


def test_show_results_does_not_change_busy(qtbot):
    panel = make_panel_with(qtbot, 1)
    g1 = panel.groups()[0]
    panel.set_busy(True)
    panel.show_results([failed(g1)])
    assert not panel.progress_bar.isHidden()
    assert not panel.create_button.isEnabled()


def test_reset_after_failure_is_fresh(qtbot):
    panel, _g1, _g2, _r1, _r2 = partial_failure(qtbot)
    panel.reset()
    groups = panel.groups()
    assert len(groups) == 1
    assert groups[0].title() == "Worktree 1"
    assert_plain(groups[0])
    assert not groups[0].is_locked()
    assert panel.error_box.toPlainText() == ""
    assert panel.error_box.isHidden()
    assert panel.create_button.text() == "Create"
    assert not panel.create_button.isEnabled()


def test_reset_while_busy_clears_busy(qtbot):
    panel = make_panel(qtbot)
    panel.set_busy(True)
    panel.reset()
    assert panel.progress_bar.isHidden()
    assert panel.add_button.isEnabled()
    group = panel.groups()[0]
    assert group.source_input.isEnabled()
    assert group.parent_input.isEnabled()

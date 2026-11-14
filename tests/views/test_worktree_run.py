import json
import shutil
import threading
from pathlib import Path

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox

from devpipe.models.tab_state import Panel, TabState
from devpipe.models.worktree import GitWorktreeError, WorktreeRequest, WorktreeResult
from devpipe.views.pipeline_tab import PipelineTab
from devpipe.views.worktree_worker import WorktreeWorker

RUN_TIMEOUT_MS = 5000
FEATURE = "feat-x"


@pytest.fixture
def warnings(monkeypatch):
    """(title, text) of every QMessageBox.warning call."""
    shown = []

    def fake(parent, title, text, *args):
        shown.append((title, text))
        return QMessageBox.StandardButton.Ok

    monkeypatch.setattr(QMessageBox, "warning", fake)
    return shown


@pytest.fixture
def writes(monkeypatch, tab_states):
    """(path, state) of every tab_states.save call (the original still runs)."""
    recorded = []
    original = tab_states.save

    def spy(path, state):
        recorded.append((path, state))
        return original(path, state)

    monkeypatch.setattr(tab_states, "save", spy)
    return recorded


def read_json(path: Path) -> dict:
    return json.loads(path.read_text("utf-8"))


def saved_tab(qtbot, tab_states, worktree_service, path, worktrees=()):
    tab = PipelineTab(tab_states, worktree_service)
    qtbot.addWidget(tab)
    tab.apply_saved(path, TabState(FEATURE, Panel.START, list(worktrees)))
    tab.open_new_worktree_panel()
    return tab


def fill(tab, tmp_path, n) -> list[Path]:
    panel = tab.new_worktree_panel
    while len(panel.groups()) < n:
        panel.add_button.click()
    targets = []
    for i, group in enumerate(panel.groups()):
        src = tmp_path / f"src{i}"
        wt = tmp_path / f"wt{i}"
        src.mkdir(exist_ok=True)
        wt.mkdir(exist_ok=True)
        group.source_input.setText(str(src))
        group.parent_input.setText(str(wt))
        targets.append((wt / FEATURE).resolve())
    return targets


def run(qtbot, tab, writes):
    writes.clear()
    with qtbot.waitSignal(tab.run_finished, timeout=RUN_TIMEOUT_MS):
        qtbot.mouseClick(tab.new_worktree_panel.create_button, Qt.MouseButton.LeftButton)


def expected_file(*targets):
    return {
        "version": 2,
        "feature_name": FEATURE,
        "active_panel": "start",
        "worktrees": [str(t) for t in targets],
    }


def list_texts(tab):
    worktrees = tab.start_panel.worktrees_list
    return [worktrees.item(i).text() for i in range(worktrees.count())]


def release(qtbot, fake_git, tab):
    """Open the gate and wait for the run to end, so no QThread is destroyed while running."""
    fake_git.gate.set()
    qtbot.waitUntil(lambda: not tab.run_in_progress, timeout=RUN_TIMEOUT_MS)


@pytest.fixture
def partial_failure(qtbot, tmp_path, tab_states, worktree_service, fake_git, writes, warnings):
    """A saved tab after a run where group 1 of 2 failed with "not a git repository"."""
    path = tmp_path / "x.json"
    tab = saved_tab(qtbot, tab_states, worktree_service, path)
    t0, t1 = fill(tab, tmp_path, 2)
    fake_git.failures[t1] = GitWorktreeError("not a git repository")
    run(qtbot, tab, writes)
    return tab, path, t0, t1


# --- normal runs ------------------------------------------------------------------


def test_successful_run_returns_to_start_and_saves_targets(
    qtbot, tmp_path, tab_states, worktree_service, fake_git, writes
):
    path = tmp_path / "x.json"
    tab = saved_tab(qtbot, tab_states, worktree_service, path)
    t0, t1 = fill(tab, tmp_path, 2)
    run(qtbot, tab, writes)
    assert fake_git.calls == [
        ((tmp_path / "src0").resolve(), FEATURE, t0),
        ((tmp_path / "src1").resolve(), FEATURE, t1),
    ]
    assert tab.stack.currentWidget() is tab.start_panel
    assert tab.active_panel is Panel.START
    assert read_json(path) == expected_file(t0, t1)
    assert list_texts(tab) == [str(t0), str(t1)]
    assert not tab.start_panel.worktrees_list.isHidden()
    assert len(writes) == 1
    assert not tab.run_in_progress


def test_panel_is_busy_while_run_in_progress(
    qtbot, tmp_path, tab_states, worktree_service, fake_git, writes
):
    path = tmp_path / "x.json"
    tab = saved_tab(qtbot, tab_states, worktree_service, path)
    fill(tab, tmp_path, 1)
    panel = tab.new_worktree_panel
    fake_git.gate = threading.Event()
    try:
        writes.clear()
        qtbot.mouseClick(panel.create_button, Qt.MouseButton.LeftButton)
        assert tab.run_in_progress
        assert not panel.progress_bar.isHidden()
        assert not panel.create_button.isEnabled()
        assert not panel.add_button.isEnabled()
        assert read_json(path)["worktrees"] == []
        with qtbot.waitSignal(tab.run_finished, timeout=RUN_TIMEOUT_MS):
            fake_git.gate.set()
        assert panel.progress_bar.isHidden()
        assert not tab.run_in_progress
    finally:
        release(qtbot, fake_git, tab)


def test_partial_failure_stays_on_panel_with_retry(partial_failure, writes):
    tab, path, t0, t1 = partial_failure
    panel = tab.new_worktree_panel
    g0, g1 = panel.groups()
    assert tab.stack.currentWidget() is panel
    assert g0.is_locked()
    assert g0.toolTip() == f"Created: {t0}"
    assert not g1.is_locked()
    assert g1.toolTip() == "Failed: not a git repository"
    assert panel.create_button.text() == "Retry"
    assert "not a git repository" in panel.error_box.toPlainText()
    assert read_json(path) == expected_file(t0)
    assert list_texts(tab) == [str(t0)]
    assert len(writes) == 1


def test_retry_processes_only_fixed_group(qtbot, tmp_path, partial_failure, fake_git, writes):
    tab, path, t0, t1 = partial_failure
    fake_git.failures.clear()
    src9 = tmp_path / "src9"
    src9.mkdir()
    tab.new_worktree_panel.groups()[1].source_input.setText(str(src9))
    before = len(fake_git.calls)
    run(qtbot, tab, writes)
    assert fake_git.calls[before:] == [(src9.resolve(), FEATURE, t1)]
    assert tab.stack.currentWidget() is tab.start_panel
    assert read_json(path) == expected_file(t0, t1)
    assert list_texts(tab) == [str(t0), str(t1)]


def test_retry_with_no_editable_group_returns_to_start(qtbot, partial_failure, fake_git, writes):
    tab, path, t0, _t1 = partial_failure
    before = list(fake_git.calls)
    qtbot.mouseClick(tab.new_worktree_panel.groups()[1].remove_button, Qt.MouseButton.LeftButton)
    run(qtbot, tab, writes)
    assert fake_git.calls == before
    assert tab.stack.currentWidget() is tab.start_panel
    assert read_json(path) == expected_file(t0)
    assert len(writes) == 1


def test_already_saved_target_is_not_duplicated(
    qtbot, tmp_path, tab_states, worktree_service, writes
):
    path = tmp_path / "x.json"
    t0 = (tmp_path / "wt0" / FEATURE).resolve()
    tab = saved_tab(qtbot, tab_states, worktree_service, path, worktrees=[t0])
    assert fill(tab, tmp_path, 1) == [t0]
    run(qtbot, tab, writes)
    assert tab.stack.currentWidget() is tab.start_panel
    assert read_json(path)["worktrees"] == [str(t0)]
    assert list_texts(tab) == [str(t0)]


# --- write failures ---------------------------------------------------------------


def test_save_failure_after_success_warns_and_keeps_paths(
    qtbot, tmp_path, tab_states, worktree_service, writes, warnings
):
    folder = tmp_path / "d"
    folder.mkdir()
    path = folder / "x.json"
    tab = saved_tab(qtbot, tab_states, worktree_service, path)
    [t0] = fill(tab, tmp_path, 1)
    shutil.rmtree(folder)
    run(qtbot, tab, writes)
    assert len(warnings) == 1
    assert warnings[0][0] == "Cannot save state file"
    assert tab.stack.currentWidget() is tab.start_panel
    folder.mkdir()
    tab.open_new_worktree_panel()
    assert read_json(path) == expected_file(t0)


def test_save_failure_after_partial_failure_stays_on_panel(
    qtbot, tmp_path, tab_states, worktree_service, fake_git, writes, warnings
):
    folder = tmp_path / "d"
    folder.mkdir()
    path = folder / "x.json"
    tab = saved_tab(qtbot, tab_states, worktree_service, path)
    _t0, t1 = fill(tab, tmp_path, 2)
    fake_git.failures[t1] = GitWorktreeError("not a git repository")
    shutil.rmtree(folder)
    run(qtbot, tab, writes)
    assert len(warnings) == 1
    assert warnings[0][0] == "Cannot save state file"
    assert tab.stack.currentWidget() is tab.new_worktree_panel
    assert tab.new_worktree_panel.create_button.text() == "Retry"


# --- unexpected errors ------------------------------------------------------------


def test_unexpected_error_applies_recovered_results(
    qtbot, tmp_path, tab_states, worktree_service, fake_git, writes, warnings
):
    path = tmp_path / "x.json"
    tab = saved_tab(qtbot, tab_states, worktree_service, path)
    t0, t1 = fill(tab, tmp_path, 2)
    fake_git.failures[t1] = RuntimeError("disk on fire")
    run(qtbot, tab, writes)
    panel = tab.new_worktree_panel
    g0, g1 = panel.groups()
    assert g0.is_locked()
    assert g0.toolTip() == f"Created: {t0}"
    assert g1.toolTip() == "Failed: unexpected error: RuntimeError: disk on fire; cleaned up"
    assert panel.create_button.text() == "Retry"
    assert fake_git.removed == [((tmp_path / "src1").resolve(), FEATURE, t1, True)]
    assert read_json(path) == expected_file(t0)
    assert len(writes) == 1
    assert warnings == []


def test_recovery_failure_shows_warning_and_changes_nothing(
    qtbot, tmp_path, tab_states, worktree_service, fake_git, writes, warnings
):
    path = tmp_path / "x.json"
    tab = saved_tab(qtbot, tab_states, worktree_service, path)
    _t0, t1 = fill(tab, tmp_path, 2)
    fake_git.failures[t1] = RuntimeError("x")
    fake_git.remove_error = RuntimeError("boom")
    run(qtbot, tab, writes)
    panel = tab.new_worktree_panel
    assert warnings == [("Worktree creation failed", "RuntimeError: boom")]
    assert writes == []
    assert tab.stack.currentWidget() is panel
    for group in panel.groups():
        assert not group.is_locked()
        assert group.styleSheet() == ""
        assert group.toolTip() == ""
    assert panel.create_button.text() == "Create"
    assert panel.create_button.isEnabled()
    assert panel.progress_bar.isHidden()
    assert read_json(path)["worktrees"] == []


def test_snapshot_failure_shows_warning_and_does_not_run(
    qtbot, tmp_path, tab_states, worktree_service, fake_git, writes, warnings
):
    tab = saved_tab(qtbot, tab_states, worktree_service, tmp_path / "x.json")
    fill(tab, tmp_path, 1)
    fake_git.branch_check_error = RuntimeError("no git")
    run(qtbot, tab, writes)
    assert warnings == [("Worktree creation failed", "RuntimeError: no git")]
    assert fake_git.calls == []
    assert writes == []


# --- run lifecycle ----------------------------------------------------------------


def test_run_finished_after_outcome_applied(qtbot, tmp_path, tab_states, worktree_service, writes):
    tab = saved_tab(qtbot, tab_states, worktree_service, tmp_path / "x.json")
    fill(tab, tmp_path, 1)
    recorded = []
    tab.run_finished.connect(
        lambda: recorded.append((tab.run_in_progress, tab.stack.currentWidget()))
    )
    run(qtbot, tab, writes)
    assert recorded == [(False, tab.start_panel)]


def test_create_ignored_while_run_in_progress(
    qtbot, tmp_path, tab_states, worktree_service, fake_git, writes
):
    tab = saved_tab(qtbot, tab_states, worktree_service, tmp_path / "x.json")
    fill(tab, tmp_path, 1)
    request = tab.new_worktree_panel.groups()[0].request()
    fake_git.gate = threading.Event()
    try:
        writes.clear()
        qtbot.mouseClick(tab.new_worktree_panel.create_button, Qt.MouseButton.LeftButton)
        tab.new_worktree_panel.create_requested.emit([request])
        with qtbot.waitSignal(tab.run_finished, timeout=RUN_TIMEOUT_MS):
            fake_git.gate.set()
        assert len(fake_git.calls) == 1
        with qtbot.assertNotEmitted(tab.run_finished, wait=200):
            pass
    finally:
        release(qtbot, fake_git, tab)


def test_create_on_unsaved_tab_is_ignored(qtbot, tmp_path, tab_states, worktree_service, fake_git):
    tab = PipelineTab(tab_states, worktree_service)
    qtbot.addWidget(tab)
    tab.open_new_worktree_panel()
    src = tmp_path / "src0"
    wt = tmp_path / "wt0"
    src.mkdir()
    wt.mkdir()
    tab.new_worktree_panel.create_requested.emit([WorktreeRequest(src, wt)])
    assert not tab.run_in_progress
    assert tab.new_worktree_panel.progress_bar.isHidden()
    assert fake_git.calls == []
    assert sorted(tmp_path.iterdir()) == sorted([src, wt])


# --- worker -----------------------------------------------------------------------


def test_worker_delivers_results(qtbot, tmp_path, worktree_service):
    src = tmp_path / "src0"
    wt = tmp_path / "wt0"
    src.mkdir()
    wt.mkdir()
    request = WorktreeRequest(src, wt)
    worker = WorktreeWorker(worktree_service, FEATURE, [request])
    try:
        with qtbot.waitSignal(worker.results_ready, timeout=RUN_TIMEOUT_MS) as blocker:
            worker.start()
        [result] = blocker.args[0]
        assert isinstance(result, WorktreeResult)
        assert result.ok
        assert result.request == request
        assert worker.wait()
    finally:
        worker.wait()


def test_worker_reports_error_type_without_message(qtbot, tmp_path, worktree_service, fake_git):
    fake_git.branch_check_error = RuntimeError()
    src = tmp_path / "src0"
    wt = tmp_path / "wt0"
    src.mkdir()
    wt.mkdir()
    worker = WorktreeWorker(worktree_service, FEATURE, [WorktreeRequest(src, wt)])
    try:
        with qtbot.waitSignal(worker.error_occurred, timeout=RUN_TIMEOUT_MS) as blocker:
            worker.start()
        assert blocker.args == ["RuntimeError"]
    finally:
        worker.wait()

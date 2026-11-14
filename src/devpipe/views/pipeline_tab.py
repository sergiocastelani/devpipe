"""One pipeline tab: a stack of panels, exactly one shown at a time.

New panels are added to `stack` and `_panels`; the start panel is always the first one.
Only panels in PERSISTED_PANELS are written as `active_panel`.
"""

from pathlib import Path

from PySide6.QtCore import Signal, Slot
from PySide6.QtWidgets import QMessageBox, QStackedWidget, QVBoxLayout, QWidget

from devpipe.models.tab_state import PERSISTED_PANELS, Panel, TabState, TabStateError
from devpipe.models.worktree import WorktreeRequest, WorktreeResult
from devpipe.services.tab_state_service import TabStateService
from devpipe.services.worktree_service import WorktreeService
from devpipe.views.new_worktree_panel import NewWorktreePanel
from devpipe.views.start_panel import StartPanel
from devpipe.views.worktree_worker import WorktreeWorker

NEW_TAB_TITLE = "New pipeline"
SAVE_ERROR_TITLE = "Cannot save state file"
RUN_ERROR_TITLE = "Worktree creation failed"


class PipelineTab(QWidget):
    identity_changed = Signal()  # emitted after title() or tooltip() change
    run_finished = Signal()  # emitted after a run's outcome was applied (results, recovery or warning)

    def __init__(self, tab_states: TabStateService, worktrees: WorktreeService) -> None:
        super().__init__()
        self._tab_states = tab_states
        self._worktree_service = worktrees  # `_worktrees` holds the path list
        self._worker: WorktreeWorker | None = None  # the run in progress, if any
        self._state_path: Path | None = None
        self._feature_name: str | None = None
        self._active_panel = Panel.START
        # The tab's worktree folders; every state file write carries it. Other code
        # may replace or append to it, and the next write persists it.
        self._worktrees: list[Path] = []

        self.stack = QStackedWidget()
        self.start_panel = StartPanel()
        self.stack.addWidget(self.start_panel)
        self.new_worktree_panel = NewWorktreePanel()
        self.stack.addWidget(self.new_worktree_panel)
        self.stack.setCurrentWidget(self.start_panel)
        # The single map from panel id to panel widget.
        self._panels: dict[Panel, QWidget] = {
            Panel.START: self.start_panel,
            Panel.NEW_WORKTREE: self.new_worktree_panel,
        }

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.stack)

        self.start_panel.new_worktree_requested.connect(self.open_new_worktree_panel)
        self.new_worktree_panel.create_requested.connect(self._start_run)

    @property
    def run_in_progress(self) -> bool:
        """True from the start of a run until its outcome was applied (just before run_finished)."""
        return self._worker is not None

    @property
    def state_path(self) -> Path | None:
        """The tab's state file; None while unsaved."""
        return self._state_path

    @property
    def active_panel(self) -> Panel:
        """The panel shown in the stack."""
        return self._active_panel

    def title(self) -> str:
        """Text of this tab in the tab bar."""
        return self._feature_name if self._state_path is not None else NEW_TAB_TITLE

    def tooltip(self) -> str:
        """Tooltip of this tab in the tab bar."""
        return str(self._state_path) if self._state_path is not None else ""

    def show_panel(self, panel: Panel) -> None:
        """Show `panel`; when saved, rewrite the state file (auto-save, no dialog).

        A failed write shows a warning; the tab stays saved and the next call writes again.
        """
        self._display(panel)
        if self._state_path is not None:
            self._write(self._state_path, self._current_state())

    def open_new_worktree_panel(self) -> None:
        """Show the New worktree panel, fresh (one empty group).

        Uses show_panel, so a saved tab auto-saves; the file keeps active_panel "start".
        """
        self.new_worktree_panel.reset()
        self.show_panel(Panel.NEW_WORKTREE)

    def apply_saved(self, path: Path, state: TabState) -> None:
        """Put the tab in saved mode for `path` and `state` without writing."""
        self._state_path = path
        self._feature_name = state.feature_name
        self._worktrees = list(state.worktrees)
        self.start_panel.show_saved(state.feature_name)
        self.start_panel.show_worktrees(state.worktrees)
        self._display(state.active_panel)
        self.identity_changed.emit()

    def save_as(self, path: Path, feature_name: str) -> bool:
        """First save: write the state file, then switch to saved mode.

        Returns False (tab unchanged, warning shown) when the write fails.
        """
        state = TabState(feature_name, self._persisted_panel(), list(self._worktrees))
        if not self._write(path, state):
            return False
        self.apply_saved(path, state)
        return True

    def _start_run(self, requests: list[WorktreeRequest]) -> None:
        """Create the worktrees of `requests` on a worker thread; ignored while a run is
        in progress or when the tab is unsaved (no feature name)."""
        if self._worker is not None or self._state_path is None:
            return
        self.new_worktree_panel.set_busy(True)
        self._worker = WorktreeWorker(self._worktree_service, self._feature_name, requests)
        self._worker.results_ready.connect(self._on_run_results)
        self._worker.error_occurred.connect(self._on_run_error)
        self._worker.start()

    @Slot(object)
    def _on_run_results(self, results: list[WorktreeResult]) -> None:
        """Apply a run's results: merge the created paths, then go back to start (all ok)
        or show the results; either way the state file is written once."""
        self._worker.wait()  # the thread is returning; finish it before any modal box
        self.new_worktree_panel.set_busy(False)
        created = [result.target for result in results if result.ok]
        self._worktrees = self._worktree_service.merge_paths(self._worktrees, created)
        self.start_panel.show_worktrees(self._worktrees)
        if all(result.ok for result in results):
            self.show_panel(Panel.START)  # its auto-save is the single write
        else:
            self.new_worktree_panel.show_results(results)
            self._write(self._state_path, self._current_state())
        self._end_run()

    @Slot(str)
    def _on_run_error(self, text: str) -> None:
        """The snapshot or the recovery raised: warn; nothing is written or changed."""
        self._worker.wait()
        self.new_worktree_panel.set_busy(False)
        QMessageBox.warning(self, RUN_ERROR_TITLE, text)
        self._end_run()

    def _end_run(self) -> None:
        worker, self._worker = self._worker, None
        worker.deleteLater()
        self.run_finished.emit()

    def _display(self, panel: Panel) -> None:
        self.stack.setCurrentWidget(self._panels[panel])
        self._active_panel = panel

    def _current_state(self) -> TabState:
        return TabState(self._feature_name, self._persisted_panel(), list(self._worktrees))

    def _persisted_panel(self) -> Panel:
        """The panel to write as active_panel: the shown one, or START when it is not persisted."""
        return self._active_panel if self._active_panel in PERSISTED_PANELS else Panel.START

    def _write(self, path: Path, state: TabState) -> bool:
        """The only place the tab writes its file; warns and returns False on failure."""
        try:
            self._tab_states.save(path, state)
        except TabStateError as error:
            QMessageBox.warning(self, SAVE_ERROR_TITLE, f"{error.path}\n\n{error.reason}")
            return False
        return True

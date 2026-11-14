"""One pipeline tab: a stack of panels, exactly one shown at a time.

New panels are added to `stack` and `_panels`; the start panel is always the first one.
Only panels in PERSISTED_PANELS are written as `active_panel`.
"""

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QMessageBox, QStackedWidget, QVBoxLayout, QWidget

from devpipe.models.tab_state import PERSISTED_PANELS, Panel, TabState, TabStateError
from devpipe.services.tab_state_service import TabStateService
from devpipe.views.new_worktree_panel import NewWorktreePanel
from devpipe.views.start_panel import StartPanel

NEW_TAB_TITLE = "New pipeline"
SAVE_ERROR_TITLE = "Cannot save state file"


class PipelineTab(QWidget):
    identity_changed = Signal()  # emitted after title() or tooltip() change

    def __init__(self, tab_states: TabStateService) -> None:
        super().__init__()
        self._tab_states = tab_states
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

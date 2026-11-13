"""Main window: one tab per feature pipeline."""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QFileDialog, QMainWindow, QMessageBox, QTabWidget, QToolButton

from devpipe.models.tab_state import TabState
from devpipe.services.paths import same_file, with_default_suffix
from devpipe.services.session_service import SessionService
from devpipe.services.tab_state_service import TabStateService
from devpipe.services.window_state_service import WindowStateService
from devpipe.views.pipeline_tab import PipelineTab

NEW_TAB_BUTTON_TEXT = "+"
NEW_TAB_BUTTON_TOOLTIP = "New pipeline tab"
STATE_FILE_SUFFIX = ".json"
STATE_FILE_FILTER = "JSON files (*.json)"
SAVE_DIALOG_TITLE = "Save pipeline state"
ALREADY_OPEN_TITLE = "State file already open"
ALREADY_OPEN_TEXT = "This state file is already open in another tab."


class MainWindow(QMainWindow):
    def __init__(
        self,
        window_state: WindowStateService,
        tab_states: TabStateService,
        session: SessionService,
    ) -> None:
        super().__init__()
        self._window_state = window_state
        self._tab_states = tab_states
        self._session = session
        self.setWindowTitle("devpipe")
        self.resize(1000, 700)

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)

        self.new_tab_button = QToolButton()
        self.new_tab_button.setText(NEW_TAB_BUTTON_TEXT)
        self.new_tab_button.setToolTip(NEW_TAB_BUTTON_TOOLTIP)
        self.new_tab_button.setAccessibleName(NEW_TAB_BUTTON_TOOLTIP)
        self.new_tab_button.clicked.connect(lambda: self.add_new_tab())  # drop the `checked` argument
        self.tabs.setCornerWidget(self.new_tab_button, Qt.Corner.TopRightCorner)

        self.add_new_tab()

    def add_pipeline_tab(self, tab: PipelineTab) -> int:
        """Insert `tab` at the end, titled from tab.title() / tab.tooltip(); return its index.

        The single entry point for adding tabs. Connects tab.identity_changed so the
        tab text and tooltip are refreshed from title() / tooltip(). Does not select the tab.
        """
        index = self.tabs.addTab(tab, tab.title())
        self.tabs.setTabToolTip(index, tab.tooltip())
        tab.identity_changed.connect(lambda: self._refresh_tab_identity(tab))
        tab.start_panel.save_requested.connect(lambda slug: self._save_tab_as(tab, slug))
        return index

    def add_new_tab(self) -> PipelineTab:
        """Build an unsaved PipelineTab, add it with add_pipeline_tab, select it, return it."""
        tab = PipelineTab(self._tab_states)
        self.tabs.setCurrentIndex(self.add_pipeline_tab(tab))
        return tab

    def add_saved_tab(self, path: Path, state: TabState) -> PipelineTab:
        """Build a PipelineTab, apply_saved(path, state) (no write), add it with
        add_pipeline_tab, select it and return it. Does not check for duplicates."""
        tab = PipelineTab(self._tab_states)
        tab.apply_saved(path, state)
        index = self.add_pipeline_tab(tab)
        self.tabs.setCurrentIndex(index)
        return tab

    def find_tab(self, path: Path) -> int | None:
        """Index of the tab whose state_path is the same file as `path` (same_file), else None.
        Unsaved tabs never match."""
        for index in range(self.tabs.count()):
            widget = self.tabs.widget(index)
            if (
                isinstance(widget, PipelineTab)
                and widget.state_path is not None
                and same_file(widget.state_path, path)
            ):
                return index
        return None

    def close_tab(self, index: int) -> None:
        """Remove the tab at `index` (no confirmation, nothing deleted on disk).

        The single place tabs are removed; wired to tabs.tabCloseRequested.
        Out-of-range index: no-op. If no tab is left, calls add_new_tab().
        """
        widget = self.tabs.widget(index)
        if widget is None:
            return
        self.tabs.removeTab(index)
        widget.deleteLater()
        if self.tabs.count() == 0:
            self.add_new_tab()

    def _save_tab_as(self, tab: PipelineTab, feature_name: str) -> None:
        """First-save flow for `tab` (Save dialog, duplicate check, write, last-used folder)."""
        suggested = self._session.start_folder() / f"{feature_name}{STATE_FILE_SUFFIX}"
        selected, _ = QFileDialog.getSaveFileName(
            self, SAVE_DIALOG_TITLE, str(suggested), STATE_FILE_FILTER
        )
        if selected == "":
            return
        path = with_default_suffix(Path(selected), STATE_FILE_SUFFIX)
        if self.find_tab(path) is not None:
            QMessageBox.warning(self, ALREADY_OPEN_TITLE, f"{path}\n\n{ALREADY_OPEN_TEXT}")
            return
        if not tab.save_as(path, feature_name):
            return  # the tab already showed the write error
        self._session.remember_folder(path)

    def _refresh_tab_identity(self, tab: PipelineTab) -> None:
        """Copy tab.title() / tab.tooltip() to its tab bar entry; no-op if `tab` is not in self.tabs."""
        index = self.tabs.indexOf(tab)
        if index < 0:
            return
        self.tabs.setTabText(index, tab.title())
        self.tabs.setTabToolTip(index, tab.tooltip())

    def show_initial(self) -> None:
        """Show the window in the state it had at the end of the last session."""
        if self._window_state.was_maximized():
            self.showMaximized()
        else:
            self.show()

    def closeEvent(self, event: QCloseEvent) -> None:
        self._window_state.remember_maximized(self.isMaximized())
        super().closeEvent(event)

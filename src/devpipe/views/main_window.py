"""Main window: one tab per feature pipeline."""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QCloseEvent, QKeySequence
from PySide6.QtWidgets import QFileDialog, QMainWindow, QMessageBox, QTabWidget, QToolButton

from devpipe.models.tab_state import TabState, TabStateError
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
FILE_MENU_TITLE = "&File"  # mnemonic: Alt+F
OPEN_ACTION_TEXT = "&Open..."  # mnemonic: O inside the File menu
OPEN_SHORTCUT = "Ctrl+O"
OPEN_DIALOG_TITLE = "Open pipeline state"
OPEN_ERROR_TITLE = "Cannot open state file"


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
        self._session_sync_enabled = False

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self._build_menu_bar()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)

        self.new_tab_button = QToolButton()
        self.new_tab_button.setText(NEW_TAB_BUTTON_TEXT)
        self.new_tab_button.setToolTip(NEW_TAB_BUTTON_TOOLTIP)
        self.new_tab_button.setAccessibleName(NEW_TAB_BUTTON_TOOLTIP)
        self.new_tab_button.clicked.connect(lambda: self.add_new_tab())  # drop the `checked` argument
        self.tabs.setCornerWidget(self.new_tab_button, Qt.Corner.TopRightCorner)
        self.tabs.setMovable(True)
        self.tabs.currentChanged.connect(lambda _index: self._sync_session())
        self.tabs.tabBar().tabMoved.connect(lambda _from, _to: self._sync_session())

        stored = (self._session.open_files(), self._session.active_file())
        self._restore_session(*stored)
        self._session_sync_enabled = True
        if self._session_snapshot() != stored:
            self._sync_session()  # only when restore dropped entries or changed the active file

    def add_pipeline_tab(self, tab: PipelineTab) -> int:
        """Insert `tab` at the end, titled from tab.title() / tab.tooltip(); return its index.

        The single entry point for adding tabs. Connects tab.identity_changed so the
        tab text and tooltip are refreshed from title() / tooltip(). Does not select the tab.
        """
        index = self.tabs.addTab(tab, tab.title())
        self.tabs.setTabToolTip(index, tab.tooltip())
        tab.identity_changed.connect(lambda: self._refresh_tab_identity(tab))
        tab.start_panel.save_requested.connect(lambda slug: self._save_tab_as(tab, slug))
        tab.identity_changed.connect(self._sync_session)  # records the first save
        self._sync_session()
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
        self._sync_session()

    def _restore_session(self, files: list[Path], active: Path | None) -> None:
        """Open a saved tab for each valid state file of `files`, in order; select `active`.

        Invalid or duplicate entries are skipped silently. If nothing was restored, add one
        unsaved tab. Called once from the constructor, while session sync is disabled.
        """
        selected: PipelineTab | None = None
        for path in files:
            if self.find_tab(path) is not None:
                continue  # duplicate entry
            try:
                state = self._tab_states.load(path)
            except TabStateError:
                continue  # invalid file: skipped silently
            tab = self.add_saved_tab(path, state)
            if active is not None and same_file(path, active):
                selected = tab
        if self.tabs.count() == 0:
            self.add_new_tab()
        elif selected is not None:
            self.tabs.setCurrentWidget(selected)
        else:
            self.tabs.setCurrentIndex(0)

    def _session_snapshot(self) -> tuple[list[Path], Path | None]:
        """(state files of the saved tabs in tab order, active file) as the tabs show them now."""
        widgets = (self.tabs.widget(index) for index in range(self.tabs.count()))
        files = [
            widget.state_path
            for widget in widgets
            if isinstance(widget, PipelineTab) and widget.state_path is not None
        ]
        return files, self._session_active_file(files)

    def _sync_session(self) -> None:
        """Write _session_snapshot() to the session (remember_session).

        No-op while session sync is disabled (during restore and after the window closed).
        """
        if not self._session_sync_enabled:
            return
        self._session.remember_session(*self._session_snapshot())

    def _session_active_file(self, files: list[Path]) -> Path | None:
        """State file to record as active for the given open `files`.

        The current tab's file when it is saved; else the previously stored active file
        if it is still open, else None.
        """
        current = self.tabs.currentWidget()
        if isinstance(current, PipelineTab) and current.state_path is not None:
            return current.state_path
        previous = self._session.active_file()
        if previous is not None and any(same_file(previous, path) for path in files):
            return previous
        return None

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

    def _build_menu_bar(self) -> None:
        """Create the File menu with the Open... action (Ctrl+O)."""
        file_menu = self.menuBar().addMenu(FILE_MENU_TITLE)
        self.open_action = QAction(OPEN_ACTION_TEXT, self)
        self.open_action.setShortcut(QKeySequence(OPEN_SHORTCUT))
        self.open_action.triggered.connect(lambda: self._open_state_file())  # drop the `checked` argument
        file_menu.addAction(self.open_action)

    def _open_state_file(self) -> None:
        """File > Open flow: Open dialog, focus an already open tab, or load and add a saved tab."""
        selected, _ = QFileDialog.getOpenFileName(
            self, OPEN_DIALOG_TITLE, str(self._session.start_folder()), STATE_FILE_FILTER
        )
        if selected == "":
            return
        path = Path(selected)
        index = self.find_tab(path)
        if index is not None:
            tab = self.tabs.widget(index)
            self.tabs.setCurrentIndex(index)
            self._session.remember_folder(tab.state_path)  # the tab's own spelling of the file
            return
        try:
            state = self._tab_states.load(path)
        except TabStateError as error:
            QMessageBox.warning(self, OPEN_ERROR_TITLE, f"{error.path}\n\n{error.reason}")
            return
        self.add_saved_tab(path, state)
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
        self._session_sync_enabled = False  # Qt may emit currentChanged while tearing tabs down
        self._window_state.remember_maximized(self.isMaximized())
        super().closeEvent(event)

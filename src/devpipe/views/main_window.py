"""Main window: one tab per feature pipeline."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QMainWindow, QTabWidget, QToolButton

from devpipe.services.window_state_service import WindowStateService
from devpipe.views.pipeline_tab import PipelineTab

NEW_TAB_BUTTON_TEXT = "+"
NEW_TAB_BUTTON_TOOLTIP = "New pipeline tab"


class MainWindow(QMainWindow):
    def __init__(self, window_state: WindowStateService) -> None:
        super().__init__()
        self._window_state = window_state
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
        return index

    def add_new_tab(self) -> PipelineTab:
        """Build an unsaved PipelineTab, add it with add_pipeline_tab, select it, return it."""
        tab = PipelineTab()
        self.tabs.setCurrentIndex(self.add_pipeline_tab(tab))
        return tab

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

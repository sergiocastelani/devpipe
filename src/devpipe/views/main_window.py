"""Main window: one tab per feature pipeline."""

from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QMainWindow, QTabWidget

from devpipe.services.window_state_service import WindowStateService
from devpipe.views.start_tab import StartTab


class MainWindow(QMainWindow):
    def __init__(self, window_state: WindowStateService) -> None:
        super().__init__()
        self._window_state = window_state
        self.setWindowTitle("devpipe")
        self.resize(1000, 700)

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self.tabs.addTab(StartTab(), "New pipeline")

    def show_initial(self) -> None:
        """Show the window in the state it had at the end of the last session."""
        if self._window_state.was_maximized():
            self.showMaximized()
        else:
            self.show()

    def closeEvent(self, event: QCloseEvent) -> None:
        self._window_state.remember_maximized(self.isMaximized())
        super().closeEvent(event)

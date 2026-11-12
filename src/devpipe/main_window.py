"""Main window: one tab per feature pipeline."""

from PySide6.QtWidgets import QMainWindow, QTabWidget

from devpipe.start_tab import StartTab


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("devpipe")
        self.resize(1000, 700)

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self.tabs.addTab(StartTab(), "New pipeline")

"""Composition root: builds repositories and services and injects them into views.

This is the only module allowed to import from every layer.
"""

import sys

from PySide6.QtWidgets import QApplication

from devpipe.views.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()

"""Entry point: `uv run devpipe` or `python -m devpipe`."""

import sys

from PySide6.QtWidgets import QApplication

from devpipe.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())

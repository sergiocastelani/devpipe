"""Devpipe create panel: opened by "Start Pipeline" on the start panel."""

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QVBoxLayout, QWidget

from devpipe.services.terminal_service import TerminalService
from devpipe.views.open_console_button import OpenConsoleButton


class DevpipeCreatePanel(QWidget):
    console_opened = Signal(object)  # forwarded from open_console_button: the TerminalId

    def __init__(self, terminals: TerminalService, worktrees: Callable[[], list[Path]]) -> None:
        """`worktrees` returns the tab's current worktree list; it is read only when
        a console is opened, which starts in the first entry."""
        super().__init__()
        self._worktrees = worktrees
        self.open_console_button = OpenConsoleButton(terminals, self._console_folder)
        self.open_console_button.console_opened.connect(self.console_opened)

        layout = QVBoxLayout(self)
        layout.addWidget(
            self.open_console_button, alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
        )
        layout.addStretch()

    def _console_folder(self) -> Path | None:
        paths = self._worktrees()
        return paths[0] if paths else None

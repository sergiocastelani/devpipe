"""Reusable "Open console" button: shows a terminal window in a folder.

Self-contained: give it a TerminalService and a folder source, a callable asked
for the folder only when the button is clicked. It has no label, only a console
icon. A click brings the console already opened in that folder to the
foreground, or opens a new one when there is none, and emits console_opened
with its TerminalId.
"""

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QMessageBox, QToolButton, QWidget

from devpipe.models.terminal import TerminalError, TerminalId
from devpipe.services.terminal_service import TerminalService

OPEN_CONSOLE_TOOLTIP = "Open console on working folder"
OPEN_CONSOLE_ERROR_TITLE = "Cannot open console"
NO_FOLDER_TEXT = "There is no working folder to open a console in."
BUTTON_SIZE = 64
ICON_SIZE = 48
_ICON_BACKGROUND = QColor("#1e1e1e")
_ICON_BORDER = QColor("#8a8a8a")
_ICON_PROMPT = QColor("#e6e6e6")
_ICON_PROMPT_TEXT = ">_"


def console_icon(size: int = ICON_SIZE) -> QIcon:
    """A command prompt icon drawn in code: a dark window with a ">_" prompt."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    margin = size * 0.06
    frame = QRectF(margin, margin + size * 0.08, size - 2 * margin, size - 2 * margin - size * 0.16)
    painter.setPen(QPen(_ICON_BORDER, max(1.0, size / 24)))
    painter.setBrush(_ICON_BACKGROUND)
    radius = size * 0.1
    painter.drawRoundedRect(frame, radius, radius)
    font = QFont("Consolas")
    font.setStyleHint(QFont.StyleHint.Monospace)
    font.setBold(True)
    font.setPixelSize(round(size * 0.38))
    painter.setFont(font)
    painter.setPen(_ICON_PROMPT)
    text_area = frame.adjusted(size * 0.12, 0, 0, 0)
    painter.drawText(text_area, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, _ICON_PROMPT_TEXT)
    painter.end()
    return QIcon(pixmap)


class OpenConsoleButton(QToolButton):
    console_opened = Signal(object)  # emitted with the TerminalId after a console was opened or brought to front

    def __init__(
        self,
        terminals: TerminalService,
        folder_source: Callable[[], Path | None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._terminals = terminals
        self._folder_source = folder_source
        self.setIcon(console_icon())
        self.setIconSize(QSize(ICON_SIZE, ICON_SIZE))
        self.setFixedSize(BUTTON_SIZE, BUTTON_SIZE)
        self.setToolTip(OPEN_CONSOLE_TOOLTIP)
        self.setAccessibleName(OPEN_CONSOLE_TOOLTIP)
        self.clicked.connect(lambda: self.open_console())  # drop the `checked` argument

    def open_console(self) -> TerminalId | None:
        """Ask the folder source for the folder and show a console there: the one
        already open in that folder (brought to the foreground) or a new one; emit
        and return its TerminalId.

        Without a folder (source returns None), or on failure, shows a warning and returns None.
        """
        folder = self._folder_source()
        if folder is None:
            QMessageBox.warning(self, OPEN_CONSOLE_ERROR_TITLE, NO_FOLDER_TEXT)
            return None
        try:
            terminal = self._terminals.open_console(folder)
        except TerminalError as error:
            QMessageBox.warning(self, OPEN_CONSOLE_ERROR_TITLE, f"{folder}\n\n{error.message}")
            return None
        self.console_opened.emit(terminal)
        return terminal

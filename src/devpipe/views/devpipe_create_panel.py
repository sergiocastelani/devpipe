"""Devpipe create panel: opened by "Start Pipeline" on the start panel."""

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QHideEvent, QResizeEvent
from PySide6.QtWidgets import QLabel, QPlainTextEdit, QVBoxLayout, QWidget

from devpipe.services.terminal_service import TerminalService
from devpipe.views.open_console_button import OpenConsoleButton

PROMPT_SAVE_DELAY_MS = 5000
"""Quiet time after the last edit of the prompt before it is reported for saving."""

PENDING_MARK = " *"
"""Appended to the prompt label while an edit is waiting to be reported."""


class DevpipeCreatePanel(QWidget):
    console_opened = Signal(object)  # forwarded from open_console_button: the TerminalId
    # The prompt text, PROMPT_SAVE_DELAY_MS after the user stopped typing
    # (or at once when the panel is hidden with an edit still pending).
    prompt_changed = Signal(str)

    def __init__(self, terminals: TerminalService, worktrees: Callable[[], list[Path]]) -> None:
        """`worktrees` returns the tab's current worktree list; it is read only when
        a console is opened, which starts in the first entry."""
        super().__init__()
        self._worktrees = worktrees
        self.open_console_button = OpenConsoleButton(terminals, self._console_folder)
        self.open_console_button.console_opened.connect(self.console_opened)

        self.prompt_label = QLabel()
        self._label_text = ""
        label_font = self.prompt_label.font()
        label_font.setPointSize(16)
        self.prompt_label.setFont(label_font)
        self.prompt_input = QPlainTextEdit()
        self.prompt_label.setBuddy(self.prompt_input)

        # Debounce: every edit restarts the timer; only its timeout reports the text.
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(PROMPT_SAVE_DELAY_MS)
        self._save_timer.timeout.connect(self._report_prompt)
        self.prompt_input.textChanged.connect(self._start_save_timer)

        layout = QVBoxLayout(self)
        layout.addWidget(
            self.open_console_button, alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
        )
        layout.addWidget(self.prompt_label)
        layout.addWidget(self.prompt_input, stretch=1)  # capped at half the panel in resizeEvent
        layout.addStretch()
        self.show_prompt("", "")

    def show_prompt(self, feature_name: str, prompt: str) -> None:
        """Show the prompt label for `feature_name` and put `prompt` in the text box,
        dropping any pending edit and without reporting a change."""
        self._save_timer.stop()
        self._label_text = f"Prompt for '/devpipe-create {feature_name}':"
        self._show_pending(False)
        self.prompt_input.blockSignals(True)
        try:
            self.prompt_input.setPlainText(prompt)
        finally:
            self.prompt_input.blockSignals(False)

    def flush_prompt(self) -> None:
        """Report a pending edit now instead of waiting for the delay; no-op when none is pending."""
        if self._save_timer.isActive():
            self._save_timer.stop()
            self._report_prompt()

    def _start_save_timer(self) -> None:
        self._save_timer.start()
        self._show_pending(True)

    def _report_prompt(self) -> None:
        self._show_pending(False)
        self.prompt_changed.emit(self.prompt_input.toPlainText())

    def _show_pending(self, pending: bool) -> None:
        self.prompt_label.setText(self._label_text + (PENDING_MARK if pending else ""))

    def hideEvent(self, event: QHideEvent) -> None:
        # Panel switch, tab close or window close: do not lose the last edit.
        self.flush_prompt()
        super().hideEvent(event)

    def resizeEvent(self, event: QResizeEvent) -> None:
        # A maximum (not a fixed) height, so the panel can still shrink.
        self.prompt_input.setMaximumHeight(event.size().height() // 2)
        super().resizeEvent(event)

    def _console_folder(self) -> Path | None:
        paths = self._worktrees()
        return paths[0] if paths else None

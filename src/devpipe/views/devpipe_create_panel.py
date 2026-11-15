"""Devpipe create panel: opened by "Start Pipeline" on the start panel."""

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QHideEvent, QResizeEvent, QShowEvent
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from devpipe.models.terminal import TerminalError, TerminalId
from devpipe.services.control_files_service import ControlFilesService
from devpipe.services.terminal_service import TerminalService
from devpipe.views.open_console_button import OpenConsoleButton

PROMPT_SAVE_DELAY_MS = 5000
"""Quiet time after the last edit of the prompt before it is reported for saving."""

PENDING_MARK = " *"
"""Appended to the prompt label while an edit is waiting to be reported."""

SEND_PROMPT_TEXT = "Send prompt to terminal"
SEND_PROMPT_ERROR_TITLE = "Cannot send prompt"
REFRESH_TEXT = "Refresh"
TITLE_TEXT = "Create Feature Spec"


def create_command(feature_name: str, prompt: str) -> str:
    """The text typed into the terminal: the '/devpipe-create' command, then the prompt."""
    return f"/devpipe-create {feature_name} \n {prompt}"


class DevpipeCreatePanel(QWidget):
    console_opened = Signal(object)  # forwarded from open_console_button: the TerminalId
    # The prompt text, PROMPT_SAVE_DELAY_MS after the user stopped typing
    # (or at once when the panel is hidden with an edit still pending).
    prompt_changed = Signal(str)

    def __init__(
        self,
        terminals: TerminalService,
        worktrees: Callable[[], list[Path]],
        feature_name: Callable[[], str],
        saved_prompt: Callable[[], str],
        tab_terminal: Callable[[], TerminalId | None],
        control_files: ControlFilesService,
        open_plan_panel: Callable[[], None],
    ) -> None:
        """`worktrees` returns the tab's current worktree list; it is read only when
        a console is opened, which starts in the first entry.

        `feature_name` and `saved_prompt` return the tab's feature name and its kept
        prompt; they are read each time the panel is shown.

        `tab_terminal` returns the tab's terminal (None when it has none); the send
        button is enabled only while it is open, checked when the panel is shown
        and after each click of the console button.

        `control_files` tells whether the feature spec (`.devpipe/<feature-name>/feature-spec.md`)
        exists in the first worktree; refresh_state checks it and, when it exists, calls
        `open_plan_panel` (deferred to the event loop, see refresh_state)."""
        super().__init__()
        self._worktrees = worktrees
        self._feature_name = feature_name
        self._saved_prompt = saved_prompt
        self._terminals = terminals
        self._tab_terminal = tab_terminal
        self._control_files = control_files
        self._open_plan_panel = open_plan_panel
        self.open_console_button = OpenConsoleButton(terminals, self._console_folder)
        self.open_console_button.console_opened.connect(self.console_opened)
        # Connected after the button's own handler, so the tab already knows the new console.
        self.open_console_button.clicked.connect(self._update_send_button)
        self.refresh_button = QPushButton(REFRESH_TEXT)
        self.refresh_button.clicked.connect(lambda: self.refresh_state())  # drop the `checked` argument

        self.title_label = QLabel(TITLE_TEXT)
        title_font = self.title_label.font()
        title_font.setPointSize(16)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

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

        self.send_prompt_button = QPushButton(SEND_PROMPT_TEXT)
        self.send_prompt_button.clicked.connect(lambda: self.send_prompt())  # drop the `checked` argument

        buttons = QHBoxLayout()
        buttons.addWidget(self.open_console_button, alignment=Qt.AlignmentFlag.AlignTop)
        buttons.addWidget(self.refresh_button, alignment=Qt.AlignmentFlag.AlignTop)
        buttons.addStretch()
        layout = QVBoxLayout(self)
        layout.addWidget(self.title_label)
        layout.addLayout(buttons)
        layout.addWidget(self.prompt_label)
        layout.addWidget(self.prompt_input, stretch=1)  # capped at half the panel in resizeEvent
        layout.addWidget(self.send_prompt_button, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addStretch()
        self._load_saved_prompt()
        self._update_send_button()

    def refresh_state(self) -> None:
        """Bring the panel up to date with the tab: the kept prompt (see
        _load_saved_prompt), the send button, and the feature spec, calling
        open_plan_panel when `<first worktree>/.devpipe/<feature-name>/feature-spec.md`
        exists. Called on show (not on a window restore) and by the Refresh button.

        A pending prompt edit is reported first, so a refresh never drops it."""
        self.flush_prompt()
        self._load_saved_prompt()
        self._update_send_button()
        folder = self._console_folder()
        if folder is not None and self._control_files.feature_spec_exists(folder, self._feature_name()):
            # Deferred: on show, the stack is still switching to this panel.
            QTimer.singleShot(0, self._open_plan_panel)

    def _load_saved_prompt(self) -> None:
        """Show the label for the tab's feature name and put the tab's kept prompt in
        the text box, dropping any pending edit and without reporting a change. The
        text box is left alone when it already holds that prompt (keeps the cursor)."""
        self._save_timer.stop()
        self._label_text = f"Prompt for '/devpipe-create {self._feature_name()}':"
        self._show_pending(False)
        prompt = self._saved_prompt()
        if self.prompt_input.toPlainText() == prompt:
            return
        self.prompt_input.blockSignals(True)
        try:
            self.prompt_input.setPlainText(prompt)
        finally:
            self.prompt_input.blockSignals(False)

    def send_prompt(self) -> None:
        """Bring the tab's terminal to the foreground and type the '/devpipe-create'
        command and the prompt into it, without pressing Enter at the end. Every
        line break is typed as Ctrl+J (new line, not submit), so the agent gets one multi-line message.

        On failure shows a warning; the button state is refreshed either way."""
        terminal = self._open_tab_terminal()
        if terminal is not None:
            text = create_command(self._feature_name(), self.prompt_input.toPlainText())
            try:
                self._terminals.send_to_console(terminal, text, enter=False, soft_newlines=True)
            except TerminalError as error:
                QMessageBox.warning(self, SEND_PROMPT_ERROR_TITLE, error.message)
        self._update_send_button()

    def _open_tab_terminal(self) -> TerminalId | None:
        """The tab's terminal while it is open, else None."""
        terminal = self._tab_terminal()
        if terminal is None or not self._terminals.is_console_open(terminal):
            return None
        return terminal

    def _update_send_button(self) -> None:
        self.send_prompt_button.setEnabled(self._open_tab_terminal() is not None)

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

    def showEvent(self, event: QShowEvent) -> None:
        # Panel switch or tab switch (not a window restore): refresh everything.
        # No edit can be pending here; hideEvent reported it.
        if not event.spontaneous():
            self.refresh_state()
        else:
            self._update_send_button()  # window restore: the terminal may have been closed
        super().showEvent(event)

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

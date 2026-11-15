"""Open interactive terminal windows and type text into them (no Qt)."""

from pathlib import Path
from typing import Protocol

from devpipe.models.terminal import TerminalError, TerminalId

FOLDER_MISSING_MESSAGE = "folder does not exist"
NO_TERMINAL_MESSAGE = "no open terminal"


class Terminals(Protocol):
    """Opens terminal windows and types into them (implemented per OS in the
    infrastructure layer). The windows stay fully usable by the user."""

    def open(self, cwd: Path) -> TerminalId:
        """Open a new, visible, interactive shell window started in `cwd`.
        Raises TerminalError (only) when it cannot be opened."""
        ...

    def send_text(
        self, terminal: TerminalId, text: str, enter: bool = True, *, soft_newlines: bool = False
    ) -> None:
        """Type `text` into the terminal as if the user typed it, then press Enter
        when `enter` is True. A "\\n" in `text` is typed as Enter, or as Ctrl+J
        when `soft_newlines` (a new line in the input, not a submit). Works for shell
        commands and for answering prompts of the running program. Raises
        TerminalError (only) when the terminal is closed or cannot be written to."""
        ...

    def is_open(self, terminal: TerminalId) -> bool:
        """The terminal's shell is still running (False once the user closed the window)."""
        ...

    def close(self, terminal: TerminalId) -> None:
        """End the terminal's shell, closing its window. No-op when already closed."""
        ...

    def bring_to_front(self, terminal: TerminalId) -> None:
        """Restore the terminal's window when minimized and make it the foreground
        window of the system. Raises TerminalError (only) when the terminal is
        closed or its window cannot be found."""
        ...


class TerminalService:
    """Keeps at most one terminal per key (e.g. one per pipeline tab), and at most
    one console per folder."""

    def __init__(self, terminals: Terminals) -> None:
        self._terminals = terminals
        self._by_key: dict[str, TerminalId] = {}
        self._consoles: dict[Path, TerminalId] = {}  # by resolved folder

    def open(self, key: str, cwd: Path) -> bool:
        """Open a terminal for `key` in `cwd`, unless `key` already has an open one.
        True when a new window was opened. Raises TerminalError when `cwd` is not
        an existing folder or the terminal cannot be opened."""
        if self.is_open(key):
            return False
        if not cwd.is_dir():
            raise TerminalError(FOLDER_MISSING_MESSAGE)
        self._by_key[key] = self._terminals.open(cwd)
        return True

    def open_console(self, cwd: Path) -> TerminalId:
        """Show a console in `cwd` and return its id. When a console opened by an
        earlier call for the same folder is still open, its window is brought to
        the foreground; otherwise a new terminal that no key owns is opened in `cwd`.
        Raises TerminalError when `cwd` is not an existing folder, or the terminal
        cannot be opened or brought to the foreground."""
        if not cwd.is_dir():
            raise TerminalError(FOLDER_MISSING_MESSAGE)
        folder = cwd.resolve()
        terminal = self._consoles.get(folder)
        if terminal is not None and self._terminals.is_open(terminal):
            self._terminals.bring_to_front(terminal)
            return terminal
        terminal = self._terminals.open(cwd)
        self._consoles[folder] = terminal
        return terminal

    def is_console_open(self, terminal: TerminalId) -> bool:
        """The terminal (e.g. one returned by open_console) is still open."""
        return self._terminals.is_open(terminal)

    def send_to_console(
        self, terminal: TerminalId, text: str, enter: bool = True, *, soft_newlines: bool = False
    ) -> None:
        """Bring the terminal's window to the foreground, then type `text` into it
        (then Enter when `enter`; `soft_newlines` as in Terminals.send_text).
        Raises TerminalError when the terminal is closed or either step fails."""
        if not self._terminals.is_open(terminal):
            raise TerminalError(NO_TERMINAL_MESSAGE)
        self._terminals.bring_to_front(terminal)
        self._terminals.send_text(terminal, text, enter, soft_newlines=soft_newlines)

    def send(self, key: str, text: str, enter: bool = True) -> None:
        """Type `text` (then Enter when `enter`) into the terminal of `key`.
        Raises TerminalError when `key` has no open terminal or the write fails."""
        if not self.is_open(key):
            raise TerminalError(NO_TERMINAL_MESSAGE)
        self._terminals.send_text(self._by_key[key], text, enter)

    def is_open(self, key: str) -> bool:
        """`key` has a terminal and the user has not closed it. Forgets closed ones."""
        terminal = self._by_key.get(key)
        if terminal is None:
            return False
        if self._terminals.is_open(terminal):
            return True
        del self._by_key[key]
        return False

    def close(self, key: str) -> None:
        """Close the terminal of `key`, if any."""
        terminal = self._by_key.pop(key, None)
        if terminal is not None:
            self._terminals.close(terminal)

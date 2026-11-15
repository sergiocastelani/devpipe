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

    def send_text(self, terminal: TerminalId, text: str, enter: bool = True) -> None:
        """Type `text` into the terminal as if the user typed it, then press Enter
        when `enter` is True. A "\\n" in `text` is typed as Enter. Works for shell
        commands and for answering prompts of the running program. Raises
        TerminalError (only) when the terminal is closed or cannot be written to."""
        ...

    def is_open(self, terminal: TerminalId) -> bool:
        """The terminal's shell is still running (False once the user closed the window)."""
        ...

    def close(self, terminal: TerminalId) -> None:
        """End the terminal's shell, closing its window. No-op when already closed."""
        ...


class TerminalService:
    """Keeps at most one terminal per key (e.g. one per pipeline tab)."""

    def __init__(self, terminals: Terminals) -> None:
        self._terminals = terminals
        self._by_key: dict[str, TerminalId] = {}

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
        """Open a new terminal in `cwd` that no key owns (every call opens another
        window; the service does not track it) and return its id.
        Raises TerminalError when `cwd` is not an existing folder or the terminal
        cannot be opened."""
        if not cwd.is_dir():
            raise TerminalError(FOLDER_MISSING_MESSAGE)
        return self._terminals.open(cwd)

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

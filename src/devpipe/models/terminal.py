"""Terminal window handles and errors (no Qt, no I/O)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class TerminalId:
    """Opaque handle to one terminal window opened by a Terminals implementation.

    Only the implementation that issued it knows what `value` means.
    """

    value: str


class TerminalError(Exception):
    """A terminal could not be opened or written to; str(error) is the readable message."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message

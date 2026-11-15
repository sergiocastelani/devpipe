"""Runtime information of one pipeline tab, kept in memory for the app session only.

Unlike TabState, nothing here is ever written to the tab state file.
"""

from dataclasses import dataclass

from devpipe.models.terminal import TerminalId


@dataclass
class TabSession:
    last_console: TerminalId | None = None
    """Terminal id of the last console opened from the tab, if any."""

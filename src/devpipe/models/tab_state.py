"""State of one pipeline tab, as kept in its tab state file."""

import enum
import re
from dataclasses import dataclass, field
from pathlib import Path

STATE_FILE_VERSION = 2
"""The tab state file format version this app writes (it also reads version 1)."""

_FEATURE_NAME_PATTERN = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")


class Panel(enum.Enum):
    """Panel ids of a tab; the values are the `active_panel` strings of the file.

    Only the panels in PERSISTED_PANELS are ever read from or written to a file.
    """

    START = "start"
    NEW_WORKTREE = "new-worktree"


PERSISTED_PANELS: frozenset[Panel] = frozenset({Panel.START})
"""The panels a tab state file may hold as `active_panel`."""


@dataclass
class TabState:
    feature_name: str
    active_panel: Panel = Panel.START
    worktrees: list[Path] = field(default_factory=list)
    """Worktree folders of the tab, in saved order (absolute when created by the app)."""


def is_valid_feature_name(name: str) -> bool:
    """True when `name` matches `^[a-z0-9]+(-[a-z0-9]+)*$` (so never for "")."""
    return _FEATURE_NAME_PATTERN.fullmatch(name) is not None


class TabStateError(Exception):
    """A tab state file could not be read or written."""

    def __init__(self, path: Path, reason: str) -> None:
        super().__init__(f"{path}: {reason}")
        self.path = path
        self.reason = reason

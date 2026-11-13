"""State of one pipeline tab, as kept in its tab state file."""

import enum
import re
from dataclasses import dataclass
from pathlib import Path

STATE_FILE_VERSION = 1
"""The only tab state file format version this app reads and writes."""

_FEATURE_NAME_PATTERN = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")


class Panel(enum.Enum):
    """Panel ids of a tab; the values are the `active_panel` strings of the file."""

    START = "start"


@dataclass
class TabState:
    feature_name: str
    active_panel: Panel = Panel.START


def is_valid_feature_name(name: str) -> bool:
    """True when `name` matches `^[a-z0-9]+(-[a-z0-9]+)*$` (so never for "")."""
    return _FEATURE_NAME_PATTERN.fullmatch(name) is not None


class TabStateError(Exception):
    """A tab state file could not be read or written."""

    def __init__(self, path: Path, reason: str) -> None:
        super().__init__(f"{path}: {reason}")
        self.path = path
        self.reason = reason

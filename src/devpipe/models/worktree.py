"""Worktree creation requests and results (no Qt, no I/O)."""

from dataclasses import dataclass
from pathlib import Path

DEFAULT_FOLDER_NAME = "worktree-{feature_name}"
# Characters Windows does not allow in a file name (plus both path separators).
_FORBIDDEN_FOLDER_CHARS = frozenset('<>:"/\\|?*')


def default_folder_name(feature_name: str) -> str:
    """The worktree folder name a new group is pre-filled with: "worktree-<feature name>"."""
    return DEFAULT_FOLDER_NAME.format(feature_name=feature_name)


def is_valid_folder_name(name: str) -> bool:
    """`name` is one usable folder name: non-empty, not "." or "..", no path separator
    or character Windows forbids, no control character, no trailing dot or space."""
    return (
        bool(name)
        and name not in (".", "..")
        and not any(char in _FORBIDDEN_FOLDER_CHARS or ord(char) < 32 for char in name)
        and not name.endswith((".", " "))
    )


@dataclass(frozen=True)
class WorktreeRequest:
    """One (source project folder, worktree parent folder, worktree folder name), as entered."""

    source: Path
    parent: Path
    folder_name: str

    def target(self) -> Path:
        """The worktree folder this request creates: `(parent / folder_name).resolve()`."""
        return (self.parent / self.folder_name).resolve()


@dataclass(frozen=True)
class WorktreeResult:
    """Outcome of one request.

    `target` is always `request.target()`, on success
    and on failure. On success it is the created worktree folder.
    `error` is None on success, else a readable message.
    """

    request: WorktreeRequest
    target: Path
    error: str | None

    @property
    def ok(self) -> bool:
        return self.error is None


@dataclass(frozen=True)
class PreRunState:
    """What existed before a run, for one request; decides what recovery may delete.

    `target` is `request.target()`, the same folder the run would create.
    """

    request: WorktreeRequest
    target: Path
    target_existed: bool  # a file or folder was at `target` before the run
    branch_existed: bool  # the branch existed in the source repository, or could not be checked


class GitWorktreeError(Exception):
    """A git worktree could not be created; str(error) is the readable message."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message

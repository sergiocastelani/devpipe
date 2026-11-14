"""Worktree creation requests and results (no Qt, no I/O)."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class WorktreeRequest:
    """One (source project folder, worktree parent folder) pair, as entered."""

    source: Path
    parent: Path


@dataclass(frozen=True)
class WorktreeResult:
    """Outcome of one request.

    `target` is always `(request.parent / feature_name).resolve()`, on success
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

    `target` is `(request.parent / feature_name).resolve()`, the same folder the run
    would create.
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

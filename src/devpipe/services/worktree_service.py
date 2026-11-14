"""Create git worktrees named after a feature, and merge their paths (no Qt)."""

from pathlib import Path
from typing import Protocol

from devpipe.models.tab_state import is_valid_feature_name
from devpipe.models.worktree import GitWorktreeError, WorktreeRequest, WorktreeResult
from devpipe.services.paths import same_file

SOURCE_MISSING_MESSAGE = "source folder does not exist"
PARENT_MISSING_MESSAGE = "parent folder does not exist"
TARGET_EXISTS_MESSAGE = "target folder already exists"


class GitWorktrees(Protocol):
    """Creates git worktrees (implemented in the infrastructure layer)."""

    def add_worktree(self, source: Path, branch: str, target: Path) -> None:
        """Add a worktree of the repository at `source` at `target`, on a new
        branch `branch` started from the source's default branch.

        Checks that `source` is a git repository and resolves the default branch
        and the start point without fetching. Raises GitWorktreeError (only) on
        any failure, including a missing git executable.
        """
        ...


class WorktreeService:
    """Creates one worktree per request and merges worktree path lists."""

    def __init__(self, git: GitWorktrees) -> None:
        self._git = git

    def create_worktrees(
        self, feature_name: str, requests: list[WorktreeRequest]
    ) -> list[WorktreeResult]:
        """One result per request, in the same order. Requests are processed
        one at a time; the call blocks until all are done.

        Raises ValueError (before processing any request) when `feature_name`
        is not a valid feature slug. Never raises for the failure of one request.
        """
        if not is_valid_feature_name(feature_name):
            raise ValueError(f"invalid feature name: {feature_name!r}")
        return [self._create_one(feature_name, request) for request in requests]

    def merge_paths(self, existing: list[Path], new: list[Path]) -> list[Path]:
        """A new list: `existing` (unchanged, in order) followed by each path of
        `new` that is not already in it (by same_file, also among earlier new
        paths). The inputs are not modified."""
        merged = list(existing)
        for path in new:
            if not any(same_file(path, kept) for kept in merged):
                merged.append(path)
        return merged

    def _create_one(self, feature_name: str, request: WorktreeRequest) -> WorktreeResult:
        """Precheck, then call git; turn a GitWorktreeError into the result's error."""
        target = (request.parent / feature_name).resolve()
        error = self._precheck(request, target)
        if error is None:
            try:
                self._git.add_worktree(request.source.resolve(), feature_name, target)
            except GitWorktreeError as exc:
                error = str(exc)
        return WorktreeResult(request, target, error)

    @staticmethod
    def _precheck(request: WorktreeRequest, target: Path) -> str | None:
        """The first failing check's message, or None when all checks pass."""
        if not request.source.is_dir():
            return SOURCE_MISSING_MESSAGE
        if not request.parent.is_dir():
            return PARENT_MISSING_MESSAGE
        if target.exists():
            return TARGET_EXISTS_MESSAGE
        return None

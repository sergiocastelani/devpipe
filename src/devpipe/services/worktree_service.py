"""Create git worktrees named after a feature, and merge their paths (no Qt)."""

from pathlib import Path
from typing import Protocol

from devpipe.models.tab_state import is_valid_feature_name
from devpipe.models.worktree import (
    GitWorktreeError,
    PreRunState,
    WorktreeRequest,
    WorktreeResult,
)
from devpipe.services.paths import same_file

SOURCE_MISSING_MESSAGE = "source folder does not exist"
PARENT_MISSING_MESSAGE = "parent folder does not exist"
TARGET_EXISTS_MESSAGE = "target folder already exists"
CLEANED_UP_MESSAGE = "unexpected error: {error}; cleaned up"
CLEANUP_FAILED_MESSAGE = "unexpected error: {error}; cleanup failed: {cleanup_error}"


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

    def branch_exists(self, source: Path, branch: str) -> bool:
        """The local branch `branch` exists in the repository of `source`.
        Raises GitWorktreeError when it cannot be checked (not a repository, git not found, ...)."""
        ...

    def is_worktree(self, source: Path, branch: str, target: Path) -> bool:
        """`target` is an existing folder registered as a worktree of the repository of
        `source` and checked out on `branch`. Raises GitWorktreeError when it cannot be checked."""
        ...

    def remove_worktree(self, source: Path, branch: str, target: Path, delete_branch: bool) -> None:
        """Undo what a failed worktree creation may have left: remove the registered
        worktree at `target` if any, delete the `target` folder if it still exists, and,
        when `delete_branch` is True, delete `branch` unless a remaining worktree has it
        checked out. Missing pieces are skipped. Raises GitWorktreeError on any failure."""
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
        self._require_valid_feature_name(feature_name)
        return [self._create_one(feature_name, request) for request in requests]

    def snapshot(self, feature_name: str, requests: list[WorktreeRequest]) -> list[PreRunState]:
        """One PreRunState per request, in order, taken before a run.

        Raises ValueError for an invalid feature name (before any git call). Never raises
        for a per-request problem: a GitWorktreeError from branch_exists counts as
        branch_existed=True, so recovery never deletes a branch it could not check.
        """
        self._require_valid_feature_name(feature_name)
        states = []
        for request in requests:
            target = (request.parent / feature_name).resolve()
            try:
                branch_existed = self._git.branch_exists(request.source.resolve(), feature_name)
            except GitWorktreeError:
                branch_existed = True
            states.append(PreRunState(request, target, target.exists(), branch_existed))
        return states

    def recover(
        self, feature_name: str, snapshot: list[PreRunState], error: str
    ) -> list[WorktreeResult]:
        """Results for a run that stopped with the unexpected error `error`, one per
        snapshot entry, in order; cleans up what the run may have left half-done.

        Raises ValueError for an invalid feature name. Never raises for a per-request
        problem (GitWorktreeError); any other exception propagates.
        """
        self._require_valid_feature_name(feature_name)
        verified = [
            not entry.target_existed and self._is_verified(feature_name, entry)
            for entry in snapshot
        ]
        verified_targets = [entry.target for entry, ok in zip(snapshot, verified) if ok]
        results = []
        for entry, is_verified in zip(snapshot, verified):
            if is_verified:
                results.append(WorktreeResult(entry.request, entry.target, None))
            elif entry.target_existed or any(
                same_file(entry.target, kept) for kept in verified_targets
            ):
                results.append(WorktreeResult(entry.request, entry.target, TARGET_EXISTS_MESSAGE))
            else:
                results.append(self._clean_up(feature_name, entry, error))
        return results

    def merge_paths(self, existing: list[Path], new: list[Path]) -> list[Path]:
        """A new list: `existing` (unchanged, in order) followed by each path of
        `new` that is not already in it (by same_file, also among earlier new
        paths). The inputs are not modified."""
        merged = list(existing)
        for path in new:
            if not any(same_file(path, kept) for kept in merged):
                merged.append(path)
        return merged

    @staticmethod
    def _require_valid_feature_name(feature_name: str) -> None:
        """Raise ValueError(f"invalid feature name: {feature_name!r}") for a non-slug name."""
        if not is_valid_feature_name(feature_name):
            raise ValueError(f"invalid feature name: {feature_name!r}")

    def _is_verified(self, feature_name: str, entry: PreRunState) -> bool:
        """is_worktree(source.resolve(), feature_name, target); a GitWorktreeError counts as False."""
        try:
            return self._git.is_worktree(entry.request.source.resolve(), feature_name, entry.target)
        except GitWorktreeError:
            return False

    def _clean_up(self, feature_name: str, entry: PreRunState, error: str) -> WorktreeResult:
        """remove_worktree(...) and the failed result that reports it."""
        try:
            self._git.remove_worktree(
                entry.request.source.resolve(),
                feature_name,
                entry.target,
                delete_branch=not entry.branch_existed,
            )
        except GitWorktreeError as exc:
            message = CLEANUP_FAILED_MESSAGE.format(error=error, cleanup_error=str(exc))
        else:
            message = CLEANED_UP_MESSAGE.format(error=error)
        return WorktreeResult(entry.request, entry.target, message)

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

"""Create git worktrees by running the git executable (no Qt, no shell)."""

import subprocess
from pathlib import Path

from devpipe.models.worktree import GitWorktreeError

GIT_EXECUTABLE = "git"
REMOTE = "origin"
FALLBACK_DEFAULT_BRANCHES = ("main", "master")

NOT_A_REPOSITORY_MESSAGE = "not a git repository"
DEFAULT_BRANCH_NOT_FOUND_MESSAGE = "default branch not found"
GIT_NOT_FOUND_MESSAGE = "git not found"


class SubprocessGitWorktrees:
    """The real GitWorktrees: runs `git -C <source> ...` with argument lists."""

    def add_worktree(self, source: Path, branch: str, target: Path) -> None:
        """See GitWorktrees.add_worktree. Raises GitWorktreeError (only)."""
        self._check_repository(source)
        start_point = self._start_point(source, self._default_branch(source))
        completed = self._run(
            source, "worktree", "add", "-b", branch, str(target), start_point
        )
        if completed.returncode != 0:
            message = completed.stderr.strip()
            raise GitWorktreeError(
                message or f"git exited with code {completed.returncode}"
            )

    def _check_repository(self, source: Path) -> None:
        """Raise GitWorktreeError(NOT_A_REPOSITORY_MESSAGE) unless
        `git rev-parse --git-dir` succeeds in `source`. A folder inside a
        repository's work tree also passes (its enclosing repository is used)."""
        if self._run(source, "rev-parse", "--git-dir").returncode != 0:
            raise GitWorktreeError(NOT_A_REPOSITORY_MESSAGE)

    def _default_branch(self, source: Path) -> str:
        """Target of refs/remotes/origin/HEAD without the "origin/" prefix,
        else the first of FALLBACK_DEFAULT_BRANCHES that exists as a local
        branch. Raises GitWorktreeError(DEFAULT_BRANCH_NOT_FOUND_MESSAGE)."""
        completed = self._run(
            source, "symbolic-ref", "--quiet", "--short", f"refs/remotes/{REMOTE}/HEAD"
        )
        name = completed.stdout.strip()
        if completed.returncode == 0 and name:
            return name.removeprefix(f"{REMOTE}/")
        for fallback in FALLBACK_DEFAULT_BRANCHES:
            if self._ref_exists(source, f"refs/heads/{fallback}"):
                return fallback
        raise GitWorktreeError(DEFAULT_BRANCH_NOT_FOUND_MESSAGE)

    def _start_point(self, source: Path, name: str) -> str:
        """`name` when refs/heads/<name> exists, else `origin/<name>` when
        refs/remotes/origin/<name> exists. Raises
        GitWorktreeError(DEFAULT_BRANCH_NOT_FOUND_MESSAGE)."""
        if self._ref_exists(source, f"refs/heads/{name}"):
            return name
        if self._ref_exists(source, f"refs/remotes/{REMOTE}/{name}"):
            return f"{REMOTE}/{name}"
        raise GitWorktreeError(DEFAULT_BRANCH_NOT_FOUND_MESSAGE)

    def _ref_exists(self, source: Path, ref: str) -> bool:
        """`git rev-parse --verify --quiet <ref>` exits 0."""
        return self._run(source, "rev-parse", "--verify", "--quiet", ref).returncode == 0

    def _run(self, source: Path, *args: str) -> subprocess.CompletedProcess[str]:
        """Run git in `source`; never raises for a non-zero exit code."""
        cmd = [GIT_EXECUTABLE, "-C", str(source), *args]
        try:
            return subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
        except FileNotFoundError as exc:
            raise GitWorktreeError(GIT_NOT_FOUND_MESSAGE) from exc
        except OSError as exc:
            raise GitWorktreeError(f"cannot run git: {exc.strerror or exc}") from exc

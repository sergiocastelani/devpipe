"""Create git worktrees by running the git executable (no Qt, no shell)."""

import os
import shutil
import stat
import subprocess
from pathlib import Path

from devpipe.models.worktree import GitWorktreeError

GIT_EXECUTABLE = "git"
REMOTE = "origin"
FALLBACK_DEFAULT_BRANCHES = ("main", "master")

NOT_A_REPOSITORY_MESSAGE = "not a git repository"
DEFAULT_BRANCH_NOT_FOUND_MESSAGE = "default branch not found"
GIT_NOT_FOUND_MESSAGE = "git not found"
BRANCH_REF = "refs/heads/{branch}"
CANNOT_DELETE_FOLDER_MESSAGE = "cannot delete folder: {reason}"


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
            raise GitWorktreeError(self._failure_message(completed))

    def branch_exists(self, source: Path, branch: str) -> bool:
        """See GitWorktrees.branch_exists."""
        self._check_repository(source)
        return self._ref_exists(source, BRANCH_REF.format(branch=branch))

    def is_worktree(self, source: Path, branch: str, target: Path) -> bool:
        """See GitWorktrees.is_worktree."""
        if not target.is_dir():
            return False
        ref = BRANCH_REF.format(branch=branch)
        return any(
            _same_folder(folder, target) and entry_ref == ref
            for folder, entry_ref in self._worktree_entries(source)
        )

    def remove_worktree(self, source: Path, branch: str, target: Path, delete_branch: bool) -> None:
        """See GitWorktrees.remove_worktree."""
        entries = self._worktree_entries(source)
        if any(_same_folder(folder, target) for folder, _ref in entries):
            self._run_checked(source, "worktree", "remove", "--force", str(target))
        self._run_checked(source, "worktree", "prune")
        if target.is_dir():
            try:
                shutil.rmtree(target, onexc=_make_writable_and_retry)
            except OSError as exc:
                raise GitWorktreeError(
                    CANNOT_DELETE_FOLDER_MESSAGE.format(reason=exc.strerror or exc)
                ) from exc
        ref = BRANCH_REF.format(branch=branch)
        if (
            delete_branch
            and self._ref_exists(source, ref)
            and not any(entry_ref == ref for _folder, entry_ref in self._worktree_entries(source))
        ):
            self._run_checked(source, "branch", "-D", branch)

    def _worktree_entries(self, source: Path) -> list[tuple[Path, str | None]]:
        """(folder, checked-out ref or None when detached) of every registered worktree,
        from `git worktree list --porcelain`. Checks the repository first."""
        self._check_repository(source)
        completed = self._run_checked(source, "worktree", "list", "--porcelain")
        entries: list[tuple[Path, str | None]] = []
        for block in completed.stdout.split("\n\n"):  # text mode: newlines are "\n"
            folder: Path | None = None
            ref: str | None = None
            for line in block.splitlines():
                if line.startswith("worktree "):
                    folder = Path(line.removeprefix("worktree "))
                elif line.startswith("branch "):
                    ref = line.removeprefix("branch ")
            if folder is not None:
                entries.append((folder, ref))
        return entries

    def _run_checked(self, source: Path, *args: str) -> subprocess.CompletedProcess[str]:
        """_run, then raise GitWorktreeError(_failure_message(completed)) on a non-zero exit."""
        completed = self._run(source, *args)
        if completed.returncode != 0:
            raise GitWorktreeError(self._failure_message(completed))
        return completed

    @staticmethod
    def _failure_message(completed: subprocess.CompletedProcess[str]) -> str:
        """Stripped stderr, or f"git exited with code {completed.returncode}" when empty."""
        return completed.stderr.strip() or f"git exited with code {completed.returncode}"

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


def _same_folder(a: Path, b: Path) -> bool:
    """Same folder after resolve(), ignoring case on Windows (os.path.normcase)."""
    return os.path.normcase(a.resolve()) == os.path.normcase(b.resolve())


def _make_writable_and_retry(function, path, _exc) -> None:
    """shutil.rmtree onexc handler: clear the read-only flag and retry (Windows)."""
    os.chmod(path, stat.S_IWRITE)
    function(path)

import shutil
import threading
from collections.abc import Callable
from pathlib import Path

import pytest

from devpipe.models.worktree import GitWorktreeError
from devpipe.persistence.config_repository import ConfigRepository
from devpipe.persistence.tab_state_repository import TabStateRepository
from devpipe.services.session_service import SessionService
from devpipe.services.tab_state_service import TabStateService
from devpipe.services.window_state_service import WindowStateService
from devpipe.services.worktree_service import WorktreeService
from devpipe.views.main_window import MainWindow

GATE_TIMEOUT_S = 5  # a gated add_worktree gives up after this, so a failing test never hangs


class FakeGitWorktrees:
    """In-memory git for view tests, configurable per resolved target.

    add_worktree waits for `gate` when set, records the call, raises failures[target]
    when present (a GitWorktreeError is a normal failure, any other exception an
    unexpected one), else creates the target folder and registers the worktree.
    """

    def __init__(self) -> None:
        self.failures: dict[Path, Exception] = {}
        self.gate: threading.Event | None = None
        self.branch_check_error: Exception | None = None  # raised by branch_exists
        self.remove_error: Exception | None = None  # raised by remove_worktree
        self.calls: list[tuple[Path, str, Path]] = []  # add_worktree calls
        self.removed: list[tuple[Path, str, Path, bool]] = []
        self.branches: set[tuple[Path, str]] = set()  # (source, branch)
        self.worktrees: set[tuple[Path, str, Path]] = set()  # (source, branch, target)

    def add_worktree(self, source, branch, target):
        if self.gate is not None and not self.gate.wait(GATE_TIMEOUT_S):
            raise GitWorktreeError("gate timeout")
        self.calls.append((source, branch, target))
        if target in self.failures:
            raise self.failures[target]
        self.branches.add((source, branch))
        self.worktrees.add((source, branch, target))
        target.mkdir()

    def branch_exists(self, source, branch):
        if self.branch_check_error is not None:
            raise self.branch_check_error
        return (source, branch) in self.branches

    def is_worktree(self, source, branch, target):
        return target.is_dir() and (source, branch, target) in self.worktrees

    def remove_worktree(self, source, branch, target, delete_branch):
        if self.remove_error is not None:
            raise self.remove_error
        self.removed.append((source, branch, target, delete_branch))
        self.worktrees.discard((source, branch, target))
        if target.is_dir():
            shutil.rmtree(target)
        if delete_branch:
            self.branches.discard((source, branch))


@pytest.fixture
def tab_states() -> TabStateService:
    return TabStateService(TabStateRepository())


@pytest.fixture
def fake_git() -> FakeGitWorktrees:
    return FakeGitWorktrees()


@pytest.fixture
def worktree_service(fake_git) -> WorktreeService:
    return WorktreeService(fake_git)


@pytest.fixture
def make_window(qtbot, tmp_path, tab_states, worktree_service) -> Callable[[], MainWindow]:
    """Return a callable building a new MainWindow with real repositories on
    tmp_path / "config.json" (same file on every call: a second call simulates a
    restart). Each window is registered with qtbot.addWidget."""

    def make() -> MainWindow:
        config = ConfigRepository(tmp_path / "config.json")
        window = MainWindow(
            WindowStateService(config), tab_states, SessionService(config), worktree_service
        )
        qtbot.addWidget(window)
        return window

    return make

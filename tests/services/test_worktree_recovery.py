from pathlib import Path

import pytest

from devpipe.models.worktree import GitWorktreeError, PreRunState, WorktreeRequest
from devpipe.services.worktree_service import TARGET_EXISTS_MESSAGE, WorktreeService

FEATURE = "feat-x"
E = "RuntimeError: boom"
CLEANED_UP = "unexpected error: RuntimeError: boom; cleaned up"


class RecordingGit:
    """Recording GitWorktrees for snapshot / recover; add_worktree is never used."""

    def __init__(self):
        self.calls = []  # ("branch_exists" | "is_worktree" | "remove_worktree", *args)
        self.branches: set[Path] = set()  # sources whose branch exists
        self.branch_errors: set[Path] = set()  # branch_exists raises GitWorktreeError("no repo")
        self.worktrees: set[tuple[Path, Path]] = set()  # (source, target) that is_worktree reports
        self.worktree_errors: set[Path] = set()  # targets for which is_worktree raises GitWorktreeError
        self.remove_errors: dict[Path, Exception] = {}  # target -> exception raised by remove_worktree

    def add_worktree(self, source, branch, target):
        raise AssertionError("add_worktree is not used by snapshot / recover")

    def branch_exists(self, source, branch):
        self.calls.append(("branch_exists", source, branch))
        if source in self.branch_errors:
            raise GitWorktreeError("no repo")
        return source in self.branches

    def is_worktree(self, source, branch, target):
        self.calls.append(("is_worktree", source, branch, target))
        if target in self.worktree_errors:
            raise GitWorktreeError("cannot list")
        return (source, target) in self.worktrees

    def remove_worktree(self, source, branch, target, delete_branch):
        self.calls.append(("remove_worktree", source, branch, target, delete_branch))
        if target in self.remove_errors:
            raise self.remove_errors[target]

    def removes(self):
        return [call[1:] for call in self.calls if call[0] == "remove_worktree"]


def make_request(tmp_path: Path, name: str) -> WorktreeRequest:
    src = tmp_path / name / "src"
    wt = tmp_path / name / "wt"
    src.mkdir(parents=True)
    wt.mkdir(parents=True)
    return WorktreeRequest(src, wt)


def target(req: WorktreeRequest) -> Path:
    return (req.parent / FEATURE).resolve()


def state(req: WorktreeRequest, existed: bool = False, branch: bool = False) -> PreRunState:
    return PreRunState(req, target(req), existed, branch)


@pytest.fixture
def git():
    return RecordingGit()


@pytest.fixture
def service(git):
    return WorktreeService(git)


# --- snapshot ---------------------------------------------------------------------


def test_snapshot_records_target_and_branch_per_request(tmp_path, git, service):
    r1 = make_request(tmp_path, "one")
    r2 = make_request(tmp_path, "two")
    target(r2).mkdir()
    git.branches = {r1.source.resolve()}

    result = service.snapshot(FEATURE, [r1, r2])

    assert result == [
        PreRunState(r1, target(r1), False, True),
        PreRunState(r2, target(r2), True, False),
    ]
    assert git.calls == [
        ("branch_exists", r1.source.resolve(), FEATURE),
        ("branch_exists", r2.source.resolve(), FEATURE),
    ]
    assert result[0].request is r1


def test_snapshot_target_file_counts_as_existing(tmp_path, service):
    r1 = make_request(tmp_path, "one")
    target(r1).write_text("x", "utf-8")
    [entry] = service.snapshot(FEATURE, [r1])
    assert entry.target_existed is True


def test_snapshot_branch_check_error_counts_as_existing(tmp_path, git, service):
    r1 = make_request(tmp_path, "one")
    git.branch_errors = {r1.source.resolve()}
    [entry] = service.snapshot(FEATURE, [r1])
    assert entry.branch_existed is True


def test_snapshot_empty_requests(git, service):
    assert service.snapshot(FEATURE, []) == []
    assert git.calls == []


def test_snapshot_invalid_feature_name_raises(tmp_path, git, service):
    r1 = make_request(tmp_path, "one")
    with pytest.raises(ValueError):
        service.snapshot("Bad", [r1])
    assert git.calls == []


# --- recover ----------------------------------------------------------------------


def test_recover_keeps_verified_and_cleans_up_the_rest(tmp_path, git, service):
    r1, r2, r3 = (make_request(tmp_path, name) for name in ("one", "two", "three"))
    git.worktrees = {(r1.source.resolve(), target(r1))}
    snapshot = [state(r1), state(r2), state(r3)]

    results = service.recover(FEATURE, snapshot, E)

    assert results[0].ok
    assert results[0].target == target(r1)
    assert results[1].error == CLEANED_UP
    assert results[2].error == CLEANED_UP
    assert git.removes() == [
        (r2.source.resolve(), FEATURE, target(r2), True),
        (r3.source.resolve(), FEATURE, target(r3), True),
    ]
    for i, result in enumerate(results):
        assert result.request is snapshot[i].request


def test_recover_never_touches_existing_target(tmp_path, git, service):
    r1 = make_request(tmp_path, "one")
    [result] = service.recover(FEATURE, [state(r1, existed=True)], E)
    assert result.error == TARGET_EXISTS_MESSAGE
    assert result.error == "target folder already exists"
    assert not any(call[0] in ("is_worktree", "remove_worktree") for call in git.calls)


def test_recover_keeps_branch_that_existed(tmp_path, git, service):
    r1 = make_request(tmp_path, "one")
    service.recover(FEATURE, [state(r1, branch=True)], E)
    assert git.removes() == [(r1.source.resolve(), FEATURE, target(r1), False)]


def test_recover_unverifiable_worktree_is_cleaned_up(tmp_path, git, service):
    r1 = make_request(tmp_path, "one")
    git.worktree_errors = {target(r1)}
    [result] = service.recover(FEATURE, [state(r1)], E)
    assert git.removes() == [(r1.source.resolve(), FEATURE, target(r1), True)]
    assert result.error == CLEANED_UP


def test_recover_cleanup_failure_reports_git_message(tmp_path, git, service):
    r1 = make_request(tmp_path, "one")
    r2 = make_request(tmp_path, "two")
    git.remove_errors = {target(r1): GitWorktreeError("boom")}
    results = service.recover(FEATURE, [state(r1), state(r2)], E)
    assert results[0].error == "unexpected error: RuntimeError: boom; cleanup failed: boom"
    assert results[1].error == CLEANED_UP


def test_recover_does_not_clean_target_of_verified_entry(tmp_path, git, service):
    parent = tmp_path / "wt"
    parent.mkdir()
    src1 = tmp_path / "src1"
    src2 = tmp_path / "src2"
    src1.mkdir()
    src2.mkdir()
    r1 = WorktreeRequest(src1, parent)
    r2 = WorktreeRequest(src2, parent)
    t = target(r1)
    git.worktrees = {(r1.source.resolve(), t)}

    results = service.recover(FEATURE, [state(r1), state(r2)], E)

    assert results[0].ok
    assert results[1].error == "target folder already exists"
    assert git.removes() == []


def test_recover_unexpected_exception_propagates(tmp_path, git, service):
    r1 = make_request(tmp_path, "one")
    git.remove_errors = {target(r1): RuntimeError("x")}
    with pytest.raises(RuntimeError):
        service.recover(FEATURE, [state(r1)], E)


def test_recover_empty_snapshot(git, service):
    assert service.recover(FEATURE, [], E) == []
    assert git.calls == []


def test_recover_invalid_feature_name_raises(tmp_path, git, service):
    r1 = make_request(tmp_path, "one")
    with pytest.raises(ValueError):
        service.recover("Bad", [state(r1)], E)
    assert git.calls == []

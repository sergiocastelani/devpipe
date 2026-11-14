from pathlib import Path

import pytest

from devpipe.models.worktree import GitWorktreeError, WorktreeRequest
from devpipe.services.worktree_service import (
    PARENT_MISSING_MESSAGE,
    SOURCE_MISSING_MESSAGE,
    TARGET_EXISTS_MESSAGE,
    WorktreeService,
)

FEATURE = "feat-x"


class FakeGitWorktrees:
    """Records add_worktree calls; raises a preset GitWorktreeError per target,
    otherwise creates the target folder like real git would."""

    def __init__(self, errors: dict[Path, GitWorktreeError] | None = None):
        self.errors = errors or {}  # keyed by the resolved target, e.g. (wt / "feat-x").resolve()
        self.calls: list[tuple[Path, str, Path]] = []

    def add_worktree(self, source, branch, target):
        self.calls.append((source, branch, target))
        if target in self.errors:
            raise self.errors[target]
        target.mkdir()


def make_request(tmp_path: Path, name: str) -> WorktreeRequest:
    src = tmp_path / name / "src"
    wt = tmp_path / name / "wt"
    src.mkdir(parents=True)
    wt.mkdir(parents=True)
    return WorktreeRequest(src, wt)


def _target(request: WorktreeRequest) -> Path:
    return (request.parent / FEATURE).resolve()


def test_creates_each_request_in_order(tmp_path):
    requests = [make_request(tmp_path, "one"), make_request(tmp_path, "two")]
    fake = FakeGitWorktrees()

    results = WorktreeService(fake).create_worktrees(FEATURE, requests)

    assert fake.calls == [
        (requests[0].source.resolve(), FEATURE, _target(requests[0])),
        (requests[1].source.resolve(), FEATURE, _target(requests[1])),
    ]
    assert len(results) == 2
    for i, result in enumerate(results):
        assert result.ok
        assert result.request is requests[i]
        assert result.target == (requests[i].parent / FEATURE).resolve()


def test_empty_requests_return_empty_list():
    fake = FakeGitWorktrees()
    assert WorktreeService(fake).create_worktrees(FEATURE, []) == []
    assert fake.calls == []


@pytest.mark.parametrize("name", ["", "-x", "Feat"])
def test_invalid_feature_name_raises(tmp_path, name):
    fake = FakeGitWorktrees()
    with pytest.raises(ValueError):
        WorktreeService(fake).create_worktrees(name, [make_request(tmp_path, "one")])
    assert fake.calls == []


def test_missing_source_fails_without_git(tmp_path):
    wt = tmp_path / "wt"
    wt.mkdir()
    request = WorktreeRequest(tmp_path / "missing", wt)
    fake = FakeGitWorktrees()

    [result] = WorktreeService(fake).create_worktrees(FEATURE, [request])

    assert result.error == SOURCE_MISSING_MESSAGE == "source folder does not exist"
    assert result.target == (wt / FEATURE).resolve()
    assert fake.calls == []


def test_source_file_counts_as_missing(tmp_path):
    src = tmp_path / "src"
    src.write_text("x", encoding="utf-8")
    wt = tmp_path / "wt"
    wt.mkdir()
    fake = FakeGitWorktrees()

    [result] = WorktreeService(fake).create_worktrees(FEATURE, [WorktreeRequest(src, wt)])

    assert result.error == "source folder does not exist"
    assert fake.calls == []


def test_missing_parent_fails_and_is_not_created(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    parent = tmp_path / "missing"
    fake = FakeGitWorktrees()

    [result] = WorktreeService(fake).create_worktrees(FEATURE, [WorktreeRequest(src, parent)])

    assert result.error == PARENT_MISSING_MESSAGE == "parent folder does not exist"
    assert not parent.exists()
    assert fake.calls == []


def test_parent_file_counts_as_missing(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    parent = tmp_path / "parent"
    parent.write_text("x", encoding="utf-8")
    fake = FakeGitWorktrees()

    [result] = WorktreeService(fake).create_worktrees(FEATURE, [WorktreeRequest(src, parent)])

    assert result.error == "parent folder does not exist"
    assert fake.calls == []


def test_existing_target_fails_without_git(tmp_path):
    request = make_request(tmp_path, "one")
    (request.parent / FEATURE).mkdir()
    fake = FakeGitWorktrees()

    [result] = WorktreeService(fake).create_worktrees(FEATURE, [request])

    assert result.error == TARGET_EXISTS_MESSAGE == "target folder already exists"
    assert fake.calls == []


def test_first_failing_check_wins(tmp_path):
    request = WorktreeRequest(tmp_path / "no-src", tmp_path / "no-wt")
    fake = FakeGitWorktrees()

    [result] = WorktreeService(fake).create_worktrees(FEATURE, [request])

    assert result.error == "source folder does not exist"
    assert fake.calls == []


def test_git_error_is_reported_and_run_continues(tmp_path):
    requests = [make_request(tmp_path, n) for n in ("one", "two", "three")]
    fake = FakeGitWorktrees({_target(requests[1]): GitWorktreeError("boom")})

    results = WorktreeService(fake).create_worktrees(FEATURE, requests)

    assert [r.error for r in results] == [None, "boom", None]
    assert [r.ok for r in results] == [True, False, True]
    assert len(fake.calls) == 3


def test_precheck_failure_does_not_stop_later_requests(tmp_path):
    wt = tmp_path / "wt"
    wt.mkdir()
    first = WorktreeRequest(tmp_path / "missing", wt)
    second = make_request(tmp_path, "two")
    fake = FakeGitWorktrees()

    results = WorktreeService(fake).create_worktrees(FEATURE, [first, second])

    assert results[0].error == "source folder does not exist"
    assert results[1].ok
    assert fake.calls == [(second.source.resolve(), FEATURE, _target(second))]


def test_same_parent_second_request_fails(tmp_path):
    wt = tmp_path / "wt"
    wt.mkdir()
    src1 = tmp_path / "src1"
    src2 = tmp_path / "src2"
    src1.mkdir()
    src2.mkdir()
    fake = FakeGitWorktrees()

    results = WorktreeService(fake).create_worktrees(
        FEATURE, [WorktreeRequest(src1, wt), WorktreeRequest(src2, wt)]
    )

    assert results[0].ok
    assert results[1].error == "target folder already exists"
    assert fake.calls == [(src1.resolve(), FEATURE, (wt / FEATURE).resolve())]


def test_relative_paths_are_resolved(tmp_path, monkeypatch):
    (tmp_path / "src").mkdir()
    (tmp_path / "wt").mkdir()
    monkeypatch.chdir(tmp_path)
    fake = FakeGitWorktrees()

    [result] = WorktreeService(fake).create_worktrees(
        FEATURE, [WorktreeRequest(Path("src"), Path("wt"))]
    )

    assert result.target == (tmp_path / "wt" / FEATURE).resolve()
    assert result.target.is_absolute()
    assert fake.calls[0][0] == (tmp_path / "src").resolve()


def test_merge_paths_appends_new_in_order(tmp_path):
    a, b, c = tmp_path / "a", tmp_path / "b", tmp_path / "c"
    service = WorktreeService(FakeGitWorktrees())
    assert service.merge_paths([a], [b, c]) == [a, b, c]


def test_merge_paths_skips_same_file(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    a2 = a.parent / "x" / ".." / a.name
    service = WorktreeService(FakeGitWorktrees())

    merged = service.merge_paths([a], [b, a2, b])

    assert merged == [a, b]
    assert merged[0] is a


def test_merge_paths_does_not_modify_inputs(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    existing = [a]
    new = [b, a]
    service = WorktreeService(FakeGitWorktrees())

    merged = service.merge_paths(existing, new)

    assert merged is not existing
    assert existing == [a]
    assert new == [b, a]


def test_merge_paths_empty():
    service = WorktreeService(FakeGitWorktrees())
    existing: list[Path] = []
    merged = service.merge_paths(existing, [])
    assert merged == []
    assert merged is not existing

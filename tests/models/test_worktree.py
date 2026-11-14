from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from devpipe.models.worktree import GitWorktreeError, WorktreeRequest, WorktreeResult


def _request() -> WorktreeRequest:
    return WorktreeRequest(Path("src"), Path("wt"))


def test_result_ok_when_no_error():
    result = WorktreeResult(_request(), Path("wt/feat-x"), None)
    assert result.ok is True


def test_result_not_ok_with_error():
    result = WorktreeResult(_request(), Path("wt/feat-x"), "boom")
    assert result.ok is False


def test_request_and_result_are_frozen():
    req = _request()
    res = WorktreeResult(req, Path("wt/feat-x"), None)
    with pytest.raises(FrozenInstanceError):
        req.source = Path("other")
    with pytest.raises(FrozenInstanceError):
        res.error = "boom"


def test_request_value_equality():
    a = WorktreeRequest(Path("src"), Path("wt"))
    b = WorktreeRequest(Path("src"), Path("wt"))
    assert a == b
    assert hash(a) == hash(b)


def test_git_worktree_error_message():
    e = GitWorktreeError("x")
    assert str(e) == "x"
    assert e.message == "x"
    assert isinstance(e, Exception)

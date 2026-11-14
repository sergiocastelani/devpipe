from pathlib import Path

import pytest

from devpipe.models.tab_state import (
    PERSISTED_PANELS,
    STATE_FILE_VERSION,
    Panel,
    TabState,
    TabStateError,
    is_valid_feature_name,
)


def test_panel_values():
    assert Panel.START.value == "start"
    assert Panel("start") is Panel.START
    assert Panel.NEW_WORKTREE.value == "new-worktree"
    assert Panel("new-worktree") is Panel.NEW_WORKTREE
    assert len(Panel) == 2


def test_persisted_panels_is_start_only():
    assert PERSISTED_PANELS == frozenset({Panel.START})


def test_tab_state_defaults_to_start_panel():
    assert TabState("a").active_panel is Panel.START
    assert TabState("a") == TabState("a", Panel.START)
    assert TabState("a") == TabState("a", Panel.START, [])
    assert TabState("a").worktrees == []


def test_tab_state_worktrees_default_is_not_shared():
    first = TabState("a")
    second = TabState("a")
    first.worktrees.append(Path("x"))
    assert second.worktrees == []


def test_state_file_version_is_2():
    assert STATE_FILE_VERSION == 2


@pytest.mark.parametrize("name", ["a", "new-feature", "nova-feature-x", "a1-2b"])
def test_is_valid_feature_name_accepts_slugs(name):
    assert is_valid_feature_name(name) is True


@pytest.mark.parametrize("name", ["", "-a", "a-", "a--b", "New", "a b", "a_b", "á", "a\n"])
def test_is_valid_feature_name_rejects_non_slugs(name):
    assert is_valid_feature_name(name) is False


def test_tab_state_error_keeps_path_and_reason():
    error = TabStateError(Path("x/s.json"), "file not found")
    assert error.path == Path("x/s.json")
    assert error.reason == "file not found"
    assert str(error) == f"{Path('x/s.json')}: file not found"
    assert isinstance(error, Exception)

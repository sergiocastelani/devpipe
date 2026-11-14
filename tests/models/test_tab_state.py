from pathlib import Path

import pytest

from devpipe.models.tab_state import (
    STATE_FILE_VERSION,
    Panel,
    TabState,
    TabStateError,
    is_valid_feature_name,
)


def test_panel_start_value_is_start():
    assert Panel.START.value == "start"
    assert Panel("start") is Panel.START
    assert len(Panel) == 1


def test_tab_state_defaults_to_start_panel():
    assert TabState("a").active_panel is Panel.START
    assert TabState("a") == TabState("a", Panel.START)


def test_state_file_version_is_1():
    assert STATE_FILE_VERSION == 1


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

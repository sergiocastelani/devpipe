import sys
from pathlib import Path

import pytest

from devpipe.services.paths import same_file, with_default_suffix


def test_same_file_for_equal_paths(tmp_path):
    assert same_file(tmp_path / "s.json", tmp_path / "s.json")


def test_same_file_resolves_dot_dot(tmp_path):
    assert same_file(tmp_path / "a" / ".." / "s.json", tmp_path / "s.json")


def test_same_file_differs_for_other_files(tmp_path):
    assert not same_file(tmp_path / "a.json", tmp_path / "b.json")


@pytest.mark.skipif(sys.platform != "win32", reason="case-insensitive paths only on Windows")
def test_same_file_ignores_case_on_windows(tmp_path):
    assert same_file(tmp_path / "S.JSON", tmp_path / "s.json")


@pytest.mark.skipif(sys.platform == "win32", reason="paths are case-insensitive on Windows")
def test_same_file_keeps_case_elsewhere(tmp_path):
    assert not same_file(tmp_path / "S.JSON", tmp_path / "s.json")


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        ("new-feature", "new-feature.json"),
        ("a.json", "a.json"),
        ("a.JSON", "a.JSON"),
        ("a.txt", "a.txt"),
        ("dir/x", "dir/x.json"),
    ],
)
def test_with_default_suffix(given, expected):
    assert with_default_suffix(Path(given), ".json") == Path(expected)

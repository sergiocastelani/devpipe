import json
from pathlib import Path

import pytest

from devpipe.models.tab_state import Panel, TabState, TabStateError
from devpipe.persistence.tab_state_repository import TabStateRepository

_VALID = {"version": 2, "feature_name": "new-feature", "active_panel": "start", "worktrees": []}
_V1_VALID = {"version": 1, "feature_name": "new-feature", "active_panel": "start"}
_VALID_BYTES = (json.dumps(_VALID, indent=2) + "\n").encode("utf-8")


def _without(key):
    return json.dumps({k: v for k, v in _VALID.items() if k != key}).encode("utf-8")


def _with(key, value):
    return json.dumps({**_VALID, key: value}).encode("utf-8")


# (id, file content or None for "no file", expected reason, prefix match)
_INVALID_FILES = [
    ("missing-file", None, "file not found", False),
    ("not-json", b"{not json", "not valid JSON: ", True),
    ("empty-file", b"", "not valid JSON: ", True),
    ("not-utf8", b"\xff\xfe", "not valid UTF-8 text", False),
    ("utf8-bom", b"\xef\xbb\xbf" + _VALID_BYTES, "not valid JSON: ", True),
    ("list", b"[]", "not a JSON object", False),
    ("string", b'"x"', "not a JSON object", False),
    ("number", b"5", "not a JSON object", False),
    ("null", b"null", "not a JSON object", False),
    ("missing-version", _without("version"), "missing version", False),
    ("version-3", _with("version", 3), "unsupported version: ", True),
    ("version-0", _with("version", 0), "unsupported version: ", True),
    ("version-str", _with("version", "2"), "unsupported version: ", True),
    ("version-true", _with("version", True), "unsupported version: ", True),
    ("version-float", _with("version", 2.0), "unsupported version: ", True),
    ("version-null", _with("version", None), "unsupported version: ", True),
    ("missing-feature-name", _without("feature_name"), "missing feature_name", False),
    ("feature-name-empty", _with("feature_name", ""), "empty feature_name", False),
    ("feature-name-spaces", _with("feature_name", "New Feature"), "invalid feature_name: ", True),
    ("feature-name-leading-hyphen", _with("feature_name", "-a"), "invalid feature_name: ", True),
    ("feature-name-double-hyphen", _with("feature_name", "a--b"), "invalid feature_name: ", True),
    ("feature-name-number", _with("feature_name", 5), "invalid feature_name: ", True),
    ("feature-name-null", _with("feature_name", None), "invalid feature_name: ", True),
    ("missing-active-panel", _without("active_panel"), "missing active_panel", False),
    ("active-panel-process", _with("active_panel", "process"), "unknown active_panel: ", True),
    ("active-panel-upper", _with("active_panel", "START"), "unknown active_panel: ", True),
    ("active-panel-number", _with("active_panel", 1), "unknown active_panel: ", True),
    ("active-panel-list", _with("active_panel", []), "unknown active_panel: ", True),
    (
        "active-panel-new-worktree",
        _with("active_panel", "new-worktree"),
        "unknown active_panel: ",
        True,
    ),
    (
        "v1-active-panel-new-worktree",
        json.dumps({**_V1_VALID, "active_panel": "new-worktree"}).encode("utf-8"),
        "unknown active_panel: ",
        True,
    ),
    ("missing-worktrees", _without("worktrees"), "invalid worktrees", False),
    ("worktrees-str", _with("worktrees", "x"), "invalid worktrees", False),
    ("worktrees-null", _with("worktrees", None), "invalid worktrees", False),
    ("worktrees-object", _with("worktrees", {}), "invalid worktrees", False),
    ("worktrees-number", _with("worktrees", 5), "invalid worktrees", False),
    ("worktrees-int-item", _with("worktrees", [1]), "invalid worktrees", False),
    ("worktrees-null-item", _with("worktrees", [None]), "invalid worktrees", False),
    ("worktrees-list-item", _with("worktrees", [[]]), "invalid worktrees", False),
    ("worktrees-empty-item", _with("worktrees", [""]), "invalid worktrees", False),
    ("worktrees-mixed", _with("worktrees", ["a", ""]), "invalid worktrees", False),
    (
        "feature-name-and-worktrees-invalid",
        json.dumps({**_VALID, "feature_name": "New Feature", "worktrees": "x"}).encode("utf-8"),
        "invalid feature_name: ",
        True,
    ),
    # Extra rows: content json.loads rejects without a JSONDecodeError.
    ("huge-number", b'{"version": ' + b"1" * 5000 + b"}", "not valid JSON: ", True),
    ("deep-nesting", b"[" * 200000 + b"]" * 200000, "not valid JSON: ", True),
    (
        "deep-nesting-in-object",
        b'{"version": 1, "x": ' + b"[" * 200000 + b"]" * 200000 + b"}",
        "not valid JSON: ",
        True,
    ),
]


def test_save_writes_exact_format(tmp_path):
    path = tmp_path / "s.json"
    a = tmp_path / "wt" / "a"
    b = tmp_path / "wt" / "b"
    TabStateRepository().save(path, TabState("new-feature", Panel.START, [a, b]))
    text = path.read_text(encoding="utf-8")
    expected = {
        "version": 2,
        "feature_name": "new-feature",
        "active_panel": "start",
        "worktrees": [str(a), str(b)],
    }
    assert json.loads(text) == expected
    assert list(json.loads(text)) == ["version", "feature_name", "active_panel", "worktrees"]
    assert text.endswith("\n")
    assert text == json.dumps(expected, indent=2) + "\n"


def test_save_writes_empty_worktrees(tmp_path):
    path = tmp_path / "s.json"
    TabStateRepository().save(path, TabState("new-feature"))
    assert json.loads(path.read_text(encoding="utf-8")) == _VALID


def test_save_then_load_round_trips(tmp_path):
    path = tmp_path / "s.json"
    repo = TabStateRepository()
    state = TabState("nova-feature-x", Panel.START, [tmp_path / "wt" / "b", tmp_path / "wt" / "a"])
    repo.save(path, state)
    assert repo.load(path) == state


def test_v2_file_load_then_save_is_identical(tmp_path):
    path = tmp_path / "s.json"
    content = json.dumps({**_VALID, "worktrees": [str(tmp_path / "wt" / "x")]}, indent=2) + "\n"
    path.write_text(content, encoding="utf-8")  # text mode, as the repository writes
    before = path.read_bytes()
    repo = TabStateRepository()
    repo.save(path, repo.load(path))
    assert path.read_bytes() == before


def _write_json(path, data):
    path.write_bytes(json.dumps(data).encode("utf-8"))


def test_load_v1_file_has_no_worktrees(tmp_path):
    path = tmp_path / "s.json"
    _write_json(path, _V1_VALID)
    assert TabStateRepository().load(path) == TabState("new-feature", Panel.START, [])


@pytest.mark.parametrize("value", [["x"], "x", [1], None], ids=["list", "str", "int-item", "null"])
def test_load_v1_ignores_worktrees_key(tmp_path, value):
    path = tmp_path / "s.json"
    _write_json(path, {**_V1_VALID, "worktrees": value})
    assert TabStateRepository().load(path).worktrees == []


def test_load_v1_then_save_writes_v2(tmp_path):
    path = tmp_path / "s.json"
    _write_json(path, _V1_VALID)
    repo = TabStateRepository()
    repo.save(path, repo.load(path))
    assert json.loads(path.read_text(encoding="utf-8")) == _VALID


def test_load_accepts_whitespace_and_relative_worktrees(tmp_path):
    path = tmp_path / "s.json"
    _write_json(path, {**_VALID, "worktrees": [" ", "rel/x"]})
    assert TabStateRepository().load(path).worktrees == [Path(" "), Path("rel/x")]


def test_load_keeps_duplicate_worktrees(tmp_path):
    path = tmp_path / "s.json"
    a = str(tmp_path / "wt" / "a")
    b = str(tmp_path / "wt" / "b")
    _write_json(path, {**_VALID, "worktrees": [a, b, a]})
    assert TabStateRepository().load(path).worktrees == [Path(a), Path(b), Path(a)]


def test_save_overwrites_existing_file(tmp_path):
    path = tmp_path / "s.json"
    path.write_text("something else", encoding="utf-8")
    repo = TabStateRepository()
    repo.save(path, TabState("new-feature"))
    assert repo.load(path) == TabState("new-feature")
    assert json.loads(path.read_text(encoding="utf-8")) == _VALID


def test_load_ignores_extra_keys(tmp_path):
    path = tmp_path / "s.json"
    path.write_bytes(_with("extra", 1))
    assert TabStateRepository().load(path) == TabState("new-feature", Panel.START)


@pytest.mark.parametrize(
    ("content", "reason", "prefix"),
    [row[1:] for row in _INVALID_FILES],
    ids=[row[0] for row in _INVALID_FILES],
)
def test_load_rejects_invalid_file(tmp_path, content, reason, prefix):
    path = tmp_path / "s.json"
    if content is not None:
        path.write_bytes(content)
    with pytest.raises(TabStateError) as info:
        TabStateRepository().load(path)
    error = info.value
    assert error.path == path
    if prefix:
        assert error.reason.startswith(reason)
    else:
        assert error.reason == reason
    assert str(error).startswith(str(path))


def test_load_folder_raises_tab_state_error(tmp_path):
    with pytest.raises(TabStateError) as info:
        TabStateRepository().load(tmp_path)
    assert info.value.path == tmp_path
    assert info.value.reason.startswith("cannot read file: ")


def test_save_into_missing_folder_raises_tab_state_error(tmp_path):
    path = tmp_path / "missing" / "s.json"
    with pytest.raises(TabStateError) as info:
        TabStateRepository().save(path, TabState("new-feature"))
    assert info.value.path == path
    assert info.value.reason.startswith("cannot write file: ")
    assert not (tmp_path / "missing").exists()


def test_save_onto_folder_raises_tab_state_error(tmp_path):
    path = tmp_path / "d"
    path.mkdir()
    with pytest.raises(TabStateError) as info:
        TabStateRepository().save(path, TabState("new-feature"))
    assert info.value.path == path
    assert info.value.reason.startswith("cannot write file: ")


def test_save_rejects_invalid_feature_name(tmp_path):
    path = tmp_path / "s.json"
    with pytest.raises(TabStateError) as info:
        TabStateRepository().save(path, TabState(""))
    assert info.value.path == path
    assert info.value.reason == "invalid feature_name"
    assert not path.exists()


def test_save_rejects_non_persisted_panel(tmp_path):
    path = tmp_path / "s.json"
    repo = TabStateRepository()
    state = TabState("new-feature", Panel.NEW_WORKTREE)
    with pytest.raises(ValueError):
        repo.save(path, state)
    assert not path.exists()

    path.write_bytes(_VALID_BYTES)
    with pytest.raises(ValueError):
        repo.save(path, state)
    assert path.read_bytes() == _VALID_BYTES

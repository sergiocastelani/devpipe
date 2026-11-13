import json

import pytest

from devpipe.models.tab_state import Panel, TabState, TabStateError
from devpipe.persistence.tab_state_repository import TabStateRepository

_VALID = {"version": 1, "feature_name": "new-feature", "active_panel": "start"}
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
    ("version-2", _with("version", 2), "unsupported version: ", True),
    ("version-str", _with("version", "1"), "unsupported version: ", True),
    ("version-true", _with("version", True), "unsupported version: ", True),
    ("version-float", _with("version", 1.0), "unsupported version: ", True),
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
    TabStateRepository().save(path, TabState("new-feature"))
    text = path.read_text(encoding="utf-8")
    expected = {"version": 1, "feature_name": "new-feature", "active_panel": "start"}
    assert json.loads(text) == expected
    assert list(json.loads(text)) == ["version", "feature_name", "active_panel"]
    assert text.endswith("\n")
    assert text == json.dumps(expected, indent=2) + "\n"


def test_save_then_load_round_trips(tmp_path):
    path = tmp_path / "s.json"
    repo = TabStateRepository()
    state = TabState("nova-feature-x", Panel.START)
    repo.save(path, state)
    assert repo.load(path) == state


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

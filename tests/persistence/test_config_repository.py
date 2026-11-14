import json
from pathlib import Path

import pytest

from devpipe.models.app_config import AppConfig
from devpipe.persistence.config_repository import ConfigRepository


def test_missing_file_gives_defaults(tmp_path):
    assert ConfigRepository(tmp_path / "config.json").load() == AppConfig()


def test_corrupt_file_gives_defaults(tmp_path):
    path = tmp_path / "config.json"
    path.write_text("{not json", encoding="utf-8")
    assert ConfigRepository(path).load() == AppConfig()


def test_save_then_load_round_trips(tmp_path):
    repo = ConfigRepository(tmp_path / "config.json")
    repo.save(AppConfig(window_maximized=True))
    assert repo.load().window_maximized is True


def test_save_keeps_unknown_keys(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"other": 1}), encoding="utf-8")
    ConfigRepository(path).save(AppConfig(window_maximized=True))
    assert json.loads(path.read_text(encoding="utf-8")) == {
        "other": 1,
        "window_maximized": True,
        "last_state_folder": None,
        "open_state_files": [],
        "active_state_file": None,
    }


def test_last_state_folder_round_trips(tmp_path):
    path = tmp_path / "config.json"
    repo = ConfigRepository(path)
    repo.save(AppConfig(last_state_folder=tmp_path / "states"))
    assert repo.load().last_state_folder == tmp_path / "states"
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw["last_state_folder"] == str(tmp_path / "states")


def test_last_state_folder_defaults_to_none(tmp_path):
    path = tmp_path / "config.json"
    assert ConfigRepository(path).load().last_state_folder is None
    path.write_text(json.dumps({"window_maximized": True}), encoding="utf-8")
    assert ConfigRepository(path).load().last_state_folder is None


@pytest.mark.parametrize("value", [None, "", 5, True, [], {}])
def test_invalid_last_state_folder_gives_none(tmp_path, value):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"last_state_folder": value}), encoding="utf-8")
    assert ConfigRepository(path).load().last_state_folder is None


def test_session_keys_round_trip(tmp_path):
    path = tmp_path / "config.json"
    repo = ConfigRepository(path)
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    repo.save(AppConfig(open_state_files=[a, b], active_state_file=b))
    loaded = repo.load()
    assert loaded.open_state_files == [a, b]
    assert loaded.active_state_file == b
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw["open_state_files"] == [str(a), str(b)]
    assert raw["active_state_file"] == str(b)


def test_session_keys_default_to_empty(tmp_path):
    path = tmp_path / "config.json"
    missing = ConfigRepository(path).load()
    assert missing.open_state_files == []
    assert missing.active_state_file is None
    path.write_text(json.dumps({"window_maximized": True}), encoding="utf-8")
    without_keys = ConfigRepository(path).load()
    assert without_keys.open_state_files == []
    assert without_keys.active_state_file is None


@pytest.mark.parametrize("value", [None, "a.json", 5, True, {}])
def test_invalid_open_state_files_gives_empty_list(tmp_path, value):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"open_state_files": value}), encoding="utf-8")
    assert ConfigRepository(path).load().open_state_files == []


def test_open_state_files_skips_invalid_items(tmp_path):
    path = tmp_path / "config.json"
    value = ["a.json", "", 5, None, ["x"], "x\u0000y.json", "b.json"]
    path.write_text(json.dumps({"open_state_files": value}), encoding="utf-8")
    assert ConfigRepository(path).load().open_state_files == [Path("a.json"), Path("b.json")]


@pytest.mark.parametrize("value", [None, "", 5, True, [], {}, "z\u0000.json"])
def test_invalid_active_state_file_gives_none(tmp_path, value):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"active_state_file": value}), encoding="utf-8")
    assert ConfigRepository(path).load().active_state_file is None

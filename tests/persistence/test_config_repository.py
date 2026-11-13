import json

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

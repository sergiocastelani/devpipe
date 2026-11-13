import json

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
    assert json.loads(path.read_text(encoding="utf-8")) == {"other": 1, "window_maximized": True}

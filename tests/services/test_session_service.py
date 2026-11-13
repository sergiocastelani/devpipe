from pathlib import Path

from devpipe.persistence.config_repository import ConfigRepository
from devpipe.services.session_service import SessionService
from devpipe.services.window_state_service import WindowStateService


def make_service(tmp_path):
    config = ConfigRepository(tmp_path / "config.json")
    return SessionService(config), config


def test_start_folder_defaults_to_home(tmp_path):
    service, _ = make_service(tmp_path)
    assert service.start_folder() == Path.home()


def test_remember_folder_stores_parent(tmp_path):
    service, config = make_service(tmp_path)
    folder = tmp_path / "states"
    folder.mkdir()
    service.remember_folder(folder / "x.json")
    assert service.start_folder() == folder
    assert config.load().last_state_folder == folder


def test_start_folder_falls_back_to_home_when_folder_is_gone(tmp_path):
    service, _ = make_service(tmp_path)
    folder = tmp_path / "states"
    folder.mkdir()
    service.remember_folder(folder / "x.json")
    folder.rmdir()
    assert service.start_folder() == Path.home()


def test_start_folder_falls_back_to_home_when_value_is_a_file(tmp_path):
    service, _ = make_service(tmp_path)
    not_a_folder = tmp_path / "file"
    not_a_folder.write_text("", encoding="utf-8")
    service.remember_folder(not_a_folder / "x.json")
    assert service.start_folder() == Path.home()


def test_remember_folder_keeps_other_settings(tmp_path):
    service, config = make_service(tmp_path)
    WindowStateService(config).remember_maximized(True)
    service.remember_folder(tmp_path / "x.json")
    assert config.load().window_maximized is True

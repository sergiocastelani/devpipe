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


def test_session_defaults_to_empty(tmp_path):
    service, _ = make_service(tmp_path)
    assert service.open_files() == []
    assert service.active_file() is None


def test_remember_session_round_trips(tmp_path):
    service, _ = make_service(tmp_path)
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    service.remember_session([a, b], b)
    assert service.open_files() == [a, b]
    assert service.active_file() == b


def test_remember_session_without_active(tmp_path):
    service, _ = make_service(tmp_path)
    service.remember_session([tmp_path / "a.json"], None)
    assert service.active_file() is None


def test_remember_session_stores_absolute_paths(tmp_path):
    service, _ = make_service(tmp_path)
    service.remember_session([Path("x.json")], Path("x.json"))
    assert service.open_files() == [Path("x.json").absolute()]
    assert service.active_file() == Path("x.json").absolute()


def test_remember_session_keeps_other_settings(tmp_path):
    service, config = make_service(tmp_path)
    WindowStateService(config).remember_maximized(True)
    service.remember_folder(tmp_path / "states" / "x.json")
    a = tmp_path / "a.json"
    service.remember_session([a], a)
    assert config.load().window_maximized is True
    assert config.load().last_state_folder == tmp_path / "states"


def test_remember_folder_keeps_session(tmp_path):
    service, _ = make_service(tmp_path)
    a = tmp_path / "a.json"
    service.remember_session([a], a)
    service.remember_folder(tmp_path / "states" / "x.json")
    assert service.open_files() == [a]
    assert service.active_file() == a

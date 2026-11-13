from devpipe.persistence.config_repository import ConfigRepository
from devpipe.services.window_state_service import WindowStateService


def test_remembers_maximized_state(tmp_path):
    service = WindowStateService(ConfigRepository(tmp_path / "config.json"))
    assert service.was_maximized() is False
    service.remember_maximized(True)
    assert service.was_maximized() is True
    service.remember_maximized(False)
    assert service.was_maximized() is False

"""Remember the main window state between sessions."""

from typing import Protocol

from devpipe.models.app_config import AppConfig


class ConfigStore(Protocol):
    """Where the app config is kept (implemented in the persistence layer)."""

    def load(self) -> AppConfig: ...

    def save(self, config: AppConfig) -> None: ...


class WindowStateService:
    def __init__(self, store: ConfigStore) -> None:
        self._store = store

    def was_maximized(self) -> bool:
        return self._store.load().window_maximized

    def remember_maximized(self, maximized: bool) -> None:
        config = self._store.load()
        config.window_maximized = maximized
        self._store.save(config)

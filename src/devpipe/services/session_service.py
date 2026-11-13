"""Remember where state files live between sessions."""

from pathlib import Path

from devpipe.services.window_state_service import ConfigStore


class SessionService:
    def __init__(self, store: ConfigStore) -> None:
        self._store = store

    def start_folder(self) -> Path:
        """Folder the Save/Open dialogs start in.

        The last-used folder if it is set and is still an existing folder, else Path.home().
        """
        folder = self._store.load().last_state_folder
        if folder is not None and folder.is_dir():
            return folder
        return Path.home()

    def remember_folder(self, state_file: Path) -> None:
        """Store state_file.parent as the last-used folder (load-modify-save, other settings kept)."""
        config = self._store.load()
        config.last_state_folder = state_file.parent
        self._store.save(config)

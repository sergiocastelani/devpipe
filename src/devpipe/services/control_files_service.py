"""Questions about a feature's control files (`<worktree>/.devpipe/<feature-name>/`)."""

from pathlib import Path
from typing import Protocol

from devpipe.models.control_files import feature_spec_file


class ControlFilesStore(Protocol):
    """Reads control files (implemented in the persistence layer)."""

    def file_exists(self, path: Path) -> bool: ...


class ControlFilesService:
    def __init__(self, store: ControlFilesStore) -> None:
        self._store = store

    def feature_spec_exists(self, worktree: Path, feature_name: str) -> bool:
        """True when `<worktree>/.devpipe/<feature_name>/feature-spec.md` exists;
        always False for an empty feature name."""
        if not feature_name:
            return False
        return self._store.file_exists(feature_spec_file(worktree, feature_name))

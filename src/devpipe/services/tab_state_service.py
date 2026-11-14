"""Load and save the state file of a pipeline tab."""

from pathlib import Path
from typing import Protocol

from devpipe.models.tab_state import TabState


class TabStateStore(Protocol):
    """Where tab states are kept (implemented in the persistence layer).

    Both methods raise TabStateError on failure.
    """

    def load(self, path: Path) -> TabState: ...

    def save(self, path: Path, state: TabState) -> None: ...


class TabStateService:
    def __init__(self, store: TabStateStore) -> None:
        self._store = store

    def load(self, path: Path) -> TabState:
        """Raises TabStateError."""
        return self._store.load(path)

    def save(self, path: Path, state: TabState) -> None:
        """Raises TabStateError."""
        self._store.save(path, state)

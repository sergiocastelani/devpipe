from pathlib import Path

import pytest

from devpipe.models.tab_state import TabState, TabStateError
from devpipe.persistence.tab_state_repository import TabStateRepository
from devpipe.services.tab_state_service import TabStateService


class FakeTabStateStore:
    """Records calls; returns a preset state from `load` or raises a preset error."""

    def __init__(self, state=None, error=None):
        self.state = state
        self.error = error
        self.calls = []

    def load(self, path):
        self.calls.append(("load", path))
        if self.error is not None:
            raise self.error
        return self.state

    def save(self, path, state):
        self.calls.append(("save", path, state))
        if self.error is not None:
            raise self.error


def test_load_returns_store_state():
    p = Path("s.json")
    state = TabState("a")
    store = FakeTabStateStore(state=state)
    assert TabStateService(store).load(p) is state
    assert store.calls == [("load", p)]


def test_save_passes_path_and_state_to_store():
    p = Path("s.json")
    store = FakeTabStateStore()
    TabStateService(store).save(p, TabState("a"))
    assert store.calls == [("save", p, TabState("a"))]


def test_errors_propagate_unchanged():
    p = Path("s.json")
    error = TabStateError(p, "boom")
    service = TabStateService(FakeTabStateStore(error=error))
    with pytest.raises(TabStateError) as info:
        service.load(p)
    assert info.value is error
    with pytest.raises(TabStateError) as info:
        service.save(p, TabState("a"))
    assert info.value is error


def test_works_with_real_repository(tmp_path):
    service = TabStateService(TabStateRepository())
    path = tmp_path / "s.json"
    state = TabState("new-feature")
    service.save(path, state)
    assert service.load(path) == state

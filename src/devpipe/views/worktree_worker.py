"""Run one worktree creation off the UI thread (snapshot, run, recovery on error)."""

from PySide6.QtCore import QThread, Signal

from devpipe.models.worktree import WorktreeRequest
from devpipe.services.worktree_service import WorktreeService


class WorktreeWorker(QThread):
    """One run: snapshot, create_worktrees, and recover if create_worktrees raises.

    Exactly one of the two signals is emitted per run, from the worker thread; slots of
    objects living in the UI thread receive it queued, on the UI thread.
    """

    results_ready = Signal(object)  # list[WorktreeResult], one per request, in order
    error_occurred = Signal(str)  # error text: the snapshot or the recovery raised

    def __init__(
        self, service: WorktreeService, feature_name: str, requests: list[WorktreeRequest]
    ) -> None:
        super().__init__()
        self._service = service
        self._feature_name = feature_name
        self._requests = list(requests)

    def run(self) -> None:
        # Broad excepts on purpose: this is the thread boundary, and an exception
        # escaping run() would leave the tab busy forever.
        try:
            snapshot = self._service.snapshot(self._feature_name, self._requests)
        except Exception as exc:
            self.error_occurred.emit(_error_text(exc))
            return
        try:
            results = self._service.create_worktrees(self._feature_name, self._requests)
        except Exception as exc:
            try:
                results = self._service.recover(self._feature_name, snapshot, _error_text(exc))
            except Exception as exc2:
                self.error_occurred.emit(_error_text(exc2))
                return
        self.results_ready.emit(results)


def _error_text(error: Exception) -> str:
    """f"{type(error).__name__}: {error}", or only the type name when str(error) is empty."""
    message = str(error)
    name = type(error).__name__
    return f"{name}: {message}" if message else name

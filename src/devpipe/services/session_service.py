"""Remember where state files live between sessions."""

from pathlib import Path
from typing import Protocol

from devpipe.models.control_files import (
    FEATURE_SPEC_FILE_NAME,
    IMPLEMENTATION_LOG_FILE_NAME,
    PLAN_FILE_NAME,
    DevpipeStage,
    feature_folder,
)
from devpipe.models.tab_state import TabState
from devpipe.services.window_state_service import ConfigStore


class ControlFilesStore(Protocol):
    """Reads control files (implemented in the persistence layer)."""

    def file_exists(self, path: Path) -> bool: ...


class SessionService:
    def __init__(self, store: ConfigStore, control_files: ControlFilesStore) -> None:
        self._store = store
        self._control_files = control_files

    def devpipe_stage(self, tab: TabState) -> DevpipeStage:
        """The stage of `tab`'s feature, from the control files in
        `<main worktree>/.devpipe/<feature-name>/` (the main worktree is the first one):

        CREATE without `feature-spec.md`, else PLAN without `plan.md`, else STEPS
        without `implementation-log.md`, else IMPLEMENTATION.
        Always CREATE when the tab has no worktree or no feature name.
        """
        if not tab.worktrees or not tab.feature_name:
            return DevpipeStage.CREATE
        folder = feature_folder(tab.worktrees[0], tab.feature_name)
        for file_name, stage in (
            (FEATURE_SPEC_FILE_NAME, DevpipeStage.CREATE),
            (PLAN_FILE_NAME, DevpipeStage.PLAN),
            (IMPLEMENTATION_LOG_FILE_NAME, DevpipeStage.STEPS),
        ):
            if not self._control_files.file_exists(folder / file_name):
                return stage
        return DevpipeStage.IMPLEMENTATION

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

    def open_files(self) -> list[Path]:
        """State files of the last session's saved tabs, in tab order (may hold invalid files)."""
        return list(self._store.load().open_state_files)

    def active_file(self) -> Path | None:
        """State file of the tab that was selected, or None."""
        return self._store.load().active_state_file

    def remember_session(self, files: list[Path], active: Path | None) -> None:
        """Store the open state files (in order) and the active one as absolute paths.

        Load-modify-save: every other setting is kept. Store errors propagate.
        """
        config = self._store.load()
        config.open_state_files = [path.absolute() for path in files]
        config.active_state_file = active.absolute() if active is not None else None
        self._store.save(config)

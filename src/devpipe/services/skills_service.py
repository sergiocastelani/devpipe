"""Install or update devpipe's agent skills in an agent's skills folder."""

from pathlib import Path
from typing import Protocol


class SkillsStore(Protocol):
    """Copies skill files (implemented in the persistence layer)."""

    def copy_contents(self, source: Path, destination: Path) -> None:
        """Copy every entry of `source` into `destination`, replacing same-named
        entries. Raises SkillsInstallError."""
        ...


class SkillsService:
    def __init__(self, store: SkillsStore, skills_folder: Path) -> None:
        self._store = store
        self._skills_folder = skills_folder

    def install(self, destination: Path) -> None:
        """Copy all files and folders of the skills folder into `destination`,
        replacing anything of the same name. Raises SkillsInstallError."""
        self._store.copy_contents(self._skills_folder, destination)

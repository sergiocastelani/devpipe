"""Copy devpipe's agent skills folder into a destination folder (no Qt)."""

import os
import shutil
import stat
from pathlib import Path

from devpipe.models.skills import SkillsInstallError

IGNORED_PATTERNS = ("__pycache__",)
SOURCE_NOT_FOUND_REASON = "skills folder not found"
DESTINATION_INSIDE_SOURCE_REASON = "destination is inside the skills folder"


class SkillsFiles:
    """The real SkillsStore: plain file system copies."""

    def copy_contents(self, source: Path, destination: Path) -> None:
        """Copy every file and folder directly inside `source` into `destination`
        (created when missing). An entry of the same name already in `destination`
        is deleted first, so it is replaced as a whole; other entries are kept.

        Raises SkillsInstallError on failure.
        """
        if not source.is_dir():
            raise SkillsInstallError(source, SOURCE_NOT_FOUND_REASON)
        if destination.resolve().is_relative_to(source.resolve()):
            raise SkillsInstallError(destination, DESTINATION_INSIDE_SOURCE_REASON)
        ignore = shutil.ignore_patterns(*IGNORED_PATTERNS)
        try:
            destination.mkdir(parents=True, exist_ok=True)
            for entry in sorted(source.iterdir()):
                if entry.name in IGNORED_PATTERNS:
                    continue
                target = destination / entry.name
                _remove(target)
                if entry.is_dir():
                    shutil.copytree(entry, target, ignore=ignore)
                else:
                    shutil.copy2(entry, target)
        except OSError as error:
            raise SkillsInstallError(destination, str(error)) from error


def _remove(path: Path) -> None:
    """Delete `path` (file, link or folder tree); nothing when it does not exist."""
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path, onexc=_make_writable_and_retry)
    elif path.exists() or path.is_symlink():
        path.chmod(stat.S_IWRITE)
        path.unlink()


def _make_writable_and_retry(function, path, _exc) -> None:
    """rmtree error handler: clear the read-only flag (Windows) and retry once."""
    os.chmod(path, stat.S_IWRITE)
    function(path)

"""Read devpipe's control files in a worktree (no Qt)."""

from pathlib import Path


class ControlFiles:
    """The real ControlFilesStore: plain file system checks."""

    def file_exists(self, path: Path) -> bool:
        """True when `path` is an existing file (False on any OS error)."""
        try:
            return path.is_file()
        except OSError:
            return False

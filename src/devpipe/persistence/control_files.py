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

    def read_text(self, path: Path) -> str | None:
        """The UTF-8 text of the file at `path` (None when it is missing, unreadable or not UTF-8)."""
        try:
            return path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return None

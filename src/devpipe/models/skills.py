"""Errors of the agent skills installation (no Qt, no I/O)."""

from pathlib import Path


class SkillsInstallError(Exception):
    """The agent skills could not be copied into a destination folder."""

    def __init__(self, path: Path, reason: str) -> None:
        super().__init__(f"{path}: {reason}")
        self.path = path
        self.reason = reason

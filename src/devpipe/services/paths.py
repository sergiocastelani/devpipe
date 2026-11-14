"""Pure helpers for state file paths (no Qt)."""

import os
from pathlib import Path


def same_file(a: Path, b: Path) -> bool:
    """True when `a` and `b` name the same file.

    Compares after Path.resolve() (absolute, `..` removed, symlinks followed;
    the files need not exist), case-insensitively on Windows (os.path.normcase).
    """
    return os.path.normcase(a.resolve()) == os.path.normcase(b.resolve())


def with_default_suffix(path: Path, suffix: str) -> Path:
    """`path` with `suffix` appended when it has no extension, else `path` unchanged."""
    return path if path.suffix else path.with_name(path.name + suffix)

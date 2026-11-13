"""Feature name normalization: turns free text into a feature slug."""

import re
import unicodedata

SLUG_SEPARATOR = "-"
_SLUG_CHARS = frozenset("abcdefghijklmnopqrstuvwxyz0123456789")
# Unicode major categories treated as word separators: separators (Z),
# punctuation (P, includes "-" and "_"), symbols (S), control/other (C, includes tab and newline).
_SEPARATOR_CATEGORIES = frozenset({"Z", "P", "S", "C"})
_SEPARATOR_RUN = re.compile(r"-+")


def normalize_feature_name(text: str) -> str:
    """Return the slug of `text`, or "" when nothing usable is left.

    The result is "" or matches ^[a-z0-9]+(-[a-z0-9]+)*$.
    """
    decomposed = unicodedata.normalize("NFKD", text).lower()
    mapped = "".join(_map_char(ch) for ch in decomposed)
    return _SEPARATOR_RUN.sub(SLUG_SEPARATOR, mapped).strip(SLUG_SEPARATOR)


def _map_char(ch: str) -> str:
    """Keep slug characters, turn separators into a hyphen, drop the rest."""
    if ch in _SLUG_CHARS:
        return ch
    if unicodedata.category(ch)[0] in _SEPARATOR_CATEGORIES:
        return SLUG_SEPARATOR
    return ""

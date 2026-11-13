"""Read/write tab state files (one JSON file per saved pipeline tab)."""

import json
from pathlib import Path

from devpipe.models.tab_state import (
    STATE_FILE_VERSION,
    Panel,
    TabState,
    TabStateError,
    is_valid_feature_name,
)

_VERSION_KEY = "version"
_FEATURE_NAME_KEY = "feature_name"
_ACTIVE_PANEL_KEY = "active_panel"
_PANEL_VALUES = frozenset(panel.value for panel in Panel)


def _os_error_text(exc: OSError) -> str:
    return exc.strerror or str(exc)


class TabStateRepository:
    def load(self, path: Path) -> TabState:
        """Read and validate the file. Raises TabStateError (only)."""
        return self._parse(path, self._read_json(path))

    def save(self, path: Path, state: TabState) -> None:
        """Write the file (overwrites).

        Raises TabStateError (only) for a well-typed `state`; a wrongly typed
        `state` is a programming error and its exception propagates.
        """
        if not is_valid_feature_name(state.feature_name):
            raise TabStateError(path, "invalid feature_name")
        data = {
            _VERSION_KEY: STATE_FILE_VERSION,
            _FEATURE_NAME_KEY: state.feature_name,
            _ACTIVE_PANEL_KEY: state.active_panel.value,
        }
        try:
            path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        except OSError as exc:
            raise TabStateError(path, f"cannot write file: {_os_error_text(exc)}") from exc

    def _read_json(self, path: Path) -> object:
        try:
            text = path.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            raise TabStateError(path, "file not found") from exc
        except OSError as exc:
            raise TabStateError(path, f"cannot read file: {_os_error_text(exc)}") from exc
        except UnicodeDecodeError as exc:
            raise TabStateError(path, "not valid UTF-8 text") from exc
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise TabStateError(
                path, f"not valid JSON: {exc.msg} (line {exc.lineno}, column {exc.colno})"
            ) from exc
        except (ValueError, RecursionError) as exc:
            # Content json.loads rejects without a JSONDecodeError: integers
            # beyond Python's digit limit, nesting beyond the recursion limit.
            raise TabStateError(path, f"not valid JSON: {exc}") from exc

    def _parse(self, path: Path, data: object) -> TabState:
        if not isinstance(data, dict):
            raise TabStateError(path, "not a JSON object")

        if _VERSION_KEY not in data:
            raise TabStateError(path, "missing version")
        version = data[_VERSION_KEY]
        # type() check: bool is a subclass of int and True == 1.
        if type(version) is not int or version != STATE_FILE_VERSION:
            raise TabStateError(path, f"unsupported version: {version!r}")

        if _FEATURE_NAME_KEY not in data:
            raise TabStateError(path, "missing feature_name")
        feature_name = data[_FEATURE_NAME_KEY]
        if isinstance(feature_name, str) and feature_name == "":
            raise TabStateError(path, "empty feature_name")
        if not isinstance(feature_name, str) or not is_valid_feature_name(feature_name):
            raise TabStateError(path, f"invalid feature_name: {feature_name!r}")

        if _ACTIVE_PANEL_KEY not in data:
            raise TabStateError(path, "missing active_panel")
        active_panel = data[_ACTIVE_PANEL_KEY]
        if not isinstance(active_panel, str) or active_panel not in _PANEL_VALUES:
            raise TabStateError(path, f"unknown active_panel: {active_panel!r}")

        return TabState(feature_name, Panel(active_panel))

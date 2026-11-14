"""Read/write tab state files (one JSON file per saved pipeline tab)."""

import json
from pathlib import Path

from devpipe.models.tab_state import (
    PERSISTED_PANELS,
    STATE_FILE_VERSION,
    Panel,
    TabState,
    TabStateError,
    is_valid_feature_name,
)

_VERSION_KEY = "version"
_FEATURE_NAME_KEY = "feature_name"
_ACTIVE_PANEL_KEY = "active_panel"
_WORKTREES_KEY = "worktrees"
_V1 = 1  # the format without `worktrees`
_READABLE_VERSIONS = frozenset({_V1, STATE_FILE_VERSION})
_PANEL_VALUES = frozenset(panel.value for panel in PERSISTED_PANELS)
_INVALID_WORKTREES = "invalid worktrees"


def _os_error_text(exc: OSError) -> str:
    return exc.strerror or str(exc)


class TabStateRepository:
    def load(self, path: Path) -> TabState:
        """Read and validate the file. Raises TabStateError (only)."""
        return self._parse(path, self._read_json(path))

    def save(self, path: Path, state: TabState) -> None:
        """Write the file (overwrites) in the current format (version 2).

        Raises TabStateError (only) for a well-typed `state`; a wrongly typed `state`
        or an `active_panel` outside PERSISTED_PANELS is a programming error:
        the latter raises ValueError and nothing is written.
        """
        if state.active_panel not in PERSISTED_PANELS:
            raise ValueError(f"panel is not persisted: {state.active_panel}")
        if not is_valid_feature_name(state.feature_name):
            raise TabStateError(path, "invalid feature_name")
        data = {
            _VERSION_KEY: STATE_FILE_VERSION,
            _FEATURE_NAME_KEY: state.feature_name,
            _ACTIVE_PANEL_KEY: state.active_panel.value,
            _WORKTREES_KEY: [str(worktree) for worktree in state.worktrees],
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
        if type(version) is not int or version not in _READABLE_VERSIONS:
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

        worktrees = self._parse_worktrees(path, data) if version != _V1 else []

        return TabState(feature_name, Panel(active_panel), worktrees)

    def _parse_worktrees(self, path: Path, data: dict) -> list[Path]:
        """The v2 `worktrees` list as Paths. Raises TabStateError(path, "invalid worktrees")
        when the key is missing, is not a list, or holds an item that is not a non-empty str."""
        worktrees = data.get(_WORKTREES_KEY)
        if not isinstance(worktrees, list):
            raise TabStateError(path, _INVALID_WORKTREES)
        if not all(isinstance(item, str) and item != "" for item in worktrees):
            raise TabStateError(path, _INVALID_WORKTREES)
        return [Path(item) for item in worktrees]

# Design Contract: Tab state file

- **Plan:** [plan.md](plan.md)
- **Updated:** 2026-11-13

## 1. Step status
| Step | Title | Status | File |
|------|-------|--------|------|
| S01 | Tabs hold a panel stack with an unsaved start panel | approved | [step-01.md](step-01.md) |
| S02 | Tab state files can be written and read back with validation | approved | [step-02.md](step-02.md) |
| S03 | First save ties a tab to a state file, then auto-saves | approved | [step-03.md](step-03.md) |
| S04 | Open tabs are kept in config.json and restored at startup | approved | [step-04.md](step-04.md) |
| S05 | File > Open loads a state file into a tab | approved | [step-05.md](step-05.md) |

Status: pending | draft | approved

## 2. Shared items
Names that cross steps (as assigned by the plan). Existing items: `MainWindow.tabs` (`QTabWidget`), `WindowStateService`, `ConfigStore` (Protocol in `services/window_state_service.py`), `AppConfig`, `ConfigRepository`.

| Item | Kind | Created by | Used / extended by | Notes |
|------|------|-----------|--------------------|-------|
| `normalize_feature_name(text) -> str` | function (`models/feature_name.py`) | S01 | - | pure; `""` or a valid slug `^[a-z0-9]+(-[a-z0-9]+)*$` |
| `StartPanel` (`name_input`, `slug_label`, `save_button`, `open_button`, `create_button`) | widget class (`views/start_panel.py`) | S01 | S03 | unsaved mode by default; Open/Create disabled until saved |
| `StartPanel.save_requested(str)` | Qt signal | S01 | S03 | emitted with the non-empty slug on Save click |
| `StartPanel.show_saved(feature_name)` | method | S01 | S03 | switches to saved mode (one-way) |
| `PipelineTab` (`stack`, `start_panel`, `title()`, `tooltip()`, `identity_changed`) | widget class (`views/pipeline_tab.py`) | S01 | S03, S04 | `title()` = "New pipeline", `tooltip()` = "" while unsaved |
| `MainWindow.add_pipeline_tab(tab) -> int` | method | S01 | S03, S04 | single insertion point; refreshes text/tooltip on `identity_changed` |
| `MainWindow.add_new_tab() -> PipelineTab` | method | S01 | S03, S04 | adds and selects an unsaved tab |
| `MainWindow.close_tab(index) -> None` | method | S01 | S04 | single removal point; adds a tab when none is left |
| `MainWindow.new_tab_button` | widget (`QToolButton` "+") | S01 | - | top-right corner widget of `tabs` |
| "Tabs and panels" section, views lines of layout tree | doc region (`docs/architecture.md`) | S01 | - | describes the panel-stack structure |
| `Panel` | enum (`models/tab_state.py`) | S02 | S03, S04, S05 | `START = "start"`; values are the `active_panel` strings |
| `TabState` | dataclass (`models/tab_state.py`) | S02 | S03, S04, S05 | `feature_name: str`, `active_panel: Panel = Panel.START` |
| `STATE_FILE_VERSION`, `is_valid_feature_name(name)` | constant, function (`models/tab_state.py`) | S02 | - | version 1; `fullmatch` of `^[a-z0-9]+(-[a-z0-9]+)*$` |
| `TabStateError(path, reason)` | exception (`models/tab_state.py`) | S02 | S03, S04, S05 | attributes `path`, `reason`; `str()` = `f"{path}: {reason}"` |
| `TabStateRepository` | class (`persistence/tab_state_repository.py`) | S02 | S03 (wiring) | no constructor args; `load(path)`, `save(path, state)`; only `TabStateError` (for well-typed input) |
| `TabStateStore`, `TabStateService(store)` | Protocol, service (`services/tab_state_service.py`) | S02 | S03, S04, S05 | `load(path)`, `save(path, state)` pass-through; not wired in `app.py` by S02 |
| Persistence row of the layer table | doc region (`docs/architecture.md`) | S02 | - | lists tab state files |
| `AppConfig.last_state_folder` + `last_state_folder` key | model field, config key | S03 | S04 (adds sibling fields) | `Path \| None`; `ConfigRepository` reads a non-empty string as Path, else None; always writes the key (`null` when unset) |
| `SessionService(store: ConfigStore)` (`start_folder()`, `remember_folder(state_file)`) | service (`services/session_service.py`) | S03 | S04 (adds methods), S05 | home fallback when folder unset or not an existing folder; `app.py` shares one `ConfigRepository` with `WindowStateService` |
| `same_file(a, b)` | function (`services/paths.py`) | S03 | - (through `find_tab`) | `os.path.normcase(a.resolve()) == os.path.normcase(b.resolve())` |
| `PipelineTab.state_path`, `active_panel` (read-only properties), `show_panel(panel)`, `apply_saved(path, state)`, saved-mode `title()` / `tooltip()` | attributes, methods | S03 | S04, S05 | constructor now takes `TabStateService`; `apply_saved` never writes; `show_panel` auto-saves when saved; saved `title()` = feature name, `tooltip()` = full path |
| `MainWindow(window_state, tab_states, session)` | constructor | S03 | S04, S05 | injected services; `save_requested` connected inside `add_pipeline_tab` |
| `MainWindow.find_tab(path) -> int \| None` | method | S03 | S05 | uses `same_file` |
| `MainWindow.add_saved_tab(path, state) -> PipelineTab` | method | S03 | S04, S05 | adds, selects and returns a saved tab |
| `make_window` | pytest fixture (`tests/views/conftest.py`) | S03 | S04, S05 | same `tmp_path / "config.json"` on every call; registered with `qtbot` |
| `AppConfig.open_state_files: list[Path]`, `AppConfig.active_state_file: Path \| None` + `open_state_files` / `active_state_file` keys | model fields, config keys | S04 | - | defaults empty / `None`; invalid list items skipped; both keys always written by `ConfigRepository.save` |
| `SessionService.open_files()`, `active_file()`, `remember_session(files, active)` | methods | S04 | - | `remember_session` stores absolute paths (load-modify-save) |
| `MainWindow.open_action` | `QAction` | S05 | - | "&Open...", Ctrl+O, in the "&File" menu of the window's menu bar |
| Session sync / startup restore in `MainWindow` | behavior | S04 | - | sync on `add_pipeline_tab`, `identity_changed`, end of `close_tab`, `currentChanged`, `tabMoved`; tabs movable; startup writes only when the restored session differs from the stored one; no writes after `closeEvent` |

## 3. Decisions
Decisions approved during a step's review, each about that step's own work only.
- (S01) Slug rule follows FR-08 and the devpipe-create skill rule: separators (Unicode categories Z, P, S, C) become one hyphen; other characters outside `a-z0-9` are dropped ("Straße" -> `strae`).
- (S01) The "+" new-tab button is the top-right corner widget of the tab bar.
- (S01) Texts: input placeholder "Feature name"; "+" tooltip "New pipeline tab".
- (S01) `README.md` example test commands are updated to `test_start_panel.py` / `start_panel`.
- (S02) Loading: a missing `active_panel` makes the file invalid; extra keys are ignored.
- (S02) `save` refuses an invalid `feature_name` with `TabStateError(path, "invalid feature_name")`.
- (S02) The file is written like `config.json` (`write_text`, platform newlines, not atomic).
- (S02) `save` raises only `TabStateError` for a well-typed `TabState`; a wrongly typed one is a programming error and its exception propagates.
- (S03) UI texts: Save dialog caption "Save pipeline state"; warning titles "Cannot save state file" and "State file already open"; message "This state file is already open in another tab."
- (S03) S03 also edits `tests/views/test_pipeline_tab.py`, because the `PipelineTab` constructor now takes `TabStateService`.
- (S03) A failed `config.json` write after a successful state file write is not handled (same as `window_maximized`).
- (S03) `PipelineTab.save_as(path, feature_name) -> bool` writes first, then calls `apply_saved`; all tab writes go through one internal method that shows the write-error warning.
- (S04) Tabs are movable (`tabs.setMovable(True)`) so reordering is possible.
- (S04) Startup writes `config.json` only when the restored session differs from the stored one.
- (S04) One guard line at the start of `MainWindow.closeEvent` stops session writes during teardown.
- (S04) When the selected tab is unsaved, the stored `active_state_file` is kept if that tab is still open, else `None`.
- (S05) Picking a file that is already open selects its tab and also stores the last-used folder (from that tab's own `state_path`); the file is not read.
- (S05) Menu texts use mnemonics: "&File" and "&Open..." (Alt+F, O).
- (S05) UI texts: Open dialog title "Open pipeline state"; warning title "Cannot open state file" (body: path, blank line, reason).
- (S05) The duplicate check (`find_tab`) runs before the file is read; cancel and invalid files leave `last_state_folder` unchanged.

# Design Contract: create-worktrees

- **Plan:** [plan.md](plan.md)
- **Updated:** 2026-11-14

## 1. Step status
| Step | Title | Status | File |
|------|-------|--------|------|
| S01 | Tab state file v2 keeps the tab's worktree list | approved | [step-01.md](step-01.md) |
| S02 | Start panel lists the tab's worktrees and opens them | approved | [step-02.md](step-02.md) |
| S03 | Worktree creation use case with the git infrastructure layer | approved | [step-03.md](step-03.md) |
| S04 | New worktree panel: edit groups of folders | approved | [step-04.md](step-04.md) |
| S05 | New worktree panel shows run results and the retry state | approved | [step-05.md](step-05.md) |
| S06 | "Create new worktree" button opens the New worktree panel | approved | [step-06.md](step-06.md) |
| S07 | Create runs in the background, saves the worktrees and returns to start | approved | [step-07.md](step-07.md) |
| S08 | Closing a tab or the window is refused while a run is in progress | approved | [step-08.md](step-08.md) |

Status: pending | draft | approved

## 2. Shared items
Names that cross steps. Filled in as each step is approved.

| Item | Kind | Created by | Used / extended by | Notes |
|------|------|-----------|--------------------|-------|
| `STATE_FILE_VERSION` (= 2) | constant, `models/tab_state.py` | S01 | - | Written version; reader accepts 1 and 2 |
| `TabState.worktrees: list[Path]` | dataclass field | S01 | S02 | Saved order, default `[]`; written as `str(path)`, loaded as `Path(item)` (whitespace-only and relative entries accepted as written) |
| `Panel.NEW_WORKTREE = "new-worktree"` | enum value | S01 | S06 | Never persisted; rejected on load as `unknown active_panel` |
| `PERSISTED_PANELS` = `frozenset({Panel.START})` | constant, `models/tab_state.py` | S01 | S06 | `TabStateRepository.save` raises `ValueError` (before any I/O) for a panel outside it |
| `PipelineTab._worktrees: list[Path]` | attribute | S01 | S07 | `[]` for a new tab; copy of `state.worktrees` after `apply_saved`; a copy is written by `save_as` and `_current_state()` on every write; may be replaced/appended |
| `WorktreeRequest(source: Path, parent: Path)` | frozen dataclass, `models/worktree.py` | S03 | S04, S07 | Paths as entered by the user |
| `WorktreeResult(request, target: Path, error: str \| None)` + `ok` | frozen dataclass, `models/worktree.py` | S03 | S05, S07 | All fields required; `target = (request.parent / feature_name).resolve()` on success and failure; `ok` is `error is None` |
| `GitWorktreeError(message: str)` | exception, `models/worktree.py` | S03 | S07 (fake in tests, recovery) | Message in `str(error)` and `.message` |
| `GitWorktrees` | Protocol, `services/worktree_service.py` | S03 | S07 (extends with `branch_exists`, `is_worktree`, `remove_worktree`; fake in tests) | `add_worktree(source: Path, branch: str, target: Path) -> None`; raises `GitWorktreeError` |
| `WorktreeService(git: GitWorktrees)` | class, `services/worktree_service.py` | S03 | S07 (extends with `snapshot`, `recover`) | - |
| `WorktreeService.create_worktrees(feature_name, requests) -> list[WorktreeResult]` | method | S03 | S07 | Sync, sequential, one result per request in order; raises `ValueError` only for an invalid feature name; per-request failures become results |
| `WorktreeService.merge_paths(existing, new) -> list[Path]` | method | S03 | S07 | New list, inputs unchanged; skips duplicates by `same_file` (also among new) |
| `SubprocessGitWorktrees` | class, `infrastructure/git_worktrees.py` | S03 | S07 (extends with the recovery methods) | Real `GitWorktrees`; no-arg constructor; built in `app.py` |
| `devpipe.infrastructure` | package / import-linter layer | S03 | S07 (`app.py` only) | Sibling of persistence (`"devpipe.persistence \| devpipe.infrastructure"`); no Qt; never imported by views |
| `StartPanel.show_worktrees(paths: list[Path]) -> None` | method | S02 | S07 | Clears and refills the list with `str(path)` in order; shows label + list when non-empty, hides both when empty; may be called any number of times |
| `StartPanel.worktrees_label` (`QLabel`, `WORKTREES_LABEL_TEXT = "Worktrees"`), `StartPanel.worktrees_list` (`QListWidget`) | widgets / constant, `views/start_panel.py` | S02 | - | Last two items of the start panel root layout, below the big-button column (which is unchanged and keeps stretch 1) |
| `NewWorktreePanel()` | widget class, `views/new_worktree_panel.py` | S04 | S05, S06, S07 | No-arg constructor; ends by calling `reset()` |
| `NewWorktreePanel.create_requested = Signal(list)` | signal | S04 | S07 | `list[WorktreeRequest]` from `Path(text.strip())` of `editable_groups()`, in display order |
| `NewWorktreePanel.groups()`, `editable_groups()` | methods | S04 | S05 | All / unlocked groups in display order; editable groups match the last emitted requests one to one while no group is added, removed or locked |
| `NewWorktreePanel.reset()` | method | S04 | S05 (extends), S06 | Deletes every group, adds one empty unlocked group; extendable to clear added state |
| `NewWorktreePanel.add_button` ('+'), `create_button` (`CREATE_TEXT = "Create"`) | widgets | S04 | S05 (relabels `create_button`) | Create's enablement is computed by the panel: all unlocked groups filled (trimmed), True when no group is unlocked |
| `WorktreeGroup` (`QGroupBox`): `source_input`, `parent_input` (`QLineEdit`), `source_picker`, `parent_picker`, `remove_button` (`QToolButton`), `set_locked(locked)`, `is_locked()` | widget class, `views/new_worktree_panel.py` | S04 | S05 | Locked = read-only inputs, disabled pickers, no '-', excluded from the Create check and from requests; locking refreshes Create; others may set style sheet, tooltip and accessible description |
| New worktree panel layout | layout | S04 | S05 | Scroll area with the groups, then '+', then Create; others may insert widgets between '+' and Create |
| `NewWorktreePanel.set_busy(busy: bool) -> None` | method | S05 | S07 | True: groups (scroll area), '+', '-', pickers and Create disabled, progress bar shown; False restores (locked groups stay locked); error box stays readable |
| `NewWorktreePanel.show_results(results: list[WorktreeResult]) -> None` | method | S05 | S07 | Pairs `results[i]` with `editable_groups()[i]` read at call time; `ValueError` and no change if counts differ; ok -> green border, locked, "Created: <target>"; failed -> red border, editable, "Failed: <error>"; does not change busy state |
| `NewWorktreePanel.error_box` (`QPlainTextEdit`, read-only), `progress_bar` (`QProgressBar`, 0-0) | widgets | S05 | - | Between '+' and Create (order: '+', error box, progress bar, Create); error box lists only the latest failures, `"{source} → {target}: {error}"`, hidden when empty |
| `RETRY_TEXT = "Retry"` | constant, `views/new_worktree_panel.py` | S05 | - | Create relabeled once results with a failure are shown; stays until `reset()` |
| `StartPanel.new_worktree_button` (`NEW_WORKTREE_TEXT = "Create new worktree"`) | widget / constant, `views/start_panel.py` | S06 | - | Built with `_big_button`, first in the centered big-button column; disabled until `show_saved` |
| `StartPanel.new_worktree_requested = Signal()` | signal | S06 | - | Emitted on click |
| `PipelineTab.new_worktree_panel` (`NewWorktreePanel`) | attribute | S06 | S07 | Stack index 1, registered as `_panels[Panel.NEW_WORKTREE]` |
| `PipelineTab.open_new_worktree_panel() -> None` | method | S06 | - | `reset()` the panel, then `show_panel(Panel.NEW_WORKTREE)` (auto-save as usual) |
| Persisted-panel mapping in `PipelineTab` | behavior | S06 | - | Private `_persisted_panel()`: active panel if in `PERSISTED_PANELS`, else `Panel.START`; used by `_current_state()` and `save_as`; `active_panel` still reports the panel shown |
| `PipelineTab(tab_states, worktrees)`, `MainWindow(window_state, tab_states, session, worktrees)` | constructors | S07 | S08 | `WorktreeService` injected from `app.py`; stored as `PipelineTab._worktree_service` |
| `PipelineTab.run_in_progress` | property | S07 | S08 | True from the Create click until the outcome is applied (including any warning box) |
| `PipelineTab.run_finished` | signal | S07 | S08 | Emitted right after `run_in_progress` turns False |
| `RUN_ERROR_TITLE = "Worktree creation failed"` | constant, `views/pipeline_tab.py` | S07 | - | Fallback warning when snapshot/recovery raises; nothing is written |
| `WorktreeWorker` (`QThread`): `results_ready(object)`, `error_occurred(str)` | class, `views/worktree_worker.py` | S07 | - | snapshot -> `create_worktrees` -> `recover` on exception; exactly one signal per run; error text `"<Type>: <message>"` |
| `PreRunState(request, target, target_existed, branch_existed)` | frozen dataclass, `models/worktree.py` | S07 | - | One per request, taken before a run |
| `GitWorktrees.branch_exists(source, branch) -> bool`, `is_worktree(source, branch, target) -> bool`, `remove_worktree(source, branch, target, delete_branch) -> None` | Protocol methods + `SubprocessGitWorktrees` impl | S07 | - | Built on `git worktree list --porcelain`; raise `GitWorktreeError` |
| `WorktreeService.snapshot(feature_name, requests) -> list[PreRunState]`, `recover(feature_name, snapshot, error) -> list[WorktreeResult]` | methods | S07 | - | `branch_exists` error counts as existing; recover verifies all first, then cleans up |
| `CLEANED_UP_MESSAGE`, `CLEANUP_FAILED_MESSAGE` | constants, `services/worktree_service.py` | S07 | - | `"unexpected error: {error}; cleaned up"`, `"unexpected error: {error}; cleanup failed: {cleanup_error}"` |
| `FakeGitWorktrees`, `fake_git` / `worktree_service` fixtures | test helpers, `tests/views/conftest.py` | S07 | S08 | Per-target outcome (`GitWorktreeError` = normal failure, other exception = unexpected); `gate` event (5 s timeout), `branch_check_error`, `remove_error` |
| `RUN_IN_PROGRESS_TITLE = "Worktree creation in progress"`, `RUN_IN_PROGRESS_TEXT = "Wait for the worktree creation to finish before closing."` | constants, `views/main_window.py` | S08 | - | Shown by private `_refuse_close()` via `QMessageBox.information` |

## 3. Decisions
Decisions approved during a step's review, each about that step's own work only.
- (S01) The reader accepts versions 1 and 2; `worktrees` is validated only in v2 files (missing, not a list, or an item that is not a non-empty string -> `TabStateError(path, "invalid worktrees")`); a `worktrees` key in a v1 file is ignored.
- (S01) Whitespace-only and relative `worktrees` entries are accepted on load and kept as written (confirmed by the user).
- (S01) Written key order: `version`, `feature_name`, `active_panel`, `worktrees`.
- (S01) `tests/views/test_session_restore.py` is left unchanged; the v1 `write_state` helper and the `"active_panel": "process"` row in `tests/views/test_file_open.py` stay on version 1 on purpose.
- (S03) `create_worktrees` raises `ValueError` for a feature name that is not a valid slug (`is_valid_feature_name`), before any request (confirmed by the user).
- (S03) Per-request checks in order: source is a folder, parent is a folder, target does not exist; a regular file counts as "does not exist". Git is called with `source.resolve()`; the result keeps the request as given.
- (S03) A source that is a subfolder of a repository (not its root) is accepted; the worktree is made from the enclosing repository (confirmed by the user).
- (S03) Messages: "source folder does not exist", "parent folder does not exist", "target folder already exists", "not a git repository", "default branch not found", "git not found", "cannot run git: ...", git's stderr (or "git exited with code N" when empty).
- (S03) `src/devpipe/services/__init__.py` docstring lists `devpipe.infrastructure` as importable; no `CREATE_NO_WINDOW` flag on Windows.
- (S02) `PipelineTab.apply_saved` calls `start_panel.show_worktrees(state.worktrees)` right after `show_saved`.
- (S02) Double-click (`itemDoubleClicked`) rebuilds the path from the item text; `Path.is_dir()` false -> warning "Folder not found" / "Folder not found: {path}" (relative or whitespace-only entries checked as written, confirmed by the user).
- (S02) If `QDesktopServices.openUrl` returns False, a warning "Cannot open folder" / "Cannot open folder: {path}" is shown (user decision); the list is never changed.
- (S04) Button texts "+", "-" and "..." with tooltips / accessible names "Add worktree", "Remove worktree", "Choose source project folder", "Choose worktree parent folder"; the picker tooltip is also the dialog caption (confirmed by the user).
- (S04) A chosen folder is written as `str(Path(chosen))` (native separators); the picker starts in the input's folder when it exists, else `""`.
- (S04) `WorktreeGroup` also has step-private public helpers `changed`, `remove_requested`, `set_removable`, `is_filled`, `request`; `set_locked` always emits `changed`.
- (S05) "Retry" stays until `reset()`, even after a later all-success `show_results` (confirmed by the user).
- (S05) While busy, every input control is disabled but the panel widget itself is not, so the error box and progress bar stay readable (confirmed by the user).
- (S05) A failed group keeps its red border and tooltip while edited, until the next `show_results` (confirmed by the user).
- (S05) `reset()` also clears the error box, restores "Create" and calls `set_busy(False)`.
- (S06) The persisted-panel mapping is applied in both `_current_state()` and `save_as` through a private `_persisted_panel()` (confirmed by the user).
- (S06) Opening the panel on a saved tab uses the existing `show_panel` auto-save, rewriting the file with the same content (confirmed by the user).
- (S06) `PipelineTab` connects `start_panel.new_worktree_requested` itself; `main_window.py` is unchanged. `test_tab_shows_start_panel_in_a_stack` now expects a stack count of 2.
- (S07) Recovery never deletes a target folder or branch that existed before the run, nor a folder or branch belonging to another request's verified worktree; such entries get "target folder already exists" (confirmed by the user).
- (S07) Recovery messages: `"unexpected error: {error}; cleaned up"` and `"unexpected error: {error}; cleanup failed: {cleanup_error}"` (confirmed by the user).
- (S07) Create is ignored while a run is in progress or when the tab is unsaved. All ok -> `show_panel(START)` is the single write; any failure -> `show_results` then one `_write`. In the fallback, worktrees created before the error stay on disk unsaved.
- (S07) `tests/views/test_main_window.py` (`IdentityTab`, `add_identity_tab`) and `make_tab` in `test_pipeline_tab.py` are updated for the new constructor argument.
- (S07) `SubprocessGitWorktrees.remove_worktree`: `worktree remove --force` if registered, always `worktree prune`, `rmtree` clearing read-only files, then `branch -D` only if the branch exists and no remaining worktree has it checked out.
- (S08) `close_tab` checks only the tab being closed (after the out-of-range check, before `removeTab`); `closeEvent` refuses as its first statement if any tab has a run in progress, before session sync is disabled and before `remember_maximized`. No "close anyway" option.

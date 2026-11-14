# Feature Request: create-worktrees

- **Date:** 2026-11-14
- **Source:** current session
- **Status:** Ready for implementation

## 1. Summary
Add a "Create new worktree" button to the start panel of a pipeline tab. It opens a
"New worktree" panel in the tab's panel stack, where the user enters one or more
(source project folder, worktree parent folder) pairs. "Create" makes a new git
worktree for each pair, on a new branch. Both the worktree folder and the branch are
named after the tab's feature name. The created worktree folders are saved in the tab
state file and listed at the bottom of the start panel. This lets a user prepare every
repository a feature needs in one step, straight from devpipe.

## 2. Problem and goals
- **Problem:** to start a feature today, the user has to run `git worktree add -b ...`
  by hand in each project and remember where the worktrees went.
- **Goals:**
  - From a saved tab, create N worktrees (N ≥ 1) in a single "Create" action.
  - Every worktree is at `<parent>/<feature-name>` on a new branch `<feature-name>`
    started from the source project's default branch.
  - The created folders are kept in the tab state file and shown on the start panel
    across restarts.
  - A partial failure never loses the successes and can be retried for the failed
    entries only.
- **Non-goals:**
  - Removing or pruning worktrees, deleting branches, or removing entries from the
    saved list.
  - Fetching from remotes, or choosing a base ref other than the default branch.
  - Persisting the in-progress contents of the New worktree panel.
  - Anything that involves AI agents (the app never talks to agents).

## 3. Users and use cases
- As a developer, I want to create worktrees for several projects at once, named after
  my feature, so that I can start working without running git by hand.
- As a developer, I want failed worktrees marked and retryable, so that one bad path
  doesn't make me redo the ones that worked.
- As a developer, I want the start panel to list my feature's worktrees and open them in
  the file explorer, so that I can find them later.

## 4. Functional requirements
**Start panel**
- FR-01: The start panel has a "Create new worktree" button below the feature-name
  input row (name input + Save). It is formatted like the existing big buttons ("Open a
  pipeline", "Create a pipeline"): built with the same `_big_button` helper (same
  minimum size and font size) and centered. It is the first button in the centered
  big-button column, above "Open a pipeline".
- FR-02: The button is disabled until the tab is saved (`show_saved` called), the same
  way as "Open a pipeline" / "Create a pipeline".
- FR-03: Clicking it opens the New worktree panel in the tab's `QStackedWidget`. The
  panel starts fresh every time it opens: exactly one empty group, the default
  (non-retry) state, and an empty error box.
- FR-04: When the tab has at least one saved worktree, the bottom of the start panel
  shows a "Worktrees" label and a list with one entry per saved worktree folder
  (absolute path), in saved order. When there are none, the label and list are hidden.
- FR-05: Double-clicking a list entry opens that folder in the system file explorer. If
  the folder does not exist, a warning message box shows "Folder not found: <path>" and
  the list does not change.

**New worktree panel**
- FR-06: The panel holds a vertical list of input groups. Each group is a grouping
  component (`QGroupBox`) with two labeled rows:
  - "Source project folder": a text input with a folder-picker button on its right.
  - "Worktree parent folder": a text input with a folder-picker button on its right.
- FR-07: Each folder-picker button opens the system's default folder-selection dialog.
  Choosing a folder writes its path into that button's input. Cancelling changes
  nothing.
- FR-08: A '+' button appends a new empty group.
- FR-09: Every group except the first has a '-' button that removes the group. Removed
  groups are not processed.
- FR-10: A "Create" button sits at the bottom of the panel. It is enabled only when
  every *editable* group (pending or failed) has both inputs non-empty after trimming
  whitespace. When there are no editable groups left, it stays enabled (see FR-17).
- FR-11: Clicking Create/Retry processes every editable group in on-screen order, on a
  background thread. While it runs, the whole panel is disabled (inputs, pickers, '+',
  '-', Create/Retry) and a busy indicator is shown.
- FR-12: Processing one group:
  1. Validate: the source folder exists and is a git repository, and the parent folder
     exists (it is **not** created). The target `<parent>/<feature-name>` must not
     exist.
  2. Find the default branch name: the target of `refs/remotes/origin/HEAD` (e.g.
     `origin/main` → `main`) when it is set, else `main` if a local branch `main`
     exists, else `master` if a local branch `master` exists, else fail with "default
     branch not found".
  3. Pick the start point: the local branch with that name, or `origin/<name>` when no
     local branch exists. Never fetch.
  4. Run `git -C <source> worktree add -b <feature-name> <parent>/<feature-name>
     <start-point>`.
  5. Any validation failure, git error (non-zero exit, stderr captured), or missing
     `git` executable fails that group with a readable message.
- FR-13: Every group that succeeds has its worktree folder appended to the tab's saved
  worktree list, and the state file is written once processing ends. A path already in
  the list (compared with `services.paths.same_file`) is not added again.
- FR-14: If every processed group succeeded, the tab returns to the start panel, which
  shows the updated list (FR-04).
- FR-15: If any group failed, the tab stays on the panel:
  - Failed groups get a red border. Succeeded groups get a green border.
  - A read-only multi-line text box at the bottom of the panel shows one error entry
    per failed group, naming the group (source → target) and the message.
  - The "Create" button is relabeled "Retry".
- FR-16: In the retry state:
  - Green groups are locked: inputs and pickers are read-only and there is no '-'.
  - Red groups stay editable and removable ('-' still follows FR-09, so the first
    group can't be removed).
  - '+' still adds new groups, and Retry processes them too.
  - Retry processes only red and new groups, then applies FR-13–FR-15 again (each
    group's border reflects its latest result). After every run the error box shows
    only the latest run's errors.
- FR-17: If Create/Retry is clicked when no editable group remains, the run has no
  failures and the tab returns to the start panel (FR-14).
- FR-18: There is no Back/Cancel button. The panel is left only through FR-14/FR-17,
  or by closing the tab or the app.

**Persistence**
- FR-19: The tab state file moves to version 2 and gains a `worktrees` key: a JSON list
  of absolute folder path strings. Version 2 is what gets written. Version 1 files
  still load, with `worktrees` = empty list.
- FR-20: The New worktree panel is never stored as `active_panel`. Opening it does not
  change what is persisted (`active_panel` stays `"start"`), so a restored tab always
  shows the start panel.

**Runs in progress**
- FR-21: While a run is in progress in any tab, closing that tab (the tab's close
  button) or the main window is refused. An information message box titled "Worktree
  creation in progress" with the text "Wait for the worktree creation to finish before
  closing." is shown, and the tab or window stays open.
- FR-22: Groups in a run are processed one at a time, in on-screen order (not in
  parallel).

## 5. Behavior and flows
**Main flow**
1. The user saves the tab with feature name `feat-x`. "Create new worktree" becomes
   enabled.
2. The user clicks it. The New worktree panel opens with one empty group.
3. The user picks the source `D:/proj-a` and the parent `D:/wt`, clicks '+', and picks
   `D:/proj-b` and `D:/wt`.
4. The user clicks Create. The panel turns busy, and on the worker thread each group
   resolves its default branch and runs `git worktree add -b feat-x D:/wt/feat-x main`.
   *(Note: two groups with the same parent would target the same folder, so the second
   one fails as "target exists". This is expected.)*
5. Everything succeeds: the paths are appended, the state file is written, and the tab
   shows the start panel with the Worktrees list.

**Alternative flow: partial failure**
- Group 2 fails (e.g. not a git repo). The state file gets group 1's path, group 1 turns
  green and group 2 red, the error box explains, and the button reads "Retry". The user
  fixes group 2's source and clicks Retry. Only group 2 runs, it succeeds, and the tab
  returns to start.

**Edge cases**
- The branch `feat-x` already exists in the source: git fails and the group turns red
  with git's message.
- The target folder already exists: the group fails before git runs.
- The parent folder is missing: the group fails ("parent folder does not exist").
- `git` is not on PATH: every processed group fails with "git not found".
- The user removes every red group: Retry with nothing pending returns to start (FR-17).
- The state file write fails after processing: the existing warning ("Cannot save state
  file") is shown. The worktrees still exist on disk. The tab's in-memory worktree list
  keeps the new paths, and the next state file write (the next panel switch or run)
  includes them. Navigation is unchanged: FR-14/FR-15 apply as if the write had
  succeeded.
- The app is closed while the panel is open (no run in progress): on restore the tab
  shows the start panel (FR-20). Worktrees already created and saved stay in the list.
- Closing a tab, or the main window, while a run is in progress is refused (FR-21).

**Empty states**
- No saved worktrees: the start panel hides the Worktrees label and list.

## 6. UI / UX
- **Start panel layout (top to bottom):** name input + Save row, slug label, then the
  centered big-button column with "Create new worktree", "Open a pipeline" and "Create
  a pipeline" (same size, font and spacing for all three: `BIG_BUTTON_*` constants),
  then the Worktrees label + list at the bottom (hidden when empty).
- **New worktree panel:** a scroll area holding the groups (so many groups still fit),
  then a '+' button, the error text box (read-only, hidden while empty), and the
  Create/Retry button at the bottom.
- **Group:** a `QGroupBox` with two rows: `[label] [line edit (stretch)] [... picker
  button]`. The '-' button sits in the group's top-right area (groups 2..N). Groups
  are titled "Worktree 1", "Worktree 2", ... by their current display position, and are
  renumbered when a group is removed.
- **Folder picker:** `QFileDialog.getExistingDirectory`, starting in the folder the input
  currently holds when that folder exists. Otherwise it gets an empty start directory,
  so the OS default is used.
- **Result colors:** red border = failed, green border = succeeded. Pending groups use
  the default style.
- **Busy state:** the panel is disabled, with an indeterminate progress indicator (e.g.
  a `QProgressBar` with range 0–0) shown during the run.
- **Accessibility:** the picker, '+' and '-' buttons have tooltips and accessible names
  (e.g. "Choose source project folder", "Add worktree", "Remove worktree"), following
  the `new_tab_button` pattern. Each group's result is also given in text, not by
  color alone: a failed group's tooltip and accessible description are "Failed:
  <error message>", a succeeded group's are "Created: <worktree path>", and a pending
  group has neither.

## 7. Data model
- `models/tab_state.py`:
  - `STATE_FILE_VERSION = 2`. The reader accepts versions 1 and 2.
  - `TabState` gains `worktrees: list[Path]` (default empty list), holding absolute
    paths.
  - `Panel` gains a value for the New worktree panel (e.g. `NEW_WORKTREE =
    "new-worktree"`), so it can sit in `PipelineTab._panels`. It is never written to
    the file (FR-20). The reader accepts only `"start"` for `active_panel`.
    `"new-worktree"` in a file is rejected as `unknown active_panel`. The writer always
    writes `"start"` while the New worktree panel is shown.
- State file v2 example:
  ```json
  {
    "version": 2,
    "feature_name": "feat-x",
    "active_panel": "start",
    "worktrees": ["D:\\wt\\feat-x", "E:\\other\\feat-x"]
  }
  ```
- Validation on load (v2): `worktrees` must be present and be a list of non-empty
  strings. Otherwise raise `TabStateError(path, "invalid worktrees")`. v1: the list is
  always empty, and a `worktrees` key in a v1 file is ignored (not validated, not
  loaded).
- Paths are stored as absolute paths (`Path.resolve()` at creation time) and written
  with `str(path)`.
- Worktree request/result value objects (no Qt, no I/O) live in `models/`, e.g.
  `WorktreeRequest(source: Path, parent: Path)` and `WorktreeResult(request, path: Path
  | None, error: str | None)`.

## 8. Integration and technical notes
- **New layer `infrastructure/`** (decision D17). It sits beside `persistence`:
  `services -> infrastructure -> models`, and infrastructure and persistence don't
  import each other.
  - `infrastructure/git_worktrees.py` (name indicative): a subprocess-based
    implementation that resolves the default branch / start point and runs `git
    worktree add`. It uses `subprocess.run([...], capture_output=True, text=True)` with
    an argument list (never `shell=True`) and `pathlib` paths.
  - Update `pyproject.toml` `[tool.importlinter]`. In the layers contract, put
    `devpipe.persistence` and `devpipe.infrastructure` as independent siblings at one
    level (import-linter supports `"devpipe.persistence | devpipe.infrastructure"`).
    Add `devpipe.infrastructure` to the "Only views and app use Qt" forbidden contract,
    and add a "views never import infrastructure" contract.
  - Update `docs/architecture.md`: the layer table, the diagram and the layout tree.
- **Service** `services/worktree_service.py`: it owns a Protocol (e.g. `GitWorktrees`)
  that infrastructure implements, plus the use case: a synchronous method that takes
  the feature name and the requests and returns results. It also merges new paths into
  the list without duplicates (`same_file`). No Qt.
- **Threading:** services can't use Qt, so the background thread lives in the view
  layer (a `QThread`/`QRunnable` worker that calls the synchronous service). Results
  come back to the UI thread through a signal.
- **Views:**
  - `views/start_panel.py`: the new button and the worktree list. A new method (e.g.
    `show_worktrees(paths)`), and a signal for the new button. Opening a folder uses
    `QDesktopServices.openUrl(QUrl.fromLocalFile(...))`.
  - New `views/new_worktree_panel.py`: the groups, '+'/'-', Create/Retry, the error
    box, the busy state and the worker.
  - `views/pipeline_tab.py`: registers the panel in `_panels`, switches panels, keeps
    `worktrees` in `_current_state()`, writes the state after a run, and does not
    persist `Panel.NEW_WORKTREE` as `active_panel`.
- **Composition:** `app.py` builds the infrastructure implementation and the
  `WorktreeService`, and injects them down through `MainWindow` → `PipelineTab`
  (matching how `TabStateService` is injected today).
- **Persistence:** `persistence/tab_state_repository.py` reads v1/v2 and writes v2 with
  `worktrees`.
- **Compatibility:** existing v1 state files and session restore keep working. Existing
  `test_tab_state_repository.py` expectations about `version: 1` need updating to v2
  for writes.
- **Constraint:** `ai-skills/` must not change.

## 9. Non-functional requirements
- **Responsiveness:** git runs off the UI thread (FR-11).
- **Security:** no shell is invoked. Paths and the feature name are passed as separate
  arguments. The feature name is already a safe slug (`^[a-z0-9]+(-[a-z0-9]+)*$`), which
  is also a valid git branch name.
- **Platform:** Windows first. Use `pathlib` everywhere, with no hard-coded separators.
- **Network:** none (no fetch).
- **Limits:** no hard limit on the number of groups. Groups run sequentially (FR-22).

## 10. Acceptance criteria
- [ ] Given an unsaved tab, when the start panel is shown, then "Create new worktree" is
      disabled.
- [ ] Given the start panel, then "Create new worktree" has the same minimum size and
      font size as "Open a pipeline" and sits centered above it.
- [ ] Given a run in progress, when the user tries to close its tab or the main window,
      then the "Worktree creation in progress" message is shown and nothing closes.
- [ ] Given a saved tab, when the user clicks "Create new worktree", then the New
      worktree panel shows exactly one empty group with no '-' button, and Create is
      disabled.
- [ ] Given the panel, when the user clicks '+', then a second group appears with a '-'
      button, and clicking '-' removes it.
- [ ] Given a group, when the user picks a folder in a picker dialog, then that path is
      written into the matching input. When the dialog is cancelled, the input is
      unchanged.
- [ ] Given every editable group has both fields filled, then Create is enabled. If
      any field is empty, Create is disabled.
- [ ] Given a fake git client that succeeds for all groups, when Create is clicked, then
      the panel is busy during the run, the tab returns to the start panel, the state
      file (v2) contains the new paths, and the start panel lists them.
- [ ] Given a fake git client where group 2 of 2 fails, when Create is clicked, then
      group 1 has a green border, group 2 has a red border, the error box shows group
      2's error, the button reads "Retry", group 1 is read-only with no '-', and the
      state file contains only group 1's path.
- [ ] Given the retry state, when the user fixes group 2 and clicks Retry, then only
      group 2 is processed, and on success the tab returns to start with both paths
      listed.
- [ ] Given the retry state where the user removed every red group, when Retry is
      clicked, then the tab returns to start.
- [ ] Given a path already in the saved list, when it is created again, then the list
      has no duplicate.
- [ ] Given a v1 state file, when it is opened, then the tab loads with no worktrees.
      The next write produces v2.
- [ ] Given a v2 file with an invalid `worktrees` value, when it is opened, then a
      `TabStateError` "invalid worktrees" is reported.
- [ ] Given the New worktree panel is open, when the app restarts, then the restored
      tab shows the start panel.
- [ ] Given a listed worktree folder that no longer exists, when it is double-clicked,
      then a "Folder not found" warning is shown and the list is unchanged.
- [ ] `uv run lint-imports` passes with the new `infrastructure` layer contracts.
- **Test scope (D18, D21):** the real-git infrastructure module has **no tests**. The
  service, the tab state v1/v2 format and the views are tested, with the service and
  views using a fake git client.

## 11. Decisions log
| # | Question | Decision | Rationale |
|---|----------|----------|-----------|
| D1 | When is "Create new worktree" enabled? | Only after Save | Feature name is fixed and a state file exists; matches Open/Create buttons |
| D2 | Base commit of the new branch | Source's default branch | User choice; predictable base |
| D3 | Behavior on partial failure | Create the others, save successes, show errors, stay on panel | Don't lose successes |
| D4 | Execution model | Background thread + busy state | Responsive UI |
| D5 | Default branch detection | `origin/HEAD` target, else local `main`, else `master`; error if none | Covers remote-backed and local-only repos |
| D6 | Remote vs local start point | Local branch (fallback `origin/<name>`), never fetch | Offline, no network side effects |
| D7 | Post-failure UI | All groups stay; red = failed, green = succeeded; error text box at bottom; Create → Retry processing failed only | User choice |
| D8 | Stored data per worktree | Worktree path only | Minimal; branch = feature name |
| D9 | Editing in retry state | Green locked; red editable/removable; '+' allowed | Retry fixes only what failed |
| D10 | When the panel returns to start | Only after a run with no failures; no Back button | User choice |
| D11 | Reuse after worktrees exist | Yes; append; no duplicates; fresh panel | Features can grow to more projects |
| D12 | State file format | Version 2 with `worktrees`; still read v1 | Explicit format change, existing files keep working |
| D13 | Restore while the panel is open | Panel not persisted; restore lands on start | Avoid being stuck on an empty panel with no Back |
| D14 | Create/Retry enablement | All editable groups have both fields filled | Cheap check; deep checks fail per group |
| D15 | Missing parent folder | Fail the group | Avoid creating folders from typos |
| D16 | Start panel list | List of paths, hidden when empty; double-click opens in explorer | User choice |
| D17 | Where git code lives | New `infrastructure/` layer beside persistence; update architecture.md + import-linter | Persistence is for devpipe's own files |
| D18 | Testing git creation | Do not test it | User choice |
| D19 | Retry with nothing pending | Return to start | No failures means success; avoids a dead end |
| D20 | Double-click on a missing folder | Warning; list unchanged | Removing entries is out of scope |
| D21 | Scope of "do not test" | Skip only the real-git infrastructure code | Service/format/views still tested with fakes |
| D22 | Layer placement of infrastructure | Beside persistence (`services -> infrastructure -> models`) | Same Protocol + injection pattern as `TabStateStore` |
| D23 | Format of "Create new worktree" | Big and centered, same as the existing start buttons; first in the column | User choice |
| D24 | Former assumptions | Made concrete: in-memory paths kept on write failure; close refused during a run; groups numbered by position; picker OS-default fallback; text result in tooltip/accessible description; reader accepts only `"start"`; v1 `worktrees` key ignored; sequential processing | User asked for concrete definitions |

## 13. Future ideas
- Remove/prune a worktree (and its branch) from the start panel list.
- Choose the base ref per group, or fetch before creating.
- Use the saved worktrees in "Open a pipeline" / "Create a pipeline" (control files in
  `<worktree>/.devpipe/<feature-name>/`).

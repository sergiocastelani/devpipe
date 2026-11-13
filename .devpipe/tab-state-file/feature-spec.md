# Feature Request: Tab state file

- **Date:** 2026-11-13
- **Source:** current session
- **Status:** Ready for implementation

## 1. Summary
Every tab in the devpipe main window gets its own JSON state file. The user names the
feature in a new start panel and picks where to save the state file with the system Save
dialog. After that first save the tab saves itself automatically. When the app starts, it
reopens the state files that were open in the last session. The content of each tab is
also restructured into a stack of panels with only one visible at a time (start panel now,
process panel and others later). This gives later features a place to keep pipeline state
and a navigation structure to build on.

## 2. Problem and goals
- **Problem:** Tabs hold no state. Nothing survives a restart, and the tab content is one
  fixed widget with no room for different working stages.
- **Goals:**
  - A tab can be tied to a user-chosen JSON file and reopened in a later session.
  - The start panel blocks every other action until the tab has a feature name and a
    saved state file.
  - Tab content is a panel stack, documented in `docs/architecture.md`, so future panels
    plug in without restructuring.
- **Non-goals:**
  - What "Open a pipeline" and "Create a pipeline" do (still undecided; they are only
    enabled/disabled here).
  - Any panel other than the start panel.
  - Renaming a feature after its state file is saved.
  - Linking the state file to the `.devpipe/<feature-name>/` control files or to
    `current-state.json`.

## 3. Users and use cases
- As a developer, I want to name a new pipeline and save its state file wherever I want,
  so that I can come back to it later.
- As a developer, I want my open pipelines to come back when I restart devpipe, so that I
  can continue where I stopped.
- As a developer, I want to open a state file I closed earlier (File > Open), so that I can
  resume a pipeline that is not in the current session.
- As a developer, I want to work with several pipelines in tabs, adding and closing tabs freely.

## 4. Functional requirements
**Tabs and window**
- FR-01: The tab bar has a "+" button that adds a new, unsaved tab showing the start panel.
- FR-02: Every tab has a close button. Closing a tab removes it from the session list. The
  state file on disk is never deleted.
- FR-03: Closing the last tab adds a new unsaved tab, so the window always has at least one tab.
- FR-04: The tab title is "New pipeline" while unsaved and the feature name once saved. A saved
  tab's tooltip shows the full state file path.
- FR-05: The window has a menu bar with File > Open... (shortcut Ctrl+O). It shows the system
  Open dialog (filter "JSON files (*.json)"), starting in the last-used folder (FR-12).

**Panel structure**
- FR-06: Each tab's content is a container that holds panels and shows exactly one at a time.
  In this feature the only panel is the start panel.

**Start panel**
- FR-07: The top of the start panel has a row with a feature-name text input and a "Save"
  button to its right. The existing "Open a pipeline" and "Create a pipeline" buttons stay below it.
- FR-08: Under the input, a label shows a live preview of the normalized feature name (slug):
  accents stripped, lowercased, spaces/underscores/other separators turned into single hyphens,
  characters outside `a-z0-9-` dropped, leading/trailing hyphens trimmed.
- FR-09: "Save" is enabled only when the slug is not empty and the tab is unsaved.
- FR-10: While the tab is unsaved, every other button on the tab ("Open a pipeline",
  "Create a pipeline", and any button added later) is disabled.
- FR-11: Clicking "Save" shows the system Save dialog (filter "JSON files (*.json)") with
  `<slug>.json` as the suggested name, starting in the last-used folder (FR-12).
- FR-12: The "last-used folder" is the folder of the most recently saved or opened state file,
  kept in `config.json`. When there is none, or the folder no longer exists, the user's home
  folder is used.
- FR-13: After a successful first save, the input text is replaced by the slug, the input and
  "Save" become disabled (the row stays visible), the other buttons are enabled, and the tab
  title/tooltip update (FR-04).
- FR-14: Cancelling the Save dialog changes nothing.

**State file**
- FR-15: The state file is JSON with exactly these fields:
  `{"version": 1, "feature_name": "<slug>", "active_panel": "start"}`.
- FR-16: After the first save, every change to the tab's state is written at once to the same
  path (auto-save). No dialog is shown again.
- FR-17: Reading a state file fails (and the file counts as invalid) when it is missing,
  unreadable, not valid JSON, not an object, has a `version` other than 1, has a missing or
  empty `feature_name`, or has an unknown `active_panel`.

**Session restore**
- FR-18: `config.json` keeps the ordered list of state file paths of the saved open tabs, and
  the path of the active tab. Unsaved tabs are never in the list.
- FR-19: The session list is written to `config.json` on every change: first save, open,
  close, reorder, and active-tab change.
- FR-20: At startup the app opens a tab for each listed state file, in list order, showing the
  panel stored in its `active_panel`, and selects the tab that was active. Files that are
  invalid (FR-17) are skipped silently and removed from the list.
- FR-21: If no tab was restored, the app opens one unsaved tab.

**Duplicates and errors**
- FR-22: File > Open on a path that is already open in a tab switches to that tab and opens
  nothing new.
- FR-23: Saving (first save) to a path that is already open in another tab shows an error
  dialog. The tab stays unsaved.
- FR-24: File > Open on an invalid file (FR-17) shows an error dialog with the path and the
  reason. No tab is opened.
- FR-25: If writing a state file fails (first save or auto-save), an error dialog shows the
  path and the reason. The in-memory state is kept. After a failed first save the tab stays
  unsaved. After a failed auto-save, the next change tries again.
- FR-26: Closing an unsaved tab, or the app while unsaved tabs exist, discards them silently
  with no confirmation.

## 5. Behavior and flows
**Main flow: new pipeline**
1. The user clicks "+" (or uses the tab present at startup). An unsaved tab shows the start
   panel, with "Save", "Open a pipeline" and "Create a pipeline" disabled.
2. The user types "New Feature". The preview shows `new-feature` and "Save" becomes enabled.
3. The user clicks "Save". The system Save dialog opens in the last-used folder, suggesting
   `new-feature.json`.
4. The user confirms. The file is written, the session list and last-used folder are updated
   in `config.json`, the input shows `new-feature` (disabled), "Save" is disabled, the other
   buttons are enabled, and the tab title becomes `new-feature`.

**Restart**
1. The user closes the app with two saved tabs and one unsaved tab. The unsaved tab is dropped.
2. On the next start, both saved tabs reopen in the same order and the previously active tab
   is selected.

**Alternative flows / edge cases**
- The input contains only characters that normalize away (e.g. "!!!"): the preview is empty
  and "Save" stays disabled.
- Save dialog cancelled: nothing changes (FR-14).
- Save to a path that is open in another tab: error, tab stays unsaved (FR-23).
- File > Open on a file that is already open: that tab is focused (FR-22).
- File > Open on an invalid file: error dialog (FR-24).
- The state file was deleted or corrupted between sessions: skipped silently at startup (FR-20).
- All listed files are invalid: one unsaved tab is shown (FR-21).
- The last tab is closed: a new unsaved tab appears (FR-03).
- Disk or permission error while writing: error dialog, state kept (FR-25).
- The active tab at shutdown was unsaved. Assumption: the last saved tab that was active is
  selected instead, or the first restored tab if none was.

## 6. UI / UX
- **Menu bar:** File > Open... (Ctrl+O).
- **Tab bar:** closable tabs, with a "+" button as the tab widget's corner widget.
- **Start panel:**
  - Top row: feature-name `QLineEdit` (stretches), then the "Save" button.
  - Below the input: a small slug preview label.
  - Below that: the existing big "Open a pipeline" / "Create a pipeline" buttons, centered as today.
- **States:**
  - Unsaved, empty name: Save, Open and Create disabled.
  - Unsaved, valid name: only Save enabled.
  - Saved: input and Save disabled; Open and Create enabled.
- **Dialogs:**
  - Save and Open use the native system dialogs (`QFileDialog.getSaveFileName` /
    `getOpenFileName`). The native Save dialog handles overwrite confirmation for files that
    exist but are not open.
  - Errors use a `QMessageBox` warning.
- Assumption: if the user types a file name without an extension in the Save dialog, `.json`
  is appended.

## 7. Data model
**Tab state file** (user-chosen path):
```json
{
  "version": 1,
  "feature_name": "new-feature",
  "active_panel": "start"
}
```
- `version`: int. Only `1` is valid in this feature. It allows migrations later.
- `feature_name`: non-empty slug that matches `^[a-z0-9]+(-[a-z0-9]+)*$`.
- `active_panel`: a panel id. Only `"start"` exists in this feature.
- Written as UTF-8, indented JSON with a trailing newline (same style as `config.json`).

**`config.json` additions** (unknown keys are still preserved, as `ConfigRepository` does today):
- `open_state_files`: list of absolute path strings, in tab order.
- `active_state_file`: path string or `null`.
- `last_state_folder`: path string or `null`.
- Invalid or missing values fall back to empty/`null`, the same way `window_maximized` is
  handled today.

**Models (suggested):**
- `TabState` dataclass (`feature_name`, `active_panel`).
- `Panel` enum (`START = "start"`).
- A pure `normalize_feature_name(text) -> str` function.
- New fields on `AppConfig`.

## 8. Integration and technical notes
Follow `docs/architecture.md` (`views -> services -> persistence -> models`, checked by
`uv run lint-imports`). Only views and `app.py` use Qt. Views never import persistence.

Suggested split (the implementer may adjust names):
- **models/:**
  - `tab_state.py` (`TabState`, `Panel`, `normalize_feature_name`, format version constant).
  - `app_config.py` gains the session fields.
- **persistence/:**
  - `tab_state_repository.py`: load/save a state file at a given `Path`. It raises one
    domain error type with a readable reason for every FR-17 case and for write failures.
  - `config_repository.py`: reads and writes the new keys.
- **services/:**
  - A session service: the ordered open-file list, the active file, the last-used folder,
    and duplicate checks.
  - A tab state service: create, save, auto-save and open. It uses the `Protocol` style of
    `WindowStateService` so tests can inject fakes.
- **views/:**
  - `main_window.py`: menu bar, "+" corner button, closable tabs, startup restore, keeping
    at least one tab.
  - A pipeline-tab container widget holding a `QStackedWidget` of panels.
  - `start_tab.py` becomes the start panel (e.g. `start_panel.py`) with the input, Save,
    preview and the existing buttons.
  - The file dialogs and message boxes live in views.
- **app.py:** builds the new repositories and services and injects them.
- **docs/architecture.md:** must describe the tab structure. Each tab is a container that
  holds a stack of panels (start, process, …) and shows one at a time, depending on what the
  user is working on; new panels are added to that stack. It must also list the tab state
  file as something the persistence layer handles, and update the layout tree.
- **Tests to update:** `tests/views/test_start_tab.py` and `tests/views/test_main_window.py`
  expect a `StartTab` as tab 0 and the two buttons. Adapt them to the new structure.
- `ai-skills/` must not change.
- Use `pathlib.Path` everywhere. Store paths in `config.json` as strings. Compare paths for
  duplicates after `Path.resolve()`, case-insensitively on Windows.
- Assumption: the tab state file is independent of `.devpipe/<feature-name>/` control files
  and `current-state.json`. Linking them is left to later features.

## 9. Non-functional requirements
- No AI involvement. All state is plain file I/O.
- Startup restore must not block on a missing network path for long. Assumption: files are
  read synchronously, as with `config.json` today; no special timeout handling.
- Settings stay in `config.json`. No `QSettings`.
- Main platform is Windows. Paths are handled with `pathlib`.

## 10. Acceptance criteria
- [ ] Given a new tab, when it is shown, then Save, "Open a pipeline" and "Create a pipeline"
  are disabled.
- [ ] Given an unsaved tab, when the user types "Nová Feature_X", then the preview shows
  `nova-feature-x` and Save is enabled.
- [ ] Given an input of "!!!", then the preview is empty and Save is disabled.
- [ ] Given a valid name, when the user clicks Save, then a native Save dialog opens in the
  last-used folder (or home) suggesting `<slug>.json` with a JSON filter.
- [ ] Given the Save dialog is cancelled, then the tab is unchanged.
- [ ] Given the user confirms a path, then the file contains
  `{"version": 1, "feature_name": "<slug>", "active_panel": "start"}`; the input and Save are
  disabled; the other buttons are enabled; the tab title is the slug and its tooltip is the path.
- [ ] Given a saved tab, when its state changes, then the file is rewritten without a dialog.
- [ ] Given a path already open in another tab, when the user saves to it, then an error
  dialog appears and the tab stays unsaved.
- [ ] Given two saved tabs and one unsaved tab, when the app is closed and restarted, then
  the two saved tabs reopen in order with the active one selected, and the unsaved one is gone.
- [ ] Given a listed state file that was deleted or corrupted, when the app starts, then it is
  skipped with no message and removed from `config.json`.
- [ ] Given no restorable files, when the app starts, then one unsaved tab is shown.
- [ ] Given File > Open (Ctrl+O) on a valid file not yet open, then it opens in a new tab and
  is added to the session list.
- [ ] Given File > Open on a file already open, then that tab is selected and no tab is added.
- [ ] Given File > Open on an invalid file, then an error dialog with the reason appears and
  no tab opens.
- [ ] Given a write failure, then an error dialog shows the path and reason, and the
  in-memory state is kept.
- [ ] Given the "+" button is clicked, then a new unsaved tab is added and selected.
- [ ] Given a tab is closed, then it is removed from the session list and its file still exists.
- [ ] Given the last tab is closed, then a new unsaved tab appears.
- [ ] `docs/architecture.md` describes the tab/panel-stack structure, and `uv run lint-imports`
  and `uv run pytest` pass.

## 11. Decisions log
| # | Question | Decision | Rationale |
|---|----------|----------|-----------|
| 1 | Existing Open/Create buttons | Keep both, disabled until saved | Matches "all other buttons disabled"; their actions stay undecided |
| 2 | Manual open of a state file | File > Open... (Ctrl+O), opens in a new tab | Standard desktop pattern |
| 3 | How new tabs are created | "+" button on the tab bar | Common pattern; QTabWidget corner widget |
| 4 | Closing tabs | Closable; removed from session; file kept | Lets the user control what is restored |
| 5 | State file content | `version`, `feature_name`, `active_panel` | Version allows safe migrations; panel restores the view |
| 6 | Later saves | Auto-save on every change | Nothing can be lost; no second dialog |
| 7 | Rename after save | Not allowed (read-only) | The name identifies the pipeline |
| 8 | Tab title | "New pipeline", then the feature name; tooltip = path | Clear identification |
| 9 | Name validation | Normalize to slug (devpipe skill rule), non-empty | Consistent with `.devpipe/<feature-name>/` naming |
| 10 | Save dialog defaults | Last-used folder (else home), `<slug>.json`, JSON filter | Fewer clicks for repeated use |
| 11 | Save row after first save | Input and Save disabled, still visible | Auto-save makes Save unnecessary; name stays visible |
| 12 | Closing unsaved tabs | Discard silently | Only a typed name is lost |
| 13 | When to normalize | Live preview label; slug replaces the text after save | The user sees the result without the cursor jumping |
| 14 | Restore errors | Skip silently, drop from the list | "If they still exist" taken literally |
| 15 | Startup tabs | Restored tabs in order, active selected; empty tab only if none | No clutter from extra empty tabs |
| 16 | Duplicate files | Open focuses the existing tab; Save to an open path is refused | Avoids two tabs writing one file |
| 17 | Panels in scope | Only the start panel, inside a QStackedWidget container | Others come with later features |
| 18 | Write errors | Error dialog, keep state; auto-save retries on the next change | The user must know the file is not saved |
| 19 | Open of an invalid file | Error dialog, no tab | The user picked the file explicitly |
| 20 | Session persistence | Written to `config.json` on every change; last close adds an empty tab | Survives crashes; the window is never empty |

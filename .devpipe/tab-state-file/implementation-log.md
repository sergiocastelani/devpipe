# Implementation Log

- **Updated:** 2026-11-13

| Step | File | Status | Rounds | Checkpoint | Notes |
|------|------|--------|--------|-----------|-------|
| S01 | [step-01.md](step-01.md) | done | 1 | 72618fb | passed first review |
| S02 | [step-02.md](step-02.md) | done | 2 | 9643b58 | round 1: unwrapped ValueError/RecursionError from json.loads, fixed |
| S03 | [step-03.md](step-03.md) | done | 2 | bab2ca9 | round 1: missing PEP 8 blank line in test_first_save.py, fixed |
| S04 | [step-04.md](step-04.md) | done | 2 | dfe3f45 | round 1: NUL character in a session entry crashed startup, fixed |
| S05 | [step-05.md](step-05.md) | done | 1 | 2c236ec | passed first review |

Status: pending | in-progress | done | skipped | blocked

## Deviations
Deviations from a step file's implementation suggestions, as reported by its implementer and accepted by its reviewer.
- (S01) Per-character mapping of `normalize_feature_name` moved into a private helper `_map_char`; same algorithm and order.
- (S01) `StartPanel` constructor calls `_refresh_save_enabled()` instead of disabling Save directly, so the Save rule lives in one place.
- (S02) `active_panel` validated by membership in a `_PANEL_VALUES` frozenset before `Panel(value)`, avoiding a try/except.
- (S02) Helper `_os_error_text(exc)` shared by the read and write error mappings.
- (S02) Empty-`feature_name` check applies only to `str` values; non-strings get "invalid feature_name: <repr>".
- (S02) `_read_json` also maps other `ValueError` (integer digit limit) and `RecursionError` to "not valid JSON: ..."; 3 extra regression rows added.
- (S03) Test fakes: `warnings` pytest fixture per file instead of a helper; Save-dialog fake is a `SaveDialog` class plus a `dialog` fixture.
- (S03) Extra test `test_start_folder_falls_back_to_home_when_value_is_a_file` for the "`last_state_folder` points to a file" edge case.
- (S03) `test_duplicate_check_ignores_case_on_windows` checks the warning for `str(tmp_path / "A.JSON")` (the selected path).
- (S04) Test helpers: `no_dialogs` is a pytest fixture; call recorder is a plain helper `record_session_calls(monkeypatch)`; local helpers `files`, `remember_session`, `tab_texts`, `state_paths`.
- (S04) `test_invalid_listed_file_is_skipped_silently_and_dropped` "missing" case checks the file still does not exist.
- (S04) `_as_path` rejects strings containing a NUL character (also covers `last_state_folder`, no observable change); extra test `test_entries_with_nul_characters_are_ignored` (3 cases) and NUL rows in two persistence tests.
- (S04) Known, out of scope (S02 reader): a session entry naming a DOS device such as `CON` hangs startup.
- (S05) Open-dialog fake is an `OpenDialog` class (callable, settable `answer`, `calls` list), like `test_first_save.py`; extra helpers `valid_file` fixture and `open_saved_then_new(window, tmp_path)`.

## Checks pending for the user
`needs-human` checks, collected from each step and verified by the user only after the run (section 4).
- (S03) Save dialog opens: with no `last_state_folder` in `config.json`, run `uv run devpipe`, type "New Feature", click Save; the native Save dialog opens in the home folder suggesting `new-feature.json` with the "JSON files (*.json)" filter. — pass
- (S03) Cancel: in that dialog, cancel; the tab is unchanged and Save is still enabled. — pass
- (S03) Confirm: in that dialog, confirm into a folder; `new-feature.json` exists with the three fields, the tab is titled `new-feature` with the full path as tooltip, the input shows `new-feature` disabled, Save is disabled, and the two big buttons are enabled. — pass
- (S03) Duplicate: with that saved tab, click "+", type "Other", click Save; the dialog opens in the same folder; pick `new-feature.json`; a warning says the file is already open and the new tab stays "New pipeline". — pass
- (S03) Write error: create `locked.json` beforehand and mark it read-only (`attrib +r locked.json`); name a new tab, click Save, pick `locked.json` and confirm the overwrite; a "Cannot save state file" warning shows the path and the reason, and the tab stays unsaved with the typed name kept. — pass

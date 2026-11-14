# Implementation Log

- **Updated:** 2026-11-14

| Step | File | Status | Rounds | Checkpoint | Notes |
|------|------|--------|--------|-----------|-------|
| S01 | [step-01.md](step-01.md) | done | 1 | a2ded7a | - |
| S02 | [step-02.md](step-02.md) | done | 1 | 9a81480 | - |
| S03 | [step-03.md](step-03.md) | done | 1 | 9323b35 | - |
| S04 | [step-04.md](step-04.md) | done | 1 | 0c39493 | - |
| S05 | [step-05.md](step-05.md) | done | 1 | 2e98e9e | Blocked once: S04 layout test expected 3 widgets; user approved updating it to 5 |
| S06 | [step-06.md](step-06.md) | done | 1 | 4859355 | - |
| S07 | [step-07.md](step-07.md) | done | 1 | COMMIT | - |
| S08 | [step-08.md](step-08.md) | pending | 0 | - | - |

Status: pending | in-progress | done | skipped | blocked

## Deviations
Deviations from a step file's implementation suggestions, as reported by its implementer and accepted by its reviewer.
- (S01) Test-side only: `test_v2_file_load_then_save_is_identical` writes its input in text mode (CRLF on Windows, like the repository); extra `_INVALID_FILES` row `worktrees-number`; `test_load_v1_ignores_worktrees_key` asserts `worktrees == []`.

- (S02) Test-side only: `test_show_worktrees_does_not_keep_caller_list` also asserts the caller's list is unmodified; `test_apply_saved_without_worktrees_hides_list` also asserts the label is hidden. The `openUrl` result is checked inline instead of stored in a local `opened`.
- (S04) `_add_group` inserts into the layout before appending to `_groups` (keeps the group before the stretch); private helpers `WorktreeGroup._tool_button` and `NewWorktreePanel._discard`; `WorktreeGroup.__init__` ends with `_refresh_controls()`; test-side helpers and extra assertions.
- (S05) Old S04 test `test_layout_order_scroll_add_create` updated to expect 5 root-layout widgets (user-approved); `test_partial_failure_shows_green_red_and_retry` builds the expected source text with `Path(...)` (native separators); `test_group_added_after_results_is_plain_and_paired_next` fills g3 before `show_results`; test-side helpers; new `reset()` docstring.
- (S07) `recover` writes its two passes as a list of verified flags followed by one results loop (same call order); `snapshot` calls `branch_exists` before `target.exists()`; `_worktree_entries` splits porcelain output on `"

"`; test-side `partial_failure` fixture, helpers `list_texts`/`release`, hand-built requests in `test_recover_does_not_clean_target_of_verified_entry`, `RecordingGit.removes()` and an `add_worktree` that raises.
- (S06) Button `clicked.connect(lambda: ...)` written on one line; test-side helpers `click_new_worktree`, `assert_fresh_panel` and extra assertions.

## Checks pending for the user
`needs-human` checks, collected from each step and verified by the user only after the run (section 4).
- (S04) Folder picker by hand: open the New worktree panel, click a group's source (or parent) picker, navigate to a folder with the mouse in the real OS dialog and choose it; expect the input to show that folder with native `\` separators. Cancel leaves the input unchanged. — pass
- (S07) Create in the real window (FR-11, FR-15): `uv run devpipe`, a tab saved as `try-wt`, New worktree panel with group 1 = a real repository and an existing empty parent folder, group 2 = a plain folder that is not a repository; click Create; expect the progress bar while it runs, group 1 green, group 2 red with "not a git repository", "Retry" shown; the state file lists only group 1's worktree. — pending
- (S07) Retry to start (FR-14, FR-16, FR-04): change group 2's source to another repository with a different parent and click Retry; expect the tab to return to the start panel listing both worktrees, and the list still there after restarting the app. — pending
- (S07) Retry with red groups removed (FR-17): with only the first group green and the second removed with '-', click Retry; expect the tab to return to start. Clean up the test worktrees and branches afterwards. — pending

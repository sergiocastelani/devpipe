# Implementation Log

- **Updated:** 2026-11-13

| Step | File | Status | Rounds | Checkpoint | Notes |
|------|------|--------|--------|-----------|-------|
| S01 | [step-01.md](step-01.md) | done | 1 | 72618fb | passed first review |
| S02 | [step-02.md](step-02.md) | done | 2 | 488cb84 | round 1: unwrapped ValueError/RecursionError from json.loads, fixed |
| S03 | [step-03.md](step-03.md) | pending | 0 | - | not selected in this run |
| S04 | [step-04.md](step-04.md) | pending | 0 | - | not selected in this run |
| S05 | [step-05.md](step-05.md) | pending | 0 | - | not selected in this run |

Status: pending | in-progress | done | skipped | blocked

## Deviations
Deviations from a step file's implementation suggestions, as reported by its implementer and accepted by its reviewer.
- (S01) Per-character mapping of `normalize_feature_name` moved into a private helper `_map_char`; same algorithm and order.
- (S01) `StartPanel` constructor calls `_refresh_save_enabled()` instead of disabling Save directly, so the Save rule lives in one place.
- (S02) `active_panel` validated by membership in a `_PANEL_VALUES` frozenset before `Panel(value)`, avoiding a try/except.
- (S02) Helper `_os_error_text(exc)` shared by the read and write error mappings.
- (S02) Empty-`feature_name` check applies only to `str` values; non-strings get "invalid feature_name: <repr>".
- (S02) `_read_json` also maps other `ValueError` (integer digit limit) and `RecursionError` to "not valid JSON: ..."; 3 extra regression rows added.

## Checks pending for the user
`needs-human` checks, collected from each step and verified by the user only after the run (section 4).

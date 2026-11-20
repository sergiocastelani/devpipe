import pytest

from devpipe.models.control_files import contract_has_open_steps, contract_step_statuses

CONTRACT = """# Design Contract: Feat

- **Plan:** [plan.md](plan.md)

## 1. Step status
| Step | Title | Status | File |
|------|-------|--------|------|
| S01 | step 1 title | approved | [step-01.md](step-01.md) |
| S02 | step 2 title | Draft | - |
| S03 | step 3 title | pending | - |

Status: pending | draft | approved

## 2. Shared items
| Item | Kind | Created by | Used / extended by | Notes |
|------|------|-----------|--------------------|-------|
| `#more` | element id | S01 | S09 | pending |
"""


def test_statuses_come_from_the_step_table_only():
    assert contract_step_statuses(CONTRACT) == ["approved", "draft", "pending"]


def test_status_column_is_found_by_its_header():
    text = "| Status | Step |\n|:--|--:|\n| draft | S01 |\n"
    assert contract_step_statuses(text) == ["draft"]


def test_no_step_table_has_no_statuses():
    assert contract_step_statuses("# Design Contract\n\nnothing yet\n") == []


@pytest.mark.parametrize(
    ("statuses", "is_open"),
    [
        (["approved", "draft"], True),
        (["pending"], True),
        (["approved", "approved"], False),
        ([], False),
    ],
)
def test_open_steps_are_pending_or_draft(statuses, is_open):
    rows = "".join(f"| S{n} | t | {status} | - |\n" for n, status in enumerate(statuses))
    text = "| Step | Title | Status | File |\n|---|---|---|---|\n" + rows
    assert contract_has_open_steps(text) is is_open

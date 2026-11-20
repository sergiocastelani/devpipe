"""Layout of devpipe's control files inside a worktree."""

import enum
from pathlib import Path

CONTROL_FOLDER_NAME = ".devpipe"
"""Folder at the worktree root that holds one control folder per feature."""

FEATURE_SPEC_FILE_NAME = "feature-spec.md"
"""The feature spec written by the devpipe-create skill, in the feature's control folder."""

PLAN_FILE_NAME = "plan.md"
"""The plan written by the devpipe-plan skill, in the feature's control folder."""

DESIGN_CONTRACT_FILE_NAME = "design-contract.md"
"""The design contract written by the devpipe-steps skill, in the feature's control folder.
Its step-status table lists each step's status (`pending`, `draft` or `approved`)."""

OPEN_STEP_STATUSES = frozenset({"pending", "draft"})
"""Step statuses of the design contract that mean the step is not designed yet."""


class DevpipeStage(enum.Enum):
    """The devpipe skill a feature is at, derived from its control files."""

    CREATE = "create"
    PLAN = "plan"
    STEPS = "steps"
    IMPLEMENTATION = "implementation"


def feature_folder(worktree: Path, feature_name: str) -> Path:
    """The control folder of `feature_name` in `worktree`: `<worktree>/.devpipe/<feature_name>`."""
    return worktree / CONTROL_FOLDER_NAME / feature_name


def feature_spec_file(worktree: Path, feature_name: str) -> Path:
    """The feature spec of `feature_name` in `worktree`: `<worktree>/.devpipe/<feature_name>/feature-spec.md`."""
    return feature_folder(worktree, feature_name) / FEATURE_SPEC_FILE_NAME


def _table_cells(line: str) -> list[str] | None:
    """The trimmed cells of a markdown table row (`| a | b |`), or None when `line` is not one."""
    line = line.strip()
    if not line.startswith("|"):
        return None
    return [cell.strip() for cell in line.strip("|").split("|")]


def contract_step_statuses(contract_text: str) -> list[str]:
    """The lower-cased step statuses of a design contract: the `Status` column of every
    markdown table whose header has both a `Step` and a `Status` column (empty when none)."""
    statuses: list[str] = []
    status_column: int | None = None
    for line in contract_text.splitlines():
        cells = _table_cells(line)
        if cells is None:
            status_column = None  # the table ended
            continue
        lowered = [cell.lower() for cell in cells]
        if status_column is None:
            if "step" in lowered and "status" in lowered:
                status_column = lowered.index("status")
            continue
        if all(set(cell) <= set("-: ") for cell in cells):
            continue  # the header separator row
        if status_column < len(lowered):
            statuses.append(lowered[status_column])
    return statuses


def contract_has_open_steps(contract_text: str) -> bool:
    """True when the design contract lists a step whose status is `pending` or `draft`."""
    return any(status in OPEN_STEP_STATUSES for status in contract_step_statuses(contract_text))

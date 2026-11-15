"""Layout of devpipe's control files inside a worktree."""

import enum
from pathlib import Path

CONTROL_FOLDER_NAME = ".devpipe"
"""Folder at the worktree root that holds one control folder per feature."""

FEATURE_SPEC_FILE_NAME = "feature-spec.md"
"""The feature spec written by the devpipe-create skill, in the feature's control folder."""

PLAN_FILE_NAME = "plan.md"
"""The plan written by the devpipe-plan skill, in the feature's control folder."""

IMPLEMENTATION_LOG_FILE_NAME = "implementation-log.md"
"""The log written by the devpipe-implement skill, in the feature's control folder."""


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

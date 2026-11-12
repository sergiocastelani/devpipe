# devpipe

A desktop app (Python + PySide6) that helps a developer organize
feature work done with AI agents.

Each tab of the app follows the development pipeline of one feature of a
target project. Each pipeline runs in its own git worktree, and its control
files live in `<worktree>/.devpipe/<feature-name>/`. The app does not run the
agents: it reads those files and shows where each pipeline stands.

## Pipeline skills

The `ai-skills/` folder holds the agent skills that produce the control files:

| Skill               | Produces                                   |
|---------------------|--------------------------------------------|
| `devpipe-create`    | `feature-spec.md`                          |
| `devpipe-plan`      | `plan.md`                                  |
| `devpipe-steps`     | `design-contract.md`, `step-NN.md`         |
| `devpipe-implement` | `implementation-log.md` and the code       |

## Requirements

- [uv](https://docs.astral.sh/uv/) for Python and dependency management.
  uv installs Python 3.12 itself (pinned in `.python-version`) if it is
  missing.
- Windows is the main platform. The app should also run on macOS and Linux,
  but those are not the focus.

## Setup

From the repository root:

```sh
uv sync
```

This creates `.venv/` and installs the app with its dev dependencies
(pytest, pytest-qt).

## Run the app

```sh
uv run devpipe
```

or, equivalently:

```sh
uv run python -m devpipe
```

## Run the tests

```sh
uv run pytest
```

Tests live in `tests/` and use [pytest-qt](https://pytest-qt.readthedocs.io/)
(the `qtbot` fixture) to build widgets without showing them on screen.

Useful variants:

```sh
uv run pytest -v                          # list each test
uv run pytest tests/test_start_tab.py     # one file
uv run pytest -k start_tab                # tests whose name matches
```

On a machine with no display (for example a Linux CI runner), run Qt
offscreen:

```sh
QT_QPA_PLATFORM=offscreen uv run pytest
```

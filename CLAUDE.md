# CLAUDE.md

Guidance for AI agents working on the devpipe codebase.

## What this is
A Python 3.12 + PySide6 desktop app. One window, one tab per feature
pipeline. Each pipeline lives in a git worktree of a target project, with
control files in `<worktree>/.devpipe/<feature-name>/`.

## Key rules
- The app never talks to AI agents. It only reads the control files and shows
  the pipeline state.
- Pipeline state (`current-state.json`) is derived deterministically from the
  control files. No AI is involved in computing it.
- App settings go in `config.json` in this folder (gitignored).
  Do not use QSettings.
- `ai-skills/` holds the devpipe agent skills. They are product content that
  the app installs into the agent's skills folder; do not change their
  behavior as a side effect of app work.

## Tooling
- Package and env management: uv (`pyproject.toml`).
- Layout: code in `src/devpipe/`, tests in `tests/` (pytest).
- Run: `uv run devpipe`. Test: `uv run pytest`.
- Main platform: Windows. Use `pathlib`, never hard-coded path separators.

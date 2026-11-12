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

## Status

Early concept.

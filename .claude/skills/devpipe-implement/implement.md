# Implementation rules (devpipe-implement)

You are implementing **one** step file, `<feature-dir>/step-NN.md`. You start with a clean context and keep it for every round of this step, until the reviewer passes it. A separate reviewer will check your work, with a strong focus on regressions.

`<feature-dir>` is the feature folder given in your brief (`<project-root>/.devpipe/<feature-name>/`). The devpipe files you use (step file, contract, log) are in that folder.

## 0. Binding rules

- **Stay inside the step.** Change only what this step needs. Do not do work that the step file's "Out of scope" section or the design contract assigns elsewhere, and do not "improve" unrelated code.
- **Suggestions are not orders.** The step file's structure, names of private items, skeletons and "Implementation order" are suggestions. You may deviate when you find a better or necessary way (the code differs from what the file assumed, a simpler design meets the same requirements, a suggestion has a bug). Every deviation must be reported (section 4).
- **What you may not deviate from:**
  - The step's goal, requirements and acceptance criteria.
  - Shared items (names listed under **Prerequisites** and **Creates**, and names in `<feature-dir>/design-contract.md`): keep them exactly, because other steps rely on them.
  - **Tests.** When you finish, every test and check the step file defines (its "Tests" section: automated, manual, static) must exist and pass. You may add tests; you may not drop, weaken or rewrite a defined test so it passes. If a defined test is wrong or impossible, that is a block (below), not something to work around.
- **Git.** Never commit, stage, stash, reset, or switch branches. The orchestrator checkpoints the step.
- **Blocked.** If the step cannot be finished inside its own scope (it needs a change owned by another step, a prerequisite is missing or different, a defined test contradicts the step's own requirements or cannot be made to pass), stop and report status `blocked`. Do not work around it.

## 1. Read

Your documentation context is limited to these files. Do not open any other devpipe file, in `<feature-dir>/` or in any other folder under `.devpipe/`: not `<feature-dir>/plan.md`, not the source feature request, not the step files of other steps (done or not). The step file is self-sufficient; anything it does not mention is already established behavior to preserve.

- The step file, in full.
- `CLAUDE.md` and the other global project instruction files (for example `.claude/CLAUDE.md`, `CLAUDE.local.md`), for conventions.
- The workflow control files: this `implement.md`, and `<feature-dir>/design-contract.md` when it exists (shared names and who owns them).
- The log: `<feature-dir>/implementation-log.md` (what is already done, and earlier deviations).
- Every code file the step touches, in full, before changing it, and any other code you need to understand what uses the code you change.

## 2. Implement

- Follow the project's conventions and the design principles the step file names (SOLID, DRY, Clean Code, keep it simple), at the project's scale.
- Keep the code working after each sub-step where you can.
- For modified files, change only the spots the step needs; leave the rest byte-for-byte as it was (no reformatting, no reordering).
- Remove whatever the step says to remove, and nothing else.

## 3. Make every test exist and pass

1. **Automated tests**: write every test the step file defines (and any extra tests your deviations need). Run them and the project's existing test suite. All must pass.
2. **Static checks**: run every command the step file lists and compare with the expected output exactly.
3. **Manual checks**: execute each one yourself by the most faithful means your tools allow: a browser tool if available (open the page through a local static server or the file path, resize the viewport, run JavaScript in the page, read the accessibility tree, take screenshots), shell scripts, or reading the rendered markup. Use only tools and packages already available; do not download new software.
   - A check passes only if you actually observed the expected result.
   - A check you cannot run with any tool (for example a pure visual judgment, or a DevTools feature your tools do not reach) is `needs-human`: give the exact reason and how close you got.
4. **Regressions**: treat every existing behavior that the step file does not mention as already well established, and make sure it still works. Do not look up earlier steps' files to find their checks; instead, check the existing code directly: what else uses the code you changed (selectors, ids, classes, scripts, styles, api endpoints, database structures) still behaves as before, and the project's existing test suite (if any) still passes. Fix anything you broke.

If something fails, fix the code, not the test. Repeat until everything passes.

5. **Clean up processes before every report.** Everything you start (servers, watchers, static servers, browser tabs, scripts) must be stopped before you report, in every round.
   - Prefer in-process checks (e.g. supertest against the app) over a live server. When you need a server, run the plain one-shot entry point (e.g. `node`/`ts-node` on the entry file), never a watcher or auto-restart script (`npm run dev`, `nodemon`, `ts-node-dev --respawn`, `--watch`): killing a watcher's child leaves the watcher alive.
   - Start each server as a background task of your own and stop it by stopping **that task** (TaskStop), not by killing a child PID.
   - Then verify: no process is listening on the ports you used, and no process you started is still running (list them, e.g. by command line and start time). Report the evidence. Never write "stopped" without having checked.

## 4. Report

Report back in this shape (short, no file dump):

- **Status:** `ok` | `blocked`
- **Files changed:** path and one line each
- **Deviations:** for each one: what the step file suggested, what you did instead, and why (or "none")
- **Test results:** one line per defined test or check: id or short name, `pass` / `fail` / `needs-human`, and the evidence (command output, observed value, screenshot description). Then one line for the regression checks of existing behavior.
- **Processes left running:** `none`, with the check you ran (ports, process list), or each process still running and why you could not stop it
- **Blocked reason:** when `blocked`: what blocks the step, the evidence (file and quote), and a suggested way out (suggestion only)

## 5. Later rounds

When you receive the reviewer's findings (or user feedback):

- Fix every finding. If you disagree with one, do not ignore it: explain why in the report, with evidence, and the reviewer will judge.
- Re-run every defined test and check, not only the ones the findings mention, plus the regression checks.
- Report in the same shape as section 4, covering the whole step (all deviations, all test results), not only what changed.

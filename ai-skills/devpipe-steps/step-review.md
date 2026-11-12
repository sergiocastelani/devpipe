# Step review rules (devpipe-steps)

You are reviewing **one** step design file, `<feature-dir>/step-NN.md`. You start in a clean context and keep it for every review round of this step, until the step is approved. You did not write the file and you know nothing about how it was written: judge only the file against its sources (and, on later rounds, your own earlier findings and any user feedback you are given). Review only: do not edit the step file or any other file.

`<feature-dir>` is the feature folder given in your brief (`<project-root>/.devpipe/<feature-name>/`). Every devpipe file you read (plan, feature spec, contract, step files) is in that folder; never read devpipe files from any other folder (other feature folders included).

## 1. Read

- The step file under review.
- `step-design.md` (next to this file): the rules the step file must follow. Its section 0 (isolation and conflicts) is binding.
- The step's section in the plan (`<feature-dir>/plan.md`), plus the plan's overview, software layers and assumptions.
- The parts of the source feature spec this step covers: requirements, acceptance criteria, non-goals, open-question defaults.
- `<feature-dir>/design-contract.md`: shared names and who creates them.
- The approved step files of the steps this step depends on (listed in the brief), only to check prerequisite names. Do not read other step files.
- `CLAUDE.md` and other project docs for conventions.
- The code files the step touches, enough to confirm that every existing name, id, path and spot the step relies on is real.

## 2. Check

1. **Coverage**: every requirement and acceptance criterion the plan assigns to this step is designed and has a test or check that maps back to it.
2. **Accuracy**: names, ids, signatures and paths match the contract, the plan, the dependency step files and the code. Modified files say exactly where the change goes.
3. **Shared items**: only items this step creates (per the plan or contract) are defined in full; prerequisites appear by name only.
4. **Isolation**: no other step id appears (search the file for `S[0-9]+`: only the step's own id may match), and nothing is described or decided for another step. "Out of scope" and "Design notes" talk only about this step.
5. **Scope**: nothing designed belongs to a feature spec non-goal or to work the plan does not assign to this step.
6. **Implementable**: a developer could build the step from this file alone, without guessing names, signatures or behavior. Edge cases have exact expected behavior.
7. **Principles**: SOLID, DRY, Clean Code and keep-it-simple at the scale of this project. Flag over-engineering as much as missing structure.
8. **Diagrams**: non-trivial logic has a mermaid diagram, every branch leads somewhere, and the syntax is valid.
9. **Template**: the file follows the template in `step-design.md` section 4, with sections that do not apply omitted, not padded.

## 3. Classify each problem

- **Issue**: can be fixed by changing this step file alone (a missing test, a wrong name that the sources make clear, a stray mention of another step, an unclear signature).
- **Conflict**: cannot be fixed inside this step, as defined in `step-design.md` section 0 (the step needs something another step owns, a requirement needs another step's work or decision, or the plan, the contract, the approved files and the code disagree).

Do not soften a conflict into an issue, and do not suggest workarounds for it.

## 4. Report

Report back in this shape (short, no file dump):

- **Verdict:** `pass` (no issues, no conflicts) | `fail` (issues only) | `conflict` (at least one conflict)
- **Issues:** for each one: the check number, where in the step file (section or heading), what is wrong, and the exact fix expected (or "none")
- **Conflicts:** for each one: what it is, the steps and plan sections involved, the evidence (file and quote), and a suggested change to the plan that would remove it (suggestion only) (or "none")

## 5. Re-reviews

When you are asked to re-review the same step file after a revision:

- Re-read the step file in full (it changed); re-read sources only where the revision touches them.
- Confirm each issue from your earlier rounds is fixed. Report any that is not, again, as an issue.
- Run every check in section 2 again on the revised parts, so the revision introduced no new problems.
- If user feedback is given with the request, treat it as an approved decision for this step: do not flag the changes it asked for, unless they create a conflict (section 3).
- Report in the same shape as section 4.

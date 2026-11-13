---
name: devpipe-steps
description: Turn each step of ".devpipe/<feature-name>/plan.md" (written by devpipe-plan) into a deep, implementation-ready design file ".devpipe/<feature-name>/step-NN.md", one step at a time. Each step is designed by a new agent and reviewed by a separate new agent, both starting with a clean context when the step starts and keeping it through every review round of that step, then reviewed with the user until approved, and only then does the next step start. Each file specifies the structure to build or change (files, classes, interfaces, enums, methods, attributes, or the stack's equivalents such as HTML sections, CSS classes and JS functions), the complex logic flows as mermaid diagrams, and exactly what must be tested, while keeping SOLID, DRY and Clean Code principles. Each step file is isolated: it never mentions or decides anything for other steps, and any conflict with another step aborts the run so the user fixes the plan. Use when the user wants to detail, design, deepen or spec out the implementation steps of a feature request.
argument-hint: "[feature name] [step ids, e.g. S03 or S02,S05 | path to plan file inside .devpipe/<feature-name>/]"
---

# devpipe-steps

Turn the plan in `<feature-dir>/plan.md` into one detailed design file per step (`<feature-dir>/step-01.md`, `<feature-dir>/step-02.md`, ...), **one step at a time**:

1. Each step is designed in a **fresh, clean context** (a new subagent that knows only that step, the shared contract and the approved files it depends on).
2. The step is **reviewed**, first by another new subagent with a clear context, then by the user, and revised until the user approves it.
3. Only then does the **next step** start.

**Agent lifetime.** The designer and the reviewer of a step are both started fresh at the start of that step's loop, and both keep their context until the step's loop is over (the step is approved, skipped or aborted). Every revision goes back to the same designer and every re-review goes back to the same reviewer, with `SendMessage`. The next step gets a new designer and a new reviewer. The only exception is **Redo from scratch** (3.3), which restarts the step's loop, so both agents are replaced.

You are the orchestrator. Keep your own context light: you do not design or review steps yourself and you do not read the codebase in depth. The detailed design rules live in `step-design.md` and the review rules in `step-review.md`, next to this `SKILL.md` (in this skill's base directory).

Design only. No step is implemented.

## Feature folder

Every file of a devpipe request lives in a folder exclusive to that request: `<project-root>/.devpipe/<feature-name>/` (the **feature folder**, written `<feature-dir>` in this skill and in `step-design.md` / `step-review.md`). `<project-root>` is the git top level (`git rev-parse --show-toplevel`); without a git repository, it is the working directory, or the parent of `.devpipe/` when the working directory is inside a `.devpipe/` folder.

Pick it before anything else:

1. **Already defined**: if `$ARGUMENTS` names the feature (a word that is not a step id: a feature name, or a path inside `.devpipe/<feature-name>/`), or a feature folder was already settled earlier in this session (by `devpipe-create` or another devpipe skill), use it without asking.
2. **Otherwise ask** with `AskUserQuestion` which feature to work with. List the existing folders in `<project-root>/.devpipe/`. The first option, suffixed "(Recommended)", is the **current folder**: the feature folder the working directory is in (`.devpipe/<name>/` or below it); when the working directory is not inside one, recommend the most recently modified feature folder instead. Add up to three other existing feature folders as options; the user can type another name with "Other".
3. If the chosen folder does not exist, tell the user and stop.

Every file this skill and its subagents use or generate for the request (the feature spec, the plan, the contract, the step files) is in the feature folder; never read devpipe files from, or write them to, anywhere else (other feature folders included). Every subagent brief includes the feature folder's absolute path.

## Step isolation and conflicts

These two rules override everything else in this skill.

**Isolation.** Every step file describes its own step and nothing else. It must not mention other steps (no other step ids, no "a later step will...", no "created by S01"), describe what they do, or decide anything for them. Items that must already exist when the step starts are listed by name as prerequisites, exactly as the contract names them, without saying which step creates them or how. Every decision in a step file is about that step's own work.

**Conflicts abort the whole run.** A conflict is anything that cannot be settled inside the step's own scope, for example:

- The step needs to create, change, rename or remove something the plan or the contract assigns to another step.
- A requirement or acceptance criterion of the step cannot be met without work, or a decision, that belongs to another step.
- The step's needs contradict the plan, the contract, an approved step file or the code (a missing or different prerequisite, two steps owning the same item, an item nobody owns).
- The user's review feedback asks for something that belongs to another step or changes another step.

Choices that live entirely inside the step (its private names, internal structure, its own tests) are not conflicts: the step decides them, or asks the user as an open question.

When a conflict appears, at any point (loading the plan, the designer's work, the reviewer's report, the user's review):

1. Stop. Do not resolve it yourself, do not ask the user to decide it here, do not edit the plan, and do not start or continue any step.
2. If a step file was written for the step being detailed, delete it and set that step back to `pending` in the contract. Steps already `approved` stay as they are.
3. Show the user every conflict found: what it is, which steps and plan sections it involves, the evidence (file and quote), and, as a suggestion only, how the plan could be changed to remove it.
4. Tell the user to resolve the conflict in the plan file (link it: `<feature-dir>/plan.md`, or the plan path in use) and then run `devpipe-steps` again.
5. End the operation. Nothing else runs in this invocation.

## 1. Load the plan

1. **Find the plan.**
   - If `$ARGUMENTS` contains a path to a `.md` file inside the feature folder, use it.
   - Otherwise use `<feature-dir>/plan.md`. If several `plan*.md` files exist in `<feature-dir>/`, ask which one with `AskUserQuestion`.
   - If none exists, tell the user to run `devpipe-plan` for this feature first, and stop.
2. **Read the whole plan**: overview, layers, every step, stages, coverage and assumptions. Skim the source feature spec (`<feature-dir>/feature-spec.md`), only enough to know its requirements and non-goals.
3. **Pick the steps to detail.**
   - If `$ARGUMENTS` lists step ids (`S03`, `S02,S05`, `S04-S07`), detail only those.
   - Otherwise detail every step that is not yet `approved` in the contract (section 2).
4. **Order them** by the plan's execution stages, then by step id, so every step comes after the steps it depends on. If a selected step depends on a step that is not approved yet, warn the user and offer to detail the dependency first.

## 2. Create or load the design contract

The contract, `<feature-dir>/design-contract.md`, is the memory shared by all the clean contexts. It is how one step's decisions reach the next step without carrying the whole conversation.

If it does not exist, create it from the plan (and a quick look at the files the plan names, only to confirm existing names):

```markdown
# Design Contract: <Feature name>

- **Plan:** [plan.md](plan.md)
- **Updated:** <YYYY-MM-DD>

## 1. Step status
| Step | Title | Status | File |
|------|-------|--------|------|
| S01 | ... | pending | - |

Status: pending | draft | approved

## 2. Shared items
Names that cross steps: types, interfaces, enums, DTOs, tables, routes, events, config keys; for front-end or static projects: element ids, CSS classes and variables, data attributes, JS functions, shared script or style regions.

| Item | Kind | Created by | Used / extended by | Notes |
|------|------|-----------|--------------------|-------|
| `#projects-more` | element id | S01 | S09, S10 | container |

## 3. Decisions
Decisions approved during a step's review, each about that step's own work only.
- (S01) ...
```

Keep every name the plan already gives. If the plan contradicts itself or the code, or ownership of an item is unclear, that is a conflict: abort as described in "Step isolation and conflicts".

If the contract exists, read it, and resume: steps marked `approved` are skipped unless the user named them in `$ARGUMENTS`. If a requested step file already exists and is `approved`, ask whether to redo it or skip it.

## 3. The step loop

For each step, in order, run the full cycle below. Never start the next step before the current one is approved or explicitly skipped by the user.

### 3.1 Design in a clean context

Start a **new** subagent with the Agent tool (`subagent_type: general-purpose`; never `fork`, which would carry this conversation). Each step gets its own new subagent. Brief it with:

- The step id and title, the absolute path of the feature folder, and the output path (`<feature-dir>/step-NN.md`).
- Absolute paths to: `step-design.md` (in this skill's base directory), the plan, the source feature spec, `<feature-dir>/design-contract.md`, and the **approved** step files of the steps this one depends on.
- The instruction: "Follow `step-design.md` exactly. Detail only this step: do not mention other steps or decide anything for them. If you find a conflict with another step, do not write the step file; report it with status `conflict`. Otherwise write only the step file. Report back in the format at the end of `step-design.md`."
- Any user decisions relevant to this step that are not yet in the contract.

Do not paste the plan, the code or other step files into the brief; the subagent reads what it needs from the paths. Keep its agent id: every revision of this step goes back to the same subagent, until the step's loop is over.

Set the step's status to `draft` in the contract.

### 3.2 Review in a clean context

If the designer subagent reports status `conflict`, abort as described in "Step isolation and conflicts", using its conflict list.

Otherwise the step file is reviewed by a reviewer subagent, never by you and never by the designer.

**First review of the step.** Start a **new** reviewer with the Agent tool (`subagent_type: general-purpose`; never `fork`, and never a reviewer from an earlier step), so it starts with a clear context. Brief it with:

- The step id and title, the absolute path of the feature folder, and the path of the step file to review.
- Absolute paths to: `step-review.md` and `step-design.md` (in this skill's base directory), the plan, the source feature spec, `<feature-dir>/design-contract.md`, and the **approved** step files of the steps this one depends on.
- The instruction: "Follow `step-review.md` exactly. Review only this step file; do not edit any file. Report back in the format at the end of `step-review.md`. You will be asked to re-review this file after each revision until the step is approved."

Keep its agent id.

**Later reviews of the same step** (after a `fail` fix or a user revision): send the same reviewer a message with `SendMessage`: "The step file was revised. Re-review it following `step-review.md` (section 5 for re-reviews) and report in the same format." When the revision came from the user (3.3), add the user's feedback in their words, so the reviewer treats it as an approved decision for this step.

Never give the reviewer the designer's report, your opinion or any of the rest of this conversation: it judges the file against its sources, its own earlier findings and the user's feedback only.

Act on the verdict:

- `pass`: go to 3.3.
- `conflict`: abort as described in "Step isolation and conflicts", using the reviewer's conflict list.
- `fail`: send the issues, as the reviewer wrote them, to the **designer** subagent with `SendMessage` and wait for the corrected file (a `conflict` report from the designer aborts). Then run another review round with the same reviewer. After 3 failed rounds, bring the remaining issues to the user in 3.3.

### 3.3 Review it with the user

Present the step to the user:

- A clickable link to the step file.
- The subagent's summary (3 to 6 bullets), the shared items it creates and its open questions (about this step only).

Then ask with `AskUserQuestion` (one question, plus up to three for the subagent's open questions, each with options and your recommendation first):

- **Approve**: the step is final.
- **Revise**: the user gives feedback ("Other" or a follow-up message).
- **Redo from scratch**: discard the file, drop the current designer and reviewer, and restart the step's loop at 3.1 with a brand-new designer (given the user's guidance) and, in 3.2, a brand-new reviewer.
- **Skip for now**: leave it as `draft` and move on (only if no later selected step depends on it).

On **Revise**, first check that the feedback stays inside this step. If it asks for something that belongs to another step or changes another step, it is a conflict: abort. Otherwise send the user's feedback, in their words, to the same designer with `SendMessage`, then repeat 3.2 (with the same reviewer) and 3.3. Loop until the user approves.

### 3.4 Close the step

When the user approves:

1. Update the contract: status `approved` with the file link, add the shared items this step creates (as the plan assigns them), and record the decisions made during review (each about this step only).
2. If closing the step would change something another step relies on (a renamed, changed or removed shared item), it is a conflict: abort instead of approving.
3. Tell the user in one line that the step is approved and which step comes next, then start 3.1 for the next step.

The step's loop is now over: its designer and reviewer are not used again. The contract is the only thing carried forward: the next step's new designer and new reviewer start clean, and the designer learns about earlier steps only through the contract and the approved files it depends on.

## 4. Finish

When every selected step is approved or skipped:

- List the step files, as clickable markdown links, with one line each and their status.
- List the decisions recorded in the contract and any steps left as `draft`.

(An aborted run does not reach this section: it ends with the conflict report.)

## Fallback without subagents

If the Agent tool is not available, still work one step at a time, and keep design and review in separate clean contexts by splitting them across runs:

1. **Design run**: design the step yourself by following `step-design.md`, write the file, set it to `draft` with the note `awaiting review` in the contract, and tell the user to clear the context (`/clear`) and run `devpipe-steps <feature-name>` again.
2. **Review run**: a step marked `awaiting review` is picked up first. Review it by following `step-review.md`, without reading anything about how it was designed beyond the step file. On `pass`, run 3.3 and close it with 3.4. On `fail`, fix the issues and re-review the fixed file in the same run (section 5 of `step-review.md`), repeating until `pass`; the review context is kept until the step is approved. On `conflict`, abort.
3. After a step is approved, tell the user to `/clear` and run `devpipe-steps <feature-name>` again; the contract makes the next run resume at the next pending step.

The isolation and conflict rules apply unchanged.

## Guidelines

- One step at a time, always. No parallel subagents, no batching of steps.
- Designer and reviewer are always different agents. Both start with a clear context at the start of a step's loop and keep it until that loop is over; they are never reused for another step. You never review a step yourself.
- The plan is the source of truth for scope and ownership. Never change it, and never work around it: any conflict with it aborts the run so the user fixes the plan.
- Forward the user's feedback faithfully; do not reinterpret it.
- Write in the same language as the plan.

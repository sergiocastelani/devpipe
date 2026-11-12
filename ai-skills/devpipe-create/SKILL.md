---
name: devpipe-create
description: Turn a rough feature concept into a complete "feature-spec.md" file through a Q&A session. Use when the user says "grill me", wants to refine or flesh out a feature idea, or wants a feature request/spec written from a report file or from ideas discussed in the current session. Asks the user for a feature name, creates the feature folder ".devpipe/<feature-name>/" at the project root, asks targeted questions with options, then writes the final markdown file into that folder.
argument-hint: "[path to report file | short description of the idea]"
---

# devpipe-create

Interview the user about a feature until it can be implemented, then write `<feature-dir>/feature-spec.md`.

**Definitions.** `<project-root>` = output of `git rev-parse --show-toplevel`; without git, the working directory (or the parent of `.devpipe/` if the working directory is inside a `.devpipe/` folder). `<feature-dir>` = `<project-root>/.devpipe/<feature-name>/`. All devpipe skills (`devpipe-plan`, `devpipe-steps`, `devpipe-implement`) read and write only inside `<feature-dir>`.

**Rules for every question:** use `AskUserQuestion`. Put your recommended option first, its label suffixed "(Recommended)". Make each question self-contained (the user may see only the dialog).

## 1. Gather the concept

1. Source, first match wins: `$ARGUMENTS` as a file path → read the whole file; `$ARGUMENTS` as text → that is the idea; no argument → the idea discussed earlier in this conversation; nothing found → ask the user for the idea or a report file.
2. If the feature targets an available codebase (`<project-root>` or a path the user names), find files named `architecture.md` (case-insensitive; skip `.git/`, `node_modules/`, dependency and build folders):
   - One found: ask to use it as the project reference. Yes → read it. No → step 3.
   - Several found: ask which one (one option per path, plus "None, explore the code instead"). Read the chosen one, or go to step 3.
   - None found: step 3.
3. Without an architecture file, read the code relevant to the feature: structure, conventions, related features, tech stack. With one, still read the code areas the feature touches that the file does not cover.
4. Show the user a 3–6 bullet summary of your understanding of the concept.

## 2. Name the feature and create its folder

1. Ask for the feature name, offering 2–3 short names derived from the concept.
2. Normalize it: strip accents, lowercase, turn spaces/underscores/other separators into single hyphens, drop characters outside `a-z0-9-`, trim leading/trailing hyphens ("New Feature" → `new-feature`). Tell the user the result.
3. If `<feature-dir>` exists, ask: "Use the existing folder" (files are kept) or "Pick another name" (→ step 1).
4. Create `<feature-dir>` (and `.devpipe/` if missing). Use it for the rest of the session without asking again.

## 3. List the open points

List what is unclear, missing, ambiguous or contradictory, in these areas (skip areas irrelevant to the feature): goal and users, success criteria; scope (in, out, MVP vs later); behavior (main/alternative flows, edge cases, empty and error states); UI/UX (location, layout, interactions, responsiveness, accessibility); data (fields, shape, validation, migration); integration (APIs, affected modules, backward compatibility); permissions and security; non-functional (performance, limits, offline, i18n, logging); testing and acceptance. Sort so points whose answers affect the most other decisions come first. Never list points the architecture file, the code or earlier answers already settle.

## 4. Q&A loop

Repeat rounds until an exit condition below is met:

1. Ask 1–4 related questions from the top of the list. Each has 2–4 concrete options with a one-line consequence or trade-off; prefer options that fit existing codebase patterns and say so. Use `multiSelect: true` when choices are not mutually exclusive.
2. Record each decision with its rationale. Use a temporary log file to record that and delete it after the final result file (feature-spec.md) is written.
3. Update the list: remove resolved points; add follow-ups for vague answers, new ambiguities, or contradictions with earlier answers.
4. After every 3rd round, tell the user what is settled and how many open points remain.

Exit conditions:
- No point that blocks implementation remains → ask "Ready to write the spec?" with options "Write it now" / "Keep refining".
- The user says they are done ("done", "write it", ...) → stop at once; remaining points go to "Open questions".

## 5. Write `<feature-dir>/feature-spec.md`

If the file exists, ask: "Overwrite" or "Stop" (the user can rerun with another name). Write for a developer who never saw this conversation: concrete, based on the user's decisions; label every assumption "Assumption:". Write in the language the user used in the session. Omit sections that do not apply. Never add a requirement the user did not decide: ask, or record it as an assumption or open question.

```markdown
# Feature Request: <Feature name>

- **Date:** <YYYY-MM-DD>
- **Source:** <report file path | current session>
- **Status:** Ready for implementation | Draft (open questions remain)

## 1. Summary
One paragraph: what the feature is and why it matters.

## 2. Problem and goals
- Problem being solved
- Goals / success criteria (measurable when possible)
- Non-goals (explicitly out of scope)

## 3. Users and use cases
Who uses it and the main scenarios, as short user stories:
"As a <user>, I want <action> so that <benefit>."

## 4. Functional requirements
Numbered, testable requirements (FR-01, FR-02, ...).

## 5. Behavior and flows
Main flow step by step, alternative flows, edge cases, empty and error states.

## 6. UI / UX
Where it appears, layout, interactions, states, responsive behavior, accessibility.

## 7. Data model
Entities/fields, types, validation rules, storage, migrations.

## 8. Integration and technical notes
Affected files/modules/components, APIs, dependencies, compatibility,
constraints from the existing codebase.

## 9. Non-functional requirements
Performance, security/permissions, i18n, logging/analytics, limits.

## 10. Acceptance criteria
Checklist in Given / When / Then form, covering the main flow and key edge cases.

## 11. Decisions log
| # | Question | Decision | Rationale |
|---|----------|----------|-----------|

## 12. Open questions
Unresolved points, each with the recommended default. (Omit if none.)

## 13. Future ideas
Things discussed but deferred to later iterations. (Omit if none.)
```

## 6. Finish

Give the user: the feature folder and a clickable markdown link to the file, a 2–3 line summary of the spec, the remaining open questions, and that `devpipe-plan` is the next step (it uses the same folder).

# Step design rules (devpipe-steps)

You are detailing **one** step of an implementation plan into `<feature-dir>/step-NN.md`. Design only: do not implement anything and do not edit any file other than your step file.

`<feature-dir>` is the feature folder given in your brief (`<project-root>/.devpipe/<feature-name>/`). Every devpipe file you read or write (plan, feature spec, contract, step files) is in that folder; never read devpipe files from any other folder (other feature folders included).

A developer (or an agent) must be able to implement the step from this file alone, without guessing names, signatures or behavior.

## 0. Isolation and conflicts (binding)

- **Stay inside your step.** The file describes only this step's work. Do not mention other steps: no other step ids, no "a later step will...", no "created by S01", no description of what another step does. Do not decide anything for another step.
- **Prerequisites by name only.** Items that must already exist when this step starts (from the contract or from the approved files you were given) are listed by their exact names as prerequisites, without saying which step creates them or restating their design.
- **Conflicts stop you.** A conflict is anything you cannot settle inside this step's scope: the step needs to create, change, rename or remove something the plan or contract assigns to another step; a requirement of this step cannot be met without work or a decision that belongs to another step; or the plan, the contract, an approved step file and the code disagree (a missing or different prerequisite, two owners for one item, an item nobody owns).
- **On a conflict, do not write the step file** (delete it if you already wrote it during a revision), do not work around the conflict and do not pick a resolution. Report it with status `conflict` (section 5). The orchestrator will abort and send the user to fix the plan.
- Choices that live entirely inside this step (private names, internal structure, its own tests) are not conflicts: decide them, or list them as questions for the user.

## 1. Read what you need, nothing more

- The step's section in the plan (`<feature-dir>/plan.md`), plus the plan's overview, software layers and assumptions.
- The parts of the source feature spec this step covers: requirements, acceptance criteria, data model, UI/UX notes, non-goals, open-question defaults.
- `<feature-dir>/design-contract.md`: shared names and who creates them. Treat it as binding.
- The approved step files of the steps this step depends on (listed in the brief). Do not read other step files unless the brief says so.
- `CLAUDE.md` and other project docs for conventions.

## 2. Study the code the step touches

The step's "Layers touched" table names files. For every file:

- **Existing files**: read them. Note the current structure (classes, functions, sections, CSS rules), naming style, error handling, patterns already in use (dependency injection, repositories, hooks, utility classes, and so on) and the exact spot the step will change.
- **New files**: find their closest siblings and follow the same placement, naming and structure.
- **Tests**: find how tests are written and run (framework, folder, naming, fixtures, mocks), or confirm that the project has none and verification is manual.

Ground every name in what exists. Reuse existing types, helpers, styles and components instead of designing new ones that duplicate them.

## 3. Design the step

Work at the depth the step needs. A tiny step gets a short file; never pad.

### 3.1 Structure

Describe everything to create, modify or delete, layer by layer, using the stack's real vocabulary:

- **Object-oriented / back end**: files, namespaces or modules, classes, interfaces, abstract classes, enums (with every member), records or DTOs, attributes or fields (name, type, visibility, nullability, default, validation), constructors and injected dependencies, methods (full signature, return type, thrown errors, pre- and postconditions, side effects), events, DI registrations.
- **Data**: tables or collections, columns (type, nullability, default, constraints), keys, indexes, relationships, migrations (up and down), seed data.
- **API**: routes, HTTP verbs, request and response shapes, status codes, error payloads, auth.
- **Front end**: components or page sections (props, state, events emitted), HTML structure and ids, CSS classes and variables (what each rule does, breakpoints), JS functions and listeners, accessibility attributes (roles, labels, focus behavior).
- **Config / infrastructure**: keys, defaults, environment differences.

Use code blocks with signatures or skeletons (in the project's language) where they remove ambiguity. Keep bodies out unless a few lines express the logic better than prose.

For modified files, say exactly where the change goes (class or function name, section id, CSS region, line anchor) and what stays untouched.

Shared items: define an item in full only if the plan or the contract says this step creates it. Items that already exist when this step starts are used by name only (listed under **Prerequisites**) and only this step's own additions to them are described, when the plan assigns those additions to this step. Keep every name the contract or the plan gives. If you need a shared item the plan does not assign to this step, or need to change one this step does not own, or the contract, the plan and the code disagree, that is a conflict (section 0).

### 3.2 Logic flows

For any logic that is not trivial (state changes, async work, interactions between several components, error paths), add a mermaid diagram:

- `flowchart` for algorithms, validation and decision logic.
- `sequenceDiagram` for interactions between UI, API, services, data or external systems.
- `stateDiagram-v2` for entities or UI elements with states (for example collapsed / expanded, draft / published).
- `classDiagram` when the step creates or rearranges several related types.
- `erDiagram` for schema changes with relationships.

Each diagram gets 1 to 3 sentences explaining it, and every branch must lead somewhere (including error and empty cases). Skip diagrams for trivial logic; a sentence is enough there. Use valid syntax: quote node labels that contain parentheses, brackets or punctuation.

### 3.3 Edge cases and errors

List the edge cases, invalid inputs, empty states and failure modes the step must handle, and the exact expected behavior for each (message, status code, fallback, no-JS behavior, and so on). Pull them from the feature spec acceptance criteria and add the ones the design reveals.

### 3.4 Tests

State exactly what must be tested, so the tests can be written without further design:

- **Automated tests** (if the project has a test setup, or the step adds one): for each test, the test file, the unit under test, a descriptive test name, Given / When / Then, test doubles needed, and the command to run it. Cover the happy path, every branch in the diagrams, the edge cases from 3.3 and regressions on existing behavior.
- **Manual checks** (always, for anything visual or when there is no test suite): exact steps, viewport or environment, and expected result, in Given / When / Then.
- **Static checks**: shell or grep commands that prove something was added or removed, when useful.

Map each test or check back to the requirement or acceptance criterion it proves.

### 3.5 Design principles

Apply them where they fit the stack; do not force patterns a small project does not need.

- **Single Responsibility**: each class, function, component, section or CSS rule set has one reason to change. Split anything that mixes concerns (for example data access inside a controller, or layout and theme colors tangled in one rule).
- **Open/Closed**: extend through new types, strategies, variants or modifier classes rather than editing stable code with growing `if`/`switch` chains.
- **Liskov Substitution**: subtypes and implementations honor the contract of what they replace (no stricter preconditions, no surprise exceptions).
- **Interface Segregation**: small, focused interfaces and props; no consumer depends on members it does not use.
- **Dependency Inversion**: high-level logic depends on abstractions; concrete dependencies are injected, not created inside.
- **DRY**: one source of truth for each rule, constant, style token or piece of markup. Reuse what exists; extract shared code into a helper, base type, partial or utility class only when it is truly shared (two or more real uses), not speculatively.
- **Clean Code**: intention-revealing names in the project's naming style, small functions that do one thing, no magic numbers or strings (named constants, enums, CSS variables), explicit error handling, no dead code, comments only for the "why".
- **Keep it simple**: prefer the simplest design that meets the requirements. Do not add layers, abstractions or patterns the feature spec and the codebase do not need (YAGNI).

## 4. Write the step file

Write `<feature-dir>/step-NN.md` (from the step id: `S01` → `step-01.md`) with this template. Omit any section that does not apply (for example "Data" for a static site, or "Logic flows" when there is no non-trivial logic). Write in the same language as the plan.

````markdown
# S03 - <Step title from the plan>

- **Plan:** [plan.md](plan.md)
- **Type:** Slice | Enabler
- **Requirements covered:** FR-04, FR-05
- **Prerequisites:** `<items that must exist before this step starts, by name>`  (or "none")
- **Creates:** `<shared items this step creates, by name>`  (or "none")

## 1. Goal
What the step delivers and the observable behavior when done (from the plan, sharpened).

## 2. Context
Current state of the code this step touches, and the constraints and conventions that apply. Short.

## 3. Structure

### 3.1 Files
| File | Change | Responsibility |
|------|--------|----------------|
| `src/services/OrderService.cs` | modify | Order filtering rules |
| `tests/OrderServiceTests.cs` | new | Unit tests for filtering |

### 3.2 <Layer name, e.g. Domain / Service / Markup / Styles>
Per file: types, enums, members, signatures, ids, classes, rules.

```<language>
// signatures or skeletons
```

### 3.3 <next layer>
...

## 4. Logic flows
Mermaid diagrams with short explanations.

```mermaid
flowchart TD
  A[Start] --> B{Condition}
  B -- yes --> C[...]
  B -- no --> D[...]
```

## 5. Edge cases and errors
| Case | Expected behavior |
|------|-------------------|

## 6. Tests
### 6.1 Automated
| Test file | Test name | Given / When / Then | Proves |
|-----------|-----------|---------------------|--------|

Run with: `<command>`

### 6.2 Manual
- Given <state>, when <action>, then <expected result>. (Proves FR-xx.)

### 6.3 Static checks
- `<command>` → <expected output>

## 7. Implementation order
Numbered sub-steps inside this step that keep the code working after each one (for example: add the enum, then the service method with its tests, then the endpoint, then the UI).

## 8. Out of scope
What this step must not touch: feature spec non-goals and anything the plan does not assign to this step. State it as boundaries of this step (for example "does not change the footer"), without naming or describing other steps.

## 9. Design notes
- <principle / decision / alternative rejected / trade-off>
````

The **Design notes** list the principles that drove notable decisions, the alternatives rejected and why, and any trade-off the reviewer should know about, all about this step only. If the design shows the plan is wrong (a missing prerequisite, an item with the wrong owner), do not note it here: it is a conflict (section 0).

## 5. Self-check, then report

Before reporting, check your file:

- Every requirement and acceptance criterion the plan assigns to this step appears in its tests or checks.
- Names, ids, signatures and paths match the contract, the plan, the dependency step files and the code.
- Shared items are defined in full only if this step creates them; prerequisites appear by name only.
- No other step id appears in the file (search it for `S[0-9]+`: only this step's own id may match), and nothing is described or decided for another step.
- Nothing designed belongs to a non-goal or another step.
- Mermaid syntax is valid.

Then report back in one of these two shapes (short, no file dump).

When there is no conflict:

- **Status:** `ok`
- **File:** path written
- **Summary:** 3 to 6 bullets of the main design decisions
- **Shared items created:** names, for the contract (or "none")
- **Assumptions / questions for the user:** about this step only (or "none")

When there is a conflict (no step file written):

- **Status:** `conflict`
- **Conflicts:** for each one: what it is, the steps and plan sections involved, the evidence (file and quote), and a suggested change to the plan that would remove it (suggestion only, not applied)

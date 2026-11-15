# devpipe tests

Tests live in `tests/`, mirroring the layers in `src/devpipe/`
(see `architecture.md`). Run them with `uv run pytest`.

## What to test

| Layer          | Test                                                        |
|----------------|-------------------------------------------------------------|
| Models         | Domain rules, validation, value behavior                    |
| Persistence    | Reading and writing files: content, versions, bad input     |
| Infrastructure | Calls to external tools, through fakes                      |
| Services       | Use cases and orchestration, with fake dependencies         |
| Views          | Behavior only (see below)                                   |

## GUI tests (`tests/views/`)

GUI tests must test **only** behavior: what happens when the user acts or
when the state changes. Allowed cases:

- **State changes**: a user action or method call changes widget state,
  e.g. a button becomes enabled or disabled, a group becomes locked, a list
  or error box is shown or hidden, a panel switches.
- **Signals**: an action emits (or does not emit) a signal, with the expected
  arguments.
- **Calls to services**: an action triggers the right service call, and the
  resulting files, session or config are written (or left untouched).
- **Error handling**: a failure shows a warning and leaves the state
  consistent.
- **Dialogs and the OS**: an action opens a file/folder dialog, a console or
  a URL, using fakes, and the answer (or a cancel) is handled.

GUI tests must **not** test layout or look:

- Widget sizes, fonts, icons, colors or styles, unless they change to
  show state (e.g. a group's border turning red after a failure).
- Layout order, nesting or which container holds a widget.
- Widget types (`isinstance` on Qt classes).
- Labels, buddies, tooltips, accessible names or button texts, unless
  the text itself is state that changes (e.g. a tab title or a "Retry" label).
- Menu structure, keyboard shortcuts, or static widget settings such as
  closable or movable tabs.

Before adding a GUI test, ask: "Would this fail if the user could no longer
do something, or if state were wrong?" If it only fails when the look
changes, do not write it.

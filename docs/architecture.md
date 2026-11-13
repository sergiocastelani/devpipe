# devpipe architecture

Code in `src/devpipe/` is split into layers. Imports only point down the
stack:

```
views  ->  services  ->  persistence  ->  models
```

| Layer         | Folder         | Responsibility                                          | May import              |
|---------------|----------------|---------------------------------------------------------|-------------------------|
| Composition   | `app.py`       | Builds repositories and services, injects them into views | everything            |
| Views         | `views/`       | Qt widgets; display state, forward user actions to services | `services`, `models` |
| Services      | `services/`    | Use cases and orchestration; no Qt                      | `persistence`, `models` |
| Persistence   | `persistence/` | Read/write devpipe's files (control files, `current-state.json`, `config.json`); no Qt | `models` |
| Models        | `models/`      | Plain data classes, enums, domain rules; no Qt, no I/O  | nothing in the project  |

Layout:

```
src/devpipe/
├── __main__.py      # entry point; calls app.main()
├── app.py
├── models/
├── persistence/
├── services/
└── views/
    ├── main_window.py   # window, tab bar with "+" and closable tabs
    ├── pipeline_tab.py  # one tab: a stack of panels
    └── start_panel.py   # first panel: feature name, Save, start buttons

tests/               # mirrors the layers: models/, persistence/, services/, views/
```

Layer rules are checked by import-linter: `uv run lint-imports`.
If it fails, fix the import direction instead of loosening the contract.

## Tabs and panels

- The main window has one tab per pipeline. The tab bar has a "+" corner button
  that adds a new tab; every tab is closable, and closing the last tab adds a new
  one, so the window always has at least one tab.
- Tabs are added only through `MainWindow.add_pipeline_tab` and removed only
  through `MainWindow.close_tab`.
- Each tab is a `PipelineTab`: a container holding a `QStackedWidget` of panels
  (start, process, ...) that shows exactly one panel at a time, depending on what
  the user is working on. The start panel (`StartPanel`) is always the first panel.
  New panels are added to that stack; the tab structure does not change.
- The tab text and tooltip come from `PipelineTab.title()` / `tooltip()`; a tab
  emits `identity_changed` when they change and the window refreshes the tab bar.
- A new tab is unsaved: its title is "New pipeline". While a tab is unsaved, every
  panel keeps its action buttons disabled; on the start panel only "Save" can be
  enabled, and only when the feature name gives a non-empty slug.

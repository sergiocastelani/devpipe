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
| Persistence   | `persistence/` | Read/write devpipe's files (control files, `current-state.json`, `config.json`, tab state files); no Qt | `models` |
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

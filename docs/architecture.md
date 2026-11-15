# devpipe architecture

Code in `src/devpipe/` is split into layers. Imports only point down the
stack:

```
views  ->  services  ->  persistence     ->  models
                     ->  infrastructure  ->
```

Persistence and infrastructure are siblings: they never import each other.

| Layer         | Folder         | Responsibility                                          | May import              |
|---------------|----------------|---------------------------------------------------------|-------------------------|
| Composition   | `app.py`       | Builds repositories, infrastructure implementations and services, injects them into views | everything |
| Views         | `views/`       | Qt widgets; display state, forward user actions to services | `services`, `models` |
| Services      | `services/`    | Use cases and orchestration; no Qt                      | `persistence`, `infrastructure`, `models` |
| Persistence   | `persistence/` | Read/write devpipe's files (control files, `current-state.json`, `config.json`, tab state files); no Qt | `models` |
| Infrastructure | `infrastructure/` | Talk to external tools (git) through `subprocess`; implements service Protocols; no Qt | `models` |
| Models        | `models/`      | Plain data classes, enums, domain rules; no Qt, no I/O  | nothing in the project  |

Layout:

<!-- Lists structural system folders only. -->

```
src/devpipe/
├── infrastructure/  # talks to external tools (git, terminal windows)
├── models/          # plain data classes, enums and domain rules
├── persistence/     # reads and writes devpipe's files
├── services/        # use cases and orchestration
└── views/           # Qt widgets: main window, tabs, panels and reusable controls

tests/               # mirrors the layers: models/, persistence/, services/, infrastructure/, views/
                     # tests/infrastructure opens real windows: opt in with DEVPIPE_TERMINAL_TESTS=1
```

Layer rules are checked by import-linter: `uv run lint-imports`.
If it fails, fix the import direction instead of loosening the contract.
